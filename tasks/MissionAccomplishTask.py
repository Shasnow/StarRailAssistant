import os

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
        if self.config["AfterShutdown"]:
            self.shutdown()
        elif self.config["AfterSleep"]:
            self.sleep()
        elif self.config["AfterExitApp"]:
            self.exit_app()
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

    def exit_app(self):
        logger.info("退出程序")
        try:
            if notify.should_capture_notification_screenshot():
                notify.capture_game_screenshot(self.operator)
            os._exit(0)
        except Exception as e:
            logger.debug(e)
            logger.error(SRAError(ErrorCode.PROCESS_KILL_FAILED, "退出程序失败", str(e)))
            return False

    def shutdown(self):
        logger.info("正在关机...")
        try:
            if notify.should_capture_notification_screenshot():
                notify.capture_game_screenshot(self.operator)
            sys_util.shutdown(time=10)
            return True
        except Exception as e:
            logger.debug(e)
            logger.error(SRAError(ErrorCode.SYSTEM_SHUTDOWN_FAILED, "关机失败", str(e)))
            return False

    def sleep(self):
        logger.info("正在睡眠...")
        try:
            if notify.should_capture_notification_screenshot():
                notify.capture_game_screenshot(self.operator)
            sys_util.sleep_system()
            return True
        except Exception as e:
            logger.debug(e)
            logger.error(SRAError(ErrorCode.SYSTEM_SHUTDOWN_FAILED, "休眠失败", str(e)))
            return False
