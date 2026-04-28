from SRACore.task import BaseTask
from SRACore.util import notify, sys_util
from SRACore.util.errors import ErrorCode, SRAError
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
        if notify.should_capture_notification_screenshot():
            notify.capture_game_screenshot(self.operator)
        if not self.operator.wait_img(IMG.ENTER):
            return False
        self.operator.press_key('esc')
        self.operator.wait_img(MAIMG.POWER)
        self.operator.click_img(MAIMG.POWER, after_sleep=0.5)
        self.operator.click_img(IMG.ENSURE)
        if self.operator.wait_img(MAIMG.LOGOUT, timeout=60):
            self.operator.click_img(MAIMG.LOGOUT)
        box = self.operator.wait_img(IMG.QUIT2)
        if box:
            self.operator.click_box(box)
        return True

    def quit_game(self):
        logger.info("退出游戏")
        try:
            if notify.should_capture_notification_screenshot():
                notify.capture_game_screenshot(self.operator)
            sys_util.task_kill("StarRail.exe")
            self.operator.sleep(2)
            return True
        except Exception as e:
            logger.debug(e)
            logger.error(SRAError(ErrorCode.PROCESS_KILL_FAILED, "结束游戏进程失败", str(e)))
            return False
