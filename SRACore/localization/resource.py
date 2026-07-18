# -*- coding: utf-8 -*-
################################################################################
## Form generated from reading TOML file 'resource.toml'
##
## Created by: pyl10nc
##
## WARNING! All changes made in this file will be lost when regenerate!
################################################################################

import json
import os


class Localization:
    """Automatically generated localization class."""
    __normalized_data: dict[str, str] = None
    lang: str = "zh-cn"
    __available_languages = ['zh-cn', 'en-us']
    __data_loaded: bool = False

    def __init__(self):
        """Initialize localization data."""
        # Don't load data immediately, wait for first access
        pass

    def __ensure_data_loaded(self):
        """Ensure translation data is loaded (lazy loading)."""
        if not self.__data_loaded:
            self.__load_language_data()
            self.__data_loaded = True

    def __load_language_data(self):
        """Load translation data for the current language."""
        json_path = self.__get_json_path()
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                self.__normalized_data = json.load(f)
        else:
            self.__normalized_data = {}

    def __get_json_path(self) -> str:
        """Get the JSON file path for the current language."""
        base_path = os.path.splitext(os.path.abspath(__file__))[0]
        return f"{base_path}_{self.lang}.json"

    def __getattribute__(self, name: str, /):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self.get_translation(name)

    @property
    def available_languages(self):
        """Get list of available languages."""
        return self.__available_languages

    def set_language(self, lang: str | int):
        """Set the language and mark data as not loaded."""
        if isinstance(lang, int):
            self.lang = self.__available_languages[lang]
        elif isinstance(lang, str):
            lang = lang.strip().lower()
            if lang in self.__available_languages:
                self.lang = lang
            else:
                raise ValueError(f"Language '{lang}' is not available. Available languages: {self.__available_languages}")
        else:
            raise TypeError(f"Invalid language type. Expected str or int, got {type(lang).__name__}")
        self.__data_loaded = False

    def get_translation(self, key: str) -> str:
        """
        Get the translation value for the specified key.
        
        :param key: Flattened translation key (e.g., test.group1.hello)
        :return: Translation value for the target language, or key if not found
        """
        self.__ensure_data_loaded()
        return self.__normalized_data.get(key, key)

    @property
    def cli_noAdminWarning(self) -> str:
        """您没有以管理员权限运行 SRA-cli。某些命令可能无法正常工作。

        From cli.noAdminWarning"""
        return self.get_translation("cli.noAdminWarning")

    def cli_invalidArguments(self, command) -> str:
        """命令 '{command}' 的参数无效。输入 'help {command}' 获取用法说明。

        From cli.invalidArguments"""
        template = self.get_translation("cli.invalidArguments")
        return template.format(command=command)

    @property
    def cli_defaultError(self) -> str:
        """{} 不是一个有效命令、别名、或宏。

        From cli.defaultError"""
        return self.get_translation("cli.defaultError")

    @property
    def cli_run_started(self) -> str:
        """已启动任务执行。

        From cli.run.started"""
        return self.get_translation("cli.run.started")

    @property
    def cli_task_taskAlreadyRunning(self) -> str:
        """任务已在运行中。

        From cli.task.taskAlreadyRunning"""
        return self.get_translation("cli.task.taskAlreadyRunning")

    @property
    def cli_task_requestStop(self) -> str:
        """已请求停止正在运行的任务。

        From cli.task.requestStop"""
        return self.get_translation("cli.task.requestStop")

    @property
    def cli_task_timeout(self) -> str:
        """等待任务完成时超时。

        From cli.task.timeout"""
        return self.get_translation("cli.task.timeout")

    @property
    def cli_task_stopped(self) -> str:
        """所有正在运行的任务已停止。

        From cli.task.stopped"""
        return self.get_translation("cli.task.stopped")

    @property
    def cli_task_notRunning(self) -> str:
        """当前没有任务在运行。

        From cli.task.notRunning"""
        return self.get_translation("cli.task.notRunning")

    @property
    def cli_trigger_alreadyRunning(self) -> str:
        """触发器服务已在运行中。

        From cli.trigger.alreadyRunning"""
        return self.get_translation("cli.trigger.alreadyRunning")

    @property
    def cli_trigger_started(self) -> str:
        """触发器服务已启动。

        From cli.trigger.started"""
        return self.get_translation("cli.trigger.started")

    @property
    def cli_trigger_stopped(self) -> str:
        """触发器服务已停止。

        From cli.trigger.stopped"""
        return self.get_translation("cli.trigger.stopped")

    @property
    def cli_trigger_notRunning(self) -> str:
        """触发器服务未运行。

        From cli.trigger.notRunning"""
        return self.get_translation("cli.trigger.notRunning")

    def cli_trigger_enabled(self, trigger_name) -> str:
        """触发器 '{trigger_name}' 已启用。

        From cli.trigger.enabled"""
        template = self.get_translation("cli.trigger.enabled")
        return template.format(trigger_name=trigger_name)

    def cli_trigger_disabled(self, trigger_name) -> str:
        """触发器 '{trigger_name}' 已禁用。

        From cli.trigger.disabled"""
        template = self.get_translation("cli.trigger.disabled")
        return template.format(trigger_name=trigger_name)

    def cli_trigger_notFound(self, trigger_name) -> str:
        """未找到触发器 '{trigger_name}'。

        From cli.trigger.notFound"""
        template = self.get_translation("cli.trigger.notFound")
        return template.format(trigger_name=trigger_name)

    def cli_trigger_attrNotFound(self, trigger_name, attr) -> str:
        """在触发器 '{trigger_name}' 中未找到属性 '{attr}'。

        From cli.trigger.attrNotFound"""
        template = self.get_translation("cli.trigger.attrNotFound")
        return template.format(trigger_name=trigger_name, attr=attr)

    def cli_trigger_attrSet(self, trigger_name, attr, value) -> str:
        """触发器 '{trigger_name}' 的属性 '{attr}' 已设置为 '{value}'。

        From cli.trigger.attrSet"""
        template = self.get_translation("cli.trigger.attrSet")
        return template.format(trigger_name=trigger_name, attr=attr, value=value)

    def cli_trigger_unknownType(self, type) -> str:
        """未知属性类型: '{type}'，支持: 'int'，'float'，'bool'，'str'。

        From cli.trigger.unknownType"""
        template = self.get_translation("cli.trigger.unknownType")
        return template.format(type=type)

    @property
    def argparse_description(self) -> str:
        """SRA-cli：SRA 命令行工具

        From argparse.description"""
        return self.get_translation("argparse.description")

    @property
    def argparse_epilog(self) -> str:
        """From argparse.epilog"""
        return self.get_translation("argparse.epilog")

    @property
    def argparse_inline_help(self) -> str:
        """内联模式（无命令提示符）

        From argparse.inline_help"""
        return self.get_translation("argparse.inline_help")

    @property
    def argparse_version_help(self) -> str:
        """显示 SRA-cli 的版本并退出。

        From argparse.version_help"""
        return self.get_translation("argparse.version_help")

    @property
    def argparse_log_level_help(self) -> str:
        """设置日志记录级别（默认：TRACE）。

        From argparse.log_level_help"""
        return self.get_translation("argparse.log_level_help")

    @property
    def task_description(self) -> str:
        """任务管理器 - 管理 SRA-cli 的任务。

        From task.description"""
        return self.get_translation("task.description")

    def task_currentConfig(self, config_name) -> str:
        """当前配置：{config_name}

        From task.currentConfig"""
        template = self.get_translation("task.currentConfig")
        return template.format(config_name=config_name)

    def task_noSelectedTasks(self, config_name) -> str:
        """{config_name} 配置中没有选中的任务, 跳过执行。

        From task.noSelectedTasks"""
        template = self.get_translation("task.noSelectedTasks")
        return template.format(config_name=config_name)

    def task_taskFailed(self, name) -> str:
        """任务 '{name}' 失败。停止进一步执行。

        From task.taskFailed"""
        template = self.get_translation("task.taskFailed")
        return template.format(name=name)

    def task_taskCrashed(self, name, error) -> str:
        """任务 '{name}' 因意外错误崩溃：{error}

        From task.taskCrashed"""
        template = self.get_translation("task.taskCrashed")
        return template.format(name=name, error=error)

    def task_taskCompleted(self, name) -> str:
        """任务 '{name}' 已完成。

        From task.taskCompleted"""
        template = self.get_translation("task.taskCompleted")
        return template.format(name=name)

    def task_configCompleted(self, config_name) -> str:
        """配置 '{config_name}' 中的所有任务已完成。

        From task.configCompleted"""
        template = self.get_translation("task.configCompleted")
        return template.format(config_name=config_name)

    @property
    def task_notificationTitle(self) -> str:
        """任务通知

        From task.notificationTitle"""
        return self.get_translation("task.notificationTitle")

    @property
    def task_notificationMessage(self) -> str:
        """您的SRA任务运行完成。

        From task.notificationMessage"""
        return self.get_translation("task.notificationMessage")

    def task_instantiateFailed(self, name, error) -> str:
        """实例化任务 '{name}' 失败：{error}

        From task.instantiateFailed"""
        template = self.get_translation("task.instantiateFailed")
        return template.format(name=name, error=error)

    def task_noSuchTask(self, identifier) -> str:
        """没有此任务：'{identifier}'

        From task.noSuchTask"""
        template = self.get_translation("task.noSuchTask")
        return template.format(identifier=identifier)

    def task_managerCrashed(self, error) -> str:
        """任务管理器因意外错误崩溃：{error}

        From task.managerCrashed"""
        template = self.get_translation("task.managerCrashed")
        return template.format(error=error)

    @property
    def run_description(self) -> str:
        """运行指定配置文件中的所有选中的任务。

        From run.description"""
        return self.get_translation("run.description")

    @property
    def run_configHelp(self) -> str:
        """配置文件名称或路径。

        From run.configHelp"""
        return self.get_translation("run.configHelp")

    @property
    def single_description(self) -> str:
        """运行由其名称或索引指定的单个任务。

        From single.description"""
        return self.get_translation("single.description")

    @property
    def single_taskHelp(self) -> str:
        """要运行的任务的名称或索引。

        From single.taskHelp"""
        return self.get_translation("single.taskHelp")

    @property
    def single_configHelp(self) -> str:
        """配置文件名称或路径。

        From single.configHelp"""
        return self.get_translation("single.configHelp")

    @property
    def stop_description(self) -> str:
        """停止当前运行的任务。

        From stop.description"""
        return self.get_translation("stop.description")

    @property
    def trigger_description(self) -> str:
        """触发器管理器 - 管理 SRA-cli 的触发器。

        From trigger.description"""
        return self.get_translation("trigger.description")

    @property
    def trigger_disable_description(self) -> str:
        """禁用指定触发器。

        From trigger.disable.description"""
        return self.get_translation("trigger.disable.description")

    @property
    def trigger_disable_nameHelp(self) -> str:
        """触发器名称。

        From trigger.disable.nameHelp"""
        return self.get_translation("trigger.disable.nameHelp")

    @property
    def trigger_enable_description(self) -> str:
        """启用指定触发器。

        From trigger.enable.description"""
        return self.get_translation("trigger.enable.description")

    @property
    def trigger_enable_nameHelp(self) -> str:
        """触发器名称。

        From trigger.enable.nameHelp"""
        return self.get_translation("trigger.enable.nameHelp")

    @property
    def trigger_run_description(self) -> str:
        """运行触发器线程。

        From trigger.run.description"""
        return self.get_translation("trigger.run.description")

    @property
    def trigger_stop_description(self) -> str:
        """停止触发器线程。

        From trigger.stop.description"""
        return self.get_translation("trigger.stop.description")

    @property
    def trigger_set_description(self) -> str:
        """设置触发器属性。

        From trigger.set.description"""
        return self.get_translation("trigger.set.description")

    @property
    def trigger_set_nameHelp(self) -> str:
        """触发器名称。

        From trigger.set.nameHelp"""
        return self.get_translation("trigger.set.nameHelp")

    @property
    def trigger_set_attrHelp(self) -> str:
        """属性名称。

        From trigger.set.attrHelp"""
        return self.get_translation("trigger.set.attrHelp")

    @property
    def trigger_set_typeHelp(self) -> str:
        """属性类型。

        From trigger.set.typeHelp"""
        return self.get_translation("trigger.set.typeHelp")

    @property
    def trigger_set_valueHelp(self) -> str:
        """属性值。

        From trigger.set.valueHelp"""
        return self.get_translation("trigger.set.valueHelp")

    def config_fileNotFound(self, path) -> str:
        """找不到文件：'{path}'

        From config.fileNotFound"""
        template = self.get_translation("config.fileNotFound")
        return template.format(path=path)

    def config_parseError(self, path, error) -> str:
        """解析文件 '{path}' 失败：{error}

        From config.parseError"""
        template = self.get_translation("config.parseError")
        return template.format(path=path, error=error)

    def config_exception(self, path, error) -> str:
        """加载文件 '{path}' 时发生错误：{error}

        From config.exception"""
        template = self.get_translation("config.exception")
        return template.format(path=path, error=error)

Resource = Localization()
