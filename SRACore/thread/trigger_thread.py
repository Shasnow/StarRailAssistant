import time

from SRACore.triggers import AutoPlotTrigger
from SRACore.triggers.BaseTrigger import BaseTrigger
from SRACore.util.logger import logger

class TriggerManager:
    __instance = None

    def __init__(self):
        self.isRunning = False
        super().__init__()
        self.triggers: list[BaseTrigger] = []
        self.register(AutoPlotTrigger())

    def run(self):
        self.isRunning = True
        while self.isRunning:
            for trigger in self.triggers:
                if trigger.enabled:
                    trigger.run()
            time.sleep(0.1)
        logger.debug("TriggerManager stopped.")

    def stop(self):
        """
        停止触发器管理器的运行。
        """
        logger.debug("正在停止触发器线程...")
        for trigger in self.triggers:
            trigger.set_enable(False)
        self.isRunning = False

    def register(self, trigger: BaseTrigger):
        """
        注册触发器实例到管理器中。
        :param trigger: 触发器实例
        """
        if trigger not in self.triggers:
            self.triggers.append(trigger)
            logger.debug(f"Trigger {trigger.__class__.__name__} registered successfully.")
        else:
            logger.debug(f"Trigger {trigger.__class__.__name__} is already registered.")

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

