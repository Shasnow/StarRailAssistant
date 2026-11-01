"""请求体模型：宽松接受客户端下发的 camelCase / PascalCase / snake_case 字段名。

历史背景：原 C# 服务端用 ASP.NET Core 的 ``[FromBody]``，其 ``PropertyNameCaseInsensitive``
默认为 true，因此 WebUI 下发的 camelCase、桌面端下发的 PascalCase 都能被绑定。Pydantic
没有这个默认行为，故这里用 ``validation_alias=AliasChoices(...)`` 显式放宽：未知键会被
``extra="allow"`` 静默吞掉，一旦字段名不匹配就会退化成默认值（如 ``/api/task/run`` 误跑全部配置）。
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class TokenRequest(_Base):
    """POST /api/auth 请求体。"""

    token: str | None = None


class RestartRequest(_Base):
    """POST /api/backend/restart 请求体（可缺省）。"""

    arguments: str | None = None


class RunRequest(_Base):
    """POST /api/task/run 请求体。

    兼容 WebUI 的 ``configName``、桌面端远程模式的 ``Config``/``Persist`` 及字段名本身。
    """

    config_name: str | None = Field(
        None, validation_alias=AliasChoices("configName", "ConfigName", "config_name")
    )
    config: dict[str, Any] | None = Field(None, validation_alias=AliasChoices("config", "Config"))
    persist: bool = Field(False, validation_alias=AliasChoices("persist", "Persist"))


class SingleTaskRequest(_Base):
    """POST /api/task/single 请求体。"""

    task_name: str = Field(
        validation_alias=AliasChoices("taskName", "TaskName", "task_name")
    )
    config_name: str | None = Field(
        None, validation_alias=AliasChoices("configName", "ConfigName", "config_name")
    )


class OperatorCallRequest(_Base):
    """POST /api/operator/call 请求体。"""

    method: str
    params: Any = None