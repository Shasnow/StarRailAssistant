from abc import ABC, abstractmethod

from SRACore.operator import Executable


class BaseTrigger(Executable, ABC):
    def __init__(self, operator):
        super().__init__(operator)
        self.enabled=False
        self.name=None

    @abstractmethod
    def run(self):
        pass

    def set_enable(self, boolean):
        self.enabled=boolean


