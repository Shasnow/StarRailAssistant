"""
崩坏：星穹铁道助手
beta v0.6
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
        with open('config.json', 'r', encoding='utf-8') as file:
            config = json.load(file)
        if not self.stop_flag:
            if config['starGame']:
                self.star_game(config['gamePath'], config['loginFlag'], config['account'], config['password'])
        if not self.check_game():
            self.finished.emit()
            return
        if not self.stop_flag:
            if config['trailBlazerProfile']:
                self.trailblazer_profile()
        if not self.stop_flag:
            if config['redeemCode']:
                self.redeem_code(config['redeemCodeList'])
        if not self.stop_flag:
            if config['assignment']:
                self.assignments_reward()
        if not self.stop_flag:
            if config['giftOfOdyssey']:
                self.gift_of_odyssey()
        if not self.stop_flag:
            if config['mail']:
                self.mail()
        if not self.stop_flag:
            if config['trailBlazePower']:
                self.replenish_flag = config['replenish_trail_blaze_power']
                self.replenish_way = config['replenish_way']
                self.replenish_time = config['replenish_trail_blaze_power_run_time']
                if not self.stop_flag:
                    if config['ornament_extraction']:
                        self.ornament_extraction(config['ornament_extraction_level'],
                                                 config['ornament_extraction_run_time'])
                if not self.stop_flag:
                    if config['calyx_golden']:
                        self.calyx_golden(config['calyx_golden_level'], config['calyx_golden_battle_time'],
                                          config['calyx_golden_run_time'])
                if not self.stop_flag:
                    if config['calyx_crimson']:
                        self.calyx_crimson(config['calyx_crimson_level'], config['calyx_crimson_battle_time'],
                                           config['calyx_crimson_run_time'])
                if not self.stop_flag:
                    if config['stagnant_shadow']:
                        self.stagnant_shadow(config['stagnant_shadow_level'], config['stagnant_shadow_run_time'])
                if not self.stop_flag:
                    if config['caver_of_corrosion']:
                        self.caver_of_corrosion(config['caver_of_corrosion_level'],
                                                config['caver_of_corrosion_run_time'])
                if not self.stop_flag:
                    if config['echo_of_war']:
                        self.echo_of_war(config['echo_of_war_level'], config['echo_of_war_run_time'])
        if not self.stop_flag:
            if config['dailyTraining']:
                self.daily_training_reward()
        if not self.stop_flag:
            if config['namelessHonor']:
                self.nameless_honor()
        if not self.stop_flag:
            if config['quitGame']:
                self.kill_game()
        if self.stop_flag:
            self.update_signal.emit('已停止')
            self.finished.emit()
        else:
            self.update_signal.emit('任务全部完成\n')
            self.finished.emit()

    def check_game(self):
        #  激活游戏窗口
        window_title = "崩坏：星穹铁道"
        hwnd = find_window(window_title)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)  # 确保窗口不是最小化状态
            win32gui.SetForegroundWindow(hwnd)
            return True
        else:
            self.update_signal.emit("未找到窗口:" + window_title + '或许你还没有运行游戏')
            return False

    def path_check(self, path):
        if path:
            if path.split('/')[-1].split('.')[0] != 'StarRail':
                self.update_signal.emit('你尝试输入一个其他应用的路径')
                return False
            else:
                return True
        else:
            self.update_signal.emit('游戏路径为空')
            return False

    def kill_game(self):
        command = f"taskkill /F /IM StarRail.exe"
        # 执行命令
        subprocess.run(command, shell=True, check=True)
        self.update_signal.emit('退出游戏')

    def launch_game(self, game_path):
        # 启动游戏
        if self.path_check(game_path):
            try:
                subprocess.Popen(game_path)
            except OSError:
                self.update_signal.emit('路径无效或权限不足')
                return
            self.update_signal.emit('等待游戏启动')
            time.sleep(5)
            times = 0
            while True:
                if find_window('崩坏：星穹铁道'):
                    self.update_signal.emit('启动成功')
                    return True
                else:
                    time.sleep(0.5)
                    times += 1
                    if times == 40:
                        self.update_signal.emit('启动时间过长，请尝试手动启动')
                        return False
        else:
            self.update_signal.emit('路径无效')

    def login(self, account, password):
        if not check('img/welcome.png', interrupt=0.1, max_time=10):  # 进入登录界面的标志
            if check('img/not_logged_in.png', max_time=4):
                if click('img/login_with_account.png'):
                    self.update_signal.emit('登录到' + account)
                    time.sleep(1)
                    pyautogui.write(account)
                    time.sleep(1)
                    pyautogui.press('tab')
                    time.sleep(0.1)
                    pyautogui.write(password)
                    pyautogui.press('enter')
                    click('img/agree.png', -158)
                    if click('img/enter_game.png'):
                        times = 0
                        while True:
                            time.sleep(0.2)
                            times += 1
                            if times == 10:
                                self.update_signal.emit('长时间未成功登录，可能密码错误或需要新设备验证')
                                break
                            else:
                                if exist('img/welcome.png'):
                                    self.update_signal.emit('登录成功')
                                    break
                    else:
                        self.update_signal.emit('发生错误，错误编号9')
                else:
                    self.update_signal.emit('发生错误，错误编号10')
            else:
                self.update_signal.emit('发生错误，错误编号11')
        else:
            self.update_signal.emit('已登录')

    def star_game(self, game_path, login_flag=False, account='', password=''):
        if find_window('崩坏：星穹铁道'):
            self.update_signal.emit('游戏已经启动')
            return True
        if self.launch_game(game_path):
            time.sleep(2)
            if login_flag and account:
                self.login(account, password)
            if check('img/quit.png'):
                x, y = get_screen_center()
                if exist('img/12+.png'):
                    pyautogui.click(x, y)
                    time.sleep(3)
                self.update_signal.emit('开始游戏')
                pyautogui.click(x, y)
                time.sleep(3)
                pyautogui.click(x, y)
                times = 0
                while True:
                    time.sleep(0.2)
                    if exist('img/chat_enter.png'):
                        return True
                    else:
                        times += 1
                        if times == 50:
                            self.update_signal.emit('发生错误，进入游戏但未处于大世界')
                            return False
            else:
                self.update_signal.emit('加载时间过长，请重试')
                return False
        else:
            self.update_signal.emit('游戏启动失败')
            return False

    def trailblazer_profile(self):
        self.update_signal.emit('执行任务：签证奖励')
        time.sleep(2)
        pyautogui.press('esc')
        if click('img/more_with_something.png'):
            pyautogui.moveRel(20, 0)
            if click('img/trailblazer_profile_finished.png'):
                if click('img/assistance_reward.png'):
                    time.sleep(2)
                    pyautogui.press('esc', presses=3, interval=2)
                else:
                    self.update_signal.emit('没有可领取的奖励1')
                    pyautogui.press('esc', presses=2, interval=2)
            else:
                self.update_signal.emit('没有可领取的奖励2')
                pyautogui.press('esc')
        else:
            self.update_signal.emit('没有可领取的奖励3')
            pyautogui.press('esc')
        self.update_signal.emit('任务完成：签证奖励\n')
        time.sleep(3)

    def redeem_code(self, redeem_code_list):
        self.update_signal.emit('执行任务：领取兑换码')
        time.sleep(2)
        pyautogui.press('esc')
        for code in redeem_code_list:
            if click('img/more.png') or click('img/more_with_something.png'):
                if click('img/redeem_code.png'):
                    time.sleep(2)
                    pyautogui.click(get_screen_center())
                    pyautogui.write(code)
                    click('img/ensure.png')
                    time.sleep(2)
                    pyautogui.press('esc')
                else:
                    self.update_signal.emit('发生错误，错误编号16')
            else:
                self.update_signal.emit('发生错误，错误编号17')
        time.sleep(2)
        pyautogui.press('esc')
        self.update_signal.emit('任务完成：领取兑换码\n')

    def mail(self):
        self.update_signal.emit('执行任务：领取邮件')
        time.sleep(2)
        pyautogui.press('esc')
        if click('img/mailbox_mail.png'):
            if click('img/claim_all_mail.png'):
                time.sleep(2)
                pyautogui.press('esc')
                time.sleep(2)
                pyautogui.press('esc')
                time.sleep(2)
                pyautogui.press('esc')
            else:
                self.update_signal.emit('没有可以领取的邮件')
                pyautogui.press('esc')
        else:
            self.update_signal.emit('没有可以领取的邮件')
            pyautogui.press('esc')
        self.update_signal.emit('任务完成：领取邮件\n')
        time.sleep(3)

    def gift_of_odyssey(self):
        self.update_signal.emit('执行任务：巡星之礼')
        time.sleep(2)
        pyautogui.press('f1')
        if click('img/gift_of_odyssey.png'):
            pass
        if click('img/gift_receive.png'):
            self.update_signal.emit('领取成功')
            time.sleep(2)
            pyautogui.press('esc')
            time.sleep(2)
            pyautogui.press('esc')
        else:
            self.update_signal.emit('没有可以领取的巡星之礼')
            pyautogui.press('esc')
        self.update_signal.emit('任务完成：巡星之礼\n')
        time.sleep(3)

    def ornament_extraction(self, level_index, battle_time=1):
        self.update_signal.emit('执行任务：饰品提取')
        level = 'img/ornament_extraction (' + str(level_index) + ').png'
        pyautogui.press('f4')
        time.sleep(3)
        if click('img/survival_index.png') or exist('img/survival_index_onclick.png'):
            if click('img/ornament_extraction.png') or exist('img/ornament_extraction_onclick.png'):
                if exist('img/no_save.png'):
                    self.update_signal.emit('当前暂无可用存档，请前往[差分宇宙]获取存档')
                    pyautogui.press('esc')
                    time.sleep(1)
                    return
                find_level(level)
                if click(level, x_add=400):
                    time.sleep(5)  # 等待传送
                    if click('img/nobody.png'):
                        click('img/preset_formation.png')
                        click('img/team1.png')
                    if click('img/battle_star.png'):
                        if exist('img/replenish.png'):
                            if self.replenish_flag:
                                self.replenish(self.replenish_way)
                                click('img/battle_star.png')
                            else:
                                self.update_signal.emit('体力不足')
                                pyautogui.press('esc', interval=1, presses=2)
                                return
                        while not exist('img/f3.png'):
                            pass
                        pyautogui.keyDown('w')
                        time.sleep(3)
                        pyautogui.keyUp('w')
                        pyautogui.click()
                        self.update_signal.emit('开始战斗')
                        self.update_signal.emit('请检查自动战斗和倍速是否开启')
                        times = 0
                        while times != 10:
                            if exist('img/q.png', interrupt=1):
                                pyautogui.press('v')
                                break
                            else:
                                times += 1
                        while battle_time > 1:
                            self.update_signal.emit('剩余次数' + str(battle_time))
                            if self.wait_battle_end():
                                if click('img/again.png'):
                                    if exist('img/replenish.png'):
                                        if self.replenish_flag and self.replenish_time:
                                            self.replenish(self.replenish_way)
                                            click('img/again.png')
                                        else:
                                            self.update_signal.emit('体力不足')
                                            pyautogui.press('esc')
                                            if click('img/quit_battle.png'):
                                                self.update_signal.emit('退出战斗')
                                            else:
                                                self.update_signal.emit('发生错误，错误编号12')
                                            break
                                    battle_time -= 1
                                    time.sleep(3)
                                else:
                                    self.update_signal.emit('发生错误，错误编号5')
                        else:
                            if self.wait_battle_end():
                                if click('img/quit_battle.png'):
                                    self.update_signal.emit('退出战斗')
                                else:
                                    self.update_signal.emit('发生错误，错误编号12')
                    else:
                        self.update_signal.emit('发生错误，错误编号3')
            else:
                self.update_signal.emit('发生错误，错误编号2')
        else:
            self.update_signal.emit('发生错误，错误编号1')
        self.update_signal.emit('任务完成：饰品提取\n')
        time.sleep(5)

    def calyx_golden(self, level_index, single_time=1, battle_time=1):
        self.update_signal.emit('执行任务：拟造花萼（金）')
        level = 'img/calyx(golden) (' + str(level_index) + ').png'
        pyautogui.press('f4')
        time.sleep(3)
        if click('img/survival_index.png') or exist('img/survival_index_onclick.png'):
            if click('img/calyx(golden).png') or exist('img/calyx(golden)_onclick.png'):
                find_level(level)
                if click(level, x_add=600, y_add=10):
                    time.sleep(5)  # 等待传送
                    for i in range(single_time - 1):
                        click('img/plus.png', interrupt=0.5)
                    time.sleep(2)
                    if click('img/battle.png'):
                        if exist('img/replenish.png'):
                            if self.replenish_flag:
                                self.replenish(self.replenish_way)
                                click('img/battle.png')
                            else:
                                self.update_signal.emit('体力不足')
                                pyautogui.press('esc', interval=1, presses=2)
                                return
                        if click('img/battle_star.png'):
                            self.update_signal.emit('开始战斗')
                            self.update_signal.emit('请检查自动战斗和倍速是否开启')
                            times = 0
                            while times != 10:
                                if exist('img/q.png', interrupt=1):
                                    pyautogui.press('v')
                                    break
                                else:
                                    times += 1
                            while battle_time > 1:
                                self.update_signal.emit('剩余次数' + str(battle_time - 1))
                                if self.wait_battle_end():
                                    if click('img/again.png'):
                                        if exist('img/replenish.png'):
                                            if self.replenish_flag and self.replenish_time:
                                                self.replenish(self.replenish_way)
                                                click('img/again.png')
                                            else:
                                                self.update_signal.emit('体力不足')
                                                pyautogui.press('esc')
                                                if click('img/quit_battle.png'):
                                                    self.update_signal.emit('退出战斗')
                                                else:
                                                    self.update_signal.emit('发生错误，错误编号12')
                                                break
                                        battle_time -= 1
                                        time.sleep(3)
                                    else:
                                        self.update_signal.emit('发生错误，错误编号5')
                            else:
                                if self.wait_battle_end():
                                    if click('img/quit_battle.png'):
                                        self.update_signal.emit('退出战斗')
                                    else:
                                        self.update_signal.emit('发生错误，错误编号12')
                        else:
                            self.update_signal.emit('发生错误，错误编号4')
                    else:
                        self.update_signal.emit('发生错误，错误编号3')
            else:
                self.update_signal.emit('发生错误，错误编号2')
        else:
            self.update_signal.emit('发生错误，错误编号1')
        self.update_signal.emit('任务完成：拟造花萼（金）\n')
        time.sleep(3)

    def calyx_crimson(self, level_index, single_time=1, battle_time=1):
        self.update_signal.emit('执行任务：拟造花萼（赤）')
        level = 'img/calyx(crimson) (' + str(level_index) + ').png'
        pyautogui.press('f4')
        time.sleep(3)
        if click('img/survival_index.png') or exist('img/survival_index_onclick.png'):
            if click('img/calyx(crimson).png') or exist('img/calyx(crimson)_onclick.png'):
                find_level(level)
                if click(level, x_add=400):
                    time.sleep(5)  # 等待传送
                    for i in range(single_time - 1):
                        click('img/plus.png', interrupt=0.5)
                    time.sleep(2)
                    if click('img/battle.png'):
                        if exist('img/replenish.png'):
                            if self.replenish_flag:
                                self.replenish(self.replenish_way)
                                click('img/battle.png')
                            else:
                                self.update_signal.emit('体力不足')
                                pyautogui.press('esc', interval=1, presses=2)
                                return
                        if click('img/battle_star.png'):
                            self.update_signal.emit('开始战斗')
                            self.update_signal.emit('请检查自动战斗和倍速是否开启')
                            times = 0
                            while times != 10:
                                if exist('img/q.png', interrupt=1):
                                    pyautogui.press('v')
                                    break
                                else:
                                    times += 1
                            while battle_time > 1:
                                self.update_signal.emit('剩余次数' + str(battle_time))
                                if self.wait_battle_end():
                                    if click('img/again.png'):
                                        if exist('img/replenish.png'):
                                            if self.replenish_flag and self.replenish_time:
                                                self.replenish(self.replenish_way)
                                                click('img/again.png')
                                            else:
                                                self.update_signal.emit('体力不足')
                                                pyautogui.press('esc')
                                                if click('img/quit_battle.png'):
                                                    self.update_signal.emit('退出战斗')
                                                else:
                                                    self.update_signal.emit('发生错误，错误编号12')
                                                break
                                        battle_time -= 1
                                        time.sleep(3)
                                    else:
                                        self.update_signal.emit('发生错误，错误编号5')
                            else:
                                if self.wait_battle_end():
                                    if click('img/quit_battle.png'):
                                        self.update_signal.emit('退出战斗')
                                    else:
                                        self.update_signal.emit('发生错误，错误编号12')
                        else:
                            self.update_signal.emit('发生错误，错误编号4')
                    else:
                        self.update_signal.emit('发生错误，错误编号3')
            else:
                self.update_signal.emit('发生错误，错误编号2')
        else:
            self.update_signal.emit('发生错误，错误编号1')
        self.update_signal.emit('任务完成：拟造花萼（赤）\n')
        time.sleep(3)

    def stagnant_shadow(self, level_index, battle_time=1):
        self.update_signal.emit('执行任务：凝滞虚影')
        level = 'img/stagnant_shadow (' + str(level_index) + ').png'
        pyautogui.press('f4')
        time.sleep(3)
        if click('img/survival_index.png') or exist('img/survival_index_onclick.png'):
            if click('img/stagnant_shadow.png') or exist('img/stagnant_shadow_onclick.png'):
                find_level(level)
                if click(level, x_add=400):
                    time.sleep(5)  # 等待传送
                    if click('img/battle.png'):
                        if exist('img/replenish.png'):
                            if self.replenish_flag:
                                self.replenish(self.replenish_way)
                                click('img/battle.png')
                            else:
                                self.update_signal.emit('体力不足')
                                pyautogui.press('esc', interval=1, presses=2)
                                return
                        if click('img/battle_star.png'):
                            time.sleep(3)
                            pyautogui.keyDown('w')
                            time.sleep(2)
                            pyautogui.keyUp('w')
                            pyautogui.click()
                            self.update_signal.emit('开始战斗')
                            self.update_signal.emit('请检查自动战斗和倍速是否开启')
                            times = 0
                            while times != 10:
                                if exist('img/q.png', interrupt=1):
                                    pyautogui.press('v')
                                    break
                                else:
                                    times += 1
                            while battle_time > 1:
                                self.update_signal.emit('剩余次数' + str(battle_time))
                                if self.wait_battle_end():
                                    if click('img/again.png'):
                                        if exist('img/replenish.png'):
                                            if self.replenish_flag and self.replenish_time:
                                                self.replenish(self.replenish_way)
                                                click('img/again.png')
                                            else:
                                                self.update_signal.emit('体力不足')
                                                pyautogui.press('esc')
                                                if click('img/quit_battle.png'):
                                                    self.update_signal.emit('退出战斗')
                                                else:
                                                    self.update_signal.emit('发生错误，错误编号12')
                                                break
                                        battle_time -= 1
                                        time.sleep(3)
                                    else:
                                        self.update_signal.emit('发生错误，错误编号5')
                            else:
                                if self.wait_battle_end():
                                    if click('img/quit_battle.png'):
                                        self.update_signal.emit('退出战斗')
                                    else:
                                        self.update_signal.emit('发生错误，错误编号12')
                        else:
                            self.update_signal.emit('发生错误，错误编号4')
                    else:
                        self.update_signal.emit('发生错误，错误编号3')
            else:
                self.update_signal.emit('发生错误，错误编号2')
        else:
            self.update_signal.emit('发生错误，错误编号1')
        self.update_signal.emit('任务完成：凝滞虚影\n')
        time.sleep(3)

    def caver_of_corrosion(self, level_index, battle_time=1):
        self.update_signal.emit('执行任务：侵蚀隧洞')
        level = 'img/caver_of_corrosion (' + str(level_index) + ').png'
        pyautogui.press('f4')
        time.sleep(3)
        if click('img/survival_index.png') or click('img/survival_index_onclick.png'):
            pyautogui.moveRel(0, 100)
            for i in range(6):
                pyautogui.scroll(-1)
                time.sleep(1)
            if click('img/caver_of_corrosion.png') or exist('img/caver_of_corrosion_onclick.png'):
                find_level(level)
                if click(level, x_add=400):
                    time.sleep(5)  # 等待传送
                    if click('img/battle.png'):
                        if exist('img/replenish.png'):
                            if self.replenish_flag:
                                self.replenish(self.replenish_way)
                                click('img/battle.png')
                            else:
                                self.update_signal.emit('体力不足')
                                pyautogui.press('esc', interval=1, presses=2)
                                return
                        if click('img/battle_star.png'):
                            self.update_signal.emit('开始战斗')
                            self.update_signal.emit('请检查自动战斗和倍速是否开启')
                            times = 0
                            while times != 10:
                                if exist('img/q.png', interrupt=1):
                                    pyautogui.press('v')
                                    break
                                else:
                                    times += 1
                            while battle_time > 1:
                                self.update_signal.emit('剩余次数' + str(battle_time))
                                if self.wait_battle_end():
                                    if click('img/again.png'):
                                        if exist('img/replenish.png'):
                                            if self.replenish_flag and self.replenish_time:
                                                self.replenish(self.replenish_way)
                                                click('img/again.png')
                                            else:
                                                self.update_signal.emit('体力不足')
                                                pyautogui.press('esc')
                                                if click('img/quit_battle.png'):
                                                    self.update_signal.emit('退出战斗')
                                                else:
                                                    self.update_signal.emit('发生错误，错误编号12')
                                                break
                                        battle_time -= 1
                                        time.sleep(3)
                                    else:
                                        self.update_signal.emit('发生错误，错误编号5')
                            else:
                                if self.wait_battle_end():
                                    if click('img/quit_battle.png'):
                                        self.update_signal.emit('退出战斗')
                                    else:
                                        self.update_signal.emit('发生错误，错误编号12')
                        else:
                            self.update_signal.emit('发生错误，错误编号4')
                    else:
                        self.update_signal.emit('发生错误，错误编号3')
            else:
                self.update_signal.emit('发生错误，错误编号2')
        else:
            self.update_signal.emit('发生错误，错误编号1')
        self.update_signal.emit('任务完成：侵蚀隧洞\n')
        time.sleep(3)

    def echo_of_war(self, level_index, battle_time=1):
        self.update_signal.emit('执行任务：历战余响')
        level = 'img/echo_of_war (' + str(level_index) + ').png'
        pyautogui.press('f4')
        time.sleep(3)
        if click('img/survival_index.png') or click('img/survival_index_onclick.png'):
            pyautogui.moveRel(0, 100)
            for i in range(6):
                pyautogui.scroll(-1)
                time.sleep(1)
            if click('img/echo_of_war.png') or exist('img/echo_of_war_onclick.png'):
                find_level(level)
                if click(level, x_add=400):
                    time.sleep(5)  # 等待传送
                    if click('img/battle.png'):
                        if exist('img/replenish.png'):
                            if self.replenish_flag:
                                self.replenish(self.replenish_way)
                                click('img/battle.png')
                            else:
                                self.update_signal.emit('体力不足')
                                pyautogui.press('esc', interval=1, presses=2)
                                return
                        if click('img/battle_star.png'):
                            self.update_signal.emit('开始战斗')
                            self.update_signal.emit('请检查自动战斗和倍速是否开启')
                            times = 0
                            while times != 10:
                                if exist('img/q.png', interrupt=1):
                                    pyautogui.press('v')
                                    break
                                else:
                                    times += 1
                            while battle_time > 1:
                                self.update_signal.emit('剩余次数' + str(battle_time))
                                if self.wait_battle_end():
                                    if click('img/again.png'):
                                        if exist('img/replenish.png'):
                                            if self.replenish_flag and self.replenish_time:
                                                self.replenish(self.replenish_way)
                                                click('img/again.png')
                                            else:
                                                self.update_signal.emit('体力不足')
                                                pyautogui.press('esc')
                                                if click('img/quit_battle.png'):
                                                    self.update_signal.emit('退出战斗')
                                                else:
                                                    self.update_signal.emit('发生错误，错误编号12')
                                                break
                                        battle_time -= 1
                                        time.sleep(3)
                                    else:
                                        self.update_signal.emit('发生错误，错误编号5')
                            else:
                                if self.wait_battle_end():
                                    if click('img/quit_battle.png'):
                                        self.update_signal.emit('退出战斗')
                                    else:
                                        self.update_signal.emit('发生错误，错误编号12')
                        else:
                            self.update_signal.emit('发生错误，错误编号4')
                    else:
                        self.update_signal.emit('发生错误，错误编号3')
            else:
                self.update_signal.emit('发生错误，错误编号2')
        else:
            self.update_signal.emit('发生错误，错误编号1')
        self.update_signal.emit('任务完成：历战余响\n')
        time.sleep(3)

    def wait_battle_end(self):
        self.update_signal.emit('等待战斗结束')
        quit_battle = cv2.imread('img/quit_battle.png')
        while True:
            time.sleep(0.2)
            try:
                pyautogui.locateOnWindow(quit_battle, '崩坏：星穹铁道', confidence=0.9)
                self.update_signal.emit('战斗结束')
                return True
            except pyautogui.ImageNotFoundException:
                continue
            except pyscreeze.PyScreezeException:
                continue

    def assignments_reward(self):
        self.update_signal.emit('执行任务：领取派遣奖励')
        time.sleep(2)
        pyautogui.press('esc')
        if click('img/assignments_none.png'):
            if click('img/assignments_reward.png'):
                if click('img/assign_again.png'):
                    self.update_signal.emit('再次派遣')
                    time.sleep(2)
                    pyautogui.press('esc')
                    time.sleep(2)
                    pyautogui.press('esc')
                else:
                    self.update_signal.emit('发生错误，错误编号6')
            else:
                self.update_signal.emit('没有可以领取的派遣奖励')
                pyautogui.press('esc')
                time.sleep(2)
                pyautogui.press('esc')
        else:
            self.update_signal.emit('没有可领取的奖励')
            pyautogui.press('esc')
        self.update_signal.emit('任务完成：领取派遣奖励\n')
        time.sleep(3)

    def daily_training_reward(self):
        self.update_signal.emit('执行任务：领取每日实训奖励')
        time.sleep(2)
        pyautogui.press('f4')
        if exist('img/survival_index_onclick.png'):
            self.update_signal.emit('没有可领取的奖励')
            pyautogui.press('esc')
        else:
            while True:
                if click('img/daily_reward.png'):
                    pyautogui.moveRel(0, -60)
                else:
                    break
            if click('img/daily_train_reward.png'):
                time.sleep(2)
                pyautogui.press('esc')
                time.sleep(2)
                pyautogui.press('esc')
            else:
                self.update_signal.emit('没有可领取的奖励')
                pyautogui.press('esc')
        self.update_signal.emit('任务完成：领取每日实训奖励\n')
        time.sleep(3)

    def nameless_honor(self):
        self.update_signal.emit('执行任务：领取无名勋礼奖励')
        time.sleep(2)
        pyautogui.press('f2')
        if exist('img/nameless_honor_reward_exist.png'):
            if click('img/nameless_honor_reward_receive.png'):
                self.update_signal.emit('领取了无名勋礼奖励')
                time.sleep(2)
                pyautogui.press('esc')
            else:
                self.update_signal.emit('发生错误，错误编号7')
        if click('img/nameless_honor_task.png'):
            if click('img/nameless_honor_task_receive.png'):
                self.update_signal.emit('成功领取无名勋礼任务奖励')
                time.sleep(1)
                pyautogui.press('esc')
                if click('img/nameless_honor_reward.png'):
                    if click('img/nameless_honor_reward_receive.png'):
                        self.update_signal.emit('领取了无名勋礼奖励')
                        time.sleep(2)
                        pyautogui.press('esc')
                        time.sleep(2)
                        pyautogui.press('esc')
                    else:
                        self.update_signal.emit('没有可领取的奖励')
                else:
                    self.update_signal.emit('没有可领取的奖励')
            else:
                self.update_signal.emit('没有已完成的无名勋礼任务')
                pyautogui.press('esc')
        else:
            self.update_signal.emit('没有可领取的奖励')
            pyautogui.press('esc')
        self.update_signal.emit('完成任务：领取无名勋礼奖励\n')
        time.sleep(3)

    def replenish(self, way):
        if self.replenish_time != 0:
            if way == 1 or way == 0:
                if exist('img/reserved_trailblaze_power_onclick.png') or click('img/reserved_trailblaze_power.png'):
                    click('img/ensure.png')
                    click('img/ensure.png')
                    time.sleep(1)
                    pyautogui.click()
                else:
                    self.update_signal.emit('发生错误，错误编号13')
                    return False
            elif way == 2:
                if click('img/fuel.png'):
                    click('img/ensure.png')
                    click('img/ensure.png')
                    time.sleep(1)
                    pyautogui.click()
                else:
                    self.update_signal.emit('发生错误，错误编号14，可能没有燃料')
                    return False
            elif way == 3:
                if click('img/stellar_jade.png'):
                    click('img/ensure.png')
                    click('img/ensure.png')
                    time.sleep(1)
                    pyautogui.click()
                else:
                    self.update_signal.emit('发生错误，错误编号15')
                    return False
            self.replenish_time -= 1
            return True
        else:
            return False


def check(img_path, interrupt=0.5, max_time=40):
    times = 0
    while True:
        time.sleep(interrupt)
        if exist(img_path):
            return True
        else:
            times += 1
            if times == max_time:
                return False


def exist(img_path, interrupt=2):
    time.sleep(interrupt)  # 等待游戏加载
    try:
        img = cv2.imread(img_path)
        if img is None:
            raise FileNotFoundError("无法找到或读取文件 " + img_path + ".png")
        pyautogui.locateOnWindow(img, '崩坏：星穹铁道', confidence=0.95)
        # print('test:' + img_path, 'exist')
        return True
    except pyautogui.ImageNotFoundException:
        # print('test:' + img_path, 'not exist')
        return False
    except FileNotFoundError as e:
        with open("log.txt", 'a', encoding='utf-8') as log:
            log.write(f'FileNotFoundError: {e}\n')
        return False


def find_window(title):
    """
    根据窗口标题查找窗口句柄
    """

    def enum_callback(hwnd, result):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) == title:
            result.append(hwnd)

    windows = []
    win32gui.EnumWindows(enum_callback, windows)
    return windows[0] if windows else None


def click(img_path, x_add=0, y_add=0, interrupt=2.0):
    try:
        time.sleep(interrupt)
        img = cv2.imread(img_path)
        if img is None:
            raise FileNotFoundError("无法找到或读取文件 " + img_path)
        location = pyautogui.locateOnWindow(img, '崩坏：星穹铁道', confidence=0.95)
        x, y = pyautogui.center(location)
        x += x_add
        y += y_add
        pyautogui.click(x, y)
        return True
    except pyautogui.ImageNotFoundException:
        with open("log.txt", 'a', encoding='utf-8') as log:
            log.write(f'ImageNotFoundException: {img_path}\n')
        return False
    except ValueError as e:
        with open("log.txt", 'a', encoding='utf-8') as log:
            log.write(f'ValueError: {e}\n')
        return False
    except FileNotFoundError as e:
        with open("log.txt", 'a', encoding='utf-8') as log:
            log.write(f'FileNotFoundError: {e}\n')
        return False


def get_screen_center():
    x, y, screen_width, screen_height = (pyautogui.getActiveWindow().left, pyautogui.getActiveWindow().top,
                                         pyautogui.getActiveWindow().width, pyautogui.getActiveWindow().height)
    return x + screen_width // 2, y + screen_height // 2


def find_level(level: str):
    x, y = get_screen_center()
    pyautogui.moveTo(x - 200, y)
    while True:
        if exist(level, interrupt=1):
            return True
        else:
            pyautogui.scroll(-1)


def notice():
    print("beta v0.2 更新公告\n"
          "新功能：\n"
          "1.新增账号登录功能，输入你的账号和密码后（本地），如果启动游戏时未登录，可以自动登录。\n"
          "2.新增领取巡星之礼功能，现在可以帮你领取巡星之礼。\n"
          "3.现在你可以对功能进行一些简单的自定义，选择跳过一些功能\n"
          "问题修复：\n"
          "1.修复了某些情况下任务结束未正确返回大世界，导致下一个任务无法执行的问题。\n"
          "2.修复了若干问题。")
    input('我已阅读')


if __name__ == '__main__':
    click('img/echo_of_war (0).png')
