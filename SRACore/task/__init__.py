from abc import ABC, abstractmethod
from typing import Any

from SRACore.operators import IOperator


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

    @abstractmethod
    def run(self) -> bool:
        pass

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return f"<{self.__class__.__name__}>"
