import os.path
import sys
from typing import Any

from loguru import logger


# 设置日志记录器
def setup_logger(path: str = "log/SRA{time:YYYYMMDD}.log", level: str = "TRACE", queue: Any = None) -> None:
    logger.remove()
    log_format = "<green>{time:HH:mm:ss}</green> | <level>{level:5}</level> | <level>{message}</level>"
    logger.add(sys.stdout, level=level,
               format=log_format,
               enqueue=True, colorize=sys.stdout.isatty())
    logger.add(path, level=level,
               format=log_format,
               colorize=False, retention=7, enqueue=True,
               encoding="utf-8")
    if queue is not None:
        logger.add(queue.put, level=level,
                   format=log_format,
                   colorize=False, enqueue=True)

    if not os.path.exists("log/ocr"):
        os.makedirs("log/ocr")


__all__ = ["logger", "setup_logger"]
