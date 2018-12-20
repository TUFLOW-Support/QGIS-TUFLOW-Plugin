# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\ui_tuflowqgis_meshSelection.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_meshSelection(object):
    def setupUi(self, meshSelection):
        meshSelection.setObjectName("meshSelection")
        meshSelection.resize(359, 228)
        self.gridLayout = QtWidgets.QGridLayout(meshSelection)
        self.gridLayout.setObjectName("gridLayout")
        self.mesh_lw = QtWidgets.QListWidget(meshSelection)
        self.mesh_lw.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.mesh_lw.setObjectName("mesh_lw")
        self.gridLayout.addWidget(self.mesh_lw, 0, 0, 1, 2)
        self.ok_button = QtWidgets.QPushButton(meshSelection)
        self.ok_button.setObjectName("ok_button")
        self.buttonGroup = QtWidgets.QButtonGroup(meshSelection)
        self.buttonGroup.setObjectName("buttonGroup")
        self.buttonGroup.addButton(self.ok_button)
        self.gridLayout.addWidget(self.ok_button, 1, 0, 1, 1)
        self.cancel_button = QtWidgets.QPushButton(meshSelection)
        self.cancel_button.setObjectName("cancel_button")
        self.buttonGroup.addButton(self.cancel_button)
        self.gridLayout.addWidget(self.cancel_button, 1, 1, 1, 1)

        self.retranslateUi(meshSelection)
        QtCore.QMetaObject.connectSlotsByName(meshSelection)

    def retranslateUi(self, meshSelection):
        _translate = QtCore.QCoreApplication.translate
        meshSelection.setWindowTitle(_translate("meshSelection", "Select Which Result to Save Style to Default . . ."))
        self.ok_button.setText(_translate("meshSelection", "OK"))
        self.cancel_button.setText(_translate("meshSelection", "Cancel"))

