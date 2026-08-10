import importlib
import json
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TYPE_CHECKING, TypeVar, get_args

from loguru import logger
from pydantic import BaseModel

from SRACore.models.app_settings import AppSettings
from SRACore.operators.factory import OperatorFactory, OperatorType
from SRACore.operators.ioperator import IOperator
from SRACore.notification import try_send_notification
from SRACore.localization.resource import Resource
from SRACore.util.const import AppDataDir, ConfigsDir

if TYPE_CHECKING:
    from SRACore.service.setting_service import SettingsService

T = TypeVar('T', bound=BaseModel)


class BaseExtension(ABC, Generic[T]):
    """扩展基类，所有扩展都应继承自此类。

    扩展是可插拔的功能模块，通过 ``extension`` 装饰器注册到注册表，
    并通过 ``ConfigManager`` 加载/保存各自的配置。

    通过泛型参数声明配置类型，例如::

        class HelloExtension(BaseExtension[HelloConfig]):
            def run(self) -> bool: ...

    扩展可通过 ``self.operator`` 执行截图、点击、OCR 等实际操作。
    """

    config: T
    operator: IOperator
    settings: AppSettings
    stop_event: threading.Event | None

    def __init__(self, operator: IOperator, config: T):
        self.operator = operator
        self.settings = operator.settings
        self.stop_event = operator.stop_event
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
    config_cls: type[BaseModel]
    name: str = ""
    description: str = ""


