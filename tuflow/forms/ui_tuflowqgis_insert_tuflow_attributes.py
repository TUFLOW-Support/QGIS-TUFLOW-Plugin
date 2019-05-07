# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_insert_tuflow_attributes.ui'
#
# Created: Fri Feb 23 13:30:38 2018
#      by: PyQt4 UI code generator 4.10.2
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

class Ui_tuflowqgis_insert_tuflow_attributes(object):
    def setupUi(self, tuflowqgis_insert_tuflow_attributes):
        tuflowqgis_insert_tuflow_attributes.setObjectName(_fromUtf8("tuflowqgis_insert_tuflow_attributes"))
        tuflowqgis_insert_tuflow_attributes.setWindowModality(QtCore.Qt.ApplicationModal)
        tuflowqgis_insert_tuflow_attributes.setEnabled(True)
        tuflowqgis_insert_tuflow_attributes.resize(372, 242)
        tuflowqgis_insert_tuflow_attributes.setMouseTracking(False)
        self.buttonBox = QDialogButtonBox(tuflowqgis_insert_tuflow_attributes)
        self.buttonBox.setGeometry(QtCore.QRect(200, 210, 160, 26))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.label1 = QLabel(tuflowqgis_insert_tuflow_attributes)
        self.label1.setGeometry(QtCore.QRect(10, 10, 108, 22))
        self.label1.setObjectName(_fromUtf8("label1"))
        self.emptydir = QLineEdit(tuflowqgis_insert_tuflow_attributes)
        self.emptydir.setGeometry(QtCore.QRect(10, 30, 261, 21))
        self.emptydir.setReadOnly(False)
        self.emptydir.setObjectName(_fromUtf8("emptydir"))
        self.browsedir = QPushButton(tuflowqgis_insert_tuflow_attributes)
        self.browsedir.setGeometry(QtCore.QRect(281, 27, 79, 26))
        self.browsedir.setObjectName(_fromUtf8("browsedir"))
        self.label2 = QLabel(tuflowqgis_insert_tuflow_attributes)
        self.label2.setGeometry(QtCore.QRect(10, 110, 121, 22))
        self.label2.setObjectName(_fromUtf8("label2"))
        self.txtRunID = QLineEdit(tuflowqgis_insert_tuflow_attributes)
        self.txtRunID.setGeometry(QtCore.QRect(10, 180, 261, 21))
        self.txtRunID.setReadOnly(False)
        self.txtRunID.setObjectName(_fromUtf8("txtRunID"))
        self.label3 = QLabel(tuflowqgis_insert_tuflow_attributes)
        self.label3.setGeometry(QtCore.QRect(10, 160, 108, 22))
        self.label3.setObjectName(_fromUtf8("label3"))
        self.label3_2 = QLabel(tuflowqgis_insert_tuflow_attributes)
        self.label3_2.setGeometry(QtCore.QRect(10, 60, 108, 22))
        self.label3_2.setObjectName(_fromUtf8("label3_2"))
        self.comboBox_inputLayer = QComboBox(tuflowqgis_insert_tuflow_attributes)
        self.comboBox_inputLayer.setGeometry(QtCore.QRect(10, 80, 351, 22))
        self.comboBox_inputLayer.setObjectName(_fromUtf8("comboBox_inputLayer"))
        self.comboBox_tfType = QComboBox(tuflowqgis_insert_tuflow_attributes)
        self.comboBox_tfType.setGeometry(QtCore.QRect(10, 130, 261, 22))
        self.comboBox_tfType.setObjectName(_fromUtf8("comboBox_tfType"))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))
        self.comboBox_tfType.addItem(_fromUtf8(""))

        self.retranslateUi(tuflowqgis_insert_tuflow_attributes)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), tuflowqgis_insert_tuflow_attributes.accept)
        self.buttonBox.accepted.connect(tuflowqgis_insert_tuflow_attributes.accept)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), tuflowqgis_insert_tuflow_attributes.reject)
        self.buttonBox.rejected.connect(tuflowqgis_insert_tuflow_attributes.reject)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_insert_tuflow_attributes)

    def retranslateUi(self, tuflowqgis_insert_tuflow_attributes):
        tuflowqgis_insert_tuflow_attributes.setWindowTitle(_translate("tuflowqgis_insert_tuflow_attributes", "Insert TUFLOW attributes to existing GIS layer", None))
        self.label1.setText(_translate("tuflowqgis_insert_tuflow_attributes", "Empty Directory", None))
        self.emptydir.setText(_translate("tuflowqgis_insert_tuflow_attributes", "<directory>", None))
        self.browsedir.setText(_translate("tuflowqgis_insert_tuflow_attributes", "Browse...", None))
        self.label2.setText(_translate("tuflowqgis_insert_tuflow_attributes", "TUFLOW attribute type", None))
        self.txtRunID.setText(_translate("tuflowqgis_insert_tuflow_attributes", "<RunID>", None))
        self.label3.setText(_translate("tuflowqgis_insert_tuflow_attributes", "Run ID", None))
        self.label3_2.setText(_translate("tuflowqgis_insert_tuflow_attributes", "Input Layer", None))
        self.comboBox_tfType.setItemText(0, _translate("tuflowqgis_insert_tuflow_attributes", "0d_RL", None))
        self.comboBox_tfType.setItemText(1, _translate("tuflowqgis_insert_tuflow_attributes", "1d_bc", None))
        self.comboBox_tfType.setItemText(2, _translate("tuflowqgis_insert_tuflow_attributes", "1d_iwl", None))
        self.comboBox_tfType.setItemText(3, _translate("tuflowqgis_insert_tuflow_attributes", "1d_mh", None))
        self.comboBox_tfType.setItemText(4, _translate("tuflowqgis_insert_tuflow_attributes", "1d_nd", None))
        self.comboBox_tfType.setItemText(5, _translate("tuflowqgis_insert_tuflow_attributes", "1d_nwk", None))
        self.comboBox_tfType.setItemText(6, _translate("tuflowqgis_insert_tuflow_attributes", "1d_nwkb", None))
        self.comboBox_tfType.setItemText(7, _translate("tuflowqgis_insert_tuflow_attributes", "1d_nwke", None))
        self.comboBox_tfType.setItemText(8, _translate("tuflowqgis_insert_tuflow_attributes", "1d_pit", None))
        self.comboBox_tfType.setItemText(9, _translate("tuflowqgis_insert_tuflow_attributes", "1d_tab", None))
        self.comboBox_tfType.setItemText(10, _translate("tuflowqgis_insert_tuflow_attributes", "1d_WLL", None))
        self.comboBox_tfType.setItemText(11, _translate("tuflowqgis_insert_tuflow_attributes", "2d_bc", None))
        self.comboBox_tfType.setItemText(12, _translate("tuflowqgis_insert_tuflow_attributes", "2d_code", None))
        self.comboBox_tfType.setItemText(13, _translate("tuflowqgis_insert_tuflow_attributes", "2d_fc", None))
        self.comboBox_tfType.setItemText(14, _translate("tuflowqgis_insert_tuflow_attributes", "2d_fcsh", None))
        self.comboBox_tfType.setItemText(15, _translate("tuflowqgis_insert_tuflow_attributes", "2d_glo", None))
        self.comboBox_tfType.setItemText(16, _translate("tuflowqgis_insert_tuflow_attributes", "2d_gw", None))
        self.comboBox_tfType.setItemText(17, _translate("tuflowqgis_insert_tuflow_attributes", "2d_iwl", None))
        self.comboBox_tfType.setItemText(18, _translate("tuflowqgis_insert_tuflow_attributes", "2d_lfcsh", None))
        self.comboBox_tfType.setItemText(19, _translate("tuflowqgis_insert_tuflow_attributes", "2d_loc", None))
        self.comboBox_tfType.setItemText(20, _translate("tuflowqgis_insert_tuflow_attributes", "2d_lp", None))
        self.comboBox_tfType.setItemText(21, _translate("tuflowqgis_insert_tuflow_attributes", "2d_mat", None))
        self.comboBox_tfType.setItemText(22, _translate("tuflowqgis_insert_tuflow_attributes", "2d_oz", None))
        self.comboBox_tfType.setItemText(23, _translate("tuflowqgis_insert_tuflow_attributes", "2d_po", None))
        self.comboBox_tfType.setItemText(24, _translate("tuflowqgis_insert_tuflow_attributes", "2d_rf", None))
        self.comboBox_tfType.setItemText(25, _translate("tuflowqgis_insert_tuflow_attributes", "2d_sa", None))
        self.comboBox_tfType.setItemText(26, _translate("tuflowqgis_insert_tuflow_attributes", "2d_sa_rf", None))
        self.comboBox_tfType.setItemText(27, _translate("tuflowqgis_insert_tuflow_attributes", "2d_sa_tr", None))
        self.comboBox_tfType.setItemText(28, _translate("tuflowqgis_insert_tuflow_attributes", "2d_soil", None))
        self.comboBox_tfType.setItemText(29, _translate("tuflowqgis_insert_tuflow_attributes", "2d_vzsh", None))
        self.comboBox_tfType.setItemText(30, _translate("tuflowqgis_insert_tuflow_attributes", "2d_z__", None))
        self.comboBox_tfType.setItemText(31, _translate("tuflowqgis_insert_tuflow_attributes", "2d_zsh", None))
        self.comboBox_tfType.setItemText(32, _translate("tuflowqgis_insert_tuflow_attributes", "2d_zshr", None))

