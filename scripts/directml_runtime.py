"""为可选 DirectML 构建保留完整 native 组件及各自许可证。"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

try:
    from .prepare_directml import ROOT, WHEEL_NAME, WHEEL_SHA256, WHEEL_URL, DIRECTML_LICENSE_URL, sha256
except ImportError:
    from prepare_directml import ROOT, WHEEL_NAME, WHEEL_SHA256, WHEEL_URL, DIRECTML_LICENSE_URL, sha256

NATIVE_SHA256 = {
    "DirectML.dll": "b73972115320e906a49602f2027a3266622881b0d325ba685e0f165a9482a8d7",
    "onnxruntime.dll": "302c69f9779d63ef4ab90316e59444c4acbaca7fe3455020d79d10bcfcb00715",
    "onnxruntime_providers_shared.dll": "f6bbae3af4c0673b0d1e6ca8db900dc85ad959a395b69d361038ec7995cc2652",
    "onnxruntime_pybind11_state.pyd": "40ed801d209e57751643581a8c70fe1a72a3df80b1ce88f26f7950cd1a83ac35",
}


def copy_directml_runtime(dist: Path) -> bool:
    import onnxruntime as ort

    if "DmlExecutionProvider" not in ort.get_available_providers():
        return False  # 默认 CPU 构建完全不增加 DirectML 文件。
    if sys.platform != "win32" or sys.version_info[:2] != (3, 12) or sys.maxsize <= 2**32:
        raise RuntimeError("The pinned DirectML build input requires Windows x64 CPython 3.12")
    if ort.__version__ != "1.24.4" or ort.get_version_string() != "1.24.4":
        raise RuntimeError("DirectML packaging requires the complete matching Python/native runtime 1.24.4")
    package = Path(ort.__file__).parent
    files = {}
    root_dml = next((p for p in dist.glob("*") if p.is_file() and p.name.lower() == "directml.dll"), None)
    if root_dml and (dist / "onnxruntime/capi/DirectML.dll").exists():
        raise ValueError("Duplicate DirectML libraries; use a fresh build output")
    for name, expected in NATIVE_SHA256.items():
        source = package / "capi" / name
        if sha256(source) != expected:
            raise ValueError(f"SHA256 mismatch: {source}")
        # Nuitka 的依赖扫描可能已经将 DirectML.dll 放在应用根目录。
        relative = root_dml.name if name == "DirectML.dll" and root_dml else "onnxruntime/capi/" + name
        files[relative] = source
    for name in ("LICENSE", "ThirdPartyNotices.txt"):
        files["onnxruntime/" + name] = package / name
    files["onnxruntime/directml/LICENSE.txt"] = ROOT / "docs/licenses/DirectML-1.15.4.txt"
    digests = {name: sha256(source) for name, source in files.items()}
    for name, expected in digests.items():
        target = dist / name
        if target.exists() and sha256(target) != expected:
            raise ValueError(f"Refusing to mix conflicting runtime files: {target}")
    for name, source in files.items():
        target = dist / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    info = {"distribution": "onnxruntime-directml", "python_package": ort.__version__,
            "native_runtime": ort.get_version_string(), "directml": "1.15.4", "wheel": WHEEL_NAME,
            "wheel_url": WHEEL_URL, "wheel_sha256": WHEEL_SHA256,
            "directml_license_url": DIRECTML_LICENSE_URL, "files": digests}
    (dist / "directml-runtime.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    return True
