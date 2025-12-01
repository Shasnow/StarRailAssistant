from abc import ABC, abstractmethod

from SRACore.util.operator import Executable


class BaseTask(Executable, ABC):
    def __init__(self, config: dict):
        """
        基础任务类，所有任务类都应继承自此类。
        """
        super().__init__()
        self.config = config
        self.stop_flag = False

    @abstractmethod
    def run(self):
        pass

    def stop(self):
        """停止任务"""
        self.stop_flag = True
