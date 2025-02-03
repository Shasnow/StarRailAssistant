import os

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QDialogButtonBox, QLineEdit, QComboBox, QSpinBox, QFrame
from PySide6.QtUiTools import QUiLoader
from StarRailAssistant.utils.WindowsProcess import Popen

class FuXuanDivination(QWidget):
    TYPE=["another","luck","item","love","weather","work","money","family","none"]
    METHOD=["time","number"]
    def __init__(self, parent):
        super().__init__(parent)
        self.ui = QUiLoader().load("res/ui/divination.ui")
        self.ui.setWindowIcon(QIcon("res/FuXuan.gif"))
        self.buttonbox:QDialogButtonBox=self.ui.findChild(QDialogButtonBox,"buttonBox")
        self.buttonbox.button(QDialogButtonBox.StandardButton.Ok).setText("占卜")
        self.buttonbox.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        self.buttonbox.accepted.connect(self.accept)
        self.num_frame:QFrame=self.ui.findChild(QFrame,"NumFrame")
        self.num_frame.setVisible(False)
        self.divination_method_combobox:QComboBox=self.ui.findChild(QComboBox, "comboBox_2")
        self.divination_method_combobox.currentIndexChanged.connect(self.method_change)

    def method_change(self,index):
        if index==0:
            self.num_frame.setVisible(False)
        else:
            self.num_frame.setVisible(True)

    def accept(self):
        question_edit:QLineEdit=self.ui.findChild(QLineEdit,"lineEdit")
        question=question_edit.text()
        question_type_combobox:QComboBox=self.ui.findChild(QComboBox,"comboBox_1")
        question_type_combobox.currentIndex()
        question_type=question_type_combobox.currentIndex()
        divination_method_combobox:QComboBox=self.ui.findChild(QComboBox, "comboBox_2")
        divination_method=divination_method_combobox.currentIndex()
        nums=[]
        if divination_method==1:
            for i in range(3):
                spinbox:QSpinBox=self.ui.findChild(QSpinBox,f"spinBox_{i}")
                nums.append(str(spinbox.value()))
        command=f"extension\SRAFuXuanDivination -q {question} -t {self.TYPE[question_type]} -m {self.METHOD[divination_method]} -n {' '.join(nums)}"
        Popen(command)