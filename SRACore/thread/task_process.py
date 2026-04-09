# type: ignore
import importlib
import threading

import tomllib
from typing import Any

from SRACore.localization import Resource
from SRACore.operators import Operator
from SRACore.task import BaseTask
from SRACore.util import (
    encryption,  # NOQA 有动态用法，确保被打包 # type: ignore
    notify,
    sys_util,  # NOQA 有动态用法，确保被打包 # type: ignore
)
from SRACore.util.data_persister import load_cache, load_config
from SRACore.util.errors import SRAError, ThreadStoppedError
from SRACore.util.logger import logger, setup_logger



# 自定义任务的 ClassName 前缀（与前端保持一致）
_CUSTOM_TASK_PREFIX = "CustomTask_"


def _resolve_custom_task_script_path(entry: dict) -> tuple[str, str] | None:
    """
    从任务条目解析脚本文件路径和类名。
    支持两种方式：
    1. ScriptId + TaskEntry（推荐，从已安装脚本目录加载）
    2. ScriptPath（旧方式，直接指定路径）
    返回 (script_path, class_name) 或 None
    """
    import os
    from SRACore.util.const import AppDataSraDir

    script_id = entry.get("ScriptId", "").strip()
    task_entry = entry.get("TaskEntry", "").strip()
    task_class = entry.get("TaskClassName", "").strip()

    if script_id and task_entry:
        # 新方式：从已安装脚本目录加载
        scripts_dir = AppDataSraDir / "scripts"
        script_path = str(scripts_dir / script_id / task_entry)
        if not os.path.isfile(script_path):
            logger.error(f"脚本文件不存在: {script_path}")
            return None
        return script_path, task_class

    # 旧方式：直接指定路径
    script_path = entry.get("ScriptPath", "").strip()
    if not script_path:
        logger.warning(f"自定义任务 '{entry.get('Name')}' 未配置脚本路径")
        return None
    if not os.path.isfile(script_path):
        logger.error(f"脚本文件不存在: {script_path}")
        return None
    return script_path, task_class


