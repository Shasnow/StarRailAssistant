import importlib
import json
import random
import sys
import tomllib

from PySide6.QtCore import Slot, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QFrame, QHBoxLayout, QCheckBox, QPushButton

from SRACore.component.common import SRAComponent
from SRACore.component.dialog import AnnouncementBoard, Announcement, MessageBox, ShutdownDialog
from SRACore.component.multi_account import MultiAccountComponent
from SRACore.component.settings_page import SettingsPageComponent
from SRACore.thread.background_thread import BackgroundThreadWorker
from SRACore.thread.trigger_thread import TriggerThread
from SRACore.ui.main_ui import Ui_MainWindow
from SRACore.util import notify, encryption
from SRACore.util.config import ConfigManager, GlobalConfigManager
from SRACore.util.const import VERSION, RANDOM_TITLE, CORE
from SRACore.util.logger import log_emitter, logger


class MainWindowComponent(QMainWindow):
    """主窗口组件，负责管理和显示各个子组件。"""
    started = Signal()
    require_stop = Signal()

    def __init__(self, parent, global_config_manager: GlobalConfigManager):
        super().__init__(parent)
        self.tray = None
        self.trigger_thread: TriggerThread | None = None
        logger.debug("Initializing MainWindowComponent")
        self.is_running = False
        self.background_thread_worker: BackgroundThreadWorker | None = None
        self.background_thread: QThread | None = None
        log_emitter.log_signal.connect(self.update_log)
        self.gcm = global_config_manager
        self.config_manager = ConfigManager(
            self.gcm.get('config_list', ['default'])[self.gcm.get('current_config', 0)])
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle(f"SRA {VERSION} | {random.choice(RANDOM_TITLE)}")
        self.setWindowIcon(QIcon("resources\\SRAicon.ico"))
        self.setGeometry(*self.gcm.get('geometry', (200, 200, 800, 600)))  # NOQA
        self.components: list[SRAComponent] = list()
        self.frames: list[TaskSelectFrame] = list()
        self.multi_account = MultiAccountComponent(self, self.gcm)
        self.settings = SettingsPageComponent(self, self.gcm)
        self.add_component()
        self.setter()
        self.connector()

        with open('version.json', 'r', encoding='utf-8') as f:
            version = json.load(f)
            if not version['Announcement.DoNotShowAgain']:
                self.announcement()

    def set_background_thread(self, thread: QThread, worker: BackgroundThreadWorker):
        """设置后台线程和工作类"""

        def hotkey_listener(key: str):
            if key == 'hotkey1':
                if self.is_running:
                    self.stop()
                else:
                    self.start()

        def schedule_listener(config: str):
            if self.is_running:
                logger.info(f"收到定时任务触发信号，当前正在运行任务，跳过执行计划：{config}")
                return
            logger.info(f"收到定时任务触发信号，开始执行计划：{config}")
            if config == "全部":
                self.gcm.set('switch2next', True)
            else:
                self.config_switch(config)
            self.start_exec()

        self.background_thread = thread
        self.background_thread_worker = worker
        self.background_thread_worker.hotkey_triggered.connect(hotkey_listener)
        self.background_thread_worker.schedule_triggered.connect(schedule_listener)
        self.background_thread.start()

    def set_trigger_thread(self, thread):
        self.trigger_thread = thread
        self.trigger_thread.start()

    def add_component(self):
        """添加子组件到主窗口的布局中"""
        self.ui.task_setting_groupBox.layout().setContentsMargins(0, 0, 0, 0)
        with open("SRACore/config.toml", "rb") as f:
            tasks = tomllib.load(f).get("tasks")
            sys.path.append(sys.path[0]+"\\SRACore")
            for task in tasks:
                component = task.get("component")
                component_module = task.get("component_module")
                _module = importlib.import_module(component_module)
                _class = getattr(_module, component)
                if not issubclass(_class, SRAComponent):
                    raise TypeError(f"Component class {component} does not inherit from SRAComponent")
                _instance = _class(self, self.config_manager)
                _frame = TaskSelectFrame(self, meta=task)
                _frame.button.clicked.connect(lambda _, x=len(self.components): self.display(x))
                self.frames.append(_frame)
                self.components.append(_instance)
                self.ui.taskSelectScrollAreaWidgetContents.layout().addWidget(_frame)
                self.ui.task_setting_groupBox.layout().addWidget(_instance)

        self.display(0)
        self.ui.multi_account_tab.layout().setContentsMargins(0, 0, 0, 0)
        self.ui.multi_account_tab.layout().addWidget(self.multi_account)
        self.ui.setting_tab.layout().setContentsMargins(0, 0, 0, 0)
        self.ui.setting_tab.layout().addWidget(self.settings)
        from SRACore.thread.trigger_thread import TriggerManager
        trigger_manager = TriggerManager.get_instance()
        for i in trigger_manager.trigger_widgets:
            self.ui.extension_groupBox.layout().addWidget(i)
        from SRACore.util.plugin import PluginManager, PluginWidget
        PluginManager.load_plugins()
        plugins_widget = PluginWidget(self)
        for name, run in PluginManager.getPlugins().items():
            plugins_widget.addPlugin(name, run)
        self.ui.plugin_groupBox.layout().addWidget(plugins_widget)

    def connector(self):
        """连接信号和槽函数"""
        self.ui.announcement_action.triggered.connect(self.announcement)
        self.ui.about_action.triggered.connect(self.about)
        self.ui.faq_action.triggered.connect(self.problem)
        self.multi_account.config_switched.connect(self.config_switch)
        self.ui.start_pushButton.clicked.connect(self.start)
        self.ui.stop_pushButton.clicked.connect(self.stop)

    def setter(self):
        """设置UI状态"""
        config = self.config_manager.get('main_window', {'task_select': (False, False, False, False, False)})
        for index, frame in enumerate(self.frames):
            frame.checkbox.setChecked(config['task_select'][index])

    def getter(self):
        """获取UI状态并保存到配置中"""

        config = {'task_select': [frame.checkbox.isChecked() for frame in self.frames]}
        self.config_manager.set('main_window', config)

    def get_all(self):
        """获取所有子组件的状态"""
        self.getter()
        for component in self.components:
            component.getter()
        self.multi_account.getter()
        self.settings.getter()

    @Slot(str)
    def config_switch(self, name: str):
        """切换配置"""
        logger.debug(f"Config switch to: {name}")
        self.get_all()
        self.config_manager.switch(name)
        self.setter()
        for component in self.components:
            component.setter()

    def display_none(self):
        for component in self.components:
            component.hide()

    def display(self, index: int):
        """显示指定的子组件，隐藏其他组件"""
        self.display_none()
        self.components[index].show()

    @Slot(str)
    def update_log(self, message: str):
        """更新日志文本框，添加新日志消息。"""
        self.ui.log_textBrowser.append(message.strip())
        self.ui.log_textBrowser.verticalScrollBar().setValue(self.ui.log_textBrowser.verticalScrollBar().maximum())

    @Slot()
    def announcement(self):
        with open('version.json', 'r', encoding='utf-8') as f:
            version = json.load(f)
        announcement_board = AnnouncementBoard(self, "公告栏")
        for anno in version['Announcement']:
            announcement_board.add(Announcement(None, anno['title'], anno['content'], anno.get('contentType','markdown')))
        announcement_board.add(
            Announcement(None, "长期公告", f"<html><i>点击下方按钮关闭公告栏</i>"
                                           "<h4>长期公告</h4>"
                                           f"<h2>SRA崩坏：星穹铁道助手 v{VERSION} by雪影</h2>"
                                           "<h3>使用说明：</h3>"
                                           "<b>重要！推荐调整游戏分辨率为1920*1080并保持游戏窗口无遮挡，注意不要让游戏窗口超出屏幕<br>"
                                           "重要！执行任务时不要进行其他操作！<br></b>"
                                           "<p>声明：本程序<font color='green'>完全免费</font>，仅供学习交流使用。本程序依靠计算机图像识别和模拟操作运行，"
                                           "不会做出任何修改游戏文件、读写游戏内存等任何危害游戏本体的行为。"
                                           "如果您使用此程序，我们认为您充分了解《米哈游游戏使用许可及服务协议》第十条之规定，"
                                           "您在使用此程序中产生的任何问题（除程序错误导致外）与此程序无关，<b>相应的后果由您自行承担</b>。</p>"
                                           "请不要在崩坏：星穹铁道及米哈游在各平台（包括但不限于：米游社、B站、微博）的官方动态下讨论任何关于 SRA 的内容。<br>"
                                           "人话：不要跳脸官方～(∠・ω&lt; )⌒☆</html>")
        )
        announcement_board.show()
        announcement_board.setDefault(0)

    @Slot()
    def about(self):
        MessageBox.info(
            self,
            "关于",
            f"版本：{VERSION}\n"
            f"内核版本：{CORE}"
        )

    @Slot()
    def problem(self):
        MessageBox.info(
            self,
            "常见问题",
            "<a href='https://starrailassistant.top/faq.html'>常见问题自查</a><br><br>"
            "1. 在差分宇宙中因奇物“绝对失败处方(进入战斗时，我方全体有150%的基础概率陷入冻结状态，持续1回合)”"
            "冻结队伍会导致无法开启自动战斗，建议开启游戏的沿用自动战斗设置。\n"
            "2. 游戏画面贴近或超出屏幕显示边缘时功能无法正常执行。\n"
            "3. 在执行“历战余响”时若未选择关卡，会导致程序闪退。\n"
            "关于编队：SRA现在还不会编队，对于除饰品提取以外的战斗功能，使用的是当前出战队伍\n"
            "对于饰品提取，如果没有队伍或者队伍有空位，使用的是预设编队的队伍1（不要改名）\n"
        )

    def save_all(self):
        """保存所有子组件的状态"""
        self.get_all()
        self.config_manager.sync()
        self.gcm.sync()

    def start_exec(self):
        self.started.emit()
        self.is_running = True

    @Slot()
    def start(self):
        self.save_all()
        self.start_exec()

    @Slot()
    def stop(self):
        """停止任务执行，发出 require_stop 信号。"""
        self.require_stop.emit()
        self.is_running = False

    @Slot()
    def finish(self):
        self.ui.start_pushButton.setEnabled(True)
        self.ui.stop_pushButton.setEnabled(False)
        if self.gcm.get("notification_allow"):
            if self.gcm.get("notification_system"):
                self.tray.show_finish_message()
            if self.gcm.get("notification_mail"):
                notify.send_mail("SRA", "SRA通知", "任务执行完成！",
                                 SMTP=self.gcm.get("smtp_server"),
                                 sender=self.gcm.get("sender_email"),
                                 password=encryption.win_decryptor(self.gcm.get("authorization_code")),
                                 receiver=self.gcm.get("receiver_email"))
        self.is_running = False
        after = self.config_manager.get("mission_accomplish")
        if after is None:
            return
        if after["shutdown"]:
            ShutdownDialog(self).show()
        else:
            if after["exit_sra"]:
                self.close()

    def closeEvent(self, event):
        """关闭窗口事件处理，保存配置和窗口状态。"""
        self.get_all()
        self.gcm.set('geometry', (self.geometry().x(),
                                  self.geometry().y(),
                                  self.geometry().width(),
                                  self.geometry().height()))
        self.config_manager.sync()
        self.gcm.sync()
        if self.gcm.get('exit_when_close'):
            self.background_thread_worker.stop()
            self.background_thread.quit()
            self.background_thread.wait()
            self.trigger_thread.stop()
            self.trigger_thread.quit()
            self.trigger_thread.wait(500)
            super().closeEvent(event)
        else:
            event.ignore()
            self.hide()

    def set_tray(self, tray):
        self.tray = tray


class TaskSelectFrame(QFrame):
    def __init__(self, parent=None, meta: dict[str, str] = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)
        self.checkbox = QCheckBox(meta.get("name", "Unnamed Task"))
        self.layout.addWidget(self.checkbox)
        self.button = QPushButton("设置")
        self.layout.addWidget(self.button)
