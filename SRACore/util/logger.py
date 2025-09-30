import sys

from PySide6.QtCore import QObject, Signal
from loguru import logger


class LogEmitter(QObject):
    """Log Emitter for logging messages in the GUI."""

    log_signal = Signal(str)

    def log_emit(self, text):
        """Emit a signal with the given text."""
        self.log_signal.emit(text)


# 实例化日志记录器
log_emitter = LogEmitter()  # 用于 GUI 日志信号发射
logger.remove(0)
if sys.stdout.isatty():
    logger.add(sys.stdout, level=0,
               format="<green>{time:HH:mm:ss}</green>[{thread}] | <level>{level:5}</level> | <cyan>{module}.{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
               colorize=True, enqueue=True)
    logger.success("已连接终端")
    logger.debug(f'启动参数: {sys.argv[1:]}')

logger.add("log/SRA{time:YYYYMMDDHHmmss}.log", level=0,
           format="{time:YYYY-MM-DD HH:mm:ss} {level:5} {module}.{function}:{line} {message}", colorize=False,
           retention=7, enqueue=True)
logger.add(log_emitter.log_emit, level=20,
           format="{time:HH:mm:ss} {level} {message}", colorize=False,
           enqueue=True)
__all__ = ["logger", "log_emitter"]
