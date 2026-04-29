# type: ignore
import cmd
import pprint
import threading
from collections.abc import Callable
from typing import Any
from loguru import logger

from SRACore.localization import Resource
from SRACore.models.app_settings import AppSettings
from SRACore.runtime.event_listener import KeyboardListener
from SRACore.thread.task_process import TaskManager
from SRACore.runtime.trigger_manager import TriggerManager
from SRACore.util.const import VERSION, CORE
from SRACore.util.data_persister import load_config


class SRACli(cmd.Cmd):
    intro = Resource.cli_intro(version=VERSION, core=CORE)
    prompt = "sra> "

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings or {}
        self.task_manager = TaskManager()
        self.task_thread = None
        self.trigger_manager = TriggerManager()
        self.trigger_thread = threading.Thread(target=self.trigger_manager.run, daemon=True)
        self.trigger_thread.start()
        if not self.is_admin():
            logger.warning(Resource.cli_noAdminWarning)
        stop_hotkey: str = settings.General.hotkeyStop
        if stop_hotkey == '':
            stop_hotkey = 'f9'

        self.event_listener = KeyboardListener()
        self.event_listener.register_key_event(stop_hotkey, self.do_task, "stop")
        self.event_listener.start()

    def default(self, line: str):
        print(Resource.cli_unknownCommand(line))

    def emptyline(self) -> bool:
        return False

    def do_config(self, name):
        if name == 'settings':
            pprint.pprint(self.settings)
        else:
            pprint.pprint(load_config(name))

    def _get_command_help(self, cmd_name: str, detail: bool = False) -> str:
        """
        获取指定命令的帮助信息
        先尝试从本地化资源中获取帮助文本，如果不存在则使用方法的docstring。
        :param cmd_name: 命令名称
        :param detail: 是否获取详细帮助
        :return: str
        """
        help_key = f'cli.{cmd_name}.help' if not detail else f'cli.help.{cmd_name}'
        help_text = Resource.get_translation(help_key)
        # 如果翻译键不存在，返回原始docstring
        if help_text == help_key:
            func = getattr(self, f"do_{cmd_name}", None)
            if func and func.__doc__:
                return func.__doc__.split('\n')[0]
            return ""
        return help_text

    def _run_task_target(self, target: Callable[..., Any], *target_args: str) -> None:
        try:
            target(*target_args)
        except KeyboardInterrupt:
            self.task_manager.request_stop()

    def _start_task_thread(self, target: Callable[..., Any], *target_args: str) -> None:
        self.task_thread = threading.Thread(
            target=self._run_task_target,
            daemon=True,
            args=(target, *target_args)
        )
        self.task_thread.start()

    def _stop_task_thread(self) -> None:
        if self.task_thread is not None and self.task_thread.is_alive():
            logger.warning(Resource.cli_task_requestStop)
            self.task_manager.request_stop()
            self.task_thread.join(timeout=30)
            if self.task_thread.is_alive():
                logger.warning(Resource.cli_task_timeout)
            else:
                logger.info(Resource.cli_task_stopped)
        else:
            print(Resource.cli_task_notRunning)

    def _execute_task_command(self, command: str, command_args: tuple[str, ...], *, threaded: bool) -> None:
        if command == 'run':
            if threaded:
                if self.task_thread is not None and self.task_thread.is_alive():
                    print(Resource.cli_task_taskAlreadyRunning)
                    return
                self._start_task_thread(self.task_manager.run, *command_args)
                return

            print(Resource.cli_run_started)
            try:
                self.task_manager.run(*command_args)
            except KeyboardInterrupt:
                self.task_manager.request_stop()
                return
            print(Resource.cli_run_started)
            return

        if command == 'single':
            if not command_args:
                print(Resource.cli_invalidArguments('task' if threaded else 'single'))
                return
            if threaded:
                if self.task_thread is not None and self.task_thread.is_alive():
                    print(Resource.cli_task_taskAlreadyRunning)
                    return
                self._start_task_thread(self.task_manager.run_task, *command_args)
                return

            print(Resource.cli_run_started)
            try:
                self.task_manager.run_task(*command_args)
            except KeyboardInterrupt:
                self.task_manager.request_stop()
                return
            print(Resource.cli_run_started)
            return

        if command == 'stop' and threaded:
            self._stop_task_thread()
            return

        print(Resource.cli_invalidArguments('task'))

    def do_EOF(self, arg: Any):  # NOQA
        """Ctrl+D exit command line tool"""
        print()
        return self.do_exit(arg)

    def do_help(self, arg: str):
        """Show help information"""
        if arg:
            func = getattr(self, f"do_{arg}", None)
            if func:
                help_text = self._get_command_help(arg, True)
                print(help_text)
            else:
                print(Resource.cli_help_unknownCommand(arg))
        else:
            print(Resource.cli_helpTitle)
            # 按命令名排序，更易读
            commands = [name[3:] for name in dir(self) if name.startswith("do_")]
            for cmd_name in sorted(commands):
                help_text = self._get_command_help(cmd_name)
                print(f"  {cmd_name} - {help_text}")
            print(Resource.cli_helpFooter)

    def do_exit(self, _: Any):
        """Exit command line tool"""
        self.task_manager.request_stop()
        if self.task_thread and self.task_thread.is_alive():
            self.task_thread.join(timeout=5)
            if self.task_thread.is_alive():
                logger.error(Resource.cli_exit_taskTimeout)

        if self.trigger_thread and self.trigger_thread.is_alive():
            self.trigger_manager.stop()  # 调用原类的停止逻辑
            self.trigger_thread.join(timeout=5)
            if self.trigger_thread.is_alive():
                logger.error(Resource.cli_exit_triggerTimeout)

        self.event_listener.stop()
        return True

    def do_task(self, arg: str):
        """Task manager command - support start/stop task process"""
        args = arg.split()
        if not args:
            print(Resource.cli_invalidArguments('task'))
            return
        self._execute_task_command(args[0], tuple(args[1:]), threaded=True)

    def do_trigger(self, arg: str):
        """Trigger manager command - support start/stop/configure triggers"""
        args = arg.split()
        if not args:
            print(Resource.cli_invalidArguments('trigger'))
            return
        command = args[0]
        if command == 'run':
            if self.trigger_thread.is_alive():
                print(Resource.cli_trigger_alreadyRunning)
                return
            self.trigger_thread = threading.Thread(target=self.trigger_manager.run, daemon=True)
            self.trigger_thread.start()
            print(Resource.cli_trigger_started)
        elif command == 'stop':
            if self.trigger_thread.is_alive():
                self.trigger_manager.stop()
                self.trigger_thread.join(timeout=5)
                if self.trigger_thread.is_alive():
                    logger.error(Resource.cli_trigger_timeout)
                else:
                    logger.info(Resource.cli_trigger_stopped)
            else:
                print(Resource.cli_trigger_notRunning)
        elif command == 'enable':
            if len(args) < 2:
                print(Resource.cli_invalidArguments('trigger'))
                return
            trigger_name = args[1]
            for trigger in self.trigger_manager.triggers:
                if trigger.__class__.__name__.lower() == trigger_name.lower():
                    trigger.set_enable(True)
                    logger.info(Resource.cli_trigger_enabled(trigger_name))
                    return
            print(Resource.cli_trigger_notFound(trigger_name))
        elif command == 'disable':
            if len(args) < 2:
                print(Resource.cli_invalidArguments('trigger'))
                return
            trigger_name = args[1]
            for trigger in self.trigger_manager.triggers:
                if trigger.__class__.__name__.lower() == trigger_name.lower():
                    trigger.set_enable(False)
                    logger.info(Resource.cli_trigger_disabled(trigger_name))
                    return
            print(Resource.cli_trigger_notFound(trigger_name))
        elif command.startswith('set-'):
            if len(args) < 3:
                print(Resource.cli_invalidArguments('trigger'))
                return
            _type = command[4:]
            trigger_name = args[1]
            attr = args[2]
            value = args[3]
            for trigger in self.trigger_manager.triggers:
                if trigger.__class__.__name__.lower() == trigger_name.lower():
                    if not hasattr(trigger, attr):
                        print(Resource.cli_trigger_attrNotFound(attr, trigger_name))
                        return
                    if _type == 'int':
                        setattr(trigger, attr, int(value))
                    elif _type == 'float':
                        setattr(trigger, attr, float(value))
                    elif _type == 'str':
                        setattr(trigger, attr, value)
                    elif _type == 'bool':
                        setattr(trigger, attr, value.lower() in ['true', '1', 'yes'])
                    else:
                        print(Resource.cli_trigger_unknownType(_type))
                        return
                    logger.info(Resource.cli_trigger_attrSet(trigger_name, attr, value))
                    return
            print(Resource.cli_trigger_notFound(trigger_name))
        else:
            print(Resource.cli_invalidArguments('trigger'))

    def do_run(self, arg: str):
        """Run specified tasks, will block current command line until tasks complete"""
        self._execute_task_command('run', tuple(arg.split()), threaded=False)

    def do_single(self, arg: str):
        """Run a single specified task, will block current command line until task complete"""
        self._execute_task_command('single', tuple(arg.split()), threaded=False)

    def do_version(self, _):  # NOQA
        """Show version information"""
        print(f"{VERSION}")

    def do_notify(self, arg: str):
        """Notification command - support test email/webhook/telegram/serverchan/onebot notification"""
        args = arg.split()
        if not args:
            print(Resource.cli_invalidArguments('notify'))
            return

        command = args[0]
        if command == 'test-email':
            from SRACore.util.notify import send_test_email
            send_test_email()
        elif command == 'test' and len(args) >= 2:
            channel = args[1]
            from SRACore.util.data_persister import load_settings
            import SRACore.util.notify as _notify_mod
            from SRACore.util.notify import (
                _build_notification_data,
                _get_test_image_bytes,
                send_webhook_notification,
                send_telegram_notification,
                send_serverchan_notification,
                send_onebot_notification,
                send_bark_notification,
                send_feishu_notification,
                send_wecom_notification,
                send_dingtalk_notification,
                send_discord_notification,
                send_xxtui_notification,
            )
            settings = load_settings("notifications")
            data = _build_notification_data("notify.test", "这是一条测试通知", "success")

            # 支持图片的渠道：若开关开启则用 SRA 图标替代截图
            _send_image_keys = {
                "telegram": "telegram.sendImage",
                "onebot":   "onebot.sendImage",
                "wecom":    "wecom.sendImage",
                "discord":  "discord.sendImage",
            }
            _orig_bytes  = _notify_mod._take_screenshot_bytes
            _orig_base64 = _notify_mod._take_screenshot_base64
            if channel in _send_image_keys and settings.get(_send_image_keys[channel], False):
                _icon = _get_test_image_bytes()
                if _icon:
                    import base64 as _b64
                    _notify_mod._take_screenshot_bytes  = lambda: _icon
                    _notify_mod._take_screenshot_base64 = lambda: _b64.b64encode(_icon).decode()

            _ch_map = {
                "webhook":   (send_webhook_notification,   "Webhook"),
                "telegram":  (send_telegram_notification,  "Telegram"),
                "serverchan":(send_serverchan_notification, "ServerChan"),
                "onebot":    (send_onebot_notification,     "OneBot"),
                "bark":      (send_bark_notification,       "Bark"),
                "feishu":    (send_feishu_notification,     "飞书"),
                "wecom":     (send_wecom_notification,      "企业微信"),
                "dingtalk":  (send_dingtalk_notification,   "钉钉"),
                "discord":   (send_discord_notification,    "Discord"),
                "xxtui":     (send_xxtui_notification,      "xxtui"),
            }
            if channel in _ch_map:
                fn, label = _ch_map[channel]
                result = fn(data, settings)
                print(label + " 测试通知发送" + ("成功" if result else "失败"))
            else:
                print(Resource.cli_invalidArguments("notify"))

            # 还原 screenshot 函数
            _notify_mod._take_screenshot_bytes  = _orig_bytes
            _notify_mod._take_screenshot_base64 = _orig_base64
        else:
            print(Resource.cli_invalidArguments('notify'))

    @staticmethod
    def is_admin() -> bool:
        """检查当前用户是否具有管理员权限（仅限 Windows）"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0  # NOQA
        except Exception as e:
            logger.debug(f"Error checking administrator privileges: {e}")
            return False
