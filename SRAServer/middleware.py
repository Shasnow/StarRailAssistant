"""访问令牌鉴权中间件（纯 ASGI）。

行为对齐 C# ``TokenAuthenticationHandler``：读取 ``X-Access-Token`` 头或 ``access_token``
查询参数并与配置逐字节比对；未配置令牌时全部放行；``POST /api/auth`` 与
``GET /api/app/background`` 匿名可达；``/api`` 及其子路径以外的请求（静态资源/openapi/mcp）不鉴权。
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs

_ANONYMOUS_PATHS = {"/api/auth", "/api/app/background"}


class TokenAuthMiddleware:
    """校验访问令牌的 ASGI 中间件。"""

    def __init__(self, app: Any, access_token: str = "", visitor_mode: bool = False) -> None:
        self.app = app
        self.access_token = access_token or ""
        self.visitor_mode = visitor_mode

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http" or not self.access_token.strip():
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        api_path = path.lower()
        # 只覆盖 /api 本身及其子路径：/apifoo 不是 API，不要求令牌
        if not (api_path == "/api" or api_path.startswith("/api/")):
            await self.app(scope, receive, send)
            return

        if path.lower() in _ANONYMOUS_PATHS:
            await self.app(scope, receive, send)
            return

        if self._extract_token(scope) == self.access_token:
            await self.app(scope, receive, send)
            return

        await self._reject(send)

    @staticmethod
    def _extract_token(scope: Any) -> str:
        for name, value in scope.get("headers", []):
            if name == b"x-access-token":
                return value.decode("latin-1")
        query = parse_qs((scope.get("query_string") or b"").decode("latin-1"))
        return (query.get("access_token") or [""])[0]

    @staticmethod
    async def _reject(send: Any) -> None:
        payload = json.dumps({"success": False, "message": "unauthorized", "data": None}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode("ascii")),
            ],
        })
        await send({"type": "http.response.body", "body": payload})