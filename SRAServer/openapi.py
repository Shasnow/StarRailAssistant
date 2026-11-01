"""``GET /openapi/v1.json``：WebUI 动态表单所依赖的 OpenAPI 规范。

Litestar 的 ``OpenAPIConfig(path="/openapi")`` 只注册 ``/openapi``、``/openapi/openapi.json``
等路径，并不提供 .NET 端使用的 ``/openapi/v1.json``，因此这里自定义该路由，并把
SRACore 生成的 ``TasksConfig`` / ``AppSettings`` 模型展开为组件合并进 ``components.schemas``。
"""

from __future__ import annotations

from litestar import Request, get
from litestar.response import Response

from SRACore.models.app_settings import AppSettings
from SRACore.models.tasks_config import TasksConfig

from SRAServer.controllers._responses import json_response


def openapi_components() -> dict[str, object]:
    """把生成模型展开为 OpenAPI 组件（含嵌套 ``$ref`` 目标）。

    Returns:
        {组件名: schema}，键包含 ``TasksConfig``、``AppSettings`` 及其嵌套模型。
    """
    components: dict[str, object] = {}
    for model in (TasksConfig, AppSettings):
        schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
        components.update(schema.pop("$defs", {}))
        components[model.__name__] = schema
    return components


@get("/openapi/v1.json", include_in_schema=False)
async def get_openapi_v1(request: Request) -> Response:
    """返回合并了 WebUI 所需组件的 OpenAPI 规范。"""
    schema = request.app.openapi_schema.to_schema()
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    components.update(openapi_components())
    return json_response(schema)


HANDLERS = [get_openapi_v1]