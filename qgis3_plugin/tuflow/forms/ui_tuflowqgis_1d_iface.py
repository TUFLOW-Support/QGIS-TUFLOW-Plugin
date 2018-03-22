# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_1d_iface.ui'
#
# Created: Fri May 08 12:43:29 2015
#      by: PyQt4 UI code generator 4.11.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import *

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig)

class Ui_tuflowqgis_1d_iface(object):
    def setupUi(self, tuflowqgis_1d_iface):
        tuflowqgis_1d_iface.setObjectName(_fromUtf8("tuflowqgis_1d_iface"))
        tuflowqgis_1d_iface.setWindowModality(QtCore.Qt.ApplicationModal)
        tuflowqgis_1d_iface.setEnabled(True)
        tuflowqgis_1d_iface.resize(388, 460)
        tuflowqgis_1d_iface.setMouseTracking(False)
        self.buttonBox = QDialogButtonBox(tuflowqgis_1d_iface)
        self.buttonBox.setGeometry(QtCore.QRect(100, 430, 160, 26))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.label1 = QLabel(tuflowqgis_1d_iface)
        self.label1.setGeometry(QtCore.QRect(10, 70, 108, 22))
        self.label1.setObjectName(_fromUtf8("label1"))
        self.label2 = QLabel(tuflowqgis_1d_iface)
        self.label2.setGeometry(QtCore.QRect(10, 138, 108, 22))
        self.label2.setObjectName(_fromUtf8("label2"))
        self.ResTypeList = QListWidget(tuflowqgis_1d_iface)
        self.ResTypeList.setGeometry(QtCore.QRect(10, 160, 191, 81))
        self.ResTypeList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.ResTypeList.setObjectName(_fromUtf8("ResTypeList"))
        self.label3 = QLabel(tuflowqgis_1d_iface)
        self.label3.setGeometry(QtCore.QRect(10, 249, 108, 22))
        self.label3.setObjectName(_fromUtf8("label3"))
        self.IDList = QListWidget(tuflowqgis_1d_iface)
        self.IDList.setGeometry(QtCore.QRect(10, 270, 361, 151))
        self.IDList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.IDList.setObjectName(_fromUtf8("IDList"))
        self.locationDrop = QComboBox(tuflowqgis_1d_iface)
        self.locationDrop.setGeometry(QtCore.QRect(10, 90, 331, 22))
        self.locationDrop.setObjectName(_fromUtf8("locationDrop"))
        self.sourcelayer = QComboBox(tuflowqgis_1d_iface)
        self.sourcelayer.setGeometry(QtCore.QRect(10, 40, 331, 22))
        self.sourcelayer.setObjectName(_fromUtf8("sourcelayer"))
        self.label1_2 = QLabel(tuflowqgis_1d_iface)
        self.label1_2.setGeometry(QtCore.QRect(10, 20, 151, 22))
        self.label1_2.setObjectName(_fromUtf8("label1_2"))

        self.retranslateUi(tuflowqgis_1d_iface)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_1d_iface)

    def retranslateUi(self, tuflowqgis_1d_iface):
        tuflowqgis_1d_iface.setWindowTitle(_translate("tuflowqgis_1d_iface", "TUFLOW Results Viewer Interface to TUF1D.py", None))
        self.label1.setText(_translate("tuflowqgis_1d_iface", "Location Type", None))
        self.label2.setText(_translate("tuflowqgis_1d_iface", "Results Type", None))
        self.label3.setText(_translate("tuflowqgis_1d_iface", "Selected Elements", None))
        self.label1_2.setText(_translate("tuflowqgis_1d_iface", "Source Layer to get ID\'s from", None))

