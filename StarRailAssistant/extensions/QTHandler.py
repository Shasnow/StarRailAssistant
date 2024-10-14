from FuXLogger import Handler, LogLevel, LogFormatter, Level
from FuXLogger.core.LogBody import LogRecord
from typing import Callable


class QTHandler(Handler):
    def __init__(self, update_log_call: Callable) -> None:
        super().__init__(name='QTHandler',
                         level=Level.INFO,
                         formatter=LogFormatter("{time} | {levelName:<7} | {message}")
                         )
        if not callable(update_log_call):
            raise TypeError("update_log_call must be a callable function and arg should be a string")
        self.update_log_call = update_log_call

    def handle(self, record: LogRecord) -> None:
        if record.level in [Level.INFO, Level.WARN, Level.ERROR]:
            self.update_log_call(self.formatter.format(record))
            return
        else:
            return
