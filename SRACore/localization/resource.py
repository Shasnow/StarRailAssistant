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

    def set_language(self, lang: str):
        """Set the language and mark data as not loaded."""
        if lang in self.__available_languages:
            self.lang = lang.lower()
            self.__data_loaded = False
        else:
            raise ValueError(f"Language '{lang}' is not available. Available languages: {self.__available_languages}")

    def get_translation(self, key: str) -> str:
        """
        Get the translation value for the specified key.
        
        :param key: Flattened translation key (e.g., test.group1.hello)
        :return: Translation value for the target language, or key if not found
        """
        self.__ensure_data_loaded()
        return self.__normalized_data.get(key, key)

    def cli_intro(self, core, version) -> str:
        """SRA-cli {version} ({core})\nType 'help' or '?' to list commands.

        From cli.intro"""
        template = self.get_translation("cli.intro")
        return template.format(core=core, version=version)

    @property
    def cli_noAdminWarning(self) -> str:
        """You are not running SRA-cli with administrative privileges. Some commands may not work as expected.

        From cli.noAdminWarning"""
        return self.get_translation("cli.noAdminWarning")

    def cli_unknownCommand(self, command) -> str:
        """Unknown command: '{command}'. Type 'help' to get a list of available commands.

        From cli.unknownCommand"""
        template = self.get_translation("cli.unknownCommand")
        return template.format(command=command)

    def cli_invalidArguments(self, command) -> str:
        """Invalid arguments for command '{command}'. Type 'help {command}' for usage.

        From cli.invalidArguments"""
        template = self.get_translation("cli.invalidArguments")
        return template.format(command=command)

    @property
    def cli_helpTitle(self) -> str:
        """Available commands:

        From cli.helpTitle"""
        return self.get_translation("cli.helpTitle")

    @property
    def cli_helpFooter(self) -> str:
        """\nType 'help <command>' to get more information about a specific command.

        From cli.helpFooter"""
        return self.get_translation("cli.helpFooter")

    def cli_help_unknownCommand(self, command) -> str:
        """Unknown command: '{command}'.

        From cli.help.unknownCommand"""
        template = self.get_translation("cli.help.unknownCommand")
        return template.format(command=command)

    @property
    def cli_help_EOF(self) -> str:
        """Exits the SRA-cli application.

        From cli.help.EOF"""
        return self.get_translation("cli.help.EOF")

    @property
    def cli_help_help(self) -> str:
        """Displays help information for commands.

        From cli.help.help"""
        return self.get_translation("cli.help.help")

    @property
    def cli_help_task(self) -> str:
        """Manages tasks within SRA-cli.\nUsage:\n  task run [<name | path>...]\n                Runs all selected tasks in specified configuration file(s).\n                If no configuration file is specified, all config files in cache will be used.\n  task single (taks_name | task_index) [<config_name | config_path>]\n                Runs a single task specified by its name or index, wether it is selected or not.\n                If no configuration file is specified, the current config file in cache will be used.\n  task stop     Stops all running tasks.\n

        From cli.help.task"""
        return self.get_translation("cli.help.task")

    @property
    def cli_help_trigger(self) -> str:
        """Manages triggers within SRA-cli.\nUsage:\n  trigger run                   Starts the trigger service.\n  trigger stop                  Stops the trigger service.\n  trigger enable <trigger_name>    Enables a specific trigger.\n  trigger disable <trigger_name>   Disables a specific trigger.\n  trigger set-<type> <trigger_name> <property> <value>\n                                Changes a property of a specific trigger.\n

        From cli.help.trigger"""
        return self.get_translation("cli.help.trigger")

    @property
    def cli_help_run(self) -> str:
        """Usage: run [<config_name | config_path>...]\nRuns all tasks in specified configuration file(s). If no configuration file is specified, the current config file in cache will be used.\nThis command will block the CLI until all tasks are finished.\n

        From cli.help.run"""
        return self.get_translation("cli.help.run")

    @property
    def cli_help_single(self) -> str:
        """Usage: single (task_name | task_index) [<config_name | config_path>]\nRuns a single task specified by its name or index, whether it is selected or not. If no configuration file is specified, the current config file in cache will be used.\nThis command will block the CLI until the task is finished.\n

        From cli.help.single"""
        return self.get_translation("cli.help.single")

    @property
    def cli_help_host(self) -> str:
        """Start WebSocket server on specified port

        From cli.help.host"""
        return self.get_translation("cli.help.host")

    @property
    def cli_help_version(self) -> str:
        """Displays the current version of SRA-cli.

        From cli.help.version"""
        return self.get_translation("cli.help.version")

    @property
    def cli_help_notify(self) -> str:
        """Notification command - support test email notification

        From cli.help.notify"""
        return self.get_translation("cli.help.notify")

    @property
    def cli_exit_help(self) -> str:
        """Exits the SRA-cli application.

        From cli.exit.help"""
        return self.get_translation("cli.exit.help")

    @property
    def cli_exit_taskTimeout(self) -> str:
        """Timeout reached while waiting for tasks to stop. Forcing exit.

        From cli.exit.taskTimeout"""
        return self.get_translation("cli.exit.taskTimeout")

    @property
    def cli_exit_triggerTimeout(self) -> str:
        """Timeout reached while waiting for triggers to stop. Forcing exit.

        From cli.exit.triggerTimeout"""
        return self.get_translation("cli.exit.triggerTimeout")

    @property
    def cli_task_help(self) -> str:
        """Manages tasks within SRA-cli, type 'help task' for more information.

        From cli.task.help"""
        return self.get_translation("cli.task.help")

    @property
    def cli_task_taskAlreadyRunning(self) -> str:
        """Task is already running.

        From cli.task.taskAlreadyRunning"""
        return self.get_translation("cli.task.taskAlreadyRunning")

    @property
    def cli_task_interrupted(self) -> str:
        """Task execution interrupted by user.

        From cli.task.interrupted"""
        return self.get_translation("cli.task.interrupted")

    @property
    def cli_task_timeout(self) -> str:
        """Timeout reached while waiting for tasks to complete.

        From cli.task.timeout"""
        return self.get_translation("cli.task.timeout")

    @property
    def cli_task_stopped(self) -> str:
        """All running tasks have been stopped.

        From cli.task.stopped"""
        return self.get_translation("cli.task.stopped")

    @property
    def cli_task_notRunning(self) -> str:
        """No tasks are currently running.

        From cli.task.notRunning"""
        return self.get_translation("cli.task.notRunning")

    @property
    def cli_trigger_help(self) -> str:
        """Manages triggers within SRA-cli, type 'help trigger' for more information.

        From cli.trigger.help"""
        return self.get_translation("cli.trigger.help")

    @property
    def cli_trigger_alreadyRunning(self) -> str:
        """Trigger service is already running.

        From cli.trigger.alreadyRunning"""
        return self.get_translation("cli.trigger.alreadyRunning")

    @property
    def cli_trigger_started(self) -> str:
        """Trigger service started.

        From cli.trigger.started"""
        return self.get_translation("cli.trigger.started")

    @property
    def cli_trigger_stopped(self) -> str:
        """Trigger service stopped.

        From cli.trigger.stopped"""
        return self.get_translation("cli.trigger.stopped")

    @property
    def cli_trigger_notRunning(self) -> str:
        """Trigger service is not running.

        From cli.trigger.notRunning"""
        return self.get_translation("cli.trigger.notRunning")

    @property
    def cli_trigger_timeout(self) -> str:
        """Timeout reached while waiting for triggers to complete.

        From cli.trigger.timeout"""
        return self.get_translation("cli.trigger.timeout")

    def cli_trigger_enabled(self, trigger_name) -> str:
        """Trigger '{trigger_name}' has been enabled.

        From cli.trigger.enabled"""
        template = self.get_translation("cli.trigger.enabled")
        return template.format(trigger_name=trigger_name)

    def cli_trigger_disabled(self, trigger_name) -> str:
        """Trigger '{trigger_name}' has been disabled.

        From cli.trigger.disabled"""
        template = self.get_translation("cli.trigger.disabled")
        return template.format(trigger_name=trigger_name)

    def cli_trigger_notFound(self, trigger_name) -> str:
        """Trigger '{trigger_name}' not found.

        From cli.trigger.notFound"""
        template = self.get_translation("cli.trigger.notFound")
        return template.format(trigger_name=trigger_name)

    def cli_trigger_attrNotFound(self, attr, trigger_name) -> str:
        """Attribute '{attr}' not found in trigger '{trigger_name}'.

        From cli.trigger.attrNotFound"""
        template = self.get_translation("cli.trigger.attrNotFound")
        return template.format(attr=attr, trigger_name=trigger_name)

    def cli_trigger_attrSet(self, attr, trigger_name, value) -> str:
        """Attribute '{attr}' of trigger '{trigger_name}' has been set to '{value}'.

        From cli.trigger.attrSet"""
        template = self.get_translation("cli.trigger.attrSet")
        return template.format(attr=attr, trigger_name=trigger_name, value=value)

    def cli_trigger_unknownType(self, type) -> str:
        """Unknown attribute type: '{type}', supports: 'int', 'float', 'bool', 'str'.

        From cli.trigger.unknownType"""
        template = self.get_translation("cli.trigger.unknownType")
        return template.format(type=type)

    @property
    def cli_run_help(self) -> str:
        """Runs all selected tasks in specified configuration file, type 'help run' for more information.

        From cli.run.help"""
        return self.get_translation("cli.run.help")

    @property
    def cli_run_started(self) -> str:
        """Task execution started, the CLI will be blocked until all tasks are finished.

        From cli.run.started"""
        return self.get_translation("cli.run.started")

    @property
    def cli_run_completed(self) -> str:
        """All tasks have been completed.

        From cli.run.completed"""
        return self.get_translation("cli.run.completed")

    @property
    def cli_single_help(self) -> str:
        """Runs a single task specified by its name or index, type 'help single' for more information.

        From cli.single.help"""
        return self.get_translation("cli.single.help")

    @property
    def cli_notify_help(self) -> str:
        """Manages notifications within SRA-cli, type 'help notify' for more information.

        From cli.notify.help"""
        return self.get_translation("cli.notify.help")

    @property
    def cli_version_help(self) -> str:
        """Displays the current version of SRA-cli.

        From cli.version.help"""
        return self.get_translation("cli.version.help")

    @property
    def cli_host_help(self) -> str:
        """Starts a WebSocket server on the specified port for remote control.\n\nUsage:\n  host <port>  Starts a WebSocket server on the specified port.\n  host stop    Stops the WebSocket server.\n

        From cli.host.help"""
        return self.get_translation("cli.host.help")

    def cli_host_started(self, port) -> str:
        """WebSocket server started on port {port}.

        From cli.host.started"""
        template = self.get_translation("cli.host.started")
        return template.format(port=port)

    def cli_host_invalidPort(self, port) -> str:
        """Invalid port number: {port}.

        From cli.host.invalidPort"""
        template = self.get_translation("cli.host.invalidPort")
        return template.format(port=port)

    @property
    def cli_host_stopped(self) -> str:
        """WebSocket server stopped.

        From cli.host.stopped"""
        return self.get_translation("cli.host.stopped")

    @property
    def cli_host_notRunning(self) -> str:
        """WebSocket server is not running.

        From cli.host.notRunning"""
        return self.get_translation("cli.host.notRunning")

    @property
    def argparse_description(self) -> str:
        """SRA-cli: A command-line interface for SRA.

        From argparse.description"""
        return self.get_translation("argparse.description")

    @property
    def argparse_epilog(self) -> str:
        """From argparse.epilog"""
        return self.get_translation("argparse.epilog")

    @property
    def argparse_host_help(self) -> str:
        """Start WebSocket server

        From argparse.host_help"""
        return self.get_translation("argparse.host_help")

    @property
    def argparse_port_help(self) -> str:
        """Port number to start the WebSocket server on.

        From argparse.port_help"""
        return self.get_translation("argparse.port_help")

    @property
    def argparse_inline_help(self) -> str:
        """Inline mode (no command prompt)

        From argparse.inline_help"""
        return self.get_translation("argparse.inline_help")

    @property
    def argparse_embed_help(self) -> str:
        """Embed mode (no command prompt)

        From argparse.embed_help"""
        return self.get_translation("argparse.embed_help")

    @property
    def argparse_version_help(self) -> str:
        """Show the version of SRA-cli and exit.

        From argparse.version_help"""
        return self.get_translation("argparse.version_help")

    @property
    def argparse_log_level_help(self) -> str:
        """Set the logging level (default: TRACE).

        From argparse.log_level_help"""
        return self.get_translation("argparse.log_level_help")

    @property
    def argparse_run_help(self) -> str:
        """Run all selected tasks in specified configuration file(s). Type 'run --help' for more information.

        From argparse.run_help"""
        return self.get_translation("argparse.run_help")

    @property
    def argparse_run_description(self) -> str:
        """Runs all tasks in specified configuration file(s).\nIf no configuration file is specified, the current config file in cache will be used.\nThis command will block the CLI until all tasks are finished.\n

        From argparse.run_description"""
        return self.get_translation("argparse.run_description")

    @property
    def argparse_config_help(self) -> str:
        """Configuration file name or path.

        From argparse.config_help"""
        return self.get_translation("argparse.config_help")

    @property
    def argparse_single_help(self) -> str:
        """Run a single task specified by its name or index. Type 'single --help' for more information.

        From argparse.single_help"""
        return self.get_translation("argparse.single_help")

    @property
    def argparse_single_description(self) -> str:
        """Runs a single task specified by its name or index, whether it is selected or not.\nIf no configuration file is specified, the current config file in cache will be used.\nThis command will block the CLI until the task is finished.\n

        From argparse.single_description"""
        return self.get_translation("argparse.single_description")

    @property
    def argparse_task_name_help(self) -> str:
        """Name or index of the task to run.

        From argparse.task_name_help"""
        return self.get_translation("argparse.task_name_help")

    @property
    def argparse_once_help(self) -> str:
        """Exit SRA-cli after running the command.

        From argparse.once_help"""
        return self.get_translation("argparse.once_help")

    def task_currentConfig(self, config_name) -> str:
        """Current config: {config_name}

        From task.currentConfig"""
        template = self.get_translation("task.currentConfig")
        return template.format(config_name=config_name)

    def task_noSelectedTasks(self, config_name) -> str:
        """No tasks are selected in {config_name}, skipping execution.

        From task.noSelectedTasks"""
        template = self.get_translation("task.noSelectedTasks")
        return template.format(config_name=config_name)

    def task_taskFailed(self, name) -> str:
        """Task '{name}' failed. Stopping further execution.

        From task.taskFailed"""
        template = self.get_translation("task.taskFailed")
        return template.format(name=name)

    def task_taskCrashed(self, name, error) -> str:
        """Task '{name}' crashed due to an unexpected error: {error}

        From task.taskCrashed"""
        template = self.get_translation("task.taskCrashed")
        return template.format(name=name, error=error)

    def task_taskCompleted(self, name) -> str:
        """Task '{name}' has been completed.

        From task.taskCompleted"""
        template = self.get_translation("task.taskCompleted")
        return template.format(name=name)

    def task_configCompleted(self, config_name) -> str:
        """All tasks in config '{config_name}' have been completed.

        From task.configCompleted"""
        template = self.get_translation("task.configCompleted")
        return template.format(config_name=config_name)

    @property
    def task_notificationTitle(self) -> str:
        """Task Completion Reminder

        From task.notificationTitle"""
        return self.get_translation("task.notificationTitle")

    @property
    def task_notificationMessage(self) -> str:
        """Your SRA task has completed.

        From task.notificationMessage"""
        return self.get_translation("task.notificationMessage")

    def task_instantiateFailed(self, name, error) -> str:
        """Failed to instantiate task '{name}': {error}

        From task.instantiateFailed"""
        template = self.get_translation("task.instantiateFailed")
        return template.format(name=name, error=error)

    def task_noSuchTask(self, identifier) -> str:
        """No such task: '{identifier}'

        From task.noSuchTask"""
        template = self.get_translation("task.noSuchTask")
        return template.format(identifier=identifier)

    def task_managerCrashed(self, error) -> str:
        """Task manager crashed due to an unexpected error: {error}

        From task.managerCrashed"""
        template = self.get_translation("task.managerCrashed")
        return template.format(error=error)

    def config_fileNotFound(self, path) -> str:
        """Could not find config file: '{path}'

        From config.fileNotFound"""
        template = self.get_translation("config.fileNotFound")
        return template.format(path=path)

    def config_parseError(self, path, error) -> str:
        """Failed to parse config file '{path}': {error}

        From config.parseError"""
        template = self.get_translation("config.parseError")
        return template.format(path=path, error=error)

    def config_exception(self, path, error) -> str:
        """An error occurred while loading config file '{path}': {error}

        From config.exception"""
        template = self.get_translation("config.exception")
        return template.format(path=path, error=error)

Resource = Localization()
