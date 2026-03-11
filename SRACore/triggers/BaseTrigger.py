from abc import ABC, abstractmethod

from SRACore.operators.ioperator import IOperator


class BaseTrigger(ABC):
    def __init__(self, operator: IOperator):
        self.operator = operator
        self.enabled: bool=False
        self.name=None

    @abstractmethod
    def run(self):
        pass

    def set_enable(self, boolean: bool):
        self.enabled=boolean

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    def __str__(self):
        return f"{self.__class__.__name__}"

