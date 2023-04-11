import re
import io
import numpy as np
from os.path import dirname, join
from PyQt5.QtWidgets import QDialog, QAction, QMenu, QApplication, QMessageBox, QWidget
from PyQt5.QtCore import pyqtSignal, QThread, QTimer, QSize, Qt
from PyQt5.QtGui import QImage, QIcon
from qgis.core import QgsVectorLayer, QgsApplication, QgsUnitTypes, Qgis, QgsRectangle
from qgis.gui import QgsRubberBand
from .DataCollector import DataCollector
from .ContinuityTool import ContinuityTool
from .FeatureData import FeatureData
from .Enumerators import *
from .FlowTraceLongPlot import DownstreamConnectivity
from .FlowTraceLongPlot_V2 import Connectivity, ContinuityLimits
from ..forms.flowtrace_plot_widget import Ui_flowTracePlotWidget
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from ..dataset_menu import DatasetMenu
from ..tuflowqgis_library import browse



class Annotation:

    def __init__(self, fig, ax, annot):
        self.fig = fig
        self.ax = ax
        self.annot = annot
        self.drawn = False
        self.pos_loaded = False
        self.bbox = None
        self.x0 = None
        self.x1 = None
        self.y0 = None
        self.y1 = None
        self.width = None
        self.height = None
        self.padw = None
        self.padh = None
        self.pad_ = None

    def update_position(self):
        if not self.drawn:
            self.annot.draw(self.fig.canvas.renderer)
            self.drawn = True
            self.bbox = self.annot.get_bbox_patch().get_bbox()
            self.pad_ = self.annot.get_bbox_patch()._bbox_transmuter.pad

        transform = self.annot.axes.transData.transform

        self.width = self.bbox.width
        self.height = self.bbox.height
        self.padw, self.padh = self.width * self.pad_, self.height * self.pad_
        self.x0, self.y1 = transform(self.annot.xy)
        self.x0 -= self.width / 2. - self.padw
        self.y1 -= self.padh
        self.x0 += self.annot.xyann[0]
        self.y1 += self.annot.xyann[1]
        self.x1, self.y0 = self.x0 + self.width + self.padw, self.y1 - self.height - self.padh

        self.pos_loaded = True

    def overlaps(self, annot_):
        if not self.pos_loaded or not annot_.pos_loaded:
            return False

        # return (annot_.x0 <= self.x0 <= annot_.x1 or annot_.x0 <= self.x1 <= annot_.x1) and \
        #        (annot_.y0 <= self.y0 <= annot_.y1 or annot_.y0 <= self.y1 < annot_.y1)

        return (self.x0 <= annot_.x0 <= self.x1 or self.x0 <= annot_.x1 <= self.x1) and \
               (self.y0 <= annot_.y0 <= self.y1 or self.y0 <= annot_.y1 < self.y1)

    def min_max(self):
        transform_inv = self.ax.transData.inverted().transform
        xmin, ymin = transform_inv((self.x0, self.y0))
        xmax, ymax = transform_inv((self.x1, self.y1))
        return xmin, xmax, ymin, ymax

class Annotations:
    START_OFFSET = 40
    MIN_OFFSET = 20
    MAX_OFFSET = 80
    OFFSET_INC = 10

    def __init__(self):
        self.annotations = []

    def append(self, annotation):
        self.annotations.append(annotation)

    def min_max(self, xmin, xmax):
        ymin, ymax = 9e29, -9e29
        for annot in self.annotations:
            xmin_, xmax_, ymin_, ymax_ = annot.min_max()
            if xmin <= xmin_ <= xmax or xmin <= xmax_ <= xmax:
                ymin, ymax = min(ymin, ymin_), max(ymax, ymax_)

        return ymin, ymax

    def try_no_overlap(self):
        for annot in self.annotations:
            annot.update_position()

        annotations = []
        for i, annot in enumerate(self.annotations):
            finished = False
            offset = -Annotations.START_OFFSET
            f = -1
            while 1:
                overlap = False
                for annot_ in annotations:
                    if annot == annot_:
                        continue
                    while annot.overlaps(annot_) and not finished:
                        overlap = True
                        offset += f * Annotations.OFFSET_INC
                        annot.annot.xyann = (0., offset)
                        annot.update_position()

                        if offset <= -Annotations.MAX_OFFSET - i:
                            f = 1
                            offset = -Annotations.START_OFFSET
                        if offset < 0 and offset >= -Annotations.MIN_OFFSET:
                            offset = Annotations.START_OFFSET
                        if offset >= Annotations.MAX_OFFSET:
                            finished = True

                if not overlap or finished:
                    break

            annotations.append(annot)



class FlowTraceTool(ContinuityTool):
    
    def __init__(self, iface=None, dataCollector=None, outputLyr=None, limitAngle=0, limitCover=99999, limitArea=100,
                 checkArea=False, checkAngle=False, checkInvert=False, checkCover=False, dataCollectorPoints=None):
        
        ContinuityTool.__init__(self, iface, dataCollector, outputLyr, limitAngle, limitCover, limitArea,
                                checkArea, checkAngle, checkInvert, checkCover)

        if self.ids_to_assess is not None:
            for_selection = {}
            for id_ in self.ids_to_assess:
                if id_ not in dataCollector.features:
                    continue

                feat = dataCollector.features[id_]
                if feat.layer not in for_selection:
                    for_selection[feat.layer] = []
                for_selection[feat.layer].append(feat.fid)

                if dataCollectorPoints is None:
                    continue

                vertex_us = '{0}0'.format(id_)
                vertex_ds = '{0}1'.format(id_)
                id_us = dataCollector.vertexes[vertex_us].point if vertex_us in dataCollector.vertexes else None
                id_ds = dataCollector.vertexes[vertex_ds].point if vertex_us in dataCollector.vertexes else None

                if id_us in dataCollectorPoints.features:
                    feat = dataCollectorPoints.features[id_us]
                    if feat.layer not in for_selection:
                        for_selection[feat.layer] = []
                    for_selection[feat.layer].append(feat.fid)

                if id_ds in dataCollectorPoints.features:
                    feat = dataCollectorPoints.features[id_ds]
                    if feat.layer not in for_selection:
                        for_selection[feat.layer] = []
                    for_selection[feat.layer].append(feat.fid)

            for layer, fids in for_selection.items():
                layer.selectByIds(fids, QgsVectorLayer.SetSelection)
        else:
            # also select all features in flow trace
            layers = []
            fids = []
            for id, fData in dataCollector.features.items():
                layer = fData.layer
                feature = fData.feature
                if layer not in layers:
                    layers.append(layer)
                    fids.append([])
                i = layers.index(layer)
                fids[i].append(feature.id())
            if dataCollectorPoints is not None:
                for id, fData in dataCollectorPoints.features.items():
                    layer = fData.layer
                    feature = fData.feature
                    if layer not in layers:
                        layers.append(layer)
                        fids.append([])
                    i = layers.index(layer)
                    fids[i].append(feature.id())
            
            for i, layer in enumerate(layers):
                layer.selectByIds(fids[i], QgsVectorLayer.SetSelection)


