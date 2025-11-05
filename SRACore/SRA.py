import cmd
import multiprocessing
import threading
import time

from SRACore.thread.task_thread import TaskManager
from SRACore.thread.trigger_thread import TriggerManager


class SRACli(cmd.Cmd):
    prompt = "sra> "  # 增加命令提示符，提升交互体验

    def __init__(self):
        super().__init__()
        self.task_manager = TaskManager()
        self.task_process = None
        self.trigger_manager = TriggerManager()
        self.trigger_thread = threading.Thread(target=self.trigger_manager.run, daemon=True)
        self.trigger_thread.start()

    def default(self, line):
        print(f"未知命令: '{line}'. 输入 'help' 获取可用命令列表。")

    def emptyline(self):
        pass

    def do_EOF(self, arg):
        """Ctrl+D 退出命令行工具"""
        return self.do_exit(arg)

    def do_help(self, arg):
        """显示帮助信息"""
        if arg:
            func = getattr(self, f"do_{arg}", None)
            if func:
                print(f"  {arg} - {func.__doc__ or '没有帮助信息'}")
            else:
                print(f"未知命令: {arg}")
        else:
            print("可用命令:")
            # 按命令名排序，更易读
            commands = [name[3:] for name in dir(self) if name.startswith("do_")]
            for cmd_name in sorted(commands):
                doc: str = getattr(self, f"do_{cmd_name}").__doc__ or "无帮助信息"
                print(f"  {cmd_name} - {doc.split('\n')[0]}")
            print("\n输入 'help <命令名>' 查看详细用法（例：help trigger）")

    def do_exit(self, _):
        """退出命令行工具"""
        # 退出前尝试停止所有进程和线程
        print("\n正在清理资源...")
        # 1. 停止任务进程
        if self.task_process and self.task_process.is_alive():
            print(f"正在停止 TaskManager（进程ID: {self.task_process.pid}）...")
            self.task_process.terminate()
            self.task_process.join(timeout=5)
            if self.task_process.is_alive():
                print("警告：TaskManager 强制终止超时，可能存在资源泄漏。")
            else:
                print("TaskManager 已成功停止。")

        # 2. 停止触发器线程
        if self.trigger_thread and self.trigger_thread.is_alive():
            print("正在停止 TriggerManager...")
            self.trigger_manager.stop()  # 调用原类的停止逻辑
            self.trigger_thread.join(timeout=5)
            if self.trigger_thread.is_alive():
                print("警告：TriggerManager 停止超时，可能未响应停止信号。")
            else:
                print("TriggerManager 已成功停止。")
        print("资源清理完成，退出程序。")
        return True

    def do_task(self, arg: str):
        """任务管理器命令 - 支持启动/停止任务进程
        用法：
          task run    - 启动 TaskManager（自动检测是否已运行）
          task stop   - 停止正在运行的 TaskManager
        示例：
          sra> task run    # 启动任务进程
        """
        args = arg.split()
        if not args:
            print("用法: task <run|stop>")
            return
        command = args[0]
        if command == 'run':
            if self.task_process is not None and self.task_process.is_alive():
                print("TaskManager 已在运行中。")
                return
            # 重新创建进程（避免重复启动已终止的进程）
            config_names = args[1:] if len(args) > 1 else tuple()
            self.task_process = multiprocessing.Process(target=self.task_manager.run, daemon=True, args=config_names)
            self.task_process.start()
            time.sleep(1)  # 确保进程有时间启动
            print("TaskManager 已启动。")
        elif command == 'stop':
            if self.task_process.is_alive():
                self.task_process.terminate()
                self.task_process.join(timeout=5)  # 增加超时，避免阻塞
                if self.task_process.is_alive():
                    print("Error: TaskManager 强制终止超时。")
                else:
                    print("[Done] TaskManager 已停止。")
            else:
                print("TaskManager 未在运行中。")
        else:
            print(f"未知的 task 子命令 '{command}'，可用子命令：run, stop")

    def do_trigger(self, arg: str):
        """触发器管理器命令 - 支持启动/停止/配置触发器
        用法：
          trigger run                - 启动 TriggerManager 线程
          trigger stop               - 停止 TriggerManager 线程
          trigger enable <名称>       - 启用指定触发器
          trigger disable <名称>      - 禁用指定触发器
          trigger set-<类型> <名> <属性> <值> - 设置属性（支持类型：int/float/str/bool）
            示例：
              trigger set-int  TimerTrigger interval 30    # 整数类型
              trigger set-bool TimerTrigger enable true     # 布尔类型
              trigger set-str  LogTrigger path /var/log     # 字符串类型
        说明：
          - 触发器名称不区分大小写（例：TimerTrigger 和 timetrigger 等效）
          - 布尔值支持：true/1/yes（真）、false/0/no（假）
        """
        args = arg.split()
        if not args:
            print("用法: trigger <run|stop|enable|disable|set> [参数]")
            return
        command = args[0]
        if command == 'run':
            if self.trigger_thread.is_alive():
                print("TriggerManager 已在运行中。")
                return
            # 重新创建线程（避免重复启动已终止的线程）
            self.trigger_thread = threading.Thread(target=self.trigger_manager.run, daemon=True)
            self.trigger_thread.start()
            print("TriggerManager 已启动。")
        elif command == 'stop':
            if self.trigger_thread.is_alive():
                self.trigger_manager.stop()
                self.trigger_thread.join(timeout=5)  # 增加超时
                if self.trigger_thread.is_alive():
                    print("警告：TriggerManager 停止超时（可能未正确响应停止信号）。")
                else:
                    print("TriggerManager 已停止。")
            else:
                print("TriggerManager 未在运行中。")
        elif command == 'enable':
            if len(args) < 2:
                print("用法: trigger enable <trigger_name>")
                return
            trigger_name = args[1]
            for trigger in self.trigger_manager.triggers:
                if trigger.__class__.__name__.lower() == trigger_name.lower():
                    trigger.set_enable(True)
                    print(f"触发器 {trigger_name} 已启用。")
                    return
            print(f"未找到触发器 {trigger_name}。")
        elif command == 'disable':
            if len(args) < 2:
                print("用法: trigger disable <trigger_name>")
                return
            trigger_name = args[1]
            for trigger in self.trigger_manager.triggers:
                if trigger.__class__.__name__.lower() == trigger_name.lower():
                    trigger.set_enable(False)
                    print(f"触发器 {trigger_name} 已禁用。")
                    return
            print(f"未找到触发器 {trigger_name}。")
        elif command.startswith('set-'):
            if len(args) < 3:
                print("用法: trigger set-<类型> <trigger_name> <属性> <值>")
                return
            _type = command[4:]
            trigger_name = args[1]
            attr = args[2]
            value = args[3]
            for trigger in self.trigger_manager.triggers:
                if trigger.__class__.__name__.lower() == trigger_name.lower():
                    if not hasattr(trigger, attr):
                        print(f"触发器 {trigger_name} 不存在属性 {attr}。")
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
                        print(f"未知的属性类型 {_type}，支持的类型有：int, float, str, bool")
                        return
                    print(f"触发器 {trigger_name} 的属性 {attr} 已设置为 {value}。")
                    return
            print(f"未找到触发器 {trigger_name}。")
        else:
            print(f"未知的 trigger 子命令 '{command}'，可用子命令：run, stop, enable, disable, set-<类型>")

    def do_run(self, arg: str):
        """运行指定任务，会阻塞当前命令行直到任务完成。
        用法：
          run [配置文件名称...]
        说明：
            - 如果不指定配置文件名称，则运行缓存中的所有配置。
            - 可以指定一个或多个配置文件名称，空格分隔。
            - 除了退出程序外，运行过程中无法中断任务。
        示例：
            sra> run DefaultConfig
            sra> run Config1 Config2
            sra> run
        """
        args = arg.split()
        print("运行任务中，当前命令行将被阻塞，直到任务完成...")
        try:
            self.task_manager.run(*args)
        except KeyboardInterrupt:
            return
        print("任务运行完成，返回命令行。")
