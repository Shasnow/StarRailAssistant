import os
import shutil

import keyboard
import schedule
import time
from PySide6.QtCore import Slot, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QAction
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMenu, QWidget, QCheckBox, QTextEdit, QComboBox, QLineEdit, \
    QPushButton, QLabel, QFileDialog, \
    QSpinBox, QRadioButton, QVBoxLayout, QSystemTrayIcon, QApplication, QTableWidget, QDoubleSpinBox, QScrollArea, \
    QGroupBox, QFrame, QMainWindow, QTextBrowser

import SRACore.utils.Logger
from SRACore.core import AutoPlot, SRAssistant
from SRACore.utils import Encryption, Configure, WindowsProcess, Notification, WindowsPower
from SRACore.utils.Dialog import MessageBox, InputDialog, ShutdownDialog, AnnouncementBoard, Announcement, \
    ScheduleDialog
from SRACore.utils.Logger import logger
from SRACore.utils.Plugins import PluginManager
from SRACore.utils.const import *

uiLoader = QUiLoader()


def convert_to_html(text):
    lines = text.split('\n')

    html_content = []

    for line in lines:
        line = line.strip()
        if not line:  # 跳过空行
            continue
        if line.endswith('：') or line.endswith(':'):
            section_title = line.replace('：', '').replace(':', '')
            html_content.append(f'<h3>{section_title}</h3>')
            continue
        if line.startswith(tuple(f'{i}.' for i in range(1, 100))):
            item_content = line[line.find('.') + 1:].strip()
            html_content.append(f'<li>{item_content}</li>')
    if html_content:
        final_html = []
        i = 0
        while i < len(html_content):
            if html_content[i].startswith('<h3>'):
                final_html.append(html_content[i])
                ul_content = []
                j = i + 1
                while j < len(html_content) and not html_content[j].startswith('<h3>'):
                    ul_content.append(html_content[j])
                    j += 1
                if ul_content:
                    final_html.append('<ol>')
                    final_html.extend(ul_content)
                    final_html.append('</ol>')
                i = j
            else:
                i += 1
        final_html.append('<br>')
        return ''.join(final_html)
    else:
        return "<p>没有可转换的内容</p>"


class SRA(QMainWindow):
    def __init__(self):
        super().__init__()
        self.main = Main(self)
        self.setCentralWidget(self.main.ui)
        self.setWindowIcon(QIcon(self.main.AppPath + "/res/SRAicon.ico"))
        self.setWindowTitle(f"SRA v{VERSION} | {PluginManager.getPluginsCount()}个插件已加载")
        size = list(map(int, self.main.globals["Settings"]["uiSize"].split("x")))
        location = list(map(int, self.main.globals["Settings"]["uiLocation"].split("x")))
        self.setGeometry(
            location[0], location[1], size[0], size[1]
        )  # 设置窗口大小与位置
        self.system_tray = SystemTray(self)
        self.system_tray.show()
        self.keyboard_listener()

    def keyboard_listener(self):
        self.hotkey = BackgroundEvent(**self.main.globals["Settings"])
        self.hotkey.start()
        self.hotkey.startOrStop.connect(self.start_status_switch)
        self.hotkey.showOrHide.connect(self.show_or_hide)
        self.hotkey.isTimeToRun.connect(self.schedule_run)
        QApplication.instance().aboutToQuit.connect(self.hotkey.stop)

    @Slot(str)
    def schedule_run(self, config):
        logger.info("定时任务触发")
        if not self.main.isRunning:
            self.main.execute_with_config(config)

    @Slot()
    def start_status_switch(self):
        if self.main.isRunning:
            self.main.kill()
        else:
            self.main.execute()

    @Slot()
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


class SRAWidget(QWidget):
    def __init__(self, parent, config: dict):
        super().__init__(parent)
        self.config = config

    def setter(self):
        raise NotImplementedError("Subclasses must implement setter method.")

    def connector(self):
        raise NotImplementedError("Subclasses must implement method.")

    def getter(self):
        raise NotImplementedError("Subclasses must implement getter method.")

    def reload(self, config):
        self.config = config
        self.setter()


