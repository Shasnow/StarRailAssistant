import dataclasses

from SRACore.component.common import SRAComponent
from SRACore.ui.simulated_universe_ui import Ui_SimulateUniverseWidget
from SRACore.util.config import ConfigManager


class SimulateUniverseComponent(SRAComponent):
    @dataclasses.dataclass
    class Config:
        mode: int = 0
        times: int = 1
        policy: int = 0

        def __init__(self, mode=0, times=1, policy=0, **_):
            self.mode = mode
            self.times = times
            self.policy = policy

    def __init__(self, parent, config_manager: ConfigManager):
        super().__init__(parent, config_manager)
        self.ui = Ui_SimulateUniverseWidget()
        self.ui.setupUi(self)
        self.init()

    def setter(self):
        self.config = self.Config(**self.config_manager.get('simulated_universe', {}))
        self.ui.game_mode.setCurrentIndex(self.config.mode)
        self.ui.times.setValue(self.config.times)
        self.ui.policy_comboBox.setCurrentIndex(self.config.policy)

    def getter(self):
        self.config.mode = self.ui.game_mode.currentIndex()
        self.config.times = self.ui.times.value()
        self.config.policy = self.ui.policy_comboBox.currentIndex()
        self.config_manager.set('simulated_universe', dataclasses.asdict(self.config))

    def connector(self):
        pass
