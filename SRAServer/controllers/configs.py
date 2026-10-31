"""Configs 控制器：配置名列表与配置的增删改查。"""

from __future__ import annotations

from typing import Any

from litestar import Request, delete, get, post, put
from litestar.params import FromPath, JSONBody
from litestar.response import Response

from SRAServer.controllers._responses import core_of, json_response
from SRAServer.schemas.envelope import R


@get("/api/configs", summary="获取所有配置名称")
async def list_configs(request: Request) -> Response:
    return json_response(R(True, "success", core_of(request).configs.names()))


@get("/api/configs/{config_name:str}", summary="获取指定配置")
async def get_config(request: Request, config_name: FromPath[str]) -> Response:
    core = core_of(request)
    if not core.configs.exists(config_name):
        return json_response(R(False, "not found"), 404)
    data = core.configs.load_dict(config_name)
    return json_response(R(True, "success", core.configs.safe_payload(config_name, data, access_token=core.config.access_token)))


@post("/api/configs/{config_name:str}", status_code=200, summary="新建配置")
async def create_config(request: Request, config_name: FromPath[str]) -> Response:
    core = core_of(request)
    if core.config.visitor_mode:
        return json_response(R(True, "success", config_name))
    if not core.configs.is_valid_name(config_name):
        return json_response(R(False, "Config name contains invalid characters"), 400)
    if core.configs.exists(config_name):
        return json_response(R(False, "Config name already exists"), 409)
    core.configs.create(config_name)
    return json_response(R(True, "success", config_name))


@put("/api/configs/{config_name:str}", summary="更新配置")
async def update_config(request: Request, config_name: FromPath[str], data: JSONBody[dict[str, Any]]) -> Response:
    core = core_of(request)
    if core.config.visitor_mode:
        return json_response(R(True, "success", config_name))
    if not core.configs.exists(config_name):
        return json_response(R(False, "not found"), 404)
    error = core.configs.update(config_name, data, access_token=core.config.access_token)
    if error:
        return json_response(R(False, error), 400)
    return json_response(R(True, "updated"))


@delete("/api/configs/{config_name:str}", status_code=200, summary="删除配置")
async def delete_config(request: Request, config_name: FromPath[str]) -> Response:
    core = core_of(request)
    if core.config.visitor_mode:
        return json_response(R(True, "deleted", config_name))
    if not core.configs.delete(config_name):
        return json_response(R(False, "not found"), 404)
    return json_response(R(True, "deleted", config_name))


HANDLERS = [list_configs, get_config, create_config, update_config, delete_config]