# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\ui_tuflowqgis_brokenLinks.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_scenarioSelection(object):
    def setupUi(self, scenarioSelection):
        scenarioSelection.setObjectName("scenarioSelection")
        scenarioSelection.resize(359, 228)
        self.gridLayout = QtWidgets.QGridLayout(scenarioSelection)
        self.gridLayout.setObjectName("gridLayout")
        self.brokenLinks_lw = QtWidgets.QListWidget(scenarioSelection)
        self.brokenLinks_lw.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.brokenLinks_lw.setObjectName("brokenLinks_lw")
        self.gridLayout.addWidget(self.brokenLinks_lw, 0, 0, 1, 2)
        self.ok_button = QtWidgets.QPushButton(scenarioSelection)
        self.ok_button.setObjectName("ok_button")
        self.buttonGroup = QtWidgets.QButtonGroup(scenarioSelection)
        self.buttonGroup.setObjectName("buttonGroup")
        self.buttonGroup.addButton(self.ok_button)
        self.gridLayout.addWidget(self.ok_button, 1, 0, 1, 2)

        self.retranslateUi(scenarioSelection)
        QtCore.QMetaObject.connectSlotsByName(scenarioSelection)

    def retranslateUi(self, scenarioSelection):
        _translate = QtCore.QCoreApplication.translate
        scenarioSelection.setWindowTitle(_translate("scenarioSelection", "Broken Result Links"))
        self.ok_button.setText(_translate("scenarioSelection", "OK"))

