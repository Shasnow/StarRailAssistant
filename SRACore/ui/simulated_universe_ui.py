# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'simulated_universe.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QSizePolicy, QSpacerItem,
    QSpinBox, QVBoxLayout, QWidget)

class Ui_SimulateUniverseWidget(object):
    def setupUi(self, SimulateUniverseWidget):
        if not SimulateUniverseWidget.objectName():
            SimulateUniverseWidget.setObjectName(u"SimulateUniverseWidget")
        SimulateUniverseWidget.resize(387, 489)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(SimulateUniverseWidget.sizePolicy().hasHeightForWidth())
        SimulateUniverseWidget.setSizePolicy(sizePolicy)
        font = QFont()
        font.setPointSize(13)
        SimulateUniverseWidget.setFont(font)
        SimulateUniverseWidget.setStyleSheet(u"background-repeat: no-repeat;\n"
"                background-position: center;\n"
"                background-color: rgba(255, 255, 255, 0.1);")
        self.verticalLayout_2 = QVBoxLayout(SimulateUniverseWidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.frame_2 = QFrame(SimulateUniverseWidget)
        self.frame_2.setObjectName(u"frame_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_2.sizePolicy().hasHeightForWidth())
        self.frame_2.setSizePolicy(sizePolicy1)
        self.frame_2.setStyleSheet(u"background-repeat: no-repeat;\n"
"                background-position: center;\n"
"                background-color: rgba(255, 255, 255, 0.6);")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label = QLabel(self.frame_2)
        self.label.setObjectName(u"label")

        self.horizontalLayout_2.addWidget(self.label)


        self.verticalLayout_2.addWidget(self.frame_2)

        self.frame_3 = QFrame(SimulateUniverseWidget)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_3)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.frame_4 = QFrame(self.frame_3)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setStyleSheet(u"\n"
"border: 1.4px solid black;  font-size: 16px;background-repeat: no-repeat;\n"
"                background-position: center;\n"
"                background-color: rgba(255, 255, 255, 0.6);")
        self.frame_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout = QGridLayout(self.frame_4)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(self.frame_4)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setStyleSheet(u"border: none;")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 2)

        self.label_4 = QLabel(self.frame_4)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setStyleSheet(u"border: none;")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.label_4, 2, 0, 1, 1)

        self.times = QSpinBox(self.frame_4)
        self.times.setObjectName(u"times")
        sizePolicy.setHeightForWidth(self.times.sizePolicy().hasHeightForWidth())
        self.times.setSizePolicy(sizePolicy)
        self.times.setMaximum(9999)

        self.gridLayout.addWidget(self.times, 2, 1, 1, 1)

        self.label_3 = QLabel(self.frame_4)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setStyleSheet(u"border: none;")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)

        self.game_mode = QComboBox(self.frame_4)
        self.game_mode.addItem("")
        self.game_mode.setObjectName(u"game_mode")
        self.game_mode.setStyleSheet(u"font-weight: bold;\n"
"                                                    QCombox{border: solid black;border-radius: 0;font-weight: bold;}\n"
"                                                    QComboBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    border-color: #bbb;\n"
"                                                    }\n"
"                                                    QComboBox QAbstractItemView {\n"
"                                                    selection-background-color: #f0f0f0; background-color: white;\n"
"                                                    }")

        self.gridLayout.addWidget(self.game_mode, 1, 1, 1, 1)

        self.label_6 = QLabel(self.frame_4)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setStyleSheet(u"border: none;")
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.label_6, 3, 0, 1, 1)

        self.policy_comboBox = QComboBox(self.frame_4)
        self.policy_comboBox.addItem("")
        self.policy_comboBox.addItem("")
        self.policy_comboBox.setObjectName(u"policy_comboBox")
        self.policy_comboBox.setStyleSheet(u"font-weight: bold;\n"
"                                                    QCombox{border: solid black;border-radius: 0;font-weight: bold;}\n"
"                                                    QComboBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    border-color: #bbb;\n"
"                                                    }\n"
"                                                    QComboBox QAbstractItemView {\n"
"                                                    selection-background-color: #f0f0f0; background-color: white;\n"
"                                                    }")

        self.gridLayout.addWidget(self.policy_comboBox, 3, 1, 1, 1)


        self.verticalLayout_3.addWidget(self.frame_4)

        self.label_5 = QLabel(self.frame_3)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setWordWrap(True)

        self.verticalLayout_3.addWidget(self.label_5)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer)


        self.verticalLayout_2.addWidget(self.frame_3)


        self.retranslateUi(SimulateUniverseWidget)

        QMetaObject.connectSlotsByName(SimulateUniverseWidget)
    # setupUi

    def retranslateUi(self, SimulateUniverseWidget):
        SimulateUniverseWidget.setWindowTitle(QCoreApplication.translate("SimulateUniverseWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("SimulateUniverseWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:16pt; font-weight:700;\">\u6a21\u62df\u5b87\u5b99</span></p></body></html>", None))
        self.label_2.setText(QCoreApplication.translate("SimulateUniverseWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:14pt; font-weight:700;\">\u5dee\u5206\u5b87\u5b99\uff1a\u5343\u9762\u82f1\u96c4</span></p></body></html>", None))
        self.label_4.setText(QCoreApplication.translate("SimulateUniverseWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:16pt; font-weight:700;\">\u6b21\u6570\uff1a</span></p></body></html>", None))
        self.label_3.setText(QCoreApplication.translate("SimulateUniverseWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:16pt; font-weight:700;\">\u6a21\u5f0f\uff1a</span></p></body></html>", None))
        self.game_mode.setItemText(0, QCoreApplication.translate("SimulateUniverseWidget", u"\u5237\u5355\u5c42", None))

        self.label_6.setText(QCoreApplication.translate("SimulateUniverseWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:16pt; font-weight:700;\">\u9009\u62e9\u7b56\u7565\uff1a</span></p></body></html>", None))
        self.policy_comboBox.setItemText(0, QCoreApplication.translate("SimulateUniverseWidget", u"\u56fe\u9274\u4f18\u5148", None))
        self.policy_comboBox.setItemText(1, QCoreApplication.translate("SimulateUniverseWidget", u"\u65e0", None))

        self.label_5.setText(QCoreApplication.translate("SimulateUniverseWidget", u"\u8bf7\u81f3\u5c11\u624b\u52a8\u5b8c\u6210\u4e00\u6b21\u4ee5\u6e05\u9664\u6240\u6709\u65b0\u624b\u63d0\u793a\u3002", None))
    # retranslateUi

