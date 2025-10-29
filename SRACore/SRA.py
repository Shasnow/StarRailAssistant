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
        self.task_process = multiprocessing.Process(target=self.task_manager.run, daemon=True)
        self.trigger_manager = TriggerManager()
        self.trigger_thread = threading.Thread(target=self.trigger_manager.run, daemon=True)

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
                print(func.__doc__ or f"{arg} 命令没有帮助信息。")
            else:
                print(f"未知命令: {arg}")
        else:
            print("可用命令:")
            # 按命令名排序，更易读
            commands = [name[3:] for name in dir(self) if name.startswith("do_")]
            for cmd_name in sorted(commands):
                doc = getattr(self, f"do_{cmd_name}").__doc__ or "无帮助信息"
                print(f"  {cmd_name} - {doc}")

    def do_exit(self, arg):
        """退出命令行工具"""
        # 退出前尝试停止所有进程和线程
        if self.task_process.is_alive():
            self.task_process.terminate()
            self.task_process.join()
        if self.trigger_thread.is_alive():
            self.trigger_manager.stop()
            self.trigger_thread.join()
        print("退出程序")
        return True

    def do_task(self, arg: str):
        """任务管理：run（启动）/ stop（停止）"""
        args = arg.split()
        if not args:
            print("用法: task <run|stop>")
            return
        command = args[0]
        if command == 'run':
            if self.task_process.is_alive():
                print("TaskManager 已在运行中。")
                return
            # 重新创建进程（避免重复启动已终止的进程）
            self.task_process = multiprocessing.Process(target=self.task_manager.run, daemon=True)
            self.task_process.start()
            time.sleep(1)  # 确保进程有时间启动
            print("TaskManager 已启动。")
        elif command == 'stop':
            if self.task_process.is_alive():
                self.task_process.terminate()
                self.task_process.join(timeout=5)  # 增加超时，避免阻塞
                if self.task_process.is_alive():
                    print("警告：TaskManager 强制终止超时。")
                else:
                    print("TaskManager 已停止。")
            else:
                print("TaskManager 未在运行中。")
        else:
            print(f"未知的 task 子命令 '{command}'，可用子命令：run, stop")

    def do_trigger(self, arg: str):
        """触发器管理：run（启动）/ stop（停止）/ enable <名称>（启用）/ disable <名称>（禁用）"""
        args = arg.split()
        if not args:
            print("用法: trigger <run|stop|enable|disable> [参数]")
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
        else:
            print(f"未知的 trigger 子命令 '{command}'，可用子命令：run, stop, enable, disable")