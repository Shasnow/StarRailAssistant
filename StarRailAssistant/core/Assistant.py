from ..utils.ConfigLoader import ConfigLoader
from .StarRail import StarRail
from ..Exceptions import TaskNotExecuteException
from .Task import AssistantTask
from ..utils.Logger import logger
import queue
from .AssistantSignal import AssistantSignal

class Assistant:

    def __init__(self, name: str, resourcePath: str) -> None:
        self.name = name
        self.resourcePath = resourcePath
        self.config = ConfigLoader(config_file_path=fr"{self.resourcePath}/config.json").loading()
        self.game: StarRail = StarRail(self.config, self.resourcePath)
        self.task_queue: queue.Queue[AssistantTask] = queue.Queue()
        self.logger = logger

    def submit_task(self, task: AssistantTask):
        self.task_queue.put(task)

    def __execute_task(self, *args, **kwargs):
        """
        每调用一次这个方法，就会从任务队列中取出一个任务，执行它，然后把它从队列中移除
        """
        if not self.task_queue.empty():
            try:
                task = self.task_queue.get(timeout=1)
                self.logger.info(f"开始执行任务 {task.task_name}")
                task.execute(*args, **kwargs)
                self.logger.info(f"任务 {task.task_name} 执行完成")
                return AssistantSignal.TASK_COMPLETE
            except TaskNotExecuteException:
                self.logger.warning(f"任务 {task.task_name} 不可执行,因为没有实现execute方法")
                return AssistantSignal.TASK_ERROR
            finally:
                self.task_queue.task_done()
                return AssistantSignal.CLEAN_REQUIRE
        else:
            self.logger.warning("没有找到可执行的任务")
            return AssistantSignal.EXIT_REQUIRE

    def run(self):
        while True:
            signal = self.__execute_task()
            match signal:
                case AssistantSignal.TASK_COMPLETE:
                    continue
                case AssistantSignal.TASK_ERROR:
                    self.logger.warning("有指定的任务执行失败，请在后续检查日志信息来获取详细的错误信息")
                    continue
                case AssistantSignal.EXIT_REQUIRE:
                    self.logger.info("收到退出信号，退出程序!")
                    break
                case AssistantSignal.CLEAN_REQUIRE:
                    continue # 这里可以执行一些清理工作
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
    
    