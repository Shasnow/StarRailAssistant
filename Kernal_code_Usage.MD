
# StarRailAssistant Kernal Code (内核代码)

## 用法

### 1. 快速开始

```python
from StarRailAssistant import Assistant
from StarRailAssistant.core.StarRailTasks import ExampleTask

if __name__ == '__main__':
    ass = Assistant("崩坏: 星穹铁道", resource_path=r"./res")
    ass.submit_task(ExampleTask())
    ass.run()
```

### 2. 自定义任务

```python
from StarRailAssistant import AssistantTask

class ExampleTask(AssistantTask):
    """
    这个任务是为了测试任务代码是否能正常运行
    """
    def __init__(self) -> None:
        super().__init__("示例任务",{"desc": "示例任务"}, self.execute)

    def execute(self) -> None:
        print("execute something")
        pass
```

- ***你也可以这样***:

```python
from StarRailAssistant import AssistantTask

def callsome():
    print("execute something")

task = AssistantTask("示例任务",{"desc": "示例任务"}, callsome)
```

### AssistantTask类介绍

```python
class AssistantTask:
    """
    这个类用于定义一个任务，包括任务名称、任务描述、任务调用。
    任务调用可以是一个函数，也可以是一个类方法。
    ### 这个类还提供了如下工具方便进行日志记录或者其他操作:
    - self.logger: 日志记录器，用于记录任务执行过程中的日志信息。
    - self.computer_operator: 电脑操作类：用于执行一些电脑的操作，比如移动鼠标，按下键盘等...
    - self.resourceFolder: 资源文件夹路径，用于存放一些资源文件，比如图片、音频、视频等。

    ### (⚠)警告:
    - 定义一个游戏中的任务必须实现execute方法，不然这个任务就是不可执行的, 会报错。
    - 错误是抛出一个 TaskNotExecuteException 异常，请捕获这个异常并处理。
    """
    ...
```

- ***下面是代码原型***:

```python
class AssistantTask:
    def __init__(self,
       task_name: str,
       task_desc: MetaData,
       task_call: TaskCall
    ) -> None:
        self.task_name: str = task_name
        self.task_desc: MetaData = task_desc
        self.task_call: TaskCall = task_call
        self.logger = logger
        self.resourceFolder = fr"{os.getcwd()}/res" if os.path.exists(fr"{os.getcwd()}/res") else fr"{os.getcwd()}/resources"
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
```

- ***提交任务给Assistant内核并且运行***:

```python
from StarRailAssistant import Assistant
from StarRailAssistant.core.StarRailTasks import ExampleTask

if __name__ == '__main__':
    ass = Assistant("崩坏: 星穹铁道", resource_path=r"./res")
    ass.submit_task(ExampleTask())  # 你可以这样直接提交,也可以
    task1 = ExampleTask()
    task2 = ExampleTask()
    ass.submit_task([task1, task2])  # 也可以提交一个包含可迭代对象(列表、元组、集合)的任务列表
    ass.run()  # run用来执行
```

- ***完成或中途错误或退出的时候想运行自己的逻辑怎么办？***:

别急，我允许你设置回调来处理这个问题。

1. 你可以在任务执行完成后设置回调函数，这个函数会在任务执行完成后被调用。

```python
from StarRailAssistant import Assistant
from StarRailAssistant.core.StarRailTasks import ExampleTask


def my_callback():
    print("任务执行完成了")


ass = Assistant("崩坏: 星穹铁道", resource_path=r"./res")
# 当任务成功的时候
ass.setCompletedCallback(my_callback)
# 任务错误的时候
ass.setErrorCallback(my_callback)
# 当整体程序退出的时候
ass.setExitCallback(my_callback)
# 当清理逻辑开始被调用的时候(每个任务完成都会调用清理逻辑,注意!)
ass.setCleanCallback(my_callback)
ass.submit_task(ExampleTask())
ass.run()
```