class Main(QWidget):
    def __init__(self, main_window: QMainWindow):
        super().__init__()
        self.son_thread = None
        self.main_window = main_window
        self.AppPath = AppPath
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
        SRACore.utils.Logger.logger.add(self.update_log, level=20,
                                        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
                                        colorize=False)

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

        self.multi_account_widget = MultiAccount(self, self.globals)
        multi_account_area: QWidget = self.ui.findChild(QWidget, "tab_4")
        multi_account_area.layout().addWidget(self.multi_account_widget.main_ui)

        self.extension()

        self.software_setting()

        self.setter()
        self.plugins()

    def setter(self):
        self.start_game_checkbox.setChecked(self.config["Mission"]["startGame"])
        self.trailBlazePower_checkbox.setChecked(self.config["Mission"]["trailBlazePower"])
        self.receive_rewards_checkbox.setChecked(self.config["ReceiveRewards"]["enable"])
        self.after_mission_checkbox.setChecked(self.config["Mission"]["afterMission"])
        self.simulatedUniverse_checkbox.setChecked(self.config["Mission"]["simulatedUniverse"])

    def getter(self):
        self.config["Mission"]["startGame"] = self.start_game_checkbox.isChecked()
        self.config["Mission"]["trailBlazePower"] = self.trailBlazePower_checkbox.isChecked()
        self.config["ReceiveRewards"]["enable"] = self.receive_rewards_checkbox.isChecked()
        self.config["Mission"]["afterMission"] = self.after_mission_checkbox.isChecked()
        self.config["Mission"]["simulatedUniverse"] = self.simulatedUniverse_checkbox.isChecked()

    def extension(self):
        auto_plot_checkbox:QCheckBox = self.ui.findChild(QCheckBox, "autoplot_checkBox")
        auto_plot_checkbox.stateChanged.connect(self.auto_plot_status)
        self.autoplot.interrupted.connect(lambda :auto_plot_checkbox.setChecked(False))
        # relics_identification_button:QPushButton=self.ui.findChild(QPushButton,"relicsIdentification")
        # relics_identification_button.clicked.connect(self.relics_identification)

    def plugins(self):
        PluginManager.public_ui = self.ui
        PluginManager.public_instance = self
        PluginManager.load_plugins()
        plugin_groupbox: QGroupBox = self.ui.findChild(QGroupBox, 'plugin_groupbox')
        plugins_widget = Plugin(self)
        for name, run in PluginManager.getPlugins().items():
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

    def software_setting(self):
        setting_area: QWidget = self.ui.findChild(QWidget, "tab_2")
        setting_area.layout().addWidget(Settings(self, self.globals, self.update_log).main_ui)

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
        self.multi_account_widget.getter()

    @Slot()
    def reloadAll(self):
        name, index = self.multi_account_widget.currentConfig()
        self.config = Configure.loadConfigByName(name)
        self.globals["Config"]["currentConfig"] = index
        self.setter()
        self.start_game.reload(self.config)
        self.trailblaze_power.reload(self.config)
        self.receive_rewards.reload(self.config)
        self.simulated_universe.reload(self.config)
        self.after_mission.reload(self.config)

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

    def execute_with_config(self, config: str):
        self.son_thread = SRAssistant.Assistant(self.password_text, config)
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
        QApplication.instance().exit()

    def notice(self):
        version = Configure.load("version.json")
        announcement_board = AnnouncementBoard(self.ui, "公告栏")
        announcement_board.add(
            Announcement(
                None,
                "更新公告",
                f"<b>版本已更新 v{version['version']}</b>"
                f"{convert_to_html(version['announcement'])}"
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
            "<a href='https://shasnow.github.io/SRA/faq.html'>常见问题自查</a><br><br>"
            "1. 在差分宇宙中因奇物“绝对失败处方(进入战斗时，我方全体有150%的基础概率陷入冻结状态，持续1回合)”"
            "冻结队伍会导致无法开启自动战斗，建议开启游戏的沿用自动战斗设置。\n"
            "2. 游戏画面贴近或超出屏幕显示边缘时功能无法正常执行。\n"
            "3. 在执行“历战余响”时若未选择关卡，会导致程序闪退。\n"
            "关于编队：SRA现在还不会编队，对于除饰品提取以外的战斗功能，使用的是当前出战队伍\n"
            "对于饰品提取，如果没有队伍或者队伍有空位，使用的是预设编队的队伍1（不要改名）\n"
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


class ReceiveRewards(SRAWidget):
    def __init__(self, parent, config: dict):
        super().__init__(parent, config)
        self.ui = uiLoader.load("res/ui/set_03.ui")
        self.option1: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox3_1"
        )
        self.option2: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox3_2"
        )
        self.option3: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox3_3"
        )
        self.option4: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox3_4"
        )
        self.option5: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox3_5"
        )
        self.option6: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox3_6"
        )
        self.option7: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox3_7"
        )
        self.redeem_code: QTextEdit = self.ui.findChild(
            QTextEdit, "textEdit"
        )
        self.setter()

    def setter(self):
        self.option1.setChecked(self.config["Mission"]["trailBlazerProfile"])
        self.option2.setChecked(self.config["Mission"]["assignment"])
        self.option3.setChecked(self.config["Mission"]["mail"])
        self.option4.setChecked(self.config["Mission"]["dailyTraining"])
        self.option5.setChecked(self.config["Mission"]["namelessHonor"])
        self.option6.setChecked(self.config["Mission"]["giftOfOdyssey"])
        self.option7.setChecked(self.config["Mission"]["redeemCode"])
        self.redeem_code.setText("\n".join(self.config["RedeemCode"]["codeList"]))

    def connector(self):
        pass

    def getter(self):
        self.config["Mission"]["trailBlazerProfile"] = self.option1.isChecked()
        self.config["Mission"]["assignment"] = self.option2.isChecked()
        self.config["Mission"]["mail"] = self.option3.isChecked()
        self.config["Mission"]["dailyTraining"] = self.option4.isChecked()
        self.config["Mission"]["namelessHonor"] = self.option5.isChecked()
        self.config["Mission"]["giftOfOdyssey"] = self.option6.isChecked()
        self.config["Mission"]["redeemCode"] = self.option7.isChecked()
        self.config["RedeemCode"]["codeList"] = self.redeem_code.toPlainText().split()


