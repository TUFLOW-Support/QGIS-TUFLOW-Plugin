# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_menu.ui'
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

class Ui_tuflowqgis_menu(object):
    def setupUi(self, tuflowqgis_menu):
        tuflowqgis_menu.setObjectName(_fromUtf8("tuflowqgis_menu"))
        tuflowqgis_menu.resize(400, 300)
        self.buttonBox = QDialogButtonBox(tuflowqgis_menu)
        self.buttonBox.setGeometry(QtCore.QRect(30, 240, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))

        self.retranslateUi(tuflowqgis_menu)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), tuflowqgis_menu.accept)
        self.buttonBox.accepted.connect(tuflowqgis_menu.accept)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), tuflowqgis_menu.reject)
        self.buttonBox.rejected.connect(tuflowqgis_menu.reject)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_menu)

    def retranslateUi(self, tuflowqgis_menu):
        tuflowqgis_menu.setWindowTitle(_translate("tuflowqgis_menu", "tuflowqgis_menu", None))

