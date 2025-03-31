from PySide6.QtCore import Slot
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QCheckBox, QTextEdit, QComboBox, QLineEdit, QPushButton, QLabel, QFileDialog, \
    QSpinBox, QRadioButton

from SRACore.utils import Encryption

uiLoader=QUiLoader()

class ReceiveRewards(QWidget):
    def __init__(self, parent, config: dict):
        super().__init__(parent)
        self.ui = uiLoader.load("res/ui/set_03.ui")
        self.config = config
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

    def getter(self):
        self.config["Mission"]["trailBlazerProfile"] = self.option1.isChecked()
        self.config["Mission"]["assignment"] = self.option2.isChecked()
        self.config["Mission"]["mail"] = self.option3.isChecked()
        self.config["Mission"]["dailyTraining"] = self.option4.isChecked()
        self.config["Mission"]["namelessHonor"] = self.option5.isChecked()
        self.config["Mission"]["giftOfOdyssey"] = self.option6.isChecked()
        self.config["Mission"]["redeemCode"] = self.option7.isChecked()
        self.config["RedeemCode"]["codeList"] = self.redeem_code.toPlainText().split()


class StartGame(QWidget):
    def __init__(self, parent, config: dict):
        super().__init__(parent)
        self.ui = uiLoader.load("res/ui/set_01.ui")
        self.config = config
        self.account_text = Encryption.load()
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
        self.setter()

    def setter(self):
        self.channel_combobox.setCurrentIndex(self.config["StartGame"]["channel"])
        self.use_launcher_checkbox.setChecked(self.config["StartGame"]["launcher"])
        self.use_launcher_checkbox.stateChanged.connect(self.use_launcher)
        self.path_text.setText("启动器路径：" if self.config["StartGame"]["launcher"] else "游戏路径：")
        self.line_area.setText(self.config["StartGame"]["gamePath"])
        self.file_select_button.clicked.connect(self.open_file)
        self.auto_launch_checkbox.setChecked(self.config["StartGame"]["autoLogin"])
        self.auto_launch_checkbox.stateChanged.connect(self.auto_launch)
        self.account.setText(self.account_text)
        self.account.setReadOnly(True)
        # self.password.setText(self.password_text)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setReadOnly(True)
        self.show_button.clicked.connect(self.togglePasswordVisibility)

    def getter(self):
        self.config["StartGame"]["channel"] = self.channel_combobox.currentIndex()
        self.config["StartGame"]["autoLogin"] = self.auto_launch_checkbox.isChecked()
        self.config["StartGame"]["gamePath"] = self.line_area.text()
        self.account_text = self.account.text()

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
    def auto_launch(self):
        """
        Change the state of mission auto launch,
        update QLineEdit state.
        """
        if self.auto_launch_checkbox.isChecked():
            self.account.setReadOnly(False)
            self.password.setReadOnly(False)
        else:
            self.account.setReadOnly(True)
            self.password.setReadOnly(True)

    @Slot()
    def togglePasswordVisibility(self):
        """Toggle password visibility"""
        if self.password.echoMode() == QLineEdit.EchoMode.Password:
            self.password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_button.setText("隐藏")
        else:
            self.password.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_button.setText("显示")