class StartGame(SRAWidget):
    def __init__(self, parent, config: dict):
        super().__init__(parent, config)
        self.ui = uiLoader.load("res/ui/set_01.ui")
        self.account_text = None
        self.password_text = None
        self.channel_combobox: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_1"
        )
        self.use_launcher_checkbox: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox2_4"
        )
        self.path_text: QLabel = self.ui.findChild(QLabel, "label2_2")
        self.line_area: QLineEdit = self.ui.findChild(
            QLineEdit, "lineEdit2_2"
        )
        self.file_select_button: QPushButton = self.ui.findChild(
            QPushButton, "pushButton2_2"
        )
        self.auto_launch_checkbox: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox2_3"
        )
        self.account: QLineEdit = self.ui.findChild(
            QLineEdit, "lineEdit2_4_12"
        )
        self.password: QLineEdit = self.ui.findChild(
            QLineEdit, "lineEdit2_4_22"
        )
        self.show_button: QPushButton = self.ui.findChild(
            QPushButton, "pushButton2_3"
        )
        self.save_pwd_checkbox: QCheckBox = self.ui.findChild(
            QCheckBox, "save_pwd"
        )
        self.setter()
        self.connector()

    def setter(self):
        if self.config["StartGame"]["user"] == '':
            self.config["StartGame"]["user"] = Encryption.new()
        user = Encryption.load(self.config['StartGame']['user'])
        self.account_text = user.account
        self.password_text = user.password
        self.channel_combobox.setCurrentIndex(self.config["StartGame"]["channel"])
        self.use_launcher_checkbox.setChecked(self.config["StartGame"]["launcher"])
        self.path_text.setText("启动器路径：" if self.config["StartGame"]["launcher"] else "游戏路径：")
        self.line_area.setText(self.config["StartGame"]["gamePath"])
        self.auto_launch_checkbox.setChecked(self.config["StartGame"]["autoLogin"])
        self.account.setText(self.account_text)
        self.password.setText(self.password_text)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.save_pwd_checkbox.setChecked(self.config["StartGame"]["savePassword"])

    def connector(self):
        self.use_launcher_checkbox.stateChanged.connect(self.use_launcher)
        self.file_select_button.clicked.connect(self.open_file)
        self.show_button.clicked.connect(self.togglePasswordVisibility)

    def getter(self):
        self.config["StartGame"]["channel"] = self.channel_combobox.currentIndex()
        self.config["StartGame"]["autoLogin"] = self.auto_launch_checkbox.isChecked()
        self.config["StartGame"]["gamePath"] = self.line_area.text()
        self.config["StartGame"]["savePassword"] = self.save_pwd_checkbox.isChecked()
        self.account_text = self.account.text()
        self.password_text = self.password.text()
        if not self.config["StartGame"]["savePassword"]:
            self.password_text = ''
        Encryption.save(self.account_text, self.password_text, self.config["StartGame"]["user"])

    def getPassword(self):
        return self.password.text()

    @Slot()
    def use_launcher(self, state):
        if state:
            self.path_text.setText("启动器路径：")
            self.config["StartGame"]["launcher"] = True
            self.config["StartGame"]["pathType"] = "launcher"
        else:
            self.path_text.setText("游戏路径：")
            self.config["StartGame"]["launcher"] = False
            self.config["StartGame"]["pathType"] = "StarRail"

    @Slot()
    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "可执行文件 (*.exe)"
        )
        if file_name:
            self.line_area.setText(file_name)

    @Slot()
    def togglePasswordVisibility(self):
        """Toggle password visibility"""
        if self.password.echoMode() == QLineEdit.EchoMode.Password:
            self.password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_button.setText("隐藏")
        else:
            self.password.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_button.setText("显示")


