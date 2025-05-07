import os
import shutil

import keyboard
import time

from PySide6.QtCore import Slot, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QAction
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QListWidget,QListWidgetItem, QMenu, QWidget, QCheckBox, QTextEdit, QComboBox, QLineEdit, QPushButton, QLabel, \
    QFileDialog, \
    QSpinBox, QRadioButton, QVBoxLayout, QSystemTrayIcon, QApplication, QTableWidget, QDoubleSpinBox, QScrollArea, \
    QGroupBox, QFrame

from SRACore.utils import Encryption, Configure, WindowsProcess, const, Notification
from SRACore.utils.Dialog import MessageBox

uiLoader = QUiLoader()


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
        self.path_text: QTextEdit = self.ui.findChild(QLabel, "label2_2")
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
        def __init__(self, parent, name, level, run_times, single_time):
            super().__init__(parent)
            self.name = name
            self.level = level
            self.run_times = run_times
            self.single_time = single_time
            self.setText(f"{name} 关卡：{level} 运行次数：{run_times} 单次次数：{single_time}")

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
        self.list_widget:QListWidget = self.ui.findChild(QListWidget, "listWidget")
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
            task=self.TaskItem(self.list_widget,task["name"],task["args"]["level"],task["args"]["runTimes"],task["args"]["singleTimes"])
            self.list_widget.addItem(task)

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

    def connector(self):
        self.ornament_extraction_addbutton.clicked.connect(self.add_ornament_extraction)
        self.calyx_golden_addbutton.clicked.connect(self.add_calyx_golden)
        self.calyx_crimson_addbutton.clicked.connect(self.add_calyx_crimson)
        self.stagnant_shadow_addbutton.clicked.connect(self.add_stagnant_shadow)
        self.caver_of_corrosion_addbutton.clicked.connect(self.add_caver_of_corrosion)
        self.echo_of_war_addbutton.clicked.connect(self.add_echo_of_war)
        self.list_widget.itemDoubleClicked.connect(self.remove_item)

    def add_task(self,name,level,run_times,single_times=1):
        task=self.TaskItem(self.list_widget,name,level,run_times,single_times)
        self.list_widget.addItem(task)
        self.config["TrailBlazePower"]["taskList"].append({
            "name":name,
            "args":{
                "level":level,
                "runTimes":run_times,
                "singleTimes":single_times
                }})
        

    def add_ornament_extraction(self):
        level = self.combobox2.currentIndex()
        run_times = self.battle_times2.value()
        self.add_task("饰品提取",level,run_times)

    def add_calyx_golden(self):
        level = self.combobox3.currentIndex()
        single_times = self.single_times3.value()
        run_times = self.battle_times3.value()
        self.add_task("拟造花萼（金）",level,run_times,single_times)

    def add_calyx_crimson(self):
        level = self.combobox4.currentIndex()
        single_times = self.single_times4.value()
        run_times = self.battle_times4.value()
        self.add_task("拟造花萼（赤）",level,run_times,single_times)

    def add_stagnant_shadow(self):
        level = self.combobox5.currentIndex()
        run_times = self.battle_times5.value()
        self.add_task("凝滞虚影",level,run_times)

    def add_caver_of_corrosion(self):
        level = self.combobox6.currentIndex()
        run_times = self.battle_times6.value()
        self.add_task("侵蚀隧洞",level,run_times)

    def add_echo_of_war(self):
        level = self.combobox7.currentIndex()
        run_times = self.battle_times7.value()
        self.add_task("历战余响",level,run_times)

    @Slot(QListWidgetItem)
    def remove_item(self, item):
        index=self.list_widget.row(item)
        self.list_widget.takeItem(index)
        del self.config["TrailBlazePower"]["taskList"][index]

        


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
        self.update_log=update_log
        self.ui=uiLoader.load("res/ui/settings_page.ui")
        self.main_ui=self.ui.findChild(QScrollArea,"scrollArea")
        self.globals=self.config
        self.key_table = self.ui.findChild(QTableWidget, "tableWidget")
        self.save_button = self.ui.findChild(QPushButton, "pushButton_save")
        self.reset_button = self.ui.findChild(QPushButton, "pushButton_reset")
        self.hotkey_setting_groupbox:QGroupBox=self.ui.findChild(QGroupBox,"hotkey_setting")
        self.hotkey_lineedit1: QLineEdit = self.ui.findChild(QLineEdit, "hotkey1")
        self.hotkey_lineedit2: QLineEdit = self.ui.findChild(QLineEdit, "hotkey2")
        self.notification_allow_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "notification_allow")
        self.system_notification_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "system_notification")
        self.email_notification_checkbox: QCheckBox = self.ui.findChild(QCheckBox, "mail_notification")
        self.email_notification_frame:QFrame=self.ui.findChild(QFrame,"mail_notification_frame")
        self.SMTP_server: QLineEdit = self.ui.findChild(QLineEdit, "smtp_server")
        self.sender_email: QLineEdit = self.ui.findChild(QLineEdit, "sender_email")
        self.authorization_code:QLineEdit = self.ui.findChild(QLineEdit, "authorization_code")
        self.receiver_email: QLineEdit = self.ui.findChild(QLineEdit, "receiver_email")
        self.email_check_cutton:QPushButton=self.ui.findChild(QPushButton, "email_check_button")
        self.startup_checkbox = self.ui.findChild(QCheckBox, "checkBox_ifStartUp")

        auto_update_checkbox = self.ui.findChild(QCheckBox, "checkBox_ifAutoUpdate")
        auto_update_checkbox.stateChanged.connect(self.auto_update)
        auto_update_checkbox.setChecked(self.globals["Settings"]["autoUpdate"])

        self.thread_safety_checkbox = self.ui.findChild(QCheckBox, "checkBox_threadSafety")
        self.confidence_spin_box: QDoubleSpinBox = self.ui.findChild(QDoubleSpinBox, "confidenceSpinBox")
        self.zoom_spinbox: QDoubleSpinBox = self.ui.findChild(QDoubleSpinBox, "zoomSpinBox")
        self.mirrorchyanCDK: QLineEdit = self.ui.findChild(
            QLineEdit, "lineEdit_mirrorchyanCDK"
        )

        self.integrity_check_button: QPushButton = self.ui.findChild(
            QPushButton, "integrityCheck"
        )
        self.exit_when_close_checkbox:QCheckBox=self.ui.findChild(QCheckBox,"exit_when_close")
        self.setter()
        self.connector()

    def setter(self):
        settings = self.globals["Settings"]
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
        authorizeCode=self.globals["Notification"]["authorizationCode"]
        if authorizeCode!='':
            authorizeCode=Encryption.win_decryptor(authorizeCode)
        self.authorization_code.setText(authorizeCode)
        self.receiver_email.setText(self.globals["Notification"]["receiver"])

        self.startup_checkbox.setChecked(self.globals["Settings"]["startup"])
        self.thread_safety_checkbox.setChecked(self.globals["Settings"]["threadSafety"])
        self.confidence_spin_box.setValue(self.globals["Settings"]["confidence"])
        self.zoom_spinbox.setValue(self.globals["Settings"]["zoom"])
        self.mirrorchyanCDK.setText(
            Encryption.win_decryptor(self.globals["Settings"]["mirrorchyanCDK"])
        )
        self.exit_when_close_checkbox.setChecked(self.globals["Settings"]["exitWhenClose"])

    def connector(self):
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
        self.mirrorchyanCDK.textChanged.connect(self.mirrorchyanCDK_changed)
        self.integrity_check_button.clicked.connect(self.integrity_check)
        self.exit_when_close_checkbox.stateChanged.connect(self.exit_when_close)

    def key_setting_save(self):
        Configure.save(self.globals,'data/globals.json')

    def key_setting_reset(self):
        for i in range(4):
            self.key_table.item(0, i).setText("f" + str(i + 1))

    def key_setting_change(self):
        for i in range(4):
            self.globals["Settings"]["F" + str(i + 1)] = self.key_table.item(0, i).text()

    @Slot()
    def hotkey_change(self):
        text1=self.hotkey_lineedit1.text()
        text2=self.hotkey_lineedit2.text()
        if self.globals["Settings"]["hotkeys"][0]!=text1 or self.globals["Settings"]["hotkeys"][1]!=text2:
            self.globals["Settings"]["hotkeys"][0]=text1
            self.globals["Settings"]["hotkeys"][1] = text2
            self.hotkey_setting_groupbox.setTitle("热键设置（已修改，重启后生效）")
            Configure.save(self.globals, "data/globals.json")

    @Slot()
    def notification_status_change(self):
        self.config["Notification"]["enable"]=self.notification_allow_checkbox.isChecked()
        self.config["Notification"]["system"]=self.system_notification_checkbox.isChecked()
        self.config["Notification"]["email"]=self.email_notification_checkbox.isChecked()
        Configure.save(self.globals,"data/globals.json")

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
            subject="邮箱测试",message="如果您能收到这封邮件，说明您的SRA邮件通知已经准备好。",
            SMTP=SMTP, sender=sender, password=authorizationCode, receiver=receiver):
            MessageBox.info(self,"邮箱测试","已发送测试消息，请注意查收。")
            self.globals["Notification"]["SMTP"] = SMTP
            self.globals["Notification"]["sender"] = sender
            self.globals["Notification"]["authorizationCode"] = Encryption.win_encryptor(authorizationCode)
            self.globals["Notification"]["receiver"] = receiver
            Configure.save(self.globals, "data/globals.json")

    def startup(self, state):
        if state == 2:
            WindowsProcess.set_startup_item("SRA", const.AppPath + "/SRA.exe")
            self.globals["Settings"]["startup"] = True
        else:
            WindowsProcess.delete_startup_item("SRA")
            self.globals["Settings"]["startup"] = False
        Configure.save(self.globals, "data/globals.json")

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

    def thread_safety(self, state):
        if state == 2:
            self.globals["Settings"]["threadSafety"] = True
        else:
            self.globals["Settings"]["threadSafety"] = False
        Configure.save(self.globals, "data/globals.json")

    def confidence_changed(self, value):
        self.globals["Settings"]["confidence"] = value
        Configure.save(self.globals, "data/globals.json")

    def zoom_changed(self, value):
        self.globals["Settings"]["zoom"] = value
        Configure.save(self.globals, "data/globals.json")

    def mirrorchyanCDK_changed(self, value):
        self.globals["Settings"]["mirrorchyanCDK"] = Encryption.win_encryptor(value)
        Configure.save(self.globals,"data/globals.json")

    def exit_when_close(self):
        self.globals["Settings"]["exitWhenClose"]=self.exit_when_close_checkbox.isChecked()
        Configure.save(self.globals, "data/globals.json")

    @staticmethod
    def integrity_check():
        command = "SRAUpdater -i"
        WindowsProcess.Popen(command)


class SystemTray(QSystemTrayIcon):
    def __init__(self, parent: QWidget):
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


class Hotkey(QThread):
    startOrStop = Signal()
    showOrHide = Signal()

    def __init__(self,hotkey_config:list[str]):
        super().__init__()
        self.running_flag = True
        keyboard.add_hotkey(hotkey_config[0], self.startOrStopCallback)
        keyboard.add_hotkey(hotkey_config[1], self.showOrHideCallback)

    def stop(self):
        self.running_flag = False
        keyboard.unhook_all()
        self.quit()
        self.wait()

    def run(self):
        while self.running_flag:
            time.sleep(0.02)

    def startOrStopCallback(self):
        self.startOrStop.emit()

    def showOrHideCallback(self):
        self.showOrHide.emit()
