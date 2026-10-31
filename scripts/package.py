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
打包：内嵌 Python 运行时 + 源码分发
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT_PATH = Path(__file__).resolve().parent.parent
DOTNET_EXE = os.environ.get("DOTNET_EXE", "dotnet")
DESKTOP_WIN_X64_PUBLISH_PATH = ROOT_PATH / "SRAFrontend" / "SRAFrontend.Desktop" / "bin" / "Release" / "net10.0" / "win-x64" / "publish"

DIST_DIR = ROOT_PATH / "main.dist"
DIST_PYTHON_DIR = DIST_DIR / "python"
# 依赖清单指纹：依赖未变化时复用内嵌环境（CI 缓存 main.dist/python 后可跳过下载与安装）
DEPS_STAMP_NAME = ".requirements.sha256"
PYTHON31210_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
# R2 自定义域名（绑定到上传桶的公开访问基址），CLI init 从此处下载 WebUI 包与资源包
R2_PUBLIC_BASE_URL = "https://resource.starrailassistant.top"

# 随包分发的 Python 源码目录与根文件
SOURCE_DIRS = ["SRACore", "SRAServer", "tasks", "extensions", "resources", "assets"]
SOURCE_FILES = ["main.py", "pyproject.toml", "README.md", "LICENSE"]

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

    def remove_prefix(self, prefix: str):
        """移除指定前缀的条目（用于剔除 WebUI 等独立产物）。"""
        prefix = self._arcname(Path(prefix)).rstrip("/")
        for arcname in [n for n in self._entries if n == prefix or n.startswith(prefix + "/")]:
            del self._entries[arcname]

    _EXCLUDESuffixes = (".pdb", ".pyc")
    # 构建元数据（依赖指纹）只在本地/CI 复用内嵌环境时使用，不进发布包
    _EXCLUDENames = {"web.config", DEPS_STAMP_NAME}
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


def download(url: str, dest: Path, timeout: int = 60, retries: int = 2):
    """下载文件到指定路径：带超时与重试，最终失败时终止打包。"""
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        suffix = f" (attempt {attempt + 1}/{retries + 1})" if attempt else ""
        print(f"Downloading {url} ...{suffix}")
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp, open(dest, "wb") as f:
                shutil.copyfileobj(resp, f)
            return
        except (urllib.error.URLError, OSError) as e:
            last_error = e
            print(f"  [WARN] Download failed: {e}")
    print(f"[ERROR] Failed to download {url}: {last_error}")
    sys.exit(1)


def runtime_requirements() -> list[str]:
    """从 pyproject.toml 读取内嵌环境所需的依赖（基础 + standard + server）。"""
    with (ROOT_PATH / "pyproject.toml").open("rb") as f:
        project = tomllib.load(f)["project"]
    requirements = list(project.get("dependencies", []))
    extras = project.get("optional-dependencies", {})
    for extra in ("standard", "server"):
        requirements.extend(extras.get(extra, []))
    return requirements


def run(cmd: list[str]):
    """执行命令，非零退出即终止打包。"""
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"[ERROR] Command failed (exit code: {result.returncode}): {' '.join(cmd)}")
        sys.exit(1)


def configure_pth():
    """启用 site 并加入 Lib/site-packages，使 embeddable 运行时能加载 pip 安装的依赖。"""
    pth_files = list(DIST_PYTHON_DIR.glob("python3*._pth"))
    if not pth_files:
        print(f"[ERROR] python3*._pth not found in {DIST_PYTHON_DIR}")
        sys.exit(1)
    stdlib_zip = next((p.name for p in DIST_PYTHON_DIR.glob("python3*.zip")), "python312.zip")
    site_packages = DIST_PYTHON_DIR / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    pth_files[0].write_text(
        f"{stdlib_zip}\n.\nLib\\site-packages\nimport site\n",
        encoding="utf-8",
    )


