import time

from SRACore.operator import Operator
from SRACore.triggers import AutoPlotTrigger
from SRACore.triggers.BaseTrigger import BaseTrigger
from SRACore.util.logger import logger


class TriggerManager:
    __instance = None

    def __init__(self):
        self.isRunning = False
        super().__init__()
        self.triggers: list[BaseTrigger] = []
        self.register(AutoPlotTrigger(Operator()))

    def run(self):
        self.isRunning = True
        while self.isRunning:
            for trigger in self.triggers:
                if trigger.enabled:
                    trigger.run()
            time.sleep(0.1)

    def stop(self):
        """
        停止触发器管理器的运行。
        """
        for trigger in self.triggers:
            trigger.set_enable(False)
        self.isRunning = False
        logger.debug('request to stop trigger service')

    def register(self, trigger: BaseTrigger):
        """
        注册触发器实例到管理器中。
        :param trigger: 触发器实例
        """
        if trigger not in self.triggers:
            self.triggers.append(trigger)
            logger.debug(f'trigger registered: {trigger}')
        else:
            logger.debug(f'trigger already registered: {trigger}')

