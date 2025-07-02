import sys

from loguru import logger

logger.remove(0)
if sys.stdout.isatty():
    logger.add(sys.stdout,level=0,format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:7}</level> | <cyan>{module}.{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",colorize=True,enqueue=True)
    logger.success("已连接终端")
    logger.debug(f'启动参数: {sys.argv[1:]}')

logger.add("log/SRAlog{time:YYYYMMDDHHmmss}.log",level=0,format="{time:YYYY-MM-DD HH:mm:ss} | {level:7} | {module}.{function}:{line} | {message}",colorize=False,retention=7,enqueue=True)
__all__ = ["logger"]
