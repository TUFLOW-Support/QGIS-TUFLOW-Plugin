# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_configure_tuflow_project.ui'
#
# Created: Tue Jan 19 11:20:11 2016
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

class Ui_tuflowqgis_configure_tf(object):
    def setupUi(self, tuflowqgis_configure_tf):
        tuflowqgis_configure_tf.setObjectName(_fromUtf8("tuflowqgis_configure_tf"))
        tuflowqgis_configure_tf.resize(397, 384)
        self.buttonBox = QtGui.QDialogButtonBox(tuflowqgis_configure_tf)
        self.buttonBox.setGeometry(QtCore.QRect(110, 340, 161, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.label_1 = QtGui.QLabel(tuflowqgis_configure_tf)
        self.label_1.setGeometry(QtCore.QRect(12, 10, 121, 22))
        self.label_1.setObjectName(_fromUtf8("label_1"))
        self.sourcelayer = QtGui.QComboBox(tuflowqgis_configure_tf)
        self.sourcelayer.setGeometry(QtCore.QRect(10, 30, 351, 27))
        self.sourcelayer.setObjectName(_fromUtf8("sourcelayer"))
        self.label_3 = QtGui.QLabel(tuflowqgis_configure_tf)
        self.label_3.setGeometry(QtCore.QRect(12, 153, 161, 22))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.outdir = QtGui.QLineEdit(tuflowqgis_configure_tf)
        self.outdir.setGeometry(QtCore.QRect(12, 176, 261, 21))
        self.outdir.setReadOnly(False)
        self.outdir.setObjectName(_fromUtf8("outdir"))
        self.browseoutfile = QtGui.QPushButton(tuflowqgis_configure_tf)
        self.browseoutfile.setGeometry(QtCore.QRect(289, 174, 79, 26))
        self.browseoutfile.setObjectName(_fromUtf8("browseoutfile"))
        self.label_2 = QtGui.QLabel(tuflowqgis_configure_tf)
        self.label_2.setGeometry(QtCore.QRect(10, 101, 181, 22))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.crsDesc = QtGui.QLineEdit(tuflowqgis_configure_tf)
        self.crsDesc.setGeometry(QtCore.QRect(10, 121, 261, 21))
        self.crsDesc.setDragEnabled(False)
        self.crsDesc.setReadOnly(True)
        self.crsDesc.setObjectName(_fromUtf8("crsDesc"))
        self.label_4 = QtGui.QLabel(tuflowqgis_configure_tf)
        self.label_4.setGeometry(QtCore.QRect(10, 212, 108, 22))
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.TUFLOW_exe = QtGui.QLineEdit(tuflowqgis_configure_tf)
        self.TUFLOW_exe.setGeometry(QtCore.QRect(10, 232, 261, 21))
        self.TUFLOW_exe.setReadOnly(False)
        self.TUFLOW_exe.setObjectName(_fromUtf8("TUFLOW_exe"))
        self.browseexe = QtGui.QPushButton(tuflowqgis_configure_tf)
        self.browseexe.setGeometry(QtCore.QRect(290, 231, 79, 26))
        self.browseexe.setObjectName(_fromUtf8("browseexe"))
        self.pbSelectCRS = QtGui.QPushButton(tuflowqgis_configure_tf)
        self.pbSelectCRS.setGeometry(QtCore.QRect(290, 121, 79, 26))
        self.pbSelectCRS.setObjectName(_fromUtf8("pbSelectCRS"))
        self.form_crsID = QtGui.QLineEdit(tuflowqgis_configure_tf)
        self.form_crsID.setGeometry(QtCore.QRect(12, 78, 261, 21))
        self.form_crsID.setDragEnabled(False)
        self.form_crsID.setReadOnly(True)
        self.form_crsID.setObjectName(_fromUtf8("form_crsID"))
        self.label_5 = QtGui.QLabel(tuflowqgis_configure_tf)
        self.label_5.setGeometry(QtCore.QRect(12, 58, 181, 22))
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.cbGlobal = QtGui.QCheckBox(tuflowqgis_configure_tf)
        self.cbGlobal.setGeometry(QtCore.QRect(20, 268, 261, 17))
        self.cbGlobal.setObjectName(_fromUtf8("cbGlobal"))
        self.cbCreate = QtGui.QCheckBox(tuflowqgis_configure_tf)
        self.cbCreate.setGeometry(QtCore.QRect(20, 291, 261, 17))
        self.cbCreate.setObjectName(_fromUtf8("cbCreate"))
        self.cbRun = QtGui.QCheckBox(tuflowqgis_configure_tf)
        self.cbRun.setGeometry(QtCore.QRect(21, 314, 261, 17))
        self.cbRun.setObjectName(_fromUtf8("cbRun"))

        self.retranslateUi(tuflowqgis_configure_tf)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), tuflowqgis_configure_tf.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), tuflowqgis_configure_tf.reject)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_configure_tf)

    def retranslateUi(self, tuflowqgis_configure_tf):
        tuflowqgis_configure_tf.setWindowTitle(_translate("tuflowqgis_configure_tf", "Configure TUFLOW Project", None))
        self.label_1.setText(_translate("tuflowqgis_configure_tf", "Source Projection Layer", None))
        self.label_3.setText(_translate("tuflowqgis_configure_tf", "Folder which contains TUFLOW", None))
        self.outdir.setText(_translate("tuflowqgis_configure_tf", "<directory>", None))
        self.browseoutfile.setText(_translate("tuflowqgis_configure_tf", "Browse...", None))
        self.label_2.setText(_translate("tuflowqgis_configure_tf", "Projection Description (display only)", None))
        self.crsDesc.setText(_translate("tuflowqgis_configure_tf", "<projection description>", None))
        self.label_4.setText(_translate("tuflowqgis_configure_tf", "TUFLOW executable", None))
        self.TUFLOW_exe.setText(_translate("tuflowqgis_configure_tf", "<TUFLOW exe>", None))
        self.browseexe.setText(_translate("tuflowqgis_configure_tf", "Browse...", None))
        self.pbSelectCRS.setText(_translate("tuflowqgis_configure_tf", "Select CRS", None))
        self.form_crsID.setText(_translate("tuflowqgis_configure_tf", "<projection id>", None))
        self.label_5.setText(_translate("tuflowqgis_configure_tf", "Projection ID (display only)", None))
        self.cbGlobal.setText(_translate("tuflowqgis_configure_tf", "Save Default Settings Globally (for all projects)", None))
        self.cbCreate.setText(_translate("tuflowqgis_configure_tf", "Create TUFLOW Folder Structure", None))
        self.cbRun.setText(_translate("tuflowqgis_configure_tf", "Run TUFLOW to create template files", None))

