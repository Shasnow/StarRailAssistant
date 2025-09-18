import dataclasses

from SRACore.component.common import SRAComponent
from SRACore.ui.mission_accomplish_ui import Ui_MissionAccomplishWidget
from SRACore.util.config import ConfigManager


class MissionAccomplishComponent(SRAComponent):
    @dataclasses.dataclass
    class Config:
        logout: bool = False
        quit_game: bool = False
        exit_sra: bool = False
        shutdown: bool = False
        sleep: bool = False

        def __init__(self, logout=False, quit_game=False, exit_sra=False, shutdown=False, sleep=False, **_):
            self.logout = logout
            self.quit_game = quit_game
            self.exit_sra = exit_sra
            self.shutdown = shutdown
            self.sleep = sleep

    def __init__(self, parent, config_manager: ConfigManager):
        super().__init__(parent, config_manager)
        self.ui = Ui_MissionAccomplishWidget()
        self.ui.setupUi(self)
        self.init()

    def setter(self):
        self.config = self.Config(**self.config_manager.get('mission_accomplish', {}))
        self.ui.log_out_checkbox.setChecked(self.config.logout)
        self.ui.quit_game_checkbox.setChecked(self.config.quit_game)
        self.ui.quit_sra_checkbox.setChecked(self.config.exit_sra)
        self.ui.shutdown_button.setChecked(self.config.shutdown)
        self.ui.hibernate_button.setChecked(self.config.sleep)

    def getter(self):
        self.config.logout = self.ui.log_out_checkbox.isChecked()
        self.config.quit_game = self.ui.quit_game_checkbox.isChecked()
        self.config.exit_sra = self.ui.quit_sra_checkbox.isChecked()
        self.config.shutdown = self.ui.shutdown_button.isChecked()
        self.config.sleep = self.ui.hibernate_button.isChecked()
        self.config_manager.set('mission_accomplish', dataclasses.asdict(self.config))
