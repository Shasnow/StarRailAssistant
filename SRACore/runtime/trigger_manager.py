import sys
import threading
import time

from SRACore.operators.factory import OperatorFactory
from SRACore.operators.operator import Operator
from SRACore.triggers import AutoPlotTrigger
from SRACore.triggers.BaseTrigger import BaseTrigger
from SRACore.util.logger import logger


class TriggerManager:
    __instance = None

    def __init__(self):
        self.isRunning = False
        super().__init__()
        self.triggers: list[BaseTrigger] = []
        self._thread: threading.Thread | None = None
        if sys.platform == 'win32':
            self.register(AutoPlotTrigger(Operator(OperatorFactory.get_ocr_instance())))

    def run(self):
        """触发器主循环"""
        self.isRunning = True
        while self.isRunning:
            for trigger in self.triggers:
                if trigger.enabled:
                    trigger.run()
            time.sleep(0.1)

    def stop(self):
        """停止触发器管理器"""
        for trigger in self.triggers:
            trigger.set_enable(False)
        self.isRunning = False
        logger.debug('request to stop trigger service')

    def register(self, trigger: BaseTrigger):
        """注册触发器"""
        if trigger not in self.triggers:
            self.triggers.append(trigger)
            logger.debug(f'trigger registered: {trigger}')
        else:
            logger.debug(f'trigger already registered: {trigger}')

    def has_enabled_triggers(self) -> bool:
        """检查是否有启用的触发器"""
        return any(t.enabled for t in self.triggers)

    def is_thread_running(self) -> bool:
        """检查触发器线程是否正在运行"""
        return self._thread is not None and self._thread.is_alive()

    def start_thread(self):
        """启动触发器线程"""
        if self.is_thread_running():
            logger.warning("Trigger thread is already running")
            return
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
        logger.info("Trigger thread started")

    def stop_thread(self, timeout: float = 5.0):
        """停止触发器线程"""
        if not self.is_thread_running():
            return
        self.stop()
        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            logger.error("Trigger thread did not stop in time")
        else:
            logger.info("Trigger thread stopped")
        self._thread = None

    def ensure_running(self):
        """确保触发器线程在运行（如果有启用的触发器）"""
        if self.has_enabled_triggers() and not self.is_thread_running():
            self.start_thread()

    def stop_if_idle(self):
        """如果没有启用的触发器，则停止线程"""
        if not self.has_enabled_triggers() and self.is_thread_running():
            self.stop_thread()
