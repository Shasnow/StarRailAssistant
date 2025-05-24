import importlib
import os
import sys

from PySide6.QtCore import QThread
from SRACore.utils.Logger import logger

from SRACore.utils.exceptions import InvalidPluginException

class PluginBase(QThread):
    def __init__(self, name: str):
        super().__init__()
        self.name = name


class PluginManager:
    plugin_dir = 'plugins'
    public_ui = None
    public_instance = None
    plugins = {}  # 用于存储所有插件的插件名和启动函数
    threads = {}  # 用于存储每个插件的线程实例
    data = {}  # 用于存储每个插件的共享数据

    @classmethod
    def load_plugins(cls) -> None:
        """扫描插件目录并加载所有插件"""
        if not os.path.exists(cls.plugin_dir):
            return

        for plugin_name in os.listdir(cls.plugin_dir):
            plugin_path = os.path.join(cls.plugin_dir, plugin_name)

            if os.path.isdir(plugin_path):
                try:
                    sys.path.append(f"{os.getcwd()} \ {plugin_path}")
                    model = importlib.import_module(plugin_path.replace('\\', '.'))
                    if not hasattr(model, 'run'):
                        raise InvalidPluginException("Plugin does not implement 'run' method.")
                    if hasattr(model, 'NAME'):
                        plugin_name = model.NAME
                    if not hasattr(model, 'VERSION'):
                        raise InvalidPluginException('Plugin does not has VERSION information.')
                    if not hasattr(model, 'DESCRIPTION'):
                        raise InvalidPluginException('Plugin does not has DESCRIPTION information.')
                    if hasattr(model, 'UI'):
                        model.UI = cls.public_ui
                    cls.plugins[plugin_name] = model.run
                except Exception as e:
                    logger.warning(f"Failed to load plugin '{plugin_name}': {e}")

    @classmethod
    def getPlugins(cls) -> dict[str, PluginBase]:
        return cls.plugins

    @classmethod
    def register(cls, thread: PluginBase) -> None:
        """注册插件线程，如果线程名已存在则抛出异常，防止线程反复启动。"""
        if thread.name in cls.threads:
            raise Exception(f"Thread '{thread.name}' already registered.")
        cls.threads[thread.name] = thread
        thread.finished.connect(lambda: cls.unregister(thread))
        thread.finished.connect(thread.deleteLater)

    @classmethod
    def unregister(cls, thread: PluginBase) -> None:
        """注销插件线程"""
        if thread.name in cls.threads:
            del cls.threads[thread.name]

    @classmethod
    def getPluginsCount(cls) -> int:
        return len(cls.plugins)
