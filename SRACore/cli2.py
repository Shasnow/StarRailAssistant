import argparse
import dataclasses

import cmd2
from loguru import logger
from rich.text import Text

from SRACore.localization import Resource
from SRACore.models.app_settings import AppSettings
from SRACore.operators.factory import OperatorFactory
from SRACore.runtime.event_listener import KeyboardListener
from SRACore.runtime.trigger_manager import TriggerManager
from SRACore.thread.task_process import TaskManager
from SRACore.util.const import VERSION, CORE


class SRACli(cmd2.Cmd):
    def __init__(self, settings: AppSettings):
        super().__init__(startup_script=".srarc")
        self.intro = f"Welcome to SRA-cli (version {VERSION}, core {CORE}). \nType 'help' to list commands."
        self.prompt = 'sra> '
        self.default_error = Resource.cli_defaultError
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
    def _build_task_parser() -> cmd2.Cmd2ArgumentParser:
        task_description = Text.assemble(Resource.task_description)
        task_parser = cmd2.Cmd2ArgumentParser(description=task_description)
        task_parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return task_parser

    @cmd2.with_argparser(_build_task_parser(), preserve_quotes=True)
    def do_task(self, args: argparse.Namespace) -> None:
        args.cmd2_subcommand_func(args)

    @staticmethod
    def _build_task_run_parser() -> cmd2.Cmd2ArgumentParser:
        task_run_description = Text.assemble(Resource.run_description)
        task_run_parser = cmd2.Cmd2ArgumentParser(description=task_run_description)
        task_run_parser.add_argument('config', nargs='*', help=Resource.run_configHelp)
        return task_run_parser

    @cmd2.as_subcommand_to("task", "run", _build_task_run_parser(), help=Resource.run_configHelp)
    def _task_run(self, args: argparse.Namespace) -> None:
        if self.task_manager.is_thread_running():
            self.poutput(Resource.cli_task_taskAlreadyRunning)
            return
        self.task_manager.run_in_thread(*args.config)

    @staticmethod
    def _build_task_single_parser() -> cmd2.Cmd2ArgumentParser:
        task_single_description = Text.assemble(Resource.single_description)
        task_single_parser = cmd2.Cmd2ArgumentParser(description=task_single_description)
        task_single_parser.add_argument('task', help=Resource.single_taskHelp)
        task_single_parser.add_argument('--config', help=Resource.single_configHelp)
        return task_single_parser

    @cmd2.as_subcommand_to("task", "single", _build_task_single_parser(), help=Resource.single_description)
    def _task_single(self, args: argparse.Namespace) -> None:
        if self.task_manager.is_thread_running():
            self.poutput(Resource.cli_task_taskAlreadyRunning)
            return
        if self.task_manager.run_task_in_thread(args.task, args.config):
            self.poutput(Resource.cli_run_started)

    @staticmethod
    def _build_task_stop_parser() -> cmd2.Cmd2ArgumentParser:
        task_stop_description = Text.assemble(Resource.stop_description)
        return cmd2.Cmd2ArgumentParser(description=task_stop_description)

    @cmd2.as_subcommand_to("task", "stop", _build_task_stop_parser(), help=Resource.stop_description)
    def _task_stop(self, _) -> None:
        if self.task_manager.is_thread_running():
            self.task_manager.stop_thread()
            self.poutput(Resource.cli_task_stopped)
        else:
            self.poutput(Resource.cli_task_notRunning)

    @staticmethod
    def _build_task_status_parser() -> cmd2.Cmd2ArgumentParser:
        task_status_description = "Show current task status"
        task_status_parser = cmd2.Cmd2ArgumentParser(description=task_status_description)
        task_status_parser.add_argument('--json', action='store_true', help='Output in JSON format')
        return task_status_parser

    @cmd2.as_subcommand_to("task", "status", _build_task_status_parser(), help="Show current task status")
    def _task_status(self, args: argparse.Namespace) -> None:
        import json
        info = self.task_manager.info
        if args.json:
            self.poutput(json.dumps(dataclasses.asdict(info)))
        else:
            self.poutput(f"Session ID: {info.sessionId}")
            self.poutput(f"PID: {info.pid}")
            self.poutput(f"Mode: {info.mode}")
            self.poutput(f"Configs: {', '.join(info.configs) if info.configs else 'N/A'}")
            self.poutput(f"Task: {info.task}")
            self.poutput(f"Status: {info.status}")

    @staticmethod
    def _build_run_parser() -> cmd2.Cmd2ArgumentParser:
        run_description = Text.assemble(Resource.run_description)
        run_parser = cmd2.Cmd2ArgumentParser(description=run_description)
        run_parser.add_argument('config', nargs='*', help=Resource.run_configHelp)
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
        single_description = Text.assemble(Resource.single_description)
        single_parser = cmd2.Cmd2ArgumentParser(description=single_description)
        single_parser.add_argument('task', help=Resource.single_taskHelp)
        single_parser.add_argument('--config', help=Resource.single_configHelp)
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
    def _build_trigger_parser() -> cmd2.Cmd2ArgumentParser:
        trigger_description = Text.assemble(Resource.trigger_description)
        trigger_parser = cmd2.Cmd2ArgumentParser(description=trigger_description)
        trigger_parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return trigger_parser

    @cmd2.with_argparser(_build_trigger_parser(), preserve_quotes=True)
    def do_trigger(self, args: argparse.Namespace) -> None:
        args.cmd2_subcommand_func(args)

    @staticmethod
    def _build_trigger_run_parser() -> cmd2.Cmd2ArgumentParser:
        trigger_run_description = Text.assemble(Resource.trigger_run_description)
        return cmd2.Cmd2ArgumentParser(description=trigger_run_description)

    @cmd2.as_subcommand_to("trigger", "run", _build_trigger_run_parser(), help=Resource.trigger_run_description)
    def _trigger_run(self, _) -> None:
        if self.trigger_manager.is_thread_running():
            self.poutput(Resource.cli_trigger_alreadyRunning)
            return
        if not self.trigger_manager.has_enabled_triggers():
            self.poutput(Resource.cli_trigger_noEnabledTriggers)
            return
        self.trigger_manager.start_thread()
        self.poutput(Resource.cli_trigger_started)

    @staticmethod
    def _build_trigger_stop_parser() -> cmd2.Cmd2ArgumentParser:
        trigger_stop_description = Text.assemble(Resource.trigger_stop_description)
        return cmd2.Cmd2ArgumentParser(description=trigger_stop_description)

    @cmd2.as_subcommand_to("trigger", "stop", _build_trigger_stop_parser(), help=Resource.trigger_stop_description)
    def _trigger_stop(self, _) -> None:
        if self.trigger_manager.is_thread_running():
            self.trigger_manager.stop_thread()
            self.poutput(Resource.cli_trigger_stopped)
        else:
            self.poutput(Resource.cli_trigger_notRunning)

    @staticmethod
    def _build_trigger_enable_parser() -> cmd2.Cmd2ArgumentParser:
        trigger_enable_description = Text.assemble(Resource.trigger_enable_description)
        trigger_enable_parser = cmd2.Cmd2ArgumentParser(description=trigger_enable_description)
        trigger_enable_parser.add_argument('name', help=Resource.trigger_enable_nameHelp)
        return trigger_enable_parser

    @cmd2.as_subcommand_to("trigger", "enable", _build_trigger_enable_parser(),
                           help=Resource.trigger_enable_description)
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
        trigger_disable_description = Text.assemble(Resource.trigger_disable_description)
        trigger_disable_parser = cmd2.Cmd2ArgumentParser(description=trigger_disable_description)
        trigger_disable_parser.add_argument('name', help=Resource.trigger_disable_nameHelp)
        return trigger_disable_parser

    @cmd2.as_subcommand_to("trigger", "disable", _build_trigger_disable_parser(),
                           help=Resource.trigger_disable_description)
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
        trigger_set_description = Text.assemble(Resource.trigger_set_description)
        trigger_set_parser = cmd2.Cmd2ArgumentParser(description=trigger_set_description)
        trigger_set_parser.add_argument('name', help=Resource.trigger_set_nameHelp)
        trigger_set_parser.add_argument('attr', help=Resource.trigger_set_attrHelp)
        trigger_set_parser.add_argument('value', help=Resource.trigger_set_valueHelp)
        trigger_set_parser.add_argument('--type', choices=['int', 'float', 'str', 'bool'],
                                        default='str', help=Resource.trigger_set_typeHelp)
        return trigger_set_parser

    @cmd2.as_subcommand_to("trigger", "set", _build_trigger_set_parser(), help=Resource.trigger_set_description)
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

    # region 游戏操作
    @staticmethod
    def _build_game_parser() -> cmd2.Cmd2ArgumentParser:
        game_description = Text.assemble("管理游戏")
        game_parser = cmd2.Cmd2ArgumentParser(description=game_description)
        game_parser.add_subparsers(metavar="SUBCOMMAND", required=True)
        return game_parser

    @cmd2.with_argparser(_build_game_parser())
    def do_game(self, args: argparse.Namespace) -> None:
        args.cmd2_subcommand_func(args)

    @staticmethod
    def _build_game_screenshot_parser() -> cmd2.Cmd2ArgumentParser:
        game_screenshot_description = Text.assemble("截取游戏截图")
        game_screenshot_parser = cmd2.Cmd2ArgumentParser(description=game_screenshot_description)
        game_screenshot_parser.add_argument('--save', nargs='?', const='screenshot.png', default=None,
                                            help="保存截图到指定路径（默认 screenshot.png）")
        game_screenshot_parser.add_argument('--show', action="store_true", help="显示截图")
        game_screenshot_parser.add_argument('--background', action="store_true", help="在后台截取截图")
        return game_screenshot_parser

    @cmd2.as_subcommand_to("game", "screenshot", _build_game_screenshot_parser, help="截取游戏截图")
    def _game_screenshot(self, args: argparse.Namespace) -> None:
        if not args.save and not args.show:
            self.poutput("--save or --show is required")
            return
        try:
            img = OperatorFactory.get_operator().screenshot(background=args.background)
        except Exception as e:
            self.poutput(f"Failed to take screenshot: {e}")
            return
        if args.save:
            img.save(args.save)
            self.poutput(f"Screenshot saved to {args.save}")
        if args.show:
            img.show()

    @staticmethod
    def _build_game_ocr_parser() -> cmd2.Cmd2ArgumentParser:
        game_ocr_description = Text.assemble("执行 OCR 文字识别")
        game_ocr_parser = cmd2.Cmd2ArgumentParser(description=game_ocr_description)
        game_ocr_parser.add_argument('--region', nargs=4, type=float, metavar=('X1', 'Y1', 'X2', 'Y2'),
                                     help="识别区域坐标比例 (0-1)，格式: X1 Y1 X2 Y2")
        game_ocr_parser.add_argument('--json', action='store_true', help="以 JSON 格式输出")
        return game_ocr_parser

    @cmd2.as_subcommand_to("game", "ocr", _build_game_ocr_parser, help="执行 OCR 文字识别")
    def _game_ocr(self, args: argparse.Namespace) -> None:
        import json
        try:
            operator = OperatorFactory.get_operator()
            region = args.region
            result = operator.ocr(
                from_x=region[0] if region else None,
                from_y=region[1] if region else None,
                to_x=region[2] if region else None,
                to_y=region[3] if region else None
            )
            if args.json:
                self.poutput(json.dumps(result, ensure_ascii=False))
            else:
                self.poutput(result)
        except Exception as e:
            self.poutput(f"OCR Error: {e}")


    # endregion

    # region 其他命令
    def do_init(self, _: str):
        """Initialize the application: download resources and create default settings/config."""
        import io
        import json
        import os
        import zipfile
        from urllib.error import URLError, HTTPError
        from urllib.request import Request, urlopen

        from SRACore.models.tasks_config import TasksConfig
        from SRACore.util.const import AppDataDir, ConfigsDir

        url = f"https://github.com/Shasnow/StarRailAssistant/releases/download/v{VERSION}/StarRailAssistant_Resources_v{VERSION}.zip"
        # url = f"https://download.auto-mas.top/d/StarRailAssistant/StarRailAssistant_Resource_v{VERSION}.zip"
        self.poutput(f"Downloading resources from {url} ...")
        try:
            req = Request(url, headers={"User-Agent": "SRA-cli"})
            with urlopen(req) as resp:
                data = resp.read()
        except (URLError, HTTPError) as e:
            self.poutput(f"Failed to download resources: {e}")
            return True

        self.poutput("Extracting resources ...")
        cwd = os.getcwd()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(cwd)
        self.poutput(f"Resources extracted to {cwd}")

        # 创建设置文件
        AppDataDir.mkdir(parents=True, exist_ok=True)
        settings_path = AppDataDir / "settings.json"
        if not settings_path.exists():
            settings = AppSettings.from_dict({})
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings.to_dict(), f, indent=2, ensure_ascii=False)
            self.poutput(f"Created settings file: {settings_path}")
        else:
            self.poutput(f"Settings file already exists: {settings_path}")

        # 创建默认配置文件
        ConfigsDir.mkdir(parents=True, exist_ok=True)
        config_path = ConfigsDir / "Default.json"
        if not config_path.exists():
            config = TasksConfig.from_dict({"name": "Default"})
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            self.poutput(f"Created default config: {config_path}")
        else:
            self.poutput(f"Default config already exists: {config_path}")

        self.poutput("Initialization completed.")
        return True

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
