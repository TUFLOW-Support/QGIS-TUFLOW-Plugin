# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_run_tf_simple.ui'
#
# Created: Tue Jan 19 11:20:11 2016
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

class Ui_tuflowqgis_run_tf_simple(object):
    def setupUi(self, tuflowqgis_run_tf_simple):
        tuflowqgis_run_tf_simple.setObjectName(_fromUtf8("tuflowqgis_run_tf_simple"))
        tuflowqgis_run_tf_simple.resize(504, 200)
        self.buttonBox = QDialogButtonBox(tuflowqgis_run_tf_simple)
        self.buttonBox.setGeometry(QtCore.QRect(170, 150, 161, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.label_1 = QLabel(tuflowqgis_run_tf_simple)
        self.label_1.setGeometry(QtCore.QRect(10, 23, 141, 22))
        self.label_1.setObjectName(_fromUtf8("label_1"))
        self.tcf = QLineEdit(tuflowqgis_run_tf_simple)
        self.tcf.setGeometry(QtCore.QRect(10, 50, 381, 21))
        self.tcf.setReadOnly(False)
        self.tcf.setObjectName(_fromUtf8("tcf"))
        self.browsetcffile = QPushButton(tuflowqgis_run_tf_simple)
        self.browsetcffile.setGeometry(QtCore.QRect(400, 47, 79, 26))
        self.browsetcffile.setObjectName(_fromUtf8("browsetcffile"))
        self.label_2 = QLabel(tuflowqgis_run_tf_simple)
        self.label_2.setGeometry(QtCore.QRect(10, 90, 108, 22))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.TUFLOW_exe = QLineEdit(tuflowqgis_run_tf_simple)
        self.TUFLOW_exe.setGeometry(QtCore.QRect(10, 110, 381, 21))
        self.TUFLOW_exe.setReadOnly(False)
        self.TUFLOW_exe.setObjectName(_fromUtf8("TUFLOW_exe"))
        self.browseexe = QPushButton(tuflowqgis_run_tf_simple)
        self.browseexe.setGeometry(QtCore.QRect(400, 108, 79, 26))
        self.browseexe.setObjectName(_fromUtf8("browseexe"))

        self.retranslateUi(tuflowqgis_run_tf_simple)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), tuflowqgis_run_tf_simple.accept)
        self.buttonBox.accepted.connect(tuflowqgis_run_tf_simple.accept)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), tuflowqgis_run_tf_simple.reject)
        self.buttonBox.rejected.connect(tuflowqgis_run_tf_simple.reject)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_run_tf_simple)

    def retranslateUi(self, tuflowqgis_run_tf_simple):
        tuflowqgis_run_tf_simple.setWindowTitle(_translate("tuflowqgis_run_tf_simple", "Run TUFLOW (Simple)", None))
        self.label_1.setText(_translate("tuflowqgis_run_tf_simple", "TUFLOW Control File (.tcf)", None))
        self.tcf.setText(_translate("tuflowqgis_run_tf_simple", "<.tcf file>", None))
        self.browsetcffile.setText(_translate("tuflowqgis_run_tf_simple", "Browse...", None))
        self.label_2.setText(_translate("tuflowqgis_run_tf_simple", "TUFLOW executable", None))
        self.TUFLOW_exe.setText(_translate("tuflowqgis_run_tf_simple", "<TUFLOW exe>", None))
        self.browseexe.setText(_translate("tuflowqgis_run_tf_simple", "Browse...", None))

