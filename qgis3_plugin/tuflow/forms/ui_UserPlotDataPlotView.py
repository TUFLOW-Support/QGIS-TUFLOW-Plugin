# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\ui_UserPlotDataPlotView.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_UserPlotData(object):
    def setupUi(self, UserPlotData):
        UserPlotData.setObjectName("UserPlotData")
        UserPlotData.resize(607, 504)
        self.gridLayout = QtWidgets.QGridLayout(UserPlotData)
        self.gridLayout.setObjectName("gridLayout")
        self.pbRefresh = QtWidgets.QPushButton(UserPlotData)
        self.pbRefresh.setObjectName("pbRefresh")
        self.gridLayout.addWidget(self.pbRefresh, 2, 2, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 2, 1, 1, 1)
        self.pbOK = QtWidgets.QPushButton(UserPlotData)
        self.pbOK.setObjectName("pbOK")
        self.gridLayout.addWidget(self.pbOK, 2, 3, 1, 1)
        self.cbDisplayDates = QtWidgets.QCheckBox(UserPlotData)
        self.cbDisplayDates.setObjectName("cbDisplayDates")
        self.gridLayout.addWidget(self.cbDisplayDates, 2, 0, 1, 1)
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.plotFrame = QtWidgets.QFrame(UserPlotData)
        self.plotFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.plotFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.plotFrame.setObjectName("plotFrame")
        self.gridLayout_2.addWidget(self.plotFrame, 0, 0, 1, 1)
        self.gridLayout.addLayout(self.gridLayout_2, 0, 0, 1, 4)

        self.retranslateUi(UserPlotData)
        QtCore.QMetaObject.connectSlotsByName(UserPlotData)

    def retranslateUi(self, UserPlotData):
        _translate = QtCore.QCoreApplication.translate
        UserPlotData.setWindowTitle(_translate("UserPlotData", "Plot"))
        self.pbRefresh.setText(_translate("UserPlotData", "Refresh Plot"))
        self.pbOK.setText(_translate("UserPlotData", "OK"))
        self.cbDisplayDates.setText(_translate("UserPlotData", "Dispay Dates"))

