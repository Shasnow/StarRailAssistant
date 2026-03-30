from abc import ABC, abstractmethod
import threading
from typing import Any

from SRACore.operators import IOperator


class Executable:
    def __init__(self, operator: IOperator, stop_event: threading.Event | None = None):
        self.operator = operator
        self.settings = operator.settings
        self._stop_event = stop_event

    @property
    def should_stop(self) -> bool:
        if self._stop_event is None:
            return False
        return self._stop_event.is_set()

    def stop(self):
        if self._stop_event is not None:
            self._stop_event.set()


class BaseTask(Executable, ABC):
    def __init__(self, operator: IOperator, config: dict[str, Any], stop_event: threading.Event | None = None):
        """
        基础任务类，所有任务类都应继承自此类。
        stop_event 用于线程执行模型下的协作式停止。
        """
        super().__init__(operator, stop_event)
        self.config = config
        self._post_init()

    def _post_init(self):
        """子类可重写此方法以进行额外初始化"""
        pass

    @abstractmethod
    def run(self) -> bool:
        pass

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return f"<{self.__class__.__name__}>"
