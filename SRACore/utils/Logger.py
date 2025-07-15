import os
import sys
import time
from abc import ABC, abstractmethod
from enum import StrEnum
from threading import Lock
from typing import Union

from PySide6.QtCore import QObject, Signal
from rich.console import Console
from rich.theme import Theme


class Level(StrEnum):
    """日志级别枚举"""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    EXCEPTION = "EXCEPTION"


class Handler(ABC):
    """日志处理器基类"""

    def __init__(self, fmt: str = "{time} {level} {message}", level: Level = Level.INFO) -> None:
        self.fmt = fmt
        self.level = level  # 默认只记录 INFO 及以上级别
        self._lock = Lock()  # 确保线程安全

    def set_level(self, level: Union[Level, str]) -> None:
        """设置日志级别"""
        if isinstance(level, str):
            try:
                self.level = Level(level)
            except ValueError:
                raise ValueError(f"无效的日志级别: {level}")
        else:
            self.level = level

    def should_handle(self, level: Union[Level, str]) -> bool:
        """检查是否应该处理该级别的日志"""
        if isinstance(level, str):
            try:
                level = Level(level)
            except ValueError:
                return True  # 未知级别默认处理

        return list(Level).index(level) >= list(Level).index(self.level)

    def format_message(self, level: Union[Level, str], message: str) -> str:
        """格式化日志消息"""
        if isinstance(level, Level):
            level_str = level.value
        else:
            level_str = level

        return self.fmt.format(
            time=time.strftime('%Y-%m-%d %H:%M:%S'),
            level=level_str,
            message=message
        )

    @abstractmethod
    def handle(self, level: Union[Level, str], message: str) -> None:
        """处理日志消息（子类必须实现）"""
        raise NotImplementedError("子类必须实现 handle 方法")


class Logger:
    """线程安全的日志记录器类"""

    def __init__(self):
        self._lock = Lock()  # 确保线程安全
        self.handlers = []

    def log(self, level: Union[Level, str], message: str) -> None:
        """记录日志"""
        for handler in self.handlers:
            try:
                handler.handle(level, message)
            except Exception as e:
                print(f"日志处理器执行失败: {e}")

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

    def add_handler(self, handler: Handler) -> int:
        """添加日志处理器"""
        if handler not in self.handlers:
            self.handlers.append(handler)
            return len(self.handlers) - 1  # 返回处理器的索引
        return -1

    def remove(self, handler: Handler | int) -> None:
        """移除日志处理器"""
        if isinstance(handler, int):
            if 0 <= handler < len(self.handlers):
                del self.handlers[handler]
        elif handler in self.handlers:
            self.handlers.remove(handler)


class ConsoleHandler(Handler):
    """支持 Rich 色彩的控制台日志处理器"""
    # 自定义主题
    custom_theme = Theme({
        "debug": "bold cyan",
        "info": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "exception": "bold red",
        "success": "bold magenta",
        "trace": "dim",
    })

    console = Console(theme=custom_theme)

    def __init__(self):
        super().__init__(level=Level.TRACE)
        self._lock = Lock()  # 确保线程安全

    def handle(self, level: Union[Level, str], message: str) -> None:
        """将日志消息打印到控制台（带 Rich 色彩）"""
        if not self.should_handle(level):
            return

        formatted_msg = self.format_message(level, message)

        # 根据日志级别应用不同样式
        with self._lock:
            self.console.print(formatted_msg)

    def format_message(self, level: Union[Level, str], message: str) -> str:
        """格式化日志消息"""
        if isinstance(level, Level):
            level_str = level.value
        else:
            level_str = level

        return self.fmt.format(
            time="[green]" + time.strftime('%Y-%m-%d %H:%M:%S') + "[/green]",
            level=f"[{level_str.lower()}]{level_str}[/{level_str.lower()}]",
            message=message
        )


class FileHandler(Handler):
    """文件日志处理器"""

    def __init__(self, file_path: str, fmt: str = "{time} {level} {message}", level: Level = Level.INFO) -> None:
        super().__init__(fmt, level)
        self.file_path = file_path

    def handle(self, level: Union[Level, str], message: str) -> None:
        """将日志消息写入文件"""
        if not self.should_handle(level):
            return

        formatted_msg = self.format_message(level, message)
        with self._lock:  # 确保线程安全
            try:
                with open(self.file_path, "a", encoding="utf-8") as f:
                    f.write(formatted_msg + "\n")
            except Exception as e:
                print(f"写入日志文件失败: {e}")


class CallbackHandler(Handler):
    """回调日志处理器"""

    def __init__(self, callback, fmt: str = "{time} {level} {message}", level: Level = Level.INFO) -> None:
        super().__init__(fmt, level)
        self.callback = callback

    def handle(self, level: Union[Level, str], message: str) -> None:
        """调用回调函数处理日志消息"""
        if not self.should_handle(level):
            return

        formatted_msg = self.format_message(level, message)
        with self._lock:  # 确保线程安全
            try:
                self.callback(formatted_msg)
            except Exception as e:
                print(f"回调处理日志失败: {e}")


class LogEmitter(QObject):
    """Log Emitter for logging messages in the GUI."""

    log_signal = Signal(str)

    def log_emit(self, text):
        """Emit a signal with the given text."""
        self.log_signal.emit(text)


# 实例化日志记录器
log_emitter = LogEmitter()  # 用于 GUI 日志信号发射
logger = Logger()
if sys.stdout.isatty():
    # 如果标准输出是终端，则添加 Rich 控制台处理器
    logger.add_handler(ConsoleHandler())
    logger.success("Rich 控制台日志处理器已启用")
if not os.path.exists("log"):
    os.mkdir("log")
logger.add_handler(FileHandler("log/SRAlog.log", level=Level.TRACE))
logger.add_handler(CallbackHandler(log_emitter.log_emit, level=Level.INFO))
__all__ = ["logger", "Level", "log_emitter"]
