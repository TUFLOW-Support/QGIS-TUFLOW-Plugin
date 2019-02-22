# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\label_properties.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_textPropertiesDialog(object):
    def setupUi(self, textPropertiesDialog):
        textPropertiesDialog.setObjectName("textPropertiesDialog")
        textPropertiesDialog.resize(444, 127)
        self.verticalLayout = QtWidgets.QVBoxLayout(textPropertiesDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 0, 2, 1, 1)
        self.fntButton = QgsFontButton(textPropertiesDialog)
        self.fntButton.setMinimumSize(QtCore.QSize(0, 21))
        self.fntButton.setMode(QgsFontButton.ModeQFont)
        self.fntButton.setObjectName("fntButton")
        self.gridLayout.addWidget(self.fntButton, 0, 1, 1, 1)
        self.backgroundColor = QgsColorButton(textPropertiesDialog)
        self.backgroundColor.setColor(QtGui.QColor(255, 255, 255))
        self.backgroundColor.setDefaultColor(QtGui.QColor(255, 255, 255))
        self.backgroundColor.setObjectName("backgroundColor")
        self.gridLayout.addWidget(self.backgroundColor, 1, 3, 1, 1)
        self.fntColor = QgsColorButton(textPropertiesDialog)
        self.fntColor.setMinimumSize(QtCore.QSize(24, 21))
        self.fntColor.setColor(QtGui.QColor(0, 0, 0))
        self.fntColor.setDefaultColor(QtGui.QColor(0, 0, 0))
        self.fntColor.setObjectName("fntColor")
        self.gridLayout.addWidget(self.fntColor, 0, 3, 1, 1)
        self.cbBackground = QtWidgets.QCheckBox(textPropertiesDialog)
        self.cbBackground.setChecked(True)
        self.cbBackground.setObjectName("cbBackground")
        self.gridLayout.addWidget(self.cbBackground, 1, 0, 1, 3)
        self.label = QtWidgets.QLabel(textPropertiesDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.cbFrame = QtWidgets.QCheckBox(textPropertiesDialog)
        self.cbFrame.setObjectName("cbFrame")
        self.gridLayout.addWidget(self.cbFrame, 2, 0, 1, 3)
        self.frameColor = QgsColorButton(textPropertiesDialog)
        self.frameColor.setMinimumSize(QtCore.QSize(24, 16))
        self.frameColor.setColor(QtGui.QColor(0, 0, 0))
        self.frameColor.setDefaultColor(QtGui.QColor(0, 0, 0))
        self.frameColor.setObjectName("frameColor")
        self.gridLayout.addWidget(self.frameColor, 2, 3, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(textPropertiesDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(textPropertiesDialog)
        self.buttonBox.accepted.connect(textPropertiesDialog.accept)
        self.buttonBox.rejected.connect(textPropertiesDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(textPropertiesDialog)

    def retranslateUi(self, textPropertiesDialog):
        _translate = QtCore.QCoreApplication.translate
        textPropertiesDialog.setWindowTitle(_translate("textPropertiesDialog", "Label Properties . . "))
        self.fntButton.setText(_translate("textPropertiesDialog", "Font . . ."))
        self.cbBackground.setText(_translate("textPropertiesDialog", "Background"))
        self.label.setText(_translate("textPropertiesDialog", "TextLabel"))
        self.cbFrame.setText(_translate("textPropertiesDialog", "Border"))

from qgscolorbutton import QgsColorButton
from qgsfontbutton import QgsFontButton
