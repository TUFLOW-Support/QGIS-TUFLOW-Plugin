import os
import sys
import re
from typing import Sequence

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path
from collections import OrderedDict
import numpy as np
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis import processing
from qgis.core import *
from qgis.gui import QgisInterface
from ..forms.ArchBridgeEditorDock import Ui_archBridgeDock

from ..tuflowqgis_library import copyStyle
from .RubberBand import RubberBand
from .BridgePlot import BridgePlot
from .BridgeEditorImport import BridgeImport, BridgeEditorImportDialog
from .ArchBridge import ArchBridge
from .FmDatParser import fm_dat_parser
from ..tuflowqgis_library import (getParabolicCoord, lineToPoints,
                                  getRasterValue, browse, is1dTable, is1dNetwork, getRightAngleLine,
                                  get_table_names)
from tuflow.toc.toc import tuflowqgis_find_layer, findAllRasterLyrs
from ..TUFLOW_XS import XS_Data
from .ArchBridgeList import Ui_ArchBridgeList
from .EofParser import EofParser
from .BridgeEditorTable import BridgeCurveTable

from ..compatibility_routines import QT_RED, QT_PALETTE_WINDOW_TEXT, QT_MESSAGE_BOX_CANCEL, QT_RICH_TEXT, QT_DARK_GREEN, QT_MESSAGE_BOX_YES, QT_HEADER_VIEW_FIXED, QT_MATCH_EXACTLY, QT_MESSAGE_BOX_NO, QT_CUSTOM_CONTEXT_MENU, QT_ABSTRACT_ITEM_VIEW_NO_EDIT_TRIGGERS, QT_ABSTRACT_ITEM_VIEW_NO_SELECTION, QT_PALETTE_WINDOW, QT_HEADER_VIEW_STRETCH, QT_PALETTE_NORMAL


class Table:
    Before = 0
    After = 1



class ArchBridgeList(QDialog, Ui_ArchBridgeList):

    def __init__(self, bridge_names):
        QDialog.__init__(self)
        self.setupUi(self)
        self.lwBridges.addItems(bridge_names)
        self.bridge_names = bridge_names[:]
        self.bridge_name = ''
        self.valid = False

        self.leFilter.textChanged.connect(self.updateBridgeList)
        self.pbOk.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

    def updateBridgeList(self, text):
        self.lwBridges.clear()

        if not self.leFilter.text().strip():
            self.lwBridges.addItems(self.bridge_names)

        self.lwBridges.addItems(x for x in self.bridge_names if self.leFilter.text().strip().lower() in x.lower())

    def accept(self):
        self.valid = True
        if self.lwBridges.selectedItems():
            self.bridge_name = self.lwBridges.selectedItems()[0].text()
        QDialog.accept(self)


