"""为本次扩展工作线程保留独立的本机日志副本。"""
from contextlib import contextmanager
from datetime import datetime
import os
import platform
import re
import threading
from uuid import uuid4

from loguru import logger
from SRACore.util.errors import ThreadStoppedError

from .paths import default_data_dir


# ssyb：日志接收范围限定为本次扩展的执行线程。
@contextmanager
def isolated_run_log():
    """不改动宿主已有日志；新文件只接收当前工作线程，退出时释放句柄。"""
    sink_id, filename = None, None
    try:
        machine = re.sub(r"[^A-Za-z0-9_.-]", "_", platform.node()).strip("._") or "unknown"
        pid, run_id, worker_id = os.getpid(), uuid4().hex, threading.get_ident()
        directory = default_data_dir() / "logs"
        directory.mkdir(parents=True, exist_ok=True)
        filename = directory / (
            f"currency-wars_{machine}_pid-{pid}_{datetime.now():%Y%m%d_%H%M%S}_run-{run_id}.log")
        sink_id = logger.add(filename, encoding="utf-8", level="DEBUG", enqueue=False,
            filter=lambda record: record["thread"].id == worker_id,
            format=("{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                f"机器={machine} | PID={pid} | 运行={run_id} | "
                "{level} | {name}:{function}:{line} | {message}\n{exception}"),
            backtrace=False, diagnose=False, catch=True)
        logger.info("货币战争优化版独立运行日志已开始。")
    except Exception as error:
        # 日志目录或文件不可写时，继续使用宿主日志，不能阻止游戏流程。
        logger.warning(f"货币战争优化版独立日志不可用，继续使用宿主日志：{type(error).__name__}")
    try:
        yield filename if sink_id is not None else None
    except ThreadStoppedError:
        logger.info("货币战争优化版本次运行已停止。")
        raise
    except Exception:
        # 宿主在线程外层记录结论之前，先为独立文件保留同一异常。
        logger.exception("货币战争优化版本次运行异常终止。")
        raise
    finally:
        if sink_id is not None:
            try:
                logger.remove(sink_id)
            except Exception as error:
                logger.warning(f"货币战争优化版独立日志释放失败：{type(error).__name__}")
