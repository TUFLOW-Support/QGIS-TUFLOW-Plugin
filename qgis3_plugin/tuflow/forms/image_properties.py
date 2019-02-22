# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\image_properties.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ImageProperties(object):
    def setupUi(self, ImageProperties):
        ImageProperties.setObjectName("ImageProperties")
        ImageProperties.resize(450, 149)
        self.verticalLayout = QtWidgets.QVBoxLayout(ImageProperties)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.label_2 = QtWidgets.QLabel(ImageProperties)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 2, 3, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 2, 0, 1, 1)
        self.sbSizeY = QtWidgets.QDoubleSpinBox(ImageProperties)
        self.sbSizeY.setDecimals(1)
        self.sbSizeY.setMinimum(1.0)
        self.sbSizeY.setMaximum(99999.0)
        self.sbSizeY.setProperty("value", 100.0)
        self.sbSizeY.setObjectName("sbSizeY")
        self.gridLayout.addWidget(self.sbSizeY, 2, 4, 1, 1)
        self.rbResizeImage = QtWidgets.QRadioButton(ImageProperties)
        self.rbResizeImage.setObjectName("rbResizeImage")
        self.gridLayout.addWidget(self.rbResizeImage, 1, 0, 1, 3)
        self.rbUseOriginalSize = QtWidgets.QRadioButton(ImageProperties)
        self.rbUseOriginalSize.setChecked(True)
        self.rbUseOriginalSize.setObjectName("rbUseOriginalSize")
        self.gridLayout.addWidget(self.rbUseOriginalSize, 0, 0, 1, 3)
        self.label = QtWidgets.QLabel(ImageProperties)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 2, 1, 1, 1)
        self.cbKeepAspectRatio = QtWidgets.QCheckBox(ImageProperties)
        self.cbKeepAspectRatio.setChecked(True)
        self.cbKeepAspectRatio.setObjectName("cbKeepAspectRatio")
        self.gridLayout.addWidget(self.cbKeepAspectRatio, 2, 5, 1, 1)
        self.sbSizeX = QtWidgets.QDoubleSpinBox(ImageProperties)
        self.sbSizeX.setDecimals(1)
        self.sbSizeX.setMinimum(1.0)
        self.sbSizeX.setMaximum(99999.0)
        self.sbSizeX.setProperty("value", 100.0)
        self.sbSizeX.setObjectName("sbSizeX")
        self.gridLayout.addWidget(self.sbSizeX, 2, 2, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 2, 6, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem2)
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.buttonBox = QtWidgets.QDialogButtonBox(ImageProperties)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout_2.addWidget(self.buttonBox, 0, 0, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout_2)

        self.retranslateUi(ImageProperties)
        self.buttonBox.accepted.connect(ImageProperties.accept)
        self.buttonBox.rejected.connect(ImageProperties.reject)
        QtCore.QMetaObject.connectSlotsByName(ImageProperties)

    def retranslateUi(self, ImageProperties):
        _translate = QtCore.QCoreApplication.translate
        ImageProperties.setWindowTitle(_translate("ImageProperties", "Image Properties"))
        self.label_2.setText(_translate("ImageProperties", "Y (mm)"))
        self.rbResizeImage.setText(_translate("ImageProperties", "Resize Image:"))
        self.rbUseOriginalSize.setText(_translate("ImageProperties", "Use Original Image Size"))
        self.label.setText(_translate("ImageProperties", "X (mm)"))
        self.cbKeepAspectRatio.setText(_translate("ImageProperties", "Maintain Original Aspect Ratio"))

