# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_configure_tuflow_project.ui'
#
# Created: Tue Jan 14 10:29:16 2014
#      by: PyQt4 UI code generator 4.10.3
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
        tuflowqgis_configure_tf.resize(397, 293)
        self.buttonBox = QtGui.QDialogButtonBox(tuflowqgis_configure_tf)
        self.buttonBox.setGeometry(QtCore.QRect(110, 250, 161, 32))
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
        self.label_3.setGeometry(QtCore.QRect(12, 122, 161, 22))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.outdir = QtGui.QLineEdit(tuflowqgis_configure_tf)
        self.outdir.setGeometry(QtCore.QRect(12, 145, 261, 21))
        self.outdir.setReadOnly(False)
        self.outdir.setObjectName(_fromUtf8("outdir"))
        self.browseoutfile = QtGui.QPushButton(tuflowqgis_configure_tf)
        self.browseoutfile.setGeometry(QtCore.QRect(289, 143, 79, 26))
        self.browseoutfile.setObjectName(_fromUtf8("browseoutfile"))
        self.label_2 = QtGui.QLabel(tuflowqgis_configure_tf)
        self.label_2.setGeometry(QtCore.QRect(10, 70, 181, 22))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.sourceCRS = QtGui.QLineEdit(tuflowqgis_configure_tf)
        self.sourceCRS.setGeometry(QtCore.QRect(10, 90, 351, 21))
        self.sourceCRS.setDragEnabled(False)
        self.sourceCRS.setReadOnly(True)
        self.sourceCRS.setObjectName(_fromUtf8("sourceCRS"))
        self.label_4 = QtGui.QLabel(tuflowqgis_configure_tf)
        self.label_4.setGeometry(QtCore.QRect(10, 181, 108, 22))
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.TUFLOW_exe = QtGui.QLineEdit(tuflowqgis_configure_tf)
        self.TUFLOW_exe.setGeometry(QtCore.QRect(10, 201, 261, 21))
        self.TUFLOW_exe.setReadOnly(False)
        self.TUFLOW_exe.setObjectName(_fromUtf8("TUFLOW_exe"))
        self.browseexe = QtGui.QPushButton(tuflowqgis_configure_tf)
        self.browseexe.setGeometry(QtCore.QRect(290, 200, 79, 26))
        self.browseexe.setObjectName(_fromUtf8("browseexe"))

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
        self.label_2.setText(_translate("tuflowqgis_configure_tf", "Source Projection Text (display only)", None))
        self.sourceCRS.setText(_translate("tuflowqgis_configure_tf", "<projection>", None))
        self.label_4.setText(_translate("tuflowqgis_configure_tf", "TUFLOW executable", None))
        self.TUFLOW_exe.setText(_translate("tuflowqgis_configure_tf", "<TUFLOW exe>", None))
        self.browseexe.setText(_translate("tuflowqgis_configure_tf", "Browse...", None))

