# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\ui_tuflowqgis_eventSelection.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets


from ..compatibility_routines import QT_ABSTRACT_ITEM_VIEW_EXTENDED_SELECTION


class Ui_eventSelection(object):
    def setupUi(self, eventSelection):
        eventSelection.setObjectName("eventSelection")
        eventSelection.resize(359, 228)
        self.gridLayout = QtWidgets.QGridLayout(eventSelection)
        self.gridLayout.setObjectName("gridLayout")
        self.events_lw = QtWidgets.QListWidget(eventSelection)
        self.events_lw.setSelectionMode(QT_ABSTRACT_ITEM_VIEW_EXTENDED_SELECTION)
        self.events_lw.setObjectName("events_lw")
        self.gridLayout.addWidget(self.events_lw, 0, 0, 1, 3)
        self.ok_button = QtWidgets.QPushButton(eventSelection)
        self.ok_button.setObjectName("ok_button")
        self.buttonGroup = QtWidgets.QButtonGroup(eventSelection)
        self.buttonGroup.setObjectName("buttonGroup")
        self.buttonGroup.addButton(self.ok_button)
        self.gridLayout.addWidget(self.ok_button, 1, 0, 1, 1)
        self.selectAll_button = QtWidgets.QPushButton(eventSelection)
        self.selectAll_button.setObjectName("selectAll_button")
        self.buttonGroup.addButton(self.selectAll_button)
        self.gridLayout.addWidget(self.selectAll_button, 1, 1, 1, 1)
        self.cancel_button = QtWidgets.QPushButton(eventSelection)
        self.cancel_button.setObjectName("cancel_button")
        self.buttonGroup.addButton(self.cancel_button)
        self.gridLayout.addWidget(self.cancel_button, 1, 2, 1, 1)

        self.retranslateUi(eventSelection)
        QtCore.QMetaObject.connectSlotsByName(eventSelection)

    def retranslateUi(self, eventSelection):
        _translate = QtCore.QCoreApplication.translate
        eventSelection.setWindowTitle(_translate("eventSelection", "Select Events To Add.."))
        self.ok_button.setText(_translate("eventSelection", "OK"))
        self.selectAll_button.setText(_translate("eventSelection", "Select All"))
        self.cancel_button.setText(_translate("eventSelection", "Cancel"))