class DataCollectorFlowTrace(DataCollector):

    def collectData(self, inputs=(), dem=None, lines=(), lineDataCollector=None, exclRadius=15, tables=(),
                    startLocs=(), flowTrace=False):
        
        DataCollector.collectData(self, inputs, dem, lines, lineDataCollector, exclRadius, tables,
                                  startLocs, flowTrace)
        self.removeUnassessedFeatures()
    
    def finishedFeature(self, feature, layer, snappedFeatures, snappedLayers, has_started):
        """
        Place holder for flow trace object to override.
        
        :param feature: QgsFeature
        :param snappedFeatures: list -> QgsFeature
        :param snappedLayers: list -> QgsVectorLayer
        :return: void
        """
        
        super().finishedFeature(feature, layer, snappedFeatures, snappedLayers, has_started)
        
        for i, feature in enumerate(snappedFeatures):
            if feature in self.featuresToAssess and feature.attribute(1).lower() == 'x':
                self.featuresToAssess.append(feature)
                self.layersToAssess.append(snappedLayers[i])
            elif feature not in self.featuresAssessed and feature not in self.featuresToAssess:
                self.featuresToAssess.append(feature)
                self.layersToAssess.append(snappedLayers[i])
            
    def removeUnassessedFeatures(self):
        """
        
        :return:
        """
        
        ids = [x for x in self.features]
        
        for id in ids:
            if id in self.features:
                fData = self.features[id]
                if fData.feature not in self.featuresAssessed:
                    del self.features[id]
                    if id in self.connections:
                        del self.connections[id]
                    if id in self.drapes:
                        del self.drapes[id]
                    if id in self.ids:
                        self.ids.remove(id)
                    vertexes = [VERTEX.First, VERTEX.Last]
                    for vertex in vertexes:
                        vname = '{0}{1}'.format(id, vertex)
                        if vname in self.vertexes:
                            del self.vertexes[vname]
                            
    def getFeaturesToAssess(self, inputs, startLocs, flowTrace, lines=(), dataCollectorLines=None):
        """
        
    
        :param inputs:
        :param startLocs:
        :param flowTrace:
        :param lines:
        :param dataCollectorLines:
        :return:
        """
        
        if lines:
            if flowTrace:
                self.getPointFeaturesToAssess(inputs, lines, dataCollectorLines)
        else:
            DataCollector.getFeaturesToAssess(self, inputs, startLocs, flowTrace, lines, dataCollectorLines)
            
    def getPointFeaturesToAssess(self, inputs, lines, dataCollectorLines):
        """
        
        :param lines:
        :param dataCollectorLines:
        :return:
        """
        
        self.featuresToAssess = []
        self.layersToAssess = []
        self.featuresAssessed = []
        
        for id, fData in dataCollectorLines.features.items():
            for layer in inputs:
                allFeatures = self.allFeatures[layer.name()]
                spatialIndex = self.spatialIndexes[layer.name()]
                rect = self.createRequest(fData, 5)
                for fid in spatialIndex.intersects(rect):
                    feat = allFeatures[fid]
                    # if fData.feature.geometry().intersects(feat.geometry()):
                    if self.isSnapped(fData, FeatureData(layer, feat)):
                        if feat not in self.featuresToAssess:
                            self.featuresToAssess.append(feat)
                            self.layersToAssess.append(layer)


