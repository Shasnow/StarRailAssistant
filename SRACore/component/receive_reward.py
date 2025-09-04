import dataclasses

from SRACore.component.common import SRAComponent
from SRACore.ui.receive_reward_ui import Ui_ReceiveRewardWidget
from SRACore.util.config import ConfigManager


class ReceiveRewardComponent(SRAComponent):
    @dataclasses.dataclass
    class Config:
        """Configuration for the ReceiveRewardComponent."""
        item_select: tuple = (True, True, True, True, True, False, False)
        redeem_code_list: list = dataclasses.field(default_factory=list)

        def __init__(self, item_select=None, redeem_code_list=None, **_):
            if item_select is None:
                item_select = (True, True, True, True, True, False, False)
            if redeem_code_list is None:
                redeem_code_list = []
            self.item_select = item_select
            self.redeem_code_list = redeem_code_list

    def __init__(self, parent, config_manager: ConfigManager):
        super().__init__(parent, config_manager)
        self.ui = Ui_ReceiveRewardWidget()
        self.ui.setupUi(self)
        self.config = None
        self.setter()

    def setter(self):
        self.config = self.Config(
            **self.config_manager.get('receive_reward', {}))
        self.ui.trailblaze_profile_checkbox.setChecked(self.config.item_select[0])
        self.ui.assignment_checkbox.setChecked(self.config.item_select[1])
        self.ui.mail_checkbox.setChecked(self.config.item_select[2])
        self.ui.daily_reward_checkbox.setChecked(self.config.item_select[3])
        self.ui.nameless_honour_checkbox.setChecked(self.config.item_select[4])
        self.ui.gift_of_odyssey_checkbox.setChecked(self.config.item_select[5])
        self.ui.redeem_code_checkbox.setChecked(self.config.item_select[6])
        self.ui.redeem_code_textEdit.setText("\n".join(self.config.redeem_code_list))

    def getter(self):
        self.config.item_select = (
            self.ui.trailblaze_profile_checkbox.isChecked(),
            self.ui.assignment_checkbox.isChecked(),
            self.ui.mail_checkbox.isChecked(),
            self.ui.daily_reward_checkbox.isChecked(),
            self.ui.nameless_honour_checkbox.isChecked(),
            self.ui.gift_of_odyssey_checkbox.isChecked(),
            self.ui.redeem_code_checkbox.isChecked()
        )
        self.config.redeem_code_list = self.ui.redeem_code_textEdit.toPlainText().split()
        self.config_manager.set('receive_reward', dataclasses.asdict(self.config))
