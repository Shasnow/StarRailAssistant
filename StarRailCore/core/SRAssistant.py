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
v0.7.0
作者：雪影
主功能
"""

import subprocess
import time

from PySide6.QtCore import QThread, Signal, Slot

from StarRailCore.extensions.QTHandler import QTHandler
from StarRailCore.utils import Configure, WindowsProcess, Encryption
from StarRailCore.utils.Logger import logger, console_handler
from StarRailCore.utils.SRAOperator import SRAOperator
from StarRailCore.utils.WindowsProcess import find_window, is_process_running

VERSION = "0.7.4"


class Assistant(QThread):
    update_signal = Signal(str)

    def __init__(self, pwd, cloud=False, driver=None):
        super().__init__()
        self.cloud = cloud
        self.driver = driver
        self.stop_flag = False
        self.config = Configure.load()
        settings = self.config["Settings"]
        SRAOperator.cloud = cloud
        SRAOperator.web_driver = driver
        SRAOperator.confidence = settings["confidence"]
        SRAOperator.zoom=settings["zoom"]
        self.pwd = pwd
        self.f1 = settings["F1"]
        self.f2 = settings["F2"]
        self.f4 = settings["F4"]
        if len(logger.handlers) == 1:
            logger.addHandler(QTHandler(self.send_signal))

    def send_signal(self, text):
        self.update_signal.emit(text)

    def request_stop(self):
        self.stop_flag = True
        if self.config["Settings"]["threadSafety"]:
            self.quit()
        else:
            self.terminate()

    @Slot()
    def run(self):
        logger.info("SRAv" + VERSION + " 创建任务喵~")
        config = self.config
        tasks = []
        if not self.cloud:
            if config["Mission"]["startGame"]:
                account_text = Encryption.load()
                password_text = self.pwd
                tasks.append((self.start_game, (
                    config["StartGame"]["gamePath"],
                    config["StartGame"]["pathType"],
                    config["StartGame"]["channel"],
                    config["StartGame"]["autoLogin"],
                    account_text,
                    password_text,
                )))
            tasks.append((self.check_game, ()))
        else:
            tasks.append((self.wait_game_load, ()))

        if config["Mission"]["trailBlazePower"]:
            tasks.append((self.trailblazer_power, ()))
        if config["ReceiveRewards"]["enable"]:
            tasks.append((self.receive_rewards, ()))
        if config["Mission"]["quitGame"]:
            tasks.append((self.quit_game, ()))
        if config["Mission"]["simulatedUniverse"]:
            tasks.append((self.divergent_universe, (config["DivergentUniverse"]["times"],)))

        for task, args in tasks:
            if not self.stop_flag:
                if not task(*args):
                    logger.warning("任务由于异常而终止")
                    break
            else:
                logger.info("已停止")
        else:
            logger.info("任务全部完成\n")

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
    def launch_game(self, game_path, path_type):
        """Launch game

        Try to run_flag the file that game path points at.

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
        if not Popen(game_path):
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

        Try to run_flag the file that game path points at.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            path (str): File path.
            path_type (str): Launcher
            channel: 0 -> official, 1 -> bilibili
        Returns:
            True if successfully launched, False otherwise.

        """
        if not self.path_check(path, path_type):
            logger.warning("路径无效")
            return False
        if not Popen(path):
            return False
        logger.info("等待启动器启动")
        time.sleep(5)
        times = 0
        while times < 20:
            if is_process_running("HYP.exe"):
                if channel == 0:
                    click('res/img/start_game.png', title="米哈游启动器")
                else:
                    click('res/img/start_game.png')
                logger.info("尝试启动游戏")
                for i in range(10):
                    time.sleep(1)
                    if is_process_running("StarRail.exe"):
                        logger.info("启动成功")
                        WindowsProcess.task_kill("HYP.exe")
                        logger.info("已为您关闭启动器")
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
        write(account)
        time.sleep(1)
        press_key("tab")
        time.sleep(0.2)
        write(password)
        press_key("enter")
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
            write(account)
        if click('res/img/bilibili_pwd.png'):
            time.sleep(0.5)
            write(password)
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
            if check("res/img/chat_enter.png", max_time=40):
                return True
            else:
                logger.warning("检测超时，尝试重新启动")
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
            if check("res/img/quit.png", max_time=120):
                x, y = get_screen_center()
                if exist("res/img/12+.png"):
                    click_point(x, y)
                    time.sleep(3)
                logger.info("开始游戏")
                click_point(x, y)
                time.sleep(3)
                click_point(x, y)
            else:
                logger.warning("加载时间过长，请重试")
                return False
        elif channel == 1:
            self.login_bilibili(account, password)
            if check("res/img/quit.png"):
                x, y = get_screen_center()
                if exist("res/img/12+.png"):
                    click_point(x, y)
                    time.sleep(3)
                logger.info("开始游戏")
                click_point(x, y)
                time.sleep(3)
                click_point(x, y)
            else:
                logger.warning("加载时间过长，请重试")
                return False
        return self.wait_game_load()

    @Slot()
    def wait_game_load(self):
        times = 0
        while True:
            time.sleep(0.2)
            if click("res/img/train_supply.png"):
                time.sleep(4)
                moveRel(0, +400)
                click_point()
            if exist("res/img/chat_enter.png") or exist("res/img/phone.png", wait_time=0):
                return True
            else:
                times += 1
                if times == 50:
                    logger.error("发生错误，进入游戏但未处于大世界")
                    return False

    def trailblazer_power(self):
        tasks = []
        config = self.config
        self.replenish_flag = config["Replenish"]["enable"]
        self.replenish_way = config["Replenish"]["way"]
        self.replenish_time = config["Replenish"]["runTimes"]
        if config["OrnamentExtraction"]["enable"]:
            tasks.append((self.ornament_extraction, (
                config["OrnamentExtraction"]["level"],
                config["OrnamentExtraction"]["runTimes"],
            )))
        if config["CalyxGolden"]["enable"]:
            tasks.append((self.calyx_golden, (
                config["CalyxGolden"]["level"],
                config["CalyxGolden"]["singleTimes"],
                config["CalyxGolden"]["runTimes"],
            )))
        if config["CalyxCrimson"]["enable"]:
            tasks.append((self.calyx_crimson, (
                config["CalyxCrimson"]["level"],
                config["CalyxCrimson"]["singleTimes"],
                config["CalyxCrimson"]["runTimes"],
            )))
        if config["StagnantShadow"]["enable"]:
            tasks.append((self.stagnant_shadow, (
                config["StagnantShadow"]["level"],
                config["StagnantShadow"]["runTimes"],
            )))
        if config["CaverOfCorrosion"]["enable"]:
            tasks.append((self.caver_of_corrosion, (
                config["CaverOfCorrosion"]["level"],
                config["CaverOfCorrosion"]["runTimes"]
            )))
        if config["EchoOfWar"]["enable"]:
            tasks.append((self.echo_of_war, (
                config["EchoOfWar"]["level"],
                config["EchoOfWar"]["runTimes"]
            )))
        for task, args in tasks:
            if self.stop_flag:
                break
            task(*args)
        else:
            return True
        return False

    def receive_rewards(self) -> bool:
        tasks = []
        config = self.config
        if config["Mission"]["trailBlazerProfile"]:
            tasks.append((self.trailblazer_profile, ()))
        if config["Mission"]["assignment"]:
            tasks.append((self.assignments_reward, ()))
        if config["Mission"]["redeemCode"]:
            tasks.append((self.redeem_code, (config["RedeemCode"]["codeList"],)))
        if config["Mission"]["mail"]:
            tasks.append((self.mail, ()))

        tasks2 = []
        if config["Mission"]["dailyTraining"]:
            tasks2.append(self.daily_training_reward)
        if config["Mission"]["namelessHonor"]:
            tasks2.append(self.nameless_honor)
        if config["Mission"]["giftOfOdyssey"]:
            tasks2.append(self.gift_of_odyssey)

        logger.info("领取奖励")
        if not check("res/img/chat_enter.png", max_time=20):
            logger.error("检测超时，编号2")
            return False
        if len(tasks) != 0:
            press_key("esc")
            for task, args in tasks:
                if not self.stop_flag:
                    task(*args)
            else:
                time.sleep(2)
            press_key("esc")

        for task in tasks2:
            if self.stop_flag:
                break
            task()
        else:
            return True
        return False

    @Slot()
    def trailblazer_profile(self):
        """Mission trailblaze profile"""
        logger.info("执行任务：签证奖励")
        if click("res/img/more_with_something.png"):
            if click("res/img/trailblazer_profile_finished.png"):
                if click("res/img/assistance_reward.png"):
                    time.sleep(2)
                    press_key("esc", presses=2, interval=2)
                else:
                    logger.info("没有可领取的奖励1")
                    press_key("esc")
            else:
                logger.info("没有可领取的奖励2")
        else:
            logger.info("没有可领取的奖励3")
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
        if len(redeem_code_list) == 0:
            logger.warning("未填写兑换码")
        for code in redeem_code_list:
            if click("res/img/more.png", wait_time=1) or click("res/img/more_with_something.png", wait_time=1):
                if click("res/img/redeem_code.png"):
                    time.sleep(2)
                    click_point(*get_screen_center())
                    write(code)
                    click("res/img/ensure.png")
                    time.sleep(2)
                    press_key("esc")
                else:
                    logger.error("发生错误，错误编号16")
            else:
                logger.error("发生错误，错误编号17")
        logger.info("任务完成：领取兑换码")

    @Slot()
    def mail(self):
        """Open mailbox and pick up mails."""
        logger.info("执行任务：领取邮件")
        if click("res/img/mailbox_mail.png"):
            if click("res/img/claim_all_mail.png"):
                time.sleep(2)
                press_key("esc", presses=2, interval=2)
            else:
                logger.info("没有可以领取的邮件")
        else:
            logger.info("没有可以领取的邮件")
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
        press_key(self.f1)
        if click("res/img/gift_of_odyssey.png"):
            pass
        if click("res/img/gift_receive.png") or click("res/img/gift_receive2.png"):
            logger.info("领取成功")
            time.sleep(2)
            press_key("esc", presses=2, interval=2)
        else:
            logger.info("没有可以领取的巡星之礼")
            press_key("esc")
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
            return False
        if exist("res/img/no_save.png"):
            logger.warning("当前暂无可用存档，请前往[差分宇宙]获取存档")
            press_key("esc")
            return
        if not find_level(level):
            return
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
                    logger.info("体力不足")
                    press_key("esc", interval=1, presses=3)
                    return
            while not exist("res/img/f3.png"):
                pass
            press_key_for_a_while("w", 2.5)
            click_point()
            self.battle_star(battle_time)
        self.update_signal.emit("任务完成：饰品提取")

    @Slot()
    def calyx_golden(self, level_index, single_time=1, battle_time=1):
        self.battle("拟造花萼（金）",
                    "calyx(golden)",
                    level_index,
                    battle_time,
                    False,
                    single_time)

    @Slot()
    def calyx_crimson(self, level_index, single_time=1, battle_time=1):
        self.battle("拟造花萼（赤）",
                    "calyx(crimson)",
                    level_index,
                    battle_time,
                    False,
                    single_time,
                    y_add=-30)

    @Slot()
    def stagnant_shadow(self, level_index, battle_time=1):
        self.battle("凝滞虚影",
                    "stagnant_shadow",
                    level_index,
                    battle_time,
                    False,
                    None)

    @Slot()
    def caver_of_corrosion(self, level_index, battle_time=1):
        self.battle("侵蚀隧洞",
                    "caver_of_corrosion",
                    level_index,
                    battle_time,
                    True,
                    None)

    @Slot()
    def echo_of_war(self, level_index, battle_time=1):
        self.battle("历战余响",
                    "echo_of_war",
                    level_index,
                    battle_time,
                    True,
                    None,
                    x_add=770,
                    y_add=25)

    def battle(self,
               mission_name: str,
               level_belonging: str,
               level_index: int,
               battle_time: int,
               scroll_flag: bool,
               multi: None | int = None,
               x_add: int = 650,
               y_add: int = 0):
        """Battle Any

            Note:
                Do not include the `self` parameter in the ``Args`` section.
            Args:

                mission_name (str): The name of this mission.
                level_belonging (str): The series to which the level belongs.
                level_index (int): The index of level in /res/img.
                battle_time (int): Number of times the task was executed.
                scroll_flag (bool): Whether scroll or not when finding session.
                multi (None|int): If this mission can battle multiply at single time,
                                    this arg must be an int, None otherwise.
                x_add: int
                y_add: int
            Returns:
                None
        """
        logger.info(f"执行任务：{mission_name}")
        level = f"res/img/{level_belonging} ({level_index}).png"
        if not self.find_session_name(level_belonging, scroll_flag):
            return False
        if not find_level(level):
            return
        if click(level, x_add=x_add, y_add=y_add):
            if not check('res/img/battle.png'):  # 等待传送
                logger.error("检测超时，编号4")
                return
            if multi is not None:
                for i in range(multi - 1):
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
                    press_key("esc", interval=1, presses=3)
                    return
            if click("res/img/battle_star.png"):
                self.battle_star(battle_time)
            else:
                logger.error("发生错误，错误编号4")
        logger.info(f"任务完成：{mission_name}")

    @Slot()
    def battle_star(self, battle_time: int):
        logger.info("开始战斗")
        logger.info("请检查自动战斗和倍速是否开启")
        if check("res/img/q.png", max_time=10):
            press_key("v")
        while battle_time > 1:
            logger.info(f"剩余次数{battle_time}")
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
                    press_key("esc")
                    if not click("res/img/quit_battle.png"):
                        logger.error("发生错误，错误编号12")
                    logger.info("退出战斗")
                    if not check("res/img/battle.png"):
                        logger.error("发生错误，错误编号23")
                    press_key("esc")
                    break
            battle_time -= 1
            time.sleep(3)
        else:
            self.wait_battle_end()
            if not click("res/img/quit_battle.png"):
                logger.error("发生错误，错误编号12")
            logger.info("退出战斗")
            if check("res/img/battle.png",max_time=10):
                press_key("esc")

    @Slot()
    def wait_battle_end(self):
        wait_battle_end()

    @Slot()
    def assignments_reward(self):
        """Receive assignment reward"""
        logger.info("执行任务：领取派遣奖励")
        if not click("res/img/assignments_none.png"):
            logger.info("没有可领取的奖励")
            return
        if not check("res/img/assignment_page.png", max_time=15):
            if not click("res/img/assignment_page2.png"):
                logger.error("检测超时，编号5")
                press_key("esc")
                return
        if click("res/img/assignments_reward.png"):
            if click("res/img/assign_again.png"):
                logger.info("再次派遣")
                time.sleep(4)
                press_key("esc")
            else:
                logger.error("发生错误，错误编号6")
                press_key("esc")
        else:
            logger.info("没有可以领取的派遣奖励")
            press_key("esc")
            time.sleep(2)
        logger.info("任务完成：领取派遣奖励")

    @Slot()
    def daily_training_reward(self):
        """Receive daily training reward"""
        logger.info("执行任务：领取每日实训奖励")
        if not check("res/img/chat_enter.png", max_time=20):
            logger.error("检测超时，编号2")
            return
        press_key(self.f4)
        if not check("res/img/f4.png", max_time=20):
            logger.error("检测超时，编号1")
            return
        if exist("res/img/survival_index_onclick.png"):
            logger.info("没有可领取的奖励")
            press_key("esc")
        else:
            while click("res/img/daily_reward.png"):
                moveRel(0, 50)
            if click("res/img/daily_train_reward.png"):
                time.sleep(2)
                press_key("esc", presses=2, interval=2)
            else:
                logger.info("没有可领取的奖励")
                press_key("esc")
        logger.info("任务完成：领取每日实训奖励")

    @Slot()
    def nameless_honor(self):
        """Receive nameless honor reward"""
        logger.info("执行任务：领取无名勋礼奖励")
        if not check("res/img/chat_enter.png", max_time=20):
            logger.error("检测超时，编号2")
            return
        press_key(self.f2)
        if not check("res/img/f2.png", max_time=20):
            logger.error("检测超时，编号1")
            return
        if click("res/img/nameless_honor_reward_receive.png"):
            logger.info("领取了无名勋礼奖励")
            time.sleep(2)
            press_key("esc")
        if not click("res/img/nameless_honor_task.png"):
            logger.info("没有可领取的奖励")
            press_key("esc")
            return
        if not click("res/img/nameless_honor_task_receive.png"):
            logger.info("没有已完成的无名勋礼任务")
            press_key("esc")
            return
        logger.info("成功领取无名勋礼任务奖励")
        time.sleep(1)
        press_key("esc")
        if not click("res/img/nameless_honor_reward.png"):
            logger.info("没有可领取的奖励")
            return
        if click("res/img/nameless_honor_reward_receive.png"):
            logger.info("领取了无名勋礼奖励")
            time.sleep(2)
            press_key("esc", presses=2, interval=2)
        else:
            logger.info("没有可领取的奖励")
        logger.info("完成任务：领取无名勋礼奖励")

    @Slot()
    def replenish(self, way):
        """Replenish trailblaze power

        Note:
            Do not include the `self` parameter in the ``Args`` section.

            ``way``:
             - ``1``->replenishes by reserved trailblaze power.\n
             - ``2``->replenishes by fuel.\n
             - ``3``->replenishes by stellar jade.
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
                    click_point()
                else:
                    logger.error("发生错误，错误编号13")
                    return False
            elif way == 2:
                if click("res/img/fuel.png") or exist("res/img/fuel_onclick.png"):
                    click("res/img/ensure.png")
                    click("res/img/ensure.png")
                    time.sleep(1)
                    click_point()
                else:
                    logger.error("发生错误，错误编号14")
                    return False
            elif way == 3:
                if click("res/img/stellar_jade.png") or exist("res/img/stellar_jade_onclick.png"):
                    click("res/img/ensure.png")
                    click("res/img/ensure.png")
                    time.sleep(1)
                    click_point()
                else:
                    logger.error("发生错误，错误编号15")
                    return False
            self.replenish_time -= 1
            return True
        else:
            return False

    @Slot()
    def find_session_name(self, name, scroll_flag=False):
        name1 = "res/img/" + name + ".png"
        name2 = "res/img/" + name + "_onclick.png"
        if not check("res/img/chat_enter.png", max_time=20):
            logger.error("检测超时，编号2")
            return False
        press_key(self.f4)
        if not check("res/img/f4.png", max_time=20):
            logger.error("检测超时，编号1")
            press_key("esc")
            return False
        if not (click("res/img/survival_index.png") or click("res/img/survival_index_onclick.png")):
            logger.error("发生错误，错误编号1")
            press_key("esc")
            return False
        if scroll_flag:
            time.sleep(2)
            moveRel(0, 100)
            for i in range(6):
                scroll(-5)
                time.sleep(1)
        if not (click(name1) or exist(name2)):
            logger.error("发生错误，错误编号2")
            press_key("esc")
            return False
        return True

    def divergent_universe(self, times: int):
        logger.info("执行任务：差分宇宙-周期演算")
        for _ in range(times):
            if check("res/img/differential_universe_start.png", max_time=20):
                click("res/img/differential_universe_start.png")
            else:
                logger.error("发生错误，错误编号18")
                return False
            if not click("res/img/periodic_calculus.png"):
                logger.error("发生错误，错误编号19")
                return False
            if click("res/img/nobody.png"):
                click("res/img/preset_formation.png")
                click("res/img/team1.png")
            if not click("res/img/launch_differential_universe.png"):
                logger.error("发生错误，错误编号20")
                return False

            logger.info("等待进入差分宇宙")
            if not check("res/img/base_effect_select.png",max_time=25):
                logger.error("超时")
                return False
            logger.info("选择基础效果")
            if not click("res/img/collection.png"):
                x,y=get_screen_center()
                click_point(x-250,y)
            click("res/img/ensure2.png",wait_time=1)
            if not check("res/img/equation_select.png",max_time=25):
                logger.error("超时")
                return False
            logger.info("选择方程")
            while check("res/img/equation_select.png", max_time=3):
                if not click("res/img/collection.png"):
                    click_point(*get_screen_center())
                click("res/img/ensure2.png",wait_time=1)
                if check("res/img/close.png", max_time=4):
                    press_key("esc")

            logger.info("获得奇物")
            if check("res/img/close.png"):
                press_key("esc")

            logger.info("选择祝福")
            if check("res/img/blessing_select.png", max_time=4):
                click_point(*get_screen_center())
                click("res/img/ensure2.png")
            else:
                logger.error("失败/超时")
                return False
            while check("res/img/close.png", max_time=4):
                press_key("esc")
            time.sleep(1)
            # press_key("esc", presses=1)

            logger.info("移动")
            press_key_for_a_while("w", during=3.2)
            logger.info("进入战斗")
            click_point(*get_screen_center())
            if check("res/img/q.png", max_time=10):
                press_key("v")
            logger.info("等待战斗结束")
            check("res/img/blessing_select.png")
            logger.info("选择祝福")
            while exist("res/img/blessing_select.png"):
                if not click("res/img/collection.png"):
                    click_point(*get_screen_center())
                click("res/img/ensure2.png")
            logger.info("退出并结算")
            press_key("esc")
            click("res/img/end_and_settle.png")
            click("res/img/ensure2.png")
            logger.info("返回主界面")
            if check("res/img/return.png"):
                click("res/img/return.png")
        press_key("esc")
        logger.info("Mission accomplished")
        return True

    @staticmethod
    def quit_game() -> bool:
        logger.info("退出游戏")
        return WindowsProcess.task_kill("StarRail.exe")


