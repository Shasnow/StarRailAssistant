# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'receive_reward.ui'
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
    QHBoxLayout, QLabel, QScrollArea, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_ReceiveRewardWidget(object):
    def setupUi(self, ReceiveRewardWidget):
        if not ReceiveRewardWidget.objectName():
            ReceiveRewardWidget.setObjectName(u"ReceiveRewardWidget")
        ReceiveRewardWidget.resize(377, 683)
        font = QFont()
        font.setPointSize(13)
        ReceiveRewardWidget.setFont(font)
        ReceiveRewardWidget.setStyleSheet(u"background-color: rgba(255, 255, 255, 0.5);")
        self.gridLayout = QGridLayout(ReceiveRewardWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.scrollArea = QScrollArea(ReceiveRewardWidget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setStyleSheet(u"background-color: rgba(255, 255, 255, 0.1);\n"
"border: 1.35px solid black;  font-size: 16px;")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 357, 610))
        self.verticalLayout_3 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.frame3_1 = QFrame(self.scrollAreaWidgetContents)
        self.frame3_1.setObjectName(u"frame3_1")
        self.frame3_1.setStyleSheet(u"border:none")
        self.frame3_1.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame3_1.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame3_1)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.trailblaze_profile_checkbox = QCheckBox(self.frame3_1)
        self.trailblaze_profile_checkbox.setObjectName(u"trailblaze_profile_checkbox")
        self.trailblaze_profile_checkbox.setMinimumSize(QSize(0, 30))
        self.trailblaze_profile_checkbox.setStyleSheet(u"QCheckBox{border: none;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.horizontalLayout_2.addWidget(self.trailblaze_profile_checkbox)


        self.verticalLayout_3.addWidget(self.frame3_1)

        self.frame3_2 = QFrame(self.scrollAreaWidgetContents)
        self.frame3_2.setObjectName(u"frame3_2")
        self.frame3_2.setStyleSheet(u"border:none")
        self.frame3_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame3_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame3_2)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.assignment_checkbox = QCheckBox(self.frame3_2)
        self.assignment_checkbox.setObjectName(u"assignment_checkbox")
        self.assignment_checkbox.setMinimumSize(QSize(0, 30))
        self.assignment_checkbox.setStyleSheet(u"QCheckBox{border: none;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.horizontalLayout_4.addWidget(self.assignment_checkbox)


        self.verticalLayout_3.addWidget(self.frame3_2)

        self.frame3_3 = QFrame(self.scrollAreaWidgetContents)
        self.frame3_3.setObjectName(u"frame3_3")
        self.frame3_3.setStyleSheet(u"border:none")
        self.frame3_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame3_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_7 = QHBoxLayout(self.frame3_3)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.mail_checkbox = QCheckBox(self.frame3_3)
        self.mail_checkbox.setObjectName(u"mail_checkbox")
        self.mail_checkbox.setMinimumSize(QSize(0, 30))
        self.mail_checkbox.setStyleSheet(u"QCheckBox{border: none;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.horizontalLayout_7.addWidget(self.mail_checkbox)


        self.verticalLayout_3.addWidget(self.frame3_3)

        self.frame3_4 = QFrame(self.scrollAreaWidgetContents)
        self.frame3_4.setObjectName(u"frame3_4")
        self.frame3_4.setStyleSheet(u"border:none")
        self.frame3_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame3_4.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_9 = QHBoxLayout(self.frame3_4)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.daily_reward_checkbox = QCheckBox(self.frame3_4)
        self.daily_reward_checkbox.setObjectName(u"daily_reward_checkbox")
        self.daily_reward_checkbox.setMinimumSize(QSize(0, 30))
        self.daily_reward_checkbox.setStyleSheet(u"QCheckBox{border: none;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.horizontalLayout_9.addWidget(self.daily_reward_checkbox)


        self.verticalLayout_3.addWidget(self.frame3_4)

        self.frame3_5 = QFrame(self.scrollAreaWidgetContents)
        self.frame3_5.setObjectName(u"frame3_5")
        self.frame3_5.setStyleSheet(u"border:none")
        self.frame3_5.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame3_5.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_8 = QHBoxLayout(self.frame3_5)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.nameless_honour_checkbox = QCheckBox(self.frame3_5)
        self.nameless_honour_checkbox.setObjectName(u"nameless_honour_checkbox")
        self.nameless_honour_checkbox.setMinimumSize(QSize(0, 30))
        self.nameless_honour_checkbox.setStyleSheet(u"QCheckBox{border: none;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.horizontalLayout_8.addWidget(self.nameless_honour_checkbox)


        self.verticalLayout_3.addWidget(self.frame3_5)

        self.frame3_6 = QFrame(self.scrollAreaWidgetContents)
        self.frame3_6.setObjectName(u"frame3_6")
        self.frame3_6.setStyleSheet(u"border:none")
        self.frame3_6.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame3_6.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_6 = QHBoxLayout(self.frame3_6)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.gift_of_odyssey_checkbox = QCheckBox(self.frame3_6)
        self.gift_of_odyssey_checkbox.setObjectName(u"gift_of_odyssey_checkbox")
        self.gift_of_odyssey_checkbox.setMinimumSize(QSize(0, 30))
        self.gift_of_odyssey_checkbox.setStyleSheet(u"QCheckBox{border: none;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.horizontalLayout_6.addWidget(self.gift_of_odyssey_checkbox)


        self.verticalLayout_3.addWidget(self.frame3_6)

        self.frame3_7 = QFrame(self.scrollAreaWidgetContents)
        self.frame3_7.setObjectName(u"frame3_7")
        self.frame3_7.setStyleSheet(u"border:none")
        self.frame3_7.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame3_7.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout = QVBoxLayout(self.frame3_7)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.redeem_code_checkbox = QCheckBox(self.frame3_7)
        self.redeem_code_checkbox.setObjectName(u"redeem_code_checkbox")
        self.redeem_code_checkbox.setMinimumSize(QSize(0, 30))
        self.redeem_code_checkbox.setStyleSheet(u"QCheckBox{border: none;}\n"
"                                                    QCheckBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    }\n"
"\n"
"                                                    /* \u52fe\u9009\u6846\u60ac\u505c\u65f6\u8fb9\u6846\u53d8\u8272 */\n"
"                                                    QCheckBox::indicator:hover {\n"
"                                                    border-color: #666;\n"
"                                                    }")

        self.verticalLayout.addWidget(self.redeem_code_checkbox)

        self.redeem_code_textEdit = QTextEdit(self.frame3_7)
        self.redeem_code_textEdit.setObjectName(u"redeem_code_textEdit")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.redeem_code_textEdit.sizePolicy().hasHeightForWidth())
        self.redeem_code_textEdit.setSizePolicy(sizePolicy)

        self.verticalLayout.addWidget(self.redeem_code_textEdit)


        self.verticalLayout_3.addWidget(self.frame3_7)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.scrollArea, 1, 0, 1, 1)

        self.frame = QFrame(ReceiveRewardWidget)
        self.frame.setObjectName(u"frame")
        self.frame.setStyleSheet(u"border-radius: 8px;\n"
"border: 1.2px solid black;\n"
"background-color: rgba(255, 255, 255, 0.4);")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"border:none")

        self.verticalLayout_2.addWidget(self.label)


        self.gridLayout.addWidget(self.frame, 0, 0, 1, 1)


        self.retranslateUi(ReceiveRewardWidget)

        QMetaObject.connectSlotsByName(ReceiveRewardWidget)
    # setupUi

    def retranslateUi(self, ReceiveRewardWidget):
        ReceiveRewardWidget.setWindowTitle(QCoreApplication.translate("ReceiveRewardWidget", u"Form", None))
        self.trailblaze_profile_checkbox.setText(QCoreApplication.translate("ReceiveRewardWidget", u"\u6f2b\u6e38\u7b7e\u8bc1", None))
        self.assignment_checkbox.setText(QCoreApplication.translate("ReceiveRewardWidget", u"\u6d3e\u9063", None))
        self.mail_checkbox.setText(QCoreApplication.translate("ReceiveRewardWidget", u"\u90ae\u4ef6", None))
        self.daily_reward_checkbox.setText(QCoreApplication.translate("ReceiveRewardWidget", u"\u6bcf\u65e5\u5b9e\u8bad", None))
        self.nameless_honour_checkbox.setText(QCoreApplication.translate("ReceiveRewardWidget", u"\u65e0\u540d\u52cb\u793c", None))
        self.gift_of_odyssey_checkbox.setText(QCoreApplication.translate("ReceiveRewardWidget", u"\u5de1\u661f\u4e4b\u793c", None))
        self.redeem_code_checkbox.setText(QCoreApplication.translate("ReceiveRewardWidget", u"\u5151\u6362\u7801", None))
        self.redeem_code_textEdit.setPlaceholderText(QCoreApplication.translate("ReceiveRewardWidget", u"\u5151\u6362\u7801\u586b\u5199\u5904", None))
        self.label.setText(QCoreApplication.translate("ReceiveRewardWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:16pt; font-weight:700;\">\u9886\u53d6\u5956\u52b1</span></p></body></html>", None))
    # retranslateUi

