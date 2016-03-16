# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_tuflowqgis_line_from_points.ui'
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

class Ui_tuflowqgis_line_from_point(object):
    def setupUi(self, tuflowqgis_line_from_point):
        tuflowqgis_line_from_point.setObjectName(_fromUtf8("tuflowqgis_line_from_point"))
        tuflowqgis_line_from_point.resize(400, 279)
        self.buttonBox = QtGui.QDialogButtonBox(tuflowqgis_line_from_point)
        self.buttonBox.setGeometry(QtCore.QRect(130, 230, 151, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.label_1 = QtGui.QLabel(tuflowqgis_line_from_point)
        self.label_1.setGeometry(QtCore.QRect(12, 10, 108, 22))
        self.label_1.setObjectName(_fromUtf8("label_1"))
        self.sourcelayer = QtGui.QComboBox(tuflowqgis_line_from_point)
        self.sourcelayer.setGeometry(QtCore.QRect(10, 30, 351, 27))
        self.sourcelayer.setObjectName(_fromUtf8("sourcelayer"))
        self.label_4 = QtGui.QLabel(tuflowqgis_line_from_point)
        self.label_4.setGeometry(QtCore.QRect(12, 170, 108, 22))
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.outfilename = QtGui.QLineEdit(tuflowqgis_line_from_point)
        self.outfilename.setGeometry(QtCore.QRect(10, 190, 261, 21))
        self.outfilename.setReadOnly(False)
        self.outfilename.setObjectName(_fromUtf8("outfilename"))
        self.browseoutfile = QtGui.QPushButton(tuflowqgis_line_from_point)
        self.browseoutfile.setGeometry(QtCore.QRect(300, 190, 79, 26))
        self.browseoutfile.setObjectName(_fromUtf8("browseoutfile"))
        self.label_2 = QtGui.QLabel(tuflowqgis_line_from_point)
        self.label_2.setGeometry(QtCore.QRect(12, 120, 351, 22))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.dmax = QtGui.QLineEdit(tuflowqgis_line_from_point)
        self.dmax.setGeometry(QtCore.QRect(10, 140, 171, 21))
        self.dmax.setReadOnly(False)
        self.dmax.setObjectName(_fromUtf8("dmax"))
        self.label_3 = QtGui.QLabel(tuflowqgis_line_from_point)
        self.label_3.setGeometry(QtCore.QRect(12, 60, 108, 22))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.elev_attr = QtGui.QComboBox(tuflowqgis_line_from_point)
        self.elev_attr.setGeometry(QtCore.QRect(10, 80, 351, 27))
        self.elev_attr.setObjectName(_fromUtf8("elev_attr"))

        self.retranslateUi(tuflowqgis_line_from_point)
        QtCore.QMetaObject.connectSlotsByName(tuflowqgis_line_from_point)

    def retranslateUi(self, tuflowqgis_line_from_point):
        tuflowqgis_line_from_point.setWindowTitle(_translate("tuflowqgis_line_from_point", "Create Breakline from Points", None))
        self.label_1.setText(_translate("tuflowqgis_line_from_point", "Source Point Layer", None))
        self.label_4.setText(_translate("tuflowqgis_line_from_point", "Output File", None))
        self.outfilename.setText(_translate("tuflowqgis_line_from_point", "<filename.shp>", None))
        self.browseoutfile.setText(_translate("tuflowqgis_line_from_point", "Browse...", None))
        self.label_2.setText(_translate("tuflowqgis_line_from_point", "Maximum Distance Between Points", None))
        self.dmax.setText(_translate("tuflowqgis_line_from_point", "10", None))
        self.label_3.setText(_translate("tuflowqgis_line_from_point", "Elevation Attribute", None))

