# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\ui_tuflowqgis_selectedElements.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_selectedElements(object):
    def setupUi(self, selectedElements):
        selectedElements.setObjectName("selectedElements")
        selectedElements.resize(303, 193)
        self.gridLayout = QtWidgets.QGridLayout(selectedElements)
        self.gridLayout.setObjectName("gridLayout")
        self.pbSelectElements = QtWidgets.QPushButton(selectedElements)
        self.pbSelectElements.setObjectName("pbSelectElements")
        self.gridLayout.addWidget(self.pbSelectElements, 1, 0, 1, 1)
        self.elementList = QtWidgets.QListWidget(selectedElements)
        self.elementList.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.elementList.setObjectName("elementList")
        self.gridLayout.addWidget(self.elementList, 0, 0, 1, 2)
        self.pbCloseWindow = QtWidgets.QPushButton(selectedElements)
        self.pbCloseWindow.setObjectName("pbCloseWindow")
        self.gridLayout.addWidget(self.pbCloseWindow, 1, 1, 1, 1)

        self.retranslateUi(selectedElements)
        QtCore.QMetaObject.connectSlotsByName(selectedElements)

    def retranslateUi(self, selectedElements):
        _translate = QtCore.QCoreApplication.translate
        selectedElements.setWindowTitle(_translate("selectedElements", "Tuview: Selected Elements"))
        self.pbSelectElements.setText(_translate("selectedElements", "Select Elements On Map"))
        self.pbCloseWindow.setText(_translate("selectedElements", "Close Window"))

