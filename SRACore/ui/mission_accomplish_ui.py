# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mission_accomplish.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QRadioButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_MissionAccomplishWidget(object):
    def setupUi(self, MissionAccomplishWidget):
        if not MissionAccomplishWidget.objectName():
            MissionAccomplishWidget.setObjectName(u"MissionAccomplishWidget")
        MissionAccomplishWidget.resize(400, 685)
        font = QFont()
        font.setPointSize(13)
        MissionAccomplishWidget.setFont(font)
        MissionAccomplishWidget.setStyleSheet(u"\u80cc\u666f\uff1abackground-repeat: no-repeat;\n"
"                background-position: center;\n"
"                background-color: rgba(255, 255, 255, 0.1);")
        self.gridLayout = QGridLayout(MissionAccomplishWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.title_frame = QFrame(MissionAccomplishWidget)
        self.title_frame.setObjectName(u"title_frame")
        self.title_frame.setStyleSheet(u"border-radius: 8px;\n"
"border: 1.2px solid black;\n"
"background-color: rgba(255, 255, 255, 0.8);")
        self.title_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.title_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.title_frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.title_label = QLabel(self.title_frame)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setStyleSheet(u"border:none")

        self.horizontalLayout.addWidget(self.title_label)


        self.gridLayout.addWidget(self.title_frame, 0, 0, 1, 1)

        self.body_frame = QFrame(MissionAccomplishWidget)
        self.body_frame.setObjectName(u"body_frame")
        self.body_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.body_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.body_frame)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.frame2_1 = QFrame(self.body_frame)
        self.frame2_1.setObjectName(u"frame2_1")
        self.frame2_1.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame2_1.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout = QVBoxLayout(self.frame2_1)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(self.frame2_1)
        self.label.setObjectName(u"label")
        self.label.setMinimumSize(QSize(0, 25))

        self.verticalLayout.addWidget(self.label)

        self.log_out_checkbox = QCheckBox(self.frame2_1)
        self.log_out_checkbox.setObjectName(u"log_out_checkbox")
        self.log_out_checkbox.setStyleSheet(u"QCheckBox{border: none;background-color: rgba(255,\n"
"                                                    255, 255, 0.8);font-size: 14px;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.verticalLayout.addWidget(self.log_out_checkbox)

        self.quit_game_checkbox = QCheckBox(self.frame2_1)
        self.quit_game_checkbox.setObjectName(u"quit_game_checkbox")
        self.quit_game_checkbox.setStyleSheet(u"QCheckBox{border: none;background-color: rgba(255,\n"
"                                                    255, 255, 0.8);font-size: 14px;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.verticalLayout.addWidget(self.quit_game_checkbox)

        self.line = QFrame(self.frame2_1)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.quit_sra_checkbox = QCheckBox(self.frame2_1)
        self.quit_sra_checkbox.setObjectName(u"quit_sra_checkbox")
        self.quit_sra_checkbox.setMinimumSize(QSize(0, 30))
        self.quit_sra_checkbox.setStyleSheet(u"QCheckBox{border: none;background-color: rgba(255,\n"
"                                                    255, 255, 0.8);font-size: 14px;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.verticalLayout.addWidget(self.quit_sra_checkbox)

        self.shutdown_button = QRadioButton(self.frame2_1)
        self.shutdown_button.setObjectName(u"shutdown_button")
        self.shutdown_button.setMinimumSize(QSize(0, 30))
        self.shutdown_button.setStyleSheet(u"\n"
"QPUSHBOTTON:QPushButton {font-size:14px;font-weight: bold\uff1b}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.verticalLayout.addWidget(self.shutdown_button)

        self.hibernate_button = QRadioButton(self.frame2_1)
        self.hibernate_button.setObjectName(u"hibernate_button")
        self.hibernate_button.setMinimumSize(QSize(0, 30))
        self.hibernate_button.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:14px;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.verticalLayout.addWidget(self.hibernate_button)

        self.radioButton = QRadioButton(self.frame2_1)
        self.radioButton.setObjectName(u"radioButton")
        self.radioButton.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:14px;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.verticalLayout.addWidget(self.radioButton)


        self.verticalLayout_3.addWidget(self.frame2_1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer)


        self.gridLayout.addWidget(self.body_frame, 1, 0, 1, 1)


        self.retranslateUi(MissionAccomplishWidget)

        QMetaObject.connectSlotsByName(MissionAccomplishWidget)
    # setupUi

    def retranslateUi(self, MissionAccomplishWidget):
        MissionAccomplishWidget.setWindowTitle(QCoreApplication.translate("MissionAccomplishWidget", u"Form", None))
        self.title_label.setText(QCoreApplication.translate("MissionAccomplishWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:16pt;\">\u4efb\u52a1\u7ed3\u675f</span></p></body></html>", None))
        self.label.setText(QCoreApplication.translate("MissionAccomplishWidget", u"<html><head/><body><p><span style=\" font-size:14pt; font-weight:700;\">\u4efb\u52a1\u7ed3\u675f\u540e\uff1a</span></p></body></html>", None))
        self.log_out_checkbox.setText(QCoreApplication.translate("MissionAccomplishWidget", u"\u767b\u51fa\u5f53\u524d\u8d26\u53f7", None))
        self.quit_game_checkbox.setText(QCoreApplication.translate("MissionAccomplishWidget", u"\u9000\u51fa\u6e38\u620f", None))
        self.quit_sra_checkbox.setText(QCoreApplication.translate("MissionAccomplishWidget", u"\u9000\u51faSRA", None))
        self.shutdown_button.setText(QCoreApplication.translate("MissionAccomplishWidget", u"\u5173\u673a", None))
        self.hibernate_button.setText(QCoreApplication.translate("MissionAccomplishWidget", u"\u4f11\u7720", None))
        self.radioButton.setText(QCoreApplication.translate("MissionAccomplishWidget", u"\u65e0\u52a8\u4f5c", None))
    # retranslateUi

