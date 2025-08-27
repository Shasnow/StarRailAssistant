import keyboard
from PySide6.QtCore import QObject, Signal, QThread

from SRACore.util.config import GlobalConfigManager
from SRACore.util.logger import logger


class BackgroundThreadWorker(QObject):
    """后台线程工作类，用于处理热键监听、定时任务等。"""
    hotkey_triggered = Signal(str)
    schedule_triggered = Signal(str)
    finished_signal = Signal()

    def __init__(self, gcm: GlobalConfigManager):
        super().__init__()
        self.gcm = gcm
        self.isRunning = False

    def run(self):
        """启动后台任务。"""
        self.isRunning = True
        hotkey1 = self.gcm.get('hotkey1')
        hotkey2 = self.gcm.get('hotkey2')
        while self.isRunning:
            QThread.msleep(100)
            if keyboard.is_pressed(hotkey1):
                self.hotkey_pressed('hotkey1')
            if keyboard.is_pressed(hotkey2):
                self.hotkey_pressed('hotkey2')
        self.finished_signal.emit()
        logger.debug("后台线程已停止。")

    def stop(self):
        """停止后台任务。"""
        logger.debug("正在停止后台线程...")
        self.isRunning = False

    def hotkey_pressed(self, hotkey):
        """处理热键按下事件。"""
        self.hotkey_triggered.emit(hotkey)

    @staticmethod
    def create(gcm: GlobalConfigManager):
        """
        创建一个后台线程和工作实例。
        使用QT推荐的thread-worker模式来处理后台任务。
        :param gcm: 全局配置管理器实例
        :return: thread: 线程实例, worker: 工作实例
        """
        thread = QThread()
        worker = BackgroundThreadWorker(gcm)
        worker.moveToThread(thread)

        # 连接信号
        thread.started.connect(worker.run)
        worker.finished_signal.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        return thread, worker
