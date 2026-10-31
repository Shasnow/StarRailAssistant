"""Extensions 控制器：扩展列表、Schema、配置读写、运行/停止/重载。"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from litestar import Request, get, post, put
from litestar.params import FromPath, FromQuery, JSONBody
from litestar.response import Response

from SRAServer.controllers._responses import core_of, json_response
from SRAServer.schemas.envelope import R


@get("/api/extensions", summary="列出所有已注册的扩展")
async def list_extensions(request: Request) -> Response:
    return json_response(R(True, "OK", core_of(request).extension_list()))


@get("/api/extensions/{ext_id:str}/schema", summary="获取扩展配置 Schema")
async def get_schema(request: Request, ext_id: FromPath[str]) -> Response:
    schema = core_of(request).extension_schema(ext_id)
    if schema is None:
        return json_response(R(False, f"Extension '{ext_id}' not found or has no config"))
    return json_response(R(True, "OK", schema))


@get("/api/extensions/{ext_id:str}/config", summary="获取扩展配置值")
async def get_config(request: Request, ext_id: FromPath[str]) -> Response:
    data = core_of(request).extension_config_get(ext_id)
    if data is None:
        return json_response(R(False, f"Extension '{ext_id}' has no config"))
    return json_response(R(True, "OK", json.dumps(data, ensure_ascii=False)))


@put("/api/extensions/{ext_id:str}/config", summary="设置扩展配置值")
async def set_config(request: Request, ext_id: FromPath[str], data: JSONBody[Any] = None) -> Response:
    core = core_of(request)
    if core.config.visitor_mode:
        return json_response(R(True, "Config updated"))
    payload = _as_dict(data)
    if payload is None:
        return json_response(R(False, "Invalid config payload"), 400)
    ok, message = await asyncio.to_thread(core.extension_config_set, ext_id, payload)
    return json_response(R(ok, "Config updated" if ok else message))


@post("/api/extensions/{ext_id:str}/run", status_code=200, summary="运行指定扩展")
async def run_extension(
    request: Request, ext_id: FromPath[str], config: FromQuery[str | None] = None
) -> Response:
    core = core_of(request)
    if core.config.visitor_mode:
        return json_response(R(True, f"Extension '{ext_id}' started"))
    ok, message = await asyncio.to_thread(core.extension_run, ext_id, config)
    return json_response(R(ok, message))


@post("/api/extensions/{ext_id:str}/stop", status_code=200, summary="停止指定扩展")
async def stop_extension(request: Request, ext_id: FromPath[str]) -> Response:
    core = core_of(request)
    if core.config.visitor_mode:
        return json_response(R(True, f"Extension '{ext_id}' stopped"))
    ok, message = await asyncio.to_thread(core.extension_stop, ext_id)
    return json_response(R(ok, message))


@post("/api/extensions/reload", status_code=200, summary="重新扫描并导入扩展模块")
async def reload_extensions(request: Request) -> Response:
    core = core_of(request)
    if core.config.visitor_mode:
        return json_response(R(True, "Extensions reloaded"))
    ok, message = await asyncio.to_thread(core.extension_reload)
    return json_response(R(ok, message))


def _as_dict(data: Any) -> dict[str, Any] | None:
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


HANDLERS = [
    list_extensions,
    get_schema,
    get_config,
    set_config,
    run_extension,
    stop_extension,
    reload_extensions,
]