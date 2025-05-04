import os
import sys

from loguru import logger
logger.remove(0)
if sys.stdout.isatty():
    logger.add(sys.stdout,level=0,format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:8}</level> | <cyan>{module}.{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",colorize=True)
if not os.path.exists("log"):
    os.mkdir("log")
logger.add("log/SRAlog{time:YYYYMMDDHHmmss}.log",level=0,format="{time:YYYY-MM-DD HH:mm:ss} | {level:8} | {module}.{function}:{line} | {message}",colorize=False,retention=7)
__all__ = ["logger"]
