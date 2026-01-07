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

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    def __str__(self):
        return f"{self.__class__.__name__}"

