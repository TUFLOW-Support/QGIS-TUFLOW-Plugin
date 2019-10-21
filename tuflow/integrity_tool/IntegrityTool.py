import os, sys
import traceback
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.gui import *
from PyQt5.QtWidgets import *
from tuflow.forms.integrity_tool_dock import Ui_IntegrityTool
from tuflow.tuflowqgis_library import (findAllRasterLyrs, findAllVectorLyrs, tuflowqgis_find_layer,
                                       is1dNetwork, is1dTable)
from tuflow.tuflowqgis_dialog import StackTraceDialog
from .DataCollector import DataCollector
from .SnappingTool import SnappingTool
from .ContinuityTool import ContinuityTool
from .FlowTraceTool import DataCollectorFlowTrace, FlowTraceTool, FlowTracePlot
from .PipeDirectionTool import PipeDirectionTool
from .Enumerators import *



class IntegrityToolDock(QDockWidget, Ui_IntegrityTool):
    # add some custom signals
    inputLineAdded = pyqtSignal(QgsMapLayer)
    inputLineRemoved = pyqtSignal()

    def __init__(self, iface):
        # initialise inherited classes
        QDockWidget.__init__(self)
        self.setupUi(self)
        Ui_IntegrityTool.__init__(self)

        # custom initialisations
        # start with QgsInterface
        self.iface = iface
        self.outputLyr = None

        # add caculation objects
        # data collectors
        self.dataCollectorLines = DataCollector(self.iface)
        self.dataCollectorPoints = DataCollector(self.iface)
        self.dataCollectorTables = DataCollector(self.iface)

        # progress bar
        self.currentStep = 0
        self.maxProgressSteps = 0

        # set up radio buttons determing which tool to run
        self.toolButtonGroup = QButtonGroup()
        self.toolButtonGroup.addButton(self.rbSnapping)
        self.toolButtonGroup.setId(self.rbSnapping, 0)
        self.toolButtonGroup.addButton(self.rbPipeDirection)
        self.toolButtonGroup.setId(self.rbPipeDirection, 1)
        self.toolButtonGroup.addButton(self.rbContinuity)
        self.toolButtonGroup.setId(self.rbContinuity, 2)
        self.toolButtonGroup.addButton(self.rbFlowTrace)
        self.toolButtonGroup.setId(self.rbFlowTrace, 3)
        self.rbSnapping.setChecked(True)

        # apply icons
        self.applyIcons()

        # populate comboboxes
        self.populateGrids()
        self.populateInputs()

        # connect browse buttons
        self.connectBrowseButtons()

        # what happens when a layer is added or removed from the workspace
        QgsProject.instance().layersAdded.connect(self.layersAdded)
        QgsProject.instance().layersRemoved.connect(self.layersRemoved)

        # connect input add and remove buttons
        self.btnAddLines.clicked.connect(lambda: self.addItem(self.cboInputLines,
                                                              self.lwLines,
                                                              QgsWkbTypes.LineGeometry))
        self.btnAddPoints.clicked.connect(lambda: self.addItem(self.cboInputPoints,
                                                               self.lwPoints,
                                                               QgsWkbTypes.PointGeometry))
        self.btnAddTables.clicked.connect(lambda: self.addItem(self.cboInputTables,
                                                               self.lwTables,
                                                               QgsWkbTypes.LineGeometry))
        self.btnRemoveLines.clicked.connect(lambda: self.removeItem(self.lwLines))
        self.btnRemovePoints.clicked.connect(lambda: self.removeItem(self.lwPoints))
        self.btnRemoveTables.clicked.connect(lambda: self.removeItem(self.lwTables))

        # what happend when the Run button is pressed
        self.pbRun.clicked.connect(self.check)

    def check(self):
        """
        Perform some checks prior to trying to run

        :return: None
        """

        # check there is at least a 1d_nwk line layer to use
        if not self.getInputs('lines'):
            QMessageBox.critical(self, "Integrity Tool", "No Network Line(s) input.")
            return
        # check all input layers exist in the workspace
        inputTypes = ['lines', 'points', 'tables']
        for inputType in inputTypes:
            for input in self.getInputs(inputType, bReturnName=True):
                if tuflowqgis_find_layer(input) is None:
                    QMessageBox.critical(self, "Integrity Tool",
                                         "Layer Does Not Exist In Workspace: {0}".format(input))
                    return
        # check dem layer exists in the workspace
        if self.gbDem.isChecked():
            if tuflowqgis_find_layer(self.cboDem.currentText()) is None:
                QMessageBox.critical(self, "Integrity Tool",
                                     "DEM Layer Does Not Exist In Workspace: {0}".format(self.cboDem.currentText()))
                return
        # check all layers are correct type
        for inputType in inputTypes:
            for layer in self.getInputs(inputType):
                if inputType == 'lines' or inputType == 'points':
                    if not is1dNetwork(layer):
                        QMessageBox.critical(self, "Integrity Tool",
                                             "Layer Is Not a 1d_nwk Type: {0}".format(input))
                        return
                else:  # tables
                    if not is1dTable(layer):
                        QMessageBox.critical(self, "Integrity Tool",
                                             "Layer Is Not a 1d_ta Type: {0}".format(input))
                        return

        self.run()

    def run(self):
        """
        Run the tool

        :return: void
        """

        self.setGuiActive(False)

        try:
            # run specified tool
            if self.toolButtonGroup.checkedId() == TOOL_TYPE.Snapping:
                self.runSnappingTool()
            elif self.toolButtonGroup.checkedId() == TOOL_TYPE.PipeDirection:
                self.runPipeDirectionTool()
            elif self.toolButtonGroup.checkedId() == TOOL_TYPE.Continuity:
                self.runContinuityTool()
            elif self.toolButtonGroup.checkedId() == TOOL_TYPE.FlowTrace:
                self.runFlowTraceTool()

            QgsProject.instance().addMapLayer(self.outputLyr)

        except Exception:
            # unexpected error
            exc_type, exc_value, exc_traceback = sys.exc_info()
            trace = ''.join(traceback.extract_tb(exc_traceback).format()) + '{0}{1}'.format(exc_type, exc_value)
            message = "Unexpected Error Occurred.\nPlease Email Stack Trace To support@tuflow.com" \
                      .format(exc_value)
            self.runStatus.setText("Unexpected Error")
            self.progressBar.setValue(100)
            QMessageBox.critical(self, "Integrity Tool", message)
            stackTraceDialog = StackTraceDialog(trace)
            stackTraceDialog.exec_()

        self.setGuiActive(True)

    def runSnappingTool(self):
        """
        
        :return:
        """

        # Get inputs
        # input dem
        if self.gbDem.isChecked():
            dem = tuflowqgis_find_layer(self.cboDem.currentText())
        else:
            dem = None
        # input vector layers
        inputLines = self.getInputs('lines')
        inputPoints = self.getInputs('points')
        inputTables = self.getInputs('tables')

        # run data collectors
        self.runDataCollectors(inputLines, inputPoints, inputTables, dem, tool='Snapping Tool')
        self.outputLyr = None
        
        # get exlusion radius
        exclRadius = self.sbExclRadius.value() if self.cbExclRadius.isChecked() else 99999

        # check snapping
        self.snappingToolLines = SnappingTool(iface=self.iface, dataCollector=self.dataCollectorLines,
                                              outputLyr=self.outputLyr, exclRadius=exclRadius,
                                              dataCollectorPoints=self.dataCollectorPoints)
        self.outputLyr = self.snappingToolLines.outputLyr
        if inputPoints:
            self.snappingToolPoints = SnappingTool(iface=self.iface, dataCollector=self.dataCollectorPoints,
                                                   outputLyr=self.outputLyr, exclRadius=exclRadius,
                                                   dataCollectorLines=self.dataCollectorLines)

        # auto snap
        if self.cbAutoSnap.isChecked():
            radius = self.sbAutoSnapSearchRadius.value()
            self.snappingToolLines.autoSnap(radius)
            for lyr in self.snappingToolLines.tmpLyrs:
                QgsProject.instance().addMapLayer(lyr)
            if inputPoints:
                self.snappingToolPoints.autoSnap(radius)
                for lyr in self.snappingToolPoints.tmpLyrs:
                    QgsProject.instance().addMapLayer(lyr)
            
            noAutoSnap = True
            if self.snappingToolLines.tmpLyrs:
                noAutoSnap = False
            if inputPoints:
                if self.snappingToolPoints.tmpLyrs:
                    noAutoSnap = False
            if noAutoSnap:
                QMessageBox.information(self.iface.mainWindow(), "Integrity Tool",
                                        "No auto snapping operations performed.")
                
    
    def runContinuityTool(self):
        """
        
        :return:
        """

        # Get inputs
        # input dem
        if self.gbDem.isChecked():
            dem = tuflowqgis_find_layer(self.cboDem.currentText())
        else:
            dem = None
        # input vector layers
        inputLines = self.getInputs('lines')
        inputPoints = self.getInputs('points')
        inputTables = self.getInputs('tables')

        # run data collectors
        self.runDataCollectors(inputLines, inputPoints, inputTables, dem, tool='Continuity Tool')
        self.outputLyr = None
        
        # user limits
        limitAngle = self.sbContinuityAngle.value()
        limitCover = self.sbContinuityCover.value()
        limitArea = self.sbContinuityArea.value()
        
        # user checks
        checkArea = self.cbContinuityArea.isChecked()
        checkInvert = self.cbContinuityInverts.isChecked()
        checkAngle = self.cbContinuityAngle.isChecked()
        checkCover = self.cbContinuityCover.isChecked()
        
        # continuity tool
        self.continuityTool = ContinuityTool(self.iface, self.dataCollectorLines, self.outputLyr, limitAngle,
                                             limitCover, limitArea, checkArea, checkAngle, checkInvert, checkCover)
        self.outputLyr = self.continuityTool.outputLyr
        
    def runFlowTraceTool(self):
        """
        
        :return:
        """

        # Get inputs
        # input dem
        if self.gbDem.isChecked():
            dem = tuflowqgis_find_layer(self.cboDem.currentText())
        else:
            dem = None
        # input vector layers
        inputLines = self.getInputs('lines')
        inputPoints = self.getInputs('points')
        inputTables = self.getInputs('tables')

        # starting features
        startLocs = []
        for lyr in inputLines:
            selFeats = lyr.selectedFeatures()
            for f in selFeats:
                fid = f.id()
                loc = (lyr.name(), fid)
                startLocs.append(loc)
        
        if not startLocs:
            QMessageBox.critical(self, "Flow Trace", "Need to select at least one feature to start the flow trace from")
            return

        # run data collectors
        self.runFlowTraceCollectors(inputLines, inputPoints, inputTables, dem, startLocs, tool='Flow Trace Tool')
        self.outputLyr = None

        # user limits
        limitAngle = self.sbFlowTraceAngle.value()
        limitCover = self.sbFlowTraceCover.value()
        limitArea = self.sbFlowTraceArea.value()

        # user checks
        checkArea = self.cbFlowTraceArea.isChecked()
        checkInvert = self.cbFlowTraceInverts.isChecked()
        checkAngle = self.cbFlowTraceAngle.isChecked()
        checkCover = self.cbFlowTraceCover.isChecked()

        # flow trace tool
        self.flowTraceTool = FlowTraceTool(self.iface, self.dataCollectorLines, self.outputLyr, limitAngle, limitCover,
                                           limitArea, checkArea, checkAngle, checkInvert, checkCover,
                                           self.dataCollectorPoints)
        self.outputLyr = self.flowTraceTool.outputLyr
        
        if self.cbFlowTraceLongPlots.isChecked():
            self.dotCount = 0
            self.message = "Generating Long Profiles"
            self.runStatus.setText(self.message)
            self.progressBar.setValue(0)
            self.progressBar.setRange(0, 0)
            self.plot = FlowTracePlot(self.iface, self.flowTraceTool)
            self.plot.finished.connect(self.showPlot)
            self.plot.updated.connect(self.updateStatusBar)
            self.plot.updateMessage.connect(self.updateMessage)
            #self.plot.show()
            
    def showPlot(self):
        self.runStatus.setText("Finished Collecting Plot Data")
        self.progressBar.setValue(100)
        self.progressBar.setRange(0, 100)
        self.plot.show()
        
    def updateStatusBar(self):
        self.dotCount += 1
        if self.dotCount > 4:
            self.dotCount = 0
        txt = self.message + ' .' * self.dotCount
        self.runStatus.setText(txt)
        
    def updateMessage(self):
        self.message = "Generating Long Profiles (I am working I promise)"
        
    def runPipeDirectionTool(self):
        """
        
        :return:
        """

        inputLines = self.getInputs('lines')
        pipeDirectionTool = PipeDirectionTool(self.iface)
        
        if self.cbBasedOnInverts.isChecked():
            pipeDirectionTool.byGradient(inputLines)
        if self.cbBasedOnContinuity.isChecked():
            self.runDataCollectors(inputLines=inputLines, tool="Pipe Direction Tool")
            pipeDirectionTool.byContinuity(inputLines, self.dataCollectorLines)
        
        self.outputLyr = pipeDirectionTool.outputLyr
        for lyr in pipeDirectionTool.tmpLyrs:
            QgsProject.instance().addMapLayer(lyr)

    def runDataCollectors(self, inputLines=(), inputPoints=(), inputTables=(), dem=None, tool=''):
        """
        Run the data collectors

        :param inputLines: list -> QgsMapLayer
        :param inputPoints: list -> QgsMapLayer
        :param inputTables: list -> QgsMapLayer
        :param dem: QgsRasterLayer
        :param tool: str tool name to be passed to progressbar
        :return: void
        """

        # get exlusion radius
        exclRadius = self.sbExclRadius.value() * 1.15 if self.cbExclRadius.isChecked() else 15

        del self.dataCollectorLines
        del self.dataCollectorPoints
        self.dataCollectorLines = DataCollector(self.iface)
        self.dataCollectorPoints = DataCollector(self.iface)

        # lines
        if inputLines:
            self.setupDataCollectorProgressBar(inputLines, 'lines')
            self.dataCollectorLines.updated.connect(self.updateProgressDataCollection)
            self.dataCollectorLines.finished.connect(
                lambda e: self.finishedDataCollection(e, text='Finished {0}'.format(tool)))
            self.dataCollectorLines.collectData(inputLines, dem, exclRadius=exclRadius)

        # points
        if inputPoints:
            self.setupDataCollectorProgressBar(inputPoints, 'points')
            self.dataCollectorPoints.updated.connect(self.updateProgressDataCollection)
            self.dataCollectorPoints.finished.connect(
                lambda e: self.finishedDataCollection(e, text='Finished {0}'.format(tool)))
            self.dataCollectorPoints.collectData(inputPoints, dem, inputLines, self.dataCollectorLines, exclRadius)
        else:
            self.dataCollectorPoints = None

        # tables
        if inputTables:
            pass
        
    def runFlowTraceCollectors(self, inputLines, inputPoints, inputTables, dem, startLocs, tool=''):
        """
        
        :param inputLines:
        :param inputPoints:
        :param inputTables:
        :param dem:
        :return:
        """

        # get exlusion radius
        exclRadius = self.sbExclRadius.value() * 1.15 if self.cbExclRadius.isChecked() else 15

        del self.dataCollectorLines
        del self.dataCollectorPoints
        self.dataCollectorLines = DataCollectorFlowTrace(self.iface)
        self.dataCollectorPoints = DataCollectorFlowTrace(self.iface)

        # lines
        if inputLines:
            self.setupDataCollectorProgressBar(inputLines, 'lines')
            self.dataCollectorLines.updated.connect(self.updateProgressDataCollection)
            self.dataCollectorLines.finished.connect(
                lambda e: self.finishedDataCollection(e, text='Finished {0}'.format(tool)))
            self.dataCollectorLines.collectData(inputLines, dem, exclRadius=exclRadius, flowTrace=True,
                                                startLocs=startLocs, tables=inputTables)
            

        # points
        if inputPoints:
            self.setupDataCollectorProgressBar(inputPoints, 'points')
            self.dataCollectorPoints.updated.connect(self.updateProgressDataCollection)
            self.dataCollectorPoints.finished.connect(
                lambda e: self.finishedDataCollection(e, text='Finished {0}'.format(tool)))
            self.dataCollectorPoints.collectData(inputPoints, dem, inputLines, self.dataCollectorLines,
                                                 exclRadius=exclRadius, flowTrace=True)

        # tables
        if inputTables:
            pass

    def getInputs(self, inputType, bReturnName=False):
        """
        Get a list of the input types

        :param inputType: str
        :param returnNameL
        :return: list -> QgsMapLayer
        """

        inputs = []

        if inputType == 'lines':
            for i in range(self.lwLines.count()):
                item = self.lwLines.item(i)
                itemText = item.text()
                if bReturnName:  # append just the text name
                    inputs.append(itemText)
                else:  # append the QgsVectorLayer
                    layer = tuflowqgis_find_layer(itemText)
                    inputs.append(layer)
        elif inputType == 'points':
            for i in range(self.lwPoints.count()):
                item = self.lwPoints.item(i)
                itemText = item.text()
                if bReturnName:  # append just the text name
                    inputs.append(itemText)
                else:  # append the QgsVectorLayer
                    layer = tuflowqgis_find_layer(itemText)
                    inputs.append(layer)
        elif inputType == 'tables':
            for i in range(self.lwTables.count()):
                item = self.lwTables.item(i)
                itemText = item.text()
                if bReturnName:  # append just the text name
                    inputs.append(itemText)
                else:  # append the QgsVectorLayer
                    layer = tuflowqgis_find_layer(itemText)
                    inputs.append(layer)

        return inputs

    def setupDataCollectorProgressBar(self, layers, inputType):
        """
        Sets up the progress bar for the data collector

        :param layers: list -> QgsMapLayer
        :param inputType: str
        :return: void
        """

        # work out maximum steps
        steps = 0
        for layer in layers:
            if layer is not None:
                steps += layer.featureCount()
        self.maxProgressSteps = steps
        self.currentStep = 0
        self.progressBar.setValue(0)

        if inputType == 'lines':
            self.runStatus.setText("Collecting data and connectivity from input lines. . .")
        elif inputType == 'points':
            self.runStatus.setText("Collecting data and connectivity from input points. . .")
        elif inputType == 'tables':
            self.runStatus.setText("Collecting data from input Tables. . .")

    def updateProgressDataCollection(self):
        """
        Updates the progress based on completed steps and maximum steps

        :return: void
        """

        self.currentStep += 1
        pComplete = (self.currentStep / self.maxProgressSteps) * 100
        self.progressBar.setValue(pComplete)
        QgsApplication.processEvents()

    def finishedDataCollection(self, e, text='Finished'):
        """
        Updates data collection progress bar to finished

        :param e: QObject
        :param text: str to be displayed
        :return: void
        """

        self.progressBar.setValue(100)
        self.runStatus.setText(text)
        if e == self.dataCollectorLines:
            self.dataCollectorLines.updated.disconnect()
            self.dataCollectorLines.finished.disconnect()
        elif e == self.dataCollectorPoints:
            self.dataCollectorPoints.updated.disconnect()
            self.dataCollectorPoints.finished.disconnect()
        elif e == self.dataCollectorTables:
            pass

    def applyIcons(self):
        """
        Apply icons to all tool buttons

        :return: void
        """

        # icons to use
        folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
        addIcon = QgsApplication.getThemeIcon('mActionAdd.svg')
        removeIcon = QgsApplication.getThemeIcon('symbologyRemove.svg')

        # buttons to apply icons to
        browseButtons = [self.browseInputLines, self.browseInputPoints, self.browseInputTables]
        addButtons = [self.btnAddLines, self.btnAddPoints, self.btnAddTables]
        removeButtons = [self.btnRemoveLines, self.btnRemovePoints, self.btnRemoveTables]

        # loop through buttons and apply icon
        for button in browseButtons:
            button.setIcon(folderIcon)
        for button in addButtons:
            button.setIcon(addIcon)
        for button in removeButtons:
            button.setIcon(removeIcon)

    def populateGrids(self):
        """
        Populate available grids to use for cover calculations in both continuity tool
        and flow trace tool

        :return: void
        """

        # comboboxes to add grids to
        cbos = [self.cboDem]

        # clear comboboxes
        for cbo in cbos:
            cbo.clear()

        # rasters / grids to add
        rasters = findAllRasterLyrs()

        # add rasters to combo box
        for cbo in cbos:
            cbo.addItems(rasters)

    def populateInputs(self):
        """
        Populate available vector shp layers for the input comboboxes

        :return: void
        """

        # comboboxes
        lineCbos = [self.cboInputLines, self.cboInputTables]
        pointCbos = [self.cboInputPoints]

        # clear comboboxes
        for cbo in lineCbos:
            cbo.clear()
        for cbo in pointCbos:
            cbo.clear()

        # vector layers
        vectors = findAllVectorLyrs()

        # add vector layers to comboboxe if appropriate geometry type
        for vector in vectors:
            layer = tuflowqgis_find_layer(vector)
            if layer is not None:
                if layer.geometryType() == QgsWkbTypes.LineGeometry:
                    for cbo in lineCbos:
                        cbo.addItem(vector)
                elif layer.geometryType() == QgsWkbTypes.PointGeometry:
                    for cbo in pointCbos:
                        cbo.addItem(vector)

    def browse(self, browseType, key, dialogName, fileType, lineEdit):
        """
        Browse folder directory

        :param type: str browse type 'folder' or 'file'
        :param key: str settings key
        :param dialogName: str dialog box label
        :param fileType: str file extension e.g. "AVI files (*.avi)"
        :param lineEdit: QLineEdit to be updated by browsing
        :return: void
        """

        settings = QSettings()
        lastFolder = settings.value(key)
        if type(lineEdit) is QLineEdit:
            startDir = lineEdit.text()
        elif type(lineEdit) is QComboBox:
            startDir = lineEdit.currentText()
        else:
            startDir = None
        if lastFolder:  # if outFolder no longer exists, work backwards in directory until find one that does
            while lastFolder:
                if os.path.exists(lastFolder):
                    startDir = lastFolder
                    break
                else:
                    lastFolder = os.path.dirname(lastFolder)
        if browseType == 'existing folder':
            f = QFileDialog.getExistingDirectory(self, dialogName, startDir)
        elif browseType == 'existing file':
            f = QFileDialog.getOpenFileName(self, dialogName, startDir, fileType)[0]
        elif browseType == 'existing files':
            f = QFileDialog.getOpenFileNames(self, dialogName, startDir, fileType)[0]
        else:
            return
        if f:
            if type(f) is list:
                fs = ''
                for i, a in enumerate(f):
                    if i == 0:
                        value = a
                        fs += a
                    else:
                        fs += ';;' + a
                f = fs
            else:
                value = f
            if type(lineEdit) is QLineEdit:
                lineEdit.setText(f)
            elif type(lineEdit) is QComboBox:
                lineEdit.setCurrentText(f)
            settings.setValue(key, value)

    def connectBrowseButtons(self):
        """
        Connects the browse buttons.

        :return: void
        """

        self.browseInputLines.clicked.connect(lambda: self.browse('existing files',
                                                                  'TUFLOW_IntegrityTool/LineInput',
                                                                  '1D Network Line Layer (1d_nwk_L)',
                                                                  "SHP format(*.shp *.SHP);;",
                                                                  self.cboInputLines))

        self.browseInputPoints.clicked.connect(lambda: self.browse('existing files',
                                                                   'TUFLOW_IntegrityTool/PointInput',
                                                                   '1D Network Point Layer (1d_nwk_P)',
                                                                   "SHP format(*.shp *.SHP);;",
                                                                   self.cboInputPoints))

        self.browseInputTables.clicked.connect(lambda: self.browse('existing files',
                                                                   'TUFLOW_IntegrityTool/TableInput',
                                                                   '1D Network Table Layer (1d_xs, 1d_cs)',
                                                                   "SHP format(*.shp *.SHP);;",
                                                                   self.cboInputTables))

    def layersAdded(self, e):
        """
        Updates the appropriate comboboxes when layers are added
        to the workspace

        :param e: list -> QgsMapLayer
        :return: void
        """

        for layer in e:
            if layer.type() == QgsMapLayer.VectorLayer:
                self.populateInputs()
            elif layer.type() == QgsMapLayer.RasterLayer:
                self.populateGrids()

    def layersRemoved(self):
        """
        Updates all the comboboxes when layers are removed from the workspace. It updates
        all comboboxes because it is not known what types have been removed (they aren't there anymore!).

        :return: void
        """

        self.populateInputs()
        self.populateGrids()

    def addItem(self, cbo, lw, geometryType):
        """
        Adds specified input item to the list widget.

        :param cbo: QComboBox
        :param lw: QListWidget
        :param geometryType: QgsWkbTypes
        :return: void
        """

        # get existing items
        addedItems = []
        for i in range(lw.count()):
            item = lw.item(i)
            itemText = item.text()
            addedItems.append(itemText)

        # first check if there is any text there
        if cbo.currentText():
            # replace path separators so they are consistent with os
            text = cbo.currentText().replace("/", os.sep)

            # check if there are multiple items to add
            items = text.split(';;')

            # loop through items and add to list widget
            for item in items:
                if item.count(os.sep) > 0:
                    # file path so need to add to workspace
                    # and check geometry type
                    if os.path.splitext(item)[1].lower() == '.shp':
                        try:
                            name = os.path.basename(os.path.splitext(item)[0])
                            # check if already open in workspace
                            layer = tuflowqgis_find_layer(name)
                            if layer is not None:
                                # already open
                                if layer.geometryType() == geometryType:
                                    if name not in addedItems:
                                        lw.addItem(name)
                                        addedItems.append(name)
                                        if lw == self.lwLines:
                                            self.inputLineAdded.emit(layer)
                                else:
                                    QMessageBox.critical(self, "1D Integrity Tool",
                                                         "Geometry type does not match required input type")
                            else:
                                # need to add to workspace
                                self.iface.addVectorLayer(item, name, "ogr")
                                layer = tuflowqgis_find_layer(name)
                                if layer is not None:
                                    if layer.geometryType() == geometryType:
                                        if name not in addedItems:
                                            lw.addItem(name)
                                            addedItems.append(name)
                                            if lw == self.lwLines:
                                                self.inputLineAdded.emit(layer)
                                    else:
                                        QgsProject.instance().removeMapLayer(layer)
                                        QMessageBox.critical(self, "1D Integrity Tool",
                                                             "Geometry type does not match required input type")
                                else:
                                    QMessageBox.critical(self, "1D Integrity Tool",
                                                         "Unexpected error")
                        except:
                            QMessageBox.critical(self, "1D Integrity Tool",
                                                 "Error importing layer into QGIS")
                    else:
                        QMessageBox.critical(self, "1D Integrity Tool",
                                             "Input layer needs to be a shp file")
                else:
                    # trying to add an already open layer
                    layer = tuflowqgis_find_layer(item)
                    if layer is not None:
                        if layer.geometryType() == geometryType:
                            if item not in addedItems:
                                lw.addItem(item)
                                addedItems.append(item)
                                if lw == self.lwLines:
                                    self.inputLineAdded.emit(layer)
                        else:
                            QMessageBox.critical(self, "1D Integrity Tool",
                                                 "Geometry type does not match required input type")

    def removeItem(self, lw):
        """
        Removes selected items from list widget. If nothing
        is selected, removes the bottom item.

        :param lw: QListWidget
        :return: void
        """

        # get selected items
        selectedItems = lw.selectedItems()

        # collect items in a list but don't include selected items
        itemNames = []
        for i in range(lw.count()):
            item = lw.item(i)
            if item not in selectedItems:
                # if there are selected items then don't include
                # those selections in new list - if there aren't
                # any selected items then remove last item
                if selectedItems:
                    itemNames.append(item.text())
                else:
                    if i < lw.count() - 1:
                        itemNames.append(item.text())

        # clear and re-add items
        lw.clear()
        lw.addItems(itemNames)

        if lw == self.lwLines:
            self.inputLineRemoved.emit()

    def appendInputLineFeatures(self, e):
        """
        Appends the features from a newly input line layer to the start element combobox
        and any selected features to the list widget

        :param e: QgaMapLayer
        :return: void
        """

        # only do if flow trace is checked on
        if self.rbFlowTrace.isChecked():
            # Add feature IDs to combobox
            for f in e.getFeatures():
                self.cboStartElement.addItem(f.attribute(0))

            # Any selected features in that layer auto add to list widget
            selectedFeatures = e.selectedFeatures()
            self.lwStartElements.addItems([x.attribute(0) for x in selectedFeatures])

    def setGuiActive(self, active):
        """
        Sets all interactive features of the gui active or inactive

        :param active: bool
        :return: void
        """

        widgets = [self.browseInputLines, self.browseInputPoints, self.browseInputTables, self.btnAddLines,
                   self.btnAddPoints, self.btnAddTables, self.btnRemoveLines, self.btnRemovePoints,
                   self.btnRemoveTables, self.rbSnapping, self.rbPipeDirection, self.rbContinuity,
                   self.rbFlowTrace, self.cbExclRadius, self.cbAutoSnap, self.sbAutoSnapSearchRadius,
                   self.cbBasedOnInverts, self.cbBasedOnContinuity, self.cbContinuityArea, self.cbContinuityInverts,
                   self.cbContinuityAngle, self.sbContinuityAngle, self.cbContinuityCover, self.sbContinuityCover,
                   self.cbFlowTraceArea, self.cbFlowTraceInverts, self.sbContinuityArea, self.sbFlowTraceArea,
                   self.cbFlowTraceAngle, self.sbFlowTraceAngle, self.cbFlowTraceCover, self.sbFlowTraceCover,
                   self.pbRun, self.sbExclRadius]

        for widget in widgets:
            widget.setEnabled(active)