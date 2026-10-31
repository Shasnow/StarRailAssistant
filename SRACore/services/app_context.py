"""``AppContext``：SRACore 的进程内宿主。

构造并持有任务/扩展/Operator 编排所需的全部对象，供 CLI 与服务端复用同一套实现。
"""

from __future__ import annotations

import inspect
import os
import sys
from typing import Any

from loguru import logger

from SRACore.extension import (
    ExtensionConfigManager,
    ExtensionRunner,
    extension_registry,
    load_extensions,
    reload_extensions,
)
from SRACore.localization import Resource
from SRACore.localization.presentation import localize_schema
from SRACore.operators.factory import OperatorFactory, OperatorType
from SRACore.operators.ioperator import IOperator
from SRACore.services.app_info_service import AppInfoService
from SRACore.services.backend_service import BackendService
from SRACore.services.cache_service import CacheService
from SRACore.services.config_service import ConfigService
from SRACore.services.log_stream import LogStreamService
from SRACore.services.setting_service import SettingsService
from SRACore.thread.task_process import TaskManager
from SRACore.util import dynamic_import
from SRACore.util.const import AppDataDir, CacheDir, ConfigsDir
from SRACore.util.logger import setup_logger
from SRACore.util.standard_io import configure_standard_streams

# 不暴露给用户的 Operator 方法（内部/静态/构造器）
_OP_EXCLUDE = frozenset({"__init__", "sleep", "do_while", "wait_any", "login"})

_DEFAULT_LOG_FORMAT = "<green>{time:HH:mm:ss}</green> | <level>{level:5}</level> | <level>{message}</level>"


