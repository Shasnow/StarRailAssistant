import dataclasses

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QListWidgetItem

from SRACore.component.common import SRAComponent
from SRACore.ui.trailblaze_power_ui import Ui_TrailblazePowerWidget
from SRACore.util.config import ConfigManager


class TrailblazePowerComponent(SRAComponent):
    @dataclasses.dataclass
    class Config:
        task_list: list = dataclasses.field(default_factory=list)
        replenish: bool = False
        replenish_way: int = 0
        replenish_time: int = 0
        use_assistant: bool = False
        change_lineup: bool = False

        def __init__(self, task_list=None, replenish=False, replenish_way=0, replenish_time=0, use_assistant=False,
                     change_lineup=False, **_):
            if task_list is None:
                task_list = []
            self.task_list = task_list
            self.replenish = replenish
            self.replenish_way = replenish_way
            self.replenish_time = replenish_time
            self.use_assistant = use_assistant
            self.change_lineup = change_lineup

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
                    "level_text": self.level_text,
                    "run_time": self.run_times,
                    "single_time": self.single_times
                }}

        @staticmethod
        def fromjson(data: dict):
            return TrailblazePowerComponent.TaskItem(
                data["name"],
                data["args"].get("level",1),
                data["args"].get("level_text", ""),
                data["args"].get("run_time",1),
                data["args"].get("single_time",1)
            )

    def __init__(self, parent, config_manager: ConfigManager):
        super().__init__(parent, config_manager)
        self.ui = Ui_TrailblazePowerWidget()
        self.ui.setupUi(self)
        self.init()

    def setter(self):
        self.config = self.Config(**self.config_manager.get('trailblaze_power', {}))
        self.ui.replenish_checkBox.setChecked(self.config.replenish)
        self.ui.replenish_way_comboBox.setCurrentIndex(self.config.replenish_way)
        self.ui.replenish_time_spinBox.setValue(self.config.replenish_time)
        self.ui.useAssist_checkBox.setChecked(self.config.use_assistant)
        self.ui.changeLineup_checkBox.setChecked(self.config.change_lineup)
        self.ui.task_listWidget.clear()
        for task in self.config.task_list:
            self.ui.task_listWidget.addItem(TrailblazePowerComponent.TaskItem.fromjson(task))

    def connector(self):
        self.ui.task_listWidget.itemDoubleClicked.connect(self.remove_item)
        self.ui.ornamentExtractionAddButton.clicked.connect(self.add_ornament_extraction)
        self.ui.calyxGoldenAddButton.clicked.connect(self.add_calyx_golden)
        self.ui.calyxCrimsonAddButton.clicked.connect(self.add_calyx_crimson)
        self.ui.stagnantShadowAddButton.clicked.connect(self.add_stagnant_shadow)
        self.ui.caverOfCorrosionAddButton.clicked.connect(self.add_caver_of_corrosion)
        self.ui.echoOfWarAddButton.clicked.connect(self.add_echo_of_war)

    def getter(self):
        self.config.replenish = self.ui.replenish_checkBox.isChecked()
        self.config.replenish_way = self.ui.replenish_way_comboBox.currentIndex()
        self.config.replenish_time = self.ui.replenish_time_spinBox.value()
        self.config.use_assistant = self.ui.useAssist_checkBox.isChecked()
        self.config.change_lineup = self.ui.changeLineup_checkBox.isChecked()
        self.config.task_list.clear()
        for i in range(self.ui.task_listWidget.count()):
            task: TrailblazePowerComponent.TaskItem | QListWidgetItem = self.ui.task_listWidget.item(i)
            self.config.task_list.append(task.tojson())
        self.config_manager.set('trailblaze_power', dataclasses.asdict(self.config))

    def add_task(self, name, level, level_text, run_times, single_times=1):
        task = self.TaskItem(name, level, level_text, run_times, single_times)
        self.ui.task_listWidget.addItem(task)

    def add_ornament_extraction(self):
        self.add_task("饰品提取",
                      self.ui.ornamentExtraction_comboBox.currentIndex(),
                      self.ui.ornamentExtraction_comboBox.currentText(),
                      self.ui.ornamentExtraction_spinBox.value())

    def add_calyx_golden(self):
        self.add_task("拟造花萼（金）",
                      self.ui.calyxGolden_comboBox.currentIndex(),
                      self.ui.calyxGolden_comboBox.currentText(),
                      self.ui.calyxGoldenRunTime_spinBox.value(),
                      self.ui.calyxGoldenSingleTime_spinBox.value())

    def add_calyx_crimson(self):
        self.add_task("拟造花萼（赤）",
                      self.ui.calyxCrimson_comboBox.currentIndex(),
                      self.ui.calyxCrimson_comboBox.currentText(),
                      self.ui.calyxCrimsonRunTime_spinBox.value(),
                      self.ui.calyxCrimsonSingleTime_spinBox.value())

    def add_stagnant_shadow(self):
        self.add_task("凝滞虚影",
                      self.ui.stagnantShadow_comboBox.currentIndex(),
                      self.ui.stagnantShadow_comboBox.currentText(),
                      self.ui.stagnantShadowRunTime_spinBox.value())

    def add_caver_of_corrosion(self):
        self.add_task("侵蚀隧洞",
                      self.ui.caverOfCorrosion_comboBox.currentIndex(),
                      self.ui.caverOfCorrosion_comboBox.currentText(),
                      self.ui.caverOfCorrosionRunTime_spinBox.value())

    def add_echo_of_war(self):
        self.add_task("历战余响",
                      self.ui.echoOfWar_comboBox.currentIndex(),
                      self.ui.echoOfWar_comboBox.currentText(),
                      self.ui.echoOfWarRunTime_spinBox.value())

    @Slot(QListWidgetItem)
    def remove_item(self, item):
        index = self.ui.task_listWidget.row(item)
        self.ui.task_listWidget.takeItem(index)
