from PySide6.QtCore import Slot, Signal

from SRACore.component.common import SRAComponent
from SRACore.component.dialog import MessageBox, InputDialog
from SRACore.ui.multi_account_ui import Ui_MultiAccountWidget
from SRACore.util.config import GlobalConfigManager, ConfigManager


class MultiAccountComponent(SRAComponent):
    config_switched = Signal(str)
    def __init__(self, parent, gcm: GlobalConfigManager):
        super().__init__(parent, None)
        self.gcm = gcm
        self.ui = Ui_MultiAccountWidget()
        self.ui.setupUi(self)
        self.init()

    def setter(self):
        self.ui.current_config_combobox.addItems(self.gcm.get('config_list', ['default']))
        self.ui.current_config_combobox.setCurrentIndex(self.gcm.get('current_config', 0))
        self.ui.switch2next_checkbox.setChecked(self.gcm.get('switch2next', False))

    def getter(self):
        self.gcm.set('current_config', self.ui.current_config_combobox.currentIndex())
        self.gcm.set('switch2next', self.ui.switch2next_checkbox.isChecked())

    def connector(self):
        self.ui.new_plan_button.clicked.connect(self.new_plan)
        self.ui.delete_plan_button.clicked.connect(self.delete_plan)
        self.ui.current_config_combobox.currentTextChanged.connect(lambda text: self.config_switched.emit(text))

    @Slot()
    def new_plan(self):
        if self.ui.current_config_combobox.count() == self.ui.current_config_combobox.maxCount():
            MessageBox.info(self, "添加失败", "配置方案已达最大数量！")
            return
        plan_name, confirm = InputDialog.getText(self, "创建方案", "方案名称：")
        if confirm and plan_name:
            if plan_name in self.gcm.get('config_list'):
                MessageBox.info(self, "添加失败", "方案已存在！")
                return
            self.gcm.get('config_list').append(plan_name)
            self.ui.current_config_combobox.addItem(plan_name)

    @Slot()
    def delete_plan(self):
        if len(self.gcm.get('config_list')) == 1:
            MessageBox.info(self, "删除失败", "至少保留一个方案")
            return
        index = self.ui.current_config_combobox.currentIndex()
        text = self.ui.current_config_combobox.currentText()
        self.ui.current_config_combobox.removeItem(index)
        del self.gcm.get('config_list')[index]
        self.gcm.set('current_config', self.ui.current_config_combobox.currentIndex())
        ConfigManager.delete(text)