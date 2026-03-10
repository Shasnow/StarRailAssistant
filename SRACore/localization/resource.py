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
    __normalized_data: dict[str, str] | None = None
    lang: str = "en-us"
    __available_languages = ['en-us', 'zh-cn']
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
        获取指定键的翻译值。
        
        :param key: 扁平化翻译键（例如 test.group1.hello）
        :return: 目标语言的翻译值，如果没有找到则为键
        """
        self.__ensure_data_loaded()
        if self.__normalized_data is None:
            return key
        return self.__normalized_data.get(key, key)

    def cli_intro(self, version, core) -> str:
        """SRA-cli {version} ({core})\n输入 'help' 或 '?' 来查看命令列表。

        From cli.intro"""
        template = self.get_translation("cli.intro")
        return template.format(version=version, core=core)

    @property
    def cli_noAdminWarning(self) -> str:
        """您没有以管理员权限运行 SRA-cli。某些命令可能无法正常工作。

        From cli.noAdminWarning"""
        return self.get_translation("cli.noAdminWarning")

    def cli_unknownCommand(self, command) -> str:
        """未知命令: '{command}'。输入 'help' 来获取可用命令列表。

        From cli.unknownCommand"""
        template = self.get_translation("cli.unknownCommand")
        return template.format(command=command)

    def cli_invalidArguments(self, command) -> str:
        """命令 '{command}' 的参数无效。输入 'help {command}' 获取用法说明。

        From cli.invalidArguments"""
        template = self.get_translation("cli.invalidArguments")
        return template.format(command=command)

    @property
    def cli_helpTitle(self) -> str:
        """可用命令：

        From cli.helpTitle"""
        return self.get_translation("cli.helpTitle")

    @property
    def cli_helpFooter(self) -> str:
        """\n输入 'help <command>' 来获取特定命令的更多信息。

        From cli.helpFooter"""
        return self.get_translation("cli.helpFooter")

    def cli_help_unknownCommand(self, command) -> str:
        """未知命令: '{command}'。

        From cli.help.unknownCommand"""
        template = self.get_translation("cli.help.unknownCommand")
        return template.format(command=command)

    @property
    def cli_help_EOF(self) -> str:
        """退出 SRA-cli 应用程序。

        From cli.help.EOF"""
        return self.get_translation("cli.help.EOF")

    @property
    def cli_help_help(self) -> str:
        """显示命令的帮助信息。

        From cli.help.help"""
        return self.get_translation("cli.help.help")

    @property
    def cli_help_task(self) -> str:
        """管理 SRA-cli 中的任务。\n用法：\ntask run [<name | path>...]\n运行指定配置文件中的所有选中的任务。\n如果未指定配置文件，则使用缓存中的全部配置文件。\ntask single (taks_name | task_index) [<config_name | config_path>]\n运行由其名称或索引指定的单个任务，无论它是否被选中。\n如果未指定配置文件，则使用缓存中的当前配置文件。\ntask stop     停止所有正在运行的任务。\n

        From cli.help.task"""
        return self.get_translation("cli.help.task")

    @property
    def cli_help_trigger(self) -> str:
        """管理 SRA-cli 中的触发器。\n用法：\n  trigger run                   启动触发器服务。\n  trigger stop                  停止触发器服务。\n  trigger enable <trigger_name>    启用特定触发器。\n  trigger disable <trigger_name>   禁用特定触发器。\n  trigger set-<type> <trigger_name> <property> <value>\n                                更改特定触发器的属性。\n

        From cli.help.trigger"""
        return self.get_translation("cli.help.trigger")

    @property
    def cli_help_run(self) -> str:
        """用法：run [<config_name | config_path>...]\n运行指定配置文件中的所有任务。如果未指定配置文件，则使用缓存中的当前配置文件。\n此命令将阻塞 CLI 直到所有任务完成。\n

        From cli.help.run"""
        return self.get_translation("cli.help.run")

    @property
    def cli_help_single(self) -> str:
        """用法：single (task_name | task_index) [<config_name | config_path>]\n运行由其名称或索引指定的单个任务，无论它是否被选中。如果未指定配置文件，则使用缓存中的当前配置文件。\n此命令将阻塞 CLI 直到任务完成。\n

        From cli.help.single"""
        return self.get_translation("cli.help.single")

    @property
    def cli_help_host(self) -> str:
        """在指定端口启动 WebSocket 服务器

        From cli.help.host"""
        return self.get_translation("cli.help.host")

    @property
    def cli_help_version(self) -> str:
        """显示 SRA-cli 的当前版本。

        From cli.help.version"""
        return self.get_translation("cli.help.version")

    @property
    def cli_help_notify(self) -> str:
        """通知命令 - 支持测试邮件通知

        From cli.help.notify"""
        return self.get_translation("cli.help.notify")

    @property
    def cli_exit_help(self) -> str:
        """退出 SRA-cli 应用程序。

        From cli.exit.help"""
        return self.get_translation("cli.exit.help")

    @property
    def cli_exit_taskTimeout(self) -> str:
        """等待任务停止时超时。强制退出。

        From cli.exit.taskTimeout"""
        return self.get_translation("cli.exit.taskTimeout")

    @property
    def cli_exit_triggerTimeout(self) -> str:
        """等待触发器停止时超时。强制退出。

        From cli.exit.triggerTimeout"""
        return self.get_translation("cli.exit.triggerTimeout")

    @property
    def cli_task_help(self) -> str:
        """管理 SRA-cli 中的任务，输入 'help task' 获取更多信息。

        From cli.task.help"""
        return self.get_translation("cli.task.help")

    @property
    def cli_task_taskAlreadyRunning(self) -> str:
        """任务已在运行中。

        From cli.task.taskAlreadyRunning"""
        return self.get_translation("cli.task.taskAlreadyRunning")

    @property
    def cli_task_interrupted(self) -> str:
        """Task execution interrupted by user.

        From cli.task.interrupted"""
        return self.get_translation("cli.task.interrupted")

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
    def cli_trigger_help(self) -> str:
        """管理 SRA-cli 中的触发器，输入 'help trigger' 获取更多信息。

        From cli.trigger.help"""
        return self.get_translation("cli.trigger.help")

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

    @property
    def cli_trigger_timeout(self) -> str:
        """等待触发器完成时超时。

        From cli.trigger.timeout"""
        return self.get_translation("cli.trigger.timeout")

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
    def cli_run_help(self) -> str:
        """运行指定配置文件中的所有选中的任务，输入 'help run' 获取更多信息。

        From cli.run.help"""
        return self.get_translation("cli.run.help")

    @property
    def cli_run_started(self) -> str:
        """任务执行已开始，CLI 将被阻塞直到所有任务完成。

        From cli.run.started"""
        return self.get_translation("cli.run.started")

    @property
    def cli_run_completed(self) -> str:
        """所有任务已完成。

        From cli.run.completed"""
        return self.get_translation("cli.run.completed")

    @property
    def cli_single_help(self) -> str:
        """运行由其名称或索引指定的单个任务，输入 'help single' 获取更多信息。

        From cli.single.help"""
        return self.get_translation("cli.single.help")

    @property
    def cli_notify_help(self) -> str:
        """管理 SRA-cli 中的通知，输入 'help notify' 获取更多信息。

        From cli.notify.help"""
        return self.get_translation("cli.notify.help")

    @property
    def cli_version_help(self) -> str:
        """显示 SRA-cli 的当前版本。

        From cli.version.help"""
        return self.get_translation("cli.version.help")

    @property
    def cli_host_help(self) -> str:
        """在指定端口启动一个 WebSocket 服务器以进行远程控制。\n\n用法：\n  host <port>  在指定端口启动 WebSocket 服务器。\n  host stop    停止 WebSocket 服务器。\n

        From cli.host.help"""
        return self.get_translation("cli.host.help")

    def cli_host_started(self, port) -> str:
        """WebSocket 服务器已在端口 {port} 启动。

        From cli.host.started"""
        template = self.get_translation("cli.host.started")
        return template.format(port=port)

    def cli_host_invalidPort(self, port) -> str:
        """无效的端口号: {port}。

        From cli.host.invalidPort"""
        template = self.get_translation("cli.host.invalidPort")
        return template.format(port=port)

    @property
    def cli_host_stopped(self) -> str:
        """WebSocket 服务器已停止。

        From cli.host.stopped"""
        return self.get_translation("cli.host.stopped")

    @property
    def cli_host_notRunning(self) -> str:
        """WebSocket 服务器未运行。

        From cli.host.notRunning"""
        return self.get_translation("cli.host.notRunning")

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
    def argparse_host_help(self) -> str:
        """启动 WebSocket 服务器

        From argparse.host_help"""
        return self.get_translation("argparse.host_help")

    @property
    def argparse_port_help(self) -> str:
        """启动 WebSocket 服务器的端口号。

        From argparse.port_help"""
        return self.get_translation("argparse.port_help")

    @property
    def argparse_inline_help(self) -> str:
        """内联模式（无命令提示符）

        From argparse.inline_help"""
        return self.get_translation("argparse.inline_help")

    @property
    def argparse_embed_help(self) -> str:
        """嵌入模式（无命令提示符）

        From argparse.embed_help"""
        return self.get_translation("argparse.embed_help")

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
    def argparse_run_help(self) -> str:
        """运行指定配置文件中的所有选中的任务。输入 'run --help' 获取更多信息。

        From argparse.run_help"""
        return self.get_translation("argparse.run_help")

    @property
    def argparse_run_description(self) -> str:
        """运行指定配置文件中的所有任务。如果未指定配置文件，则使用缓存中的全部配置文件。此命令将阻塞 CLI 直到所有任务完成。

        From argparse.run_description"""
        return self.get_translation("argparse.run_description")

    @property
    def argparse_config_help(self) -> str:
        """配置文件名称或路径。

        From argparse.config_help"""
        return self.get_translation("argparse.config_help")

    @property
    def argparse_single_help(self) -> str:
        """运行由其名称或索引指定的单个任务。输入 'single --help' 获取更多信息。

        From argparse.single_help"""
        return self.get_translation("argparse.single_help")

    @property
    def argparse_single_description(self) -> str:
        """运行由其名称或索引指定的单个任务，无论它是否被选中。如果未指定配置文件，则使用缓存中的当前配置文件。此命令将阻塞 CLI 直到任务完成。

        From argparse.single_description"""
        return self.get_translation("argparse.single_description")

    @property
    def argparse_task_name_help(self) -> str:
        """要运行的任务的名称或索引。

        From argparse.task_name_help"""
        return self.get_translation("argparse.task_name_help")

    @property
    def argparse_once_help(self) -> str:
        """运行命令后退出 SRA-cli。

        From argparse.once_help"""
        return self.get_translation("argparse.once_help")

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

    def task_taskCrashed(self, error, name) -> str:
        """任务 '{name}' 因意外错误崩溃：{error}

        From task.taskCrashed"""
        template = self.get_translation("task.taskCrashed")
        return template.format(error=error, name=name)

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
        """任务完成提醒

        From task.notificationTitle"""
        return self.get_translation("task.notificationTitle")

    @property
    def task_notificationMessage(self) -> str:
        """您的SRA任务运行完成。

        From task.notificationMessage"""
        return self.get_translation("task.notificationMessage")

    def task_instantiateFailed(self, error, name) -> str:
        """实例化任务 '{name}' 失败：{error}

        From task.instantiateFailed"""
        template = self.get_translation("task.instantiateFailed")
        return template.format(error=error, name=name)

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

    def config_fileNotFound(self, path) -> str:
        """找不到文件：'{path}'

        From config.fileNotFound"""
        template = self.get_translation("config.fileNotFound")
        return template.format(path=path)

    def config_parseError(self, error, path) -> str:
        """解析文件 '{path}' 失败：{error}

        From config.parseError"""
        template = self.get_translation("config.parseError")
        return template.format(error=error, path=path)

    def config_exception(self, error, path) -> str:
        """加载文件 '{path}' 时发生错误：{error}

        From config.exception"""
        template = self.get_translation("config.exception")
        return template.format(error=error, path=path)

Resource = Localization()
