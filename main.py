import argparse
import os
import sys

from SRACore.localization import Resource
from SRACore.util.const import VERSION


def main():
    parser = argparse.ArgumentParser(
        description=Resource.argparse_description,
        epilog= Resource.argparse_epilog,
        formatter_class=argparse.RawTextHelpFormatter
    )
    # 全局参数（模式控制）
    parser.add_argument(
        '--inline',
        action='store_true',
        help=Resource.argparse_inline_help
    )
    parser.add_argument(
        '--embed',
        action='store_true',
        help=Resource.argparse_embed_help
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'SRA-cli {VERSION}',
        help=Resource.argparse_version_help
    )
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'],
        default='TRACE',
        help=Resource.argparse_log_level_help
    )
    # 子命令解析器
    subparsers = parser.add_subparsers(
        dest='subcommand',
        title= 'subcommands',
    )
    # 子命令：run
    run_parser = subparsers.add_parser(
        'run',
        help=Resource.argparse_run_help,
        description=Resource.argparse_run_description
    )
    run_parser.add_argument(
        '--config',
        nargs='*',
        help=Resource.argparse_config_help
    )
    run_parser.add_argument(
        '--once',
        action='store_true',
        help=Resource.argparse_once_help
    )

    # 子命令：single
    single_parser = subparsers.add_parser(
        'single',
        help=Resource.argparse_single_help,
        description=Resource.argparse_single_description
    )
    single_parser.add_argument(
        '--task-name', '-t',
        type=str,
        required=True,
        help=Resource.argparse_task_name_help
    )
    single_parser.add_argument(
        '--config',
        nargs='?',  # 0或1个参数
        help=Resource.argparse_config_help
    )
    single_parser.add_argument(
        '--once',
        action='store_true',
        help=Resource.argparse_once_help
    )

    # 解析参数
    args = parser.parse_args()
    # 延迟导入 SRACli
    from SRACore.util.logger import logger, setup_logger, set_log_level
    # 设置日志级别
    set_log_level(args.log_level)
    # 设置日志记录器
    setup_logger()
    from SRACore.SRA import SRACli
    cli_instance = SRACli()
    logger.debug(f"cwd: {os.getcwd()}")
    # 配置交互式模式（隐藏提示符）
    if args.inline or args.embed:
        cli_instance.intro = ''
        cli_instance.prompt = ''

    # 统一处理子命令逻辑
    def execute_subcommand(cmd_prefix: str, *args_parts:str) -> bool:
        """
        拼接并执行子命令，返回是否需要退出
        :param cmd_prefix: 指令前缀（run/single）
        :param args_parts: 指令参数列表
        :return: 是否退出（onecmd返回True 或 指定--once）
        """
        # 拼接指令
        cmd_str = f"{cmd_prefix} {' '.join(arg for arg in args_parts if arg)}"
        if not cmd_str:
            return False
        # 执行指令
        logger.info(cmd_str)
        exit_flag = cli_instance.onecmd(cmd_str)
        # 判断是否需要退出
        return exit_flag or args.once

    # 7. 处理子命令
    exit_program = False
    if args.subcommand == 'run':
        # 处理 run 子命令：config 是列表，拼接为空格分隔的字符串
        exit_program = execute_subcommand('run', *args.config if args.config else [])
    elif args.subcommand == 'single':
        # 处理 single 子命令：task-name + config（单个参数）
        exit_program = execute_subcommand('single', args.task_name, args.config)

    # 8. 退出或启动交互式命令行
    if exit_program:
        sys.exit(0)
    cli_instance.cmdloop()


if __name__ == '__main__':
    main()
