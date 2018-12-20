# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\ui_UserPlotDataTableView.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_UserTableData(object):
    def setupUi(self, UserTableData):
        UserTableData.setObjectName("UserTableData")
        UserTableData.resize(433, 431)
        self.gridLayout = QtWidgets.QGridLayout(UserTableData)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.dataTable = QtWidgets.QTableWidget(UserTableData)
        self.dataTable.setObjectName("dataTable")
        self.dataTable.setColumnCount(0)
        self.dataTable.setRowCount(0)
        self.verticalLayout.addWidget(self.dataTable)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 2)
        self.pbPlot = QtWidgets.QPushButton(UserTableData)
        self.pbPlot.setObjectName("pbPlot")
        self.gridLayout.addWidget(self.pbPlot, 1, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(UserTableData)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 1, 1, 1, 1)

        self.retranslateUi(UserTableData)
        self.buttonBox.accepted.connect(UserTableData.accept)
        self.buttonBox.rejected.connect(UserTableData.reject)
        QtCore.QMetaObject.connectSlotsByName(UserTableData)

    def retranslateUi(self, UserTableData):
        _translate = QtCore.QCoreApplication.translate
        UserTableData.setWindowTitle(_translate("UserTableData", "Data"))
        self.pbPlot.setText(_translate("UserTableData", "Plot"))

