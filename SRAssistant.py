#   <StarRailAssistant:An automated program that helps you complete daily tasks of StarRail.>
#   Copyright © <2024> <Shasnow>

#   This file is part of StarRailAssistant.

#   StarRailAssistant is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the Free Software Foundation,
#   either version 3 of the License, or (at your option) any later version.

#   StarRailAssistant is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#   without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#   See the GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License along with StarRailAssistant.
#   If not, see <https://www.gnu.org/licenses/>.

#   yukikage@qq.com

"""
崩坏：星穹铁道助手
v0.6.4_beta
作者：雪影
主功能
"""

import subprocess
import time

import cv2
import pyautogui
import pyscreeze
from PySide6.QtCore import QThread, Signal, Slot

import Configure
import WindowsProcess
import encryption
from StarRailAssistant.extensions.QTHandler import QTHandler
from StarRailAssistant.utils.Logger import logger, console_handler
from WindowsProcess import find_window, is_process_running


class Assistant(QThread):
    update_signal = Signal(str)

    def __init__(self, pwd):
        super().__init__()
        self.stop_flag = False
        self.pwd = pwd
        settings = Configure.load()["Settings"]
        self.f1 = settings["F1"]
        self.f2 = settings["F2"]
        self.f4 = settings["F4"]
        if len(logger.handlers) == 1:
            logger.addHandler(QTHandler(self.send_signal))

    def send_signal(self, text):
        self.update_signal.emit(text)

    def request_stop(self):
        self.stop_flag = True

    @Slot()
    def run(self):
        logger.info("创建任务")
        config = Configure.load()
        if not self.stop_flag:
            if config["Mission"]["startGame"]:
                account_text = encryption.load()
                password_text = self.pwd
                self.start_game(
                    config["StartGame"]["gamePath"],
                    config["StartGame"]["pathType"],
                    config["StartGame"]["channel"],
                    config["StartGame"]["autoLogin"],
                    account_text,
                    password_text,
                )
        if not self.check_game():
            return
        if not self.stop_flag:
            if config["Mission"]["trailBlazerProfile"]:
                self.trailblazer_profile()
        if not self.stop_flag:
            if config["Mission"]["redeemCode"]:
                self.redeem_code(config["RedeemCode"]["codeList"])
        if not self.stop_flag:
            if config["Mission"]["assignment"]:
                self.assignments_reward()
        if not self.stop_flag:
            if config["Mission"]["giftOfOdyssey"]:
                self.gift_of_odyssey()
        if not self.stop_flag:
            if config["Mission"]["mail"]:
                self.mail()
        if not self.stop_flag:
            if config["Mission"]["trailBlazePower"]:
                self.replenish_flag = config["Replenish"]["enable"]
                self.replenish_way = config["Replenish"]["way"]
                self.replenish_time = config["Replenish"]["runTimes"]
                if not self.stop_flag:
                    if config["OrnamentExtraction"]["enable"]:
                        self.ornament_extraction(
                            config["OrnamentExtraction"]["level"],
                            config["OrnamentExtraction"]["runTimes"],
                        )
                if not self.stop_flag:
                    if config["CalyxGolden"]["enable"]:
                        self.calyx_golden(
                            config["CalyxGolden"]["level"],
                            config["CalyxGolden"]["singleTimes"],
                            config["CalyxGolden"]["runTimes"],
                        )
                if not self.stop_flag:
                    if config["CalyxCrimson"]["enable"]:
                        self.calyx_crimson(
                            config["CalyxCrimson"]["level"],
                            config["CalyxCrimson"]["singleTimes"],
                            config["CalyxCrimson"]["runTimes"],
                        )
                if not self.stop_flag:
                    if config["StagnantShadow"]["enable"]:
                        self.stagnant_shadow(
                            config["StagnantShadow"]["level"],
                            config["StagnantShadow"]["runTimes"],
                        )
                if not self.stop_flag:
                    if config["CaverOfCorrosion"]["enable"]:
                        self.caver_of_corrosion(
                            config["CaverOfCorrosion"]["level"],
                            config["CaverOfCorrosion"]["runTimes"]
                        )
                if not self.stop_flag:
                    if config["EchoOfWar"]["enable"]:
                        self.echo_of_war(
                            config["EchoOfWar"]["level"],
                            config["EchoOfWar"]["runTimes"]
                        )
        if not self.stop_flag:
            if config["Mission"]["dailyTraining"]:
                self.daily_training_reward()
        if not self.stop_flag:
            if config["Mission"]["namelessHonor"]:
                self.nameless_honor()
        if not self.stop_flag:
            if config["Mission"]["quitGame"]:
                self.kill_game()
        if self.stop_flag:
            logger.info("已停止")
        else:
            logger.info("任务全部完成")

    @Slot()
    def check_game(self):
        """Check that the game is running.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Returns:
            True if game is running,False if not.
        """
        window_title = "崩坏：星穹铁道"
        if not WindowsProcess.check_window(window_title):
            logger.warning("未找到窗口:" + window_title + "或许你还没有运行游戏")
            return False
        return True

    @Slot()
    def path_check(self, path, path_type="StarRail"):
        """Check game path.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            path (str): File path.
            path_type (str): Use StarRail.exe or launcher.exe
        Returns:
            True if path points to channel, False otherwise.
        """
        if path:
            if path.split("/")[-1].split(".")[0] != path_type:
                logger.warning("你尝试输入一个其他应用的路径")
                return False
            else:
                return True
        else:
            logger.error("游戏路径为空")
            return False

    @Slot()
    def kill_game(self):
        """Kill the game"""
        command = f"taskkill /F /IM StarRail.exe"
        # 执行命令
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL)
        logger.info("退出游戏")

    @Slot()
    def kill_launcher(self):
        """Kill the launcher"""
        command = f"taskkill /F /IM HYP.exe"
        # 执行命令
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL)
        logger.info("已为您关闭启动器")

    @Slot()
    def launch_game(self, game_path, path_type):
        """Launch game

        Try to run the file that game path points at.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            game_path (str): File path.
            path_type (str): Game or Launcher
        Returns:
            True if successfully launched, False otherwise.

        """
        if not self.path_check(game_path, path_type):
            logger.warning("路径无效")
            return False
        try:
            subprocess.Popen(game_path)
        except OSError:
            logger.error("路径无效或权限不足")
            return False
        logger.info("等待游戏启动")
        time.sleep(5)
        times = 0
        while True:
            if find_window("崩坏：星穹铁道"):
                logger.info("启动成功")
                return True
            else:
                time.sleep(0.5)
                times += 1
                if times == 40:
                    logger.warning("启动时间过长，请尝试手动启动")
                    return False

    @Slot()
    def launch_launcher(self, path, path_type, channel):
        """Launch game

        Try to run the file that game path points at.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            path (str): File path.
            path_type (str): Launcher
            channel: 0 -> official, 1 -> bilibili
        Returns:
            True if successfully launched, False otherwise.

        """
        if not is_process_running("HYP.exe"):
            if not self.path_check(path, path_type):
                logger.warning("路径无效")
                return False
            try:
                subprocess.Popen(path)
            except OSError:
                logger.error("路径无效或权限不足")
                return False
            logger.info("等待启动器启动")
        time.sleep(5)
        times = 0
        while times<40:
            if is_process_running("HYP.exe"):
                time.sleep(2)
                if channel==0:
                    click('res/img/star_game.png', title="米哈游启动器")
                else:
                    click('res/img/star_game.png')
                logger.info("等待游戏启动")
                for i in range(10):
                    time.sleep(1)
                    if is_process_running("StarRail.exe"):
                        logger.info("启动成功")
                        self.kill_launcher()
                        return True
            else:
                time.sleep(0.5)
                times += 1
        else:
            logger.warning("启动时间过长，请尝试手动启动")
            return False

    @Slot()
    def login(self, account, password):
        """Login game.

        Try to log in game. If it is already logged in, skip this section.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            account (str): user account
            password (str): user password
        Returns:
            True if successfully logged in, False otherwise.

        """
        if check(
                "res/img/welcome.png", interval=0.1, max_time=10
        ):  # 进入登录界面的标志
            logger.info("已登录")
            return True
        if not check("res/img/not_logged_in.png", max_time=10):
            logger.error("发生错误，错误编号11")
            return False
        if not click("res/img/login_with_account.png"):
            logger.error("发生错误，错误编号10")
            return False
        logger.info("登录到" + account)
        time.sleep(1)
        pyautogui.write(account)
        time.sleep(1)
        pyautogui.press("tab")
        time.sleep(0.2)
        pyautogui.write(password)
        pyautogui.press("enter")
        click("res/img/agree.png", -158)
        if not click("res/img/enter_game.png"):
            logger.error("发生错误，错误编号9")
            return False
        times = 0
        while True:
            time.sleep(0.2)
            times += 1
            if times == 10:
                logger.warning("长时间未成功登录，可能密码错误或需要新设备验证")
                return False
            else:
                if exist("res/img/welcome.png"):
                    logger.info("登录成功")
                    return True

    @Slot()
    def login_bilibili(self, account, password):
        """Login game.

        Try to log in game with bilibili channel. If it is already logged in, skip this section.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            account (str): user account
            password (str): user password
        Returns:
            True if successfully logged in, False otherwise.

        """
        if not check("res/img/bilibili_login.png", interval=0.2, max_time=20):  # 进入登录界面的标志
            logger.error("检测超时，编号3")
            return False
        if click('res/img/bilibili_account.png'):
            logger.info("登录到" + account)
            time.sleep(0.5)
            pyautogui.write(account)
        if click('res/img/bilibili_pwd.png'):
            time.sleep(0.5)
            pyautogui.write(password)
        click('res/img/bilibili_remember.png')
        click("res/img/bilibili_read.png", x_add=-30)
        click("res/img/bilibili_login.png")
        return True

    @Slot()
    def start_game(self, game_path, path_type, channel=0, login_flag=False, account="", password=""):
        """Launch and enter game.

        If the game is already star, skip this section.
        If not, launch and enter game.
        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            game_path (str): Path of game.
            path_type (str): Game or Launcher.
            channel (int): 0->官服，1->bilibili
            login_flag (bool): Whether to enable the launch game function.
            account (str): User account.
            password (str): User password.
        Returns:
            True if entered game successfully, False otherwise.

        """
        if find_window("崩坏：星穹铁道"):
            logger.info("游戏已经启动")
            if check("res/img/chat_enter.png", max_time=10):
                return True
        if path_type == "StarRail":
            if not self.launch_game(game_path, path_type):
                time.sleep(2)
                logger.warning("游戏启动失败")
                return False
        elif path_type == "launcher":
            if not self.launch_launcher(game_path, path_type, channel):
                logger.warning("游戏启动失败")
                return False
        if channel == 0:
            if login_flag and account:
                self.login(account, password)
            if check("res/img/quit.png"):
                x, y = get_screen_center()
                if exist("res/img/12+.png"):
                    pyautogui.click(x, y)
                    time.sleep(3)
                logger.info("开始游戏")
                pyautogui.click(x, y)
                time.sleep(3)
                pyautogui.click(x, y)
            else:
                logger.warning("加载时间过长，请重试")
                return False
        elif channel == 1:
            self.login_bilibili(account, password)
            if check("res/img/quit.png"):
                x, y = get_screen_center()
                if exist("res/img/12+.png"):
                    pyautogui.click(x, y)
                    time.sleep(3)
                logger.info("开始游戏")
                pyautogui.click(x, y)
                time.sleep(3)
                pyautogui.click(x, y)
            else:
                logger.warning("加载时间过长，请重试")
                return False
        times = 0
        while True:
            time.sleep(0.2)
            if click("res/img/train_supply.png"):
                time.sleep(4)
                pyautogui.moveRel(0, +400)
                pyautogui.click()
            if exist("res/img/chat_enter.png") or exist("res/img/phone.png", wait_time=0):
                return True
            else:
                times += 1
                if times == 50:
                    logger.error("发生错误，进入游戏但未处于大世界")
                    return False

    @Slot()
    def trailblazer_profile(self):
        """Mission trailblaze profile"""
        logger.info("执行任务：签证奖励")
        if not check("res/img/chat_enter.png", max_time=20):
            logger.error("检测超时，编号2")
            return
        pyautogui.press("esc")
        if click("res/img/more_with_something.png"):
            pyautogui.moveRel(20, 0)
            if click("res/img/trailblazer_profile_finished.png"):
                if click("res/img/assistance_reward.png"):
                    time.sleep(2)
                    pyautogui.press("esc", presses=3, interval=2)
                else:
                    logger.info("没有可领取的奖励1")
                    pyautogui.press("esc", presses=2, interval=2)
            else:
                logger.info("没有可领取的奖励2")
                pyautogui.press("esc")
        else:
            logger.info("没有可领取的奖励3")
            pyautogui.press("esc")
        logger.info("任务完成：签证奖励")

    @Slot()
    def redeem_code(self, redeem_code_list):
        """Fills in redeem code and redeems them.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            redeem_code_list (list): The list thar stored redeem codes.
        Returns:
            None
        """
        logger.info("执行任务：领取兑换码")
        if not check("res/img/chat_enter.png", max_time=20):
            logger.error("检测超时，编号2")
            return
        pyautogui.press("esc")
        if len(redeem_code_list) == 0:
            logger.warning("未填写兑换码")
        for code in redeem_code_list:
            if click("res/img/more.png") or click("res/img/more_with_something.png"):
                if click("res/img/redeem_code.png"):
                    time.sleep(2)
                    pyautogui.click(get_screen_center())
                    pyautogui.write(code)
                    click("res/img/ensure.png")
                    time.sleep(2)
                    pyautogui.press("esc")
                else:
                    logger.error("发生错误，错误编号16")
            else:
                logger.error("发生错误，错误编号17")
        time.sleep(2)
        pyautogui.press("esc")
        logger.info("任务完成：领取兑换码")

    @Slot()
    def mail(self):
        """Open mailbox and pick up mails."""
        logger.info("执行任务：领取邮件")
        if not check("res/img/chat_enter.png", max_time=20):
            logger.error("检测超时，编号2")
            return
        pyautogui.press("esc")
        if click("res/img/mailbox_mail.png"):
            if click("res/img/claim_all_mail.png"):
                time.sleep(2)
                pyautogui.press("esc", presses=3, interval=2)
            else:
                logger.info("没有可以领取的邮件")
                pyautogui.press("esc")
        else:
            logger.info("没有可以领取的邮件")
            pyautogui.press("esc")
        logger.info("任务完成：领取邮件")

    @Slot()
    def gift_of_odyssey(self):
        """Open the activity screen to receive gift_of_odyssey.

        Remember to update the gift_of_odyssey.png in each game version.
        """
        logger.info("执行任务：巡星之礼")
        if not check("res/img/chat_enter.png", max_time=20):
            logger.error("检测超时，编号2")
            return
        pyautogui.press(self.f1)
        if click("res/img/gift_of_odyssey.png"):
            pass
        if click("res/img/gift_receive.png"):
            logger.info("领取成功")
            time.sleep(2)
            pyautogui.press("esc", presses=2, interval=2)
        else:
            logger.info("没有可以领取的巡星之礼")
            pyautogui.press("esc")
        logger.info("任务完成：巡星之礼")

    @Slot()
    def ornament_extraction(self, level_index, battle_time=1):
        """Ornament extraction

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            level_index (int): The index of level in /res/img.
            battle_time (int): The time of battle.
        Returns:
            None
        """
        logger.info("执行任务：饰品提取")
        level = "res/img/ornament_extraction (" + str(level_index) + ").png"
        if not self.find_session_name("ornament_extraction"):
            return
        if exist("res/img/no_save.png"):
            logger.warning("当前暂无可用存档，请前往[差分宇宙]获取存档")
            pyautogui.press("esc")
            return
        find_level(level)
        if not click(level, x_add=700):
            logger.error("发生错误，错误编号3")
            return
        if not check('res/img/ornament_extraction_page.png'):  # 等待传送
            logger.error("检测超时，编号4")
            return
        if click("res/img/nobody.png"):
            click("res/img/preset_formation.png")
            click("res/img/team1.png")
        if click("res/img/battle_star.png"):
            if exist("res/img/replenish.png"):
                if self.replenish_flag:
                    self.replenish(self.replenish_way)
                    click("res/img/battle_star.png")
                else:
                    self.update_signal.emit("体力不足")
                    pyautogui.press("esc", interval=1, presses=2)
                    return
            while not exist("res/img/f3.png"):
                pass
            pyautogui.keyDown("w")
            time.sleep(2.5)
            pyautogui.keyUp("w")
            pyautogui.click()
            self.battle_star(battle_time)
        self.update_signal.emit("任务完成：饰品提取")

    @Slot()
    def calyx_golden(self, level_index, single_time=1, battle_time=1):
        """Battle calyx(golden)

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            level_index (int): The index of level in /res/img.
            single_time (int): The single battle times(1~6).
            battle_time (int): Number of times the task was executed.
        Returns:
            None
        """
        logger.info("执行任务：拟造花萼（金）")
        level = "res/img/calyx(golden) (" + str(level_index) + ").png"
        if not self.find_session_name("calyx(golden)"):
            return
        find_level(level)
        if click(level, x_add=600, y_add=10):
            if not check('res/img/battle.png'):  # 等待传送
                logger.error("检测超时，编号4")
                return
            for i in range(single_time - 1):
                click("res/img/plus.png", wait_time=0.5)
            time.sleep(2)
            if not click("res/img/battle.png"):
                logger.error("发生错误，错误编号3")
                return
            if exist("res/img/replenish.png"):
                if self.replenish_flag:
                    self.replenish(self.replenish_way)
                    click("res/img/battle.png")
                else:
                    logger.info("体力不足")
                    pyautogui.press("esc", interval=1, presses=2)
                    return
            if click("res/img/battle_star.png"):
                self.battle_star(battle_time)
            else:
                logger.error("发生错误，错误编号4")
        logger.info("任务完成：拟造花萼（金）")

    @Slot()
    def calyx_crimson(self, level_index, single_time=1, battle_time=1):
        """Battle calyx(crimson)

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            level_index (int): The index of level in /res/img.
            single_time (int): The single battle times(1~6).
            battle_time (int): Number of times the task was executed.
        Returns:
            None
        """
        logger.info("执行任务：拟造花萼（赤）")
        level = "res/img/calyx(crimson) (" + str(level_index) + ").png"
        if not self.find_session_name("calyx(crimson)"):
            return
        find_level(level)
        if click(level, x_add=400):
            if not check('res/img/battle.png'):  # 等待传送
                logger.error("检测超时，编号4")
                return
            for i in range(single_time - 1):
                click("res/img/plus.png", wait_time=0.5)
            time.sleep(2)
            if not click("res/img/battle.png"):
                logger.error("发生错误，错误编号3")
                return
            if exist("res/img/replenish.png"):
                if self.replenish_flag:
                    self.replenish(self.replenish_way)
                    click("res/img/battle.png")
                else:
                    logger.info("体力不足")
                    pyautogui.press("esc", interval=1, presses=2)
                    return
            if click("res/img/battle_star.png"):
                self.battle_star(battle_time)
            else:
                logger.error("发生错误，错误编号4")
        logger.info("任务完成：拟造花萼（赤）")

    @Slot()
    def stagnant_shadow(self, level_index, battle_time=1):
        """Battle stagnant shadow

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            level_index (int): The index of level in /res/img.
            battle_time (int): Number of times the task was executed.
        Returns:
            None
        """
        logger.info("执行任务：凝滞虚影")
        level = "res/img/stagnant_shadow (" + str(level_index) + ").png"
        if not self.find_session_name("stagnant_shadow"):
            return
        find_level(level)
        if click(level, x_add=400):
            if not check('res/img/battle.png'):  # 等待传送
                logger.error("检测超时，编号4")
                return
            if not click("res/img/battle.png"):
                logger.error("发生错误，错误编号3")
                return
            if exist("res/img/replenish.png"):
                if self.replenish_flag:
                    self.replenish(self.replenish_way)
                    click("res/img/battle.png")
                else:
                    logger.info("体力不足")
                    pyautogui.press("esc", interval=1, presses=2)
                    return
            if click("res/img/battle_star.png"):
                time.sleep(3)
                pyautogui.keyDown("w")
                time.sleep(2)
                pyautogui.keyUp("w")
                pyautogui.click()
                self.battle_star(battle_time)
            else:
                logger.error("发生错误，错误编号4")
        logger.info("任务完成：凝滞虚影")

    @Slot()
    def caver_of_corrosion(self, level_index, battle_time=1):
        """Battle caver of corrosion

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            level_index (int): The index of level in /res/img.
            battle_time (int): Number of times the task was executed.
        Returns:
            None
        """
        logger.info("执行任务：侵蚀隧洞")
        level = "res/img/caver_of_corrosion (" + str(level_index) + ").png"
        if not self.find_session_name("caver_of_corrosion", True):
            return
        find_level(level)
        if click(level, x_add=700):
            if not check('res/img/battle.png'):  # 等待传送
                logger.error("检测超时，编号4")
                return
            if not click("res/img/battle.png"):
                logger.error("发生错误，错误编号3")
                return
            if exist("res/img/replenish.png"):
                if self.replenish_flag:
                    self.replenish(self.replenish_way)
                    click("res/img/battle.png")
                else:
                    logger.info("体力不足")
                    pyautogui.press("esc", interval=1, presses=2)
                    return
            if click("res/img/battle_star.png"):
                self.battle_star(battle_time)
            else:
                logger.error("发生错误，错误编号4")
        logger.info("任务完成：侵蚀隧洞")

    @Slot()
    def echo_of_war(self, level_index, battle_time=1):
        """Battle echo of war

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            level_index (int): The index of level in /res/img.
            battle_time (int): Number of times the task was executed.
        Returns:
            None
        """
        logger.info("执行任务：历战余响")
        level = "res/img/echo_of_war (" + str(level_index) + ").png"
        if not self.find_session_name("echo_of_war", True):
            return
        find_level(level)
        if click(level, x_add=400):
            if not check('res/img/battle.png'):  # 等待传送
                logger.error("检测超时，编号4")
                return
            if not click("res/img/battle.png"):
                logger.error("发生错误，错误编号3")
                return
            if exist("res/img/replenish.png"):
                if self.replenish_flag:
                    self.replenish(self.replenish_way)
                    click("res/img/battle.png")
                else:
                    logger.info("体力不足")
                    pyautogui.press("esc", interval=1, presses=2)
                    return
            if click("res/img/battle_star.png"):
                self.battle_star(battle_time)
            else:
                logger.error("发生错误，错误编号4")
        logger.info("任务完成：历战余响")

    @Slot()
    def battle_star(self, battle_time):
        logger.info("开始战斗")
        logger.info("请检查自动战斗和倍速是否开启")
        times = 0
        while times != 10:
            if exist("res/img/q.png", wait_time=1):
                pyautogui.press("v")
                break
            else:
                times += 1
        while battle_time > 1:
            logger.info("剩余次数" + str(battle_time))
            self.wait_battle_end()
            if not click("res/img/again.png"):
                logger.error("发生错误，错误编号5")
                continue
            if exist("res/img/replenish.png"):
                if self.replenish_flag and self.replenish_time:
                    self.replenish(self.replenish_way)
                    click("res/img/again.png")
                else:
                    logger.info("体力不足")
                    pyautogui.press("esc")
                    if click("res/img/quit_battle.png"):
                        logger.info("退出战斗")
                    else:
                        logger.error("发生错误，错误编号12")
                    break
            battle_time -= 1
            time.sleep(3)
        else:
            self.wait_battle_end()
            if click("res/img/quit_battle.png"):
                logger.info("退出战斗")
            else:
                logger.error("发生错误，错误编号12")

    @Slot()
    def wait_battle_end(self):
        """Wait battle end

        Returns:
            True if battle end.
        """
        logger.info("等待战斗结束")
        quit_battle = cv2.imread("res/img/quit_battle.png")
        while True:
            time.sleep(0.2)
            try:
                pyautogui.locateOnWindow(quit_battle, "崩坏：星穹铁道", confidence=0.9)
                logger.info("战斗结束")
                return True
            except pyautogui.ImageNotFoundException:
                continue
            except pyscreeze.PyScreezeException:
                continue

    @Slot()
    def assignments_reward(self):
        """Receive assignment reward"""
        logger.info("执行任务：领取派遣奖励")
        if not check("res/img/chat_enter.png", max_time=20):
            logger.error("检测超时，编号2")
            return
        pyautogui.press("esc")
        if not click("res/img/assignments_none.png"):
            logger.info("没有可领取的奖励")
            pyautogui.press("esc")
            return
        while not exist("res/img/assignment_page.png"):
            pass
        if click("res/img/assignments_reward.png"):
            if click("res/img/assign_again.png"):
                logger.info("再次派遣")
                time.sleep(2)
                pyautogui.press("esc", presses=2, interval=2)
            else:
                logger.error("发生错误，错误编号6")
        else:
            logger.info("没有可以领取的派遣奖励")
            pyautogui.press("esc")
            time.sleep(2)
            pyautogui.press("esc")

        logger.info("任务完成：领取派遣奖励")

    @Slot()
    def daily_training_reward(self):
        """Receive daily training reward"""
        logger.info("执行任务：领取每日实训奖励")
        if not check("res/img/chat_enter.png", max_time=20):
            logger.error("检测超时，编号2")
            return
        pyautogui.press(self.f4)
        if not check("res/img/f4.png", max_time=20):
            logger.error("检测超时，编号1")
            return
        if exist("res/img/survival_index_onclick.png"):
            logger.info("没有可领取的奖励")
            pyautogui.press("esc")
        else:
            while True:
                if click("res/img/daily_reward.png"):
                    pyautogui.moveRel(0, -60)
                else:
                    break
            if click("res/img/daily_train_reward.png"):
                time.sleep(2)
                pyautogui.press("esc", presses=2, interval=2)
            else:
                logger.info("没有可领取的奖励")
                pyautogui.press("esc")
        logger.info("任务完成：领取每日实训奖励")

    @Slot()
    def nameless_honor(self):
        """Receive nameless honor reward"""
        logger.info("执行任务：领取无名勋礼奖励")
        if not check("res/img/chat_enter.png", max_time=20):
            logger.error("检测超时，编号2")
            return
        pyautogui.press(self.f2)
        if not check("res/img/f2.png", max_time=20):
            logger.error("检测超时，编号1")
            return
        if exist("res/img/nameless_honor_reward_exist.png"):
            if click("res/img/nameless_honor_reward_receive.png"):
                logger.info("领取了无名勋礼奖励")
                time.sleep(2)
                pyautogui.press("esc")
            else:
                logger.error("发生错误，错误编号7")
        if not click("res/img/nameless_honor_task.png"):
            logger.info("没有可领取的奖励")
            pyautogui.press("esc")
            return
        if not click("res/img/nameless_honor_task_receive.png"):
            logger.info("没有已完成的无名勋礼任务")
            pyautogui.press("esc")
            return
        logger.info("成功领取无名勋礼任务奖励")
        time.sleep(1)
        pyautogui.press("esc")
        if not click("res/img/nameless_honor_reward.png"):
            logger.info("没有可领取的奖励")
            return
        if click("res/img/nameless_honor_reward_receive.png"):
            logger.info("领取了无名勋礼奖励")
            time.sleep(2)
            pyautogui.press("esc", presses=2, interval=2)
        else:
            logger.info("没有可领取的奖励")
        logger.info("完成任务：领取无名勋礼奖励")

    @Slot()
    def replenish(self, way):
        """Replenish trailblaze power

        Note:
            Do not include the `self` parameter in the ``Args`` section.

            ``way``:
             ``1``->replenishes by reserved trailblaze power.\n
             ``2``->replenishes by fuel.\n
             ``3``->replenishes by stellar jade.
        Args:
            way (int): Index of way in /res/img.
        Returns:
            True if replenished successfully, False otherwise.
        """
        if self.replenish_time != 0:
            if way == 1 or way == 0:
                if exist("res/img/reserved_trailblaze_power_onclick.png") or click(
                        "res/img/reserved_trailblaze_power.png"):
                    click("res/img/ensure.png")
                    click("res/img/ensure.png")
                    time.sleep(1)
                    pyautogui.click()
                else:
                    logger.error("发生错误，错误编号13")
                    return False
            elif way == 2:
                if click("res/img/fuel.png") or exist("res/img/fuel_onclick.png"):
                    click("res/img/ensure.png")
                    click("res/img/ensure.png")
                    time.sleep(1)
                    pyautogui.click()
                else:
                    logger.error("发生错误，错误编号14")
                    return False
            elif way == 3:
                if click("res/img/stellar_jade.png") or exist("res/img/stellar_jade_onclick.png"):
                    click("res/img/ensure.png")
                    click("res/img/ensure.png")
                    time.sleep(1)
                    pyautogui.click()
                else:
                    logger.error("发生错误，错误编号15")
                    return False
            self.replenish_time -= 1
            return True
        else:
            return False

    @Slot()
    def find_session_name(self, name, scroll=False):
        name1 = "res/img/" + name + ".png"
        name2 = "res/img/" + name + "_onclick.png"
        if not check("res/img/chat_enter.png", max_time=20):
            logger.error("检测超时，编号2")
            return False
        pyautogui.press(self.f4)
        if not check("res/img/f4.png", max_time=20):
            logger.error("检测超时，编号1")
            pyautogui.press("esc")
            return False
        if not (click("res/img/survival_index.png") or click("res/img/survival_index_onclick.png")):
            logger.error("发生错误，错误编号1")
            pyautogui.press("esc")
            return False
        if scroll:
            pyautogui.moveRel(0, 100)
            for i in range(6):
                pyautogui.scroll(-1)
                time.sleep(1)
        if not (click(name1) or exist(name2)):
            logger.error("发生错误，错误编号2")
            pyautogui.press("esc")
            return False
        return True


