import importlib
import json
import threading
from abc import abstractmethod, ABC
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TYPE_CHECKING, TypeVar, get_args

from loguru import logger
from pydantic import BaseModel

from SRACore.localization.resource import Resource
from SRACore.models.app_settings import AppSettings
from SRACore.notification import try_send_notification
from SRACore.operators.factory import OperatorFactory, OperatorType
from SRACore.operators.ioperator import IOperator
from SRACore.task import Executable
from SRACore.thread.runner import Runner
from SRACore.util.const import AppDataDir, ConfigsDir
from SRACore.util.errors import ThreadStoppedError

if TYPE_CHECKING:
    from SRACore.service.setting_service import SettingsService

T = TypeVar('T', bound=BaseModel)


class BaseExtension(Executable, Generic[T], ABC):
    """扩展基类，所有扩展都应继承自此类。

    扩展是可插拔的功能模块，通过 ``extension`` 装饰器注册到注册表，
    并通过 ``ConfigManager`` 加载/保存各自的配置。

    通过泛型参数声明配置类型，例如::

        class HelloExtension(BaseExtension[HelloConfig]):
            def run(self) -> bool: ...

    也可不声明配置类型，此时 ``self.config`` 为 ``None``::

        class SimpleExtension(BaseExtension):
            def run(self) -> bool: ...

    扩展可通过 ``self.operator`` 执行截图、点击、OCR 等实际操作。
    """

    config: T | None = None
    operator: IOperator
    settings: AppSettings

    def __init__(self, operator: IOperator, config: T | None = None):
        super().__init__(operator)
        self.config = config
        self.__post_init__()

    def __post_init__(self) -> None:
        """子类可重写此方法以进行额外初始化"""
        pass

    @abstractmethod
    def run(self) -> bool:
        """执行扩展逻辑，返回是否成功"""
        ...

    def on_start(self) -> None:
        """扩展开始执行前的回调（可选重写）"""
        pass

    def on_completed(self) -> None:
        """扩展执行完成后的回调（可选重写）"""
        pass

    def on_failed(self) -> None:
        """扩展执行失败后的回调（可选重写）"""
        pass

    def send_notification(self, message: str, result: str, image=None) -> None:
        """发送通知，与 BaseTask.send_notification 行为一致。"""
        try_send_notification(
            self.settings.Notification,
            Resource.task_notificationTitle,
            message,
            result=result,
            image=image
        )

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


@dataclass
class ExtensionEntry:
    """注册表中单个扩展的完整元数据。"""
    extension_cls: type[BaseExtension]
    config_cls: type[BaseModel] | None = None
    name: str = ""
    description: str = ""
    is_background: bool = False


class ExtensionRegistry:
    """扩展注册表，统一管理扩展类与其配置模型"""

    def __init__(self):
        self._storage: dict[str, ExtensionEntry] = {}

    def register(self, extension_id: str, extension_cls: type[BaseExtension],
                 config_cls: type[BaseModel] | None = None, *, name: str = "", description: str = "",
                 is_background: bool = False) -> None:
        if extension_id in self._storage:
            raise KeyError(f"Extension '{extension_id}' already exists")
        self._storage[extension_id] = ExtensionEntry(
            extension_cls=extension_cls, config_cls=config_cls,
            name=name, description=description, is_background=is_background,
        )

    def get(self, extension_id: str) -> ExtensionEntry:
        if extension_id not in self._storage:
            raise KeyError(f"Extension '{extension_id}' does not exist")
        return self._storage[extension_id]

    def get_extension_class(self, extension_id: str) -> type[BaseExtension]:
        return self.get(extension_id).extension_cls

    def get_config_class(self, extension_id: str) -> type[BaseModel] | None:
        return self.get(extension_id).config_cls

    def get_name(self, extension_id: str) -> str:
        return self.get(extension_id).name

    def get_description(self, extension_id: str) -> str:
        return self.get(extension_id).description

    def is_background(self, extension_id: str) -> bool:
        return self.get(extension_id).is_background

    def get_background_ids(self) -> list[str]:
        return [ext_id for ext_id, entry in self._storage.items() if entry.is_background]

    def get_all_config_classes(self) -> dict[str, type[BaseModel]]:
        return {ext_id: entry.config_cls for ext_id, entry in self._storage.items()
                if entry.config_cls is not None}

    def get_all_extension_classes(self) -> dict[str, type[BaseExtension]]:
        return {ext_id: entry.extension_cls for ext_id, entry in self._storage.items()}

    def has_id(self, extension_id: str) -> bool:
        return extension_id in self._storage

    def get_schema(self, extension_id: str) -> dict[str, Any] | None:
        entry = self._storage.get(extension_id)
        if entry is None or entry.config_cls is None:
            return None
        return entry.config_cls.model_json_schema()

    def get_all_schemas(self) -> dict[str, Any]:
        return {ext_id: entry.config_cls.model_json_schema()
                for ext_id, entry in self._storage.items()
                if entry.config_cls is not None}

    def get_ids(self) -> list[str]:
        return list(self._storage.keys())


