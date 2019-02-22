# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\XMDF_info.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_XmdfInfoDialog(object):
    def setupUi(self, XmdfInfoDialog):
        XmdfInfoDialog.setObjectName("XmdfInfoDialog")
        XmdfInfoDialog.resize(400, 300)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(XmdfInfoDialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.teXmdfInfo = QtWidgets.QPlainTextEdit(XmdfInfoDialog)
        self.teXmdfInfo.setObjectName("teXmdfInfo")
        self.verticalLayout.addWidget(self.teXmdfInfo)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(XmdfInfoDialog)
        QtCore.QMetaObject.connectSlotsByName(XmdfInfoDialog)

    def retranslateUi(self, XmdfInfoDialog):
        _translate = QtCore.QCoreApplication.translate
        XmdfInfoDialog.setWindowTitle(_translate("XmdfInfoDialog", "XMDF Info"))

