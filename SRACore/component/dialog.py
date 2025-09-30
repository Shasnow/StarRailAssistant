import json

from PySide6.QtCore import Slot, QTimer, Qt
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import QDialogButtonBox, QDialog, QVBoxLayout, QLabel, QWidget, QGridLayout, \
    QSpacerItem, QSizePolicy, QFrame, QLCDNumber, QHBoxLayout, QPushButton, QListWidget, QStackedWidget, QTextBrowser, \
    QMessageBox, QLineEdit, QTimeEdit, QComboBox

from SRACore.util import system


class Announcement(QWidget):
    def __init__(self, parent=None, title="title", content="text", content_type="text"):
        super().__init__(parent)
        self.title = title
        self.setLayout(QVBoxLayout())
        self.content = QTextBrowser(self)
        self.content.setOpenExternalLinks(True)
        self.content.setAutoFillBackground(True)
        match content_type:
            case "html":
                self.content.setHtml(content)
            case "text":
                self.content.setText(content)
            case "markdown":
                self.content.setMarkdown(content)
            case _:
                self.content.setText(content)
        self.layout().addWidget(self.content)


class AnnouncementBoard(QDialog):
    def __init__(self, parent=None, title="announcements"):
        super().__init__(parent)

        # 主布局
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.resize(600, 500)
        self.setWindowTitle(title)
        self.setFont(QFont("MicroSoft YaHei", 13))
        self.setWindowIcon(QIcon("resources/SRAicon.ico"))
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        # 左侧标题栏
        self.title_list = QListWidget()
        self.title_list.setSpacing(10)
        self.title_list.setFixedWidth(100)  # 固定宽度
        self.title_list.currentRowChanged.connect(self.on_title_clicked)
        self.title_list.addItem("ALL")

        # 右侧内容栏
        right_layout = QGridLayout()
        self.content_stack = QStackedWidget()
        right_layout.addWidget(self.content_stack, 0, 0, 1, 3)
        horizontal_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        right_layout.addItem(horizontal_spacer, 1, 0, 1, 1)
        frame = QFrame(self)
        frame.setFixedSize(100, 100)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Raised)
        frame.setStyleSheet("border-image: url(resources/Robin.gif) 0 0 0 0 stretch stretch;")

        right_layout.addWidget(frame, 1, 1, 1, 1)

        # 按钮箱 - 初始禁用按钮
        self.button_box = QDialogButtonBox(self)
        self.confirm_btn = self.button_box.addButton("确认", QDialogButtonBox.ButtonRole.AcceptRole)
        self.dont_show_btn = self.button_box.addButton("不再提醒", QDialogButtonBox.ButtonRole.RejectRole)
        self.confirm_btn.setEnabled(False)
        self.dont_show_btn.setEnabled(False)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        right_layout.addWidget(self.button_box, 1, 2, 1, 1)

        # 创建ALL公告页面
        self.all = Announcement(None, "ALL", "滚动至底部可关闭公告\n")
        self.content_stack.addWidget(self.all)

        # 存储标题和内容的映射
        self.title_content_map = {"ALL": self.all}

        # 添加到主布局
        self.main_layout.addWidget(self.title_list)
        self.main_layout.addLayout(right_layout)

        # 跟踪当前活动的滚动区域
        self.current_scroll_area = None

        # 连接滚动事件
        self.setup_scroll_handlers()

    def setup_scroll_handlers(self):
        """设置滚动事件处理"""
        # 为ALL页面设置滚动监听
        if hasattr(self.all.content, 'verticalScrollBar'):
            scroll_bar = self.all.content.verticalScrollBar()
            scroll_bar.valueChanged.connect(lambda: self.check_scroll_position("ALL"))

        # 监听内容栈切换事件，以便为新显示的页面设置滚动监听
        self.content_stack.currentChanged.connect(self.on_stack_changed)

    def on_stack_changed(self, index):
        """当切换到新的内容页面时，设置滚动监听"""
        # 移除之前页面的滚动监听
        if self.current_scroll_area and hasattr(self.current_scroll_area, 'verticalScrollBar'):
            scroll_bar = self.current_scroll_area.verticalScrollBar()
            try:
                scroll_bar.valueChanged.disconnect(self.check_current_scroll_position)
            except TypeError:
                pass  # 如果没有连接过，忽略错误

        # 获取当前页面并设置新的滚动监听
        current_widget = self.content_stack.widget(index)
        if current_widget and hasattr(current_widget, 'content') and hasattr(current_widget.content,
                                                                             'verticalScrollBar'):
            self.current_scroll_area = current_widget.content
            scroll_bar = self.current_scroll_area.verticalScrollBar()
            scroll_bar.valueChanged.connect(self.check_current_scroll_position)
            # 检查当前滚动位置
            self.check_current_scroll_position(scroll_bar.value())

    def check_current_scroll_position(self, value):
        """检查当前活动页面的滚动位置"""
        if not self.current_scroll_area:
            return

        current_title = self.title_list.currentItem().text()
        self.check_scroll_position(current_title)

    def check_scroll_position(self, title):
        """检查指定页面是否滚动到底部"""
        # 获取对应页面的内容部件
        if title in self.title_content_map:
            widget = self.title_content_map[title]
            if hasattr(widget.content, 'verticalScrollBar'):
                scroll_bar = widget.content.verticalScrollBar()
                # 检查是否滚动到底部（考虑一定的容差，例如10像素）
                is_at_bottom = (scroll_bar.value() + 10 >= scroll_bar.maximum())
                # 更新按钮状态
                self.confirm_btn.setEnabled(is_at_bottom)
                self.dont_show_btn.setEnabled(is_at_bottom)

    def add(self, dialog: Announcement):
        """添加一个公告条目"""
        # 将标题添加到左侧标题栏
        title = dialog.title
        dialog.setParent(self)
        self.title_list.addItem(title)

        # 将内容添加到右侧内容栏
        self.content_stack.addWidget(dialog)

        # 保存标题和内容的映射关系
        self.title_content_map[title] = dialog
        self.all.content.append(dialog.content.toMarkdown())

        # 为新添加的公告设置滚动监听
        if hasattr(dialog.content, 'verticalScrollBar'):
            scroll_bar = dialog.content.verticalScrollBar()
            scroll_bar.valueChanged.connect(lambda: self.check_scroll_position(title))

        # 重新检查ALL页面的滚动状态，因为内容已更新
        # self.check_scroll_position("ALL")

    @Slot(int)
    def on_title_clicked(self, index):
        """当用户点击左侧标题栏时，切换右侧内容栏"""
        self.content_stack.setCurrentIndex(index)

    def setDefault(self, index: int):
        self.title_list.setCurrentRow(index)
        self.all.content.verticalScrollBar().setValue(0)
        # 确保按钮初始为禁用状态
        self.confirm_btn.setEnabled(False)
        self.dont_show_btn.setEnabled(False)

    def reject(self) -> None:
        with open('version.json', 'r', encoding='utf-8') as f:
            version = json.load(f)
        version[f"Announcement.DoNotShowAgain"] = True
        with open('version.json', 'w', encoding='utf-8') as f:
            json.dump(version, f, indent=4, ensure_ascii=False)
        return super().reject()


class ShutdownDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关机")
        self.setWindowIcon(QIcon("resources/SRAicon.ico"))
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(342, 246)
        self.verticalLayout = QVBoxLayout()
        self.setLayout(self.verticalLayout)
        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.label = QLabel(self.frame)
        font = QFont()
        font.setPointSize(14)
        self.label.setFont(font)
        self.label.setText("您的计算机将在倒计时结束后关机，\n如果要取消关机，请按“取消”")
        self.verticalLayout_2.addWidget(self.label)

        self.lcdNumber = QLCDNumber(self.frame)
        self.lcdNumber.setAutoFillBackground(True)
        self.lcdNumber.setDigitCount(2)
        self.lcdNumber.setSegmentStyle(QLCDNumber.SegmentStyle.Filled)
        self.lcdNumber.setProperty(u"value", 60)

        self.verticalLayout_2.addWidget(self.lcdNumber)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButton = QPushButton(self.frame)
        self.pushButton.setFont(font)
        self.pushButton.setText("取消")
        self.pushButton.clicked.connect(system.shutdown_cancel)
        self.pushButton.clicked.connect(self.close)

        self.horizontalLayout.addWidget(self.pushButton)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.verticalLayout.addWidget(self.frame)

        self.timer = QTimer(self)
        self.pushButton.clicked.connect(self.timer.stop)
        self.timer.timeout.connect(self.update_countdown)
        self.time_left = 60
        self.timer.start(1000)

    def update_countdown(self):
        """更新倒计时"""
        self.time_left -= 1
        if self.time_left < 0:
            self.timer.stop()
            self.lcdNumber.display(00)
            self.close()  # 显示00表示倒计时结束
        else:
            self.lcdNumber.display(self.time_left)

    def show(self, /):
        system.shutdown(60)
        super().show()


