

class StarRailException(Exception):
    pass

class NotImplementException(StarRailException):
    pass

class StarRailAssistantException(Exception):
    pass

class TaskNotExecuteException(StarRailAssistantException): # 任务不可执行
    pass