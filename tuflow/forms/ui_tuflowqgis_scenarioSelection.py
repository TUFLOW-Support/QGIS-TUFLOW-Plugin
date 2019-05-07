# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\ui_tuflowqgis_scenarioSelection.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_scenarioSelection(object):
    def setupUi(self, scenarioSelection):
        scenarioSelection.setObjectName("scenarioSelection")
        scenarioSelection.resize(359, 228)
        self.gridLayout = QtWidgets.QGridLayout(scenarioSelection)
        self.gridLayout.setObjectName("gridLayout")
        self.scenario_lw = QtWidgets.QListWidget(scenarioSelection)
        self.scenario_lw.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.scenario_lw.setObjectName("scenario_lw")
        self.gridLayout.addWidget(self.scenario_lw, 0, 0, 1, 3)
        self.ok_button = QtWidgets.QPushButton(scenarioSelection)
        self.ok_button.setObjectName("ok_button")
        self.buttonGroup = QtWidgets.QButtonGroup(scenarioSelection)
        self.buttonGroup.setObjectName("buttonGroup")
        self.buttonGroup.addButton(self.ok_button)
        self.gridLayout.addWidget(self.ok_button, 1, 0, 1, 1)
        self.selectAll_button = QtWidgets.QPushButton(scenarioSelection)
        self.selectAll_button.setObjectName("selectAll_button")
        self.buttonGroup.addButton(self.selectAll_button)
        self.gridLayout.addWidget(self.selectAll_button, 1, 1, 1, 1)
        self.cancel_button = QtWidgets.QPushButton(scenarioSelection)
        self.cancel_button.setObjectName("cancel_button")
        self.buttonGroup.addButton(self.cancel_button)
        self.gridLayout.addWidget(self.cancel_button, 1, 2, 1, 1)

        self.retranslateUi(scenarioSelection)
        QtCore.QMetaObject.connectSlotsByName(scenarioSelection)

    def retranslateUi(self, scenarioSelection):
        _translate = QtCore.QCoreApplication.translate
        scenarioSelection.setWindowTitle(_translate("scenarioSelection", "Select Scenarios To Add.."))
        self.ok_button.setText(_translate("scenarioSelection", "OK"))
        self.selectAll_button.setText(_translate("scenarioSelection", "Select All"))
        self.cancel_button.setText(_translate("scenarioSelection", "Cancel"))

