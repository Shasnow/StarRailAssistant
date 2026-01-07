import importlib
import tomllib

from SRACore.localization import Resource
from SRACore.operator import Operator
from SRACore.task import BaseTask
from SRACore.util import encryption  # NOQA 有动态用法，确保被打包
from SRACore.util import notify
from SRACore.util import sys_util  # NOQA 有动态用法，确保被打包
from SRACore.util.config import load_config, load_cache
from SRACore.util.logger import logger, setup_logger


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

        self.task_list: list[type] = []
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
        logger.debug(f"Successfully load task: {self.task_list}")

    def stop(self):
        """
        外部调用的停止方法，设置运行标志为 False 并记录日志。
        注意：此方法可能不会立即终止正在运行的任务（需任务内部支持中断）。
        """
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
        logger.debug('[Start]')
        try:
            if len(args)==0:
                # 不指定配置时，加载缓存中的全部配置名称
                config_list = load_cache().get("ConfigNames")
            else:
                # 指定配置名称
                config_list = args

            for config_name in config_list:
                logger.info(Resource.task_currentConfig(config_name))
                # 每次循环检查中断标志
                if not self.running_flag:
                    break

                # 获取当前配置需要执行的任务列表
                tasks_to_run = self.get_tasks(config_name)
                logger.debug(f'tasks_to_run: {tasks_to_run}')
                if not tasks_to_run:
                    logger.warning(Resource.task_noSelectedTasks(config_name))
                    continue

                # 依次执行任务
                for task in tasks_to_run:
                    if not self.running_flag:
                        break
                    try:
                        # 运行任务，如果返回 False 表示任务失败
                        logger.debug('running task: ' + str(task))
                        if not task.run():
                            logger.debug('task failed: ' + str(task))
                            logger.error(Resource.task_taskFailed(str(task)))
                            return  # 终止当前配置的执行
                    except Exception as e:
                        # 捕获任务执行中的异常（如未处理的错误）
                        logger.exception(Resource.task_taskCrashed(str(task), str(e)))
                        break
                logger.info(Resource.task_configCompleted(config_name))
            logger.info("All tasks completed.")
            notify.try_send_notification(Resource.task_notificationTitle, Resource.task_notificationMessage)
        except Exception as e:
            # 捕获线程主循环中的异常（如配置加载失败）
            logger.exception(Resource.task_managerCrashed(str(e)))
        finally:
            # 确保标志位被重置，避免僵尸线程
            self.running_flag = False
            logger.debug("[Done]")

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
        # 加载指定配置
        config = load_config(config_name)
        if config is None:
            return []
        print_config = config.copy()
        print_config["StartGamePassword"] = "******"
        logger.debug('config: ' + str(print_config))
        # 从配置中读取任务选择列表（如 [True, False, True]）
        task_select = config.get("EnabledTasks")
        logger.debug('task_select: ' + str(task_select))
        if not task_select:
            return []
        tasks = []

        # 遍历 task_select，根据选择状态实例化对应任务
        for index, is_select in enumerate(task_select):
            # 检查：1. 任务被选中 2. 索引在 task_list 范围内 3. 任务类不为 None
            if is_select and index < len(self.task_list) and self.task_list[index] is not None:
                try:
                    # 实例化任务类
                    tasks.append(self.task_list[index](Operator(), config))
                except Exception as e:
                    logger.exception(Resource.task_instantiateFailed(index, str(e)))
        return tasks

    def run_task(self, task: int | str, config_name: str | None = None) -> bool:
        """
        根据配置名称和任务索引或名称执行单个任务。

        Args:
            task (int | str): 任务索引（int）或任务类名称（str）
            config_name (str): 配置名称

        Returns:
            bool: 任务执行结果（成功返回 True，失败返回 False）

        Raises:
            ValueError: 如果任务未找到或配置加载失败
        """
        setup_logger()
        self.running_flag = True
        logger.debug('[Start]')
        try:
            if config_name is None:
                # 不指定配置时，使用缓存中的当前配置名称
                config_name = load_cache().get("CurrentConfigName")
            logger.debug(f"run single task: config={config_name}, task={task}")
            # 获取任务实例
            task_instance = self.get_task(config_name, task)
            if task_instance is None:
                logger.error(Resource.task_noSuchTask(config_name))
                return False
            logger.debug('running task: ' + str(task_instance.__class__.__name__))
            # 运行任务
            result = task_instance.run()
            if not result:
                logger.error(Resource.task_taskFailed(str(task_instance)))
            else:
                logger.info(Resource.task_taskCompleted(str(task_instance)))
            return result
        except Exception as e:
            logger.exception(Resource.task_taskCrashed(task, str(e)))
            return False
        finally:
            self.running_flag = False
            logger.debug("[Done]")

    def get_task(self, config_name: str, task: str) -> BaseTask | None:
        """
        根据配置名称和任务索引或名称获取单个任务实例。

        Args:
            config_name (str): 配置名称
            task ( str): 任务索引或任务类名称（str）

        Returns:
            BaseTask: 任务实例

        Raises:
            ValueError: 如果任务未找到或配置加载失败
        """
        # 根据参数类型获取任务类
        task_class = None
        if task.isdecimal():
            index = int(task)
            if 0 <= index < len(self.task_list):
                task_class = self.task_list[index]
        else:
            for cls in self.task_list:
                if cls.__name__.lower() == task.lower():
                    task_class = cls
                    break
        if task_class is None:
            return None
        try:
            # 加载指定配置
            config = load_config(config_name)
            if config is None:
                return None
            print_config = config.copy()
            print_config["StartGamePassword"] = "******"
            logger.debug('config: ' + str(config))
            # 实例化任务类
            return task_class(Operator(), config)
        except Exception as e:
            logger.error(Resource.task_instantiateFailed(task, f'{e.__class__.__name__}: {e}'))
            return None
