import cmd
import os

from rich.console import Console

from SRACore.utils.Logger import logger
from SRACore.utils.const import CORE

logger.success("正在以命令行模式运行 SRA")
console = Console()
print = console.print


class CommandLine(cmd.Cmd):
    intro = f"SRAv{CORE}\n欢迎使用 SRA 命令行模式！输入 help 或 ? 查看帮助信息。"
    prompt = "SRA> "

    def do_exit(self, _):
        """退出命令行模式"""
        print("正在退出 SRA 命令行模式...", style="yellow")
        return True

    def default(self, line):
        """处理未识别的命令"""
        print(f"[red]未知命令: {line}[/red]")
        print("输入 help 或 ? 查看帮助信息。")

    def do_help(self, arg):
        """显示帮助信息"""
        if arg:
            # 如果指定了具体命令，显示该命令的帮助信息
            func = getattr(self, f"do_{arg}", None)
            if func:
                print(func.__doc__ or f"{arg} 命令没有帮助信息。")
            else:
                print(f"[red]未知命令: {arg}[/red]")
        else:
            # 显示所有命令的列表
            print("[bold green]可用命令:[/bold green]")
            for name in dir(self):
                if name.startswith("do_"):
                    print(f"  {name[3:]} - {getattr(self, name).__doc__ or '无帮助信息'}")

    def do_echo(self, arg):
        """回显输入的内容"""
        if arg:
            print(arg, style="cyan")

    def do_cls(self, _):
        """清屏"""
        os.system("cls" if os.name == "nt" else "clear")

    def do_config(self, arg):
        """显示指定配置"""
        if not arg:
            arg = 'Default'
        from SRACore.utils.Configure import load
        try:
            config = load(f"data/config-{arg}.json")
        except FileNotFoundError:
            print(f"[red]配置文件 data/config-{arg}.json 未找到。请检查配置名称是否正确。[/red]")
            return
        if config:
            print(f"[bold yellow]当前配置 {arg}:[/bold yellow]")
            for key, value in config.items():
                print(f"  {key}: {value}")
        else:
            print("未找到配置文件或配置为空。")

    def do_globals(self, _):
        """显示全局配置"""
        from SRACore.utils.Configure import load
        try:
            config = load("data/globals.json")
        except FileNotFoundError:
            print("[red]全局配置文件 data/globals.json 未找到。[/red]")
            return
        if config:
            print("[bold yellow]全局配置:[/bold yellow]")
            for key, value in config.items():
                print(f"  {key}: {value}")
        else:
            print("[red]全局配置为空。")

    def do_run(self, args:str=None):
        """运行指定配置的任务"""
        global i
        args=args.split()
        if len(args) == 0:
            args.append("Default")
        try:
            logger.warning(f"即将开始执行任务, 当前配置: {args} , 终端将被任务占用！")
            from .SRAssistant import Assistant
            assistant = Assistant("")
            for i in args:
                assistant.assist_start(i)
        except FileNotFoundError:
            print(f"[red]配置文件 data/config-{i}.json 未找到。请检查配置名称是否正确。[/red]")
        except KeyboardInterrupt:
            print("[red]已中断运行。[/red]")

    def do_version(self, _):
        """显示当前 SRA 版本"""
        from SRACore.utils.Configure import load
        version = load("version.json")
        if version:
            print(f"[bold green]当前 SRA 版本: {version['version']}[/bold green]")
            print(f"更新日志: {version['announcement']}")
        else:
            print("[red]无法获取版本信息。[/red]")
