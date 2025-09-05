from PySide6.QtCore import QThread

from SRACore.tasks.BaseTask import BaseTask
from SRACore.tasks.MissionAccomplishTask import MissionAccomplishTask
from SRACore.tasks.ReceiveRewardTask import ReceiveRewardTask
from SRACore.tasks.SimulateUniverseTask import SimulateUniverseTask
from SRACore.tasks.StartGameTask import StartGameTask
from SRACore.tasks.TrailblazePowerTask import TrailblazePowerTask
from SRACore.util.config import GlobalConfigManager, ConfigManager
from SRACore.util.logger import logger


class TaskManager(QThread):
    """
    任务管理器线程，负责按顺序执行多个任务（如启动游戏、体力刷取等）。
    支持通过配置动态加载任务列表，并处理任务的中断和错误。
    """

    def __init__(self, gcm: GlobalConfigManager):
        """
        初始化任务管理器。

        Args:
            gcm (GlobalConfigManager): 全局配置管理器，用于读取任务配置列表。
        """
        super().__init__()
        self.gcm = gcm  # 全局配置管理器
        self.config_manager = ConfigManager.get_instance()  # 单例配置管理器
        self.running_flag = False
        # 预定义的任务类列表，索引对应配置中的 task_select 下标
        # None 表示保留位，暂未分配任务
        self.task_list = [StartGameTask, TrailblazePowerTask, ReceiveRewardTask, SimulateUniverseTask,
                          MissionAccomplishTask]

    def stop(self):
        """
        外部调用的停止方法，设置运行标志为 False 并记录日志。
        注意：此方法可能不会立即终止正在运行的任务（需任务内部支持中断）。
        """
        logger.warning("Task execution interrupted by user.")
        self.running_flag = False
        if self.gcm.get('thread_safety'):
            self.quit()
        else:
            self.terminate()

    def run(self):
        """
        线程主循环：
        1. 读取配置列表（单配置或多配置）
        2. 对每个配置加载任务列表并执行
        3. 处理任务中断或失败的情况
        """
        self.running_flag = True
        try:
            # 根据全局配置决定是执行多配置还是当前配置
            config_list = self.gcm.get('config_list') if self.gcm.get('switch2next') else [
                self.config_manager.current_name]

            for config_name in config_list:
                # 每次循环检查中断标志
                if not self.running_flag:
                    break

                # 获取当前配置需要执行的任务列表
                tasks_to_run = self.get_tasks(config_name)
                if not tasks_to_run:
                    logger.warning(f"No tasks selected in config '{config_name}'. Skipping.")
                    continue

                # 依次执行任务
                for task in tasks_to_run:
                    if not self.running_flag:
                        break
                    try:
                        # 运行任务，如果返回 False 表示任务失败
                        if not task.run():
                            logger.error(f"Task '{task.__class__.__name__}' failed. Stopping further execution.")
                            return  # 终止当前配置的执行
                    except Exception as e:
                        # 捕获任务执行中的异常（如未处理的错误）
                        logger.exception(f"Task '{task.__class__.__name__}' crashed: {str(e)}")
                        break

            logger.info("All tasks completed.")
        except Exception as e:
            # 捕获线程主循环中的异常（如配置加载失败）
            logger.exception(f"TaskManager crashed: {str(e)}")
        finally:
            # 确保标志位被重置，避免僵尸线程
            self.running_flag = False

    def get_tasks(self, config_name) -> list[BaseTask]:
        """
        根据配置名称加载配置，并返回需要执行的任务实例列表。

        Args:
            config_name (str): 配置名称

        Returns:
            List[Executable]: 可执行任务实例列表（已过滤未选中的任务）

        Raises:
            Exception: 如果配置加载或任务实例化失败（异常会被上层捕获）
        """
        # 加载指定配置（注意：可能修改全局状态）
        if self.config_manager.current_name!=config_name:
            self.config_manager.load(config_name)
        # 从配置中读取任务选择列表（如 [True, False, True]）
        task_select = self.config_manager.get('main_window')['task_select']
        tasks = []

        # 遍历 task_select，根据选择状态实例化对应任务
        for index, is_select in enumerate(task_select):
            # 检查：1. 任务被选中 2. 索引在 task_list 范围内 3. 任务类不为 None
            if is_select and index < len(self.task_list) and self.task_list[index] is not None:
                try:
                    # 实例化任务类（假设所有任务类都有无参构造函数）
                    tasks.append(self.task_list[index]())
                except Exception as e:
                    logger.error(f"Failed to instantiate task at index {index}: {str(e)}")
        return tasks
