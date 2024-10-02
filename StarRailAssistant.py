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
beta v0.7
作者：雪影
主功能
"""

import json
import time
import subprocess
import cv2
import pyautogui
import pyscreeze
import win32con
import win32gui
import encryption
from PyQt5.QtCore import QThread, pyqtSignal


# noinspection PyUnresolvedReferences


class Assistant(QThread):
    update_signal = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.stop_flag = False

    def request_stop(self):
        self.stop_flag = True

    def run(self):
        with open("data/config.json", "r", encoding="utf-8") as file:
            config = json.load(file)
        if not self.stop_flag:
            if config["starGame"]:
                with open("data/privacy.sra", "rb") as sra_file:
                    privacy = sra_file.readlines()
                    try:
                        pwd = privacy[1]
                        acc = privacy[0]
                        password_text = encryption.decrypt_word(pwd)
                        account_text = encryption.decrypt_word(acc)
                    except IndexError:
                        password_text = ''
                        account_text = ''
                self.star_game(
                    config["gamePath"],
                    config["loginFlag"],
                    account_text,
                    password_text,
                )
        if not self.check_game():
            self.finished.emit()
            return
        if not self.stop_flag:
            if config["trailBlazerProfile"]:
                self.trailblazer_profile()
        if not self.stop_flag:
            if config["redeemCode"]:
                self.redeem_code(config["redeemCodeList"])
        if not self.stop_flag:
            if config["assignment"]:
                self.assignments_reward()
        if not self.stop_flag:
            if config["giftOfOdyssey"]:
                self.gift_of_odyssey()
        if not self.stop_flag:
            if config["mail"]:
                self.mail()
        if not self.stop_flag:
            if config["trailBlazePower"]:
                self.replenish_flag = config["replenish_trail_blaze_power"]
                self.replenish_way = config["replenish_way"]
                self.replenish_time = config["replenish_trail_blaze_power_run_time"]
                if not self.stop_flag:
                    if config["ornament_extraction"]:
                        self.ornament_extraction(
                            config["ornament_extraction_level"],
                            config["ornament_extraction_run_time"],
                        )
                if not self.stop_flag:
                    if config["calyx_golden"]:
                        self.calyx_golden(
                            config["calyx_golden_level"],
                            config["calyx_golden_battle_time"],
                            config["calyx_golden_run_time"],
                        )
                if not self.stop_flag:
                    if config["calyx_crimson"]:
                        self.calyx_crimson(
                            config["calyx_crimson_level"],
                            config["calyx_crimson_battle_time"],
                            config["calyx_crimson_run_time"],
                        )
                if not self.stop_flag:
                    if config["stagnant_shadow"]:
                        self.stagnant_shadow(
                            config["stagnant_shadow_level"],
                            config["stagnant_shadow_run_time"],
                        )
                if not self.stop_flag:
                    if config["caver_of_corrosion"]:
                        self.caver_of_corrosion(
                            config["caver_of_corrosion_level"],
                            config["caver_of_corrosion_run_time"],
                        )
                if not self.stop_flag:
                    if config["echo_of_war"]:
                        self.echo_of_war(
                            config["echo_of_war_level"], config["echo_of_war_run_time"]
                        )
        if not self.stop_flag:
            if config["dailyTraining"]:
                self.daily_training_reward()
        if not self.stop_flag:
            if config["namelessHonor"]:
                self.nameless_honor()
        if not self.stop_flag:
            if config["quitGame"]:
                self.kill_game()
        if self.stop_flag:
            self.update_signal.emit("已停止")
            self.finished.emit()
        else:
            self.update_signal.emit("任务全部完成\n")
            self.finished.emit()

    def check_game(self):
        """Check that the game is running.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Returns:
            True if game is running,False if not.
        """
        window_title = "崩坏：星穹铁道"
        hwnd = find_window(window_title)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)  # 确保窗口不是最小化状态
            win32gui.SetForegroundWindow(hwnd)
            return True
        else:
            self.update_signal.emit(
                "未找到窗口:" + window_title + "或许你还没有运行游戏"
            )
            return False

    def path_check(self, path):
        """Check game path.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            path (str): File path.
        Returns:
            True if path points to 'StraRail.exe', False otherwise.
        """
        if path:
            if path.split("/")[-1].split(".")[0] != "StarRail":
                self.update_signal.emit("你尝试输入一个其他应用的路径")
                return False
            else:
                return True
        else:
            self.update_signal.emit("游戏路径为空")
            return False

    def kill_game(self):
        """Kill the game"""
        command = f"taskkill /F /IM StarRail.exe"
        # 执行命令
        subprocess.run(command, shell=True, check=True)
        self.update_signal.emit("退出游戏")

    def launch_game(self, game_path):
        """Launch game

        Try to run the file that game path points at.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            game_path (str): File path.
        Returns:
            True if successfully launched, False otherwise.

        """
        if not self.path_check(game_path):
            self.update_signal.emit("路径无效")
            return False
        try:
            subprocess.Popen(game_path)
        except OSError:
            self.update_signal.emit("路径无效或权限不足")
            return False
        self.update_signal.emit("等待游戏启动")
        time.sleep(5)
        times = 0
        while True:
            if find_window("崩坏：星穹铁道"):
                self.update_signal.emit("启动成功")
                return True
            else:
                time.sleep(0.5)
                times += 1
                if times == 40:
                    self.update_signal.emit("启动时间过长，请尝试手动启动")
                    return False

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
        if check("res/img/welcome.png", interval=0.1, max_time=10):  # 进入登录界面的标志
            self.update_signal.emit("已登录")
            return True
        if check("res/img/not_logged_in.png", max_time=4):
            if click("res/img/login_with_account.png"):
                self.update_signal.emit("登录到" + account)
                time.sleep(1)
                pyautogui.write(account)
                time.sleep(1)
                pyautogui.press("tab")
                time.sleep(0.1)
                pyautogui.write(password)
                pyautogui.press("enter")
                click("res/img/agree.png", -158)
                if click("res/img/enter_game.png"):
                    times = 0
                    while True:
                        time.sleep(0.2)
                        times += 1
                        if times == 10:
                            self.update_signal.emit(
                                "长时间未成功登录，可能密码错误或需要新设备验证"
                            )
                            return False
                        else:
                            if exist("res/img/welcome.png"):
                                self.update_signal.emit("登录成功")
                                return True
                else:
                    self.update_signal.emit("发生错误，错误编号9")
                    return False
            else:
                self.update_signal.emit("发生错误，错误编号10")
                return False
        else:
            self.update_signal.emit("发生错误，错误编号11")
            return False

    def star_game(self, game_path, login_flag=False, account="", password=""):
        """Launch and enter game.

        If the game is already star, skip this section.
        If not, launch and enter game.
        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            game_path (str): Path of game.
            login_flag (bool): Whether to enable the launch game function.
            account (str): User account.
            password (str): User password.
        Returns:
            True if entered game successfully, False otherwise.

        """
        if find_window("崩坏：星穹铁道"):
            self.update_signal.emit("游戏已经启动")
            if check('res/img/chat_enter.png', max_time=10):
                return True
        if self.launch_game(game_path):
            time.sleep(2)
            if login_flag and account:
                self.login(account, password)
            if check("res/img/quit.png"):
                x, y = get_screen_center()
                if exist("res/img/12+.png"):
                    pyautogui.click(x, y)
                    time.sleep(3)
                self.update_signal.emit("开始游戏")
                pyautogui.click(x, y)
                time.sleep(3)
                pyautogui.click(x, y)
                times = 0
                while True:
                    time.sleep(0.2)
                    if exist("res/img/chat_enter.png"):
                        return True
                    else:
                        times += 1
                        if times == 50:
                            self.update_signal.emit("发生错误，进入游戏但未处于大世界")
                            return False
            else:
                self.update_signal.emit("加载时间过长，请重试")
                return False
        else:
            self.update_signal.emit("游戏启动失败")
            return False

    def trailblazer_profile(self):
        """Mission trailblaze profile"""
        self.update_signal.emit("执行任务：签证奖励")
        time.sleep(2)
        pyautogui.press("esc")
        if click("res/img/more_with_something.png"):
            pyautogui.moveRel(20, 0)
            if click("res/img/trailblazer_profile_finished.png"):
                if click("res/img/assistance_reward.png"):
                    time.sleep(2)
                    pyautogui.press("esc", presses=3, interval=2)
                else:
                    self.update_signal.emit("没有可领取的奖励1")
                    pyautogui.press("esc", presses=2, interval=2)
            else:
                self.update_signal.emit("没有可领取的奖励2")
                pyautogui.press("esc")
        else:
            self.update_signal.emit("没有可领取的奖励3")
            pyautogui.press("esc")
        self.update_signal.emit("任务完成：签证奖励\n")
        time.sleep(3)

    def redeem_code(self, redeem_code_list):
        """Fills in redeem code and redeems them.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            redeem_code_list (list): The list thar stored redeem codes.
        Returns:
            None
        """
        self.update_signal.emit("执行任务：领取兑换码")
        time.sleep(2)
        pyautogui.press("esc")
        if len(redeem_code_list) == 0:
            for code in redeem_code_list:
                if click("res/img/more.png") or click(
                        "res/img/more_with_something.png"
                ):
                    if click("res/img/redeem_code.png"):
                        time.sleep(2)
                        pyautogui.click(get_screen_center())
                        pyautogui.write(code)
                        click("res/img/ensure.png")
                        time.sleep(2)
                        pyautogui.press("esc")
                    else:
                        self.update_signal.emit("发生错误，错误编号16")
                else:
                    self.update_signal.emit("发生错误，错误编号17")
        else:
            self.update_signal.emit("未填写兑换码")
        time.sleep(2)
        pyautogui.press("esc")
        self.update_signal.emit("任务完成：领取兑换码\n")

    def mail(self):
        """Open mailbox and pick up mails."""
        self.update_signal.emit("执行任务：领取邮件")
        time.sleep(2)
        pyautogui.press("esc")
        if click("res/img/mailbox_mail.png"):
            if click("res/img/claim_all_mail.png"):
                time.sleep(2)
                pyautogui.press("esc")
                time.sleep(2)
                pyautogui.press("esc")
                time.sleep(2)
                pyautogui.press("esc")
            else:
                self.update_signal.emit("没有可以领取的邮件")
                pyautogui.press("esc")
        else:
            self.update_signal.emit("没有可以领取的邮件")
            pyautogui.press("esc")
        self.update_signal.emit("任务完成：领取邮件\n")
        time.sleep(3)

    def gift_of_odyssey(self):
        """Open the activity screen to receive gift_of_odyssey.

        Remember to update the gift_of_odyssey.png in each game version.
        """
        self.update_signal.emit("执行任务：巡星之礼")
        time.sleep(2)
        pyautogui.press("f1")
        if click("res/img/gift_of_odyssey.png"):
            pass
        if click("res/img/gift_receive.png"):
            self.update_signal.emit("领取成功")
            time.sleep(2)
            pyautogui.press("esc")
            time.sleep(2)
            pyautogui.press("esc")
        else:
            self.update_signal.emit("没有可以领取的巡星之礼")
            pyautogui.press("esc")
        self.update_signal.emit("任务完成：巡星之礼\n")
        time.sleep(3)

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
        self.update_signal.emit("执行任务：饰品提取")
        level = "res/img/ornament_extraction (" + str(level_index) + ").png"
        pyautogui.press("f4")
        time.sleep(3)
        if click("res/img/survival_index.png") or exist(
                "res/img/survival_index_onclick.png"
        ):
            if click("res/img/ornament_extraction.png") or exist(
                    "res/img/ornament_extraction_onclick.png"
            ):
                if exist("res/img/no_save.png"):
                    self.update_signal.emit(
                        "当前暂无可用存档，请前往[差分宇宙]获取存档"
                    )
                    pyautogui.press("esc")
                    time.sleep(1)
                    return
                find_level(level)
                if click(level, x_add=400):
                    time.sleep(5)  # 等待传送
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
                        time.sleep(3)
                        pyautogui.keyUp("w")
                        pyautogui.click()
                        self.update_signal.emit("开始战斗")
                        self.update_signal.emit("请检查自动战斗和倍速是否开启")
                        times = 0
                        while times != 10:
                            if exist("res/img/q.png", interval=1):
                                pyautogui.press("v")
                                break
                            else:
                                times += 1
                        while battle_time > 1:
                            self.update_signal.emit("剩余次数" + str(battle_time))
                            if self.wait_battle_end():
                                if click("res/img/again.png"):
                                    if exist("res/img/replenish.png"):
                                        if self.replenish_flag and self.replenish_time:
                                            self.replenish(self.replenish_way)
                                            click("res/img/again.png")
                                        else:
                                            self.update_signal.emit("体力不足")
                                            pyautogui.press("esc")
                                            if click("res/img/quit_battle.png"):
                                                self.update_signal.emit("退出战斗")
                                            else:
                                                self.update_signal.emit(
                                                    "发生错误，错误编号12"
                                                )
                                            break
                                    battle_time -= 1
                                    time.sleep(3)
                                else:
                                    self.update_signal.emit("发生错误，错误编号5")
                        else:
                            if self.wait_battle_end():
                                if click("res/img/quit_battle.png"):
                                    self.update_signal.emit("退出战斗")
                                else:
                                    self.update_signal.emit("发生错误，错误编号12")
                    else:
                        self.update_signal.emit("发生错误，错误编号3")
            else:
                self.update_signal.emit("发生错误，错误编号2")
        else:
            self.update_signal.emit("发生错误，错误编号1")
        self.update_signal.emit("任务完成：饰品提取\n")
        time.sleep(5)

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
        self.update_signal.emit("执行任务：拟造花萼（金）")
        level = "res/img/calyx(golden) (" + str(level_index) + ").png"
        pyautogui.press("f4")
        time.sleep(3)
        if click("res/img/survival_index.png") or exist(
                "res/img/survival_index_onclick.png"
        ):
            if click("res/img/calyx(golden).png") or exist(
                    "res/img/calyx(golden)_onclick.png"
            ):
                find_level(level)
                if click(level, x_add=600, y_add=10):
                    time.sleep(5)  # 等待传送
                    for i in range(single_time - 1):
                        click("res/img/plus.png", interval=0.5)
                    time.sleep(2)
                    if click("res/img/battle.png"):
                        if exist("res/img/replenish.png"):
                            if self.replenish_flag:
                                self.replenish(self.replenish_way)
                                click("res/img/battle.png")
                            else:
                                self.update_signal.emit("体力不足")
                                pyautogui.press("esc", interval=1, presses=2)
                                return
                        if click("res/img/battle_star.png"):
                            self.update_signal.emit("开始战斗")
                            self.update_signal.emit("请检查自动战斗和倍速是否开启")
                            times = 0
                            while times != 10:
                                if exist("res/img/q.png", interval=1):
                                    pyautogui.press("v")
                                    break
                                else:
                                    times += 1
                            while battle_time > 1:
                                self.update_signal.emit(
                                    "剩余次数" + str(battle_time - 1)
                                )
                                if self.wait_battle_end():
                                    if click("res/img/again.png"):
                                        if exist("res/img/replenish.png"):
                                            if (
                                                    self.replenish_flag
                                                    and self.replenish_time
                                            ):
                                                self.replenish(self.replenish_way)
                                                click("res/img/again.png")
                                            else:
                                                self.update_signal.emit("体力不足")
                                                pyautogui.press("esc")
                                                if click("res/img/quit_battle.png"):
                                                    self.update_signal.emit("退出战斗")
                                                else:
                                                    self.update_signal.emit(
                                                        "发生错误，错误编号12"
                                                    )
                                                break
                                        battle_time -= 1
                                        time.sleep(3)
                                    else:
                                        self.update_signal.emit("发生错误，错误编号5")
                            else:
                                if self.wait_battle_end():
                                    if click("res/img/quit_battle.png"):
                                        self.update_signal.emit("退出战斗")
                                    else:
                                        self.update_signal.emit("发生错误，错误编号12")
                        else:
                            self.update_signal.emit("发生错误，错误编号4")
                    else:
                        self.update_signal.emit("发生错误，错误编号3")
            else:
                self.update_signal.emit("发生错误，错误编号2")
        else:
            self.update_signal.emit("发生错误，错误编号1")
        self.update_signal.emit("任务完成：拟造花萼（金）\n")
        time.sleep(3)

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
        self.update_signal.emit("执行任务：拟造花萼（赤）")
        level = "res/img/calyx(crimson) (" + str(level_index) + ").png"
        pyautogui.press("f4")
        time.sleep(3)
        if click("res/img/survival_index.png") or exist(
                "res/img/survival_index_onclick.png"
        ):
            if click("res/img/calyx(crimson).png") or exist(
                    "res/img/calyx(crimson)_onclick.png"
            ):
                find_level(level)
                if click(level, x_add=400):
                    time.sleep(5)  # 等待传送
                    for i in range(single_time - 1):
                        click("res/img/plus.png", interval=0.5)
                    time.sleep(2)
                    if click("res/img/battle.png"):
                        if exist("res/img/replenish.png"):
                            if self.replenish_flag:
                                self.replenish(self.replenish_way)
                                click("res/img/battle.png")
                            else:
                                self.update_signal.emit("体力不足")
                                pyautogui.press("esc", interval=1, presses=2)
                                return
                        if click("res/img/battle_star.png"):
                            self.update_signal.emit("开始战斗")
                            self.update_signal.emit("请检查自动战斗和倍速是否开启")
                            times = 0
                            while times != 10:
                                if exist("res/img/q.png", interval=1):
                                    pyautogui.press("v")
                                    break
                                else:
                                    times += 1
                            while battle_time > 1:
                                self.update_signal.emit("剩余次数" + str(battle_time))
                                if self.wait_battle_end():
                                    if click("res/img/again.png"):
                                        if exist("res/img/replenish.png"):
                                            if (
                                                    self.replenish_flag
                                                    and self.replenish_time
                                            ):
                                                self.replenish(self.replenish_way)
                                                click("res/img/again.png")
                                            else:
                                                self.update_signal.emit("体力不足")
                                                pyautogui.press("esc")
                                                if click("res/img/quit_battle.png"):
                                                    self.update_signal.emit("退出战斗")
                                                else:
                                                    self.update_signal.emit(
                                                        "发生错误，错误编号12"
                                                    )
                                                break
                                        battle_time -= 1
                                        time.sleep(3)
                                    else:
                                        self.update_signal.emit("发生错误，错误编号5")
                            else:
                                if self.wait_battle_end():
                                    if click("res/img/quit_battle.png"):
                                        self.update_signal.emit("退出战斗")
                                    else:
                                        self.update_signal.emit("发生错误，错误编号12")
                        else:
                            self.update_signal.emit("发生错误，错误编号4")
                    else:
                        self.update_signal.emit("发生错误，错误编号3")
            else:
                self.update_signal.emit("发生错误，错误编号2")
        else:
            self.update_signal.emit("发生错误，错误编号1")
        self.update_signal.emit("任务完成：拟造花萼（赤）\n")
        time.sleep(3)

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
        self.update_signal.emit("执行任务：凝滞虚影")
        level = "res/img/stagnant_shadow (" + str(level_index) + ").png"
        pyautogui.press("f4")
        time.sleep(3)
        if click("res/img/survival_index.png") or exist(
                "res/img/survival_index_onclick.png"
        ):
            if click("res/img/stagnant_shadow.png") or exist(
                    "res/img/stagnant_shadow_onclick.png"
            ):
                find_level(level)
                if click(level, x_add=400):
                    time.sleep(5)  # 等待传送
                    if click("res/img/battle.png"):
                        if exist("res/img/replenish.png"):
                            if self.replenish_flag:
                                self.replenish(self.replenish_way)
                                click("res/img/battle.png")
                            else:
                                self.update_signal.emit("体力不足")
                                pyautogui.press("esc", interval=1, presses=2)
                                return
                        if click("res/img/battle_star.png"):
                            time.sleep(3)
                            pyautogui.keyDown("w")
                            time.sleep(2)
                            pyautogui.keyUp("w")
                            pyautogui.click()
                            self.update_signal.emit("开始战斗")
                            self.update_signal.emit("请检查自动战斗和倍速是否开启")
                            times = 0
                            while times != 10:
                                if exist("res/img/q.png", interval=1):
                                    pyautogui.press("v")
                                    break
                                else:
                                    times += 1
                            while battle_time > 1:
                                self.update_signal.emit("剩余次数" + str(battle_time))
                                if self.wait_battle_end():
                                    if click("res/img/again.png"):
                                        if exist("res/img/replenish.png"):
                                            if (
                                                    self.replenish_flag
                                                    and self.replenish_time
                                            ):
                                                self.replenish(self.replenish_way)
                                                click("res/img/again.png")
                                            else:
                                                self.update_signal.emit("体力不足")
                                                pyautogui.press("esc")
                                                if click("res/img/quit_battle.png"):
                                                    self.update_signal.emit("退出战斗")
                                                else:
                                                    self.update_signal.emit(
                                                        "发生错误，错误编号12"
                                                    )
                                                break
                                        battle_time -= 1
                                        time.sleep(3)
                                    else:
                                        self.update_signal.emit("发生错误，错误编号5")
                            else:
                                if self.wait_battle_end():
                                    if click("res/img/quit_battle.png"):
                                        self.update_signal.emit("退出战斗")
                                    else:
                                        self.update_signal.emit("发生错误，错误编号12")
                        else:
                            self.update_signal.emit("发生错误，错误编号4")
                    else:
                        self.update_signal.emit("发生错误，错误编号3")
            else:
                self.update_signal.emit("发生错误，错误编号2")
        else:
            self.update_signal.emit("发生错误，错误编号1")
        self.update_signal.emit("任务完成：凝滞虚影\n")
        time.sleep(3)

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
        self.update_signal.emit("执行任务：侵蚀隧洞")
        level = "res/img/caver_of_corrosion (" + str(level_index) + ").png"
        pyautogui.press("f4")
        time.sleep(3)
        if click("res/img/survival_index.png") or click(
                "res/img/survival_index_onclick.png"
        ):
            pyautogui.moveRel(0, 100)
            for i in range(6):
                pyautogui.scroll(-1)
                time.sleep(1)
            if click("res/img/caver_of_corrosion.png") or exist(
                    "res/img/caver_of_corrosion_onclick.png"
            ):
                find_level(level)
                if click(level, x_add=400):
                    time.sleep(5)  # 等待传送
                    if click("res/img/battle.png"):
                        if exist("res/img/replenish.png"):
                            if self.replenish_flag:
                                self.replenish(self.replenish_way)
                                click("res/img/battle.png")
                            else:
                                self.update_signal.emit("体力不足")
                                pyautogui.press("esc", interval=1, presses=2)
                                return
                        if click("res/img/battle_star.png"):
                            self.update_signal.emit("开始战斗")
                            self.update_signal.emit("请检查自动战斗和倍速是否开启")
                            times = 0
                            while times != 10:
                                if exist("res/img/q.png", interval=1):
                                    pyautogui.press("v")
                                    break
                                else:
                                    times += 1
                            while battle_time > 1:
                                self.update_signal.emit("剩余次数" + str(battle_time))
                                if self.wait_battle_end():
                                    if click("res/img/again.png"):
                                        if exist("res/img/replenish.png"):
                                            if (
                                                    self.replenish_flag
                                                    and self.replenish_time
                                            ):
                                                self.replenish(self.replenish_way)
                                                click("res/img/again.png")
                                            else:
                                                self.update_signal.emit("体力不足")
                                                pyautogui.press("esc")
                                                if click("res/img/quit_battle.png"):
                                                    self.update_signal.emit("退出战斗")
                                                else:
                                                    self.update_signal.emit(
                                                        "发生错误，错误编号12"
                                                    )
                                                break
                                        battle_time -= 1
                                        time.sleep(3)
                                    else:
                                        self.update_signal.emit("发生错误，错误编号5")
                            else:
                                if self.wait_battle_end():
                                    if click("res/img/quit_battle.png"):
                                        self.update_signal.emit("退出战斗")
                                    else:
                                        self.update_signal.emit("发生错误，错误编号12")
                        else:
                            self.update_signal.emit("发生错误，错误编号4")
                    else:
                        self.update_signal.emit("发生错误，错误编号3")
            else:
                self.update_signal.emit("发生错误，错误编号2")
        else:
            self.update_signal.emit("发生错误，错误编号1")
        self.update_signal.emit("任务完成：侵蚀隧洞\n")
        time.sleep(3)

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
        self.update_signal.emit("执行任务：历战余响")
        level = "res/img/echo_of_war (" + str(level_index) + ").png"
        pyautogui.press("f4")
        time.sleep(3)
        if click("res/img/survival_index.png") or click(
                "res/img/survival_index_onclick.png"
        ):
            pyautogui.moveRel(0, 100)
            for i in range(6):
                pyautogui.scroll(-1)
                time.sleep(1)
            if click("res/img/echo_of_war.png") or exist(
                    "res/img/echo_of_war_onclick.png"
            ):
                find_level(level)
                if click(level, x_add=400):
                    time.sleep(5)  # 等待传送
                    if click("res/img/battle.png"):
                        if exist("res/img/replenish.png"):
                            if self.replenish_flag:
                                self.replenish(self.replenish_way)
                                click("res/img/battle.png")
                            else:
                                self.update_signal.emit("体力不足")
                                pyautogui.press("esc", interval=1, presses=2)
                                return
                        if click("res/img/battle_star.png"):
                            self.update_signal.emit("开始战斗")
                            self.update_signal.emit("请检查自动战斗和倍速是否开启")
                            times = 0
                            while times != 10:
                                if exist("res/img/q.png", interval=1):
                                    pyautogui.press("v")
                                    break
                                else:
                                    times += 1
                            while battle_time > 1:
                                self.update_signal.emit("剩余次数" + str(battle_time))
                                if self.wait_battle_end():
                                    if click("res/img/again.png"):
                                        if exist("res/img/replenish.png"):
                                            if (
                                                    self.replenish_flag
                                                    and self.replenish_time
                                            ):
                                                self.replenish(self.replenish_way)
                                                click("res/img/again.png")
                                            else:
                                                self.update_signal.emit("体力不足")
                                                pyautogui.press("esc")
                                                if click("res/img/quit_battle.png"):
                                                    self.update_signal.emit("退出战斗")
                                                else:
                                                    self.update_signal.emit(
                                                        "发生错误，错误编号12"
                                                    )
                                                break
                                        battle_time -= 1
                                        time.sleep(3)
                                    else:
                                        self.update_signal.emit("发生错误，错误编号5")
                            else:
                                if self.wait_battle_end():
                                    if click("res/img/quit_battle.png"):
                                        self.update_signal.emit("退出战斗")
                                    else:
                                        self.update_signal.emit("发生错误，错误编号12")
                        else:
                            self.update_signal.emit("发生错误，错误编号4")
                    else:
                        self.update_signal.emit("发生错误，错误编号3")
            else:
                self.update_signal.emit("发生错误，错误编号2")
        else:
            self.update_signal.emit("发生错误，错误编号1")
        self.update_signal.emit("任务完成：历战余响\n")
        time.sleep(3)

    def wait_battle_end(self):
        """Wait battle end

        Returns:
            True if battle end.
        """
        self.update_signal.emit("等待战斗结束")
        quit_battle = cv2.imread("res/img/quit_battle.png")
        while True:
            time.sleep(0.2)
            try:
                pyautogui.locateOnWindow(quit_battle, "崩坏：星穹铁道", confidence=0.9)
                self.update_signal.emit("战斗结束")
                return True
            except pyautogui.ImageNotFoundException:
                continue
            except pyscreeze.PyScreezeException:
                continue

    def assignments_reward(self):
        """Receive assignment reward"""
        self.update_signal.emit("执行任务：领取派遣奖励")
        time.sleep(2)
        pyautogui.press("esc")
        if click("res/img/assignments_none.png"):
            while not exist('res/img/assignment_page.png'):
                pass
            if click("res/img/assignments_reward.png"):
                if click("res/img/assign_again.png"):
                    self.update_signal.emit("再次派遣")
                    time.sleep(2)
                    pyautogui.press("esc")
                    time.sleep(2)
                    pyautogui.press("esc")
                else:
                    self.update_signal.emit("发生错误，错误编号6")
            else:
                self.update_signal.emit("没有可以领取的派遣奖励")
                pyautogui.press("esc")
                time.sleep(2)
                pyautogui.press("esc")
        else:
            self.update_signal.emit("没有可领取的奖励")
            pyautogui.press("esc")
        self.update_signal.emit("任务完成：领取派遣奖励\n")
        time.sleep(3)

    def daily_training_reward(self):
        """Receive daily training reward"""
        self.update_signal.emit("执行任务：领取每日实训奖励")
        time.sleep(2)
        pyautogui.press("f4")
        if exist("res/img/survival_index_onclick.png"):
            self.update_signal.emit("没有可领取的奖励")
            pyautogui.press("esc")
        else:
            while True:
                if click("res/img/daily_reward.png"):
                    pyautogui.moveRel(0, -60)
                else:
                    break
            if click("res/img/daily_train_reward.png"):
                time.sleep(2)
                pyautogui.press("esc")
                time.sleep(2)
                pyautogui.press("esc")
            else:
                self.update_signal.emit("没有可领取的奖励")
                pyautogui.press("esc")
        self.update_signal.emit("任务完成：领取每日实训奖励\n")
        time.sleep(3)

    def nameless_honor(self):
        """Receive nameless honor reward"""
        self.update_signal.emit("执行任务：领取无名勋礼奖励")
        time.sleep(2)
        pyautogui.press("f2")
        if exist("res/img/nameless_honor_reward_exist.png"):
            if click("res/img/nameless_honor_reward_receive.png"):
                self.update_signal.emit("领取了无名勋礼奖励")
                time.sleep(2)
                pyautogui.press("esc")
            else:
                self.update_signal.emit("发生错误，错误编号7")
        if click("res/img/nameless_honor_task.png"):
            if click("res/img/nameless_honor_task_receive.png"):
                self.update_signal.emit("成功领取无名勋礼任务奖励")
                time.sleep(1)
                pyautogui.press("esc")
                if click("res/img/nameless_honor_reward.png"):
                    if click("res/img/nameless_honor_reward_receive.png"):
                        self.update_signal.emit("领取了无名勋礼奖励")
                        time.sleep(2)
                        pyautogui.press("esc")
                        time.sleep(2)
                        pyautogui.press("esc")
                    else:
                        self.update_signal.emit("没有可领取的奖励")
                else:
                    self.update_signal.emit("没有可领取的奖励")
            else:
                self.update_signal.emit("没有已完成的无名勋礼任务")
                pyautogui.press("esc")
        else:
            self.update_signal.emit("没有可领取的奖励")
            pyautogui.press("esc")
        self.update_signal.emit("完成任务：领取无名勋礼奖励\n")
        time.sleep(3)

    def replenish(self, way):
        """Replenish trailblaze power

        Note:
            Do not include the `self` parameter in the ``Args`` section.

            ``way``:
             ``1``--replenishes by reserved trailblaze power.\n
             ``2``--replenishes by fuel.\n
             ``3``--replenishes by stellar jade.
        Args:
            way (int): Index of way in /res/img.
        Returns:
            True if replenished successfully, False otherwise.
        """
        if self.replenish_time != 0:
            if way == 1 or way == 0:
                if exist("res/img/reserved_trailblaze_power_onclick.png") or click(
                        "res/img/reserved_trailblaze_power.png"
                ):
                    click("res/img/ensure.png")
                    click("res/img/ensure.png")
                    time.sleep(1)
                    pyautogui.click()
                else:
                    self.update_signal.emit("发生错误，错误编号13")
                    return False
            elif way == 2:
                if click("res/img/fuel.png"):
                    click("res/img/ensure.png")
                    click("res/img/ensure.png")
                    time.sleep(1)
                    pyautogui.click()
                else:
                    self.update_signal.emit("发生错误，错误编号14，可能没有燃料")
                    return False
            elif way == 3:
                if click("res/img/stellar_jade.png"):
                    click("res/img/ensure.png")
                    click("res/img/ensure.png")
                    time.sleep(1)
                    pyautogui.click()
                else:
                    self.update_signal.emit("发生错误，错误编号15")
                    return False
            self.replenish_time -= 1
            return True
        else:
            return False


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


def exist(img_path, interval=2):
    """Determine if a situation exists.

    Args:
        img_path (str): Img path of the situation.
        interval (int): Waiting time before run.
    Returns:
        True if existed, False otherwise.
    """
    time.sleep(interval)  # 等待游戏加载
    try:
        img = cv2.imread(img_path)
        if img is None:
            raise FileNotFoundError("无法找到或读取文件 " + img_path + ".png")
        pyautogui.locateOnWindow(img, "崩坏：星穹铁道", confidence=0.95)
        # print('test:' + img_path, 'exist')
        return True
    except pyautogui.ImageNotFoundException:
        # print('test:' + img_path, 'not exist')
        return False
    except FileNotFoundError as e:
        with open("data/log.txt", "a", encoding="utf-8") as log:
            log.write(f"FileNotFoundError: {e}\n")
        return False


def find_window(title):
    """Find window handles based on the window title

    Args:
        title (str): Window title.
    Returns:
        list if found, None otherwise.
    """

    def enum_callback(hwnd, result):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) == title:
            result.append(hwnd)

    windows = []
    win32gui.EnumWindows(enum_callback, windows)
    return windows[0] if windows else None


def click(img_path, x_add=0, y_add=0, interval=2.0):
    """Click the corresponding image on the screen

    Args:
        img_path (str): Img path.
        x_add (int): X-axis offset(px).
        y_add (int): Y-axis offset(px).
        interval (float): Waiting time before run(s).
    Returns:
        True if clicked successfully, False otherwise.
    """
    try:
        time.sleep(interval)
        img = cv2.imread(img_path)
        if img is None:
            raise FileNotFoundError("无法找到或读取文件 " + img_path)
        location = pyautogui.locateOnWindow(img, "崩坏：星穹铁道", confidence=0.95)
        x, y = pyautogui.center(location)
        x += x_add
        y += y_add
        pyautogui.click(x, y)
        return True
    except pyautogui.ImageNotFoundException:
        with open("data/log.txt", "a", encoding="utf-8") as log:
            log.write(f"ImageNotFoundException: {img_path}\n")
        return False
    except ValueError as e:
        with open("data/log.txt", "a", encoding="utf-8") as log:
            log.write(f"ValueError: {e}\n")
        return False
    except FileNotFoundError as e:
        with open("data/log.txt", "a", encoding="utf-8") as log:
            log.write(f"FileNotFoundError: {e}\n")
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
        if exist(level, interval=1):
            return True
        else:
            pyautogui.scroll(-1)


if __name__ == "__main__":
    click("res/img/echo_of_war (0).png")
