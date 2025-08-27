import json
import os
from typing import Any

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
            if self._config.get("version", 0) != version:
                self._config = {"version": version}
                logger.debug(f"Config file config_{name}.json version mismatch, using empty config.")
            logger.debug(f"Successfully loaded config file: config_{name}.json")
        except FileNotFoundError:
            self._config = {}
            logger.debug(f"Config file config_{name}.json not found, using empty config.")
        except json.JSONDecodeError:
            self._config = {}
            logger.debug(f"Error decoding JSON from config_{name}.json")
        self.current_name = name

    def set(self, key: str, value) -> None:
        """
        设置配置项的值。如果配置项不存在，则创建它。
        :param key: 配置项的键
        :param value: 配置项的值
        :return: None
        """
        self._config[key] = value

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

    def remove(self, key: str) -> None:
        """
        删除指定的配置项。
        :param key: 配置项的键
        :return: None
        """
        if key in self._config:
            del self._config[key]

    def clear(self) -> None:
        """
        清空当前配置。
        :return: None
        """
        self._config.clear()

    def all(self) -> dict:
        """
        获取当前配置的所有键值对。
        :return: 当前配置的副本
        """
        return self._config.copy()

    def sync(self) -> None:
        """
        将当前配置保存到文件。
        如果文件不存在，将创建一个新的配置文件。
        如果文件已存在，将覆盖它。
        :return: None
        """
        with open(f'data/config_{self.current_name}.json', 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)
        logger.debug(f"Successfully saved config file: config_{self.current_name}.json")

    def switch(self, name) -> None:
        """
        切换到指定名称的配置。
        在切换前会保存当前配置。
        :param name: 要切换到的配置名称
        :return: None
        """
        self.sync()
        self.load(name)

    @classmethod
    def get_instance(cls):
        """
        获取当前配置管理器实例。
        如果实例不存在，则创建一个新的实例。
        :return: ConfigManager实例
        """
        if cls.instance is None:
            raise RuntimeError("ConfigManager instance is not initialized. Please create an instance first.")
        # 如果实例已存在，直接返回
        return cls.instance

    @staticmethod
    def delete(name: str) -> None:
        """
        删除指定名称的配置文件。
        :param name: 要删除的配置名称
        :return: None
        """
        try:
            os.remove(f'data/config_{name}.json')
            logger.debug(f"Successfully deleted config file: config_{name}.json")
        except FileNotFoundError:
            logger.warning(f"Config file config_{name}.json not found, nothing to delete.")
        except Exception as e:
            logger.error(f"Error deleting config file config_{name}.json: {e}")


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
            with open('data/globals.json', 'r', encoding='utf-8') as f:
                self._global_config = json.load(f)
            if self._global_config.get("version", 0) != version:
                self._global_config = {"version": version}
                logger.debug("Global config file version mismatch, using default values.")
        except FileNotFoundError:
            logger.debug("Global config file not found, using default values.")
        except json.JSONDecodeError:
            logger.debug("Error decoding JSON from globals.json, using default values.")
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

    def sync(self) -> None:
        """
        将当前全局配置保存到文件 globals.json。
        如果文件不存在，将创建一个新的配置文件。
        如果文件已存在，将覆盖它。
        :return: None
        """
        with open('data/globals.json', 'w', encoding='utf-8') as f:
            json.dump(self._global_config, f, indent=4, ensure_ascii=False)

    @classmethod
    def get_instance(cls):
        """
        获取当前全局配置管理器实例。
        如果实例不存在，抛出异常。
        :return: GlobalConfigManager实例
        """
        if cls.__instance is None:
            raise RuntimeError("GlobalConfigManager instance is not initialized. Please create an instance first.")
        return cls.__instance
