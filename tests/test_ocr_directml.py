"""通过公开 OCR 工厂检查可选 provider；不截屏、不下载模型、不发送输入。"""
from pathlib import Path

import numpy as np
import pytest
import rapidocr
from PIL import Image, ImageDraw, ImageFont

from SRACore.operators.factory import OperatorFactory


@pytest.fixture
def ocr_factory(monkeypatch):
    models = Path(rapidocr.__file__).parent / "models"
    required = ("PP-OCRv6_det_small.onnx", "ch_ppocr_mobile_v2.0_cls_mobile.onnx", "PP-OCRv6_rec_small.onnx")
    if not all((models / name).is_file() for name in required):
        pytest.skip("Install the unchanged RapidOCR models before running OCR integration tests")
    # 每个场景使用自己的公开工厂实例，不修改全局单例。
    class TestFactory(OperatorFactory):
        pass

    monkeypatch.setenv("SRA_OCR_PROVIDER", "cpu")
    return TestFactory


def test_requested_directml_without_provider_reports_cpu_fallback(ocr_factory, monkeypatch):
    import onnxruntime
    from loguru import logger

    monkeypatch.setenv("SRA_OCR_PROVIDER", "directml")
    monkeypatch.setattr(onnxruntime, "get_available_providers", lambda: ["CPUExecutionProvider"])
    messages = []
    sink = logger.add(lambda message: messages.append(str(message)))
    try:
        engine = ocr_factory.get_ocr_instance()
        result = engine(np.full((48, 192, 3), 255, dtype=np.uint8), use_det=True, use_cls=False, use_rec=True)
    finally:
        logger.remove(sink)
    assert result.txts is None
    assert any("DirectML" in message and "CPU" in message for message in messages)
    assert engine.text_det.session.session.get_providers() == ["CPUExecutionProvider"]
    assert engine.text_cls.session.session.get_providers() == ["CPUExecutionProvider"]
    assert engine.text_rec.session.session.get_providers() == ["CPUExecutionProvider"]


def test_directml_executes_detector_and_recognizer_but_keeps_classifier_on_cpu(ocr_factory, monkeypatch, tmp_path):
    import json
    import onnxruntime as ort

    if "DmlExecutionProvider" not in ort.get_available_providers():
        pytest.skip("This test requires the optional DirectML runtime and a compatible GPU")
    monkeypatch.setenv("SRA_OCR_PROVIDER", "directml")
    original_session = ort.InferenceSession
    gpu_sessions = []

    def profiled_session(path, sess_options=None, providers=None, **kwargs):
        if providers and "DmlExecutionProvider" in [item[0] if isinstance(item, tuple) else item for item in providers]:
            assert not sess_options.enable_mem_pattern
            assert sess_options.execution_mode == ort.ExecutionMode.ORT_SEQUENTIAL
            sess_options.enable_profiling = True
            sess_options.profile_file_prefix = str(tmp_path / Path(path).stem)
            session = original_session(path, sess_options=sess_options, providers=providers, **kwargs)
            gpu_sessions.append(session)
            return session
        return original_session(path, sess_options=sess_options, providers=providers, **kwargs)

    monkeypatch.setattr(ort, "InferenceSession", profiled_session)
    engine = ocr_factory.get_ocr_instance()
    image = Image.new("RGB", (256, 64), "white")
    ImageDraw.Draw(image).text((8, 8), "12345", fill="black", font=ImageFont.load_default(size=36))
    result = engine(image, use_det=True, use_cls=False, use_rec=True)
    assert result.txts == ("12345",)
    assert engine.text_det.session.session.get_providers()[0] == "DmlExecutionProvider"
    assert engine.text_rec.session.session.get_providers()[0] == "DmlExecutionProvider"
    assert engine.text_cls.session.session.get_providers() == ["CPUExecutionProvider"]
    assert len(gpu_sessions) == 2
    for session in gpu_sessions:
        profile = json.loads(Path(session.end_profiling()).read_text(encoding="utf-8"))
        assert any(event.get("args", {}).get("provider") == "DmlExecutionProvider" for event in profile)


