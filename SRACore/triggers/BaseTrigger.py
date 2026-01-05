from abc import ABC, abstractmethod


class BaseTrigger(ABC):
    def __init__(self, operator):
        self.operator = operator
        self.enabled=False
        self.name=None

    @abstractmethod
    def run(self):
        pass

    def set_enable(self, boolean):
        self.enabled=boolean


