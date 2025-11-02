import sys

from SRACore.util.logger import setup_logger,logger

if __name__ == '__main__':
    setup_logger()
    logger.debug("工作目录：" + str(sys.path[0]))
    args = sys.argv[1:]
    from SRACore.SRA import SRACli
    cli_instance = SRACli()
    if args:
        if args[0] == '--inline' or args[0] == '--embed':
            cli_instance.prompt='' # 内嵌模式无提示符
        elif args[0] == 'run':
            cli_instance.onecmd(' '.join(args))
            sys.exit(0)
    cli_instance.cmdloop()
