__VK__ = '0000000000-000000000000-000000000000'
import os, sys
import re
from datetime import datetime, timedelta
from qgis.core import (QgsApplication, QgsMapLayer, QgsVectorLayer,
                       QgsProject, QgsWkbTypes, QgsUnitTypes)
import processing
from qgis.gui import QgisInterface
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QRegExpValidator, QPalette
from PyQt5.QtWidgets import (QDockWidget, QLineEdit, QFileDialog,
                             QComboBox, QMessageBox, QLabel, QListWidgetItem,
                             QWidget, QCheckBox, QHBoxLayout, QSpacerItem, QSizePolicy,
                             QLayout, QTableWidgetItem, QListWidget)
from .refh2_dock import Ui_refh2
from .engine import Refh2



class Refh2Dock(QDockWidget, Ui_refh2):
    """Class for ReFH2 to TUFLOW dialog / dock"""
    
    def __init__(self, iface: QgisInterface) -> None:
        QDockWidget.__init__(self)
        self.setupUi(self)
        self.iface = iface
        self.connections = []
        
        self.applyIcons()
        self.setupTimeLineEdits()
        self.addGIS()
        self.populateCboFeatures()
        self.populateCboFields()
        self.cbCCAllActive.setLayoutDirection(Qt.RightToLeft)

        # input checking - add red text if an error is flagged
        self.flags = []
        self.leInputXML.editingFinished.connect(self.inputCatchmentChanged)
        self.rbUserArea.toggled.connect(self.checkAreaInput)
        self.sbArea.valueChanged.connect(self.checkAreaInput)
        self.cboInputGIS.currentIndexChanged.connect(self.checkAreaInput)
        self.leDuration.editingFinished.connect(self.durationChanged)
        self.leTimestep.editingFinished.connect(self.durationChanged)
        self.gbOutRainfall.toggled.connect(self.rainfallOutputChanged)
        self.rbGrossRainfall.toggled.connect(self.rainfallOutputChanged)
        self.rbNetRainfall.toggled.connect(self.rainfallOutputChanged)
        self.gbOutHydrograph.toggled.connect(self.hydrographOutputChanged)
        self.rbDirectRunoff.toggled.connect(self.hydrographOutputChanged)
        self.rbBaseFlow.toggled.connect(self.hydrographOutputChanged)
        self.rbTotalRunoff.toggled.connect(self.hydrographOutputChanged)
        self.gbRainToGis.toggled.connect(self.outputToTuflowGisToggled_Rainfall)
        self.cboInputGIS.currentIndexChanged.connect(self.outputToTuflowGisToggled_Rainfall)
        self.gbOutRainfall.toggled.connect(self.outputToTuflowGisToggled_Rainfall)
        self.rb2dRf.toggled.connect(self.outputToTuflowGisToggled_Rainfall)
        self.gbHydToGis.toggled.connect(self.outputToTuflowGisToggled_Runoff)
        self.cboInputGIS.currentIndexChanged.connect(self.outputToTuflowGisToggled_Runoff)
        self.gbOutHydrograph.toggled.connect(self.outputToTuflowGisToggled_Runoff)
        self.rb2dSa.toggled.connect(self.outputToTuflowGisToggled_Runoff)
        self.rb1dBc.toggled.connect(self.outputToTuflowGisToggled_Runoff)
        self.rb2dBc.toggled.connect(self.outputToTuflowGisToggled_Runoff)

        # other signals
        QgsProject.instance().layersAdded.connect(self.addGIS)
        QgsProject.instance().layersRemoved.connect(self.addGIS)
        self.cboInputGIS.currentIndexChanged.connect(self.populateCboFields)
        self.cboInputGIS.currentIndexChanged.connect(self.populateCboFeatures)
        self.cboFields.currentIndexChanged.connect(self.populateCboFeatures)
        self.cbSelectAll.clicked.connect(self.toggleSelectAll)
        self.btnAddRP.clicked.connect(self.addReturnPeriod)
        self.btnRemoveRP.clicked.connect(self.removeReturnPeriods)
        self.btnAddDur.clicked.connect(self.addDurTimestep)
        self.btnRemDur.clicked.connect(self.removeDurTimestep)
        self.connectEventCheckBoxes()
        self.cbCCAllActive.clicked.connect(self.toggleClimChangeAllActive)
        self.connectClimChangeCheckBoxes()
        self.rbEngine23.clicked.connect(self.toggleEngine23Enabled)
        self.rbEngine22.clicked.connect(self.toggleEngine23Enabled)
        # self.rbRural.clicked.connect(lambda e: self.radioButtonClones(button=self.rbRural))
        # self.rbUrban.clicked.connect(lambda e: self.radioButtonClones(button=self.rbUrban))
        # self.rbRuralClone.clicked.connect(lambda e: self.radioButtonClones(button=self.rbRuralClone))
        # self.rbUrbanClone.clicked.connect(lambda e: self.radioButtonClones(button=self.rbUrbanClone))
        self.pbRun.clicked.connect(self.check)

        dir = os.path.dirname(os.path.dirname(__file__))
        rf2Icon = QIcon(os.path.join(dir, 'icons', "ReFH2icon.png"))
        self.btnInputXML.clicked.connect(lambda: browse(self, "existing file", "TUFLOW/refh2_xml",
                                                        "Catchment Descriptor Input", "XML (*.xml *.XML)",
                                                        self.leInputXML, rf2Icon, lambda: self.inputCatchmentChanged()))
        self.btnOutfile.clicked.connect(lambda: browse(self, "output file", "TUFLOW/refh2_outfile",
                                                       "ReFH2 Output CSV File", "CSV (*.csv *.CSV)",
                                                       self.leOutfile, rf2Icon))

    def run(self, vk=None) -> None:
        """
        Run the tool
        Collects inputs and passes to engine.py for processing
        
        :return: None
        """

        if vk != __VK__:
            QMessageBox.warning(self, "ReFH2 to TUFLOW",
                                "Tool needs to be run compiled. Please contact support@tuflow.com.")
            return

        # collect inputs - initialise with actual values where can
        # otherwise some dummy values
        inputs = {
            'descriptor': self.leInputXML.text(),
            'location': Refh2.England if self.rbEngland.isChecked() else Refh2.Scotland,
            'area': 0,
            'return periods': [],
            'durations': [],
            'timesteps': [],
            'season': Refh2.Winter if self.rbWinter.isChecked() else Refh2.Summer,
            'do output rainfall': True if self.gbOutRainfall.isChecked() else False,
            'do output hydrograph': True if self.gbOutHydrograph.isChecked() else False,
            'output data': [],
            'output hydrograph type': {},
            'output gis': None,
            'output file': os.path.splitext(self.leOutfile.text())[0] if self.leOutfile.text() else \
                os.path.splitext(self.leInputXML.text())[0],
            'catchment name': None,
            'inflow name': 'Inflow',
            'rainfall name': 'Rainfall',
            'gis feature': None,
            'crs': None,
            'gis geometry': None,
            'zero padding': Refh2.AutoPad,
            'number zero padding': 3,
            'engine version': 2.3 if self.rbEngine23.isChecked() else 2.2,
            'urban area': 0,
            'arf': self.sbARF.value() if self.cbARF.isChecked() else None,
        }
        
        # populate rest with real values
        # inflow / rainfall names
        layer = tuflowqgis_find_layer(self.cboInputGIS.currentText())
        layerUnits = None
        feat = None
        fid = None
        area = 0
        if self.cboInputGIS.currentText() and layer is not None:
            #layer = tuflowqgis_find_layer(self.cboInputGIS.currentText())
            #if layer is not None:
            inputs['gis geometry'] = layer.wkbType()
            crs = layer.sourceCrs()
            layerUnits = crs.mapUnits()
            inputs['crs'] = crs

            fid = self.cboFeatures.currentIndex()
            fids = {x.id(): x for x in layer.getFeatures()}
            feat = fids[fid]
            inputs['catchment name'] = '{0}'.format(feat.attribute(self.cboFields.currentIndex()))
            if inputs['do output rainfall'] and inputs['do output hydrograph']:
                inputs['inflow name'] = '{0}_inflow'.format(feat.attribute(self.cboFields.currentIndex()))
                inputs['rainfall name'] = '{0}_rf'.format(feat.attribute(self.cboFields.currentIndex()))
            else:
                inputs['inflow name'] = '{0}'.format(feat.attribute(self.cboFields.currentIndex()))
                inputs['rainfall name'] = '{0}'.format(feat.attribute(self.cboFields.currentIndex()))
        else:
            if self.gbBoundaryName.isChecked() and self.leBoundaryName.text():
                bname = self.leBoundaryName.text()
                if inputs['do output rainfall'] and inputs['do output hydrograph']:
                    inputs['inflow name'] = '{0}_inflow'.format(bname)
                    inputs['rainfall name'] = '{0}_rf'.format(bname)
                else:
                    inputs['inflow name'] = bname
                    inputs['rainfall name'] = bname
        
        # area
        urbanArea = self.sbAreaUrban.value()
        if self.rbUserArea.isChecked():
            area = self.sbArea.value()
        elif layerUnits is not None and feat is not None and fid is not None:
            area = feat.geometry().area()
            if layerUnits == QgsUnitTypes.DistanceMeters:
                area = area / 1000 / 1000
            elif layerUnits == QgsUnitTypes.DistanceCentimeters:
                area = area / 100000 / 100000
            elif layerUnits == QgsUnitTypes.DistanceMillimeters:
                area = area / 1000000 / 1000000
            elif layerUnits == QgsUnitTypes.DistanceFeet:
                area = area / 3.28084 / 3.28084 / 1000 / 1000
            elif layerUnits == QgsUnitTypes.DistanceNauticalMiles:
                area = area * 1852 * 1852 / 1000 / 1000
            elif layerUnits == QgsUnitTypes.DistanceYards:
                area = area / 1.09361 / 1.09361 / 1000 / 1000
            elif layerUnits == QgsUnitTypes.DistanceMiles:
                area = area * 1609.34 * 1609.34 / 1000 / 1000
            elif layerUnits == QgsUnitTypes.DistanceDegrees:
                # convert to meters
                centroid = feat.geometry().centroid()
                x = centroid.asPoint()[0]
                epsg = self.getCartesian(x)
                parameters = {'INPUT': layer, 'TARGET_CRS': epsg, 'OUTPUT': 'memory:Reprojected'}
                reproject = processing.run("qgis:reprojectlayer", parameters)
                layer_reproject = reproject['OUTPUT']
                fids_reproject = {x.id(): x for x in layer_reproject.getFeatures()}
                feat_reproject = fids_reproject[fid]
                area = feat_reproject.geometry().area() / 1000 / 1000
            else:  # assume meters
                area = area / 1000 / 1000
        else:
            # should not be here
            QMessageBox.critical(self, "ReFH2 to TUFLOW",
                                 f"Unexpected ERROR: Variable(s) should not be None\n"
                                 f"layerUnits: {layerUnits}\n"
                                 f"feat: {feat}\n"
                                 f"fid: {fid}\n"
                                 "Please contact support@tuflow.com")
            return
        if area <= 0:
            area = 0.001
        inputs['area'] = area
        inputs['urban area'] = urbanArea
        
        # return periods
        rps = []
        aris = [1, 2, 5, 10, 30, 50, 75, 100, 200, 1000]
        f = self.sbCCFactor.value()  # climate change factor
        for ari in aris:
            cb = eval("self.cb{0:04d}y".format(ari))
            cb_cc = eval("self.cb{0:04d}y_CC".format(ari))  # climate change
            if cb.isChecked():
                rps.append(str(ari))
                if cb_cc.isChecked() and cb_cc.isEnabled():
                    rps.append("{0}CC{1:.1f}".format(ari, f))
        for i in range(self.lwRP.count()):
            item = self.lwRP.item(i)
            widget = self.lwRP.itemWidget(item)
            labelRp = widget.layout().itemAt(0).widget()
            cb = widget.layout().itemAt(2).widget()  # climate change
            rp = labelRp.text().strip('year').strip()
            rps.append(rp)
            if cb.isChecked() and cb.isEnabled():
                rp = "{0}CC{1:.1f}".format(rp, f)
                rps.append(rp)
        inputs['return periods'] = rps

        # duration(s)
        if self.lwDuration.count():
            for t in [self.lwDuration.item(x).text() for x in range(self.lwDuration.count())]:
                durText, tsText = t.split(" - ")
                inputs['durations'].append(convertFormattedTimeToFormattedTime(durText))
                inputs['timesteps'].append(convertFormattedTimeToFormattedTime(tsText))
        else:
            durText = self.leDuration.text()
            if durText != '::':
                inputs['durations'].append(convertFormattedTimeToFormattedTime(durText))

            # timestep(s)
            tsText = self.leTimestep.text()
            if tsText != '::':
                inputs['timesteps'].append(convertFormattedTimeToFormattedTime(tsText))
        
        # output data
        outdata = []
        if self.gbOutRainfall.isChecked():
            if self.rbGrossRainfall.isChecked():
                outdata.append(Refh2.GrossRainfall)
            if self.rbNetRainfall.isChecked():
                outdata.append(Refh2.NetRainfall)
        if self.gbOutHydrograph.isChecked():
            if self.rbDirectRunoff.isChecked():
                outdata.append(Refh2.DirectRunoff)
            if self.rbBaseFlow.isChecked():
                outdata.append(Refh2.BaseFlow)
            if self.rbTotalRunoff.isChecked():
                outdata.append(Refh2.TotalRunoff)
        inputs['output data'] = outdata
        
        # output GIS
        outGIS = []
        if self.gbOutRainfall.isChecked() and self.gbRainToGis.isChecked():
            inputs['gis feature'] = feat
            if self.rb2dRf.isChecked():
                outGIS.append(Refh2.RF)
            else:
                outGIS.append(Refh2.SA_RF)
        if self.gbOutHydrograph.isChecked() and self.gbHydToGis.isChecked():
            inputs['gis feature'] = feat
            if self.rb2dBc.isChecked():
                outGIS.append(Refh2.BC_2d)
            elif self.rb2dSa.isChecked():
                outGIS.append(Refh2.SA)
            else:
                outGIS.append(Refh2.BC_1d)
        if outGIS:
            inputs['output gis'] = outGIS

        # rural and/or urban
        if self.gbOutRainfall.isChecked():
            inputs["output hydrograph type"]['rainfall'] = Refh2.Rural if self.rbRuralClone.isChecked() else Refh2.Urban
        if self.gbOutHydrograph.isChecked():
            inputs["output hydrograph type"]['hydrograph'] = Refh2.Rural if self.rbRural.isChecked() else Refh2.Urban

        # output zero padding
        if self.rbNoPad.isChecked():
            inputs['zero padding'] = Refh2.NoPad
        elif self.rbSetPad.isChecked():
            inputs['zero padding'] = Refh2.UserPad
            inputs['number zero padding'] = self.sbPadNo.value()

        # outfile - make sure output directory exists or can be created
        dir = os.path.dirname(inputs['output file'])
        if not makeDir(dir):
            QMessageBox.critical(self, "ReFH2 to TUFLOW", "Unexpected Error with Output File Location: "
                                                          "Double Check Directory")
            return
        # make sure not locked for editing
        if os.path.exists(inputs['output file']):
            try:
                fo = open(inputs['output file'], 'a')
                fo.close()
            except PermissionError:
                QMessageBox.critical(self, "ReFH2 to TUFLOW", "Output File Locked:\n{0}".format(inputs['output file']))
                return
        # rainmodel - only 2013 available in this tool for now but can add 1999 later if needed
        rainModel = '2013'
        inputs['rain model'] = rainModel

            
        # setup run process on a separate thread
        # so that an infinite progress bar can be used
        self.thread = QThread()
        self.refh2 = Refh2(inputs, __VK__)
        self.refh2.moveToThread(self.thread)
        self.refh2.locatingExe.connect(self.findingExe)
        self.refh2.refh2Start.connect(self.refh2Started)
        self.refh2.tuflowProcessingStart.connect(self.tuflowProcessingStarted)
        self.refh2.finished.connect(self.refh2Finished)
        self.thread.started.connect(self.refh2.run)
        self.thread.start()
        
        self.progressBar.setRange(0, 0)
        self.progressBar.setValue(0)
        
    def findingExe(self) -> None:
        """
        
        :return: None
        """

        self.progressBarLabel.setText("Locating ReFH2 Executable . . . .")
    
    def refh2Started(self) -> None:
        """
        Event that happens when ReFH2 is started.
        Sets progress bar to infinite and
        updates text.
        
        :return: None
        """
        
        self.progressBarLabel.setText("Getting ReFH2 Data . . . .")
        
    def tuflowProcessingStarted(self) -> None:
        """
        Event that happens when ReFH2 is finished
        and the data is being processed into
        TUFLOW format.
        
        :return: None
        """

        self.progressBarLabel.setText("Processing Data Into TUFLOW Format . . . .")
        
    def refh2Finished(self, message: str='') -> None:
        """
        Event is triggered when finished. If message
        is empty = completed successfully, else error.
        
        :param message: str error message if any
        :return: None
        """
        
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(100)
        if message:
            if message[:7] == "WARNING":
                self.progressBarLabel.setText("Finished Successfully")
                QMessageBox.information(self, "ReFH2 to TUFLOW", message)
            else:
                self.progressBarLabel.setText("Finished.. Errors Occured")
                QMessageBox.critical(self, "ReFH2 to TUFLOW", message)
        else:
            self.progressBarLabel.setText("Finished Successfully")
        self.thread.terminate()
        self.thread.wait()

    def returnPeriodWidget(self, rp):
        """

        """

        widget = QWidget()
        label = QLabel(rp)
        cb = QCheckBox("CC")
        cb.setLayoutDirection(Qt.RightToLeft)
        if self.cbCCAllActive.isChecked():
            cb.setChecked(True)
        cb.stateChanged.connect(self.reAssessAllActiveCheckBox)
        spacerItem = QSpacerItem(40, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 10, 0)
        layout.addWidget(label)
        layout.addItem(spacerItem)
        layout.addWidget(cb)
        widget.setLayout(layout)

        return widget, layout

    def addReturnPeriod(self) -> None:
        """
        Adds return period in spinbox to list widget.
        
        :return: None
        """
        
        rp = '{0} year'.format(self.sbRP.value())
        
        rps = []
        for i in range(self.lwRP.count()):
            item = self.lwRP.item(i)
            widget = self.lwRP.itemWidget(item)
            rps.append(widget.layout().itemAt(0).widget().text())

        if rp in rps:
            return

        item = QListWidgetItem()
        widget, layout = self.returnPeriodWidget(rp)
        self.lwRP.addItem(item)
        self.lwRP.setItemWidget(item, widget)

        enabled = True if self.rbEngine23.isChecked() else False
        cb = layout.itemAt(2).widget()
        cb.setEnabled(enabled)
            
    def removeReturnPeriods(self) -> None:
        """
        Remove return period(s) from list widget.
        Will remove selected return periods, or last entry
        if none selected.
        
        :return: None
        """
        
        sel = self.lwRP.selectedItems()
        
        if sel:
            for i in reversed(range(self.lwRP.count())):
                if self.lwRP.item(i) in sel:
                    self.lwRP.takeItem(i)
        else:
            self.lwRP.takeItem(self.lwRP.count() - 1)

    def addDurTimestep(self) -> None:
        """
        Add Duration - Timestep to list widget
        """

        self.durationChanged()
        for flag in self.flags[:]:
            if flag[0] is self.horizontalLayout_8 or flag[0] is self.horizontalLayout_7 or \
                    flag[0] is self.verticalLayout_10:  # input flag
                return

        durText = self.leDuration.text()
        dur = convertFormattedTimeToFormattedTime(durText)
        tsText = self.leTimestep.text()
        ts = convertFormattedTimeToFormattedTime(tsText)

        t = f"{dur} - {ts}"
        if t not in [self.lwDuration.item(x).text() for x in range(self.lwDuration.count())]:
            self.lwDuration.addItem(t)

    def removeDurTimestep(self) -> None:
        """
        Remove Duration - Timestep from list widget.
        Will remove selected return periods, or last entry
        if none selected.
        """

        sel = self.lwDuration.selectedItems()

        if sel:
            for i in reversed(range(self.lwDuration.count())):
                if self.lwDuration.item(i) in sel:
                    self.lwDuration.takeItem(i)
        else:
            self.lwDuration.takeItem(self.lwDuration.count() - 1)
    
    def setupTimeLineEdits(self) -> None:
        """
        Formats the line edit to a time HH:MM:SS format
        
        :return: None
        """

        # set up regular expression to stop minutes and seconds from exceeding 59
        regExp = QRegExp(r'[_\d]?[_\d]?:[_0-5]?[_\d]?:[_0-5]?[_\d]?', Qt.CaseInsensitive)
        validator = QRegExpValidator(regExp)

        self.leDuration.setInputMask("09\\:99\\:99;_")
        self.leTimestep.setInputMask("09\\:99\\:99;_")
        self.leDuration.setValidator(validator)
        self.leTimestep.setValidator(validator)

    def populateCboFeatures(self) -> None:
        """
        Add feature IDs to combobox
    
        :return: None
        """
    
        self.cboFeatures.clear()
    
        layer = tuflowqgis_find_layer(self.cboInputGIS.currentText())
        if layer is not None:
            iField = self.cboFields.currentIndex()
            if iField > -1:
                atts = [str(f.attribute(iField)) for f in layer.getFeatures()]
                self.cboFeatures.addItems(atts)
            
    def populateCboFields(self) -> None:
        """
        Add field names to combobox
        
        :return: None
        """
        
        self.cboFields.clear()

        layer = tuflowqgis_find_layer(self.cboInputGIS.currentText())
        if layer is not None:
            self.cboFields.addItems(layer.fields().names())
    
    def addGIS(self) -> None:
        """
        Add GIS layer(s) to input catchment file combobox.
        
        :return: None
        """
        
        layers = []
        for id, layer in QgsProject.instance().mapLayers().items():
            if self.isValidLayer(layer):
                if layer.name() not in layers:
                    layers.append(layer.name())
        self.cboInputGIS.clear()
        self.cboInputGIS.addItem('-None-')
        self.cboInputGIS.addItems(layers)
        
    def isValidLayer(self, layer: QgsMapLayer) -> bool:
        """
        Checks if a QgsMapLayer is a valid input layer.
        
        :param layer: QgsMapLayer
        :return: bool
        """
        
        if type(layer) is QgsVectorLayer:
            #if layer.geometryType() == QgsWkbTypes.PolygonGeometry or \
            #        layer.geometryType() == QgsWkbTypes.PointGeometry:
            return True
            
        return False
    
    def applyIcons(self) -> None:
        """
        Sets icons in gui
        
        :return: None
        """

        dir = os.path.dirname(os.path.dirname(__file__))
        fldIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
        addIcon = QgsApplication.getThemeIcon('mActionAdd.svg')
        remIcon = QgsApplication.getThemeIcon('symbologyRemove.svg')
        rf2Icon = QIcon(os.path.join(dir, 'icons', "ReFH2icon.png"))
        
        btnBrs = [self.btnInputXML, self.btnOutfile]
        btnAdd = [self.btnAddRP, self.btnAddDur]
        btnRem = [self.btnRemoveRP, self.btnRemDur]
        
        self.setWindowIcon(rf2Icon)
        for btn in btnBrs:
            btn.setIcon(fldIcon)
        for btn in btnAdd:
            btn.setIcon(addIcon)
        for btn in btnRem:
            btn.setIcon(remIcon)
            
    def toggleSelectAll(self) -> None:
        """
        Select All check box is toggled on / off
        - selects all check boxes or deselects all check boxes
        
        :return: None
        """

        if self.cbSelectAll.checkState() == Qt.PartiallyChecked:
            self.cbSelectAll.setCheckState(Qt.Checked)
        
        select = True if self.cbSelectAll.checkState() == Qt.Checked else False
        
        aris = [1, 2, 5, 10, 30, 50, 75, 100, 200, 1000]
        for ari in aris:
            eval("self.cb{0:04d}y".format(ari)).setChecked(select)

    def reAssessSelectAllCheckBox(self) -> None:
        """
        Updates the check state of the select all checkbox
        based on the new state of the event check boxes.
        """

        aris = [1, 2, 5, 10, 30, 50, 75, 100, 200, 1000]
        checkedAll = []
        for ari in aris:
            checkedAll.append(eval("self.cb{0:04d}y".format(ari)).isChecked())

        if self.cbSelectAll.checkState() == Qt.Unchecked and False not in checkedAll:
            self.cbSelectAll.setCheckState(Qt.Checked)
        elif self.cbSelectAll.checkState() == Qt.PartiallyChecked:
            if True not in checkedAll:
                self.cbSelectAll.setCheckState(Qt.Unchecked)
            elif False not in checkedAll:
                self.cbSelectAll.setCheckState(Qt.Checked)
        elif self.cbSelectAll.checkState() == Qt.Checked:
            if False in checkedAll:
                self.cbSelectAll.setCheckState(Qt.PartiallyChecked)

    def connectEventCheckBoxes(self) -> None:
        """
        Connects all checkboxes so that 'select all' check box
        can change state appropriately
        """

        aris = [1, 2, 5, 10, 30, 50, 75, 100, 200, 1000]
        for ari in aris:
            eval("self.cb{0:04d}y".format(ari)).stateChanged.connect(self.reAssessSelectAllCheckBox)
            eval("self.cb{0:04d}y".format(ari)).stateChanged.connect(self.alignClimateChangeCheckBox)

    def toggleClimateChangeBoxes(self):
        """

        """

        aris = [1, 2, 5, 10, 30, 50, 75, 100, 200, 1000]
        for ari in aris:
            if eval("self.cb{0:04d}y".format(ari)).isChecked():
                eval("self.cb{0:04d}y_CC".format(ari)).setChecked(True)

        for i in range(self.lwRP.count()):
            item = self.lwRP.item(i)
            cb = self.lwRP.itemWidget(item).layout().itemAt(2).widget()
            cb.setChecked(True)

    def toggleClimChangeAllActive(self):
        """
        Selects CC checkboxes for all selected events
        """

        if not self.cbCCAllActive.isChecked():
            return

        self.disconnectClimChangeCheckBoxes()
        self.toggleClimateChangeBoxes()
        self.connectClimChangeCheckBoxes()

    def reAssessAllActiveCheckBox(self):
        """

        """

        if not self.cbCCAllActive.isChecked():
            return

        aris = [1, 2, 5, 10, 30, 50, 75, 100, 200, 1000]
        for ari in aris:
            if eval("self.cb{0:04d}y".format(ari)).isChecked():
                if not eval("self.cb{0:04d}y_CC".format(ari)).isChecked():
                    self.cbCCAllActive.setChecked(False)
                    return

        for i in range(self.lwRP.count()):
            item = self.lwRP.item(i)
            cb = self.lwRP.itemWidget(item).layout().itemAt(2).widget()
            if not cb.isChecked():
                self.cbCCAllActive.setChecked(False)
                return

    def connectClimChangeCheckBoxes(self):
        """

        """

        aris = [1, 2, 5, 10, 30, 50, 75, 100, 200, 1000]
        for ari in aris:
            eval("self.cb{0:04d}y_CC".format(ari)).stateChanged.connect(self.reAssessAllActiveCheckBox)

        for i in range(self.lwRP.count()):
            item = self.lwRP.item(i)
            cb = self.lwRP.itemWidget(item).layout().itemAt(2).widget()
            cb.stateChanged.connect(self.reAssessAllActiveCheckBox)

    def disconnectClimChangeCheckBoxes(self):
        """

        """

        aris = [1, 2, 5, 10, 30, 50, 75, 100, 200, 1000]
        for ari in aris:
            eval("self.cb{0:04d}y_CC".format(ari)).stateChanged.disconnect(self.reAssessAllActiveCheckBox)

        for i in range(self.lwRP.count()):
            item = self.lwRP.item(i)
            cb = self.lwRP.itemWidget(item).layout().itemAt(2).widget()
            cb.stateChanged.connect(self.reAssessAllActiveCheckBox)

    def alignClimateChangeCheckBox(self):
        """

        """

        if not self.cbCCAllActive.isChecked():
            return

        self.toggleClimateChangeBoxes()

    def toggleEngine23Enabled(self):
        """

        """

        enabled = True if self.rbEngine23.isChecked() else False

        # urban area
        self.label_22.setEnabled(enabled)
        self.sbAreaUrban.setEnabled(enabled)

        # climate change heading
        self.cbCCAllActive.setEnabled(enabled)
        self.label_20.setEnabled(enabled)

        aris = [1, 2, 5, 10, 30, 50, 75, 100, 200, 1000]
        for ari in aris:
            eval("self.cb{0:04d}y_CC".format(ari)).setEnabled(enabled)

        for i in range(self.lwRP.count()):
            item = self.lwRP.item(i)
            cb = self.lwRP.itemWidget(item).layout().itemAt(2).widget()
            cb.setEnabled(enabled)

    def getCartesian(self, x):
        """
        Returns EPSG for a cartesian crs for a given x location (longitude)

        :param x: float
        :return: str
        """

        if -12 <= x < -6:
            return 'epsg:32629'
        elif -6 <= x < 0:
            return 'epsg:32630'
        elif 0 <= x <= 6:
            return 'epsg:32631'
        else:
            return None

    def radioButtonClones(self, e = None, button = None):
        """
        Deals with the radio button clones - urban and rural buttons.
        i.e. makes sure they match one another

        :param e: QEvent
        :param button: QRadioButton
        :return: None
        """

        rbs = ['rbUrban', 'rbRural']
        for r in rbs:
            rb = eval('self.{0}'.format(r))
            rbClone = eval('self.{0}Clone'.format(r))
            if rb == button:
                rbClone.setChecked(rb.isChecked())
            elif rbClone == button:
                rb.setChecked(rbClone.isChecked())

    def createLabel(self, text: str, bWrapText: bool = False) -> QLabel:
        """

        :param text: str
        :return: QLabel
        """

        label = QLabel()
        label.setTextFormat(Qt.RichText)
        label.setText(text)
        label.setWordWrap(bWrapText)
        palette = label.palette()
        palette.setColor(QPalette.Foreground, Qt.red)
        font = label.font()
        font.setItalic(True)
        label.setPalette(palette)
        label.setFont(font)

        return label


    def removeWidget(self, layout, widget, msg) -> None:
        """
        Removes widget from layout.

        :param layout: QLayout
        :param widget: QWidget
        :return: None
        """

        flag = (layout, widget, msg)
        self.flags.remove(flag)
        layout.removeWidget(widget)
        widget.deleteLater()
        widget.setParent(None)

    def isDescriptor(self, text=None) -> bool:
        """

        :return: bool
        """

        isDescriptor = False

        t = text
        try:
            if t is None:
                t = ''.join(open(self.leInputXML.text(), "r").readlines())
            if re.findall(r"<fehcdromexporteddescriptors.*>", t, flags=re.IGNORECASE):
                isDescriptor = True
        except:
            pass

        return isDescriptor

    def isPointDescriptor(self, text=None) -> bool:
        """

        :param text: str
        :return: bool
        """

        isPointDescriptor = False

        t = text
        try:
            if t is None:
                t = ''.join(open(self.leInputXML.text(), "r").readlines())
            if re.findall(r"<pointdescriptors.*>", t, flags=re.IGNORECASE):
                isPointDescriptor = True
        except:
            pass

        return isPointDescriptor

    def checkAreaInput(self, e=None, b=None) -> None:
        """

        :param e: QEvent
        :param b: bool isPointDescriptor
        :return: None
        """

        # remove previous messages
        for flag in self.flags[:]:
            if flag[0] is self.verticalLayout_23 or flag[0] is self.horizontalLayout_6:  # input flag
                layout = flag[0]
                widget = flag[1]
                msg = flag[2]
                self.removeWidget(layout, widget, msg)

        isPointDescriptor = b
        if isPointDescriptor is None:
            isPointDescriptor = self.isPointDescriptor()

        # input area - required for point descriptors
        if isPointDescriptor:
            if self.rbUserArea.isChecked():
                if self.sbArea.value() <= 0:
                    msg = "Area Must Be Greater Than Zero For Point Descriptors"
                    label = self.createLabel(msg)
                    self.horizontalLayout_6.insertWidget(self.horizontalLayout_6.count() - 1, label)
                    self.flags.append((self.horizontalLayout_6, label, msg))
            else:
                if self.cboInputGIS.currentText() == '-None-':
                    msg = "No Input GIS Catchment File Specified"
                    label = self.createLabel(msg)
                    self.verticalLayout_23.addWidget(label)
                    self.flags.append((self.verticalLayout_23, label, msg))
                elif tuflowqgis_find_layer(self.cboInputGIS.currentText()) is None:
                    msg = "Input GIS Catchment File Not in Workspace"
                    label = self.createLabel(msg)
                    self.verticalLayout_23.addWidget(label)
                    self.flags.append((self.verticalLayout_23, label, msg))
                elif tuflowqgis_find_layer(
                        self.cboInputGIS.currentText()).geometryType() != QgsWkbTypes.PolygonGeometry:
                    msg = "Can Only Calculate Area From Region GIS Layer"
                    label = self.createLabel(msg)
                    self.verticalLayout_23.addWidget(label)
                    self.flags.append((self.verticalLayout_23, label, msg))

    def inputCatchmentChanged(self, e=None) -> None:
        """
        Checks input catchment is a point or catchment descriptor.
        If point descriptor, needs a catchment area input.

        Also checks to see if it is a valid descriptor file.

        :param e: QEvent
        :return: None
        """

        # remove previous flags
        for flag in self.flags[:]:
            if flag[0] is self.verticalLayout_22:  # input flag
                layout = flag[0]
                widget = flag[1]
                msg = flag[2]
                self.removeWidget(layout, widget, msg)

        fo = None
        try:
            fo = ''.join(open(self.leInputXML.text(), "r").readlines())
        except IOError:
            msg = "Input XML File Does Not Exist"
            label = self.createLabel(msg)
            self.verticalLayout_22.addWidget(label)
            self.flags.append((self.verticalLayout_22, label, msg))
        except:
            msg = "Unexpected Error Reading Input XML File"
            label = self.createLabel(msg)
            self.verticalLayout_22.addWidget(label)
            self.flags.append((self.verticalLayout_22, label, msg))

        isDescriptor = self.isDescriptor(fo)
        isPointDescriptor = self.isPointDescriptor(fo)

        if not isDescriptor:
            # add red text
            msg = "Input XML Not Recognised"
            label = self.createLabel(msg)
            self.verticalLayout_22.addWidget(label)
            self.flags.append((self.verticalLayout_22, label, msg))


        # input area - required for point descriptors
        self.checkAreaInput(b=isPointDescriptor)

    def durationChanged(self, e=None) -> None:
        """

        :param e: QEvent
        :return: None
        """

        # remove previous flags
        for flag in self.flags[:]:
            if flag[0] is self.horizontalLayout_8 or flag[0] is self.horizontalLayout_7 or \
                    flag[0] is self.verticalLayout_10:  # input flag
                layout = flag[0]
                widget = flag[1]
                msg = flag[2]
                self.removeWidget(layout, widget, msg)

        # duration and timestep
        if self.leDuration.text() != '::':
            dur = convertFormattedTimeToTime(self.leDuration.text()) * 60. * 60.
            if not dur:
                msg = "Duration Must be Greater Than Zero"
                label = self.createLabel(msg, True)
                self.verticalLayout_10.insertWidget(self.verticalLayout_10.count() - 2, label)
                self.flags.append((self.verticalLayout_10, label, msg))
            if self.leTimestep.text() == '::':
                msg = "Timestep Must Be Specified if Duration is Specified"
                label = self.createLabel(msg, True)
                self.verticalLayout_10.insertWidget(self.verticalLayout_10.count() - 2, label)
                self.flags.append((self.verticalLayout_10, label, msg))
        if self.leTimestep.text() != '::':
            ts = convertFormattedTimeToTime(self.leTimestep.text()) * 60. * 60.
            if not ts:
                msg = "Timestep Must be Greater Than Zero"
                label = self.createLabel(msg, True)
                self.verticalLayout_10.insertWidget(self.verticalLayout_10.count() - 2, label)
                self.flags.append((self.verticalLayout_10, label, msg))
            if self.leDuration.text() == '::':
                msg = "Duration Must Be Specified if Timestep is Specified"
                label = self.createLabel(msg, True)
                self.verticalLayout_10.insertWidget(self.verticalLayout_10.count() - 2, label)
                self.flags.append((self.verticalLayout_10, label, msg))
        if self.leDuration.text() != '::' and self.leTimestep.text() != '::':
            dur = convertFormattedTimeToTime(self.leDuration.text()) * 60. * 60.
            ts = convertFormattedTimeToTime(self.leTimestep.text()) * 60. * 60.
            if dur and ts:
                if dur % ts > 0:
                    msg = "Duration Must be a Multiple of Timestep"
                    label = self.createLabel(msg, True)
                    self.verticalLayout_10.insertWidget(self.verticalLayout_10.count() - 2, label)
                    self.flags.append((self.verticalLayout_10, label, msg))
                nTs = dur / ts
                if nTs % 2 == 0:
                    msg = "There Must be an Odd Number of Timesteps (Duration / Timestep = Odd Number) " \
                          "Calculated No. of Timesteps: {0:.0f}".format(nTs)
                    label = self.createLabel(msg, True)
                    self.verticalLayout_10.insertWidget(self.verticalLayout_10.count() - 2, label)
                    self.flags.append((self.verticalLayout_10, label, msg))

    def rainfallOutputChanged(self, e=None) -> None:
        """
        Rainfall output changed - error checking

        :param e: QEvent
        :return: None
        """

        # remove previous flags
        for flag in self.flags[:]:
            if flag[0] is self.verticalLayout_21:
                layout = flag[0]
                widget = flag[1]
                msg = flag[2]
                self.removeWidget(layout, widget, msg)

        # check for new flags
        if self.gbOutHydrograph.isChecked():
            if not self.rbGrossRainfall.isChecked() and not self.rbNetRainfall.isChecked():
                msg = "Must Specify at least one Rainfall Output Type"
                label = self.createLabel(msg, True)
                self.verticalLayout_21.insertWidget(self.verticalLayout_21.count() - 3, label)
                self.flags.append((self.verticalLayout_21, label, msg))

    def hydrographOutputChanged(self, e=None) -> None:
        """
        Rainfall output changed - error checking

        :param e: QEvent
        :return: None
        """

        # remove previous flags
        for flag in self.flags[:]:
            if flag[0] is self.verticalLayout_13:
                layout = flag[0]
                widget = flag[1]
                msg = flag[2]
                self.removeWidget(layout, widget, msg)

        # check for new flags
        if self.gbOutHydrograph.isChecked():
            if not self.rbDirectRunoff.isChecked() and not self.rbBaseFlow.isChecked() \
                    and not self.rbTotalRunoff.isChecked():
                msg = "Must Specify at least one Runoff Output Type"
                label = self.createLabel(msg, True)
                self.verticalLayout_13.insertWidget(self.verticalLayout_13.count() - 3, label)
                self.flags.append((self.verticalLayout_13, label, msg))

    def outputToTuflowGisToggled_Rainfall(self, e=None) -> None:
        """
        Output to TUFLOW GIS changed - error checking

        :param e: QEvent
        :return: None
        """

        # remove previous flags
        for flag in self.flags[:]:
            if flag[0] is self.verticalLayout_29:
                layout = flag[0]
                widget = flag[1]
                msg = flag[2]
                self.removeWidget(layout, widget, msg)

        # check for new flags
        if self.gbOutRainfall.isChecked() and self.gbRainToGis.isChecked():
            if self.cboInputGIS.currentText() == '-None-':
                msg = "Must Specify Input GIS (Catchment) Layer to Output To TUFLOW GIS"
                label = self.createLabel(msg, True)
                self.verticalLayout_29.insertWidget(self.verticalLayout_29.count(), label)
                self.flags.append((self.verticalLayout_29, label, msg))
                return
            if self.rb2dRf.isChecked() and \
                    tuflowqgis_find_layer(self.cboInputGIS.currentText()).geometryType() != QgsWkbTypes.PolygonGeometry:
                msg = "Input GIS (Catchment) Layer Must be a Polygon for 2d_rf output"
                label = self.createLabel(msg, True)
                self.verticalLayout_29.insertWidget(self.verticalLayout_29.count(), label)
                self.flags.append((self.verticalLayout_29, label, msg))
                return
            if self.rb2dSaRf.isChecked() and \
                    tuflowqgis_find_layer(self.cboInputGIS.currentText()).geometryType() != QgsWkbTypes.PolygonGeometry:
                msg = "Input GIS (Catchment) Layer Must be a Polygon for 2d_sa_rf output"
                label = self.createLabel(msg, True)
                self.verticalLayout_29.insertWidget(self.verticalLayout_29.count(), label)
                self.flags.append((self.verticalLayout_29, label, msg))
                return

    def outputToTuflowGisToggled_Runoff(self, e=None) -> None:
        """
        Output to TUFLOW GIS changed - error checking

        :param e: QEvent
        :return: None
        """

        # remove previous flags
        for flag in self.flags[:]:
            if flag[0] is self.verticalLayout_30:
                layout = flag[0]
                widget = flag[1]
                msg = flag[2]
                self.removeWidget(layout, widget, msg)

        # check for new flags
        if self.gbOutHydrograph.isChecked() and self.gbHydToGis.isChecked():
            if self.cboInputGIS.currentText() == '-None-' or tuflowqgis_find_layer(self.cboInputGIS.currentText()) is None:
                msg = "Must Specify Input GIS (Catchment) Layer to Output To TUFLOW GIS"
                label = self.createLabel(msg, True)
                self.verticalLayout_30.insertWidget(self.verticalLayout_30.count(), label)
                self.flags.append((self.verticalLayout_30, label, msg))
                return
            if self.rb2dSa.isChecked() and \
                    tuflowqgis_find_layer(self.cboInputGIS.currentText()).geometryType() != QgsWkbTypes.PolygonGeometry:
                msg = "Input GIS (Catchment) Layer Must be a Polygon for 2d_sa output"
                label = self.createLabel(msg, True)
                self.verticalLayout_30.insertWidget(self.verticalLayout_30.count(), label)
                self.flags.append((self.verticalLayout_30, label, msg))
                return
            if self.rb2dBc.isChecked() and \
                    tuflowqgis_find_layer(self.cboInputGIS.currentText()).geometryType() != QgsWkbTypes.LineGeometry:
                msg = "Input GIS (Catchment) Layer Must be a Line / Polyline for 2d_bc output"
                label = self.createLabel(msg, True)
                self.verticalLayout_30.insertWidget(self.verticalLayout_30.count(), label)
                self.flags.append((self.verticalLayout_30, label, msg))
                return
            if self.rb1dBc.isChecked() and \
                    tuflowqgis_find_layer(self.cboInputGIS.currentText()).geometryType() == QgsWkbTypes.LineGeometry:
                msg = "Input GIS (Catchment) Layer Cannot be a Line / Polyline for 1d_bc output"
                label = self.createLabel(msg, True)
                self.verticalLayout_30.insertWidget(self.verticalLayout_30.count(), label)
                self.flags.append((self.verticalLayout_30, label, msg))
                return

    def check(self) -> None:
        """
        Checks input for silly mistakes or omissions as best as can
        at this stage.

        If passes all checks, will start run function :)
        
        :return: None
        """

        # start with already found flags
        for flag in self.flags:
            msg = flag[2]
            QMessageBox.critical(self, "ReFH2 to TUFLOW", msg)
            return

        # input catchment descriptor / locator - required
        if not self.leInputXML.text():
            QMessageBox.critical(self, "ReFH2 to TUFLOW", "No Catchment Descriptor Input Locator File Specified")
            return
        if not os.path.exists(self.leInputXML.text()):
            QMessageBox.critical(self, "ReFH2 to TUFLOW", "Catchment Descriptor Input Locator File Does Not Exist")
            return

        # Return Period - at least one return period and must be between 1 and 1000 year inclusive
        rps = []
        aris = [1, 2, 5, 10, 30, 50, 75, 100, 200, 1000]
        for ari in aris:
            cb = eval("self.cb{0:04d}y".format(ari))
            if cb.isChecked():
                rps.append(ari)
        for i in range(self.lwRP.count()):
            item = self.lwRP.item(i)
            widget = self.lwRP.itemWidget(item)
            labelRp = widget.layout().itemAt(0).widget()
            rp = labelRp.text().strip('year').strip()
            rps.append(rp)
            if not 1 <= int(rp) <= 1000:
                QMessageBox.critical(self, "ReFH2 to TUFLOW", "Return Period Not Valid: {0}".format(rp))
                return
            else:
                rps.append(rp)
        if not rps:
            QMessageBox.critical(self, "ReFH2 to TUFLOW", "No Return Period(s) Selected")
            return

        if not self.gbOutRainfall.isChecked() and not self.gbOutHydrograph.isChecked():
            QMessageBox.critical(self, "ReFH2 to TUFLOW", "No Output (Rainfall or Hydrograph) Selected")
            return

        # output
        #if self.gbOutRainfall.isChecked() and self.gbRainToGis.isChecked():
        #    if not self.cboInputGIS.currentText() or not self.cboFields.currentText() \
        #            or not self.cboFeatures.currentText():
        #        QMessageBox.critical(self, "ReFH2 to TUFLOW", "Must Specify Input GIS Layer to Output To TUFLOW GIS")
        #        return
        #    if self.rb2dRf.isChecked() and \
        #            tuflowqgis_find_layer(self.cboInputGIS.currentText()).geometryType() != QgsWkbTypes.PolygonGeometry:
        #        QMessageBox.critical(self, "ReFH2 to TUFLOW", "Must Use Region GIS Layer to Output 2d_rf")
        #        return
        #    if self.rb2dSaRf.isChecked() and \
        #            tuflowqgis_find_layer(self.cboInputGIS.currentText()).geometryType() != QgsWkbTypes.PolygonGeometry:
        #        QMessageBox.critical(self, "ReFH2 to TUFLOW", "Must Use Region GIS Layer to Output 2d_sa_rf")
        #        return
        #if self.gbOutHydrograph.isChecked() and self.gbHydToGis.isChecked():
        #    #if not self.cboInputGIS.currentText() or not self.cboFields.currentText() \
        #    #        or not self.cboFeatures.currentText():
        #    #    QMessageBox.critical(self, "ReFH2 to TUFLOW", "Must Specify Input GIS Layer to Output To TUFLOW GIS")
        #    #    return
        #    if self.rb2dSa.isChecked() and \
        #            tuflowqgis_find_layer(self.cboInputGIS.currentText()).geometryType() != QgsWkbTypes.PolygonGeometry:
        #        QMessageBox.critical(self, "ReFH2 to TUFLOW", "Must Use Region GIS Layer to Output 2d_sa")
        #        return
        #    if self.rb2dBc.isChecked() and \
        #            tuflowqgis_find_layer(self.cboInputGIS.currentText()).geometryType() != QgsWkbTypes.LineGeometry:
        #        QMessageBox.critical(self, "ReFH2 to TUFLOW", "Must Use Line GIS Layer to Output 2d_bc")
        #        return
        #    if self.rb1dBc.isChecked() and \
        #            tuflowqgis_find_layer(self.cboInputGIS.currentText()).geometryType() == QgsWkbTypes.LineGeometry:
        #        QMessageBox.critical(self, "ReFH2 to TUFLOW", "Cannot Use Line GIS Layer to Output 1d_bc")
        #        return
        if self.rbQgisArea.isChecked():
            # if using spherical coords, check it can be converted to cartesian
            layer = tuflowqgis_find_layer(self.cboInputGIS.currentText())
            crs = layer.sourceCrs()
            layerUnits = crs.mapUnits()
            if layerUnits == QgsUnitTypes.DistanceDegrees:
                fid = self.cboFeatures.currentIndex()
                fids = {x.id(): x for x in layer.getFeatures()}
                feat = fids[fid]
                x = feat.geometry().centroid().asPoint()[0]
                if self.getCartesian(x) is None:
                    QMessageBox.critical(self, "ReFH2 to TUFLOW", "Difficulty Converting Degrees to Meters... "
                                                                  "Please Double Check Projection and Location"
                                                                  "of Input GIS Layer and Workspace")
                    return

        self.run(__VK__)

    def qgisDisconnect(self):
        """disconnect signals"""

        try:
            self.leInputXML.editingFinished.disconnect(self.inputCatchmentChanged)
        except:
            pass
        try:
            self.rbUserArea.toggled.disconnect(self.checkAreaInput)
        except:
            pass
        try:
            self.sbArea.valueChanged.disconnect(self.checkAreaInput)
        except:
            pass
        try:
            self.cboInputGIS.currentIndexChanged.disconnect(self.checkAreaInput)
        except:
            pass
        try:
            self.leDuration.editingFinished.disconnect(self.durationChanged)
        except:
            pass
        try:
            self.leTimestep.editingFinished.disconnect(self.durationChanged)
        except:
            pass
        try:
            self.gbOutRainfall.toggled.disconnect(self.rainfallOutputChanged)
        except:
            pass
        try:
            self.rbGrossRainfall.toggled.disconnect(self.rainfallOutputChanged)
        except:
            pass
        try:
            self.rbNetRainfall.toggled.disconnect(self.rainfallOutputChanged)
        except:
            pass
        try:
            self.gbOutHydrograph.toggled.disconnect(self.hydrographOutputChanged)
        except:
            pass
        try:
            self.rbDirectRunoff.toggled.disconnect(self.hydrographOutputChanged)
        except:
            pass
        try:
            self.rbBaseFlow.toggled.disconnect(self.hydrographOutputChanged)
        except:
            pass
        try:
            self.rbTotalRunoff.toggled.disconnect(self.hydrographOutputChanged)
        except:
            pass
        try:
            self.gbRainToGis.toggled.disconnect(self.outputToTuflowGisToggled_Rainfall)
        except:
            pass
        try:
            self.cboInputGIS.currentIndexChanged.disconnect(self.outputToTuflowGisToggled_Rainfall)
        except:
            pass
        try:
            self.gbOutRainfall.toggled.disconnect(self.outputToTuflowGisToggled_Rainfall)
        except:
            pass
        try:
            self.rb2dRf.toggled.disconnect(self.outputToTuflowGisToggled_Rainfall)
        except:
            pass
        try:
            self.gbHydToGis.toggled.disconnect(self.outputToTuflowGisToggled_Runoff)
        except:
            pass
        try:
            self.cboInputGIS.currentIndexChanged.disconnect(self.outputToTuflowGisToggled_Runoff)
        except:
            pass
        try:
            self.gbOutHydrograph.toggled.disconnect(self.outputToTuflowGisToggled_Runoff)
        except:
            pass
        try:
            self.rb2dSa.toggled.disconnect(self.outputToTuflowGisToggled_Runoff)
        except:
            pass
        try:
            self.rb1dBc.toggled.disconnect(self.outputToTuflowGisToggled_Runoff)
        except:
            pass
        try:
            self.rb2dBc.toggled.disconnect(self.outputToTuflowGisToggled_Runoff)
        except:
            pass
        try:
            QgsProject.instance().layersAdded.disconnect(self.addGIS)
        except:
            pass
        try:
            QgsProject.instance().layersRemoved.disconnect(self.addGIS)
        except:
            pass
        try:
            self.cboInputGIS.currentIndexChanged.disconnect(self.populateCboFields)
        except:
            pass
        try:
            self.cboInputGIS.currentIndexChanged.disconnect(self.populateCboFeatures)
        except:
            pass
        try:
            self.cboFields.currentIndexChanged.disconnect(self.populateCboFeatures)
        except:
            pass
        try:
            self.cbSelectAll.clicked.disconnect(self.toggleSelectAll)
        except:
            pass
        try:
            self.btnAddRP.clicked.disconnect(self.addReturnPeriod)
        except:
            pass
        try:
            self.btnRemoveRP.clicked.disconnect(self.removeReturnPeriods)
        except:
            pass
        try:
            self.btnAddDur.clicked.disconnect(self.addDurTimestep)
        except:
            pass
        try:
            self.btnRemDur.clicked.disconnect(self.removeDurTimestep)
        except:
            pass
        try:
            self.pbRun.clicked.disconnect(self.check)
        except:
            pass
        try:
            self.btnInputXML.clicked.disconnect()
        except:
            pass
        try:
            self.btnOutfile.clicked.disconnect()
        except:
            pass


