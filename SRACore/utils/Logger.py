import time
from enum import StrEnum


class Level(StrEnum):
    """日志级别枚举"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    DEBUG = "DEBUG"
    TRACE = "TRACE"
    EXCEPTION = "EXCEPTION"

class Logger:
    """日志记录器类"""

    def log(self, level: Level | str, message=""):  # NOQA
        """记录日志"""
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), level, message)

    def info(self, message=""):
        """记录信息级别日志"""
        self.log(Level.INFO, message)

    def warning(self, message=""):
        """记录警告级别日志"""
        self.log(Level.WARNING, message)

    def error(self, message=""):
        """记录错误级别日志"""
        self.log(Level.ERROR, message)

    def success(self, message=""):
        """记录成功级别日志"""
        self.log(Level.SUCCESS, message)

    def debug(self, message=""):
        """记录调试级别日志"""
        self.log(Level.DEBUG, message)

    def trace(self, message=""):
        """记录追踪级别日志"""
        self.log(Level.TRACE, message)

    def exception(self, message=""):
        """记录异常级别日志"""
        self.log(Level.EXCEPTION, message)

# 实例化日志记录器

logger = Logger()
__all__ = ["logger"]