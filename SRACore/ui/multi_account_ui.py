# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'multi_account.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QGroupBox, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

class Ui_MultiAccountWidget(object):
    def setupUi(self, MultiAccountWidget):
        if not MultiAccountWidget.objectName():
            MultiAccountWidget.setObjectName(u"MultiAccountWidget")
        MultiAccountWidget.resize(526, 586)
        font = QFont()
        font.setPointSize(13)
        MultiAccountWidget.setFont(font)
        self.verticalLayout = QVBoxLayout(MultiAccountWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.scrollArea = QScrollArea(MultiAccountWidget)
        self.scrollArea.setObjectName(u"scrollArea")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea.sizePolicy().hasHeightForWidth())
        self.scrollArea.setSizePolicy(sizePolicy)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_4 = QWidget()
        self.scrollAreaWidgetContents_4.setObjectName(u"scrollAreaWidgetContents_4")
        self.scrollAreaWidgetContents_4.setGeometry(QRect(0, 0, 506, 116))
        self.verticalLayout_4 = QVBoxLayout(self.scrollAreaWidgetContents_4)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.groupBox = QGroupBox(self.scrollAreaWidgetContents_4)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setStyleSheet(u"\n"
"background-color: rgba(255, 255, 255, 0.6);\n"
"border: 1.4px solid black;  font-size: 16px;")
        self.gridLayout_5 = QGridLayout(self.groupBox)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.new_plan_button = QPushButton(self.groupBox)
        self.new_plan_button.setObjectName(u"new_plan_button")
        self.new_plan_button.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:16px;font-weight: bold;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.gridLayout_5.addWidget(self.new_plan_button, 1, 0, 1, 1)

        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"border: none;   background-color: transparent")

        self.gridLayout_5.addWidget(self.label, 0, 0, 1, 1)

        self.current_config_combobox = QComboBox(self.groupBox)
        self.current_config_combobox.setObjectName(u"current_config_combobox")
        self.current_config_combobox.setStyleSheet(u"font-weight: bold;\n"
"                                                    QCombox{border: solid black;border-radius: 0;font-weight: bold;}\n"
"                                                    QComboBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    border-color: #bbb;\n"
"                                                    }\n"
"                                                    QComboBox QAbstractItemView {\n"
"                                                    selection-background-color: #f0f0f0; background-color: white;\n"
"                                                    }")
        self.current_config_combobox.setMaxCount(5)

        self.gridLayout_5.addWidget(self.current_config_combobox, 0, 1, 1, 2)

        self.switch2next_checkbox = QCheckBox(self.groupBox)
        self.switch2next_checkbox.setObjectName(u"switch2next_checkbox")
        self.switch2next_checkbox.setStyleSheet(u"QCheckBox{border: none;font-size: 14px;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.gridLayout_5.addWidget(self.switch2next_checkbox, 2, 0, 1, 3)

        self.delete_plan_button = QPushButton(self.groupBox)
        self.delete_plan_button.setObjectName(u"delete_plan_button")
        self.delete_plan_button.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:16px;font-weight: bold;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.gridLayout_5.addWidget(self.delete_plan_button, 1, 1, 1, 1)


        self.verticalLayout_4.addWidget(self.groupBox)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents_4)

        self.verticalLayout.addWidget(self.scrollArea)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(MultiAccountWidget)

        QMetaObject.connectSlotsByName(MultiAccountWidget)
    # setupUi

    def retranslateUi(self, MultiAccountWidget):
        MultiAccountWidget.setWindowTitle(QCoreApplication.translate("MultiAccountWidget", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("MultiAccountWidget", u"\u914d\u7f6e\u65b9\u6848", None))
        self.new_plan_button.setText(QCoreApplication.translate("MultiAccountWidget", u"\u65b0\u5efa\u65b9\u6848", None))
        self.label.setText(QCoreApplication.translate("MultiAccountWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:11pt;\">\u5f53\u524d\u914d\u7f6e\u65b9\u6848</span></p></body></html>", None))
        self.switch2next_checkbox.setText(QCoreApplication.translate("MultiAccountWidget", u"\u5f53\u524d\u65b9\u6848\u7ed3\u675f\u65f6\u5207\u6362\u4e0b\u4e00\u4e2a\u65b9\u6848", None))
        self.delete_plan_button.setText(QCoreApplication.translate("MultiAccountWidget", u"\u5220\u9664\u65b9\u6848", None))
    # retranslateUi

