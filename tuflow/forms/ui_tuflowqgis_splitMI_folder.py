# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_splitMI_folder.ui'
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

class Ui_tuflowqgis_splitMI_folder(object):
    def setupUi(self, tuflowqgis_splitMI_folder):
        tuflowqgis_splitMI_folder.setObjectName(_fromUtf8("tuflowqgis_splitMI_folder"))
        tuflowqgis_splitMI_folder.resize(402, 165)
        self.buttonBox = QDialogButtonBox(tuflowqgis_splitMI_folder)
        self.buttonBox.setGeometry(QtCore.QRect(100, 120, 171, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.label2 = QLabel(tuflowqgis_splitMI_folder)
        self.label2.setGeometry(QtCore.QRect(10, 20, 121, 22))
        self.label2.setObjectName(_fromUtf8("label2"))
        self.outfolder = QLineEdit(tuflowqgis_splitMI_folder)
        self.outfolder.setGeometry(QtCore.QRect(10, 50, 261, 21))
        self.outfolder.setReadOnly(False)
        self.outfolder.setObjectName(_fromUtf8("outfolder"))
        self.browseoutfile = QPushButton(tuflowqgis_splitMI_folder)
        self.browseoutfile.setGeometry(QtCore.QRect(290, 50, 81, 26))
        self.browseoutfile.setObjectName(_fromUtf8("browseoutfile"))
        self.cbRecursive = QCheckBox(tuflowqgis_splitMI_folder)
        self.cbRecursive.setGeometry(QtCore.QRect(20, 90, 191, 17))
        self.cbRecursive.setObjectName(_fromUtf8("cbRecursive"))

        self.retranslateUi(tuflowqgis_splitMI_folder)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_splitMI_folder)

    def retranslateUi(self, tuflowqgis_splitMI_folder):
        tuflowqgis_splitMI_folder.setWindowTitle(_translate("tuflowqgis_splitMI_folder", "Convert MI Files in Folder to Shapefile", None))
        self.label2.setText(_translate("tuflowqgis_splitMI_folder", "Input Folder", None))
        self.outfolder.setText(_translate("tuflowqgis_splitMI_folder", "<folder>", None))
        self.browseoutfile.setText(_translate("tuflowqgis_splitMI_folder", "Browse...", None))
        self.cbRecursive.setText(_translate("tuflowqgis_splitMI_folder", "Search in subfolder", None))

