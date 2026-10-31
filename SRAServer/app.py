"""Litestar 应用装配：路由、鉴权、OpenAPI、静态 SPA 回退与 ``/mcp`` 挂载。"""

from __future__ import annotations

import asyncio
import mimetypes
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Any, Callable

from litestar import Litestar, Request, get
from litestar.openapi import OpenAPIConfig
from litestar.handlers import asgi
from litestar.middleware import DefineMiddleware as Middleware
from litestar.response import Response

from SRACore.util.const import VERSION

from SRAServer import controllers
from SRAServer.config import ServerConfig
from SRAServer.context import ServerContext
from SRAServer.mcp.server import build_mcp_asgi
from SRAServer.middleware import TokenAuthMiddleware
from SRAServer.openapi import get_openapi_v1

_STATIC_DIR = Path(__file__).resolve().parent / "static"


def _operation_id_creator(route_handler: Any, http_method: Any, path_components: Any) -> str:
    """生成含请求方法与路径的 OpenAPI operationId，保证同名处理器不会冲突。"""
    method = getattr(http_method, "value", http_method)
    parts = [str(method), route_handler.handler_name or ""]
    for component in path_components or ():
        parts.append("".join(ch if ch.isalnum() else "_" for ch in str(component)))
    return "_".join(part for part in parts if part)


def _mcp_asgi_handler(mcp_app: Any) -> Callable[..., Any]:
    """包装 MCP 的 Starlette 应用：还原被 Litestar 挂载剥除的 ``/mcp`` 前缀。"""

    async def handler(scope: Any, receive: Any, send: Any) -> None:
        sub = scope.get("path") or "/"
        scope["path"] = "/mcp" if sub == "/" else "/mcp" + sub
        scope["raw_path"] = scope["path"].encode()
        await mcp_app(scope, receive, send)

    return handler


def _build_spa_handler(static_dir: Path) -> list[Callable[..., Any]]:
    """构造静态资源 + SPA 回退处理器：命中文件则返回文件，否则返回 index.html。"""
    base = static_dir.resolve()

    def _serve(path: str) -> Response:
        relative = path.lstrip("/")
        # 未注册的 /api/* 直接 404：否则 SPA 回退会把它变成 index.html + 200，写错接口时极难排查
        if relative == "api" or relative.startswith("api/"):
            return Response(content=b"Not Found", media_type="text/plain", status_code=404)
        candidate = (base / relative).resolve()
        if candidate.is_relative_to(base) and candidate.is_file():
            media_type, _ = mimetypes.guess_type(candidate.name)
            return Response(content=candidate.read_bytes(), media_type=media_type or "application/octet-stream")

        index = base / "index.html"
        if index.is_file():
            return Response(content=index.read_bytes(), media_type="text/html")
        return Response(content=b"Not Found", media_type="text/plain", status_code=404)

    @get("/", include_in_schema=False, sync_to_thread=True)
    def spa_root() -> Response:
        return _serve("")

    @get("/{path:path}", include_in_schema=False, sync_to_thread=True)
    def spa_deep(path: str) -> Response:
        return _serve(path)

    return [spa_root, spa_deep]


def create_app(config: ServerConfig | None = None, core: ServerContext | None = None) -> Litestar:
    """构造 Litestar 应用。

    Args:
        config: 服务端配置，缺省时从环境变量/server.toml 加载。
        core: 已初始化的 ServerContext（测试可注入），缺省时按 config 构造。
    """
    config = config or ServerConfig.load()
    if core is None:
        core = ServerContext(config)

    handlers: list[Any] = [*controllers.HANDLERS, get_openapi_v1]

    session_manager = None
    if not config.visitor_mode:
        mcp_app, session_manager = build_mcp_asgi(core, config.host)
        handlers.append(asgi("/mcp", is_mount=True, copy_scope=True)(_mcp_asgi_handler(mcp_app)))

    if config.webui:
        handlers.extend(_build_spa_handler(_STATIC_DIR))

    @asynccontextmanager
    async def lifespan(_app: Litestar):
        core.bind_event_loop(asyncio.get_running_loop())
        async with AsyncExitStack() as stack:
            if session_manager is not None:
                await stack.enter_async_context(session_manager.run())
            # 退出时先清理 MCP 会话，再停工作线程与全局键盘监听（stack 为后进先出）
            stack.callback(core.shutdown)
            yield

    app = Litestar(
        route_handlers=handlers,
        middleware=[Middleware(TokenAuthMiddleware, access_token=config.access_token, visitor_mode=config.visitor_mode)],
        openapi_config=OpenAPIConfig(
            title="SRA Server API", version=VERSION, path="/openapi", operation_id_creator=_operation_id_creator
        ),
        lifespan=[lifespan],
    )
    app.state.core = core
    return app