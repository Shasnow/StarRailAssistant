import argparse
import sys
import os

from SRACore.util.const import VERSION


def main():
    # 创建 argparse 解析器
    parser = argparse.ArgumentParser(
        description="SRA 命令行工具",
        epilog="examples:\n"
               "  交互模式: SRA-cli\n"
               "  单次执行: SRA-cli run [配置名称...] --once\n"
               "  内嵌模式: SRA-cli --inline",
        formatter_class=argparse.RawTextHelpFormatter  # 保留换行符，优化帮助信息格式
    )
    # 全局参数（模式控制）
    parser.add_argument(
        '--inline',
        action='store_true',
        help='内嵌模式（无命令提示符，适用于被其他程序调用）'
    )
    parser.add_argument(
        '--embed',
        action='store_true',
        help='同 --inline'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'SRA-cli {VERSION}',
        help='显示版本信息并退出'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='启用详细日志输出（调试模式）'
    )

    # 子命令：run（用于单次执行命令）
    subparsers = parser.add_subparsers(
        dest='subcommand',  # 存储子命令名称的变量
        title='commands',
    )
    run_parser = subparsers.add_parser(
        'run',
        help='单次执行任务（如 "run Default"）',
        description='执行完任务后默认进入交互模式，可配合 --once 立即退出'
    )
    # 接收 run 后的所有参数（作为要执行的命令）
    run_parser.add_argument(
        '--config',
        nargs='*',
        help='要运行的配置名称，不指定则运行缓存中的全部配置'
    )
    run_parser.add_argument(
        '--once',
        action='store_true',
        help='执行完任务后退出'
    )

    # 解析参数
    args = parser.parse_args()
    # 延迟导入 SRACli（减少启动时的依赖加载）
    from SRACore.util.logger import logger
    from SRACore.SRA import SRACli
    cli_instance = SRACli()
    logger.debug(f"工作目录：{os.getcwd()}")
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
