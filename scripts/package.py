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
WIN_X64_PUBLISH_PATH = ROOT_PATH / "SRAFrontend" / "bin" / "Release" / "net8.0" / "win-x64" / "publish"
DIST_DIR = ROOT_PATH / "main.dist"


def add_to_zip(zipf: ZipFile, path: Path, base_path: Path = None):
    if base_path is None:
        base_path = path.parent
    if not path.exists():
        print(f"  [WARN] 跳过不存在的路径: {path}")
        return
    if path.is_file():
        zipf.write(path, path.relative_to(base_path))
        return
    for file in sorted(path.rglob("*")):
        if file.is_file():
            zipf.write(file, file.relative_to(base_path))


def copy_json_tree(src: Path, dst: Path):
    dst.mkdir(parents=True, exist_ok=True)
    for json_file in src.glob("*.json"):
        shutil.copy2(json_file, dst / json_file.name)


def nuitka_build(version: str):
    file_version = version.split("-")[0]
    print("正在编译 Python 程序 (Nuitka) ...")
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
        print(f"[ERROR] Nuitka 编译失败 (exit code: {result.returncode})")
        sys.exit(1)
    print("[OK] Python 程序编译完成")


def copy_core_resources(dist: Path):
    print("正在复制资源文件 ...")
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "SRACore").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT_PATH / "SRACore" / "config.toml", dist / "SRACore" / "config.toml")
    shutil.copy2(ROOT_PATH / "LICENSE", dist / "LICENSE")
    shutil.copy2(ROOT_PATH / "README.md", dist / "README.md")
    shutil.copytree(ROOT_PATH / "resources", dist / "resources")
    copy_json_tree(ROOT_PATH / "SRACore" / "localization", dist / "SRACore" / "localization")
    shutil.copytree(ROOT_PATH / "rapidocr_onnxruntime", dist / "rapidocr_onnxruntime")
    shutil.copytree(ROOT_PATH / "tasks", dist / "tasks")
    print("[OK] 资源文件复制完成")


def package_core(version: str):
    print("正在打包 Core 包 ...")
    core_zip_path = ROOT_PATH / f"StarRailAssistant_Core_v{version}.zip"
    with ZipFile(core_zip_path, "w", compression=ZIP_DEFLATED) as zipf:
        for item in DIST_DIR.iterdir():
            add_to_zip(zipf, item)
    print(f"[OK] Core 包: {core_zip_path.name}")


def package_code(version: str):
    print("正在打包 Code 包 ...")
    code_zip_path = ROOT_PATH / f"StarRailAssistant_Code_v{version}.zip"
    with ZipFile(code_zip_path, "w", compression=ZIP_DEFLATED) as zipf:
        for item in ["SRACore", "tasks", "resources"]:
            add_to_zip(zipf, ROOT_PATH / item)
        for file in ["main.py", "README.md", "LICENSE", "requirements.txt"]:
            add_to_zip(zipf, ROOT_PATH / file)
    print(f"[OK] Code 包: {code_zip_path.name}")


def package_lite(version: str):
    print("正在打包 Lite 包 ...")
    lite_zip_path = ROOT_PATH / f"StarRailAssistant_Lite_v{version}.zip"
    with ZipFile(lite_zip_path, "w", compression=ZIP_DEFLATED) as zipf:
        for file in WIN_X64_PUBLISH_PATH.iterdir():
            add_to_zip(zipf, file)
        for item in ["SRACore", "tasks", "resources"]:
            add_to_zip(zipf, ROOT_PATH / item)
        for file in ["main.py", "README.md", "LICENSE", "requirements.txt"]:
            add_to_zip(zipf, ROOT_PATH / file)
    print(f"[OK] Lite 包: {lite_zip_path.name}")


def package_full(version: str):
    shutil.copytree(WIN_X64_PUBLISH_PATH, DIST_DIR, dirs_exist_ok=True)
    print("正在打包 Full 包 ...")
    full_zip_path = ROOT_PATH / f"StarRailAssistant_v{version}.zip"
    with ZipFile(full_zip_path, "w", compression=ZIP_DEFLATED) as zipf:
        for file in DIST_DIR.iterdir():
            add_to_zip(zipf, file)
    print(f"[OK] Full 包: {full_zip_path.name}")


if __name__ == "__main__":
    with (ROOT_PATH / "package.json").open(encoding="utf-8") as f:
        data = json.load(f)
    version = data["version"]

    with (ROOT_PATH / "ChangeLog2.0.md").open(encoding="utf-8") as f:
        changelog = f.read()

    nuitka_build(version)
    copy_core_resources(DIST_DIR)

    package_core(version)
    package_code(version)
    package_lite(version)
    package_full(version)

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    (ROOT_PATH / "version_info.txt").write_text(f"v{version}\n\n{changelog}", encoding="utf-8")
    print(f"\n打包完成! 版本: v{version}")
