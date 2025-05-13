from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon
from matplotlib.collections import PolyCollection, PathCollection
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from ..forms.ArchBridgePlot import Ui_BridgePlot
import numpy as np
import math
from ..dataset_menu import DatasetMenu

from .Plotter import Plotter



from ..compatibility_routines import QT_EVENT_MOUSE_BUTTON_PRESS, QT_CUSTOM_CONTEXT_MENU, QT_RIGHT_BUTTON


def make_patch_spines_invisible(ax):
    ax.set_frame_on(True)
    ax.patch.set_visible(False)
    for sp in ax.spines.values():
        sp.set_visible(False)


class BridgePlot(QDialog, Ui_BridgePlot):
    
    def __init__(self, parent, xData, yData, x2Data, y2Data, labels, bridges=(), xsArea=(), bgArea=(), bgBlockage=(),
                 **kwargs):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.xData = xData
        self.yData = yData
        self.x2Data = x2Data
        self.y2Data = y2Data
        self.labels = labels
        self.bridges = bridges
        self.xsArea = xsArea
        self.bgArea = bgArea
        self.bgBlockage = bgBlockage

        self.plot_mannings = False
        self.plot_bridge = bool(xData)
        self.plot_curves = kwargs['plot_curves'] if 'plot_curves' in kwargs else False
        self.has_plot_curves = xsArea is not None and bgArea is not None and bgBlockage is not None \
                               and type(xsArea) is not tuple and type(bgArea) is not tuple \
                               and type(bgBlockage) is not tuple \
                               and xsArea.any() and bgArea.any() and bgBlockage.any()
        self.switch_axis = False  # for bridge curve only plot
        self.legendPos = 0  # auto
        
        self.pbClose.clicked.connect(self.accept)

        self.plotter = Plotter()
        if self.plot_mannings:
            # self.fig, self.axs = plt.subplots(nrows=2, sharex=True)
            self.fig, self.axs = self.plotter.subplots(nrows=2, sharex=True)
            self.ax = self.axs[1]
            self.ax2 = self.axs[0]
            self.ax3 = None
        else:
            # self.fig, self.ax = plt.subplots()
            self.fig, self.ax = self.plotter.subplots()
            self.ax2 = None
            self.ax3 = None

        self.plotWidget = FigureCanvasQTAgg(self.fig)
        self.plotLayout.addWidget(self.plotWidget)
        self.bridge = None
        self.channel = None
        self.bridge_data = np.array(sum([x.tolist() for x in bridges], []))
        self.channel_data = []

        # context menu
        self.contextMenuConnected = True
        self.rightMouseButtonHeld = False
        self.loadContextMenu()
        self.plotWidget.setContextMenuPolicy(QT_CUSTOM_CONTEXT_MENU)
        self.plotWidget.customContextMenuRequested.connect(self.showContextMenu)
        self.fig.canvas.mpl_connect('button_press_event', self.right_click_event)
        self.fig.canvas.mpl_connect('motion_notify_event', self.motion_event)

        # hover labels
        # self.fig.canvas.mpl_connect("motion_notify_event", self.hover)

        self.drawPlot()

    def setBridgeCurves(self, xsArea, bgArea, bgBlockage):
        """Sets the bridge curve properties."""

        self.has_plot_curves = xsArea is not None and bgArea is not None and bgBlockage is not None \
                               and type(xsArea) is not tuple and type(bgArea) is not tuple \
                               and type(bgBlockage) is not tuple \
                               and xsArea.any() and bgArea.any() and bgBlockage.any()

        if self.has_plot_curves:
            self.xsArea = xsArea
            self.bgArea = bgArea
            self.bgBlockage = bgBlockage
            return True
        else:
            return False

    def right_click_event(self, e):
        if e.guiEvent.type() == QT_EVENT_MOUSE_BUTTON_PRESS and e.guiEvent.button() == QT_RIGHT_BUTTON:
            self.rightMouseButtonHeld = True

    def motion_event(self, e):
        if self.rightMouseButtonHeld:
            for action in self.mplTools.actions():
                if action.isChecked():
                    # disconnect context menu
                    self.contextMenuConnected = False
                    return

    def loadContextMenu(self):
        """Load context menu options"""

        self.menu = QMenu(self.plotWidget)

        self.mplTools = NavigationToolbar2QT(self.plotWidget, None)
        self.menu.addActions(self.mplTools.actions()[:6])
        self.menu.addActions(self.mplTools.actions()[7:10])

        self.menu.addSeparator()
        self.switchAxis_action = QAction('Switch axis', self.menu)
        self.switchAxis_action.triggered.connect(self.switchAxis)
        self.menu.addAction(self.switchAxis_action)

        self.menu.addSeparator()
        self.showBridgeCurves_action = QAction('Show bridge curves', self.menu)
        self.showBridgeCurves_action.setCheckable(True)
        self.showBridgeCurves_action.triggered.connect(self.showBridgeCurvesToggled)
        self.menu.addAction(self.showBridgeCurves_action)

        self.menu.addSeparator()
        self.legendMenu = DatasetMenu('&Legend')
        self.legendAuto_action = QAction('Auto')
        self.legendAuto_action.setCheckable(True)
        self.legendAuto_action.setChecked(True)
        self.legendAuto_action.triggered.connect(lambda: self.toggleLegendPos(self.legendAuto_action))
        self.legendMenu.addAction(self.legendAuto_action)
        self.legendUR_action = QAction('Upper Right')
        self.legendUR_action.setCheckable(True)
        self.legendUR_action.triggered.connect(lambda: self.toggleLegendPos(self.legendUR_action))
        self.legendMenu.addAction(self.legendUR_action)
        self.legendUL_action = QAction('Upper Left')
        self.legendUL_action.setCheckable(True)
        self.legendUL_action.triggered.connect(lambda: self.toggleLegendPos(self.legendUL_action))
        self.legendMenu.addAction(self.legendUL_action)
        self.legendLL_action = QAction('Lower Left')
        self.legendLL_action.setCheckable(True)
        self.legendLL_action.triggered.connect(lambda: self.toggleLegendPos(self.legendLL_action))
        self.legendMenu.addAction(self.legendLL_action)
        self.legendLR_action = QAction('Lower Right')
        self.legendLR_action.setCheckable(True)
        self.legendLR_action.triggered.connect(lambda: self.toggleLegendPos(self.legendLR_action))
        self.legendMenu.addAction(self.legendLR_action)
        self.legendCL_action = QAction('Centre Left')
        self.legendCL_action.setCheckable(True)
        self.legendCL_action.triggered.connect(lambda: self.toggleLegendPos(self.legendCL_action))
        self.legendMenu.addAction(self.legendCL_action)
        self.legendCR_action = QAction('Centre Right')
        self.legendCR_action.setCheckable(True)
        self.legendCR_action.triggered.connect(lambda: self.toggleLegendPos(self.legendCR_action))
        self.legendMenu.addAction(self.legendCR_action)
        self.legendLC_action = QAction('Lower Centre')
        self.legendLC_action.setCheckable(True)
        self.legendLC_action.triggered.connect(lambda: self.toggleLegendPos(self.legendLC_action))
        self.legendMenu.addAction(self.legendLC_action)
        self.legendUC_action = QAction('Upper Centre')
        self.legendUC_action.setCheckable(True)
        self.legendUC_action.triggered.connect(lambda: self.toggleLegendPos(self.legendUC_action))
        self.legendMenu.addAction(self.legendUC_action)
        self.legendC_action = QAction('Centre')
        self.legendC_action.setCheckable(True)
        self.legendC_action.triggered.connect(lambda: self.toggleLegendPos(self.legendC_action))
        self.legendMenu.addAction(self.legendC_action)
        self.menu.addMenu(self.legendMenu)

    def toggleLegendPos(self, action):
        actions = [self.legendAuto_action, self.legendUR_action, self.legendUL_action, self.legendLL_action,
                   self.legendLR_action, self.legendCL_action, self.legendCR_action, self.legendLC_action,
                   self.legendUC_action, self.legendC_action]

        if action is not None:
            for a in actions:
                if a == action:
                    if not action.isChecked():
                        self.legendMenu.menuAction().setChecked(False)
                    else:
                        self.legendMenu.menuAction().setChecked(True)
                else:
                    a.setChecked(False)

        self.legend(update=True)

    def refreshContextMenuOptions(self):
        """Refresh context menu options based on what's loaded in the tool"""

        if self.plot_bridge:
            self.switchAxis_action.setVisible(False)
            self.showBridgeCurves_action.setVisible(True)
            if self.has_plot_curves:
                self.showBridgeCurves_action.setEnabled(True)
            else:
                self.showBridgeCurves_action.setEnabled(False)
        else:
            self.switchAxis_action.setVisible(True)
            self.showBridgeCurves_action.setVisible(False)

    def showContextMenu(self, pos):
        """Context menu on plot"""

        self.rightMouseButtonHeld = False
        if not self.contextMenuConnected:
            self.contextMenuConnected = True
            return

        self.refreshContextMenuOptions()
        self.menu.popup(self.plotWidget.mapToGlobal(pos))

    def switchAxis(self):
        """Switch plot axis around"""

        if not self.plot_bridge:
            self.switch_axis = not self.switch_axis
            self.drawPlot()

    def showBridgeCurvesToggled(self):
        """Toggle bridge curves on bridge plot on/off"""

        self.plot_curves = self.showBridgeCurves_action.isChecked()
        self.drawPlot()

    def manageAx(self):
        """
        Applies a few grid settings.
        
        :return: void
        """
        
        for ax in [self.ax, self.ax2, self.ax3]:
            if ax is None:
                continue
            if ax == self.ax:
                ax.grid()
            elif ax == self.ax2:
                ax.grid(linestyle='--')
            elif ax == self.ax3:
                ax.grid(linestyle=':')
                ax.spines['top'].set_position(('axes', 1.2))
                make_patch_spines_invisible(ax)
                ax.spines['top'].set_visible(True)
            if ax == self.ax:
                ax.tick_params(axis="both", which="major", direction="out", length=10, width=1, bottom=True, top=False,
                                left=True, right=False)
            if ax == self.ax:
                ax.minorticks_on()
                ax.tick_params(axis="both", which="minor", direction="out", length=5, width=1, bottom=True, top=False,
                               left=True, right=False)

        # axis names
        if self.plot_bridge:
            self.ax._label = 'Chainage (Primary Axis)'
            if self.ax2 is not None:
                self.ax2._label = 'Area (Secondary Axis)'
            if self.ax3 is not None:
                self.ax3._label = 'Blockage (Secondary Axis)'
        elif self.plot_curves:
            self.ax._label = 'Area (Primary Axis)'
            if self.ax2 is not None:
                self.ax2._label = 'Blockage (Secondary Axis)'

        # setup hover over labels
        self.annotation = self.ax.annotate("debug", xy=(15, 15), xycoords='data', textcoords="offset pixels",
                                           bbox=dict(boxstyle="round", fc="w"))
        self.annotation.set_visible(False)
        self.annotation2 = None
        if self.ax2 is not None:
            self.annotation2 = self.ax2.annotate("debug", xy=(15, 15), xycoords='data', textcoords="offset pixels",
                                                 bbox=dict(boxstyle="round", fc="w"))
            self.annotation2.set_visible(False)
        self.annotation3 = None
        if self.ax3 is not None:
            self.annotation3 = self.ax3.annotate("debug", xy=(15, 15), xycoords='data', textcoords="offset pixels",
                                                 bbox=dict(boxstyle="round", fc="w"))
            self.annotation3.set_visible(False)
        self.hover_point = self.ax.scatter(10, 30, 20, 'red')
        self.hover_point.set_visible(False)
        self.hover_point2 = None
        if self.ax2 is not None:
            self.hover_point2 = self.ax2.scatter(10, 30, 20, 'red')
            self.hover_point2.set_visible(False)
        self.hover_point3 = None
        if self.ax3 is not None:
            self.hover_point3 = self.ax3.scatter(10, 30, 20, 'red')
            self.hover_point3.set_visible(False)

    def axisNames(self):
        """
        Applies axis names
        
        :return: void
        """

        if self.plot_bridge:
            self.ax.set_xlabel('Cross Chainage (m)')
            self.ax.set_ylabel('Elevation (m)')
            if self.ax2 is not None:
                # self.ax2.set_ylabel("Manning's n")
                self.ax2.set_xlabel('Area (m$^2$)')
            if self.ax3 is not None:
                self.ax3.set_xlabel('Blockage')
        elif self.plot_curves:
            if self.switch_axis:
                self.ax.set_ylabel('Area (m$^2$)')
                self.ax.set_xlabel('Elevation (m)')
                if self.ax2 is not None:
                    self.ax2.set_ylabel('Blockage')
            else:
                self.ax.set_xlabel('Area (m$^2$)')
                self.ax.set_ylabel('Elevation (m)')
                if self.ax2 is not None:
                    self.ax2.set_xlabel('Blockage')
        
    def axisTicks(self):
        """
        
        :return: void
        """

        if self.plot_bridge:
            uniqueValues = []
            for y in self.y2Data:
                for a in y:
                    if a not in uniqueValues:
                        uniqueValues.append(a)

            uniqueValues = sorted(uniqueValues)
            if self.ax2 is not None:
                self.ax2.set_yticks(uniqueValues)
        
    def legend(self, update=False):
        """
        Applies legend.
        
        :return: void
        """

        # get legend labels and artists
        uniqueNames, uniqueNames2, uniqueLines, uniqueLines2 = [], [], [], []
        
        # primary axis
        line, lab = self.ax.get_legend_handles_labels()
        # remove duplicates i.e. culvert and pipes only need to appear in legend once
        for i, l in enumerate(lab):
            if l not in uniqueNames:
                uniqueNames.append(l)
                uniqueLines.append(line[i])
        
        # secondary axis
        line2 = []
        lab2 = []
        if self.ax2 is not None:
            line2, lab2 = self.ax2.get_legend_handles_labels()
        # remove duplicates i.e. culvert and pipes only need to appear in legend once
        uniqueNames2 = []
        uniqueLines2 = []
        for i, l in enumerate(lab2):
            if l not in uniqueNames:
                uniqueNames2.append(l)
                uniqueLines2.append(line2[i])

        # third axis
        line3 = []
        lab3 = []
        if self.ax3 is not None:
            line3, lab3 = self.ax3.get_legend_handles_labels()
        # remove duplicates i.e. culvert and pipes only need to appear in legend once
        uniqueNames3 = []
        uniqueLines3 = []
        for i, l in enumerate(lab3):
            if l not in uniqueNames:
                uniqueNames3.append(l)
                uniqueLines3.append(line3[i])
        
        lines = uniqueLines + uniqueLines2 + uniqueLines3
        labels = uniqueNames + uniqueNames2 + uniqueNames3

        # legend position
        legendPos = -1
        if self.legendAuto_action.isChecked():
            legendPos = 0
        elif self.legendUR_action.isChecked():
            legendPos = 1
        elif self.legendUL_action.isChecked():
            legendPos = 2
        elif self.legendLL_action.isChecked():
            legendPos = 3
        elif self.legendLR_action.isChecked():
            legendPos = 4
        elif self.legendCL_action.isChecked():
            legendPos = 6
        elif self.legendCR_action.isChecked():
            legendPos = 7
        elif self.legendLC_action.isChecked():
            legendPos = 8
        elif self.legendUC_action.isChecked():
            legendPos = 9
        elif self.legendC_action.isChecked():
            legendPos = 10

        if legendPos == 0:
            self.ax.legend(lines, labels)
        elif 0 < legendPos <= 10:
            self.ax.legend(lines, labels, loc=legendPos)
        elif self.ax.get_legend() is not None:
            self.ax.get_legend().remove()

        if update:
            self.plotWidget.draw_idle()
        
    def setLimits(self):
        """
        
        :return:
        """

        if self.plot_bridge:
            ymin, ymax = 99999, -99999
            for y in self.yData:
                for a in y:
                    ymin = min(a, ymin)
                    ymax = max(a, ymax)
            range = ymax - ymin
            ymin -= range * 0.15
            ymax += range * 0.15

            xmin, xmax = 99999, -99999
            for x in self.xData:
                for a in x:
                    xmin = min(a, xmin)
                    xmax = max(a, xmax)

            self.ax.set_ylim((ymin, ymax))
            self.ax.set_xlim((xmin, xmax))
            self.addWhiteSpace(self.ax, 'x', xmin, xmax, 0.01)
            if self.ax2 is not None:
                xmin, xmax = 99999, -99999
                for a in self.ax2.lines:
                    xmin = min(xmin, np.nanmin(a.get_xdata()))
                    xmax = max(xmax, np.nanmax(a.get_xdata()))
                self.ax2.set_xlim((xmin, xmax))
                self.addWhiteSpace(self.ax2, 'x', xmin, xmax, 0.05)
            if self.ax3 is not None:
                xmin, xmax = 99999, -99999
                for a in self.ax3.lines:
                    xmin = min(xmin, np.nanmin(a.get_xdata()))
                    xmax = max(xmax, np.nanmax(a.get_xdata()))
                self.ax3.set_xlim((xmin, xmax))
                self.addWhiteSpace(self.ax3, 'x', xmin, xmax, 0.05)
        elif self.plot_curves:
            ymin, ymax = 99999, -99999
            xmin, xmax = 99999, -99999
            for a in self.ax.lines:
                ymin = min(ymin, np.nanmin(a.get_ydata()))
                ymax = max(ymax, np.nanmax(a.get_ydata()))
                xmin = min(xmin, np.nanmin(a.get_xdata()))
                xmax = max(xmax, np.nanmax(a.get_xdata()))
            self.ax.set_xlim((xmin, xmax))
            self.ax.set_ylim((ymin, ymax))
            self.addWhiteSpace(self.ax, 'x', xmin, xmax, 0.05)
            self.addWhiteSpace(self.ax, 'y', ymin, ymax, 0.05)
            if self.ax2 is not None:
                xmin, xmax = 99999, -99999
                ymin, ymax = 99999, -99999
                for a in self.ax2.lines:
                    if self.switch_axis:
                        ymin = min(ymin, np.nanmin(a.get_ydata()))
                        ymax = max(ymax, np.nanmax(a.get_ydata()))
                    else:
                        xmin = min(xmin, np.nanmin(a.get_xdata()))
                        xmax = max(xmax, np.nanmax(a.get_xdata()))
                if self.switch_axis:
                    self.ax2.set_ylim((ymin, ymax))
                    self.addWhiteSpace(self.ax2, 'y', ymin, ymax, 0.05)
                else:
                    self.ax2.set_xlim((xmin, xmax))
                    self.addWhiteSpace(self.ax2, 'x', xmin, xmax, 0.05)

    def addWhiteSpace(self, ax, axis, min_, max_, f):
        """
        Relimit axis, adding white space around data limits.

        """

        if axis == 'x':
            td0 = ax.transData.transform((min_, 0))
            td1 = ax.transData.transform((max_, 0))
            td2 = td0[0] - (td1[0] - td0[0]) * f
            td3 = td1[0] + (td1[0] - td0[0]) * f
            xmin = ax.transData.inverted().transform((td2, td0[1]))[0]
            xmax = ax.transData.inverted().transform((td3, td1[1]))[0]
            ax.set_xlim([xmin, xmax])
        elif axis == 'y':
            td0 = ax.transData.transform((min_, 0))
            td1 = ax.transData.transform((max_, 0))
            td2 = td0[0] - (td1[0] - td0[0]) * f
            td3 = td1[0] + (td1[0] - td0[0]) * f
            ymin = ax.transData.inverted().transform((td2, td0[1]))[0]
            ymax = ax.transData.inverted().transform((td3, td1[1]))[0]
            ax.set_ylim([ymin, ymax])
    
    def addPatch(self, typ, xs, ys, xs2=(), ys2=(), bridge=None):
        """
        Add matplotlib patch for terrain and bridge
        
        :param typ: str
        :param xs: list -> float
        :param ys: list -> float
        :param xs2: list -> float
        :param ys2: list -> float
        :return: void
        """

        if typ == 'ground':
            if len(xs) == len(ys):
                ymin = min(ys)
                verts = []
                for i, x in enumerate(xs):
                    y = ys[i]
                    verts.append((x, y))
                verts.append((xs[-1] + 20, ys[-1]))
                verts.append((xs[-1], ymin - 20))
                verts.append((xs[0], ymin - 20))
                verts.append((xs[0] - 20, ys[0]))

                polygon = Polygon(verts, facecolor='brown')
                self.channel = self.ax.add_patch(polygon)
                self.channel_data = self.channel.get_xy()
                
        elif typ == 'bridge':
            if len(xs) == len(ys):
                # reorder bridge data so that it goes low -> high
                key = {}
                for i, xData in enumerate(xs):
                    if xData.any():
                        key[tuple(ys[i])] = xData[0]
                xsSorted = sorted(xs, key=lambda x: x[0])
                ysSorted = sorted(ys, key=lambda x: key[tuple(x)])
                
                # follow terrain data in-between bridges
                xWithTerrain = []
                yWithTerrain = []
                for i, xData in enumerate(xsSorted[:]):
                    if i > 0:
                        x = xData[0]
                        xprev = xsSorted[i-1][-1]
                        # xi = xs2.index(x)
                        # xi = int(np.where(xs2 == x)[0])
                        # xprevi = xs2.index(xprev)
                        # xprevi = int(np.where(xs2 == xprev)[0])
                        a1 = np.where(xs2 < x)
                        a2 = np.where(xprev < xs2)
                        ai = np.intersect1d(a1, a2)
                        xterrain = [xprev]
                        yterrain = [np.interp(xprev, xs2, ys2)]
                        if ai.shape[0]:
                            for j in ai:
                                xterrain.append(xs2[j])
                                yterrain.append(ys2[j])
                        xWithTerrain.append(xterrain)
                        yWithTerrain.append(yterrain)
                    xWithTerrain.append(xData.tolist())
                    yWithTerrain.append(ys[i].tolist())
                
                # combine bridge data into one list
                xsBridge = sum(xWithTerrain, [])
                ysBridge = sum(yWithTerrain, [])
                
                # implement bridge patch following terrain on either side of bridge
                ymax = max(ysBridge)
                xmin = min(xs2)
                xmax = max(xs2)
                x0 = xsBridge[0]
                x1 = xsBridge[-1]
                verts = []
                for i, x in enumerate(xs2):
                    if x < x0:
                        y = ys2[i]
                        verts.append((x, y))
                    else:
                        break
                for i, x in enumerate(xsBridge):
                    y = ysBridge[i]
                    verts.append((x, y))
                for i, x in enumerate(xs2):
                    if x > x1:
                        y = ys2[i]
                        verts.append((x, y))
                verts.append((xmax + 20, ys2[-1]))
                verts.append((xmax + 20, ymax + 20))
                verts.append((xmin - 20, ymax + 20))
                verts.append((xmin - 20, ys2[0]))

                polygon = Polygon(verts, facecolor='0.9')
                self.bridge = self.ax.add_patch(polygon)

    def drawPlot(self):
        """
        Draw plot based on data passed in through
        initialisation.
        
        :return: void
        """

        self.ax.cla()
        if self.ax2 is not None:
            self.fig.delaxes(self.ax2)
            self.ax2 = None
        if self.ax3 is not None:
            self.fig.delaxes(self.ax3)
            self.ax3 = None

        # bridge and cross section
        if self.plot_bridge:
            # primary axis
            xChannel, yChannel = None, None
            xBridges, yBridges = [], []
            if len(self.xData) == len(self.yData) == len(self.labels):
                for i, x in enumerate(self.xData):
                    y = self.yData[i]
                    label = self.labels[i]
                    if label.lower() == 'channel':
                        xChannel = x[:]
                        yChannel = y[:]
                        colour = 'brown'
                        self.addPatch('ground', x, y)
                    elif label.lower() == 'bridge':
                        colour = 'black'
                        xBridges.append(x)
                        yBridges.append(y)
                    else:
                        colour = 'blue'
                    if len(x) == len(y):
                        self.ax.plot(x, y, label=label, color=colour)

                if xChannel is not None and yChannel is not None:
                    if xBridges and yBridges:
                        self.addPatch("bridge", xBridges, yBridges, xChannel, yChannel)

        # bridge curves
        if self.plot_curves:
            for curve, label in [(self.xsArea, 'Unobstructed Area'), (self.bgArea, 'Bridge Opening Area'), (self.bgBlockage, 'Blockage')]:
                if curve is None or not curve.any():
                    continue

                i, j = (0, 1) if self.switch_axis else (1, 0)
                if self.ax2 is None:
                    if self.switch_axis:
                        self.ax2 = self.ax.twinx()
                    else:
                        self.ax2 = self.ax.twiny()
                if self.plot_bridge and self.ax3 is None:
                    self.ax3 = self.ax.twiny()
                if label != 'Blockage':
                    if self.plot_bridge:
                        self.ax2.plot(curve[:, i], curve[:, j], label=label)
                    else:
                        self.ax.plot(curve[:,i], curve[:,j], label=label)
                else:
                    if self.plot_bridge:
                        self.ax3.plot(curve[:, i], curve[:, j], label=label, color='green')
                    else:
                        self.ax2.plot(curve[:,i], curve[:,j], label=label, color='green')

        self.manageAx()
        self.axisNames()
        self.legend()
        self.setLimits()
        self.fig.tight_layout()
        self.fig.set_tight_layout(True)
        self.plotWidget.draw()
