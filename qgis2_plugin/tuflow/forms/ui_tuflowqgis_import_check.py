# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_import_check.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
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

class Ui_tuflowqgis_import_check(object):
    def setupUi(self, tuflowqgis_import_check):
        tuflowqgis_import_check.setObjectName(_fromUtf8("tuflowqgis_import_check"))
        tuflowqgis_import_check.setWindowModality(QtCore.Qt.ApplicationModal)
        tuflowqgis_import_check.setEnabled(True)
        tuflowqgis_import_check.resize(388, 183)
        tuflowqgis_import_check.setMouseTracking(False)
        self.gridLayout = QtGui.QGridLayout(tuflowqgis_import_check)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label1 = QtGui.QLabel(tuflowqgis_import_check)
        self.label1.setObjectName(_fromUtf8("label1"))
        self.gridLayout.addWidget(self.label1, 0, 0, 1, 1)
        self.browsedir = QtGui.QPushButton(tuflowqgis_import_check)
        self.browsedir.setObjectName(_fromUtf8("browsedir"))
        self.gridLayout.addWidget(self.browsedir, 1, 0, 1, 1)
        self.emptydir = QtGui.QLineEdit(tuflowqgis_import_check)
        self.emptydir.setReadOnly(False)
        self.emptydir.setObjectName(_fromUtf8("emptydir"))
        self.gridLayout.addWidget(self.emptydir, 2, 0, 1, 1)
        self.label3 = QtGui.QLabel(tuflowqgis_import_check)
        self.label3.setObjectName(_fromUtf8("label3"))
        self.gridLayout.addWidget(self.label3, 3, 0, 1, 1)
        self.txtRunID = QtGui.QLineEdit(tuflowqgis_import_check)
        self.txtRunID.setReadOnly(False)
        self.txtRunID.setObjectName(_fromUtf8("txtRunID"))
        self.gridLayout.addWidget(self.txtRunID, 4, 0, 1, 1)
        self.showchecks = QtGui.QRadioButton(tuflowqgis_import_check)
        self.showchecks.setChecked(True)
        self.showchecks.setObjectName(_fromUtf8("showchecks"))
        self.gridLayout.addWidget(self.showchecks, 5, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(tuflowqgis_import_check)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 6, 0, 1, 1)

        self.retranslateUi(tuflowqgis_import_check)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), tuflowqgis_import_check.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), tuflowqgis_import_check.reject)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_import_check)

    def retranslateUi(self, tuflowqgis_import_check):
        tuflowqgis_import_check.setWindowTitle(_translate("tuflowqgis_import_check", "Import TUFLOW Check File", None))
        self.label1.setText(_translate("tuflowqgis_import_check", "Check Directory", None))
        self.browsedir.setText(_translate("tuflowqgis_import_check", "Browse...", None))
        self.emptydir.setText(_translate("tuflowqgis_import_check", "<directory>", None))
        self.label3.setText(_translate("tuflowqgis_import_check", "Run ID", None))
        self.txtRunID.setText(_translate("tuflowqgis_import_check", "RunID", None))
        self.showchecks.setText(_translate("tuflowqgis_import_check", "Check Files Visible (uvpt, zpt and grd are always non-visible by default)", None))

