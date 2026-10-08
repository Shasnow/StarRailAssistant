#   <StarRailAssistant:An automated program that helps you complete daily task of StarRail.>
#   Copyright © <2024> <Shasnow>

#   This file is part of StarRailAssistant.

#   StarRailAssistant is free software: you can redistribute it and/or modify it
#   under the terms of the GNU Affero General Public License as published by the Free Software Foundation,
#   either version 3 of the License, or (at your option) any later version.

#   StarRailAssistant is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#   without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#   See the GNU Affero General Public License for more details.

#   You should have received a copy of the GNU Affero General Public License along with StarRailAssistant.
#   If not, see <https://www.gnu.org/licenses/>.

#   yukikage@qq.com

"""
崩坏：星穹铁道助手
作者：雪影
打包
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT_PATH = Path(__file__).resolve().parent.parent
DOTNET_EXE = os.environ.get("DOTNET_EXE", "dotnet")
DESKTOP_WIN_X64_PUBLISH_PATH = ROOT_PATH / "SRAFrontend" / "SRAFrontend.Desktop" / "bin" / "Release" / "net10.0" / "win-x64" / "publish"
SERVER_WIN_X64_PUBLISH_PATH = ROOT_PATH / "SRAFrontend" / "SRAFrontend.Server" / "bin" / "Release" / "net10.0" / "win-x64" / "publish"
DIST_DIR = ROOT_PATH / "main.dist"
PYTHON31210_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
# R2 自定义域名（绑定到上传桶的公开访问基址），CLI init 从此处下载 Server 包
R2_PUBLIC_BASE_URL = "https://resource.starrailassistant.top"
SITE_PACKAGES_DIR = None
for p in sys.path[1:]:
    if p.endswith("site-packages"):
        SITE_PACKAGES_DIR = Path(p)
        break
if SITE_PACKAGES_DIR is None:
    print(f"[ERROR] Could not find site-packages directory in sys.path: {sys.path}")
    sys.exit(1)

class ZipBuilder:
    """增量构建 zip：收集文件条目，不同阶段快照写入不同 zip。"""

    def __init__(self):
        self._entries: dict[str, Path] = {}  # arcname -> source path

    @staticmethod
    def _md5(path: Path) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def add(self, path: Path, base_path: Path | None = None):
        if base_path is None:
            base_path = path.parent
        if not path.exists():
            print(f"  [WARN] Skipping non-existent path: {path}")
            return
        if path.is_file():
            self._entries[self._arcname(path.relative_to(base_path))] = path
            return
        for file in sorted(path.rglob("*")):
            if file.is_file():
                self._entries[self._arcname(file.relative_to(base_path))] = file

    @staticmethod
    def _arcname(relative_path: Path) -> str:
        """归一化为 zip 标准的正斜杠分隔路径，与压缩包内条目名及 MD5 清单键保持一致。"""
        return str(relative_path).replace("\\", "/")

    def add_file(self, file: Path, arcname: str):
        self._entries[arcname] = file

    _EXCLUDESuffixes = (".pdb",)
    _EXCLUDENames = {"web.config"}
    # OpenCV 视频 IO 后端，本项目只用于截图与模板匹配，不使用 VideoCapture/VideoWriter
    _EXCLUDEPrefixes = ("opencv_videoio_ffmpeg",)

    # MD5 校验清单在压缩包内的固定路径，便于统一读取
    MD5_MANIFEST_NAME = "manifest.md5.json"

    def snapshot(self, zip_path: Path):
        """将当前所有条目写入 zip 文件，并在压缩包内写入固定命名的 MD5 校验清单。"""
        md5_dict: dict[str, str] = {}
        entries: list[tuple[str, Path]] = []
        for arcname, src in self._entries.items():
            name = Path(arcname).name
            if (name.lower().endswith(self._EXCLUDESuffixes)
                    or name.lower() in self._EXCLUDENames
                    or name.lower().startswith(self._EXCLUDEPrefixes)):
                continue
            entries.append((arcname, src))
            md5_dict[arcname] = self._md5(src)
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zipf:
            for arcname, src in entries:
                zipf.write(src, arcname)
            zipf.writestr(self.MD5_MANIFEST_NAME, json.dumps(md5_dict, indent=2, ensure_ascii=False))
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
        "--windows-console-mode=force",
        "--windows-icon-from-ico=resources/SRAicon.ico",
        "--company-name=StarRailAssistant Team",
        "--product-name=StarRailAssistant",
        f"--file-version={file_version}",
        f"--product-version={file_version}",
        "--file-description=StarRailAssistant Component",
        "--copyright=Copyright 2024 Shasnow",
        "--assume-yes-for-downloads",
        "--output-filename=SRA-cli",
        "--remove-output",
        "--include-package=selenium.webdriver.edge",
        "--include-package=selenium.webdriver.firefox",
        "--include-package=selenium.webdriver.chrome",
        "--include-package=selenium.webdriver.common.action_chains",
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
    # shutil.copy2(ROOT_PATH / "main.py", dist / "main.py")
    # shutil.copytree(ROOT_PATH / "SRACore", dist / "SRACore")
    (DIST_DIR / "SRACore" / "localization").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT_PATH / "SRACore" / "localization" / "resource_en-us.json", DIST_DIR / "SRACore" / "localization" / "resource_en-us.json")
    shutil.copy2(ROOT_PATH / "SRACore" / "localization" / "resource_zh-cn.json", DIST_DIR / "SRACore" / "localization" / "resource_zh-cn.json")
    shutil.copytree(ROOT_PATH / "resources", dist / "resources")
    rapidocr_pkg = SITE_PACKAGES_DIR / "rapidocr"  # pyright: ignore[reportOptionalOperand]
    if rapidocr_pkg.exists():
        (dist / "rapidocr").mkdir(parents=True, exist_ok=True)
        models_dir = rapidocr_pkg / "models"
        if models_dir.exists():
            shutil.copytree(models_dir, dist / "rapidocr" / "models")
        config_path = rapidocr_pkg / "config.yaml"
        if config_path.exists():
            shutil.copy2(config_path, dist / "rapidocr" / "config.yaml")
            shutil.copy2(rapidocr_pkg / "default_models.yaml", dist / "rapidocr" / "default_models.yaml")
    else:
        print(f"  [WARN] rapidocr not found in {SITE_PACKAGES_DIR}, skipping OCR model copy")
    shutil.copytree(ROOT_PATH / "tasks", dist / "tasks")
    extensions_dir = ROOT_PATH / "extensions"
    if extensions_dir.exists():
        shutil.copytree(extensions_dir, dist / "extensions")
    else:
        print(f"  [WARN] extensions directory not found, skipping")
    print("[OK] Resources copied")


def package_lite(version: str):
    print("Packaging Lite ...")
    lite_zip_path = ROOT_PATH / f"StarRailAssistant_Lite_v{version}.zip"
    builder = ZipBuilder()
    for file in DESKTOP_WIN_X64_PUBLISH_PATH.iterdir():
        builder.add(file)
    for file in SERVER_WIN_X64_PUBLISH_PATH.iterdir():
        builder.add(file)
    for item in ["SRACore", "tasks", "extensions", "resources"]:
        builder.add(ROOT_PATH / item)
    for file in ["main.py", "README.md", "LICENSE", "requirements.txt"]:
        builder.add(ROOT_PATH / file)
    builder.snapshot(lite_zip_path)


def publish_dotnet_projects():
    print("Publishing .NET projects ...")
    commands = [
        [DOTNET_EXE, "publish", "-c", "Release", "-r", "win-x64", "SRAFrontend\\SRAFrontend.Desktop\\SRAFrontend.Desktop.csproj"],
        [DOTNET_EXE, "publish", "-c", "Release", "-r", "win-x64", "SRAFrontend\\SRAFrontend.Server\\SRAFrontend.Server.csproj"],
    ]
    for cmd in commands:
        result = subprocess.run(cmd, cwd=ROOT_PATH)
        if result.returncode != 0:
            print(f"[ERROR] dotnet publish failed (exit code: {result.returncode})")
            sys.exit(1)
    print("[OK] .NET projects published successfully")


def package_resources(version: str):
    print("Packaging Resources ...")
    resources_zip = ZipBuilder()
    resources_zip.add(ROOT_PATH / "tasks")
    resources_zip.add(ROOT_PATH / "extensions")
    resources_zip.add(ROOT_PATH / "resources")
    resources_zip.add_file(ROOT_PATH / "package.json", "package.json")
    resources_zip.snapshot(ROOT_PATH / f"StarRailAssistant_Resources_v{version}.zip")


def server_package_object_key(version: str) -> str:
    """R2 对象键：区分正式版/beta 的固定文件名，避免发布 beta 时覆盖正式版压缩包。"""
    return "SRAFrontend_Server_beta.zip" if "-" in version else "SRAFrontend_Server.zip"


def package_server(version: str) -> Path:
    """打包 SRAFrontend.Server 的发布产物，供 CLI init 命令下载。"""
    print("Packaging Server ...")
    if not SERVER_WIN_X64_PUBLISH_PATH.exists():
        print(f"[ERROR] Server publish path not found: {SERVER_WIN_X64_PUBLISH_PATH}")
        print("        Run `dotnet publish -c Release -r win-x64 .\\SRAFrontend\\SRAFrontend.sln` first.")
        sys.exit(1)
    zip_path = ROOT_PATH / f"SRAFrontend_Server_v{version}.zip"
    builder = ZipBuilder()
    builder.add(SERVER_WIN_X64_PUBLISH_PATH, SERVER_WIN_X64_PUBLISH_PATH)
    builder.snapshot(zip_path)
    return zip_path


def upload_to_r2(zip_path: Path, version: str):
    """通过 Cloudflare R2 REST API（Bearer Token + PUT 对象）上传 Server 包。

    文档：https://developers.cloudflare.com/api/resources/r2/
    凭据从环境变量读取：R2_ACCOUNT_ID、R2_API_TOKEN、R2_BUCKET。
    凭据缺失时跳过上传（仅警告），不影响本地打包。
    """
    env_vars = ["R2_ACCOUNT_ID", "R2_API_TOKEN", "R2_BUCKET"]
    values = {name: os.environ.get(name, "") for name in env_vars}
    missing = [name for name, value in values.items() if not value]
    if missing:
        print(f"[WARN] Missing environment variables: {', '.join(missing)}, skipping R2 upload")
        return

    account_id = values["R2_ACCOUNT_ID"]
    api_token = values["R2_API_TOKEN"]
    bucket = values["R2_BUCKET"]
    object_key = server_package_object_key(version)

    print(f"Uploading {zip_path.name} to r2://{bucket}/{object_key} ...")
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/r2/buckets/{bucket}/objects/{urllib.parse.quote(object_key, safe='/.-')}"
    )
    req = urllib.request.Request(url, data=zip_path.read_bytes(), method="PUT", headers={
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/zip",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        print(f"[ERROR] R2 upload failed: HTTP {e.code} {e.read().decode('utf-8', errors='replace')}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[ERROR] R2 upload failed: {e.reason}")
        sys.exit(1)
    print(f"[OK] Uploaded to {R2_PUBLIC_BASE_URL}/{object_key}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StarRailAssistant 打包脚本")
    parser.add_argument("--resources-only", action="store_true", help="只打包资源，跳过 Nuitka 构建等其他操作")
    parser.add_argument("--server-only", action="store_true", help="只打包并上传 Server 包，跳过 Nuitka 构建等其他操作")
    args = parser.parse_args()

    with (ROOT_PATH / "package.json").open(encoding="utf-8") as f:
        data = json.load(f)
    version = data["version"]

    if args.resources_only:
        package_resources(version)
        print(f"\nPackaging completed! Version: v{version}")
        sys.exit(0)

    if args.server_only:
        server_zip = package_server(version)
        upload_to_r2(server_zip, version)
        print(f"\nPackaging completed! Version: v{version}")
        sys.exit(0)

    with (ROOT_PATH / "ChangeLog2.0.md").open(encoding="utf-8") as f:
        changelog = f.read().replace("${VERSION}", version)

    nuitka_build(version)
    copy_core_resources(DIST_DIR)

    # Lite
    package_lite(version)

    # Core → Basic 增量构建
    builder = ZipBuilder()

    print("Packaging Core ...")
    collect_core_files(builder)
    builder.snapshot(ROOT_PATH / f"StarRailAssistant_Core_v{version}.zip")

    print("Packaging Basic ...")
    builder.add(DESKTOP_WIN_X64_PUBLISH_PATH, DESKTOP_WIN_X64_PUBLISH_PATH)
    builder.add(SERVER_WIN_X64_PUBLISH_PATH, SERVER_WIN_X64_PUBLISH_PATH)
    builder.snapshot(ROOT_PATH / f"StarRailAssistant_v{version}.zip")

    package_resources(version)

    # Server 包 → R2（供 CLI init 下载）
    server_zip = package_server(version)
    upload_to_r2(server_zip, version)

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    (ROOT_PATH / "version_info.txt").write_text(f"v{version}\n\n{changelog}", encoding="utf-8")
    print(f"\nPackaging completed! Version: v{version}")
