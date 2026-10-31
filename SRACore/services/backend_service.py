"""Backend 服务：进程内的重启/停止语义与截图。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from SRACore.util.const import AppDataDir
from SRACore.util.logger import logger

if TYPE_CHECKING:
    from SRACore.services.app_context import AppContext

_SCREENSHOT_PATH = AppDataDir / "cache" / "screenshot.jpg"


class BackendService:
    """进程内后端控制（取代 C# 端对子进程的启停）。"""

    def __init__(self, context: AppContext) -> None:
        self._context = context

    def restart(self) -> None:
        """进程内重启：重新初始化 SRACore（重载任务/扩展、重读设置与缓存）。

        对齐 C# 端重启子进程的效果；``--inline --no-admin`` 等参数在进程内无意义，忽略。
        """
        logger.info("Restarting backend (in-process)...")
        self._context.restart()

    def stop(self) -> None:
        """停止当前运行中的任务/扩展（进程内无子进程可终止）。"""
        logger.info("Stopping backend (in-process): requesting stop of running work...")
        self._context.request_stop_all()

    def screenshot(self) -> tuple[str, bytes]:
        """截取游戏窗口 720p 画面，返回 (提示信息, JPEG 字节)。失败时字节为空。"""
        try:
            _SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
            operator = self._context.create_operator()
            operator.screenshot(
                save_path=str(_SCREENSHOT_PATH),
                background=True,
                resize=(1280, 720),
                jpeg_quality=80,
            )
            data = Path(_SCREENSHOT_PATH).read_bytes()
            return "success", data
        except Exception as e:  # 游戏未运行等
            logger.error(f"Failed to capture screenshot: {e}")
            return str(e), b""