class ExceptionMessageBox(QMessageBox):
    def __init__(self, exception, value, traceback):
        super().__init__()
        self.setWindowTitle("喜报")
        self.setWindowIcon(QIcon("resources/SRAicon.ico"))
        self.setIcon(QMessageBox.Icon.Critical)
        self.setFont(QFont("MicroSoft YaHei", 12))
        self.setText("SRA崩溃了! 由于以下未处理的异常: \n"
                     f"    {exception}: {value} \n"
                     "如果无法自行解决，请联系开发者！")
        self.setDetailedText(traceback)
        self.setStandardButtons(QMessageBox.StandardButton.Ok)


class InputDialog(QDialog):
    def __init__(self, parent, title: str, text: str):
        super().__init__(parent)
        self.isAccept = False
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon("resources/SRAicon.ico"))
        self.setLayout(QVBoxLayout())
        self.label = QLabel(self)
        self.label.setText(text)
        self.layout().addWidget(self.label)
        self.line_edit = QLineEdit(self)
        self.layout().addWidget(self.line_edit)
        self.button_box = QDialogButtonBox()
        self.button_box.addButton(QPushButton("确认"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.button_box.addButton(QPushButton("取消"), QDialogButtonBox.ButtonRole.RejectRole)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout().addWidget(self.button_box)

    def accept(self):
        super().accept()
        self.isAccept = True

    @staticmethod
    def getText(parent: QWidget, title: str, text: str):
        dialog = InputDialog(parent, title, text)
        dialog.exec()
        return dialog.line_edit.text(), dialog.isAccept


class MessageBox(QDialog):
    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon("resources/SRAicon.ico"))
        self.setFont(QFont("MicroSoft YaHei", 13))
        self.setLayout(QVBoxLayout())
        self.label = QTextBrowser(self)
        self.label.setOpenExternalLinks(True)
        self.label.setText(text)
        self.layout().addWidget(self.label)
        self.ok_button = QPushButton("确认")
        self.ok_button.clicked.connect(self.accept)
        self.layout().addWidget(self.ok_button)

    @staticmethod
    def info(parent: QWidget | None, title: str, text: str):
        msg = MessageBox(parent, title, text)
        msg.exec()


class ScheduleDialog(QDialog):
    def __init__(self, parent, configs):
        super().__init__(parent)
        self.setWindowIcon(QIcon("resources/SRAicon.ico"))
        self.setWindowTitle("定时任务")
        self.setFont(QFont("Microsoft YaHei", 13))
        layout = QGridLayout(self)

        # Time Widget
        time_widget = QWidget()
        time_layout = QHBoxLayout(time_widget)
        time_layout.addWidget(QLabel("时间"))
        self.time_edit = QTimeEdit()
        time_layout.addWidget(self.time_edit)
        layout.addWidget(time_widget, 3, 0, 1, 2)

        # Button Box
        accept_button = QPushButton("确定")
        reject_button = QPushButton("取消")
        button_box = QDialogButtonBox()
        button_box.setOrientation(Qt.Orientation.Horizontal)
        button_box.addButton(accept_button, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(reject_button, QDialogButtonBox.ButtonRole.RejectRole)
        layout.addWidget(button_box, 6, 0, 1, 2)

        # Frequency Widget
        freq_widget = QWidget()
        freq_layout = QHBoxLayout(freq_widget)
        freq_layout.addWidget(QLabel("频率"))
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(["每天", "每周"])
        self.freq_combo.currentTextChanged.connect(lambda text: self.week_widget.setVisible(text == "每周"))
        freq_layout.addWidget(self.freq_combo)
        layout.addWidget(freq_widget, 0, 0, 1, 2)

        # Week Widget
        self.week_widget = QWidget()
        week_layout = QHBoxLayout(self.week_widget)
        week_layout.addWidget(QLabel("星期"))
        self.week_combo = QComboBox()
        self.week_combo.addItems(["一", "二", "三", "四", "五", "六", "日", ""])
        week_layout.addWidget(self.week_combo)
        self.week_widget.setVisible(False)
        layout.addWidget(self.week_widget, 2, 0, 1, 2)

        # Configuration Widget
        config_widget = QWidget()
        config_layout = QHBoxLayout(config_widget)
        config_layout.addWidget(QLabel("配置"))
        self.config_combo = QComboBox()
        self.config_combo.addItem("全部")
        self.config_combo.addItems(configs)
        config_layout.addWidget(self.config_combo)
        layout.addWidget(config_widget, 5, 0, 1, 2)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    @staticmethod
    def getSchedule(parent, configs):
        dialog = ScheduleDialog(parent, configs)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            freq = dialog.freq_combo.currentText()
            week = dialog.week_combo.currentText()
            time = dialog.time_edit.time().toString("HH:mm")
            config = dialog.config_combo.currentText()
            if freq == "每天":
                return freq, time, config
            else:
                return freq, week, time, config
        return None