class AppContext:
    """SRACore 的进程内宿主。"""

    def __init__(
        self,
        *,
        log_level: str = "INFO",
        log_format: str = _DEFAULT_LOG_FORMAT,
        working_dir: str | None = None,
        with_log_stream: bool = False,
    ) -> None:
        # 将工作目录加入 sys.path，使 tasks/extensions 可被动态导入（与 CLI 一致）
        sys.path.append(working_dir or os.getcwd())
        configure_standard_streams()

        self.settings: SettingsService = SettingsService()
        Resource.set_language(self.settings.settings.Display.Language)
        setup_logger(level=log_level)

        self.log_stream = LogStreamService()
        if with_log_stream:
            # CLI 不接 SSE，默认不注册 sink；服务端显式开启
            logger.add(self.log_stream.sink, level=log_level, format=log_format, enqueue=False)

        dynamic_import("tasks")
        load_extensions()

        self.task_manager = TaskManager(self.settings)
        self.extension_config_manager = ExtensionConfigManager()
        self._event_listener = self._create_event_listener()
        self.extension_runner = ExtensionRunner(
            self.extension_config_manager,
            self.settings,
            event_listener=self._event_listener,
        )

        # 服务层
        self.cache = CacheService()
        self.configs = ConfigService(self.cache)
        self.app = AppInfoService(self.settings)
        self.backend = BackendService(self)

        self._ensure_dirs()
        logger.info(f"SRA core ready (language={self.settings.settings.Display.Language}).")

    # ── 基础设施 ──

    @staticmethod
    def _ensure_dirs() -> None:
        for directory in (AppDataDir, ConfigsDir, CacheDir):
            directory.mkdir(parents=True, exist_ok=True)

    def _create_event_listener(self):
        """创建全局键盘监听（pynput 缺失时返回 None）。"""
        try:
            from SRACore.runtime.event_listener import KeyboardListener
        except Exception:
            logger.warning("Keyboard listener unavailable (pynput not installed), hotkeys disabled")
            return None
        try:
            stop_hotkey = self.settings.settings.General.hotkeyStop.lower() or "f9"
            listener = KeyboardListener()
            listener.register_key_event(stop_hotkey, lambda _: self.request_stop_all())
            listener.start()
            return listener
        except Exception as e:
            logger.warning(f"Failed to start keyboard listener: {e}")
            return None

    def bind_event_loop(self, loop) -> None:
        self.log_stream.bind_loop(loop)

    def shutdown(self) -> None:
        """停止运行中的工作并释放全局键盘监听（退出时调用）。"""
        self.task_manager.stop_thread(timeout=5.0)
        self.extension_runner.stop_thread(timeout=5.0)
        if self._event_listener is not None:
            self._event_listener.stop()

    # ── 生命周期 ──

    def request_stop_all(self) -> None:
        """请求停止当前运行中的任务与扩展（两者共享工作线程）。"""
        self.task_manager.request_stop()
        self.extension_runner.request_stop()

    def stop_running_work(self) -> None:
        """请求停止并等待共享工作线程结束。"""
        self.request_stop_all()
        self.task_manager.stop_thread()

    def is_busy(self) -> bool:
        return self.task_manager.is_thread_running()

    def restart(self) -> None:
        """进程内重启：停止运行、重载任务与扩展、重载设置。"""
        self.stop_running_work()

        from SRACore.task import task_registry
        from SRACore.util import reload_package

        task_registry.clear()
        reload_package("tasks")

        reload_extensions()
        self.extension_config_manager.refresh()
        # 触发设置按 mtime 重新加载
        _ = self.settings.settings
        logger.info("Backend restarted.")

    # ── 任务 ──

    def run_configs(self, config_names: list[str]) -> bool:
        """运行指定配置（空列表表示全部配置），已有任务运行时返回 False。"""
        if self.is_busy():
            return False
        return self.task_manager.run_in_thread(*config_names)

    def run_single(self, task: str, config_name: str | None = None) -> bool:
        if self.is_busy():
            return False
        return self.task_manager.run_task_in_thread(task, config_name)

    def task_status(self) -> dict[str, Any]:
        info = self.task_manager.info
        return {
            "session_id": info.session_id,
            "pid": info.pid,
            "mode": info.mode,
            "status": str(info.status),
            "configs": list(info.configs),
            "unit": info.unit,
            "error": info.error,
            "progress": [info.progress[0], info.progress[1]],
        }

    # ── 扩展 ──

    def extension_list(self) -> list[dict[str, Any]]:
        from SRACore.localization.presentation import translate

        data = []
        for ext_id in extension_registry.get_ids():
            entry = extension_registry.get(ext_id)
            data.append({
                "id": ext_id,
                "name": translate(entry.name),
                "description": translate(entry.description),
                "extension_class": entry.extension_cls.__name__,
                "config_class": entry.config_cls.__name__ if entry.config_cls else "",
            })
        return data

    def extension_schema(self, ext_id: str) -> dict[str, Any] | None:
        if not extension_registry.has_id(ext_id):
            return None
        return localize_schema(extension_registry.get_schema(ext_id))

    def extension_config_get(self, ext_id: str) -> dict[str, Any] | None:
        if not extension_registry.has_id(ext_id):
            return None
        config = self.extension_config_manager.get(ext_id)
        return config.model_dump(by_alias=True) if config is not None else None

    def extension_config_set(self, ext_id: str, data: dict[str, Any]) -> tuple[bool, str]:
        if not extension_registry.has_id(ext_id):
            return False, f"扩展 '{ext_id}' 不存在"
        config_cls = extension_registry.get_config_class(ext_id)
        if config_cls is None:
            return False, f"扩展 '{ext_id}' 没有配置"
        try:
            config = config_cls.model_validate(data, by_alias=True)
        except Exception as e:
            return False, f"配置验证失败: {e}"
        self.extension_config_manager.set(ext_id, config)
        self.extension_config_manager.save()
        return True, f"扩展 {ext_id} 配置已保存"

    def extension_run(self, ext_id: str, config_name: str | None = None) -> tuple[bool, str]:
        if not extension_registry.has_id(ext_id):
            return False, f"扩展 '{ext_id}' 不存在，使用 'extension list' 查看可用扩展"
        if config_name:
            self.extension_config_manager.load(config_name)
        if extension_registry.is_background(ext_id):
            ok = self.extension_runner.start_extension(ext_id)
            return ok, (f"已启动后台扩展 '{ext_id}'" if ok else f"无法启动后台扩展 '{ext_id}'")
        ok = self.extension_runner.run_in_thread(ext_id)
        return ok, (f"已启动扩展 '{ext_id}'" if ok else f"无法启动扩展 '{ext_id}'")

    def extension_stop(self, ext_id: str) -> tuple[bool, str]:
        if not extension_registry.has_id(ext_id):
            return False, f"扩展 '{ext_id}' 不存在"
        if extension_registry.is_background(ext_id):
            stopped = self.extension_runner.stop_extension(ext_id)
            return True, (f"已停止后台扩展 '{ext_id}'" if stopped else f"后台扩展 '{ext_id}' 未运行")
        info = self.extension_runner.info
        if not self.extension_runner.is_thread_running():
            return False, f"扩展 '{ext_id}' 未在运行"
        if info.unit and info.unit != ext_id:
            return False, f"当前正在运行的扩展是 '{info.unit}'，不是 '{ext_id}'"
        self.extension_runner.stop_thread()
        return True, f"已停止扩展 '{ext_id}'"

    def extension_reload(self) -> tuple[bool, str]:
        if self.extension_runner.is_thread_running():
            return False, "扩展线程正在运行中，无法执行重载操作"
        active_background = [
            ext_id for ext_id in self.extension_runner.extensions
            if extension_registry.is_background(ext_id)
        ]
        for ext_id in active_background:
            self.extension_runner.stop_extension(ext_id)

        before, after = reload_extensions()
        self.extension_config_manager.refresh()

        restarted = []
        for ext_id in active_background:
            if extension_registry.has_id(ext_id) and self.extension_runner.start_extension(ext_id):
                restarted.append(ext_id)

        if not after:
            return False, "重载完成，但没有已注册的扩展"
        added = sorted(after - before)
        removed = sorted(before - after)
        message = f"已重载扩展，当前共 {len(after)} 个（更新 {len(sorted(before & after))} 个）"
        if added:
            message += f"，新增: {', '.join(added)}"
        if removed:
            message += f"，移除: {', '.join(removed)}"
        if restarted:
            message += f"，已重启后台扩展: {', '.join(restarted)}"
        return True, message

    # ── Operator ──

    def create_operator(self) -> IOperator:
        optype = (
            OperatorType.Browser
            if self.settings.settings.General.isCloudGameEnabled
            else OperatorType.Local
        )
        return OperatorFactory.get_operator(
            optype, self.settings.settings, self.task_manager.stop_event
        )

    def operator_list(self) -> list[str]:
        return sorted(
            name
            for name, _ in inspect.getmembers(IOperator, predicate=inspect.isfunction)
            if not name.startswith("_") and name not in _OP_EXCLUDE
        )

    def operator_help(self, method: str) -> dict[str, Any] | None:
        fn = getattr(IOperator, method, None)
        if fn is None or not callable(fn):
            return None
        sig = inspect.signature(fn)
        params = []
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            info: dict[str, Any] = {"name": name}
            if param.default is not inspect.Parameter.empty:
                info["default"] = param.default
            if param.annotation is not inspect.Parameter.empty:
                info["type"] = str(param.annotation)
            params.append(info)
        doc = (fn.__doc__ or "").strip()
        summary = doc.split("\n")[0] if doc else ""
        return {"method": method, "summary": summary, "parameters": params, "doc": doc}

    def operator_call(self, method: str, params: Any) -> tuple[bool, str, Any]:
        """调用 Operator 方法，返回 (success, message, data)。"""
        try:
            operator = self.create_operator()
        except Exception as e:
            return False, f"Operator 初始化失败: {e}", None

        fn = getattr(operator, method, None)
        if fn is None or not callable(fn):
            return False, f"方法 '{method}' 不存在。可用方法: {', '.join(self.operator_list())}", None

        if not isinstance(params, dict):
            params = {}
        try:
            sig = inspect.signature(fn)
            bound = sig.bind(**params)
            bound.apply_defaults()
            result = fn(*bound.args, **bound.kwargs)
        except FileNotFoundError as e:
            return False, f"文件未找到: {e}", None
        except KeyError as e:
            return False, f"缺少必需参数: {e}", None
        except TypeError as e:
            return False, f"参数类型错误: {e}", None
        except Exception as e:
            return False, f"执行失败: {e}", None

        return True, f"{method} 执行成功", self._serialize_operator_result(result, params)

    @staticmethod
    def _serialize_operator_result(result: Any, params: dict[str, Any]) -> Any:
        from PIL.Image import Image as PILImage

        if isinstance(result, PILImage):
            return {"path": params.get("save_path"), "width": result.width, "height": result.height}
        return result