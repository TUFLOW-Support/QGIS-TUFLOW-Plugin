# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_1d_res.ui'
#
# Created: Mon Oct 28 08:41:38 2013
#      by: PyQt4 UI code generator 4.10.3
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

class Ui_tuflowqgis_1d_res(object):
    def setupUi(self, tuflowqgis_1d_res):
        tuflowqgis_1d_res.setObjectName(_fromUtf8("tuflowqgis_1d_res"))
        tuflowqgis_1d_res.setWindowModality(QtCore.Qt.ApplicationModal)
        tuflowqgis_1d_res.setEnabled(True)
        tuflowqgis_1d_res.resize(852, 570)
        tuflowqgis_1d_res.setMouseTracking(False)
        self.label2 = QtGui.QLabel(tuflowqgis_1d_res)
        self.label2.setGeometry(QtCore.QRect(10, 70, 108, 22))
        self.label2.setObjectName(_fromUtf8("label2"))
        self.label3 = QtGui.QLabel(tuflowqgis_1d_res)
        self.label3.setGeometry(QtCore.QRect(10, 138, 108, 22))
        self.label3.setObjectName(_fromUtf8("label3"))
        self.ResTypeList = QtGui.QListWidget(tuflowqgis_1d_res)
        self.ResTypeList.setGeometry(QtCore.QRect(10, 160, 191, 81))
        self.ResTypeList.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.ResTypeList.setObjectName(_fromUtf8("ResTypeList"))
        self.label4 = QtGui.QLabel(tuflowqgis_1d_res)
        self.label4.setGeometry(QtCore.QRect(10, 249, 108, 22))
        self.label4.setObjectName(_fromUtf8("label4"))
        self.IDList = QtGui.QListWidget(tuflowqgis_1d_res)
        self.IDList.setGeometry(QtCore.QRect(10, 270, 191, 151))
        self.IDList.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.IDList.setObjectName(_fromUtf8("IDList"))
        self.locationDrop = QtGui.QComboBox(tuflowqgis_1d_res)
        self.locationDrop.setGeometry(QtCore.QRect(10, 90, 191, 22))
        self.locationDrop.setObjectName(_fromUtf8("locationDrop"))
        self.sourcelayer = QtGui.QComboBox(tuflowqgis_1d_res)
        self.sourcelayer.setGeometry(QtCore.QRect(10, 40, 191, 22))
        self.sourcelayer.setObjectName(_fromUtf8("sourcelayer"))
        self.label1 = QtGui.QLabel(tuflowqgis_1d_res)
        self.label1.setGeometry(QtCore.QRect(10, 20, 151, 22))
        self.label1.setObjectName(_fromUtf8("label1"))
        self.gridLayoutWidget = QtGui.QWidget(tuflowqgis_1d_res)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(220, 30, 611, 511))
        self.gridLayoutWidget.setObjectName(_fromUtf8("gridLayoutWidget"))
        self.gridLayout = QtGui.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setMargin(0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.frame_for_plot = QtGui.QFrame(self.gridLayoutWidget)
        self.frame_for_plot.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame_for_plot.setFrameShadow(QtGui.QFrame.Raised)
        self.frame_for_plot.setObjectName(_fromUtf8("frame_for_plot"))
        self.gridLayout.addWidget(self.frame_for_plot, 0, 0, 1, 1)
        self.ResList = QtGui.QListWidget(tuflowqgis_1d_res)
        self.ResList.setGeometry(QtCore.QRect(10, 450, 191, 61))
        self.ResList.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.ResList.setObjectName(_fromUtf8("ResList"))
        self.label5 = QtGui.QLabel(tuflowqgis_1d_res)
        self.label5.setGeometry(QtCore.QRect(10, 430, 108, 22))
        self.label5.setObjectName(_fromUtf8("label5"))
        self.AddRes = QtGui.QPushButton(tuflowqgis_1d_res)
        self.AddRes.setGeometry(QtCore.QRect(10, 520, 91, 23))
        self.AddRes.setObjectName(_fromUtf8("AddRes"))
        self.CloseRes = QtGui.QPushButton(tuflowqgis_1d_res)
        self.CloseRes.setGeometry(QtCore.QRect(129, 520, 81, 23))
        self.CloseRes.setObjectName(_fromUtf8("CloseRes"))

        self.retranslateUi(tuflowqgis_1d_res)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_1d_res)

    def retranslateUi(self, tuflowqgis_1d_res):
        tuflowqgis_1d_res.setWindowTitle(_translate("tuflowqgis_1d_res", "TUFLOW Results Viewer", None))
        self.label2.setText(_translate("tuflowqgis_1d_res", "Location Type", None))
        self.label3.setText(_translate("tuflowqgis_1d_res", "Results Type", None))
        self.label4.setText(_translate("tuflowqgis_1d_res", "Selected Elements", None))
        self.label1.setText(_translate("tuflowqgis_1d_res", "Source Layer to get ID\'s from", None))
        self.label5.setText(_translate("tuflowqgis_1d_res", "Results Files", None))
        self.AddRes.setText(_translate("tuflowqgis_1d_res", "Add Result", None))
        self.CloseRes.setText(_translate("tuflowqgis_1d_res", "Close Result", None))

