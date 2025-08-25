from abc import ABC, abstractmethod

from SRACore.util.config import ConfigManager
from SRACore.util.operator import Executable


class BaseTask(Executable, ABC):
    def __init__(self, name: str):
        """
        基础任务类，所有任务类都应继承自此类。
        :param name: 名称，用于配置文件字段的标识
        """
        super().__init__()
        self.cm = ConfigManager.get_instance()
        self.config = self.cm.get(name)
        self.stop_flag = False

    @abstractmethod
    def run(self):
        pass

    def stop(self):
        """停止任务"""
        self.stop_flag = True