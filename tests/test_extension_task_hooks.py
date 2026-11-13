"""扩展系统「任务注册后钩子」的回归测试。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from SRACore.extension import BaseExtension, ExtensionRegistry, extension, run_task_hooks
from SRACore.task import task_registry


class _HookConfig(BaseModel):
    enabled: bool = True


class _ConfigManager:
    """只实现 run_task_hooks 需要的 get 接口。"""

    def __init__(self, configs: dict[str, Any] | None = None) -> None:
        self._configs = configs or {}

    def get(self, extension_id: str) -> Any:
        return self._configs.get(extension_id)


def test_hook_receives_config_and_task_registry() -> None:
    registry = ExtensionRegistry()
    calls: list[tuple[Any, Any]] = []

    @extension(registry=registry)
    class RecordHookExtension(BaseExtension[_HookConfig]):
        @classmethod
        def on_tasks_registered(cls, tasks, config=None) -> None:
            calls.append((tasks, config))

        def run(self) -> bool:
            return True

    config = _HookConfig()
    run_task_hooks(_ConfigManager({'RecordHook': config}), registry)

    assert calls == [(task_registry, config)]
    assert calls[0][0] is task_registry


def test_hook_is_called_even_when_disabled() -> None:
    registry = ExtensionRegistry()
    calls: list[bool | None] = []

    @extension(registry=registry)
    class DisabledHookExtension(BaseExtension[_HookConfig]):
        @classmethod
        def on_tasks_registered(cls, tasks, config=None) -> None:
            calls.append(config.enabled if config is not None else None)

        def run(self) -> bool:
            return True

    run_task_hooks(_ConfigManager({'DisabledHook': _HookConfig(enabled=False)}), registry)

    assert calls == [False]


def test_hook_failure_does_not_block_other_extensions() -> None:
    registry = ExtensionRegistry()
    calls: list[str] = []

    @extension(registry=registry)
    class BrokenHookExtension(BaseExtension[_HookConfig]):
        @classmethod
        def on_tasks_registered(cls, tasks, config=None) -> None:
            raise RuntimeError('hook failed')

        def run(self) -> bool:
            return True

    @extension(registry=registry)
    class HealthyHookExtension(BaseExtension[_HookConfig]):
        @classmethod
        def on_tasks_registered(cls, tasks, config=None) -> None:
            calls.append('healthy')

        def run(self) -> bool:
            return True

    run_task_hooks(_ConfigManager(), registry)

    assert calls == ['healthy']


def test_extension_without_config_receives_none() -> None:
    registry = ExtensionRegistry()
    calls: list[Any] = []

    @extension(registry=registry)
    class NoConfigHookExtension(BaseExtension):
        @classmethod
        def on_tasks_registered(cls, tasks, config=None) -> None:
            calls.append(config)

        def run(self) -> bool:
            return True

    run_task_hooks(_ConfigManager(), registry)

    assert calls == [None]
