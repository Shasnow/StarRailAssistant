import importlib
import os
import sys

from PySide6.QtCore import QThread

class PluginBase(QThread):
    def __init__(self,name):
        super().__init__()
        self.name=name

class PluginManager:
    plugin_dir = 'plugins'
    public_ui=None
    plugins = {}  # 用于存储所有插件的插件名和启动函数
    threads = {}  # 用于存储每个插件的线程实例
    data = {}  # 用于存储每个插件的共享数据

    @classmethod
    def load_plugins(cls):
        """扫描插件目录并加载所有插件"""
        if not os.path.exists(cls.plugin_dir):
            print(f"Plugin directory '{cls.plugin_dir}' does not exist.")
            return

        for plugin_name in os.listdir(cls.plugin_dir):
            plugin_path = os.path.join(cls.plugin_dir, plugin_name)

            if os.path.isdir(plugin_path):
                try:
                    sys.path.append(f"{os.getcwd()}\{plugin_path}")
                    model=importlib.import_module(plugin_path.replace('\\','.'))
                    if not hasattr(model,'run'):
                        raise Exception('Plugin does not implement run method.')
                    if hasattr(model,'NAME'):
                        plugin_name=model.NAME
                    if not hasattr(model,'VERSION'):
                        raise Exception('Plugin does not implement VERSION.')
                    if not hasattr(model,'DESCRIPTION'):
                        raise Exception('Plugin does not implement DESCRIPTION.')
                    if hasattr(model,'UI'):
                        model.UI=cls.public_ui
                    cls.plugins[plugin_name]=model.run
                except Exception as e:
                    print(f"Failed to load plugin '{plugin_name}': {e}")

    @classmethod
    def getPlugins(cls):
        return cls.plugins

    @classmethod
    def register(cls, thread:PluginBase):
        """注册插件线程"""
        cls.threads[thread.name] = thread
        thread.finished.connect(lambda: cls.unregister(thread))

    @classmethod
    def unregister(cls, thread:PluginBase):
        """注销插件线程"""
        if thread.name in cls.threads:
            del cls.threads[thread.name]

    def get_plugin(self, name):
        """根据插件名称获取插件"""
        return self.plugins.get(name)