def Popen(path: str):
    try:
        subprocess.Popen(path)
        return True
    except FileNotFoundError as e:
        logger.error(e)
        return False
    except OSError:
        logger.error("路径无效或权限不足")
        return False


def check(img_path, interval=0.5, max_time=40):
    return SRAOperator.check(img_path, interval, max_time)


def click(img_path: str, x_add=0, y_add=0, wait_time=2.0, title="崩坏：星穹铁道") -> bool:
    return SRAOperator.click_img(img_path, x_add, y_add, wait_time, title)


def click_point(x: int = None, y: int = None) -> bool:
    return SRAOperator.click_point(x, y)


def write(content: str = "") -> bool:
    return SRAOperator.write(content)


def press_key(key: str, presses: int = 1, interval: float = 2) -> bool:
    return SRAOperator.press_key(key, presses, interval)


def exist(img_path, wait_time=2) -> bool:
    return SRAOperator.exist(img_path, wait_time)


def get_screen_center() -> tuple[int, int]:
    return SRAOperator.get_screen_center()


def moveRel(x_offset: int, y_offset: int) -> bool:
    return SRAOperator.moveRel(x_offset, y_offset)


def find_level(level: str) -> bool:
    return SRAOperator.find_level(level)


def press_key_for_a_while(key: str, during: float = 0) -> bool:
    return SRAOperator.press_key_for_a_while(key, during)


def wait_battle_end() -> bool:
    return SRAOperator.wait_battle_end()


def scroll(distance: int) -> bool:
    return SRAOperator.scroll(distance)


if __name__ == "__main__":
    logger.addHandler(console_handler)
    click("res/img/echo_of_war (0).png")
