
from .Task import AssistantTask
import time

class ExampleTask(AssistantTask):
    """
    这个任务是为了测试任务代码是否能正常运行
    """
    def __init__(self) -> None:
        super().__init__("示例任务",{"desc": "示例任务"}, self.execute)

    def execute(self) -> None:
        print("execute something")
        pass

class TrailblazerTask(AssistantTask):
    """
    示例任务,领取签证奖励, 其他任务按照这种写法去写即可
    """
    def __init__(self) -> None:
        super().__init__("领取签证奖励",{"desc": "领取签证奖励"}, self.execute)

    def execute(self) -> None:
        time.sleep(2) # 等待游戏加载完成
        self.computer_operator.press_key("esc")
        if self.computer_operator.click_screen(fr"{self.resourceFolder}/img/more_with_something.png"):
            self.computer_operator.move_by_offset(20, 0)
            if self.computer_operator.click_screen(fr"{self.resourceFolder}/img/trailblazer_profile_finished.png"):
                if self.computer_operator.click_screen(fr"{self.resourceFolder}/img/assistance_reward.png"):
                    time.sleep(2) # 等待领取奖励完成
                    self.computer_operator.press_key("esc", 3, 2)
                else:
                    self.logger.info("没有可以领取的奖励")
                    self.computer_operator.press_key("esc", 2, 2)
            else:
                self.logger.info("没有找到奖励页面")
        else:
            self.logger.info("没有找到更多选项")