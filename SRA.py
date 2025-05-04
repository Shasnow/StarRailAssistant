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
import traceback

import sys
import time
from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon, QAction
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
    QGroupBox,
    QTextBrowser,
    QPushButton,
    QCheckBox,
    QVBoxLayout,
    QComboBox,
)  # 从 PySide6 中导入所需的类

from SRACore.utils import Notification, const
from SRACore.core import SRAssistant, AutoPlot
from SRACore.core.SRAssistant import VERSION, CORE
from SRACore.utils import Configure, WindowsPower, Encryption
from SRACore.utils.Dialog import (
    Announcement,
    ShutdownDialog,
    AnnouncementBoard,
    ExceptionMessageBox,
    InputDialog,
    MessageBox
)
from SRACore.utils.Plugins import PluginManager
from SRACore.utils.SRAWidgets import (
    ReceiveRewards,
    StartGame,
    TrailblazePower,
    AfterMission,
    SimulatedUniverse, Plugin, SystemTray, Hotkey, Settings,
)

# from ocr import SRAocr

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SRA")  # 修改任务栏图标

uiLoader = QUiLoader()


class Main(QWidget):
    def __init__(self, main_window: QMainWindow):
        super().__init__()
        self.main_window = main_window
        self.AppPath=const.AppPath
        # self.ocr_window=None
        self.autoplot = AutoPlot.Main()
        self.exit_SRA = False
        self.sleep = False
        self.shutdown = False
        self.isRunning = False
        Configure.init()
        self.globals = Configure.load("data/globals.json")
        current = self.globals['Config']['configList'][self.globals['Config']['currentConfig']]
        self.config = Configure.loadConfigByName(current)
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
        about_action = self.ui.findChild(QAction, "action_4")
        about_action.triggered.connect(self.about)
        # end
        # console
        self.start_game_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "checkBox1_1")
        self.setting1: QPushButton = self.ui.findChild(QPushButton, "pushButton1_1")
        self.setting1.clicked.connect(self.show_start_game_setting)

        self.trailBlazePower_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "checkBox1_2")
        self.setting2: QPushButton = self.ui.findChild(QPushButton, "pushButton1_2")
        self.setting2.clicked.connect(self.show_trail_blaze_power_setting)

        self.receive_rewards_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "checkBox1_3")
        self.setting3 = self.ui.findChild(QPushButton, "pushButton1_3")
        self.setting3.clicked.connect(self.show_receive_rewards_setting)

        self.after_mission_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "checkBox1_4")
        self.setting4 = self.ui.findChild(QPushButton, "pushButton1_4")
        self.setting4.clicked.connect(self.show_quit_game_setting)

        self.simulatedUniverse_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "checkBox1_5")
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

        self.after_mission = AfterMission(self, self.config)
        self.task_set_vbox_layout.addWidget(self.after_mission.ui)
        self.after_mission.ui.setVisible(False)

        self.simulated_universe = SimulatedUniverse(self, self.config)
        self.task_set_vbox_layout.addWidget(self.simulated_universe.ui)
        self.simulated_universe.ui.setVisible(False)

        self.extension()
        self.plugins()
        self.multi_account()

        self.software_setting()

        self.setter()

    def setter(self):
        self.start_game_checkbox.setChecked(self.config["Mission"]["startGame"])
        self.trailBlazePower_checkbox.setChecked(self.config["Mission"]["trailBlazePower"])
        self.receive_rewards_checkbox.setChecked(self.config["ReceiveRewards"]["enable"])
        self.after_mission_checkbox.setChecked(self.config["Mission"]["afterMission"])
        self.simulatedUniverse_checkbox.setChecked(self.config["Mission"]["simulatedUniverse"])
        self.switch2next_checkbox.setChecked(self.globals["Config"]["next"])

    def getter(self):
        self.config["Mission"]["startGame"] = self.start_game_checkbox.isChecked()
        self.config["Mission"]["trailBlazePower"] = self.trailBlazePower_checkbox.isChecked()
        self.config["ReceiveRewards"]["enable"] = self.receive_rewards_checkbox.isChecked()
        self.config["Mission"]["afterMission"] = self.after_mission_checkbox.isChecked()
        self.config["Mission"]["simulatedUniverse"] = self.simulatedUniverse_checkbox.isChecked()
        self.globals["Config"]["next"] = self.switch2next_checkbox.isChecked()

    def extension(self):
        auto_plot_checkbox = self.ui.findChild(QCheckBox, "autoplot_checkBox")
        auto_plot_checkbox.stateChanged.connect(self.auto_plot_status)
        # relics_identification_button:QPushButton=self.ui.findChild(QPushButton,"relicsIdentification")
        # relics_identification_button.clicked.connect(self.relics_identification)

    def plugins(self):
        PluginManager.public_ui=self.ui
        PluginManager.load_plugins()
        plugin_groupbox:QGroupBox=self.ui.findChild(QGroupBox,'plugin_groupbox')
        plugins_widget=Plugin(self)
        for name,run in PluginManager.getPlugins().items():
            plugins_widget.addPlugin(name, run)
        plugin_groupbox.layout().addWidget(plugins_widget)

    def auto_plot_status(self, state):
        if state == 2:
            self.autoplot.run_application()
        else:
            self.autoplot.quit_application()

    # def relics_identification(self):
    #     self.ocr_window=SRAocr()
    #     self.ocr_window.show()

    def multi_account(self):
        self.current_config_combobox: QComboBox = self.ui.findChild(QComboBox, "current_config")
        self.current_config_combobox.addItems(self.globals["Config"]["configList"])
        self.current_config_combobox.setCurrentIndex(self.globals["Config"]["currentConfig"])
        self.current_config_combobox.currentIndexChanged.connect(self.reloadAll)
        save_plan_button: QPushButton = self.ui.findChild(QPushButton, "save_plan")
        save_plan_button.clicked.connect(self.save_plan)
        reload_button: QPushButton = self.ui.findChild(QPushButton, "reload")
        reload_button.clicked.connect(self.reloadAll)
        new_plan_button: QPushButton = self.ui.findChild(QPushButton, "new_plan")
        new_plan_button.clicked.connect(self.new_plan)
        delete_plan_button: QPushButton = self.ui.findChild(QPushButton, "delete_plan")
        delete_plan_button.clicked.connect(self.delete_plan)
        rename_plan_button: QPushButton = self.ui.findChild(QPushButton, "rename_plan")
        rename_plan_button.clicked.connect(self.rename_plan)
        self.switch2next_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "switch2next")

    def save_plan(self):
        self.getAll()
        Configure.save(self.config, f'data/config-{self.current_config_combobox.currentText()}.json')

    @Slot()
    def reloadAll(self):
        self.config = Configure.loadConfigByName(self.current_config_combobox.currentText())
        self.globals["Config"]["currentConfig"] = self.current_config_combobox.currentIndex()
        self.setter()
        self.start_game.reload(self.config)
        self.trailblaze_power.reload(self.config)
        self.receive_rewards.reload(self.config)
        self.simulated_universe.reload(self.config)
        self.after_mission.reload(self.config)

    def new_plan(self):
        plan_name, confirm = InputDialog.getText(self.ui, "创建方案", "方案名称：")
        if confirm and plan_name:
            Configure.addConfig(plan_name)
            self.globals["Config"]["configList"].append(plan_name)
            Configure.save(self.globals, "data/globals.json")
            self.current_config_combobox.addItem(plan_name)

    def delete_plan(self):
        if len(self.globals["Config"]["configList"]) == 1:
            MessageBox.info(self.ui, "删除失败", "至少保留一个方案")
            return
        index = self.current_config_combobox.currentIndex()
        item = self.current_config_combobox.currentText()
        Encryption.remove(self.config["StartGame"]["user"])
        self.current_config_combobox.removeItem(index)
        self.globals["Config"]["configList"].remove(item)
        self.globals["Config"]["currentConfig"] = self.current_config_combobox.currentIndex()
        Configure.remove(item)

    def rename_plan(self):
        old = self.current_config_combobox.currentText()
        index = self.current_config_combobox.currentIndex()
        new, confirm = InputDialog.getText(self.ui, "重命名方案", "方案名称：")
        if confirm and new:
            Configure.rename(old, new)
            self.globals["Config"]["configList"][index] = new
            self.current_config_combobox.setItemText(index, new)

    def software_setting(self):
        setting_area:QWidget=self.ui.findChild(QWidget,"tab_2")
        setting_area.layout().addWidget(Settings(self,self.globals,self.update_log).main_ui)


    def display_none(self):
        """Sets the invisible state of the container."""
        self.start_game.ui.setVisible(False)
        self.trailblaze_power.ui.setVisible(False)
        self.receive_rewards.ui.setVisible(False)
        self.after_mission.ui.setVisible(False)
        self.simulated_universe.ui.setVisible(False)

    def show_start_game_setting(self):
        """Set start game setting visible"""
        self.display_none()
        self.start_game.ui.setVisible(True)

    def show_receive_rewards_setting(self):
        """Set redeem code visible."""
        self.display_none()
        self.receive_rewards.ui.setVisible(True)

    def show_trail_blaze_power_setting(self):
        self.display_none()
        self.trailblaze_power.ui.setVisible(True)

    def show_quit_game_setting(self):
        self.display_none()
        self.after_mission.ui.setVisible(True)

    def show_simulated_universe_setting(self):
        self.display_none()
        self.simulated_universe.ui.show()

    @Slot(str)
    def update_log(self, text):
        """Update the content in the log area."""
        self.log.append(text)

    def getAll(self):
        self.getter()
        self.start_game.getter()
        self.password_text = self.start_game.getPassword()
        self.receive_rewards.getter()
        self.trailblaze_power.getter()
        self.exit_SRA, self.shutdown, self.sleep = self.after_mission.getter()
        self.simulated_universe.getter()

    def execute(self):
        """Save configuration, create a work thread and monitor signal."""
        self.getAll()
        flags = [
            self.config["Mission"]["startGame"],
            self.config["Mission"]["trailBlazePower"],
            self.config["ReceiveRewards"]["enable"],
            self.config["Mission"]["afterMission"],
            self.config["Mission"]["simulatedUniverse"]
        ]
        if all(not flag for flag in flags):
            self.log.append("未选择任何任务")
            return

        current = self.globals['Config']['configList'][self.globals['Config']['currentConfig']]
        Configure.save(self.globals, "data/globals.json")
        if not Configure.save(self.config, f"data/config-{current}.json"):
            self.log.append("配置失败")
            return
        self.son_thread = SRAssistant.Assistant(self.password_text)
        self.son_thread.update_signal.connect(self.update_log)
        self.son_thread.finished.connect(self.missions_finished)
        self.son_thread.start()
        self.button0_2.setEnabled(True)
        self.button0_1.setEnabled(False)
        self.isRunning = True

    def missions_finished(self):
        """接收到任务完成信号后执行的工作"""
        self.notification()
        self.isRunning = False
        del self.son_thread
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
        self.button0_1.setEnabled(True)
        self.button0_2.setEnabled(False)
        if not self.globals["Notification"]["enable"]:
            return
        if self.globals["Notification"]["system"]:
            Notification.send_system_notification("SRA", "任务完成")
        if self.globals["Notification"]["email"]:
            Notification.send_mail_notification("SRA", "任务完成", self.globals["Notification"])

    def kill(self):
        """Kill the child thread"""
        self.son_thread.request_stop()
        self.button0_2.setEnabled(False)
        if self.globals["Settings"]["threadSafety"]:
            self.log.append("等待当前任务完成后停止")
        else:
            self.log.append("已停止")

    def exitSRA(self):
        self.ui.close()
        self.main_window.close()

    def notice(self):
        version = Configure.load("version.json")
        announcement_board = AnnouncementBoard(self.ui, "公告栏")
        announcement_board.add(
            Announcement(
                None,
                "更新公告",
                version["VersionUpdate"],
            )
        )
        announcement_board.add(
            Announcement(
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
            )
        )
        announcement_board.show()
        announcement_board.setDefault(0)

    def problem(self):
        MessageBox.info(
            self.ui,
            "常见问题",
            "1. 在差分宇宙中因奇物“绝对失败处方(进入战斗时，我方全体有150%的基础概率陷入冻结状态，持续1回合)”"
            "冻结队伍会导致无法开启自动战斗，建议开启游戏的沿用自动战斗设置。\n"
            "2. 游戏画面贴近或超出屏幕显示边缘时功能无法正常执行。\n"
            "3. 在执行“历战余响”时若未选择关卡，会导致程序闪退。\n"
            "关于编队：SRA现在还不会编队，对于除饰品提取以外的战斗功能，使用的是当前出战队伍\n"
            "对于饰品提取，如果没有队伍或者队伍有空位，使用的是预设编队的队伍1（不要改名）\n",
        )

    def report(self):
        MessageBox.info(
            self.ui,
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
        MessageBox.info(
            self.ui,
            "关于",
            f"版本：{VERSION}\n"
            f"内核版本：{CORE}"
        )



class SRA(QMainWindow):
    def __init__(self):
        super().__init__()

        self.system_tray=SystemTray(self)
        self.system_tray.show()
        self.main = Main(self)
        self.setCentralWidget(self.main.ui)
        self.setWindowIcon(QIcon(self.main.AppPath + "/res/SRAicon.ico"))
        self.setWindowTitle(f"SRA v{VERSION} | {PluginManager.getPluginsCount()}个插件已加载")
        size = list(map(int, self.main.globals["Settings"]["uiSize"].split("x")))
        location = list(map(int, self.main.globals["Settings"]["uiLocation"].split("x")))
        self.setGeometry(
            location[0], location[1], size[0], size[1]
        )  # 设置窗口大小与位置
        self.keyboard_listener()

    def keyboard_listener(self):
        self.hotkey=Hotkey(self.main.globals["Settings"]["hotkeys"])
        self.hotkey.start()
        self.hotkey.startOrStop.connect(self.start_status_switch)
        self.hotkey.showOrHide.connect(self.show_or_hide)
        QApplication.instance().aboutToQuit.connect(self.hotkey.stop)

    def start_status_switch(self):
        if self.main.isRunning:
            self.main.kill()
        else:
            self.main.execute()

    def show_or_hide(self):
        self.system_tray.activated.emit(self.system_tray.ActivationReason.Trigger)

    def closeEvent(self, event):
        """Save the window info"""
        # 保存窗口大小与位置
        self.main.globals["Settings"][
            "uiSize"
        ] = f"{self.geometry().width()}x{self.geometry().height()}"
        self.main.globals["Settings"][
            "uiLocation"
        ] = f"{self.geometry().x()}x{self.geometry().y()}"
        Configure.save(self.main.globals, "data/globals.json")
        # 结束残余进程
        event.accept()
        if self.main.globals["Settings"]["exitWhenClose"]:
            QApplication.quit()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def exception_hook(exc_type: type, value):
    """全局异常捕获钩子"""
    try:
        msg_box = ExceptionMessageBox(exc_type.__name__, value, traceback.format_exc())
        msg_box.exec()
    except Exception:
        # 如果连 GUI 都无法启动
        with open("error.log", "w", encoding="utf-8") as file:
            file.write(f"{exc_type}:{value}:{traceback.format_exc()}")
    finally:
        sys.exit(1)  # 确保程序退出


def main():
    if is_admin():
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
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
            window.main.notice()
        sys.exit(app.exec())

    else:
        # 重新以管理员权限运行脚本
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        # 退出当前进程
        sys.exit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        exception_hook(type(e), e)
