from abc import ABC, abstractmethod

from SRACore.operator.operator import Executable


class BaseTrigger(Executable, ABC):
    def __init__(self):
        super().__init__()
        self.enabled=False
        self.name=None

    @abstractmethod
    def run(self):
        pass

    def set_enable(self, boolean):
        self.enabled=boolean


