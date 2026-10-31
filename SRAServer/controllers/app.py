"""App 控制器：系统信息、首页短语与背景图。"""

from __future__ import annotations

from litestar import Request, get
from litestar.response import Response

from SRAServer.controllers._responses import core_of, json_response
from SRAServer.schemas.envelope import R


@get("/api/app/background", summary="获取背景图")
async def get_background(request: Request) -> Response:
    data = await core_of(request).app.background()
    return Response(content=data, media_type="image/jpeg")


@get("/api/app/system-info", summary="获取系统信息")
async def get_system_info(request: Request) -> Response:
    return json_response(R(True, "success", core_of(request).app.system_info()))


@get("/api/app/phrases", summary="获取短语")
async def get_phrases(request: Request) -> Response:
    return json_response(R(True, "success", core_of(request).app.phrases()))


HANDLERS = [get_background, get_system_info, get_phrases]