class TrailblazePower(SRAWidget):
    class TaskItem(QListWidgetItem):
        def __init__(self, name, level, level_text, run_times, single_time):
            super().__init__()
            self.name = name
            self.level = level
            self.level_text = level_text
            self.run_times = run_times
            self.single_times = single_time
            self.setText(f"{name} \n关卡：{level_text} \n运行次数：{run_times} \n单次次数：{single_time}")

        def tojson(self):
            return {
                "name": self.name,
                "args": {
                    "level": self.level,
                    "levelText": self.level_text,
                    "runTimes": self.run_times,
                    "singleTimes": self.single_times
                }}

        @staticmethod
        def fromjson(data: dict):
            return TrailblazePower.TaskItem(
                data["name"],
                data["args"]["level"],
                data["args"]["levelText"],
                data["args"]["runTimes"],
                data["args"]["singleTimes"]
            )

    def __init__(self, parent, config: dict):
        super().__init__(parent, config)
        self.ui = uiLoader.load("res/ui/set_07.ui")
        self.opt1: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox2_1_11"
        )
        self.combobox1: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_1_13"
        )
        self.times1: QSpinBox = self.ui.findChild(QSpinBox, "spinBox2_1_23")
        self.use_assist_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "useAssist")
        self.change_lineup_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "changeLineup")
        self.ornament_extraction_addbutton: QPushButton = self.ui.findChild(QPushButton, "ornamentExtractionAddButton")
        self.combobox2: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_2_13"
        )
        self.battle_times2: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_2_23"
        )
        self.calyx_golden_addbutton: QPushButton = self.ui.findChild(QPushButton, "calyxGoldenAddButton")
        self.combobox3: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_3_13"
        )
        self.single_times3: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_3_23"
        )
        self.battle_times3: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_3_33"
        )
        self.calyx_crimson_addbutton: QPushButton = self.ui.findChild(QPushButton, "calyxCrimsonAddButton")
        self.combobox4: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_4_13"
        )
        self.single_times4: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_4_23"
        )
        self.battle_times4: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_4_33"
        )
        self.stagnant_shadow_addbutton: QPushButton = self.ui.findChild(QPushButton, "stagnantShadowAddButton")
        self.combobox5: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_5_13"
        )
        self.battle_times5: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_5_23"
        )
        self.caver_of_corrosion_addbutton: QPushButton = self.ui.findChild(QPushButton, "caverOfCorrosionAddButton")
        self.combobox6: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_6_13"
        )
        self.battle_times6: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_6_23"
        )
        self.echo_of_war_addbutton: QPushButton = self.ui.findChild(QPushButton, "echoOfWarAddButton")
        self.combobox7: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_7_13"
        )
        self.battle_times7: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_7_23"
        )
        self.list_widget: QListWidget = self.ui.findChild(QListWidget, "listWidget")
        self.setter()
        self.connector()

    def setter(self):
        self.opt1.setChecked(self.config["Replenish"]["enable"])
        self.combobox1.setCurrentIndex(self.config["Replenish"]["way"])
        self.times1.setValue(self.config["Replenish"]["runTimes"])
        self.use_assist_checkbox.setChecked(self.config["Support"]["enable"])
        self.change_lineup_checkbox.setChecked(self.config["Support"]['changeLineup'])
        self.combobox2.setCurrentIndex(self.config["OrnamentExtraction"]["level"])
        self.battle_times2.setValue(self.config["OrnamentExtraction"]["runTimes"])
        self.combobox3.setCurrentIndex(self.config["CalyxGolden"]["level"])
        self.single_times3.setValue(self.config["CalyxGolden"]["singleTimes"])
        self.battle_times3.setValue(self.config["CalyxGolden"]["runTimes"])
        self.combobox4.setCurrentIndex(self.config["CalyxCrimson"]["level"])
        self.single_times4.setValue(self.config["CalyxCrimson"]["singleTimes"])
        self.battle_times4.setValue(self.config["CalyxCrimson"]["runTimes"])
        self.combobox5.setCurrentIndex(self.config["StagnantShadow"]["level"])
        self.battle_times5.setValue(self.config["StagnantShadow"]["runTimes"])
        self.combobox6.setCurrentIndex(self.config["CaverOfCorrosion"]["level"])
        self.battle_times6.setValue(self.config["CaverOfCorrosion"]["runTimes"])
        self.combobox7.setCurrentIndex(self.config["EchoOfWar"]["level"])
        self.battle_times7.setValue(self.config["EchoOfWar"]["runTimes"])
        self.list_widget.clear()
        for task in self.config["TrailBlazePower"]["taskList"]:
            self.list_widget.addItem(TrailblazePower.TaskItem.fromjson(task))

    def getter(self):
        self.config["Replenish"]["enable"] = self.opt1.isChecked()
        self.config["Replenish"]["way"] = self.combobox1.currentIndex()
        self.config["Replenish"]["runTimes"] = self.times1.value()
        self.config["Support"]["enable"] = self.use_assist_checkbox.isChecked()
        self.config["Support"]['changeLineup'] = self.change_lineup_checkbox.isChecked()
        self.config["OrnamentExtraction"]["level"] = self.combobox2.currentIndex()
        self.config["OrnamentExtraction"]["runTimes"] = self.battle_times2.value()
        self.config["CalyxGolden"]["level"] = self.combobox3.currentIndex()
        self.config["CalyxGolden"]["singleTimes"] = self.single_times3.value()
        self.config["CalyxGolden"]["runTimes"] = self.battle_times3.value()
        self.config["CalyxCrimson"]["level"] = self.combobox4.currentIndex()
        self.config["CalyxCrimson"]["singleTimes"] = self.single_times4.value()
        self.config["CalyxCrimson"]["runTimes"] = self.battle_times4.value()
        self.config["StagnantShadow"]["level"] = self.combobox5.currentIndex()
        self.config["StagnantShadow"]["runTimes"] = self.battle_times5.value()
        self.config["CaverOfCorrosion"]["level"] = self.combobox6.currentIndex()
        self.config["CaverOfCorrosion"]["runTimes"] = self.battle_times6.value()
        self.config["EchoOfWar"]["level"] = self.combobox7.currentIndex()
        self.config["EchoOfWar"]["runTimes"] = self.battle_times7.value()

        self.config["TrailBlazePower"]["taskList"].clear()
        for i in range(self.list_widget.count()):
            task: TrailblazePower.TaskItem | QListWidgetItem = self.list_widget.item(i)
            self.config["TrailBlazePower"]["taskList"].append(task.tojson())

    def connector(self):
        self.ornament_extraction_addbutton.clicked.connect(self.add_ornament_extraction)
        self.calyx_golden_addbutton.clicked.connect(self.add_calyx_golden)
        self.calyx_crimson_addbutton.clicked.connect(self.add_calyx_crimson)
        self.stagnant_shadow_addbutton.clicked.connect(self.add_stagnant_shadow)
        self.caver_of_corrosion_addbutton.clicked.connect(self.add_caver_of_corrosion)
        self.echo_of_war_addbutton.clicked.connect(self.add_echo_of_war)
        self.list_widget.itemDoubleClicked.connect(self.remove_item)

    def add_task(self, name, level, level_text, run_times, single_times=1):
        task = self.TaskItem(name, level, level_text, run_times, single_times)
        self.list_widget.addItem(task)

    def add_ornament_extraction(self):
        self.add_task("饰品提取",
                      self.combobox2.currentIndex(),
                      self.combobox2.currentText(),
                      self.battle_times2.value())

    def add_calyx_golden(self):
        self.add_task("拟造花萼（金）",
                      self.combobox3.currentIndex(),
                      self.combobox3.currentText(),
                      self.battle_times3.value(),
                      self.single_times3.value())

    def add_calyx_crimson(self):
        self.add_task("拟造花萼（赤）",
                      self.combobox4.currentIndex(),
                      self.combobox4.currentText(),
                      self.battle_times4.value(),
                      self.single_times4.value())

    def add_stagnant_shadow(self):
        self.add_task("凝滞虚影",
                      self.combobox5.currentIndex(),
                      self.combobox5.currentText(),
                      self.battle_times5.value())

    def add_caver_of_corrosion(self):
        self.add_task("侵蚀隧洞",
                      self.combobox6.currentIndex(),
                      self.combobox6.currentText(),
                      self.battle_times6.value())

    def add_echo_of_war(self):
        self.add_task("历战余响",
                      self.combobox7.currentIndex(),
                      self.combobox7.currentText(),
                      self.battle_times7.value())

    @Slot(QListWidgetItem)
    def remove_item(self, item):
        index = self.list_widget.row(item)
        self.list_widget.takeItem(index)


