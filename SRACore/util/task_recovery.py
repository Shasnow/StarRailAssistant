"""任务失败恢复工具

提供统一的任务失败处理逻辑：
- 检测是否需要重试
- 终止游戏进程
- 等待后重新启动游戏
"""
import time

from SRACore.localization import Resource
from SRACore.util import sys_util
from SRACore.util.data_persister import load_app_settings
from SRACore.util.logger import logger

# 游戏进程名
_GAME_PROCESS = "StarRail.exe"


class TaskRecovery:
    """任务失败恢复处理器

    在 TaskManager 中使用，负责：
    1. 判断是否应该重试
    2. 杀死游戏进程、等待、重新启动游戏
    3. 跟踪重试次数

    每次判断时从文件重新读取设置，确保前端修改能及时生效。
    """

    def __init__(self):
        self._retry_count: int = 0

    @property
    def retry_count(self) -> int:
        return self._retry_count

    def _load_retry_settings(self) -> tuple[bool, int]:
        """从文件读取最新的重试设置"""
        try:
            settings = load_app_settings()
            return settings.General.isRetryOnTaskFailure, settings.General.maxRetryCount
        except Exception:
            return False, 0

    def reset(self) -> None:
        """重置重试计数器（在新一轮任务执行开始时调用）"""
        self._retry_count = 0

    def should_retry(self) -> bool:
        """判断是否还可以重试（每次从文件读取最新设置）"""
        enabled, max_retries = self._load_retry_settings()
        return enabled and self._retry_count < max_retries

    def prepare_retry(self) -> bool:
        """准备重试：杀死游戏进程并等待

        Returns:
            True 如果准备好重试，False 如果不应重试
        """
        if not self.should_retry():
            return False

        self._retry_count += 1
        _, max_retries = self._load_retry_settings()
        logger.warning(
            Resource.task_retryPreparing(self._retry_count, max_retries)
        )

        # 杀死游戏进程
        self._kill_game()

        # 等待一段时间让进程完全退出
        wait_seconds = 5
        logger.info(Resource.task_waitingForRetry(wait_seconds))
        time.sleep(wait_seconds)

        return True

    @staticmethod
    def _kill_game() -> None:
        """杀死游戏进程"""
        try:
            if sys_util.is_process_running(_GAME_PROCESS):
                logger.info(Resource.task_killingGameProcess)
                sys_util.task_kill(_GAME_PROCESS)
                # 等待进程完全退出
                for _ in range(10):
                    if not sys_util.is_process_running(_GAME_PROCESS):
                        break
                    time.sleep(0.5)
                logger.info(Resource.task_gameProcessKilled)
            else:
                logger.debug("游戏进程未在运行，无需终止")
        except Exception as e:
            logger.warning(f"终止游戏进程时出错: {e}")
