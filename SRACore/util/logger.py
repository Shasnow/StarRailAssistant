import sys

from loguru import logger

# 实例化日志记录器
def setup_logger(path: str = "log/SRA{time:YYYYMMDD}.log"):
    logger.remove()
    if sys.stdout.isatty():
        logger.add(sys.stdout, level=0,
               format="<green>{time:HH:mm:ss}</green>[{thread}] | <level>{level:5}</level> | <cyan>{module}.{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
               colorize=True, enqueue=True)
    else:
        logger.add(sys.stdout, level=0,
                   format="{time:HH:mm:ss}[{thread}] | {level:5} | {message}",
                   colorize=False, enqueue=True)
    logger.add(path, level=0,
           format="{time:YYYY-MM-DD HH:mm:ss} {level:5} {module}.{function}:{line} {message}",
           colorize=False, retention=7, enqueue=True,
           encoding="utf-8")
# 初始化日志
setup_logger()
__all__ = ["logger","setup_logger"]
