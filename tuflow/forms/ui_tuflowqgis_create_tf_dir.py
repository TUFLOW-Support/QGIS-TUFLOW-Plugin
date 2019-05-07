# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_create_tf_dir.ui'
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

class Ui_tuflowqgis_create_tf_dir(object):
    def setupUi(self, tuflowqgis_create_tf_dir):
        tuflowqgis_create_tf_dir.setObjectName(_fromUtf8("tuflowqgis_create_tf_dir"))
        tuflowqgis_create_tf_dir.resize(397, 352)
        self.buttonBox = QDialogButtonBox(tuflowqgis_create_tf_dir)
        self.buttonBox.setGeometry(QtCore.QRect(120, 310, 161, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.label_1 = QLabel(tuflowqgis_create_tf_dir)
        self.label_1.setGeometry(QtCore.QRect(12, 10, 121, 22))
        self.label_1.setObjectName(_fromUtf8("label_1"))
        self.sourcelayer = QComboBox(tuflowqgis_create_tf_dir)
        self.sourcelayer.setGeometry(QtCore.QRect(10, 30, 351, 27))
        self.sourcelayer.setObjectName(_fromUtf8("sourcelayer"))
        self.label_3 = QLabel(tuflowqgis_create_tf_dir)
        self.label_3.setGeometry(QtCore.QRect(10, 153, 108, 22))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.outdir = QLineEdit(tuflowqgis_create_tf_dir)
        self.outdir.setGeometry(QtCore.QRect(10, 176, 261, 21))
        self.outdir.setReadOnly(False)
        self.outdir.setObjectName(_fromUtf8("outdir"))
        self.browseoutfile = QPushButton(tuflowqgis_create_tf_dir)
        self.browseoutfile.setGeometry(QtCore.QRect(287, 174, 79, 26))
        self.browseoutfile.setObjectName(_fromUtf8("browseoutfile"))
        self.label_2 = QLabel(tuflowqgis_create_tf_dir)
        self.label_2.setGeometry(QtCore.QRect(10, 85, 108, 22))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.sourceCRS = QLineEdit(tuflowqgis_create_tf_dir)
        self.sourceCRS.setGeometry(QtCore.QRect(10, 110, 351, 21))
        self.sourceCRS.setReadOnly(False)
        self.sourceCRS.setObjectName(_fromUtf8("sourceCRS"))
        self.checkBox = QCheckBox(tuflowqgis_create_tf_dir)
        self.checkBox.setGeometry(QtCore.QRect(20, 210, 251, 21))
        self.checkBox.setObjectName(_fromUtf8("checkBox"))
        self.label_4 = QLabel(tuflowqgis_create_tf_dir)
        self.label_4.setGeometry(QtCore.QRect(10, 240, 108, 22))
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.TUFLOW_exe = QLineEdit(tuflowqgis_create_tf_dir)
        self.TUFLOW_exe.setGeometry(QtCore.QRect(10, 260, 261, 21))
        self.TUFLOW_exe.setReadOnly(False)
        self.TUFLOW_exe.setObjectName(_fromUtf8("TUFLOW_exe"))
        self.browseexe = QPushButton(tuflowqgis_create_tf_dir)
        self.browseexe.setGeometry(QtCore.QRect(290, 259, 79, 26))
        self.browseexe.setObjectName(_fromUtf8("browseexe"))

        self.retranslateUi(tuflowqgis_create_tf_dir)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), tuflowqgis_create_tf_dir.accept)
        self.buttonBox.accepted.connect(tuflowqgis_create_tf_dir.accept)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), tuflowqgis_create_tf_dir.reject)
        self.buttonBox.rejected.connect(tuflowqgis_create_tf_dir.reject)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_create_tf_dir)

    def retranslateUi(self, tuflowqgis_create_tf_dir):
        tuflowqgis_create_tf_dir.setWindowTitle(_translate("tuflowqgis_create_tf_dir", "Create TUFLOW Directory Structure", None))
        self.label_1.setText(_translate("tuflowqgis_create_tf_dir", "Source Projection Layer", None))
        self.label_3.setText(_translate("tuflowqgis_create_tf_dir", "Output Directory", None))
        self.outdir.setText(_translate("tuflowqgis_create_tf_dir", "<directory>", None))
        self.browseoutfile.setText(_translate("tuflowqgis_create_tf_dir", "Browse...", None))
        self.label_2.setText(_translate("tuflowqgis_create_tf_dir", "Source Projection", None))
        self.sourceCRS.setText(_translate("tuflowqgis_create_tf_dir", "<projection>", None))
        self.checkBox.setText(_translate("tuflowqgis_create_tf_dir", "Run TUFLOW to create Empties (Windows Only)", None))
        self.label_4.setText(_translate("tuflowqgis_create_tf_dir", "TUFLOW executable", None))
        self.TUFLOW_exe.setText(_translate("tuflowqgis_create_tf_dir", "<TUFLOW exe>", None))
        self.browseexe.setText(_translate("tuflowqgis_create_tf_dir", "Browse...", None))

