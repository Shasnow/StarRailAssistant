"""可选的真实CPU OCR集成：离线图片与虚拟导航，不连接游戏或下载模型。"""
import os
from pathlib import Path
import socket
from types import SimpleNamespace

from PIL import Image
import pytest

from tests.test_cw_terminal_reliability import TerminalOperator, engine

pytestmark = pytest.mark.skipif(os.environ.get("SRA_CW_REAL_OCR") != "1",
                                reason="opt in with SRA_CW_REAL_OCR=1 and preinstalled OCR models")


@pytest.fixture(scope="module")
def cpu_ocr():
    import rapidocr
    from SRACore.operators.factory import OperatorFactory

    models = Path(rapidocr.__file__).parent / "models"
    if not all((models / name).is_file() for name in (
            "PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx", "ch_ppocr_mobile_v2.0_cls_mobile.onnx")):
        pytest.skip("preinstalled PP-OCRv6 and classifier models required; no downloads allowed")

    def no_network(*args, **kwargs):
        raise AssertionError("offline OCR integration forbids network access")

    with pytest.MonkeyPatch.context() as context:
        context.setattr(socket.socket, "connect", no_network)
        context.setattr(socket.socket, "connect_ex", no_network)
        context.setattr(socket, "create_connection", no_network)
        ocr = OperatorFactory.get_ocr_instance()
        for model in (ocr.text_det, ocr.text_cls, ocr.text_rec):
            assert model.session.session.get_providers() == ["CPUExecutionProvider"]
        yield ocr


@pytest.mark.parametrize("case", ["terminal_overclock", "terminal_recorded_235133"])
def test_real_cpu_ocr_navigates_saved_summary_to_synthetic_main_menu(tmp_path, monkeypatch, cpu_ocr, case):
    operator = TerminalOperator()
    with Image.open(Path(__file__).parent / "fixtures" / case / "summary.png") as crop:
        frame = Image.new("RGB", (1920, 1080))
        frame.paste(crop.convert("RGB"), (500, 160))
    operator.pages["summary"] = frame
    operator.ocr_engine = cpu_ocr
    monkeypatch.setattr(engine, "time", SimpleNamespace(monotonic=operator.clock.monotonic))
    task = engine.CurrencyWars(operator, 1, data_dir=tmp_path)
    task._vision.max_samples = 0
    task.REWARD_TRANSITION_TIMEOUT = 20

    assert task.handle_game_over(None) is True
    assert operator.page == "main"
    assert operator.clicks == ["终局：final_summary", "终局：final_next_page", "终局：final_return"]