class ArchBridgeDock(QDockWidget, Ui_archBridgeDock):
    
    def __init__(self, iface: QgisInterface) -> None:
        # initialise inherited classes and gui
        QDockWidget.__init__(self)
        self.setupUi(self)
        
        # member properties
        self.iface = iface
        self.channelTableRows = []
        self.bridgeTableRows = []
        self.row2error = {}
        self.rubberBand = None
        self.plot = None
        self.curvePlot = None
        self.connected = False
        self.selChangedSignal = None
        self.editedNwkLayerSignal = None
        self.editedXsLayerSignal = None
        self.pbReloadBridgeClicked = None
        self.pbReloadCrossSectionClicked = None
        self.btnBrowseOutDbClicked = None
        self.btnBrowseOutFileClicked = None
        self.cboNwkFeatChangedSignal = None
        self.cboXsFeatChangedSignal = None
        self.prevMapTool = None
        self.fid2nwklyr = OrderedDict({})
        self.fid2xslyr = OrderedDict({})
        self.xsFeat = None
        self.eof = EofParser()
        self.xsAreaCurve = None
        self.bridgeAreaCurve = None
        self.bridgeBlockageCurve = None
        self.bridgeCurveTable = None
        
        # icons
        dir = os.path.dirname(os.path.dirname(__file__))
        icon = QIcon(os.path.join(dir, "icons", "ArchBridge.png"))
        self.setWindowIcon(icon)
        self.applyIcons()

        self.featMsgLabel_2.setVisible(False)

        # tables
        self.twChannel.verticalHeader().setSectionResizeMode(QT_HEADER_VIEW_FIXED)
        self.twBridge.verticalHeader().setSectionResizeMode(QT_HEADER_VIEW_FIXED)
        # self.resizeTable()

        # context menus
        self.contextMenuChannelTable()
        self.contextMenuBridgeTable()
        
        # tables
        self.twChannel.verticalHeader().setSectionResizeMode(QT_HEADER_VIEW_FIXED)
        self.twBridge.verticalHeader().setSectionResizeMode(QT_HEADER_VIEW_FIXED)
        # self.resizeTable()

        # initialise comboboxes
        self.populateLayerComboBoxes()
        self.outFormatChanged()
        self.outputTypeChanged()

        # initialise settings
        # bridge
        bridge_save_setting = QSettings().value('tuflow/arch_bridge_editor/bridge_save_setting', 'csv_folder')
        bridge_save_path = QSettings().value('tuflow/arch_bridge_editor/bridge_save_path', '')
        if bridge_save_setting == 'in_place':
            self.bridge_csv_loc_in_place.setChecked(True)
        elif bridge_save_setting == 'custom_folder':
            self.bridge_csv_loc_custom_folder.setChecked(True)
        else:
            self.bridge_csv_loc_csv_folder.setChecked(True)
        self.leCustomName.setText(bridge_save_path)
        # cross-section
        xs_save_setting = QSettings().value('tuflow/arch_bridge_editor/xs_save_setting', 'csv_folder')
        xs_save_path = QSettings().value('tuflow/arch_bridge_editor/xs_save_path', '')
        if xs_save_setting == 'in_place':
            self.xs_csv_loc_in_place.setChecked(True)
        elif xs_save_setting == 'custom_folder':
            self.xs_csv_loc_custom_folder.setChecked(True)
        else:
            self.xs_csv_loc_csv_folder.setChecked(True)
        self.leXSCustomName.setText(xs_save_path)

        self.connectAll()

    def __del__(self) -> None:
        self.disconnectAll()
        QDockWidget.__del__(self)
        
    def check(self) -> None:
        """Checks inputs before running."""
        
        if self.row2error:
            message = []
            for row, widgets in sorted(self.row2error.items()):
                label = widgets[1]
                message.append(label.text())
            message = '\n'.join(message)
            QMessageBox.critical(self, "Arch Bridge", "Errors found:\n{0}".format(message))
            return

        # 1d_nwk is specified
        if not self.cboNwkLayer.currentText() or tuflowqgis_find_layer(self.cboNwkLayer.currentText()) is None:
            QMessageBox.critical(self, 'Arch Bridge', 'No valid 1d_nwk layer specified')
            return

        # 1d_nwk bridge is selected
        if not self.cboNwkFeature.currentText():
            QMessageBox.critical(self, 'Arch Bridge', 'No valid bridge feature is specified')
            return

        # check 1d_nwk type attribute has enough length
        lyr = tuflowqgis_find_layer(self.cboNwkLayer.currentText())
        i_type = 2 if '.gpkg|layername=' in lyr.dataProvider().dataSourceUri() else 1
        field = lyr.fields().field(i_type)
        if field.length() < 5 and i_type == 1:  # GPKG can break length rules so only concerned with SHP files
            answer = QMessageBox.warning(self, 'Arch Bridge', '1d_nwk layer Type attribute is not long enough for '
                                                              '"BArch" - Do you want the Arch Bridge Editor to refactor'
                                                              ' the field?<p><p><b>A new memory (temporary) layer will be created '
                                                              'and it will be up to the user to save '
                                                              'it afterward.</b>', QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_CANCEL)
            if answer == QT_MESSAGE_BOX_CANCEL:
                return

        # if output is new layer
        if self.twChannel.rowCount():
            # check if layer is already open (and locked) in workspace
            if self.cboOutFormat.currentIndex() == 0:
                outdb = Path(self.leOutName.text())
                outlyr = outdb.stem
                outUri = str(outdb)
            else:
                outdb = Path(self.leOutDatabase.text())
                outlyr = self.leOutName.text()
                outUri = '{0}|layername={1}'.format(outdb, outlyr)

            if self.cboOutputType.currentIndex() == 0:
                for lyrid, lyr_ in QgsProject.instance().mapLayers().items():
                    if lyr_.dataProvider().dataSourceUri() == outUri:
                        QMessageBox.critical(self, 'Arch Bridge',
                                             'Output layer is open in workspace. Please close before running the tool:\n{0}'.format(outlyr))
                        return

            if self.cboOutputType.currentIndex() == 0 and self.cboOutFormat.currentIndex() == 0 and not self.leOutName.text():
                QMessageBox.critical(self, 'Arch Bridge',
                                     '"New Layer" output option requires an output file to be specified')
                return
            if self.cboOutputType.currentIndex() == 0 and self.cboOutFormat.currentIndex() == 1 and \
                    (not self.leOutName.text() or not self.leOutDatabase.text()):
                QMessageBox.critical(self, 'Arch Bridge',
                                     '"New Layer" output option requires an output database to be specified')
                return

            # if output to be appended
            if self.cboOutputType.currentIndex() == 1 and \
                    (not self.cboXsLayerOut.currentText() or tuflowqgis_find_layer(self.cboXsLayerOut.currentText()) is None):
                QMessageBox.critical(self, 'Arch Bridge',
                                     '"Append to existing layer" requires a valid output layer to be specified')
                return

            # if overwrite existing
            if self.cboOutputType.currentIndex() == 2 and \
                    (not self.cboXsLayer.currentText() or tuflowqgis_find_layer(self.cboXsLayer.currentText()) is None):
                QMessageBox.critical(self, 'Arch Bridge',
                                     '"Overwrite items" requires a valid input XS layer to be specified')
                return

            # output cross-section name
            if not self.leChannelName.text() and self.cboXsLayer.currentText() == '-None-':
                QMessageBox.critical(self, 'Arch Bridge',
                                     'Cross-section name must be present in bridge editor or in cross-section layer')
                return
            elif not self.leChannelName.text() and self.cboXsLayer.currentText() != '-None-' and \
                    tuflowqgis_find_layer(self.cboXsLayer.currentText()) is None:
                QMessageBox.critical(self, 'Arch Bridge',
                                     'Cross-section name must be present in bridge editor or in cross-section layer')
                return
            elif not self.leChannelName.text() and self.cboXsLayer.currentText() != '-None-' and self.xsFeat is None:
                QMessageBox.critical(self, 'Arch Bridge',
                                     'Cross-section name must be present in bridge editor or in cross-section layer')
                return
            elif not self.leChannelName.text() and self.cboXsLayer.currentText() != '-None-':
                xslyr = tuflowqgis_find_layer(self.cboXsLayer.currentText())
                i_source = 1 if '.gpkg|layername=' in xslyr.dataProvider().dataSourceUri() else 0
                if self.xsFeat[i_source] == NULL or not self.xsFeat[i_source]:
                    QMessageBox.critical(self, 'Arch Bridge',
                                         'Cross-section name must be present in bridge editor or in cross-section layer')
                    return

        # output bridge name
        lyr = tuflowqgis_find_layer(self.cboNwkLayer.currentText())
        i_bridge = 11 if '.gpkg|layername=' in lyr.dataProvider().dataSourceUri() else 10
        fid = list(self.fid2nwklyr)[self.cboNwkFeature.currentIndex()]
        feat = [f for f in lyr.getFeatures() if f.id() == fid][0]
        if '[feature id' in self.cboNwkLayer.currentText() and not self.leBridgeName.text() and \
                (feat[i_bridge] == NULL or not feat[i_bridge].strip()):
            QMessageBox.critical(self, 'Arch Bridge',
                                 'Bridge name must be present in bridge editor or in bridge feature either in "ID" '
                                 'field or "Inlet_Type" field')
            return

        # no problems - time to run :)
        self.disconnectAll()
        self.run()
        self.connectAll()
        
    def run(self) -> None:
        """Creates TUFLOW input layers for arch bridge."""
        # process bridge and 1d_nwk layer
        nwklyr = tuflowqgis_find_layer(self.cboNwkLayer.currentText())
        lyr = tuflowqgis_find_layer(self.cboNwkLayer.currentText())
        i_id = 1 if lyr.storageType() == 'GPKG' else 0
        i_type = i_id + 1
        field = lyr.fields().field(i_type)
        if field.length() < 5 and i_type == 1:
            field_mapping = [{'name': x.name(), 'type': x.type(), 'length': x.length(), 'precision': x.precision(),
                              'expression': '"{0}"'.format(x.name())} for x in nwklyr.fields()]
            field_mapping[i_type]['length'] = 8
            parameters = {'INPUT': nwklyr, 'OUTPUT': 'memory:{0}_refactored'.format(nwklyr.name()), 'FIELDS_MAPPING': field_mapping}
            try:
                refactored = processing.run("native:refactorfields", parameters)
                nwklyr = refactored['OUTPUT']
                QgsProject.instance().addMapLayer(nwklyr)
                self.cboNwkLayer.addItem(nwklyr.name())
                self.cboNwkLayer.setCurrentText(nwklyr.name())
                copyStyle(lyr, nwklyr)
            except:
                QMessageBox.warning(self, 'Arch Bridge', 'Failed to refactor fields. Please take care using the '
                                                         'output in TUFLOW as the type attribute will be cut short.')
                return

        nwkFeat = self.getFeatureFromCbo(lyr, nwklyr)
        if nwkFeat is None:
            QMessageBox.critical(self, 'Arch Bridge', 'Unexpected error occurred after creating refactored layer '
                                                      'and could not find arch bridge feature')
            return

        if lyr != nwklyr:
            self.fid2nwklyr = OrderedDict({})
            for feat in nwklyr.getFeatures():
                name = feat.attribute(i_id)
                if name != NULL and name.strip():
                    self.fid2nwklyr[feat.id()] = name
                else:
                    self.fid2nwklyr[feat.id()] = 'Blank ID [feature id: {0}]'.format(feat.id())
            self.cboNwkFeature.clear()
            self.cboNwkFeature.addItems(list(self.fid2nwklyr.values()))
            self.cboNwkFeature.setCurrentText(nwkFeat[i_id])

        # cross section
        xsSuccess = True
        xslyr = None
        if self.twChannel.rowCount():
            if self.leChannelName.text():
                xsName = self.leChannelName.text()
            elif self.cboXsLayer.currentText() != '-None-' and self.xsFeat is not None:
                xslyr = tuflowqgis_find_layer(self.cboXsLayer.currentText())
                i_source = 1 if xslyr.storageType() == 'GPKG' else 0
                xsName = Path(self.xsFeat[i_source]).with_suffix('').name
            else:
                QMessageBox.critical(self, 'Arch Bridge', 'No valid ID for cross-section found')
                return

            # get layer
            success = True
            if self.cboOutputType.currentIndex() == 0:  # new layer
                if self.cboOutFormat.currentIndex() == 0:
                    outdb = Path(self.leOutName.text())
                    outlyr = outdb.with_suffix('').name
                    outUri = str(outdb)
                else:
                    outdb = Path(self.leOutDatabase.text())
                    outlyr = self.leOutName.text()
                    outUri = '{0}|layername={1}'.format(outdb, outlyr)

                uri = 'linestring?crs={0}'.format(nwklyr.crs().authid())
                if self.cboOutFormat.currentIndex() == 1:  # gpkg
                    uri = '{0}&field=fid:integer'.format(uri)

                uri = '{0}&field=Source:String(50)&field=Type:String(2)&field=Flags:String(8)&' \
                      'field=Column_1:String(8)&field=Column_2:String(8)&field=Column_3:String(8)&' \
                      'field=Column_4:String(8)&field=Column_5:String(8)&field=Column_6:String(8)&' \
                      'field=Z_Incremen:Real(23,15)&field=Z_Maximum:Real(23,15)'.format(uri)

                xslyr = QgsVectorLayer(uri, outlyr, 'memory')
                success = xslyr.isValid()
                if not success:
                    QMessageBox.critical(self, 'Arch Bridge', 'Error creating cross section layer')
                    return
            elif self.cboOutputType.currentIndex() == 1:  # append to existing layer
                xslyr = tuflowqgis_find_layer(self.cboXsLayerOut.currentText())
            else:  # overwrite existing
                xslyr = tuflowqgis_find_layer(self.cboXsLayer.currentText())

            if xslyr and self.cboXsLayer.currentText() != '-None-' and self.xsFeat:
                feats = [f for f in xslyr.getFeatures()]
                if self.xsFeat not in feats:
                    featIntersects = self.findCrossSection(nwkFeat, xslyr)
                    if featIntersects:
                        self.xsFeat = featIntersects[0]
                    else:
                        QMessageBox.critical(self, 'Arch Bridge', 'Error finding existing cross-section - please try selecting "-None-" then the cross-section layer again in the 1d_xs Layer dropdown box')
                        return

            # get feature
            if success:
                if self.cboOutputType.currentIndex() == 2 and self.xsFeat is not None:
                    xsFeat = self.xsFeat
                    xslyr.startEditing()
                elif self.xsFeat is not None:
                    xsGeom = self.xsFeat.geometry()
                    xsFeat = QgsFeature()
                    xsFeat.setGeometry(xsGeom)
                    xsFeat.setFields(xslyr.fields())
                else:
                    xsGeom = getRightAngleLine(nwkFeat.geometry(), 10)
                    if xsGeom is None:
                        QMessageBox.critical(self, 'Arch Bridge', 'Error creating cross-section line geometry')
                        success = False
                    else:
                        xsFeat = QgsFeature()
                        xsFeat.setGeometry(xsGeom)
                        xsFeat.setFields(xslyr.fields())

            # source
            if self.cboOutputType.currentIndex() == 0:
                lyrPath = Path(outdb)
                i_source = self.cboOutFormat.currentIndex()  # conveniently shp sits at index 0 and GPKG at index 1
            else:
                lyrPath = Path(re.split(r'\|layer=', xslyr.dataProvider().dataSourceUri(), flags=re.IGNORECASE)[0])
                i_source = 1 if xslyr.storageType() == 'GPKG' else 0
            sourceAttr = Path(xsName).with_suffix('.csv')
            if self.xs_csv_loc_csv_folder.isChecked():
                sourceAttr = Path('..') / 'csv' / sourceAttr
            elif self.xs_csv_loc_custom_folder.isChecked():
                custom_path = self.leXSCustomName.text().replace('\\', os.sep).replace('/', os.sep)
                sourceAttr = Path(custom_path) / sourceAttr
            csvPath = (lyrPath.parent / sourceAttr).resolve()
            if success:
                if xsFeat[i_source] != NULL and xsFeat[i_source]:
                    sourceAttr = Path(xsFeat[i_source]).with_name('{0}.csv'.format(xsName))
                    csvPath = (lyrPath.parent / sourceAttr).resolve()

                success = xsFeat.setAttribute(i_source, str(sourceAttr))
                if not success:
                    QMessageBox.critical(self, 'Arch Bridge', 'Error setting source attribute in output cross section')

            # type
            if success:
                i_type = i_source + 1
                success = xsFeat.setAttribute(i_type, 'XZ')
                if not success:
                    QMessageBox.critical(self, 'Arch Bridge', 'Error setting type attribute in output cross section')

            # add/update feature in layer
            if self.cboOutputType.currentIndex() == 2 and self.xsFeat is not None:
                if success:
                    success = xslyr.updateFeature(self.xsFeat)
                    if not success:
                        QMessageBox.critical(self, 'Arch Bridge', 'Error updating cross section')
                        xslyr.commitChanges()
                    else:
                        success = xslyr.commitChanges()
                        if not success:
                            QMessageBox.critical(self, 'Arch Bridge', 'Error committing changes to cross section layer')
                else:
                    xslyr.commitChanges()
            elif success:
                xslyr.dataProvider().truncate()
                xslyr.startEditing()
                success = xslyr.addFeature(xsFeat)
                xslyr.commitChanges()
                if not success:
                    QMessageBox.critical(self, 'Arch Bridge', 'Error adding cross section to output layer')

            if success:
                xslyr.updateExtents()
                xslyr.triggerRepaint()

                if self.cboOutputType.currentIndex() == 0:  # new layer
                    # output options
                    options = QgsVectorFileWriter.SaveVectorOptions()
                    options.layerName = outlyr
                    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                    answer = QT_MESSAGE_BOX_YES
                    if self.cboOutFormat.currentIndex() == 1:  # gpkg
                        options.driverName = 'GPKG'
                        if outdb.exists():
                            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                        if outdb.exists() and outlyr.lower() in [x.lower() for x in get_table_names(outdb)]:
                            answer = QMessageBox.question(self, 'Arch Bridge',
                                                          '{0} already exists in {1}\nOverwrite layer?'.format(outlyr, outdb.name),
                                                          QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_CANCEL)
                            if answer == QT_MESSAGE_BOX_CANCEL:
                                return
                    else:
                        options.driverName = 'ESRI Shapefile'
                        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

                    # write layer
                    if not outdb.parent.exists():
                        outdb.parent.mkdir(parents=True)
                    if Qgis.QGIS_VERSION_INT >= 32000:
                        error = QgsVectorFileWriter.writeAsVectorFormatV3(xslyr, str(outdb), QgsCoordinateTransformContext(), options)
                    else:
                        error = QgsVectorFileWriter.writeAsVectorFormatV2(xslyr, str(outdb), QgsCoordinateTransformContext(), options)
                    success = error[0] == QgsVectorFileWriter.NoError
                    if not success:
                        QMessageBox.critical(self, 'Arch Bridge', 'Error writing output layer: {0}'.format(error[1]))
                    else:
                        # open layer in QGIS
                        xslyr = None
                        xslyr = QgsVectorLayer(outUri, outlyr, 'ogr')
                        success = xslyr.isValid()
                        if not success:
                            QMessageBox.critical(self, 'Arch Bridge', 'Error opening cross section layer in QGIS')
                        else:
                            QgsProject.instance().addMapLayer(xslyr)

            xsSuccess = success

            # write out csv
            answer = QT_MESSAGE_BOX_YES
            if csvPath.exists():
                answer = QMessageBox.question(self, 'Arch Bridge', '{0}\nalready exists. Overwrite file?'.format(csvPath),
                                              QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO | QT_MESSAGE_BOX_CANCEL)
                if answer == QT_MESSAGE_BOX_CANCEL:
                    return
            if answer == QT_MESSAGE_BOX_YES:
                if not csvPath.parent.exists():
                    csvPath.parent.mkdir(parents=True)
                while 1:
                    try:
                        with csvPath.open('w') as f:
                            model = self.twChannel.model()
                            f.write('X,Z\n')
                            for i in range(self.twChannel.rowCount()):
                                f.write('{0},{1}\n'.format(*[model.index(i, j).data() for j in range(2)]))
                        break
                    except (PermissionError):
                        answer = QMessageBox.question(self, 'Arch Bridge',
                                                      '{0}\nis currently locked by another process. Retry?'.format(
                                                          csvPath),
                                                      QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO | QT_MESSAGE_BOX_CANCEL)
                        if answer == QT_MESSAGE_BOX_CANCEL:
                            return
                        elif answer == QT_MESSAGE_BOX_NO:
                            break
                    except Exception as e:
                        QMessageBox.critical(self, 'Arch Bridge', '{0}\nunexpected error writing data'.format(csvPath))
                        break

        # bridge name
        i_id = 1 if nwklyr.storageType() == 'GPKG' else 0
        i_bridge = i_id + 10
        if self.leBridgeName.text():
            bridgeName = self.leBridgeName.text()
        elif nwkFeat[i_bridge] != NULL and nwkFeat[i_bridge].strip():
            bridgeName = Path(nwkFeat[i_bridge]).with_suffix('').name
        elif nwkFeat[i_id] != NULL and nwkFeat[i_id].strip():
            bridgeName = nwkFeat[i_id]
        else:
            QMessageBox.critical(self, 'Arch Bridge', 'No valid ID for bridge found')
            return

        bridgeSuccess = True
        success = True
        if not nwklyr.isEditable():
            success = nwklyr.startEditing()
        if not success:
            QMessageBox.critical(self, 'Arch Bridge', 'Could not open the layer for editing')
            return

        # id
        if nwkFeat[i_id] == NULL or not nwkFeat[i_id].strip():
            success = nwkFeat.setAttribute(i_id, bridgeName)
            if not success:
                nwklyr.commitChanges()
                QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge id')

        # type
        if success:
            success = nwkFeat.setAttribute(i_id+1, 'BArch')
            if not success:
                nwklyr.commitChanges()
                QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge type')
                return

        # invert
        if success:
            if nwkFeat[i_id+6] == NULL:
                success = nwkFeat.setAttribute(i_id+6, -99999.)
                if not success:
                    nwklyr.commitChanges()
                    QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge US_Invert')
                    return
            if nwkFeat[i_id+7] == NULL:
                success = nwkFeat.setAttribute(i_id+7, -99999.)
                if not success:
                    nwklyr.commitChanges()
                    QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge DS_Invert')
                    return

        # inlet type
        lyrPath = Path(re.split(r'\|layer=', lyr.dataProvider().dataSourceUri(), flags=re.IGNORECASE)[0])
        if nwkFeat[i_bridge] != NULL and nwkFeat[i_bridge].strip():
            bridgeAttrText = nwkFeat[i_bridge].strip()
            csvPath = (lyrPath.parent / bridgeAttrText).resolve()
            self.leBridgeName.setText(csvPath.stem)
        else:
            if self.bridge_csv_loc_in_place.isChecked():
                csvPath = (lyrPath.parent / bridgeName).with_suffix('.csv')
                bridgeAttrText = csvPath.name
            elif self.bridge_csv_loc_csv_folder.isChecked():
                csvPath = (lyrPath.parent.parent / 'csv' / bridgeName).with_suffix('.csv')
                bridgeAttrText = '..{0}csv{0}{1}'.format(os.sep, csvPath.name)
            else:
                custom_path = Path(self.leCustomName.text().strip())
                if custom_path.suffix:
                    custom_path = custom_path.parent
                csvPath = (lyrPath.parent / custom_path / bridgeName).with_suffix('.csv')
                bridgeAttrText = os.path.relpath(csvPath, lyrPath.parent)
        if success:
            success = nwkFeat.setAttribute(i_bridge, bridgeAttrText)
            if not success:
                nwklyr.commitChanges()
                QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge Inlet_Type')
                return

        # calibration coefficient
        if self.sbCalibCoeff.value() != 1.:
            if success:
                success = nwkFeat.setAttribute(i_id+14, self.sbCalibCoeff.value())
                if not success:
                    nwklyr.commitChanges()
                    QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge calib coeff (Height attribute)')
                    return

        # skew
        if self.sbSkewAngle.value() != 0.:
            if success:
                success = nwkFeat.setAttribute(i_id+13, self.sbSkewAngle.value())
                if not success:
                    nwklyr.commitChanges()
                    QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge skew angle (Width attribute)')
                    return

        if self.gbOrificeFlow.isChecked():
            if success:
                success = nwkFeat.setAttribute(i_id+16, self.sbDischargeCoef.value()*-1)
                if not success:
                    nwklyr.commitChanges()
                    QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge discharge coeff (HConF attribute)')
                    return

            if success:
                success = nwkFeat.setAttribute(i_id+18, self.sbLowerTransDepth.value())
                if not success:
                    nwklyr.commitChanges()
                    QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge lower transition depth (EntryC attribute)')
                    return

            if success:
                success = nwkFeat.setAttribute(i_id+19, self.sbUpperTransDepth.value())
                if not success:
                    nwklyr.commitChanges()
                    QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge upper transition depth (ExitC attribute)')
                    return
        else:
            if success:
                success = nwkFeat.setAttribute(i_id + 16, 0)
                if not success:
                    nwklyr.commitChanges()
                    QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge discharge coeff (HConF attribute)')
                    return

            if success:
                success = nwkFeat.setAttribute(i_id+18, 0.)
                if not success:
                    nwklyr.commitChanges()
                    QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge lower transition depth (EntryC attribute)')
                    return

            if success:
                success = nwkFeat.setAttribute(i_id+19, 0.)
                if not success:
                    nwklyr.commitChanges()
                    QMessageBox.critical(self, 'Arch Bridge', 'Could not edit bridge upper transition depth (ExitC attribute)')
                    return

        if success:
            success = nwklyr.updateFeature(nwkFeat)
            if not success:
                nwklyr.commitChanges()
                QMessageBox.critical(self, 'Arch Bridge', 'Unable to update bridge feature')
                return

        if success:
            success = nwklyr.commitChanges()
            if not success:
                QMessageBox.critical(self, 'Arch Bridge', 'Unable to save updates to bridge feature')
                return

        bridgeSuccess = success

        # write out csv
        if self.twBridge.rowCount():
            answer = QT_MESSAGE_BOX_YES
            if csvPath.exists():
                answer = QMessageBox.question(self, 'Arch Bridge', '{0}\nalready exists. Overwrite file?'.format(csvPath),
                                              QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO | QT_MESSAGE_BOX_CANCEL)
                if answer == QT_MESSAGE_BOX_CANCEL:
                    return
            if answer == QT_MESSAGE_BOX_YES:
                model = self.twBridge.model()
                if not csvPath.parent.exists():
                    csvPath.parent.mkdir(parents=True)
                while 1:
                    try:
                        with csvPath.open('w') as f:
                            f.write('Start,Finish,Springing Level,Soffit Level\n')
                            for i in range(self.twBridge.rowCount()):
                                f.write('{0},{1},{2},{3}\n'.format(*[model.index(i,j).data() for j in range(self.twBridge.columnCount())]))
                        break
                    except (PermissionError):
                        answer = QMessageBox.question(self, 'Arch Bridge', '{0}\nis currently locked by another process. Retry?'.format(csvPath),
                                                      QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO | QT_MESSAGE_BOX_CANCEL)
                        if answer == QT_MESSAGE_BOX_CANCEL:
                            return
                        elif answer == QT_MESSAGE_BOX_NO:
                            break
                    except Exception as e:
                        QMessageBox.critical(self, 'Arch Bridge', '{0}\nUnexpected error writing file: {1}'.format(csvPath, e))
                        break

        # set xs layer to new layer
        self.populateLayerComboBoxes()
        for lyrid, lyr_ in QgsProject.instance().mapLayers().items():
            if lyr_ is xslyr:
                self.cboXsLayer.setCurrentText(lyr_.name())
                break

        self.cboNwkFeatureChanged(None, True, True)

        if not bridgeSuccess and xsSuccess:
            QMessageBox.warning(self, 'Arch Bridge',
                                'Finished running Arch Bridge tool... errors occurred processing/writing both '
                                'the cross-section and bridge data')
        elif not xsSuccess:
            QMessageBox.warning(self, 'Arch Bridge', 'Finished running Arch Bridge tool... errors occurred '
                                                     'processing/writing the cross-section data')
        elif not bridgeSuccess:
            QMessageBox.warning(self, 'Arch Bridge', 'Finished running Arch Bridge tool... errors occurred '
                                                     'processing/writing the bridge data')
        else:
            QMessageBox.information(self, 'Arch Bridge', 'Successfully ran Arch Bridge tool')

    def getFeatureFromCbo(self, lyr, new_lyr):
        fid = list(self.fid2nwklyr)[self.cboNwkFeature.currentIndex()]
        feat = lyr.getFeature(fid)
        if not feat:
            i = self.cboNwkFeature.currentIndex()
            self.populateFeatureCombobox(self.cboNwkLayer.currentIndex())
            self.cboNwkFeature.setCurrentIndex(i)
            fid = list(self.fid2nwklyr)[self.cboNwkFeature.currentIndex()]
            feat = [f for f in lyr.getFeatures() if f.id() == fid]

        if not feat:
            return None

        if lyr == new_lyr:
            return feat

        i_id = 1 if '.gpkg|layername=' in lyr.dataProvider().dataSourceUri() else 0
        id_ = feat[i_id]
        field_name = lyr.fields()[i_id].name()

        feat_req = QgsFeatureRequest(QgsExpression('"{0}" = \'{1}\''.format(field_name, id_)))
        possible_feats = list(new_lyr.getFeatures(feat_req))
        if len(possible_feats) == 1:
            return possible_feats[0]

        geom = feat.geometry()
        for f in possible_feats:
            if geom.equals(f.geometry()):
                return f

    def startDrawing(self, dem: str) -> None:
        """Initialise the rubberband object."""
        
        if self.rubberBand is not None:
            self.iface.mapCanvas().scene().removeItem(self.rubberBand.rubberBand)
            for marker in self.rubberBand.lineMarkers:
                self.iface.mapCanvas().scene().removeItem(marker)
        
        layer = tuflowqgis_find_layer(dem)
        if layer is not None:
            self.rubberBand = RubberBand(self.iface.mapCanvas(), layer)
            self.rubberBand.finishedDrawing.connect(self.finishDrawing)
            
    def finishDrawing(self) -> None:
        """
        Populate elevation from rubberband object
        in channel table.
        """
        
        self.rubberBand.finishedDrawing.disconnect()

        if len(self.rubberBand.linePoints) >= 2:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.rubberBand.linePoints]))
            spacing = max(self.rubberBand.layer.rasterUnitsPerPixelX(), self.rubberBand.layer.rasterUnitsPerPixelY())
            points, chainage, dir = lineToPoints(feat, spacing, self.iface.mapCanvas().mapUnits())
            elevations = []
            for p in points:
                elev = getRasterValue(p, self.rubberBand.layer)
                elevations.append(elev)

            self.importData(BridgeImport.Channel, chainage, elevations)

    def clearGraphic(self) -> None:
        """Clear rubberband line."""

        if self.rubberBand is not None:
            self.rubberBand.deleteLine()
    
    def openDemMenu(self) -> None:
        """Open DEM menu - List available DEMs."""

        menu = self.pbDem.menu()
        if menu is not None:
            menu.clear()
        else:
            menu = QMenu()
            
        self.actions = []
        dems = findAllRasterLyrs()
        for dem in dems:
            action = QAction(dem, menu)
            action.triggered.connect(lambda: self.startDrawing(dem))
            self.actions.append(action)
        menu.addActions(self.actions)
        self.pbDem.setMenu(menu)
        self.pbDem.showMenu()
        self.pbDem.setMenu(None)
    
    def openImportMenu(self) -> None:
        """Open import menu."""
        
        menu = QMenu()
        importChannelAction = QAction("Import Channel Data From Text File...", menu)
        importBridgeAction = QAction("Import Bridge Data From Text File...", menu)
        importFMAction = QAction("Import Data From FM .dat File...", menu)
        importChannelAction.triggered.connect(lambda: self.openImportDialog(BridgeImport.Channel))
        importBridgeAction.triggered.connect(lambda: self.openImportDialog(BridgeImport.Arch))
        importFMAction.triggered.connect(self.importFMDat)
        menu.addAction(importChannelAction)
        menu.addAction(importBridgeAction)
        menu.addAction(importFMAction)
        self.pbImport.setMenu(menu)
        self.pbImport.showMenu()
        self.pbImport.setMenu(None)

    def openBridgeCurveMenu(self) -> None:
        """Open bridge curve menu"""

        menu = QMenu()
        importCurveAction = QAction("Import Bridge Curve From EOF...", menu)
        plotCurveAction = QAction("Imported Curve Plot...", menu)
        tableCurveAction = QAction("Imported Curve Table...", menu)
        importCurveAction.triggered.connect(self.importBridgeCurveFromEOF)
        plotCurveAction.triggered.connect(self.plotBridgeCurve)
        tableCurveAction.triggered.connect(self.tableBridgeCurve)
        menu.addAction(importCurveAction)
        menu.addAction(plotCurveAction)
        menu.addAction(tableCurveAction)
        self.pbBridgeCurves.setMenu(menu)
        self.pbBridgeCurves.showMenu()
        self.pbBridgeCurves.setMenu(None)

    def importBridgeCurveFromEOF(self):
        """Import bridge curves from EOF file."""

        eof = browse(self, 'existing file', 'tuflow/arch_bridge_editor_eof',
                     'Import Bridge Curve From EOF', 'EOF (*.eof *.EOF)')

        if eof is None:
            return

        # scan eof for arch bridges
        self.eof.load(eof)
        if not self.eof.bridges:
            QMessageBox.information(self, 'Import Bridge Curve From EOF', 'No arch bridges found in EOF.')
            return

        bridge_list_dialog = ArchBridgeList(list(self.eof.bridges.keys()))
        bridge_list_dialog.exec()
        if not bridge_list_dialog.valid:
            return
        if not bridge_list_dialog.bridge_name:
            return
        bridge_name = bridge_list_dialog.bridge_name

        self.xsAreaCurve = self.eof.bridges[bridge_name][:,0:2]
        self.bridgeAreaCurve = np.append(self.eof.bridges[bridge_name][:,0:1],
                                         self.eof.bridges[bridge_name][:,2:3],
                                         axis=1)
        self.bridgeBlockageCurve = np.append(self.eof.bridges[bridge_name][:,0:1],
                                             self.eof.bridges[bridge_name][:,3:4],
                                             axis=1)

        if self.plot is not None:
            success = self.plot.setBridgeCurves(self.xsAreaCurve, self.bridgeAreaCurve, self.bridgeBlockageCurve)
            if success and self.plot.plot_curves:
                self.plot.drawPlot()
        if self.curvePlot is not None:
            success = self.curvePlot.setBridgeCurves(self.xsAreaCurve, self.bridgeAreaCurve, self.bridgeBlockageCurve)
            if success:
                self.curvePlot.drawPlot()

        QMessageBox.information(self, 'Import Bridge Curve From EOF',
                                'Successfully imported bridge curves for {0}'.format(bridge_name))

    def plotBridgeCurve(self):
        """View imported bridge curve as a table."""

        if self.xsAreaCurve is None or self.bridgeAreaCurve is None or self.bridgeBlockageCurve is None:
            QMessageBox.information(self, 'Bridge Curves', 'No bridge curves loaded')
            return

        if not self.xsAreaCurve.any() or not self.bridgeAreaCurve.any() or not self.bridgeBlockageCurve.any():
            QMessageBox.information(self, 'Bridge Curves', 'No bridge curves loaded')
            return

        if self.curvePlot is not None:
            self.curvePlot.accept()

        try:
            self.curvePlot = BridgePlot(self, (), (), (), (), (), (),
                                        self.xsAreaCurve, self.bridgeAreaCurve, self.bridgeBlockageCurve,
                                        plot_curves=True)
            self.curvePlot.finished.connect(self.curvePlotClosed)
            self.curvePlot.rejected.connect(self.curvePlotClosed)
            self.curvePlot.show()
        except Exception as e:
            label = QLabel()
            layout = QHBoxLayout()
            layout.addWidget(label)
            self.tabWidget.widget(0).layout().addLayout(layout)
            self.row2error[0] = (layout, label)
            self.setBridgeErrorText(label, 'Unexpected error while plotting: {0}'.format(e), True)
            return

    def tableBridgeCurve(self):
        """View bridge curves as a table"""

        if self.xsAreaCurve is None or self.bridgeAreaCurve is None or self.bridgeBlockageCurve is None:
            QMessageBox.information(self, 'Bridge Curves', 'No bridge curves loaded')
            return

        if not self.xsAreaCurve.any() or not self.bridgeAreaCurve.any() or not self.bridgeBlockageCurve.any():
            QMessageBox.information(self, 'Bridge Curves', 'No bridge curves loaded')
            return

        if self.bridgeCurveTable is not None:
            self.bridgeCurveTable.close()

        try:
            self.bridgeCurveTable = QDialog(self)
            layout = QVBoxLayout()
            self.bridgeCurveTable.setLayout(layout)
            table = BridgeCurveTable(None)
            layout.addWidget(table)
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(['Elevation', 'Unobstructed Area', 'Bridge Opening Area', 'Blockage'])
            table.horizontalHeader().setStretchLastSection(True)
            table.horizontalHeader().setDefaultSectionSize(128)
            table.setRowCount(self.xsAreaCurve.shape[0])
            table.setEditTriggers(QT_ABSTRACT_ITEM_VIEW_NO_EDIT_TRIGGERS)
            table.setAlternatingRowColors(True)
            model = table.model()
            for i in range(self.xsAreaCurve.shape[0]):
                model.setData(model.index(i, 0), self.xsAreaCurve[i, 0])
                model.setData(model.index(i, 1), self.xsAreaCurve[i, 1])
                model.setData(model.index(i, 2), self.bridgeAreaCurve[i, 1])
                model.setData(model.index(i, 3), self.bridgeBlockageCurve[i, 1])
            self.bridgeCurveTable.resize(QSize(table.horizontalHeader().length(), 600))
            self.bridgeCurveTable.finished.connect(self.curveTableClosed)
            self.bridgeCurveTable.rejected.connect(self.curveTableClosed)
            self.bridgeCurveTable.show()
        except Exception as e:
            label = QLabel()
            layout = QHBoxLayout()
            layout.addWidget(label)
            self.tabWidget.widget(0).layout().addLayout(layout)
            self.row2error[0] = (layout, label)
            self.setBridgeErrorText(label, 'Unexpected error while creating table: {0}'.format(e), True)
            return

    def curvePlotClosed(self) -> None:
        """Plot window is closed"""

        self.curvePlot = None

    def curveTableClosed(self) -> None:
        """Table window is closed"""

        self.bridgeCurveTable = None

    def importFMDat(self):
        """Import arch bridge data from a Flood Modeller DAT file"""


        dat = browse(self, 'existing file', 'TUFLOW/arch_bridge_editor_fmdat',
                     'Select FM DAT file', 'DAT (*.dat *.DAT)')

        if dat is None or not os.path.exists(dat):
            return

        # read dat and find arch bridges
        arch_bridges = fm_dat_parser(dat, ['BRIDGE'], ['ARCH'], None)
        if not arch_bridges:
            QMessageBox.information(self, 'Import Bridge', 'Did not find any arch bridges in {0}'.format(dat))
            return

        bridge_list_dialog = ArchBridgeList(arch_bridges)
        bridge_list_dialog.exec()
        if not bridge_list_dialog.valid:
            return
        if not bridge_list_dialog.bridge_name:
            return
        bridge_name = bridge_list_dialog.bridge_name

        bridge = fm_dat_parser(dat, ['BRIDGE'], ['ARCH'], bridge_name)
        if not bridge:
            QMessageBox.critical(self, 'Import Bridge', 'Unexpected error. Could not find bridge.')
            return
        bg = bridge[0]

        # clear cross section table and populate
        self.twChannel.setRowCount(0)
        self.twChannel.setRowCount(bg.xs.shape[0])
        model = self.twChannel.model()
        for i in range(bg.xs.shape[0]):
            for j in range(bg.xs.shape[1]):
                model.setData(model.index(i, j), bg.xs[i,j])

        # clear arch table and populate
        self.twBridge.setRowCount(0)
        self.twBridge.setRowCount(bg.arches.shape[0])
        model = self.twBridge.model()
        for i in range(bg.arches.shape[0]):
            for j in range(bg.arches.shape[1]):
                model.setData(model.index(i, j), bg.arches[i,j])

        # bridge name
        self.leChannelName.setText('xs_{0}'.format(bridge_name))
        self.leBridgeName.setText(bridge_name)

        # cc and skew
        self.sbCalibCoeff.setValue(bg.cc)
        self.sbSkewAngle.setValue(bg.skew)
        self.gbOrificeFlow.setChecked(bg.orifice_flag)
        self.sbDischargeCoef.setValue(bg.discharge_coefficient)
        self.sbLowerTransDepth.setValue(bg.lower_transition_depth)
        self.sbUpperTransDepth.setValue(bg.upper_transition_depth)

    def importData(self, importType: BridgeImport, col1: list = (),
                   col2: list = (), col3: list = (), col4: list = ()) -> None:
        """Import data to gui tables"""

        if importType == BridgeImport.Channel:
            self.clearChannelTable()
            for i, d in enumerate(col1):
                self.addChannelStation()
        
                # column 1
                item = self.twChannel.item(i, 0)
                item.setText('{0:.3f}'.format(d))
        
                # column 2
                if col2:
                    item = self.twChannel.item(i, 1)
                    item.setText('{0:.3f}'.format(col2[i]))
        
                # column 3
                if col3:
                    item = self.twChannel.item(i, 2)
                    item.setText('{0:.3f}'.format(col3[i]))
        elif importType == BridgeImport.Arch:
            self.clearBridgeTable()
            for i, d in enumerate(col1):
                self.addBridgeStation()
        
                # column 1
                item = self.twBridge.item(i, 0)
                item.setText('{0:.3f}'.format(d))
        
                # column 2
                if col2:
                    item = self.twBridge.item(i, 1)
                    item.setText('{0:.3f}'.format(col2[i]))
        
                # column 3
                if col3:
                    item = self.twBridge.item(i, 2)
                    item.setText('{0:.3f}'.format(col3[i]))
        
                # column 4
                if col4:
                    item = self.twBridge.item(i, 3)
                    item.setText('{0:.3f}'.format(col4[i]))
        
    def openImportDialog(self, event: BridgeImport = None) -> None:
        """Open the import dialog for bridge editor."""
        
        if event is not None:
            self.importDialog = BridgeEditorImportDialog(self.iface, event)
            self.importDialog.exec()
            if self.importDialog.imported:
                self.importData(event, self.importDialog.col1, self.importDialog.col2, self.importDialog.col3,
                                self.importDialog.col4)
    
    def plotBridge(self) -> None:
        """
        Plot channel data.
        Create bridge data and plot.
        """

        # clear any previous plotting errors
        for row, widgets in reversed(sorted(self.row2error.items())):
            layout = widgets[0]
            label = widgets[1]
            if 'plotting' in label.text():
                layout.removeWidget(label)
                label.deleteLater()
                label.setParent(None)
                count = self.tabWidget.widget(0).layout().count()
                layout = self.tabWidget.widget(0).layout().takeAt(count-1)
                layout.deleteLater()
                layout.setParent(None)
                del self.row2error[row]
        
        xData, yData, x2Data, y2Data, labels, bridges = [], [], [], [], [], []
        
        # channel
        if not self.twChannel.rowCount():
            return
        try:
            xy = self.getChannelData()
            if xy.any():
                xData.append(xy[:,0])
                yData.append(xy[:,1])
                labels.append('Channel')
            xy = self.getManningsData()
            if xy.any():
                x2Data.append(xy[:,0])
                y2Data.append(xy[:,1])
        except Exception as e:
            label = QLabel()
            layout = QHBoxLayout()
            layout.addWidget(label)
            self.tabWidget.widget(0).layout().addLayout(layout)
            self.row2error[0] = (layout, label)
            self.setBridgeErrorText(label, 'Unexpected plotting error in channel data: {0}'.format(e))
            return
        
        # bridge
        if self.row2error:
            QMessageBox.warning(self, 'Bridge Plot', 'Please fix bridge errors before plotting')
            return
        try:
            for i in range(self.twBridge.rowCount()):
                xy, bridge = self.getBridgeData(i)  # xy data including channel for patch, just bridge data
                if xy.any():
                    xData.append(xy[:,0])
                    yData.append(xy[:,1])
                    labels.append('Bridge')
                if bridge.any():
                    bridges.append(bridge)
        except Exception as e:
            label = QLabel()
            layout = QHBoxLayout()
            layout.addWidget(label)
            self.tabWidget.widget(0).layout().addLayout(layout)
            self.row2error[0] = (layout, label)
            self.setBridgeErrorText(label, 'Unexpected plotting error in bridge data: {0}'.format(e))
            return

        if self.plot is not None:
            self.plot.accept()

        try:
            self.plot = BridgePlot(self, xData, yData, x2Data, y2Data, labels, bridges,
                                   self.xsAreaCurve, self.bridgeAreaCurve, self.bridgeBlockageCurve)
            self.plot.finished.connect(self.plotClosed)
            self.plot.rejected.connect(self.plotClosed)
            self.plot.show()
        except Exception as e:
            label = QLabel()
            layout = QHBoxLayout()
            layout.addWidget(label)
            self.tabWidget.widget(0).layout().addLayout(layout)
            self.row2error[0] = (layout, label)
            self.setBridgeErrorText(label, 'Unexpected error while plotting: {0}'.format(e), True)
            return

    def plotClosed(self) -> None:
        """Plot window is closed"""

        self.plot = None

    def getBridgeData(self, row: int):
        """
        Get bridge data for plotting.
        Uses parabola equation: y = ax2 + bx + c
        using 3 (x, y) points to solve for 3 unknowns
        to generate arch curve of bridge.
        """

        x, y = [], []
        bridge = []  # only bridge data points
        
        # y = ax2 + bx + c
        model = self.twBridge.model()
        if self.twBridge.rowCount() >= row + 1:
            if self.twBridge.item(row, 0) is not None and self.twBridge.item(row, 1) is not None \
                    and self.twBridge.item(row, 2) is not None and self.twBridge.item(row, 3) is not None:
                try:
                    x1 = float(model.data(model.index(row, 0)))
                    y1 = float(model.data(model.index(row, 2)))
                    # x1 = float(self.twBridge.item(row, 0).text())
                    # y1 = float(self.twBridge.item(row, 2).text())

                    x2 = (float(model.data(model.index(row, 1))) + float(model.data(model.index(row, 0)))) / 2.0
                    y2 = float(model.data(model.index(row, 3)))
                    # x2 = (float(self.twBridge.item(row, 1).text()) + float(self.twBridge.item(row, 0).text())) / 2.0
                    # y2 = float(self.twBridge.item(row, 3).text())

                    x3 = float(model.data(model.index(row, 1)))
                    y3 = float(model.data(model.index(row, 2)))
                    # x3 = float(self.twBridge.item(row, 1).text())
                    # y3 = float(self.twBridge.item(row, 2).text())
                except ValueError:
                    x, y = [], []
                    return np.transpose(np.array([x, y]))
                except TypeError:
                    x, y = [], []
                    return np.transpose(np.array([x, y]))
                
                x = [x / 10000 for x in range(int(x1*10000), int(x3*10000), int(0.25 * 10000))]
                x.append(x3)
                for a in x:
                    y.append(getParabolicCoord(a, x1, x2, x3, y1, y2, y3))
                
                x.insert(0, x1)
                y.insert(0, self.getElevationAtStation(row, 0))
                x.append(x3)
                y.append(self.getElevationAtStation(row, 1))

                bridge = [(x[0], y[0]), (x1, y1), (x2, y2), (x3, y3), (x[-1], y[-1])]
                    
        return np.transpose(np.array([x, y])), np.array(bridge)
    
    def getChannelData(self) -> np.ndarray:
        """Returns the channel data as x, y list"""
        
        xy = []
        model = self.twChannel.model()
        for i in range(self.twChannel.rowCount()):
            if self.twChannel.item(i, 0) is not None and self.twChannel.item(i, 1) is not None:
                xy.append((float(model.data(model.index(i, 0))), float(model.data(model.index(i, 1)))))

        return np.array(xy)
    
    def getManningsData(self) -> np.ndarray:
        """Returns the manning's data as x, y list"""
        
        xy = []
        model = self.twChannel.model()
        for i in range(self.twChannel.rowCount()):
            if self.twChannel.item(i, 0) is not None and self.twChannel.item(i, 2) is not None:
                if i == 0:
                    xy.append((float(model.data(model.index(i, 0))), float(model.data(model.index(i, 2)))))
                elif i == self.twChannel.rowCount() - 1:
                    xy.append((float(model.data(model.index(i, 0))), float(model.data(model.index(i-1, 2)))))
                else:
                    xy.append((float(model.data(model.index(i, 0))), float(model.data(model.index(i-1, 2)))))
                    xy.append((float(model.data(model.index(i, 0))), float(model.data(model.index(i, 2)))))
                    
        return np.array(xy)
    
    def setBridgeErrorText(self, label: QLabel, text: str, wordWrap = False):
        """Sets the error text for the bridge section"""
        
        if not text:
            label.setVisible(False)
        else:
            label.setVisible(True)
            label.setTextFormat(QT_RICH_TEXT)
            label.setText(text)
            label.setWordWrap(wordWrap)
            palette = label.palette()
            palette.setColor(QT_PALETTE_WINDOW_TEXT, QT_RED)
            font = label.font()
            font.setItalic(True)
            label.setPalette(palette)
            label.setFont(font)
    
    def resizeTable(self) -> None:
        """Auto resize bridge section table"""

        self.twChannel.horizontalHeader().setSectionResizeMode(QT_HEADER_VIEW_STRETCH)
        self.twBridge.horizontalHeader().setSectionResizeMode(QT_HEADER_VIEW_STRETCH)
    
    def getElevationAtStation(self, row: int, col: int) -> float:
        """
        Return a cross section elevation at a given chainage value.
        Chainage value must be a value in the channel table,
        there is currently no interpolation.
        If more than one row in the table is found, will return the
        maximum elevation of chainage values.
        """
        
        # maxElev = None
        z = None
        model = self.twChannel.model()
        if self.twBridge.item(row, col) is not None and self.twBridge.model().data(model.index(row, col)) is not None \
                and self.twChannel.rowCount():
            # indexes = self.twBridge.findMatchingRowIndexes(row, col)
            # j = 0
            # for ind in indexes:
            #     if self.twChannel.item(ind, 1) is not None:
            #         #elev = float(self.twChannel.item(ind, 1).text())
            #         elev = float(model.data(model.index(ind, 1)))
            #         if j == 0:
            #             maxElev = elev
            #         else:
            #             maxElev = max(elev, maxElev)
            #         j += 1
            try:
                x = float(self.twBridge.model().index(row, col).data())
                a = np.array([[float(self.twChannel.model().index(i, 0).data()),
                               float(self.twChannel.model().index(i, 1).data())] for i in
                              range(self.twChannel.rowCount())])
                if np.where(a[:,0] == x)[0].shape[0] > 1:
                    z = -9e29
                    for i in np.where(a[:,0] == x)[0]:
                        z = max(z, a[i,1])
                    return z
                a = a[a[:, 0].argsort()]
                z = np.interp(x, a[:,0], a[:,1])
            except (ValueError, TypeError):
                pass
            
        return z

    def setMinimumBridgeLevels(self) -> None:
        """
        Sets the minimum value for the spinboxes in the
        bridge station table.
        """
        
        for i in range(self.twBridge.rowCount()):
            start = -99999
            elev = self.getElevationAtStation(i, 0)
            if elev is not None:
                start = elev
                
            finish = -99999
            elev = self.getElevationAtStation(i, 1)
            if elev is not None:
                finish = elev
            
            minimum = max(start, finish)
            self.twBridge.setMinimum(minimum, i, 2)
            self.twBridge.setMinimum(minimum, i, 3)
    
    def checkBridgeStationIncreases(self, row: int = -1, column: int = -1) -> None:
        """Checks that the finish (m) station is greater than start (m) station."""

        for row, widgets in reversed(sorted(self.row2error.items())):
            layout = widgets[0]
            label = widgets[1]
            layout.removeWidget(label)
            label.deleteLater()
            label.setParent(None)
            count = self.tabWidget.widget(0).layout().count()
            layout = self.tabWidget.widget(0).layout().takeAt(count-1)
            layout.deleteLater()
            layout.setParent(None)
            
        self.row2error.clear()

        j = 0
        for i in range(self.twBridge.rowCount()):
            if self.twBridge.item(i, 0) is not None and self.twBridge.item(i, 1) is not None:
                if self.twBridge.item(i, 0).text() and self.twBridge.item(i, 1).text():
                   if float(self.twBridge.item(i, 1).text()) <= float(self.twBridge.item(i, 0).text()):
                        j += 1
                        label = QLabel()
                        layout = QHBoxLayout()
                        layout.addWidget(label)
                        self.tabWidget.widget(0).layout().addLayout(layout)
                        self.row2error[j] = (layout, label)
                        self.setBridgeErrorText(label,
                                                'Error [Row {0}]: "Finish (m)" Station Must '
                                                'be Greater Than "Start (m)" Station'.format(i+1))
                if i == 0:
                    if self.twBridge.item(i, 1) is not None:
                        finishPrev = self.twBridge.item(i, 1).text()
                else:
                    if self.twBridge.item(i, 1) is not None:
                        if self.twBridge.item(i, 0).text() and finishPrev:
                            if float(self.twBridge.item(i, 0).text()) < float(finishPrev):
                                j += 1
                                label = QLabel()
                                layout = QHBoxLayout()
                                layout.addWidget(label)
                                self.tabWidget.widget(0).layout().addLayout(layout)
                                self.row2error[j] = (layout, label)
                                self.setBridgeErrorText(label,
                                                        'Error [Row {0}]: "Start (m)" Station Must '
                                                        'be Greater Than or Equal To Previous '
                                                        'Row "Finish (m)" Station'.format(i + 1))
            if self.twBridge.item(i, 0) is None or not str(self.twBridge.model().index(0, 0).data()):
                j += 1
                label = QLabel()
                layout = QHBoxLayout()
                layout.addWidget(label)
                self.tabWidget.widget(0).layout().addLayout(layout)
                self.row2error[j] = (layout, label)
                self.setBridgeErrorText(label,
                                        'Error [Row {0}]: Missing Information '
                                        'in "Start (m)"'.format(i + 1))
            if self.twBridge.item(i, 1) is None or not str(self.twBridge.model().index(0, 1).data()):
                j += 1
                label = QLabel()
                layout = QHBoxLayout()
                layout.addWidget(label)
                self.tabWidget.widget(0).layout().addLayout(layout)
                self.row2error[j] = (layout, label)
                self.setBridgeErrorText(label,
                                        'Error [Row {0}]: Missing Information '
                                        'in "Finish (m)"'.format(i + 1))
            if self.twBridge.item(i, 2) is not None and self.twBridge.item(i, 3) is not None:
                if self.twBridge.item(i, 2).text() and self.twBridge.item(i, 3).text():
                    if float(self.twBridge.item(i, 2).text()) > float(self.twBridge.item(i, 3).text()):
                        j += 1
                        label = QLabel()
                        layout = QHBoxLayout()
                        layout.addWidget(label)
                        self.tabWidget.widget(0).layout().addLayout(layout)
                        self.row2error[j] = (layout, label)
                        self.setBridgeErrorText(label,
                                                'Error [Row {0}]: Soffit Level Must be Equal To or Greater'
                                                'Than Springing Level'.format(i + 1))

    def collectChannelTableRows(self):
        """"""

        self.channelTableRows.clear()

        for i in range(self.twChannel.rowCount()):
            item1 = QTableWidgetItem(0)
            if self.twChannel.item(i, 0) is not None:
                item1.setText('{0:.03f}'.format(float(self.twChannel.model().index(i, 0).data())))
            item2 = QTableWidgetItem(0)
            if self.twChannel.item(i, 1) is not None:
                item2.setText('{0:.03f}'.format(float(self.twChannel.model().index(i, 1).data())))
            item3 = QTableWidgetItem(0)
            if self.twChannel.item(i, 2) is not None:
                item3.setText('{0:.03f}'.format(float(self.twChannel.model().index(i, 2).data())))
            channelTableRow = [item1, item2, item3]
            self.channelTableRows.append(channelTableRow)

    def channelTableChanged(self) -> None:
        """
        Set the options in the bridge station table to reflect
        changes made to the channel section table.
        """

        # recollect channel table rows - need to do this in-case the change was made by copy/paste
        self.collectChannelTableRows()

        items = []
        model = self.twChannel.model()
        for i in range(self.twChannel.rowCount()):
            if self.twChannel.item(i, 0) is not None:
                try:
                    item = '{0:.03f}'.format(float(model.data(model.index(i, 0))))
                    items.append(item)
                except ValueError:
                    continue

        # self.twBridge.itemDelegateForColumn(0).setItems(items)
        # self.twBridge.itemDelegateForColumn(1).setItems(items)
        # for i in range(self.twBridge.rowCount()):
        #     self.twBridge.customUpdate(i)

    def bridgeTableChanged(self) -> None:
        """
        Re-add the bridge items into member
        """

        self.bridgeTableRows.clear()

        for i in range(self.twBridge.rowCount()):
            item1 = QTableWidgetItem(0)
            if self.twBridge.item(i, 0) is not None and self.twBridge.item(i, 0).text():
                item1.setText('{0:.03f}'.format(float(self.twBridge.model().index(i, 0).data())))
            item2 = QTableWidgetItem(0)
            if self.twBridge.item(i, 1) is not None and self.twBridge.item(i, 1).text():
                item2.setText('{0:.03f}'.format(float(self.twBridge.model().index(i, 1).data())))
            item3 = QTableWidgetItem(0)
            if self.twBridge.item(i, 2) is not None and self.twBridge.item(i, 2).text():
                item3.setText('{0:.03f}'.format(float(self.twBridge.model().index(i, 2).data())))
            item4 = QTableWidgetItem(0)
            if self.twBridge.item(i, 3) is not None and self.twBridge.item(i, 3).text():
                item4.setText('{0:.03f}'.format(float(self.twBridge.model().index(i, 3).data())))
            bridgeTableRow = [item1, item2, item3, item4]
            self.bridgeTableRows.append(bridgeTableRow)

    def contextMenuBridgeTable(self) -> None:
        """
        Context menu for bridge table - right click on row number
        gives option to delete, insert before, insert after.
        """
    
        self.twBridge.verticalHeader().setContextMenuPolicy(QT_CUSTOM_CONTEXT_MENU)
        # self.twBridge.verticalHeader().customContextMenuRequested.connect(self.bridgeTableMenu)

    def bridgeTableMenu(self, pos: QPoint) -> None:
        """
        Prepare the context menu for the channel section table.
        """
    
        self.bridgeTableMenu = QMenu()
        self.bridgeTableInsertRowBefore = QAction("Insert Above", self.bridgeTableMenu)
        self.bridgeTableInsertRowAfter = QAction("Insert Below", self.bridgeTableMenu)
        self.bridgeTableDeleteRow = QAction("Delete", self.bridgeTableMenu)
    
        index = self.twBridge.rowAt(pos.y())
        self.bridgeTableInsertRowBefore.triggered.connect(lambda: self.insertBridgeStation(index, Table.Before))
        self.bridgeTableInsertRowAfter.triggered.connect(lambda: self.insertBridgeStation(index, Table.After))
        self.bridgeTableDeleteRow.triggered.connect(lambda: self.removeBridgeStation(index))
    
        self.bridgeTableMenu.addAction(self.bridgeTableInsertRowBefore)
        self.bridgeTableMenu.addAction(self.bridgeTableInsertRowAfter)
        self.bridgeTableMenu.addSeparator()
        self.bridgeTableMenu.addAction(self.bridgeTableDeleteRow)
    
        posH = self.twBridge.mapToGlobal(pos).x()
        posV = self.twBridge.mapToGlobal(pos).y() + \
               self.bridgeTableMenu.actionGeometry(self.bridgeTableInsertRowBefore).height()
        newPos = QPoint(posH, int(posV))
        self.bridgeTableMenu.popup(newPos, self.bridgeTableInsertRowBefore)
    
    def addBridgeStation(self) -> None:
        """Add a row to the bridge table."""

        items = []
        model = self.twChannel.model()
        for i in range(self.twChannel.rowCount()):
            if self.twChannel.item(i, 0) is not None:
                try:
                    item = '{0:.03f}'.format(float(model.data(model.index(i, 0))))
                    items.append(item)
                except ValueError:
                    continue
                # item = self.twChannel.item(i, 0).text()
                # items.append(item)

        rowNo = self.twBridge.rowCount()
        rowCount = rowNo + 1
        self.twBridge.setRowCount(rowCount)

        if rowNo >= 1:
            value1 = str(self.twBridge.model().data(self.twBridge.model().index(rowNo - 1, 0)))
            value2 = str(self.twBridge.model().data(self.twBridge.model().index(rowNo - 1, 1)))
            value3 = str(self.twBridge.model().data(self.twBridge.model().index(rowNo - 1, 2)))
            value4 = str(self.twBridge.model().data(self.twBridge.model().index(rowNo - 1, 3)))
        else:
            value1 = '0.000'
            value2 = '0.000'
            value3 = '0.000'
            value4 = '0.000'

        item1 = QTableWidgetItem(0)
        item1.setText(value1)
        item2 = QTableWidgetItem(0)
        item2.setText(value2)
        item3 = QTableWidgetItem(0)
        item3.setText(value3)
        item4 = QTableWidgetItem(0)
        item4.setText(value4)
        bridgeTableRow = [item1, item2, item3, item4]
        self.bridgeTableRows.append(bridgeTableRow)
    
        self.twBridge.setItem(rowNo, 0, item1)
        # self.twBridge.itemDelegateForColumn(0).setItems(items)
        self.twBridge.setItem(rowNo, 1, item2)
        # self.twBridge.itemDelegateForColumn(1).setItems(items)
        self.twBridge.setItem(rowNo, 2, item3)
        self.twBridge.setItem(rowNo, 3, item4)

    def insertBridgeStation(self, index: int = -1, loc: Table = Table.Before):
        """
        Insert a row into the bridge table.
        Can be inserted before or after clicked row.
        """

        self.twBridge.cellChanged.disconnect(self.bridgeTableChanged)

        if index != -1:
            for i, bridgeTableRow in enumerate(self.bridgeTableRows):
                item1 = QTableWidgetItem(0)
                item1.setText(bridgeTableRow[0].text())
                item2 = QTableWidgetItem(0)
                item2.setText(bridgeTableRow[1].text())
                item3 = QTableWidgetItem(0)
                item3.setText(bridgeTableRow[2].text())
                item4 = QTableWidgetItem(0)
                item4.setText(bridgeTableRow[3].text())
                bridgeTableRow = [item1, item2, item3, item4]
                self.bridgeTableRows[i] = bridgeTableRow
        
            if loc == Table.Before:
                j = index
            else:
                j = index + 1
            item1 = QTableWidgetItem(0)
            item2 = QTableWidgetItem(0)
            item3 = QTableWidgetItem(0)
            item3.setText("0.001")
            item4 = QTableWidgetItem(0)
            item3.setText("0.001")
            bridgeTableRow = [item1, item2, item3, item4]
            self.bridgeTableRows.insert(j, bridgeTableRow)
        
            self.reAddBridgeStations()

        self.twBridge.cellChanged.connect(self.bridgeTableChanged)

    def reAddBridgeStations(self) -> None:
        """Re-adds all bridge station data in table."""

        self.twBridge.setRowCount(0)
    
        for i, bridgeTableRow in enumerate(self.bridgeTableRows):
            rowNo = i
            rowCount = i + 1
        
            self.twBridge.setRowCount(rowCount)
        
            self.twBridge.setItem(rowNo, 0, bridgeTableRow[0])
            self.twBridge.setItem(rowNo, 1, bridgeTableRow[1])
            self.twBridge.setItem(rowNo, 2, bridgeTableRow[2])
            self.twBridge.setItem(rowNo, 3, bridgeTableRow[3])

    def removeBridgeStation(self, index: int = -1) -> None:
        """
        Remove row(s) from bridge section table.
        Will remove selected rows, or if now rows are
        selected, will remove the last entry.
        """

        selectionRange = self.twBridge.selectedRanges()
        selectionRange = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRange]
        selectionRange = sum(selectionRange, [])
        if index != -1 and index is not False:
            if index not in selectionRange:
                selectionRange = [index]
    
        if selectionRange:
            for i, bridgeTableRow in enumerate(self.bridgeTableRows):
                item1 = QTableWidgetItem(0)
                item1.setText(bridgeTableRow[0].text())
                item2 = QTableWidgetItem(0)
                item2.setText(bridgeTableRow[1].text())
                item3 = QTableWidgetItem(0)
                item3.setText(bridgeTableRow[2].text())
                item4 = QTableWidgetItem(0)
                item4.setText(bridgeTableRow[3].text())
                bridgeTableRow = [item1, item2, item3, item4]
                self.bridgeTableRows[i] = bridgeTableRow
            for i in reversed(selectionRange):
                self.bridgeTableRows.pop(i)
            self.reAddBridgeStations()
        else:
            if self.twBridge.rowCount():
                self.twBridge.setRowCount(self.twBridge.rowCount() - 1)
                self.bridgeTableRows.pop()
    
    def contextMenuChannelTable(self) -> None:
        """
        Context menu for channel table - right click on row number
        gives option to delete, insert before, insert after.
        """
        
        self.twChannel.verticalHeader().setContextMenuPolicy(QT_CUSTOM_CONTEXT_MENU)
        # self.twChannel.verticalHeader().customContextMenuRequested.connect(self.channelTableMenu)
        
    def channelTableMenu(self, pos: QPoint) -> None:
        """Prepare the context menu for the channel section table."""
        
        self.channelTableMenu = QMenu()
        self.channelTableInsertRowBefore = QAction("Insert Above", self.channelTableMenu)
        self.channelTableInsertRowAfter = QAction("Insert Below", self.channelTableMenu)
        self.channelTableDeleteRow = QAction("Delete", self.channelTableMenu)
        
        index = self.twChannel.rowAt(pos.y())
        self.channelTableInsertRowBefore.triggered.connect(lambda: self.insertChannelStation(index, Table.Before))
        self.channelTableInsertRowAfter.triggered.connect(lambda: self.insertChannelStation(index, Table.After))
        self.channelTableDeleteRow.triggered.connect(lambda: self.removeChannelStation(index))
        
        self.channelTableMenu.addAction(self.channelTableInsertRowBefore)
        self.channelTableMenu.addAction(self.channelTableInsertRowAfter)
        self.channelTableMenu.addSeparator()
        self.channelTableMenu.addAction(self.channelTableDeleteRow)

        posH = self.twChannel.mapToGlobal(pos).x()
        posV = self.twChannel.mapToGlobal(pos).y() + \
               self.channelTableMenu.actionGeometry(self.channelTableInsertRowBefore).height()
        newPos = QPoint(posH, int(posV))
        self.channelTableMenu.popup(newPos, self.channelTableInsertRowBefore)
        
    def insertChannelStation(self, index: int = -1, loc: Table = Table.Before):
        """
        Insert a row into the channel table.
        Can be inserted before or after clicked row.
        
        :param index: int
        :param loc: Table
        :return: void
        """

        self.twChannel.cellChanged.disconnect(self.channelTableChanged)
        
        if index != -1:
            for i, channelTableRow in enumerate(self.channelTableRows):
                item1 = QTableWidgetItem(0)
                item1.setText(channelTableRow[0].text())
                item2 = QTableWidgetItem(0)
                item2.setText(channelTableRow[1].text())
                item3 = QTableWidgetItem(0)
                item3.setText(channelTableRow[2].text())
                channelTableRow = [item1, item2, item3]
                self.channelTableRows[i] = channelTableRow
            
            if loc == Table.Before:
                j = index
            else:
                j = index + 1
            item1 = QTableWidgetItem(0)
            item1.setText("0.000")
            item2 = QTableWidgetItem(0)
            item2.setText("0.000")
            item3 = QTableWidgetItem(0)
            item3.setText("0.001")
            channelTableRow = [item1, item2, item3]
            self.channelTableRows.insert(j, channelTableRow)
            
            self.reAddChannelStations()

        self.twChannel.cellChanged.connect(self.channelTableChanged)
    
    def addChannelStation(self) -> None:
        """Add a row to the channel section table."""
        
        rowNo = self.twChannel.rowCount()
        rowCount = rowNo + 1
        self.twChannel.setRowCount(rowCount)
        
        item1 = QTableWidgetItem(0)
        item1.setText("0.000")
        item2 = QTableWidgetItem(0)
        item2.setText("0.000")
        item3 = QTableWidgetItem(0)
        item3.setText("0.001")
        channelTableRow = [item1, item2, item3]
        self.channelTableRows.append(channelTableRow)
        
        self.twChannel.setItem(rowNo, 0, item1)
        self.twChannel.setItem(rowNo, 1, item2)
        self.twChannel.setItem(rowNo, 2, item3)
        
    def reAddChannelStations(self) -> None:
        """Re-adds all channel station data in table."""

        self.twChannel.setRowCount(0)
        
        for i, channelTableRow in enumerate(self.channelTableRows):
            rowNo = i
            rowCount = i + 1

            self.twChannel.setRowCount(rowCount)

            self.twChannel.setItem(rowNo, 0, channelTableRow[0])
            self.twChannel.setItem(rowNo, 1, channelTableRow[1])
            self.twChannel.setItem(rowNo, 2, channelTableRow[2])
    
    def removeChannelStation(self, index: int = -1) -> None:
        """
        Remove row(s) from channel section table.
        Will remove selected rows, or if now rows are
        selected, will remove the last entry.
        """

        self.twChannel.cellChanged.disconnect(self.channelTableChanged)
        
        selectionRange = self.twChannel.selectedRanges()
        selectionRange = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRange]
        selectionRange = sum(selectionRange, [])
        if index != -1 and index is not False:
            if index not in selectionRange:
                selectionRange = [index]
        
        if selectionRange:
            for i, channelTableRow in enumerate(self.channelTableRows):
                item1 = QTableWidgetItem(0)
                item1.setText(channelTableRow[0].text())
                item2 = QTableWidgetItem(0)
                item2.setText(channelTableRow[1].text())
                item3 = QTableWidgetItem(0)
                item3.setText(channelTableRow[2].text())
                channelTableRow = [item1, item2, item3]
                self.channelTableRows[i] = channelTableRow
            for i in reversed(selectionRange):
                self.channelTableRows.pop(i)
            self.reAddChannelStations()
        else:
            if self.twChannel.rowCount():
                self.twChannel.setRowCount(self.twChannel.rowCount() - 1)
                self.channelTableRows.pop()

        self.twChannel.cellChanged.connect(self.channelTableChanged)
    
    def redErrorText(self, txt: str, lw: QListWidget) -> None:
        """Red text to add to the list widget."""

        item = QListWidgetItem(txt)
        font = item.font()
        font.setItalic(True)
        item.setFont(font)
        brush = item.foreground()
        brush.setColor(QT_RED)
        item.setForeground(brush)
        lw.addItem(item)
        lw.setSelectionMode(QT_ABSTRACT_ITEM_VIEW_NO_SELECTION)
        
    def greenGoodText(self, txt: str, lw: QListWidget) -> None:
        """Green text to add to the list widget."""

        item = QListWidgetItem(txt)
        font = item.font()
        item.setFont(font)
        brush = item.foreground()
        brush.setColor(QT_DARK_GREEN)
        item.setForeground(brush)
        lw.addItem(item)
        lw.setSelectionMode(QT_ABSTRACT_ITEM_VIEW_NO_SELECTION)
    
    def useSelection(self) -> None:
        """
        Sets the bridge feature combobox to the first selection found
        in the chosen 1D network layer.
        """
        
        if self.cboNwkLayer.currentIndex() > -1:
            layer = tuflowqgis_find_layer(self.cboNwkLayer.currentText())
            if layer is not None:
                name = ''
                for feat in layer.getSelectedFeatures():
                    name = feat.attribute(0)
                    break
                if name:
                    self.cboNwkFeature.setCurrentText(name)

    def selectFeatureInteractive(self):
        """Allow user to interactively select feature"""

        # is there a layer selected in cbo
        if not self.cboNwkLayer.currentText():
            QMessageBox.information(self, 'Select Feature', 'Select a 1d_nwk layer')
            return

        # retrieve layer
        lyr = tuflowqgis_find_layer(self.cboNwkLayer.currentText())
        if lyr is None:
            QMessageBox.warning(self, 'Select Feature', "Error finding {0} in workspace".format(self.cboNwkLayer.currentText()))
            return

        # make nwk layer active
        self.iface.setActiveLayer(lyr)
        self.selChangedSignal = lyr.selectionChanged.connect(self.processInteractiveSelection)
        self.iface.currentLayerChanged.connect(self.endInteractiveSelection)

        self.prevMapTool = self.iface.mapCanvas().mapTool()
        self.iface.actionSelect().trigger()

    def processInteractiveSelection(self, newSel, oldSel, clearAndSel):
        self.endInteractiveSelection()
        if not newSel:
            return

        # is there a layer selected in cbo
        if not self.cboNwkLayer.currentText():
            return

        # retrieve layer
        lyr = tuflowqgis_find_layer(self.cboNwkLayer.currentText())
        if lyr is None:
            return
        i_id = 1 if '.gpkg|layername=' in lyr.dataProvider().dataSourceUri() else 0

        fid = newSel[0]
        if fid not in self.fid2nwklyr:
            self.populateFeatureCombobox(self.cboNwkLayer.currentIndex())
        self.cboNwkFeature.setCurrentText(self.fid2nwklyr[newSel[0]])

    def endInteractiveSelection(self):
        if self.selChangedSignal is not None:
            if self.cboNwkLayer.currentText():
                lyr = tuflowqgis_find_layer(self.cboNwkLayer.currentText())
                if lyr is not None:
                    try:
                        lyr.selectionChanged.disconnect(self.selChangedSignal)
                    except Exception as e:
                        pass
                    self.selChangedSignal = None
                    try:
                        self.iface.currentLayerChanged.disconnect(self.endInteractiveSelection)
                    except Exception as e:
                        pass
                    if self.prevMapTool is not None:
                        self.iface.mapCanvas().setMapTool(self.prevMapTool)
                        self.prevMapTool = None
                    return

            # shouldn't get here but just in case loop through all layer and disconnect if possible
            for lyrid, lyr in QgsProject.instance().mapLayers():
                try:
                    lyr.selectionChanged.disconnect(self.selChangedSignal)
                except Exception as e:
                    pass
            self.selChangedSignal = None
            try:
                self.iface.currentLayerChanged.disconnect(self.endInteractiveSelection)
            except Exception as e:
                pass
            if self.prevMapTool is not None:
                self.iface.mapCanvas().setMapTool(self.prevMapTool)
                self.prevMapTool = None
    
    def populateLayerComboBoxes(self) -> None:
        """
        Populate layer comboboxes. Will only populate with
        layers starting with the corresponding type e.g. 1d_nwk.
        """

        self.disconnectAll()
        comboBoxes = {self.cboNwkLayer: (is1dNetwork, '1d_nwk', '1d_nwke'),
                      self.cboXsLayer: (is1dTable, '1d_xs', '1d_xz', '1d_cs', '1d_bg', '1d_lc', '1d_tab'),
                      self.cboXsLayerOut: (is1dTable, '1d_xs', '1d_xz', '1d_cs', '1d_bg', '1d_lc', '1d_tab')}
        currentText = {x: x.currentText() for x in comboBoxes}
        cbo_feat_text = self.cboNwkFeature.currentText()
        
        for cbo, types in comboBoxes.items():
            layers = []
            cbo.clear()
            if cbo == self.cboXsLayer:
                cbo.addItem('-None-')
            for id, layer in QgsProject.instance().mapLayers().items():
                for typ in types[1:]:
                    if typ in layer.name().lower() and types[0](layer):
                        if layer.name() not in layers:
                            layers.append(layer.name())

            cbo.addItems(layers)

            if currentText[cbo]:
                i = cbo.findText(currentText[cbo], QT_MATCH_EXACTLY)
                cbo.setCurrentIndex((i))
            else:
                if cbo == self.cboXsLayer:
                    cbo.setCurrentIndex(0)
                else:
                    cbo.setCurrentIndex(-1)

            if cbo == self.cboNwkLayer:
                self.populateFeatureCombobox(cbo.currentIndex())

            self.connectAll()
            
    def populateFeatureCombobox(self, index: int = -1) -> None:
        """
        Populate the feature combobox with features in the
        chosen 1d_nwk layer.
        """

        self.disconnectAll()

        # currentText = self.cboNwkFeature.currentText()
        currentFid = list(self.fid2nwklyr)[self.cboNwkFeature.currentIndex()] if self.cboNwkFeature.currentIndex() != -1 else None
        self.cboNwkFeature.clear()
        self.fid2nwklyr.clear()
        layer = None
        if index > -1:
            layer = tuflowqgis_find_layer(self.cboNwkLayer.itemText(index))
            if layer is None:
                return
            i_id = 0
            if '.gpkg|layername=' in layer.dataProvider().dataSourceUri():
                i_id = 1
            if layer is not None:
                for feat in layer.getFeatures():
                    name = feat.attribute(i_id)
                    if name != NULL and name.strip():
                        self.fid2nwklyr[feat.id()] = name
                    else:
                        self.fid2nwklyr[feat.id()] = 'Blank ID [feature id: {0}]'.format(feat.id())
                    self.cboNwkFeature.addItem(self.fid2nwklyr[feat.id()], feat)

        # self.cboNwkFeature.addItems(list(self.fid2nwklyr.values()))
        
        if currentFid is not None and currentFid in self.fid2nwklyr:
            self.cboNwkFeature.setCurrentText(self.fid2nwklyr[currentFid])
        else:
            self.cboNwkFeature.setCurrentIndex(-1)

        if layer is not None:
            self.editedNwkLayerSignal = layer.editCommandEnded.connect(lambda: self.populateFeatureCombobox(0))

        self.connectAll()

    def cboNwkFeatureChanged(self, e = None, processCrossSection = True, processBridge = True):
        """Try to find cross section and bridge data from feature"""


        # is there a feature selected in cbo
        if not self.cboNwkFeature.currentText():
            self.featMsgLabel_1.setText("No 1d_nwk bridge is selected")
            self.featMsgLabel_2.setVisible(False)
            return
        elif self.cboXsLayer.currentText() == '-None-':
            self.featMsgLabel_1.setText('Will create cross-section layer')
            if processCrossSection:
                return
        elif not self.cboXsLayer.currentText():
            self.featMsgLabel_1.setText('No 1d_xs layer is selected')

        # is there a layer selected in cbo
        if not self.cboNwkLayer.currentText():
            self.featMsgLabel_1.setText("No 1d_nwk layer is selected")
            self.featMsgLabel_2.setVisible(False)
            return

        # retrieve layer
        lyr = tuflowqgis_find_layer(self.cboNwkLayer.currentText())
        if lyr is None:
            self.featMsgLabel_1.setText("Error finding {0} in workspace".format(self.cboNwkLayer.currentText()))
            self.featMsgLabel_2.setVisible(False)
            return

        # index of ID field - gpkg layers will have FID as first field
        i_id = 1 if '.gpkg|layername=' in lyr.dataProvider().dataSourceUri().lower() else 0

        # retrieve feature
        fid = list(self.fid2nwklyr)[self.cboNwkFeature.currentIndex()]
        feat = [f for f in lyr.getFeatures() if f.id() == fid]
        if not feat:
            i = self.cboNwkFeature.currentIndex()
            self.populateFeatureCombobox(self.cboNwkLayer.currentIndex())
            self.cboNwkFeature.setCurrentIndex(i)
            fid = list(self.fid2nwklyr)[self.cboNwkFeature.currentIndex()]
            feat = [f for f in lyr.getFeatures() if f.id() == fid]
        # feats = [x[i_id] for x in lyr.getFeatures()]
        # count = feats.count(self.cboNwkFeature.currentText())
        # if count == 0:
        if not feat:
            self.featMsgLabel_1.setText("Error finding {0} in {1}".format(self.cboNwkFeature.currentText(), lyr.name()))
            self.featMsgLabel_2.setVisible(False)
            return
        feat = feat[0]

        if not processCrossSection:
            processCrossSection = not self.twChannel.rowCount()

        # find any intersecting cross sections
        self.xsFeat = None
        if processCrossSection:
            if self.editedXsLayerSignal is not None:
                for i in range(self.cboXsLayer.count()):
                    lyrXs = tuflowqgis_find_layer(self.cboXsLayer.itemText(i))
                    if lyrXs is None:
                        continue
                    try:
                        lyrXs.editCommandEnded.disconnect(self.editedXsLayerSignal)
                        self.editedXsLayerSignal = None
                        break
                    except Exception as e:
                        pass

            if self.cboXsLayer.currentText() == '-None-':
                for i in range(self.cboXsLayer.count()):
                    lyrXs = tuflowqgis_find_layer(self.cboXsLayer.itemText(i))
                    if lyrXs is None:
                        continue
                    featIntersects = self.findCrossSection(feat, lyrXs)
                    if featIntersects:
                        self.cboXsLayer.setCurrentIndex(i)
                        break

            if self.cboXsLayer.currentText() and self.cboXsLayer.currentText() != '-None-':
                lyrXs = tuflowqgis_find_layer(self.cboXsLayer.currentText())
                if lyrXs is None:
                    self.featMsgLabel_1.setText("Error finding {0} in workspace".format(self.cboXsLayer.currentText()))
                else:
                    featIntersects = self.findCrossSection(feat, lyrXs)
                    if featIntersects:
                        featIntersect = featIntersects[0]
                        i_source = 1 if '.gpkg|layername=' in lyr.dataProvider().dataSourceUri().lower() else 0
                        if len(featIntersects) > 1:
                            self.featMsgLabel_1.setText('WARNING more than one intersecting cross-section found... using {0}'
                                                        .format(self.fid2xslyr[featIntersect.id()]))
                        else:
                            self.featMsgLabel_1.setText('Found cross-section: {0}'.format(self.fid2xslyr[featIntersect.id()]))

                        # get cross section data
                        self.xsFeat = featIntersect
                        if featIntersect[i_source] == NULL or not featIntersect[i_source].strip():
                            self.featMsgLabel_1.setText('{0}... Blank "Source" attribute'.format(self.featMsgLabel_1.text()))
                        else:
                            lyrPath = Path(re.split(r'\|layer=', lyrXs.dataProvider().dataSourceUri(), flags=re.IGNORECASE)[0])
                            source = lyrPath.parent / featIntersect[i_source]
                            self.leChannelName.setText(source.with_suffix('').name)
                            if not source.exists():
                                self.featMsgLabel_1.setText('{0}... {1} does not exist'
                                                            .format(self.featMsgLabel_1.text(), source))
                            else:
                                args = [featIntersect[i] for i in range(featIntersect.fields().count())][i_source+1:i_source+9] + \
                                       [featIntersect]
                                xs = XS_Data(str(source.parent), source.name, *args)
                                if xs.error:
                                    self.featMsgLabel_1.setText('{0}... {1}'.format(self.featMsgLabel_1.text(), xs.message))
                                else:
                                    # add data to table
                                    self.clearChannelTable()
                                    self.twChannel.setRowCount(xs.np)
                                    model = self.twChannel.model()
                                    for i in range(xs.np):
                                        model.setData(model.index(i, 0), xs.x[i])
                                        model.setData(model.index(i, 1), xs.z[i])
                                        n = xs.mat[i] if xs.mat else 0.
                                        model.setData(model.index(i, 2), n)
                    else:
                        self.featMsgLabel_1.setText("No intersecting cross-section found")

                if lyrXs is not None:
                    self.editedXsLayerSignal = lyrXs.editCommandEnded.connect(lambda: self.cboNwkFeatureChanged(None, True, False))

        # find bridge data
        if processBridge:
            i_cc = i_id + 14
            i_sk = i_id + 13
            i_cd = i_id + 16
            i_rl = i_id + 18
            i_ru = i_id + 19
            if feat[i_cc] == 0. or feat[i_cc] == NULL:
                self.sbCalibCoeff.setValue(1.)
            else:
                self.sbCalibCoeff.setValue(feat[i_cc])
            if feat[i_sk] != NULL:
                self.sbSkewAngle.setValue(feat[i_sk])
            else:
                self.sbSkewAngle.setValue(0.)
            if feat[i_cd] != NULL and feat[i_cd] < 0.:
                self.sbDischargeCoef.setValue(abs(feat[i_cd]))
                self.gbOrificeFlow.setChecked(True)
            else:
                self.sbDischargeCoef.setValue(1.)
                self.gbOrificeFlow.setChecked(False)
            if feat[i_rl] != NULL:
                self.sbLowerTransDepth.setValue(feat[i_rl])
            if feat[i_ru] != NULL:
                self.sbUpperTransDepth.setValue(feat[i_ru])

            i_bridge = i_id + 10
            bridge = feat[i_bridge]
            if not bridge:
                self.featMsgLabel_2.setVisible(True)
                self.featMsgLabel_2.setText('Blank "Inlet_Type" attribute')
                return

            lyrPath = Path(re.split(r'\|layer=', lyr.dataProvider().dataSourceUri(), flags=re.IGNORECASE)[0])
            bridgeCsv = lyrPath.parent / bridge
            self.leBridgeName.setText(bridgeCsv.with_suffix('').name)
            if not bridgeCsv.exists():
                self.featMsgLabel_2.setVisible(True)
                self.featMsgLabel_2.setText('{0} does not exist'.format(bridgeCsv))
                return

            self.featMsgLabel_2.setVisible(True)
            self.featMsgLabel_2.setText('Found bridge data: {0}'.format(bridgeCsv.name))
            bridgeAttr = ArchBridge(bridgeCsv)
            if bridgeAttr.error:
                self.featMsgLabel_2.setVisible(True)
                self.featMsgLabel_2.setText('{0}... {1}'.format(self.featMsgLabel_2.Text(), bridgeAttr.msg))
                return

            self.clearBridgeTable()
            self.twBridge.setRowCount(bridgeAttr.nopenings)
            model = self.twBridge.model()
            for i in range(bridgeAttr.nopenings):
                model.setData(model.index(i, 0), bridgeAttr.openings[i].start)
                model.setData(model.index(i, 1), bridgeAttr.openings[i].end)
                model.setData(model.index(i, 2), bridgeAttr.openings[i].springing)
                model.setData(model.index(i, 3), bridgeAttr.openings[i].soffit)

    def findCrossSection(self, feat, lyr):
        """Find cross section intersect"""

        self.fid2xslyr.clear()
        featIntersects = []

        i_type = 2 if '.gpkg|layername=' in lyr.dataProvider().dataSourceUri() else 1
        i_source = i_type - 1
        for f in lyr.getFeatures():
            if f[i_type] == NULL or f[i_type].lower() == 'xz' or f[i_type].lower() == NULL:
                if f.geometry().intersects(feat.geometry()):
                    featIntersects.append(f)
                    if f[i_source] != NULL and f[i_source].strip():
                        self.fid2xslyr[f.id()] = f[i_source]
                    else:
                        self.fid2xslyr[f.id()] = 'Blank Source [feature id: {0}]'.format(f.id())

        return featIntersects
    
    def applyIcons(self) -> None:
        """Sets tool button icons."""
        
        addIcon = QgsApplication.getThemeIcon('mActionAdd.svg')
        remIcon = QgsApplication.getThemeIcon('symbologyRemove.svg')
        selIcon = QgsApplication.getThemeIcon('mActionSelectRectangle.svg')
        folIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
        addButtons = [self.btnAddChannelRow, self.btnAddBridgeRow]
        remButtons = [self.btnRemChannelRow, self.btnRemBridgeRow]
        selButtons = [self.bridgeBySelection]
        bwsButtons = [self.btnBrowseOutDatabase, self.btnBrowseOutFile]
        
        for b in addButtons:
            b.setIcon(addIcon)
            
        for b in remButtons:
            b.setIcon(remIcon)
            
        for b in selButtons:
            b.setIcon(selIcon)

        for b in bwsButtons:
            b.setIcon(folIcon)

    def graphicToVector(self) -> None:
        """Exports the graphic layer to a vector layer with attributes of a 1d_xz"""

        if self.rubberBand is None:
            QMessageBox.warning(self, 'Bridge Editor', 'No graphic layer to export.')
            return

        if len(self.rubberBand.linePoints) < 2:
            QMessageBox.warning(self, 'Bridge Editor', 'No graphic layer to export')
            return

        vectorFile = browse(
            parent=self,
            browseType='output file',
            key='TUFLOW/bridge_editor_graphic_to_vector',
            dialogName='Graphic to Vector File',
            fileType='GPKG (*.gpkg *.GPKG);;MIF (*.mif *.MIF);;SHP (*.shp *.SHP);;TAB (*.tab *.TAB)'
        )
        if vectorFile is None:
            return

        if not os.path.exists(os.path.dirname(vectorFile)):
            QMessageBox.critical(self, 'Bridge Editor', 'Directory does not exist: {0}'.format(os.path.dirname(vectorFile)))
            return

        crs = QgsProject.instance().crs()
        crsId = crs.authid()
        uri = 'linestring?crs={0}' \
              '&field=Source:string(50)' \
              '&field=Type:string(2)' \
              '&field=Flags:string(8)' \
              '&field=Column_1:string(8)' \
              '&field=Column_2:string(8)' \
              '&field=Column_3:string(8)' \
              '&field=Column_4:string(8)' \
              '&field=Column_5:string(8)' \
              '&field=Column_6:string(8)' \
              '&field=Z_Incremen:double(23,15)' \
              '&field=Z_Maximum:double(23,15)' \
              .format(crsId)
        vectorLayer = QgsVectorLayer(uri, os.path.splitext(os.path.basename(vectorFile))[0], 'memory')
        feat = QgsFeature()  # list of QgsFeature objects
        feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.rubberBand.linePoints]))
        error = vectorLayer.dataProvider().addFeatures([feat])
        vectorLayer.updateExtents()

        ext = os.path.splitext(vectorFile)[-1].lower()
        if ext == '.shp':
            driver = 'ESRI Shapefile'
        elif ext == '.mif' or ext == '.tab':
            driver = 'MapInfo File'
        elif ext == '.gpkg':
            driver = 'GPKG'
        else:
            QMessageBox.critical(self, 'Bridge Editor',
                                 'Vector file extension not recognised: {0}'.format(os.path.basename(vectorFile)))
            return
        status = QgsVectorFileWriter.writeAsVectorFormat(vectorLayer, vectorFile, 'CP1250', crs, driver)
        if status[0] != QgsVectorFileWriter.NoError:
            QMessageBox.critical(self, "Info", ("Error Creating: {0}\n{1}".format(*status)))
            return

        QgsProject.instance().addMapLayer(vectorLayer)
        self.clearGraphic()

    def clearChannelTable(self) -> None:
        """Clears the channel table"""

        self.channelTableRows.clear()
        self.twChannel.setRowCount(0)

    def clearBridgeTable(self) -> None:
        """Clears the bridge table"""

        self.bridgeTableRows.clear()
        self.twBridge.setRowCount(0)

    def reset(self) -> None:
        """
        Resets the dock back to initial conditions.
        Allows the user to clear the working and start a new bridge.
        """

        answer = QMessageBox.question(self, 'Bridge Editor', 'Reset inputs?', QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO | QT_MESSAGE_BOX_CANCEL)

        if answer == QT_MESSAGE_BOX_YES:
            # general data
            self.leChannelName.setText('')
            self.leBridgeName.setText('')

            # section data
            self.clearChannelTable()
            self.clearBridgeTable()

            # calib and skew
            self.sbCalibCoeff.setValue(0.)
            self.sbSkewAngle.setValue(0.)

            # orifice data
            self.gbOrificeFlow.setChecked(False)
            self.sbLowerTransDepth.setValue(0.)
            self.sbUpperTransDepth.setValue(0.)
            self.sbDischargeCoef.setValue(1.)

            # outputs
            # pass

            # inputs
            self.cboNwkFeature.setCurrentIndex(-1)
            self.cboXsLayer.setCurrentIndex(0)

    def outputTypeChanged(self):
        """Reconfigure the gui based on the output type"""

        b = self.cboOutputType.currentIndex() == 0

        self.label_9.setVisible(not b)
        self.cboXsLayerOut.setVisible(not b)
        self.label_4.setVisible(b)
        self.cboOutFormat.setVisible(b)
        self.label_5.setVisible(b)
        self.leOutDatabase.setVisible(b)
        self.btnBrowseOutDatabase.setVisible(b)
        self.label_11.setVisible(b)
        self.leOutName.setVisible(b)
        self.btnBrowseOutFile.setVisible(b)

        if self.cboOutputType.currentIndex() == 2:
            self.label_9.setVisible(False)
            self.cboXsLayerOut.setVisible(False)

        if b:
            self.outFormatChanged()

    def outFormatChanged(self):
        """Reconfigure the gui based on what the output format is selected"""

        b = self.cboOutFormat.currentIndex() == 0

        self.label_5.setVisible(not b)
        self.leOutDatabase.setVisible(not b)
        self.btnBrowseOutDatabase.setVisible(not b)
        self.btnBrowseOutFile.setVisible(b)
        self.label_11.setText('Output File: ') if b else self.label_11.setText('Layer Name:')

    def save_bridge_output_setting_in_place(self, e=None):
        QSettings().setValue('tuflow/arch_bridge_editor/bridge_save_setting', 'in_place')

    def save_bridge_output_setting_csv_folder(self, e=None):
        QSettings().setValue('tuflow/arch_bridge_editor/bridge_save_setting', 'csv_folder')

    def save_bridge_output_setting_custom_folder(self, e=None):
        QSettings().setValue('tuflow/arch_bridge_editor/bridge_save_setting', 'custom_folder')

    def save_bridge_output_setting_custom_folder_text(self, e=None):
        QSettings().setValue('tuflow/arch_bridge_editor/bridge_save_path', self.leCustomName.text())

    def save_xs_output_setting_in_place(self, e=None):
        QSettings().setValue('tuflow/arch_bridge_editor/xs_save_setting', 'in_place')

    def save_xs_output_setting_csv_folder(self, e=None):
        QSettings().setValue('tuflow/arch_bridge_editor/xs_save_setting', 'csv_folder')

    def save_xs_output_setting_custom_folder(self, e=None):
        QSettings().setValue('tuflow/arch_bridge_editor/xs_save_setting', 'custom_folder')

    def save_xs_output_setting_custom_folder_text(self, e=None):
        QSettings().setValue('tuflow/arch_bridge_editor/xs_save_path', self.leXSCustomName.text())

    def connectAll(self):
        """Connect signals"""

        if not self.connected:
            self.connected = True

            # what happends when layers are added or removed from workspace
            QgsProject.instance().layersAdded.connect(self.populateLayerComboBoxes)
            QgsProject.instance().layersRemoved.connect(self.populateLayerComboBoxes)

            # layers datasource is changed
            for layerid, layer in QgsProject.instance().mapLayers().items():
                layer.dataSourceChanged.connect(self.populateLayerComboBoxes)
                layer.nameChanged.connect(self.populateLayerComboBoxes)
                layer.configChanged.connect(self.populateLayerComboBoxes)

            # General Data tab
            # what happens when nwk layer combobox is updated
            self.cboNwkLayer.currentIndexChanged.connect(self.populateFeatureCombobox)

            # what happens when feature is changed or if xs layer is changed
            self.cboNwkFeatChangedSignal = self.cboNwkFeature.currentIndexChanged.connect(lambda: self.cboNwkFeatureChanged(None, False, True))
            self.cboXsFeatChangedSignal = self.cboXsLayer.currentIndexChanged.connect(lambda: self.cboNwkFeatureChanged(None, True, False))

            # reload buttons
            self.pbReloadBridgeClicked = self.pbReloadBridge.clicked.connect(lambda: self.cboNwkFeatureChanged(None, False, True))
            self.pbReloadCrossSectionClicked = self.pbReloadCrossSection.clicked.connect(lambda: self.cboNwkFeatureChanged(None, True, False))

            # use selected feature as nwk bridge
            self.bridgeBySelection.clicked.connect(self.selectFeatureInteractive)

            # context menus
            self.twChannel.verticalHeader().customContextMenuRequested.connect(self.channelTableMenu)
            self.twBridge.verticalHeader().customContextMenuRequested.connect(self.bridgeTableMenu)

            # channel table
            self.btnAddChannelRow.clicked.connect(self.addChannelStation)
            self.btnAddChannelRow.clicked.connect(self.channelTableChanged)
            self.btnRemChannelRow.clicked.connect(self.removeChannelStation)
            self.btnRemChannelRow.clicked.connect(self.channelTableChanged)
            self.twChannel.cellChanged.connect(self.channelTableChanged)
            # self.twChannel.cellChanged.connect(self.setMinimumBridgeLevels)

            # bridge table
            self.btnAddBridgeRow.clicked.connect(self.addBridgeStation)
            self.btnRemBridgeRow.clicked.connect(self.removeBridgeStation)
            self.btnRemBridgeRow.clicked.connect(self.checkBridgeStationIncreases)
            self.twBridge.cellChanged.connect(self.bridgeTableChanged)
            self.twBridge.cellChanged.connect(self.checkBridgeStationIncreases)
            # self.twBridge.cellChanged.connect(self.setMinimumBridgeLevels)

            # buttons next to tables
            self.pbPlot.clicked.connect(self.plotBridge)
            self.pbImport.clicked.connect(self.openImportMenu)
            self.pbDem.clicked.connect(self.openDemMenu)
            self.pbBridgeCurves.clicked.connect(self.openBridgeCurveMenu)

            # run button
            self.pbRun.clicked.connect(self.check)

            # reset button
            self.pbReset.clicked.connect(self.reset)

            # clear graphic
            self.pbClearGraphic.clicked.connect(self.clearGraphic)

            # clear table
            self.pbClearChannelTable.clicked.connect(self.clearChannelTable)

            # graphic to vector
            self.pbGraphicToVector.clicked.connect(self.graphicToVector)

            # output type changed
            self.cboOutputType.currentIndexChanged.connect(self.outputTypeChanged)

            # output format changed
            self.cboOutFormat.currentIndexChanged.connect(self.outFormatChanged)

            # browse buttons
            self.btnBrowseOutDbClicked = self.btnBrowseOutDatabase.clicked.connect(
                                                    lambda: browse(self, 'output database', "TUFLOW/import_empty_database",
                                                                   'Output Database', 'GPKG (*.gpkg *.GPKG)',
                                                                   self.leOutDatabase))
            self.btnBrowseOutFileClicked = self.btnBrowseOutFile.clicked.connect(lambda: browse(self, 'output file', 'TUFLOW/output_shpfile',
                                                                                 'Output File', 'Shapefile (*.shp *.SHP)',
                                                                                 self.leOutName))

            # setting buttons
            # bridge
            self.bridge_csv_loc_in_place.clicked.connect(self.save_bridge_output_setting_in_place)
            self.bridge_csv_loc_csv_folder.clicked.connect(self.save_bridge_output_setting_csv_folder)
            self.bridge_csv_loc_custom_folder.clicked.connect(self.save_bridge_output_setting_custom_folder)
            self.leCustomName.textChanged.connect(self.save_bridge_output_setting_custom_folder_text)
            # cross-section
            self.xs_csv_loc_in_place.clicked.connect(self.save_xs_output_setting_in_place)
            self.xs_csv_loc_csv_folder.clicked.connect(self.save_xs_output_setting_csv_folder)
            self.xs_csv_loc_custom_folder.clicked.connect(self.save_xs_output_setting_custom_folder)
            self.leXSCustomName.textChanged.connect(self.save_xs_output_setting_custom_folder_text)

    def disconnectAll(self) -> None:
        """Disconnects active signals"""

        if self.connected:
            self.connected = False

            if self.editedNwkLayerSignal is not None:
                for i in range(self.cboNwkLayer.count()):
                    lyr = tuflowqgis_find_layer(self.cboNwkLayer.itemText(i))
                    if lyr is None:
                        continue
                    try:
                        lyr.editCommandEnded.disconnect(self.editedNwkLayerSignal)
                    except Exception as e:
                        pass
                    finally:
                        self.editedNwkLayerSignal = None
                        break

            if self.editedXsLayerSignal is not None:
                for i in range(self.cboXsLayer.count()):
                    lyr = tuflowqgis_find_layer(self.cboXsLayer.itemText(i))
                    if lyr is None:
                        continue
                    try:
                        lyr.editCommandEnded.disconnect(self.editedXsLayerSignal)
                        self.editedXsLayerSignal = None
                        break
                    except Exception as e:
                        pass

            # what happends when layers are added or removed from workspace
            try:
                QgsProject.instance().layersAdded.disconnect(self.populateLayerComboBoxes)
            except:
                pass
            try:
                QgsProject.instance().layersRemoved.disconnect(self.populateLayerComboBoxes)
            except:
                pass

            # datasource changed
            for layerid, layer in QgsProject.instance().mapLayers().items():
                try:
                    layer.dataSourceChanged.disconnect(self.populateLayerComboBoxes)
                except:
                    pass
                try:
                    layer.nameChanged.disconnect(self.populateLayerComboBoxes)
                except:
                    pass
                try:
                    layer.configChanged.disconnect(self.populateLayerComboBoxes)
                except:
                    pass

            # General Data tab
            # what happens when nwk layer combobox is updated
            try:
                self.cboNwkLayer.currentIndexChanged.disconnect(self.populateFeatureCombobox)
            except:
                pass

            # what happens when feature is changed or if xs layer is changed
            if self.cboNwkFeatChangedSignal is not None:
                try:
                    self.cboNwkFeature.currentIndexChanged.disconnect(self.cboNwkFeatChangedSignal)
                except:
                    pass
                self.cboNwkFeatChangedSignal = None
            if self.cboXsFeatChangedSignal is not None:
                try:
                    self.cboXsLayer.currentIndexChanged.disconnect(self.cboXsFeatChangedSignal)
                except:
                    pass
                self.cboXsFeatChangedSignal = None

            # reload buttons
            if self.pbReloadBridgeClicked is not None:
                try:
                    self.pbReloadBridge.clicked.disconnect(self.pbReloadBridgeClicked)
                except:
                    pass
                self.pbReloadBridgeClicked = None
            if self.pbReloadCrossSectionClicked is not None:
                try:
                    self.pbReloadCrossSection.clicked.disconnect(self.pbReloadCrossSectionClicked)
                except:
                    pass
                self.pbReloadCrossSectionClicked = None

            # use selected feature as nwk bridge
            try:
                self.bridgeBySelection.clicked.disconnect(self.selectFeatureInteractive)
            except:
                pass

            # context menus
            try:
                self.twChannel.verticalHeader().customContextMenuRequested.disconnect(self.channelTableMenu)
            except:
                pass
            try:
                self.twBridge.verticalHeader().customContextMenuRequested.disconnect(self.bridgeTableMenu)
            except:
                pass

            # channel table
            try:
                self.btnAddChannelRow.clicked.disconnect(self.addChannelStation)
            except:
                pass
            try:
                self.btnAddChannelRow.clicked.disconnect(self.channelTableChanged)
            except:
                pass
            try:
                self.btnRemChannelRow.clicked.disconnect(self.removeChannelStation)
            except:
                pass
            try:
                self.btnRemChannelRow.clicked.disconnect(self.channelTableChanged)
            except:
                pass
            try:
                self.twChannel.cellChanged.disconnect(self.channelTableChanged)
            except:
                pass
            # try:
            #     self.twChannel.cellChanged.disconnect(self.setMinimumBridgeLevels)
            # except:
            #     pass

            # bridge table
            try:
                self.btnAddBridgeRow.clicked.disconnect(self.addBridgeStation)
            except:
                pass
            try:
                self.btnRemBridgeRow.clicked.disconnect(self.removeBridgeStation)
            except:
                pass
            try:
                self.btnRemBridgeRow.clicked.disconnect(self.checkBridgeStationIncreases)
            except:
                pass
            try:
                self.twBridge.cellChanged.disconnect(self.bridgeTableChanged)
            except:
                pass
            try:
                self.twBridge.cellChanged.disconnect(self.checkBridgeStationIncreases)
            except:
                pass
            # try:
            #     self.twBridge.cellChanged.disconnect(self.setMinimumBridgeLevels)
            # except:
            #     pass

            # buttons next to tables
            try:
                self.pbPlot.clicked.disconnect(self.plotBridge)
            except:
                pass
            try:
                self.pbImport.clicked.disconnect(self.openImportMenu)
            except:
                pass
            try:
                self.pbDem.clicked.disconnect(self.openDemMenu)
            except:
                pass
            try:
                self.pbBridgeCurves.clicked.disconnect(self.openBridgeCurveMenu)
            except:
                pass

            # run button
            try:
                self.pbRun.clicked.disconnect(self.check)
            except:
                pass

            # reset button
            try:
                self.pbReset.clicked.disconnect(self.reset)
            except:
                pass

            # clear graphic
            try:
                self.pbClearGraphic.clicked.connect(self.clearGraphic)
            except:
                pass

            # clear table
            try:
                self.pbClearChannelTable.clicked.disconnect(self.clearChannelTable)
            except:
                pass

            # graphic to vector
            try:
                self.pbGraphicToVector.clicked.disconnect(self.graphicToVector)
            except:
                pass

            # output type changed
            try:
                self.cboOutputType.currentIndexChanged.disconnect(self.outputTypeChanged)
            except:
                pass

            # output format changed
            try:
                self.cboOutFormat.currentIndexChanged.disconnect(self.outFormatChanged)
            except:
                pass

            # browse buttons
            if self.btnBrowseOutDbClicked is not None:
                try:
                    self.btnBrowseOutDatabase.clicked.disconnect(self.btnBrowseOutDbClicked)
                except:
                    pass
                self.btnBrowseOutDbClicked = None
            if self.btnBrowseOutFileClicked is not None:
                try:
                    self.btnBrowseOutFile.clicked.disconnect(self.btnBrowseOutFileClicked)
                except:
                    pass
                self.btnBrowseOutFileClicked = None