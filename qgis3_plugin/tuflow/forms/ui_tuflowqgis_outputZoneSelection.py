# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\ui_tuflowqgis_outputZoneSelection.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_outputZoneSelection(object):
    def setupUi(self, outputZoneSelection):
        outputZoneSelection.setObjectName("outputZoneSelection")
        outputZoneSelection.resize(359, 228)
        self.gridLayout = QtWidgets.QGridLayout(outputZoneSelection)
        self.gridLayout.setObjectName("gridLayout")
        self.listWidget = QtWidgets.QListWidget(outputZoneSelection)
        self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.listWidget.setObjectName("listWidget")
        self.gridLayout.addWidget(self.listWidget, 0, 0, 1, 3)
        self.ok_button = QtWidgets.QPushButton(outputZoneSelection)
        self.ok_button.setObjectName("ok_button")
        self.buttonGroup = QtWidgets.QButtonGroup(outputZoneSelection)
        self.buttonGroup.setObjectName("buttonGroup")
        self.buttonGroup.addButton(self.ok_button)
        self.gridLayout.addWidget(self.ok_button, 1, 0, 1, 1)
        self.selectAll_button = QtWidgets.QPushButton(outputZoneSelection)
        self.selectAll_button.setObjectName("selectAll_button")
        self.buttonGroup.addButton(self.selectAll_button)
        self.gridLayout.addWidget(self.selectAll_button, 1, 1, 1, 1)
        self.cancel_button = QtWidgets.QPushButton(outputZoneSelection)
        self.cancel_button.setObjectName("cancel_button")
        self.buttonGroup.addButton(self.cancel_button)
        self.gridLayout.addWidget(self.cancel_button, 1, 2, 1, 1)

        self.retranslateUi(outputZoneSelection)
        QtCore.QMetaObject.connectSlotsByName(outputZoneSelection)

    def retranslateUi(self, outputZoneSelection):
        _translate = QtCore.QCoreApplication.translate
        outputZoneSelection.setWindowTitle(_translate("outputZoneSelection", "Select Output Zones to Add . . ."))
        self.ok_button.setText(_translate("outputZoneSelection", "OK"))
        self.selectAll_button.setText(_translate("outputZoneSelection", "Select All"))
        self.cancel_button.setText(_translate("outputZoneSelection", "Cancel"))

