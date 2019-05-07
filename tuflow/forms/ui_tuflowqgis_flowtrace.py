# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_flowtrace.ui'
#
# Created: Tue Jan 19 11:20:12 2016
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

class Ui_tuflowqgis_flowtrace(object):
    def setupUi(self, tuflowqgis_flowtrace):
        tuflowqgis_flowtrace.setObjectName(_fromUtf8("tuflowqgis_flowtrace"))
        tuflowqgis_flowtrace.resize(400, 300)
        self.buttonBox = QDialogButtonBox(tuflowqgis_flowtrace)
        self.buttonBox.setGeometry(QtCore.QRect(100, 260, 171, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.cb_US = QCheckBox(tuflowqgis_flowtrace)
        self.cb_US.setGeometry(QtCore.QRect(27, 27, 121, 17))
        self.cb_US.setChecked(True)
        self.cb_US.setObjectName(_fromUtf8("cb_US"))
        self.pb_Run = QPushButton(tuflowqgis_flowtrace)
        self.pb_Run.setGeometry(QtCore.QRect(160, 230, 75, 23))
        self.pb_Run.setObjectName(_fromUtf8("pb_Run"))
        self.cb_DS = QCheckBox(tuflowqgis_flowtrace)
        self.cb_DS.setGeometry(QtCore.QRect(220, 30, 121, 17))
        self.cb_DS.setChecked(True)
        self.cb_DS.setObjectName(_fromUtf8("cb_DS"))
        self.lw_Log = QListWidget(tuflowqgis_flowtrace)
        self.lw_Log.setGeometry(QtCore.QRect(20, 90, 361, 131))
        self.lw_Log.setObjectName(_fromUtf8("lw_Log"))
        self.le_dt = QLineEdit(tuflowqgis_flowtrace)
        self.le_dt.setGeometry(QtCore.QRect(20, 60, 113, 20))
        self.le_dt.setObjectName(_fromUtf8("le_dt"))
        self.label = QLabel(tuflowqgis_flowtrace)
        self.label.setGeometry(QtCore.QRect(140, 60, 141, 16))
        self.label.setObjectName(_fromUtf8("label"))

        self.retranslateUi(tuflowqgis_flowtrace)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_flowtrace)

    def retranslateUi(self, tuflowqgis_flowtrace):
        tuflowqgis_flowtrace.setWindowTitle(_translate("tuflowqgis_flowtrace", "Trace Connectivity", None))
        self.cb_US.setText(_translate("tuflowqgis_flowtrace", "Search upstream", None))
        self.pb_Run.setText(_translate("tuflowqgis_flowtrace", "Run", None))
        self.cb_DS.setText(_translate("tuflowqgis_flowtrace", "Search downstream", None))
        self.le_dt.setText(_translate("tuflowqgis_flowtrace", "1.0", None))
        self.label.setText(_translate("tuflowqgis_flowtrace", "Snap Tolerance (map units)", None))

