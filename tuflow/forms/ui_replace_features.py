# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_replace_features.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_dlg_features_from_layer(object):
    def setupUi(self, dlg_features_from_layer):
        dlg_features_from_layer.setObjectName("dlg_features_from_layer")
        dlg_features_from_layer.resize(399, 75)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(dlg_features_from_layer.sizePolicy().hasHeightForWidth())
        dlg_features_from_layer.setSizePolicy(sizePolicy)
        dlg_features_from_layer.setSizeGripEnabled(True)
        self.formLayout = QtWidgets.QFormLayout(dlg_features_from_layer)
        self.formLayout.setObjectName("formLayout")
        self.label = QtWidgets.QLabel(dlg_features_from_layer)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.comboBox = QtWidgets.QComboBox(dlg_features_from_layer)
        self.comboBox.setMinimumContentsLength(30)
        self.comboBox.setObjectName("comboBox")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.comboBox)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.formLayout.setItem(2, QtWidgets.QFormLayout.LabelRole, spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(dlg_features_from_layer)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.buttonBox)

        self.retranslateUi(dlg_features_from_layer)
        self.buttonBox.accepted.connect(dlg_features_from_layer.accept)
        self.buttonBox.rejected.connect(dlg_features_from_layer.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_features_from_layer)

    def retranslateUi(self, dlg_features_from_layer):
        _translate = QtCore.QCoreApplication.translate
        dlg_features_from_layer.setWindowTitle(_translate("dlg_features_from_layer", "Replace Features From Layer"))
        self.label.setText(_translate("dlg_features_from_layer", "Source Layer"))