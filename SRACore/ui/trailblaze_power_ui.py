# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'trailblaze_power.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QSpinBox, QVBoxLayout,
    QWidget)

class Ui_TrailblazePowerWidget(object):
    def setupUi(self, TrailblazePowerWidget):
        if not TrailblazePowerWidget.objectName():
            TrailblazePowerWidget.setObjectName(u"TrailblazePowerWidget")
        TrailblazePowerWidget.resize(526, 787)
        font = QFont()
        font.setPointSize(13)
        TrailblazePowerWidget.setFont(font)
        TrailblazePowerWidget.setStyleSheet(u"")
        self.gridLayout_8 = QGridLayout(TrailblazePowerWidget)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.scrollArea = QScrollArea(TrailblazePowerWidget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setMaximumSize(QSize(408, 16777215))
        self.scrollArea.setStyleSheet(u"border: 1.4px solid black;  font-size: 16px;")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_7 = QWidget()
        self.scrollAreaWidgetContents_7.setObjectName(u"scrollAreaWidgetContents_7")
        self.scrollAreaWidgetContents_7.setGeometry(QRect(0, -230, 313, 944))
        self.verticalLayout_3 = QVBoxLayout(self.scrollAreaWidgetContents_7)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.frame2_1 = QFrame(self.scrollAreaWidgetContents_7)
        self.frame2_1.setObjectName(u"frame2_1")
        self.frame2_1.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame2_1.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout = QGridLayout(self.frame2_1)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalSpacer2_1_22 = QSpacerItem(315, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer2_1_22, 1, 1, 1, 1)

        self.replenish_time_spinBox = QSpinBox(self.frame2_1)
        self.replenish_time_spinBox.setObjectName(u"replenish_time_spinBox")
        self.replenish_time_spinBox.setMinimumSize(QSize(0, 30))
        self.replenish_time_spinBox.setMinimum(1)
        self.replenish_time_spinBox.setMaximum(300)

        self.gridLayout.addWidget(self.replenish_time_spinBox, 1, 2, 1, 1)

        self.label2_1_21 = QLabel(self.frame2_1)
        self.label2_1_21.setObjectName(u"label2_1_21")
        self.label2_1_21.setStyleSheet(u"border:none")
        self.label2_1_21.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.label2_1_21, 1, 0, 1, 1)

        self.replenish_way_comboBox = QComboBox(self.frame2_1)
        self.replenish_way_comboBox.addItem("")
        self.replenish_way_comboBox.addItem("")
        self.replenish_way_comboBox.addItem("")
        self.replenish_way_comboBox.addItem("")
        self.replenish_way_comboBox.setObjectName(u"replenish_way_comboBox")
        self.replenish_way_comboBox.setMinimumSize(QSize(0, 30))
        self.replenish_way_comboBox.setStyleSheet(u"\n"
"                                                    QCombox{border: solid black;border-radius: 0;font-weight: bold;}\n"
"                                                    QComboBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    border-color: #bbb;\n"
"                                                    }\n"
"                                                    QComboBox QAbstractItemView {\n"
"                                                    selection-background-color: #f0f0f0; background-color: white;\n"
"                                                    }")

        self.gridLayout.addWidget(self.replenish_way_comboBox, 0, 1, 1, 2)

        self.replenish_checkBox = QCheckBox(self.frame2_1)
        self.replenish_checkBox.setObjectName(u"replenish_checkBox")
        self.replenish_checkBox.setStyleSheet(u"border:none")

        self.gridLayout.addWidget(self.replenish_checkBox, 0, 0, 1, 1)

        self.useAssist_checkBox = QCheckBox(self.frame2_1)
        self.useAssist_checkBox.setObjectName(u"useAssist_checkBox")
        self.useAssist_checkBox.setStyleSheet(u"border:none")

        self.gridLayout.addWidget(self.useAssist_checkBox, 2, 0, 1, 3)

        self.changeLineup_checkBox = QCheckBox(self.frame2_1)
        self.changeLineup_checkBox.setObjectName(u"changeLineup_checkBox")
        self.changeLineup_checkBox.setStyleSheet(u"border:none")

        self.gridLayout.addWidget(self.changeLineup_checkBox, 3, 0, 1, 3)


        self.verticalLayout_3.addWidget(self.frame2_1)

        self.frame2_2 = QFrame(self.scrollAreaWidgetContents_7)
        self.frame2_2.setObjectName(u"frame2_2")
        self.frame2_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame2_2.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_2 = QGridLayout(self.frame2_2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.horizontalSpacer2_2_22 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacer2_2_22, 2, 1, 1, 1)

        self.label2_2_21 = QLabel(self.frame2_2)
        self.label2_2_21.setObjectName(u"label2_2_21")
        self.label2_2_21.setStyleSheet(u"border:none")

        self.gridLayout_2.addWidget(self.label2_2_21, 2, 0, 1, 1)

        self.ornamentExtraction_spinBox = QSpinBox(self.frame2_2)
        self.ornamentExtraction_spinBox.setObjectName(u"ornamentExtraction_spinBox")
        self.ornamentExtraction_spinBox.setMinimumSize(QSize(0, 30))
        self.ornamentExtraction_spinBox.setMinimum(1)

        self.gridLayout_2.addWidget(self.ornamentExtraction_spinBox, 2, 2, 1, 1)

        self.ornamentExtractionAddButton = QPushButton(self.frame2_2)
        self.ornamentExtractionAddButton.setObjectName(u"ornamentExtractionAddButton")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.ornamentExtractionAddButton.sizePolicy().hasHeightForWidth())
        self.ornamentExtractionAddButton.setSizePolicy(sizePolicy)
        self.ornamentExtractionAddButton.setMinimumSize(QSize(30, 0))
        self.ornamentExtractionAddButton.setMaximumSize(QSize(30, 16777215))

        self.gridLayout_2.addWidget(self.ornamentExtractionAddButton, 2, 3, 1, 1)

        self.ornamentExtraction_comboBox = QComboBox(self.frame2_2)
        self.ornamentExtraction_comboBox.addItem("")
        self.ornamentExtraction_comboBox.addItem("")
        self.ornamentExtraction_comboBox.addItem("")
        self.ornamentExtraction_comboBox.addItem("")
        self.ornamentExtraction_comboBox.addItem("")
        self.ornamentExtraction_comboBox.addItem("")
        self.ornamentExtraction_comboBox.addItem("")
        self.ornamentExtraction_comboBox.addItem("")
        self.ornamentExtraction_comboBox.addItem("")
        self.ornamentExtraction_comboBox.addItem("")
        self.ornamentExtraction_comboBox.addItem("")
        self.ornamentExtraction_comboBox.addItem("")
        self.ornamentExtraction_comboBox.setObjectName(u"ornamentExtraction_comboBox")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.ornamentExtraction_comboBox.sizePolicy().hasHeightForWidth())
        self.ornamentExtraction_comboBox.setSizePolicy(sizePolicy1)
        self.ornamentExtraction_comboBox.setMinimumSize(QSize(0, 30))
        self.ornamentExtraction_comboBox.setStyleSheet(u"\n"
"                                                    QCombox{border: solid black;border-radius: 0;font-weight: bold;}\n"
"                                                    QComboBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    border-color: #bbb;\n"
"                                                    }\n"
"                                                    QComboBox QAbstractItemView {\n"
"                                                    selection-background-color: #f0f0f0; background-color: white;\n"
"                                                    }")

        self.gridLayout_2.addWidget(self.ornamentExtraction_comboBox, 1, 0, 1, 4)

        self.label_2 = QLabel(self.frame2_2)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setStyleSheet(u"border:none")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_2, 0, 0, 1, 4)


        self.verticalLayout_3.addWidget(self.frame2_2)

        self.frame2_3 = QFrame(self.scrollAreaWidgetContents_7)
        self.frame2_3.setObjectName(u"frame2_3")
        self.frame2_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame2_3.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_3 = QGridLayout(self.frame2_3)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.calyxGoldenSingleTime_spinBox = QSpinBox(self.frame2_3)
        self.calyxGoldenSingleTime_spinBox.setObjectName(u"calyxGoldenSingleTime_spinBox")
        self.calyxGoldenSingleTime_spinBox.setMinimumSize(QSize(0, 30))
        self.calyxGoldenSingleTime_spinBox.setMinimum(1)
        self.calyxGoldenSingleTime_spinBox.setMaximum(6)

        self.gridLayout_3.addWidget(self.calyxGoldenSingleTime_spinBox, 2, 2, 1, 1)

        self.label2_3_21 = QLabel(self.frame2_3)
        self.label2_3_21.setObjectName(u"label2_3_21")
        self.label2_3_21.setStyleSheet(u"border:none")

        self.gridLayout_3.addWidget(self.label2_3_21, 2, 0, 1, 1)

        self.calyxGoldenRunTime_spinBox = QSpinBox(self.frame2_3)
        self.calyxGoldenRunTime_spinBox.setObjectName(u"calyxGoldenRunTime_spinBox")
        self.calyxGoldenRunTime_spinBox.setMinimumSize(QSize(0, 30))
        self.calyxGoldenRunTime_spinBox.setMinimum(1)

        self.gridLayout_3.addWidget(self.calyxGoldenRunTime_spinBox, 3, 2, 1, 1)

        self.calyxGoldenAddButton = QPushButton(self.frame2_3)
        self.calyxGoldenAddButton.setObjectName(u"calyxGoldenAddButton")
        sizePolicy.setHeightForWidth(self.calyxGoldenAddButton.sizePolicy().hasHeightForWidth())
        self.calyxGoldenAddButton.setSizePolicy(sizePolicy)
        self.calyxGoldenAddButton.setMinimumSize(QSize(30, 0))
        self.calyxGoldenAddButton.setMaximumSize(QSize(30, 16777215))

        self.gridLayout_3.addWidget(self.calyxGoldenAddButton, 2, 3, 1, 1)

        self.label2_3_31 = QLabel(self.frame2_3)
        self.label2_3_31.setObjectName(u"label2_3_31")
        self.label2_3_31.setStyleSheet(u"border:none")

        self.gridLayout_3.addWidget(self.label2_3_31, 3, 0, 1, 1)

        self.horizontalSpacer2_3_32 = QSpacerItem(95, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer2_3_32, 3, 1, 1, 1)

        self.horizontalSpacer2_3_22 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer2_3_22, 2, 1, 1, 1)

        self.calyxGolden_comboBox = QComboBox(self.frame2_3)
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.addItem("")
        self.calyxGolden_comboBox.setObjectName(u"calyxGolden_comboBox")
        self.calyxGolden_comboBox.setMinimumSize(QSize(200, 30))
        self.calyxGolden_comboBox.setStyleSheet(u"\n"
"                                                    QCombox{border: solid black;border-radius: 0;font-weight: bold;}\n"
"                                                    QComboBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    border-color: #bbb;\n"
"                                                    }\n"
"                                                    QComboBox QAbstractItemView {\n"
"                                                    selection-background-color: #f0f0f0; background-color: white;\n"
"                                                    }")

        self.gridLayout_3.addWidget(self.calyxGolden_comboBox, 1, 0, 1, 4)

        self.label_3 = QLabel(self.frame2_3)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setStyleSheet(u"border:none")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_3.addWidget(self.label_3, 0, 0, 1, 4)


        self.verticalLayout_3.addWidget(self.frame2_3)

        self.frame2_4 = QFrame(self.scrollAreaWidgetContents_7)
        self.frame2_4.setObjectName(u"frame2_4")
        self.frame2_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame2_4.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_4 = QGridLayout(self.frame2_4)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.horizontalSpacer2_4_22 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_4.addItem(self.horizontalSpacer2_4_22, 3, 1, 1, 1)

        self.calyxCrimsonSingleTime_spinBox = QSpinBox(self.frame2_4)
        self.calyxCrimsonSingleTime_spinBox.setObjectName(u"calyxCrimsonSingleTime_spinBox")
        self.calyxCrimsonSingleTime_spinBox.setMinimumSize(QSize(0, 30))
        self.calyxCrimsonSingleTime_spinBox.setMinimum(1)
        self.calyxCrimsonSingleTime_spinBox.setMaximum(6)

        self.gridLayout_4.addWidget(self.calyxCrimsonSingleTime_spinBox, 3, 2, 1, 1)

        self.calyxCrimsonAddButton = QPushButton(self.frame2_4)
        self.calyxCrimsonAddButton.setObjectName(u"calyxCrimsonAddButton")
        sizePolicy.setHeightForWidth(self.calyxCrimsonAddButton.sizePolicy().hasHeightForWidth())
        self.calyxCrimsonAddButton.setSizePolicy(sizePolicy)
        self.calyxCrimsonAddButton.setMinimumSize(QSize(30, 0))
        self.calyxCrimsonAddButton.setMaximumSize(QSize(30, 16777215))

        self.gridLayout_4.addWidget(self.calyxCrimsonAddButton, 3, 3, 1, 1)

        self.horizontalSpacer2_4_32 = QSpacerItem(29, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_4.addItem(self.horizontalSpacer2_4_32, 4, 1, 1, 1)

        self.calyxCrimsonRunTime_spinBox = QSpinBox(self.frame2_4)
        self.calyxCrimsonRunTime_spinBox.setObjectName(u"calyxCrimsonRunTime_spinBox")
        self.calyxCrimsonRunTime_spinBox.setMinimumSize(QSize(0, 30))
        self.calyxCrimsonRunTime_spinBox.setMinimum(1)

        self.gridLayout_4.addWidget(self.calyxCrimsonRunTime_spinBox, 4, 2, 1, 1)

        self.label2_4_21 = QLabel(self.frame2_4)
        self.label2_4_21.setObjectName(u"label2_4_21")
        self.label2_4_21.setStyleSheet(u"border:none")

        self.gridLayout_4.addWidget(self.label2_4_21, 3, 0, 1, 1)

        self.label2_4_31 = QLabel(self.frame2_4)
        self.label2_4_31.setObjectName(u"label2_4_31")
        self.label2_4_31.setStyleSheet(u"border:none")

        self.gridLayout_4.addWidget(self.label2_4_31, 4, 0, 1, 1)

        self.calyxCrimson_comboBox = QComboBox(self.frame2_4)
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.addItem("")
        self.calyxCrimson_comboBox.setObjectName(u"calyxCrimson_comboBox")
        self.calyxCrimson_comboBox.setMinimumSize(QSize(200, 30))
        self.calyxCrimson_comboBox.setStyleSheet(u"\n"
"                                                    QCombox{border: solid black;border-radius: 0;font-weight: bold;}\n"
"                                                    QComboBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    border-color: #bbb;\n"
"                                                    }\n"
"                                                    QComboBox QAbstractItemView {\n"
"                                                    selection-background-color: #f0f0f0; background-color: white;\n"
"                                                    }")

        self.gridLayout_4.addWidget(self.calyxCrimson_comboBox, 1, 0, 1, 4)

        self.label_4 = QLabel(self.frame2_4)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setStyleSheet(u"border:none")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_4.addWidget(self.label_4, 0, 0, 1, 4)


        self.verticalLayout_3.addWidget(self.frame2_4)

        self.frame2_5 = QFrame(self.scrollAreaWidgetContents_7)
        self.frame2_5.setObjectName(u"frame2_5")
        self.frame2_5.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame2_5.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_5 = QGridLayout(self.frame2_5)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.stagnantShadowRunTime_spinBox = QSpinBox(self.frame2_5)
        self.stagnantShadowRunTime_spinBox.setObjectName(u"stagnantShadowRunTime_spinBox")
        self.stagnantShadowRunTime_spinBox.setMinimumSize(QSize(0, 30))
        self.stagnantShadowRunTime_spinBox.setMinimum(1)

        self.gridLayout_5.addWidget(self.stagnantShadowRunTime_spinBox, 3, 2, 1, 1)

        self.label2_5_21 = QLabel(self.frame2_5)
        self.label2_5_21.setObjectName(u"label2_5_21")
        self.label2_5_21.setStyleSheet(u"border:none")

        self.gridLayout_5.addWidget(self.label2_5_21, 3, 0, 1, 1)

        self.horizontalSpacer2_5_22 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_5.addItem(self.horizontalSpacer2_5_22, 3, 1, 1, 1)

        self.stagnantShadowAddButton = QPushButton(self.frame2_5)
        self.stagnantShadowAddButton.setObjectName(u"stagnantShadowAddButton")
        sizePolicy.setHeightForWidth(self.stagnantShadowAddButton.sizePolicy().hasHeightForWidth())
        self.stagnantShadowAddButton.setSizePolicy(sizePolicy)
        self.stagnantShadowAddButton.setMinimumSize(QSize(30, 0))
        self.stagnantShadowAddButton.setMaximumSize(QSize(30, 16777215))

        self.gridLayout_5.addWidget(self.stagnantShadowAddButton, 3, 3, 1, 1)

        self.stagnantShadow_comboBox = QComboBox(self.frame2_5)
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.addItem("")
        self.stagnantShadow_comboBox.setObjectName(u"stagnantShadow_comboBox")
        self.stagnantShadow_comboBox.setMinimumSize(QSize(220, 30))
        self.stagnantShadow_comboBox.setStyleSheet(u"\n"
"                                                    QCombox{border: solid black;border-radius: 0;font-weight: bold;}\n"
"                                                    QComboBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    border-color: #bbb;\n"
"                                                    }\n"
"                                                    QComboBox QAbstractItemView {\n"
"                                                    selection-background-color: #f0f0f0; background-color: white;\n"
"                                                    }")

        self.gridLayout_5.addWidget(self.stagnantShadow_comboBox, 1, 0, 1, 4)

        self.label_5 = QLabel(self.frame2_5)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setStyleSheet(u"border:none")
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_5.addWidget(self.label_5, 0, 0, 1, 4)


        self.verticalLayout_3.addWidget(self.frame2_5)

        self.frame2_6 = QFrame(self.scrollAreaWidgetContents_7)
        self.frame2_6.setObjectName(u"frame2_6")
        self.frame2_6.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame2_6.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_6 = QGridLayout(self.frame2_6)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.label2_6_21 = QLabel(self.frame2_6)
        self.label2_6_21.setObjectName(u"label2_6_21")
        self.label2_6_21.setStyleSheet(u"border:none")

        self.gridLayout_6.addWidget(self.label2_6_21, 2, 0, 1, 1)

        self.caverOfCorrosionRunTime_spinBox = QSpinBox(self.frame2_6)
        self.caverOfCorrosionRunTime_spinBox.setObjectName(u"caverOfCorrosionRunTime_spinBox")
        self.caverOfCorrosionRunTime_spinBox.setMinimumSize(QSize(0, 30))
        self.caverOfCorrosionRunTime_spinBox.setMinimum(1)

        self.gridLayout_6.addWidget(self.caverOfCorrosionRunTime_spinBox, 2, 2, 1, 1)

        self.horizontalSpacer2_6_22 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_6.addItem(self.horizontalSpacer2_6_22, 2, 1, 1, 1)

        self.caverOfCorrosionAddButton = QPushButton(self.frame2_6)
        self.caverOfCorrosionAddButton.setObjectName(u"caverOfCorrosionAddButton")
        sizePolicy.setHeightForWidth(self.caverOfCorrosionAddButton.sizePolicy().hasHeightForWidth())
        self.caverOfCorrosionAddButton.setSizePolicy(sizePolicy)
        self.caverOfCorrosionAddButton.setMinimumSize(QSize(30, 0))
        self.caverOfCorrosionAddButton.setMaximumSize(QSize(30, 16777215))

        self.gridLayout_6.addWidget(self.caverOfCorrosionAddButton, 2, 3, 1, 1)

        self.label_6 = QLabel(self.frame2_6)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setStyleSheet(u"border:none")
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.label_6, 0, 0, 1, 4)

        self.caverOfCorrosion_comboBox = QComboBox(self.frame2_6)
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.addItem("")
        self.caverOfCorrosion_comboBox.setObjectName(u"caverOfCorrosion_comboBox")
        self.caverOfCorrosion_comboBox.setMinimumSize(QSize(0, 30))
        self.caverOfCorrosion_comboBox.setStyleSheet(u"\n"
"                                                    QCombox{border: solid black;border-radius: 0;font-weight: bold;}\n"
"                                                    QComboBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    border-color: #bbb;\n"
"                                                    }\n"
"                                                    QComboBox QAbstractItemView {\n"
"                                                    selection-background-color: #f0f0f0; background-color: white;\n"
"                                                    }")

        self.gridLayout_6.addWidget(self.caverOfCorrosion_comboBox, 1, 0, 1, 4)


        self.verticalLayout_3.addWidget(self.frame2_6)

        self.frame2_7 = QFrame(self.scrollAreaWidgetContents_7)
        self.frame2_7.setObjectName(u"frame2_7")
        self.frame2_7.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame2_7.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_7 = QGridLayout(self.frame2_7)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.echoOfWarRunTime_spinBox = QSpinBox(self.frame2_7)
        self.echoOfWarRunTime_spinBox.setObjectName(u"echoOfWarRunTime_spinBox")
        self.echoOfWarRunTime_spinBox.setMinimumSize(QSize(0, 30))
        self.echoOfWarRunTime_spinBox.setMinimum(1)
        self.echoOfWarRunTime_spinBox.setMaximum(3)

        self.gridLayout_7.addWidget(self.echoOfWarRunTime_spinBox, 2, 2, 1, 1)

        self.horizontalSpacer2_7_22 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_7.addItem(self.horizontalSpacer2_7_22, 2, 1, 1, 1)

        self.label2_7_21 = QLabel(self.frame2_7)
        self.label2_7_21.setObjectName(u"label2_7_21")
        self.label2_7_21.setStyleSheet(u"border:none")

        self.gridLayout_7.addWidget(self.label2_7_21, 2, 0, 1, 1)

        self.echoOfWarAddButton = QPushButton(self.frame2_7)
        self.echoOfWarAddButton.setObjectName(u"echoOfWarAddButton")
        sizePolicy.setHeightForWidth(self.echoOfWarAddButton.sizePolicy().hasHeightForWidth())
        self.echoOfWarAddButton.setSizePolicy(sizePolicy)
        self.echoOfWarAddButton.setMinimumSize(QSize(30, 0))
        self.echoOfWarAddButton.setMaximumSize(QSize(30, 16777215))

        self.gridLayout_7.addWidget(self.echoOfWarAddButton, 2, 3, 1, 1)

        self.echoOfWar_comboBox = QComboBox(self.frame2_7)
        self.echoOfWar_comboBox.addItem("")
        self.echoOfWar_comboBox.addItem("")
        self.echoOfWar_comboBox.addItem("")
        self.echoOfWar_comboBox.addItem("")
        self.echoOfWar_comboBox.addItem("")
        self.echoOfWar_comboBox.addItem("")
        self.echoOfWar_comboBox.addItem("")
        self.echoOfWar_comboBox.addItem("")
        self.echoOfWar_comboBox.setObjectName(u"echoOfWar_comboBox")
        self.echoOfWar_comboBox.setMinimumSize(QSize(0, 30))
        self.echoOfWar_comboBox.setStyleSheet(u"\n"
"                                                    QCombox{border: solid black;border-radius: 0;font-weight: bold;}\n"
"                                                    QComboBox:hover {\n"
"                                                    background-color: #f0f0f0;\n"
"                                                    border-color: #bbb;\n"
"                                                    }\n"
"                                                    QComboBox QAbstractItemView {\n"
"                                                    selection-background-color: #f0f0f0; background-color: white;\n"
"                                                    }")

        self.gridLayout_7.addWidget(self.echoOfWar_comboBox, 1, 0, 1, 4)

        self.label_7 = QLabel(self.frame2_7)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setStyleSheet(u"border:none")
        self.label_7.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_7.addWidget(self.label_7, 0, 0, 1, 4)


        self.verticalLayout_3.addWidget(self.frame2_7)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents_7)

        self.gridLayout_8.addWidget(self.scrollArea, 1, 0, 1, 1)

        self.frame_1 = QFrame(TrailblazePowerWidget)
        self.frame_1.setObjectName(u"frame_1")
        self.frame_1.setStyleSheet(u"border: 1.4px solid black;  font-size: 16px;background-color: rgba(255, 255, 255, 0.4);")
        self.frame_1.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_1.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_1)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(self.frame_1)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"border:none")

        self.horizontalLayout.addWidget(self.label)


        self.gridLayout_8.addWidget(self.frame_1, 0, 0, 1, 2)

        self.task_listWidget = QListWidget(TrailblazePowerWidget)
        QListWidgetItem(self.task_listWidget)
        QListWidgetItem(self.task_listWidget)
        QListWidgetItem(self.task_listWidget)
        self.task_listWidget.setObjectName(u"task_listWidget")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.task_listWidget.sizePolicy().hasHeightForWidth())
        self.task_listWidget.setSizePolicy(sizePolicy2)
        self.task_listWidget.setFont(font)
        self.task_listWidget.setStyleSheet(u"")
        self.task_listWidget.setTabKeyNavigation(False)
        self.task_listWidget.setDragEnabled(True)
        self.task_listWidget.setDragDropOverwriteMode(True)
        self.task_listWidget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.task_listWidget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.task_listWidget.setAlternatingRowColors(False)
        self.task_listWidget.setWordWrap(True)

        self.gridLayout_8.addWidget(self.task_listWidget, 1, 1, 1, 1)


        self.retranslateUi(TrailblazePowerWidget)

        QMetaObject.connectSlotsByName(TrailblazePowerWidget)
    # setupUi

    def retranslateUi(self, TrailblazePowerWidget):
        TrailblazePowerWidget.setWindowTitle(QCoreApplication.translate("TrailblazePowerWidget", u"Form", None))
        self.label2_1_21.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">\u6b21\u6570\uff1a</span></p></body></html>", None))
        self.replenish_way_comboBox.setItemText(0, QCoreApplication.translate("TrailblazePowerWidget", u"---\u65b9\u5f0f---", None))
        self.replenish_way_comboBox.setItemText(1, QCoreApplication.translate("TrailblazePowerWidget", u"\u540e\u5907", None))
        self.replenish_way_comboBox.setItemText(2, QCoreApplication.translate("TrailblazePowerWidget", u"\u71c3\u6599", None))
        self.replenish_way_comboBox.setItemText(3, QCoreApplication.translate("TrailblazePowerWidget", u"\u661f\u743c", None))

        self.replenish_checkBox.setText(QCoreApplication.translate("TrailblazePowerWidget", u"\u8865\u5145\u4f53\u529b", None))
        self.useAssist_checkBox.setText(QCoreApplication.translate("TrailblazePowerWidget", u"\u4f7f\u7528\u652f\u63f4\u89d2\u8272", None))
        self.changeLineup_checkBox.setText(QCoreApplication.translate("TrailblazePowerWidget", u"\u91cd\u65b0\u7f16\u961f", None))
        self.label2_2_21.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u6b21\u6570\uff1a</span></p></body></html>", None))
        self.ornamentExtractionAddButton.setText(QCoreApplication.translate("TrailblazePowerWidget", u"+", None))
        self.ornamentExtraction_comboBox.setItemText(0, QCoreApplication.translate("TrailblazePowerWidget", u"-----\u9009\u62e9\u526f\u672c-----", None))
        self.ornamentExtraction_comboBox.setItemText(1, QCoreApplication.translate("TrailblazePowerWidget", u"\u6708\u4e0b\u6731\u6bb7\uff08\u5996\u7cbe/\u6d77\u9685\uff09", None))
        self.ornamentExtraction_comboBox.setItemText(2, QCoreApplication.translate("TrailblazePowerWidget", u"\u7eb7\u4e89\u4e0d\u4f11\uff08\u62fe\u9aa8\u5730/\u5de8\u6811\uff09", None))
        self.ornamentExtraction_comboBox.setItemText(3, QCoreApplication.translate("TrailblazePowerWidget", u"\u8839\u5f79\u9965\u80a0\uff08\u9732\u838e\u5361/\u8549\u4e50\u56ed\uff09", None))
        self.ornamentExtraction_comboBox.setItemText(4, QCoreApplication.translate("TrailblazePowerWidget", u"\u6c38\u6052\u7b11\u5267\uff08\u90fd\u84dd/\u52ab\u706b\uff09", None))
        self.ornamentExtraction_comboBox.setItemText(5, QCoreApplication.translate("TrailblazePowerWidget", u"\u4f34\u4f60\u5165\u7720\uff08\u8328\u5188\u5c3c\u4e9a/\u51fa\u4e91\u663e\u4e16\uff09", None))
        self.ornamentExtraction_comboBox.setItemText(6, QCoreApplication.translate("TrailblazePowerWidget", u"\u5929\u5251\u5982\u96e8\uff08\u683c\u62c9\u9ed8/\u5339\u8bfa\u5eb7\u5c3c\uff09", None))
        self.ornamentExtraction_comboBox.setItemText(7, QCoreApplication.translate("TrailblazePowerWidget", u"\u5b7d\u679c\u76d8\u751f\uff08\u7e41\u661f/\u9f99\u9aa8\uff09", None))
        self.ornamentExtraction_comboBox.setItemText(8, QCoreApplication.translate("TrailblazePowerWidget", u"\u767e\u5e74\u51bb\u571f\uff08\u8d1d\u6d1b\u4f2f\u683c/\u8428\u5c14\u7d22\u56fe\uff09", None))
        self.ornamentExtraction_comboBox.setItemText(9, QCoreApplication.translate("TrailblazePowerWidget", u"\u6e29\u67d4\u8bdd\u8bed\uff08\u516c\u53f8/\u5dee\u5206\u673a\uff09", None))
        self.ornamentExtraction_comboBox.setItemText(10, QCoreApplication.translate("TrailblazePowerWidget", u"\u6d74\u706b\u94a2\u5fc3\uff08\u5854\u5229\u4e9a/\u7fc1\u74e6\u514b\uff09", None))
        self.ornamentExtraction_comboBox.setItemText(11, QCoreApplication.translate("TrailblazePowerWidget", u"\u575a\u57ce\u4e0d\u5012\uff08\u592a\u7a7a\u5c01\u5370\u7ad9/\u4ed9\u821f\uff09", None))

        self.label_2.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">\u9970\u54c1\u63d0\u53d6</span></p></body></html>", None))
        self.label2_3_21.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u8fde\u7eed\u4f5c\u6218\uff1a</span></p></body></html>", None))
        self.calyxGoldenAddButton.setText(QCoreApplication.translate("TrailblazePowerWidget", u"+", None))
        self.label2_3_31.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u6267\u884c\u6b21\u6570\uff1a</span></p></body></html>", None))
        self.calyxGolden_comboBox.setItemText(0, QCoreApplication.translate("TrailblazePowerWidget", u"-----\u9009\u62e9\u526f\u672c-----", None))
        self.calyxGolden_comboBox.setItemText(1, QCoreApplication.translate("TrailblazePowerWidget", u"\u56de\u5fc6\u4e4b\u857e\uff08\u7fc1\u6cd5\u7f57\u65af\uff09", None))
        self.calyxGolden_comboBox.setItemText(2, QCoreApplication.translate("TrailblazePowerWidget", u"\u4ee5\u592a\u4e4b\u857e\uff08\u7fc1\u6cd5\u7f57\u65af\uff09", None))
        self.calyxGolden_comboBox.setItemText(3, QCoreApplication.translate("TrailblazePowerWidget", u"\u73cd\u85cf\u4e4b\u857e\uff08\u7fc1\u6cd5\u7f57\u65af\uff09", None))
        self.calyxGolden_comboBox.setItemText(4, QCoreApplication.translate("TrailblazePowerWidget", u"\u56de\u5fc6\u4e4b\u857e\uff08\u5339\u8bfa\u5eb7\u5c3c\uff09", None))
        self.calyxGolden_comboBox.setItemText(5, QCoreApplication.translate("TrailblazePowerWidget", u"\u4ee5\u592a\u4e4b\u857e\uff08\u5339\u8bfa\u5eb7\u5c3c\uff09", None))
        self.calyxGolden_comboBox.setItemText(6, QCoreApplication.translate("TrailblazePowerWidget", u"\u73cd\u85cf\u4e4b\u857e\uff08\u5339\u8bfa\u5eb7\u5c3c\uff09", None))
        self.calyxGolden_comboBox.setItemText(7, QCoreApplication.translate("TrailblazePowerWidget", u"\u56de\u5fc6\u4e4b\u857e\uff08\u4ed9\u821f\u7f57\u6d6e\uff09", None))
        self.calyxGolden_comboBox.setItemText(8, QCoreApplication.translate("TrailblazePowerWidget", u"\u4ee5\u592a\u4e4b\u857e\uff08\u4ed9\u821f\u7f57\u6d6e\uff09", None))
        self.calyxGolden_comboBox.setItemText(9, QCoreApplication.translate("TrailblazePowerWidget", u"\u73cd\u85cf\u4e4b\u857e\uff08\u4ed9\u821f\u7f57\u6d6e\uff09", None))
        self.calyxGolden_comboBox.setItemText(10, QCoreApplication.translate("TrailblazePowerWidget", u"\u56de\u5fc6\u4e4b\u857e\uff08\u96c5\u5229\u6d1bVI\uff09", None))
        self.calyxGolden_comboBox.setItemText(11, QCoreApplication.translate("TrailblazePowerWidget", u"\u4ee5\u592a\u4e4b\u857e\uff08\u96c5\u5229\u6d1bVI\uff09", None))
        self.calyxGolden_comboBox.setItemText(12, QCoreApplication.translate("TrailblazePowerWidget", u"\u73cd\u85cf\u4e4b\u857e\uff08\u96c5\u5229\u6d1bVI\uff09", None))

        self.label_3.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">\u62df\u9020\u82b1\u843c\uff08\u91d1\uff09</span></p></body></html>", None))
        self.calyxCrimsonAddButton.setText(QCoreApplication.translate("TrailblazePowerWidget", u"+", None))
        self.label2_4_21.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u8fde\u7eed\u4f5c\u6218\uff1a</span></p></body></html>", None))
        self.label2_4_31.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u6267\u884c\u6b21\u6570\uff1a</span></p></body></html>", None))
        self.calyxCrimson_comboBox.setItemText(0, QCoreApplication.translate("TrailblazePowerWidget", u"-----\u9009\u62e9\u526f\u672c-----", None))
        self.calyxCrimson_comboBox.setItemText(1, QCoreApplication.translate("TrailblazePowerWidget", u"\u6708\u72c2\u7360\u7259\uff08\u6bc1\u706d\uff09", None))
        self.calyxCrimson_comboBox.setItemText(2, QCoreApplication.translate("TrailblazePowerWidget", u"\u51c0\u4e16\u6b8b\u5203\uff08\u6bc1\u706d\uff09", None))
        self.calyxCrimson_comboBox.setItemText(3, QCoreApplication.translate("TrailblazePowerWidget", u"\u795e\u4f53\u7425\u73c0\uff08\u5b58\u62a4\uff09", None))
        self.calyxCrimson_comboBox.setItemText(4, QCoreApplication.translate("TrailblazePowerWidget", u"\u7425\u73c0\u7684\u575a\u5b88\uff08\u5b58\u62a4\uff09", None))
        self.calyxCrimson_comboBox.setItemText(5, QCoreApplication.translate("TrailblazePowerWidget", u"\u9006\u65f6\u4e00\u51fb\uff08\u5de1\u730e\uff09", None))
        self.calyxCrimson_comboBox.setItemText(6, QCoreApplication.translate("TrailblazePowerWidget", u"\u9010\u661f\u4e4b\u77e2\uff08\u5de1\u730e\uff09", None))
        self.calyxCrimson_comboBox.setItemText(7, QCoreApplication.translate("TrailblazePowerWidget", u"\u4e07\u8c61\u679c\u5b9e\uff08\u4e30\u9976\uff09", None))
        self.calyxCrimson_comboBox.setItemText(8, QCoreApplication.translate("TrailblazePowerWidget", u"\u6c38\u6052\u4e4b\u82b1\uff08\u4e30\u9976\uff09", None))
        self.calyxCrimson_comboBox.setItemText(9, QCoreApplication.translate("TrailblazePowerWidget", u"\u7cbe\u81f4\u8272\u7a3f\uff08\u667a\u8bc6\uff09", None))
        self.calyxCrimson_comboBox.setItemText(10, QCoreApplication.translate("TrailblazePowerWidget", u"\u667a\u8bc6\u4e4b\u94a5\uff08\u667a\u8bc6\uff09", None))
        self.calyxCrimson_comboBox.setItemText(11, QCoreApplication.translate("TrailblazePowerWidget", u"\u5929\u5916\u4e50\u7ae0\uff08\u540c\u8c10\uff09", None))
        self.calyxCrimson_comboBox.setItemText(12, QCoreApplication.translate("TrailblazePowerWidget", u"\u7fa4\u661f\u4e50\u7ae0\uff08\u540c\u8c10\uff09", None))
        self.calyxCrimson_comboBox.setItemText(13, QCoreApplication.translate("TrailblazePowerWidget", u"\u711a\u5929\u4e4b\u9b54\uff08\u865a\u65e0\uff09", None))
        self.calyxCrimson_comboBox.setItemText(14, QCoreApplication.translate("TrailblazePowerWidget", u"\u6c89\u6ca6\u9ed1\u66dc\uff08\u865a\u65e0\uff09", None))
        self.calyxCrimson_comboBox.setItemText(15, QCoreApplication.translate("TrailblazePowerWidget", u"\u963f\u8d56\u8036\u534e\uff08\u8bb0\u5fc6\uff09", None))

        self.label_4.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">\u62df\u9020\u82b1\u843c\uff08\u8d64\uff09</span></p></body></html>", None))
        self.label2_5_21.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u6b21\u6570\uff1a</span></p></body></html>", None))
        self.stagnantShadowAddButton.setText(QCoreApplication.translate("TrailblazePowerWidget", u"+", None))
        self.stagnantShadow_comboBox.setItemText(0, QCoreApplication.translate("TrailblazePowerWidget", u"-----\u9009\u62e9\u526f\u672c-----", None))
        self.stagnantShadow_comboBox.setItemText(1, QCoreApplication.translate("TrailblazePowerWidget", u"\u4fb5\u7565\u51dd\u5757\uff08\u7269\u7406\uff09", None))
        self.stagnantShadow_comboBox.setItemText(2, QCoreApplication.translate("TrailblazePowerWidget", u"\u661f\u9645\u548c\u5e73\u5de5\u4f5c\u8bc1\uff08\u7269\u7406\uff09", None))
        self.stagnantShadow_comboBox.setItemText(3, QCoreApplication.translate("TrailblazePowerWidget", u"\u5e7d\u5e9c\u901a\u4ee4\uff08\u7269\u7406\uff09", None))
        self.stagnantShadow_comboBox.setItemText(4, QCoreApplication.translate("TrailblazePowerWidget", u"\u94c1\u72fc\u788e\u9f7f\uff08\u7269\u7406\uff09", None))
        self.stagnantShadow_comboBox.setItemText(5, QCoreApplication.translate("TrailblazePowerWidget", u"\u5fff\u706b\u4e4b\u5fc3\uff08\u706b\uff09", None))
        self.stagnantShadow_comboBox.setItemText(6, QCoreApplication.translate("TrailblazePowerWidget", u"\u8fc7\u70ed\u94a2\u5200\uff08\u706b\uff09", None))
        self.stagnantShadow_comboBox.setItemText(7, QCoreApplication.translate("TrailblazePowerWidget", u"\u6052\u6e29\u6676\u58f3\uff08\u706b\uff09", None))
        self.stagnantShadow_comboBox.setItemText(8, QCoreApplication.translate("TrailblazePowerWidget", u"\u51b7\u85cf\u68a6\u7bb1\uff08\u51b0\uff09", None))
        self.stagnantShadow_comboBox.setItemText(9, QCoreApplication.translate("TrailblazePowerWidget", u"\u82e6\u5bd2\u6676\u58f3\uff08\u51b0\uff09", None))
        self.stagnantShadow_comboBox.setItemText(10, QCoreApplication.translate("TrailblazePowerWidget", u"\u98ce\u96ea\u4e4b\u89d2\uff08\u51b0\uff09", None))
        self.stagnantShadow_comboBox.setItemText(11, QCoreApplication.translate("TrailblazePowerWidget", u"\u517d\u9986\u4e4b\u9489\uff08\u96f7\uff09", None))
        self.stagnantShadow_comboBox.setItemText(12, QCoreApplication.translate("TrailblazePowerWidget", u"\u70bc\u5f62\u8005\u96f7\u679d\uff08\u96f7\uff09", None))
        self.stagnantShadow_comboBox.setItemText(13, QCoreApplication.translate("TrailblazePowerWidget", u"\u5f80\u65e5\u4e4b\u5f71\u7684\u96f7\u51a0\uff08\u96f7\uff09", None))
        self.stagnantShadow_comboBox.setItemText(14, QCoreApplication.translate("TrailblazePowerWidget", u"\u66ae\u8f89\u70ec\u857e\uff08\u98ce\uff09", None))
        self.stagnantShadow_comboBox.setItemText(15, QCoreApplication.translate("TrailblazePowerWidget", u"\u4e00\u676f\u9169\u914a\u7684\u65f6\u4ee3\uff08\u98ce\uff09", None))
        self.stagnantShadow_comboBox.setItemText(16, QCoreApplication.translate("TrailblazePowerWidget", u"\u65e0\u4eba\u9057\u57a2\uff08\u98ce\uff09", None))
        self.stagnantShadow_comboBox.setItemText(17, QCoreApplication.translate("TrailblazePowerWidget", u"\u66b4\u98ce\u4e4b\u773c\uff08\u98ce\uff09", None))
        self.stagnantShadow_comboBox.setItemText(18, QCoreApplication.translate("TrailblazePowerWidget", u"\u6697\u5e37\u6708\u534e\uff08\u91cf\u5b50\uff09", None))
        self.stagnantShadow_comboBox.setItemText(19, QCoreApplication.translate("TrailblazePowerWidget", u"\u7099\u68a6\u55b7\u67aa\uff08\u91cf\u5b50\uff09", None))
        self.stagnantShadow_comboBox.setItemText(20, QCoreApplication.translate("TrailblazePowerWidget", u"\u82cd\u733f\u4e4b\u9489\uff08\u91cf\u5b50\uff09", None))
        self.stagnantShadow_comboBox.setItemText(21, QCoreApplication.translate("TrailblazePowerWidget", u"\u865a\u5e7b\u94f8\u94c1\uff08\u91cf\u5b50\uff09", None))
        self.stagnantShadow_comboBox.setItemText(22, QCoreApplication.translate("TrailblazePowerWidget", u"\u7eb7\u4e89\u524d\u5146\uff08\u865a\u6570\uff09", None))
        self.stagnantShadow_comboBox.setItemText(23, QCoreApplication.translate("TrailblazePowerWidget", u"\u4e00\u66f2\u548c\u5f26\u7684\u5e7b\u666f\uff08\u865a\u6570\uff09", None))
        self.stagnantShadow_comboBox.setItemText(24, QCoreApplication.translate("TrailblazePowerWidget", u"\u9547\u7075\u6555\u7b26\uff08\u865a\u6570\uff09", None))
        self.stagnantShadow_comboBox.setItemText(25, QCoreApplication.translate("TrailblazePowerWidget", u"\u5f80\u65e5\u4e4b\u5f71\u7684\u91d1\u9970\uff08\u865a\u6570\uff09", None))

        self.label_5.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u51dd\u6ede\u865a\u5f71</span></p></body></html>", None))
        self.label2_6_21.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u6b21\u6570\uff1a</span></p></body></html>", None))
        self.caverOfCorrosionAddButton.setText(QCoreApplication.translate("TrailblazePowerWidget", u"+", None))
        self.label_6.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u4fb5\u8680\u96a7\u6d1e</span></p></body></html>", None))
        self.caverOfCorrosion_comboBox.setItemText(0, QCoreApplication.translate("TrailblazePowerWidget", u"-----\u9009\u62e9\u526f\u672c-----", None))
        self.caverOfCorrosion_comboBox.setItemText(1, QCoreApplication.translate("TrailblazePowerWidget", u"\u96f3\u52c7\u4e4b\u5f84\uff08\u5973\u6b66\u795e/\u8239\u957f\uff09", None))
        self.caverOfCorrosion_comboBox.setItemText(2, QCoreApplication.translate("TrailblazePowerWidget", u"\u5f26\u6b4c\u4e4b\u5f84\uff08\u82f1\u8c6a/\u8bd7\u4eba\uff09", None))
        self.caverOfCorrosion_comboBox.setItemText(3, QCoreApplication.translate("TrailblazePowerWidget", u"\u8ff7\u8bc6\u4e4b\u5f84\uff08\u53f8\u94ce\u5957/\u5b66\u8005\u5957\uff09", None))
        self.caverOfCorrosion_comboBox.setItemText(4, QCoreApplication.translate("TrailblazePowerWidget", u"\u52c7\u9a91\u4e4b\u5f84\uff08\u94c1\u9a91\u5957/\u52c7\u70c8\u5957\uff09", None))
        self.caverOfCorrosion_comboBox.setItemText(5, QCoreApplication.translate("TrailblazePowerWidget", u"\u68a6\u6f5c\u4e4b\u5f84\uff08\u6b7b\u6c34/\u949f\u8868\u5320\uff09", None))
        self.caverOfCorrosion_comboBox.setItemText(6, QCoreApplication.translate("TrailblazePowerWidget", u"\u5e7d\u51a5\u4e4b\u5f84\uff08\u5927\u516c/\u5e7d\u56da\uff09", None))
        self.caverOfCorrosion_comboBox.setItemText(7, QCoreApplication.translate("TrailblazePowerWidget", u"\u836f\u4f7f\u4e4b\u5f84\uff08\u83b3\u8005/\u4fe1\u4f7f\uff09", None))
        self.caverOfCorrosion_comboBox.setItemText(8, QCoreApplication.translate("TrailblazePowerWidget", u"\u91ce\u7130\u4e4b\u5f84\uff08\u706b\u5320/\u5e9f\u571f\u5ba2\uff09", None))
        self.caverOfCorrosion_comboBox.setItemText(9, QCoreApplication.translate("TrailblazePowerWidget", u"\u5723\u9882\u4e4b\u5f84\uff08\u5723\u9a91/\u4e50\u961f\uff09", None))
        self.caverOfCorrosion_comboBox.setItemText(10, QCoreApplication.translate("TrailblazePowerWidget", u"\u777f\u667a\u4e4b\u5f84\uff08\u94c1\u536b/\u91cf\u5b50\u5957\uff09", None))
        self.caverOfCorrosion_comboBox.setItemText(11, QCoreApplication.translate("TrailblazePowerWidget", u"\u6f02\u6cca\u4e4b\u5f84\uff08\u8fc7\u5ba2/\u5feb\u67aa\u624b\uff09", None))
        self.caverOfCorrosion_comboBox.setItemText(12, QCoreApplication.translate("TrailblazePowerWidget", u"\u8fc5\u62f3\u4e4b\u5f84\uff08\u62f3\u7687/\u602a\u76d7\uff09", None))
        self.caverOfCorrosion_comboBox.setItemText(13, QCoreApplication.translate("TrailblazePowerWidget", u"\u971c\u98ce\u4e4b\u5f84\uff08\u51b0/\u98ce\u5957\uff09", None))

        self.label2_7_21.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u6b21\u6570\uff1a</span></p></body></html>", None))
        self.echoOfWarAddButton.setText(QCoreApplication.translate("TrailblazePowerWidget", u"+", None))
        self.echoOfWar_comboBox.setItemText(0, QCoreApplication.translate("TrailblazePowerWidget", u"-----\u9009\u62e9\u526f\u672c-----", None))
        self.echoOfWar_comboBox.setItemText(1, QCoreApplication.translate("TrailblazePowerWidget", u"\u6668\u660f\u7684\u56de\u7738", None))
        self.echoOfWar_comboBox.setItemText(2, QCoreApplication.translate("TrailblazePowerWidget", u"\u5fc3\u517d\u7684\u6218\u573a", None))
        self.echoOfWar_comboBox.setItemText(3, QCoreApplication.translate("TrailblazePowerWidget", u"\u5c18\u68a6\u7684\u8d5e\u793c", None))
        self.echoOfWar_comboBox.setItemText(4, QCoreApplication.translate("TrailblazePowerWidget", u"\u86c0\u661f\u7684\u65e7\u9765", None))
        self.echoOfWar_comboBox.setItemText(5, QCoreApplication.translate("TrailblazePowerWidget", u"\u4e0d\u6b7b\u7684\u795e\u5b9e", None))
        self.echoOfWar_comboBox.setItemText(6, QCoreApplication.translate("TrailblazePowerWidget", u"\u5bd2\u6f6e\u7684\u843d\u5e55", None))
        self.echoOfWar_comboBox.setItemText(7, QCoreApplication.translate("TrailblazePowerWidget", u"\u6bc1\u706d\u7684\u5f00\u7aef", None))

        self.label_7.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">\u5386\u6218\u4f59\u54cd</span></p></body></html>", None))
        self.label.setText(QCoreApplication.translate("TrailblazePowerWidget", u"<html><head/><body><p align=\"center\"><span style=\" font-size:16pt; font-weight:700;\">\u6e05\u5f00\u62d3\u529b</span></p></body></html>", None))

        __sortingEnabled = self.task_listWidget.isSortingEnabled()
        self.task_listWidget.setSortingEnabled(False)
        ___qlistwidgetitem = self.task_listWidget.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("TrailblazePowerWidget", u"\u65b0\u5efa\u9879\u76ee", None));
        ___qlistwidgetitem1 = self.task_listWidget.item(1)
        ___qlistwidgetitem1.setText(QCoreApplication.translate("TrailblazePowerWidget", u"\u65b0\u5efa\u9879\u76ee", None));
        ___qlistwidgetitem2 = self.task_listWidget.item(2)
        ___qlistwidgetitem2.setText(QCoreApplication.translate("TrailblazePowerWidget", u"\u65b0\u5efa\u9879\u76ee", None));
        self.task_listWidget.setSortingEnabled(__sortingEnabled)

    # retranslateUi

