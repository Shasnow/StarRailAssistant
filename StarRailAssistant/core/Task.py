
from ..utils._types import TaskCall , MetaData
from ..Exceptions import TaskNotExecuteException
from ..utils.Logger import logger
from ..utils.ComputerOperator import ComputerOperator

class AssistantTask:
    """
    这个类用于定义一个任务，包括任务名称、任务描述、任务调用。
    任务调用可以是一个函数，也可以是一个类方法。
    ### 这个类还提供了如下工具方便进行日志记录或者其他操作:
    - self.logger: 日志记录器，用于记录任务执行过程中的日志信息。
    - self.computer_operator: 电脑操作类：用于执行一些电脑的操作，比如移动鼠标，按下键盘等...

    ### (⚠)警告:
    - 定义一个游戏中的任务必须实现execute方法，不然这个任务就是不可执行的, 会报错。
    """
    def __init__(self,
       task_name: str,
       task_desc: MetaData,
       task_call: TaskCall
    ) -> None:
        self.task_name: str = task_name
        self.task_desc: MetaData = task_desc
        self.task_call: TaskCall = task_call
        self.logger = logger
        self.computer_operator: ComputerOperator = ComputerOperator()
        self._completed: bool = False

    def execute(self, *args, **kwargs):
        """
        基类只提供调用的接口, 具体的任务执行需要在子类中实现。
        """
        if self.task_call:
            result = self.task_call(*args, **kwargs)
            self._completed = True
            return result
        else:
            raise TaskNotExecuteException("Task not execute")

    def __repr__(self) -> str:
        return f"<AssistantTask({self.task_name}, {self.task_desc}, {self.task_call})>"
    
    def __str__(self) -> str:
        return f"AssistantTask: {self.task_name}"
    
    def __call__(self, *args, **kwargs):
        if self.task_call:
            result = self.task_call(*args, **kwargs)
            self._completed = True
            return result
        else:
            raise TaskNotExecuteException("Task not execute")