extension_registry = ExtensionRegistry()


def load_extensions(package: str = "extensions") -> None:
    """动态导入指定目录下的所有扩展模块。

    与 ``dynamic_import("tasks")`` 行为一致：扫描 ``package`` 目录下的所有
    ``.py`` 文件（不含 ``__init__``），通过 ``importlib.import_module`` 导入，
    触发模块顶层的 ``@extension`` 装饰器完成注册。

    Args:
        package: 扩展模块所在目录名，默认为 ``"extensions"``。
    """
    try:
        pkg_path = Path(package)
        if not pkg_path.is_dir():
            logger.debug(f"Extensions directory '{package}' not found, skipping")
            return
        for file in pkg_path.glob("*.py"):
            if file.stem == "__init__":
                continue
            try:
                importlib.import_module(f"{package}.{file.stem}")
            except Exception as e:
                logger.exception(f"Failed to import extension module '{file.stem}': {e}")
        logger.info(f"Loaded {len(extension_registry.get_ids())} extension(s): "
                    f"{extension_registry.get_ids()}")
    except Exception as e:
        logger.exception(f"Error loading extensions: {e}")


def extension(_cls: type[BaseExtension] | None = None, *, extension_id: str | None = None,
              name: str | None = None, description: str | None = None,
              background: bool = False, registry: ExtensionRegistry | None = None):
    """扩展注册装饰器，将扩展类及其配置模型注册到注册表中。

    配置模型通过泛型参数声明::

        @extension(name="问候", description="简单的问候示例")
        class HelloExtension(BaseExtension[HelloConfig]):
            def run(self) -> bool: ...

    Args:
        _cls: 被装饰的扩展类（无需手动传入）。
        extension_id: 注册标识，默认根据类名自动生成（去除 ``Extension`` 后缀）。
        name: 展示名称，默认使用类名。
        description: 扩展描述，默认使用类 docstring 首行。
        registry: 目标注册表，默认使用全局 ``extension_registry``。
        background: 是否为后台扩展。
    """
    reg = registry or extension_registry

    def _resolve_config(cls: type[BaseExtension]) -> type[BaseModel] | None:
        """从泛型基类 ``BaseExtension[Config]`` 中提取配置类，无泛型参数则返回 None。"""
        for base in getattr(cls, '__orig_bases__', []):
            origin: type | None = getattr(base, '__origin__', None)
            if origin is None or not issubclass(origin, BaseExtension):
                continue
            args = get_args(base)
            if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
                return args[0]
        return None

    def decorator(cls: type[BaseExtension]) -> type[BaseExtension]:
        if not issubclass(cls, BaseExtension):
            raise TypeError(f"Extension {cls.__name__} must inherit from BaseExtension")
        resolved_config = _resolve_config(cls)
        _id = extension_id if extension_id is not None else cls.__name__.removesuffix("Extension")
        _name = name or cls.__name__
        _desc = description or (cls.__doc__.strip().splitlines()[0] if cls.__doc__ else "")
        reg.register(_id, cls, resolved_config, name=_name, description=_desc,
                    is_background=background)
        _config_name = resolved_config.__name__ if resolved_config else "None"
        logger.debug(f"Registered extension: {_id} -> {cls.__name__} "
                     f"(config={_config_name}, background={background})")
        return cls

    if _cls is None:
        return decorator
    return decorator(_cls)


