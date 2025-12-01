from SRACore.task import BaseTask
from SRACore.util import sys_util
from SRACore.util.logger import logger


class MissionAccomplishTask(BaseTask):
    def run(self):
        if self.config["AfterLogout"]:
            self.logout()
        if self.config["AfterExitGame"]:
            self.quit_game()
        return True

    def logout(self):
        logger.info("登出账号")
        if not self.wait_img("resources/img/enter.png"):
            return False
        self.press_key('esc')
        self.wait_img("resources/img/power.png")
        self.click_img("resources/img/power.png", after_sleep=0.5)
        self.click_img("resources/img/ensure.png")
        if self.wait_img("resources/img/logout.png", timeout=60):
            self.click_img("resources/img/logout.png")
        self.click_img("resources/img/quit2.png")
        return True

    def quit_game(self):
        logger.info("退出游戏")
        try:
            sys_util.task_kill("StarRail.exe")
            return True
        except Exception as e:
            logger.debug(e)
            logger.error("发生错误，错误编号7")
            return False
