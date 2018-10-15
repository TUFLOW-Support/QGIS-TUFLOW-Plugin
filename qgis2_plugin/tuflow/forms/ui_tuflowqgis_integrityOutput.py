# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_integrityOutput.ui'
#
# Created: Fri Apr 27 11:19:26 2018
#      by: PyQt4 UI code generator 4.10.2
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

class Ui_integrityOutput(object):
    def setupUi(self, integrityOutput):
        integrityOutput.setObjectName(_fromUtf8("integrityOutput"))
        integrityOutput.resize(511, 672)
        self.gridLayout = QtGui.QGridLayout(integrityOutput)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.textBrowser = QtGui.QTextBrowser(integrityOutput)
        self.textBrowser.setObjectName(_fromUtf8("textBrowser"))
        self.gridLayout.addWidget(self.textBrowser, 0, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(integrityOutput)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.retranslateUi(integrityOutput)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), integrityOutput.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), integrityOutput.reject)
        QtCore.QMetaObject.connectSlotsByName(integrityOutput)

    def retranslateUi(self, integrityOutput):
        integrityOutput.setWindowTitle(_translate("integrityOutput", "1D Integrity Output", None))

