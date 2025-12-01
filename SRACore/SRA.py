import cmd
import multiprocessing
import threading
import time

from loguru import logger

from SRACore.thread.task_thread import TaskManager
from SRACore.thread.trigger_thread import TriggerManager
from SRACore.util.const import VERSION, CORE
from SRACore.util.i18n import t


class SRACli(cmd.Cmd):
    intro = t('cli.intro', version=VERSION, core=CORE)
    prompt = t('cli.prompt')

    def __init__(self):
        super().__init__()
        self.task_manager = TaskManager()
        self.task_process = None
        self.trigger_manager = TriggerManager()
        self.trigger_thread = threading.Thread(target=self.trigger_manager.run, daemon=True)
        self.trigger_thread.start()
        if not self.is_admin():
            logger.warning(t('cli.no_admin_warning'))

    def default(self, line):
        print(t('cli.unknown_command', line=line))

    def emptyline(self):
        pass

    def _get_command_help(self, cmd_name):
        """获取命令的帮助文本"""
        help_key = f'cli.help_{cmd_name}'
        help_text = t(help_key)
        # 如果翻译键不存在，返回原始docstring
        if help_text == help_key:
            func = getattr(self, f"do_{cmd_name}", None)
            if func and func.__doc__:
                return func.__doc__.split('\n')[0]
            return t('cli.help_no_doc')
        return help_text

    def do_EOF(self, arg):
        """Ctrl+D exit command line tool"""
        return self.do_exit(arg)

    def do_help(self, arg):
        """Show help information"""
        if arg:
            func = getattr(self, f"do_{arg}", None)
            if func:
                help_text = self._get_command_help(arg)
                print(f"  {arg} - {help_text}")
            else:
                print(t('cli.help_unknown', cmd=arg))
        else:
            print(t('cli.help_title'))
            # 按命令名排序，更易读
            commands = [name[3:] for name in dir(self) if name.startswith("do_")]
            for cmd_name in sorted(commands):
                help_text = self._get_command_help(cmd_name)
                print(f"  {cmd_name} - {help_text}")
            print("\n" + t('cli.help_detail'))

    def do_exit(self, _):
        """Exit command line tool"""
        if self.task_process and self.task_process.is_alive():
            self.task_process.terminate()
            self.task_process.join(timeout=5)
            if self.task_process.is_alive():
                logger.error(t('cli.task_timeout'))

        if self.trigger_thread and self.trigger_thread.is_alive():
            self.trigger_manager.stop()  # 调用原类的停止逻辑
            self.trigger_thread.join(timeout=5)
            if self.trigger_thread.is_alive():
                logger.error(t('cli.trigger_timeout'))
        return True

    def do_task(self, arg: str):
        """Task manager command - support start/stop task process"""
        args = arg.split()
        if not args:
            print(t('cli.task_usage'))
            return
        command = args[0]
        if command == 'run':
            if self.task_process is not None and self.task_process.is_alive():
                print(t('cli.task_already_running'))
                return
            # 重新创建进程（避免重复启动已终止的进程）
            config_names = args[1:] if len(args) > 1 else tuple()
            self.task_process = multiprocessing.Process(target=self.task_manager.run, daemon=True, args=config_names)
            self.task_process.start()
            time.sleep(1)  # 确保进程有时间启动
            logger.info(t('cli.task_started'))
        elif command == 'stop':
            if self.task_process.is_alive():
                logger.debug(t('cli.task_abort'))
                self.task_process.terminate()
                self.task_process.join(timeout=5)  # 增加超时，避免阻塞
                if self.task_process.is_alive():
                    logger.error(t('cli.task_timeout'))
                else:
                    logger.debug(t('cli.task_stopped'))
            else:
                print(t('cli.task_not_running'))
        else:
            print(t('cli.task_unknown_subcommand', command=command))

    def do_trigger(self, arg: str):
        """Trigger manager command - support start/stop/configure triggers"""
        args = arg.split()
        if not args:
            print(t('cli.trigger_usage'))
            return
        command = args[0]
        if command == 'run':
            if self.trigger_thread.is_alive():
                print(t('cli.trigger_already_running'))
                return
            # 重新创建线程（避免重复启动已终止的线程）
            self.trigger_thread = threading.Thread(target=self.trigger_manager.run, daemon=True)
            self.trigger_thread.start()
            print(t('cli.trigger_started'))
        elif command == 'stop':
            if self.trigger_thread.is_alive():
                self.trigger_manager.stop()
                self.trigger_thread.join(timeout=5)  # 增加超时
                if self.trigger_thread.is_alive():
                    logger.error(t('cli.trigger_timeout'))
                else:
                    logger.debug(t('cli.trigger_stopped'))
            else:
                print(t('cli.trigger_not_running'))
        elif command == 'enable':
            if len(args) < 2:
                print(t('cli.trigger_enable_usage'))
                return
            trigger_name = args[1]
            for trigger in self.trigger_manager.triggers:
                if trigger.__class__.__name__.lower() == trigger_name.lower():
                    trigger.set_enable(True)
                    logger.info(t('cli.trigger_enabled', name=trigger_name))
                    return
            print(t('cli.trigger_not_found', name=trigger_name))
        elif command == 'disable':
            if len(args) < 2:
                print(t('cli.trigger_disable_usage'))
                return
            trigger_name = args[1]
            for trigger in self.trigger_manager.triggers:
                if trigger.__class__.__name__.lower() == trigger_name.lower():
                    trigger.set_enable(False)
                    logger.info(t('cli.trigger_disabled', name=trigger_name))
                    return
            print(t('cli.trigger_not_found', name=trigger_name))
        elif command.startswith('set-'):
            if len(args) < 3:
                print(t('cli.trigger_set_usage'))
                return
            _type = command[4:]
            trigger_name = args[1]
            attr = args[2]
            value = args[3]
            for trigger in self.trigger_manager.triggers:
                if trigger.__class__.__name__.lower() == trigger_name.lower():
                    if not hasattr(trigger, attr):
                        print(t('cli.trigger_attr_not_found', name=trigger_name, attr=attr))
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
                        print(t('cli.trigger_unknown_type', type=_type))
                        return
                    logger.info(t('cli.trigger_attr_set', name=trigger_name, attr=attr, value=value))
                    return
            print(t('cli.trigger_not_found', name=trigger_name))
        else:
            print(t('cli.trigger_unknown_subcommand', command=command))

    def do_run(self, arg: str):
        """Run specified tasks, will block current command line until tasks complete"""
        args = arg.split()
        print(t('cli.run_blocking'))
        try:
            self.task_manager.run(*args)
        except KeyboardInterrupt:
            return
        print(t('cli.run_completed'))

    def do_version(self, _):
        """Show version information"""
        print(f"{VERSION}")

    @staticmethod
    def is_admin() -> bool:
        """检查当前用户是否具有管理员权限（仅限 Windows）"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0  # NOQA
        except Exception as e:
            logger.error(t('cli.admin_check_error', error=e))
            return False
