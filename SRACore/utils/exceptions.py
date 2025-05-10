class StarRailException(Exception):
    pass


class NotImplementException(StarRailException):
    pass


class SRAException(Exception):
    pass


class TaskNotExecuteException(SRAException):  # 任务不可执行
    pass


class WindowNoFoundException(SRAException):
    pass


class MultipleWindowsException(SRAException):
    pass


class MatchFailureException(SRAException):
    pass


class WindowInactiveException(SRAException):
    pass

class InvalidPluginException(SRAException):
    pass
