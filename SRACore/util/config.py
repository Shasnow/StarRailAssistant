import json
import os
from typing import Any

from SRACore.util.const import ApplicationDataPath
from SRACore.util.logger import logger

version = 1


class ConfigManager:
    """
    管理单个账号的配置文件，支持加载、保存、切换配置。
    """
    instance = None

    def __init__(self, current_name: str):
        """
        初始化配置管理器。
        :param current_name: 当前配置的名称。
        """
        self.current_name = current_name
        self._config: dict[str, Any] = {}
        # 确保配置目录存在
        os.makedirs('data', exist_ok=True)
        self.load(current_name)
        self._config.setdefault('name', current_name)
        ConfigManager.instance = self

    def load(self, name: str) -> None:
        """
        加载指定名称的配置文件。
        失败时使用空配置。
        :param name: 配置名称
        例如，如果name为"Default"，则加载文件data/config_Default.json。
        如果文件不存在或无法解析，将使用空配置。
        :return: None
        """
        try:
            with open(f'data/config_{name}.json', 'r', encoding='utf-8') as f:
                self._config = json.load(f)
                self._config['name'] = name
            if self._config.get("version", 0) != version:
                self._config = {"version": version, 'name': name}
                logger.debug(f"Config file config_{name}.json version mismatch, using empty config.")
            logger.debug(f"Successfully loaded config file: config_{name}.json")
        except FileNotFoundError:
            self._config = {'version': version, 'name': name}
            logger.debug(f"Config file config_{name}.json not found, using empty config.")
        except json.JSONDecodeError:
            self._config = {'version': version, 'name': name}
            logger.debug(f"Error decoding JSON from config_{name}.json")
        self.current_name = name

    @staticmethod
    def read(name: str) -> dict:
        """
        读取指定名称的配置文件内容并返回。(不改变当前配置)
        失败时返回空配置。
        :param name: 配置名称
        例如，如果name为"Default"，则读取文件data/config_Default.json。
        如果文件不存在或无法解析，将返回空配置。
        :return: 配置内容的副本
        """
        try:
            with open(f'data/config_{name}.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                config['name'] = name
            if config.get("version", 0) != version:
                logger.debug(f"Config file config_{name}.json version mismatch, returning empty config.")
                return {"version": version, 'name': name}
            logger.debug(f"Successfully read config file: config_{name}.json")
            return config
        except FileNotFoundError:
            logger.debug(f"Config file config_{name}.json not found, returning empty config.")
            return {'version': version, 'name': name}
        except json.JSONDecodeError:
            logger.debug(f"Error decoding JSON from config_{name}.json, returning empty config.")
            return {'version': version, 'name': name}

    def get(self, key: str, default=None):
        """
        获取配置项的值。如果配置项不存在，则设置为默认值并返回。
        如果没有提供默认值，则返回None。
        例如，config.get("theme", "light")将返回"theme"配置项的值，如果不存在则设置为"light"并返回。
        如果没有提供默认值，则返回None。
        这确保了配置项始终有一个值。
        :param key: 配置项的键
        :param default: 如果配置项不存在，则使用的默认值
        :return: 配置项的值，如果不存在则返回默认值
        """
        if key not in self._config:
            self.set(key, default)
        return self._config[key]

    @classmethod
    def get_instance(cls):
        """
        获取当前配置管理器实例。
        如果实例不存在，则创建一个新的实例。
        """
        if cls.instance is None:
            cls.instance = ConfigManager("default")
        # 如果实例已存在，直接返回
        return cls.instance

class GlobalConfigManager:
    """
    管理全局配置文件 globals.json，支持加载、保存、获取和设置配置项。
    """
    __instance = None

    def __init__(self):
        self._global_config = {}
        self.load()
        GlobalConfigManager.__instance = self

    def load(self):
        """
        加载全局配置文件 globals.json。
        如果文件不存在或无法解析，将使用默认值。
        如果发生错误（如文件不存在、JSON解析错误或类型错误），将打印错误信息并使用默认值。
        例如，如果文件不存在，将打印"Global config file not found, using default values."。
        如果JSON解析错误，将打印"Error decoding JSON from globals.json, using default values."。
        如果发生类型错误，将打印"Error initializing GlobalConfig, using default values."。
        这些错误处理确保程序在配置文件有问题时仍能正常运行。
        该方法不会抛出异常，而是通过打印错误信息来通知用户
        :return: None
        """
        try:
            with open(ApplicationDataPath / "settings.json", 'r', encoding='utf-8') as f:
                self._global_config = json.load(f)
            if self._global_config.get("version", 0) != version:
                self._global_config = {"version": version}
                logger.debug("Global config file version mismatch, using default values.")
        except FileNotFoundError:
            logger.debug("Global config file not found, using default values.")
        except json.JSONDecodeError:
            logger.debug("Error decoding JSON from settings.json, using default values.")
        except TypeError:
            logger.debug("Error initializing GlobalConfig, using default values.")

    def get(self, key, default=None):
        """
        获取全局配置项的值。如果配置项不存在，则设置为默认值并返回。
        确保配置项始终有一个值。
        如果没有提供默认值，则返回None。
        :param key: 配置项的键
        :param default: 如果配置项不存在，则使用的默认值
        :return: 配置项的值，如果不存在则返回默认值
        """
        if key not in self._global_config:
            self.set(key, default)
        return self._global_config[key]

    def set(self, key, value) -> None:
        """
        设置全局配置项的值。如果配置项不存在，则创建它。
        :param key: 配置项的键
        :param value: 配置项的值
        :return: None
        """
        self._global_config[key] = value

    @classmethod
    def get_instance(cls):
        """
        获取当前全局配置管理器实例。如果不存在，则创建一个新的实例。
        """
        if cls.__instance is None:
            cls.__instance = GlobalConfigManager()
        return cls.__instance