class AfterMission(SRAWidget):
    def __init__(self, parent, config: dict):
        super().__init__(parent, config)
        self.ui = uiLoader.load("res/ui/set_10.ui")
        self.logout_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "log_out")
        self.quit_game_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "quit_game")
        self.exit_checkbox: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox2_1_1"
        )
        self.radio_button1: QRadioButton = self.ui.findChild(
            QRadioButton, "radioButton2_1_2"
        )
        self.radio_button2: QRadioButton = self.ui.findChild(
            QRadioButton, "radioButton2_1_3"
        )
        self.setter()

    def setter(self):
        self.logout_checkbox.setChecked(self.config["AfterMission"]["logout"])
        self.quit_game_checkbox.setChecked(self.config["AfterMission"]["quitGame"])

    def connector(self):
        pass

    def getter(self):
        self.config["AfterMission"]["logout"] = self.logout_checkbox.isChecked()
        self.config["AfterMission"]["quitGame"] = self.quit_game_checkbox.isChecked()
        return self.exit_checkbox.isChecked(), self.radio_button1.isChecked(), self.radio_button2.isChecked()


class SimulatedUniverse(SRAWidget):
    def __init__(self, parent, config: dict):
        super().__init__(parent, config)
        self.ui = uiLoader.load("res/ui/simulated_universe.ui")
        self.mode_combobox: QComboBox = self.ui.findChild(QComboBox, "game_mode")
        self.times_spinbox: QSpinBox = self.ui.findChild(QSpinBox, "times")
        self.policy_checkbox: QComboBox = self.ui.findChild(QComboBox, 'policy_comboBox')
        self.setter()

    def setter(self):
        self.mode_combobox.setCurrentIndex(self.config["DivergentUniverse"]["mode"])
        self.times_spinbox.setValue(self.config["DivergentUniverse"]["times"])
        self.policy_checkbox.setCurrentIndex(self.config["DivergentUniverse"]["policy"])

    def getter(self):
        self.config["DivergentUniverse"]["mode"] = self.mode_combobox.currentIndex()
        self.config["DivergentUniverse"]["times"] = self.times_spinbox.value()
        self.config["DivergentUniverse"]["policy"] = self.policy_checkbox.currentIndex()


