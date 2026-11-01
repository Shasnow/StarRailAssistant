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
# SRA-cli.exe 启动器：取代旧版 Nuitka 构建的命令行可执行文件，转发到内嵌运行时
LAUNCHER_DIR = ROOT_PATH / "scripts" / "launcher"
LAUNCHER_NAME = "SRA-cli.exe"
LAUNCHER_SOURCE = LAUNCHER_DIR / "SRA-cli.c"
LAUNCHER_MANIFEST = LAUNCHER_DIR / "SRA-cli.manifest"
LAUNCHER_ICON = ROOT_PATH / "assets" / "SRAicon.ico"
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


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None):
    """执行命令，非零退出即终止打包。"""
    result = subprocess.run(cmd, cwd=cwd, env=env)
    if result.returncode != 0:
        print(f"[ERROR] Command failed (exit code: {result.returncode}): {' '.join(cmd)}")
        sys.exit(1)


def msvc_environment() -> dict[str, str] | None:
    """返回可用的 MSVC 工具链环境变量；cl.exe 不可用时返回 None。

    优先复用当前环境（PATH 中已有 cl.exe），否则通过 vswhere 定位 Visual Studio
    并执行 vcvars64.bat 导出环境，避免要求调用方预先打开开发者命令提示符。
    """
    env = os.environ.copy()
    if shutil.which("cl"):
        return env

    vswhere = (
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    )
    if not vswhere.is_file():
        return None

    installation = ""
    for query in (
        ["-latest", "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64"],
        ["-latest", "-products", "*"],
    ):
        query_result = subprocess.run(
            [str(vswhere), *query, "-property", "installationPath"],
            capture_output=True, text=True, errors="replace",
        )
        if query_result.returncode == 0 and query_result.stdout.strip():
            installation = query_result.stdout.strip().splitlines()[0].strip()
            break
    if not installation:
        return None

    vcvars = Path(installation) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    if not vcvars.is_file():
        return None

    dump = subprocess.run(
        ["cmd", "/c", f'"{vcvars}" && set'],
        capture_output=True, text=True, errors="replace",
    )
    if dump.returncode != 0:
        return None
    for line in dump.stdout.splitlines():
        name, separator, value = line.partition("=")
        if separator and name:
            env[name] = value
    return env


def gcc_toolchain() -> tuple[str, str] | None:
    """返回 (gcc, windres) 可执行名；无可用 mingw-w64 工具链时返回 None。

    MSVC 缺失时的降级路径（例如仅有 mingw 的开发机），CI 仍以 MSVC 为准。
    """
    windres = shutil.which("windres") or shutil.which("x86_64-w64-mingw32-windres")
    if windres is None:
        return None
    for name in ("x86_64-w64-mingw32-gcc", "gcc"):
        if shutil.which(name):
            return name, windres
    return None


def launcher_rc(version: str) -> str:
    """生成 SRA-cli.exe 的资源脚本：图标、管理员清单与版本信息。

    编译在临时目录中进行，图标与清单按文件名引用，规避 rc 对反斜杠路径的转义差异。
    """
    release = version.split("-", 1)[0]
    numbers = [int(part) for part in release.split(".")]
    numbers = (numbers + [0, 0, 0, 0])[:4]
    file_version = ",".join(str(number) for number in numbers)
    return f'''1 ICON "SRAicon.ico"
1 24 "SRA-cli.manifest"

1 VERSIONINFO
  FILEVERSION     {file_version}
  PRODUCTVERSION  {file_version}
  FILEOS          0x00040000L
  FILETYPE        0x00000001L
BEGIN
  BLOCK "StringFileInfo"
  BEGIN
    BLOCK "080404b0"
    BEGIN
      VALUE "CompanyName", "StarRailAssistant Team"
      VALUE "FileDescription", "StarRailAssistant Component"
      VALUE "FileVersion", "{release}"
      VALUE "LegalCopyright", "Copyright 2024 Shasnow"
      VALUE "OriginalFilename", "SRA-cli.exe"
      VALUE "ProductName", "StarRailAssistant"
      VALUE "ProductVersion", "{release}"
    END
  END
  BLOCK "VarFileInfo"
  BEGIN
    VALUE "Translation", 0x804, 1200
  END
END
'''