class ExtensionConfigManager:
    """扩展配置管理器，负责从文件加载/保存各扩展的配置实例"""

    DEFAULT_PATH = AppDataDir / "extensions.json"

    def __init__(self, registry: ExtensionRegistry | None = None):
        self.name: str = ""
        self.version: int = 4
        self._configs: dict[str, BaseModel] = {}
        self.path: str | Path = self.DEFAULT_PATH
        self._registry = registry or extension_registry
        self._extension_config_changed_callback: Callable[[str], None] | None = None
        self.load()

    def set_extension_config_changed_callback(self, callback: Callable[[str], None]) -> None:
        """设置扩展配置变更回调函数，当某个扩展的配置被修改时调用。

        Args:
            callback: 回调函数，接收一个参数：扩展标识。
        """
        self._extension_config_changed_callback = callback

    def load(self, name: str | None = None) -> None:
        try:
            if name is None:
                self.path = self.DEFAULT_PATH
            elif ".json" in name:
                self.path = name.replace('\"', '')
            else:
                self.path = ConfigsDir / f'{name}.json'
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.name = data.get("name", name or "extensions")
            for ext_id, value in data.items():
                if ext_id in ("name", "version"):
                    continue
                if not self._registry.has_id(ext_id):
                    continue
                config_cls = self._registry.get_config_class(ext_id)
                if config_cls is None:
                    continue
                logger.info(f"加载扩展配置 {ext_id}...")
                self._configs[ext_id] = config_cls.model_validate(value, by_alias=True)
        except FileNotFoundError:
            logger.debug(f"扩展配置文件 {self.path} 不存在，将使用默认配置")
        except json.JSONDecodeError as e:
            logger.error(f"扩展配置文件 {self.path} 格式错误: {e}")
        except Exception as e:
            logger.error(f"加载扩展配置文件 {self.path} 时发生未知错误: {e}")

        for ext_id in self._registry.get_ids():
            if ext_id not in self._configs:
                config_cls = self._registry.get_config_class(ext_id)
                if config_cls is None:
                    continue
                logger.debug(f"扩展配置 {ext_id} 未在文件中找到，使用默认值")
                self._configs[ext_id] = config_cls()

    def save(self) -> None:
        data: dict[str, Any] = {"name": self.name, "version": self.version}
        for ext_id, model in self._configs.items():
            data[ext_id] = model.model_dump(by_alias=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_required(self, extension_id: str) -> BaseModel:
        if extension_id not in self._configs:
            raise KeyError(f"Extension config '{extension_id}' does not exist")
        return self._configs[extension_id]

    def get(self, extension_id: str) -> BaseModel | None:
        return self._configs.get(extension_id, None)

    def set(self, extension_id: str, config: BaseModel) -> None:
        if not self._registry.has_id(extension_id):
            raise KeyError(f"Extension '{extension_id}' is not registered")
        self._configs[extension_id] = config
        if self._extension_config_changed_callback is not None:
            self._extension_config_changed_callback(extension_id)

    def ids(self) -> list[str]:
        return list(self._configs.keys())


class ExtensionRunner(Runner):
    """扩展运行器，负责实例化扩展并执行其 ``run`` 逻辑。

    继承 ``Runner``，与 ``TaskManager`` 共享单线程互斥模型——同一时刻
    最多只有一个扩展或任务在运行。

    典型用法::

        load_extensions()                          # 动态导入扩展模块
        config_manager = ExtensionConfigManager()
        runner = ExtensionRunner(config_manager, settings_service)
        runner.run_in_thread("MyExtension")        # 运行单个扩展（后台线程）
    """

    def __init__(self, config_manager: ExtensionConfigManager,
                 settings_service: 'SettingsService',
                 registry: ExtensionRegistry | None = None):
        super().__init__()
        self._config_manager = config_manager
        self._settings_service = settings_service
        self._registry = registry or extension_registry
        self.extensions: dict[str, BaseExtension] = {}
        self._background_thread: threading.Thread | None = None
        self._background_stop_event = threading.Event()
        self._config_manager.set_extension_config_changed_callback(self.reload_extension)

    def _create_operator(self) -> IOperator:
        """根据设置创建 IOperator 实例"""
        settings = self._settings_service.settings
        optype = (OperatorType.Browser
                  if settings.General.isCloudGameEnabled
                  else OperatorType.Local)
        return OperatorFactory.get_operator(optype, settings, self.stop_event)

    def create(self, extension_id: str) -> BaseExtension:
        """根据标识实例化扩展（不含运行）。

        Args:
            extension_id: 注册时使用的标识。

        Returns:
            扩展实例。

        Raises:
            KeyError: 扩展未注册。
        """
        ext_cls = self._registry.get_extension_class(extension_id)
        config = self._config_manager.get(extension_id)
        if config is None:
            config_cls = self._registry.get_config_class(extension_id)
            if config_cls is not None:
                config = config_cls()
                logger.debug(f"Config for '{extension_id}' not loaded, using default")
        operator = self._create_operator()
        return ext_cls(operator, config)

    def _run_extension(self, ext_id: str):
        """扩展执行逻辑（在线程中运行）"""
        self._set_unit(ext_id)
        self._set_configs([ext_id])
        self._set_progress(0, 1)

        instance = self.create(ext_id)

        instance.on_start()
        try:
            result = instance.run()
            if result:
                instance.on_completed()
                logger.info(f"[Extension] '{ext_id}' completed")
                return True
            else:
                instance.on_failed()
                logger.warning(f"[Extension] '{ext_id}' returned False")
                return False
        except ThreadStoppedError:
            raise
        except Exception:
            instance.on_failed()
            raise

    def run_in_thread(self, extension_id: str) -> bool:
        """在独立线程中运行单个扩展。

        Returns:
            True 表示成功启动，False 表示已有线程在运行。
        """
        if self.is_thread_running():
            return False

        self._reset_info("extension")
        logger.info(f"[Extension] Starting '{extension_id}' in background thread...")
        self.start_thread(self._run_extension, extension_id)
        return True

    def _start_background_loop(self) -> None:
        if self._background_thread is not None and self._background_thread.is_alive():
            return
        self._background_stop_event.clear()
        self._background_thread = threading.Thread(target=self._background_loop, daemon=True)
        # noinspection unresolved-references
        self._background_thread.start()

    def _stop_background_loop(self, timeout: float = 5.0) -> None:
        self._background_stop_event.set()
        thread = self._background_thread
        if thread is None or not thread.is_alive():
            self._background_thread = None
            return
        thread.join(timeout=timeout)
        self._background_thread = None

    def _background_loop(self) -> None:
        """共享后台线程：每 200ms 检查并执行当前启用的后台扩展。"""
        logger.debug("Background extension thread started")
        while not self._background_stop_event.is_set():
            self._background_stop_event.wait(0.5)
            if not self.extensions:
                continue

            for ext_id in list(self.extensions.keys()):
                if self._background_stop_event.is_set():
                    break
                instance = self.extensions.get(ext_id)
                if instance is None:
                    self.extensions.pop(ext_id, None)
                    continue
                try:
                    instance.run()
                except ThreadStoppedError:
                    logger.warning(f"Background extension '{ext_id}' stopped by request")
                    self.stop_extension(ext_id)
                except Exception as e:
                    logger.exception(f"Background extension '{ext_id}' crashed: {e}")
                    self.stop_extension(ext_id)

        logger.debug("Background extension thread stopped")

    def start_extension(self, extension_id: str) -> bool:
        """启动指定后台扩展并加入共享轮询列表。"""
        if not extension_registry.has_id(extension_id):
            logger.error(f"Background extension '{extension_id}' is not registered")
            return False
        if not extension_registry.is_background(extension_id):
            logger.error(f"Extension '{extension_id}' is not a background extension")
            return False
        if extension_id in self.extensions:
            return True

        instance = self.create(extension_id)

        self.extensions[extension_id] = instance
        self._start_background_loop()
        logger.info(f"Background extension '{extension_id}' enabled")
        return True

    def stop_extension(self, extension_id: str, timeout: float = 5.0) -> bool:
        """停止指定后台扩展，并从共享轮询列表中移出/销毁实例。"""
        if extension_id in self.extensions:
            self.extensions.pop(extension_id, None)

        if not self.extensions:
            self._stop_background_loop(timeout=timeout)
            return True

        logger.info(f"Background extension '{extension_id}' stopped")
        return True

    def reload_extension(self, extension_id: str) -> None:
        """重新加载指定后台扩展实例（用于配置更新后）。

        注意：后台扩展使用共享轮询线程，因此配置变更时不应在单个扩展
        重新实例化时停止并重启整个线程；应仅替换当前实例，保留线程
        持续运行，避免无意义的线程重建。
        """
        if extension_id not in extension_registry.get_background_ids():
            return

        if extension_id not in self.extensions:
            return

        try:
            new_instance = self.create(extension_id)
        except Exception:
            logger.exception(f"Failed to reload background extension '{extension_id}'")
            return

        self.extensions[extension_id] = new_instance
        if self._background_thread is None or not self._background_thread.is_alive():
            self._start_background_loop()

        logger.debug(f"Reloaded background extension '{extension_id}'")