class MultiAccount(SRAWidget):
    def __init__(self, parent: Main, config: dict):
        super().__init__(parent, config)
        self.globals = self.config
        self.parent = parent
        self.ui = uiLoader.load("res/ui/multi_account.ui")
        self.main_ui = self.ui.findChild(QScrollArea, "scrollArea")
        self.current_config_combobox: QComboBox = self.ui.findChild(QComboBox, "current_config")
        self.current_config_combobox.addItems(self.globals["Config"]["configList"])
        self.current_config_combobox.setCurrentIndex(self.globals["Config"]["currentConfig"])
        self.current_config_combobox.currentIndexChanged.connect(self.parent.reloadAll)
        save_plan_button: QPushButton = self.ui.findChild(QPushButton, "save_plan")
        save_plan_button.clicked.connect(self.save_plan)
        reload_button: QPushButton = self.ui.findChild(QPushButton, "reload")
        reload_button.clicked.connect(self.parent.reloadAll)
        new_plan_button: QPushButton = self.ui.findChild(QPushButton, "new_plan")
        new_plan_button.clicked.connect(self.new_plan)
        delete_plan_button: QPushButton = self.ui.findChild(QPushButton, "delete_plan")
        delete_plan_button.clicked.connect(self.delete_plan)
        rename_plan_button: QPushButton = self.ui.findChild(QPushButton, "rename_plan")
        rename_plan_button.clicked.connect(self.rename_plan)
        self.switch2next_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "switch2next")
        self.switch2next_checkbox.setChecked(self.globals["Config"]["next"])

    def getter(self):
        self.globals["Config"]["next"] = self.switch2next_checkbox.isChecked()

    def save_plan(self):
        self.parent.getAll()
        Configure.save(self.parent.config, f'data/config-{self.current_config_combobox.currentText()}.json')

    def new_plan(self):
        if self.current_config_combobox.count() == self.current_config_combobox.maxCount():
            MessageBox.info(self, "添加失败", "配置方案已达最大数量！")
            return
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
        Encryption.remove(self.parent.config["StartGame"]["user"])
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

    def currentConfig(self):
        return self.current_config_combobox.currentText(), self.current_config_combobox.currentIndex()

    @staticmethod
    def getConfigs():
        """获取所有配置方案"""
        return Configure.load("data/globals.json")["Config"]["configList"]


