# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractScrollArea, QApplication, QCheckBox, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QMainWindow,
    QMenu, QMenuBar, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QStatusBar, QTabWidget,
    QTextBrowser, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(660, 665)
        font = QFont()
        font.setPointSize(13)
        MainWindow.setFont(font)
        MainWindow.setStyleSheet(u"background-repeat: no-repeat;\n"
"                background-position: center;\n"
"                background-color: rgba(255, 255, 255, 0.2);")
        self.announcement_action = QAction(MainWindow)
        self.announcement_action.setObjectName(u"announcement_action")
        self.faq_action = QAction(MainWindow)
        self.faq_action.setObjectName(u"faq_action")
        self.feedback_action = QAction(MainWindow)
        self.feedback_action.setObjectName(u"feedback_action")
        self.about_action = QAction(MainWindow)
        self.about_action.setObjectName(u"about_action")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setStyleSheet(u"border-radius: 0;")
        self.console_tab = QWidget()
        self.console_tab.setObjectName(u"console_tab")
        self.gridLayout_2 = QGridLayout(self.console_tab)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.task_select_groupBox = QGroupBox(self.console_tab)
        self.task_select_groupBox.setObjectName(u"task_select_groupBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.task_select_groupBox.sizePolicy().hasHeightForWidth())
        self.task_select_groupBox.setSizePolicy(sizePolicy)
        self.task_select_groupBox.setMinimumSize(QSize(0, 0))
        self.task_select_groupBox.setMaximumSize(QSize(16777215, 16777215))
        self.task_select_groupBox.setStyleSheet(u"background-color: transparent")
        self.horizontalLayout_23 = QHBoxLayout(self.task_select_groupBox)
        self.horizontalLayout_23.setObjectName(u"horizontalLayout_23")
        self.task_select_scrollArea = QScrollArea(self.task_select_groupBox)
        self.task_select_scrollArea.setObjectName(u"task_select_scrollArea")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.task_select_scrollArea.sizePolicy().hasHeightForWidth())
        self.task_select_scrollArea.setSizePolicy(sizePolicy1)
        self.task_select_scrollArea.setMinimumSize(QSize(225, 0))
        self.task_select_scrollArea.setMaximumSize(QSize(225, 16777215))
        self.task_select_scrollArea.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.task_select_scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 225, 427))
        self.verticalLayout_6 = QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.frame1_1 = QFrame(self.scrollAreaWidgetContents_2)
        self.frame1_1.setObjectName(u"frame1_1")
        self.frame1_1.setStyleSheet(u"border-radius: 8px;\n"
"border: 1.2px solid black;\n"
"background-color: rgba(255, 255, 255, 0.8);\n"
"  font-size: 16px;")
        self.frame1_1.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame1_1.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame1_1)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.start_game_checkBox = QCheckBox(self.frame1_1)
        self.start_game_checkBox.setObjectName(u"start_game_checkBox")
        self.start_game_checkBox.setMinimumSize(QSize(0, 30))
        self.start_game_checkBox.setStyleSheet(u"checkbox1\uff1afont-size: 14px;border: none;font-weight:bold;")

        self.horizontalLayout.addWidget(self.start_game_checkBox)

        self.start_game_pushButton = QPushButton(self.frame1_1)
        self.start_game_pushButton.setObjectName(u"start_game_pushButton")
        self.start_game_pushButton.setMinimumSize(QSize(70, 30))
        self.start_game_pushButton.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:14px;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.horizontalLayout.addWidget(self.start_game_pushButton)


        self.verticalLayout_6.addWidget(self.frame1_1)

        self.frame1_2 = QFrame(self.scrollAreaWidgetContents_2)
        self.frame1_2.setObjectName(u"frame1_2")
        self.frame1_2.setStyleSheet(u"border-radius: 8px;\n"
"border: 1.2px solid black;\n"
"background-color: rgba(255, 255, 255, 0.8);\n"
"font-size: 16px;")
        self.frame1_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame1_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_7 = QHBoxLayout(self.frame1_2)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.trailblaze_power_checkBox = QCheckBox(self.frame1_2)
        self.trailblaze_power_checkBox.setObjectName(u"trailblaze_power_checkBox")
        self.trailblaze_power_checkBox.setMinimumSize(QSize(0, 30))
        self.trailblaze_power_checkBox.setStyleSheet(u"checkbox1\uff1afont-size: 14px;border: none;font-weight:bold;")

        self.horizontalLayout_7.addWidget(self.trailblaze_power_checkBox)

        self.trailblaze_power_pushButton = QPushButton(self.frame1_2)
        self.trailblaze_power_pushButton.setObjectName(u"trailblaze_power_pushButton")
        self.trailblaze_power_pushButton.setMinimumSize(QSize(70, 30))
        self.trailblaze_power_pushButton.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:14px;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.horizontalLayout_7.addWidget(self.trailblaze_power_pushButton)


        self.verticalLayout_6.addWidget(self.frame1_2)

        self.frame1_3 = QFrame(self.scrollAreaWidgetContents_2)
        self.frame1_3.setObjectName(u"frame1_3")
        self.frame1_3.setStyleSheet(u"border-radius: 8px;\n"
"border: 1.2px solid black;\n"
"background-color: rgba(255, 255, 255, 0.8);\n"
"font-size: 16px;")
        self.frame1_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame1_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame1_3)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.receive_reward_checkBox = QCheckBox(self.frame1_3)
        self.receive_reward_checkBox.setObjectName(u"receive_reward_checkBox")
        self.receive_reward_checkBox.setMinimumSize(QSize(0, 30))
        self.receive_reward_checkBox.setStyleSheet(u"checkbox1\uff1afont-size: 14px;border: none;font-weight:bold;")

        self.horizontalLayout_3.addWidget(self.receive_reward_checkBox)

        self.receive_reward_pushButton = QPushButton(self.frame1_3)
        self.receive_reward_pushButton.setObjectName(u"receive_reward_pushButton")
        self.receive_reward_pushButton.setMinimumSize(QSize(70, 30))
        self.receive_reward_pushButton.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:14px;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.horizontalLayout_3.addWidget(self.receive_reward_pushButton)


        self.verticalLayout_6.addWidget(self.frame1_3)

        self.frame1_5 = QFrame(self.scrollAreaWidgetContents_2)
        self.frame1_5.setObjectName(u"frame1_5")
        self.frame1_5.setEnabled(True)
        self.frame1_5.setStyleSheet(u"border-radius: 8px;\n"
"border: 1.2px solid black;\n"
"background-color: rgba(255, 255, 255, 0.8);\n"
" font-size: 16px;")
        self.frame1_5.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame1_5.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_20 = QHBoxLayout(self.frame1_5)
        self.horizontalLayout_20.setObjectName(u"horizontalLayout_20")
        self.simulate_universe_checkBox = QCheckBox(self.frame1_5)
        self.simulate_universe_checkBox.setObjectName(u"simulate_universe_checkBox")
        self.simulate_universe_checkBox.setMinimumSize(QSize(0, 30))
        self.simulate_universe_checkBox.setStyleSheet(u"checkbox1\uff1afont-size: 14px;border: none;font-weight:bold;")

        self.horizontalLayout_20.addWidget(self.simulate_universe_checkBox)

        self.simulate_universe_pushButton = QPushButton(self.frame1_5)
        self.simulate_universe_pushButton.setObjectName(u"simulate_universe_pushButton")
        self.simulate_universe_pushButton.setMinimumSize(QSize(70, 30))
        self.simulate_universe_pushButton.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:14px;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.horizontalLayout_20.addWidget(self.simulate_universe_pushButton)


        self.verticalLayout_6.addWidget(self.frame1_5)

        self.frame1_4 = QFrame(self.scrollAreaWidgetContents_2)
        self.frame1_4.setObjectName(u"frame1_4")
        self.frame1_4.setStyleSheet(u"border-radius: 8px;\n"
"border: 1.2px solid black;\n"
"background-color: rgba(255, 255, 255, 0.8);\n"
"  font-size: 16px;")
        self.frame1_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame1_4.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_10 = QHBoxLayout(self.frame1_4)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.mission_accomplish_checkBox = QCheckBox(self.frame1_4)
        self.mission_accomplish_checkBox.setObjectName(u"mission_accomplish_checkBox")
        self.mission_accomplish_checkBox.setMinimumSize(QSize(0, 30))
        self.mission_accomplish_checkBox.setStyleSheet(u"checkbox1\uff1afont-size: 14px;border: none;font-weight:bold;")

        self.horizontalLayout_10.addWidget(self.mission_accomplish_checkBox)

        self.mission_accomplish_pushButton = QPushButton(self.frame1_4)
        self.mission_accomplish_pushButton.setObjectName(u"mission_accomplish_pushButton")
        self.mission_accomplish_pushButton.setMinimumSize(QSize(70, 30))
        self.mission_accomplish_pushButton.setStyleSheet(u"QPUSHBOTTON:QPushButton {font-size:14px;}\n"
"  QPushButton:hover {ackground-color: #f0f0f0;border-color: #ccc;}")

        self.horizontalLayout_10.addWidget(self.mission_accomplish_pushButton)


        self.verticalLayout_6.addWidget(self.frame1_4)

        self.frame1_0 = QFrame(self.scrollAreaWidgetContents_2)
        self.frame1_0.setObjectName(u"frame1_0")
        self.frame1_0.setStyleSheet(u"border-radius: 8px;\n"
"border: 1.2px solid black;\n"
"background-color: rgba(255, 255, 255, 0.8);\n"
"font-size: 16px;")
        self.frame1_0.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame1_0.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_12 = QHBoxLayout(self.frame1_0)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.start_pushButton = QPushButton(self.frame1_0)
        self.start_pushButton.setObjectName(u"start_pushButton")

        self.horizontalLayout_12.addWidget(self.start_pushButton)

        self.stop_pushButton = QPushButton(self.frame1_0)
        self.stop_pushButton.setObjectName(u"stop_pushButton")
        self.stop_pushButton.setEnabled(False)
        self.stop_pushButton.setMinimumSize(QSize(80, 30))

        self.horizontalLayout_12.addWidget(self.stop_pushButton)


        self.verticalLayout_6.addWidget(self.frame1_0)

        self.task_select_scrollArea.setWidget(self.scrollAreaWidgetContents_2)

        self.horizontalLayout_23.addWidget(self.task_select_scrollArea)


        self.gridLayout_2.addWidget(self.task_select_groupBox, 0, 0, 1, 1)

        self.log_textBrowser = QTextBrowser(self.console_tab)
        self.log_textBrowser.setObjectName(u"log_textBrowser")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.log_textBrowser.sizePolicy().hasHeightForWidth())
        self.log_textBrowser.setSizePolicy(sizePolicy2)
        self.log_textBrowser.setMaximumSize(QSize(16777215, 100))
        self.log_textBrowser.setStyleSheet(u"border-radius: 8px;\n"
"border: 1.2px solid black;\n"
"background-color: rgba(255, 255, 255, 0.8);")

        self.gridLayout_2.addWidget(self.log_textBrowser, 1, 0, 1, 3)

        self.task_setting_groupBox = QGroupBox(self.console_tab)
        self.task_setting_groupBox.setObjectName(u"task_setting_groupBox")
        self.task_setting_groupBox.setStyleSheet(u"border: none;\n"
"                                                border-radius: 8px;\n"
"                                                background-color: rgba(255, 255, 255, 0.6);")
        self.verticalLayout_2 = QVBoxLayout(self.task_setting_groupBox)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")

        self.gridLayout_2.addWidget(self.task_setting_groupBox, 0, 1, 1, 2)

        self.tabWidget.addTab(self.console_tab, "")
        self.multi_account_tab = QWidget()
        self.multi_account_tab.setObjectName(u"multi_account_tab")
        self.horizontalLayout_5 = QHBoxLayout(self.multi_account_tab)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.tabWidget.addTab(self.multi_account_tab, "")
        self.extension_tab = QWidget()
        self.extension_tab.setObjectName(u"extension_tab")
        self.verticalLayout_7 = QVBoxLayout(self.extension_tab)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.scrollArea_3 = QScrollArea(self.extension_tab)
        self.scrollArea_3.setObjectName(u"scrollArea_3")
        self.scrollArea_3.setWidgetResizable(True)
        self.scrollAreaWidgetContents_3 = QWidget()
        self.scrollAreaWidgetContents_3.setObjectName(u"scrollAreaWidgetContents_3")
        self.scrollAreaWidgetContents_3.setGeometry(QRect(0, 0, 108, 38))
        self.horizontalLayout_16 = QHBoxLayout(self.scrollAreaWidgetContents_3)
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.extension_groupBox = QGroupBox(self.scrollAreaWidgetContents_3)
        self.extension_groupBox.setObjectName(u"extension_groupBox")
        self.extension_groupBox.setStyleSheet(u"border-radius: 8px;\n"
"border: 1.2px solid black;\n"
"background-color: rgba(255, 255, 255, 0.8);")
        self.gridLayout_8 = QGridLayout(self.extension_groupBox)
        self.gridLayout_8.setObjectName(u"gridLayout_8")

        self.horizontalLayout_16.addWidget(self.extension_groupBox)

        self.plugin_groupBox = QGroupBox(self.scrollAreaWidgetContents_3)
        self.plugin_groupBox.setObjectName(u"plugin_groupBox")
        self.plugin_groupBox.setStyleSheet(u"border-radius: 8px;\n"
"border: 1.2px solid black;\n"
"background-color: rgba(255, 255, 255, 0.8);")
        self.verticalLayout = QVBoxLayout(self.plugin_groupBox)
        self.verticalLayout.setObjectName(u"verticalLayout")

        self.horizontalLayout_16.addWidget(self.plugin_groupBox)

        self.scrollArea_3.setWidget(self.scrollAreaWidgetContents_3)

        self.verticalLayout_7.addWidget(self.scrollArea_3)

        self.textBrowser = QTextBrowser(self.extension_tab)
        self.textBrowser.setObjectName(u"textBrowser")
        self.textBrowser.setStyleSheet(u"border-radius: 8px;\n"
"border: 1.2px solid black;\n"
"background-color: rgba(255, 255, 255, 0.8);")

        self.verticalLayout_7.addWidget(self.textBrowser)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_7.addItem(self.verticalSpacer)

        self.tabWidget.addTab(self.extension_tab, "")
        self.setting_tab = QWidget()
        self.setting_tab.setObjectName(u"setting_tab")
        self.verticalLayout_5 = QVBoxLayout(self.setting_tab)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.tabWidget.addTab(self.setting_tab, "")

        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 660, 33))
        self.menush_help = QMenu(self.menubar)
        self.menush_help.setObjectName(u"menush_help")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menush_help.menuAction())
        self.menush_help.addAction(self.announcement_action)
        self.menush_help.addAction(self.faq_action)
        self.menush_help.addAction(self.about_action)

        self.retranslateUi(MainWindow)
        self.start_pushButton.clicked["bool"].connect(self.stop_pushButton.setDisabled)
        self.start_pushButton.clicked["bool"].connect(self.start_pushButton.setEnabled)
        self.stop_pushButton.clicked["bool"].connect(self.start_pushButton.setDisabled)
        self.stop_pushButton.clicked["bool"].connect(self.stop_pushButton.setEnabled)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"SRA", None))
        self.announcement_action.setText(QCoreApplication.translate("MainWindow", u"\u516c\u544a", None))
        self.faq_action.setText(QCoreApplication.translate("MainWindow", u"\u5e38\u89c1\u95ee\u9898", None))
        self.feedback_action.setText(QCoreApplication.translate("MainWindow", u"\u95ee\u9898\u53cd\u9988", None))
        self.about_action.setText(QCoreApplication.translate("MainWindow", u"\u5173\u4e8e", None))
        self.task_select_groupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u4efb\u52a1\u914d\u7f6e", None))
        self.start_game_checkBox.setText(QCoreApplication.translate("MainWindow", u"\u542f\u52a8\u6e38\u620f", None))
        self.start_game_pushButton.setText(QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e", None))
        self.trailblaze_power_checkBox.setText(QCoreApplication.translate("MainWindow", u"\u6e05\u5f00\u62d3\u529b", None))
        self.trailblaze_power_pushButton.setText(QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e", None))
        self.receive_reward_checkBox.setText(QCoreApplication.translate("MainWindow", u"\u9886\u53d6\u5956\u52b1", None))
        self.receive_reward_pushButton.setText(QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e", None))
        self.simulate_universe_checkBox.setText(QCoreApplication.translate("MainWindow", u"\u6a21\u62df\u5b87\u5b99", None))
        self.simulate_universe_pushButton.setText(QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e", None))
        self.mission_accomplish_checkBox.setText(QCoreApplication.translate("MainWindow", u"\u7ed3\u675f\u540e", None))
        self.mission_accomplish_pushButton.setText(QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e", None))
        self.start_pushButton.setText(QCoreApplication.translate("MainWindow", u"\u5f00\u59cb", None))
        self.stop_pushButton.setText(QCoreApplication.translate("MainWindow", u"\u505c\u6b62", None))
        self.task_setting_groupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u4efb\u52a1\u8bbe\u7f6e", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.console_tab), QCoreApplication.translate("MainWindow", u"\u63a7\u5236\u53f0", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.multi_account_tab), QCoreApplication.translate("MainWindow", u"\u914d\u7f6e\u65b9\u6848", None))
        self.extension_groupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u62d3\u5c55\u529f\u80fd", None))
        self.plugin_groupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u63d2\u4ef6", None))
        self.textBrowser.setHtml(QCoreApplication.translate("MainWindow", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Microsoft YaHei UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:13pt;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:13pt;\">\u81ea\u52a8\u5bf9\u8bdd\uff1a\u5f00\u542f\u540e\u5728\u8fdb\u5165\u5267\u60c5\u65f6\u4f1a\u81ea\u52a8\u64ad\u653e\u5bf9\u8bdd\u3001\u81ea\u52a8\u9009\u62e9\u5bf9\u8bdd\u9009\u9879\u3002"
                        "\u6b64\u529f\u80fd\u4e0d\u4f1a\u63a7\u5236\u9f20\u6807\uff0c\u4f46\u662f\u4f1a\u8ba9\u6e38\u620f\u5904\u4e8e\u524d\u53f0\u3002\u5982\u679c\u9700\u8981\u53d6\u6d88\u6267\u884c\uff0c\u5c1d\u8bd5\u5c06\u6e38\u620f\u6700\u5c0f\u5316\u540e\u56de\u5230\u6b64\u9875\u9762\u53d6\u6d88\u52fe\u9009\u3002</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:13pt;\">\u6ce8\u610f\uff1a\u529f\u80fd\u52fe\u9009\u540e\u4f1a\u7acb\u5373\u6267\u884c\uff0c\u4e0e\u5176\u4ed6\u4efb\u52a1\u72ec\u7acb\uff0c\u5982\u679c\u8981\u53d6\u6d88\u6267\u884c\u8bf7\u53d6\u6d88\u52fe\u9009\u3002</span></p></body></html>", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.extension_tab), QCoreApplication.translate("MainWindow", u"\u62d3\u5c55/\u63d2\u4ef6", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.setting_tab), QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e", None))
        self.menush_help.setTitle(QCoreApplication.translate("MainWindow", u"\u5e2e\u52a9", None))
    # retranslateUi

