"""日志流服务：环形缓冲最近日志并提供 SSE 广播。

由 loguru sink 驱动：``AppContext`` 在 ``with_log_stream=True`` 时把
``logger.add(log_stream.sink)`` 注册进日志系统，日志行同时进入环形缓冲
（``recent``）与订阅队列（``subscribe``），不再依赖子进程 stdout/stderr。
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from typing import Any


class LogStreamService:
    """最近日志环形缓冲 + 异步订阅广播。"""

    def __init__(self, max_recent: int = 500) -> None:
        self._recent: deque[str] = deque(maxlen=max_recent)
        self._subscribers: list[asyncio.Queue[str]] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """绑定事件循环，供其他线程中的 sink 调度广播。"""
        self._loop = loop

    def sink(self, message: Any) -> None:
        """loguru sink：记录并广播一行日志（可能由任意线程调用）。"""
        line = str(message).rstrip("\n")
        self._recent.append(line)

        loop = self._loop
        if loop is None or not self._subscribers:
            return
        for queue in list(self._subscribers):
            loop.call_soon_threadsafe(self._offer, queue, line)

    @staticmethod
    def _offer(queue: asyncio.Queue[str], line: str) -> None:
        try:
            queue.put_nowait(line)
        except asyncio.QueueFull:
            pass

    def recent(self, count: int = 100) -> list[str]:
        """获取最近 count 条日志（不足时返回全部）。"""
        if count <= 0:
            return []
        return list(self._recent)[-count:]

    async def subscribe(self) -> AsyncIterator[str]:
        """订阅实时日志流，断开时自动注销订阅者。"""
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            if queue in self._subscribers:
                self._subscribers.remove(queue)