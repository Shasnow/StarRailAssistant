import cmd
import multiprocessing
import threading
import time

from loguru import logger

from SRACore.localization.resource import Resource
from SRACore.thread.event_thread import EventListener
from SRACore.thread.task_thread import TaskManager
from SRACore.thread.trigger_thread import TriggerManager
from SRACore.util.config import load_settings
from SRACore.util.const import VERSION, CORE

class SRACli(cmd.Cmd):
    intro = Resource.cli_intro(version=VERSION, core=CORE)
    prompt = "sra> "

    def __init__(self):
        super().__init__()
        self.task_manager = TaskManager()
        self.task_process = None
        self.trigger_manager = TriggerManager()
        self.trigger_thread = threading.Thread(target=self.trigger_manager.run, daemon=True)
        self.trigger_thread.start()
        if not self.is_admin():
            logger.warning(Resource.cli_noAdminWarning)
        stop_hotkey:str = load_settings().get('StartStopHotkey')
        stop_hotkey=stop_hotkey.lower()  # 统一小写
        if stop_hotkey is None or stop_hotkey == '':
            stop_hotkey = 'f9'
        EventListener.register_key_event(stop_hotkey, self.do_task, "stop")
        EventListener.run()

    def default(self, line):
        print(Resource.cli_unknownCommand(line))

    def emptyline(self):
        pass

    def _get_command_help(self, cmd_name, detail=False) -> str:
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

    def do_EOF(self, arg):  # NOQA
        """Ctrl+D exit command line tool"""
        print()
        return self.do_exit(arg)

    def do_help(self, arg):
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

    def do_exit(self, _):
        """Exit command line tool"""
        if self.task_process and self.task_process.is_alive():
            self.task_process.terminate()
            self.task_process.join(timeout=5)
            if self.task_process.is_alive():
                logger.error(Resource.cli_exit_taskTimeout)

        if self.trigger_thread and self.trigger_thread.is_alive():
            self.trigger_manager.stop()  # 调用原类的停止逻辑
            self.trigger_thread.join(timeout=5)
            if self.trigger_thread.is_alive():
                logger.error(Resource.cli_exit_triggerTimeout)
        EventListener.stop()
        return True

    def do_task(self, arg: str):
        """Task manager command - support start/stop task process"""
        args = arg.split()
        if not args:
            print(Resource.cli_task_invalidArguments('task'))
            return
        command = args[0]
        if command == 'run':
            if self.task_process is not None and self.task_process.is_alive():
                print(Resource.cli_task_taskAlreadyRunning)
                return
            # 重新创建进程（避免重复启动已终止的进程）
            config_names = args[1:] if len(args) > 1 else tuple()
            self.task_process = multiprocessing.Process(target=self.task_manager.run, daemon=True, args=config_names)
            self.task_process.start()
            time.sleep(1)  # 确保进程有时间启动
            logger.info("[Start]")
        elif command == 'stop':
            if self.task_process is not None and self.task_process.is_alive():
                logger.warning(Resource.cli_task_interrupted)
                self.task_process.terminate()
                self.task_process.join(timeout=5)  # 增加超时，避免阻塞
                if self.task_process.is_alive():
                    logger.error(Resource.cli_task_timeout)
                else:
                    logger.info(Resource.cli_task_stopped)
            else:
                print(Resource.cli_task_notRunning)
        elif command == 'single':
            if len(args) < 2:
                print(Resource.cli_invalidArguments('task'))
                return
            if self.task_process is not None and self.task_process.is_alive():
                print(Resource.cli_task_taskAlreadyRunning)
                return
            sub_args = args[1:]
            # 重新创建进程（避免重复启动已终止的进程）
            self.task_process = multiprocessing.Process(target=self.task_manager.run_task, daemon=True, args=sub_args)
            self.task_process.start()
            time.sleep(1)  # 确保进程有时间启动
            logger.info("[Start]")
        else:
            print(Resource.cli_invalidArguments('task'))

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
            # 重新创建线程（避免重复启动已终止的线程）
            self.trigger_thread = threading.Thread(target=self.trigger_manager.run, daemon=True)
            self.trigger_thread.start()
            print(Resource.cli_trigger_started)
        elif command == 'stop':
            if self.trigger_thread.is_alive():
                self.trigger_manager.stop()
                self.trigger_thread.join(timeout=5)  # 增加超时
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
                print(Resource.cli_trigger_invalidArguments('trigger'))
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
                    logger.info(Resource.cli_trigger_attrSet(attr, trigger_name, value))
                    return
            print(Resource.cli_trigger_notFound(trigger_name))
        else:
            print(Resource.cli_invalidArguments('trigger'))

    def do_run(self, arg: str):
        """Run specified tasks, will block current command line until tasks complete"""
        args = arg.split()
        print(Resource.cli_run_started)
        try:
            self.task_manager.run(*args)
        except KeyboardInterrupt:
            return
        print(Resource.cli_run_started)

    def do_single(self, arg: str):
        """Run a single specified task, will block current command line until task complete"""
        args = arg.split()
        if len(args) < 1:
            print(Resource.invalidArguments('single'))
            return
        print(Resource.cli_run_started)
        try:
            self.task_manager.run_task(*args)
        except KeyboardInterrupt:
            return
        print(Resource.cli_run_started)

    def do_version(self, _):  # NOQA
        """Show version information"""
        print(f"{VERSION}")

    @staticmethod
    def is_admin() -> bool:
        """检查当前用户是否具有管理员权限（仅限 Windows）"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0  # NOQA
        except Exception as e:
            logger.debug(f"Error checking administrator privileges: {e}")
            return False