class FlowTracePlot(QWidget, Ui_flowTracePlotWidget):

    finished_ = pyqtSignal()
    updated_ = pyqtSignal()
    error_ = pyqtSignal()
    updateMessage_ = pyqtSignal(int)
    updateMaxSteps_ = pyqtSignal(int)

    def __init__(self, parent=None, flowTraceTool=None, iface=None):
        # QDialog.__init__(self, parent=parent)
        super().__init__(parent, Qt.Window)
        self.setupUi(self)
        qv = Qgis.QGIS_VERSION_INT

        self.flowTraceTool = flowTraceTool
        self.errmsg = None
        self.iface = iface

        # initialise plot
        self.fig, self.ax = plt.subplots()

        self.draw_connection = self.fig.canvas.mpl_connect('draw_event', self.onDraw)
        self.fig_leave_connection = self.fig.canvas.mpl_connect('figure_leave_event', self.onLeave)
        self.hover_connection = self.fig.canvas.mpl_connect("motion_notify_event", self.onHover)

        self.plotWidget = FigureCanvasQTAgg(self.fig)
        self.ax.set_xbound(0, 1000)
        self.ax.set_ybound(0, 1000)
        self.manageMatplotlibAxe(self.ax)
        self.plotLayout.addWidget(self.plotWidget)
        self._creating_background = False
        self.background = None

        # mpl toolbar
        self.mpltoolbar = NavigationToolbar2QT(self.plotWidget, self.toolbarFrame)
        w = 24
        if qv >= 31600:
            w = int(QgsApplication.scaleIconSize(w, True))
        w2 = int(np.ceil(w * 1.5))
        w3 = int(np.ceil(w2 * 6))
        self.toolbarFrame.setMinimumHeight(w2)
        self.toolbarFrame.setMinimumWidth(w3)
        self.toolbarFrame.resize(QSize(w3, w2))
        self.paths.setMaximumWidth(w3)
        self.mplactions = self.mpltoolbar.actions()
        self.mpltoolbar.removeAction(self.mplactions[3])
        self.mpltoolbar.removeAction(self.mplactions[6])
        self.mpltoolbar.removeAction(self.mplactions[7])
        self.mpltoolbar.removeAction(self.mplactions[8])
        self.mpltoolbar.removeAction(self.mplactions[9])
        self.mpltoolbar.removeAction(self.mplactions[10])
        iconRefreshPlot = QIcon(join(dirname(dirname(__file__)), "icons", "RefreshPlotBlack.png"))
        self.refresh_plot_action = QAction(iconRefreshPlot, 'Refresh Plot')
        self.refresh_plot_action.triggered.connect(self.refreshPlot)
        self.mpltoolbar.addAction(self.refresh_plot_action)

        # mpl hover over labelling
        self.annot = None
        self.point = None
        self.polygon = None
        self.line = None

        # intialise signal connections
        self.paths.itemSelectionChanged.connect(self.drawPlot)
        self.pbSelectPath.clicked.connect(self.selectPathInWorkspace)
        # self.resized.connect(self.resizePlot)
        self.cbLabel.clicked.connect(self.addLabels)

        # context menu actions
        self.context_menu_open = False
        self._copy_menu_actions = []
        self._export_menu_actions = []
        self._init_context_menu_actions()
        self._context_menu = None
        self.plotWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.plotWidget.customContextMenuRequested.connect(self._show_context_menu)

        # rubber band
        self.rubber_band = ChannelRubberBand(self.iface)

    def run_plotter(self):
        # get paths
        self.getPaths_V2()

    def _init_context_menu_actions(self):
        # actions
        self._zoom_to_paths_action = QAction('Zoom to Selected Paths')
        self._zoom_to_feature_action = QAction('Zoom to feature')
        self._legend_action = QAction('Legend')
        self._show_area_flag_action = QAction('Area Flags')
        self._show_invert_flag_action = QAction('Invert Flags')
        self._show_angle_flag_action = QAction('Angle Flags')
        self._show_cover_flag_action = QAction('Cover Flags')
        self._copy_image_action = QAction('Copy Image to Clipboard')
        self._copy_data_action = QAction('Copy Data to Clipboard')
        self._copy_area_flag_action = QAction('Copy Area Flag IDs to Clipboard')
        self._copy_invert_flag_action = QAction('Copy Invert Flag IDs to Clipboard')
        self._copy_angle_flag_action = QAction('Copy Angle Flag IDs to Clipboard')
        self._copy_cover_flag_action = QAction('Copy Cover Flag IDs to Clipboard')
        self._export_data_action = QAction('Export Data')
        self._export_area_flag_action = QAction('Export Area Flag IDs')
        self._export_invert_flag_action = QAction('Export Invert Flag IDs')
        self._export_angle_flag_action = QAction('Export Angle Flag IDs')
        self._export_cover_flag_action = QAction('Export Cover Flag IDs')

        # action properties
        self._legend_action.setCheckable(True)
        self._legend_action.setChecked(True)
        self._show_area_flag_action.setCheckable(True)
        self._show_area_flag_action.setChecked(True)
        self._show_invert_flag_action.setCheckable(True)
        self._show_invert_flag_action.setChecked(True)
        self._show_angle_flag_action.setCheckable(True)
        self._show_angle_flag_action.setChecked(True)
        self._show_cover_flag_action.setCheckable(True)
        self._show_cover_flag_action.setChecked(True)

        # action signals
        self._zoom_to_paths_action.triggered.connect(self._zoom_to_paths)
        self._zoom_to_feature_action.triggered.connect(self._zoom_to_feature)
        self._legend_action.triggered.connect(self._legend_toggled)
        self._show_area_flag_action.triggered.connect(self._area_flags_toggled)
        self._show_invert_flag_action.triggered.connect(self._invert_flags_toggled)
        self._show_angle_flag_action.triggered.connect(self._angle_flags_toggled)
        self._show_cover_flag_action.triggered.connect(self._cover_flags_toggled)
        self._copy_image_action.triggered.connect(self._copy_plot_image_to_clipboard)
        self._copy_data_action.triggered.connect(self._copy_plot_data_to_clipboard)
        self._copy_area_flag_action.triggered.connect(self._copy_area_flag_to_clipboard)
        self._copy_invert_flag_action.triggered.connect(self._copy_invert_flag_to_clipboard)
        self._copy_angle_flag_action.triggered.connect(self._copy_angle_flag_to_clipboard)
        self._copy_cover_flag_action.triggered.connect(self._copy_cover_flag_to_clipboard)
        self._export_data_action.triggered.connect(self._export_plot_data)
        self._export_area_flag_action.triggered.connect(self._export_area_flag)
        self._export_invert_flag_action.triggered.connect(self._export_invert_flag)
        self._export_angle_flag_action.triggered.connect(self._export_angle_flag)
        self._export_cover_flag_action.triggered.connect(self._export_cover_flag)

        self._copy_menu_actions = [self._copy_image_action, self._copy_data_action, self._copy_area_flag_action,
                                   self._copy_invert_flag_action, self._copy_angle_flag_action,
                                   self._copy_cover_flag_action]
        self._export_menu_actions = [self.mplactions[9], self._export_data_action, self._export_area_flag_action,
                                     self._export_invert_flag_action, self._export_angle_flag_action,
                                     self._export_cover_flag_action]

    def _context_menu_about_to_hide(self):
        self.context_menu_open = False
        self._hover_set_visible(False)
        self._blitted_draw()

    def _show_context_menu(self, pos):
        if self.mplactions[4].isChecked() or self.mplactions[5].isChecked():
            return

        if self._context_menu is None:
            self._context_menu = DatasetMenu('context menu', self.plotWidget)
            self._context_menu.aboutToHide.connect(self._context_menu_about_to_hide)

            copy_menu = QMenu('Copy', self._context_menu)
            export_menu = QMenu('Export', self._context_menu)

            for action in self._copy_menu_actions:
                copy_menu.addAction(action)
            for action in self._export_menu_actions:
                export_menu.addAction(action)

            self._context_menu.addAction(self._zoom_to_paths_action)
            self._context_menu.addAction(self._zoom_to_feature_action)
            self._context_menu.addSeparator()
            self._context_menu.addAction(self._legend_action)
            self._context_menu.addAction(self._show_area_flag_action)
            self._context_menu.addAction(self._show_invert_flag_action)
            self._context_menu.addAction(self._show_angle_flag_action)
            self._context_menu.addAction(self._show_cover_flag_action)
            self._context_menu.addSeparator()
            self._context_menu.addMenu(copy_menu)
            self._context_menu.addMenu(export_menu)

        b = self.polygon.get_visible() or self.line.get_visible()
        self._zoom_to_feature_action.setVisible(b)

        self._context_menu.popup(self.plotWidget.mapToGlobal(pos))
        self.context_menu_open = True

    def resizePlot(self):
        """
        
        :return:
        """

        # draw
        self.fig.tight_layout()
        self.plotWidget.draw()

    def manageMatplotlibAxe(self, axe1):
        """
        Set up Matplotlib plot object e.g. grid lines

        :param axe1: matplotlib.axis object
        :return: bool -> True for successful, False for unsuccessful
        """
    
        axe1.grid()
        axe1.tick_params(axis="both", which="major", direction="out", length=10, width=1, bottom=True, top=False,
                         left=True, right=False)
        axe1.minorticks_on()
        axe1.tick_params(axis="both", which="minor", direction="out", length=5, width=1, bottom=True, top=False,
                         left=True, right=False)

    def _get_chan_ids(self):
        dc = self.downstreamConnectivity
        chan_ids = [dc.branches[i] for i in range(self.paths.count()) if self.paths.item(i).isSelected()]
        return sum(chan_ids, [])

    def selectPathInWorkspace(self):
        """
        
        :return:
        """
        
        for_selection = {}
        chan_ids = self._get_chan_ids()
        for id_ in chan_ids:
            f = self.flowTraceTool.dataCollector.features[id_]
            if f.layer not in for_selection:
                for_selection[f.layer] = []
            for_selection[f.layer].append(f.fid)

        for layer, fids in for_selection.items():
            layer.selectByIds(fids)

    def getPaths_V2(self):
        self.updateMessage_.emit(LongPlotMessages.CollectingBranches)
        self.downstreamConnectivity = Connectivity(self.flowTraceTool.dataCollector.startLocs,
                                                   self.flowTraceTool.dataCollector)

        self.thread = QThread()
        self.downstreamConnectivity.moveToThread(self.thread)
        self.thread.started.connect(self.downstreamConnectivity.getBranches)
        self.downstreamConnectivity.branchesCollected.connect(self.populateInfo)
        self.downstreamConnectivity.error.connect(self.catchError)

        self.thread.start()

    def populateInfo(self):
        self.updateMessage_.emit(LongPlotMessages.Populating)
        continuityLimits = ContinuityLimits(QgsUnitTypes.DistanceMeters, self.flowTraceTool)

        if not self.downstreamConnectivity.valid:
            return

        self.thread.started.disconnect(self.downstreamConnectivity.getBranches)
        self.thread.terminate()

        self.thread = QThread()
        self.thread.started.connect(lambda: self.downstreamConnectivity.populateInfo(continuityLimits))
        self.downstreamConnectivity.populatedInfo.connect(self.finishedConnectivity)
        self.downstreamConnectivity.error.connect(self.catchError)
        self.downstreamConnectivity.started.connect(self.startedPopulate)
        self.downstreamConnectivity.updated.connect(self.updateProgress)

        self.thread.start()

    def finishedConnectivity(self):
        self.paths.addItems(self.downstreamConnectivity.pathsName)
        if self.paths.count():
            self.paths.item(0).setSelected(True)
        self.thread.terminate()
        self.finished_.emit()
        self.thread.terminate()
        self.thread = None

    def catchError(self):
        self.thread.terminate()
        self.thread = None
        self.errmsg = self.downstreamConnectivity.errmsg
        self.error_.emit()

    def startedPopulate(self):
        max_steps = int(sum([len(x) for x in self.downstreamConnectivity.branches]))
        self.updateMaxSteps_.emit(max_steps)

    def updateProgress(self):
        self.updated_.emit()
        
    def getPaths(self):
        """
        DEPRECATED. See getPaths_V2.
        
        :return:
        """
        
        # build dictionaries for long plot creation
        # long plot code ported straight from QGIS 2 plugin
        # I figured it all out once - too hard to do it all again!
        dsLines = {}  # {name: [[dns network channels], [us invert, ds invert], [angle], [dns-dns connected channels], [upsnetworks}, [ups-ups channels]]
        lineDrape = {}  # dict {name: [[QgsPoint - line vertices], [vertex chainage], [elevations]]}
        lineDict = {}
        startLines = []
        inLyrs = []
        areaFlags = self.flowTraceTool.flaggedAreaIds[:]
        angleFlags = self.flowTraceTool.flaggedAngleIds[:]
        invertFlags = self.flowTraceTool.flaggedInvertIds[:]
        gradientFlags = self.flowTraceTool.flaggedGradientIds[:]
        for id in self.flowTraceTool.dataCollector.ids:
            fData = self.flowTraceTool.dataCollector.features[id]
            dData = self.flowTraceTool.dataCollector.drapes[id]
            cData = self.flowTraceTool.dataCollector.connections[id]
            properties = []
            linesDs = []
            for line in cData.linesDs:
                if line in self.flowTraceTool.dataCollector.ids:
                    linesDs.append(line)
            properties.append(linesDs)
            properties.append([fData.invertUs, fData.invertDs])
            properties.append([180])  # refine later
            properties.append(cData.linesDsDs)
            properties.append(cData.linesUs)
            properties.append(cData.linesUsUs)
            
            drape = []
            drape.append(dData.points)
            drape.append(dData.chainages)
            drape.append(dData.elevations)
            
            line = []
            line.append([fData.startVertex, fData.endVertex])
            line.append(fData.fid)
            line.append(fData.layer)
            line.append(fData.invertUs)
            line.append(fData.invertDs)
            line.append(fData.type)
            line.append(fData.feature)
            
            dsLines[id] = properties
            lineDrape[id] = drape
            lineDict[id] = line
            
            if not cData.linesUs:
                startLines.append(id)
                
            if fData.layer not in inLyrs:
                inLyrs.append(fData.layer)
                

        self.downstreamConnectivity = DownstreamConnectivity(dsLines, startLines, inLyrs, self.flowTraceTool.limitAngle,
                                                             lineDrape, self.flowTraceTool.limitCover, lineDict,
                                                             QgsUnitTypes.DistanceMeters, areaFlags, angleFlags,
                                                             invertFlags, gradientFlags)
        self.thread = QThread()
        self.downstreamConnectivity.moveToThread(self.thread)
        self.thread.started.connect(self.downstreamConnectivity.getBranches)
        self.downstreamConnectivity.branchesCollected.connect(self.downstreamConnectivity.getPlotFormat)
        self.downstreamConnectivity.pathsCollected.connect(self.pathsCollected)
        
        self.timer = QTimer()
        self.timer.setInterval(750)
        self.timer.timeout.connect(self.updated_.emit)
        
        self.timer2 = QTimer()
        self.timer2.setInterval(120000)
        self.timer2.setSingleShot(True)
        #self.timer2.timeout.connect(self.updateMessage.emit)
        
        self.timer.start()
        self.timer2.start()
        self.thread.start()
        #self.downstreamConnectivity.getBranches()
        #self.downstreamConnectivity.getPlotFormat()
        
    def pathsCollected(self):
        self.paths.addItems(self.downstreamConnectivity.pathsName)
        if self.paths.count():
            self.paths.item(0).setSelected(True)
        self.thread.terminate()
        self.timer.stop()
        self.timer2.stop()
        self.finished_.emit()

    def refreshPlot(self):
        self.fig.tight_layout()
        self.fig.canvas.draw()
            
    def drawPlot(self):
        """
        
        :return:
        """

        try:

            dc = self.downstreamConnectivity

            self.ax.clear()
            self.manageMatplotlibAxe(self.ax)
            ymax = -99999

            for i in range(self.paths.count()):
                item = self.paths.item(i)

                if item.isSelected():
                    pathName = item.text()

                    # path index
                    j = None
                    if pathName in self.downstreamConnectivity.pathsName:
                        j = self.downstreamConnectivity.pathsName.index(pathName)

                    if j is not None:

                        # inverts
                        x = dc.getChanInvert(j, 'x')
                        y = dc.getChanInvert(j, 'y')
                        label = '{0}: Invert'.format(pathName)
                        self.ax.plot(x, y, label=label)

                        # ground
                        x = dc.getGround(j, 'x')
                        y = dc.getGround(j, 'y')
                        label = '{0}: Ground'.format(pathName)
                        if y.any():
                            self.ax.plot(x, y, label=label)

                        # pipes
                        for k, poly in enumerate(dc.pathsPipe[j]):
                            id_ = dc.branches[i][k]
                            label = '{0}: Pipes__{1}__'.format(pathName, id_)
                            if poly.any():
                                for v in poly:
                                    ymax = max(ymax, v[1])
                                p = Polygon(poly, facecolor='0.9', edgecolor='0.5', label=label)
                                self.ax.add_patch(p)

                        # area flag
                        if dc.hasWarning(j, 'area'):
                            x = dc.getWarning(j, 'x', 'area')
                            y = dc.getWarning(j, 'y', 'area')
                            label = '{0}: Area decrease'.format(pathName)
                            if y.any():
                                a, = self.ax.plot(x, y, label=label, linestyle='None', marker='o')
                                a.set_visible(self._show_area_flag_action.isChecked())

                        # invert flag
                        if dc.hasWarning(j, 'invert'):
                            x = dc.getWarning(j, 'x', 'invert')
                            y = dc.getWarning(j, 'y', 'invert')
                            label = '{0}: Adverse invert'.format(pathName)
                            a, = self.ax.plot(x, y, label=label, linestyle='None', marker='o')
                            a.set_visible(self._show_invert_flag_action.isChecked())

                        # gradient flag
                        if dc.hasWarning(j, 'gradient'):
                            x = dc.getWarning(j, 'x', 'gradient')
                            y = dc.getWarning(j, 'y', 'gradient')
                            label = '{0}: Adverse gradient'.format(pathName)
                            a, = self.ax.plot(x, y, label=label, linestyle='None', marker='o')
                            a.set_visible(self._show_invert_flag_action.isChecked())

                        # angle flag
                        if dc.hasWarning(j, 'angle'):
                            x = dc.getWarning(j, 'x', 'angle')
                            y = dc.getWarning(j, 'y', 'angle')
                            label = '{0}: Sharp angle'.format(pathName)
                            a, = self.ax.plot(x, y, label=label, linestyle='None', marker='o')
                            a.set_visible(self._show_angle_flag_action.isChecked())

                        # cover flag
                        if dc.hasWarning(j, 'cover'):
                            x = dc.getWarning(j, 'x', 'cover')
                            y = dc.getWarning(j, 'y', 'cover')
                            label = '{0}: Insuff. Cover'.format(pathName)
                            a, = self.ax.plot(x, y, label=label, linestyle='None', marker='o')
                            a.set_visible(self._show_cover_flag_action.isChecked())

            # set axis y max - matplotlib doesn't consider patches when it automates this step
            self.setYMax(ymax)

            # set legend - remove duplicate 'pipe' entries
            if self._legend_action.isChecked():
                self.setLegend()

            # draw
            self.fig.tight_layout()
            self.plotWidget.draw()

            # add labels
            if self.cbLabel.isChecked():
                self.addLabels()
        except:
            import sys
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.errmsg = ''.join(traceback.extract_tb(exc_traceback).format()) + '{0}{1}'.format(exc_type, exc_value)
            self.error_.emit()
            return

    def addLabels(self):
        """
        Add labels to plot for 1d elements
        """

        self.ax.texts.clear()
        self.fig.texts.clear()

        if self.cbLabel.isChecked():
            try:
                annotations = Annotations()

                bbox_template = dict(boxstyle="round", fc="0.8", alpha=0.3)
                arrowprops = dict(
                    arrowstyle="->",
                    connectionstyle="angle,angleA=0,angleB=90,rad=10")

                artists, labels = self.ax.get_legend_handles_labels()
                for i, artist in enumerate(artists):
                    if type(artist) is not Polygon or artist == self.polygon:
                        continue

                    label = labels[i].split('__')
                    if len(label) < 3:
                        continue
                    label = label[-2]
                    xy = artist.get_xy()
                    xmin = np.nanmin(xy[:,0])
                    xmax = np.nanmax(xy[:,0])

                    j = np.where(xy[:,0] == xmin)
                    ymin = np.nanmin(xy[j][:,1])
                    k = np.where(xy[j][:,1] == ymin)
                    k = k[0][0]
                    x1, y1 = xmin, xy[j][:,1][k]

                    j = np.where(xy[:, 0] == xmax)
                    ymin = np.nanmin(xy[j][:, 1])
                    k = np.where(xy[j][:, 1] == ymin)
                    k = k[0][0]
                    x2, y2 = xmax, xy[j][:, 1][k]

                    a = np.array([[x1, y1], [x2, y2]])
                    a = a[a[:, 0].argsort()]

                    xpos = (xmin + xmax) / 2.
                    ypos = np.interp(xpos, a[:,0], a[:,1])
                    annot = self.ax.annotate(label, xy=(xpos, ypos), xycoords='data', textcoords="offset pixels",
                                             bbox=bbox_template, arrowprops=arrowprops, horizontalalignment='center')
                    annot.xyann = (0., -40)
                    annotations.append(Annotation(self.fig, self.ax, annot))

                annotations.try_no_overlap()

                # rescale plot coordinates
                iter_ = 3
                i = -1
                while i < iter_:
                    i += 1
                    xmin, xmax = self.ax.get_xlim()
                    ymin, ymax = self.ax.get_ylim()
                    ymin_without_labels, ymax_without_labels = ymin, ymax

                    ymin_, ymax_ = annotations.min_max(xmin, xmax)
                    ymin, ymax = min(ymin, ymin_), max(ymax, ymax_)

                    ax_changed = False
                    if ymin < ymin_without_labels:
                        xloc, yloc = self.ax.transData.transform((xmin, ymin))
                        yloc -= 15
                        xmin, ymin = self.ax.transData.inverted().transform((xloc, yloc))
                        ax_changed = True
                    if ymax > ymax_without_labels:
                        xloc, yloc = self.ax.transData.transform((xmax, ymax))
                        yloc += 15
                        xmax, ymax = self.ax.transData.inverted().transform((xloc, yloc))
                        ax_changed = True

                    self.ax.set_ylim((ymin, ymax))
                    if ax_changed:
                        annotations.try_no_overlap()
                    else:
                        break

            except:
                import sys
                import traceback
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.errmsg = ''.join(traceback.extract_tb(exc_traceback).format()) + '{0}{1}'.format(exc_type, exc_value)
                self.error_.emit()
                return

        self.fig.canvas.draw()
        
    def setYMax(self, ymax):
        """
        
        :param ymax:
        :return:
        """
        
        ylimits = self.ax.get_ylim()
        if ylimits:
            if ymax > ylimits[1]:
                self.ax.set_ylim(ylimits[0], ymax)
                
    def setLegend(self):
        """
        
        :return:
        """
        
        lines, labs = self.ax.get_legend_handles_labels()
        uniqueLines, uniqueLabs = [], []
        for i, lab in enumerate(labs):
            add_to_legend = True
            if ':' in lab:
                lab_ = lab.split(':')[1].strip()
                if lab_ == 'Area decrease' and not self._show_area_flag_action.isChecked():
                    add_to_legend = False
                elif lab_ == 'Adverse invert' and not self._show_invert_flag_action.isChecked():
                    add_to_legend = False
                elif lab_ == 'Adverse gradient' and not self._show_invert_flag_action.isChecked():
                    add_to_legend = False
                elif lab_ == 'Sharp angle' and not self._show_angle_flag_action.isChecked():
                    add_to_legend = False
                elif lab_ == 'Insuff. Cover' and not self._show_cover_flag_action.isChecked():
                    add_to_legend = False

            lab = re.split(r'__.*__$', lab)[0]
            if lab not in uniqueLabs and add_to_legend:
                uniqueLabs.append(lab)
                uniqueLines.append(lines[i])
        
        self.ax.legend(uniqueLines, uniqueLabs)

    def onDraw(self, e):
        self.create_new_background()

    def onLeave(self, e):
        if not self.context_menu_open:
            self._hover_set_visible(False)
            self.fig.canvas.draw()
        else:
            v1, v2, v3 = self.line.get_visible(), self.polygon.get_visible(), self.rubber_band.get_visible()
            self._hover_set_visible(False)
            self.line.set_visible(v1)
            self.polygon.set_visible(v2)
            self.rubber_band.set_visible(v3)
            self._blitted_draw()

    def onHover(self, e):
        """Updates annotation and red dot when user hovers cursor over the plot."""

        SNAP_TOLERANCE = 5

        self._init_hover_objects()

        if e.inaxes != self.ax:
            self._hover_set_visible(False)
            self._blitted_draw()
            return

        artists, labels = self.ax.get_legend_handles_labels()

        # check for vertex snapping
        closest_vertex, dist, closest_artist = None, None, None
        for i, artist in enumerate(artists):
            if isinstance(artist, plt.Line2D) and not re.findall(r'Path \d+: ((Invert)|Ground)', labels[i]):
                continue
            closest_vertex_, dist_ = self._closest_vertex(artist, (e.xdata, e.ydata), SNAP_TOLERANCE)
            if dist is None or (dist_ is not None and dist_ < dist):
                closest_vertex, dist, closest_artist = closest_vertex_, dist_, artist

        if dist is not None and dist < SNAP_TOLERANCE:
            text = '{0:.3f}, {1:.3f}'.format(*closest_vertex)
            self._update_hover(closest_vertex, closest_artist, text, None)
            self._hover_set_visible(True)
            self.polygon.set_visible(False)
            self.line.set_visible(False)
            self.rubber_band.set_visible(False)
            self._blitted_draw()
            return

        # check contains
        for i, artist in enumerate(artists):
            xy_ = None
            continuity_flag = False
            if isinstance(artist, plt.Line2D):
                contains, d = artist.contains(e)
                if not contains:
                    continue

                if re.findall(r'Path \d+: Invert', labels[i]):
                    # get data and sort low to hight by x values
                    xdata, ydata = [np.reshape(x, (x.shape[0], 1)) for x in artist.get_data()]
                    data_ = np.append(xdata, ydata, axis=1)
                    data_ = data_[data_[:,0].argsort()]

                    j2 = min(np.searchsorted(data_[:,0], e.xdata), data_.shape[0] - 1)
                    if j2 % 2 == 0:
                        j2 -= 1
                    j1 = j2 - 1

                    xy_ = np.transpose(data_[j1:j2+1,:])

                    y_ = np.interp(e.xdata, data_[:,0], data_[:,1])
                    x_ = e.xdata

                    text = self._get_line2d_label(labels[i], data_.shape[0] - 1 - j2)
                else:  # continuity flag
                    x_ = e.xdata
                    y_ = e.ydata
                    try:
                        ind = int(d['ind'][0])
                    except:
                        ind = 10000

                    text = self._generate_continuity_flag_label(labels[i], ind)
                    continuity_flag = True

            elif isinstance(artist, Polygon):
                contains, _ = artist.contains(e)
                if not contains:
                    continue

                x_ = e.xdata
                y_ = e.ydata
                text = self._get_polygon_label(labels[i])

            else:
                contains = False

            if contains:
                self._update_hover((x_, y_), artist, text, xy_)
                self._hover_set_visible(True)
                self.point.set_visible(False)
                if isinstance(artist, plt.Line2D) or continuity_flag:
                    self.polygon.set_visible(False)
                if isinstance(artist, Polygon) or continuity_flag:
                    self.line.set_visible(False)
                if not continuity_flag:
                    id_ = re.findall(r'(?<=ID:).*(?=\n)', text)
                    geom = None
                    if id_:
                        id_ = id_[0].strip()
                    if id_ in self.flowTraceTool.dataCollector.features:
                        geom = self.flowTraceTool.dataCollector.features[id_].feature.geometry()
                    self.rubber_band.update_geometry(geom)
                    self.rubber_band.set_visible(True)
                self._blitted_draw()
                return

        if self._hover_get_visible():
            self._hover_set_visible(False)
            self._blitted_draw()

    def _blitted_draw(self):
        if self.background is None:
            self.create_new_background()
        self.fig.canvas.restore_region(self.background)
        self.ax.draw_artist(self.point)
        self.ax.draw_artist(self.polygon)
        self.ax.draw_artist(self.line)
        self.ax.draw_artist(self.annot)
        self.fig.canvas.blit(self.ax.bbox)

    def _update_hover(self, xy_, artist, text, xydata):
        self.annot.xy = xy_
        if isinstance(artist, plt.Line2D):
            self.annot.get_bbox_patch().set_facecolor(artist.get_color())
            if xydata is not None:
                self.line.set_data(xydata)
                self.line.set_zorder(90)
        elif isinstance(artist, Polygon):
            self.annot.get_bbox_patch().set_facecolor(artist.get_facecolor())
            self.polygon.set_xy(artist.get_xy())
            self.polygon.set_zorder(90)
        else:
            return
        self.annot.set_text(text)
        self.annot.xyann = (10., 10.)
        self.annot.set_zorder(100)
        self.point.set_zorder(90)
        self.point.set_offsets([xy_])

        # check annotation doesn't exceed plot window bounds
        trans = self.ax.transData.transform
        vis = self.annot.get_visible()
        self.annot.set_visible(True)
        self.annot.draw(self.fig.canvas.renderer)
        if trans(xy_)[0] + self.annot.get_bbox_patch().get_width() + 25 > self.fig.bbox.width:
            self.annot.xyann = (-self.annot.get_bbox_patch().get_width() - 7, self.annot.xyann[1])
        if trans(xy_)[1] + self.annot.get_bbox_patch().get_height() + 25 > self.fig.bbox.height:
            self.annot.xyann = (self.annot.xyann[0], -self.annot.get_bbox_patch().get_height() - 7)
        self.annot.set_visible(vis)

        # transfer annotation to figure
        if self.ax.texts and self.annot in self.ax.texts:
            i = self.ax.texts.index(self.annot)
            self.fig.texts.append(self.ax.texts.pop(i))
            if self.annot.axes is None:
                self.annot.axes = self.ax
            if self.annot.figure is None:
                self.annot.figure = self.fig

    def _get_polygon_label(self, artist_label):
        label = artist_label.split('__')
        if len(label) < 3:
            return ''
        return self._generate_network_attr_label(label[-2])

    def _generate_network_attr_label(self, id_):
        features = self.flowTraceTool.dataCollector.features
        if id_ not in features:
            return id_

        feat = features[id_]
        label = 'ID: {0}\nType: {1}\nNo. of: {2}'.format(id_, feat.type, feat.numberOf)
        if feat.type.upper() == 'C':
            label = '{0}\nDia: {1}'.format(label, feat.width)
        elif feat.type.upper() == 'R':
            label = '{0}\nWidth: {1}\nHeight: {2}'.format(label, feat.width, feat.height)
        label = '{0}\nUS Invert: {1:.2f}\nDS Invert: {2:.2f}'.format(label, feat.invertUs, feat.invertDs)

        return label

    def _generate_continuity_flag_label(self, artist_label, i):
        try:
            j = int(re.findall(r'(?<=^path\s)\d+(?=:)', artist_label, flags=re.IGNORECASE)[0]) - 1
        except:
            return ''

        flag_type = artist_label.split(':')[-1].strip()
        flag_labels = self._get_flag_labels(flag_type)
        if flag_labels is None:
            return ''

        if 0 <= j <= len(flag_labels) - 1:
            if 0 <= i <= len(flag_labels[j]) - 1:
                return '{0}\n{1}'.format(flag_type, flag_labels[j][i])

        return ''

    def _get_flag_labels(self, flag_type):
        if flag_type == 'Area decrease':
            return self.downstreamConnectivity.pathsPlotDecALabel
        if flag_type == 'Adverse invert':
            return self.downstreamConnectivity.pathsPlotAdvILabel
        if flag_type == 'Adverse gradient':
            return self.downstreamConnectivity.pathsPlotAdvGLabel
        if flag_type == 'Sharp angle':
            return self.downstreamConnectivity.pathsPlotSharpALabel
        if flag_type == 'Insuff. Cover':
            return self.downstreamConnectivity.pathsPlotInCoverLabel

    def _get_line2d_label(self, artist_label, i):
        if i % 2 != 0:
            i -= 1
        i = int(i / 2)
        try:
            j = int(re.findall(r'(?<=^path\s)\d+(?=:)', artist_label, flags=re.IGNORECASE)[0]) - 1
        except:
            return ''

        if 0 <= j <= len(self.downstreamConnectivity.branches) - 1:
            if 0 <= i <= len(self.downstreamConnectivity.branches[j]) -1:
                return self._generate_network_attr_label(self.downstreamConnectivity.branches[j][i])

        return ''

    def _closest_vertex(self, artist, xy_, snap_tolerance):
        if artist == self.polygon or artist == self.line or artist == self.point:
            return None, None

        if isinstance(artist, plt.Line2D):
            d = list(zip(*artist.get_data()))
        elif isinstance(artist, Polygon):
            d = artist.get_xy()
        else:
            return None, None

        trans = self.ax.transData.transform  # distance based on figure pixels not x, y data coordinates

        close_points = np.array([(np.absolute(np.array(x) - np.array(xy_)).sum(), i) for i, x in enumerate(d) if np.isclose(trans(x), trans(xy_), atol=snap_tolerance).all()])
        if not close_points.any():
            return None, None
        i = np.where(close_points[:, 0] == np.amin(close_points[:, 0]))[0][0]
        point_xy = d[int(close_points[:, 1][i])]
        dist = ((trans(point_xy)[0] - trans(xy_)[0]) ** 2 + (trans(point_xy)[1] - trans(xy_)[1]) ** 2) ** 0.5

        return point_xy, dist

    def _init_hover_objects(self):
        # annotation - annotation may be sitting with fig as this places it above all other artists

        if self.fig.texts:
            if self.fig.texts:
                [self.fig.texts.pop(i) for i in range(len(self.fig.texts))]
        if self.annot is not None and self.annot in self.ax.texts:
            self.ax.texts.remove(self.annot)

        self.annot = None
        self.annot = self.ax.annotate("debug", xy=(15, 15), xycoords='data', textcoords="offset pixels",
                                      bbox=dict(boxstyle="round", fc="w"))
        self.annot.get_bbox_patch().set_alpha(0.3)

        # point
        if self.point is None:
            self.point = self.ax.scatter(0, 0, 20, 'red')

        if not [x for x in self.ax.collections]:
            self.ax.collections.append(self.point)

        x_ = np.mean(self.ax.get_xlim())
        y_ = np.mean(self.ax.get_ylim())
        self.point.set_offsets([(x_, y_)])

        # polygon
        if self.polygon is None:
            self.polygon = Polygon([[x_, y_], [x_, y_], [x_, y_], [x_, y_], [x_, y_]], fill=False, edgecolor='red', linewidth=2, color='red')
            self.ax.add_patch(self.polygon)

        if self.polygon not in self.ax.patches:
            self.ax.add_patch(self.polygon)

        self.polygon.set_xy(np.array([[x_, y_], [x_, y_], [x_, y_], [x_, y_], [x_, y_]]))

        # line
        if self.line is None:
            self.line, = self.ax.plot([x_, x_], [y_, y_], color='red', linewidth=2)

        if self.line not in self.ax.lines:
            self.ax.add_line(self.line)

        self.line.set_data([x_, x_], [y_, y_])

    def _hover_get_visible(self):
        if self.annot is not None:
            return self.annot.get_visible()

        return False

    def _hover_set_visible(self, b):
        if self.annot is not None:
            self.annot.set_visible(b)
        if self.point is not None:
            self.point.set_visible(b)
        if self.polygon is not None:
            self.polygon.set_visible(b)
        if self.line is not None:
            self.line.set_visible(b)
        self.rubber_band.set_visible(b)

    def create_new_background(self):
        if self._creating_background:
            return
        self._creating_background = True
        self.fig.canvas.draw()
        self.background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        self.addLabels()
        self._creating_background = False

    def _export_label(self, label):
        if re.findall(r'__.*__$', label) and ':' in label:
            pipe_name = re.findall(r'(?<=_{2}).*(?=_{2})', label)[0]
            return '{0}: {1}'.format(label.split(':')[0].strip(), pipe_name)

        return label

    def _data_header(self, delim, labels):
        header1 = delim.join(sum([[self._export_label(x), ''] for x in labels if x], []))
        header2 = delim.join(sum([['x', 'y'] for _ in labels], []))

        return '{0}\n{1}\n'.format(header1, header2)

    def _collect_data(self, delim):
        artists, labels = self.ax.get_legend_handles_labels()
        header = self._data_header(delim, labels)

        data_len = 0
        data_count = 0
        for i, artist in enumerate(artists):
            if not labels[i] or artist == self.point or artist == self.polygon or artist == self.line:
                continue
            data_count += 1
            if isinstance(artist, plt.Line2D):
                data_ = artist.get_xdata()
                data_len = max(data_len, data_.shape[0])
            elif isinstance(artist, Polygon):
                data_ = artist.get_xy()
                data_len = max(data_len, data_.shape[0])
            else:
                data_count -= 1

        if not data_len or not data_count:
            return

        data_count *= 2
        a = [['' for _ in range(data_count)] for _ in range(data_len)]
        j = -1
        for i, artist in enumerate(artists):
            if not labels[i] or artist == self.point or artist == self.polygon or artist == self.line:
                continue
            j += 1
            m = j * 2
            n = m + 1
            if isinstance(artist, plt.Line2D):
                data_ = artist.get_data()
                for k in range(data_[0].shape[0]):
                    a[k][m] = str(data_[0][k])
                    a[k][n] = str(data_[1][k])
            elif isinstance(artist, Polygon):
                data_ = artist.get_xy()
                for k in range(data_.shape[0]):
                    a[k][m] = str(data_[k,0])
                    a[k][n] = str(data_[k,1])

        return '{0}{1}'.format(header, '\n'.join([delim.join(x) for x in a]))

    def _collect_flag_data(self, flag_types, delim):
        ids = []
        msg = []
        paths = []
        len_ = 0
        for flag_type in flag_types:
            flag_labels = self._get_flag_labels(flag_type)

            for item in self.paths.selectedItems():
                i = int(re.findall(r'\d+', item.text())[0]) - 1
                if item.text() not in paths:
                    paths.append(item.text())
                    len_ = max(len_, len(flag_labels[i]))
                    ids.append([x.split('\n')[0].strip() for x in flag_labels[i]])
                    msg.append(['; '.join(x.split('\n')[1:]) for x in flag_labels[i]])
                else:
                    j = paths.index(item.text())
                    ids[j].extend([x.split('\n')[0].strip() for x in flag_labels[i]])
                    msg[j].extend(['; '.join(x.split('\n')[1:]) for x in flag_labels[i]])
                    len_ = max(len_, len(ids[j]))

        a = [['' for _ in range(len(paths) * 2)] for _ in range(len_)]
        for i in range(len(paths)):
            m = i * 2
            n = m + 1
            for j in range(len(ids[i])):
                a[j][m] = ids[i][j]
                a[j][n] = msg[i][j]

        header = delim.join(sum([[x, ''] for x in paths], []))

        return '{0}\n{1}'.format(header, '\n'.join([delim.join(x) for x in a]))

    def _export_data(self, data_):
        file = browse(self, 'output file', '1d_integrity_tool/plot_export', 'Export...', 'CSV (*.csv *.CSV)')
        if file is None:
            return
        while 1:
            try:
                with open(file, 'w') as f:
                    f.write(data_)
                QMessageBox.information(self, 'Export', 'Successfully exported data')
                return
            except PermissionError:
                retry = QMessageBox.warning(self, 'Export...', 'File is currently locked by another application',
                                            QMessageBox.Retry | QMessageBox.Cancel)
                if retry == QMessageBox.Cancel:
                    return

    def _legend_toggled(self):
        if self._legend_action.isChecked() and not self.ax.get_legend():
            self.setLegend()
            self.fig.canvas.draw()
        elif not self._legend_action.isChecked() and self.ax.get_legend():
            self.ax.get_legend().remove()
            self.fig.canvas.draw()

    def _update_legend(self):
        if self._legend_action.isChecked():
            self.ax.get_legend().remove()
            self.setLegend()

    def _flag_toggled(self, action, flag_label):
        b = action.isChecked()
        artists, labels = self.ax.get_legend_handles_labels()
        for i, artist in enumerate(artists):
            label = labels[i]
            if ':' not in label:
                continue
            label = label.split(':')[1].strip()
            if label in flag_label:
                artist.set_visible(b)

        self._update_legend()
        self.fig.canvas.draw()

    def _area_flags_toggled(self):
        self._flag_toggled(self._show_area_flag_action, ['Area decrease'])

    def _invert_flags_toggled(self):
        self._flag_toggled(self._show_invert_flag_action, ['Adverse invert', 'Adverse gradient'])

    def _angle_flags_toggled(self):
        self._flag_toggled(self._show_angle_flag_action, ['Sharp angle'])

    def _cover_flags_toggled(self):
        self._flag_toggled(self._show_cover_flag_action, ['Insuff. Cover'])

    def _copy_plot_image_to_clipboard(self):
        buf = io.BytesIO()
        self.fig.savefig(buf)
        clipboard = QApplication.clipboard()
        clipboard.setImage(QImage.fromData(buf.getvalue()))
        buf.close()

    def _copy_plot_data_to_clipboard(self):
        data_ = self._collect_data('\t')
        clipboard = QApplication.clipboard()
        clipboard.setText(data_)

    def _copy_area_flag_to_clipboard(self):
        data_ = self._collect_flag_data(['Area decrease'], '\t')
        clipboard = QApplication.clipboard()
        clipboard.setText(data_)

    def _copy_invert_flag_to_clipboard(self):
        data_ = self._collect_flag_data(['Adverse invert', 'Adverse gradient'], '\t')
        clipboard = QApplication.clipboard()
        clipboard.setText(data_)

    def _copy_angle_flag_to_clipboard(self):
        data_ = self._collect_flag_data(['Sharp angle'], '\t')
        clipboard = QApplication.clipboard()
        clipboard.setText(data_)

    def _copy_cover_flag_to_clipboard(self):
        data_ = self._collect_flag_data(['Insuff. Cover'], '\t')
        clipboard = QApplication.clipboard()
        clipboard.setText(data_)

    def _export_plot_data(self):
        data_ = self._collect_data(',')
        if data_ is None:
            QMessageBox.warning(self, 'Export', 'No plot data to export')
            return

        self._export_data(data_)

    def _export_area_flag(self):
        data_ = self._collect_flag_data(['Area decrease'], ',')
        self._export_data(data_)

    def _export_invert_flag(self):
        data_ = self._collect_flag_data(['Adverse invert', 'Adverse gradient'], ',')
        self._export_data(data_)

    def _export_angle_flag(self):
        data_ = self._collect_flag_data(['Sharp angle'], ',')
        self._export_data(data_)

    def _export_cover_flag(self):
        data_ = self._collect_flag_data(['Insuff. Cover'], ',')
        self._export_data(data_)

    def _path_extent(self, i):
        feats = self.flowTraceTool.dataCollector.features

        rect = QgsRectangle()
        if 0 <= i < len(self.downstreamConnectivity.branches):
            for id_ in self.downstreamConnectivity.branches[i]:
                if id_ in feats:
                    rect.combineExtentWith(feats[id_].feature.geometry().buffer(20, 1).boundingBox())

        return rect

    def _zoom_to_paths(self):
        if self._context_menu is not None:
            self._context_menu.hide()

        if self.iface is None:
            QMessageBox.warning(self, 'Long Plot', 'Unexpected error - please contact support@tuflow.com')
            return

        rect = QgsRectangle()
        for item in self.paths.selectedItems():
            path = item.text()
            i = int(re.findall(r'\d+', path)[0]) - 1
            rect_ = self._path_extent(i)
            rect.combineExtentWith(rect_)

        map_canvas = self.iface.mapCanvas()
        map_canvas.setExtent(rect)
        map_canvas.refresh()


    def _zoom_to_feature(self):
        if self._context_menu is not None:
            self._context_menu.hide()

        if self.iface is None:
            QMessageBox.warning(self, 'Long Plot', 'Unexpected error - please contact support@tuflow.com')
            return

        if self.annot is None or (self.polygon is None and self.line is None):
            QMessageBox.warning(self, 'Long Plot', 'Unable to determine feature')
            return

        text = self.annot.get_text()
        id_ = re.findall(r'(?<=ID:).*(?=\n)', text)
        if not id_:
            QMessageBox.warning(self, 'Long Plot', 'Unable to determine feature')
            return
        id_ = id_[0].strip()
        if id_ not in self.flowTraceTool.dataCollector.features:
            QMessageBox.warning(self, 'Long Plot', 'Unable to determine feature')
            return
        feat = self.flowTraceTool.dataCollector.features[id_].feature

        map_canvas = self.iface.mapCanvas()
        map_canvas.setExtent(feat.geometry().buffer(20, 1).boundingBox())
        map_canvas.refresh()


class ChannelRubberBand:

    def __init__(self, iface=None):
        self._iface = iface
        self._map_canvas = None
        self._rubber_band = None
        self._visible = False
        self._geometry = None

        if iface is not None:
            self._map_canvas = iface.mapCanvas()

        self._rubber_band = QgsRubberBand(self._map_canvas)
        self._rubber_band.setWidth(2)
        self._rubber_band.setColor(Qt.red)

    def update_geometry(self, geometry):
        if self._iface is None:
            return
        self._geometry = geometry
        if self._visible:
            self._rubber_band.setToGeometry(self._geometry)
            self._map_canvas.refresh()

    def get_visible(self):
        return self._visible

    def set_visible(self, b):
        if b and self._geometry:
            self._rubber_band.setToGeometry(self._geometry)
            self._visible = True
        else:
            self._rubber_band.reset()
            self._visible = False

        if self._map_canvas is not None:
            self._map_canvas.refresh()
