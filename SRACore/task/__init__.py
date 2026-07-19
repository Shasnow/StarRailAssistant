import importlib
from abc import ABC, abstractmethod
import time
from typing import final
from pathlib import Path

from loguru import logger
from PIL.Image import Image

from SRACore.localization import Resource
from SRACore.models.tasks_config import TasksConfig
from SRACore.notification import try_send_notification
from SRACore.operators.ioperator import IOperator
from SRACore.util.const import LogsScreenshotDir


class Executable:
    def __init__(self, operator: IOperator):
        self.operator = operator
        self.settings = operator.settings
        self.stop_event = self.operator.stop_event

    def stop(self):
        if self.stop_event is not None:
            self.stop_event.set()


class BaseTask(Executable, ABC):
    def __init__(self, operator: IOperator, config: TasksConfig):
        """
        基础任务类，所有任务类都应继承自此类。
        """
        super().__init__(operator)
        self.config = config
        self._post_init()

    def _post_init(self):
        """子类可重写此方法以进行额外初始化"""
        pass

    @final
    def start(self) -> None:
        self.on_start()

    @abstractmethod
    def run(self) -> bool:
        pass

    @final
    def complete(self) -> None:
        self.on_completed()

    @final
    def fail(self) -> None:
        self.on_failed()

    def send_notification(self, message: str, result: str, image: Image | None = None) -> None:
        try_send_notification(
            Resource.task_notificationTitle,
            message,
            result=result,
            image=image
        )

    def on_start(self) -> None:
        on_start = self.settings.Notification.onStart
        if self.__class__.__name__ in on_start:
            self.send_notification(f"任务 {self.__class__.__name__} 开始执行。", "success")

    def on_completed(self) -> None:
        on_complete = self.settings.Notification.onCompleted
        if self.__class__.__name__ in on_complete:
            self.send_notification(f"任务 {self.__class__.__name__} 执行完成。", "success")

    def on_failed(self) -> None:
        if self.operator.width != 1920 and self.operator.height != 1080:
            logger.warning(
                f"可能的失败原因：游戏分辨率不符合要求：1920x1080，当前：{self.operator.width}x{self.operator.height}。")
        image = None
        try:
            image = self.operator.screenshot()
            image.save(LogsScreenshotDir / f"{self.__class__.__name__}_lastfailed.png")
        except Exception:
            pass
        self.send_notification(f"任务 {self.__class__.__name__} 执行失败。", "error", image=image)

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


registry: list[tuple[int, type[BaseTask]]] = list()


def _ensure_task_modules_loaded(package="tasks") -> None:
    """确保任务模块已被导入，从而触发装饰器注册。"""
    try:
        # 扫描 tasks 包下的所有 .py 文件，导入每个模块
        for file in Path(package).glob("*.py"):
            importlib.import_module(f"{package}.{file.stem}")
    except ModuleNotFoundError:
        pass


def task(_cls: type[BaseTask] | None = None, *, order: int | None = None):
    """
    任务注册装饰器，用于将任务类注册到全局任务列表中，并指定执行顺序。
    """

    def decorator(cls: type[BaseTask]) -> type[BaseTask]:
        if not issubclass(cls, BaseTask):
            raise TypeError("只能注册 BaseTask 的子类")
        _order = len(registry) if order is None else order
        registry.append((_order, cls))
        return cls

    if _cls is None:
        return decorator
    return decorator(_cls)


def get_task_classes() -> list[type[BaseTask]]:
    _ensure_task_modules_loaded()
    return [cls for order, cls in sorted(registry, key=lambda x: x[0])]
