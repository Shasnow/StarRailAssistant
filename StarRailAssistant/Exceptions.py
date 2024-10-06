

class StarRailException(Exception):
    pass

class NotImplementException(StarRailException):
    pass

class StarRailAssitantException(Exception):
    pass

class TaskNotExecuteException(StarRailAssitantException): # 任务不可执行
    pass