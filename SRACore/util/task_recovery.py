"""任务失败恢复工具

提供统一的任务失败处理逻辑：
- 检测是否需要重试
- 终止游戏进程
- 等待后重新启动游戏
"""
import time

from SRACore.localization import Resource
from SRACore.models.app_settings import AppSettings
from SRACore.util import sys_util
from SRACore.util.logger import logger

# 游戏进程名
_GAME_PROCESS = "StarRail.exe"


class TaskRecovery:
    """任务失败恢复处理器

    在 TaskManager 中使用，负责：
    1. 判断是否应该重试
    2. 杀死游戏进程、等待、重新启动游戏
    3. 跟踪重试次数
    """

    def __init__(self, settings: AppSettings):
        self._settings = settings
        self._retry_count: int = 0

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def settings(self) -> AppSettings:
        return self._settings

    @settings.setter
    def settings(self, value: AppSettings) -> None:
        self._settings = value

    def reset(self) -> None:
        """重置重试计数器（在新一轮任务执行开始时调用）"""
        self._retry_count = 0

    def should_retry(self) -> bool:
        """判断是否还可以重试"""
        return self._settings.General.isRetryOnTaskFailure and self._retry_count < self._settings.General.maxRetryCount

    def prepare_retry(self) -> bool:
        """准备重试：杀死游戏进程并等待

        Returns:
            True 如果准备好重试，False 如果不应重试
        """
        if not self.should_retry():
            return False

        self._retry_count += 1
        max_retries = self._settings.General.maxRetryCount
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
