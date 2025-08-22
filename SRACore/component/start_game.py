import dataclasses

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QLineEdit, QFileDialog

from SRACore.component.common import SRAComponent
from SRACore.ui.start_game_ui import Ui_StartGameWidget
from SRACore.util import encryption


class StartGameComponent(SRAComponent):
    """
    启动游戏任务设置组件
    对应的UI文件为start_game.ui
    对应的py文件为start_game_ui.py
    该组件用于管理和展示启动游戏的相关设置选项
    """

    @dataclasses.dataclass
    class Config:
        auto_login: bool = False
        launcher: bool = False
        path: str = ""
        channel: int = 0
        user: str = ""
        passwd: str = ""

        def __init__(self, auto_login=True, launcher=False, path="", channel=0, user="", passwd="", **_):
            self.passwd = passwd
            self.auto_login = auto_login
            self.launcher = launcher
            self.path = path
            self.channel = channel
            self.user = user

    def __init__(self, parent, config_manager):
        super().__init__(parent, config_manager)
        self.ui = Ui_StartGameWidget()
        self.ui.setupUi(self)
        self.config = None
        self.init()

    def pre_connector(self):
        self.ui.use_launcher_checkbox.stateChanged.connect(self.use_launcher_state_changed)

    def setter(self):
        self.config = self.Config(**self.config_manager.get('start_game', {}))
        self.ui.auto_login_checkBox.setChecked(self.config.auto_login)
        self.ui.use_launcher_checkbox.setChecked(self.config.launcher)
        self.ui.path_lineEdit.setText(self.config.path)
        self.ui.channel_comboBox.setCurrentIndex(self.config.channel)
        self.ui.account_lineEdit.setText(encryption.win_decryptor(self.config.user))
        self.ui.password_lineEdit.setText(encryption.win_decryptor(self.config.passwd))

    def connector(self):
        self.ui.file_pushButton.clicked.connect(self.open_file)
        self.ui.password_toggle_button.clicked.connect(self.toggle_passwd_visibility)

    def getter(self):
        self.config.auto_login = self.ui.auto_login_checkBox.isChecked()
        self.config.launcher = self.ui.use_launcher_checkbox.isChecked()
        self.config.path = self.ui.path_lineEdit.text()
        self.config.channel = self.ui.channel_comboBox.currentIndex()
        self.config.user = encryption.win_encryptor(self.ui.account_lineEdit.text())
        self.config.passwd = encryption.win_encryptor(self.ui.password_lineEdit.text())
        self.config_manager.set('start_game', dataclasses.asdict(self.config))

    @Slot()
    def toggle_passwd_visibility(self):
        """Toggle password visibility"""
        if self.ui.password_lineEdit.echoMode() == QLineEdit.EchoMode.Password:
            self.ui.password_lineEdit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.ui.password_toggle_button.setText("隐藏密码")
        else:
            self.ui.password_lineEdit.setEchoMode(QLineEdit.EchoMode.Password)
            self.ui.password_toggle_button.setText("显示密码")

    @Slot()
    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "可执行文件 (*.exe)"
        )
        if file_name:
            self.ui.path_lineEdit.setText(file_name)

    @Slot(int)
    def use_launcher_state_changed(self, state):
        if state == 2:
            self.ui.path_label.setText("启动器路径")
        else:
            self.ui.path_label.setText("游戏路径")
