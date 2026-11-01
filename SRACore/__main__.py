import argparse
import os
import subprocess
import sys

sys.path.append(os.getcwd())  # 将当前工作目录添加到 sys.path，以便导入 tasks

from SRACore.localization import Resource
from SRACore.localization.presentation import translate
from SRACore.services.setting_service import SettingsService
from SRACore.util.const import VERSION, AppDataDir, CacheDir, ConfigsDir, LogsDir, SettingsJson
from SRACore.util.standard_io import configure_standard_streams


def main():
    # Must precede argparse output and cmd2/Rich/logging stream capture.
    configure_standard_streams()
    settings = SettingsService()
    language: int = settings.settings.Display.Language
    Resource.set_language(language)
    parser = argparse.ArgumentParser(
        description=Resource.argparse_description,
        epilog=Resource.argparse_epilog,
        formatter_class=argparse.RawTextHelpFormatter
    )
    setup_argumentparser(parser)
    # 解析参数
    args = parser.parse_known_args()[0]
    if args.subcommand:
        if subcommand_handler(args.subcommand, args.rest):
            return
    if args.no_admin:
        sys.argv.remove('--no-admin')  # 移除参数，不向下传递（无论是否已是管理员）
    if not is_admin():
        if args.no_admin:
            print(Resource.cli_noAdminWarning)
        else:
            restart_as_admin()
    # 构造进程内宿主：统一负责日志、tasks/extensions 动态导入与任务/扩展编排
    from SRACore.services import AppContext
    context = AppContext(log_level=args.log_level)
    from SRACore.util.logger import logger
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
    if args.inline:
        sys.argv.remove('--inline')
    # 延迟导入 SRACli
    from SRACore.cli2 import SRACli
    cli_instance = SRACli(context)
    # 配置交互式模式（隐藏提示符）
    if args.inline:
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
        help=translate('The command to execute AFTER launch'),
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
        help=translate("Do not require admin privileges")
    )

    parser.add_argument(
        'subcommand',
        type=str,
        nargs='?',
        default='',
        metavar=f'{{{",".join(subcommands.keys())}}}',
        help=translate("Subcommands, type '{subcommand} --help' for more information")
    )

    parser.add_argument(
        'rest',
        nargs=argparse.REMAINDER,
        help=argparse.SUPPRESS
    )


def subcommand_handler(subcommand: str, rest: list) -> bool:
    """处理子命令"""
    if subcommand in subcommands:
        parser, func = subcommands[subcommand]  # 值为 (解析器, 处理函数) 的单个元组
        args = parser().parse_args(rest)
        return func(args)
    return False


def where_parser() -> argparse.ArgumentParser:
    """返回路径查找解析器"""
    parser = argparse.ArgumentParser(
        prog=f'{os.path.basename(sys.argv[0])} where',
        description=translate('Find the path of the executable file or a directory'),
    )
    parser.add_argument(
        'path',
        type=str,
        nargs='?',
        choices=['configs', 'logs', 'cache', 'data', 'settings', ''],
        default='',
        help=translate('The path to find'),
    )
    return parser


def where(args: argparse.Namespace) -> bool:
    """查找路径"""
    paths = {
        '': sys.executable,
        'configs': str(ConfigsDir),
        'logs': str(LogsDir),
        'cache': str(CacheDir),
        'data': str(AppDataDir),
        'settings': str(SettingsJson),
    }
    if args.path in paths:
        print(paths[args.path])
    else:
        print(f'Unknown path: {args.path}, available paths: {",".join(paths.keys())}')
    return True

def serve_parser() -> argparse.ArgumentParser:
    """返回服务器解析器"""
    parser = argparse.ArgumentParser(
        prog=f'{os.path.basename(sys.argv[0])} serve',
        description=translate('Start the SRA server'),
    )
    parser.add_argument(
        '--host',
        action='store_true',
        help=translate('Expose the server to the public network'),
    )
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help=translate('The port to use'),
    )
    parser.add_argument(
        '--no-webui',
        action='store_true',
        help=translate('Do not host the WebUI static files'),
    )
    return parser

def serve(args: argparse.Namespace) -> bool:
    """启动服务端（与 ``sra-server`` 共用 ``SRAServer.run_server``，进程内运行）。"""
    from SRAServer.__main__ import run_server
    run_server(host=args.host, port=args.port, webui=False if args.no_webui else None)
    return True


subcommands = {
    'where': (where_parser, where),
    'serve': (serve_parser, serve),
}


# noinspection unresolved-references
def restart_as_admin():
    """以管理员权限重启当前进程"""
    if sys.platform == 'win32' and not is_admin():
        import ctypes
        cmdline = subprocess.list2cmdline(sys.argv)
        executable = sys.executable.removesuffix('.exe')
        executable += '.exe'
        # 保留当前工作目录：源码分发模式下 main.py、tasks/ 与 resources/ 均按 cwd 解析
        cwd = os.getcwd()
        result = ctypes.windll.shell32.ShellExecuteW(None, 'runas', 'wt.exe', f'"{executable}" {cmdline}', cwd, 1)
        if result > 32:
            sys.exit(0)
        else:
            result = ctypes.windll.shell32.ShellExecuteW(None, 'runas', executable, cmdline, cwd, 1)
            sys.exit(result)


def is_admin() -> bool:
    """检查当前用户是否具有管理员权限（仅限 Windows）"""
    if sys.platform == 'win32':
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0  # NOQA
    return True


if __name__ == '__main__':
    main()
