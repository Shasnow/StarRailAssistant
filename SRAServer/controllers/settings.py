"""Settings 控制器：获取与按字段部分修改应用设置。"""

from __future__ import annotations

import asyncio
from typing import Any

from litestar import Request, get, put
from litestar.params import JSONBody
from litestar.response import Response

from SRAServer.controllers._responses import core_of, json_response
from SRAServer.schemas.envelope import R


@get("/api/settings", summary="获取设置")
async def get_settings(request: Request) -> Response:
    return json_response(R(True, "Settings retrieved", core_of(request).settings.get_dict()))


@put("/api/settings", summary="修改设置")
async def update_settings(request: Request, data: JSONBody[dict[str, Any]]) -> Response:
    core = core_of(request)
    if core.config.visitor_mode:
        return json_response(R(True, "Settings updated", data))
    updated = await asyncio.to_thread(core.settings.patch, data)
    if not updated:
        return json_response(R(False, "No valid settings were updated"), 400)
    return json_response(R(True, "Settings updated", updated))


HANDLERS = [get_settings, update_settings]