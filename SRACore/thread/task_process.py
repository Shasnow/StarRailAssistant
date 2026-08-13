import importlib
from typing import Any

from SRACore.localization import Resource
from SRACore.notification import try_send_notification
from SRACore.operators.factory import OperatorFactory, OperatorType
from SRACore.service.setting_service import SettingsService
from SRACore.task import BaseTask, get_task_classes, task_registry
from SRACore.thread.runner import Runner
from SRACore.util import sys_util  # NOQA
from SRACore.util.data_persister import load_cache, load_config
from SRACore.util.errors import ThreadStoppedError
from SRACore.util.logger import logger
from SRACore.util.task_recovery import TaskRecovery


class TaskManager(Runner):
    """
    任务管理器，负责按顺序执行多个任务（如启动游戏、体力刷取等）。
    继承 Runner，与 ExtensionRunner 共享单线程互斥模型。
    """

    def __init__(self, settings_service: SettingsService):
        super().__init__()
        self.task_list: list[type[BaseTask]] = get_task_classes()
        self.settings_service: SettingsService = settings_service
        self._recovery = TaskRecovery(settings_service.settings)
        logger.debug(f"Successfully load task: {self.task_list}")

    def run_in_thread(self, *args: Any) -> bool:
        """在线程中运行任务（非阻塞）"""
        self._reset_info("run")
        return self.start_thread(self.run, *args)

    def run_and_wait(self, *args: Any) -> bool:
        """启动任务并阻塞当前调用者，直到执行完成。"""
        self._reset_info("run")
        return self.start_and_wait(self.run, *args)

    def run_task_in_thread(self, task: int | str, config_name: str | None = None) -> bool:
        """在线程中运行单个任务（非阻塞）"""
        self._reset_info("single")
        self._set_unit(str(task))
        return self.start_thread(self.run_task, task, config_name)

    def run_task_and_wait(self, task: int | str, config_name: str | None = None) -> bool:
        """启动单个任务并阻塞当前调用者，直到执行完成。"""
        self._reset_info("single")
        self._set_unit(str(task))
        return self.start_and_wait(self.run_task, task, config_name)

    def run(self, *args: str) -> bool:
        """
        进程主循环：
        1. 读取配置列表（单配置或多配置）
        2. 对每个配置加载任务列表并执行
        3. 处理任务中断或失败的情况
        4. 任务失败时支持自动重试（重启游戏后从当前配置重新开始）
        """
        self.stop_event.clear()
        self._recovery.settings = self.settings_service.settings
        self._recovery.reset()
        self._reset_info("run")

        if len(args)==0:
            # 不指定配置时，加载缓存中的全部配置名称
            config_list = load_cache().get("ConfigNames", [])
        else:
            # 指定配置名称
            config_list = args
        self._set_configs(config_list)
        last_operator = None
        # 支持重试的配置索引，从这里继续执行
        config_start_index = 0
        while config_start_index < len(config_list):
            if self.stop_event.is_set():
                return False
            retry_triggered = False
            for ci in range(config_start_index, len(config_list)):
                config_name = config_list[ci]
                if self.stop_event.is_set():
                    return False
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
                task_failed = False
                for ti, task in enumerate(tasks_to_run):
                    try:
                        # 运行任务，如果返回 False 表示任务失败
                        logger.debug('running task: ' + str(task))
                        self._set_unit(str(task))
                        self._set_progress(ti, len(tasks_to_run))
                        # 任务开始
                        task.on_start()
                        if not task.run():
                            # 如果是用户主动停止，直接返回，不触发重试
                            if self.stop_event.is_set():
                                return False
                            logger.error(Resource.task_taskFailed(str(task)))
                            task.on_failed()
                            # 尝试重试
                            if self._recovery.should_retry():
                                task_failed = True
                                break
                            else:
                                return False
                        # 任务完成
                        task.on_completed()
                    except ThreadStoppedError as e:
                        logger.warning(e)
                        return False
                    except Exception as e:
                        # 如果是用户主动停止，直接返回，不触发重试
                        if self.stop_event.is_set():
                            return False
                        # 捕获任务执行中的异常（如未处理的错误）
                        logger.exception(Resource.task_taskCrashed(str(task), str(e)))
                        task.on_failed()
                        # 尝试重试
                        if self._recovery.should_retry():
                            task_failed = True
                            break
                        else:
                            return False

                if task_failed:
                    # 准备重试：杀死游戏进程并等待
                    if self._recovery.prepare_retry():
                        # 如果在等待期间用户停止了任务，直接返回
                        if self.stop_event.is_set():
                            return False
                        # 重试时需要确保游戏已启动
                        # 如果任务列表中没有 StartGameTask，则先执行它
                        if not any(t.__class__.__name__ == 'StartGameTask' for t in tasks_to_run):
                            logger.info("重试时需要启动游戏，自动执行启动游戏任务")
                            start_game_task = self._create_start_game_task(config_name)
                            if start_game_task:
                                try:
                                    start_game_task.on_start()
                                    if not start_game_task.run():
                                        logger.error("重试时启动游戏失败")
                                        return False
                                    start_game_task.on_completed()
                                except Exception as e:
                                    logger.error(f"重试时启动游戏异常: {e}")
                                    return False
                        logger.info(Resource.task_retryFromConfig(config_name))
                        config_start_index = ci
                        retry_triggered = True
                        break  # 跳出 tasks 循环，重新开始当前配置
                    else:
                        return False

                logger.info(Resource.task_configCompleted(config_name))
                logger.info("=" * 50)

            if not retry_triggered:
                break  # 所有配置执行完毕，退出重试循环

        logger.info("All tasks completed.")
        try_send_notification(
            self.settings_service.settings.Notification,
            Resource.task_notificationTitle,
            Resource.task_notificationMessage,
            image=last_operator.screenshot() if last_operator else None
        )
        return True

    def _create_start_game_task(self, config_name: str) -> BaseTask | None:
        """创建 StartGameTask 实例（用于重试时启动游戏）"""
        config = load_config(config_name)
        if config is None:
            return None
        try:
            optype = OperatorType.Browser if self.settings_service.settings.General.isCloudGameEnabled else OperatorType.Local
            operator = OperatorFactory.get_operator(optype, self.settings_service.settings, self.stop_event)
            # StartGameTask 是第一个任务（index=0）
            if len(self.task_list) > 0:
                return self.task_list[0](operator, config)
        except Exception as e:
            logger.error(f"创建 StartGameTask 失败: {e}")
        return None

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
        optype = OperatorType.Browser if self.settings_service.settings.General.isCloudGameEnabled else OperatorType.Local
        operator = OperatorFactory.get_operator(optype, self.settings_service.settings, self.stop_event)

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
        if config is None:
            # 不指定配置时，使用缓存中的当前配置名称
            config = load_cache().get("CurrentConfigName")
        if config is None:
            return False
        task_name = str(task)
        logger.debug(f"run single task: config={config}, task={task}")
        self._reset_info("single")
        # 获取任务实例
        task_instance = self.get_task(config, task_name)
        self._set_progress(0, 1)
        if task_instance is None:
            logger.error(Resource.task_noSuchTask(config))
            return False
        self.stop_event.clear()
        try:
            logger.debug('running task: ' + str(task_instance.__class__.__name__))
            # 单次运行：开始通知
            task_instance.on_start()
            # 运行任务
            result = task_instance.run()
            if not result:
                logger.error(Resource.task_taskFailed(str(task_instance)))
                task_instance.on_failed()
            else:
                logger.info(Resource.task_taskCompleted(str(task_instance)))
                # 单次运行：完成
                task_instance.on_completed()
            self._set_progress(1, 1)
            return result
        except ThreadStoppedError:
            raise
        except Exception:
            task_instance.on_failed()
            raise

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
            try:
                task_class = task_registry.get_task_class(task)
            except KeyError:
                try:
                    task_class = importlib.import_module(f"tasks.{task}").__getattribute__(task)
                except (ModuleNotFoundError, AttributeError):
                    task_class = None
        if task_class is None:
            return None
        try:
            # 加载指定配置
            config = load_config(config_name)
            if config is None:
                return None
            print_config = config.to_dict()
            print_config["startGame"]["password"] = "******"
            print_config["startGame"]["username"] = "******"
            logger.debug('config: ' + str(print_config))
            # 实例化任务类
            optype = OperatorType.Browser if self.settings_service.settings.General.isCloudGameEnabled else OperatorType.Local
            operator = OperatorFactory.get_operator(optype, self.settings_service.settings, self.stop_event)
            return task_class(operator, config)
        except Exception as e:
            logger.error(Resource.task_instantiateFailed(task, f'{e.__class__.__name__}: {e}'))
            return None
