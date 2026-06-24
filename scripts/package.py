#   <StarRailAssistant:An automated program that helps you complete daily task of StarRail.>
#   Copyright © <2024> <Shasnow>

#   This file is part of StarRailAssistant.

#   StarRailAssistant is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the Free Software Foundation,
#   either version 3 of the License, or (at your option) any later version.

#   StarRailAssistant is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#   without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#   See the GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License along with StarRailAssistant.
#   If not, see <https://www.gnu.org/licenses/>.

#   yukikage@qq.com

"""
崩坏：星穹铁道助手
作者：雪影
打包
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT_PATH = Path(__file__).resolve().parent.parent
DESKTOP_WIN_X64_PUBLISH_PATH = ROOT_PATH / "SRAFrontend" / "SRAFrontend.Desktop" / "bin" / "Release" / "net10.0" / "win-x64" / "publish"
SERVER_WIN_X64_PUBLISH_PATH = ROOT_PATH / "SRAFrontend" / "SRAFrontend.Server" / "bin" / "Release" / "net10.0" / "win-x64" / "publish"
DIST_DIR = ROOT_PATH / "main.dist"
PYTHON31210_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
SITE_PACKAGES_DIR = None
for p in sys.path[1:]:
    if p.endswith("site-packages"):
        SITE_PACKAGES_DIR = Path(p)
        break
if SITE_PACKAGES_DIR is None:
    print(f"[ERROR] Could not find site-packages directory in sys.path: {sys.path}")
    sys.exit(1)

def add_to_zip(zipf: ZipFile, path: Path, base_path: Path | None = None):
    if base_path is None:
        base_path = path.parent
    if not path.exists():
        print(f"  [WARN] Skipping non-existent path: {path}")
        return
    if path.is_file():
        zipf.write(path, path.relative_to(base_path))
        return
    for file in sorted(path.rglob("*")):
        if file.is_file():
            zipf.write(file, file.relative_to(base_path))


class ZipBuilder:
    """增量构建 zip：收集文件条目，不同阶段快照写入不同 zip。"""

    def __init__(self):
        self._entries: dict[str, Path] = {}  # arcname -> source path

    def add(self, path: Path, base_path: Path | None = None):
        if base_path is None:
            base_path = path.parent
        if not path.exists():
            print(f"  [WARN] Skipping non-existent path: {path}")
            return
        if path.is_file():
            self._entries[str(path.relative_to(base_path))] = path
            return
        for file in sorted(path.rglob("*")):
            if file.is_file():
                self._entries[str(file.relative_to(base_path))] = file

    def add_file(self, file: Path, arcname: str):
        self._entries[arcname] = file

    def snapshot(self, zip_path: Path):
        """将当前所有条目写入 zip 文件。"""
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zipf:
            for arcname, src in self._entries.items():
                zipf.write(src, arcname)
        print(f"[OK] {zip_path.name} ({len(self._entries)} files)")


def collect_core_files(builder: ZipBuilder):
    """收集 Core 层文件：Nuitka 产物 + 资源文件。"""
    for item in DIST_DIR.iterdir():
        builder.add(item)


def nuitka_build(version: str):
    file_version = version.split("-")[0]
    print("Building Python program with Nuitka ...")
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone", "--mingw64",
        "--windows-console-mode=force", "--windows-uac-admin",
        "--windows-icon-from-ico=resources/SRAicon.ico",
        "--company-name=StarRailAssistant Team",
        "--product-name=StarRailAssistant",
        f"--file-version={file_version}",
        f"--product-version={file_version}",
        "--file-description=StarRailAssistant Component",
        "--copyright=Copyright 2024 Shasnow",
        "--assume-yes-for-downloads",
        "--output-filename=SRA-cli",
        "--include-module=selenium.webdriver.common.action_chains",
        "--remove-output",
        "main.py",
    ]
    result = subprocess.run(cmd, cwd=ROOT_PATH)
    if result.returncode != 0:
        print(f"[ERROR] Nuitka build failed (exit code: {result.returncode})")
        sys.exit(1)
    print("[OK] Python program built successfully")

def copy_core_resources(dist: Path):
    print("Copying resources ...")
    dist.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT_PATH / "LICENSE", dist / "LICENSE")
    shutil.copy2(ROOT_PATH / "README.md", dist / "README.md")
    # shutil.copy2(ROOT_PATH / "requirements.txt", dist / "requirements.txt")
    # shutil.copy2(ROOT_PATH / "requirements-linux.txt", dist / "requirements-linux.txt")
    # shutil.copy2(ROOT_PATH / "main.py", dist / "main.py")
    # shutil.copytree(ROOT_PATH / "SRACore", dist / "SRACore")
    (DIST_DIR / "SRACore" / "localization").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT_PATH / "SRACore" / "localization" / "resource_en-us.json", DIST_DIR / "SRACore" / "localization" / "resource_en-us.json")
    shutil.copy2(ROOT_PATH / "SRACore" / "localization" / "resource_zh-cn.json", DIST_DIR / "SRACore" / "localization" / "resource_zh-cn.json")
    shutil.copytree(ROOT_PATH / "resources", dist / "resources")
    (dist / "rapidocr_onnxruntime").mkdir(parents=True, exist_ok=True)
    shutil.copytree(SITE_PACKAGES_DIR / "rapidocr_onnxruntime" / "models", dist / "rapidocr_onnxruntime" / "models")
    shutil.copy2(SITE_PACKAGES_DIR / "rapidocr_onnxruntime" / "config.yaml", dist / "rapidocr_onnxruntime" / "config.yaml")
    shutil.copytree(ROOT_PATH / "tasks", dist / "tasks")
    print("[OK] Resources copied")


def package_lite(version: str):
    print("Packaging Lite ...")
    lite_zip_path = ROOT_PATH / f"StarRailAssistant_Lite_v{version}.zip"
    with ZipFile(lite_zip_path, "w", compression=ZIP_DEFLATED) as zipf:
        for file in DESKTOP_WIN_X64_PUBLISH_PATH.iterdir():
            add_to_zip(zipf, file)
        for item in ["SRACore", "tasks", "resources"]:
            add_to_zip(zipf, ROOT_PATH / item)
        for file in ["main.py", "README.md", "LICENSE", "requirements.txt", "requirements-linux.txt"]:
            add_to_zip(zipf, ROOT_PATH / file)
    print(f"[OK] Lite package: {lite_zip_path.name}")


if __name__ == "__main__":
    with (ROOT_PATH / "package.json").open(encoding="utf-8") as f:
        data = json.load(f)
    version = data["version"]

    with (ROOT_PATH / "ChangeLog2.0.md").open(encoding="utf-8") as f:
        changelog = f.read()

    nuitka_build(version)
    copy_core_resources(DIST_DIR)

    # Lite（独立流程，不使用 ZipBuilder）
    package_lite(version)

    # Core → Basic → Full 增量构建
    builder = ZipBuilder()

    print("Packaging Core ...")
    collect_core_files(builder)
    builder.snapshot(ROOT_PATH / f"StarRailAssistant_Core_v{version}.zip")

    print("Packaging Basic ...")
    builder.add(DESKTOP_WIN_X64_PUBLISH_PATH, DESKTOP_WIN_X64_PUBLISH_PATH)
    builder.snapshot(ROOT_PATH / f"StarRailAssistant_v{version}.zip")

    print("Packaging Full ...")
    builder.add(SERVER_WIN_X64_PUBLISH_PATH, SERVER_WIN_X64_PUBLISH_PATH)
    builder.snapshot(ROOT_PATH / f"StarRailAssistant_Full_v{version}.zip")

    print("Packaging ServerDLC ...")
    server_dlc = ZipBuilder()
    server_dlc.add(SERVER_WIN_X64_PUBLISH_PATH, SERVER_WIN_X64_PUBLISH_PATH)
    server_dlc.snapshot(ROOT_PATH / f"StarRailAssistant_ServerDLC_v{version}.zip")

    print("Packaging DesktopDLC ...")
    desktop_dlc = ZipBuilder()
    desktop_dlc.add(DESKTOP_WIN_X64_PUBLISH_PATH, DESKTOP_WIN_X64_PUBLISH_PATH)
    desktop_dlc.snapshot(ROOT_PATH / f"StarRailAssistant_DesktopDLC_v{version}.zip")

    print("Packaging Resources ...")
    resources_zip = ZipBuilder()
    resources_zip.add(ROOT_PATH / "tasks", ROOT_PATH / "tasks")
    resources_zip.add(ROOT_PATH / "resources", ROOT_PATH / "resources")
    resources_zip.add_file(ROOT_PATH / "package.json", "package.json")
    resources_zip.snapshot(ROOT_PATH / f"StarRailAssistant_Resources_v{version}.zip")

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    (ROOT_PATH / "version_info.txt").write_text(f"v{version}\n\n{changelog}", encoding="utf-8")
    print(f"\nPackaging completed! Version: v{version}")
