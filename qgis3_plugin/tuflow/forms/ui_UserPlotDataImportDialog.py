# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Ellis.Symons\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\tuflow\forms\ui_UserPlotDataImportDialog.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_UserPlotDataImportDialog(object):
    def setupUi(self, UserPlotDataImportDialog):
        UserPlotDataImportDialog.setObjectName("UserPlotDataImportDialog")
        UserPlotDataImportDialog.resize(684, 579)
        self.gridLayout_2 = QtWidgets.QGridLayout(UserPlotDataImportDialog)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.mGroupBox = QgsCollapsibleGroupBox(UserPlotDataImportDialog)
        self.mGroupBox.setMinimumSize(QtCore.QSize(0, 0))
        self.mGroupBox.setFlat(True)
        self.mGroupBox.setCheckable(False)
        self.mGroupBox.setCollapsed(True)
        self.mGroupBox.setSaveCollapsedState(False)
        self.mGroupBox.setObjectName("mGroupBox")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.mGroupBox)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.label_9 = QtWidgets.QLabel(self.mGroupBox)
        self.label_9.setObjectName("label_9")
        self.gridLayout_4.addWidget(self.label_9, 0, 0, 1, 1)
        self.label_10 = QtWidgets.QLabel(self.mGroupBox)
        self.label_10.setObjectName("label_10")
        self.gridLayout_4.addWidget(self.label_10, 1, 0, 1, 1)
        self.dateFormat = QtWidgets.QLineEdit(self.mGroupBox)
        self.dateFormat.setObjectName("dateFormat")
        self.gridLayout_4.addWidget(self.dateFormat, 0, 1, 1, 1)
        self.zeroHourDate = QtWidgets.QLineEdit(self.mGroupBox)
        self.zeroHourDate.setObjectName("zeroHourDate")
        self.gridLayout_4.addWidget(self.zeroHourDate, 1, 1, 1, 1)
        self.gridLayout.addWidget(self.mGroupBox, 11, 0, 1, 5)
        spacerItem = QtWidgets.QSpacerItem(20, 15, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 10, 0, 1, 5)
        self.sbLines2Discard = QtWidgets.QSpinBox(UserPlotDataImportDialog)
        self.sbLines2Discard.setProperty("value", 1)
        self.sbLines2Discard.setObjectName("sbLines2Discard")
        self.gridLayout.addWidget(self.sbLines2Discard, 5, 3, 1, 1)
        self.label_2 = QtWidgets.QLabel(UserPlotDataImportDialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 8, 0, 1, 2)
        spacerItem1 = QtWidgets.QSpacerItem(20, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 3, 0, 1, 5)
        self.label_4 = QtWidgets.QLabel(UserPlotDataImportDialog)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 8, 3, 1, 1)
        self.label_6 = QtWidgets.QLabel(UserPlotDataImportDialog)
        self.label_6.setObjectName("label_6")
        self.gridLayout.addWidget(self.label_6, 5, 0, 1, 3)
        self.cbHeadersAsLabels = QtWidgets.QCheckBox(UserPlotDataImportDialog)
        self.cbHeadersAsLabels.setChecked(True)
        self.cbHeadersAsLabels.setObjectName("cbHeadersAsLabels")
        self.gridLayout.addWidget(self.cbHeadersAsLabels, 6, 0, 1, 3)
        self.label_8 = QtWidgets.QLabel(UserPlotDataImportDialog)
        self.label_8.setObjectName("label_8")
        self.gridLayout.addWidget(self.label_8, 4, 0, 1, 5)
        self.label = QtWidgets.QLabel(UserPlotDataImportDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 5)
        self.btnBrowse = QtWidgets.QToolButton(UserPlotDataImportDialog)
        self.btnBrowse.setObjectName("btnBrowse")
        self.gridLayout.addWidget(self.btnBrowse, 1, 0, 1, 1)
        self.label_5 = QtWidgets.QLabel(UserPlotDataImportDialog)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 12, 0, 1, 5)
        self.cbXColumn = QtWidgets.QComboBox(UserPlotDataImportDialog)
        self.cbXColumn.setMinimumSize(QtCore.QSize(125, 0))
        self.cbXColumn.setEditable(True)
        self.cbXColumn.setObjectName("cbXColumn")
        self.gridLayout.addWidget(self.cbXColumn, 8, 2, 1, 1)
        self.mcbYColumn = QgsCheckableComboBox(UserPlotDataImportDialog)
        self.mcbYColumn.setMinimumSize(QtCore.QSize(125, 0))
        self.mcbYColumn.setObjectName("mcbYColumn")
        self.gridLayout.addWidget(self.mcbYColumn, 8, 4, 1, 1)
        self.inFile = QtWidgets.QLineEdit(UserPlotDataImportDialog)
        self.inFile.setObjectName("inFile")
        self.gridLayout.addWidget(self.inFile, 1, 1, 1, 4)
        self.previewTable = QtWidgets.QTableWidget(UserPlotDataImportDialog)
        self.previewTable.setObjectName("previewTable")
        self.previewTable.setColumnCount(0)
        self.previewTable.setRowCount(0)
        self.previewTable.horizontalHeader().setVisible(True)
        self.gridLayout.addWidget(self.previewTable, 13, 0, 1, 5)
        self.label_7 = QtWidgets.QLabel(UserPlotDataImportDialog)
        self.label_7.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_7.setObjectName("label_7")
        self.gridLayout.addWidget(self.label_7, 6, 3, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(20, 15, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem2, 7, 0, 1, 5)
        self.grouBox = QtWidgets.QGroupBox(UserPlotDataImportDialog)
        self.grouBox.setMinimumSize(QtCore.QSize(0, 50))
        self.grouBox.setObjectName("grouBox")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.grouBox)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.rbOther = QtWidgets.QRadioButton(self.grouBox)
        self.rbOther.setObjectName("rbOther")
        self.bgDelimiter = QtWidgets.QButtonGroup(UserPlotDataImportDialog)
        self.bgDelimiter.setObjectName("bgDelimiter")
        self.bgDelimiter.addButton(self.rbOther)
        self.gridLayout_3.addWidget(self.rbOther, 0, 3, 1, 1)
        self.rbTab = QtWidgets.QRadioButton(self.grouBox)
        self.rbTab.setObjectName("rbTab")
        self.bgDelimiter.addButton(self.rbTab)
        self.gridLayout_3.addWidget(self.rbTab, 0, 2, 1, 1)
        self.rbSpace = QtWidgets.QRadioButton(self.grouBox)
        self.rbSpace.setObjectName("rbSpace")
        self.bgDelimiter.addButton(self.rbSpace)
        self.gridLayout_3.addWidget(self.rbSpace, 0, 1, 1, 1)
        self.rbCSV = QtWidgets.QRadioButton(self.grouBox)
        self.rbCSV.setChecked(True)
        self.rbCSV.setObjectName("rbCSV")
        self.bgDelimiter.addButton(self.rbCSV)
        self.gridLayout_3.addWidget(self.rbCSV, 0, 0, 1, 1)
        self.delimiter = QtWidgets.QLineEdit(self.grouBox)
        self.delimiter.setObjectName("delimiter")
        self.gridLayout_3.addWidget(self.delimiter, 0, 4, 1, 1)
        self.gridLayout.addWidget(self.grouBox, 2, 0, 1, 5)
        self.sbLabelRow = QtWidgets.QSpinBox(UserPlotDataImportDialog)
        self.sbLabelRow.setMinimum(1)
        self.sbLabelRow.setProperty("value", 1)
        self.sbLabelRow.setObjectName("sbLabelRow")
        self.gridLayout.addWidget(self.sbLabelRow, 6, 4, 1, 1)
        self.label_3 = QtWidgets.QLabel(UserPlotDataImportDialog)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 9, 0, 1, 2)
        self.nullValue = QtWidgets.QLineEdit(UserPlotDataImportDialog)
        self.nullValue.setObjectName("nullValue")
        self.gridLayout.addWidget(self.nullValue, 9, 2, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.textBrowser = QtWidgets.QTextBrowser(UserPlotDataImportDialog)
        self.textBrowser.setObjectName("textBrowser")
        self.verticalLayout.addWidget(self.textBrowser)
        self.gridLayout_2.addLayout(self.verticalLayout, 0, 1, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(UserPlotDataImportDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout_2.addWidget(self.buttonBox, 1, 0, 1, 2)
        self.gridLayout_2.setColumnStretch(0, 10)
        self.gridLayout_2.setColumnStretch(1, 5)

        self.retranslateUi(UserPlotDataImportDialog)
        self.buttonBox.accepted.connect(UserPlotDataImportDialog.accept)
        self.buttonBox.rejected.connect(UserPlotDataImportDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(UserPlotDataImportDialog)

    def retranslateUi(self, UserPlotDataImportDialog):
        _translate = QtCore.QCoreApplication.translate
        UserPlotDataImportDialog.setWindowTitle(_translate("UserPlotDataImportDialog", "Import User Plot Data . . ."))
        self.mGroupBox.setTitle(_translate("UserPlotDataImportDialog", "Convert From Date Format (only required if importing time as dates)"))
        self.label_9.setText(_translate("UserPlotDataImportDialog", "Input Format:"))
        self.label_10.setText(_translate("UserPlotDataImportDialog", "Zero Hour Date (DD/MM/YYYY* hh:mm:ss):"))
        self.label_2.setText(_translate("UserPlotDataImportDialog", "X Column:"))
        self.label_4.setText(_translate("UserPlotDataImportDialog", "Y Column:"))
        self.label_6.setText(_translate("UserPlotDataImportDialog", "Number of Header Lines to Discard:"))
        self.cbHeadersAsLabels.setText(_translate("UserPlotDataImportDialog", "Use Header Line as Data Labels"))
        self.label_8.setText(_translate("UserPlotDataImportDialog", "Header Rows"))
        self.label.setText(_translate("UserPlotDataImportDialog", "Delimited File"))
        self.btnBrowse.setText(_translate("UserPlotDataImportDialog", "..."))
        self.label_5.setText(_translate("UserPlotDataImportDialog", "Preview"))
        self.label_7.setText(_translate("UserPlotDataImportDialog", "Use Row: "))
        self.grouBox.setTitle(_translate("UserPlotDataImportDialog", "Delimited Format"))
        self.rbOther.setText(_translate("UserPlotDataImportDialog", "Other:"))
        self.rbTab.setText(_translate("UserPlotDataImportDialog", "Tab"))
        self.rbSpace.setText(_translate("UserPlotDataImportDialog", "Space"))
        self.rbCSV.setText(_translate("UserPlotDataImportDialog", "CSV"))
        self.label_3.setText(_translate("UserPlotDataImportDialog", "Null Value (optional)"))
        self.textBrowser.setHtml(_translate("UserPlotDataImportDialog", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">ToolTip</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-weight:600;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Converts a delimited text file (e.g. *.csv) into X, Y data to be plotted in TUVIEW.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-weight:600;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Delimeter File:</span> file containing plot data</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Delimited Format: </span>Character delimiting data</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Number of Header Lines to Discard: </span>The number of rows at the top of file to ignore</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">User Header Line as Data Labels: </span>Uses row values as labels for data series- can be changed later.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">X Column: </span>Column containing X-Values</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Y Column: </span>Column containing Y-Values- can be multiple</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Null Value: </span>Value to be treated as null when plotting- blank values will always be treated as null</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Input Format: </span>Input date format- use capital \'D\' for days captial \'M\' for month capital \'Y\' for year lower \'h\' for hour lower \'m\' for minutes lower \'s\' for seconds. Use \'/\' \':\' \'-\' or space for separators e.g. DD/MM/YYYY hh:mm:ss</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Zero Hour Date: </span>Date for zero hour, if none specified will use first value. Must be input in specified format (DD/MM/YYYY* hh:mm:ss) </p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">*number of Y depends on the input format - should be consistent</p></body></html>"))

from qgscheckablecombobox import QgsCheckableComboBox
from qgscollapsiblegroupbox import QgsCollapsibleGroupBox
