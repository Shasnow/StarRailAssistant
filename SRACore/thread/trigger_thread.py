from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QFrame, QLabel, QSpinBox, QFormLayout, QLineEdit, QGridLayout, QSizePolicy, QToolButton

from SRACore.triggers import AutoPlotTrigger
from SRACore.triggers.BaseTrigger import BaseTrigger
from SRACore.util.logger import logger
from SRACore.widget.ToggleSwitch import ToggleSwitch


class TriggerManager(QThread):
    __instance = None
    finished_signal = Signal()

    def __init__(self):
        self.isRunning = False
        super().__init__()
        self.triggers: list[BaseTrigger] = []
        self.trigger_widgets = []
        self.register(AutoPlotTrigger())

    def run(self):
        self.isRunning = True
        while self.isRunning:
            for trigger in self.triggers:
                if trigger.enabled:
                    trigger.run()
            QThread.msleep(100)
        logger.debug("TriggerManager stopped.")

    def stop(self):
        """
        停止触发器管理器的运行。
        """
        logger.debug("正在停止触发器线程...")
        for trigger in self.triggers:
            trigger.set_enable(False)
        self.isRunning = False

    def register(self, trigger: BaseTrigger):
        """
        注册触发器实例到管理器中。
        :param trigger: 触发器实例
        """
        if trigger not in self.triggers:
            self.triggers.append(trigger)
            logger.debug(f"Trigger {trigger.__class__.__name__} registered successfully.")
        else:
            logger.debug(f"Trigger {trigger.__class__.__name__} is already registered.")

        self.trigger_widgets.append(TriggerItemWidget(trigger))
        logger.debug(f"Trigger widget for {trigger.__class__.__name__} created successfully.")

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance


class TriggerItemWidget(QFrame):
    """单个触发器的 UI 组件"""

    def __init__(self, trigger: BaseTrigger, parent=None):
        super().__init__(parent)
        self.trigger = trigger
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        self.label = QLabel(trigger.name)
        grid_layout.addWidget(self.label, 0, 0, 1, 1)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.toggle_switch = ToggleSwitch()
        self.toggle_switch.stateChanged.connect(trigger.set_enable)
        grid_layout.addWidget(self.toggle_switch, 0, 1, 1, 1)
        self.tool_button = QToolButton()
        self.tool_button.setAutoRaise(True)
        self.tool_button.setArrowType(Qt.ArrowType.UpArrow)
        grid_layout.addWidget(self.tool_button, 0, 2, 1, 1)
        self.config_frame = QFrame()
        config_layout = QFormLayout()
        self.config_frame.setLayout(config_layout)
        self.config_frame.hide()
        grid_layout.addWidget(self.config_frame, 1, 0, 1, 3)
        self.tool_button.clicked.connect(self.toggle_config)
        for w in self.create_widget_for_config():
            config_layout.addRow(w[0], w[1])

    def toggle_config(self):
        """切换配置面板的显示状态"""
        if self.config_frame.isVisible():
            self.tool_button.setArrowType(Qt.ArrowType.UpArrow)
            self.config_frame.hide()
        else:
            self.tool_button.setArrowType(Qt.ArrowType.DownArrow)
            self.config_frame.show()

    def create_widget_for_config(self):
        """根据 config 的键值对类型生成对应的输入控件"""
        widgets = []
        for key, value in self.trigger.config.items():
            if isinstance(value, bool):
                widget = ToggleSwitch()
                widget.setOn(value)
                widget.stateChanged.connect(lambda v: self.trigger.set(key, v))
                widgets.append((key, widget))
            elif isinstance(value, int):
                widget = QSpinBox()
                widget.setValue(value)
                widget.valueChanged.connect(lambda v: self.trigger.set(key, v))
                widgets.append((key, widget))
            else:  # 默认当作字符串处理
                widget = QLineEdit()
                widget.setText(str(value))
                widget.textChanged.connect(lambda v: self.trigger.set(key, v))
                widgets.append((key, widget))
        return widgets
