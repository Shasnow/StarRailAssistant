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
beta v0.6
作者：雪影
图形化
"""

import sys  # 导入 sys 模块，用于与 Python 解释器交互
import json
import time
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QCheckBox,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QFileDialog,
    QFormLayout,
    QTextEdit,
    QAction,
    QMessageBox,
    QComboBox,
    QSpinBox,
)  # 从 PyQt5 中导入所需的类
from plyer import notification
import encryption
import StarRailAssistant
import ctypes

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SRA")  # 修改任务栏图标


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()  # 调用父类 QMainWindow 的初始化方法
        encryption.init()
        with open("data/config.json", "r", encoding="utf-8") as file:
            config = json.load(file)
        with open("data/privacy.sra", "rb") as sra_file:
            privacy = sra_file.readlines()
            try:
                pwd = privacy[1]
                acc = privacy[0]
                self.password_text = encryption.decrypt_word(pwd)
                self.account_text = encryption.decrypt_word(acc)
            except IndexError:
                self.password_text = ""
                self.account_text = ""
        self.login_flag = config["loginFlag"]
        self.game_path = config["gamePath"]
        self.mission_star_game = config["starGame"]
        self.mission_trailblazer_profile = config["trailBlazerProfile"]
        self.mission_redeem_code = False
        self.redeem_code_list = None
        self.redeem_code = None
        self.mission_assignments_reward = config["assignment"]
        self.mission_gift_of_odyssey = config["giftOfOdyssey"]
        self.mission_mail = config["mail"]
        self.mission_trail_blaze_power = config["trailBlazePower"]
        self.mission_daily_training = config["dailyTraining"]
        self.mission_nameless_honor = config["namelessHonor"]
        self.mission_quit_game = config["quitGame"]
        self.calyx_golden_run_time = config["calyx_golden_run_time"]
        self.calyx_golden_battle_time = config["calyx_golden_battle_time"]
        self.calyx_golden_level = config["calyx_golden_level"]
        self.battle_calyx_golden = config["calyx_golden"]
        self.calyx_crimson_run_time = config["calyx_crimson_run_time"]
        self.calyx_crimson_battle_time = config["calyx_crimson_battle_time"]
        self.calyx_crimson_level = config["calyx_crimson_level"]
        self.battle_crimson_golden = config["calyx_crimson"]
        self.stagnant_shadow_run_time = config["stagnant_shadow_run_time"]
        self.stagnant_shadow_level = config["stagnant_shadow_level"]
        self.battle_stagnant_shadow = config["stagnant_shadow"]
        self.caver_of_corrosion_run_time = config["caver_of_corrosion_run_time"]
        self.caver_of_corrosion_level = config["caver_of_corrosion_level"]
        self.battle_caver_of_corrosion = config["caver_of_corrosion"]
        self.echo_of_war_run_time = config["echo_of_war_run_time"]
        self.echo_of_war_level = config["echo_of_war_level"]
        self.battle_echo_of_war = config["echo_of_war"]
        self.battle_ornament_extraction = config["ornament_extraction"]
        self.ornament_extraction_level = config["ornament_extraction_level"]
        self.ornament_extraction_run_time = config["ornament_extraction_run_time"]
        self.replenish_trail_blaze_power_run_time = 1
        self.replenish_way = 1
        self.replenish_trail_blaze_power = False
        self.trail_blaze_power_container = QWidget()
        self.star_game_setting_container = QWidget()
        self.redeem_code_setting_container = QWidget()

        menu_bar = self.menuBar()
        help_menu = menu_bar.addMenu("帮助")
        notice_action = QAction("更新公告", self)
        notice_action.triggered.connect(self.notice)
        problem_action = QAction("常见问题", self)
        problem_action.triggered.connect(self.problem)
        report_action = QAction("问题反馈", self)
        report_action.triggered.connect(self.report)
        help_menu.addAction(notice_action)
        help_menu.addAction(problem_action)
        help_menu.addAction(report_action)
        # self.flag()
        central_widget = QWidget(self)
        self.setWindowTitle("SRA beta v0.6")  # 设置窗口标题
        self.setWindowIcon(QIcon("res/SRAicon.ico"))

        # 创建垂直布局管理器
        vbox_layout_left = QVBoxLayout()
        self.vbox_layout_middle = QVBoxLayout()
        vbox_layout_right = QVBoxLayout()

        hbox_layout_center = QHBoxLayout()
        hbox_layout_center.addLayout(vbox_layout_left)
        hbox_layout_center.addLayout(self.vbox_layout_middle)
        hbox_layout_center.addLayout(vbox_layout_right)

        # 创建标签控件并添加到布局中
        label_left = QLabel("功能选择")
        label_left.setFixedSize(200, 50)
        label_left.setAlignment(Qt.AlignCenter)
        vbox_layout_left.addWidget(label_left)

        label_middle = QLabel("任务设置")
        label_middle.setFixedSize(400, 50)
        label_middle.setAlignment(Qt.AlignCenter)
        self.vbox_layout_middle.addWidget(label_middle)

        label_right = QLabel("日志")
        label_right.setAlignment(Qt.AlignCenter)
        label_right.setMinimumSize(300, 50)
        vbox_layout_right.addWidget(label_right)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        vbox_layout_right.addWidget(self.log)

        self.setCentralWidget(central_widget)  # 将标签作为窗口的中央控件
        option1 = QCheckBox("启动游戏")
        option1.setChecked(self.mission_star_game)
        option1.stateChanged.connect(self.star_game_status)
        button1 = QPushButton("设置")
        button1.clicked.connect(self.show_star_game_setting)
        opt1 = QHBoxLayout()
        opt1.addWidget(option1)
        opt1.addWidget(button1)

        option2 = QCheckBox("漫游签证")
        option2.setChecked(self.mission_trailblazer_profile)
        option2.stateChanged.connect(self.trailblazer_profile_status)
        # button2 = QPushButton('设置')
        opt2 = QHBoxLayout()
        opt2.addWidget(option2)
        # opt2.addWidget(button2)

        option11 = QCheckBox("兑换码")
        option11.setChecked(self.mission_redeem_code)
        option11.stateChanged.connect(self.redeem_code_status)
        button11 = QPushButton("设置")
        button11.clicked.connect(self.show_redeem_code_setting)
        opt11 = QHBoxLayout()
        opt11.addWidget(option11)
        opt11.addWidget(button11)

        option3 = QCheckBox("派遣")
        option3.setChecked(self.mission_assignments_reward)
        option3.stateChanged.connect(self.assignment_status)
        # button3 = QPushButton('设置')
        opt3 = QHBoxLayout()
        opt3.addWidget(option3)
        # opt3.addWidget(button3)

        option4 = QCheckBox("巡星之礼")
        option4.setChecked(self.mission_gift_of_odyssey)
        option4.stateChanged.connect(self.gift_of_odyssey_status)
        # button4 = QPushButton('设置')
        opt4 = QHBoxLayout()
        opt4.addWidget(option4)
        # opt4.addWidget(button4)

        option5 = QCheckBox("邮件")
        option5.setChecked(self.mission_mail)
        option5.stateChanged.connect(self.mail_status)
        # button5 = QPushButton('设置')
        opt5 = QHBoxLayout()
        opt5.addWidget(option5)
        # opt5.addWidget(button5)

        option6 = QCheckBox("清开拓力")
        option6.setChecked(self.mission_trail_blaze_power)
        option6.stateChanged.connect(self.trail_blaze_power_status)
        button6 = QPushButton("设置")
        button6.clicked.connect(self.show_trail_blaze_power_setting)
        opt6 = QHBoxLayout()
        opt6.addWidget(option6)
        opt6.addWidget(button6)

        option7 = QCheckBox("每日实训")
        option7.setChecked(self.mission_daily_training)
        option7.stateChanged.connect(self.daily_training_status)
        # button7 = QPushButton('设置')
        opt7 = QHBoxLayout()
        opt7.addWidget(option7)
        # opt7.addWidget(button7)

        option8 = QCheckBox("无名勋礼")
        option8.setChecked(self.mission_nameless_honor)
        option8.stateChanged.connect(self.nameless_honor_status)
        # button8 = QPushButton('设置')
        opt8 = QHBoxLayout()
        opt8.addWidget(option8)
        # opt8.addWidget(button8)

        opt9 = QCheckBox("退出游戏")
        opt9.setChecked(self.mission_quit_game)
        opt9.stateChanged.connect(self.quit_game_status)
        self.button9 = QPushButton("执行")
        self.button9.clicked.connect(self.execute)
        self.button10 = QPushButton("停止")
        self.button10.clicked.connect(self.kill)
        self.button10.setEnabled(False)

        vbox_layout_left.addLayout(opt1)
        vbox_layout_left.addLayout(opt2)
        vbox_layout_left.addLayout(opt11)
        vbox_layout_left.addLayout(opt3)
        vbox_layout_left.addLayout(opt4)
        vbox_layout_left.addLayout(opt5)
        vbox_layout_left.addLayout(opt6)
        vbox_layout_left.addLayout(opt7)
        vbox_layout_left.addLayout(opt8)
        vbox_layout_left.addWidget(opt9)
        vbox_layout_left.addWidget(self.button9)
        vbox_layout_left.addWidget(self.button10)

        central_widget.setLayout(hbox_layout_center)
        self.star_game_setting()
        self.trail_blaze_power_setting()
        self.redeem_code_setting()
        QMessageBox.information(
            self,
            "使用说明",
            "SRA崩坏：星穹铁道助手beta v0.6 by雪影\n"
            "使用说明：\n"
            "重要！以管理员模式运行程序！\n"
            "重要！调整游戏分辨率为1920*1080并保持游戏窗口无遮挡，注意不要让游戏窗口超出屏幕\n"
            "重要！执行任务时不要进行其他操作！*请使用游戏默认键位！\n"
            "\n声明：本程序完全免费，仅供学习交流使用。本程序依靠计算机图像识别和模拟操作运行，"
            "不会做出任何修改游戏文件、读写游戏内存等任何危害游戏本体的行为。"
            "如果您使用此程序，我们认为您充分了解《米哈游游戏使用许可及服务协议》第十条之规定，"
            "您在使用此程序中产生的任何问题（除程序错误导致外）与此程序无关，相应的后果由您自行承担。\n\n"
            "请不要在崩坏：星穹铁道及米哈游在各平台（包括但不限于：米游社、B 站、微博）的官方动态下讨论任何关于 SRA 内容。"
            "\n"
            "\n人话：不要跳脸官方～(∠・ω< )⌒☆",
        )
        self.update_log(
            "在" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "成功启动"
        )

    def star_game_setting(self):
        game_path = QHBoxLayout()
        setting1 = QVBoxLayout()

        text = QLabel("游戏路径：")
        self.line_area = QLineEdit()
        self.line_area.setText(self.game_path)
        self.line_area.textChanged.connect(self.get_path)
        button = QPushButton("浏览")
        button.clicked.connect(self.open_file)
        game_path.addWidget(text)
        game_path.addWidget(self.line_area)
        game_path.addWidget(button)
        setting1.addLayout(game_path)

        auto_launch_checkbox = QCheckBox("自动登录")
        auto_launch_checkbox.stateChanged.connect(self.auto_launch)
        setting1.addWidget(auto_launch_checkbox)
        form = QFormLayout()
        acc = QLabel("账号：")
        self.account = QLineEdit(self.account_text)
        self.account.setReadOnly(True)
        self.account.textChanged.connect(self.get_account)
        psw = QLabel("密码：")
        self.password = QLineEdit(self.password_text)
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setReadOnly(True)
        self.password.textChanged.connect(self.get_password)
        self.show_button = QPushButton("显示")
        self.show_button.clicked.connect(self.togglePasswordVisibility)
        form.addRow(acc, self.account)
        form.addRow(psw, self.password)
        form.addRow(None, self.show_button)
        setting1.addLayout(form)
        self.star_game_setting_container.setLayout(setting1)
        self.vbox_layout_middle.addWidget(self.star_game_setting_container)
        self.star_game_setting_container.setVisible(True)

    def show_star_game_setting(self):
        self.display_none()
        self.star_game_setting_container.setVisible(True)

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "可执行文件 (*.exe)"
        )
        if file_name:
            self.line_area.setText(file_name)
            self.game_path = file_name

    def get_path(self, text):
        self.game_path = text

    def get_account(self, text):
        self.account_text = text

    def get_password(self, text):
        self.password_text = text

    def auto_launch(self, state):
        if state == Qt.Checked:
            self.log.append("自动登录已启用")
            self.login_flag = True
            self.account.setReadOnly(False)
            self.password.setReadOnly(False)
        else:
            self.log.append("自动登录已禁用")
            self.login_flag = False
            self.account.setReadOnly(True)
            self.password.setReadOnly(True)

    def togglePasswordVisibility(self):
        # 切换密码可见性
        if self.password.echoMode() == QLineEdit.Password:
            self.password.setEchoMode(QLineEdit.Normal)
            self.show_button.setText("隐藏")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.show_button.setText("显示")

    def display_none(self):
        self.star_game_setting_container.setVisible(False)
        self.trail_blaze_power_container.setVisible(False)
        self.redeem_code_setting_container.setVisible(False)

    def star_game_status(self, state):
        if state == Qt.Checked:
            self.log.append("启动游戏已启用")
            self.mission_star_game = True
        else:
            self.log.append("启动游戏已禁用")
            self.mission_star_game = False

    def trailblazer_profile_status(self, state):
        if state == Qt.Checked:
            self.log.append("添加任务：领取签证奖励")
            self.mission_trailblazer_profile = True
        else:
            self.log.append("取消任务：领取签证奖励")
            self.mission_trailblazer_profile = False

    def redeem_code_status(self, state):
        if state == Qt.Checked:
            self.log.append("添加任务：领取兑换码奖励")
            self.mission_redeem_code = True
            self.mission_mail = True
        else:
            self.log.append("取消任务：领取兑换码奖励")
            self.mission_redeem_code = False

    def assignment_status(self, state):
        if state == Qt.Checked:
            self.log.append("添加任务：领取派遣奖励")
            self.mission_assignments_reward = True
        else:
            self.log.append("取消任务：领取派遣奖励")
            self.mission_assignments_reward = False

    def gift_of_odyssey_status(self, state):
        if state == Qt.Checked:
            self.log.append("添加任务：领取巡星之礼")
            self.mission_gift_of_odyssey = True
        else:
            self.log.append("取消任务：领取巡星之礼")
            self.mission_gift_of_odyssey = False

    def mail_status(self, state):
        if state == Qt.Checked:
            self.log.append("添加任务：领取邮件")
            self.mission_mail = True
        else:
            self.log.append("取消任务：领取邮件")
            self.mission_mail = False
            self.mission_redeem_code = False

    def trail_blaze_power_status(self, state):
        if state == Qt.Checked:
            self.log.append("添加任务：清开拓力")
            self.mission_trail_blaze_power = True
        else:
            self.log.append("取消任务：清开拓力")
            self.mission_trail_blaze_power = False

    def daily_training_status(self, state):
        if state == Qt.Checked:
            self.log.append("添加任务：领取每日实训")
            self.mission_daily_training = True
        else:
            self.log.append("取消任务：领取每日实训")
            self.mission_daily_training = False

    def nameless_honor_status(self, state):
        if state == Qt.Checked:
            self.log.append("添加任务：领取无名勋礼")
            self.mission_nameless_honor = True
        else:
            self.log.append("取消任务：领取无名勋礼")
            self.mission_nameless_honor = False

    def quit_game_status(self, state):
        if state == Qt.Checked:
            self.log.append("退出游戏已启用")
            self.mission_quit_game = True
        else:
            self.log.append("退出游戏已禁用")
            self.mission_quit_game = False

    def redeem_code_setting(self):
        setting = QVBoxLayout()
        text = QLabel("兑换码")
        text.setAlignment(Qt.AlignCenter)
        self.redeem_code = QTextEdit()
        self.redeem_code.textChanged.connect(self.redeem_code_change)
        setting.addWidget(text)
        setting.addWidget(self.redeem_code)
        self.redeem_code_setting_container.setLayout(setting)
        self.vbox_layout_middle.addWidget(self.redeem_code_setting_container)
        self.redeem_code_setting_container.setVisible(False)

    def redeem_code_change(self):
        redeem_code = self.redeem_code.toPlainText()
        # self.log.append(redeem_code)
        self.redeem_code_list = redeem_code.split()

    def show_redeem_code_setting(self):
        self.display_none()
        self.redeem_code_setting_container.setVisible(True)

    def trail_blaze_power_setting(self):
        self.trail_blaze_power_container = QWidget()
        setting = QVBoxLayout()

        replenish_trail_blaze_power = QVBoxLayout()
        option0 = QHBoxLayout()
        opt0 = QCheckBox("补充体力")
        opt0.setChecked(self.replenish_trail_blaze_power)
        opt0.stateChanged.connect(self.replenish_trail_blaze_power_status)
        combobox0 = QComboBox()
        combobox0.addItems(["-----补充方式-----", "后备开拓力", "燃料", "星琼"])
        combobox0.currentIndexChanged.connect(self.replenish_way_select)
        combobox0.setCurrentIndex(self.replenish_way)
        option0.addWidget(opt0)
        option0.addWidget(combobox0)
        replenish_trail_blaze_power.addLayout(option0)
        times_box0 = QHBoxLayout()
        text0 = QLabel("次数：")
        times0 = QSpinBox()
        times0.setMinimum(1)
        times0.setValue(self.replenish_trail_blaze_power_run_time)
        times0.valueChanged.connect(self.replenish_trail_blaze_power_run_time_change)
        times_box0.addWidget(text0)
        times_box0.addWidget(times0)
        replenish_trail_blaze_power.addLayout(times_box0)

        ornament_extraction = QVBoxLayout()
        option1 = QHBoxLayout()
        opt1 = QCheckBox("饰品提取")
        opt1.setChecked(self.battle_ornament_extraction)
        opt1.stateChanged.connect(self.ornament_extraction_status)
        combobox1 = QComboBox()
        combobox1.addItems(
            [
                "-----选择副本-----",
                "蠹役饥肠（露莎卡/蕉乐园）",
                "永恒笑剧（都蓝/劫火）",
                "伴你入眠（茨冈尼亚/出云显世）",
                "天剑如雨（格拉默/匹诺康尼）",
                "孽果盘生（繁星/龙骨）",
                "百年冻土（贝洛伯格/萨尔索图）",
                "温柔话语（公司/差分机）",
                "浴火钢心（塔利亚/翁瓦克）",
                "坚城不倒（太空封印站/仙舟）",
            ]
        )
        combobox1.currentIndexChanged.connect(self.ornament_extraction_level_select)
        combobox1.setCurrentIndex(self.ornament_extraction_level)
        option1.addWidget(opt1)
        option1.addWidget(combobox1)
        ornament_extraction.addLayout(option1)
        times_box = QHBoxLayout()
        text = QLabel("次数：")
        times = QSpinBox()
        times.setMinimum(1)
        times.setValue(self.ornament_extraction_run_time)
        times.valueChanged.connect(self.ornament_extraction_run_time_change)
        times_box.addWidget(text)
        times_box.addWidget(times)
        ornament_extraction.addLayout(times_box)

        calyx_golden = QVBoxLayout()
        option2 = QHBoxLayout()
        opt2 = QCheckBox("拟造花萼（金）(10)")
        opt2.setChecked(self.battle_calyx_golden)
        opt2.stateChanged.connect(self.calyx_golden_status)
        combobox2 = QComboBox()
        combobox2.addItems(
            [
                "-----选择副本-----",
                "回忆之蕾（匹诺康尼）",
                "以太之蕾（匹诺康尼）",
                "珍藏之蕾（匹诺康尼）",
                "回忆之蕾（仙舟罗浮）",
                "以太之蕾（仙舟罗浮）",
                "珍藏之蕾（仙舟罗浮）",
                "回忆之蕾（雅利洛VI）",
                "以太之蕾（雅利洛VI）",
                "珍藏之蕾（雅利洛VI）",
            ]
        )
        combobox2.setCurrentIndex(self.calyx_golden_level)
        combobox2.currentIndexChanged.connect(self.calyx_golden_level_select)
        option2.addWidget(opt2)
        option2.addWidget(combobox2)
        calyx_golden.addLayout(option2)
        times_box2 = QHBoxLayout()
        single_times2_text = QLabel("连续作战：")
        single_times2 = QSpinBox()
        single_times2.setMinimum(1)
        single_times2.setValue(self.calyx_golden_battle_time)
        single_times2.setMaximum(6)
        single_times2.valueChanged.connect(self.calyx_golden_battle_time_change)
        battle_times2_text = QLabel("执行次数：")
        battle_times2 = QSpinBox()
        battle_times2.setMinimum(1)
        battle_times2.setValue(self.calyx_golden_run_time)
        battle_times2.valueChanged.connect(self.calyx_golden_run_time_change)
        times_box2.addWidget(single_times2_text)
        times_box2.addWidget(single_times2)
        times_box2.addWidget(battle_times2_text)
        times_box2.addWidget(battle_times2)
        calyx_golden.addLayout(times_box2)

        calyx_crimson = QVBoxLayout()
        option3 = QHBoxLayout()
        opt3 = QCheckBox("拟造花萼（赤）(10)")
        opt3.setChecked(self.battle_crimson_golden)
        opt3.stateChanged.connect(self.calyx_crimson_status)
        combobox3 = QComboBox()
        combobox3.addItems(
            [
                "-----选择副本-----",
                "月狂獠牙（毁灭）",
                "净世残刃（毁灭）",
                "神体琥珀（存护）",
                "琥珀的坚守（存护）",
                "逆时一击（巡猎）",
                "逐星之矢（巡猎）",
                "万象果实（丰饶）",
                "永恒之花（丰饶）",
                "精致色稿（智识）",
                "智识之钥（智识）",
                "天外乐章（同谐）",
                "群星乐章（同谐）",
                "焚天之魔（虚无）",
                "沉沦黑曜（虚无）",
            ]
        )
        combobox3.setCurrentIndex(self.calyx_crimson_level)
        combobox3.currentIndexChanged.connect(self.calyx_crimson_level_select)
        option3.addWidget(opt3)
        option3.addWidget(combobox3)
        calyx_crimson.addLayout(option3)
        times_box3 = QHBoxLayout()
        single_times3_text = QLabel("连续作战：")
        single_times3 = QSpinBox()
        single_times3.setMinimum(1)
        single_times3.setValue(self.calyx_crimson_battle_time)
        single_times3.setMaximum(6)
        single_times3.valueChanged.connect(self.calyx_crimson_battle_time_change)
        battle_times3_text = QLabel("执行次数：")
        battle_times3 = QSpinBox()
        battle_times3.setMinimum(1)
        battle_times3.setValue(self.calyx_crimson_run_time)
        battle_times3.valueChanged.connect(self.calyx_crimson_run_time_change)
        times_box3.addWidget(single_times3_text)
        times_box3.addWidget(single_times3)
        times_box3.addWidget(battle_times3_text)
        times_box3.addWidget(battle_times3)
        calyx_crimson.addLayout(times_box3)

        stagnant_shadow = QVBoxLayout()
        option4 = QHBoxLayout()
        opt4 = QCheckBox("凝滞虚影(30)")
        opt4.setChecked(self.battle_stagnant_shadow)
        opt4.stateChanged.connect(self.stagnant_shadow_status)
        combobox4 = QComboBox()
        combobox4.addItems(
            [
                "-----选择副本-----",
                "星际和平工作证（物理）",
                "幽府通令（物理）",
                "铁狼碎齿（物理）",
                "忿火之心（火）",
                "过热钢刀（火）",
                "恒温晶壳（火）",
                "冷藏梦箱（冰）",
                "苦寒晶壳（冰）",
                "风雪之角（冰）",
                "兽馆之钉（雷）",
                "炼形者雷枝（雷）",
                "往日之影的雷冠（雷）",
                "一杯酩酊的时代（风）",
                "无人遗垢（风）",
                "暴风之眼（风）",
                "炙梦喷枪（量子）",
                "苍猿之钉（量子）",
                "虚幻铸铁（量子）",
                "镇灵敕符（虚数）",
                "往日之影的金饰（虚数）",
            ]
        )
        combobox4.setCurrentIndex(self.stagnant_shadow_level)
        combobox4.currentIndexChanged.connect(self.stagnant_shadow_level_select)
        option4.addWidget(opt4)
        option4.addWidget(combobox4)
        stagnant_shadow.addLayout(option4)
        times_box4 = QHBoxLayout()
        battle_times4_text = QLabel("执行次数：")
        battle_times4 = QSpinBox()
        battle_times4.setMinimum(1)
        battle_times4.setValue(self.stagnant_shadow_run_time)
        battle_times4.valueChanged.connect(self.stagnant_shadow_run_time_change)
        times_box4.addWidget(battle_times4_text)
        times_box4.addWidget(battle_times4)
        stagnant_shadow.addLayout(times_box4)

        caver_of_corrosion = QVBoxLayout()
        option5 = QHBoxLayout()
        opt5 = QCheckBox("侵蚀隧洞(40)")
        opt5.setChecked(self.battle_caver_of_corrosion)
        opt5.stateChanged.connect(self.caver_of_corrosion_status)
        combobox5 = QComboBox()
        combobox5.addItems(
            [
                "-----选择副本-----",
                "勇骑之径",
                "梦潜之径",
                "幽冥之径",
                "药使之径",
                "野焰之径",
                "圣颂之径",
                "睿智之径",
                "漂泊之径",
                "迅拳之径",
                "霜风之径",
            ]
        )
        combobox5.setCurrentIndex(self.caver_of_corrosion_level)
        combobox5.currentIndexChanged.connect(self.caver_of_corrosion_level_select)
        option5.addWidget(opt5)
        option5.addWidget(combobox5)
        caver_of_corrosion.addLayout(option5)
        times_box5 = QHBoxLayout()
        battle_times5_text = QLabel("执行次数：")
        battle_times5 = QSpinBox()
        battle_times5.setMinimum(1)
        battle_times5.setValue(self.caver_of_corrosion_run_time)
        battle_times5.valueChanged.connect(self.caver_of_corrosion_run_time_change)
        times_box5.addWidget(battle_times5_text)
        times_box5.addWidget(battle_times5)
        caver_of_corrosion.addLayout(times_box5)

        echo_of_war = QVBoxLayout()
        option6 = QHBoxLayout()
        opt6 = QCheckBox("历战余响(30)")
        opt6.setChecked(self.battle_echo_of_war)
        opt6.stateChanged.connect(self.echo_of_war_status)
        combobox6 = QComboBox()
        combobox6.addItems(
            [
                "-----选择副本-----",
                "心兽的战场",
                "尘梦的赞礼",
                "蛀星的旧靥",
                "不死的神实",
                "寒潮的落幕",
                "毁灭的开端",
            ]
        )
        combobox6.setCurrentIndex(self.echo_of_war_level)
        combobox6.currentIndexChanged.connect(self.echo_of_war_level_select)
        option6.addWidget(opt6)
        option6.addWidget(combobox6)
        echo_of_war.addLayout(option6)
        times_box6 = QHBoxLayout()
        battle_times6_text = QLabel("执行次数：")
        battle_times6 = QSpinBox()
        battle_times6.setMinimum(0)
        battle_times6.setMaximum(3)
        battle_times6.setValue(self.echo_of_war_run_time)
        battle_times6.valueChanged.connect(self.echo_of_war_run_time_change)
        times_box6.addWidget(battle_times6_text)
        times_box6.addWidget(battle_times6)
        echo_of_war.addLayout(times_box6)

        setting.addLayout(replenish_trail_blaze_power)
        setting.addLayout(ornament_extraction)
        setting.addLayout(calyx_golden)
        setting.addLayout(calyx_crimson)
        setting.addLayout(stagnant_shadow)
        setting.addLayout(caver_of_corrosion)
        setting.addLayout(echo_of_war)
        self.trail_blaze_power_container.setLayout(setting)
        self.vbox_layout_middle.addWidget(self.trail_blaze_power_container)
        self.trail_blaze_power_container.setVisible(False)

    def replenish_trail_blaze_power_status(self, state):
        if state == Qt.Checked:
            # self.log.append('ornament_extraction T')
            self.replenish_trail_blaze_power = True
        else:
            # self.log.append('ornament_extraction F')
            self.replenish_trail_blaze_power = False

    def replenish_way_select(self, index):
        self.replenish_way = index
        # self.log.append(str(index))

    def replenish_trail_blaze_power_run_time_change(self, value):
        self.replenish_trail_blaze_power_run_time = value
        # self.log.append(str(value))

    def ornament_extraction_status(self, state):
        if state == Qt.Checked:
            # self.log.append('ornament_extraction T')
            self.battle_ornament_extraction = True
        else:
            # self.log.append('ornament_extraction F')
            self.battle_ornament_extraction = False

    def ornament_extraction_level_select(self, index):
        self.ornament_extraction_level = index
        # self.log.append(str(index))

    def ornament_extraction_run_time_change(self, value):
        self.ornament_extraction_run_time = value
        # self.log.append(str(value))

    def calyx_golden_status(self, state):
        if state == Qt.Checked:
            # self.log.append('calyx_golden T')
            self.battle_calyx_golden = True
        else:
            # self.log.append('calyx_golden F')
            self.battle_calyx_golden = False

    def calyx_golden_level_select(self, index):
        self.calyx_golden_level = index
        # self.log.append(str(index))

    def calyx_golden_battle_time_change(self, value):
        self.calyx_golden_battle_time = value
        # self.log.append(str(self.calyx_golden_battle_time))

    def calyx_golden_run_time_change(self, value):
        self.calyx_golden_run_time = value
        # self.log.append(str(value))

    def calyx_crimson_status(self, state):
        if state == Qt.Checked:
            # self.log.append('calyx_crimson T')
            self.battle_crimson_golden = True
        else:
            # self.log.append('calyx_crimson F')
            self.battle_crimson_golden = False

    def calyx_crimson_level_select(self, index):
        self.calyx_crimson_level = index
        # self.log.append(str(index))

    def calyx_crimson_battle_time_change(self, value):
        self.calyx_crimson_battle_time = value
        # self.log.append(str(self.calyx_crimson_battle_time))

    def calyx_crimson_run_time_change(self, value):
        self.calyx_crimson_run_time = value
        # self.log.append(str(value))

    def stagnant_shadow_status(self, state):
        if state == Qt.Checked:
            # self.log.append('stagnant_shadow T')
            self.battle_stagnant_shadow = True
        else:
            # self.log.append('stagnant_shadow F')
            self.battle_stagnant_shadow = False

    def stagnant_shadow_level_select(self, index):
        self.stagnant_shadow_level = index
        # self.log.append(str(index))

    def stagnant_shadow_run_time_change(self, value):
        self.stagnant_shadow_run_time = value
        # self.log.append(str(value))

    def caver_of_corrosion_status(self, state):
        if state == Qt.Checked:
            # self.log.append('caver_of_corrosion T')
            self.battle_caver_of_corrosion = True
        else:
            # self.log.append('caver_of_corrosion F')
            self.battle_caver_of_corrosion = False

    def caver_of_corrosion_level_select(self, index):
        self.caver_of_corrosion_level = index
        # self.log.append(str(index))

    def caver_of_corrosion_run_time_change(self, value):
        self.caver_of_corrosion_run_time = value
        # self.log.append(str(value))

    def echo_of_war_status(self, state):
        if state == Qt.Checked:
            # self.log.append('echo_of_war T')
            self.battle_echo_of_war = True
        else:
            # self.log.append('echo_of_war F')
            self.battle_echo_of_war = False

    def echo_of_war_level_select(self, index):
        self.echo_of_war_level = index
        # self.log.append(str(index))

    def echo_of_war_run_time_change(self, value):
        self.echo_of_war_run_time = value
        # self.log.append(str(value))

    def show_trail_blaze_power_setting(self):
        self.display_none()
        self.trail_blaze_power_container.setVisible(True)

    def update_log(self, text):
        # 在主线程中更新QTextEdit
        self.log.append(text)
        with open("log.txt", "a", encoding="utf-8") as logfile:
            logfile.write(text + "\n")

    def execute(self):
        flags = [
            self.mission_star_game,
            self.mission_trailblazer_profile,
            self.mission_assignments_reward,
            self.mission_redeem_code,
            self.mission_gift_of_odyssey,
            self.mission_mail,
            self.mission_trail_blaze_power,
            self.mission_daily_training,
            self.mission_nameless_honor,
            self.mission_quit_game,
        ]
        if all(not flag for flag in flags):
            self.log.append("未选择任何任务")
        else:
            self.button10.setEnabled(True)
            self.button9.setEnabled(False)
            configuration = {
                "gamePath": self.game_path,
                "starGame": self.mission_star_game,
                "loginFlag": self.login_flag,
                "trailBlazerProfile": self.mission_trailblazer_profile,
                "assignment": self.mission_assignments_reward,
                "redeemCode": self.mission_redeem_code,
                "redeemCodeList": self.redeem_code_list,
                "giftOfOdyssey": self.mission_gift_of_odyssey,
                "mail": self.mission_mail,
                "trailBlazePower": self.mission_trail_blaze_power,
                "dailyTraining": self.mission_daily_training,
                "namelessHonor": self.mission_nameless_honor,
                "quitGame": self.mission_quit_game,
                "ornament_extraction": self.battle_ornament_extraction,
                "ornament_extraction_level": self.ornament_extraction_level,
                "ornament_extraction_run_time": self.ornament_extraction_run_time,
                "calyx_golden": self.battle_calyx_golden,
                "calyx_golden_level": self.calyx_golden_level,
                "calyx_golden_battle_time": self.calyx_golden_battle_time,
                "calyx_golden_run_time": self.calyx_golden_run_time,
                "calyx_crimson": self.battle_crimson_golden,
                "calyx_crimson_level": self.calyx_crimson_level,
                "calyx_crimson_battle_time": self.calyx_crimson_battle_time,
                "calyx_crimson_run_time": self.calyx_crimson_run_time,
                "stagnant_shadow_run_time": self.stagnant_shadow_run_time,
                "stagnant_shadow_level": self.stagnant_shadow_level,
                "stagnant_shadow": self.battle_stagnant_shadow,
                "caver_of_corrosion": self.battle_caver_of_corrosion,
                "caver_of_corrosion_run_time": self.caver_of_corrosion_run_time,
                "caver_of_corrosion_level": self.caver_of_corrosion_level,
                "echo_of_war": self.battle_echo_of_war,
                "echo_of_war_run_time": self.echo_of_war_run_time,
                "echo_of_war_level": self.echo_of_war_level,
                "replenish_trail_blaze_power": self.replenish_trail_blaze_power,
                "replenish_way": self.replenish_way,
                "replenish_trail_blaze_power_run_time": self.replenish_trail_blaze_power_run_time,
            }
            acc = encryption.encrypt_word(self.account_text)
            pwd = encryption.encrypt_word(self.password_text)
            with open("data/privacy.sra", "wb") as sra_file:
                sra_file.write(acc + b"\n" + pwd)
            with open("data/config.json", "w", encoding="utf-8") as json_file:
                json.dump(configuration, json_file, indent=4)
            self.son_thread = StarRailAssistant.Assistant()
            self.son_thread.update_signal.connect(self.update_log)
            self.son_thread.finished.connect(self.notification)
            self.son_thread.start()

    def notification(self):
        self.button9.setEnabled(True)
        self.button10.setEnabled(False)
        try:
            notification.notify(
                title="SRA",
                message="任务全部完成",
                app_icon="res/SRAicon.ico",  # 可以指定一个图标路径
                timeout=10,  # 通知持续时间，秒
            )
        except Exception as e:
            with open("log.txt", "a", encoding="utf-8") as log:
                log.write(str(e) + "\n")

    def kill(self):
        self.son_thread.request_stop()
        self.button10.setEnabled(False)
        self.button9.setEnabled(True)
        self.log.append("等待当前任务完成后停止")

    def notice(self):
        QMessageBox.information(
            self,
            "更新公告",
            "beta v0.7 更新公告\n"
            "新功能：\n"
            "1.\n"
            "2.\n"
            "3.\n"
            "4.\n"
            "5.\n"
            "\n"
            "问题修复：\n"
            "1.修复了在未填写兑换码时勾选此功能会导致程序崩溃的问题。\n"
            "2.修复了无法正常传送到精致色稿副本和万象果实副本的问题。\n"
            "3.\n"
            "4.\n"
            "\n感谢您对SRA的支持！",
        )

    def problem(self):
        QMessageBox.information(
            self,
            "常见问题",
            "\n"
            "1. 在差分宇宙中因奇物“绝对失败处方(进入战斗时，我方全体有150%的基础概率陷入冻结状态，持续1回合)”"
            "冻结队伍会导致无法开启自动战斗，建议开启游戏的沿用自动战斗设置。"
            "\n2. 游戏画面贴近或超出屏幕显示边缘时功能无法正常执行。"
            "\n3. 在执行“历战余响”时若未选择关卡，会导致程序闪退。"
            "\n关于编队：SRA现在还不会编队，对于除饰品提取以外的战斗功能，使用的是当前出战队伍"
            "对于饰品提取，如果没有队伍或者队伍有空位，使用的是预设编队的队伍1（不要改名）\n"
            "此问题等待后续优化\n\n",
        )

    def report(self):
        QMessageBox.information(
            self,
            "问题反馈",
            "B站：https://space.bilibili.com/349682013\nQQ邮箱：yukikage@qq.com\nQQ群：994571792",
        )


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if __name__ == "__main__":
    if is_admin():
        # 创建一个 PyQt5 应用程序对象
        app = QApplication(sys.argv)

        # 应用全局样式表
        app.setStyleSheet(
            "QPushButton, QLabel, QTextEdit, QCheckBox, QComboBox, QSpinBox, QLineEdit "
            "{ font-family: Microsoft YaHei; font-size: 12pt; }"
        )

        # 创建主窗口实例
        window = MainWindow()
        window.show()  # 显示窗口

        # 进入应用程序的事件循环，保持应用程序运行，直到关闭窗口
        sys.exit(app.exec_())

    else:
        # 重新以管理员权限运行脚本
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        # 退出当前进程
        sys.exit()