def check(img_path, interval=0.5, max_time=40):
    """Detects whether the object appears on the screen.

    Args:
        img_path (str): Img path of object.
        interval (float): Interval between checks.
        max_time (int): Maximum number of check times.
    Returns:
        True if obj appeared, False if reach maximum times.
    """
    times = 0
    while True:
        time.sleep(interval)
        if exist(img_path):
            return True
        else:
            times += 1
            if times == max_time:
                return False


def exist(img_path, wait_time=2):
    """Determine if a situation exists.

    Args:
        img_path (str): Img path of the situation.
        wait_time (int): Waiting time before run.
    Returns:
        True if existed, False otherwise.
    """
    time.sleep(wait_time)  # 等待游戏加载
    try:
        img = cv2.imread(img_path)
        if img is None:
            raise FileNotFoundError("无法找到或读取文件 " + img_path + ".png")
        pyautogui.locateOnWindow(img, "崩坏：星穹铁道", confidence=0.95)
        return True
    except pyautogui.ImageNotFoundException:
        return False
    except FileNotFoundError as e:
        logger.exception(e, is_fatal=True)
        return False
    except pyscreeze.PyScreezeException as e:
        logger.exception(e, is_fatal=True)
        return False


def click(img_path, x_add=0, y_add=0, wait_time=2.0, title="崩坏：星穹铁道"):
    """Click the corresponding image on the screen

    Args:
        img_path (str): Img path.
        x_add (int): X-axis offset(px).
        y_add (int): Y-axis offset(px).
        wait_time (float): Waiting time before run(s).
        title (str): Window title.
    Returns:
        True if clicked successfully, False otherwise.
    """
    try:
        time.sleep(wait_time)
        img = cv2.imread(img_path)
        if img is None:
            raise FileNotFoundError("无法找到或读取文件 " + img_path)
        location = pyautogui.locateOnWindow(img, title, confidence=0.95)
        x, y = pyautogui.center(location)
        x += x_add
        y += y_add
        pyautogui.click(x, y)
        return True
    except pyautogui.ImageNotFoundException as e:
        logger.exception(e, is_fatal=True)
        return False
    except ValueError as e:
        logger.exception(e, is_fatal=True)
        return False
    except FileNotFoundError as e:
        logger.exception(e, is_fatal=True)
        return False


def get_screen_center():
    """Get the center of game window.

    Returns:
        tuple(x, y)
    """
    x, y, screen_width, screen_height = (
        pyautogui.getActiveWindow().left,
        pyautogui.getActiveWindow().top,
        pyautogui.getActiveWindow().width,
        pyautogui.getActiveWindow().height,
    )
    return x + screen_width // 2, y + screen_height // 2


def find_level(level: str):
    """Fine battle level

    Returns:
        True if found.
    """
    x, y = get_screen_center()
    pyautogui.moveTo(x - 200, y)
    while True:
        if exist(level, wait_time=1):
            return True
        else:
            pyautogui.scroll(-1)


if __name__ == "__main__":
    logger.addHandler(console_handler)
    click("res/img/echo_of_war (0).png")
