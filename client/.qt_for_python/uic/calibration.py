# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'calibration.ui'
##
## Created by: Qt User Interface Compiler version 6.1.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import *  # type: ignore
from PySide6.QtGui import *  # type: ignore
from PySide6.QtWidgets import *  # type: ignore


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(276, 355)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.formLayoutWidget = QWidget(self.centralwidget)
        self.formLayoutWidget.setObjectName(u"formLayoutWidget")
        self.formLayoutWidget.setGeometry(QRect(10, 50, 251, 221))
        self.formLayout = QFormLayout(self.formLayoutWidget)
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.formLayoutWidget)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(10)
        font.setBold(False)
        self.label.setFont(font)

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label)

        self.txtMPUX = QLineEdit(self.formLayoutWidget)
        self.txtMPUX.setObjectName(u"txtMPUX")
        font1 = QFont()
        font1.setPointSize(10)
        self.txtMPUX.setFont(font1)

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.txtMPUX)

        self.label_2 = QLabel(self.formLayoutWidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font)

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_2)

        self.txtMPUY = QLineEdit(self.formLayoutWidget)
        self.txtMPUY.setObjectName(u"txtMPUY")
        self.txtMPUY.setFont(font1)

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.txtMPUY)

        self.label_4 = QLabel(self.formLayoutWidget)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setFont(font)

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.label_4)

        self.txtMPUZ = QLineEdit(self.formLayoutWidget)
        self.txtMPUZ.setObjectName(u"txtMPUZ")
        self.txtMPUZ.setFont(font1)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.txtMPUZ)

        self.label_6 = QLabel(self.formLayoutWidget)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setFont(font)

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.label_6)

        self.txtMPUT = QLineEdit(self.formLayoutWidget)
        self.txtMPUT.setObjectName(u"txtMPUT")
        self.txtMPUT.setFont(font1)

        self.formLayout.setWidget(3, QFormLayout.FieldRole, self.txtMPUT)

        self.label_5 = QLabel(self.formLayoutWidget)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setFont(font)

        self.formLayout.setWidget(4, QFormLayout.LabelRole, self.label_5)

        self.txtTFMD = QLineEdit(self.formLayoutWidget)
        self.txtTFMD.setObjectName(u"txtTFMD")
        self.txtTFMD.setFont(font1)

        self.formLayout.setWidget(4, QFormLayout.FieldRole, self.txtTFMD)

        self.label_8 = QLabel(self.formLayoutWidget)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setFont(font)

        self.formLayout.setWidget(5, QFormLayout.LabelRole, self.label_8)

        self.txtTFMT = QLineEdit(self.formLayoutWidget)
        self.txtTFMT.setObjectName(u"txtTFMT")
        self.txtTFMT.setFont(font1)

        self.formLayout.setWidget(5, QFormLayout.FieldRole, self.txtTFMT)

        self.label_7 = QLabel(self.formLayoutWidget)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setFont(font)

        self.formLayout.setWidget(6, QFormLayout.LabelRole, self.label_7)

        self.txtPOSX = QLineEdit(self.formLayoutWidget)
        self.txtPOSX.setObjectName(u"txtPOSX")
        self.txtPOSX.setFont(font1)

        self.formLayout.setWidget(6, QFormLayout.FieldRole, self.txtPOSX)

        self.label_3 = QLabel(self.formLayoutWidget)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font)

        self.formLayout.setWidget(7, QFormLayout.LabelRole, self.label_3)

        self.txtPOSY = QLineEdit(self.formLayoutWidget)
        self.txtPOSY.setObjectName(u"txtPOSY")
        self.txtPOSY.setFont(font1)

        self.formLayout.setWidget(7, QFormLayout.FieldRole, self.txtPOSY)

        self.label_9 = QLabel(self.centralwidget)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setGeometry(QRect(10, 9, 251, 31))
        font2 = QFont()
        font2.setPointSize(12)
        font2.setBold(True)
        self.label_9.setFont(font2)
        self.label_9.setAlignment(Qt.AlignCenter)
        self.btnCancel = QPushButton(self.centralwidget)
        self.btnCancel.setObjectName(u"btnCancel")
        self.btnCancel.setGeometry(QRect(146, 280, 121, 24))
        self.btnCancel.setFont(font1)
        self.btnConfirm = QPushButton(self.centralwidget)
        self.btnConfirm.setObjectName(u"btnConfirm")
        self.btnConfirm.setGeometry(QRect(10, 280, 121, 24))
        self.btnConfirm.setFont(font1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 276, 21))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"MPU X Offset", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"MPU Y Offset", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"MPU Z Offset", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"MPU T Offset", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"TFM D Offset", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"TFM T Offset", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"POS X Offset", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"POS Y Offset", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"CVS Calibration Wizard", None))
        self.btnCancel.setText(QCoreApplication.translate("MainWindow", u"Cancel", None))
        self.btnConfirm.setText(QCoreApplication.translate("MainWindow", u"Confirm", None))
    # retranslateUi

