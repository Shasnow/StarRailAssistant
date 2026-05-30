import argparse
import os
import subprocess
import sys
from SRACore.localization import Resource
from SRACore.util.const import VERSION
from SRACore.util.data_persister import load_app_settings


def main():
    settings = load_app_settings()
    language: int = settings.Display.language
    Resource.set_language(language)
    parser = argparse.ArgumentParser(
        description=Resource.argparse_description,
        epilog=Resource.argparse_epilog,
        formatter_class=argparse.RawTextHelpFormatter
    )
    setup_argumentparser(parser)
    # 解析参数
    args = parser.parse_known_args()[0]
    if not is_admin():
        if args.no_admin:
            sys.argv.remove('--no-admin')  # 移除参数，不向下传递
            print(Resource.cli_noAdminWarning)
        else:
            restart_as_admin()
    from SRACore.util.logger import logger, setup_logger
    # 设置日志记录器
    setup_logger(level=args.log_level)
    logger.info(f"Current version: {VERSION}")
    logger.debug(f"cwd: {os.getcwd()}")

    if args.command:
        for cmd in args.command:
            sys.argv.remove(cmd)  # 移除命令参数, 避免重复执行
        cmd_str = " ".join(args.command).replace('&', '+')
        commands = cmd_str.split('+')
        for cmd in commands:
            sys.argv.append(cmd)
        print(sys.argv)
    inline = args.inline
    if inline:
        sys.argv.remove('--inline')
    # 延迟导入 SRACli
    from SRACore.cli2 import SRACli
    cli_instance = SRACli(settings=settings)
    # 配置交互式模式（隐藏提示符）
    if inline:
        cli_instance.intro = ''
        cli_instance.prompt = ''
    cli_instance.cmdloop()

def setup_argumentparser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--inline',
        action='store_true',
        help=Resource.argparse_inline_help
    )
    parser.add_argument(
         '--command', '-c', '--execute', '-e',
        nargs='*',
        type=str,
        help='The command to execute AFTER launch',
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'{VERSION}',
        help=Resource.argparse_version_help
    )
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'],
        default='TRACE',
        help=Resource.argparse_log_level_help
    )
    parser.add_argument(
        '--no-admin',
        action='store_true',
        help="Do not require admin privileges"
    )

def restart_as_admin():
    """
    以管理员权限重启当前进程
    """
    if sys.platform == 'win32' and not is_admin():
        import ctypes
        cmdline = subprocess.list2cmdline(sys.argv)
        result = ctypes.windll.shell32.ShellExecuteW(None, 'runas', 'wt.exe', f'"{sys.executable}" {cmdline}', None, 1)
        if result > 32:
            sys.exit(0)
        else:
            result = ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, cmdline, None, 1)
            sys.exit(result)

def is_admin() -> bool:
    """检查当前用户是否具有管理员权限（仅限 Windows）"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0  # NOQA
    except Exception as e:
        print(f"Error checking administrator privileges: {e}")
        return False

if __name__ == '__main__':
    main()
