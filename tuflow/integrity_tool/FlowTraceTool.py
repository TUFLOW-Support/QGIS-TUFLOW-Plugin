import os, sys
from qgis.core import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal, QThread, QTimer
from .DataCollector import DataCollector
from .ContinuityTool import ContinuityTool
from .FeatureData import FeatureData
from .Enumerators import *
from .FlowTraceLongPlot import DownstreamConnectivity
from tuflow.forms.flowtrace_plot import Ui_flowTracePlot
from tuflow.PlotDialog import PlotDialog
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg


class FlowTraceTool(ContinuityTool):
    
    def __init__(self, iface=None, dataCollector=None, outputLyr=None, limitAngle=0, limitCover=99999, limitArea=100,
                 checkArea=False, checkAngle=False, checkInvert=False, checkCover=False, dataCollectorPoints=None):
        
        ContinuityTool.__init__(self, iface, dataCollector, outputLyr, limitAngle, limitCover, limitArea,
                                checkArea, checkAngle, checkInvert, checkCover)
        
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
    
    def finishedFeature(self, feature, layer, snappedFeatures, snappedLayers):
        """
        Place holder for flow trace object to override.
        
        :param feature: QgsFeature
        :param snappedFeatures: list -> QgsFeature
        :param snappedLayers: list -> QgsVectorLayer
        :return: void
        """
        
        DataCollector.finishedFeature(self, feature, layer, snappedFeatures, snappedLayers)
        
        for i, feature in enumerate(snappedFeatures):
            if feature not in self.featuresAssessed and feature not in self.featuresToAssess:
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
        
class FlowTracePlot(PlotDialog, Ui_flowTracePlot):
    
    finished = pyqtSignal()
    updated = pyqtSignal()
    updateMessage = pyqtSignal()
    
    def __init__(self, iface=None, flowTraceTool=None):
        if iface is not None:
            parent = iface.mainWindow()
        else:
            parent = None
        QDialog.__init__(self, parent=parent)
        self.setupUi(self)
        self.iface = iface
        self.flowTraceTool = flowTraceTool
        
        # initialise plot
        self.fig, self.ax = plt.subplots()
        self.plotWidget = FigureCanvasQTAgg(self.fig)
        self.ax.set_xbound(0, 1000)
        self.ax.set_ybound(0, 1000)
        self.manageMatplotlibAxe(self.ax)
        self.plotLayout.addWidget(self.plotWidget)
        
        # intialise signal connections
        self.paths.itemSelectionChanged.connect(self.drawPlot)
        self.pbSelectPath.clicked.connect(self.selectPathInWorkspace)
        self.resized.connect(self.resizePlot)
        
        # get paths
        self.getPaths()
        
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
        
    def selectPathInWorkspace(self):
        """
        
        :return:
        """
        
        layers = []
        fids = []
        nwks = []
        for i in range(self.paths.count()):
            item = self.paths.item(i)
    
            if item.isSelected():
                pathName = item.text()
                for nwk in self.downstreamConnectivity.usedPathNwks[i]:
                    if type(nwk) is list:
                        nwks += nwk
                    else:
                        nwks.append(nwk)

        for id in self.flowTraceTool.dataCollector.ids:
            if id in nwks:
                fData = self.flowTraceTool.dataCollector.features[id]
                if fData.layer not in layers:
                    layers.append(fData.layer)
                    fids.append([fData.fid])
                else:
                    i = layers.index(fData.layer)
                    fids[i].append(fData.fid)
                        
        for i, layer in enumerate(layers):
            layer.selectByIds(fids[i])
        
    def getPaths(self):
        """
        
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
        self.timer.timeout.connect(self.updated.emit)
        
        self.timer2 = QTimer()
        self.timer2.setInterval(120000)
        self.timer2.setSingleShot(True)
        self.timer2.timeout.connect(self.updateMessage.emit)
        
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
        self.finished.emit()
            
    def drawPlot(self):
        """
        
        :return:
        """
        
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
                    x = self.downstreamConnectivity.pathsX[j][:]
                    y = self.downstreamConnectivity.pathsInvert[j][:]
                    label = '{0}: Invert'.format(pathName)
                    self.ax.plot(x, y, label=label)
                    
                    # ground
                    x = self.downstreamConnectivity.pathsGroundX[j][:]
                    y = self.downstreamConnectivity.pathsGroundY[j][:]
                    label = '{0}: Ground'.format(pathName)
                    if y:
                        self.ax.plot(x, y, label=label)
                    
                    # pipes
                    label = '{0}: Pipes'.format(pathName)
                    for poly in self.downstreamConnectivity.pathsPipe[j]:
                        if poly:
                            for v in poly:
                                ymax = max(ymax, v[1])
                            p = Polygon(poly, facecolor='0.9', edgecolor='0.5', label=label)
                            self.ax.add_patch(p)
                        
                    # area flag
                    if self.downstreamConnectivity.pathsPlotDecA[j][1]:
                        x = self.downstreamConnectivity.pathsPlotDecA[j][0][:]
                        y = self.downstreamConnectivity.pathsPlotDecA[j][1][:]
                        label = '{0}: Area Decrease'.format(pathName)
                        self.ax.plot(x, y, label=label, linestyle='None', marker='o')
                        
                    # invert flag
                    if self.downstreamConnectivity.pathsPlotAdvI[j][1]:
                        x = self.downstreamConnectivity.pathsPlotAdvI[j][0][:]
                        y = self.downstreamConnectivity.pathsPlotAdvI[j][1][:]
                        label = '{0}: Adverse Invert'.format(pathName)
                        self.ax.plot(x, y, label=label, linestyle='None', marker='o')

                    # gradient flag
                    if self.downstreamConnectivity.pathsPlotAdvG[j][1]:
                        x = self.downstreamConnectivity.pathsPlotAdvG[j][0][:]
                        y = self.downstreamConnectivity.pathsPlotAdvG[j][1][:]
                        label = '{0}: Adverse Gradient'.format(pathName)
                        self.ax.plot(x, y, label=label, linestyle='None', marker='o')

                    # angle flag
                    if self.downstreamConnectivity.pathsPlotSharpA[j][1]:
                        x = self.downstreamConnectivity.pathsPlotSharpA[j][0][:]
                        y = self.downstreamConnectivity.pathsPlotSharpA[j][1][:]
                        label = '{0}: Sharp Angle'.format(pathName)
                        self.ax.plot(x, y, label=label, linestyle='None', marker='o')

                    # cover flag
                    if self.downstreamConnectivity.pathsPlotInCover[j][1]:
                        x = self.downstreamConnectivity.pathsPlotInCover[j][0][:]
                        y = self.downstreamConnectivity.pathsPlotInCover[j][1][:]
                        label = '{0}: Insufficient Cover'.format(pathName)
                        self.ax.plot(x, y, label=label, linestyle='None', marker='o')
                    
        # set axis y max - matplotlib doesn't consider patches when it automates this step
        self.setYMax(ymax)
        
        # set legend - remove duplicate 'pipe' entries
        self.setLegend()
        
        # draw
        self.fig.tight_layout()
        self.plotWidget.draw()
        
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
            if lab not in uniqueLabs:
                uniqueLabs.append(lab)
                uniqueLines.append(lines[i])
        
        self.ax.legend(uniqueLines, uniqueLabs)