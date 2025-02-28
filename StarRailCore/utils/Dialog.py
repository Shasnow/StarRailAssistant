from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import QDialogButtonBox, QDialog, QVBoxLayout, QLabel, QScrollArea, QWidget, QGridLayout, \
    QSpacerItem, QSizePolicy, QFrame

from StarRailCore.utils.Configure import load, save
from StarRailCore.utils.WindowsProcess import Popen


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

    def __init__(self, parent, title, text, announcement_type):
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
        self.frame.setStyleSheet("border-image: url(res/Robin.gif) 0 0 0 0 stretch stretch;")

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