def test_failed_gpu_run_retries_on_cpu_and_stays_on_cpu(ocr_factory, monkeypatch):
    import onnxruntime as ort
    from onnxruntime.capi.onnxruntime_pybind11_state import EPFail

    if "DmlExecutionProvider" not in ort.get_available_providers():
        pytest.skip("Requires optional DirectML runtime")
    monkeypatch.setenv("SRA_OCR_PROVIDER", "directml")
    original_session = ort.InferenceSession
    failures = []

    def failing_session(path, **kwargs):
        session = original_session(path, **kwargs)
        if "rec" in Path(path).name and session.get_providers()[0] == "DmlExecutionProvider":
            def device_removed(*args, **kwargs):
                failures.append("device removed")
                raise EPFail("Injected GPU device removal at the native runtime boundary")
            session.run = device_removed
        return session

    monkeypatch.setattr(ort, "InferenceSession", failing_session)
    engine = ocr_factory.get_ocr_instance()
    image = Image.new("RGB", (256, 64), "white")
    ImageDraw.Draw(image).text((8, 8), "12345", fill="black", font=ImageFont.load_default(size=36))
    for _ in range(3):
        assert engine(image, use_det=True, use_cls=False, use_rec=True).txts == ("12345",)
    assert engine.text_det.session.session.get_providers() == ["CPUExecutionProvider"]
    assert engine.text_rec.session.session.get_providers() == ["CPUExecutionProvider"]
    assert failures == ["device removed"]


def test_gpu_initialization_error_preserves_working_cpu_ocr(ocr_factory, monkeypatch):
    import onnxruntime as ort

    monkeypatch.setenv("SRA_OCR_PROVIDER", "directml")
    monkeypatch.setattr(ort, "get_available_providers", lambda: ["DmlExecutionProvider", "CPUExecutionProvider"])
    original_session = ort.InferenceSession

    def rejected_session(path, **kwargs):
        if kwargs.get("providers", [None])[0] == ("DmlExecutionProvider", {"device_id": 0}):
            raise RuntimeError("Injected adapter initialization failure")
        return original_session(path, **kwargs)

    monkeypatch.setattr(ort, "InferenceSession", rejected_session)
    engine = ocr_factory.get_ocr_instance()
    image = Image.new("RGB", (256, 64), "white")
    ImageDraw.Draw(image).text((8, 8), "12345", fill="black", font=ImageFont.load_default(size=36))
    assert engine(image, use_det=True, use_cls=False, use_rec=True).txts == ("12345",)
    assert engine.text_det.session.session.get_providers() == ["CPUExecutionProvider"]
    assert engine.text_rec.session.session.get_providers() == ["CPUExecutionProvider"]


def test_forced_cpu_works_with_repeated_calls_and_classifier(ocr_factory):
    engine = ocr_factory.get_ocr_instance()
    assert ocr_factory.get_ocr_instance() is engine
    image = Image.new("RGB", (256, 64), "white")
    ImageDraw.Draw(image).text((8, 8), "12345", fill="black", font=ImageFont.load_default(size=36))
    for use_cls in (False, True, False):
        assert engine(image, use_det=True, use_cls=use_cls, use_rec=True).txts == ("12345",)
    for model in (engine.text_det, engine.text_cls, engine.text_rec):
        assert model.session.session.get_providers() == ["CPUExecutionProvider"]


def test_unset_provider_preserves_the_original_cpu_pipeline(ocr_factory, monkeypatch):
    monkeypatch.delenv("SRA_OCR_PROVIDER", raising=False)
    engine = ocr_factory.get_ocr_instance()
    assert type(engine) is rapidocr.RapidOCR
    image = Image.new("RGB", (256, 64), "white")
    ImageDraw.Draw(image).text((8, 8), "12345", fill="black", font=ImageFont.load_default(size=36))
    assert engine(image, use_det=True, use_cls=False, use_rec=True).txts == ("12345",)
    for model in (engine.text_det, engine.text_cls, engine.text_rec):
        assert model.session.session.get_providers() == ["CPUExecutionProvider"]


def test_python_native_version_mismatch_does_not_enable_gpu(ocr_factory, monkeypatch):
    import onnxruntime as ort

    monkeypatch.setenv("SRA_OCR_PROVIDER", "directml")
    monkeypatch.setattr(ort, "__version__", "incompatible-python-package")
    engine = ocr_factory.get_ocr_instance()
    assert engine.text_det.session.session.get_providers() == ["CPUExecutionProvider"]
    assert engine.text_rec.session.session.get_providers() == ["CPUExecutionProvider"]


def test_directml_serializes_concurrent_public_ocr_calls(ocr_factory, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import onnxruntime as ort

    if "DmlExecutionProvider" not in ort.get_available_providers():
        pytest.skip("Requires optional DirectML runtime")
    monkeypatch.setenv("SRA_OCR_PROVIDER", "directml")
    engine = ocr_factory.get_ocr_instance()
    image = Image.new("RGB", (256, 64), "white")
    ImageDraw.Draw(image).text((8, 8), "12345", fill="black", font=ImageFont.load_default(size=36))

    def recognize(_index):
        return engine(image, use_det=True, use_cls=False, use_rec=True).txts

    with ThreadPoolExecutor(max_workers=4) as workers:
        assert list(workers.map(recognize, range(12))) == [("12345",)] * 12