class Plugin(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setLayout(QVBoxLayout(self))
        self.setFont(QFont("MicroSoft YaHei", 13))

    def addPlugin(self, name, slot):
        button = QPushButton(name)
        button.clicked.connect(slot)
        self.layout().addWidget(button)


class Settings(SRAWidget):
    def __init__(self, parent, config: dict, update_log):
        super().__init__(parent, config)
        self.update_log = update_log
        self.ui = uiLoader.load("res/ui/settings_page.ui")
        self.main_ui = self.ui.findChild(QScrollArea, "scrollArea")
        self.globals = self.config
        self.schedule_list: QListWidget = self.ui.findChild(QListWidget, "schedule_list")
        self.schedule_add_button: QPushButton = self.ui.findChild(QPushButton, "schedule_add_button")
        self.key_table = self.ui.findChild(QTableWidget, "tableWidget")
        self.save_button = self.ui.findChild(QPushButton, "pushButton_save")
        self.reset_button = self.ui.findChild(QPushButton, "pushButton_reset")
        self.hotkey_setting_groupbox: QGroupBox = self.ui.findChild(QGroupBox, "hotkey_setting")
        self.hotkey_lineedit1: QLineEdit = self.ui.findChild(QLineEdit, "hotkey1")
        self.hotkey_lineedit2: QLineEdit = self.ui.findChild(QLineEdit, "hotkey2")
        self.notification_allow_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "notification_allow")
        self.system_notification_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "system_notification")
        self.email_notification_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "mail_notification")
        self.email_notification_frame: QFrame = self.ui.findChild(QFrame, "mail_notification_frame")
        self.SMTP_server: QLineEdit = self.ui.findChild(QLineEdit, "smtp_server")
        self.sender_email: QLineEdit = self.ui.findChild(QLineEdit, "sender_email")
        self.authorization_code: QLineEdit = self.ui.findChild(QLineEdit, "authorization_code")
        self.receiver_email: QLineEdit = self.ui.findChild(QLineEdit, "receiver_email")
        self.email_check_cutton: QPushButton = self.ui.findChild(QPushButton, "email_check_button")
        self.startup_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "checkBox_ifStartUp")

        auto_update_checkbox = self.ui.findChild(QCheckBox, "checkBox_ifAutoUpdate")
        auto_update_checkbox.stateChanged.connect(self.auto_update)
        auto_update_checkbox.setChecked(self.globals["Settings"]["autoUpdate"])

        self.thread_safety_checkbox = self.ui.findChild(QCheckBox, "checkBox_threadSafety")
        self.confidence_spin_box: QDoubleSpinBox = self.ui.findChild(QDoubleSpinBox, "confidenceSpinBox")
        self.zoom_spinbox: QDoubleSpinBox = self.ui.findChild(QDoubleSpinBox, "zoomSpinBox")
        self.performance_spinbox: QDoubleSpinBox = self.ui.findChild(QDoubleSpinBox, "performanceSpinBox")
        self.mirrorchyanCDK: QLineEdit = self.ui.findChild(
            QLineEdit, "lineEdit_mirrorchyanCDK"
        )

        self.integrity_check_button: QPushButton = self.ui.findChild(
            QPushButton, "integrityCheck"
        )
        self.exit_when_close_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "exit_when_close")
        self.setter()
        self.connector()

    def setter(self):
        settings = self.globals["Settings"]
        for sc in settings["scheduleList"]:
            self.schedule_list.addItem("".join(sc))
        for i in range(4):
            self.key_table.item(0, i).setText(settings["F" + str(i + 1)])
        self.hotkey_lineedit1.setText(self.globals["Settings"]["hotkeys"][0])
        self.hotkey_lineedit2.setText(self.globals["Settings"]["hotkeys"][1])
        self.notification_allow_checkbox.setChecked(self.globals["Notification"]["enable"])
        self.system_notification_checkbox.setChecked(self.globals["Notification"]["system"])
        self.email_notification_checkbox.setChecked(self.globals["Notification"]["email"])
        self.email_notification_frame.setVisible(self.globals["Notification"]["email"])
        self.SMTP_server.setText(self.globals["Notification"]["SMTP"])
        self.sender_email.setText(self.globals["Notification"]["sender"])
        authorizeCode = self.globals["Notification"]["authorizationCode"]
        if authorizeCode != '':
            authorizeCode = Encryption.win_decryptor(authorizeCode)
        self.authorization_code.setText(authorizeCode)
        self.receiver_email.setText(self.globals["Notification"]["receiver"])

        self.startup_checkbox.setChecked(self.globals["Settings"]["startup"])
        self.thread_safety_checkbox.setChecked(self.globals["Settings"]["threadSafety"])
        self.confidence_spin_box.setValue(self.globals["Settings"]["confidence"])
        self.zoom_spinbox.setValue(self.globals["Settings"]["zoom"])
        self.performance_spinbox.setValue(self.globals["Settings"]["performance"])
        self.mirrorchyanCDK.setText(
            Encryption.win_decryptor(self.globals["Settings"]["mirrorchyanCDK"])
        )
        self.exit_when_close_checkbox.setChecked(self.globals["Settings"]["exitWhenClose"])

    def connector(self):
        self.schedule_list.itemDoubleClicked.connect(self.remove_schedule)
        self.schedule_add_button.clicked.connect(self.add_schedule)
        self.key_table.cellChanged.connect(self.key_setting_change)
        self.save_button.clicked.connect(self.key_setting_save)
        self.reset_button.clicked.connect(self.key_setting_reset)
        self.hotkey_lineedit1.editingFinished.connect(self.hotkey_change)
        self.hotkey_lineedit2.editingFinished.connect(self.hotkey_change)
        self.notification_allow_checkbox.stateChanged.connect(self.notification_status_change)
        self.system_notification_checkbox.stateChanged.connect(self.notification_status_change)
        self.email_notification_checkbox.stateChanged.connect(self.notification_status_change)
        self.email_check_cutton.clicked.connect(self.email_check)
        self.startup_checkbox.stateChanged.connect(self.startup)
        self.thread_safety_checkbox.stateChanged.connect(self.thread_safety)
        self.confidence_spin_box.valueChanged.connect(self.confidence_changed)
        self.zoom_spinbox.valueChanged.connect(self.zoom_changed)
        self.performance_spinbox.valueChanged.connect(self.performance_changed)
        self.mirrorchyanCDK.textChanged.connect(self.mirrorchyanCDK_changed)
        self.integrity_check_button.clicked.connect(self.integrity_check)
        self.exit_when_close_checkbox.stateChanged.connect(self.exit_when_close)

    def add_schedule(self):
        sc = ScheduleDialog.getSchedule(self, MultiAccount.getConfigs())
        if sc is not None:
            self.globals["Settings"]["scheduleList"].append(sc)
            self.schedule_list.addItem("".join(sc))

    @Slot(QListWidgetItem)
    def remove_schedule(self, item):
        index = self.schedule_list.row(item)
        self.schedule_list.takeItem(index)
        del self.globals["Settings"]["scheduleList"][index]

    def key_setting_save(self):
        Configure.save(self.globals, 'data/globals.json')

    def key_setting_reset(self):
        for i in range(4):
            self.key_table.item(0, i).setText("f" + str(i + 1))

    def key_setting_change(self):
        for i in range(4):
            self.globals["Settings"]["F" + str(i + 1)] = self.key_table.item(0, i).text()

    @Slot()
    def hotkey_change(self):
        text1 = self.hotkey_lineedit1.text()
        text2 = self.hotkey_lineedit2.text()
        if self.globals["Settings"]["hotkeys"][0] != text1 or self.globals["Settings"]["hotkeys"][1] != text2:
            self.globals["Settings"]["hotkeys"][0] = text1
            self.globals["Settings"]["hotkeys"][1] = text2
            self.hotkey_setting_groupbox.setTitle("热键设置（已修改，重启后生效）")
            Configure.save(self.globals, "data/globals.json")

    @Slot()
    def notification_status_change(self):
        self.config["Notification"]["enable"] = self.notification_allow_checkbox.isChecked()
        self.config["Notification"]["system"] = self.system_notification_checkbox.isChecked()
        self.config["Notification"]["email"] = self.email_notification_checkbox.isChecked()
        Configure.save(self.globals, "data/globals.json")

    @Slot()
    def email_check(self):
        sender = self.sender_email.text()
        SMTP = self.SMTP_server.text()
        authorizationCode = self.authorization_code.text()
        receiver = self.receiver_email.text()
        if sender == "" or SMTP == "" or authorizationCode == "" or receiver == "":
            MessageBox.info(self, "警告", "请填写完整的邮箱信息")
            return
        if Notification.send_mail(
                title="SRA",
                subject="邮箱测试", message="如果您能收到这封邮件，说明您的SRA邮件通知已经准备好。",
                SMTP=SMTP, sender=sender, password=authorizationCode, receiver=receiver):
            MessageBox.info(self, "邮箱测试", "已发送测试消息，请注意查收。")
            self.globals["Notification"]["SMTP"] = SMTP
            self.globals["Notification"]["sender"] = sender
            self.globals["Notification"]["authorizationCode"] = Encryption.win_encryptor(authorizationCode)
            self.globals["Notification"]["receiver"] = receiver
            Configure.save(self.globals, "data/globals.json")

    def startup(self, state):
        if state == 2:
            WindowsProcess.set_startup_item("SRA", AppPath + "/SRA.exe")
            self.globals["Settings"]["startup"] = True
        else:
            WindowsProcess.delete_startup_item("SRA")
            self.globals["Settings"]["startup"] = False
        Configure.save(self.globals, "data/globals.json")

    @Slot(int)
    def auto_update(self, state):
        if state == 2:
            if os.path.exists("SRAUpdater.exe"):
                shutil.copy("SRAUpdater.exe", "SRAUpdater.active.exe")
                WindowsProcess.Popen("SRAUpdater.active.exe")
            else:
                self.update_log("缺少文件SRAUpdater.exe 无法自动更新")
            self.globals["Settings"]["autoUpdate"] = True
        else:
            self.globals["Settings"]["autoUpdate"] = False
        Configure.save(self.globals, "data/globals.json")

    @Slot(int)
    def thread_safety(self, state):
        if state == 2:
            self.globals["Settings"]["threadSafety"] = True
        else:
            self.globals["Settings"]["threadSafety"] = False
        Configure.save(self.globals, "data/globals.json")

    @Slot(float)
    def confidence_changed(self, value):
        self.globals["Settings"]["confidence"] = value
        Configure.save(self.globals, "data/globals.json")

    @Slot(float)
    def zoom_changed(self, value):
        self.globals["Settings"]["zoom"] = value
        Configure.save(self.globals, "data/globals.json")

    @Slot(float)
    def performance_changed(self, value):
        self.globals["Settings"]["performance"] = value
        Configure.save(self.globals, "data/globals.json")

    @Slot(str)
    def mirrorchyanCDK_changed(self, value):
        self.globals["Settings"]["mirrorchyanCDK"] = Encryption.win_encryptor(value)
        Configure.save(self.globals, "data/globals.json")

    def exit_when_close(self):
        self.globals["Settings"]["exitWhenClose"] = self.exit_when_close_checkbox.isChecked()
        Configure.save(self.globals, "data/globals.json")

    @staticmethod
    def integrity_check():
        command = "SRAUpdater -i"
        WindowsProcess.Popen(command)


