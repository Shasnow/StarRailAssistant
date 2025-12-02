import argparse
import sys
import os

from SRACore.util.const import VERSION
from SRACore.util.i18n import t


def main():
    # 创建 argparse 解析器
    parser = argparse.ArgumentParser(
        description=t('cli.description'),
        epilog=t('cli.examples'),
        formatter_class=argparse.RawTextHelpFormatter  # 保留换行符，优化帮助信息格式
    )
    # 全局参数（模式控制）
    parser.add_argument(
        '--inline',
        action='store_true',
        help=t('cli.inline_help')
    )
    parser.add_argument(
        '--embed',
        action='store_true',
        help=t('cli.embed_help')
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'SRA-cli {VERSION}',
        help=t('cli.version_help')
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help=t('cli.verbose_help')
    )

    # 子命令：run（用于单次执行命令）
    subparsers = parser.add_subparsers(
        dest='subcommand',  # 存储子命令名称的变量
        title=t('cli.commands_title'),
    )
    run_parser = subparsers.add_parser(
        'run',
        help=t('cli.run_help'),
        description=t('cli.run_description')
    )
    # 接收 run 后的所有参数（作为要执行的命令）
    run_parser.add_argument(
        '--config',
        nargs='*',
        help=t('cli.config_help')
    )
    run_parser.add_argument(
        '--once',
        action='store_true',
        help=t('cli.once_help')
    )

    # 解析参数
    args = parser.parse_args()
    # 延迟导入 SRACli（减少启动时的依赖加载）
    from SRACore.util.logger import logger
    from SRACore.SRA import SRACli
    cli_instance = SRACli()
    logger.debug(t('cli.working_directory', path=os.getcwd()))
    # 根据参数处理模式
    # 内嵌模式：隐藏提示符
    if args.inline or args.embed:
        cli_instance.intro = ''
        cli_instance.prompt = ''
    # 处理 run 子命令（单次执行）
    if args.subcommand == 'run':
        cmd_str = 'run '
        if args.config:
             cmd_str += ' '.join(args.config)
        cli_instance.onecmd(cmd_str)
        if args.once:
            sys.exit(0)  # 若指定 --once 或命令返回退出信号（如 exit），则退出

    cli_instance.cmdloop()


if __name__ == '__main__':
    main()
