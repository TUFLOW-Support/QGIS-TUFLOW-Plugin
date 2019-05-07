# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_increment.ui'
#
# Created: Tue Mar 29 20:47:10 2016
#      by: PyQt4 UI code generator 4.11.1
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

class Ui_tuflowqgis_increment(object):
    def setupUi(self, tuflowqgis_increment):
        tuflowqgis_increment.setObjectName(_fromUtf8("tuflowqgis_increment"))
        tuflowqgis_increment.resize(400, 275)
        self.buttonBox = QtGui.QDialogButtonBox(tuflowqgis_increment)
        self.buttonBox.setGeometry(QtCore.QRect(-60, 230, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.label_1 = QtGui.QLabel(tuflowqgis_increment)
        self.label_1.setGeometry(QtCore.QRect(12, 10, 108, 22))
        self.label_1.setObjectName(_fromUtf8("label_1"))
        self.sourcelayer = QtGui.QComboBox(tuflowqgis_increment)
        self.sourcelayer.setGeometry(QtCore.QRect(10, 30, 361, 27))
        self.sourcelayer.setObjectName(_fromUtf8("sourcelayer"))
        self.label = QtGui.QLabel(tuflowqgis_increment)
        self.label.setGeometry(QtCore.QRect(10, 170, 108, 22))
        self.label.setObjectName(_fromUtf8("label"))
        self.outfilename = QtGui.QLineEdit(tuflowqgis_increment)
        self.outfilename.setGeometry(QtCore.QRect(10, 190, 261, 21))
        self.outfilename.setReadOnly(False)
        self.outfilename.setObjectName(_fromUtf8("outfilename"))
        self.browseoutfile = QtGui.QPushButton(tuflowqgis_increment)
        self.browseoutfile.setGeometry(QtCore.QRect(290, 190, 79, 26))
        self.browseoutfile.setObjectName(_fromUtf8("browseoutfile"))
        self.label_2 = QtGui.QLabel(tuflowqgis_increment)
        self.label_2.setGeometry(QtCore.QRect(10, 120, 108, 22))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.outfolder = QtGui.QLineEdit(tuflowqgis_increment)
        self.outfolder.setGeometry(QtCore.QRect(10, 140, 361, 21))
        self.outfolder.setReadOnly(False)
        self.outfolder.setObjectName(_fromUtf8("outfolder"))
        self.checkBox = QtGui.QCheckBox(tuflowqgis_increment)
        self.checkBox.setGeometry(QtCore.QRect(10, 70, 141, 17))
        self.checkBox.setAcceptDrops(False)
        self.checkBox.setChecked(False)
        self.checkBox.setObjectName(_fromUtf8("checkBox"))

        self.retranslateUi(tuflowqgis_increment)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), tuflowqgis_increment.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), tuflowqgis_increment.reject)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_increment)

    def retranslateUi(self, tuflowqgis_increment):
        tuflowqgis_increment.setWindowTitle(_translate("tuflowqgis_increment", "Increment Selected Layer", None))
        self.label_1.setText(_translate("tuflowqgis_increment", "Source Layer", None))
        self.label.setText(_translate("tuflowqgis_increment", "Output File", None))
        self.outfilename.setText(_translate("tuflowqgis_increment", "<filename.shp>", None))
        self.browseoutfile.setText(_translate("tuflowqgis_increment", "Browse...", None))
        self.label_2.setText(_translate("tuflowqgis_increment", "Output Folder", None))
        self.outfolder.setText(_translate("tuflowqgis_increment", "<outfolder>", None))
        self.checkBox.setText(_translate("tuflowqgis_increment", "Keep Source Formatting", None))

