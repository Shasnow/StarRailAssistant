import sys
import functools

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

def _log_entry_exit(func):
    """装饰器：在函数进入和退出时打印日志，方便调试函数调用流程"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f">>> 进入 {func_name}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"<<< 退出 {func_name} (返回: {result})")
            return result
        except Exception as e:
            logger.debug(f"<<< 异常退出 {func_name}: {type(e).__name__}: {e}")
            raise
    return wrapper


def _auto_log_methods(cls):
    """类装饰器：自动给类中所有公开方法添加进入/退出日志"""
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

# 初始化日志
setup_logger()
__all__ = ["logger","setup_logger"]