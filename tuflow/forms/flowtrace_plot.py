# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\flowtrace_plot.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_flowTracePlot(object):
    def setupUi(self, flowTracePlot):
        flowTracePlot.setObjectName("flowTracePlot")
        flowTracePlot.resize(963, 312)
        self.verticalLayout = QtWidgets.QVBoxLayout(flowTracePlot)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.paths = QtWidgets.QListWidget(flowTracePlot)
        self.paths.setMaximumSize(QtCore.QSize(150, 16777215))
        self.paths.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.paths.setObjectName("paths")
        self.gridLayout.addWidget(self.paths, 1, 1, 1, 1)
        self.label = QtWidgets.QLabel(flowTracePlot)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 1, 1, 1)
        self.pbSelectPath = QtWidgets.QPushButton(flowTracePlot)
        self.pbSelectPath.setObjectName("pbSelectPath")
        self.gridLayout.addWidget(self.pbSelectPath, 2, 1, 1, 1)
        self.plotLayout = QtWidgets.QGridLayout()
        self.plotLayout.setObjectName("plotLayout")
        self.gridLayout.addLayout(self.plotLayout, 0, 0, 3, 1)
        self.verticalLayout.addLayout(self.gridLayout)

        self.retranslateUi(flowTracePlot)
        QtCore.QMetaObject.connectSlotsByName(flowTracePlot)

    def retranslateUi(self, flowTracePlot):
        _translate = QtCore.QCoreApplication.translate
        flowTracePlot.setWindowTitle(_translate("flowTracePlot", "Flow Trace"))
        self.label.setText(_translate("flowTracePlot", "Paths"))
        self.pbSelectPath.setText(_translate("flowTracePlot", "Select Path In Workspace"))

