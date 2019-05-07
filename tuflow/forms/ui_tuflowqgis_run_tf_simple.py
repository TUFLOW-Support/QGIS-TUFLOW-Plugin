# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\ui_tuflowqgis_run_tf_simple.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_tuflowqgis_run_tf_simple(object):
    def setupUi(self, tuflowqgis_run_tf_simple):
        tuflowqgis_run_tf_simple.setObjectName("tuflowqgis_run_tf_simple")
        tuflowqgis_run_tf_simple.resize(504, 200)
        self.buttonBox = QtWidgets.QDialogButtonBox(tuflowqgis_run_tf_simple)
        self.buttonBox.setGeometry(QtCore.QRect(170, 150, 161, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.label_1 = QtWidgets.QLabel(tuflowqgis_run_tf_simple)
        self.label_1.setGeometry(QtCore.QRect(10, 23, 191, 22))
        self.label_1.setObjectName("label_1")
        self.tcf = QtWidgets.QLineEdit(tuflowqgis_run_tf_simple)
        self.tcf.setGeometry(QtCore.QRect(10, 50, 381, 21))
        self.tcf.setReadOnly(False)
        self.tcf.setObjectName("tcf")
        self.browsetcffile = QtWidgets.QPushButton(tuflowqgis_run_tf_simple)
        self.browsetcffile.setGeometry(QtCore.QRect(400, 47, 79, 26))
        self.browsetcffile.setObjectName("browsetcffile")
        self.label_2 = QtWidgets.QLabel(tuflowqgis_run_tf_simple)
        self.label_2.setGeometry(QtCore.QRect(10, 90, 108, 22))
        self.label_2.setObjectName("label_2")
        self.TUFLOW_exe = QtWidgets.QLineEdit(tuflowqgis_run_tf_simple)
        self.TUFLOW_exe.setGeometry(QtCore.QRect(10, 110, 381, 21))
        self.TUFLOW_exe.setReadOnly(False)
        self.TUFLOW_exe.setObjectName("TUFLOW_exe")
        self.browseexe = QtWidgets.QPushButton(tuflowqgis_run_tf_simple)
        self.browseexe.setGeometry(QtCore.QRect(400, 108, 79, 26))
        self.browseexe.setObjectName("browseexe")

        self.retranslateUi(tuflowqgis_run_tf_simple)
        self.buttonBox.accepted.connect(tuflowqgis_run_tf_simple.accept)
        self.buttonBox.rejected.connect(tuflowqgis_run_tf_simple.reject)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_run_tf_simple)

    def retranslateUi(self, tuflowqgis_run_tf_simple):
        _translate = QtCore.QCoreApplication.translate
        tuflowqgis_run_tf_simple.setWindowTitle(_translate("tuflowqgis_run_tf_simple", "Run TUFLOW (Simple)"))
        self.label_1.setText(_translate("tuflowqgis_run_tf_simple", "TUFLOW Control File (.tcf or .fvc)"))
        self.tcf.setText(_translate("tuflowqgis_run_tf_simple", "<control file>"))
        self.browsetcffile.setText(_translate("tuflowqgis_run_tf_simple", "Browse..."))
        self.label_2.setText(_translate("tuflowqgis_run_tf_simple", "TUFLOW executable"))
        self.TUFLOW_exe.setText(_translate("tuflowqgis_run_tf_simple", "<TUFLOW exe>"))
        self.browseexe.setText(_translate("tuflowqgis_run_tf_simple", "Browse..."))

