# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'shutdown_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.7.3
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
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout,
    QLCDNumber, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(342, 246)
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.frame = QFrame(Dialog)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(14)
        self.label.setFont(font)

        self.verticalLayout_2.addWidget(self.label)

        self.lcdNumber = QLCDNumber(self.frame)
        self.lcdNumber.setObjectName(u"lcdNumber")
        self.lcdNumber.setAutoFillBackground(True)
        self.lcdNumber.setDigitCount(2)
        self.lcdNumber.setSegmentStyle(QLCDNumber.SegmentStyle.Filled)
        self.lcdNumber.setProperty(u"value", 60.000000000000000)

        self.verticalLayout_2.addWidget(self.lcdNumber)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.cancel_buttion = QPushButton(self.frame)
        self.cancel_buttion.setObjectName(u"cancel_buttion")
        self.cancel_buttion.setFont(font)

        self.horizontalLayout.addWidget(self.cancel_buttion)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)


        self.verticalLayout_2.addLayout(self.horizontalLayout)


        self.verticalLayout.addWidget(self.frame)


        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"\u60a8\u7684\u8ba1\u7b97\u673a\u5c06\u5728\u5012\u8ba1\u65f6\u7ed3\u675f\u540e\u5173\u673a\uff0c\n"
"                                        \u5982\u679c\u8981\u53d6\u6d88\u5173\u673a\uff0c\u8bf7\u6309\u201c\u53d6\u6d88\u201d\n"
"                                    ", None))
        self.cancel_buttion.setText(QCoreApplication.translate("Dialog", u"\u53d6\u6d88", None))
    # retranslateUi

