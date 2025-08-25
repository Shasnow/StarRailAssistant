from PySide6.QtWidgets import QDialog

from SRACore.ui.shutdown_dialog_ui import Ui_Dialog


class ShutdownDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)