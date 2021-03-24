import os, sys
import numpy as np
from qgis.core import (QgsApplication, QgsMapLayer, QgsVectorLayer,
                       QgsProject, QgsWkbTypes, QgsUnitTypes)
import processing
from qgis.gui import QgisInterface
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QRegExpValidator, QPalette
from PyQt5.QtWidgets import (QDockWidget, QLineEdit, QFileDialog,
                             QComboBox, QMessageBox, QLabel)
from tuflow.forms.scs_dock import Ui_scs
from .engine import SCS
from tuflow.tuflowqgis_library import (tuflowqgis_find_layer, browse, makeDir)



class SCSDock(QDockWidget, Ui_scs):
    """ Class for SCS to TUFLOW dialog / dock. """
    
    def __init__(self, iface: QgisInterface) -> None:
        QDockWidget.__init__(self)
        self.setupUi(self)
        self.iface = iface
        
        self.applyIcons()
        self.addGis()

        # input checking - add red text if an error is flagged
        self.flags = []
        QgsProject.instance().layersAdded.connect(self.addGis)
        QgsProject.instance().layersRemoved.connect(self.addGis)
        dir = os.path.dirname(os.path.dirname(__file__))
        scsIcon = QIcon(os.path.join(dir, 'icons', "CNicon.png"))

        self.cboLocation.currentIndexChanged.connect(self.prefillCCRaise)
        self.cbSelectAllEvents.clicked.connect(self.toggleSelectAll)
        self.cbSelectAllEventsCC.clicked.connect(self.toggleSelectAllCC)
        self.le002YearDepth.editingFinished.connect(self.calculateDepth002Year)
        self.le005YearDepth.editingFinished.connect(self.calculateDepth005Year)
        self.le010YearDepth.editingFinished.connect(self.calculateDepth010Year)
        self.le020YearDepth.editingFinished.connect(self.calculateDepth020Year)
        self.le050YearDepth.editingFinished.connect(self.calculateDepth050Year)
        self.le100YearDepth.editingFinished.connect(self.calculateDepth100Year)
        self.le002YearDepthCC.editingFinished.connect(self.calculateDepth002YearCC)
        self.le005YearDepthCC.editingFinished.connect(self.calculateDepth005YearCC)
        self.le010YearDepthCC.editingFinished.connect(self.calculateDepth010YearCC)
        self.le020YearDepthCC.editingFinished.connect(self.calculateDepth020YearCC)
        self.le050YearDepthCC.editingFinished.connect(self.calculateDepth050YearCC)
        self.le100YearDepthCC.editingFinished.connect(self.calculateDepth100YearCC)
        self.gbManualApproach.clicked.connect(self.checkManualOnly)
        self.gbGisApproach.clicked.connect(self.checkGisOnly)
        self.cboInputPolygons.currentIndexChanged.connect(self.populateGisFields)
        self.cboIdField.currentIndexChanged.connect(self.collectCatchIdGis)
        self.cboCnField.currentIndexChanged.connect(self.collectCnGis)
        self.cboAreaPerField.currentIndexChanged.connect(self.collectAreaPerGis)
        self.cboAreaPerCCField.currentIndexChanged.connect(self.collectAreaPerCCGis)
        self.cboAreaImp1Field.currentIndexChanged.connect(self.collectAreaImp1Gis)
        self.cboAreaImp1CCField.currentIndexChanged.connect(self.collectAreaImp1CCGis)
        self.cboAreaImp2Field.currentIndexChanged.connect(self.collectAreaImp2Gis)
        self.cboAreaImp2CCField.currentIndexChanged.connect(self.collectAreaImp2CCGis)
        self.cboTpTcField.currentIndexChanged.connect(self.collectTpTcGis)
        self.cboCField.currentIndexChanged.connect(self.collectCGis)
        self.cboLengthField.currentIndexChanged.connect(self.collectLengthGis)
        self.cboSlopeField.currentIndexChanged.connect(self.collectSlopeGis)
        # self.rbCGis.clicked.connect(self.activateCField)
        self.cbTpCheck.clicked.connect(self.checkTpOnly)
        self.cbTcCheck.clicked.connect(self.checkTcOnly)
        self.btnOutput.clicked.connect(lambda: browse(self, "existing folder", "TUFLOW/scs_outfile", "SCS Output Folder",
                                                    "", self.leOutput, scsIcon))
        self.pbRun.clicked.connect(self.check)

    def applyIcons(self) -> None:
        """ Set icons in gui. """

        dir = os.path.dirname(os.path.dirname(__file__))
        fldIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
        scsIcon = QIcon(os.path.join(dir, 'icons', "CNicon.png"))

        btnBrs = [self.btnOutput]

        self.setWindowIcon(scsIcon)
        for btn in btnBrs:
            btn.setIcon(fldIcon)

    def addGis(self) -> None:
        """ Add GIS layer(s) to input catchment files combo boxes. """

        layers = []
        for id, layer in QgsProject.instance().mapLayers().items():
            if self.isValidLayer(layer):
                if layer.name() not in layers:
                    layers.append(layer.name())
        self.cboInputPolygons.clear()
        self.cboInputPolygons.addItem('- None -')
        self.cboInputPolygons.addItems(layers)
        self.cboInputPolylines.clear()
        self.cboInputPolylines.addItem('- None -')
        self.cboInputPolylines.addItems(layers)
        self.cboInputDem.clear()
        self.cboInputDem.addItem('- None -')
        self.cboInputDem.addItems(layers)

    def isValidLayer(self, layer: QgsMapLayer) -> bool:
        """ Check if a QgsMapLayer is a valid input layer. """

        if type(layer) is QgsVectorLayer:
            return True
        return False

    def toggleSelectAll(self) -> None:
        """ Select or deselect All check boxes when toggled on / off. """

        select = True if self.cbSelectAllEvents.isChecked() else False
        aris = [2, 5, 10, 20, 50, 100]
        for ari in aris:
            eval(f'self.cb{ari:03d}Year').setChecked(select)

    def toggleSelectAllCC(self) -> None:
        """ Select or deselect All CC check boxes when toggled on / off. """

        selectCC = True if self.cbSelectAllEventsCC.isChecked() else False
        aris = [2, 5, 10, 20, 50, 100]
        for ari in aris:
            eval(f'self.cb{ari:03d}YearCC').setChecked(selectCC)

    def createEventsList(self) -> list:
        """ Create list of events based on what is checked in the QGIS tool.
            :return: events + events_cc
        """

        events = []
        eventsCC = []
        aris = [2, 5, 10, 20, 50, 100]
        for ari in aris:
            event = eval(f'self.cb{ari:03d}Year')
            if event.isChecked():
                ariString = f'{ari:03d}yr'
                events.append(ariString)
            eventCC = eval(f'self.cb{ari:03d}YearCC')
            if eventCC.isChecked():
                ariStringCC = f'{ari:03d}yrCC'
                eventsCC.append(ariStringCC)

        return events + eventsCC

    def prefillCCRaise(self) -> None:
        """ Prefill percentage of raise for climate change based on location. """

        if self.cboLocation.currentText() == 'Auckland Region (TP108)':
            self.le002YearRaiseCC.setText('9.0')
            self.le005YearRaiseCC.setText('11.3')
            self.le010YearRaiseCC.setText('13.2')
            self.le020YearRaiseCC.setText('15.1')
            self.le050YearRaiseCC.setText('16.8')
            self.le100YearRaiseCC.setText('16.8')
        else:
            self.le002YearRaiseCC.setText('')
            self.le005YearRaiseCC.setText('')
            self.le010YearRaiseCC.setText('')
            self.le020YearRaiseCC.setText('')
            self.le050YearRaiseCC.setText('')
            self.le100YearRaiseCC.setText('')

    def calculateDepth(self, years, now_or_CC) -> None:
        """ Calculate climate change depth based on depth and CC raise. """

        controls = {
            2: (self.le002YearDepth, self.le002YearRaiseCC, self.le002YearDepthCC),
            5: (self.le005YearDepth, self.le005YearRaiseCC, self.le005YearDepthCC),
            10: (self.le010YearDepth, self.le010YearRaiseCC, self.le010YearDepthCC),
            20: (self.le020YearDepth, self.le020YearRaiseCC, self.le020YearDepthCC),
            50: (self.le050YearDepth, self.le050YearRaiseCC, self.le050YearDepthCC),
            100: (self.le100YearDepth, self.le100YearRaiseCC, self.le100YearDepthCC)
        }
        depth, percentCC, depthCC = controls[years]
        try:
            if now_or_CC == 'now':
                depth_result = round(float(depth.text())+(float(depth.text())*float(percentCC.text())*0.01), 2)
            else:
                depth_result = round(float(depthCC.text())/((float(percentCC.text()))+100)*100, 2)
        except ValueError:
            depth_result = ''
        if now_or_CC == 'now':
            depthCC.setText(str(depth_result))
        else:
            depth.setText(str(depth_result))

    def calculateDepth002Year(self) -> None:
        self.calculateDepth(2, 'now')

    def calculateDepth005Year(self) -> None:
        self.calculateDepth(5, 'now')

    def calculateDepth010Year(self) -> None:
        self.calculateDepth(10, 'now')

    def calculateDepth020Year(self) -> None:
        self.calculateDepth(20, 'now')

    def calculateDepth050Year(self) -> None:
        self.calculateDepth(50, 'now')

    def calculateDepth100Year(self) -> None:
        self.calculateDepth(100, 'now')

    def calculateDepth002YearCC(self) -> None:
        self.calculateDepth(2, 'CC')

    def calculateDepth005YearCC(self) -> None:
        self.calculateDepth(5, 'CC')

    def calculateDepth010YearCC(self) -> None:
        self.calculateDepth(10, 'CC')

    def calculateDepth020YearCC(self) -> None:
        self.calculateDepth(20, 'CC')

    def calculateDepth050YearCC(self) -> None:
        self.calculateDepth(50, 'CC')

    def calculateDepth100YearCC(self) -> None:
        self.calculateDepth(100, 'CC')

    def checkManualOnly(self) -> None:
        """ Check only one box - Manual or GIS Approach. """

        if self.gbManualApproach.isChecked()and self.gbGisApproach.isChecked():
                self.gbGisApproach.setChecked(False)

    def checkGisOnly(self) -> None:
        """ Check only one box - Manual or GIS Approach. """

        if self.gbManualApproach.isChecked()and self.gbGisApproach.isChecked():
                self.gbManualApproach.setChecked(False)

    def unitHydrographOrdinates(self) -> np.array:
        """ Create unit hydrograph ordinates.
            :return: uhOrdinates
        """
        uhOrdinates = np.array([[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6,
                                1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1, 3.2, 3.3,
                                3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 5.0],
                               [0.0000, 0.0300, 0.1000, 0.1900, 0.3100, 0.4700, 0.6600, 0.8200, 0.9300, 0.9900,
                                1.0000, 0.9900, 0.9300, 0.8600, 0.7800, 0.6800, 0.5600, 0.4600, 0.3900, 0.3300,
                                0.2800, 0.2435, 0.2070, 0.1770, 0.1470, 0.1270, 0.1070, 0.0920, 0.0770, 0.0660,
                                0.0550, 0.0475, 0.0400, 0.0345, 0.0290, 0.0250, 0.0210, 0.0180, 0.0150, 0.0130,
                                0.0110, 0.0098, 0.0086, 0.0074, 0.0062, 0.0050, 0.0040, 0.0030, 0.0020, 0.0010, 0]])

        return uhOrdinates

    def populateGisFields(self) -> None:
        """ Add field names to input comboboxes. """

        self.cboIdField.clear()
        self.cboAreaPerField.clear()
        self.cboAreaPerCCField.clear()
        self.cboAreaImp1Field.clear()
        self.cboAreaImp1CCField.clear()
        self.cboAreaImp2Field.clear()
        self.cboAreaImp2CCField.clear()
        self.cboCnField.clear()
        self.cboTpTcField.clear()
        self.cboCField.clear()
        self.cboLengthField.clear()
        self.cboSlopeField.clear()
        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        if self.gbGisApproach.isChecked() and layer is not None:
            self.cboIdField.addItems(layer.fields().names())
            self.cboAreaPerField.addItems(layer.fields().names())
            self.cboAreaPerCCField.addItems(layer.fields().names())
            self.cboAreaImp1Field.addItems(layer.fields().names())
            self.cboAreaImp1CCField.addItems(layer.fields().names())
            self.cboAreaImp2Field.addItems(layer.fields().names())
            self.cboAreaImp2CCField.addItems(layer.fields().names())
            self.cboCnField.addItems(layer.fields().names())
            self.cboTpTcField.addItems(layer.fields().names())
            self.cboCField.addItems(layer.fields().names())
            self.cboLengthField.addItems(layer.fields().names())
            self.cboSlopeField.addItems(layer.fields().names())

    def collectCatchIdGis(self) -> list:
        """ Collect catchment ID's from shapefile.
            :return: catchIdGis
        """

        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        catchIdGis = []
        if self.gbGisApproach.isChecked() and layer is not None:
            catchIdField = self.cboIdField.currentIndex()
            if catchIdField > -1:
                catchIdGis = [str(f.attribute(catchIdField)) for f in layer.getFeatures()]

        return catchIdGis

    def collectCnGis(self) -> list:
        """ Collect curve numbers from shapefile.
            :return: cnGis
        """

        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        cnGis = []
        if self.gbGisApproach.isChecked() and layer is not None:
            cnField = self.cboCnField.currentIndex()
            if cnField > -1:
                cnGis = [str(f.attribute(cnField)) for f in layer.getFeatures()]

        return cnGis

    def collectAreaPerGis(self) -> list:
        """ Collect area pervious from shapefile.
            :return: areaPerGis
        """

        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        areaPerGis = []
        if self.gbGisApproach.isChecked() and layer is not None:
            areaPerField = self.cboAreaPerField.currentIndex()
            if areaPerField > -1:
                areaPerGis = [str(f.attribute(areaPerField)) for f in layer.getFeatures()]

        return areaPerGis

    def collectAreaPerCCGis(self) -> list:
        """ Collect area pervious CC from shapefile.
            :return: areaPerCCGis
        """

        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        areaPerCCGis = []
        if self.gbGisApproach.isChecked() and layer is not None:
            areaPerCCField = self.cboAreaPerCCField.currentIndex()
            if areaPerCCField > -1:
                areaPerCCGis = [str(f.attribute(areaPerCCField)) for f in layer.getFeatures()]

        return areaPerCCGis

    def collectAreaImp1Gis(self) -> list:
        """ Collect area impervious 1 from shapefile.
            :return: areaImp1Gis
        """

        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        areaImp1Gis = []
        if self.gbGisApproach.isChecked() and layer is not None:
            areaImp1Field = self.cboAreaImp1Field.currentIndex()
            if areaImp1Field > -1:
                areaImp1Gis = [str(f.attribute(areaImp1Field)) for f in layer.getFeatures()]

        return areaImp1Gis

    def collectAreaImp1CCGis(self) -> list:
        """ Collect area impervious 1 CC from shapefile.
            :return: areaImp1CCGis
        """

        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        areaImp1CCGis = []
        if self.gbGisApproach.isChecked() and layer is not None:
            areaImp1CCField = self.cboAreaImp1CCField.currentIndex()
            if areaImp1CCField > -1:
                areaImp1CCGis = [str(f.attribute(areaImp1CCField)) for f in layer.getFeatures()]

        return areaImp1CCGis

    def collectAreaImp2Gis(self) -> list:
        """ Collect area impervious 2 from shapefile.
            :return: areaImp2Gis
        """

        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        areaImp2Gis = []
        if self.gbGisApproach.isChecked() and self.cbAreaImp2Gis.isChecked() and layer is not None:
            areaImp2Field = self.cboAreaImp2Field.currentIndex()
            if areaImp2Field > -1:
                areaImp2Gis = [str(f.attribute(areaImp2Field)) for f in layer.getFeatures()]

        return areaImp2Gis

    def collectAreaImp2CCGis(self) -> list:
        """ Collect area impervious 2 CC from shapefile.
            :return: areaImp2CCGis
        """

        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        areaImp2CCGis = []
        if self.gbGisApproach.isChecked() and self.cbAreaImp2Gis.isChecked() and layer is not None:
            areaImp2CCField = self.cboAreaImp2CCField.currentIndex()
            if areaImp2CCField > -1:
                areaImp2CCGis = [str(f.attribute(areaImp2CCField)) for f in layer.getFeatures()]

        return areaImp2CCGis

    def collectTpTcGis(self) -> list:
        """ Collect time of peak or time or concentration from shapefile.
            :return: tpTcGis
        """

        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        tpTcGis = []
        if self.gbGisApproach.isChecked() and self.rbTpTcGis.isChecked() and layer is not None:
            tpTcField = self.cboTpTcField.currentIndex()
            if tpTcField > -1:
                tpTcGis = [str(f.attribute(tpTcField)) for f in layer.getFeatures()]

        return tpTcGis

    def collectCGis(self) -> list:
        """ Collect channelisation factor from shapefile.
            :return: cGis
        """

        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        cGis = []
        if self.gbGisApproach.isChecked() and self.rbTpTcCalcsGis.isChecked() and layer is not None:
            cField = self.cboCField.currentIndex()
            if cField > -1:
                cGis = [str(f.attribute(cField)) for f in layer.getFeatures()]

        return cGis

    def collectLengthGis(self) -> list:
        """ Collect subcatchment length from shapefile.
            :return: lengthGis
        """

        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        lengthGis = []
        if self.gbGisApproach.isChecked() and self.rbTpTcCalcsGis.isChecked() and self.rbLengthSlope.isChecked() and layer is not None:
            lengthField = self.cboLengthField.currentIndex()
            if lengthField > -1:
                lengthGis = [str(f.attribute(lengthField)) for f in layer.getFeatures()]

        return lengthGis

    def collectSlopeGis(self) -> list:
        """ Collect subcatchment length from shapefile.
            :return: slopeGis
        """

        layer = tuflowqgis_find_layer(self.cboInputPolygons.currentText())
        slopeGis = []
        if self.gbGisApproach.isChecked() and self.rbTpTcCalcsGis.isChecked() and self.rbLengthSlope.isChecked() and layer is not None:
            slopeField = self.cboSlopeField.currentIndex()
            if slopeField > -1:
                slopeGis = [str(f.attribute(slopeField)) for f in layer.getFeatures()]

        return slopeGis

    # def activateCField(self) -> None:
    #     """ Activate C Field when radio button is checked. """
    #
    #     if self.rbCGis.isChecked():
    #         self.cboCField.setEnabled(True)
    #     else:
    #         self.cboCField.setEnabled(False)

    def checkTpOnly(self) -> None:
        """ Check only one box - Tp or Tc. """

        if self.cbTpCheck.isChecked()and self.cbTcCheck.isChecked():
                self.cbTcCheck.setChecked(False)

    def checkTcOnly(self) -> None:
        """ Check only one box - Tp or Tc. """

        if self.cbTpCheck.isChecked()and self.cbTcCheck.isChecked():
                self.cbTpCheck.setChecked(False)

    def check(self) -> None:
        """ Check input for silly mistakes or omissions as best as can.
            If passes all checks, will start run function.
        """

        # input catchment location
        if self.cboLocation.currentText() != 'Auckland Region (TP108)':
            QMessageBox.critical(self, "SCS to TUFLOW", "No Catchment Location Specified")
            return

        # event selection - at least one event must be selected
        events = self.createEventsList()
        if not events:
            QMessageBox.critical(self, "SCS to TUFLOW", "No Event Selected")
            return

        # depth
        for depthCheck, depthValue in [
            (self.cb002Year, self.le002YearDepth), (self.cb002YearCC, self.le002YearDepthCC),
            (self.cb005Year, self.le005YearDepth), (self.cb005YearCC, self.le005YearDepthCC),
            (self.cb010Year, self.le010YearDepth), (self.cb010YearCC, self.le010YearDepthCC),
            (self.cb020Year, self.le020YearDepth), (self.cb020YearCC, self.le020YearDepthCC),
            (self.cb050Year, self.le050YearDepth), (self.cb050YearCC, self.le050YearDepthCC),
            (self.cb100Year, self.le100YearDepth), (self.cb100YearCC, self.le100YearDepthCC)]:
            if depthCheck.isChecked() and depthValue.text() == '':
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Depth for All Selected Event(s)")
                return
            if depthCheck.isChecked():
                try:
                    float(depthValue.text())
                except ValueError:
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Depth as an Integer or Float")
                    return

        # calculation method
        if not self.gbManualApproach.isChecked() and not self.gbGisApproach.isChecked():
            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Either Manual Approach or GIS Approach")
            return
        if self.gbManualApproach.isChecked() and self.gbGisApproach.isChecked():
            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Either Manual Approach or GIS Approach")
            return

        # manual method
        if self.gbManualApproach.isChecked():
            # catchment ID
            if self.leCatchId.text() == '' or ' ' in self.leCatchId.text():
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Catchment ID and Avoid Spaces")
                return
            # curve number
            if self.leCnPer.text() == '':
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Curve Number")
                return
            try:
                float(self.leCnPer.text())
            except ValueError:
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Curve Number as an Integer or Float")
                return
            if float(self.leCnPer.text()) <= 0 :
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Curve Number Above Zero")
                return
            # area pervious
            if self.leAreaPer.text() == '':
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Pervious")
                return
            try:
                float(self.leAreaPer.text())
            except ValueError:
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Pervious as an Integer or Float")
                return
            if float(self.leAreaPer.text()) < 0 :
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Pervious Above Zero or Zero")
                return
            # area impervious 1
            if self.leAreaImp1.text() == '':
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 1")
                return
            try:
                float(self.leAreaImp1.text())
            except ValueError:
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 1 as an Integer or Float")
                return
            if float(self.leAreaImp1.text()) < 0 :
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 1 Above Zero or Zero")
                return
            # area impervious 2
            if self.cbAreaImp2.isChecked():
                if self.leAreaImp2.text() == '':
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 2")
                    return
                try:
                    float(self.leAreaImp2.text())
                except ValueError:
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 2 as an Integer or Float")
                    return
                if float(self.leAreaImp2.text()) < 0:
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 2 Above Zero or Zero")
                    return
            # area suffix
            areaSuffixManual = []
            areaSuffixManual.append(self.leAreaPerSuf.text())
            areaSuffixManual.append(self.leAreaImp1Suf.text())
            if self.cbAreaImp2.isChecked():
                areaSuffixManual.append(self.leAreaImp2Suf.text())
            if len(areaSuffixManual) > len(set(areaSuffixManual)):
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Unique Suffix for All Required Areas.")
                return
            if self.leAreaPerSuf.text() == '' or ' ' in self.leAreaPerSuf.text():
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Pervious Suffix and Avoid Spaces")
                return
            if self.leAreaPerSuf.text() == '' or ' ' in self.leAreaImp1Suf.text():
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 1 Suffix and Avoid Spaces")
                return
            if self.cbAreaImp2.isChecked():
                if self.leAreaImp2Suf.text() == '' or ' ' in self.leAreaImp2Suf.text():
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 2 Suffix and Avoid Spaces")
                    return
            # time of peak and time of concentration
            if not self.rbTpManual.isChecked() and not self.rbTcManual.isChecked() and not self.rbTpTcCalcsManual.isChecked():
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify One Tp / Tc Method")
                return
            if self.rbTpManual.isChecked():
                if self.leTpPer.text() == '' or self.leTpImp.text() == '':
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Tp Pervious and Tp Impervious Value")
                    return
                for float_check in [self.leTpPer, self.leTpImp]:
                    try:
                        float(float_check.text())
                    except ValueError:
                        QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Tp Pervious and Tp Impervious as an Integer or Float")
                        return
                    if float(float_check.text()) < 0.11:
                        QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Tp Pervious and Tp Impervious Above 0.11hr.")
                        return
            if self.rbTcManual.isChecked():
                if self.leTcPer.text() == '' or self.leTcImp.text() == '':
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Tc Pervious and Tc Impervious Value")
                    return
                for float_check in [self.leTcPer, self.leTcImp]:
                    try:
                        float(float_check.text())
                    except ValueError:
                        QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Tc Pervious and Tc Impervious as an Integer or Float")
                        return
                    if float(float_check.text()) < 0.16667:
                        QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Tc Pervious and Tc Impervious Above 0.16667hr.")
                        return
            if self.rbTpTcCalcsManual.isChecked():
                if self.leCPer.text() == '' or self.leCImp.text() == '' or self.leLength.text() == '' or self.leSlope.text() == '':
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Channelisation Factor, Length and/or Slope")
                    return
                for float_check in [self.leCPer, self.leCImp, self.leLength, self.leSlope]:
                    try:
                        float(float_check.text())
                    except ValueError:
                        QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Channelisation Factor, Length and/or Slope as an Integer or Float")
                        return
                for float_check in [self.leCPer, self.leCImp]:
                    if float(float_check.text()) != 0.6:
                        if float(float_check.text()) != 0.8:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Channelisation Factor 0.6 or 0.8")
                            return
                if float(self.leLength.text()) <= 0:
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Length Above Zero.")
                    return
                if float(self.leSlope.text()) < 0:
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Slope Above Zero or Zero.")
                    return

        # GIS method
        if self.gbGisApproach.isChecked():
            # polygons
            if self.cboInputPolygons.currentText() == '- None -':
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Polygons GIS Data")
                return
            # catchment ID
            catchIdGis = self.collectCatchIdGis()
            if len(catchIdGis) > len(set(catchIdGis)):
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Unique Catchment IDs in Polygons Layer.")
                return
            # curve number
            cnGis = self.collectCnGis()
            for cn in cnGis:
                try:
                    float(cn)
                except ValueError:
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Curve Number as an Integer or Float in Polygons Layer.")
                    return
                if float(cn) <= 0:
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Curve Number Above Zero in Polygons Layer.")
                    return
            # area
            areaPerGis = self.collectAreaPerGis()
            areaPerCCGis = self.collectAreaPerCCGis()
            areaImp1Gis = self.collectAreaImp1Gis()
            areaImp1CCGis = self.collectAreaImp1CCGis()
            areaImp2Gis = 0
            areaImp2CCGis = 0
            if self.cbAreaImp2Gis.isChecked():
                areaImp2Gis = self.collectAreaImp2Gis()
                areaImp2CCGis = self.collectAreaImp2CCGis()
            events = self.createEventsList()
            for event in events:
                if 'CC' not in event:
                    for area in areaPerGis:
                        try:
                            float(area)
                        except ValueError:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Pervious as an Integer or Float in Polygons Layer.")
                            return
                        if float(area) < 0:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Pervious Above Zero or Zero in Polygons Layer.")
                            return
                    for area in areaImp1Gis:
                        try:
                            float(area)
                        except ValueError:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 1 as an Integer or Float in Polygons Layer.")
                            return
                        if float(area) < 0:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 1 Above Zero or Zero in Polygons Layer.")
                            return
                    if self.cbAreaImp2Gis.isChecked():
                        for area in areaImp2Gis:
                            try:
                                float(area)
                            except ValueError:
                                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 2 as an Integer or Float in Polygons Layer.")
                                return
                            if float(area) < 0:
                                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 2 Above Zero or Zero in Polygons Layer.")
                                return
                if 'CC' in event:
                    for area in areaPerCCGis:
                        try:
                            float(area)
                        except ValueError:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Pervious CC as an Integer or Float in Polygons Layer.")
                            return
                        if float(area) < 0:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Pervious CC Above Zero or Zero in Polygons Layer.")
                            return
                    for area in areaImp1CCGis:
                        try:
                            float(area)
                        except ValueError:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 1 CC as an Integer or Float in Polygons Layer.")
                            return
                        if float(area) < 0:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 1 CC Above Zero or Zero in Polygons Layer.")
                            return
                    if self.cbAreaImp2Gis.isChecked():
                        for area in areaImp2CCGis:
                            try:
                                float(area)
                            except ValueError:
                                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 2 CC as an Integer or Float in Polygons Layer.")
                                return
                            if float(area) < 0:
                                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 2 CC Above Zero or Zero in Polygons Layer.")
                                return
            # area suffix
            areaSuffixGis = []
            areaSuffixGis.append(self.leAreaPerSufGis.text())
            areaSuffixGis.append(self.leAreaImp1SufGis.text())
            if self.cbAreaImp2Gis.isChecked():
                areaSuffixGis.append(self.leAreaImp2SufGis.text())
            if len(areaSuffixGis) > len(set(areaSuffixGis)):
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Unique Suffix for All Required Areas.")
                return
            if self.leAreaPerSufGis.text() == '' or ' ' in self.leAreaPerSufGis.text():
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Pervious Suffix and Avoid Spaces")
                return
            if self.leAreaImp1SufGis.text() == '' or ' ' in self.leAreaImp1SufGis.text():
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 1 Suffix and Avoid Spaces")
                return
            if self.cbAreaImp2Gis.isChecked():
                if self.leAreaImp2SufGis.text() == '' or ' ' in self.leAreaImp2SufGis.text():
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Area Impervious 2 Suffix and Avoid Spaces")
                    return
            # time of peak and time of concentration
            if not self.rbTpTcGis.isChecked() and not self.rbTpTcCalcsGis.isChecked():
                QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify One Tp / Tc Method")
                return
            if self.rbTpTcGis.isChecked():
                if not self.cbTpCheck.isChecked() and not self.cbTcCheck.isChecked():
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Either Tp or Tc")
                    return
                tpTcGis = self.collectTpTcGis()
                if self.cbTpCheck.isChecked():
                    for tp in tpTcGis:
                        try:
                            float(tp)
                        except ValueError:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Tp as an Integer or Float in Polygons Layer.")
                            return
                        if float(tp) < 0.11:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Tp Above 0.11hr in Polygons Layer.")
                            return
                if self.cbTcCheck.isChecked():
                    for tc in tpTcGis:
                        try:
                            float(tc)
                        except ValueError:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Tc as an Integer or Float in Polygons Layer.")
                            return
                        if float(tc) < 0.16667:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Tc Above 0.16667hr in Polygons Layer.")
                            return
            # channelisation factor
            if self.rbTpTcCalcsGis.isChecked():
                cGis = self.collectCGis()
                for c in cGis:
                    try:
                        float(c)
                    except ValueError:
                        QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Channelisation Factor as an Integer or Float in Polygons Layer.")
                        return
                    if float(c) != 0.6:
                        if float(c) != 0.8:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Channelisation Factor 0.6 or 0.8 in Polygons Layer")
                            return
            # length/slope and DEM/streamline
            if self.rbTpTcCalcsGis.isChecked():
                if not self.rbLengthSlope.isChecked() and not self.rbDemStreamline.isChecked():
                    QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Either Length/Slope or DEM/Streamline")
                    return
                if self.rbLengthSlope.isChecked():
                    lengthGis = self.collectLengthGis()
                    slopeGis = self.collectSlopeGis()
                    for length in lengthGis:
                        try:
                            float(length)
                        except ValueError:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Length as an Integer or Float in Polygons Layer.")
                            return
                        if float(length) <= 0:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Length Above Zero in Polygons Layer.")
                            return
                    for slope in slopeGis:
                        try:
                            float(slope)
                        except ValueError:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Slope as an Integer or Float in Polygons Layer.")
                            return
                        if float(slope) < 0:
                            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Slope Above Zero or Zero in Polygons Layer.")
                            return
                if self.rbDemStreamline.isChecked():
                    if self.cboInputDem.currentText() == '- None -':
                        QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify DEM Input")
                        return
                    if self.cboInputPolylines.currentText() == '- None -':
                        QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Streamline Layer")
                        return

        # output location
        if self.leOutput.text() == '':
            QMessageBox.critical(self, "SCS to TUFLOW", "Must Specify Output Location")
            return

        self.run()

    def run(self) -> None:
        """ Run the tool. Collect inputs and pass them to engine.py for processing. """

        # hardcoded variables for now
        interval = 0.0166667
        #intervalOut = 0.0166667
        iaPer = 5
        iaImp = 0
        cnImp = 98
        uhCurve = 0.75
        uhStep = 0.1
        # arf = 1

        # collect inputs - initialise with actual values where can otherwise some dummy values
        inputs = {
            # location
            'location': SCS.auckland if self.cboLocation.currentText() == 'Auckland Region (TP108)' else SCS.other,
            # 'unitHydrograph': SCS.aucklandUh if self.cboLocation.currentText() == 'Auckland Region' else SCS.otherUh,
            # rainfall and events
            'events': [],
            '002yr': float(self.le002YearDepth.text()) if self.cb002Year.isChecked() else None,
            '005yr': float(self.le005YearDepth.text()) if self.cb005Year.isChecked() else None,
            '010yr': float(self.le010YearDepth.text()) if self.cb010Year.isChecked() else None,
            '020yr': float(self.le020YearDepth.text()) if self.cb020Year.isChecked() else None,
            '050yr': float(self.le050YearDepth.text()) if self.cb050Year.isChecked() else None,
            '100yr': float(self.le100YearDepth.text()) if self.cb100Year.isChecked() else None,
            '002yrCC': float(self.le002YearDepthCC.text()) if self.cb002YearCC.isChecked() else None,
            '005yrCC': float(self.le005YearDepthCC.text()) if self.cb005YearCC.isChecked() else None,
            '010yrCC': float(self.le010YearDepthCC.text()) if self.cb010YearCC.isChecked() else None,
            '020yrCC': float(self.le020YearDepthCC.text()) if self.cb020YearCC.isChecked() else None,
            '050yrCC': float(self.le050YearDepthCC.text()) if self.cb050YearCC.isChecked() else None,
            '100yrCC': float(self.le100YearDepthCC.text()) if self.cb100YearCC.isChecked() else None,
            # simulation settings
            'intervalIn': self.leIntervalIn.text(),
            'intervalOut': float(self.sbIntervalOut.text()),
            'decimals': int(self.sbDecimals.text()),
            # manual approach
            'manualApproachChecked': SCS.manualApproachChecked if self.gbManualApproach.isChecked() else None,
            'catchmentId': self.leCatchId.text() if self.gbManualApproach.isChecked() else None,
            'cnPer': float(self.leCnPer.text()) if self.gbManualApproach.isChecked() else None,
            'areaPer': float(self.leAreaPer.text()) if self.gbManualApproach.isChecked() else None,
            'areaImp1': float(self.leAreaImp1.text()) if self.gbManualApproach.isChecked() else None,
            'areaImp2': float(self.leAreaImp2.text()) if self.gbManualApproach.isChecked() and self.cbAreaImp2.isChecked() else None,
            'areaPerSuf': self.leAreaPerSuf.text() if self.gbManualApproach.isChecked() else None,
            'areaImp1Suf': self.leAreaImp1Suf.text() if self.gbManualApproach.isChecked() else None,
            'areaImp2Suf': self.leAreaImp2Suf.text() if self.gbManualApproach.isChecked() and self.cbAreaImp2.isChecked() else None,
            'areaImp2Checked': SCS.areaImp2Checked if self.gbManualApproach.isChecked() and self.cbAreaImp2.isChecked() else None,
            'tpManualChecked': SCS.tpManualChecked if self.gbManualApproach.isChecked() and self.rbTpManual.isChecked() else None,
            'tpPer': float(self.leTpPer.text()) if self.gbManualApproach.isChecked() and self.rbTpManual.isChecked() else None,
            'tpImp': float(self.leTpImp.text()) if self.gbManualApproach.isChecked() and self.rbTpManual.isChecked() else None,
            'tcManualChecked': SCS.tcManualChecked if self.gbManualApproach.isChecked() and self.rbTcManual.isChecked() else None,
            'tcPer': float(self.leTcPer.text()) if self.gbManualApproach.isChecked() and self.rbTcManual.isChecked() else None,
            'tcImp': float(self.leTcImp.text()) if self.gbManualApproach.isChecked() and self.rbTcManual.isChecked() else None,
            'tpTcCalcsManualChecked': SCS.tpTcCalcsManualChecked if self.gbManualApproach.isChecked() and self.rbTpTcCalcsManual.isChecked() else None,
            'cPer': float(self.leCPer.text()) if self.gbManualApproach.isChecked() and self.rbTpTcCalcsManual.isChecked() else None,
            'cImp': float(self.leCImp.text()) if self.gbManualApproach.isChecked() and self.rbTpTcCalcsManual.isChecked() else None,
            'length': float(self.leLength.text()) if self.gbManualApproach.isChecked() and self.rbTpTcCalcsManual.isChecked() else None,
            'slope': float(self.leSlope.text()) if self.gbManualApproach.isChecked() and self.rbTpTcCalcsManual.isChecked() else None,
            # GIS approach
            'gisApproachChecked': SCS.gisApproachChecked if self.gbGisApproach.isChecked() else None,
            'catchIdGis': [],
            'cnGis': [],
            'areaPerGis': [],
            'areaPerCCGis': [],
            'areaImp1Gis': [],
            'areaImp1CCGis': [],
            'areaImp2Gis': [],
            'areaImp2CCGis': [],
            'areaPerSufGis': self.leAreaPerSufGis.text() if self.gbGisApproach.isChecked() else None,
            'areaImp1SufGis': self.leAreaImp1SufGis.text() if self.gbGisApproach.isChecked() else None,
            'areaImp2SufGis': self.leAreaImp2SufGis.text() if self.gbGisApproach.isChecked() and self.cbAreaImp2Gis.isChecked() else None,
            'areaImp2GisChecked': SCS.areaImp2GisChecked if self.gbGisApproach.isChecked() and self.cbAreaImp2Gis.isChecked() else None,
            'tpTcGisChecked': SCS.tpTcGisChecked if self.gbGisApproach.isChecked() and self.rbTpTcGis.isChecked() else None,
            'tpGisChecked': SCS.tpGisChecked if self.gbGisApproach.isChecked() and self.rbTpTcGis.isChecked() and self.cbTpCheck.isChecked() else None,
            'tcGisChecked': SCS.tcGisChecked if self.gbGisApproach.isChecked() and self.rbTpTcGis.isChecked() and self.cbTcCheck.isChecked() else None,
            'tpTcGis': [],
            'tpTcCalcsGisChecked': SCS.tpTcCalcsGisChecked if self.gbGisApproach.isChecked() and self.rbTpTcCalcsGis.isChecked() else None,
            'cGis': [],
            'lengthSlopeChecked': SCS.lengthSlopeChecked if self.gbGisApproach.isChecked() and self.rbTpTcCalcsGis.isChecked() and self.rbLengthSlope.isChecked() else None,
            'lengthGis': [],
            'slopeGis': [],
            'demStreamlineChecked': SCS.demStreamlineChecked if self.gbGisApproach.isChecked() and self.rbTpTcCalcsGis.isChecked() and self.rbDemStreamline.isChecked() else None,
            # output
            'outputFolder': self.leOutput.text(),
            'sourceInflows': None,
            # hardcoded
            'interval': interval,
            #'intervalOut': intervalOut,
            'iniLossPer': iaPer,
            'iniLossImp': iaImp,
            'cnImp': cnImp,
            'uhCurve': uhCurve,
            'uhStep': uhStep
            #'arf': arf,
        }

        # populate rest with real values
        # events
        events = self.createEventsList()
        inputs['events'] = events

        # unit hydrograph ordinates
        uhOrdinates = self.unitHydrographOrdinates()
        inputs['uhOrdinates'] = uhOrdinates

        # GIS fields
        if self.gbGisApproach.isChecked():
            catchIdGis = self.collectCatchIdGis()
            inputs['catchIdGis'] = catchIdGis
            cnGis = self.collectCnGis()
            inputs['cnGis'] = cnGis
            areaPerGis = self.collectAreaPerGis()
            inputs['areaPerGis'] = areaPerGis
            areaPerCCGis = self.collectAreaPerCCGis()
            inputs['areaPerCCGis'] = areaPerCCGis
            areaImp1Gis = self.collectAreaImp1Gis()
            inputs['areaImp1Gis'] = areaImp1Gis
            areaImp1CCGis = self.collectAreaImp1CCGis()
            inputs['areaImp1CCGis'] = areaImp1CCGis
            if self.cbAreaImp2Gis.isChecked():
                areaImp2Gis = self.collectAreaImp2Gis()
                inputs['areaImp2Gis'] = areaImp2Gis
                areaImp2CCGis = self.collectAreaImp2CCGis()
                inputs['areaImp2CCGis'] = areaImp2CCGis
            if self.rbTpTcGis.isChecked():
                tpTcGis = self.collectTpTcGis()
                inputs['tpTcGis'] = tpTcGis
            if self.rbTpTcCalcsGis.isChecked():
                cGis = self.collectCGis()
                inputs['cGis'] = cGis
                if self.rbLengthSlope.isChecked():
                    lengthGis = self.collectLengthGis()
                    inputs['lengthGis'] = lengthGis
                    slopeGis = self.collectSlopeGis()
                    inputs['slopeGis'] = slopeGis

        # outfile - make sure output directory exists or can be created
        dir = os.path.dirname(inputs['outputFolder'])
        if not makeDir(dir):
            QMessageBox.critical(self, "SCS to TUFLOW", "Unexpected Error with Output Folder Location: "
                                                          "Double Check Directory")
            return

        # setup run process on a separate thread so that an infinite progress bar can be used
        self.thread = QThread()
        self.SCS = SCS(inputs)
        self.SCS.moveToThread(self.thread)
        self.SCS.scsStart.connect(self.scsStarted)
        self.SCS.tuflowProcessingStart.connect(self.tuflowProcessingStarted)
        self.SCS.finished.connect(self.scsFinished)
        self.thread.started.connect(self.SCS.run)
        self.thread.start()

        self.progressBar.setRange(0, 0)
        self.progressBar.setValue(0)


    def scsStarted(self) -> None:
        """ Event that happens when SCS is started. Sets progress bar to infinite and updates text. """

        self.progressBarLabel.setText("Getting SCS Data . . .")

    def tuflowProcessingStarted(self) -> None:
        """ Event that happens when SCS is finished and the data is being processed into TUFLOW format. """

        self.progressBarLabel.setText("Processing Data Into TUFLOW Format . . .")

    def scsFinished(self, message: str = '') -> None:
        """ Event is triggered when finished. If message is empty = completed successfully, else error.
            :param message: str error message if any
        """

        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(100)
        if message:
            self.progressBarLabel.setText("Finished... Errors Occured")
            QMessageBox.critical(self, "SCS to TUFLOW", message)
        else:
            self.progressBarLabel.setText("Finished Successfully")
        self.thread.terminate()
        self.thread.wait()