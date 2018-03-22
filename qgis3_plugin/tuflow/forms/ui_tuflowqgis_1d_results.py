# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_1d_results.ui'
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

class Ui_tuflowqgis_1d_results(object):
    def setupUi(self, tuflowqgis_1d_results):
        tuflowqgis_1d_results.setObjectName(_fromUtf8("tuflowqgis_1d_results"))
        tuflowqgis_1d_results.resize(400, 300)
        self.buttonBox = QDialogButtonBox(tuflowqgis_1d_results)
        self.buttonBox.setGeometry(QtCore.QRect(80, 240, 191, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.label = QLabel(tuflowqgis_1d_results)
        self.label.setGeometry(QtCore.QRect(30, 20, 321, 51))
        font = QFont()
        font.setPointSize(12)
        self.label.setFont(font)
        self.label.setObjectName(_fromUtf8("label"))
        self.label_2 = QLabel(tuflowqgis_1d_results)
        self.label_2.setGeometry(QtCore.QRect(30, 70, 321, 101))
        font = QFont()
        font.setPointSize(12)
        self.label_2.setFont(font)
        self.label_2.setObjectName(_fromUtf8("label_2"))

        self.retranslateUi(tuflowqgis_1d_results)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), tuflowqgis_1d_results.accept)
        self.buttonBox.accepted.connect(tuflowqgis_1d_results.acceptt)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), tuflowqgis_1d_results.reject)
        self.buttonBox.rejected.connect(tuflowqgis_1d_results.reject)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_1d_results)

    def retranslateUi(self, tuflowqgis_1d_results):
        tuflowqgis_1d_results.setWindowTitle(_translate("tuflowqgis_1d_results", "TUFLOW 1D Results Viewer", None))
        self.label.setText(_translate("tuflowqgis_1d_results", "This 1D results visualisation is currently \n"
"being interegrated with QGIS.", None))
        self.label_2.setText(_translate("tuflowqgis_1d_results", "Clicking OK will launch the utility in \n"
"stand-alone mode. \n"
"It requires the results in the format \n"
"outputted in the beta 2013 TUFLOW release.", None))

