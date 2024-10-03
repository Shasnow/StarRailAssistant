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
图形化
"""

import os
import sys  # 导入 sys 模块，用于与 Python 解释器交互
import json
import time
from PySide6.QtGui import QIcon, QAction
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
    QGroupBox,
    QFileDialog,
    QMessageBox,
    QLineEdit,
    QTextEdit,
    QTextBrowser,
    QComboBox,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QVBoxLayout,
)  # 从 PySide6 中导入所需的类
from plyer import notification
import encryption
import StarRailAssistant
import ctypes

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SRA")  # 修改任务栏图标

uiLoader = QUiLoader()


class Main(QMainWindow):

    AppPath = os.path.dirname(os.path.realpath(sys.argv[0])).replace(
        "\\", "/"
    )  # 获取软件自身的路径

    def __init__(self):
        super().__init__()  # 调用父类 QMainWindow 的初始化方法
        encryption.init()

        with open(self.AppPath + "/data/config.json", "r", encoding="utf-8") as file:
            config = json.load(file)
        with open(self.AppPath + "/data/privacy.sra", "rb") as sra_file:
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
        self.mission_start_game = config["starGame"]
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

        self.ui = uiLoader.load(self.AppPath + "/res/ui/main.ui")
        self.start_game_setting_container = uiLoader.load(
            self.AppPath + "/res/ui/set_01.ui"
        )
        self.redeem_code_setting_container = uiLoader.load(
            self.AppPath + "/res/ui/set_03.ui"
        )
        self.trail_blaze_power_container = uiLoader.load(
            self.AppPath + "/res/ui/set_07.ui"
        )

        notice_action = self.ui.findChild(QAction, "action_1")
        notice_action.triggered.connect(self.notice)
        problem_action = self.ui.findChild(QAction, "action_2")
        problem_action.triggered.connect(self.problem)
        report_action = self.ui.findChild(QAction, "action_3")
        report_action.triggered.connect(self.report)
        # central_widget = QWidget(self)
        self.ui.setWindowTitle("SRA v0.7_beta")  # 设置窗口标题
        self.ui.setWindowIcon(QIcon(self.AppPath + "/res/SRAicon.ico"))

        # 创建垂直布局管理器用于任务设置
        self.task_set_vbox_layout = QVBoxLayout()
        task_set = self.ui.findChild(QGroupBox, "groupBox_2")
        task_set.setLayout(self.task_set_vbox_layout)

        # 创建标签控件并添加到布局中
        self.log = self.ui.findChild(QTextBrowser, "textBrowser_log")

        self.option1 = self.ui.findChild(QCheckBox, "checkBox1_1")
        self.option1.setChecked(self.mission_start_game)
        self.option1.stateChanged.connect(self.start_game_status)
        button1 = self.ui.findChild(QPushButton, "pushButton1_1")
        button1.clicked.connect(self.show_start_game_setting)

        self.option2 = self.ui.findChild(QCheckBox, "checkBox1_2")
        self.option2.setChecked(self.mission_trailblazer_profile)
        self.option2.stateChanged.connect(self.trailblazer_profile_status)
        # button2 = self.ui.findChild(QPushButton, "pushButton1_2")

        self.option3 = self.ui.findChild(QCheckBox, "checkBox1_3")
        self.option3.setChecked(self.mission_redeem_code)
        self.option3.stateChanged.connect(self.redeem_code_status)
        button3 = self.ui.findChild(QPushButton, "pushButton1_3")
        button3.clicked.connect(self.show_redeem_code_setting)

        self.option4 = self.ui.findChild(QCheckBox, "checkBox1_4")
        self.option4.setChecked(self.mission_assignments_reward)
        self.option4.stateChanged.connect(self.assignment_status)
        # button4 = self.ui.findChild(QPushButton, "pushButton1_4")

        self.option5 = self.ui.findChild(QCheckBox, "checkBox1_5")
        self.option5.setChecked(self.mission_gift_of_odyssey)
        self.option5.stateChanged.connect(self.gift_of_odyssey_status)
        # button5 = self.ui.findChild(QPushButton, "pushButton1_5")

        self.option6 = self.ui.findChild(QCheckBox, "checkBox1_6")
        self.option6.setChecked(self.mission_mail)
        self.option6.stateChanged.connect(self.mail_status)
        # button6 = self.ui.findChild(QPushButton, "pushButton1_6")

        self.option7 = self.ui.findChild(QCheckBox, "checkBox1_7")
        self.option7.setChecked(self.mission_trail_blaze_power)
        self.option7.stateChanged.connect(self.trail_blaze_power_status)
        button7 = self.ui.findChild(QPushButton, "pushButton1_7")
        button7.clicked.connect(self.show_trail_blaze_power_setting)

        self.option8 = self.ui.findChild(QCheckBox, "checkBox1_8")
        self.option8.setChecked(self.mission_daily_training)
        self.option8.stateChanged.connect(self.daily_training_status)
        # button8 = self.ui.findChild(QPushButton, "pushButton1_8")

        self.option9 = self.ui.findChild(QCheckBox, "checkBox1_9")
        self.option9.setChecked(self.mission_nameless_honor)
        self.option9.stateChanged.connect(self.nameless_honor_status)
        # button9 = self.ui.findChild(QPushButton, "pushButton1_9")

        self.option10 = self.ui.findChild(QCheckBox, "checkBox1_10")
        self.option10.setChecked(self.mission_quit_game)
        self.option10.stateChanged.connect(self.quit_game_status)
        # button10 = self.ui.findChild(QPushButton, "pushButton1_10")

        self.button0_1 = self.ui.findChild(QPushButton, "pushButton1_0_1")
        self.button0_1.clicked.connect(self.execute)
        self.button0_2 = self.ui.findChild(QPushButton, "pushButton1_0_2")
        self.button0_2.clicked.connect(self.kill)
        self.button0_2.setEnabled(False)

        self.start_game_setting()
        self.trail_blaze_power_setting()
        self.redeem_code_setting()

        self.update_log(
            time.strftime("%Y-%m-%d %H:%M:%S ", time.localtime()) + "启动成功"
        )

    def start_game_setting(self):

        self.line_area = self.start_game_setting_container.findChild(
            QLineEdit, "lineEdit2_1"
        )
        self.line_area.setText(self.game_path)
        self.line_area.textChanged.connect(self.get_path)
        button = self.start_game_setting_container.findChild(
            QPushButton, "pushButton2_1"
        )
        button.clicked.connect(self.open_file)

        self.auto_launch_checkbox = self.start_game_setting_container.findChild(
            QCheckBox, "checkBox2_2"
        )
        self.auto_launch_checkbox.stateChanged.connect(self.auto_launch)
        self.account = self.start_game_setting_container.findChild(
            QLineEdit, "lineEdit2_3_12"
        )
        self.account.setText(self.account_text)
        self.account.setReadOnly(True)
        self.account.textChanged.connect(self.get_account)
        self.password = self.start_game_setting_container.findChild(
            QLineEdit, "lineEdit2_3_22"
        )
        self.password.setText(self.password_text)
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setReadOnly(True)
        self.password.textChanged.connect(self.get_password)
        self.show_button = self.start_game_setting_container.findChild(
            QPushButton, "pushButton2_2"
        )
        self.show_button.clicked.connect(self.togglePasswordVisibility)
        self.task_set_vbox_layout.addWidget(self.start_game_setting_container)
        self.start_game_setting_container.setVisible(True)

    def show_start_game_setting(self):
        """Set start game setting visible"""
        self.display_none()
        self.start_game_setting_container.setVisible(True)

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

    def auto_launch(self):
        """
        Change the state of mission auto launch,
        update QLineEdit state.
        """
        if self.auto_launch_checkbox.isChecked():
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
        """Toggle password visibility"""
        if self.password.echoMode() == QLineEdit.Password:
            self.password.setEchoMode(QLineEdit.Normal)
            self.show_button.setText("隐藏")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.show_button.setText("显示")

    def display_none(self):
        """Sets the invisible state of the container."""
        self.start_game_setting_container.setVisible(False)
        self.trail_blaze_power_container.setVisible(False)
        self.redeem_code_setting_container.setVisible(False)

    def start_game_status(self):
        """Change the state of mission start game."""
        if self.option1.isChecked():
            self.log.append("启动游戏已启用")
            self.mission_start_game = True
        else:
            self.log.append("启动游戏已禁用")
            self.mission_start_game = False

    def trailblazer_profile_status(self):
        """Change the state of mission trailblazer profile."""
        if self.option2.isChecked():
            self.log.append("添加任务：领取签证奖励")
            self.mission_trailblazer_profile = True
        else:
            self.log.append("取消任务：领取签证奖励")
            self.mission_trailblazer_profile = False

    def redeem_code_status(self):
        """Change the state of mission redeem code."""
        if self.option3.isChecked():
            self.log.append("添加任务：领取兑换码奖励")
            self.mission_redeem_code = True
            self.mission_mail = True
        else:
            self.log.append("取消任务：领取兑换码奖励")
            self.mission_redeem_code = False

    def assignment_status(self):
        """Change the state of mission assignment."""
        if self.option4.isChecked():
            self.log.append("添加任务：领取派遣奖励")
            self.mission_assignments_reward = True
        else:
            self.log.append("取消任务：领取派遣奖励")
            self.mission_assignments_reward = False

    def gift_of_odyssey_status(self):
        """Change the state of mission gift of odyssey."""
        if self.option5.isChecked():
            self.log.append("添加任务：领取巡星之礼")
            self.mission_gift_of_odyssey = True
        else:
            self.log.append("取消任务：领取巡星之礼")
            self.mission_gift_of_odyssey = False

    def mail_status(self):
        """Change the state of mission mail."""
        if self.option6.isChecked():
            self.log.append("添加任务：领取邮件")
            self.mission_mail = True
        else:
            self.log.append("取消任务：领取邮件")
            self.mission_mail = False
            self.mission_redeem_code = False

    def trail_blaze_power_status(self):
        """Change the state of mission trailblaze power."""
        if self.option7.isChecked():
            self.log.append("添加任务：清开拓力")
            self.mission_trail_blaze_power = True
        else:
            self.log.append("取消任务：清开拓力")
            self.mission_trail_blaze_power = False

    def daily_training_status(self):
        """Change the state of mission daily training."""
        if self.option8.isChecked():
            self.log.append("添加任务：领取每日实训")
            self.mission_daily_training = True
        else:
            self.log.append("取消任务：领取每日实训")
            self.mission_daily_training = False

    def nameless_honor_status(self):
        """Change the state of mission nameless honor."""
        if self.option9.isChecked():
            self.log.append("添加任务：领取无名勋礼")
            self.mission_nameless_honor = True
        else:
            self.log.append("取消任务：领取无名勋礼")
            self.mission_nameless_honor = False

    def quit_game_status(self):
        """Change the state of mission quit game."""
        if self.option10.isChecked():
            self.log.append("退出游戏已启用")
            self.mission_quit_game = True
        else:
            self.log.append("退出游戏已禁用")
            self.mission_quit_game = False

    def redeem_code_setting(self):
        """Create component in redeem code setting."""
        self.redeem_code = self.redeem_code_setting_container.findChild(
            QTextEdit, "textEdit"
        )
        self.redeem_code.textChanged.connect(self.redeem_code_change)
        self.task_set_vbox_layout.addWidget(self.redeem_code_setting_container)
        self.redeem_code_setting_container.setVisible(False)

    def redeem_code_change(self):
        """Change the redeem code list while redeem code text changes."""
        redeem_code = self.redeem_code.toPlainText()
        # self.log.append(redeem_code)
        self.redeem_code_list = redeem_code.split()

    def show_redeem_code_setting(self):
        """Set redeem code visible."""
        self.display_none()
        self.redeem_code_setting_container.setVisible(True)

    def trail_blaze_power_setting(self):
        """Create component of trailblaze power."""
        self.opt1 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_1_11"
        )
        self.opt1.setChecked(self.replenish_trail_blaze_power)
        self.opt1.stateChanged.connect(self.replenish_trail_blaze_power_status)
        combobox1 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_1_13"
        )
        combobox1.addItems(["-----补充方式-----", "后备开拓力", "燃料", "星琼"])
        combobox1.currentIndexChanged.connect(self.replenish_way_select)
        combobox1.setCurrentIndex(self.replenish_way)
        times1 = self.trail_blaze_power_container.findChild(QSpinBox, "spinBox2_1_23")
        times1.setMinimum(1)
        times1.setValue(self.replenish_trail_blaze_power_run_time)
        times1.valueChanged.connect(self.replenish_trail_blaze_power_run_time_change)

        self.opt2 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_2_11"
        )
        self.opt2.setChecked(self.battle_ornament_extraction)
        self.opt2.stateChanged.connect(self.ornament_extraction_status)
        combobox2 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_2_13"
        )
        combobox2.addItems(
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
        combobox2.currentIndexChanged.connect(self.ornament_extraction_level_select)
        combobox2.setCurrentIndex(self.ornament_extraction_level)
        battle_times2 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_2_23"
        )
        battle_times2.setMinimum(1)
        battle_times2.setValue(self.ornament_extraction_run_time)
        battle_times2.valueChanged.connect(self.ornament_extraction_run_time_change)

        self.opt3 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_3_11"
        )
        self.opt3.setChecked(self.battle_calyx_golden)
        self.opt3.stateChanged.connect(self.calyx_golden_status)
        combobox3 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_3_13"
        )
        combobox3.addItems(
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
        combobox3.setCurrentIndex(self.calyx_golden_level)
        combobox3.currentIndexChanged.connect(self.calyx_golden_level_select)
        single_times3 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_3_23"
        )
        single_times3.setMinimum(1)
        single_times3.setValue(self.calyx_golden_battle_time)
        single_times3.setMaximum(6)
        single_times3.valueChanged.connect(self.calyx_golden_battle_time_change)
        battle_times3 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_3_33"
        )
        battle_times3.setMinimum(1)
        battle_times3.setValue(self.calyx_golden_run_time)
        battle_times3.valueChanged.connect(self.calyx_golden_run_time_change)

        self.opt4 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_4_11"
        )
        self.opt4.setChecked(self.battle_crimson_golden)
        self.opt4.stateChanged.connect(self.calyx_crimson_status)
        combobox4 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_4_13"
        )
        combobox4.addItems(
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
        combobox4.setCurrentIndex(self.calyx_crimson_level)
        combobox4.currentIndexChanged.connect(self.calyx_crimson_level_select)
        single_times4 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_4_23"
        )
        single_times4.setMinimum(1)
        single_times4.setValue(self.calyx_crimson_battle_time)
        single_times4.setMaximum(6)
        single_times4.valueChanged.connect(self.calyx_crimson_battle_time_change)
        battle_times4 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_4_33"
        )
        battle_times4.setMinimum(1)
        battle_times4.setValue(self.calyx_crimson_run_time)
        battle_times4.valueChanged.connect(self.calyx_crimson_run_time_change)

        self.opt5 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_5_11"
        )
        self.opt5.setChecked(self.battle_stagnant_shadow)
        self.opt5.stateChanged.connect(self.stagnant_shadow_status)
        combobox5 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_5_13"
        )
        combobox5.addItems(
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
        combobox5.setCurrentIndex(self.stagnant_shadow_level)
        combobox5.currentIndexChanged.connect(self.stagnant_shadow_level_select)
        battle_times5 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_5_23"
        )
        battle_times5.setMinimum(1)
        battle_times5.setValue(self.stagnant_shadow_run_time)
        battle_times5.valueChanged.connect(self.stagnant_shadow_run_time_change)

        self.opt6 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_6_11"
        )
        self.opt6.setChecked(self.battle_caver_of_corrosion)
        self.opt6.stateChanged.connect(self.caver_of_corrosion_status)
        combobox6 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_6_13"
        )
        combobox6.addItems(
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
        combobox6.setCurrentIndex(self.caver_of_corrosion_level)
        combobox6.currentIndexChanged.connect(self.caver_of_corrosion_level_select)
        battle_times6 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_6_23"
        )
        battle_times6.setMinimum(1)
        battle_times6.setValue(self.caver_of_corrosion_run_time)
        battle_times6.valueChanged.connect(self.caver_of_corrosion_run_time_change)

        self.opt7 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_7_11"
        )
        self.opt7.setChecked(self.battle_echo_of_war)
        self.opt7.stateChanged.connect(self.echo_of_war_status)
        combobox7 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_7_13"
        )
        combobox7.addItems(
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
        combobox7.setCurrentIndex(self.echo_of_war_level)
        combobox7.currentIndexChanged.connect(self.echo_of_war_level_select)
        battle_times7 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_7_23"
        )
        battle_times7.setMinimum(0)
        battle_times7.setMaximum(3)
        battle_times7.setValue(self.echo_of_war_run_time)
        battle_times7.valueChanged.connect(self.echo_of_war_run_time_change)

        self.task_set_vbox_layout.addWidget(self.trail_blaze_power_container)
        self.trail_blaze_power_container.setVisible(False)

    # Change series state in mission trailblaze power.
    def replenish_trail_blaze_power_status(self):
        if self.opt1.isChecked():
            self.replenish_trail_blaze_power = True
        else:
            self.replenish_trail_blaze_power = False

    def replenish_way_select(self, index):
        self.replenish_way = index

    def replenish_trail_blaze_power_run_time_change(self, value):
        self.replenish_trail_blaze_power_run_time = value

    def ornament_extraction_status(self):
        if self.opt2.isChecked():
            self.battle_ornament_extraction = True
        else:
            self.battle_ornament_extraction = False

    def ornament_extraction_level_select(self, index):
        self.ornament_extraction_level = index

    def ornament_extraction_run_time_change(self, value):
        self.ornament_extraction_run_time = value

    def calyx_golden_status(self):
        if self.opt3.isChecked():
            self.battle_calyx_golden = True
        else:
            self.battle_calyx_golden = False

    def calyx_golden_level_select(self, index):
        self.calyx_golden_level = index

    def calyx_golden_battle_time_change(self, value):
        self.calyx_golden_battle_time = value

    def calyx_golden_run_time_change(self, value):
        self.calyx_golden_run_time = value

    def calyx_crimson_status(self):
        if self.opt4.isChecked():
            self.battle_crimson_golden = True
        else:
            self.battle_crimson_golden = False

    def calyx_crimson_level_select(self, index):
        self.calyx_crimson_level = index

    def calyx_crimson_battle_time_change(self, value):
        self.calyx_crimson_battle_time = value

    def calyx_crimson_run_time_change(self, value):
        self.calyx_crimson_run_time = value

    def stagnant_shadow_status(self):
        if self.opt5.isChecked():
            self.battle_stagnant_shadow = True
        else:
            self.battle_stagnant_shadow = False

    def stagnant_shadow_level_select(self, index):
        self.stagnant_shadow_level = index

    def stagnant_shadow_run_time_change(self, value):
        self.stagnant_shadow_run_time = value

    def caver_of_corrosion_status(self):
        if self.opt6.isChecked():
            self.battle_caver_of_corrosion = True
        else:
            self.battle_caver_of_corrosion = False

    def caver_of_corrosion_level_select(self, index):
        self.caver_of_corrosion_level = index

    def caver_of_corrosion_run_time_change(self, value):
        self.caver_of_corrosion_run_time = value

    def echo_of_war_status(self, state):
        if self.opt7.isChecked():
            self.battle_echo_of_war = True
        else:
            self.battle_echo_of_war = False

    def echo_of_war_level_select(self, index):
        self.echo_of_war_level = index

    def echo_of_war_run_time_change(self, value):
        self.echo_of_war_run_time = value

    def show_trail_blaze_power_setting(self):
        self.display_none()
        self.trail_blaze_power_container.setVisible(True)

    def update_log(self, text):
        """Update the content in log area and store it in log.txt."""
        self.log.append(text)
        with open("data/log.txt", "a", encoding="utf-8") as logfile:
            logfile.write(text + "\n")

    def execute(self):
        """Save configuration, create work thread and monitor signal."""
        flags = [
            self.mission_start_game,
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
            self.button0_2.setEnabled(True)
            self.button0_1.setEnabled(False)
            configuration = {
                "gamePath": self.game_path,
                "starGame": self.mission_start_game,
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
            with open(self.AppPath + "/data/privacy.sra", "wb") as sra_file:
                sra_file.write(acc + b"\n" + pwd)
            with open(
                self.AppPath + "/data/config.json", "w", encoding="utf-8"
            ) as json_file:
                json.dump(configuration, json_file, indent=4)
            self.son_thread = StarRailAssistant.Assistant()
            self.son_thread.update_signal.connect(self.update_log)
            self.son_thread.finished.connect(self.notification)
            self.son_thread.start()

    def notification(self):
        """Windows notify"""
        self.button0_1.setEnabled(True)
        self.button0_2.setEnabled(False)
        try:
            notification.notify(
                title="SRA",
                message="任务全部完成",
                app_icon=self.AppPath + "/res/SRAicon.ico",
                timeout=10,
            )
        except Exception as e:
            with open("data/log.txt", "a", encoding="utf-8") as log:
                log.write(str(e) + "\n")

    def kill(self):
        """Kill the child thread"""
        self.son_thread.request_stop()
        self.button0_2.setEnabled(False)
        self.button0_1.setEnabled(True)
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


class SRA(QApplication):
    def __init__(self):
        super().__init__()

        self.main = Main()
        self.main.ui.show()
        QMessageBox.information(
            self.main.ui,
            "使用说明",
            "SRA崩坏：星穹铁道助手 v0.7_beta by雪影\n"
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


if __name__ == "__main__":
    if is_admin():
        app = SRA()
        app.exec()

    else:
        # 重新以管理员权限运行脚本
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        # 退出当前进程
        sys.exit()
