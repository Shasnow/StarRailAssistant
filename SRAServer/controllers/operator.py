"""Operator 控制器：列出方法、方法帮助与统一调用。"""

from __future__ import annotations

import asyncio

from litestar import Request, get, post
from litestar.params import FromPath, JSONBody
from litestar.response import Response

from SRAServer.controllers._responses import core_of, json_response
from SRAServer.schemas.envelope import R
from SRAServer.schemas.requests import OperatorCallRequest


@get("/api/operator/list", summary="列出所有可用的 Operator 方法")
async def list_methods(request: Request) -> Response:
    return json_response(R(True, "Operator methods", core_of(request).operator_list()))


@get("/api/operator/help/{method:str}", summary="获取 Operator 方法的详细帮助")
async def get_method_help(request: Request, method: FromPath[str]) -> Response:
    data = core_of(request).operator_help(method)
    if data is None:
        return json_response(R(False, f"方法 '{method}' 不存在"))
    return json_response(R(True, method, data))


@post("/api/operator/call", status_code=200, summary="调用 Operator 方法")
async def call_method(request: Request, data: JSONBody[OperatorCallRequest]) -> Response:
    core = core_of(request)
    if not data.method or not data.method.strip():
        return json_response(R(False, "method is required"), 400)
    if core.config.visitor_mode:
        return json_response(R(True, "Method called"))
    ok, message, result = await asyncio.to_thread(core.operator_call, data.method, data.params)
    return json_response(R(ok, message, result))


HANDLERS = [list_methods, get_method_help, call_method]