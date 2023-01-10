import os, sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from qgis.core import *
from tuflow.forms.BridgeEditorImportDialog import Ui_bridgeEditorImportDialog


class BridgeImport:
    Channel = 0
    Arch = 1
    ClearSpan = 2


class BridgeEditorImportDialog(QDialog, Ui_bridgeEditorImportDialog):
    
    def __init__(self, iface, importType):
        QDialog.__init__(self)
        self.setupUi(self)
        self.iface = iface
        self.importType = importType
        folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
        self.btnBrowse.setIcon(folderIcon)
        
        # import data to these members
        # data type depends on importType (i.e. channel, arch bridge etc)
        self.col1 = []
        self.col2 = []
        self.col3 = []
        self.col4 = []
        self.imported = False
        self.message = []
        self.error = False
        
        if self.importType == BridgeImport.Channel:
            self.labelCol1.setText("Chainage Column")
            self.labelCol2.setText("Elevation Column")
            self.labelCol3.setText("Manning's n Column (optional)")
            self.labelCol4.setVisible(False)
            self.cboCol4.setVisible(False)
            self.setWindowTitle('Import Bridge Channel Data')
        elif self.importType == BridgeImport.Arch:
            self.labelCol1.setText("Start Column")
            self.labelCol2.setText("Finish Column")
            self.labelCol3.setText("Springing Level Coluumn")
            self.labelCol4.setText("Soffit Level Column")
            self.labelCol4.setVisible(True)
            self.cboCol4.setVisible(True)
            self.setWindowTitle('Import Bridge Property Data')
        else:
            pass
        
        self.btnBrowse.clicked.connect(self.browse)
        self.inFile.textChanged.connect(self.populateDataColumns)
        self.inFile.textChanged.connect(self.updatePreview)
        self.sbLines2Discard.valueChanged.connect(self.populateDataColumns)
        self.sbLines2Discard.valueChanged.connect(self.updatePreview)
        self.cboCol1.currentIndexChanged.connect(self.updatePreview)
        self.cboCol2.currentIndexChanged.connect(self.updatePreview)
        self.cboCol3.currentIndexChanged.connect(self.updatePreview)
        self.cboCol4.currentIndexChanged.connect(self.updatePreview)
        self.nullValue.textChanged.connect(self.updatePreview)
        self.rbCSV.clicked.connect(self.populateDataColumns)
        self.rbSpace.clicked.connect(self.populateDataColumns)
        self.rbTab.clicked.connect(self.populateDataColumns)
        self.rbOther.clicked.connect(self.populateDataColumns)
        self.delimiter.textChanged.connect(self.populateDataColumns)
        self.pbOk.clicked.connect(self.check)
        self.pbCancel.clicked.connect(self.reject)
    
    def browse(self):
        settings = QSettings()
        inFile = settings.value('TUFLOW/import_bridge_data')
        startDir = None
        if inFile:  # if outFolder no longer exists, work backwards in directory until find one that does
            while inFile:
                if os.path.exists(inFile):
                    startDir = inFile
                    break
                else:
                    inFile = os.path.dirname(inFile)
        inFile = QFileDialog.getOpenFileName(self, 'Import Delimited File', startDir)[0]
        if inFile:
            self.inFile.setText(inFile)
            settings.setValue('TUFLOW/import_bridge_data', inFile)
    
    def getDelim(self):
        if self.rbCSV.isChecked():
            return ','
        elif self.rbSpace.isChecked():
            return ' '
        elif self.rbTab.isChecked():
            return '\t'
        elif self.rbOther.isChecked():
            return self.delimiter.text()
    
    def checkConsecutive(self, letter):
        f = self.dateFormat.text()
        for i in range(f.count(letter)):
            if i == 0:
                indPrev = f.find(letter)
            else:
                ind = f[indPrev + 1:].find(letter)
                if ind != 0:
                    return False
                indPrev += 1
        
        return True
    
    def populateDataColumns(self):
        self.cboCol1.clear()
        self.cboCol2.clear()
        self.cboCol3.clear()
        self.cboCol4.clear()
        if self.inFile.text():
            if os.path.exists(self.inFile.text()):
                header_line = self.sbLines2Discard.value() - 1
                if header_line >= 0:
                    with open(self.inFile.text(), 'r') as fo:
                        for i, line in enumerate(fo):
                            if i == header_line:
                                delim = self.getDelim()
                                if delim != '':
                                    headers = line.split(delim)
                                    headers[-1] = headers[-1].strip('\n')
                                    for j, header in enumerate(headers):
                                        headers[j] = header.strip('"').strip("'")
                            elif i > header_line:
                                break
                else:
                    with open(self.inFile.text(), 'r') as fo:
                        for i, line in enumerate(fo):
                            if i == 0:
                                delim = self.getDelim()
                                if delim != '':
                                    n = len(line.split(delim))
                                    headers = ['Column {0}'.format(x + 1) for x in range(n)]
                            else:
                                break
                self.cboCol1.addItems(headers)
                self.cboCol2.addItems(headers)
                self.cboCol3.addItems(headers)
                self.cboCol4.addItems(headers)
                                
        self.cboCol1.addItem('-None-')
        self.cboCol2.addItem('-None-')
        self.cboCol3.addItem('-None-')
        self.cboCol4.addItem('-None-')
        self.cboCol1.setCurrentIndex(-1)
        self.cboCol2.setCurrentIndex(-1)
        self.cboCol3.setCurrentIndex(-1)
        self.cboCol4.setCurrentIndex(-1)
    
    def updatePreview(self):
        channelColumnNames = ['Chainage (m)', 'Elevation (m RL)', "Manning's n"]
        archColumnNames = ['Start (m)', 'Finish (m)', 'Springing Level (m RL)', 'Soffit Level (m RL)']
        clearSpanColumnNames = ['', '', '', '']
        if self.importType == BridgeImport.Channel:
            allColumnNames = channelColumnNames[:]
        elif self.importType == BridgeImport.Arch:
            allColumnNames = archColumnNames[:]
        else:
            allColumnNames = clearSpanColumnNames[:]
        iCol1 = 0
        iCol2 = 0
        iCol3 = 0
        iCol4 = 0
        
        self.previewTable.clear()
        self.previewTable.setRowCount(0)
        self.previewTable.setColumnCount(0)
        if self.inFile.text():
            if os.path.exists(self.inFile.text()):
                # sort out number of columns and column names
                tableColumnNames = []
                if self.cboCol1.currentIndex() > -1 and self.cboCol1.currentText() != '-None-':
                    self.previewTable.setColumnCount(1)
                    tableColumnNames = allColumnNames[0:1]
                    iCol1 = self.cboCol1.currentIndex()
                if self.cboCol2.currentIndex() > -1 and self.cboCol2.currentText() != '-None-':
                    self.previewTable.setColumnCount(2)
                    tableColumnNames = allColumnNames[0:2]
                    iCol2 = self.cboCol2.currentIndex()
                if self.cboCol3.currentIndex() > -1 and self.cboCol3.currentText() != '-None-':
                    self.previewTable.setColumnCount(3)
                    tableColumnNames = allColumnNames[0:3]
                    iCol3 = self.cboCol3.currentIndex()
                if self.cboCol4.isVisible() and self.cboCol4.currentIndex() > -1 and \
                        self.cboCol4.currentText() != '-None-':
                    self.previewTable.setColumnCount(4)
                    tableColumnNames = allColumnNames[0:4]
                    iCol4 = self.cboCol4.currentIndex()
                self.previewTable.setHorizontalHeaderLabels(tableColumnNames)
                
                if self.previewTable.columnCount():
                    # read in first 10 rows of data for preview
                    with open(self.inFile.text(), 'r') as fo:
                        header_line = self.sbLines2Discard.value() - 1
                        data_entries = 0
                        for i, line in enumerate(fo):
                            if i > header_line:
                                if data_entries > 9:
                                    break
                                delim = self.getDelim()
                                values = line.split(delim)
                                if self.nullValue.text():
                                    if self.nullValue.text().lower() in [x.lower() for x in values]:
                                        continue
                                
                                self.previewTable.setRowCount(self.previewTable.rowCount() + 1)
                                # first column
                                if len(values) > iCol1:
                                    value = values[iCol1]
                                else:
                                    value = ''
                                item = QTableWidgetItem(0)
                                item.setText(value)
                                self.previewTable.setItem(data_entries, 0, item)
                                
                                # second column
                                if self.previewTable.columnCount() > 1:
                                    if len(values) > iCol2:
                                        value = values[iCol2]
                                    else:
                                        value = ''
                                item = QTableWidgetItem(0)
                                item.setText(value)
                                self.previewTable.setItem(data_entries, 1, item)
                                
                                # third column
                                if self.previewTable.columnCount() > 2:
                                    if len(values) > iCol3:
                                        value = values[iCol3]
                                    else:
                                        value = ''
                                item = QTableWidgetItem(0)
                                item.setText(value)
                                self.previewTable.setItem(data_entries, 2, item)
                                
                                # forth column
                                if self.previewTable.columnCount() > 3:
                                    if len(values) > iCol4:
                                        value = values[iCol4]
                                    else:
                                        value = ''
                                item = QTableWidgetItem(0)
                                item.setText(value)
                                self.previewTable.setItem(data_entries, 3, item)
                                
                                data_entries += 1
    
    def check(self):
        if not self.inFile.text():
            QMessageBox.critical(self, 'Import Data', 'No Input File Specified')
            return
        if not os.path.exists(self.inFile.text()):
            QMessageBox.critical(self, 'Import Data', 'Invalid Input File')
            return
        if self.cboCol1.count() < 1:
            QMessageBox.critical(self, 'Import Data',
                                    'Invalid Delimiter or Input File is Empty')
            return
        if self.importType == BridgeImport.Channel:
            if not self.cboCol1.currentText():
                QMessageBox.critical(self, 'Import Data',
                                        'No Chainage Column Chosen')
                return
            if not self.cboCol2.currentText():
                QMessageBox.critical(self, 'Import Data',
                                        'No Elevation Column Chosen')
                return
        if self.importType == BridgeImport.Arch:
            if not self.cboCol1.currentText():
                QMessageBox.critical(self, 'Import Data',
                                        'No Start Chainage Chosen')
                return
            if not self.cboCol2.currentText():
                QMessageBox.critical(self, 'Import Data',
                                        'No Finish Chainage Chosen')
                return
            if not self.cboCol3.currentText():
                QMessageBox.critical(self, 'Import Data',
                                        'No Springing Elevation Column Chosen')
                return
            if not self.cboCol4.currentText():
                QMessageBox.critical(self, 'Import Data',
                                        'No Soffit Elevation Column Chosen')
                return
            
        # prelim checks out :)
        self.run()
    
    def run(self):
        # make sure entries are reset and blank
        self.col1 = []
        self.col2 = []
        self.col3 = []
        self.col4 = []
        self.imported = False
        self.message = []
        self.error = False
        
        # columns to import
        iCol1 = None
        iCol2 = None
        iCol3 = None
        iCol4 = None
        if self.cboCol1.currentIndex() > -1 and self.cboCol1.currentText() != '-None-':
            iCol1 = self.cboCol1.currentIndex()
        if self.cboCol2.currentIndex() > -1 and self.cboCol2.currentText() != '-None-':
            iCol2 = self.cboCol2.currentIndex()
        if self.cboCol3.currentIndex() > -1 and self.cboCol3.currentText() != '-None-':
            iCol3 = self.cboCol3.currentIndex()
        if self.cboCol4.isVisible() and self.cboCol4.currentIndex() > -1 and \
                self.cboCol4.currentText() != '-None-':
            iCol4 = self.cboCol4.currentIndex()

        with open(self.inFile.text(), 'r') as fo:
            header_line = self.sbLines2Discard.value() - 1
            for i, line in enumerate(fo):
                col1 = None
                col2 = None
                col3 = None
                col4 = None
                if i > header_line:
                    delim = self.getDelim()
                    values = line.split(delim)
                    if self.nullValue.text():
                        if self.nullValue.text().lower() in [x.lower() for x in values]:
                            continue  # skip when a null value exists anywhere in data
            
                    # first column
                    if iCol1 is not None:
                        if len(values) > iCol1:
                            value = values[iCol1]
                            try:
                                col1 = float(value)
                            except ValueError:
                                self.error = True
                                self.message.append('Non Number Value: Row {0}, Column {1}'.format(i+1, iCol1+1))
                        else:
                            self.error = True
                            self.message.append('Blank Entry: Row {0}, Column {1}'.format(i+1, iCol1+1))
                    
            
                    # second column
                    if iCol2 is not None:
                        if len(values) > iCol2:
                            value = values[iCol2]
                            try:
                                col2 = float(value)
                            except ValueError:
                                self.error = True
                                self.message.append('Non Number Value: Row {0}, Column {1}'.format(i + 1, iCol2 + 1))
                        else:
                            self.error = True
                            self.message.append('Blank Entry: Row {0}, Column {1}'.format(i + 1, iCol2 + 1))
            
                    # third column
                    if iCol3 is not None:
                        if len(values) > iCol3:
                            value = values[iCol3]
                            try:
                                col3 = float(value)
                            except ValueError:
                                self.error = True
                                self.message.append('Non Number Value: Row {0}, Column {1}'.format(i + 1, iCol3 + 1))
                        else:
                            self.error = True
                            self.message.append('Blank Entry: Row {0}, Column {1}'.format(i + 1, iCol3 + 1))
            
                    # forth column
                    if iCol4 is not None:
                        if len(values) > iCol4:
                            value = values[iCol4]
                            try:
                                col4 = float(value)
                            except ValueError:
                                self.error = True
                                self.message.append('Non Number Value: Row {0}, Column {1}'.format(i + 1, iCol4 + 1))
                        else:
                            self.error = True
                            self.message.append('Blank Entry: Row {0}, Column {1}'.format(i + 1, iCol4 + 1))
                            
                    if (iCol1 is not None and col1 is None) or (iCol2 is not None and col2 is None) or \
                            (iCol3 is not None and col3 is None) or (iCol4 is not None and col4 is None):
                        pass
                    else:
                        if col1 is not None:
                            self.col1.append(col1)
                        if col2 is not None:
                            self.col2.append(col2)
                        if col3 is not None:
                            self.col3.append(col3)
                        if col4 is not None:
                            self.col4.append(col4)
                            
        if self.col1:
            if self.col2:
                if len(self.col1) != len(self.col2):
                    QMessageBox.critical(self, "Import Data", "Error Importing Data: Data Set Lengths Do Not Match")
                    return
            if self.col3:
                if len(self.col1) != len(self.col3):
                    QMessageBox.critical(self, "Import Data", "Error Importing Data: Data Set Lengths Do Not Match")
                    return
            if self.col4:
                if len(self.col1) != len(self.col4):
                    QMessageBox.critical(self, "Import Data", "Error Importing Data: Data Set Lengths Do Not Match")
                    return
        else:
            QMessageBox.critical(self, "Import Data", "Empty Data Set. Check Input File Contains Useable Data")
            return
        
        # finally destroy dialog box
        self.imported = True
        QMessageBox.information(self, "Import Data", "Import Successful")
        self.accept()