class TrailblazePower(QWidget):
    def __init__(self, parent, config: dict):
        super().__init__(parent)
        self.ui = uiLoader.load("res/ui/set_07.ui")
        self.config = config
        self.opt1: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox2_1_11"
        )
        self.combobox1: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_1_13"
        )
        self.times1: QSpinBox = self.ui.findChild(QSpinBox, "spinBox2_1_23")
        self.use_assist_checkbox:QCheckBox=self.ui.findChild(QCheckBox, "useAssist")
        self.change_lineup_checkbox:QCheckBox=self.ui.findChild(QCheckBox, "changeLineup")
        self.opt2: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox2_2_11"
        )
        self.combobox2: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_2_13"
        )
        self.battle_times2: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_2_23"
        )
        self.opt3: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox2_3_11"
        )
        self.combobox3: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_3_13"
        )
        self.single_times3: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_3_23"
        )
        self.battle_times3: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_3_33"
        )
        self.opt4: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox2_4_11"
        )
        self.combobox4: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_4_13"
        )
        self.single_times4: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_4_23"
        )
        self.battle_times4: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_4_33"
        )
        self.opt5: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox2_5_11"
        )
        self.combobox5: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_5_13"
        )
        self.battle_times5: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_5_23"
        )
        self.opt6: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox2_6_11"
        )
        self.combobox6: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_6_13"
        )
        self.battle_times6: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_6_23"
        )
        self.opt7: QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox2_7_11"
        )
        self.combobox7: QComboBox = self.ui.findChild(
            QComboBox, "comboBox2_7_13"
        )
        self.battle_times7: QSpinBox = self.ui.findChild(
            QSpinBox, "spinBox2_7_23"
        )
        self.setter()

    def setter(self):
        self.opt1.setChecked(self.config["Replenish"]["enable"])
        self.combobox1.setCurrentIndex(self.config["Replenish"]["way"])
        self.times1.setValue(self.config["Replenish"]["runTimes"])
        self.use_assist_checkbox.setChecked(self.config["Support"]["enable"])
        self.change_lineup_checkbox.setChecked(self.config["Support"]['changeLineup'])
        self.opt2.setChecked(self.config["OrnamentExtraction"]["enable"])
        self.combobox2.setCurrentIndex(self.config["OrnamentExtraction"]["level"])
        self.battle_times2.setValue(self.config["OrnamentExtraction"]["runTimes"])
        self.opt3.setChecked(self.config["CalyxGolden"]["enable"])
        self.combobox3.setCurrentIndex(self.config["CalyxGolden"]["level"])
        self.single_times3.setValue(self.config["CalyxGolden"]["singleTimes"])
        self.battle_times3.setValue(self.config["CalyxGolden"]["runTimes"])
        self.opt4.setChecked(self.config["CalyxCrimson"]["enable"])
        self.combobox4.setCurrentIndex(self.config["CalyxCrimson"]["level"])
        self.single_times4.setValue(self.config["CalyxCrimson"]["singleTimes"])
        self.battle_times4.setValue(self.config["CalyxCrimson"]["runTimes"])
        self.opt5.setChecked(self.config["StagnantShadow"]["enable"])
        self.combobox5.setCurrentIndex(self.config["StagnantShadow"]["level"])
        self.battle_times5.setValue(self.config["StagnantShadow"]["runTimes"])
        self.opt6.setChecked(self.config["CaverOfCorrosion"]["enable"])
        self.combobox6.setCurrentIndex(self.config["CaverOfCorrosion"]["level"])
        self.battle_times6.setValue(self.config["CaverOfCorrosion"]["runTimes"])
        self.opt7.setChecked(self.config["EchoOfWar"]["enable"])
        self.combobox7.setCurrentIndex(self.config["EchoOfWar"]["level"])
        self.battle_times7.setValue(self.config["EchoOfWar"]["runTimes"])

    def getter(self):
        self.config["Replenish"]["enable"] = self.opt1.isChecked()
        self.config["Replenish"]["way"] = self.combobox1.currentIndex()
        self.config["Replenish"]["runTimes"] = self.times1.value()
        self.config["Support"]["enable"]=self.use_assist_checkbox.isChecked()
        self.config["Support"]['changeLineup']=self.change_lineup_checkbox.isChecked()
        self.config["OrnamentExtraction"]["enable"] = self.opt2.isChecked()
        self.config["OrnamentExtraction"]["level"] = self.combobox2.currentIndex()
        self.config["OrnamentExtraction"]["runTimes"] = self.battle_times2.value()
        self.config["CalyxGolden"]["enable"] = self.opt3.isChecked()
        self.config["CalyxGolden"]["level"] = self.combobox3.currentIndex()
        self.config["CalyxGolden"]["singleTimes"] = self.single_times3.value()
        self.config["CalyxGolden"]["runTimes"] = self.battle_times3.value()
        self.config["CalyxCrimson"]["enable"] = self.opt4.isChecked()
        self.config["CalyxCrimson"]["level"] = self.combobox4.currentIndex()
        self.config["CalyxCrimson"]["singleTimes"] = self.single_times4.value()
        self.config["CalyxCrimson"]["runTimes"] = self.battle_times4.value()
        self.config["StagnantShadow"]["enable"] = self.opt5.isChecked()
        self.config["StagnantShadow"]["level"] = self.combobox5.currentIndex()
        self.config["StagnantShadow"]["runTimes"] = self.battle_times5.value()
        self.config["CaverOfCorrosion"]["enable"] = self.opt6.isChecked()
        self.config["CaverOfCorrosion"]["level"] = self.combobox6.currentIndex()
        self.config["CaverOfCorrosion"]["runTimes"] = self.battle_times6.value()
        self.config["EchoOfWar"]["enable"] = self.opt7.isChecked()
        self.config["EchoOfWar"]["level"] = self.combobox7.currentIndex()
        self.config["EchoOfWar"]["runTimes"] = self.battle_times7.value()

class QuitGame(QWidget):
    def __init__(self, parent, config: dict):
        super().__init__(parent)
        self.ui=uiLoader.load("res/ui/set_10.ui")
        self.config=config
        self.exit_checkbox:QCheckBox = self.ui.findChild(
            QCheckBox, "checkBox2_1_1"
        )
        self.radio_button1:QRadioButton = self.ui.findChild(
            QRadioButton, "radioButton2_1_2"
        )
        self.radio_button2:QRadioButton = self.ui.findChild(
            QRadioButton, "radioButton2_1_3"
        )

    def getter(self):
        return self.exit_checkbox.isChecked(),self.radio_button1.isChecked(),self.radio_button2.isChecked()
    

class SimulatedUniverse(QWidget):
    def __init__(self,parent, config:dict):
        super().__init__(parent)
        self.ui=uiLoader.load("res/ui/simulated_universe.ui")
        self.config=config
        self.mode_combobox: QComboBox = self.ui.findChild(QComboBox, "game_mode")
        self.times_spinbox: QSpinBox = self.ui.findChild(QSpinBox, "times")
        self.policy_checkbox:QComboBox=self.ui.findChild(QComboBox,'policy_comboBox')
        self.setter()

    def setter(self):
        self.mode_combobox.setCurrentIndex(self.config["DivergentUniverse"]["mode"])
        self.times_spinbox.setValue(self.config["DivergentUniverse"]["times"])
        self.policy_checkbox.setCurrentIndex(self.config["DivergentUniverse"]["policy"])

    def getter(self):
        self.config["DivergentUniverse"]["mode"]=self.mode_combobox.currentIndex()
        self.config["DivergentUniverse"]["times"]=self.times_spinbox.value()
        self.config["DivergentUniverse"]["policy"]=self.policy_checkbox.currentIndex()