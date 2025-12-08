import importlib
import tomllib

from SRACore.util import sys_util  # NOQA 有动态用法，确保被打包
from SRACore.util import encryption  # NOQA 有动态用法，确保被打包
from SRACore.task import BaseTask
from SRACore.util.config import load_config, load_cache, load_settings
from SRACore.util.logger import logger, setup_logger
from SRACore.util.notify import send_mail_notification, send_windows_notification
from SRACore.util.i18n import t


class TaskManager:
    """
    任务管理器线程，负责按顺序执行多个任务（如启动游戏、体力刷取等）。
    支持通过配置动态加载任务列表，并处理任务的中断和错误。
    """

    def __init__(self):
        """
        初始化任务管理器。
        """
        self.running_flag = False

        self.task_list = []
        with open("SRACore/config.toml", "rb") as f:
            tasks = tomllib.load(f).get("tasks")
            for task in tasks:
                main_class = task.get("main")
                module = task.get("module")
                _module = importlib.import_module(module)
                _class = getattr(_module, main_class)
                if not issubclass(_class, BaseTask):
                    raise TypeError(f"Task class {main_class} does not inherit from BaseTask")
                if not callable(getattr(_class, "run", None)):
                    raise TypeError(f"Task class {main_class} does not implement a callable 'run' method")
                self.task_list.append(_class)
        logger.debug(t('task.load_success', tasks=str(self.task_list)))

    def stop(self):
        """
        外部调用的停止方法，设置运行标志为 False 并记录日志。
        注意：此方法可能不会立即终止正在运行的任务（需任务内部支持中断）。
        """
        logger.warning(t('task.interrupted'))
        self.running_flag = False

    def run(self, *args):
        """
        进程主循环：
        1. 读取配置列表（单配置或多配置）
        2. 对每个配置加载任务列表并执行
        3. 处理任务中断或失败的情况
        """
        setup_logger()
        self.running_flag = True
        logger.debug(t('task.start'))
        try:
            if len(args)==0:
                # 不指定配置时，加载缓存中的全部配置名称
                config_list = load_cache().get("ConfigNames")
            else:
                # 指定配置名称
                config_list = args

            for config_name in config_list:
                logger.info(t('task.current_config', name=config_name))
                # 每次循环检查中断标志
                if not self.running_flag:
                    break

                # 获取当前配置需要执行的任务列表
                tasks_to_run = self.get_tasks(config_name)
                if not tasks_to_run:
                    logger.warning(t('task.no_task_selected', name=config_name))
                    continue

                # 依次执行任务
                for task in tasks_to_run:
                    if not self.running_flag:
                        break
                    try:
                        # 运行任务，如果返回 False 表示任务失败
                        if not task.run():
                            logger.error(t('task.task_failed', name=task.__class__.__name__))
                            return  # 终止当前配置的执行
                    except Exception as e:
                        # 捕获任务执行中的异常（如未处理的错误）
                        logger.exception(t('task.task_crashed', name=task.__class__.__name__, error=str(e)))
                        break
                logger.info(t('task.config_completed', name=config_name))

            logger.info(t('task.all_completed'))
            self.send_notification()
        except Exception as e:
            # 捕获线程主循环中的异常（如配置加载失败）
            logger.exception(t('task.manager_crashed', error=str(e)))
        finally:
            # 确保标志位被重置，避免僵尸线程
            self.running_flag = False
            logger.debug(t('task.done'))

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
        config = load_config(config_name)
        # 从配置中读取任务选择列表（如 [True, False, True]）
        task_select = config.get("EnabledTasks")
        if not task_select:
            return []
        tasks = []

        # 遍历 task_select，根据选择状态实例化对应任务
        for index, is_select in enumerate(task_select):
            # 检查：1. 任务被选中 2. 索引在 task_list 范围内 3. 任务类不为 None
            if is_select and index < len(self.task_list) and self.task_list[index] is not None:
                try:
                    # 实例化任务类
                    tasks.append(self.task_list[index](config))
                except Exception as e:
                    logger.exception(t('task.instantiate_failed', index=index, error=str(e)))
        return tasks

    @staticmethod
    def send_notification():
        setting=load_settings()
        if not setting.get('AllowNotifications', False):
            return
        if setting.get('AllowSystemNotifications', False):
            send_windows_notification(t('task.notification_title'), t('task.notification_body'))
        if setting.get('AllowEmailNotifications', False):
            send_mail_notification(t('task.notification_title'), t('task.notification_body'), setting)