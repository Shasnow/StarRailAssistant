"""SRAServer 命令行入口：``python -m SRAServer`` / ``sra-server`` / ``sra serve``。

启动逻辑集中在 :func:`run_server`；:func:`main` 在其之上负责参数解析与 Windows 下的管理员
自提权，三个入口都会经过 ``main``。

默认监听 127.0.0.1:5073，``--host`` 暴露公网（绑定 0.0.0.0），``--no-webui`` 关闭静态托管。
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from typing import TYPE_CHECKING

from SRACore.util.const import VERSION

if TYPE_CHECKING:
    import uvicorn

    from SRACore.services import AppContext

# 服务端运行所需依赖，随 `[server]` extra 安装
_SERVER_REQUIREMENTS = ("litestar", "uvicorn", "mcp", "cryptography", "anyio")


def build_parser() -> argparse.ArgumentParser:
    """构造命令行解析器。"""
    parser = argparse.ArgumentParser(
        prog="sra-server",
        description="StarRailAssistant 服务端（基于 Litestar，进程内托管 SRACore）",
    )
    parser.add_argument("--host", action="store_true", help="暴露到公网（绑定 0.0.0.0）")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="监听端口（缺省时取 SRA_PORT / server.toml，否则 5073）",
    )
    parser.add_argument("--no-webui", action="store_true", help="不托管 WebUI 静态资源")
    parser.add_argument("--no-admin", action="store_true", help="不请求管理员权限")
    parser.add_argument("-v", "--version", action="version", version=VERSION)
    return parser


def missing_server_dependencies() -> list[str]:
    """返回缺失的服务端依赖模块名（未安装 `[server]` extra 时非空）。"""
    return [name for name in _SERVER_REQUIREMENTS if importlib.util.find_spec(name) is None]


def create_server(
    *,
    host: bool = False,
    port: int | None = None,
    webui: bool | None = None,
    context: AppContext | None = None,
) -> uvicorn.Server:
    """构造 uvicorn 服务实例（不启动），供后台线程或 :func:`run_server` 使用。

    Args:
        host: 是否暴露到公网（绑定 0.0.0.0）；``False`` 表示沿用 ServerConfig。
        port: 监听端口；``None`` 表示沿用 ServerConfig（环境变量/server.toml/默认 5073）。
        webui: 是否托管 WebUI 静态资源；``None`` 表示沿用 ServerConfig（环境变量/server.toml）。
        context: 复用的 ``AppContext``（CLI 内嵌服务端时传入，暴露当前会话的任务/扩展状态）。
    """
    missing = missing_server_dependencies()
    if missing:
        print(
            "缺少服务端依赖：" + ", ".join(missing) + "\n"
            "请安装服务端依赖后再启动：\n"
            "  uv tool install starrailassistant --extra server\n"
            "  pip install \"starrailassistant[server]\"\n"
            "  pipx install \"starrailassistant[server]\"",
            file=sys.stderr,
        )
        raise SystemExit(1)

    import uvicorn

    from SRAServer.app import create_app
    from SRAServer.config import ServerConfig
    from SRAServer.context import ServerContext

    config = ServerConfig.load(
        host="0.0.0.0" if host else None,
        port=port,
        webui=False if webui is False else None,
    )
    app = create_app(config, core=ServerContext(config, context))
    server = uvicorn.Server(uvicorn.Config(app, host=config.host, port=config.port))
    # 供 /api/backend/stop 触发优雅退出：进程内托管时没有子进程可终止
    app.state.uvicorn_server = server
    return server


def run_server(
    *,
    host: bool = False,
    port: int | None = None,
    webui: bool | None = None,
    context: AppContext | None = None,
) -> None:
    """启动服务端并阻塞到服务停止（``sra serve`` / ``sra-server`` / ``python -m SRAServer`` 共用）。

    服务端代码随已安装的 ``SRAServer`` 包加载；WebUI 静态资源由 ``sra init`` 下载的 WebUI 包
    解压到当前目录 ``SRAServer/static``，由 :func:`SRAServer.app._resolve_static_dir` 优先采用。
    参数含义见 :func:`create_server`。
    """
    create_server(host=host, port=port, webui=webui, context=context).run()


def main(argv: list[str] | None = None) -> None:
    """``python -m SRAServer`` / ``sra-server`` 入口：解析参数并按需自提权后启动。"""
    args = build_parser().parse_args(argv)

    if not args.no_admin:
        from SRACore.__main__ import is_admin, restart_as_admin

        if not is_admin():
            restart_as_admin()

    run_server(host=args.host, port=args.port, webui=False if args.no_webui else None)


if __name__ == "__main__":
    main()