from SRACore.task import BaseTask
from SRACore.util import sys_util
from SRACore.util.logger import logger
from tasks.img import IMG, MAIMG


class MissionAccomplishTask(BaseTask):
    def run(self):
        if self.config["AfterLogout"]:
            self.logout()
        if self.config["AfterExitGame"]:
            self.quit_game()
        return True

    def logout(self):
        logger.info("登出账号")
        if not self.operator.wait_img(IMG.ENTER):
            return False
        self.operator.press_key('esc')
        self.operator.wait_img(MAIMG.POWER)
        self.operator.click_img(MAIMG.POWER, after_sleep=0.5)
        self.operator.click_img(IMG.ENSURE)
        if self.operator.wait_img(MAIMG.LOGOUT, timeout=60):
            self.operator.click_img(MAIMG.LOGOUT)
        self.operator.click_img(IMG.QUIT2)
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
