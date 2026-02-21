import sys
import functools

from loguru import logger


# 设置日志记录器
def setup_logger(path: str = "log/SRA{time:YYYYMMDD}.log", level: str = "TRACE", queue = None) -> None:
    logger.remove()
    log_format = "{time:HH:mm:ss}[{process.id}] | {level:5} | {message}"
    if sys.stdout.isatty():
        logger.add(sys.stdout, level=level,
                   format=f"<green>{log_format}</green>",
                   colorize=True, enqueue=True)
    else:
        logger.add(sys.stdout, level=level,
                   format=log_format,
                   colorize=False, enqueue=True)
    logger.add(path, level=level,
               format=log_format,
               colorize=False, retention=7, enqueue=True,
               encoding="utf-8")
    if queue is not None:
        logger.add(queue.put, level=level,
                   format=log_format,
                   colorize=False, enqueue=True)


def _log_entry_exit(func):
    """装饰器：仅在函数异常时打印日志，避免 Enter/Exit 噪音"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Exception in {func_name}: {type(e).__name__}: {e}")
            raise

    return wrapper


def auto_log_methods(cls):
    """类装饰器：自动给类中所有公开方法添加异常日志"""
    for name in dir(cls):
        # if name.startswith('__'):
        # continue
        attr = getattr(cls, name)
        if callable(attr) and hasattr(attr, '__func__'):
            # 跳过继承自父类的方法，只装饰本类定义的方法
            if name in cls.__dict__:
                setattr(cls, name, _log_entry_exit(cls.__dict__[name]))
            else:
                setattr(cls, name, _log_entry_exit(attr))
        elif callable(attr) and name in cls.__dict__:
            setattr(cls, name, _log_entry_exit(attr))
    return cls


__all__ = ["logger", "setup_logger", "auto_log_methods"]
