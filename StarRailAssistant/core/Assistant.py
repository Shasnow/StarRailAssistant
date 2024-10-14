from ..utils.ConfigLoader import ConfigLoader
from .StarRail import StarRail
from ..Exceptions import TaskNotExecuteException
from .Task import AssistantTask
from ..utils.Logger import logger
import queue
from .AssistantSignal import AssistantSignal
from typing import Callable, Iterable


class Assistant:
    """
    内核类，可以说整个程序的核心接口逻辑都在这里实现
    """

    def __init__(self, name: str, resource_path: str) -> None:
        self.name = name
        self.resourcePath = resource_path
        self.config = ConfigLoader(config_file_path=fr"{self.resourcePath}/config.json").loading()
        self.game: StarRail = StarRail(self.config, self.resourcePath)
        self.task_queue: queue.Queue[AssistantTask] = queue.Queue()
        self.logger = logger
        self.completedCallback = None
        self.errorCallback = None
        self.exitCallback = None
        self.cleanCallback = None

    def submit_task(self, task: AssistantTask | Iterable[AssistantTask]) -> None:
        if isinstance(task, AssistantTask):
            self.task_queue.put(task)
        elif isinstance(task, Iterable):
            for t in task:
                self.task_queue.put(t)
        else:
            self.logger.warning(f"提交任务失败, 任务类型 {type(task)} 错误")

    def __execute_task(self, *args, **kwargs):
        """
        每调用一次这个方法，就会从任务队列中取出一个任务，执行它，然后把它从队列中移除
        """
        if not self.task_queue.empty():
            task = self.task_queue.get(timeout=1)
            try:
                self.logger.info(f"开始执行任务 {task.task_name}")
                task.execute(*args, **kwargs)
                self.logger.info(f"任务 {task.task_name} 执行完成")
                return AssistantSignal.TASK_COMPLETE
            except TaskNotExecuteException:
                self.logger.warning(f"任务 {task.task_name} 不可执行,因为没有实现execute方法")
                return AssistantSignal.TASK_ERROR
            except KeyboardInterrupt:
                self.logger.warning("执行任务中途被用户中断，退出程序!")
                return AssistantSignal.EXIT_REQUIRE
            finally:
                self.task_queue.task_done()
                return AssistantSignal.CLEAN_REQUIRE
        else:
            return AssistantSignal.EXIT_REQUIRE

    def setCompletedCallback(self, callback: Callable) -> None:
        """ 设置任务执行完成的回调函数 """
        self.completedCallback = callback

    def setErrorCallback(self, callback: Callable) -> None:
        """ 设置任务执行失败的回调函数 """
        self.errorCallback = callback

    def setExitCallback(self, callback: Callable) -> None:
        """ 设置程序退出的回调函数 """
        self.exitCallback = callback

    def setCleanCallback(self, callback: Callable) -> None:
        """ 设置清理资源的回调函数 """
        self.cleanCallback = callback

    def run(self):
        while True:
            signal = self.__execute_task()
            match signal:
                case AssistantSignal.TASK_COMPLETE:
                    if self.completedCallback:
                        self.completedCallback()
                    continue
                case AssistantSignal.TASK_ERROR:
                    self.logger.warning("有指定的任务执行失败，请在后续检查日志信息来获取详细的错误信息")
                    if self.errorCallback:
                        self.errorCallback()
                    continue
                case AssistantSignal.EXIT_REQUIRE:
                    self.logger.info("收到退出信号，退出程序!")
                    if self.exitCallback:
                        self.exitCallback()
                    break
                case AssistantSignal.CLEAN_REQUIRE:
                    if self.cleanCallback:
                        self.cleanCallback()
                    continue
                case _:
                    self.logger.warning(f"未知的信号 {signal}")
                    continue

    def login(self, account: str, password: str):
        """
        执行任务前,需要登录到游戏
        :param account: 账号
        :param password: 密码
        :return: None
        """
        return self.game.login(account=account, password=password)
