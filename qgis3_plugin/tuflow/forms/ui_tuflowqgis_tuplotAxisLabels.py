# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_tuplotAxisLabels.ui'
#
# Created: Sun Jun 03 16:50:12 2018
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

class Ui_tuplotAxisLabel(object):
    def setupUi(self, tuplotAxisLabel):
        tuplotAxisLabel.setObjectName(_fromUtf8("tuplotAxisLabel"))
        tuplotAxisLabel.resize(337, 280)
        self.buttonBox = QDialogButtonBox(tuplotAxisLabel)
        self.buttonBox.setGeometry(QtCore.QRect(170, 250, 161, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.xAxisLabel = QLineEdit(tuplotAxisLabel)
        self.xAxisLabel.setGeometry(QtCore.QRect(50, 82, 271, 20))
        self.xAxisLabel.setObjectName(_fromUtf8("xAxisLabel"))
        self.label = QLabel(tuplotAxisLabel)
        self.label.setGeometry(QtCore.QRect(60, 64, 61, 16))
        self.label.setObjectName(_fromUtf8("label"))
        self.label_2 = QLabel(tuplotAxisLabel)
        self.label_2.setGeometry(QtCore.QRect(60, 104, 61, 16))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.yAxisLabel = QLineEdit(tuplotAxisLabel)
        self.yAxisLabel.setGeometry(QtCore.QRect(50, 122, 271, 20))
        self.yAxisLabel.setObjectName(_fromUtf8("yAxisLabel"))
        self.label_3 = QLabel(tuplotAxisLabel)
        self.label_3.setGeometry(QtCore.QRect(60, 161, 121, 16))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.label_4 = QLabel(tuplotAxisLabel)
        self.label_4.setGeometry(QtCore.QRect(60, 201, 121, 16))
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.xAxisLabel2 = QLineEdit(tuplotAxisLabel)
        self.xAxisLabel2.setGeometry(QtCore.QRect(50, 179, 271, 20))
        self.xAxisLabel2.setObjectName(_fromUtf8("xAxisLabel2"))
        self.yAxisLabel2 = QLineEdit(tuplotAxisLabel)
        self.yAxisLabel2.setGeometry(QtCore.QRect(50, 219, 271, 20))
        self.yAxisLabel2.setObjectName(_fromUtf8("yAxisLabel2"))
        self.chartTitle = QLineEdit(tuplotAxisLabel)
        self.chartTitle.setGeometry(QtCore.QRect(50, 32, 271, 20))
        self.chartTitle.setObjectName(_fromUtf8("chartTitle"))
        self.label_5 = QLabel(tuplotAxisLabel)
        self.label_5.setGeometry(QtCore.QRect(60, 14, 61, 16))
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.xAxisAuto_cb = QCheckBox(tuplotAxisLabel)
        self.xAxisAuto_cb.setGeometry(QtCore.QRect(23, 83, 16, 17))
        self.xAxisAuto_cb.setText(_fromUtf8(""))
        self.xAxisAuto_cb.setObjectName(_fromUtf8("xAxisAuto_cb"))
        self.label_6 = QLabel(tuplotAxisLabel)
        self.label_6.setGeometry(QtCore.QRect(2, 5, 40, 31))
        self.label_6.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_6.setWordWrap(True)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.yAxisAuto_cb = QCheckBox(tuplotAxisLabel)
        self.yAxisAuto_cb.setGeometry(QtCore.QRect(23, 123, 16, 17))
        self.yAxisAuto_cb.setText(_fromUtf8(""))
        self.yAxisAuto_cb.setObjectName(_fromUtf8("yAxisAuto_cb"))
        self.xAxisAuto2_cb = QCheckBox(tuplotAxisLabel)
        self.xAxisAuto2_cb.setGeometry(QtCore.QRect(25, 180, 16, 17))
        self.xAxisAuto2_cb.setText(_fromUtf8(""))
        self.xAxisAuto2_cb.setObjectName(_fromUtf8("xAxisAuto2_cb"))
        self.yAxisAuto2_cb = QCheckBox(tuplotAxisLabel)
        self.yAxisAuto2_cb.setGeometry(QtCore.QRect(25, 220, 16, 17))
        self.yAxisAuto2_cb.setText(_fromUtf8(""))
        self.yAxisAuto2_cb.setObjectName(_fromUtf8("yAxisAuto2_cb"))
        self.line = QFrame(tuplotAxisLabel)
        self.line.setGeometry(QtCore.QRect(37, 5, 20, 271))
        self.line.setFrameShape(QFrame.VLine)
        self.line.setFrameShadow(QFrame.Sunken)
        self.line.setObjectName(_fromUtf8("line"))

        self.retranslateUi(tuplotAxisLabel)
        self.buttonBox.accepted.connect(tuplotAxisLabel.accept)
        self.buttonBox.rejected.connect(tuplotAxisLabel.reject)
        QtCore.QMetaObject.connectSlotsByName(tuplotAxisLabel)

    def retranslateUi(self, tuplotAxisLabel):
        tuplotAxisLabel.setWindowTitle(_translate("tuplotAxisLabel", "Tuplot - Axis Labels", None))
        self.label.setText(_translate("tuplotAxisLabel", "X Axis Label", None))
        self.label_2.setText(_translate("tuplotAxisLabel", "Y Axis Label", None))
        self.label_3.setText(_translate("tuplotAxisLabel", "Secondary X Axis Label", None))
        self.label_4.setText(_translate("tuplotAxisLabel", "Secondary Y Axis Label", None))
        self.label_5.setText(_translate("tuplotAxisLabel", "Chart Title", None))
        self.label_6.setText(_translate("tuplotAxisLabel", "Use Custom", None))

