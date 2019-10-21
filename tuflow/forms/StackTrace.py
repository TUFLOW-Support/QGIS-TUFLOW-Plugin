# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\StackTrace.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_StackTraceDialog(object):
    def setupUi(self, StackTraceDialog):
        StackTraceDialog.setObjectName("StackTraceDialog")
        StackTraceDialog.resize(400, 300)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(StackTraceDialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.teStackTrace = QtWidgets.QPlainTextEdit(StackTraceDialog)
        self.teStackTrace.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.teStackTrace.setReadOnly(True)
        self.teStackTrace.setObjectName("teStackTrace")
        self.verticalLayout.addWidget(self.teStackTrace)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(StackTraceDialog)
        QtCore.QMetaObject.connectSlotsByName(StackTraceDialog)

    def retranslateUi(self, StackTraceDialog):
        _translate = QtCore.QCoreApplication.translate
        StackTraceDialog.setWindowTitle(_translate("StackTraceDialog", "StackTrace"))

