from FuXLogger import LogManager , LogLevel , StreamHandler , FileHandler , LogFormatter

my_log_fmt = LogFormatter("{time} | {levelName:<7} | {module}:{function} | {file}:{line:02} | {message}")
logger = LogManager.getLogger("StarRailAssitant", my_log_fmt)

console_handler = StreamHandler("console", LogLevel.TRACE, my_log_fmt, colorize=True, enableXMLRender=True)
file_handler = FileHandler("file", LogLevel.INFO, my_log_fmt, "StarRailAssitant.log")

logger.addHandler(console_handler)
logger.addHandler(file_handler)

__all__ = ["logger"]