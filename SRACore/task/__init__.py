from abc import ABC, abstractmethod
from typing import Any, final
from loguru import logger

from SRACore.localization import Resource
from SRACore.operators import IOperator
from SRACore.util import notify


class Executable:
    def __init__(self, operator: IOperator):
        self.operator = operator
        self.settings = operator.settings
        self.stop_event = self.operator.stop_event

    def stop(self):
        if self.stop_event is not None:
            self.stop_event.set()


class BaseTask(Executable, ABC):
    def __init__(self, operator: IOperator, config: dict[str, Any]):
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
    def finish(self) -> None:
        self.on_finish()

    @final
    def fail(self) -> None:
        self.on_failure()

    def send_notification(self, message: str, result: str) -> None:
        notify.try_send_notification(
            Resource.task_notificationTitle,
            message,
            result=result,
            operator=self.operator
        )

    def on_start(self) -> None:
        on_start = self.settings.Notification.onStart
        if self.__class__.__name__ in on_start:
            self.send_notification(f"任务 {self.__class__.__name__} 开始执行。", "success")

    def on_finish(self) -> None:
        on_complete = self.settings.Notification.onComplete
        if self.__class__.__name__ in on_complete:
            self.send_notification(f"任务 {self.__class__.__name__} 执行完成。", "success")

    def on_failure(self) -> None:
        if self.operator.width != 1920 and self.operator.height != 1080:
            logger.warning(f"可能的失败原因：游戏分辨率不符合要求：1920x1080，当前：{self.operator.width}x{self.operator.height}。")
        self.send_notification(f"任务 {self.__class__.__name__} 执行失败。", "error")

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return f"<{self.__class__.__name__}>"
