"""线程运行器基类。

提供统一的单线程管理、互斥机制和运行时状态，供 TaskManager 和 ExtensionRunner 共用。
所有 Runner 子类共享同一个工作线程和停止事件，确保同一时刻只有一个在运行。
"""
import os
import threading
import uuid
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from SRACore.util.errors import ThreadStoppedError


# ── 运行时状态 ──

@dataclass
class RuntimeInfo:
    """统一运行时状态，记录当前 Runner 的执行情况。

    由 Runner 内部方法更新，对外只读（通过 properties 暴露）。
    """
    session_id: str = field(default_factory=lambda :uuid.uuid4().hex)
    pid: int = field(default_factory=os.getpid)
    mode: str = "unknown"
    status: str = "idle"
    configs: tuple[str, ...] = ()
    unit: str = ""
    error: str = ""
    progress: tuple[int, int] = (0, 0)


class Runner(ABC):
    """单线程运行器基类。

    所有 Runner 子类共享同一个后台工作线程和停止事件。
    当任意一个 Runner 启动时，其他 Runner 无法启动，直到当前 Runner 完成或被停止。

    统一运行时状态通过 ``self.info`` 暴露，由内部 ``_set_*`` 方法更新，
    下层 Task / Extension 只读，禁止直接修改。
    """

    # ── 全局共享线程 ──
    _shared_thread: threading.Thread | None = None

    def __init__(self):
        self.stop_event = threading.Event()
        self._info = RuntimeInfo()

    # ── 只读属性：对外暴露，禁止下层直接修改 ──

    @property
    def info(self) -> RuntimeInfo:
        """运行时状态（只读）。"""
        return self._info

    # ── 内部状态更新方法：仅 Runner 及子类调度层调用 ──

    def _reset_info(self, mode: str = "unknown") -> None:
        """重置运行时状态，每次启动线程时调用。"""
        self._info = RuntimeInfo(
            mode=mode,
            status="running",
        )

    def _set_status(self, status: str) -> None:
        self._info.status = status

    def _set_configs(self, configs: tuple[str, ...] | list[str]) -> None:
        self._info.configs = tuple(configs)

    def _set_unit(self, unit: str) -> None:
        self._info.unit = unit

    def _set_error(self, error: str) -> None:
        self._info.error = error

    def _set_progress(self, current: int, total: int) -> None:
        self._info.progress = (current, total)

    # ── 线程管理 ──

    def request_stop(self) -> None:
        """请求停止当前工作。"""
        self.stop_event.set()

    @classmethod
    def is_thread_running(cls) -> bool:
        """检查共享线程是否正在运行。"""
        return Runner._shared_thread is not None and Runner._shared_thread.is_alive()

    def start_thread(self, target: Callable[..., Any], *args) -> bool:
        """在共享线程中启动工作。如果已有线程在运行则拒绝。

        Returns:
            True 表示成功启动，False 表示已有线程在运行。
        """
        if self.is_thread_running():
            logger.warning(f"{self.__class__.__name__} cannot start: another Runner is already running")
            return False
        self.stop_event.clear()
        Runner._shared_thread = threading.Thread(
            target=self._worker,
            daemon=True,
            args=(target, *args),
        )
        Runner._shared_thread.start()
        logger.info(f"{self.__class__.__name__} thread started")
        return True

    def start_and_wait(self, target: Callable[..., Any], *args) -> bool:
        """启动工作线程并阻塞当前调用者，直到工作完成。

        适用于命令行场景中需要同步执行任务/扩展的调用方式。
        """
        if not self.start_thread(target, *args):
            return False
        worker = Runner._shared_thread
        if worker is None:
            return False
        worker.join()
        return True

    def stop_thread(self, timeout: float = 30.0) -> None:
        """停止共享线程并等待其结束。

        仅设置停止事件并 join 等待。资源清理由 worker() 的 finally 块负责。
        """
        self.request_stop()
        t = Runner._shared_thread
        if t is None or not t.is_alive():
            return
        t.join(timeout=timeout)
        if t.is_alive():
            logger.warning(f"{self.__class__.__name__} thread did not stop within timeout")
        else:
            logger.info(f"{self.__class__.__name__} thread stopped")

    def _worker(self, target: Callable[..., Any], *args):
        """线程执行目标函数的包装器，捕获异常，完成后清理共享状态。"""
        logger.debug("[Start]")
        self._set_status("running")
        try:
            result = target(*args)
            if result is False:
                self._set_status("stopped" if self.stop_event.is_set() else "failed")
            elif self.stop_event.is_set():
                self._set_status("stopped")
            elif self._info.status == "running":
                self._set_status("completed")
        except KeyboardInterrupt:
            self.request_stop()
            self._set_status("stopped")
        except ThreadStoppedError:
            logger.warning(f"{self.__class__.__name__} stopped by request")
            self._set_status("stopped")
        except Exception as e:
            logger.exception(f"{self.__class__.__name__} crashed: {e}")
            self._set_error(str(e))
            self._set_status("failed")
        finally:
            if self._info.status == "running":
                self._set_status("stopped" if self.stop_event.is_set() else "completed")
            logger.debug("[Done]")
            Runner._shared_thread = None
