import sys
import time

from PySide6.QtWidgets import QApplication

from SRACore.component.main_window import MainWindowComponent
from SRACore.component.tray import SystemTray
from SRACore.thread.background_thread import BackgroundThreadWorker
from SRACore.thread.task_thread import TaskManager
from SRACore.thread.trigger_thread import TriggerManager
from SRACore.util.config import GlobalConfigManager
from SRACore.util.logger import logger
from SRACore.util.plugin import PluginManager


class SRA:
    """应用程序的主类，负责初始化和运行应用程序。"""
    def __init__(self):
        PluginManager.scan_plugins()
        self.global_manager = GlobalConfigManager()
        self.trigger_manager = TriggerManager.get_instance()
        self.main_window = MainWindowComponent(None, self.global_manager)
        PluginManager.public_instance = self
        PluginManager.public_main_window = self.main_window
        self.tray = SystemTray(self.main_window)
        self.main_window.set_background_thread(*BackgroundThreadWorker.create(self.global_manager))
        self.task_thread = TaskManager(self.global_manager)
        self.main_window.started.connect(self.task_thread.start)
        self.main_window.require_stop.connect(self.task_thread.stop)
        self.task_thread.finished.connect(self.main_window.finish)
        self.main_window.set_trigger_thread(self.trigger_manager)

    @staticmethod
    def run():
        """启动应用程序的静态方法。"""
        start_time = time.time()
        app = QApplication(sys.argv)
        sra = SRA()
        sra.main_window.show()
        sra.tray.show()
        PluginManager.load_plugins('late')
        end_time = time.time()
        logger.info("SRA 启动完成，耗时 {:.2f} 秒".format(end_time - start_time))
        sys.exit(app.exec_())