class SystemTray(QSystemTrayIcon):
    def __init__(self, parent: SRA):
        super().__init__(QIcon("res/SRAico.png"), parent)
        self.parent_object = parent
        self.setToolTip("SRA")
        right_click_menu = QMenu()
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        right_click_menu.addAction("显示主界面", self.parent().show)
        right_click_menu.addAction(quit_action)
        self.setContextMenu(right_click_menu)
        self.activated.connect(self.active_handle)

    @Slot(QSystemTrayIcon.ActivationReason)
    def active_handle(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.parent_object.isVisible():
                if self.parent_object.isMinimized():
                    self.parent_object.showNormal()
                else:
                    self.parent_object.showMinimized()

            else:
                self.parent_object.show()


class BackgroundEvent(QThread):
    startOrStop = Signal()
    showOrHide = Signal()
    isTimeToRun = Signal(str)

    def __init__(self, hotkeys: list[str], scheduleList: list[str], **_):
        super().__init__()
        self.running_flag = True
        self.has_scheduled = False
        keyboard.add_hotkey(hotkeys[0], self.startOrStopCallback)
        keyboard.add_hotkey(hotkeys[1], self.showOrHideCallback)
        if len(scheduleList) == 0:
            return
        self.has_scheduled = True
        for sc in scheduleList:
            logger.debug(f'正在添加定时任务：{"".join(sc)}')
            if sc[0] == "每天":
                schedule.every().day.at(sc[1]).do(self.isTimeToRun.emit, sc[2])
            elif sc[0] == "每周":
                str_to_weekday = {
                    "一": schedule.every().monday,
                    "二": schedule.every().tuesday,
                    "三": schedule.every().wednesday,
                    "四": schedule.every().thursday,
                    "五": schedule.every().friday,
                    "六": schedule.every().saturday,
                    "日": schedule.every().sunday
                }
                day_in_week = str_to_weekday[sc[1]]
                day_in_week.at(sc[2]).do(self.isTimeToRun.emit, sc[3])

    def stop(self):
        self.running_flag = False
        keyboard.unhook_all()
        self.quit()
        self.wait()

    def run(self):
        while self.running_flag:
            if self.has_scheduled:
                schedule.run_pending()
            time.sleep(0.02)

    def startOrStopCallback(self):
        self.startOrStop.emit()

    def showOrHideCallback(self):
        self.showOrHide.emit()