def prepare_embedded_python():
    """准备内嵌 Python 3.12 运行时并安装 standard + server 依赖（依赖未变化时复用已有环境）。"""
    requirements = runtime_requirements()
    digest = hashlib.sha256("\n".join(requirements).encode("utf-8")).hexdigest()
    stamp = DIST_PYTHON_DIR / DEPS_STAMP_NAME
    python_exe = DIST_PYTHON_DIR / "python.exe"
    if python_exe.exists() and stamp.exists() and stamp.read_text(encoding="utf-8").strip() == digest:
        print("[SKIP] Embedded Python is up to date")
        return

    print("Preparing embedded Python ...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_PYTHON_DIR.mkdir(parents=True)

    with tempfile.TemporaryDirectory() as tmp:
        embed_zip = Path(tmp) / "python-embed-amd64.zip"
        download(PYTHON31210_URL, embed_zip)
        print("Extracting embedded Python ...")
        with ZipFile(embed_zip) as zf:
            zf.extractall(DIST_PYTHON_DIR)

        configure_pth()

        get_pip = Path(tmp) / "get-pip.py"
        download(GET_PIP_URL, get_pip)
        print("Installing pip into embedded Python ...")
        run([str(python_exe), str(get_pip), "--no-warn-script-location"])

        # embeddable 运行时存在 python3*._pth 时会忽略 PYTHONPATH，pip 的构建隔离
        # 无法把临时构建环境注入 sys.path（pyscreeze 等 sdist 会报
        # Cannot import 'setuptools.build_meta'），故预装构建工具并禁用构建隔离。
        run([str(python_exe), "-m", "pip", "install", "--no-warn-script-location", "setuptools", "wheel"])

        print(f"Installing {len(requirements)} runtime requirements ...")
        # 保留 pip 的 wheel 缓存：CI 缓存 %LOCALAPPDATA%\pip\Cache 后可直接复用已下载的 wheel
        run([
            str(python_exe), "-m", "pip", "install",
            "--no-warn-script-location", "--no-build-isolation",
            *requirements,
        ])

    stamp.write_text(digest, encoding="utf-8")
    print("[OK] Embedded Python prepared")


def copy_python_sources():
    """把 Python 源码、任务、扩展与资源复制到发布目录。"""
    print("Copying Python sources ...")
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name in SOURCE_DIRS:
        src = ROOT_PATH / name
        if not src.exists():
            print(f"  [WARN] Skipping non-existent directory: {src}")
            continue
        # 复用内嵌环境时 DIST_DIR 可能残留上次的源码，先删除目标目录避免旧文件混入
        target = DIST_DIR / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src, target, ignore=ignore)
    static_dir = DIST_DIR / "SRAServer" / "static"
    if static_dir.exists():
        # WebUI 是独立产物（sra init 下载），不随服务端包分发
        shutil.rmtree(static_dir)
    for name in SOURCE_FILES:
        shutil.copy2(ROOT_PATH / name, DIST_DIR / name)
    print("[OK] Python sources copied")


def package_lite(version: str):
    print("Packaging Lite ...")
    lite_zip_path = ROOT_PATH / f"StarRailAssistant_Lite_v{version}.zip"
    builder = ZipBuilder()
    for file in DESKTOP_WIN_X64_PUBLISH_PATH.iterdir():
        builder.add(file)
    for item in ["SRACore", "SRAServer", "tasks", "extensions", "resources", "assets"]:
        builder.add(ROOT_PATH / item)
    # WebUI 是独立产物（sra init 下载），不随服务端包分发
    builder.remove_prefix("SRAServer/static")
    # pyproject.toml 随包分发：用户在解压目录执行 pip install ".[standard]" 安装依赖
    for file in ["main.py", "README.md", "LICENSE", "pyproject.toml"]:
        builder.add(ROOT_PATH / file)
    builder.snapshot(lite_zip_path)


def package_core_and_full(version: str):
    """Core = 内嵌 Python + 源码；Full = Core + .NET 桌面端产物。"""
    builder = ZipBuilder()

    print("Packaging Core ...")
    for item in DIST_DIR.iterdir():
        builder.add(item)
    builder.snapshot(ROOT_PATH / f"StarRailAssistant_Core_v{version}.zip")

    print("Packaging Full ...")
    builder.add(DESKTOP_WIN_X64_PUBLISH_PATH, DESKTOP_WIN_X64_PUBLISH_PATH)
    builder.snapshot(ROOT_PATH / f"StarRailAssistant_v{version}.zip")


def publish_dotnet_projects():
    print("Publishing .NET projects ...")
    commands = [
        [DOTNET_EXE, "publish", "-c", "Release", "-r", "win-x64", "SRAFrontend\\SRAFrontend.Desktop\\SRAFrontend.Desktop.csproj"],
    ]
    for cmd in commands:
        result = subprocess.run(cmd, cwd=ROOT_PATH)
        if result.returncode != 0:
            print(f"[ERROR] dotnet publish failed (exit code: {result.returncode})")
            sys.exit(1)
    print("[OK] .NET projects published successfully")


