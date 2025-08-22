import os.path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QListWidgetItem

import SRACore.util.system as system
from SRACore.component.common import SRAComponent
from SRACore.component.dialog import ScheduleDialog
from SRACore.ui.settings_page_ui import Ui_SettingWidget
from SRACore.util.config import GlobalConfigManager
from SRACore.util.logger import logger


class SettingsPageComponent(SRAComponent):
    """
    设置页面组件
    对应的UI文件为settings_page.ui
    对应的py文件为settings_page_ui.py
    该组件用于管理和展示应用程序的设置选项
    """

    def __init__(self, parent, gcm: GlobalConfigManager):
        super().__init__(parent, gcm)
        self.gcm = gcm
        self.ui = Ui_SettingWidget()
        self.ui.setupUi(self)
        self.pre_connector()
        self.setter()

    def setter(self):
        for i in self.gcm.get('schedule_list', []):
            self.ui.schedule_list.addItem(''.join(i))
        for i in range(4):
            self.ui.key_tableWidget.item(0, i).setText(self.gcm.get(f'key_f{i + 1}', f'f{i + 1}'))
        self.ui.hotkey1.setText(self.gcm.get('hotkey1', 'f9'))
        self.ui.hotkey2.setText(self.gcm.get('hotkey2', 'f10'))
        self.ui.notification_allow_checkbox.setChecked(self.gcm.get('notification_allow', True))
        self.ui.system_notification_checkbox.setChecked(self.gcm.get('notification_system', True))
        self.ui.mail_notification_checkbox.setChecked(self.gcm.get('notification_mail', False))
        self.ui.mail_notification_frame.setVisible(self.ui.mail_notification_checkbox.isChecked())
        self.ui.smtp_server.setText(self.gcm.get('smtp_server', ''))
        self.ui.sender_email.setText(self.gcm.get('sender_email', ''))
        self.ui.authorization_code.setText(self.gcm.get('authorization_code', ''))
        self.ui.receiver_email.setText(self.gcm.get('receiver_email', ''))
        self.ui.threadSafety_checkBox.setChecked(self.gcm.get('thread_safety', False))
        self.ui.startup_checkBox.setChecked(self.gcm.get('startup', False))
        self.ui.autoUpdate_checkBox.setChecked(self.gcm.get('autoupdate', True))
        self.ui.zoomSpinBox.setValue(self.gcm.get('zoom', 1.50))
        self.ui.confidenceSpinBox.setValue(self.gcm.get('confidence', 0.90))
        self.ui.performanceSpinBox.setValue(self.gcm.get('performance', 2.0))
        self.ui.exit_when_close_checkBox.setChecked(self.gcm.get('exit_when_close', True))
        self.ui.mirrorchyanCDK_lineEdit.setText(self.gcm.get('mirrorchyanCDK', ''))  # NOQA

    def getter(self):
        for i in range(4):
            self.gcm.set(f'key_f{i + 1}', self.ui.key_tableWidget.item(0, i).text())
        self.gcm.set('hotkey1', self.ui.hotkey1.text())
        self.gcm.set('hotkey2', self.ui.hotkey2.text())
        self.gcm.set('notification_allow', self.ui.notification_allow_checkbox.isChecked())
        self.gcm.set('notification_system', self.ui.system_notification_checkbox.isChecked())
        self.gcm.set('notification_mail', self.ui.mail_notification_checkbox.isChecked())
        self.gcm.set('smtp_server', self.ui.smtp_server.text())
        self.gcm.set('sender_email', self.ui.sender_email.text())
        self.gcm.set('authorization_code', self.ui.authorization_code.text())
        self.gcm.set('receiver_email', self.ui.receiver_email.text())
        self.gcm.set('thread_safety', self.ui.threadSafety_checkBox.isChecked())
        self.gcm.set('startup', self.ui.startup_checkBox.isChecked())
        self.gcm.set('zoom', float(self.ui.zoomSpinBox.value()))
        self.gcm.set('confidence', float(self.ui.confidenceSpinBox.value()))
        self.gcm.set('performance', float(self.ui.performanceSpinBox.value()))
        self.gcm.set('exit_when_close', self.ui.exit_when_close_checkBox.isChecked())
        self.gcm.set('mirrorchyanCDK', str(self.ui.mirrorchyanCDK_lineEdit.text()))  # NOQA

    def pre_connector(self):
        """预连接函数，用于连接信号和槽，在setter之前执行"""
        self.ui.autoUpdate_checkBox.stateChanged.connect(self.auto_update_state_changed_event)
        self.ui.integrityCheckButton.clicked.connect(self.integrity_check)
        self.ui.schedule_add_button.clicked.connect(self.add_schedule)
        self.ui.schedule_list.itemDoubleClicked.connect(self.remove_schedule)
        self.ui.reset_pushButton.clicked.connect(self.reset_keys)

    @Slot()
    def add_schedule(self):
        sc = ScheduleDialog.getSchedule(self, self.gcm.get('configList', []))
        if sc is not None:
            self.ui.schedule_list.addItem(''.join(sc))
            self.gcm.get('schedule_list').append(sc)

    @Slot(QListWidgetItem)
    def remove_schedule(self, item):
        index = self.ui.schedule_list.row(item)
        self.ui.schedule_list.takeItem(index)
        del self.gcm.get('schedule_list')[index]

    @Slot()
    def reset_keys(self):
        """重置快捷键"""
        for i in range(4):
            self.ui.key_tableWidget.item(0, i).setText(f'f{i + 1}')

    @Slot()
    def integrity_check(self):
        """调用工具进行完整性检查"""
        command = "SRAUpdater -i"
        system.Popen(command)

    @Slot(int)
    def auto_update_state_changed_event(self, state: int):
        """
        自动更新按钮的槽函数
        该函数会触发自动更新操作
        """
        if state == 2:  # Qt.Checked
            self.gcm.set('autoupdate', True)
            if os.path.exists("SRAUpdater.exe"):
                system.Popen("SRAUpdater.exe")
            else:
                logger.info("SRAUpdater.exe文件不存在，无法启动更新程序")
        else:
            self.gcm.set('autoupdate', False)
