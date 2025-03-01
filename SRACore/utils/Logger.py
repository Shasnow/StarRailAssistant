from FuXLogger import LogManager, Level, StreamHandler, FileHandler, LogFormatter

my_log_fmt = LogFormatter("{time} | {levelName:<7} | {module}:{function} | {file}:{line:02} | {message}")
logger = LogManager.getLogger("StarRailAssistant", Level.ON, my_log_fmt)

console_handler = StreamHandler("console", Level.TRACE, my_log_fmt, colorize=True, enableXMLRender=True)
file_handler = FileHandler("file", Level.INFO, my_log_fmt, "SRAlog.txt")

# logger.addHandler(console_handler)
logger.addHandler(file_handler)

__all__ = ["logger","console_handler"]
