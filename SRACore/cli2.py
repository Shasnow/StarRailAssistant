import argparse

import cmd2
from loguru import logger
from rich.text import Text

from SRACore.localization import Resource
from SRACore.models.app_settings import AppSettings
from SRACore.runtime.event_listener import KeyboardListener
from SRACore.runtime.trigger_manager import TriggerManager
from SRACore.thread.task_process import TaskManager
from SRACore.util.const import VERSION, CORE


class SRACli(cmd2.Cmd):
    def __init__(self, settings: AppSettings):
        super().__init__(startup_script=".srarc")
        self.intro = f"Welcome to SRA-cli (version {VERSION}, core {CORE}). \nType 'help' to list commands."
        self.prompt = 'sra> '
        self.settings = settings

        # 移除不需要的 settable 选项
        # for attr in ["debug", "timing", "quiet", "feedback_to_output",
        #               "max_completion_items", "allow_style", "always_show_hint",
        #               "scripts_add_to_history", "echo"]:
        #     self.remove_settable(attr)

        # 移除不需要的内置命令
        for cmd_name in ["run_pyscript"]:
            if hasattr(cmd2.Cmd, f"do_{cmd_name}"):
                delattr(cmd2.Cmd, f"do_{cmd_name}")
        # 初始化任务管理器
        self.task_manager = TaskManager(settings)
        # 初始化触发器管理器
        self.trigger_manager = TriggerManager()

        # 初始化键盘监听器
        stop_hotkey = settings.General.hotkeyStop.lower() or 'f9'
        self.event_listener = KeyboardListener()
        self.event_listener.register_key_event(stop_hotkey, self._task_stop)
        self.event_listener.start()

    # region 任务管理
    @staticmethod
    def _build_task_parser() -> argparse.ArgumentParser:
        task_description = Text.assemble("Manages tasks within SRA-cli.")
        task_parser = cmd2.argparse_custom.DEFAULT_ARGUMENT_PARSER(description=task_description)
        task_parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return task_parser

    @cmd2.with_argparser(_build_task_parser(), preserve_quotes=True)
    def do_task(self, args: argparse.Namespace) -> None:
        handler = args.cmd2_handler.get()
        handler(args)

    @staticmethod
    def _build_task_run_parser() -> cmd2.Cmd2ArgumentParser:
        task_run_description = Text.assemble("Executes a task based on the provided configuration.")
        task_run_parser = cmd2.argparse_custom.DEFAULT_ARGUMENT_PARSER(description=task_run_description)
        task_run_parser.add_argument('config', nargs='*', help="The configuration(s) to execute.")
        return task_run_parser

    @cmd2.as_subcommand_to("task", "run", _build_task_run_parser(), help="Executes a task")
    def _task_run(self, args: argparse.Namespace) -> None:
        if self.task_manager.is_thread_running():
            self.poutput(Resource.cli_task_taskAlreadyRunning)
            return
        self.task_manager.run_in_thread(*args.config)

    @staticmethod
    def _build_task_single_parser() -> cmd2.Cmd2ArgumentParser:
        task_single_description = Text.assemble("Executes a single task with a specific name and configuration.")
        task_single_parser = cmd2.argparse_custom.DEFAULT_ARGUMENT_PARSER(description=task_single_description)
        task_single_parser.add_argument('task', help="The name or index of the task to execute.")
        task_single_parser.add_argument('--config', help="The configuration for the task.")
        return task_single_parser

    @cmd2.as_subcommand_to("task", "single", _build_task_single_parser(), help="Executes a single task")
    def _task_single(self, args: argparse.Namespace) -> None:
        if self.task_manager.is_thread_running():
            self.poutput(Resource.cli_task_taskAlreadyRunning)
            return
        if self.task_manager.run_task_in_thread(args.task, args.config):
            self.poutput(Resource.cli_run_started)

    @staticmethod
    def _build_task_stop_parser() -> cmd2.Cmd2ArgumentParser:
        task_stop_description = Text.assemble("Stops the currently running task.")
        return cmd2.argparse_custom.DEFAULT_ARGUMENT_PARSER(description=task_stop_description)

    @cmd2.as_subcommand_to("task", "stop", _build_task_stop_parser(), help="Stops the running task")
    def _task_stop(self, _) -> None:
        if self.task_manager.is_thread_running():
            self.task_manager.stop_thread()
            self.poutput(Resource.cli_task_stopped)
        else:
            self.poutput(Resource.cli_task_notRunning)

    @staticmethod
    def _build_run_parser() -> cmd2.Cmd2ArgumentParser:
        run_description = Text.assemble("Run specified tasks, will block current command line until tasks complete.")
        run_parser = cmd2.argparse_custom.DEFAULT_ARGUMENT_PARSER(description=run_description)
        run_parser.add_argument('config', nargs='*', help="The configuration(s) to execute.")
        return run_parser

    @cmd2.with_argparser(_build_run_parser())
    def do_run(self, args: argparse.Namespace) -> None:
        """Run specified tasks, will block current command line until tasks complete"""
        self.poutput(Resource.cli_run_started)
        try:
            self.task_manager.run(*args.config)
        except KeyboardInterrupt:
            self.task_manager.request_stop()

    @staticmethod
    def _build_single_parser() -> cmd2.Cmd2ArgumentParser:
        single_description = Text.assemble(
            "Run a single specified task, will block current command line until task complete.")
        single_parser = cmd2.argparse_custom.DEFAULT_ARGUMENT_PARSER(description=single_description)
        single_parser.add_argument('task', help="The name or index of the task to execute.")
        single_parser.add_argument('config', nargs='?', help="The configuration for the task.")
        return single_parser

    @cmd2.with_argparser(_build_single_parser())
    def do_single(self, args: argparse.Namespace) -> None:
        """Run a single specified task, will block current command line until task complete"""
        self.poutput(Resource.cli_run_started)
        try:
            self.task_manager.run_task(args.task, args.config)
        except KeyboardInterrupt:
            self.task_manager.request_stop()

    # endregion

    # region 触发器管理

    @staticmethod
    def _build_trigger_parser() -> argparse.ArgumentParser:
        trigger_description = Text.assemble("Manages triggers within SRA-cli.")
        trigger_parser = cmd2.argparse_custom.DEFAULT_ARGUMENT_PARSER(description=trigger_description)
        trigger_parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return trigger_parser

    @cmd2.with_argparser(_build_trigger_parser(), preserve_quotes=True)
    def do_trigger(self, args: argparse.Namespace) -> None:
        handler = args.cmd2_handler.get()
        handler(args)

    @staticmethod
    def _build_trigger_run_parser() -> cmd2.Cmd2ArgumentParser:
        trigger_run_description = Text.assemble("Starts the trigger manager.")
        return cmd2.argparse_custom.DEFAULT_ARGUMENT_PARSER(description=trigger_run_description)

    @cmd2.as_subcommand_to("trigger", "run", _build_trigger_run_parser(), help="Starts the trigger manager")
    def _trigger_run(self, _) -> None:
        if self.trigger_manager.is_thread_running():
            self.poutput(Resource.cli_trigger_alreadyRunning)
            return
        if not self.trigger_manager.has_enabled_triggers():
            self.poutput("No enabled triggers found. Use 'trigger enable <name>' first.")
            return
        self.trigger_manager.start_thread()
        self.poutput(Resource.cli_trigger_started)

    @staticmethod
    def _build_trigger_stop_parser() -> cmd2.Cmd2ArgumentParser:
        trigger_stop_description = Text.assemble("Stops the trigger manager.")
        return cmd2.argparse_custom.DEFAULT_ARGUMENT_PARSER(description=trigger_stop_description)

    @cmd2.as_subcommand_to("trigger", "stop", _build_trigger_stop_parser(), help="Stops the trigger manager")
    def _trigger_stop(self, _) -> None:
        if self.trigger_manager.is_thread_running():
            self.trigger_manager.stop_thread()
            self.poutput(Resource.cli_trigger_stopped)
        else:
            self.poutput(Resource.cli_trigger_notRunning)

    @staticmethod
    def _build_trigger_enable_parser() -> cmd2.Cmd2ArgumentParser:
        trigger_enable_description = Text.assemble("Enables a specific trigger.")
        trigger_enable_parser = cmd2.argparse_custom.DEFAULT_ARGUMENT_PARSER(description=trigger_enable_description)
        trigger_enable_parser.add_argument('name', help="The name of the trigger to enable.")
        return trigger_enable_parser

    @cmd2.as_subcommand_to("trigger", "enable", _build_trigger_enable_parser(), help="Enables a trigger")
    def _trigger_enable(self, args: argparse.Namespace) -> None:
        for trigger in self.trigger_manager.triggers:
            if trigger.__class__.__name__.lower() == args.name.lower():
                trigger.set_enable(True)
                logger.info(Resource.cli_trigger_enabled(args.name))
                self.trigger_manager.ensure_running()
                return
        self.poutput(Resource.cli_trigger_notFound(args.name))

    @staticmethod
    def _build_trigger_disable_parser() -> cmd2.Cmd2ArgumentParser:
        trigger_disable_description = Text.assemble("Disables a specific trigger.")
        trigger_disable_parser = cmd2.argparse_custom.DEFAULT_ARGUMENT_PARSER(description=trigger_disable_description)
        trigger_disable_parser.add_argument('name', help="The name of the trigger to disable.")
        return trigger_disable_parser

    @cmd2.as_subcommand_to("trigger", "disable", _build_trigger_disable_parser(), help="Disables a trigger")
    def _trigger_disable(self, args: argparse.Namespace) -> None:
        for trigger in self.trigger_manager.triggers:
            if trigger.__class__.__name__.lower() == args.name.lower():
                trigger.set_enable(False)
                logger.info(Resource.cli_trigger_disabled(args.name))
                self.trigger_manager.stop_if_idle()
                return
        self.poutput(Resource.cli_trigger_notFound(args.name))

    @staticmethod
    def _build_trigger_set_parser() -> cmd2.Cmd2ArgumentParser:
        trigger_set_description = Text.assemble("Sets an attribute of a specific trigger.")
        trigger_set_parser = cmd2.argparse_custom.DEFAULT_ARGUMENT_PARSER(description=trigger_set_description)
        trigger_set_parser.add_argument('name', help="The name of the trigger.")
        trigger_set_parser.add_argument('attr', help="The attribute to set.")
        trigger_set_parser.add_argument('value', help="The value to set.")
        trigger_set_parser.add_argument('--type', choices=['int', 'float', 'str', 'bool'],
                                        default='str', help="The type of the value.")
        return trigger_set_parser

    @cmd2.as_subcommand_to("trigger", "set", _build_trigger_set_parser(), help="Sets a trigger attribute")
    def _trigger_set(self, args: argparse.Namespace) -> None:
        for trigger in self.trigger_manager.triggers:
            if trigger.__class__.__name__.lower() == args.name.lower():
                if not hasattr(trigger, args.attr):
                    self.poutput(Resource.cli_trigger_attrNotFound(args.attr, args.name))
                    return
                if args.type == 'int':
                    setattr(trigger, args.attr, int(args.value))
                elif args.type == 'float':
                    setattr(trigger, args.attr, float(args.value))
                elif args.type == 'str':
                    setattr(trigger, args.attr, args.value)
                elif args.type == 'bool':
                    setattr(trigger, args.attr, args.value.lower() in ['true', '1', 'yes'])
                else:
                    self.poutput(Resource.cli_trigger_unknownType(args.type))
                    return
                logger.info(Resource.cli_trigger_attrSet(args.name, args.attr, args.value))
                return
        self.poutput(Resource.cli_trigger_notFound(args.name))

    # endregion

    # region 其他命令
    def do_version(self, _: str):
        """Show version information"""
        self.poutput(f"{VERSION}")

    def do_quit(self, _: argparse.Namespace) -> bool | None:
        """Exit this application."""
        self._cleanup()
        # Return True to stop the command loop
        self.last_result = True
        return True
    do_exit = do_quit

    def do_notify(self, arg: str):
        """Notification command - support test email/webhook/telegram/serverchan/onebot notification"""
        args = arg.split()
        if not args:
            self.poutput(Resource.cli_invalidArguments('notify'))
            return

        command = args[0]
        if command == 'test' and len(args) >= 2:
            channel = args[1]
            from SRACore.notification import send_channel_test_notification

            label, result = send_channel_test_notification(channel)
            if label:
                self.poutput(label + "测试通知发送" + ("成功" if result else "失败"))
            else:
                self.poutput(Resource.cli_invalidArguments("notify"))
        else:
            self.poutput(Resource.cli_invalidArguments('notify'))

    # endregion

    # region 生命周期管理

    def _cleanup(self):
        """清理资源"""
        self.task_manager.stop_thread(timeout=5.0)
        self.trigger_manager.stop_thread(timeout=5.0)
        self.event_listener.stop()

    # endregion
