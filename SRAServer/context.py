"""服务端宿主：在 :class:`~SRACore.services.AppContext` 之上叠加服务端配置。

服务端只做装配：业务实现全部来自 SRACore 的进程内服务，这里把
controllers/MCP 需要的调用面显式委托出去（不使用 ``__getattr__`` 魔法，
便于静态检查与阅读）。
"""

from __future__ import annotations

import asyncio
from typing import Any

from SRACore.extension import ExtensionConfigManager, ExtensionRunner
from SRACore.operators.ioperator import IOperator
from SRACore.services import (
    AppContext,
    AppInfoService,
    BackendService,
    CacheService,
    ConfigService,
    LogStreamService,
    SettingsService,
)
from SRACore.thread.task_process import TaskManager

from SRAServer.config import ServerConfig


class ServerContext:
    """服务端宿主：AppContext + 服务端配置（AccessToken / 访问模式等）。"""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self._context = AppContext(log_level=config.log_level, with_log_stream=True)

    # ── 服务层（委托 AppContext）──

    @property
    def settings(self) -> SettingsService:
        return self._context.settings

    @property
    def cache(self) -> CacheService:
        return self._context.cache

    @property
    def configs(self) -> ConfigService:
        return self._context.configs

    @property
    def app(self) -> AppInfoService:
        return self._context.app

    @property
    def backend(self) -> BackendService:
        return self._context.backend

    @property
    def log_stream(self) -> LogStreamService:
        return self._context.log_stream

    @property
    def task_manager(self) -> TaskManager:
        return self._context.task_manager

    @property
    def extension_config_manager(self) -> ExtensionConfigManager:
        return self._context.extension_config_manager

    @property
    def extension_runner(self) -> ExtensionRunner:
        return self._context.extension_runner

    # ── 生命周期 ──

    def bind_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._context.bind_event_loop(loop)

    def shutdown(self) -> None:
        """停止运行中的工作并释放全局键盘监听（进程退出时调用）。"""
        self._context.shutdown()

    def request_stop_all(self) -> None:
        self._context.request_stop_all()

    def stop_running_work(self) -> None:
        self._context.stop_running_work()

    def is_busy(self) -> bool:
        return self._context.is_busy()

    def restart(self) -> None:
        self._context.restart()

    # ── 任务 ──

    def run_configs(self, config_names: list[str]) -> bool:
        return self._context.run_configs(config_names)

    def run_single(self, task: str, config_name: str | None = None) -> bool:
        return self._context.run_single(task, config_name)

    def task_status(self) -> dict[str, Any]:
        return self._context.task_status()

    # ── 扩展 ──

    def extension_list(self) -> list[dict[str, Any]]:
        return self._context.extension_list()

    def extension_schema(self, ext_id: str) -> dict[str, Any] | None:
        return self._context.extension_schema(ext_id)

    def extension_config_get(self, ext_id: str) -> dict[str, Any] | None:
        return self._context.extension_config_get(ext_id)

    def extension_config_set(self, ext_id: str, data: dict[str, Any]) -> tuple[bool, str]:
        return self._context.extension_config_set(ext_id, data)

    def extension_run(self, ext_id: str, config_name: str | None = None) -> tuple[bool, str]:
        return self._context.extension_run(ext_id, config_name)

    def extension_stop(self, ext_id: str) -> tuple[bool, str]:
        return self._context.extension_stop(ext_id)

    def extension_reload(self) -> tuple[bool, str]:
        return self._context.extension_reload()

    # ── Operator ──

    def create_operator(self) -> IOperator:
        return self._context.create_operator()

    def operator_list(self) -> list[str]:
        return self._context.operator_list()

    def operator_help(self, method: str) -> dict[str, Any] | None:
        return self._context.operator_help(method)

    def operator_call(self, method: str, params: Any) -> tuple[bool, str, Any]:
        return self._context.operator_call(method, params)