def build_launcher(version: str) -> Path | None:
    """编译并放置 SRA-cli.exe 启动器；无 C 工具链时警告并跳过（Lite 包不含启动器）。

    优先使用 MSVC（CI 环境），缺失时降级到 mingw-w64，便于开发机本地打包出同样的入口。
    """
    msvc_env = msvc_environment()
    gcc = gcc_toolchain()
    if msvc_env is None and gcc is None:
        print("[WARN] Neither MSVC nor mingw-w64 was found, skipping SRA-cli.exe "
              "(install Visual Studio Build Tools with the C++ workload, or mingw-w64)")
        return None
    if not LAUNCHER_ICON.is_file():
        print(f"[WARN] Launcher icon not found: {LAUNCHER_ICON}, skipping SRA-cli.exe")
        return None

    print("Building SRA-cli.exe launcher ...")
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        shutil.copy2(LAUNCHER_SOURCE, work_dir / LAUNCHER_SOURCE.name)
        shutil.copy2(LAUNCHER_MANIFEST, work_dir / LAUNCHER_MANIFEST.name)
        shutil.copy2(LAUNCHER_ICON, work_dir / "SRAicon.ico")
        (work_dir / "SRA-cli.rc").write_text(launcher_rc(version), encoding="utf-8")

        if msvc_env is not None:
            print("  toolchain: MSVC")
            run(["rc", "/nologo", "/fo", "SRA-cli.res", "SRA-cli.rc"], cwd=work_dir, env=msvc_env)
            # /MT 静态链接 CRT，避免依赖 VC 运行库；/MANIFEST:NO 保留资源内自带的管理员清单
            run([
                "cl", "/nologo", "/O2", "/MT", "/W3", "SRA-cli.c", "SRA-cli.res",
                "/Fe:SRA-cli.exe",
                "/link", "/SUBSYSTEM:CONSOLE", "/INCREMENTAL:NO", "/MANIFEST:NO",
            ], cwd=work_dir, env=msvc_env)
        else:
            gcc_name, windres_name = gcc
            print(f"  toolchain: {gcc_name} (MSVC not available)")
            run([windres_name, "SRA-cli.rc", "-O", "coff", "-o", "SRA-cli_res.o"], cwd=work_dir)
            # -municode 提供 wmain 入口；-static 静态链接，避免依赖 mingw 运行库 DLL
            run([
                gcc_name, "SRA-cli.c", "SRA-cli_res.o",
                "-municode", "-O2", "-static", "-s", "-o", LAUNCHER_NAME,
            ], cwd=work_dir)

        built = work_dir / LAUNCHER_NAME
        if not built.is_file():
            print(f"[ERROR] SRA-cli.exe was not produced in {work_dir}")
            sys.exit(1)
        DIST_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(built, DIST_DIR / LAUNCHER_NAME)
        print(f"[OK] {LAUNCHER_NAME} built ({built.stat().st_size} bytes)")
    return DIST_DIR / LAUNCHER_NAME


def configure_pth():
    """启用 site 并配置 sys.path，使 embeddable 运行时能加载 pip 依赖与程序源码。

    embeddable 运行时一旦存在 python3*._pth，sys.path 就完全由该文件决定，
    不会自动加入脚本目录，因此必须显式加入程序根目录（``..``，相对 python 目录），
    否则 ``python main.py`` 无法导入 SRACore。
    """
    pth_files = list(DIST_PYTHON_DIR.glob("python3*._pth"))
    if not pth_files:
        print(f"[ERROR] python3*._pth not found in {DIST_PYTHON_DIR}")
        sys.exit(1)
    stdlib_zip = next((p.name for p in DIST_PYTHON_DIR.glob("python3*.zip")), "python312.zip")
    site_packages = DIST_PYTHON_DIR / "Lib" / "site-packages"
    # 必须先建目录：site.addsitedir 会跳过不存在的路径，
    # 否则 `import site` 不会把 Lib/site-packages 加入 sys.path
    site_packages.mkdir(parents=True, exist_ok=True)
    # 条目顺序：标准库 → 运行时目录 → 程序根目录（源码）；
    # Lib/site-packages 由 `import site` 自动加入，无需在此列出
    pth_files[0].write_text(
        f"{stdlib_zip}\n.\n..\nimport site\n",
        encoding="utf-8",
    )


def prepare_embedded_python():
    """准备内嵌 Python 3.12 运行时并安装 standard + server 依赖（依赖未变化时复用已有环境）。"""
    requirements = runtime_requirements()
    digest = hashlib.sha256("\n".join(requirements).encode("utf-8")).hexdigest()
    stamp = DIST_PYTHON_DIR / DEPS_STAMP_NAME
    python_exe = DIST_PYTHON_DIR / "python.exe"
    if python_exe.exists() and stamp.exists() and stamp.read_text(encoding="utf-8").strip() == digest:
        # 复用的环境可能是旧版 _pth 生成的，这里幂等重写，保证 sys.path 配置与当前代码一致
        configure_pth()
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

    # SRA-cli.exe 启动器：兼容旧版 Nuitka 构建的命令行入口，随 Core/Full 包分发
    build_launcher(version)

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
