# -*- coding: utf-8 -*-
################################################################################
## Form generated from reading TOML file 'resources.toml'
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
    __available_languages = ['zh-cn', 'en-us', 'ru-ru']
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
    def cli_task_statusDescription(self) -> str:
        """显示当前任务状态

        From cli.task.statusDescription"""
        return self.get_translation("cli.task.statusDescription")

    @property
    def cli_task_statusTitle(self) -> str:
        """任务状态

        From cli.task.statusTitle"""
        return self.get_translation("cli.task.statusTitle")

    @property
    def cli_task_listDescription(self) -> str:
        """列出所有已注册的任务

        From cli.task.listDescription"""
        return self.get_translation("cli.task.listDescription")

    @property
    def cli_task_listEmpty(self) -> str:
        """没有已注册的任务

        From cli.task.listEmpty"""
        return self.get_translation("cli.task.listEmpty")

    @property
    def cli_task_listHeader(self) -> str:
        """可用任务:

        From cli.task.listHeader"""
        return self.get_translation("cli.task.listHeader")

    def cli_task_listRegistered(self, count) -> str:
        """已注册 {count} 个任务

        From cli.task.listRegistered"""
        template = self.get_translation("cli.task.listRegistered")
        return template.format(count=count)

    @property
    def cli_task_reloadDescription(self) -> str:
        """重新导入任务模块，实现热重载

        From cli.task.reloadDescription"""
        return self.get_translation("cli.task.reloadDescription")

    @property
    def cli_task_reloadBusy(self) -> str:
        """任务线程正在运行中，无法执行重载操作

        From cli.task.reloadBusy"""
        return self.get_translation("cli.task.reloadBusy")

    def cli_task_reloadNotFound(self, path) -> str:
        """任务目录不存在: {path}

        From cli.task.reloadNotFound"""
        template = self.get_translation("cli.task.reloadNotFound")
        return template.format(path=path)

    @property
    def cli_task_reloadEmpty(self) -> str:
        """重载完成，但没有已注册的任务

        From cli.task.reloadEmpty"""
        return self.get_translation("cli.task.reloadEmpty")

    def cli_task_reloadSummary(self, count) -> str:
        """已重载任务，当前共 {count} 个任务

        From cli.task.reloadSummary"""
        template = self.get_translation("cli.task.reloadSummary")
        return template.format(count=count)

    def cli_task_reloadAdded(self, names) -> str:
        """，新增: {names}

        From cli.task.reloadAdded"""
        template = self.get_translation("cli.task.reloadAdded")
        return template.format(names=names)

    def cli_task_reloadRemoved(self, names) -> str:
        """，移除: {names}

        From cli.task.reloadRemoved"""
        template = self.get_translation("cli.task.reloadRemoved")
        return template.format(names=names)

    @property
    def cli_task_listNoDescription(self) -> str:
        """无描述

        From cli.task.listNoDescription"""
        return self.get_translation("cli.task.listNoDescription")

    @property
    def cli_buildInCategory(self) -> str:
        """内置命令

        From cli.buildInCategory"""
        return self.get_translation("cli.buildInCategory")

    def cli_intro(self, version, core) -> str:
        """欢迎使用 SRA-cli（版本 {version}，内核 {core}）。\n输入 'help' 查看命令列表。

        From cli.intro"""
        template = self.get_translation("cli.intro")
        return template.format(version=version, core=core)

    @property
    def cli_extension_description(self) -> str:
        """扩展管理：查看、运行已注册的扩展

        From cli.extension.description"""
        return self.get_translation("cli.extension.description")

    @property
    def cli_extension_listDescription(self) -> str:
        """列出所有已注册的扩展

        From cli.extension.listDescription"""
        return self.get_translation("cli.extension.listDescription")

    @property
    def cli_extension_listEmpty(self) -> str:
        """没有已注册的扩展

        From cli.extension.listEmpty"""
        return self.get_translation("cli.extension.listEmpty")

    @property
    def cli_extension_listHeader(self) -> str:
        """扩展：

        From cli.extension.listHeader"""
        return self.get_translation("cli.extension.listHeader")

    def cli_extension_listRegistered(self, count) -> str:
        """已注册 {count} 个扩展

        From cli.extension.listRegistered"""
        template = self.get_translation("cli.extension.listRegistered")
        return template.format(count=count)

    @property
    def cli_extension_runDescription(self) -> str:
        """按扩展类型自动分发：非后台扩展走共享线程，后台扩展走专用线程

        From cli.extension.runDescription"""
        return self.get_translation("cli.extension.runDescription")

    @property
    def cli_extension_runNameHelp(self) -> str:
        """扩展标识（可通过 extension list 查看）

        From cli.extension.runNameHelp"""
        return self.get_translation("cli.extension.runNameHelp")

    @property
    def cli_extension_runConfigHelp(self) -> str:
        """扩展配置文件名（不带 .json 后缀），不指定则不加载文件配置

        From cli.extension.runConfigHelp"""
        return self.get_translation("cli.extension.runConfigHelp")

    @property
    def cli_extension_schemaDescription(self) -> str:
        """显示扩展的配置 Schema 详情

        From cli.extension.schemaDescription"""
        return self.get_translation("cli.extension.schemaDescription")

    @property
    def cli_extension_schemaNameHelp(self) -> str:
        """扩展键名

        From cli.extension.schemaNameHelp"""
        return self.get_translation("cli.extension.schemaNameHelp")

    def cli_extension_schemaNotFound(self, name) -> str:
        """扩展 '{name}' 不存在

        From cli.extension.schemaNotFound"""
        template = self.get_translation("cli.extension.schemaNotFound")
        return template.format(name=name)

    def cli_extension_schemaTitle(self, name) -> str:
        """扩展 {name} 配置模式

        From cli.extension.schemaTitle"""
        template = self.get_translation("cli.extension.schemaTitle")
        return template.format(name=name)

    @property
    def cli_extension_reloadDescription(self) -> str:
        """重新导入扩展模块（含已导入模块的热重载）

        From cli.extension.reloadDescription"""
        return self.get_translation("cli.extension.reloadDescription")

    @property
    def cli_extension_stopDescription(self) -> str:
        """停止指定的后台扩展或当前正在运行的单次扩展

        From cli.extension.stopDescription"""
        return self.get_translation("cli.extension.stopDescription")

    @property
    def cli_extension_stopNameHelp(self) -> str:
        """扩展标识；若不传则停止当前单次扩展

        From cli.extension.stopNameHelp"""
        return self.get_translation("cli.extension.stopNameHelp")

    @property
    def cli_extension_stopCurrentHelp(self) -> str:
        """停止指定后台扩展或当前正在运行的单次扩展

        From cli.extension.stopCurrentHelp"""
        return self.get_translation("cli.extension.stopCurrentHelp")

    @property
    def cli_extension_stopNone(self) -> str:
        """当前没有正在运行的扩展

        From cli.extension.stopNone"""
        return self.get_translation("cli.extension.stopNone")

    @property
    def cli_extension_stopped(self) -> str:
        """扩展已停止

        From cli.extension.stopped"""
        return self.get_translation("cli.extension.stopped")

    @property
    def cli_extension_statusDescription(self) -> str:
        """显示扩展运行状态

        From cli.extension.statusDescription"""
        return self.get_translation("cli.extension.statusDescription")

    @property
    def cli_extension_configDescription(self) -> str:
        """扩展配置管理

        From cli.extension.configDescription"""
        return self.get_translation("cli.extension.configDescription")

    @property
    def cli_extension_configGetDescription(self) -> str:
        """获取扩展配置

        From cli.extension.configGetDescription"""
        return self.get_translation("cli.extension.configGetDescription")

    @property
    def cli_extension_configGetNameHelp(self) -> str:
        """扩展标识

        From cli.extension.configGetNameHelp"""
        return self.get_translation("cli.extension.configGetNameHelp")

    def cli_extension_configGetTitle(self, name) -> str:
        """扩展 {name} 配置

        From cli.extension.configGetTitle"""
        template = self.get_translation("cli.extension.configGetTitle")
        return template.format(name=name)

    @property
    def cli_extension_configSetDescription(self) -> str:
        """设置扩展配置

        From cli.extension.configSetDescription"""
        return self.get_translation("cli.extension.configSetDescription")

    @property
    def cli_extension_configSetNameHelp(self) -> str:
        """扩展标识

        From cli.extension.configSetNameHelp"""
        return self.get_translation("cli.extension.configSetNameHelp")

    @property
    def cli_extension_configSetJsonHelp(self) -> str:
        """配置 JSON 字符串

        From cli.extension.configSetJsonHelp"""
        return self.get_translation("cli.extension.configSetJsonHelp")

    def cli_extension_configSetJsonError(self, error) -> str:
        """JSON 格式错误: {error}

        From cli.extension.configSetJsonError"""
        template = self.get_translation("cli.extension.configSetJsonError")
        return template.format(error=error)

    @property
    def cli_extension_statusTitle(self) -> str:
        """扩展状态

        From cli.extension.statusTitle"""
        return self.get_translation("cli.extension.statusTitle")

    @property
    def cli_operator_description(self) -> str:
        """统一调用 Operator 方法，与游戏交互

        From cli.operator.description"""
        return self.get_translation("cli.operator.description")

    @property
    def cli_operator_listDescription(self) -> str:
        """列出所有可用的 Operator 方法

        From cli.operator.listDescription"""
        return self.get_translation("cli.operator.listDescription")

    @property
    def cli_operator_listHeader(self) -> str:
        """可用方法:

        From cli.operator.listHeader"""
        return self.get_translation("cli.operator.listHeader")

    @property
    def cli_operator_helpDescription(self) -> str:
        """获取 Operator 方法的详细帮助

        From cli.operator.helpDescription"""
        return self.get_translation("cli.operator.helpDescription")

    @property
    def cli_operator_methodHelp(self) -> str:
        """方法名称

        From cli.operator.methodHelp"""
        return self.get_translation("cli.operator.methodHelp")

    def cli_operator_helpNotFound(self, method) -> str:
        """方法 '{method}' 不存在

        From cli.operator.helpNotFound"""
        template = self.get_translation("cli.operator.helpNotFound")
        return template.format(method=method)

    @property
    def cli_operator_callDescription(self) -> str:
        """调用指定的 Operator 方法

        From cli.operator.callDescription"""
        return self.get_translation("cli.operator.callDescription")

    @property
    def cli_operator_callMethodHelp(self) -> str:
        """方法名称（可通过 operator list 查看）

        From cli.operator.callMethodHelp"""
        return self.get_translation("cli.operator.callMethodHelp")

    @property
    def cli_operator_callParamsHelp(self) -> str:
        """JSON 格式的方法参数

        From cli.operator.callParamsHelp"""
        return self.get_translation("cli.operator.callParamsHelp")

    def cli_operator_callJsonError(self, error) -> str:
        """JSON 解析错误: {error}

        From cli.operator.callJsonError"""
        template = self.get_translation("cli.operator.callJsonError")
        return template.format(error=error)

    @property
    def cli_operator_listTitle(self) -> str:
        """Operator 方法

        From cli.operator.listTitle"""
        return self.get_translation("cli.operator.listTitle")

    @property
    def cli_jsonHelp(self) -> str:
        """以 JSON 格式输出

        From cli.jsonHelp"""
        return self.get_translation("cli.jsonHelp")

    @property
    def cli_argHelp_command(self) -> str:
        """启动后执行的命令

        From cli.argHelp.command"""
        return self.get_translation("cli.argHelp.command")

    @property
    def cli_argHelp_noAdmin(self) -> str:
        """不要求管理员权限

        From cli.argHelp.noAdmin"""
        return self.get_translation("cli.argHelp.noAdmin")

    @property
    def cli_argHelp_subcommand(self) -> str:
        """子命令；输入 '<子命令> --help' 查看详细说明

        From cli.argHelp.subcommand"""
        return self.get_translation("cli.argHelp.subcommand")

    @property
    def cli_argHelp_whereDescription(self) -> str:
        """查找可执行文件或目录的路径

        From cli.argHelp.whereDescription"""
        return self.get_translation("cli.argHelp.whereDescription")

    @property
    def cli_argHelp_wherePath(self) -> str:
        """要查找的路径

        From cli.argHelp.wherePath"""
        return self.get_translation("cli.argHelp.wherePath")

    @property
    def cli_argHelp_serverDescription(self) -> str:
        """启动 SRA 服务端

        From cli.argHelp.serverDescription"""
        return self.get_translation("cli.argHelp.serverDescription")

    @property
    def cli_argHelp_serverHost(self) -> str:
        """将服务端暴露到公网

        From cli.argHelp.serverHost"""
        return self.get_translation("cli.argHelp.serverHost")

    @property
    def cli_argHelp_serverPort(self) -> str:
        """使用的端口

        From cli.argHelp.serverPort"""
        return self.get_translation("cli.argHelp.serverPort")

    @property
    def cli_argHelp_serverNoWebui(self) -> str:
        """不托管 WebUI 静态文件

        From cli.argHelp.serverNoWebui"""
        return self.get_translation("cli.argHelp.serverNoWebui")

    @property
    def cli_initCompleted(self) -> str:
        """初始化完成。请重启应用，或运行 `sra serve` 启动服务端。

        From cli.initCompleted"""
        return self.get_translation("cli.initCompleted")

    @property
    def cli_versionTitle(self) -> str:
        """版本

        From cli.versionTitle"""
        return self.get_translation("cli.versionTitle")

    @property
    def cli_status_sessionId(self) -> str:
        """会话 ID

        From cli.status.sessionId"""
        return self.get_translation("cli.status.sessionId")

    @property
    def cli_status_pid(self) -> str:
        """PID

        From cli.status.pid"""
        return self.get_translation("cli.status.pid")

    @property
    def cli_status_mode(self) -> str:
        """模式

        From cli.status.mode"""
        return self.get_translation("cli.status.mode")

    @property
    def cli_status_status(self) -> str:
        """状态

        From cli.status.status"""
        return self.get_translation("cli.status.status")

    @property
    def cli_status_unit(self) -> str:
        """单元

        From cli.status.unit"""
        return self.get_translation("cli.status.unit")

    @property
    def cli_status_configs(self) -> str:
        """配置

        From cli.status.configs"""
        return self.get_translation("cli.status.configs")

    @property
    def cli_status_progress(self) -> str:
        """进度

        From cli.status.progress"""
        return self.get_translation("cli.status.progress")

    @property
    def cli_status_error(self) -> str:
        """错误

        From cli.status.error"""
        return self.get_translation("cli.status.error")

    @property
    def cli_status_none(self) -> str:
        """无

        From cli.status.none"""
        return self.get_translation("cli.status.none")

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

    def task_retryPreparing(self, current, max_retries) -> str:
        """任务失败，准备重试 ({current}/{max_retries})...

        From task.retryPreparing"""
        template = self.get_translation("task.retryPreparing")
        return template.format(current=current, max_retries=max_retries)

    @property
    def task_killingGameProcess(self) -> str:
        """正在终止游戏进程...

        From task.killingGameProcess"""
        return self.get_translation("task.killingGameProcess")

    @property
    def task_gameProcessKilled(self) -> str:
        """游戏进程已终止

        From task.gameProcessKilled"""
        return self.get_translation("task.gameProcessKilled")

    def task_waitingForRetry(self, seconds) -> str:
        """等待 {seconds} 秒后重试...

        From task.waitingForRetry"""
        template = self.get_translation("task.waitingForRetry")
        return template.format(seconds=seconds)

    def task_retryFromConfig(self, config_name) -> str:
        """将从当前配置 [{config_name}] 重新开始执行

        From task.retryFromConfig"""
        template = self.get_translation("task.retryFromConfig")
        return template.format(config_name=config_name)

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

    def notification_taskStarted(self, task) -> str:
        """任务 {task} 开始执行。

        From notification.taskStarted"""
        template = self.get_translation("notification.taskStarted")
        return template.format(task=task)

    def notification_taskCompleted(self, task) -> str:
        """任务 {task} 执行完成。

        From notification.taskCompleted"""
        template = self.get_translation("notification.taskCompleted")
        return template.format(task=task)

    def notification_taskFailed(self, task) -> str:
        """任务 {task} 执行失败。

        From notification.taskFailed"""
        template = self.get_translation("notification.taskFailed")
        return template.format(task=task)

    @property
    def notification_testTitle(self) -> str:
        """通知渠道测试

        From notification.testTitle"""
        return self.get_translation("notification.testTitle")

    @property
    def notification_testMessage(self) -> str:
        """这是一条测试通知, 如果你收到此通知，证明你的渠道配置正确

        From notification.testMessage"""
        return self.get_translation("notification.testMessage")

    @property
    def notification_payloadHeader(self) -> str:
        """[SRA 通知]

        From notification.payloadHeader"""
        return self.get_translation("notification.payloadHeader")

    @property
    def notification_payloadEvent(self) -> str:
        """事件: 

        From notification.payloadEvent"""
        return self.get_translation("notification.payloadEvent")

    @property
    def notification_payloadResult(self) -> str:
        """结果: 

        From notification.payloadResult"""
        return self.get_translation("notification.payloadResult")

    @property
    def notification_payloadTime(self) -> str:
        """时间: 

        From notification.payloadTime"""
        return self.get_translation("notification.payloadTime")

    @property
    def notification_payloadMessage(self) -> str:
        """消息: 

        From notification.payloadMessage"""
        return self.get_translation("notification.payloadMessage")

    @property
    def notification_channelEmail(self) -> str:
        """邮件

        From notification.channelEmail"""
        return self.get_translation("notification.channelEmail")

    @property
    def notification_channelFeishu(self) -> str:
        """飞书

        From notification.channelFeishu"""
        return self.get_translation("notification.channelFeishu")

    @property
    def notification_channelWeCom(self) -> str:
        """企业微信

        From notification.channelWeCom"""
        return self.get_translation("notification.channelWeCom")

    @property
    def notification_channelDingTalk(self) -> str:
        """钉钉

        From notification.channelDingTalk"""
        return self.get_translation("notification.channelDingTalk")

    @property
    def notification_channelSystem(self) -> str:
        """系统

        From notification.channelSystem"""
        return self.get_translation("notification.channelSystem")

    def extension_notFound(self, ext_id) -> str:
        """扩展 '{ext_id}' 不存在

        From extension.notFound"""
        template = self.get_translation("extension.notFound")
        return template.format(ext_id=ext_id)

    def extension_noConfig(self, ext_id) -> str:
        """扩展 '{ext_id}' 没有配置

        From extension.noConfig"""
        template = self.get_translation("extension.noConfig")
        return template.format(ext_id=ext_id)

    def extension_configInvalid(self, error) -> str:
        """配置验证失败: {error}

        From extension.configInvalid"""
        template = self.get_translation("extension.configInvalid")
        return template.format(error=error)

    def extension_configSaved(self, ext_id) -> str:
        """扩展 {ext_id} 配置已保存

        From extension.configSaved"""
        template = self.get_translation("extension.configSaved")
        return template.format(ext_id=ext_id)

    def extension_notFoundHint(self, ext_id) -> str:
        """扩展 '{ext_id}' 不存在，使用 'extension list' 查看可用扩展

        From extension.notFoundHint"""
        template = self.get_translation("extension.notFoundHint")
        return template.format(ext_id=ext_id)

    def extension_backgroundStarted(self, ext_id) -> str:
        """已启动后台扩展 '{ext_id}'

        From extension.backgroundStarted"""
        template = self.get_translation("extension.backgroundStarted")
        return template.format(ext_id=ext_id)

    def extension_backgroundStartFailed(self, ext_id) -> str:
        """无法启动后台扩展 '{ext_id}'

        From extension.backgroundStartFailed"""
        template = self.get_translation("extension.backgroundStartFailed")
        return template.format(ext_id=ext_id)

    def extension_started(self, ext_id) -> str:
        """已启动扩展 '{ext_id}'

        From extension.started"""
        template = self.get_translation("extension.started")
        return template.format(ext_id=ext_id)

    def extension_startFailed(self, ext_id) -> str:
        """无法启动扩展 '{ext_id}'

        From extension.startFailed"""
        template = self.get_translation("extension.startFailed")
        return template.format(ext_id=ext_id)

    def extension_backgroundStopped(self, ext_id) -> str:
        """已停止后台扩展 '{ext_id}'

        From extension.backgroundStopped"""
        template = self.get_translation("extension.backgroundStopped")
        return template.format(ext_id=ext_id)

    def extension_backgroundNotRunning(self, ext_id) -> str:
        """后台扩展 '{ext_id}' 未运行

        From extension.backgroundNotRunning"""
        template = self.get_translation("extension.backgroundNotRunning")
        return template.format(ext_id=ext_id)

    def extension_notRunning(self, ext_id) -> str:
        """扩展 '{ext_id}' 未在运行

        From extension.notRunning"""
        template = self.get_translation("extension.notRunning")
        return template.format(ext_id=ext_id)

    def extension_otherRunning(self, current, ext_id) -> str:
        """当前正在运行的扩展是 '{current}'，不是 '{ext_id}'

        From extension.otherRunning"""
        template = self.get_translation("extension.otherRunning")
        return template.format(current=current, ext_id=ext_id)

    def extension_stopped(self, ext_id) -> str:
        """已停止扩展 '{ext_id}'

        From extension.stopped"""
        template = self.get_translation("extension.stopped")
        return template.format(ext_id=ext_id)

    @property
    def extension_reloadBusy(self) -> str:
        """扩展线程正在运行中，无法执行重载操作

        From extension.reloadBusy"""
        return self.get_translation("extension.reloadBusy")

    @property
    def extension_reloadEmpty(self) -> str:
        """重载完成，但没有已注册的扩展

        From extension.reloadEmpty"""
        return self.get_translation("extension.reloadEmpty")

    def extension_reloaded(self, count, updated) -> str:
        """已重载扩展，当前共 {count} 个（更新 {updated} 个）

        From extension.reloaded"""
        template = self.get_translation("extension.reloaded")
        return template.format(count=count, updated=updated)

    def extension_reloadAdded(self, names) -> str:
        """，新增: {names}

        From extension.reloadAdded"""
        template = self.get_translation("extension.reloadAdded")
        return template.format(names=names)

    def extension_reloadRemoved(self, names) -> str:
        """，移除: {names}

        From extension.reloadRemoved"""
        template = self.get_translation("extension.reloadRemoved")
        return template.format(names=names)

    def extension_reloadRestarted(self, names) -> str:
        """，已重启后台扩展: {names}

        From extension.reloadRestarted"""
        template = self.get_translation("extension.reloadRestarted")
        return template.format(names=names)

    def operator_initFailed(self, error) -> str:
        """Operator 初始化失败: {error}

        From operator.initFailed"""
        template = self.get_translation("operator.initFailed")
        return template.format(error=error)

    def operator_methodNotFound(self, method, methods) -> str:
        """方法 '{method}' 不存在。可用方法: {methods}

        From operator.methodNotFound"""
        template = self.get_translation("operator.methodNotFound")
        return template.format(method=method, methods=methods)

    def operator_fileNotFound(self, error) -> str:
        """文件未找到: {error}

        From operator.fileNotFound"""
        template = self.get_translation("operator.fileNotFound")
        return template.format(error=error)

    def operator_missingParam(self, error) -> str:
        """缺少必需参数: {error}

        From operator.missingParam"""
        template = self.get_translation("operator.missingParam")
        return template.format(error=error)

    def operator_typeError(self, error) -> str:
        """参数类型错误: {error}

        From operator.typeError"""
        template = self.get_translation("operator.typeError")
        return template.format(error=error)

    def operator_executionFailed(self, error) -> str:
        """执行失败: {error}

        From operator.executionFailed"""
        template = self.get_translation("operator.executionFailed")
        return template.format(error=error)

    def operator_callSucceeded(self, method) -> str:
        """{method} 执行成功

        From operator.callSucceeded"""
        template = self.get_translation("operator.callSucceeded")
        return template.format(method=method)

Resources = Localization()
