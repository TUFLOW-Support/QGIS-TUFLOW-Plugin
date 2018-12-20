# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\ui_UserPlotDataManagerDialog.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_UserPlotDataManagerDialog(object):
    def setupUi(self, UserPlotDataManagerDialog):
        UserPlotDataManagerDialog.setObjectName("UserPlotDataManagerDialog")
        UserPlotDataManagerDialog.resize(443, 351)
        self.gridLayout_2 = QtWidgets.QGridLayout(UserPlotDataManagerDialog)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.pbOK = QtWidgets.QPushButton(UserPlotDataManagerDialog)
        self.pbOK.setObjectName("pbOK")
        self.gridLayout_2.addWidget(self.pbOK, 1, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(37, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem, 1, 0, 1, 1)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.UserPlotDataTable = QtWidgets.QTableWidget(UserPlotDataManagerDialog)
        self.UserPlotDataTable.setShowGrid(False)
        self.UserPlotDataTable.setObjectName("UserPlotDataTable")
        self.UserPlotDataTable.setColumnCount(2)
        self.UserPlotDataTable.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.UserPlotDataTable.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.UserPlotDataTable.setHorizontalHeaderItem(1, item)
        self.UserPlotDataTable.horizontalHeader().setVisible(False)
        self.UserPlotDataTable.horizontalHeader().setDefaultSectionSize(150)
        self.UserPlotDataTable.verticalHeader().setVisible(True)
        self.verticalLayout.addWidget(self.UserPlotDataTable)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.pbAddData = QtWidgets.QPushButton(UserPlotDataManagerDialog)
        self.pbAddData.setObjectName("pbAddData")
        self.verticalLayout_2.addWidget(self.pbAddData)
        self.pbRemoveData = QtWidgets.QPushButton(UserPlotDataManagerDialog)
        self.pbRemoveData.setObjectName("pbRemoveData")
        self.verticalLayout_2.addWidget(self.pbRemoveData)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem1)
        self.pbViewTable = QtWidgets.QPushButton(UserPlotDataManagerDialog)
        self.pbViewTable.setObjectName("pbViewTable")
        self.verticalLayout_2.addWidget(self.pbViewTable)
        self.pbViewPlot = QtWidgets.QPushButton(UserPlotDataManagerDialog)
        self.pbViewPlot.setObjectName("pbViewPlot")
        self.verticalLayout_2.addWidget(self.pbViewPlot)
        self.gridLayout.addLayout(self.verticalLayout_2, 0, 1, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 2)

        self.retranslateUi(UserPlotDataManagerDialog)
        QtCore.QMetaObject.connectSlotsByName(UserPlotDataManagerDialog)

    def retranslateUi(self, UserPlotDataManagerDialog):
        _translate = QtCore.QCoreApplication.translate
        UserPlotDataManagerDialog.setWindowTitle(_translate("UserPlotDataManagerDialog", "User Plot Data Manager"))
        self.pbOK.setText(_translate("UserPlotDataManagerDialog", "OK"))
        item = self.UserPlotDataTable.horizontalHeaderItem(0)
        item.setText(_translate("UserPlotDataManagerDialog", "Plot Data"))
        item = self.UserPlotDataTable.horizontalHeaderItem(1)
        item.setText(_translate("UserPlotDataManagerDialog", "Plot Window"))
        self.pbAddData.setText(_translate("UserPlotDataManagerDialog", "Add Data"))
        self.pbRemoveData.setText(_translate("UserPlotDataManagerDialog", "Remove Data"))
        self.pbViewTable.setText(_translate("UserPlotDataManagerDialog", "View Data"))
        self.pbViewPlot.setText(_translate("UserPlotDataManagerDialog", "Plot Data"))

