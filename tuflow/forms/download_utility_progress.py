# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\download_utility_progress.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_downloadUtilityProgressDialog(object):
    def setupUi(self, downloadUtilityProgressDialog):
        downloadUtilityProgressDialog.setObjectName("downloadUtilityProgressDialog")
        downloadUtilityProgressDialog.resize(400, 58)
        self.verticalLayout = QtWidgets.QVBoxLayout(downloadUtilityProgressDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(downloadUtilityProgressDialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.progressBar = QtWidgets.QProgressBar(downloadUtilityProgressDialog)
        self.progressBar.setMaximum(0)
        self.progressBar.setProperty("value", -1)
        self.progressBar.setFormat("")
        self.progressBar.setObjectName("progressBar")
        self.verticalLayout.addWidget(self.progressBar)

        self.retranslateUi(downloadUtilityProgressDialog)
        QtCore.QMetaObject.connectSlotsByName(downloadUtilityProgressDialog)

    def retranslateUi(self, downloadUtilityProgressDialog):
        _translate = QtCore.QCoreApplication.translate
        downloadUtilityProgressDialog.setWindowTitle(_translate("downloadUtilityProgressDialog", "Downloading TUFLOW Utilities . . ."))
        self.label.setText(_translate("downloadUtilityProgressDialog", "Starting Download"))