def _load_custom_task(class_name: str, config: dict):
    """
    根据 ClassName 从 config 的 CustomTasks 列表里找到对应条目，
    动态加载脚本文件并返回任务类。
    class_name 格式: CustomTask_{id}
    """
    import importlib.util, os

    task_id = class_name.replace(_CUSTOM_TASK_PREFIX, "", 1)
    custom_tasks = config.get("CustomTasks", [])
    entry = next((t for t in custom_tasks if t.get("Id") == task_id), None)
    if entry is None:
        logger.warning(f"未找到自定义任务条目: id={task_id}")
        return None

    result = _resolve_custom_task_script_path(entry)
    if result is None:
        return None
    script_path, hint_class = result

    try:
        spec = importlib.util.spec_from_file_location("_custom_task_" + task_id, script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 优先用 manifest 里指定的类名
        task_class = getattr(module, hint_class, None) if hint_class else None

        if task_class is None:
            # fallback：文件名转驼峰
            class_guess = os.path.splitext(os.path.basename(script_path))[0]
            class_guess = "".join(w.capitalize() for w in class_guess.split("_"))
            task_class = getattr(module, class_guess, None)

        if task_class is None:
            # fallback：找第一个 BaseTask 子类
            from SRACore.task import BaseTask
            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(obj, type) and issubclass(obj, BaseTask) and obj is not BaseTask:
                    task_class = obj
                    break

        if task_class is None:
            logger.error(f"在脚本 {script_path} 中未找到 BaseTask 子类")
            return None
        return task_class
    except Exception as e:
        logger.exception(f"加载自定义任务脚本失败: {script_path}, {e}")
        return None


# 任务类名 -> settings 中对应的通知配置前缀
_TASK_NOTIFY_KEY_MAP = {
    "StartGameTask":         "StartGameTask",
    "TrailblazePowerTask":   "TrailblazePowerTask",
    "ReceiveRewardsTask":    "ReceiveRewardsTask",
    "CosmicStrifeTask":      "CosmicStrifeTask",
    "MissionAccomplishTask": "MissionAccomplishTask",
}


def _should_notify_task(task_class_name: str, event: str, setting: dict,
                        config: dict | None = None) -> bool:
    """
    判断某个任务在 event（'OnStart' 或 'OnComplete'）时是否应该发送通知。
    内置任务从 settings 中读取，自定义任务从 config.CustomTasks 条目中读取。
    task_class_name 对自定义任务传 'CustomTask_{id}'，对内置任务传类名。
    """
    # 自定义任务：从 config.CustomTasks 条目读取独立开关
    if task_class_name.startswith(_CUSTOM_TASK_PREFIX):
        if config is None:
            return False
        task_id = task_class_name.replace(_CUSTOM_TASK_PREFIX, "", 1)
        custom_tasks = config.get("CustomTasks", [])
        entry = next((t for t in custom_tasks if t.get("Id") == task_id), None)
        if entry is None:
            return False
        field = "NotifyOn" + event  # NotifyOnStart / NotifyOnComplete
        return bool(entry.get(field, False))
    # 内置任务：从 settings 读
    key_prefix = _TASK_NOTIFY_KEY_MAP.get(task_class_name)
    if not key_prefix:
        return False
    field = key_prefix + "Notify" + event   # e.g. StartGameTaskNotifyOnStart
    return bool(setting.get(field, False))

class TaskManager:
    """
    任务管理器线程，负责按顺序执行多个任务（如启动游戏、体力刷取等）。
    支持通过配置动态加载任务列表，并处理任务的中断和错误。
    """

    def __init__(self):
        """
        初始化任务管理器。
        """
        self.log_level = "TRACE"
        self.log_queue = None
        self._stop_event = threading.Event()
        self.task_list: list[type[BaseTask]] = []
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
                self.task_list.append(_class)
        logger.debug(f"Successfully load task: {self.task_list}")

    def request_stop(self) -> None:
        """请求停止当前任务执行。"""
        self._stop_event.set()

    def run(self, *args: Any) -> None:
        """
        进程主循环：
        1. 读取配置列表（单配置或多配置）
        2. 对每个配置加载任务列表并执行
        3. 处理任务中断或失败的情况
        """
        self._stop_event.clear()
        logger.debug('[Start]')
        try:
            if len(args)==0:
                # 不指定配置时，加载缓存中的全部配置名称
                config_list = load_cache().get("ConfigNames", [])
            else:
                # 指定配置名称
                config_list = args

            last_operator = None
            for config_name in config_list:
                logger.info(Resource.task_currentConfig(config_name))

                # 获取当前配置需要执行的任务列表
                tasks_to_run = self.get_tasks(config_name)
                if tasks_to_run:
                    last_operator = tasks_to_run[0].operator
                logger.debug(f'tasks_to_run: {tasks_to_run}')
                if not tasks_to_run:
                    logger.warning(Resource.task_noSelectedTasks(config_name))
                    continue

                # 加载配置（通知判断需要）
                config = load_config(config_name)

                # 依次执行任务
                for task in tasks_to_run:
                    if self._stop_event.is_set():
                        logger.info("用户请求停止，终止后续任务执行")
                        break
                    try:
                        # 运行任务，如果返回 False 表示任务失败
                        logger.debug('running task: ' + str(task))
                        # 任务开始通知
                        _setting = notify._load_settings_for_task_notify()
                        _task_cn = getattr(task, "_custom_class_name", task.__class__.__name__)
                        if _should_notify_task(_task_cn, "OnStart", _setting, config):
                            notify.try_send_notification(
                                Resource.task_notificationTitle,
                                "任务 '" + str(task) + "' 开始执行。",
                                result="success",
                                operator=task.operator
                            )
                        if not task.run():
                            logger.debug('task failed: ' + str(task))
                            logger.error(Resource.task_taskFailed(str(task)))
                            notify.try_send_notification(
                                Resource.task_notificationTitle,
                                Resource.task_taskFailed(str(task)),
                                result="fail",
                                operator=task.operator
                            )
                            return  # 终止当前配置的执行
                        # 任务完成通知
                        _setting = notify._load_settings_for_task_notify()
                        if _should_notify_task(_task_cn, "OnComplete", _setting, config):
                            notify.try_send_notification(
                                Resource.task_notificationTitle,
                                Resource.task_taskCompleted(str(task)),
                                result="success",
                                operator=task.operator
                            )
                    except ThreadStoppedError as e:
                        logger.error(e)
                        break
                    except Exception as e:
                        # 捕获任务执行中的异常（如未处理的错误）
                        logger.exception(Resource.task_taskCrashed(str(task), str(e)))
                        notify.try_send_notification(
                            Resource.task_notificationTitle,
                            Resource.task_taskCrashed(str(task), str(e)),
                            result="fail",
                            operator=task.operator
                        )
                        break
                logger.info(Resource.task_configCompleted(config_name))
                logger.info("=" * 50)
            logger.info("All tasks completed.")
            notify.try_send_notification(
                Resource.task_notificationTitle,
                Resource.task_notificationMessage,
                operator=last_operator
            )
        except Exception as e:
            # 捕获线程主循环中的异常（如配置加载失败）
            logger.exception(Resource.task_managerCrashed(str(e)))
        finally:
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
        print_config = config.copy()
        print_config["StartGamePassword"] = "******"
        logger.debug('config: ' + str(print_config))
        # 优先读取 TaskOrder（新格式），降级兼容 EnabledTasks（旧格式）
        task_order = config.get("TaskOrder")
        task_select = config.get("EnabledTasks")

        tasks = []
        operator = Operator(stop_event=self._stop_event)
        task_class_map = {cls.__name__: cls for cls in self.task_list}
        original_indices = {cls.__name__: i for i, cls in enumerate(self.task_list)}

        if task_order and isinstance(task_order, list):
            logger.debug('task_order: ' + str(task_order))
            for class_name in task_order:
                # 自定义任务：动态加载
                if class_name.startswith(_CUSTOM_TASK_PREFIX):
                    task_class = _load_custom_task(class_name, config)
                    if task_class is None:
                        continue
                    # 检查 IsEnabled
                    task_id = class_name.replace(_CUSTOM_TASK_PREFIX, "", 1)
                    custom_tasks = config.get("CustomTasks", [])
                    entry = next((t for t in custom_tasks if t.get("Id") == task_id), None)
                    if entry and not entry.get("IsEnabled", True):
                        continue
                    try:
                        instance = task_class(operator, config)
                        instance._custom_class_name = class_name  # CustomTask_{id}
                        tasks.append(instance)
                    except Exception as e:
                        logger.exception(Resource.task_instantiateFailed(class_name, str(e)))
                    continue
                # 内置任务
                task_class = task_class_map.get(class_name)
                if task_class is None:
                    logger.warning("TaskOrder 中包含未知任务类名: " + class_name)
                    continue
                orig_idx = original_indices.get(class_name, -1)
                if orig_idx >= 0 and task_select and orig_idx < len(task_select):
                    if not task_select[orig_idx]:
                        continue
                try:
                    tasks.append(task_class(operator, config))
                except Exception as e:
                    logger.exception(Resource.task_instantiateFailed(class_name, str(e)))
        elif task_select:
            logger.debug('task_select (legacy): ' + str(task_select))
            for index, is_select in enumerate(task_select):
                if is_select and index < len(self.task_list):
                    try:
                        tasks.append(self.task_list[index](operator, config))
                    except Exception as e:
                        logger.exception(Resource.task_instantiateFailed(index, str(e)))
        else:
            return []
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
        setup_logger(level=self.log_level, queue=self.log_queue)
        self._stop_event.clear()
        logger.debug('[Start]')
        try:
            if config_name is None:
                # 不指定配置时，使用缓存中的当前配置名称
                config_name = load_cache().get("CurrentConfigName")
            if config_name is None:
                return False
            task_name = str(task)
            logger.debug(f"run single task: config={config_name}, task={task}")
            # 加载配置（自定义任务和通知都需要）
            config = load_config(config_name)
            # 自定义任务：直接动态加载
            if task_name.startswith(_CUSTOM_TASK_PREFIX):
                task_class = _load_custom_task(task_name, config)
                if task_class is None:
                    return False
                operator = Operator(stop_event=self._stop_event)
                task_instance = task_class(operator, config)
            else:
                # 获取任务实例
                task_instance = self.get_task(config_name, task_name)
            if task_instance is None:
                logger.error(Resource.task_noSuchTask(config_name))
                return False
            if self._stop_event.is_set():
                return False
            logger.debug('running task: ' + str(task_instance.__class__.__name__))
            # 单次运行：开始通知
            _setting = notify._load_settings_for_task_notify()
            _notify_cn = task_name if task_name.startswith(_CUSTOM_TASK_PREFIX) else task_instance.__class__.__name__
            if _should_notify_task(_notify_cn, "OnStart", _setting, config):
                notify.try_send_notification(
                    Resource.task_notificationTitle,
                    "任务 '" + str(task_instance) + "' 开始执行。",
                    result="success",
                    operator=task_instance.operator
                )
            # 运行任务
            result = task_instance.run()
            if not result:
                logger.error(Resource.task_taskFailed(str(task_instance)))
                notify.try_send_notification(
                    Resource.task_notificationTitle,
                    Resource.task_taskFailed(str(task_instance)),
                    result="fail",
                    operator=task_instance.operator
                )
            else:
                logger.info(Resource.task_taskCompleted(str(task_instance)))
                # 单次运行：完成通知
                _setting = notify._load_settings_for_task_notify()
                if _should_notify_task(_notify_cn, "OnComplete", _setting, config):
                    notify.try_send_notification(
                        Resource.task_notificationTitle,
                        Resource.task_taskCompleted(str(task_instance)),
                        result="success",
                        operator=task_instance.operator
                    )
            return result
        except ThreadStoppedError as e:
            logger.error(e)
            return False
        except Exception as e:
            logger.exception(Resource.task_taskCrashed(task, str(e)))
            notify.try_send_notification(
                Resource.task_notificationTitle,
                Resource.task_taskCrashed(str(task), str(e)),
                result="fail",
                operator=getattr(locals().get("task_instance", None), "operator", None)
            )
            return False
        finally:
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
            else:
                task_class = importlib.import_module(f"tasks.{task}").__getattribute__(task)
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
            operator = Operator()
            operator.stop_event = self._stop_event
            return task_class(operator, config)
        except Exception as e:
            logger.error(Resource.task_instantiateFailed(task, f'{e.__class__.__name__}: {e}'))
            return None