def package_resources(version: str) -> Path:
    print("Packaging Resources ...")
    resources_zip = ZipBuilder()
    resources_zip.add(ROOT_PATH / "tasks")
    resources_zip.add(ROOT_PATH / "extensions")
    resources_zip.add(ROOT_PATH / "resources")
    resources_zip.add_file(ROOT_PATH / "package.json", "package.json")
    zip_path = ROOT_PATH / f"StarRailAssistant_Resources_v{version}.zip"
    resources_zip.snapshot(zip_path)
    return zip_path


def webui_package_object_key(version: str) -> str:
    """R2 对象键：区分正式版/beta 的固定文件名，避免发布 beta 时覆盖正式版压缩包。"""
    return "SRAFrontend_WebUI_beta.zip" if "-" in version else "SRAFrontend_WebUI.zip"


def resources_package_object_key(version: str) -> str:
    """R2 对象键：资源包同样区分正式版/beta，规则与 WebUI 包一致。"""
    return "StarRailAssistant_Resources_beta.zip" if "-" in version else "StarRailAssistant_Resources.zip"


def package_webui(version: str) -> Path:
    """打包构建好的 WebUI 静态资源（SRAServer/static），供 CLI init 下载。

    压缩包内条目为 ``SRAServer/static/**``，``sra init`` 解压到当前目录后，服务端即可从
    ``<cwd>/SRAServer/static`` 托管 WebUI；服务端代码本身随 wheel 安装，用户无需再额外
    安装 .NET / ASP.NET Core Runtime。
    """
    print("Packaging WebUI ...")
    static_dir = ROOT_PATH / "SRAServer" / "static"
    if not static_dir.exists() or not any(static_dir.iterdir()):
        print(f"[ERROR] WebUI static dir not found or empty: {static_dir}")
        print("        Run `pnpm run build` in SRAFrontend/srafrontend-webui first.")
        sys.exit(1)
    zip_path = ROOT_PATH / f"SRAFrontend_WebUI_v{version}.zip"
    builder = ZipBuilder()
    builder.add(static_dir, ROOT_PATH)
    builder.snapshot(zip_path)
    return zip_path


def upload_to_r2(zip_path: Path, object_key: str):
    """通过 Cloudflare R2 REST API（Bearer Token + PUT 对象）上传压缩包到指定对象键。

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
    parser.add_argument("--resources-only", action="store_true", help="只打包资源，跳过 Python 运行时与源码打包等其他操作")
    parser.add_argument("--webui-only", action="store_true", help="只打包并上传 WebUI 包，跳过 Python 运行时与源码打包等其他操作")
    args = parser.parse_args()

    with (ROOT_PATH / "package.json").open(encoding="utf-8") as f:
        data = json.load(f)
    version = data["version"]

    if args.resources_only:
        resources_zip = package_resources(version)
        upload_to_r2(resources_zip, resources_package_object_key(version))
        print(f"\nPackaging completed! Version: v{version}")
        sys.exit(0)

    if args.webui_only:
        webui_zip = package_webui(version)
        upload_to_r2(webui_zip, webui_package_object_key(version))
        print(f"\nPackaging completed! Version: v{version}")
        sys.exit(0)

    with (ROOT_PATH / "ChangeLog2.0.md").open(encoding="utf-8") as f:
        changelog = f.read().replace("${VERSION}", version)

    prepare_embedded_python()
    copy_python_sources()

    # Lite
    package_lite(version)

    # Core / Full
    package_core_and_full(version)

    # 资源包 → R2（供 CLI init 下载）
    resources_zip = package_resources(version)
    upload_to_r2(resources_zip, resources_package_object_key(version))

    # WebUI 包 → R2（供 CLI init 下载）
    webui_zip = package_webui(version)
    upload_to_r2(webui_zip, webui_package_object_key(version))

    # 保留 main.dist/python 供下次复用（CI 缓存该目录以跳过下载与安装），
    # 打包产物已在压缩包内，源码目录下次会被重新复制覆盖
    (ROOT_PATH / "version_info.txt").write_text(f"v{version}\n\n{changelog}", encoding="utf-8")
    print(f"\nPackaging completed! Version: v{version}")
