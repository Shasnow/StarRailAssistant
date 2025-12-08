import importlib
import os
import sys
import tomllib

from SRACore.util.const import VERSION
from SRACore.util.logger import logger
from SRACore.util.i18n import t

class PluginManager:
    plugin_dir = 'plugins'
    public_main_window = None
    public_instance = None
    plugins = {}  # 用于存储所有插件的插件名和启动函数
    plugin_datas: dict[str, dict[str, str]] = {}
    threads = {}  # 用于存储每个插件的线程实例
    data = {}  # 用于存储每个插件的共享数据

    @classmethod
    def scan_plugins(cls) -> None:
        """扫描插件目录"""
        if not os.path.exists(cls.plugin_dir):
            return

        for plugin_name in os.listdir(cls.plugin_dir):
            plugin_path = os.path.join(cls.plugin_dir, plugin_name)

            if not os.path.isdir(plugin_path):
                continue
            try:
                sys.path.append(f"{os.getcwd()}\\{plugin_path}")
                with open(f"{plugin_path}\\plugin.toml", 'rb') as toml_file:
                    plugin_info = tomllib.load(toml_file)
                    if plugin_info.get('enable', True):
                        cls.plugin_datas[plugin_name] = plugin_info
            except Exception as e:
                logger.warning(t('plugin.load_failed', name=plugin_name, error=e))

    @classmethod
    def load_plugins(cls, period="normal"):
        """
        根据指定的加载时期加载插件。

        此方法遍历所有插件数据，根据插件的加载时期与传入的period参数是否匹配来决定是否加载该插件。
        如果匹配，则尝试加载插件。加载过程中，如果插件没有实现'run'方法，则抛出异常并跳过该插件。
        如果插件定义了UI属性，则将其设置为公共UI。最终将插件的run方法注册到插件字典中。

        Args:
            period (str): 插件的加载时期，默认为"normal"。加载时期与插件配置中的"loadPeriod"字段匹配的插件将被加载。
        """
        # 遍历插件数据字典，根据加载时期筛选并加载插件
        for plugin_name, plugin_info in cls.plugin_datas.items():
            # 检查插件的加载时期是否与当前传入的period参数匹配
            if plugin_info.get("loadPeriod", "normal") != period:
                continue
            if plugin_info.get("SRAversion", "0.0.0") != VERSION:
                logger.warning(t('plugin.version_mismatch', name=plugin_name, 
                                 required=plugin_info.get('SRAversion', '0.0.0'), actual=VERSION))
                continue
            try:
                # 构建插件的完整路径
                plugin_path = os.path.join(cls.plugin_dir, plugin_name)
                # 导入插件模块
                logger.info(t('plugin.importing', path=plugin_path.replace('\\', '.')))
                model = importlib.import_module(plugin_path.replace('\\', '.'))
                # 检查插件是否实现了 'run' 方法
                if not hasattr(model, 'run') and plugin_info.get("loadPeriod") != "late":
                    raise Exception("Plugin does not implement 'run' method and is not a late-load type.")
                # 如果插件定义了UI属性，将其设置为公共UI
                if hasattr(model, 'UI'):
                    model.UI = cls.public_main_window
                if hasattr(model, 'instance'):
                    model.instance = cls.public_instance
                # 将插件的run方法注册到插件字典中，以插件的displayName为键
                cls.plugins[plugin_info.get("displayName", plugin_name)] = model.run
            except Exception as e:
                # 如果加载插件时发生异常，记录警告日志并跳过该插件
                logger.warning(t('plugin.load_failed', name=plugin_name, error=e))
                continue

    @classmethod
    def getPlugins(cls) -> dict:
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


class PluginWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setLayout(QVBoxLayout(self))
        self.setFont(QFont("MicroSoft YaHei", 13))

    def addPlugin(self, name, slot):
        button = QPushButton(name)
        button.clicked.connect(slot)
        self.layout().addWidget(button)
