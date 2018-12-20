# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\ui_BatchExportPlotDialog.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_BatchPlotExport(object):
    def setupUi(self, BatchPlotExport):
        BatchPlotExport.setObjectName("BatchPlotExport")
        BatchPlotExport.resize(526, 528)
        self.gridLayout_3 = QtWidgets.QGridLayout(BatchPlotExport)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.label_6 = QtWidgets.QLabel(BatchPlotExport)
        self.label_6.setObjectName("label_6")
        self.gridLayout.addWidget(self.label_6, 2, 0, 1, 2)
        self.cbNameAttribute = QtWidgets.QComboBox(BatchPlotExport)
        self.cbNameAttribute.setEditable(True)
        self.cbNameAttribute.setObjectName("cbNameAttribute")
        self.cbNameAttribute.addItem("")
        self.gridLayout.addWidget(self.cbNameAttribute, 3, 0, 1, 2)
        self.groupBox = QtWidgets.QGroupBox(BatchPlotExport)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName("verticalLayout")
        self.rbAllFeatures = QtWidgets.QRadioButton(self.groupBox)
        self.rbAllFeatures.setChecked(True)
        self.rbAllFeatures.setObjectName("rbAllFeatures")
        self.verticalLayout.addWidget(self.rbAllFeatures)
        self.rbSelectedFeatures = QtWidgets.QRadioButton(self.groupBox)
        self.rbSelectedFeatures.setObjectName("rbSelectedFeatures")
        self.verticalLayout.addWidget(self.rbSelectedFeatures)
        self.gridLayout.addWidget(self.groupBox, 10, 0, 1, 2)
        self.mcbResultTypes = QgsCheckableComboBox(BatchPlotExport)
        self.mcbResultTypes.setObjectName("mcbResultTypes")
        self.gridLayout.addWidget(self.mcbResultTypes, 7, 0, 1, 2)
        self.label_2 = QtWidgets.QLabel(BatchPlotExport)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 6, 0, 1, 2)
        self.mcbResultMesh = QgsCheckableComboBox(BatchPlotExport)
        self.mcbResultMesh.setObjectName("mcbResultMesh")
        self.gridLayout.addWidget(self.mcbResultMesh, 5, 0, 1, 2)
        self.groupBox_2 = QtWidgets.QGroupBox(BatchPlotExport)
        self.groupBox_2.setObjectName("groupBox_2")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox_2)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.rbCSV = QtWidgets.QRadioButton(self.groupBox_2)
        self.rbCSV.setChecked(True)
        self.rbCSV.setObjectName("rbCSV")
        self.gridLayout_2.addWidget(self.rbCSV, 0, 0, 1, 2)
        self.rbImage = QtWidgets.QRadioButton(self.groupBox_2)
        self.rbImage.setObjectName("rbImage")
        self.gridLayout_2.addWidget(self.rbImage, 1, 0, 1, 1)
        self.cbImageFormat = QtWidgets.QComboBox(self.groupBox_2)
        self.cbImageFormat.setObjectName("cbImageFormat")
        self.gridLayout_2.addWidget(self.cbImageFormat, 1, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(150, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem, 1, 2, 1, 1)
        self.gridLayout_2.setColumnStretch(0, 1)
        self.gridLayout_2.setColumnStretch(1, 10)
        self.gridLayout.addWidget(self.groupBox_2, 11, 0, 1, 2)
        self.label_3 = QtWidgets.QLabel(BatchPlotExport)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 12, 0, 1, 2)
        self.label_4 = QtWidgets.QLabel(BatchPlotExport)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 8, 0, 1, 2)
        self.label_5 = QtWidgets.QLabel(BatchPlotExport)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 4, 0, 1, 2)
        self.label = QtWidgets.QLabel(BatchPlotExport)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 2)
        self.buttonBox = QtWidgets.QDialogButtonBox(BatchPlotExport)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 16, 0, 1, 3)
        self.cbTimesteps = QtWidgets.QComboBox(BatchPlotExport)
        self.cbTimesteps.setEditable(True)
        self.cbTimesteps.setObjectName("cbTimesteps")
        self.gridLayout.addWidget(self.cbTimesteps, 9, 0, 1, 2)
        self.cbGISLayer = QtWidgets.QComboBox(BatchPlotExport)
        self.cbGISLayer.setEditable(True)
        self.cbGISLayer.setObjectName("cbGISLayer")
        self.gridLayout.addWidget(self.cbGISLayer, 1, 0, 1, 2)
        self.textBrowser = QtWidgets.QTextBrowser(BatchPlotExport)
        self.textBrowser.setMinimumSize(QtCore.QSize(200, 0))
        self.textBrowser.setMaximumSize(QtCore.QSize(200, 16777215))
        self.textBrowser.setObjectName("textBrowser")
        self.gridLayout.addWidget(self.textBrowser, 0, 2, 16, 1)
        self.btnBrowse = QtWidgets.QToolButton(BatchPlotExport)
        self.btnBrowse.setObjectName("btnBrowse")
        self.gridLayout.addWidget(self.btnBrowse, 13, 0, 2, 1)
        self.outputFolder = QtWidgets.QLineEdit(BatchPlotExport)
        self.outputFolder.setObjectName("outputFolder")
        self.gridLayout.addWidget(self.outputFolder, 13, 1, 2, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.MinimumExpanding)
        self.gridLayout.addItem(spacerItem1, 15, 0, 1, 2)
        self.gridLayout.setRowStretch(0, 1)
        self.gridLayout.setRowStretch(1, 10)
        self.gridLayout.setRowStretch(2, 1)
        self.gridLayout.setRowStretch(3, 10)
        self.gridLayout.setRowStretch(4, 1)
        self.gridLayout.setRowStretch(5, 10)
        self.gridLayout.setRowStretch(6, 1)
        self.gridLayout.setRowStretch(7, 10)
        self.gridLayout.setRowStretch(8, 1)
        self.gridLayout.setRowStretch(9, 10)
        self.gridLayout.setRowStretch(10, 10)
        self.gridLayout.setRowStretch(11, 10)
        self.gridLayout.setRowStretch(12, 1)
        self.gridLayout.setRowStretch(13, 1)
        self.gridLayout.setRowStretch(14, 1)
        self.gridLayout.setRowStretch(15, 1)
        self.gridLayout.setRowStretch(16, 10)
        self.gridLayout_3.addLayout(self.gridLayout, 0, 0, 1, 1)

        self.retranslateUi(BatchPlotExport)
        QtCore.QMetaObject.connectSlotsByName(BatchPlotExport)

    def retranslateUi(self, BatchPlotExport):
        _translate = QtCore.QCoreApplication.translate
        BatchPlotExport.setWindowTitle(_translate("BatchPlotExport", "Batch Plot and Export Features"))
        self.label_6.setText(_translate("BatchPlotExport", "Name Attribute Field (optional)"))
        self.cbNameAttribute.setItemText(0, _translate("BatchPlotExport", "-None-"))
        self.groupBox.setTitle(_translate("BatchPlotExport", "Export . . ."))
        self.rbAllFeatures.setText(_translate("BatchPlotExport", "All Features"))
        self.rbSelectedFeatures.setText(_translate("BatchPlotExport", "Selected Features Only"))
        self.label_2.setText(_translate("BatchPlotExport", "Result Types"))
        self.groupBox_2.setTitle(_translate("BatchPlotExport", "Format . . ."))
        self.rbCSV.setText(_translate("BatchPlotExport", "CSV"))
        self.rbImage.setText(_translate("BatchPlotExport", "Image"))
        self.label_3.setText(_translate("BatchPlotExport", "Output Folder"))
        self.label_4.setText(_translate("BatchPlotExport", "Time Step (for cross sections)"))
        self.label_5.setText(_translate("BatchPlotExport", "Result Mesh"))
        self.label.setText(_translate("BatchPlotExport", "GIS Layer"))
        self.textBrowser.setHtml(_translate("BatchPlotExport", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Tool Tip</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-weight:600;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Iterates through the features in an input shp layer and extracts plotted results to individual CSV or Image files. Depending on geometry type, will extract either time series results for points or cross section results for line type.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">GIS Layer: </span>Vector layer containing features used for extracting results</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Name Attribute:</span> Name attribute field used as file name for export. If -None- will use FID</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Result Mesh: </span>Mesh layers to extract data from</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Result Types: </span>Result types for plotting e.g. bed elevation, water level</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Time Step: </span>Output time step for cross section plotting</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Export: </span>Choose either all features or selected features to iterate through</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Format: </span>Choose either CSV or Image (iimage format also selectable)</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Output Folder:</span> Folder location for outputs</p></body></html>"))
        self.btnBrowse.setToolTip(_translate("BatchPlotExport", "Browse"))
        self.btnBrowse.setText(_translate("BatchPlotExport", "..."))

from qgscheckablecombobox import QgsCheckableComboBox
