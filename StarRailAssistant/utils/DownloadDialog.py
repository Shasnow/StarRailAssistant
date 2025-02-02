from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import QDialogButtonBox, QDialog, QVBoxLayout, QLabel
from StarRailAssistant.utils.WindowsProcess import Popen


class DownloadDialog(QDialog):
    def __init__(self,parent,name,url):
        super().__init__(parent)
        self.setFont(QFont("MicroSoft YaHei",13))
        self.setWindowIcon(QIcon("res/img/SRAicon.ico"))
        self.setWindowTitle("确认下载")
        self.url=url
        layout = QVBoxLayout(self)
        label = QLabel(f"确认要下载 {name} 吗", self)
        layout.addWidget(label)

        button_box = QDialogButtonBox(self)
        button_box.addButton("确认",QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton("取消",QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.accepted.connect(self.ensure)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    def ensure(self):
        command=f"SRAUpdater -u {self.url} -np"
        Popen(command)