def tuflowqgis_find_layer(layer_name, **kwargs):
    search_type = kwargs['search_type'] if 'search_type' in kwargs.keys() else 'name'
    return_type = kwargs['return_type'] if 'return_type' in kwargs else 'layer'

    for name, search_layer in QgsProject.instance().mapLayers().items():
        if search_type.lower() == 'name':
            if search_layer.name() == layer_name:
                if return_type == 'layer':
                    return search_layer
                elif return_type == 'layerid':
                    return name
                elif return_type == 'name':
                    return search_layer.name()
                else:
                    return name
        elif search_type.lower() == 'layerid':
            if name == layer_name:
                if return_type == 'layer':
                    return search_layer
                elif return_type == 'layerid':
                    return name
                elif return_type == 'name':
                    return search_layer.name()
                else:
                    return name

        elif search_type.lower() == 'datasource':
            if search_layer.dataProvider().dataSourceUri() == layer_name:
                if return_type == 'layer':
                    return search_layer
                elif return_type == 'layerid':
                    return name
                elif return_type == 'name':
                    return search_layer.name()
                else:
                    return name

    return None


def browse(parent: QWidget = None, browseType: str = '', key: str = "TUFLOW",
           dialogName: str = "TUFLOW", fileType: str = "ALL (*)",
           lineEdit=None, icon: QIcon = None, action=None, allowDuplicates=True, default_filename=None) -> None:
    """
    Browse folder directory

    :param parent: QWidget Parent widget
    :param type: str browse type 'folder' or 'file'
    :param key: str settings key
    :param dialogName: str dialog box label
    :param fileType: str file extension e.g. "AVI files (*.avi)"
    :param lineEdit: QLineEdit to be updated by browsing
    :param icon: QIcon dialog window icon
    :param action: lambda function
    :param bool: noDuplicates - if adding to list widget, don't allow duplicate entries
    :return: str
    """

    settings = QSettings()
    lastFolder = settings.value(key)

    startDir = os.getcwd()
    if lineEdit is not None:
        if type(lineEdit) is QLineEdit:
            if not re.findall(r'^<.*>$', lineEdit.text()) and lineEdit.text():
                startDir = lineEdit.text()
        elif type(lineEdit) is QComboBox:
            if not re.findall(r'^<.*>$', lineEdit.currentText()) and lineEdit.currentText():
                startDir = lineEdit.currentText()

    if lastFolder and startDir == os.getcwd():  # if outFolder no longer exists, work backwards in directory until find one that does
        if os.path.exists(os.path.splitdrive(lastFolder)[0]):
            pattern = r'[a-z]\:\\$'  # windows root drive directory
            loop_limit = 100
            loop_count = 0
            while lastFolder:
                if os.path.exists(lastFolder):
                    startDir = lastFolder
                    break
                elif not lastFolder:
                    startDir = lastFolder
                    break
                elif re.findall(pattern, lastFolder, re.IGNORECASE):
                    startDir = ''
                    break
                elif loop_count > loop_limit:
                    startDir = ''
                    break
                else:
                    lastFolder = os.path.dirname(lastFolder)
                    loop_count += 1
    if default_filename:
        startDir = os.path.join(startDir, default_filename)
    dialog = QFileDialog(parent, dialogName, startDir, fileType)
    f = []
    if icon is not None:
        dialog.setWindowIcon(icon)
    if browseType == 'existing folder':
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        dialog.setViewMode(QFileDialog.Detail)
    # f = QFileDialog.getExistingDirectory(parent, dialogName, startDir)
    elif browseType == 'existing file':
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setViewMode(QFileDialog.Detail)
    # f = QFileDialog.getOpenFileName(parent, dialogName, startDir, fileType)[0]
    elif browseType == 'existing files':
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setViewMode(QFileDialog.Detail)
    # f = QFileDialog.getOpenFileNames(parent, dialogName, startDir, fileType)[0]
    elif browseType == 'output file':
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setViewMode(QFileDialog.Detail)
    elif browseType == 'output database':
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setViewMode(QFileDialog.Detail)
        dialog.setOptions(QFileDialog.DontConfirmOverwrite)
    # f = QFileDialog.getSaveFileName(parent, dialogName, startDir, fileType)[0]
    else:
        return
    if dialog.exec():
        f = dialog.selectedFiles()
    if f:
        if type(f) is list:
            fs = ''
            for i, a in enumerate(f):
                if i == 0:
                    value = a.replace('/', os.sep).replace('\\', os.sep)
                    fs += a.replace('/', os.sep).replace('\\', os.sep)
                else:
                    fs += ';;' + a.replace('/', os.sep).replace('\\', os.sep)
            f = fs
        else:
            f = f.replace('/', os.sep).replace('\\', os.sep)
            value = f
        f = re.sub(r'[\\/]', re.escape(os.sep), f)  # os slashes
        settings.setValue(key, value)
        if lineEdit is not None:
            if type(lineEdit) is QLineEdit:
                lineEdit.setText(f)
            elif type(lineEdit) is QComboBox:
                lineEdit.setCurrentText(f)
            elif type(lineEdit) is QTableWidgetItem:
                lineEdit.setText(f)
            elif type(lineEdit) is QModelIndex:
                lineEdit.model().setData(lineEdit, f, Qt.EditRole)
            elif type(lineEdit) is QListWidget:
                items = [lineEdit.item(x).text() for x in range(lineEdit.count())]
                for f2 in f.split(';;'):
                    if not allowDuplicates:
                        if f2 not in items:
                            lineEdit.addItem(f2)
                    else:
                        lineEdit.addItem(f2)
                for i in range(lineEdit.count()):
                    item = lineEdit.item(i)
                    if item.text() in f.split(';;'):
                        item.setSelected(True)
        else:
            if browseType == 'existing files':
                return f.split(';;')
            else:
                return f

        if action is not None:
            action()


