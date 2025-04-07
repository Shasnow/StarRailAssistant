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

from PySide6.QtGui import QIcon, QAction
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
    QGroupBox,
    QMessageBox,
    QTextBrowser,
    QPushButton,
    QCheckBox,
    QVBoxLayout,
    QTableWidget, QDoubleSpinBox, )  # 从 PySide6 中导入所需的类
from plyer import notification

from SRACore.core import SRAssistant, AutoPlot
from SRACore.core.SRAssistant import VERSION,CORE
from SRACore.utils import Configure, WindowsPower, WindowsProcess, Encryption
from SRACore.utils.Dialog import DownloadDialog, AnnouncementDialog, ShutdownDialog, AnnouncementBoard
from SRACore.utils.SRAWidgets import ReceiveRewards, StartGame, TrailblazePower, QuitGame, SimulatedUniverse

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
        self.log = self.ui.findChild(QTextBrowser, "textBrowser_log")

        # 创建中间的垂直布局管理器用于任务设置

        task_set = self.ui.findChild(QGroupBox, "groupBox_2")
        self.task_set_vbox_layout = QVBoxLayout()
        task_set.setLayout(self.task_set_vbox_layout)
        # toolbar
        notice_action = self.ui.findChild(QAction, "action_1")
        notice_action.triggered.connect(self.notice)
        problem_action = self.ui.findChild(QAction, "action_2")
        problem_action.triggered.connect(self.problem)
        report_action = self.ui.findChild(QAction, "action_3")
        report_action.triggered.connect(self.report)
        about_action=self.ui.findChild(QAction,"action_4")
        about_action.triggered.connect(self.about)
        # end
        # console
        self.start_game_checkbox:QCheckBox = self.ui.findChild(QCheckBox, "checkBox1_1")
        self.start_game_checkbox.setChecked(self.config["Mission"]["startGame"])
        self.setting1:QPushButton = self.ui.findChild(QPushButton, "pushButton1_1")
        self.setting1.clicked.connect(self.show_start_game_setting)

        self.trailBlazePower_checkbox:QCheckBox = self.ui.findChild(QCheckBox, "checkBox1_2")
        self.trailBlazePower_checkbox.setChecked(self.config["Mission"]["trailBlazePower"])
        self.setting2:QPushButton = self.ui.findChild(QPushButton, "pushButton1_2")
        self.setting2.clicked.connect(self.show_trail_blaze_power_setting)

        self.receive_rewards_checkbox:QCheckBox = self.ui.findChild(QCheckBox, "checkBox1_3")
        self.receive_rewards_checkbox.setChecked(self.config["ReceiveRewards"]["enable"])
        self.setting3 = self.ui.findChild(QPushButton, "pushButton1_3")
        self.setting3.clicked.connect(self.show_receive_rewards_setting)

        self.quit_game_checkbox:QCheckBox = self.ui.findChild(QCheckBox, "checkBox1_4")
        self.quit_game_checkbox.setChecked(self.config["Mission"]["quitGame"])
        self.setting4 = self.ui.findChild(QPushButton, "pushButton1_4")
        self.setting4.clicked.connect(self.show_quit_game_setting)

        self.simulatedUniverse_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "checkBox1_5")
        self.simulatedUniverse_checkbox.setChecked(self.config["Mission"]["simulatedUniverse"])
        self.setting5: QPushButton = self.ui.findChild(QPushButton, "pushButton1_5")
        self.setting5.clicked.connect(self.show_simulated_universe_setting)

        self.button0_1 = self.ui.findChild(QPushButton, "pushButton1_0_1")
        self.button0_1.clicked.connect(self.execute)
        self.button0_2 = self.ui.findChild(QPushButton, "pushButton1_0_2")
        self.button0_2.clicked.connect(self.kill)
        self.button0_2.setEnabled(False)
        # console end

        self.start_game = StartGame(self, self.config)
        self.task_set_vbox_layout.addWidget(self.start_game.ui)
        self.start_game.ui.setVisible(True)

        self.receive_rewards = ReceiveRewards(self, self.config)
        self.task_set_vbox_layout.addWidget(self.receive_rewards.ui)
        self.receive_rewards.ui.setVisible(False)

        self.trailblaze_power = TrailblazePower(self, self.config)
        self.task_set_vbox_layout.addWidget(self.trailblaze_power.ui)
        self.trailblaze_power.ui.setVisible(False)

        self.quit_game = QuitGame(self, self.config)
        self.task_set_vbox_layout.addWidget(self.quit_game.ui)
        self.quit_game.ui.setVisible(False)

        self.simulated_universe = SimulatedUniverse(self, self.config)
        self.task_set_vbox_layout.addWidget(self.simulated_universe.ui)
        self.simulated_universe.ui.setVisible(False)

        self.extension()

        self.software_setting()

    def get_mission(self):
        self.config["Mission"]["startGame"]=self.start_game_checkbox.isChecked()
        self.config["Mission"]["trailBlazePower"]=self.trailBlazePower_checkbox.isChecked()
        self.config["ReceiveRewards"]["enable"]=self.receive_rewards_checkbox.isChecked()
        self.config["Mission"]["quitGame"]=self.quit_game_checkbox.isChecked()
        self.config["Mission"]["simulatedUniverse"]=self.simulatedUniverse_checkbox.isChecked()

    def extension(self):
        auto_plot_checkbox = self.ui.findChild(QCheckBox, "autoplot_checkBox")
        auto_plot_checkbox.stateChanged.connect(self.auto_plot_status)
        # relics_identification_button:QPushButton=self.ui.findChild(QPushButton,"relicsIdentification")
        # relics_identification_button.clicked.connect(self.relics_identification)
        divination_button: QPushButton = self.ui.findChild(QPushButton, "pushButton_add_app_1")
        divination_button.clicked.connect(self.divination)

    def divination(self):
        if os.path.exists("res/ui/divination.ui"):
            from SRACore.extensions.FuXuanDivination import FuXuanDivination
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

        integrity_check_button:QPushButton=self.ui.findChild(QPushButton,"integrityCheck")
        integrity_check_button.clicked.connect(self.integrity_check)

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

    @staticmethod
    def integrity_check():
        command="SRAUpdater -i"
        WindowsProcess.Popen(command)

    def show_start_game_setting(self):
        """Set start game setting visible"""
        self.display_none()
        self.start_game.ui.setVisible(True)

    def display_none(self):
        """Sets the invisible state of the container."""
        self.start_game.ui.setVisible(False)
        self.trailblaze_power.ui.setVisible(False)
        self.receive_rewards.ui.setVisible(False)
        self.quit_game.ui.setVisible(False)
        self.simulated_universe.ui.setVisible(False)

    def show_receive_rewards_setting(self):
        """Set redeem code visible."""
        self.display_none()
        self.receive_rewards.ui.setVisible(True)

    def show_trail_blaze_power_setting(self):
        self.display_none()
        self.trailblaze_power.ui.setVisible(True)

    def update_log(self, text):
        """Update the content in log area."""
        self.log.append(text)

    def show_quit_game_setting(self):
        self.display_none()
        self.quit_game.ui.setVisible(True)

    def show_simulated_universe_setting(self):
        self.display_none()
        self.simulated_universe.ui.show()

    def getAll(self):
        self.get_mission()
        self.start_game.getter()
        self.password_text = self.start_game.getPassword()
        self.receive_rewards.getter()
        self.trailblaze_power.getter()
        self.exit_SRA, self.shutdown, self.sleep = self.quit_game.getter()
        self.simulated_universe.getter()

    def execute(self):
        """Save configuration, create work thread and monitor signal."""
        self.getAll()
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
            WindowsPower.schedule_shutdown(60)
            self.countdown()
        elif self.sleep:
            WindowsPower.hibernate()
        if self.exit_SRA:
            self.exitSRA()

    def countdown(self):
        """关机倒计时"""
        shutdown_dialog = ShutdownDialog(self)
        shutdown_dialog.show()

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
            with open("SRAlog.log", "a", encoding="utf-8") as log:
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
            "更新公告已移动"
            "\n感谢您对SRA的支持！")

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

    def about(self):
        QMessageBox.information(
            self,
            "关于",
            f"版本：{VERSION}\n"
            f"内核版本：{CORE}"
        )
    @staticmethod
    def clearLog():
        with open("SRAlog.log", "w", encoding="utf-8"):
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

        version = Configure.load("version.json")
        if not version["Announcement.DoNotShowAgain"]:
            announcement_board=AnnouncementBoard(window.main.ui,"公告栏")
            announcement_board.add(AnnouncementDialog(
                None,
                "长期公告",
                f"<html><i>点击下方按钮关闭公告栏</i>{version['Announcement']}"
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
                announcement_type="Announcement",icon='res/Robin.gif'))

            announcement_board.add(AnnouncementDialog(
                None, "更新公告",
                version["VersionUpdate"],
                announcement_type="VersionUpdate",
                icon='res/Robin2.gif'))
            announcement_board.show()
        sys.exit(app.exec())

    else:
        # 重新以管理员权限运行脚本
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        # 退出当前进程
        sys.exit()
