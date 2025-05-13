# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\Tuflow_utility_error.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets

class Ui_utilityErrorDialog(object):
    def setupUi(self, utilityErrorDialog):
        utilityErrorDialog.setObjectName("utilityErrorDialog")
        utilityErrorDialog.resize(400, 300)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(utilityErrorDialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.teError = QtWidgets.QPlainTextEdit(utilityErrorDialog)
        self.teError.setObjectName("teError")
        self.verticalLayout.addWidget(self.teError)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(utilityErrorDialog)
        QtCore.QMetaObject.connectSlotsByName(utilityErrorDialog)

    def retranslateUi(self, utilityErrorDialog):
        _translate = QtCore.QCoreApplication.translate
        utilityErrorDialog.setWindowTitle(_translate("utilityErrorDialog", "TUFLOW Utility Error"))