def convertFormattedTimeToTime(formatted_time, hour_padding=2, unit='h'):
    """
    Converts formatted time hh:mm:ss.ms to time (hours or seconds)

    :param formatted_time: str
    :return: float
    """

    t = formatted_time.split(':')
    if len(t) < 3:
        return 0
    h = int(t[0]) if t[0] != '' else 0
    m = int(t[1]) if t[1] != '' else 0
    s = float(t[2]) if t[2] != '' else 0

    d = timedelta(hours=h, minutes=m, seconds=s)

    if unit == 's':
        return d.total_seconds()
    else:
        return d.total_seconds() / 3600


def makeDir(path: str) -> bool:
    """
    Makes directory - will brute force make a directory

    :param path: str full path to dir
    :return: bool
    """

    # make sure separators are in
    # operating system format
    ospath = path.replace("/", os.sep)
    path_comp = ospath.split(os.sep)

    # work out where directories
    # need to be made
    i = 0
    j = len(path_comp) + 1
    testpath = os.sep.join(path_comp)
    while not os.path.exists(testpath):
        i += 1
        testpath = os.sep.join(path_comp[:j - i])
        if not testpath:
            return False

    # now work in reverse and create all
    # required directories
    for k in range(i - 1):
        i -= 1
        try:
            os.mkdir(os.sep.join(path_comp[:j - i]))
        except FileNotFoundError:
            return False
        except OSError:
            return False

    return True


def convertFormattedTimeToFormattedTime(formatted_time: str, return_format: str = '{0:02d}:{1:02d}:{2:02.0f}') -> str:
    """
    Converts formatted time hh:mm:ss.ms to another formatted time string. Benefit is that it can
    take non digit characters e.g. '_'

    :param formatted_time: str
    :param return_format: str format of the return time string
    :return: str
    """

    t = formatted_time.split(':')
    h = int(t[0]) if t[0] != '' else 0
    m = int(t[1]) if t[1] != '' else 0
    s = float(t[2]) if t[2] != '' else 0

    return return_format.format(h, m, s)
