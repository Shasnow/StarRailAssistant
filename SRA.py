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
作者：雪影
图形化界面及程序主入口
"""

import ctypes
import os
import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon, QAction
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
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
    QLabel,
    QRadioButton,
    QLCDNumber,
    QTableWidget, QDoubleSpinBox, )  # 从 PySide6 中导入所需的类
from plyer import notification

from StarRailCore.core import SRAssistant, AutoPlot, SRACloud
from StarRailCore.core.SRAssistant import VERSION
from StarRailCore.utils import Configure, WindowsPower, WindowsProcess, Encryption
from StarRailCore.utils.Dialog import DownloadDialog, AnnouncementDialog

# from ocr import SRAocr

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SRA")  # 修改任务栏图标

uiLoader = QUiLoader()


class Main(QWidget):
    AppPath = os.path.dirname(os.path.realpath(sys.argv[0])).replace(
        "\\", "/"
    )  # 获取软件自身的路径

    def __init__(self, main_window: QMainWindow):
        super().__init__()
        self.main_window = main_window
        # self.ocr_window=None
        self.cloud = False
        self.autoplot = AutoPlot.Main()
        self.exit_SRA = False
        self.sleep = False
        self.shutdown = False
        Configure.init()
        Encryption.init()
        self.config = Configure.load()
        self.account_text = Encryption.load()
        self.password_text = ""
        self.ui = uiLoader.load(self.AppPath + "/res/ui/main.ui")
        self.start_game_setting_container = uiLoader.load(
            self.AppPath + "/res/ui/set_01.ui"
        )
        self.receive_rewards_setting_container = uiLoader.load(
            self.AppPath + "/res/ui/set_03.ui"
        )
        self.trail_blaze_power_container = uiLoader.load(
            self.AppPath + "/res/ui/set_07.ui"
        )
        self.quit_game_setting_container = uiLoader.load(
            self.AppPath + "/res/ui/set_10.ui"
        )
        self.simulated_universe_container = uiLoader.load(
            self.AppPath + "/res/ui/simulated_universe.ui"
        )

        self.console()
        self.start_game_setting()
        self.trail_blaze_power_setting()
        self.receive_rewards_setting()
        self.quit_game_setting()
        self.simulated_universe_setting()

        self.extension()

        self.software_setting()

    def console(self):
        """左侧控制台功能绑定"""
        # 工具栏
        notice_action = self.ui.findChild(QAction, "action_1")
        notice_action.triggered.connect(self.notice)
        problem_action = self.ui.findChild(QAction, "action_2")
        problem_action.triggered.connect(self.problem)
        report_action = self.ui.findChild(QAction, "action_3")
        report_action.triggered.connect(self.report)

        # 创建垂直布局管理器用于任务设置
        self.task_set_vbox_layout = QVBoxLayout()
        task_set = self.ui.findChild(QGroupBox, "groupBox_2")
        task_set.setLayout(self.task_set_vbox_layout)

        self.log = self.ui.findChild(QTextBrowser, "textBrowser_log")

        self.option1 = self.ui.findChild(QCheckBox, "checkBox1_1")
        self.option1.setChecked(self.config["Mission"]["startGame"])
        self.option1.stateChanged.connect(self.start_game_status)
        button1 = self.ui.findChild(QPushButton, "pushButton1_1")
        button1.clicked.connect(self.show_start_game_setting)

        self.option7 = self.ui.findChild(QCheckBox, "checkBox1_2")
        self.option7.setChecked(self.config["Mission"]["trailBlazePower"])
        self.option7.stateChanged.connect(self.trail_blaze_power_status)
        button7 = self.ui.findChild(QPushButton, "pushButton1_2")
        button7.clicked.connect(self.show_trail_blaze_power_setting)

        self.option3 = self.ui.findChild(QCheckBox, "checkBox1_3")
        self.option3.setChecked(self.config["ReceiveRewards"]["enable"])
        self.option3.stateChanged.connect(self.receive_rewards_status)
        button3 = self.ui.findChild(QPushButton, "pushButton1_3")
        button3.clicked.connect(self.show_receive_rewards_setting)

        self.option10 = self.ui.findChild(QCheckBox, "checkBox1_4")
        self.option10.setChecked(self.config["Mission"]["quitGame"])
        self.option10.stateChanged.connect(self.quit_game_status)
        button10 = self.ui.findChild(QPushButton, "pushButton1_4")
        button10.clicked.connect(self.show_quit_game_setting)

        option11: QCheckBox = self.ui.findChild(QCheckBox, "checkBox1_5")
        option11.setChecked(self.config["Mission"]["simulatedUniverse"])
        option11.stateChanged.connect(self.simulated_universe_status)
        button11: QPushButton = self.ui.findChild(QPushButton, "pushButton1_5")
        button11.clicked.connect(self.show_simulated_universe_setting)

        self.button0_1 = self.ui.findChild(QPushButton, "pushButton1_0_1")
        self.button0_1.clicked.connect(self.execute)
        self.button0_2 = self.ui.findChild(QPushButton, "pushButton1_0_2")
        self.button0_2.clicked.connect(self.kill)
        self.button0_2.setEnabled(False)

    def receive_rewards_setting(self):
        self.option2 = self.receive_rewards_setting_container.findChild(
            QCheckBox, "checkBox3_1"
        )
        self.option2.setChecked(self.config["Mission"]["trailBlazerProfile"])
        self.option2.stateChanged.connect(self.trailblazer_profile_status)

        self.option4 = self.receive_rewards_setting_container.findChild(
            QCheckBox, "checkBox3_2"
        )
        self.option4.setChecked(self.config["Mission"]["assignment"])
        self.option4.stateChanged.connect(self.assignment_status)

        self.option6 = self.receive_rewards_setting_container.findChild(
            QCheckBox, "checkBox3_3"
        )
        self.option6.setChecked(self.config["Mission"]["mail"])
        self.option6.stateChanged.connect(self.mail_status)

        self.option8 = self.receive_rewards_setting_container.findChild(
            QCheckBox, "checkBox3_4"
        )
        self.option8.setChecked(self.config["Mission"]["dailyTraining"])
        self.option8.stateChanged.connect(self.daily_training_status)

        self.option9 = self.receive_rewards_setting_container.findChild(
            QCheckBox, "checkBox3_5"
        )
        self.option9.setChecked(self.config["Mission"]["namelessHonor"])
        self.option9.stateChanged.connect(self.nameless_honor_status)

        self.option5 = self.receive_rewards_setting_container.findChild(
            QCheckBox, "checkBox3_6"
        )
        self.option5.setChecked(self.config["Mission"]["giftOfOdyssey"])
        self.option5.stateChanged.connect(self.gift_of_odyssey_status)

        self.option3 = self.receive_rewards_setting_container.findChild(
            QCheckBox, "checkBox3_7"
        )
        self.option3.setChecked(self.config["Mission"]["redeemCode"])
        self.option3.stateChanged.connect(self.redeem_code_status)

        self.redeem_code = self.receive_rewards_setting_container.findChild(
            QTextEdit, "textEdit"
        )
        self.redeem_code.setText("\n".join(self.config["RedeemCode"]["codeList"]))
        self.redeem_code.textChanged.connect(self.redeem_code_change)
        self.task_set_vbox_layout.addWidget(self.receive_rewards_setting_container)
        self.receive_rewards_setting_container.setVisible(False)

    def extension(self):
        auto_plot_checkbox = self.ui.findChild(QCheckBox, "autoplot_checkBox")
        auto_plot_checkbox.stateChanged.connect(self.auto_plot_status)
        # relics_identification_button:QPushButton=self.ui.findChild(QPushButton,"relicsIdentification")
        # relics_identification_button.clicked.connect(self.relics_identification)
        divination_button: QPushButton = self.ui.findChild(QPushButton, "pushButton_add_app_1")
        divination_button.clicked.connect(self.divination)

    def divination(self):
        if os.path.exists("res/ui/divination.ui"):
            from StarRailCore.utils.FuXuanDivination import FuXuanDivination
            div = FuXuanDivination(self)
            div.ui.show()
        else:
            download = DownloadDialog(self, "大衍穷观阵",
                                      "https://gitee.com/yukikage/StarRailAssistant/releases/download/divination/divination.zip")
            download.show()

    def auto_plot_status(self, state):
        if state == 2:
            self.autoplot.run_application()
        else:
            self.autoplot.quit_application()

    # def relics_identification(self):
    #     self.ocr_window=SRAocr()
    #     self.ocr_window.show()

    def software_setting(self):
        self.key_table = self.ui.findChild(QTableWidget, "tableWidget")
        self.key_setting_show()
        self.key_table.cellChanged.connect(self.key_setting_change)
        save_button = self.ui.findChild(QPushButton, "pushButton_save")
        save_button.clicked.connect(self.key_setting_save)
        reset_button = self.ui.findChild(QPushButton, "pushButton_reset")
        reset_button.clicked.connect(self.key_setting_reset)

        startup_checkbox = self.ui.findChild(QCheckBox, "checkBox_ifStartUp")
        startup_checkbox.setChecked(self.config["Settings"]["startup"])
        startup_checkbox.stateChanged.connect(self.startup)

        auto_update_checkbox = self.ui.findChild(QCheckBox, "checkBox_ifAutoUpdate")
        auto_update_checkbox.stateChanged.connect(self.auto_update)
        auto_update_checkbox.setChecked(self.config["Settings"]["autoUpdate"])

        thread_safety_checkbox = self.ui.findChild(QCheckBox, "checkBox_threadSafety")
        thread_safety_checkbox.setChecked(self.config["Settings"]["threadSafety"])
        thread_safety_checkbox.stateChanged.connect(self.thread_safety)

        clear_log_button: QPushButton = self.ui.findChild(QPushButton, "clearLog")
        clear_log_button.clicked.connect(self.clearLog)

        confidence_spin_box: QDoubleSpinBox = self.ui.findChild(QDoubleSpinBox, "confidenceSpinBox")
        confidence_spin_box.setValue(self.config["Settings"]["confidence"])
        confidence_spin_box.valueChanged.connect(self.confidence_changed)

        zoom_spinbox: QDoubleSpinBox = self.ui.findChild(QDoubleSpinBox, "zoomSpinBox")
        zoom_spinbox.setValue(self.config["Settings"]["zoom"])
        zoom_spinbox.valueChanged.connect(self.zoom_changed)

    def key_setting_save(self):
        Configure.save(self.config)

    def key_setting_show(self):
        settings = self.config["Settings"]
        for i in range(4):
            self.key_table.item(0, i).setText(settings["F" + str(i + 1)])

    def key_setting_reset(self):
        for i in range(4):
            self.key_table.item(0, i).setText("f" + str(i + 1))

    def key_setting_change(self):
        for i in range(4):
            self.config["Settings"]["F" + str(i + 1)] = self.key_table.item(0, i).text()

    def startup(self, state):
        if state == 2:
            WindowsProcess.set_startup_item("SRA", self.AppPath + "/SRA.exe")
            self.config["Settings"]["startup"] = True
        else:
            WindowsProcess.delete_startup_item("SRA")
            self.config["Settings"]["startup"] = False
        Configure.save(self.config)

    def auto_update(self, state):
        if state == 2:
            if os.path.exists("SRAUpdater.exe"):
                WindowsProcess.Popen("SRAUpdater.exe")
            else:
                self.update_log("缺少文件SRAUpdater.exe 无法自动更新")
            self.config["Settings"]["autoUpdate"] = True
        else:
            self.config["Settings"]["autoUpdate"] = False
        Configure.save(self.config)

    def thread_safety(self, state):
        if state == 2:
            self.config["Settings"]["threadSafety"] = True
        else:
            self.config["Settings"]["threadSafety"] = False
        Configure.save(self.config)

    def confidence_changed(self, value):
        self.config["Settings"]["confidence"] = value
        Configure.save(self.config)

    def zoom_changed(self, value):
        self.config["Settings"]["zoom"] = value
        Configure.save(self.config)

    def start_game_setting(self):
        channel_combobox = self.start_game_setting_container.findChild(
            QComboBox, "comboBox2_1"
        )
        channel_combobox.setCurrentIndex(self.config["StartGame"]["channel"])
        channel_combobox.currentIndexChanged.connect(self.channel_change)
        use_launcher_checkbox: QCheckBox = self.start_game_setting_container.findChild(
            QCheckBox, "checkBox2_4"
        )
        use_launcher_checkbox.setChecked(self.config["StartGame"]["launcher"])
        use_launcher_checkbox.stateChanged.connect(self.use_launcher)

        # cloud_game_checkbox = self.start_game_setting_container.findChild(
        #     QCheckBox, "cloud_game"
        # )
        # cloud_game_checkbox.stateChanged.connect(self.use_cloud_game)

        self.path_text: QTextEdit = self.start_game_setting_container.findChild(QLabel, "label2_2")
        self.path_text.setText("启动器路径：" if self.config["StartGame"]["launcher"] else "游戏路径：")
        self.line_area = self.start_game_setting_container.findChild(
            QLineEdit, "lineEdit2_2"
        )
        self.line_area.setText(self.config["StartGame"]["gamePath"])
        self.line_area.textChanged.connect(self.get_path)

        button = self.start_game_setting_container.findChild(
            QPushButton, "pushButton2_2"
        )
        button.clicked.connect(self.open_file)

        self.auto_launch_checkbox: QCheckBox = self.start_game_setting_container.findChild(
            QCheckBox, "checkBox2_3"
        )
        self.auto_launch_checkbox.setChecked(self.config["StartGame"]["autoLogin"])
        self.auto_launch_checkbox.stateChanged.connect(self.auto_launch)
        self.account = self.start_game_setting_container.findChild(
            QLineEdit, "lineEdit2_4_12"
        )
        self.account.setText(self.account_text)
        self.account.setReadOnly(True)
        self.account.textChanged.connect(self.get_account)
        self.password = self.start_game_setting_container.findChild(
            QLineEdit, "lineEdit2_4_22"
        )
        # self.password.setText(self.password_text)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setReadOnly(True)
        self.password.textChanged.connect(self.get_password)
        self.show_button = self.start_game_setting_container.findChild(
            QPushButton, "pushButton2_3"
        )
        self.show_button.clicked.connect(self.togglePasswordVisibility)
        self.task_set_vbox_layout.addWidget(self.start_game_setting_container)
        self.start_game_setting_container.setVisible(True)

    def show_start_game_setting(self):
        """Set start game setting visible"""
        self.display_none()
        self.start_game_setting_container.setVisible(True)

    def channel_change(self, index):
        self.config["StartGame"]["channel"] = index

    def use_launcher(self, state):
        if state:
            self.path_text.setText("启动器路径：")
            self.config["StartGame"]["launcher"] = True
            self.config["StartGame"]["pathType"] = "launcher"
        else:
            self.path_text.setText("游戏路径：")
            self.config["StartGame"]["launcher"] = False
            self.config["StartGame"]["pathType"] = "StarRail"

    def use_cloud_game(self, state):
        if state:
            self.cloud = True
        else:
            self.cloud = False

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "可执行文件 (*.exe)"
        )
        if file_name:
            self.line_area.setText(file_name)
            self.config["StartGame"]["gamePath"] = file_name

    def get_path(self, text):
        self.config["StartGame"]["gamePath"] = text

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
            self.config["StartGame"]["autoLogin"] = True
            self.account.setReadOnly(False)
            self.password.setReadOnly(False)
        else:
            self.log.append("自动登录已禁用")
            self.config["StartGame"]["autoLogin"] = False
            self.account.setReadOnly(True)
            self.password.setReadOnly(True)

    def togglePasswordVisibility(self):
        """Toggle password visibility"""
        if self.password.echoMode() == QLineEdit.EchoMode.Password:
            self.password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_button.setText("隐藏")
        else:
            self.password.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_button.setText("显示")

    def display_none(self):
        """Sets the invisible state of the container."""
        self.start_game_setting_container.setVisible(False)
        self.trail_blaze_power_container.setVisible(False)
        self.receive_rewards_setting_container.setVisible(False)
        self.quit_game_setting_container.setVisible(False)
        self.simulated_universe_container.setVisible(False)

    def start_game_status(self):
        """Change the state of mission start game."""
        if self.option1.isChecked():
            self.log.append("启动游戏已启用")
            self.config["Mission"]["startGame"] = True
        else:
            self.log.append("启动游戏已禁用")
            self.config["Mission"]["startGame"] = False

    def receive_rewards_status(self, state):
        if state == 2:
            self.config["ReceiveRewards"]["enable"] = True
        else:
            self.config["ReceiveRewards"]["enable"] = False

    def trailblazer_profile_status(self):
        """Change the state of mission trailblazer profile."""
        if self.option2.isChecked():
            self.log.append("添加任务：领取签证奖励")
            self.config["Mission"]["trailBlazerProfile"] = True
        else:
            self.log.append("取消任务：领取签证奖励")
            self.config["Mission"]["trailBlazerProfile"] = False

    def redeem_code_status(self):
        """Change the state of mission redeem code."""
        if self.option3.isChecked():
            self.log.append("添加任务：领取兑换码奖励")
            self.config["Mission"]["redeemCode"] = True
            self.config["Mission"]["mail"] = True
        else:
            self.log.append("取消任务：领取兑换码奖励")
            self.config["Mission"]["redeemCode"] = False

    def assignment_status(self):
        """Change the state of mission assignment."""
        if self.option4.isChecked():
            self.log.append("添加任务：领取派遣奖励")
            self.config["Mission"]["assignment"] = True
        else:
            self.log.append("取消任务：领取派遣奖励")
            self.config["Mission"]["assignment"] = False

    def gift_of_odyssey_status(self):
        """Change the state of mission gift of odyssey."""
        if self.option5.isChecked():
            self.log.append("添加任务：领取巡星之礼")
            self.config["Mission"]["giftOfOdyssey"] = True
        else:
            self.log.append("取消任务：领取巡星之礼")
            self.config["Mission"]["giftOfOdyssey"] = False

    def mail_status(self):
        """Change the state of mission mail."""
        if self.option6.isChecked():
            self.log.append("添加任务：领取邮件")
            self.config["Mission"]["mail"] = True
        else:
            self.log.append("取消任务：领取邮件")
            self.config["Mission"]["mail"] = False
            self.config["Mission"]["redeemCode"] = False

    def trail_blaze_power_status(self):
        """Change the state of mission trailblaze power."""
        if self.option7.isChecked():
            self.log.append("添加任务：清开拓力")
            self.config["Mission"]["trailBlazePower"] = True
        else:
            self.log.append("取消任务：清开拓力")
            self.config["Mission"]["trailBlazePower"] = False

    def daily_training_status(self):
        """Change the state of mission daily training."""
        if self.option8.isChecked():
            self.log.append("添加任务：领取每日实训")
            self.config["Mission"]["dailyTraining"] = True
        else:
            self.log.append("取消任务：领取每日实训")
            self.config["Mission"]["dailyTraining"] = False

    def nameless_honor_status(self):
        """Change the state of mission nameless honor."""
        if self.option9.isChecked():
            self.log.append("添加任务：领取无名勋礼")
            self.config["Mission"]["namelessHonor"] = True
        else:
            self.log.append("取消任务：领取无名勋礼")
            self.config["Mission"]["namelessHonor"] = False

    def quit_game_status(self):
        """Change the state of mission quit game."""
        if self.option10.isChecked():
            self.log.append("退出游戏已启用")
            self.config["Mission"]["quitGame"] = True
        else:
            self.log.append("退出游戏已禁用")
            self.config["Mission"]["quitGame"] = False

    def simulated_universe_status(self, state):
        if state == 2:
            self.config["Mission"]["simulatedUniverse"] = True
        else:
            self.config["Mission"]["simulatedUniverse"] = False

    def redeem_code_change(self):
        """Change the redeem code list while redeem code text changes."""
        redeem_code = self.redeem_code.toPlainText()
        self.config["RedeemCode"]["codeList"] = redeem_code.split()

    def show_receive_rewards_setting(self):
        """Set redeem code visible."""
        self.display_none()
        self.receive_rewards_setting_container.setVisible(True)

    def trail_blaze_power_setting(self):
        """Create component of trailblaze power."""
        self.opt1 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_1_11"
        )
        self.opt1.setChecked(self.config["Replenish"]["enable"])
        self.opt1.stateChanged.connect(self.replenish_trail_blaze_power_status)
        combobox1 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_1_13"
        )
        combobox1.setCurrentIndex(self.config["Replenish"]["way"])
        combobox1.currentIndexChanged.connect(self.replenish_way_select)
        times1 = self.trail_blaze_power_container.findChild(QSpinBox, "spinBox2_1_23")
        times1.setValue(self.config["Replenish"]["runTimes"])
        times1.valueChanged.connect(self.replenish_trail_blaze_power_run_time_change)

        self.opt2 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_2_11"
        )
        self.opt2.setChecked(self.config["OrnamentExtraction"]["enable"])
        self.opt2.stateChanged.connect(self.ornament_extraction_status)
        combobox2 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_2_13"
        )
        combobox2.currentIndexChanged.connect(self.ornament_extraction_level_select)
        combobox2.setCurrentIndex(self.config["OrnamentExtraction"]["level"])
        battle_times2 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_2_23"
        )
        battle_times2.setValue(self.config["OrnamentExtraction"]["runTimes"])
        battle_times2.valueChanged.connect(self.ornament_extraction_run_time_change)

        self.opt3 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_3_11"
        )
        self.opt3.setChecked(self.config["CalyxGolden"]["enable"])
        self.opt3.stateChanged.connect(self.calyx_golden_status)
        combobox3 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_3_13"
        )
        combobox3.setCurrentIndex(self.config["CalyxGolden"]["level"])
        combobox3.currentIndexChanged.connect(self.calyx_golden_level_select)
        single_times3 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_3_23"
        )
        single_times3.setValue(self.config["CalyxGolden"]["singleTimes"])
        single_times3.valueChanged.connect(self.calyx_golden_battle_time_change)
        battle_times3 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_3_33"
        )
        battle_times3.setValue(self.config["CalyxGolden"]["runTimes"])
        battle_times3.valueChanged.connect(self.calyx_golden_run_time_change)

        self.opt4 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_4_11"
        )
        self.opt4.setChecked(self.config["CalyxCrimson"]["enable"])
        self.opt4.stateChanged.connect(self.calyx_crimson_status)
        combobox4 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_4_13"
        )
        combobox4.setCurrentIndex(self.config["CalyxCrimson"]["level"])
        combobox4.currentIndexChanged.connect(self.calyx_crimson_level_select)
        single_times4 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_4_23"
        )
        single_times4.setValue(self.config["CalyxCrimson"]["singleTimes"])
        single_times4.valueChanged.connect(self.calyx_crimson_battle_time_change)
        battle_times4 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_4_33"
        )
        battle_times4.setValue(self.config["CalyxCrimson"]["runTimes"])
        battle_times4.valueChanged.connect(self.calyx_crimson_run_time_change)

        self.opt5 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_5_11"
        )
        self.opt5.setChecked(self.config["StagnantShadow"]["enable"])
        self.opt5.stateChanged.connect(self.stagnant_shadow_status)
        combobox5 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_5_13"
        )
        combobox5.setCurrentIndex(self.config["StagnantShadow"]["level"])
        combobox5.currentIndexChanged.connect(self.stagnant_shadow_level_select)
        battle_times5 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_5_23"
        )
        battle_times5.setValue(self.config["StagnantShadow"]["runTimes"])
        battle_times5.valueChanged.connect(self.stagnant_shadow_run_time_change)

        self.opt6 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_6_11"
        )
        self.opt6.setChecked(self.config["CaverOfCorrosion"]["enable"])
        self.opt6.stateChanged.connect(self.caver_of_corrosion_status)
        combobox6 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_6_13"
        )
        combobox6.setCurrentIndex(self.config["CaverOfCorrosion"]["level"])
        combobox6.currentIndexChanged.connect(self.caver_of_corrosion_level_select)
        battle_times6 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_6_23"
        )
        battle_times6.setValue(self.config["CaverOfCorrosion"]["runTimes"])
        battle_times6.valueChanged.connect(self.caver_of_corrosion_run_time_change)

        self.opt7 = self.trail_blaze_power_container.findChild(
            QCheckBox, "checkBox2_7_11"
        )
        self.opt7.setChecked(self.config["EchoOfWar"]["enable"])
        self.opt7.stateChanged.connect(self.echo_of_war_status)
        combobox7 = self.trail_blaze_power_container.findChild(
            QComboBox, "comboBox2_7_13"
        )
        combobox7.setCurrentIndex(self.config["EchoOfWar"]["level"])
        combobox7.currentIndexChanged.connect(self.echo_of_war_level_select)
        battle_times7 = self.trail_blaze_power_container.findChild(
            QSpinBox, "spinBox2_7_23"
        )
        battle_times7.setValue(self.config["EchoOfWar"]["runTimes"])
        battle_times7.valueChanged.connect(self.echo_of_war_run_time_change)

        self.task_set_vbox_layout.addWidget(self.trail_blaze_power_container)
        self.trail_blaze_power_container.setVisible(False)

    # Change series state in mission trailblaze power.
    def replenish_trail_blaze_power_status(self):
        if self.opt1.isChecked():
            self.config["Replenish"]["enable"] = True
        else:
            self.config["Replenish"]["enable"] = False

    def replenish_way_select(self, index):
        self.config["Replenish"]["way"] = index

    def replenish_trail_blaze_power_run_time_change(self, value):
        self.config["Replenish"]["runTimes"] = value

    def ornament_extraction_status(self):
        if self.opt2.isChecked():
            self.config["OrnamentExtraction"]["enable"] = True
        else:
            self.config["OrnamentExtraction"]["enable"] = False

    def ornament_extraction_level_select(self, index):
        self.config["OrnamentExtraction"]["level"] = index

    def ornament_extraction_run_time_change(self, value):
        self.config["OrnamentExtraction"]["runTimes"] = value

    def calyx_golden_status(self):
        if self.opt3.isChecked():
            self.config["CalyxGolden"]["enable"] = True
        else:
            self.config["CalyxGolden"]["enable"] = False

    def calyx_golden_level_select(self, index):
        self.config["CalyxGolden"]["level"] = index

    def calyx_golden_battle_time_change(self, value):
        self.config["CalyxGolden"]["singleTimes"] = value

    def calyx_golden_run_time_change(self, value):
        self.config["CalyxGolden"]["runTimes"] = value

    def calyx_crimson_status(self):
        if self.opt4.isChecked():
            self.config["CalyxCrimson"]["enable"] = True
        else:
            self.config["CalyxCrimson"]["enable"] = False

    def calyx_crimson_level_select(self, index):
        self.config["CalyxCrimson"]["level"] = index

    def calyx_crimson_battle_time_change(self, value):
        self.config["CalyxCrimson"]["singleTimes"] = value

    def calyx_crimson_run_time_change(self, value):
        self.config["CalyxCrimson"]["runTimes"] = value

    def stagnant_shadow_status(self):
        if self.opt5.isChecked():
            self.config["StagnantShadow"]["enable"] = True
        else:
            self.config["StagnantShadow"]["enable"] = False

    def stagnant_shadow_level_select(self, index):
        self.config["StagnantShadow"]["level"] = index

    def stagnant_shadow_run_time_change(self, value):
        self.config["StagnantShadow"]["runTimes"] = value

    def caver_of_corrosion_status(self):
        if self.opt6.isChecked():
            self.config["CaverOfCorrosion"]["enable"] = True
        else:
            self.config["CaverOfCorrosion"]["enable"] = False

    def caver_of_corrosion_level_select(self, index):
        self.config["CaverOfCorrosion"]["level"] = index

    def caver_of_corrosion_run_time_change(self, value):
        self.config["CaverOfCorrosion"]["runTimes"] = value

    def echo_of_war_status(self):
        if self.opt7.isChecked():
            self.config["EchoOfWar"]["enable"] = True
        else:
            self.config["EchoOfWar"]["enable"] = False

    def echo_of_war_level_select(self, index):
        self.config["EchoOfWar"]["level"] = index

    def echo_of_war_run_time_change(self, value):
        self.config["EchoOfWar"]["runTimes"] = value

    def show_trail_blaze_power_setting(self):
        self.display_none()
        self.trail_blaze_power_container.setVisible(True)

    def update_log(self, text):
        """Update the content in log area."""
        self.log.append(text)

    def quit_game_setting(self):
        self.quit_game_setting_container.setVisible(False)
        exit_checkbox = self.quit_game_setting_container.findChild(
            QCheckBox, "checkBox2_1_1"
        )
        exit_checkbox.stateChanged.connect(self.exit_SRA_status)
        self.radio_button1 = self.quit_game_setting_container.findChild(
            QRadioButton, "radioButton2_1_2"
        )
        self.radio_button2 = self.quit_game_setting_container.findChild(
            QRadioButton, "radioButton2_1_3"
        )
        self.radio_button1.toggled.connect(self.shutdown_status)
        self.radio_button2.toggled.connect(self.sleep_status)
        self.task_set_vbox_layout.addWidget(self.quit_game_setting_container)

    def show_quit_game_setting(self):
        self.display_none()
        self.quit_game_setting_container.setVisible(True)

    def exit_SRA_status(self, state):
        if state == 2:
            self.exit_SRA = True
        else:
            self.exit_SRA = False

    def shutdown_status(self, checked):
        self.shutdown = checked

    def sleep_status(self, checked):
        self.sleep = checked

    def simulated_universe_setting(self):
        mode_combobox: QComboBox = self.simulated_universe_container.findChild(QComboBox, "game_mode")
        mode_combobox.setCurrentIndex(self.config["DivergentUniverse"]["mode"])
        mode_combobox.currentIndexChanged.connect(self.mode_change)

        times_spinbox: QSpinBox = self.simulated_universe_container.findChild(QSpinBox, "times")
        times_spinbox.setValue(self.config["DivergentUniverse"]["times"])
        times_spinbox.valueChanged.connect(self.times_change)

        self.task_set_vbox_layout.addWidget(self.simulated_universe_container)
        self.simulated_universe_container.setVisible(False)

    def show_simulated_universe_setting(self):
        self.display_none()
        self.simulated_universe_container.show()

    def mode_change(self, index):
        self.config["DivergentUniverse"]["mode"] = index

    def times_change(self, value):
        self.config["DivergentUniverse"]["times"] = value

    def execute(self):
        """Save configuration, create work thread and monitor signal."""
        flags = [
            self.config["Mission"]["startGame"],
            self.config["Mission"]["trailBlazePower"],
            self.config["ReceiveRewards"]["enable"],
            self.config["Mission"]["quitGame"],
            self.config["Mission"]["simulatedUniverse"]
        ]
        if all(not flag for flag in flags):
            self.log.append("未选择任何任务")
            return
        if self.config["CloudGame"]["firstly"] and self.cloud:
            if self.account_text == "" or self.password_text == "":
                self.log.append(
                    "首次使用云·星穹铁道，必须勾选自动登录并填入有效的账号密码"
                )
                return
            self.config["CloudGame"]["firstly"] = False
        Encryption.save(self.account_text)
        if not Configure.save(self.config):
            self.log.append("配置失败")
            return
        if self.cloud:
            self.son_thread = SRACloud.SRACloud(self.password_text)
        else:
            self.son_thread = SRAssistant.Assistant(self.password_text)
        self.son_thread.update_signal.connect(self.update_log)
        self.son_thread.finished.connect(self.missions_finished)
        self.son_thread.start()
        self.button0_2.setEnabled(True)
        self.button0_1.setEnabled(False)

    def missions_finished(self):
        """接收到任务完成信号后执行的工作"""
        self.notification()
        # if not self.config["Mission"]["quitGame"]:
        #     return
        if self.shutdown:
            WindowsPower.schedule_shutdown(61)
            self.countdown()
        elif self.sleep:
            WindowsPower.hibernate()
        if self.exit_SRA:
            self.exitSRA()

    def countdown(self):
        """关机倒计时"""
        self.shutdown_dialog = uiLoader.load("res/ui/shutdown_dialog.ui")
        self.shutdown_dialog.setWindowTitle("关机")
        self.shutdown_dialog.setWindowIcon(QIcon(self.AppPath + "/res/SRAicon.ico"))
        cancel_button = self.shutdown_dialog.findChild(QPushButton, "pushButton")
        cancel_button.clicked.connect(WindowsPower.shutdown_cancel)
        cancel_button.clicked.connect(self.shutdown_dialog.close)
        self.timer = QTimer(self)
        cancel_button.clicked.connect(self.timer.stop)
        self.lease_time = self.shutdown_dialog.findChild(QLCDNumber, "lcdNumber")
        self.timer.timeout.connect(self.update_countdown)
        self.time_left = 59
        self.timer.start(1000)
        self.shutdown_dialog.show()

    def update_countdown(self):
        """更新倒计时"""
        self.time_left -= 1
        if self.time_left < 0:
            self.timer.stop()
            self.lease_time.display(00)
            self.shutdown_dialog.close()  # 显示00表示倒计时结束
        else:
            self.lease_time.display(self.time_left)

    def notification(self):
        """Windows notify"""
        self.button0_1.setEnabled(True)
        self.button0_2.setEnabled(False)
        try:
            notification.notify(
                title="SRA",
                message="任务全部完成",
                app_icon=self.AppPath + "/res/SRAicon.ico",
                timeout=5,
            )
        except Exception as e:
            with open("SRAlog.txt", "a", encoding="utf-8") as log:
                log.write(str(e) + "\n")

    def kill(self):
        """Kill the child thread"""
        self.son_thread.request_stop()
        self.button0_2.setEnabled(False)
        if self.config["Settings"]["threadSafety"]:
            self.log.append("等待当前任务完成后停止")
        else:
            self.log.append("已停止")

    def exitSRA(self):
        self.ui.close()
        self.main_window.close()

    def notice(self):
        QMessageBox.information(
            self,
            "更新公告",
            "\n感谢您对SRA的支持！",
        )

    def problem(self):
        QMessageBox.information(
            self,
            "常见问题",
            "1. 在差分宇宙中因奇物“绝对失败处方(进入战斗时，我方全体有150%的基础概率陷入冻结状态，持续1回合)”"
            "冻结队伍会导致无法开启自动战斗，建议开启游戏的沿用自动战斗设置。\n"
            "2. 游戏画面贴近或超出屏幕显示边缘时功能无法正常执行。\n"
            "3. 在执行“历战余响”时若未选择关卡，会导致程序闪退。\n"
            "关于编队：SRA现在还不会编队，对于除饰品提取以外的战斗功能，使用的是当前出战队伍\n"
            "对于饰品提取，如果没有队伍或者队伍有空位，使用的是预设编队的队伍1（不要改名）\n",
        )

    def report(self):
        QMessageBox.information(
            self,
            "问题反馈",
            "反馈渠道：\n"
            "   B站：https://space.bilibili.com/349682013\n"
            "   QQ邮箱：yukikage@qq.com\n"
            "   QQ群：994571792\n"
            "反馈须知：\n"
            "    向开发者反馈问题时，除问题描述外，\n"
            "    请给出所使用软件的版本号以及日志文件",
        )

    @staticmethod
    def clearLog():
        with open("SRAlog.txt", "w", encoding="utf-8"):
            pass


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


class SRA(QMainWindow):
    def __init__(self):
        super().__init__()


        self.main = Main(self)
        self.setCentralWidget(self.main.ui)
        self.setWindowIcon(QIcon(self.main.AppPath + "/res/SRAicon.ico"))
        self.setWindowTitle("SRA v" + VERSION)
        size = list(map(int, self.main.config["Settings"]["uiSize"].split("x")))
        location = list(map(int, self.main.config["Settings"]["uiLocation"].split("x")))
        self.setGeometry(
            location[0], location[1], size[0], size[1]
        )  # 设置窗口大小与位置

    def closeEvent(self, event):
        """Save the windows info"""
        # 保存窗口大小与位置
        self.main.config["Settings"][
            "uiSize"
        ] = f"{self.geometry().width()}x{self.geometry().height()}"
        self.main.config["Settings"][
            "uiLocation"
        ] = f"{self.geometry().x()}x{self.geometry().y()}"
        Configure.save(self.main.config)
        # 结束残余进程
        self.main.exitSRA()

        event.accept()


if __name__ == "__main__":
    if is_admin():
        app = QApplication(sys.argv)
        start_time = time.time()
        window = SRA()
        window.show()
        end_time = time.time()
        total_time = end_time - start_time
        window.main.update_log(
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) +
            " 程序启动成功，耗时" + f"{total_time:.2f}s")

        version=Configure.load("version.json")
        if not version["Announcement.DoNotShowAgain"]:
            announcement = AnnouncementDialog(window.main.ui,
                "公告",
                f"<html><i>滚动至底部关闭此公告</i>{version['Announcement']}"
                "<h4>长期公告</h4>"
                f"<h2>SRA崩坏：星穹铁道助手 v{VERSION} by雪影</h2>"
                "<h3>使用说明：</h3>"
                "<b>重要！推荐调整游戏分辨率为1920*1080并保持游戏窗口无遮挡，注意不要让游戏窗口超出屏幕<br>"
                "重要！执行任务时不要进行其他操作！<br></b>"
                "<p>声明：本程序<font color='green'>完全免费</font>，仅供学习交流使用。本程序依靠计算机图像识别和模拟操作运行，"
                "不会做出任何修改游戏文件、读写游戏内存等任何危害游戏本体的行为。"
                "如果您使用此程序，我们认为您充分了解《米哈游游戏使用许可及服务协议》第十条之规定，"
                "您在使用此程序中产生的任何问题（除程序错误导致外）与此程序无关，<b>相应的后果由您自行承担</b>。</p>"
                "请不要在崩坏：星穹铁道及米哈游在各平台（包括但不限于：米游社、B站、微博）的官方动态下讨论任何关于 SRA 的内容。<br>"
                "人话：不要跳脸官方～(∠・ω&lt; )⌒☆</html>",
                                              "Announcement")
            announcement.show()

        if not version["VersionUpdate.DoNotShowAgain"]:
            version_update= AnnouncementDialog(window.main.ui, "更新公告", version["VersionUpdate"], "VersionUpdate")
            version_update.show()
        sys.exit(app.exec())

    else:
        # 重新以管理员权限运行脚本
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        # 退出当前进程
        sys.exit()
