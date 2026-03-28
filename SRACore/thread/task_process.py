# type: ignore
import importlib
from dataclasses import dataclass
from typing import Any

import tomllib

from SRACore.localization import Resource
from SRACore.operators import Operator
from SRACore.task import BaseTask
from SRACore.util import (
    encryption,  # NOQA 有动态用法，确保被打包 # type: ignore
    notify,
    sys_util,  # NOQA 有动态用法，确保被打包 # type: ignore
)
from SRACore.util.data_persister import load_cache, load_config
from SRACore.util.logger import logger, setup_logger


@dataclass
class TaskMeta:
    """任务元信息：存储任务类和固定位置约束"""
    task_class: type
    fixed: str | None = None  # "first" / "last" / None


class TaskManager:
    """
    任务管理器，负责按顺序执行多个任务（如启动游戏、体力刷取等）。
    支持通过配置动态加载任务列表，并处理任务的中断和错误。
    """

    def __init__(self):
        """初始化任务管理器，从 config.toml 加载任务注册表。"""
        self.log_level = "TRACE"
        self.log_queue = None
        self.task_registry: dict[str, TaskMeta] = {}
        with open("SRACore/config.toml", "rb") as f:
            tasks = tomllib.load(f).get("tasks", [])
            for task in tasks:
                main_class = task.get("main")
                module = task.get("module")
                _module = importlib.import_module(module)
                _class = getattr(_module, main_class)
                if not issubclass(_class, BaseTask):
                    raise TypeError(f"Task class {main_class} does not inherit from BaseTask")
                if not callable(getattr(_class, "run", None)):
                    raise TypeError(f"Task class {main_class} does not implement a callable 'run' method")
                self.task_registry[main_class] = TaskMeta(
                    task_class=_class,
                    fixed=task.get("fixed"),
                )
        # 向后兼容：保留 task_list 供旧代码使用
        logger.debug(f"Successfully load task: {list(self.task_registry.keys())}")

    def run(self, *args: Any) -> None:
        """
        进程主循环：
        1. 读取配置列表（单配置或多配置）
        2. 对每个配置加载任务列表并执行
        3. 处理任务中断或失败的情况
        """
        setup_logger(level=self.log_level, queue=self.log_queue)
        logger.debug('[Start]')
        try:
            if len(args)==0:
                # 不指定配置时，加载缓存中的全部配置名称
                config_list = load_cache().get("ConfigNames", [])
            else:
                # 指定配置名称
                config_list = args

            for config_name in config_list:
                logger.info(Resource.task_currentConfig(config_name))

                # 获取当前配置需要执行的任务列表
                tasks_to_run = self.get_tasks(config_name)
                logger.debug(f'tasks_to_run: {tasks_to_run}')
                if not tasks_to_run:
                    logger.warning(Resource.task_noSelectedTasks(config_name))
                    continue

                # 依次执行任务
                for task in tasks_to_run:
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
                logger.info("=" * 50)
            logger.info("All tasks completed.")
            notify.try_send_notification(Resource.task_notificationTitle, Resource.task_notificationMessage)
        except Exception as e:
            # 捕获线程主循环中的异常（如配置加载失败）
            logger.exception(Resource.task_managerCrashed(str(e)))
        finally:
            logger.debug("[Done]")

    def get_tasks(self, config_name: str) -> list[BaseTask]:
        """
        根据配置名称加载配置，并返回需要执行的任务实例列表。

        fixed="first" 的任务固定在最前，fixed="last" 的任务固定在最后。
        配置版本不符（Version < StaticVersion）时由前端丢弃，后端不做迁移。
        """
        # 加载指定配置
        config = load_config(config_name)
        if config is None:
            return []
        print_config = config.copy()
        if "StartGamePassword" in print_config:
            print_config["StartGamePassword"] = "******"
        logger.debug('config: ' + str(print_config))

        task_order = config.get("TaskOrder")
        if not task_order:
            return []

        logger.debug('task_order: ' + str(task_order))

        # 按 fixed 分组
        first_tasks = []
        ordered_tasks = []
        last_tasks = []

        for name in task_order:
            meta = self.task_registry.get(name)
            if meta is None:
                logger.warning(f"未知任务: {name}，跳过")
                continue
            if meta.fixed == "first":
                first_tasks.append(meta.task_class)
            elif meta.fixed == "last":
                last_tasks.append(meta.task_class)
            else:
                ordered_tasks.append(meta.task_class)

        # 拼接：固定头 + 用户排序 + 固定尾
        final_order = first_tasks + ordered_tasks + last_tasks

        operator = Operator()
        return [cls(operator, config) for cls in final_order]

    def run_task(self, task: str, config_name: str | None = None) -> bool:
        """
        根据配置名称和任务名称执行单个任务。

        Args:
            task (str): 任务类名称（如 "StartGameTask"）
            config_name (str | None): 配置名称，为 None 时从缓存读取当前配置

        Returns:
            bool: 任务执行结果（成功返回 True，失败返回 False）
        """
        setup_logger(level=self.log_level, queue=self.log_queue)
        logger.debug('[Start]')
        try:
            if config_name is None:
                # 不指定配置时，使用缓存中的当前配置名称
                config_name = load_cache().get("CurrentConfigName")
            if config_name is None:
                return False
            task_name = str(task)
            logger.debug(f"run single task: config={config_name}, task={task}")
            # 获取任务实例
            task_instance = self.get_task(config_name, task_name)
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
            logger.debug("[Done]")

    def get_task(self, config_name: str, task: str) -> BaseTask | None:
        """
        根据配置名称和任务索引或名称获取单个任务实例。

        Args:
            config_name (str): 配置名称
            task (str): 任务类名称（如 "StartGameTask"）

        Returns:
            BaseTask | None: 任务实例，未找到或配置加载失败时返回 None
        """
        # 从 task_registry 查找任务类
        task_class = None
        meta = self.task_registry.get(task)
        if meta:
            task_class = meta.task_class
        else:
            # 不区分大小写回退查找
            for name, m in self.task_registry.items():
                if name.lower() == task.lower():
                    task_class = m.task_class
                    break
            else:
                try:
                    task_class = importlib.import_module(f"tasks.{task}").__getattribute__(task)
                except (ModuleNotFoundError, AttributeError):
                    return None
        if task_class is None:
            return None
        try:
            # 加载指定配置
            config = load_config(config_name)
            if config is None:
                return None
            print_config = config.copy()
            if "StartGamePassword" in print_config:
                print_config["StartGamePassword"] = "******"
            logger.debug('config: ' + str(print_config))
            # 实例化任务类
            return task_class(Operator(), config)
        except Exception as e:
            logger.error(Resource.task_instantiateFailed(task, f'{e.__class__.__name__}: {e}'))
            return None
