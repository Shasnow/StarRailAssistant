# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'start_game.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_StartGameWidget(object):
    def setupUi(self, StartGameWidget):
        if not StartGameWidget.objectName():
            StartGameWidget.setObjectName(u"StartGameWidget")
        StartGameWidget.resize(447, 616)
        font = QFont()
        font.setPointSize(13)
        StartGameWidget.setFont(font)
        self.gridLayout_2 = QGridLayout(StartGameWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)

        self.gridLayout_2.addItem(self.verticalSpacer, 2, 0, 1, 1)

        self.frame_1 = QFrame(StartGameWidget)
        self.frame_1.setObjectName(u"frame_1")
        self.frame_1.setStyleSheet(u"background-color: rgba(255, 255, 255, 0.2);")
        self.frame_1.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_1.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_1)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(self.frame_1)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"border:none")

        self.horizontalLayout.addWidget(self.label)


        self.gridLayout_2.addWidget(self.frame_1, 0, 0, 1, 1)

        self.scrollArea = QScrollArea(StartGameWidget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setStyleSheet(u"background-color: rgba(255, 255, 255, 0.6);")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 427, 497))
        self.verticalLayout_3 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.frame2_1 = QFrame(self.scrollAreaWidgetContents)
        self.frame2_1.setObjectName(u"frame2_1")
        self.frame2_1.setStyleSheet(u"\n"
"border: 1.4px solid black;  font-size: 16px;\n"
"                                                      ")
        self.frame2_1.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame2_1.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame2_1)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label2_1 = QLabel(self.frame2_1)
        self.label2_1.setObjectName(u"label2_1")
        self.label2_1.setStyleSheet(u"border:none")

        self.horizontalLayout_4.addWidget(self.label2_1)

        self.channel_comboBox = QComboBox(self.frame2_1)
        self.channel_comboBox.addItem("")
        self.channel_comboBox.addItem("")
        self.channel_comboBox.setObjectName(u"channel_comboBox")
        self.channel_comboBox.setMinimumSize(QSize(0, 30))
        self.channel_comboBox.setStyleSheet(u"font-weight: bold;\n"
"                                                    QCombox{border: solid black;border-radius: 0;font-weight: bold;}\n"
"                                                    QComboBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    border-color: #bbb;\n"
"                                                    }\n"
"                                                    QComboBox QAbstractItemView {\n"
"                                                    selection-background-color: #f0f0f0; background-color: white;\n"
"                                                    }")

        self.horizontalLayout_4.addWidget(self.channel_comboBox)


        self.verticalLayout_3.addWidget(self.frame2_1)

        self.frame_3 = QFrame(self.scrollAreaWidgetContents)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setStyleSheet(u"\n"
"border: 1.4px solid black;  font-size: 16px;")
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.use_launcher_checkbox = QCheckBox(self.frame_3)
        self.use_launcher_checkbox.setObjectName(u"use_launcher_checkbox")
        self.use_launcher_checkbox.setEnabled(False)
        self.use_launcher_checkbox.setMinimumSize(QSize(0, 30))
        self.use_launcher_checkbox.setAutoFillBackground(False)
        self.use_launcher_checkbox.setCheckable(True)
        self.use_launcher_checkbox.setChecked(False)

        self.horizontalLayout_5.addWidget(self.use_launcher_checkbox)


        self.verticalLayout_3.addWidget(self.frame_3)

        self.frame2_2 = QFrame(self.scrollAreaWidgetContents)
        self.frame2_2.setObjectName(u"frame2_2")
        self.frame2_2.setStyleSheet(u"\n"
"border: 1.4px solid black;  font-size: 16px;")
        self.frame2_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame2_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame2_2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.path_label = QLabel(self.frame2_2)
        self.path_label.setObjectName(u"path_label")
        self.path_label.setStyleSheet(u"border:none")

        self.horizontalLayout_2.addWidget(self.path_label)

        self.path_lineEdit = QLineEdit(self.frame2_2)
        self.path_lineEdit.setObjectName(u"path_lineEdit")
        self.path_lineEdit.setMinimumSize(QSize(0, 30))

        self.horizontalLayout_2.addWidget(self.path_lineEdit)

        self.file_pushButton = QPushButton(self.frame2_2)
        self.file_pushButton.setObjectName(u"file_pushButton")
        self.file_pushButton.setMinimumSize(QSize(0, 30))
        self.file_pushButton.setStyleSheet(u"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.horizontalLayout_2.addWidget(self.file_pushButton)


        self.verticalLayout_3.addWidget(self.frame2_2)

        self.frame_2 = QFrame(self.scrollAreaWidgetContents)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout = QVBoxLayout(self.frame_2)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.frame2_3 = QFrame(self.frame_2)
        self.frame2_3.setObjectName(u"frame2_3")
        self.frame2_3.setStyleSheet(u"\n"
"border: 1.4px solid black;  font-size: 16px;")
        self.frame2_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame2_3.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_3 = QGridLayout(self.frame2_3)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.auto_login_checkBox = QCheckBox(self.frame2_3)
        self.auto_login_checkBox.setObjectName(u"auto_login_checkBox")
        self.auto_login_checkBox.setStyleSheet(u"QCheckBox{border: none;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.gridLayout_3.addWidget(self.auto_login_checkBox, 0, 1, 1, 1)

        self.horizontalSpacer2_3 = QSpacerItem(178, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer2_3, 0, 2, 1, 1)

        self.password_toggle_button = QPushButton(self.frame2_3)
        self.password_toggle_button.setObjectName(u"password_toggle_button")
        self.password_toggle_button.setMinimumSize(QSize(100, 30))
        self.password_toggle_button.setStyleSheet(u"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.gridLayout_3.addWidget(self.password_toggle_button, 0, 3, 1, 1)

        self.label_2 = QLabel(self.frame2_3)
        self.label_2.setObjectName(u"label_2")
        font1 = QFont()
        self.label_2.setFont(font1)
        self.label_2.setWordWrap(True)

        self.gridLayout_3.addWidget(self.label_2, 1, 1, 1, 3)

        self.always_logout_checkBox = QCheckBox(self.frame2_3)
        self.always_logout_checkBox.setObjectName(u"always_logout_checkBox")
        self.always_logout_checkBox.setStyleSheet(u"QCheckBox{border: none;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.gridLayout_3.addWidget(self.always_logout_checkBox, 2, 1, 1, 1)


        self.verticalLayout.addWidget(self.frame2_3)

        self.frame2_4 = QFrame(self.frame_2)
        self.frame2_4.setObjectName(u"frame2_4")
        self.frame2_4.setStyleSheet(u"\n"
"border: 1.4px solid black;  font-size: 16px;")
        self.frame2_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame2_4.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout = QGridLayout(self.frame2_4)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label2_4_11 = QLabel(self.frame2_4)
        self.label2_4_11.setObjectName(u"label2_4_11")
        self.label2_4_11.setStyleSheet(u"border:none")

        self.gridLayout.addWidget(self.label2_4_11, 0, 0, 1, 1)

        self.password_lineEdit = QLineEdit(self.frame2_4)
        self.password_lineEdit.setObjectName(u"password_lineEdit")
        self.password_lineEdit.setMinimumSize(QSize(0, 30))
        self.password_lineEdit.setEchoMode(QLineEdit.EchoMode.Password)

        self.gridLayout.addWidget(self.password_lineEdit, 1, 1, 1, 1)

        self.label2_4_21 = QLabel(self.frame2_4)
        self.label2_4_21.setObjectName(u"label2_4_21")
        self.label2_4_21.setStyleSheet(u"border:none")

        self.gridLayout.addWidget(self.label2_4_21, 1, 0, 1, 1)

        self.account_lineEdit = QLineEdit(self.frame2_4)
        self.account_lineEdit.setObjectName(u"account_lineEdit")
        self.account_lineEdit.setMinimumSize(QSize(0, 30))

        self.gridLayout.addWidget(self.account_lineEdit, 0, 1, 1, 1)


        self.verticalLayout.addWidget(self.frame2_4)


        self.verticalLayout_3.addWidget(self.frame_2)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 1, 0, 1, 1)


        self.retranslateUi(StartGameWidget)

        QMetaObject.connectSlotsByName(StartGameWidget)
    # setupUi

    def retranslateUi(self, StartGameWidget):
        StartGameWidget.setWindowTitle(QCoreApplication.translate("StartGameWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("StartGameWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:16pt; font-weight:700;\">\u542f\u52a8\u6e38\u620f</span></p></body></html>", None))
        self.label2_1.setText(QCoreApplication.translate("StartGameWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:14pt; font-weight:700;\">\u6e20\u9053\uff1a</span></p></body></html>", None))
        self.channel_comboBox.setItemText(0, QCoreApplication.translate("StartGameWidget", u"\u5b98\u670d", None))
        self.channel_comboBox.setItemText(1, QCoreApplication.translate("StartGameWidget", u"bilibili", None))

#if QT_CONFIG(tooltip)
        self.use_launcher_checkbox.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.use_launcher_checkbox.setText(QCoreApplication.translate("StartGameWidget", u"\u4f7f\u7528\u542f\u52a8\u5668", None))
        self.path_label.setText(QCoreApplication.translate("StartGameWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u6e38\u620f\u8def\u5f84\uff1a</span></p></body></html>", None))
        self.file_pushButton.setText(QCoreApplication.translate("StartGameWidget", u"\u6d4f\u89c8", None))
        self.auto_login_checkBox.setText(QCoreApplication.translate("StartGameWidget", u"\u81ea\u52a8\u767b\u5f55", None))
        self.password_toggle_button.setText(QCoreApplication.translate("StartGameWidget", u"\u663e\u793a\u5bc6\u7801", None))
        self.label_2.setText(QCoreApplication.translate("StartGameWidget", u"<html><head/><body><p><span style=\" font-size:14pt; font-weight:700;\">\u52fe\u9009\u81ea\u52a8\u767b\u5f55\u8868\u660e\u60a8\u5df2\u9605\u8bfb\u5e76\u540c\u610f\u300a\u7528\u6237\u534f\u8bae\u300b\u548c\u300a\u9690\u79c1\u653f\u7b56\u300b</span></p><p><span style=\" font-weight:700;\"><br/></span></p></body></html>", None))
#if QT_CONFIG(whatsthis)
        self.always_logout_checkBox.setWhatsThis(QCoreApplication.translate("StartGameWidget", u"\u5982\u679c\u542f\u7528\uff0c\u767b\u5f55\u65f6\u4f1a\u767b\u51fa\u5df2\u7ecf\u767b\u5f55\u7684\u8d26\u53f7\u91cd\u65b0\u767b\u5f55\n"
"                                                                ", None))
#endif // QT_CONFIG(whatsthis)
        self.always_logout_checkBox.setText(QCoreApplication.translate("StartGameWidget", u"\u603b\u662f\u91cd\u65b0\u767b\u5f55", None))
        self.label2_4_11.setText(QCoreApplication.translate("StartGameWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u8d26\u53f7\uff1a</span></p></body></html>", None))
        self.label2_4_21.setText(QCoreApplication.translate("StartGameWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u5bc6\u7801\uff1a</span></p></body></html>", None))
    # retranslateUi

