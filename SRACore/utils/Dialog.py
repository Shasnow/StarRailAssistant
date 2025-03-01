from PySide6.QtCore import Slot, QTimer
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import QDialogButtonBox, QDialog, QVBoxLayout, QLabel, QScrollArea, QWidget, QGridLayout, \
    QSpacerItem, QSizePolicy, QFrame, QLCDNumber, QHBoxLayout, QPushButton

from SRACore.utils import WindowsPower
from SRACore.utils.Configure import load, save
from SRACore.utils.WindowsProcess import Popen


class DownloadDialog(QDialog):
    def __init__(self, parent, name, url):
        super().__init__(parent)
        self.setFont(QFont("MicroSoft YaHei", 13))
        self.setWindowIcon(QIcon("res/SRAicon.ico"))
        self.setWindowTitle("确认下载")
        self.url = url
        layout = QVBoxLayout(self)
        label = QLabel(f"确认要下载 {name} 吗", self)
        layout.addWidget(label)

        button_box = QDialogButtonBox(self)
        button_box.addButton("确认", QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.accepted.connect(self.ensure)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)
        self.setLayout(layout)

    def ensure(self):
        command = f"SRAUpdater -u {self.url} -np"
        Popen(command)


class AnnouncementDialog(QDialog):

    def __init__(self, parent, title, text, announcement_type, icon):
        super().__init__(parent)
        self.setFont(QFont("MicroSoft YaHei", 13))
        self.setWindowTitle(title)
        self.type=announcement_type
        self.setWindowIcon(QIcon("res/SRAicon.ico"))
        # self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint,False)
        self.resize(500, 500)
        self.setLayout(QVBoxLayout())
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        # self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 600, 600))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.gridLayout.addItem(self.horizontalSpacer, 1, 0, 1, 1)

        self.frame = QFrame(self.scrollAreaWidgetContents)
        self.frame.setFixedSize(100, 100)
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.frame.setStyleSheet(f"border-image: url({icon}) 0 0 0 0 stretch stretch;")

        self.gridLayout.addWidget(self.frame, 1, 1, 1, 1)

        button_box = QDialogButtonBox(self.scrollAreaWidgetContents)
        button_box.addButton("确认", QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton("不再提醒", QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.rejected.connect(self.no_notice)
        self.gridLayout.addWidget(button_box, 1, 2, 1, 1)

        self.label = QLabel(self.scrollAreaWidgetContents)
        self.label.setOpenExternalLinks(True)
        self.label.setAutoFillBackground(True)
        self.label.setWordWrap(True)
        self.label.setText(text)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 3)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.layout().addWidget(self.scrollArea)

    @Slot()
    def no_notice(self):
        version=load("version.json")
        version[f"{self.type}.DoNotShowAgain"]=True
        save(version,"version.json")


class ShutdownDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("关机")
        self.setWindowIcon(QIcon("res/SRAicon.ico"))
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
        self.pushButton.clicked.connect(WindowsPower.shutdown_cancel)
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