class ExtensionRegistry:
    """扩展注册表，统一管理扩展类与其配置模型"""

    def __init__(self):
        self._storage: dict[str, ExtensionEntry] = {}

    def register(self, extension_id: str, extension_cls: type[BaseExtension],
                 config_cls: type[BaseModel], *, name: str = "", description: str = "") -> None:
        if extension_id in self._storage:
            raise KeyError(f"Extension '{extension_id}' already exists")
        self._storage[extension_id] = ExtensionEntry(
            extension_cls=extension_cls, config_cls=config_cls,
            name=name, description=description,
        )

    def get(self, extension_id: str) -> ExtensionEntry:
        if extension_id not in self._storage:
            raise KeyError(f"Extension '{extension_id}' does not exist")
        return self._storage[extension_id]

    def get_extension_class(self, extension_id: str) -> type[BaseExtension]:
        return self.get(extension_id).extension_cls

    def get_config_class(self, extension_id: str) -> type[BaseModel]:
        return self.get(extension_id).config_cls

    def get_name(self, extension_id: str) -> str:
        return self.get(extension_id).name

    def get_description(self, extension_id: str) -> str:
        return self.get(extension_id).description

    def get_all_config_classes(self) -> dict[str, type[BaseModel]]:
        return {ext_id: entry.config_cls for ext_id, entry in self._storage.items()}

    def get_all_extension_classes(self) -> dict[str, type[BaseExtension]]:
        return {ext_id: entry.extension_cls for ext_id, entry in self._storage.items()}

    def has_id(self, extension_id: str) -> bool:
        return extension_id in self._storage

    def get_schema(self, extension_id: str) -> dict[str, Any] | None:
        entry = self._storage.get(extension_id)
        if entry is None:
            return None
        return entry.config_cls.model_json_schema()

    def get_all_schemas(self) -> dict[str, Any]:
        return {ext_id: entry.config_cls.model_json_schema()
                for ext_id, entry in self._storage.items()}

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
              registry: ExtensionRegistry | None = None):
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
    """
    reg = registry or extension_registry

    def _resolve_config(cls: type[BaseExtension]) -> type[BaseModel]:
        """从泛型基类 ``BaseExtension[Config]`` 中提取配置类。"""
        for base in getattr(cls, '__orig_bases__', []):
            origin = getattr(base, '__origin__', None)
            if origin is None or not issubclass(origin, BaseExtension):
                continue
            args = get_args(base)
            if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
                return args[0]
        raise ValueError(
            f"Extension '{cls.__name__}' must declare its config via generic parameter, "
            f"e.g. `class {cls.__name__}(BaseExtension[YourConfig])`."
        )

    def decorator(cls: type[BaseExtension]) -> type[BaseExtension]:
        if not issubclass(cls, BaseExtension):
            raise TypeError(f"Extension {cls.__name__} must inherit from BaseExtension")
        resolved_config = _resolve_config(cls)
        _id = extension_id if extension_id is not None else cls.__name__.removesuffix("Extension")
        _name = name or cls.__name__
        _desc = description or (cls.__doc__.strip().splitlines()[0] if cls.__doc__ else "")
        reg.register(_id, cls, resolved_config, name=_name, description=_desc)
        logger.debug(f"Registered extension: {_id} -> {cls.__name__} (config={resolved_config.__name__})")
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
        self.load()

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
                logger.info(f"加载扩展配置 {ext_id}...")
                if self._registry.has_id(ext_id):
                    config_cls = self._registry.get_config_class(ext_id)
                    self._configs[ext_id] = config_cls.model_validate(value, by_alias=True)
        except FileNotFoundError:
            logger.debug(f"扩展配置文件 {self.path} 不存在，将使用默认配置")
        except json.JSONDecodeError as e:
            logger.error(f"扩展配置文件 {self.path} 格式错误: {e}")
        except Exception as e:
            logger.error(f"加载扩展配置文件 {self.path} 时发生未知错误: {e}")

        for ext_id in self._registry.get_ids():
            if ext_id not in self._configs:
                logger.debug(f"扩展配置 {ext_id} 未在文件中找到，使用默认值")
                config_cls = self._registry.get_config_class(ext_id)
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

    def ids(self) -> list[str]:
        return list(self._configs.keys())


class ExtensionRunner:
    """扩展运行器，负责实例化扩展并执行其 ``run`` 逻辑。

    与 ``TaskManager`` 类似，每次运行时通过 ``OperatorFactory`` 创建
    ``IOperator`` 实例并注入扩展，使扩展可执行截图、点击、OCR 等实际操作。

    典型用法::

        load_extensions()                          # 动态导入扩展模块
        config_manager = ExtensionConfigManager()
        runner = ExtensionRunner(config_manager, settings_service)
        runner.run("MyExtension")                   # 运行单个扩展
        runner.run_all()                            # 运行所有已注册扩展
    """

    def __init__(self, config_manager: ExtensionConfigManager,
                 settings_service: 'SettingsService',
                 stop_event: threading.Event | None = None,
                 registry: ExtensionRegistry | None = None):
        self._config_manager = config_manager
        self._settings_service = settings_service
        self._stop_event = stop_event
        self._registry = registry or extension_registry

    def _create_operator(self) -> IOperator:
        """根据设置创建 IOperator 实例"""
        settings = self._settings_service.settings
        optype = (OperatorType.Browser
                  if settings.General.isCloudGameEnabled
                  else OperatorType.Local)
        return OperatorFactory.get_operator(optype, settings, self._stop_event)

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
            config = config_cls()
            logger.debug(f"Config for '{extension_id}' not loaded, using default")
        operator = self._create_operator()
        return ext_cls(operator, config)

    def run(self, extension_id: str) -> bool:
        """运行单个扩展，返回是否成功。

        会依次触发 ``on_start`` → ``run`` → ``on_completed`` / ``on_failed`` 回调。
        """
        logger.info(f"[Extension] Running '{extension_id}'...")
        try:
            instance = self.create(extension_id)
        except Exception as e:
            logger.exception(f"Failed to instantiate extension '{extension_id}': {e}")
            return False

        instance.on_start()
        try:
            result = instance.run()
        except Exception as e:
            logger.exception(f"Extension '{extension_id}' crashed: {e}")
            instance.on_failed()
            return False

        if result:
            instance.on_completed()
            logger.info(f"[Extension] '{extension_id}' completed")
        else:
            instance.on_failed()
            logger.warning(f"[Extension] '{extension_id}' returned False")
        return result

    def run_all(self) -> dict[str, bool]:
        """运行所有已注册扩展，返回各扩展的执行结果。

        单个扩展失败不会中断其他扩展的执行。
        """
        results: dict[str, bool] = {}
        for ext_id in self._registry.get_ids():
            results[ext_id] = self.run(ext_id)
        succeeded = sum(1 for v in results.values() if v)
        logger.info(f"[Extension] run_all finished: {succeeded}/{len(results)} succeeded")
        return results

    def run_many(self, ids: list[str]) -> dict[str, bool]:
        """运行指定的多个扩展，返回各扩展的执行结果。"""
        results: dict[str, bool] = {}
        for ext_id in ids:
            if not self._registry.has_id(ext_id):
                logger.warning(f"[Extension] '{ext_id}' is not registered, skipping")
                results[ext_id] = False
                continue
            results[ext_id] = self.run(ext_id)
        return results
