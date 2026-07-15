import dataclasses
import importlib
import os
import threading
import uuid
from typing import Any

from SRACore.localization import Resource
from SRACore.models.app_settings import AppSettings
from SRACore.notification import try_send_notification
from SRACore.operators.factory import OperatorFactory, OperatorType
from SRACore.task import BaseTask, get_task_classes
from SRACore.util import sys_util  # NOQA
from SRACore.util.data_persister import load_cache, load_config
from SRACore.util.errors import ThreadStoppedError
from SRACore.util.logger import logger


@dataclasses.dataclass
class TaskInfo:
    sessionId: str = uuid.uuid4().hex
    pid: int = os.getpid()
    mode: str = "unknown"
    configs: tuple[str, ...] = dataclasses.field(default_factory=tuple)
    task: str = "unknown"
    status: str = "stop"

class TaskManager:
    """
    任务管理器线程，负责按顺序执行多个任务（如启动游戏、体力刷取等）。
    支持通过配置动态加载任务列表，并处理任务的中断和错误。
    """

    def __init__(self, settings: AppSettings):
        """
        初始化任务管理器。
        """
        self.log_queue = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.info = TaskInfo()
        self.task_list: list[type[BaseTask]] = get_task_classes()
        self.settings: AppSettings = settings
        logger.debug(f"Successfully load task: {self.task_list}")

    def request_stop(self) -> None:
        """请求停止当前任务执行。"""
        self._stop_event.set()

    def is_thread_running(self) -> bool:
        """检查任务线程是否正在运行"""
        return self._thread is not None and self._thread.is_alive()

    def _run_target(self, target, *args):
        """线程执行目标函数的包装器"""
        try:
            target(*args)
        except KeyboardInterrupt:
            self.request_stop()

    def start_thread(self, target, *args):
        """启动任务线程"""
        if self.is_thread_running():
            logger.warning("Task thread is already running")
            return False
        self._thread = threading.Thread(
            target=self._run_target,
            daemon=True,
            args=(target, *args)
        )
        self._thread.start()
        logger.info("Task thread started")
        return True

    def stop_thread(self, timeout: float = 30.0):
        """停止任务线程"""
        if not self.is_thread_running():
            return
        logger.warning(Resource.cli_task_requestStop)
        self.request_stop()
        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            logger.warning(Resource.cli_task_timeout)
        else:
            logger.info(Resource.cli_task_stopped)
        self._thread = None

    def run_in_thread(self, *args: Any) -> bool:
        """在线程中运行任务（非阻塞）"""
        if self.is_thread_running():
            logger.warning(Resource.cli_task_taskAlreadyRunning)
            return False
        return self.start_thread(self.run, *args)

    def run_task_in_thread(self, task: int | str, config_name: str | None = None) -> bool:
        """在线程中运行单个任务（非阻塞）"""
        if self.is_thread_running():
            logger.warning(Resource.cli_task_taskAlreadyRunning)
            return False
        return self.start_thread(self.run_task, task, config_name)

    def run(self, *args: str) -> None:
        """
        进程主循环：
        1. 读取配置列表（单配置或多配置）
        2. 对每个配置加载任务列表并执行
        3. 处理任务中断或失败的情况
        """
        self._stop_event.clear()
        logger.debug('[Start]')
        self.info.mode = "run"
        self.info.status = "running"
        try:
            if len(args)==0:
                # 不指定配置时，加载缓存中的全部配置名称
                config_list = load_cache().get("ConfigNames", [])
            else:
                # 指定配置名称
                config_list = args
            self.info.configs = config_list
            last_operator = None
            for config_name in config_list:
                if self._stop_event.is_set():
                    return
                logger.info(Resource.task_currentConfig(config_name))

                # 获取当前配置需要执行的任务列表
                tasks_to_run = self.get_tasks(config_name)
                if tasks_to_run:
                    last_operator = tasks_to_run[0].operator
                logger.debug(f'tasks_to_run: {tasks_to_run}')
                if not tasks_to_run:
                    logger.warning(Resource.task_noSelectedTasks(config_name))
                    continue

                # 依次执行任务
                for task in tasks_to_run:
                    try:
                        # 运行任务，如果返回 False 表示任务失败
                        logger.debug('running task: ' + str(task))
                        self.info.task = str(task)
                        # 任务开始
                        task.start()
                        if not task.run():
                            logger.error(Resource.task_taskFailed(str(task)))
                            task.fail()
                            return  # 终止所有配置的执行
                        # 任务完成
                        task.complete()
                    except ThreadStoppedError as e:
                        logger.error(e)
                        return  # 终止所有配置的执行
                    except Exception as e:
                        # 捕获任务执行中的异常（如未处理的错误）
                        logger.exception(Resource.task_taskCrashed(str(task), str(e)))
                        task.fail()
                        return  # 终止所有配置的执行
                logger.info(Resource.task_configCompleted(config_name))
                logger.info("=" * 50)
            logger.info("All tasks completed.")
            try_send_notification(
                Resource.task_notificationTitle,
                Resource.task_notificationMessage,
                operator=last_operator
            )
        except Exception as e:
            # 捕获线程主循环中的异常（如配置加载失败）
            logger.exception(Resource.task_managerCrashed(str(e)))
        finally:
            final_state = "stopped" if self._stop_event.is_set() else "completed"
            self.info.status = final_state
            logger.debug("[Done]")

    def get_tasks(self, config_name: str) -> list[BaseTask]:
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
        print_config = config.to_dict()
        print_config["startGame"]["password"] = "******"
        print_config["startGame"]["username"] = "******"
        logger.debug('config: ' + str(print_config))
        # 从配置中读取任务选择列表（如 [True, False, True]）
        task_select = [config.StartGame.isEnabled,
                       config.TrailblazePower.isEnabled,
                       config.ReceiveRewards.isEnabled,
                       config.CosmicStrife.isEnabled,
                       config.MissionAccomplished.isEnabled]
        logger.debug('task_select: ' + str(task_select))
        if not task_select:
            return []
        tasks = []
        optype = OperatorType.Browser if self.settings.General.isCloudGameEnabled else OperatorType.Local
        operator = OperatorFactory.get_operator(optype, self._stop_event)

        # 遍历 task_select，根据选择状态实例化对应任务
        for index, is_select in enumerate(task_select):
            # 检查：1. 任务被选中 2. 索引在 task_list 范围内
            if is_select and index < len(self.task_list):
                try:
                    # 实例化任务类
                    tasks.append(self.task_list[index](operator, config))
                except Exception as e:
                    logger.exception(Resource.task_instantiateFailed(index, str(e)))
        return tasks

    def run_task(self, task: int | str, config: str | None = None) -> bool:
        """
        根据配置名称和任务索引或名称执行单个任务。

        Args:
            task (int | str): 任务索引（int）或任务类名称（str）
            config (str): 配置名称

        Returns:
            bool: 任务执行结果（成功返回 True，失败返回 False）

        Raises:
            ValueError: 如果任务未找到或配置加载失败
        """
        logger.debug('[Start]')
        if config is None:
            # 不指定配置时，使用缓存中的当前配置名称
            config = load_cache().get("CurrentConfigName")
        if config is None:
            return False
        task_name = str(task)
        logger.debug(f"run single task: config={config}, task={task}")
        self.info.mode = "single"
        # 获取任务实例
        task_instance = self.get_task(config, task_name)
        if task_instance is None:
            logger.error(Resource.task_noSuchTask(config))
            return False
        self._stop_event.clear()
        try:
            logger.debug('running task: ' + str(task_instance.__class__.__name__))
            # 单次运行：开始通知
            task_instance.start()
            # 运行任务
            result = task_instance.run()
            if not result:
                logger.error(Resource.task_taskFailed(str(task_instance)))
                task_instance.fail()
            else:
                logger.info(Resource.task_taskCompleted(str(task_instance)))
                # 单次运行：完成
                task_instance.complete()
            return result
        except ThreadStoppedError as e:
            logger.error(e)
            return False
        except Exception as e:
            logger.exception(Resource.task_taskCrashed(task, str(e)))
            task_instance.fail()
            return False
        finally:
            final_state = "stopped" if self._stop_event.is_set() else "completed"
            self.info.status = final_state
            logger.debug("[Done]")

    def get_task(self, config: str, task: str) -> BaseTask | None:
        """
        根据配置名称和任务索引或名称获取单个任务实例。

        Args:
            config (str): 配置名称
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
            else:
                task_class = importlib.import_module(f"tasks.{task}").__getattribute__(task)
        if task_class is None:
            return None
        try:
            # 加载指定配置
            config = load_config(config)
            if config is None:
                return None
            print_config = config.to_dict()
            print_config["startGame"]["password"] = "******"
            print_config["startGame"]["username"] = "******"
            logger.debug('config: ' + str(print_config))
            # 实例化任务类
            optype = OperatorType.Browser if self.settings.General.isCloudGameEnabled else OperatorType.Local
            operator = OperatorFactory.get_operator(optype, self._stop_event)
            return task_class(operator, config)
        except Exception as e:
            logger.error(Resource.task_instantiateFailed(task, f'{e.__class__.__name__}: {e}'))
            return None
