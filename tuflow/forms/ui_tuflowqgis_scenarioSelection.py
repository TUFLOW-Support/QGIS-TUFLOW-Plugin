# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_scenarioSelection.ui'
#
# Created: Sat May 19 20:43:58 2018
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_scenarioSelection(object):
    def setupUi(self, scenarioSelection):
        scenarioSelection.setObjectName(_fromUtf8("scenarioSelection"))
        scenarioSelection.resize(359, 228)
        self.gridLayout = QtGui.QGridLayout(scenarioSelection)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.scenario_lw = QtGui.QListWidget(scenarioSelection)
        self.scenario_lw.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.scenario_lw.setObjectName(_fromUtf8("scenario_lw"))
        self.gridLayout.addWidget(self.scenario_lw, 0, 0, 1, 3)
        self.ok_button = QtGui.QPushButton(scenarioSelection)
        self.ok_button.setObjectName(_fromUtf8("ok_button"))
        self.buttonGroup = QtGui.QButtonGroup(scenarioSelection)
        self.buttonGroup.setObjectName(_fromUtf8("buttonGroup"))
        self.buttonGroup.addButton(self.ok_button)
        self.gridLayout.addWidget(self.ok_button, 1, 0, 1, 1)
        self.selectAll_button = QtGui.QPushButton(scenarioSelection)
        self.selectAll_button.setObjectName(_fromUtf8("selectAll_button"))
        self.buttonGroup.addButton(self.selectAll_button)
        self.gridLayout.addWidget(self.selectAll_button, 1, 1, 1, 1)
        self.cancel_button = QtGui.QPushButton(scenarioSelection)
        self.cancel_button.setObjectName(_fromUtf8("cancel_button"))
        self.buttonGroup.addButton(self.cancel_button)
        self.gridLayout.addWidget(self.cancel_button, 1, 2, 1, 1)

        self.retranslateUi(scenarioSelection)
        self.ok_button.clicked.connect(scenarioSelection.accept)
        self.cancel_button.clicked.connect(scenarioSelection.reject)
        QtCore.QMetaObject.connectSlotsByName(scenarioSelection)

    def retranslateUi(self, scenarioSelection):
        scenarioSelection.setWindowTitle(_translate("scenarioSelection", "Select Scenarios To Add..", None))
        self.ok_button.setText(_translate("scenarioSelection", "OK", None))
        self.selectAll_button.setText(_translate("scenarioSelection", "Select All", None))
        self.cancel_button.setText(_translate("scenarioSelection", "Cancel", None))

