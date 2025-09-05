# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'settings_page.ui'
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
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QCheckBox, QDoubleSpinBox,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QTableWidget, QTableWidgetItem, QTextBrowser,
    QVBoxLayout, QWidget)

class Ui_SettingWidget(object):
    def setupUi(self, SettingWidget):
        if not SettingWidget.objectName():
            SettingWidget.setObjectName(u"SettingWidget")
        SettingWidget.resize(607, 690)
        self.horizontalLayout = QHBoxLayout(SettingWidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.scrollArea = QScrollArea(SettingWidget)
        self.scrollArea.setObjectName(u"scrollArea")
        font = QFont()
        font.setPointSize(13)
        self.scrollArea.setFont(font)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, -594, 575, 1332))
        self.verticalLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox_2 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_2.setObjectName(u"groupBox_2")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_2.sizePolicy().hasHeightForWidth())
        self.groupBox_2.setSizePolicy(sizePolicy)
        self.groupBox_2.setMaximumSize(QSize(16777215, 200))
        self.groupBox_2.setStyleSheet(u"\n"
"border: 1.4px solid black;  font-size: 16px;")
        self.gridLayout_7 = QGridLayout(self.groupBox_2)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.schedule_list = QListWidget(self.groupBox_2)
        self.schedule_list.setObjectName(u"schedule_list")
        self.schedule_list.setStyleSheet(u"background-repeat: no-repeat;\n"
"                background-position: center;\n"
"                background-color: rgba(255, 255, 255, 0.1);border: none;")

        self.gridLayout_7.addWidget(self.schedule_list, 0, 0, 1, 1)

        self.schedule_add_button = QPushButton(self.groupBox_2)
        self.schedule_add_button.setObjectName(u"schedule_add_button")
        self.schedule_add_button.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:14px;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.gridLayout_7.addWidget(self.schedule_add_button, 1, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_2)

        self.groupBox_6 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.groupBox_6.setStyleSheet(u"\n"
"border: 1.4px solid black;  font-size:9px;")
        self.gridLayout_6 = QGridLayout(self.groupBox_6)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.key_tableWidget = QTableWidget(self.groupBox_6)
        if (self.key_tableWidget.columnCount() < 4):
            self.key_tableWidget.setColumnCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        __qtablewidgetitem.setFont(font);
        self.key_tableWidget.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        __qtablewidgetitem1.setFont(font);
        self.key_tableWidget.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        __qtablewidgetitem2.setFont(font);
        self.key_tableWidget.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        __qtablewidgetitem3.setFont(font);
        self.key_tableWidget.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        if (self.key_tableWidget.rowCount() < 1):
            self.key_tableWidget.setRowCount(1)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.key_tableWidget.setVerticalHeaderItem(0, __qtablewidgetitem4)
        brush = QBrush(QColor(0, 0, 0, 255))
        brush.setStyle(Qt.BrushStyle.NoBrush)
        __qtablewidgetitem5 = QTableWidgetItem()
        __qtablewidgetitem5.setForeground(brush);
        self.key_tableWidget.setItem(0, 0, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.key_tableWidget.setItem(0, 1, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.key_tableWidget.setItem(0, 2, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.key_tableWidget.setItem(0, 3, __qtablewidgetitem8)
        self.key_tableWidget.setObjectName(u"key_tableWidget")
        self.key_tableWidget.setMinimumSize(QSize(0, 80))
        self.key_tableWidget.setMaximumSize(QSize(16777215, 100))
        self.key_tableWidget.horizontalHeader().setDefaultSectionSize(175)
        self.key_tableWidget.horizontalHeader().setStretchLastSection(True)
        self.key_tableWidget.verticalHeader().setMinimumSectionSize(30)

        self.gridLayout_6.addWidget(self.key_tableWidget, 1, 0, 1, 2)

        self.horizontalSpacer_4 = QSpacerItem(793, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_6.addItem(self.horizontalSpacer_4, 2, 0, 1, 1)

        self.reset_pushButton = QPushButton(self.groupBox_6)
        self.reset_pushButton.setObjectName(u"reset_pushButton")
        self.reset_pushButton.setMinimumSize(QSize(100, 0))
        self.reset_pushButton.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:14px;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.gridLayout_6.addWidget(self.reset_pushButton, 2, 1, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_6)

        self.hotkey_setting = QGroupBox(self.scrollAreaWidgetContents)
        self.hotkey_setting.setObjectName(u"hotkey_setting")
        self.hotkey_setting.setStyleSheet(u"\n"
"border: 1.4px solid black;  font-size: 10px;")
        self.horizontalLayout_6 = QHBoxLayout(self.hotkey_setting)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.label_5 = QLabel(self.hotkey_setting)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setStyleSheet(u"border: none;font-size: 16px;")

        self.horizontalLayout_6.addWidget(self.label_5)

        self.hotkey1 = QLineEdit(self.hotkey_setting)
        self.hotkey1.setObjectName(u"hotkey1")

        self.horizontalLayout_6.addWidget(self.hotkey1)

        self.label_4 = QLabel(self.hotkey_setting)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setStyleSheet(u"border: none;font-size: 16px;")

        self.horizontalLayout_6.addWidget(self.label_4)

        self.hotkey2 = QLineEdit(self.hotkey_setting)
        self.hotkey2.setObjectName(u"hotkey2")

        self.horizontalLayout_6.addWidget(self.hotkey2)


        self.verticalLayout.addWidget(self.hotkey_setting)

        self.groupBox = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setStyleSheet(u"\n"
"border: 1.4px solid black;  font-size: 16px;")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.frame_6 = QFrame(self.groupBox)
        self.frame_6.setObjectName(u"frame_6")
        self.frame_6.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_6.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_8 = QHBoxLayout(self.frame_6)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.system_notification_checkbox = QCheckBox(self.frame_6)
        self.system_notification_checkbox.setObjectName(u"system_notification_checkbox")
        self.system_notification_checkbox.setStyleSheet(u"border: none;")

        self.horizontalLayout_8.addWidget(self.system_notification_checkbox)


        self.gridLayout.addWidget(self.frame_6, 1, 0, 1, 1)

        self.frame_5 = QFrame(self.groupBox)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_7 = QHBoxLayout(self.frame_5)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.notification_allow_checkbox = QCheckBox(self.frame_5)
        self.notification_allow_checkbox.setObjectName(u"notification_allow_checkbox")
        self.notification_allow_checkbox.setStyleSheet(u"border: none;")

        self.horizontalLayout_7.addWidget(self.notification_allow_checkbox)


        self.gridLayout.addWidget(self.frame_5, 0, 0, 1, 1)

        self.mail_notification_frame = QFrame(self.groupBox)
        self.mail_notification_frame.setObjectName(u"mail_notification_frame")
        self.mail_notification_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.mail_notification_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_4 = QGridLayout(self.mail_notification_frame)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.receiver_email = QLineEdit(self.mail_notification_frame)
        self.receiver_email.setObjectName(u"receiver_email")

        self.gridLayout_4.addWidget(self.receiver_email, 3, 1, 1, 1)

        self.label_6 = QLabel(self.mail_notification_frame)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setStyleSheet(u"border: none;")

        self.gridLayout_4.addWidget(self.label_6, 0, 0, 1, 1)

        self.authorization_code = QLineEdit(self.mail_notification_frame)
        self.authorization_code.setObjectName(u"authorization_code")
        self.authorization_code.setEchoMode(QLineEdit.EchoMode.Password)

        self.gridLayout_4.addWidget(self.authorization_code, 2, 1, 1, 1)

        self.label_7 = QLabel(self.mail_notification_frame)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setStyleSheet(u"border: none;")

        self.gridLayout_4.addWidget(self.label_7, 1, 0, 1, 1)

        self.smtp_server = QLineEdit(self.mail_notification_frame)
        self.smtp_server.setObjectName(u"smtp_server")

        self.gridLayout_4.addWidget(self.smtp_server, 0, 1, 1, 1)

        self.sender_email = QLineEdit(self.mail_notification_frame)
        self.sender_email.setObjectName(u"sender_email")

        self.gridLayout_4.addWidget(self.sender_email, 1, 1, 1, 1)

        self.label_8 = QLabel(self.mail_notification_frame)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setStyleSheet(u"border: none;")

        self.gridLayout_4.addWidget(self.label_8, 2, 0, 1, 1)

        self.label_9 = QLabel(self.mail_notification_frame)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setStyleSheet(u"border: none;")

        self.gridLayout_4.addWidget(self.label_9, 3, 0, 1, 1)

        self.email_check_button = QPushButton(self.mail_notification_frame)
        self.email_check_button.setObjectName(u"email_check_button")
        self.email_check_button.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:14px;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.gridLayout_4.addWidget(self.email_check_button, 4, 0, 1, 1)


        self.gridLayout.addWidget(self.mail_notification_frame, 3, 0, 1, 2)

        self.frame_7 = QFrame(self.groupBox)
        self.frame_7.setObjectName(u"frame_7")
        self.frame_7.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_7.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_9 = QHBoxLayout(self.frame_7)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.mail_notification_checkbox = QCheckBox(self.frame_7)
        self.mail_notification_checkbox.setObjectName(u"mail_notification_checkbox")
        self.mail_notification_checkbox.setStyleSheet(u"border: none;")

        self.horizontalLayout_9.addWidget(self.mail_notification_checkbox)


        self.gridLayout.addWidget(self.frame_7, 1, 1, 1, 1)


        self.verticalLayout.addWidget(self.groupBox)

        self.groupBox_7 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_7.setObjectName(u"groupBox_7")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.groupBox_7.sizePolicy().hasHeightForWidth())
        self.groupBox_7.setSizePolicy(sizePolicy1)
        self.groupBox_7.setStyleSheet(u"\n"
"border: 1.4px solid black;  font-size: 16px;")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox_7)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.frame_8 = QFrame(self.groupBox_7)
        self.frame_8.setObjectName(u"frame_8")
        self.frame_8.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_8.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_10 = QHBoxLayout(self.frame_8)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.label_10 = QLabel(self.frame_8)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setStyleSheet(u"border: none;")

        self.horizontalLayout_10.addWidget(self.label_10)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_10.addItem(self.horizontalSpacer_8)

        self.integrityCheckButton = QPushButton(self.frame_8)
        self.integrityCheckButton.setObjectName(u"integrityCheckButton")
        sizePolicy1.setHeightForWidth(self.integrityCheckButton.sizePolicy().hasHeightForWidth())
        self.integrityCheckButton.setSizePolicy(sizePolicy1)
        self.integrityCheckButton.setMinimumSize(QSize(130, 46))
        self.integrityCheckButton.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:14px;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.horizontalLayout_10.addWidget(self.integrityCheckButton)


        self.verticalLayout_2.addWidget(self.frame_8)

        self.frame_routine_5 = QFrame(self.groupBox_7)
        self.frame_routine_5.setObjectName(u"frame_routine_5")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.frame_routine_5.sizePolicy().hasHeightForWidth())
        self.frame_routine_5.setSizePolicy(sizePolicy2)
        self.frame_routine_5.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_routine_5.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_26 = QHBoxLayout(self.frame_routine_5)
        self.horizontalLayout_26.setObjectName(u"horizontalLayout_26")
        self.threadSafety_checkBox = QCheckBox(self.frame_routine_5)
        self.threadSafety_checkBox.setObjectName(u"threadSafety_checkBox")
        self.threadSafety_checkBox.setStyleSheet(u"border: none;")

        self.horizontalLayout_26.addWidget(self.threadSafety_checkBox)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_26.addItem(self.horizontalSpacer_3)


        self.verticalLayout_2.addWidget(self.frame_routine_5)

        self.frame_routine_3 = QFrame(self.groupBox_7)
        self.frame_routine_3.setObjectName(u"frame_routine_3")
        sizePolicy2.setHeightForWidth(self.frame_routine_3.sizePolicy().hasHeightForWidth())
        self.frame_routine_3.setSizePolicy(sizePolicy2)
        self.frame_routine_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_routine_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_24 = QHBoxLayout(self.frame_routine_3)
        self.horizontalLayout_24.setObjectName(u"horizontalLayout_24")
        self.startup_checkBox = QCheckBox(self.frame_routine_3)
        self.startup_checkBox.setObjectName(u"startup_checkBox")
        self.startup_checkBox.setEnabled(True)
        self.startup_checkBox.setStyleSheet(u"border: none;")
        self.startup_checkBox.setCheckable(True)

        self.horizontalLayout_24.addWidget(self.startup_checkBox)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_24.addItem(self.horizontalSpacer)


        self.verticalLayout_2.addWidget(self.frame_routine_3)

        self.frame_routine_4 = QFrame(self.groupBox_7)
        self.frame_routine_4.setObjectName(u"frame_routine_4")
        sizePolicy2.setHeightForWidth(self.frame_routine_4.sizePolicy().hasHeightForWidth())
        self.frame_routine_4.setSizePolicy(sizePolicy2)
        self.frame_routine_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_routine_4.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_25 = QHBoxLayout(self.frame_routine_4)
        self.horizontalLayout_25.setObjectName(u"horizontalLayout_25")
        self.autoUpdate_checkBox = QCheckBox(self.frame_routine_4)
        self.autoUpdate_checkBox.setObjectName(u"autoUpdate_checkBox")
        self.autoUpdate_checkBox.setStyleSheet(u"border: none;")

        self.horizontalLayout_25.addWidget(self.autoUpdate_checkBox)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_25.addItem(self.horizontalSpacer_2)


        self.verticalLayout_2.addWidget(self.frame_routine_4)

        self.frame_2 = QFrame(self.groupBox_7)
        self.frame_2.setObjectName(u"frame_2")
        sizePolicy2.setHeightForWidth(self.frame_2.sizePolicy().hasHeightForWidth())
        self.frame_2.setSizePolicy(sizePolicy2)
        self.frame_2.setMinimumSize(QSize(224, 0))
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_2 = QLabel(self.frame_2)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setStyleSheet(u"border: none;")

        self.horizontalLayout_4.addWidget(self.label_2)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_6)

        self.zoomSpinBox = QDoubleSpinBox(self.frame_2)
        self.zoomSpinBox.setObjectName(u"zoomSpinBox")
        sizePolicy1.setHeightForWidth(self.zoomSpinBox.sizePolicy().hasHeightForWidth())
        self.zoomSpinBox.setSizePolicy(sizePolicy1)
        self.zoomSpinBox.setMinimumSize(QSize(100, 0))
        self.zoomSpinBox.setMinimum(1.000000000000000)
        self.zoomSpinBox.setMaximum(5.000000000000000)
        self.zoomSpinBox.setSingleStep(0.250000000000000)
        self.zoomSpinBox.setStepType(QAbstractSpinBox.StepType.DefaultStepType)
        self.zoomSpinBox.setValue(1.500000000000000)

        self.horizontalLayout_4.addWidget(self.zoomSpinBox)


        self.verticalLayout_2.addWidget(self.frame_2)

        self.frame = QFrame(self.groupBox_7)
        self.frame.setObjectName(u"frame")
        sizePolicy2.setHeightForWidth(self.frame.sizePolicy().hasHeightForWidth())
        self.frame.setSizePolicy(sizePolicy2)
        self.frame.setMinimumSize(QSize(224, 0))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"border: none;")

        self.horizontalLayout_2.addWidget(self.label)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_5)

        self.confidenceSpinBox = QDoubleSpinBox(self.frame)
        self.confidenceSpinBox.setObjectName(u"confidenceSpinBox")
        sizePolicy1.setHeightForWidth(self.confidenceSpinBox.sizePolicy().hasHeightForWidth())
        self.confidenceSpinBox.setSizePolicy(sizePolicy1)
        self.confidenceSpinBox.setMinimumSize(QSize(100, 0))
        self.confidenceSpinBox.setMinimum(0.010000000000000)
        self.confidenceSpinBox.setMaximum(1.000000000000000)
        self.confidenceSpinBox.setSingleStep(0.010000000000000)
        self.confidenceSpinBox.setValue(0.900000000000000)

        self.horizontalLayout_2.addWidget(self.confidenceSpinBox)


        self.verticalLayout_2.addWidget(self.frame)

        self.frame_4 = QFrame(self.groupBox_7)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_4)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.exit_when_close_checkBox = QCheckBox(self.frame_4)
        self.exit_when_close_checkBox.setObjectName(u"exit_when_close_checkBox")
        self.exit_when_close_checkBox.setStyleSheet(u"border: none;")

        self.horizontalLayout_3.addWidget(self.exit_when_close_checkBox)


        self.verticalLayout_2.addWidget(self.frame_4)

        self.frame_3 = QFrame(self.groupBox_7)
        self.frame_3.setObjectName(u"frame_3")
        sizePolicy2.setHeightForWidth(self.frame_3.sizePolicy().hasHeightForWidth())
        self.frame_3.setSizePolicy(sizePolicy2)
        self.frame_3.setMinimumSize(QSize(224, 0))
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_3 = QLabel(self.frame_3)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setStyleSheet(u"border: none;")

        self.horizontalLayout_5.addWidget(self.label_3)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_7)

        self.mirrorchyanCDK_lineEdit = QLineEdit(self.frame_3)
        self.mirrorchyanCDK_lineEdit.setObjectName(u"mirrorchyanCDK_lineEdit")
        self.mirrorchyanCDK_lineEdit.setFrame(False)
        self.mirrorchyanCDK_lineEdit.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)

        self.horizontalLayout_5.addWidget(self.mirrorchyanCDK_lineEdit)


        self.verticalLayout_2.addWidget(self.frame_3)


        self.verticalLayout.addWidget(self.groupBox_7)

        self.groupBox_5 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_5.setObjectName(u"groupBox_5")
        sizePolicy.setHeightForWidth(self.groupBox_5.sizePolicy().hasHeightForWidth())
        self.groupBox_5.setSizePolicy(sizePolicy)
        self.groupBox_5.setStyleSheet(u"\n"
"border: 1.4px solid black;  font-size: 16px;")
        self.gridLayout_3 = QGridLayout(self.groupBox_5)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.textBrowser_tips = QTextBrowser(self.groupBox_5)
        self.textBrowser_tips.setObjectName(u"textBrowser_tips")
        self.textBrowser_tips.setOpenExternalLinks(True)

        self.gridLayout_3.addWidget(self.textBrowser_tips, 0, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_5)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.horizontalLayout.addWidget(self.scrollArea)


        self.retranslateUi(SettingWidget)
        self.mail_notification_checkbox.toggled.connect(self.mail_notification_frame.setVisible)

        QMetaObject.connectSlotsByName(SettingWidget)
    # setupUi

    def retranslateUi(self, SettingWidget):
        SettingWidget.setWindowTitle(QCoreApplication.translate("SettingWidget", u"Form", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("SettingWidget", u"\u5b9a\u65f6\u6267\u884c", None))
        self.schedule_add_button.setText(QCoreApplication.translate("SettingWidget", u"\u6dfb\u52a0", None))
        self.groupBox_6.setTitle(QCoreApplication.translate("SettingWidget", u" \u952e\u4f4d\u8bbe\u7f6e", None))
        ___qtablewidgetitem = self.key_tableWidget.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("SettingWidget", u"\u6d3b\u52a8", None));
        ___qtablewidgetitem1 = self.key_tableWidget.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("SettingWidget", u"\u65e0\u540d\u52cb\u793c", None));
        ___qtablewidgetitem2 = self.key_tableWidget.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("SettingWidget", u"\u8dc3\u8fc1", None));
        ___qtablewidgetitem3 = self.key_tableWidget.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("SettingWidget", u"\u661f\u9645\u548c\u5e73\u6307\u5357", None));
        ___qtablewidgetitem4 = self.key_tableWidget.verticalHeaderItem(0)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("SettingWidget", u"\u952e\u4f4d", None));

        __sortingEnabled = self.key_tableWidget.isSortingEnabled()
        self.key_tableWidget.setSortingEnabled(False)
        self.key_tableWidget.setSortingEnabled(__sortingEnabled)

        self.reset_pushButton.setText(QCoreApplication.translate("SettingWidget", u"\u91cd\u7f6e\u952e\u4f4d", None))
        self.hotkey_setting.setTitle(QCoreApplication.translate("SettingWidget", u"\u70ed\u952e\u8bbe\u7f6e", None))
        self.label_5.setText(QCoreApplication.translate("SettingWidget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">\u5f00\u59cb/\u505c\u6b62 \u4efb\u52a1\uff1a</span></p></body></html>", None))
        self.label_4.setText(QCoreApplication.translate("SettingWidget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">\u663e\u793a/\u9690\u85cf SRA\uff1a</span></p></body></html>", None))
        self.groupBox.setTitle(QCoreApplication.translate("SettingWidget", u"\u901a\u77e5", None))
        self.system_notification_checkbox.setText(QCoreApplication.translate("SettingWidget", u"\u7cfb\u7edf\u901a\u77e5", None))
        self.notification_allow_checkbox.setText(QCoreApplication.translate("SettingWidget", u"\u5141\u8bb8\u901a\u77e5", None))
        self.label_6.setText(QCoreApplication.translate("SettingWidget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">SMTP\u670d\u52a1\u5668\u5730\u5740\uff1a</span></p></body></html>", None))
        self.label_7.setText(QCoreApplication.translate("SettingWidget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">\u53d1\u4ef6\u90ae\u7bb1\u5730\u5740\uff1a</span></p></body></html>", None))
        self.label_8.setText(QCoreApplication.translate("SettingWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u6388\u6743\u7801\uff1a</span></p></body></html>", None))
        self.label_9.setText(QCoreApplication.translate("SettingWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u6536\u4ef6\u90ae\u7bb1\u5730\u5740\uff1a</span></p></body></html>", None))
        self.email_check_button.setText(QCoreApplication.translate("SettingWidget", u"\u9a8c\u8bc1", None))
        self.mail_notification_checkbox.setText(QCoreApplication.translate("SettingWidget", u"\u90ae\u4ef6\u901a\u77e5", None))
        self.groupBox_7.setTitle(QCoreApplication.translate("SettingWidget", u"SRA\u8bbe\u7f6e", None))
        self.label_10.setText(QCoreApplication.translate("SettingWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u6587\u4ef6\u5b8c\u6574\u6027\u68c0\u67e5</span></p></body></html>", None))
#if QT_CONFIG(tooltip)
        self.integrityCheckButton.setToolTip(QCoreApplication.translate("SettingWidget", u"\u70b9\u51fb\u6b64\u6309\u94ae\u5c06\u7acb\u5373\u8fdb\u884c\u6587\u4ef6\u5b8c\u6574\u6027\u68c0\u67e5", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self.integrityCheckButton.setWhatsThis(QCoreApplication.translate("SettingWidget", u"\u70b9\u51fb\u6b64\u6309\u94ae\u5c06\u7acb\u5373\u8fdb\u884c\u6587\u4ef6\u5b8c\u6574\u6027\u68c0\u67e5", None))
#endif // QT_CONFIG(whatsthis)
        self.integrityCheckButton.setText(QCoreApplication.translate("SettingWidget", u"\u7acb\u5373\u68c0\u67e5", None))
#if QT_CONFIG(tooltip)
        self.threadSafety_checkBox.setToolTip(QCoreApplication.translate("SettingWidget", u"\n"
"                                                                    \u5173\u95ed\u6b64\u9009\u9879\u540e\uff0c\u63a7\u5236\u53f0\u7684\u505c\u6b62\u529f\u80fd\u5c06\u4e0d\u518d\u7b49\u5f85\u4efb\u52a1\u7ed3\u675f\u3002\n"
"                                                                ", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self.threadSafety_checkBox.setWhatsThis(QCoreApplication.translate("SettingWidget", u"\n"
"                                                                    \u5173\u95ed\u6b64\u9009\u9879\u540e\uff0c\u63a7\u5236\u53f0\u7684\u505c\u6b62\u529f\u80fd\u5c06\u4e0d\u518d\u7b49\u5f85\u4efb\u52a1\u7ed3\u675f\u3002\n"
"                                                                ", None))
#endif // QT_CONFIG(whatsthis)
        self.threadSafety_checkBox.setText(QCoreApplication.translate("SettingWidget", u"\u7ebf\u7a0b\u5b89\u5168", None))
        self.startup_checkBox.setText(QCoreApplication.translate("SettingWidget", u"\u5f00\u673a\u81ea\u542f\u52a8", None))
        self.autoUpdate_checkBox.setText(QCoreApplication.translate("SettingWidget", u"\u81ea\u52a8\u66f4\u65b0", None))
#if QT_CONFIG(tooltip)
        self.frame_2.setToolTip(QCoreApplication.translate("SettingWidget", u"\u8bf7\u6839\u636e\u5b9e\u9645\u5c4f\u5e55\u7f29\u653e\u8c03\u6574\u6b64\u503c", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self.frame_2.setWhatsThis(QCoreApplication.translate("SettingWidget", u"\u8bf7\u6839\u636e\u5b9e\u9645\u5c4f\u5e55\u7f29\u653e\u8c03\u6574\u6b64\u503c", None))
#endif // QT_CONFIG(whatsthis)
        self.label_2.setText(QCoreApplication.translate("SettingWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u5c4f\u5e55\u7f29\u653e</span></p></body></html>", None))
#if QT_CONFIG(tooltip)
        self.zoomSpinBox.setToolTip(QCoreApplication.translate("SettingWidget", u"\u8bf7\u6839\u636e\u5b9e\u9645\u5c4f\u5e55\u7f29\u653e\u8c03\u6574\u6b64\u503c", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self.zoomSpinBox.setWhatsThis(QCoreApplication.translate("SettingWidget", u"\u8bf7\u6839\u636e\u5b9e\u9645\u5c4f\u5e55\u7f29\u653e\u8c03\u6574\u6b64\u503c", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.frame.setToolTip(QCoreApplication.translate("SettingWidget", u"\u7f6e\u4fe1\u5ea6\u8d8a\u5927\u5bf9\u56fe\u7247\u7cbe\u5ea6\u8981\u6c42\u8d8a\u9ad8", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self.frame.setWhatsThis(QCoreApplication.translate("SettingWidget", u"\u7f6e\u4fe1\u5ea6\u8d8a\u5927\u5bf9\u56fe\u7247\u7cbe\u5ea6\u8981\u6c42\u8d8a\u9ad8", None))
#endif // QT_CONFIG(whatsthis)
        self.label.setText(QCoreApplication.translate("SettingWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u8bc6\u56fe\u7f6e\u4fe1\u5ea6</span></p></body></html>", None))
#if QT_CONFIG(tooltip)
        self.confidenceSpinBox.setToolTip(QCoreApplication.translate("SettingWidget", u"\u7f6e\u4fe1\u5ea6\u8d8a\u5927\u5bf9\u56fe\u7247\u7cbe\u5ea6\u8981\u6c42\u8d8a\u9ad8", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self.confidenceSpinBox.setWhatsThis(QCoreApplication.translate("SettingWidget", u"\u7f6e\u4fe1\u5ea6\u8d8a\u5927\u5bf9\u56fe\u7247\u7cbe\u5ea6\u8981\u6c42\u8d8a\u9ad8", None))
#endif // QT_CONFIG(whatsthis)
        self.exit_when_close_checkBox.setText(QCoreApplication.translate("SettingWidget", u"\u5173\u95ed\u7a97\u53e3\u65f6\u76f4\u63a5\u9000\u51fa", None))
#if QT_CONFIG(tooltip)
        self.frame_3.setToolTip(QCoreApplication.translate("SettingWidget", u"<html><head/><body><p><br/></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self.frame_3.setWhatsThis(QCoreApplication.translate("SettingWidget", u"<html><head/><body><p><br/></p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.label_3.setText(QCoreApplication.translate("SettingWidget", u"MirrorChyanCDK", None))
#if QT_CONFIG(tooltip)
        self.mirrorchyanCDK_lineEdit.setToolTip(QCoreApplication.translate("SettingWidget", u"\u586b\u5199\u540e\u542f\u7528MirrorChyan\u63d0\u4f9b\u7684\u9ad8\u901f\u4e0b\u8f7d\u670d\u52a1", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self.mirrorchyanCDK_lineEdit.setWhatsThis(QCoreApplication.translate("SettingWidget", u"\u586b\u5199\u540e\u542f\u7528MirrorChyan\u63d0\u4f9b\u7684\u9ad8\u901f\u4e0b\u8f7d\u670d\u52a1", None))
#endif // QT_CONFIG(whatsthis)
        self.mirrorchyanCDK_lineEdit.setPlaceholderText(QCoreApplication.translate("SettingWidget", u"CDK", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("SettingWidget", u"tips", None))
        self.textBrowser_tips.setHtml(QCoreApplication.translate("SettingWidget", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Microsoft YaHei UI'; font-size:16px; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:13pt;\">                                                        </span></p>\n"
"<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:13pt;\">\u5982\u679c\u5728\u4f7f\u7528\u4e2d\u9047\u5230\u95ee\u9898\uff0c\u8bf7\u9605\u8bfb</span><a href=\"https://starrail"
                        "assistant.top/faq.html\"><span style=\" font-size:13pt; text-decoration: underline; color:#0078d4;\">\u5e38\u89c1\u95ee\u9898</span></a><span style=\" font-size:13pt;\">                                                        </span></p>\n"
"<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:13pt;\">SRA\u5b8c\u5168\u514d\u8d39\uff0c\u5982\u679c\u60a8\u662f\u901a\u8fc7\u4ed8\u8d39\u6e20\u9053\u83b7\u53d6\u7684\u8be5\u8f6f\u4ef6\uff0c\u8bf7\u53ca\u65f6\u9000\u6b3e\u5e76\u4e3e\u62a5\u5546\u5bb6\u3002                                                        </span></p>\n"
"<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:13pt;\">GitHub\u4e0a\u7684SRA\uff1a</span><a href=\"https://github.com/Shasnow/StarRailAssistant\"><span style=\" font-size:13pt; text-decoration: underline; color:#0078d4;\">ht"
                        "tps://github.com/Shasnow/StarRailAssistant</span></a><span style=\" font-size:13pt;\">                                                        </span></p>\n"
"<p align=\"center\" style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><a href=\"https://starrailassistant.top\"><span style=\" font-size:13pt; text-decoration: underline; color:#0078d4;\">SRA\u5b98\u7f51</span></a><span style=\" font-size:13pt;\">                                                        </span></p>\n"
"<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:13pt;\">\u83b7\u53d6MirrorChyanCDK-&gt;:</span><a href=\"https://mirrorchyan.com/zh/projects?rid=StarRailAssistant&amp;source=sra-app\"><span style=\" font-size:13pt; text-decoration: underline; color:#0078d4;\">Mirror\u9171</span></a>                                                    </p></body></html>", None))
    # retranslateUi

