import os, sys
import re
import traceback
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.gui import *
from PyQt5.QtWidgets import *
from tuflow.forms.integrity_tool_dock import Ui_IntegrityTool
from tuflow.tuflowqgis_library import (findAllRasterLyrs, findAllVectorLyrs, tuflowqgis_find_layer,
                                       is1dNetwork, is1dTable, tuflowqgis_apply_check_tf_clayer, copyStyle)
from tuflow.tuflowqgis_dialog import StackTraceDialog
from .DataCollector import DataCollector
from .SnappingTool import SnappingTool
from .ContinuityTool import ContinuityTool
from .FlowTraceTool import DataCollectorFlowTrace, FlowTraceTool, FlowTracePlot
from .PipeDirectionTool import PipeDirectionTool
from .Enumerators import *
from .UniqueIds import UniqueIds, DuplicateRule, CreateNameRule, CreateNameRules
from .NullGeometry import NullGeometry, NullGeometryDialog


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
        self.selectedFeats = {}

        # add caculation objects
        # data collectors
        self.dataCollectorLines = DataCollector(self.iface)
        self.dataCollectorPoints = DataCollector(self.iface)
        self.dataCollectorTables = DataCollector(self.iface)
        self.uniqueIds = UniqueIds()
        self.nullGeometry = NullGeometry()

        self.plot = None

        # progress bar
        self.currentStep = 0
        self.maxProgressSteps = 0

        # set up radio buttons determing which tool to run
        # self.toolButtonGroup = QButtonGroup()
        # self.toolButtonGroup.addButton(self.rbSnapping)
        # self.toolButtonGroup.setId(self.rbSnapping, 0)
        # self.toolButtonGroup.addButton(self.rbPipeDirection)
        # self.toolButtonGroup.setId(self.rbPipeDirection, 1)
        # self.toolButtonGroup.addButton(self.rbContinuity)
        # self.toolButtonGroup.setId(self.rbContinuity, 2)
        # self.toolButtonGroup.addButton(self.rbFlowTrace)
        # self.toolButtonGroup.setId(self.rbFlowTrace, 3)
        # self.rbSnapping.setChecked(True)

        # apply icons
        self.applyIcons()

        # tooltips
        self.applyToolTips()

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
        self.pbUsePrevChan.clicked.connect(self.usePreviousSelection)

        # what happend when the Run button is pressed
        self.pbRun.clicked.connect(self.check)

    def qgisDisconnect(self):
        """Disconnect signals"""

        try:
            QgsProject.instance().layersAdded.disconnect(self.layersAdded)
        except:
            pass
        try:
            QgsProject.instance().layersRemoved.disconnect(self.layersRemoved)
        except:
            pass
        try:
            self.btnAddLines.clicked.disconnect()
        except:
            pass
        try:
            self.btnAddPoints.clicked.disconnect()
        except:
            pass
        try:
            self.btnAddTables.clicked.disconnect()
        except:
            pass
        try:
            self.btnRemoveLines.clicked.disconnect()
        except:
            pass
        try:
            self.btnRemovePoints.clicked.disconnect()
        except:
            pass
        try:
            self.btnRemoveTables.clicked.disconnect()
        except:
            pass
        try:
            self.pbRun.clicked.disconnect(self.check)
        except:
            pass

    def check(self):
        """
        Perform some checks prior to trying to run

        :return: None
        """

        # check there is at least a 1d_nwk line layer to use
        if self.tabWidget.currentIndex() != TOOL_TYPE.NullGeometry:
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
                        # QMessageBox.critical(self, "Integrity Tool",
                        #                      "Layer Is Not a 1d_nwk Type: {0}".format(layer.name()))
                        question = QMessageBox.warning(self, "Integrity Tool",
                                                       "Layer does not look like a 1d_nwk type: \"{0}\" - "
                                                       "Tool might not work if layer is not a 1d_nwk type. "
                                                       "Do you wish to continue?".format(layer.name()),
                                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                        if question != QMessageBox.Yes:
                            return
                    if inputType == 'lines':
                        for f in layer.getFeatures():
                            if isinstance(f.attribute(1), QVariant):
                                QMessageBox.critical(self, "Integrity Tool",
                                                     "Feature type must be character or string type (cannot be blank "
                                                     "or NULL).\nLayer: {0}\nFID: {1}".format(layer.name(), f.id()))
                                return
                else:  # tables
                    if not is1dTable(layer):
                        QMessageBox.critical(self, "Integrity Tool",
                                             "Layer Is Not a 1d_ta Type: {0}".format(layer.name()))
                        return

        self.run()

    def run(self):
        """
        Run the tool

        :return: void
        """

        self.setGuiActive(False)

        try:
            # check for null geometries
            if self.tabWidget.currentIndex() != TOOL_TYPE.NullGeometry:
                ok = self.checkNullGeometries()
                if not ok:
                    self.setGuiActive(True)
                    return

            # check unique ids and that every channel has an id (except x connectors)
            if self.tabWidget.currentIndex() != TOOL_TYPE.UniqueIds and \
                    self.tabWidget.currentIndex() != TOOL_TYPE.NullGeometry:
                ok = self.checkUniqueIds()
                if not ok:
                    self.setGuiActive(True)
                    return

            # run specified tool
            if self.tabWidget.currentIndex() == TOOL_TYPE.Snapping:
                self.runSnappingTool()
            elif self.tabWidget.currentIndex() == TOOL_TYPE.PipeDirection:
                self.runPipeDirectionTool()
            elif self.tabWidget.currentIndex() == TOOL_TYPE.Continuity:
                self.runContinuityTool()
            elif self.tabWidget.currentIndex() == TOOL_TYPE.FlowTrace:
                self.runFlowTraceTool()
            elif self.tabWidget.currentIndex() == TOOL_TYPE.UniqueIds:
                self.runUniqueIdTool()
            elif self.tabWidget.currentIndex() == TOOL_TYPE.NullGeometry:
                self.runNullGeometryTool()

            QgsProject.instance().addMapLayer(self.outputLyr)
            tuflowqgis_apply_check_tf_clayer(self.iface, layer=self.outputLyr)

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

    def checkUniqueIds(self):
        """
        Check that each channel has a unique id before running other tools.

        return: bool - whether to continue running other tools or not
        """

        layers = self.getInputs('lines')
        self.setupDataCollectorProgressBar(layers, 'uniqueIds')

        self.uniqueIds = UniqueIds()
        self.uniqueIds.updated.connect(self.updateProgressDataCollection)
        self.uniqueIds.finished.connect(lambda e: self.finishedDataCollection(e, text='Finished checking channel IDs'))
        self.uniqueIds.checkForDuplicates(layers)

        return len(self.uniqueIds.duplicate_ids) == 0 and self.uniqueIds.null_id_count == 0

    def checkNullGeometries(self):
        """
        Check all gis layers for null geometries before running other tools.

        return: bool
        """

        layers = self.getInputs(['lines', 'points', 'tables'])
        self.setupDataCollectorProgressBar(layers, 'nullGeometry')

        self.nullGeometry = NullGeometry()
        self.nullGeometry.updated.connect(self.updateProgressDataCollection)
        self.nullGeometry.finished.connect(lambda e: self.finishedDataCollection(e, text='Finished checking for empty geometry'))
        self.nullGeometry.checkForNullGeometries(layers)

        return self.nullGeometry.null_geom_count == 0

    def copyStyle(self, lyrs):
        for tmplyrname, oldlyrname in lyrs.items():
            tmplyr = tuflowqgis_find_layer(tmplyrname)
            oldlyr = tuflowqgis_find_layer(oldlyrname)
            if tmplyr is None or oldlyr is None:
                continue
            errmsg = copyStyle(oldlyr, tmplyr)
            if not errmsg:
                tmplyr.triggerRepaint()

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
            self.copyStyle(self.snappingToolLines.tmplyr2oldlyr)

            if inputPoints:
                self.snappingToolPoints.autoSnap(radius)
                for lyr in self.snappingToolPoints.tmpLyrs:
                    QgsProject.instance().addMapLayer(lyr)

                self.copyStyle(self.snappingToolPoints.tmplyr2oldlyr)
            
            noAutoSnap = True
            if self.snappingToolLines.tmpLyrs:
                noAutoSnap = False
            if inputPoints:
                if self.snappingToolPoints.tmpLyrs:
                    noAutoSnap = False
            if noAutoSnap:
                QMessageBox.information(self.iface.mainWindow(), "Integrity Tool",
                                        "No auto snapping operations performed.")
            else:
                self.replaceInputs([self.snappingToolLines.tmplyr2oldlyr, self.snappingToolPoints.tmplyr2oldlyr], TOOL_TYPE.Snapping)
    
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
        startLocs_ = {}
        for lyr in inputLines:
            selFeats = lyr.selectedFeatures()
            for f in selFeats:
                fid = f.id()
                loc = (lyr.name(), fid)
                startLocs.append(loc)

                if lyr.id() not in startLocs_:
                    startLocs_[lyr.id()] = []
                startLocs_[lyr.id()].append(fid)
        
        if not startLocs:
            QMessageBox.critical(self, "Flow Trace", "Need to select at least one feature to start the flow trace from")
            return

        if len(startLocs) > 5:
            QMessageBox.critical(self, "Flow Trace", "Upper limit of 5 channels are allowed to be selected")
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
        self.selectedFeats = {x: y for x, y in startLocs_.items()}
        
        if self.cbFlowTraceLongPlots.isChecked():
            self.dotCount = 0
            self.message = "Generating Long Profiles"
            self.runStatus.setText(self.message)
            self.progressBar.setValue(0)
            self.progressBar.setRange(0, 0)
            self.plot = FlowTracePlot(self, self.flowTraceTool, self.iface)
            self.plot.finished_.connect(self.showPlot)
            self.plot.updated_.connect(self.updateStatusBar)
            self.plot.updateMessage_.connect(self.updateMessage)
            self.plot.error_.connect(self.catchPlotError)
            self.plot.updateMaxSteps_.connect(self.updateMaxProgressSteps)

            self.plot.run_plotter()
            
    def showPlot(self):
        self.runStatus.setText("Finished Generating Long Plot")
        self.progressBar.setValue(100)
        self.progressBar.setRange(0, 100)
        self.plot.show()

        try:
            self.plot.finished_.disconnect(self.showPlot)
        except:
            pass
        try:
            self.plot.updated_.disconnect(self.updateStatusBar)
        except:
            pass
        try:
            self.plot.updateMessage_.disconnect(self.updateMessage)
        except:
            pass
        # try:
        #     self.plot.error_.disconnect(self.catchPlotError)
        # except:
        #     pass
        try:
            self.plot.updateMaxSteps_.disconnect(self.updateMaxProgressSteps)
        except:
            pass

    def catchPlotError(self):
        self.setGuiActive(True)
        message = "Unexpected Error Occurred.\nPlease Email Stack Trace To support@tuflow.com"
        self.runStatus.setText("Unexpected Error")
        self.progressBar.setValue(100)
        QMessageBox.critical(self, "Integrity Tool", message)
        msg = self.plot.errmsg if self.plot.errmsg is not None else ''
        stackTraceDialog = StackTraceDialog(msg)
        stackTraceDialog.exec_()

    def runUniqueIdTool(self):
        """
        Check that each channel has a unique id before running other tools.

        return: bool - whether to continue running other tools or not
        """

        layers = self.getInputs('lines')

        self.outputLyr = None
        self.uniqueIds = UniqueIds()
        self.uniqueIds.updated.connect(self.updateProgressDataCollection)
        self.uniqueIds.finished.connect(lambda e: self.finishedDataCollection(e, text='Finished checking channel IDs'))

        self.setupDataCollectorProgressBar(layers, 'uniqueIds')
        self.uniqueIds.checkForDuplicates(layers, write_duplicate_errors=False)
        if not self.uniqueIds.duplicate_ids and not self.uniqueIds.null_id_count:
            QMessageBox.information(self, 'Integrity Tools', 'All channel IDs were compliant')
            return

        if self.cbFindNonCompIDs.isChecked():
            # reset progressbar
            self.currentStep = 0
            self.maxProgressSteps = len(self.uniqueIds.duplicate_ids) + self.uniqueIds.null_id_count
            self.progressBar.setValue(0)

            # reconnect signals
            self.uniqueIds.updated.connect(self.updateProgressDataCollection)
            self.uniqueIds.finished.connect(lambda e: self.finishedDataCollection(e, text='Finished flagging non-compliant IDs'))

            # run process
            self.uniqueIds.findNonCompliantIds()

        if self.cbFixChannelIDs.isChecked():
            # re-setup progress bar
            self.setupDataCollectorProgressBar(layers, 'fixChannelIds')

            # collect rules
            duplicateRule = DuplicateRule(
                append_letter=self.rbDuplicateUseLetters.isChecked(),
                append_number=self.rbDuplicateUseNumbers.isChecked(),
                delimiter=self.leCustomDelim.text().strip()
            )
            # stuff needed for eval in list comprehension
            globs = globals()
            locs = locals()
            createNameRuleList = [
                CreateNameRule(
                    duplicate_rule=duplicateRule,
                    type=eval('self.leType{0}.text().strip()'.format(x), globs, locs),
                    prefix=eval('self.lePrefix{0}.text().strip()'.format(x), globs, locs)
                )
                for x in range(1, 5) if eval('self.leType{0}.text().strip()'.format(x), globs, locs)
            ]
            createNameRuleList.append(
                CreateNameRule(
                    duplicate_rule=duplicateRule,
                    default_rule=True,
                    prefix=self.leDefaultPrefix.text().strip()
                )
            )
            createNameRules = CreateNameRules(createNameRuleList)

            # pass rules to class and run
            # reconnect signals
            self.uniqueIds.updated.connect(self.updateProgressDataCollection)
            self.uniqueIds.finished.connect(lambda e: self.finishedDataCollection(e, text='Finished correcting non-compliant IDs'))
            self.uniqueIds.fixChannelIDs(duplicateRule, createNameRules)

        if self.uniqueIds.outputLyr is not None and self.uniqueIds.outputLyr.isValid():
            QgsProject.instance().addMapLayer(self.uniqueIds.outputLyr)
            tuflowqgis_apply_check_tf_clayer(self.iface, layer=self.uniqueIds.outputLyr)

        self.copyStyle(self.uniqueIds.tmplyr2oldlyr)

        self.replaceInputs([self.uniqueIds.tmplyr2oldlyr], TOOL_TYPE.UniqueIds)

    def runNullGeometryTool(self):
        layers = self.getInputs(['lines', 'points', 'tables'])
        self.setupDataCollectorProgressBar(layers, 'nullGeometry')

        self.nullGeometry = NullGeometry()
        self.nullGeometry.updated.connect(self.updateProgressDataCollection)
        self.nullGeometry.finished.connect(lambda e: self.finishedDataCollection(e, text='Finished checking for empty geometry'))
        self.nullGeometry.checkForNullGeometries(layers, write_null_geom_errors=False)

        if not self.nullGeometry.null_geom_count:
            QMessageBox.information(self, 'Integrity Tools', 'No empty geometries found.')
            return

        message = '<span style=" font-size:10pt; font-weight:600; text-decoration: underline;">' \
                  '{0} empty geometry found</span>.<br><br>'.format(self.nullGeometry.null_geom_count)
        for layer in layers:
            if layer.name() not in self.nullGeometry.gis_layers_containing_null:
                message = '{0}<span style="font-weight:600;">{1} [0]</span>:<br>' \
                          '<span style="font-style:italic;">&nbsp;&nbsp;&nbsp;&nbsp;No Empty Geometry' \
                          '</span><br><br>'.format(message, layer.name())
                continue

            count = len(self.nullGeometry.gis_layers_containing_null[layer.name()])
            message = '{0}<span style="font-weight:600;">{1} [{2}]</span>:<br>'.format(message, layer.name(), count)
            ids_ = ''
            for id_ in self.nullGeometry.gis_layers_containing_null[layer.name()]:
                if id_ == 'Empty ID':
                    ids_ = '{0}<span style="font-style:italic;">&nbsp;&nbsp;&nbsp;&nbsp;{1}' \
                           '</span><br>'.format(ids_, id_)
                else:
                    ids_ = '{0}&nbsp;&nbsp;&nbsp;&nbsp;{1}<br>'.format(ids_, id_)
            message = '{0}{1}<br><br>'.format(message, ids_)

        self.nullGeometryDialog = NullGeometryDialog(self, message)
        self.nullGeometryDialog.exec_()

        if not self.nullGeometryDialog.confirmDelete:
            return

        layers = [x for x in layers if x.name() in self.nullGeometry.gis_layers_containing_null]
        self.setupDataCollectorProgressBar(layers, 'nullGeometry')

        # reconnect signals
        self.nullGeometry.updated.connect(self.updateProgressDataCollection)
        self.nullGeometry.finished.connect(lambda e: self.finishedDataCollection(e, text='Finished deleting empty geometry'))
        # delete empty geometries
        self.nullGeometry.deleteNullGeometry()

        self.copyStyle(self.nullGeometry.tmplyr2oldlyr)

        self.replaceInputs([self.nullGeometry.tmplyr2oldlyr], TOOL_TYPE.NullGeometry)

    def updateMaxProgressSteps(self, value):
        self.currentStep = 0
        self.maxProgressSteps = value
        self.progressBar.setValue(0)
        self.progressBar.setRange(0, 100)

    def updateStatusBar(self):
        self.updateProgressDataCollection()
        
    def updateMessage(self, msg_no):
        messages = {
            LongPlotMessages.CollectingBranches: 'Collecting long plot branches . . .',
            LongPlotMessages.Populating: 'Populating long plot information . . .'
        }
        self.message = messages.get(msg_no)
        self.runStatus.setText(self.message)

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
        self.copyStyle(pipeDirectionTool.tmplyr2oldlyr)

        self.replaceInputs([pipeDirectionTool.tmplyr2oldlyr], TOOL_TYPE.PipeDirection)

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
            if self.dataCollectorLines.errMessage is not None:
                self.finishedDataCollection(self.dataCollectorLines, "Errors occurred")

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

        if inputType == 'lines' or 'lines' in inputType:
            for i in range(self.lwLines.count()):
                item = self.lwLines.item(i)
                itemText = item.text()
                if bReturnName:  # append just the text name
                    inputs.append(itemText)
                else:  # append the QgsVectorLayer
                    layer = tuflowqgis_find_layer(itemText)
                    inputs.append(layer)
        if inputType == 'points' or 'points' in inputType:
            for i in range(self.lwPoints.count()):
                item = self.lwPoints.item(i)
                itemText = item.text()
                if bReturnName:  # append just the text name
                    inputs.append(itemText)
                else:  # append the QgsVectorLayer
                    layer = tuflowqgis_find_layer(itemText)
                    inputs.append(layer)
        if inputType == 'tables' or 'tables' in inputType:
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
        elif inputType == 'uniqueIds':
            self.runStatus.setText("Checking channels for duplicate IDs. . .")
        elif inputType == 'fixChannelIds':
            self.runStatus.setText("Fixing Channel IDs. . .")
        elif inputType == 'nullGeometry':
            self.runStatus.setText("Checking GIS layers for null geometries. . .")

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
            if e.errMessage is not None:
                QMessageBox.critical(self, "Integrity Tool", e.errMessage)
                self.runStatus.setText(e.errMessage)
            self.dataCollectorLines.updated.disconnect()
            self.dataCollectorLines.finished.disconnect()
        elif e == self.dataCollectorPoints:
            if e.errMessage is not None:
                QMessageBox.critical(self, "Integrity Tool", e.errMessage)
                self.runStatus.setText(e.errMessage)
            self.dataCollectorPoints.updated.disconnect()
            self.dataCollectorPoints.finished.disconnect()
        elif e == self.dataCollectorTables:
            pass
        elif e == self.uniqueIds:
            if e.errMessage is not None:
                QMessageBox.critical(self, "Integrity Tool", e.errMessage)
                self.runStatus.setText(e.errStatus)
            self.uniqueIds.updated.disconnect()
            self.uniqueIds.finished.disconnect()
        elif e == self.nullGeometry:
            if e.errMessage is not None:
                QMessageBox.critical(self, "Integrity Tool", e.errMessage)
                self.runStatus.setText(e.errStatus)
            self.nullGeometry.updated.disconnect()
            self.nullGeometry.finished.disconnect()

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

    def applyToolTips(self):
        """Setup tooltips."""

        self.inputLinesToolTip.setToolTip(
            self.tr('Any input using 1d_nwk template file can be used as an input.\n'
                    '\n'
                    'e.g. pipes, culverts, open channels etc')
        )
        self.inputPointsToolTip.setToolTip(
            self.tr('Any input using 1d_nwk template file can be used as an input.\n'
                    '\n'
                    'e.g. pits, nodes, manholes etc')
        )
        self.inputTablesToolTip.setToolTip(
            self.tr('Any input using 1d_ta template file can be used as an input.\n'
                    '\n'
                    'e.g. cross-sections, HW tables, CS tables etc')
        )

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
                   self.btnRemoveTables,
                   # self.rbSnapping, self.rbPipeDirection, self.rbContinuity, self.rbFlowTrace,
                   self.cbExclRadius, self.cbAutoSnap, self.sbAutoSnapSearchRadius,
                   self.cbBasedOnInverts, self.cbBasedOnContinuity, self.cbContinuityArea, self.cbContinuityInverts,
                   self.cbContinuityAngle, self.sbContinuityAngle, self.cbContinuityCover, self.sbContinuityCover,
                   self.cbFlowTraceArea, self.cbFlowTraceInverts, self.sbContinuityArea, self.sbFlowTraceArea,
                   self.cbFlowTraceAngle, self.sbFlowTraceAngle, self.cbFlowTraceCover, self.sbFlowTraceCover,
                   self.pbRun, self.sbExclRadius,
                   self.cbFindNonCompIDs, self.cbFixChannelIDs, self.rbDuplicateUseLetters, self.rbDuplicateUseNumbers,
                   self.leCustomDelim, self.leDefaultPrefix, self.leType1, self.lePrefix1, self.leType2, self.lePrefix2,
                   self.leType3, self.lePrefix3, self.leType4, self.lePrefix4]

        for widget in widgets:
            widget.setEnabled(active)

    def usePreviousSelection(self):
        inputs = self.getInputs('lines')
        for lyr in inputs:
            lyrid = lyr.id()
            if lyrid in self.selectedFeats:
                fids = self.selectedFeats[lyrid]
                lyr.selectByIds(fids, QgsVectorLayer.SetSelection)
            else:
                lyr.deselect([x.id() for x in lyr.getFeatures()])

    def replaceInputs(self, new_lyrs, tool):
        suffix = {
            TOOL_TYPE.Snapping: r'_SN\d+$',
            TOOL_TYPE.PipeDirection: r'_PD\d+$',
            TOOL_TYPE.UniqueIds: r'_ID\d+$',
            TOOL_TYPE.NullGeometry: r'_EG\d+$'
        }

        if not new_lyrs or not [x for x in new_lyrs if x]:
            return

        answer = QMessageBox.information(self, '1D Integrity Tool', 'Replace inputs with tool outputs?',
                                         QMessageBox.Yes, QMessageBox.No)

        if answer != QMessageBox.Yes:
            return

        for tmplyrs in new_lyrs:
            for tmplyrname, oldlyrname in tmplyrs.items():
                lyr = tuflowqgis_find_layer(tmplyrname)
                if lyr is None:
                    continue

                if lyr.geometryType() == QgsWkbTypes.GeometryType.PointGeometry:
                    lw = self.lwPoints
                elif lyr.geometryType() == QgsWkbTypes.GeometryType.LineGeometry:
                    lw = self.lwLines
                else:
                    continue

                for i in range(lw.count()):
                    item = lw.item(i)
                    if item.text() == oldlyrname:
                        item.setText(tmplyrname)
