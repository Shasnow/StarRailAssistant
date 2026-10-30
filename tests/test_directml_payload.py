"""验证构建工具的公开命令行，不修改现有安装。"""
import os
from pathlib import Path
import subprocess
import sys
import json
import hashlib

import pytest


def test_payload_rejects_unverified_wheel_without_creating_output(tmp_path):
    wheel = tmp_path / "untrusted.whl"
    wheel.write_bytes(b"not the pinned official wheel")
    output = tmp_path / "runtime"
    result = subprocess.run(
        [sys.executable, "scripts/prepare_directml.py", "--wheel", str(wheel), "--output", str(output)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=30,
        env=dict(os.environ, PYTHONUTF8="1"))
    assert result.returncode != 0
    assert b"SHA256" in result.stderr
    assert not output.exists()


@pytest.fixture(scope="module")
def runtime_payload(tmp_path_factory):
    wheel = os.environ.get("SRA_DIRECTML_WHEEL")
    if not wheel:
        pytest.skip("Set SRA_DIRECTML_WHEEL to test the real, checksum-pinned optional payload")
    output = tmp_path_factory.mktemp("directml-build-input") / "runtime"
    result = subprocess.run(
        [sys.executable, "scripts/prepare_directml.py", "--wheel", wheel, "--output", str(output)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=60,
        env=dict(os.environ, PYTHONUTF8="1"))
    assert result.returncode == 0, result.stderr.decode("utf-8")
    return output


def test_prepared_runtime_is_complete_coherent_and_preserves_licenses(runtime_payload):
    manifest = json.loads((runtime_payload / "directml-runtime.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((runtime_payload / name).read_bytes()).hexdigest() == expected
    for name in ("LICENSE", "ThirdPartyNotices.txt", "directml/LICENSE.txt"):
        assert (runtime_payload / "onnxruntime" / name).is_file()
    code = "import onnxruntime as o; assert o.__version__ == o.get_version_string() == '1.24.4'"
    result = subprocess.run([sys.executable, "-c", code],
                            env=dict(os.environ, PYTHONPATH=str(runtime_payload)), capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode("utf-8")


def test_absent_directml_dll_does_not_break_startup_or_cpu_ocr(runtime_payload, tmp_path):
    import rapidocr

    models = Path(rapidocr.__file__).parent / "models"
    required = ("PP-OCRv6_det_small.onnx", "ch_ppocr_mobile_v2.0_cls_mobile.onnx", "PP-OCRv6_rec_small.onnx")
    if not all((models / name).is_file() for name in required):
        pytest.skip("Install the unchanged OCR models first; this test never downloads models")
    dll = runtime_payload / "onnxruntime/capi/DirectML.dll"
    disabled = dll.with_suffix(".disabled")
    dll.rename(disabled)
    env = dict(os.environ, PYTHONPATH=str(runtime_payload), SRA_OCR_PROVIDER="directml", APPDATA=str(tmp_path),
               PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    try:
        code = ("from SRACore.operators.factory import OperatorFactory; import numpy as np; "
                "o = OperatorFactory.get_ocr_instance(); "
                "r=o(np.full((48,192,3),255,dtype=np.uint8),use_det=True,use_cls=False,use_rec=True); "
                "assert r.txts is None; "
                "assert o.text_det.session.session.get_providers()==['CPUExecutionProvider']; "
                "assert o.text_rec.session.session.get_providers()==['CPUExecutionProvider']")
        ocr = subprocess.run([sys.executable, "-c", code], capture_output=True, env=env, timeout=60)
        assert ocr.returncode == 0, ocr.stderr.decode("utf-8")
        startup = subprocess.run([sys.executable, "main.py", "--no-admin", "-c", "exit"],
                                  capture_output=True, env=env, timeout=30)
        assert startup.returncode == 0, startup.stderr.decode("utf-8")
    finally:
        disabled.rename(dll)


def test_packaging_copies_verified_native_files_and_license_material(tmp_path):
    import onnxruntime as ort
    from scripts.directml_runtime import copy_directml_runtime

    if "DmlExecutionProvider" not in ort.get_available_providers():
        pytest.skip("Requires the optional build runtime")
    assert copy_directml_runtime(tmp_path)
    for name in ("DirectML.dll", "onnxruntime.dll", "onnxruntime_providers_shared.dll", "onnxruntime_pybind11_state.pyd"):
        assert (tmp_path / "onnxruntime/capi" / name).is_file()
    for name in ("LICENSE", "ThirdPartyNotices.txt", "directml/LICENSE.txt"):
        assert (tmp_path / "onnxruntime" / name).is_file()
    info = json.loads((tmp_path / "directml-runtime.json").read_text(encoding="utf-8"))
    assert info["python_package"] == info["native_runtime"] == "1.24.4"


def test_packaging_does_not_duplicate_nuitkas_root_directml_library(tmp_path):
    import shutil
    import onnxruntime as ort
    from scripts.directml_runtime import copy_directml_runtime

    if "DmlExecutionProvider" not in ort.get_available_providers():
        pytest.skip("Requires optional DirectML build input")
    shutil.copyfile(Path(ort.__file__).parent / "capi/DirectML.dll", tmp_path / "directml.dll")
    copy_directml_runtime(tmp_path)
    copies = [path for path in tmp_path.rglob("*") if path.name.lower() == "directml.dll"]
    assert len(copies) == 1
