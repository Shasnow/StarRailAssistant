"""Auth 控制器：校验访问令牌（匿名可达）。"""

from __future__ import annotations

from litestar import Request, post
from litestar.params import JSONBody
from litestar.response import Response

from SRAServer.controllers._responses import core_of, json_response
from SRAServer.schemas.envelope import R
from SRAServer.schemas.requests import TokenRequest


@post("/api/auth", status_code=200, summary="校验访问令牌")
async def auth(request: Request, data: JSONBody[TokenRequest]) -> Response:
    token = (data.token or "").strip()
    configured = core_of(request).config.access_token
    if not configured.strip():
        return json_response(R(True, "No access token configured"))
    if token != configured:
        return json_response(R(False, "unauthorized"), 401)
    return json_response(R(True, "authorized"))


HANDLERS = [auth]