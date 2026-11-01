"""准备完整、版本一致的官方 DirectML wheel，作为独立构建输入；不安装包。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import urllib.request
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
WHEEL_NAME = "onnxruntime_directml-1.24.4-cp312-cp312-win_amd64.whl"
WHEEL_SHA256 = "f2ecb68b7b7b259d2ef3112ae760149f9b5a1e7c0fbb73d539da6250a648a614"
WHEEL_URL = ("https://files.pythonhosted.org/packages/88/ea/"
             "33814eb0ec96775eda4c1d30b0d86e91d7d2cd0d84c66d3915aef0e06fa3/" + WHEEL_NAME)
DIRECTML_LICENSE_URL = "https://www.nuget.org/packages/Microsoft.AI.DirectML/1.15.4/License"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(wheel: Path, output: Path):
    if sha256(wheel) != WHEEL_SHA256:
        raise ValueError("SHA256 mismatch: refusing an unverified DirectML wheel")
    if output.exists():
        raise FileExistsError("--output must not exist; never overlay an installation")
    with ZipFile(wheel) as archive:
        if archive.testzip() is not None:
            raise ValueError("Wheel CRC verification failed")
        for name in archive.namelist():
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
                raise ValueError("Unsafe wheel path")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="sra-directml-", dir=output.parent) as temporary:
            payload = Path(temporary) / "runtime"
            payload.mkdir()
            archive.extractall(payload)
            license_dir = payload / "onnxruntime" / "directml"
            license_dir.mkdir()
            shutil.copyfile(ROOT / "docs/licenses/DirectML-1.15.4.txt", license_dir / "LICENSE.txt")
            manifest = {
                "distribution": "onnxruntime-directml", "python_package": "1.24.4", "native_runtime": "1.24.4",
                "directml": "1.15.4", "python_abi": "cp312", "platform": "win_amd64",
                "wheel": WHEEL_NAME, "wheel_url": WHEEL_URL, "wheel_sha256": WHEEL_SHA256,
                "directml_license_url": DIRECTML_LICENSE_URL,
                "files": {p.relative_to(payload).as_posix(): sha256(p) for p in sorted(payload.rglob("*")) if p.is_file()},
            }
            (payload / "directml-runtime.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            payload.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, help="Reuse the pinned official wheel without downloading")
    parser.add_argument("--download", action="store_true", help="Explicitly allow the pinned PyPI download")
    parser.add_argument("--output", type=Path, required=True, help="New build-input directory, not an existing app")
    args = parser.parse_args()
    if not args.wheel and not args.download:
        parser.error("Supply --wheel or explicitly allow --download")
    if args.output.exists():
        parser.error("--output must not exist; never overlay an installation")
    try:
        if args.wheel:
            prepare(args.wheel, args.output.resolve())
        else:
            args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="sra-directml-download-", dir=args.output.resolve().parent) as temporary:
                wheel = Path(temporary) / WHEEL_NAME
                with urllib.request.urlopen(WHEEL_URL, timeout=120) as response, wheel.open("wb") as stream:
                    shutil.copyfileobj(response, stream)
                prepare(wheel, args.output.resolve())
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"Prepared complete DirectML runtime: {args.output.resolve()}")


if __name__ == "__main__":
    main()
