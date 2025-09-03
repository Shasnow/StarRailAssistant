from abc import ABC, abstractmethod

from SRACore.util.operator import Executable


class BaseTrigger(Executable, ABC):
    def __init__(self):
        super().__init__()
        self.enabled=False
        self.name=None
        self.config:dict|None=None

    @abstractmethod
    def run(self):
        pass

    def set_enable(self, boolean):
        self.enabled=boolean

    def set(self, key, v):
        self.config[key] = v

