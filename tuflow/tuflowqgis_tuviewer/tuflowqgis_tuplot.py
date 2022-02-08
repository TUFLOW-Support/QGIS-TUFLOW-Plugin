from datetime import datetime, timedelta
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from qgis.gui import QgsVertexMarker
from PyQt5.QtWidgets  import *
import sys
import os
import re
import matplotlib
import numpy as np
import numpy.ma as ma
try:
	import matplotlib.pyplot as plt
except:
	current_path = os.path.dirname(__file__)
	plugin_folder = os.path.dirname(current_path)
	sys.path.append(os.path.join(plugin_folder, '_tk\\DLLs'))
	sys.path.append(os.path.join(plugin_folder, '_tk\\libs'))
	sys.path.append(os.path.join(plugin_folder, '_tk\\Lib'))
	import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.patches import Polygon
import matplotlib.dates as mdates
import matplotlib.ticker
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.quiver import Quiver
from matplotlib.collections import PolyCollection, PathCollection
import matplotlib.gridspec as gridspec
from matplotlib.pyplot import arrow, ScalarFormatter
from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.dates import date2num, num2date
# from matplotlib.backend_bases import MouseButton
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplottoolbar import TuPlotToolbar
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplotselection import TuPlotSelection
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turubberband import TuRubberBand, TuMarker
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuflowline import TuFlowLine
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot2d import TuPlot2D
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot1d import TuPlot1D
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuuserplotdata import TuUserPlotDataManager
from tuflow.tuflowqgis_library import (applyMatplotLibArtist, getMean, roundSeconds, convert_datetime_to_float,
                                       generateRandomMatplotColours2, saveMatplotLibArtist,
                                       polyCollectionPathIndexFromXY, regex_dict_val, datetime2timespec,
                                       convertFormattedTimeToTime, getPolyCollectionData)
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot3d import (TuPlot3D, ColourBar)



class TuPlot():
	"""
	Class for plotting.
	
	"""

	TimeSeries = 0
	CrossSection = 1
	CrossSection1D = 2
	VerticalProfile = 3
	TotalPlotNo = 4

	DataTimeSeries2D = 100
	DataCrossSection2D = 101
	DataFlow2D = 102
	DataTimeSeries1D = 103
	DataCrossSection1D = 104
	DataUserData = 105
	DataCurrentTime = 106
	DataTimeSeriesStartLine = 107
	DataCrossSectionStartLine = 108
	DataCrossSectionStartLine1D = 109
	DataCurtainPlot = 110
	DataTimeSeriesDepAv = 111
	DataCrossSectionDepAv = 112
	DataVerticalProfileStartLine = 113
	DataVerticalProfile = 114
	DataCrossSection1DViewer = 115
	DataHydraulicProperty = 116
	DataVerticalMesh = 117

	def __init__(self, TuView):
		self.tuView = TuView
		self.iface = self.tuView.iface
		self.canvas = self.tuView.canvas

		# Initialise figures
		# time series
		self.layoutTimeSeries = self.tuView.TimeSeriesFrame.layout()
		self.figTimeSeries, self.subplotTimeSeries = plt.subplots()
		self.plotWidgetTimeSeries = FigureCanvasQTAgg(self.figTimeSeries)
		self.plotWidgetTimeSeries.setMinimumWidth(0)
		self.figTimeSeries.canvas.mpl_connect('button_press_event', lambda e: self.onclick(e, TuPlot.TimeSeries))
		self.timeSeriesAnnot = self.subplotTimeSeries.annotate("debug", xy=(15,15),
		                                                       xycoords='data',
		                                                       # xycoords=self.subplotTimeSeries.transData.transform,
		                                                       textcoords="offset pixels",
                                                               bbox=dict(boxstyle="round", fc="w"))
		self.timeSeriesAnnot.set_visible(False)
		self.timeSeriesHoverPoint = self.subplotTimeSeries.scatter(0, 0, 20, 'red')
		self.timeSeriesHoverPoint.set_visible(False)
		self.figTimeSeries.canvas.mpl_connect("motion_notify_event", lambda e: self.hover(e, TuPlot.TimeSeries))

		
		# long plot
		self.layoutLongPlot = self.tuView.LongPlotFrame.layout()
		self.figLongPlot, self.subplotLongPlot = plt.subplots()
		self.plotWidgetLongPlot = FigureCanvasQTAgg(self.figLongPlot)
		self.plotWidgetLongPlot.setMinimumWidth(0)
		self.figLongPlot.canvas.mpl_connect('button_press_event', lambda e: self.onclick(e, TuPlot.CrossSection))
		self.longPlotAnnot = self.subplotLongPlot.annotate("debug", xy=(15, 15), xycoords='data',
		                                                       textcoords="offset pixels",
		                                                       bbox=dict(boxstyle="round", fc="w"))
		self.longPlotAnnot.set_visible(False)
		self.longPlotHoverPoint = self.subplotLongPlot.scatter(0, 0, 20, 'red')
		self.longPlotHoverPoint.set_visible(False)
		self.figLongPlot.canvas.mpl_connect("motion_notify_event", lambda e: self.hover(e, TuPlot.CrossSection))
		self.figLongPlot.canvas.mpl_connect("motion_notify_event", self.updateCursorMarker)

		# cross section
		self.layoutCrossSection = self.tuView.CrossSectionFrame.layout()
		self.figCrossSection, self.subplotCrossSection = plt.subplots()
		self.plotWidgetCrossSection = FigureCanvasQTAgg(self.figCrossSection)
		self.plotWidgetCrossSection.setMinimumWidth(0)
		self.figCrossSection.canvas.mpl_connect('button_press_event', lambda e: self.onclick(e, TuPlot.CrossSection1D))
		self.crossSectionAnnot = self.subplotCrossSection.annotate("debug", xy=(15, 15),
		                                                           xycoords='data',
		                                                           textcoords="offset pixels",
		                                                           bbox=dict(boxstyle="round", fc="w"))
		self.crossSectionAnnot.set_visible(False)
		self.crossSectionHoverPoint = self.subplotCrossSection.scatter(0, 0, 20, 'red')
		self.crossSectionHoverPoint.set_visible(False)
		self.figCrossSection.canvas.mpl_connect("motion_notify_event", lambda e: self.hover(e, TuPlot.CrossSection1D))

		# vertical profile
		self.layoutVerticalProfile = self.tuView.VerticalProfileFrame.layout()
		self.figVerticalProfile, self.subplotVerticalProfile = plt.subplots()
		self.plotWidgetVerticalProfile = FigureCanvasQTAgg(self.figVerticalProfile)
		self.plotWidgetVerticalProfile.setMinimumWidth(0)
		self.figVerticalProfile.canvas.mpl_connect('button_press_event', lambda e: self.onclick(e, TuPlot.VerticalProfile))
		self.verticalProfileAnnot = self.subplotVerticalProfile.annotate("debug", xy=(15, 15), xycoords='data',
		                                                           textcoords="offset pixels",
		                                                           bbox=dict(boxstyle="round", fc="w"))
		self.verticalProfileAnnot.set_visible(False)
		self.verticalProfileHoverPoint = self.subplotVerticalProfile.scatter(0, 0, 20, 'red')
		self.verticalProfileHoverPoint.set_visible(False)
		self.figVerticalProfile.canvas.mpl_connect("motion_notify_event", lambda e: self.hover(e, TuPlot.VerticalProfile))
		
		# Initialise other variables
		# time series
		self.artistsTimeSeriesFirst = []
		self.artistsTimeSeriesSecond = []
		self.labelsTimeSeriesFirst = []
		self.labelsTimeSeriesSecond = []
		self.unitTimeSeriesFirst = []  # use list because list is mutable
		self.unitTimeSeriesSecond = []
		self.xAxisLimitsTimeSeriesFirst = []
		self.xAxisLimitsTimeSeriesSecond = []
		self.yAxisLimitsTimeSeriesFirst = []
		self.yAxisLimitsTimeSeriesSecond = []
		self.yAxisLabelTimeSeriesFirst = []
		self.yAxisLabelTimeSeriesSecond = []
		self.xAxisLabelTimeSeriesFirst = []
		self.xAxisLabelTimeSeriesSecond = []
		self.yAxisLabelTypesTimeSeriesFirst = []  # just types e.g. h. labels above are with units e.g. h (m RL)
		self.yAxisLabelTypesTimeSeriesSecond = []
		self.isTimeSeriesSecondaryAxis = [False]  # use list because a list is mutable
		self.timeSeriesPlotFirst = True  # first time series plot - so the test case can be removed
		self.holdTimeSeriesPlot = False  # holds the current time series plot if True - used when plotting multi
		self.clearedTimeSeriesPlot = True
		self.frozenTSProperties = {}  # dictionary object to save user defined names and styles
		self.frozenTSAxisLabels = {}  # dictionary object to save user defined axis labels
		
		# long plot
		self.artistsLongPlotFirst = []
		self.artistsLongPlotSecond = []
		self.labelsLongPlotFirst = []
		self.labelsLongPlotSecond = []
		self.unitLongPlotFirst = []  # use list because list is mutable
		self.unitLongPlotSecond = []
		self.xAxisLimitsLongPlotFirst = []
		self.xAxisLimitsLongPlotSecond = []
		self.yAxisLimitsLongPlotFirst = []
		self.yAxisLimitsLongPlotSecond = []
		self.yAxisLabelLongPlotFirst = []
		self.yAxisLabelLongPlotSecond = []
		self.xAxisLabelLongPlotFirst = []
		self.xAxisLabelLongPlotSecond = []
		self.yAxisLabelTypesLongPlotFirst = []  # just types e.g. h. labels above are with units e.g. h (m RL)
		self.yAxisLabelTypesLongPlotSecond = []
		self.isLongPlotSecondaryAxis = [False]
		self.profilePlotFirst = True  # first long profile plot - so the test case can be removed
		self.holdLongProfilePlot = False  # holds the current cross section plot if True
		self.clearedLongPlot = True
		self.frozenLPProperties = {}  # dictionary object to save user defined names and styles
		self.frozenLPAxisLabels = {}  # dictionary object to save user defined axis labels
		cid = self.figLongPlot.canvas.mpl_connect('draw_event', self.resize)
		cid2 = self.figLongPlot.canvas.mpl_connect('resize_event', self.resize)

		# cross section
		self.artistsCrossSectionFirst = []
		self.artistsCrossSectionSecond = []
		self.labelsCrossSectionFirst = []
		self.labelsCrossSectionSecond = []
		self.unitCrossSectionFirst = []  # use list because list is mutable
		self.unitCrossSectionSecond = []
		self.xAxisLimitsCrossSectionFirst = []
		self.xAxisLimitsCrossSectionSecond = []
		self.yAxisLimitsCrossSectionFirst = []
		self.yAxisLimitsCrossSectionSecond = []
		self.yAxisLabelCrossSectionFirst = []
		self.yAxisLabelCrossSectionSecond = []
		self.xAxisLabelCrossSectionFirst = []
		self.xAxisLabelCrossSectionSecond = []
		self.yAxisLabelTypesCrossSectionFirst = []  # just types e.g. h. labels above are with units e.g. h (m RL)
		self.yAxisLabelTypesCrossSectionSecond = []
		self.isCrossSectionSecondaryAxis = [False]
		self.crossSectionFirst = True  # first long profile plot - so the test case can be removed
		self.holdCrossSectionPlot = False  # holds the current cross section plot if True
		self.clearedCrossSectionPlot = True
		self.frozenCSProperties = {}  # dictionary object to save user defined names and styles
		self.frozenCSAxisLabels = {}  # dictionary object to save user defined axis labels

		# vertical profile
		self.artistsVerticalProfileFirst = []
		self.artistsVerticalProfileSecond = []
		self.labelsVerticalProfileFirst = []
		self.labelsVerticalProfileSecond = []
		self.unitVerticalProfileFirst = []  # use list because list is mutable
		self.unitVerticalProfileSecond = []
		self.xAxisLimitsVerticalProfileFirst = []
		self.xAxisLimitsVerticalProfileSecond = []
		self.yAxisLimitsVerticalProfileFirst = []
		self.yAxisLimitsVerticalProfileSecond = []
		self.yAxisLabelVerticalProfileFirst = []
		self.yAxisLabelVerticalProfileSecond = []
		self.xAxisLabelVerticalProfileFirst = []
		self.xAxisLabelVerticalProfileSecond = []
		self.yAxisLabelTypesVerticalProfileFirst = []  # just types e.g. h. labels above are with units e.g. h (m RL)
		self.yAxisLabelTypesVerticalProfileSecond = []
		self.isVerticalProfileSecondaryAxis = [False]
		self.verticalProfileFirst = True  # first long profile plot - so the test case can be removed
		self.holdVerticalProfilePlot = False  # holds the current cross section plot if True
		self.clearedVerticalProfilePlot = True
		self.frozenVPProperties = {}  # dictionary object to save user defined names and styles
		self.frozenVPAxisLabels = {}  # dictionary object to save user defined axis labels

		# keep track of all the data being plotted so plot can be cleared appropriately
		self.plotData = {
			TuPlot.DataTimeSeries1D: [],
			TuPlot.DataTimeSeries2D: [],
			TuPlot.DataCrossSection1D: [],
			TuPlot.DataCrossSection2D: [],
			TuPlot.DataFlow2D: [],
			TuPlot.DataUserData: [],
			TuPlot.DataCurrentTime: [],
			TuPlot.DataTimeSeriesStartLine: [],
			TuPlot.DataCrossSectionStartLine: [],
			TuPlot.DataCrossSectionStartLine1D: [],
			TuPlot.DataCurtainPlot: [],
			TuPlot.DataTimeSeriesDepAv: [],
			TuPlot.DataCrossSectionDepAv: [],
			TuPlot.DataVerticalProfileStartLine: [],
			TuPlot.DataVerticalProfile: [],
			TuPlot.DataCrossSection1DViewer: [],
			TuPlot.DataHydraulicProperty: [],
			TuPlot.DataVerticalMesh: [],
		}

		self.plotDataToPlotType = {
			TuPlot.DataTimeSeries1D: TuPlot.TimeSeries,
			TuPlot.DataTimeSeries2D: TuPlot.TimeSeries,
			TuPlot.DataCrossSection1D: TuPlot.CrossSection,
			TuPlot.DataCrossSection2D: TuPlot.CrossSection,
			TuPlot.DataFlow2D: TuPlot.TimeSeries,
			TuPlot.DataUserData: TuPlot.TimeSeries,
			TuPlot.DataCurrentTime: TuPlot.TimeSeries,
			TuPlot.DataTimeSeriesStartLine: TuPlot.TimeSeries,
			TuPlot.DataCrossSectionStartLine: TuPlot.CrossSection,
			TuPlot.DataCrossSectionStartLine1D: TuPlot.CrossSection1D,
			TuPlot.DataCurtainPlot: TuPlot.CrossSection,
			TuPlot.DataTimeSeriesDepAv: TuPlot.TimeSeries,
			TuPlot.DataCrossSectionDepAv: TuPlot.CrossSection,
			TuPlot.DataVerticalProfileStartLine: TuPlot.VerticalProfile,
			TuPlot.DataVerticalProfile: TuPlot.VerticalProfile,
			TuPlot.DataCrossSection1DViewer: TuPlot.CrossSection,
			TuPlot.DataHydraulicProperty: TuPlot.CrossSection,
			TuPlot.DataVerticalMesh: TuPlot.VerticalProfile,
		}

		self.plotDataPlottingTypes = [
			TuPlot.DataTimeSeries2D,
			TuPlot.DataCrossSection2D,
			TuPlot.DataFlow2D,
			TuPlot.DataCurtainPlot,
			TuPlot.DataTimeSeriesDepAv,
			TuPlot.DataCrossSectionDepAv,
			TuPlot.DataVerticalProfile,
		]

		self.plotDataTemporalPlottingTypes = [
			TuPlot.DataTimeSeries2D,
			TuPlot.DataFlow2D,
			TuPlot.DataTimeSeriesDepAv,
		]

		# Draw Plots
		self.initialisePlot(TuPlot.TimeSeries, TuPlot.DataTimeSeriesStartLine)  # time series
		
		self.initialisePlot(TuPlot.CrossSection, TuPlot.DataCrossSectionStartLine)  # long profile / cross section
		
		self.initialisePlot(TuPlot.CrossSection1D, TuPlot.DataCrossSectionStartLine1D)  # cross section editor

		self.initialisePlot(TuPlot.VerticalProfile, TuPlot.DataVerticalProfileStartLine)  # vertical profile
		
		# plot toolbar class
		self.tuPlotToolbar = TuPlotToolbar(self)
		
		# user selection plot class
		self.tuPlotSelection = TuPlotSelection(self)
		
		# TuPlot2D class
		self.tuPlot2D = TuPlot2D(self)
		
		# TuPlot1D class
		self.tuPlot1D = TuPlot1D(self)

		# TuPlot3D class
		self.tuPlot3D = TuPlot3D(self)

		# rubberband class plot class
		self.tuTSPoint = TuMarker(self, TuPlot.TimeSeries, TuPlot.DataTimeSeries2D,
		                          self.tuPlotToolbar.plotTSMenu, self.tuPlot2D.plotTimeSeriesFromMap,
		                          Qt.red, QgsVertexMarker.ICON_CIRCLE, True)
		self.tuCrossSection = TuRubberBand(self, TuPlot.CrossSection, TuPlot.DataCrossSection2D,
		                                   self.tuPlotToolbar.plotLPMenu, self.tuPlot2D.plotCrossSectionFromMap,
		                                   Qt.red, QgsVertexMarker.ICON_BOX, True)
		self.tuFlowLine = TuFlowLine(self, TuPlot.TimeSeries, TuPlot.DataFlow2D,
		                             self.tuPlotToolbar.plotFluxButton, self.tuPlot2D.plotFlowFromMap,
		                             Qt.blue, QgsVertexMarker.ICON_DOUBLE_TRIANGLE, False)
		self.tuCurtainLine = TuRubberBand(self, TuPlot.CrossSection, TuPlot.DataCurtainPlot,
		                                  self.tuPlotToolbar.curtainPlotMenu, self.tuPlot3D.plotCurtainFromMap,
		                                  Qt.green, QgsVertexMarker.ICON_BOX, False)
		self.tuTSPointDepAv = TuMarker(self, TuPlot.TimeSeries, TuPlot.DataTimeSeriesDepAv,
		                               self.tuPlotToolbar.averageMethodTSMenu, self.tuPlot3D.plotTimeSeriesFromMap,
		                               Qt.darkGreen, QgsVertexMarker.ICON_CIRCLE, True)
		self.tuCSLineDepAv = TuRubberBand(self, TuPlot.CrossSection, TuPlot.DataCrossSectionDepAv,
		                                   self.tuPlotToolbar.averageMethodCSMenu, self.tuPlot3D.plotCrossSectionFromMap,
		                                   Qt.darkGreen, QgsVertexMarker.ICON_BOX, True)
		self.tuVPPoint = TuMarker(self, TuPlot.VerticalProfile, TuPlot.DataVerticalProfile,
		                          self.tuPlotToolbar.plotVPMenu, self.tuPlot3D.plotVerticalProfileFromMap,
		                          Qt.magenta, QgsVertexMarker.ICON_CIRCLE, True)

		self.markers = {
			self.tuTSPoint: 'Time Series',
		    self.tuTSPointDepAv: '3D to 2D DepAv Time Series',
			self.tuVPPoint: 'Vertical Profile',
		}
		self.lines = {
			self.tuCrossSection: 'Cross Section',
			self.tuFlowLine: 'Flow Line',
			self.tuCurtainLine: 'Curtain Line',
			self.tuCSLineDepAv: '3D to 2D DepAv Cross Section',
		}

		# cursor marker - projects cursor from plot to the map canvas
		self.cursorMarker = CursorMarker(self.canvas)
		
		# User Plot Data Manager
		self.userPlotData = TuUserPlotDataManager()

		# vertical mesh
		self.verticalMesh_action = QAction('Vertical Mesh', None)
		self.verticalMesh_action.setCheckable(True)
		self.verticalMesh_action.triggered.connect(self.vmeshToggled)

		# plot colours
		self.colours = generateRandomMatplotColours2(20)

		self.cax = None  # axes object for colourbar
		self.qk = None  # artist object for vector arrow legend

		# plot data to graphic
		self.plotDataToGraphic = {
			TuPlot.DataTimeSeries1D: None,
			TuPlot.DataTimeSeries2D: self.tuTSPoint,
			TuPlot.DataCrossSection1D: None,
			TuPlot.DataCrossSection2D: self.tuCrossSection,
			TuPlot.DataFlow2D: self.tuFlowLine,
			TuPlot.DataUserData: None,
			TuPlot.DataCurrentTime: None,
			TuPlot.DataTimeSeriesStartLine: None,
			TuPlot.DataCrossSectionStartLine: None,
			TuPlot.DataCrossSectionStartLine1D: None,
			TuPlot.DataCurtainPlot: self.tuCurtainLine,
			TuPlot.DataTimeSeriesDepAv: self.tuTSPointDepAv,
			TuPlot.DataCrossSectionDepAv: self.tuCSLineDepAv,
			TuPlot.DataVerticalProfileStartLine: None,
			TuPlot.DataVerticalProfile: self.tuVPPoint,
			TuPlot.DataCrossSection1DViewer: None,
			TuPlot.DataHydraulicProperty: None,
			TuPlot.DataVerticalMesh: None,
		}

		# plot data to selection
		self.plotDataToSelection = {
			TuPlot.DataTimeSeries1D: None,
			TuPlot.DataTimeSeries2D: self.tuPlot2D.plotSelectionPointFeat,
			TuPlot.DataCrossSection1D: None,
			TuPlot.DataCrossSection2D: self.tuPlot2D.plotSelectionLineFeat,
			TuPlot.DataFlow2D: self.tuPlot2D.plotSelectionFlowFeat,
			TuPlot.DataUserData: None,
			TuPlot.DataCurrentTime: None,
			TuPlot.DataTimeSeriesStartLine: None,
			TuPlot.DataCrossSectionStartLine: None,
			TuPlot.DataCrossSectionStartLine1D: None,
			TuPlot.DataCurtainPlot: self.tuPlot3D.plotSelectionCurtainFeat,
			TuPlot.DataTimeSeriesDepAv: self.tuPlot3D.plotSelectionPointFeat,
			TuPlot.DataCrossSectionDepAv: self.tuPlot3D.plotSelectionLineFeat,
			TuPlot.DataVerticalProfileStartLine: None,
			TuPlot.DataVerticalProfile: self.tuPlot3D.plotSelectionVPFeat,
			TuPlot.DataCrossSection1DViewer: None,
			TuPlot.DataHydraulicProperty: None,
			TuPlot.DataVerticalMesh: None,
		}

	def plot2D(self):
		"""
		Get plot from 2D results from selection or from map.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if self.tuView.cboSelectType.currentText() == 'From Map' \
			or self.tuView.cboSelectType.currentText() == 'From Map Multi':
			self.tuRubberBand.startRubberBand()
		else:
			self.tuPlotSelection.useSelection()
			
		return True
		
	def plotFlow(self):
		"""
		Get flow from 2D results along line or from map.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		if self.tuView.cboSelectType.currentText() == 'From Map' \
				or self.tuView.cboSelectType.currentText() == 'From Map Multi':
			self.tuFlowLine.startRubberBand()
		else:
			self.tuPlotSelection.useSelection(rtype='flow')
		
		return True
	
	def plotEnumerator(self, plotNo):
		"""
		Returns plot variables depending on the enumerator.
		
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:return: QFrame
		:return: matplotlib Figure
		:return: matplotlib AxesSubplot
		:return: QWidget
		:return: list -> bool True when there is a secondary axis
		:return: tuple -> list -> matplotlib Line2D e.g. ( [ 1st axis lines ], [ 2nd axis lines ] )
		:return: tuple -> list -> str e.g. ( [ 1st axis labels], [ 2nd axis labels ] )
		:return: tuple -> list -> str e.g. ( [ 1st axis units], [ 2nd axis units ] )
		:return: tuple -> list -> str e.g. ( [ 1st axis y label], [ 2nd axis y label ] )
		"""
		
		plotEnumeratorDict = {
			0: [self.tuView.TimeSeriesLayout, self.figTimeSeries, self.subplotTimeSeries,
			    self.plotWidgetTimeSeries, self.isTimeSeriesSecondaryAxis,
			    (self.artistsTimeSeriesFirst, self.artistsTimeSeriesSecond),
			    (self.labelsTimeSeriesFirst, self.labelsTimeSeriesSecond),
			    (self.unitTimeSeriesFirst, self.unitTimeSeriesSecond),
			    (self.yAxisLabelTypesTimeSeriesFirst, self.yAxisLabelTypesTimeSeriesSecond),
			    (self.yAxisLabelTimeSeriesFirst, self.yAxisLabelTimeSeriesSecond),
			    (self.xAxisLabelTimeSeriesFirst, self.xAxisLabelTimeSeriesSecond),
			    (self.xAxisLimitsTimeSeriesFirst, self.xAxisLimitsTimeSeriesSecond),
			    (self.yAxisLimitsTimeSeriesFirst, self.yAxisLimitsTimeSeriesSecond)],
			1: [self.tuView.LongPlotLayout, self.figLongPlot, self.subplotLongPlot,
			    self.plotWidgetLongPlot, self.isLongPlotSecondaryAxis,
			    (self.artistsLongPlotFirst, self.artistsLongPlotSecond),
			    (self.labelsLongPlotFirst, self.labelsLongPlotSecond),
			    (self.unitLongPlotFirst, self.unitLongPlotSecond),
			    (self.yAxisLabelTypesLongPlotFirst, self.yAxisLabelTypesLongPlotSecond),
			    (self.yAxisLabelLongPlotFirst, self.yAxisLabelLongPlotSecond),
			    (self.xAxisLabelLongPlotFirst, self.xAxisLabelLongPlotSecond),
			    (self.xAxisLimitsLongPlotFirst, self.xAxisLimitsLongPlotSecond),
			    (self.yAxisLimitsLongPlotFirst, self.yAxisLimitsLongPlotSecond)],
			2: [self.tuView.CrossSectionLayout, self.figCrossSection, self.subplotCrossSection,
			    self.plotWidgetCrossSection, self.isCrossSectionSecondaryAxis,
			    (self.artistsCrossSectionFirst, self.artistsCrossSectionSecond),
			    (self.labelsCrossSectionFirst, self.labelsCrossSectionSecond),
			    (self.unitCrossSectionFirst, self.unitCrossSectionSecond),
			    (self.yAxisLabelTypesCrossSectionFirst, self.yAxisLabelTypesCrossSectionSecond),
			    (self.yAxisLabelCrossSectionFirst, self.yAxisLabelCrossSectionSecond),
			    (self.xAxisLabelCrossSectionFirst, self.xAxisLabelCrossSectionSecond),
			    (self.xAxisLimitsCrossSectionFirst, self.xAxisLimitsCrossSectionSecond),
			    (self.yAxisLimitsCrossSectionFirst, self.yAxisLimitsCrossSectionSecond)],
			3: [self.tuView.VerticalProfileLayout, self.figVerticalProfile, self.subplotVerticalProfile,
			    self.plotWidgetVerticalProfile, self.isVerticalProfileSecondaryAxis,
			    (self.artistsVerticalProfileFirst, self.artistsVerticalProfileSecond),
			    (self.labelsVerticalProfileFirst, self.labelsVerticalProfileSecond),
			    (self.unitVerticalProfileFirst, self.unitVerticalProfileSecond),
			    (self.yAxisLabelTypesVerticalProfileFirst, self.yAxisLabelTypesVerticalProfileSecond),
			    (self.yAxisLabelVerticalProfileFirst, self.yAxisLabelVerticalProfileSecond),
			    (self.xAxisLabelVerticalProfileFirst, self.xAxisLabelVerticalProfileSecond),
			    (self.xAxisLimitsVerticalProfileFirst, self.xAxisLimitsVerticalProfileSecond),
			    (self.yAxisLimitsVerticalProfileFirst, self.yAxisLimitsVerticalProfileSecond)]
		}
		
		parentLayout = plotEnumeratorDict[plotNo][0]
		figure = plotEnumeratorDict[plotNo][1]
		subplot = plotEnumeratorDict[plotNo][2]
		plotWidget = plotEnumeratorDict[plotNo][3]
		isSecondaryAxis = plotEnumeratorDict[plotNo][4]
		artists = plotEnumeratorDict[plotNo][5]  # (1st axis, 2nd axis)
		labels = plotEnumeratorDict[plotNo][6]  # (1st axis, 2nd axis)
		unit = plotEnumeratorDict[plotNo][7]  # (1st axis, 2nd axis)
		yAxisLabelTypes = plotEnumeratorDict[plotNo][8]  # (1st axis, 2nd axis)
		yAxisLabel = plotEnumeratorDict[plotNo][9]  # (1st axis, 2nd axis)
		xAxisLabel = plotEnumeratorDict[plotNo][10]  # (1st axis, 2nd axis)
		xAxisLimits = plotEnumeratorDict[plotNo][11]  # (1st axis (min, max), 2nd axis (min, max))
		yAxisLimits = plotEnumeratorDict[plotNo][12]  # (1st axis (min, max), 2nd axis (min, max))
		
		return parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, \
		       yAxisLabelTypes, yAxisLabel,  xAxisLabel, xAxisLimits, yAxisLimits
	
	def initialisePlot(self, plotNo, dataType):
		"""


		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		
		font = {'family': 'arial', 'weight': 'normal', 'size': 12}
		
		rect = figure.patch
		# rect.set_facecolor((0.9, 0.9, 0.9))
		rect.set_facecolor(self.tuView.tuOptions.plotBackgroundColour)
		subplot.set_xbound(0, 1000)
		subplot.set_ybound(0, 1000)
		self.manageMatplotlibAxe(subplot)
		sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		sizePolicy.setHorizontalStretch(0)
		sizePolicy.setVerticalStretch(0)
		plotWidget.setSizePolicy(sizePolicy)
		parentLayout.addWidget(plotWidget)
		
		# create curve
		label = "test"
		x = np.linspace(-np.pi, np.pi, 201)
		y = np.sin(x)
		a, = subplot.plot(x, y)
		self.plotData[dataType].append(a)
		artists[0].append(a)
		labels[0].append(label)
		#subplot.hold(True)
		figure.tight_layout()
		plotWidget.draw()
		
		xLimits = subplot.get_xlim()
		yLimits = subplot.get_ylim()
		
		xAxisLimits[0].append(xLimits)
		yAxisLimits[0].append(yLimits)
		
		return True
	
	def manageMatplotlibAxe(self, axe1):
		"""
		Set up Matplotlib plot object e.g. grid lines

		:param axe1: matplotlib.axis object
		:return: bool -> True for successful, False for unsuccessful
		"""

		try:
			for plotNo in [TuPlot.TimeSeries, TuPlot.CrossSection, TuPlot.CrossSection1D, TuPlot.VerticalProfile]:
				parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
					self.plotEnumerator(plotNo)
				if subplot == axe1:
					break
			toolbar, viewToolbar, mplToolbar = self.tuPlotToolbar.plotNoToToolbar[plotNo]
			if viewToolbar.hGridLines_action.isChecked() and viewToolbar.vGridLines_action.isChecked():
				axe1.grid(True, axis='both')
			elif viewToolbar.hGridLines_action.isChecked():
				axe1.grid(True, axis='y')
				axe1.grid(False, axis='x')
			elif viewToolbar.vGridLines_action.isChecked():
				axe1.grid(False, axis='y')
				axe1.grid(True, axis='x')
			else:
				axe1.grid(False, axis='both')
		except:
			axe1.grid(True, axis='both')

		#if axis is not None:
		#	axe1.grid(b, axis=axis)
		axe1.tick_params(axis="both", which="major", direction="out", length=10, width=1, bottom=True, top=False,
		                 left=True, right=False)
		axe1.minorticks_on()
		axe1.tick_params(axis="both", which="minor", direction="out", length=5, width=1, bottom=True, top=False,
		                 left=True, right=False)
		
		return True
	
	def changeLineAxis(self, clickedItem):
		"""

		"""

		for plotNo in [TuPlot.TimeSeries, TuPlot.CrossSection, TuPlot.VerticalProfile]:
			data = []
			labels = []
			types = []
			dataTypes = []
			plotAsPoints = []
			flowRegime = []
			flowRegimeTied = []
			plotAsPatch = []
			plotAsCollection = []
			plotAsQuiver = []

			bFlowRegimeTied = False
			flowRegimeY = []
			flowRegimeX = []

			pipeNames = []

			for dpt in self.plotData:
				if self.plotDataToPlotType[dpt] == plotNo:
					for line in self.plotData[dpt][:]:
						if type(line) is dict:
							artist = list(line.keys())[0]
							rtype = line[artist]
							if type(artist) is matplotlib.lines.Line2D:
								# get data
								x, y = artist.get_data()
								label = artist.get_label()

								if rtype not in types:
									normal = True
								elif re.findall(r"flow regime_\d", rtype, flags=re.IGNORECASE):
									normal = False
								else:
									normal = True

								if normal:
									if bFlowRegimeTied:
										data.append([flowRegimeX, flowRegimeY])
										bFlowRegimeTied = False
										flowRegimeX.clear()
										flowRegimeY.clear()
									labels.append(label)
									types.append(rtype)
									dataTypes.append(dpt)
									plotAsPatch.append(False)
									plotAsCollection.append(False)
									plotAsQuiver.append(False)

									if artist.get_linestyle() == 'None':
										plotAsPoints.append(True)
									else:
										plotAsPoints.append(False)

									if rtype.lower() == "flow regime_1d":
										flowRegime.append(True)
										flowRegimeTied.append(-1)
										data.append([x, y])
									elif re.findall(r"flow regime_\d", rtype, flags=re.IGNORECASE):
										f_id = re.split(r".*_\d_", rtype, flags=re.IGNORECASE)[1]
										flowRegime.append(True)
										flowRegimeTied.append(int(re.findall(r"\d", rtype)[0]))
										flowRegimeX.append(x[0])
										flowRegimeY.append(artist.get_marker().strip('$'))
									else:
										flowRegime.append(False)
										flowRegimeTied.append(-1)
										data.append([x, y])
								# elif re.findall(r"flow regime_\d", rtype, flags=re.IGNORECASE):
								else:
									bFlowRegimeTied = True
									flowRegimeX.append(x[0])
									flowRegimeY.append(artist.get_marker().strip('$'))
							elif type(artist) is Polygon or type(artist) is TuflowPipe:
								xy = artist.get_xy()
								x = xy[:, 0]
								y = xy[:, 1]
								x = [list(zip(x, y))]
								y = [x for x in range(6)]
								label = artist.get_label()

								try:
									pipeNames.append([artist.channel_id])
								except AttributeError:
									pipeNames.append([None])

								data.append([x, y])
								labels.append(label)
								types.append(rtype)
								dataTypes.append(dpt)
								plotAsPatch.append(True)
								plotAsPoints.append(False)
								flowRegime.append(False)
								plotAsCollection.append(False)
								plotAsQuiver.append(False)
								flowRegimeTied.append(-1)

							elif type(artist) is PolyCollection:
								edgecolour = ((0, 0, 0, 1),) if self.verticalMesh_action.isChecked() else 'face'
								xy = np.array([x.vertices for x in artist.get_paths()])
								pc = PolyCollection(xy, array=artist.get_array(), edgecolor=edgecolour, label=rtype,
								                    **self.tuPlot3D.colSpec)
								data.append(pc)
								labels.append(artist.get_label())
								types.append(rtype)
								dataTypes.append(dpt)
								plotAsPatch.append(True)
								plotAsPoints.append(False)
								flowRegime.append(False)
								plotAsCollection.append(True)
								plotAsQuiver.append(False)
								flowRegimeTied.append(-1)
							elif type(artist) is Quiver:
								qv = self.tuPlot3D.quiver[:]
								data.append(qv)
								labels.append(artist.get_label())
								types.append(rtype)
								dataTypes.append(dpt)
								plotAsPatch.append(True)
								plotAsPoints.append(False)
								flowRegime.append(False)
								plotAsCollection.append(False)
								plotAsQuiver.append(True)
								flowRegimeTied.append(-1)
					if bFlowRegimeTied:
						data.append([flowRegimeX, flowRegimeY])
						bFlowRegimeTied = False

			if data:
				self.clearPlot2(plotNo, clear_rubberband=False, clear_selection=False ,clear_cursor_marker=False)
				self.drawPlot(plotNo, data, labels, types, dataTypes, draw=True, plot_as_points=plotAsPoints,
				              plot_as_patch=plotAsPatch, flow_regime=flowRegime, flow_regime_tied=flowRegimeTied,
				              plot_as_collection=plotAsCollection, plot_as_quiver=plotAsQuiver, pipe_names=pipeNames)

	def clearAllPlots(self):
		"""
		Clear all plots.

		:return: bool -> True for successful, False for unsuccessful
		"""

		for i in range(TuPlot.TotalPlotNo):
			self.clearPlot2(i)

		return True

	def clearPlot2(self, plotNo, clearType = None, last_only = False, remove_no = 1, clearOnly = (), **kwargs):
		"""
		Updated clear plot method.

		Clears only lines of one type. Previous clearPlot method cleared everything and then
		replotted kept data (obviously a little inefficient)
		"""

		clearRubberband = kwargs['clear_rubberband'] if 'clear_rubberband' in kwargs else True
		clearSelection = kwargs['clear_selection'] if 'clear_selection' in kwargs else True
		clearCursorMarker = kwargs['clear_cursor_marker'] if 'clear_cursor_marker' in kwargs else True

		# get plot objects
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)

		if clearType is None:
			# disconnect rubberbands
			if plotNo == TuPlot.TimeSeries:
				if self.tuTSPoint.cursorTrackingConnected:
					self.tuTSPoint.escape(None)
				if self.tuFlowLine.cursorTrackingConnected:
					self.tuFlowLine.escape(None)
				if self.tuTSPointDepAv.cursorTrackingConnected:
					self.tuTSPointDepAv.escape(None)
			elif plotNo == TuPlot.CrossSection:
				if self.tuCrossSection.cursorTrackingConnected:
					self.tuCrossSection.escape(None)
				if self.tuCurtainLine.cursorTrackingConnected:
					self.tuCurtainLine.escape(None)
				if self.tuCSLineDepAv.cursorTrackingConnected:
					self.tuCSLineDepAv.escape(None)
				if clearCursorMarker:
					self.cursorMarker.clear()
			elif plotNo == TuPlot.VerticalProfile:
				if self.tuVPPoint.cursorTrackingConnected:
					self.tuVPPoint.escape(None)

			for dpt in self.plotData:
				if self.plotDataToPlotType[dpt] == plotNo:
					for line in self.plotData[dpt][:]:
						self.plotData[dpt].remove(line)
			self.removeColourBar(plotNo)
			self.removeQuiverKey(plotNo)
			self.clearPlot(plotNo, clear_rubberband=clearRubberband, clear_selection=clearSelection)
			return

		if isSecondaryAxis[0]:
			subplot2 = self.getSecondaryAxis(plotNo)
		else:
			subplot2 = None

		# delete lines associated with plotting type
		for i, line in enumerate(self.plotData[clearType][:]):
			if type(line) is dict:
				artist = list(line.keys())[0]
			else:
				artist = line
			for k, ax in enumerate(artists):
				for j, a in enumerate(ax):
					if a == artist:
						# label = a.get_label()
						ax.pop(j)
						if len(labels[k]) >= j + 1:
							label = labels[k].pop(j)
							if clearCursorMarker:
								if clearType == TuPlot.DataCurtainPlot:
									label = '{0}__curtain__'.format(label)
								self.cursorMarker.removeTracker(label)
			if not last_only and not clearOnly or i + 1 >= len(self.plotData[clearType]) - remove_no + 1 or line in clearOnly:
				if artist in subplot.lines:
					subplot.lines.remove(artist)
				if subplot2 is not None and artist in subplot2.lines:
					subplot2.lines.remove(artist)
				if artist in subplot.collections:
					subplot.collections.remove(artist)
				if subplot2 is not None and artist in subplot2.collections:
					subplot2.collections.remove(artist)
				if artist in subplot.patches:
					subplot.patches.remove(artist)
				if subplot2 is not None and artist in subplot2.patches:
					subplot2.patches.remove(artist)
				self.plotData[clearType].remove(line)
				if clearSelection:
					self.tuPlotSelection.clearSelection(clearType)

		# some lines that are always removed
		# showCurrentTime = clearType == TuPlot.DataCurrentTime
		showCurrentTime = clearType == TuPlot.DataCurrentTime and self.tuView.cbShowCurrentTime.isChecked()
		if plotNo == TuPlot.TimeSeries:
			for line in self.plotData[TuPlot.DataCurrentTime]:
				if type(line) is dict:
					artist = list(line.keys())[0]
				else:
					artist = line
				if artist in artists[0]:
					ind = artists[0].index(artist)
					labels[0].pop(ind)
					artists[0].pop(ind)
				if artist in artists[1]:
					ind = artists[1].index(artist)
					labels[1].pop(ind)
					artists[1].pop(ind)
				if artist in subplot.lines:
					showCurrentTime = True
					subplot.lines.remove(artist)
				del line
			for line in self.plotData[TuPlot.DataTimeSeriesStartLine]:
				if type(line) is dict:
					artist = list(line.keys())[0]
				else:
					artist = line
				if artist in artists[0]:
					ind = artists[0].index(artist)
					labels[0].pop(ind)
					artists[0].pop(ind)
				if artist in artists[1]:
					ind = artists[1].index(artist)
					labels[1].pop(ind)
					artists[1].pop(ind)
				if artist in subplot.lines:
					subplot.lines.remove(line)
				del line
		elif plotNo == TuPlot.CrossSection:
			for line in self.plotData[TuPlot.DataCrossSectionStartLine]:
				if type(line) is dict:
					artist = list(line.keys())[0]
				else:
					artist = line
				if artist in artists[0]:
					ind = artists[0].index(artist)
					labels[0].pop(ind)
					artists[0].pop(ind)
				if artist in artists[1]:
					ind = artists[0].index(artist)
					labels[1].pop(ind)
					artists[1].pop(ind)
				if artist in subplot.lines:
					subplot.lines.remove(line)
				del line
		elif plotNo == TuPlot.CrossSection1D:
			for line in self.plotData[TuPlot.DataCrossSectionStartLine1D]:
				if type(line) is dict:
					artist = list(line.keys())[0]
				else:
					artist = line
				if artist in artists[0]:
					ind = artists[0].index(artist)
					labels[0].pop(ind)
					artists[0].pop(ind)
				if artist in artists[1]:
					ind = artists[0].index(artist)
					labels[1].pop(ind)
					artists[1].pop(ind)
				if artist in subplot.lines:
					subplot.lines.remove(line)
				del line
		elif plotNo == TuPlot.VerticalProfile:
			for line in self.plotData[TuPlot.DataVerticalMesh][:]:
				if type(line) is dict:
					artist = list(line.keys())[0]
				else:
					artist = line
				if artist in artists[0]:
					ind = artists[0].index(artist)
					labels[0].pop(ind)
					artists[0].pop(ind)
				if artist in artists[1]:
					ind = artists[0].index(artist)
					labels[1].pop(ind)
					artists[1].pop(ind)
				if artist in subplot.lines:
					subplot.lines.remove(line)
				del line
			for line in self.plotData[TuPlot.DataVerticalProfileStartLine]:
				if type(line) is dict:
					artist = list(line.keys())[0]
				else:
					artist = line
				if artist in artists[0]:
					ind = artists[0].index(artist)
					labels[0].pop(ind)
					artists[0].pop(ind)
				if artist in artists[1]:
					ind = artists[0].index(artist)
					labels[1].pop(ind)
					artists[1].pop(ind)
				if artist in subplot.lines:
					subplot.lines.remove(line)
				del line

		self.removeColourBar(plotNo)
		self.removeQuiverKey(plotNo)

		# self.drawPlot(plotNo, [], [], [], [], refreshOnly=True, draw=True, showCurrentTime=showCurrentTime)
		if clearType == TuPlot.DataCurrentTime and not showCurrentTime:
			plotWidget.draw()
		else:
			self.drawPlot(plotNo, [], [], [], [], draw=True, show_current_time=showCurrentTime)

	def addColourBarAxes(self, plotNo, **kwargs):

		# get plot objects
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)

		if 'respec' in kwargs:
			gs, rsi, rei, csi, cei = kwargs['respec']
			gs_pos = gs[rsi:rei, 89:94]
			pos = gs_pos.get_position(figure)
			self.cax.set_position(pos)
			self.cax.set_subplotspec(gs_pos)
		else:
			self.removeColourBar(plotNo)
			self.cax = 1  # dummy value
			gs, rsi, rei, csi, cei = self.reSpecPlot(plotNo)
			self.cax = figure.add_subplot(gs[rsi:rei, 89:94])
		# gs = gridspec.GridSpec(100, 100)
		# figure.subplotpars.bottom = 0  # 0.206
		# figure.subplotpars.top = 1  # 0.9424
		# figure.subplotpars.left = 0  # 0.085
		# figure.subplotpars.right = 1  # 0.98

		# rsi = 6
		# rei = int(100 - (subplot.xaxis.get_tightbbox(figure.canvas.get_renderer()).height +
		#                  subplot.xaxis.get_label().get_size() + subplot.xaxis.get_ticklabels()[0].get_size() +
		#                  subplot.xaxis.get_tick_padding() + 20)  / figure.bbox.height * 100)
		# csi = int((subplot.yaxis.get_tightbbox(figure.canvas.get_renderer()).width +
		#            subplot.yaxis.get_label().get_size() + subplot.yaxis.get_ticklabels()[0].get_size() +
		#            subplot.yaxis.get_tick_padding() + 20) / figure.bbox.width * 100)

		# if isSecondaryAxis[0]:
		# 	cei = 81
		# 	# gs_pos = gs[6:79,9:81]
		# 	subplot2 = self.getSecondaryAxis(plotNo)
		# else:
		# 	# gs_pos = gs[6:79, 9:86]
		# 	cei = 86
		# 	subplot2 = None

		# gs_pos = gs[rsi:rei, csi:cei]
		# pos = gs_pos.get_position(figure)
		# subplot.set_position(pos)
		# subplot.set_subplotspec(gs_pos)

		# if subplot2 is not None:
		# 	subplot2.set_position(pos)
		# 	subplot2.set_subplotspec(gs_pos)


	def removeColourBar(self, plotNo):

		# get plot objects
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)

		# delete colour bar axis
		if self.cax is not None:
			if self.cax in figure.axes:
				self.cax.remove()
			self.cax = None

		# force find and remove and axes object that isn't meant to be there (happens if cax bugs out and remains)
		if self.cax is None:
			if isSecondaryAxis[0]:
				subplot2 = self.getSecondaryAxis(plotNo)
			else:
				subplot2 = None
			for ax in figure.axes:
				if ax != subplot and ax != subplot2:
					ax.remove()

		gs = gridspec.GridSpec(1, 1)
		subplot.set_position(gs[0, 0].get_position(figure))
		subplot.set_subplotspec(gs[0, 0])
		if isSecondaryAxis[0]:
			subplot2 = self.getSecondaryAxis(plotNo)
			subplot2.set_position(gs[0, 0].get_position(figure))
			subplot2.set_subplotspec(gs[0, 0])

	def addQuiverLegend(self, plotNo, line, label):
		"""

		"""

		# get plot objects
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)

		self.removeQuiverKey(plotNo)
		self.qk = 1  # dummy value
		gs, rsi, rei, csi, cei = self.reSpecPlot(plotNo)

		# self.qk = subplot.quiverkey(line, X=cei+0.1, Y=(1-rsi+0.05), U=1, label=label, labelpos='W', coordinates='figure')
		if self.cax is not None:
			X = 0.95
			Y = 1 - (rsi+4)/100 + 0.05
		else:
			X = 0.95
			Y = 0.05
		self.qk = subplot.quiverkey(line, X=X, Y=Y, U=self.quiver_U, label=label, labelpos='W', coordinates='figure')
		if self.cax is not None:
			self.addColourBarAxes(plotNo, respec=(gs, rsi+4, rei, csi, cei))

	def removeQuiverKey(self, plotNo):

		# get plot objects
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)

		if self.qk is not None:
			for ax in figure.axes:
				if self.qk in ax.artists:
					ax.artists.remove(self.qk)
			self.qk = None

	def reSpecPlot(self, plotNo):
		"""

		"""

		# get plot objects
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		if isSecondaryAxis[0]:
			subplot2 = self.getSecondaryAxis(plotNo)
		else:
			subplot2 = None

		toolbar, viewToolbar, mplToolbar = self.tuPlotToolbar.plotNoToToolbar[plotNo]

		# if self.cax is None and self.qk is None:
		# 	gs = gridspec.GridSpec(1, 1)
		# 	rsi, rei, csi, cei = 0, 1, 0, 1
		# else:
		gs = gridspec.GridSpec(100, 100)
		figure.subplotpars.bottom = 0  # 0.206
		figure.subplotpars.top = 1  # 0.9424
		figure.subplotpars.left = 0  # 0.085
		figure.subplotpars.right = 1  # 0.98
		padding = 20
		xlabelsize = 7 if subplot.get_xlabel() else subplot.xaxis.get_label().get_size() + subplot.xaxis.get_ticklabels()[0].get_size() + \
		                 subplot.xaxis.get_tick_padding()
		ylabelsize = 7 if subplot.get_ylabel() else subplot.yaxis.get_label().get_size() + subplot.yaxis.get_ticklabels()[0].get_size() + \
		           subplot.yaxis.get_tick_padding()
		rei = int(100 - (subplot.xaxis.get_tightbbox(figure.canvas.get_renderer()).height +
		                 xlabelsize +
		                 padding) / figure.bbox.height * 100)

		csi = int((subplot.yaxis.get_tightbbox(figure.canvas.get_renderer()).width +
		           ylabelsize +
		           padding) / figure.bbox.width * 100)
		if subplot2 is not None and plotNo == TuPlot.VerticalProfile:
			# x2labelsize = 10 if not subplot2.get_xlabel() else subplot2.xaxis.get_label().get_size() + \
			#                                               subplot2.xaxis.get_ticklabels()[0].get_size() + \
			#                                               subplot2.xaxis.get_tick_padding()
			try:
				x2labelsize = subplot2.xaxis.get_label().get_size() + \
	                          subplot2.xaxis.get_ticklabels()[0].get_size() + \
	                          subplot2.xaxis.get_tick_padding()
			except:
				x2labelsize = 23
			rsi = int((subplot2.xaxis.get_tightbbox(figure.canvas.get_renderer()).height + x2labelsize + padding) / figure.bbox.height * 100)
		else:
			rsi = 3
		if self.cax is not None:
			if subplot2 is not None:
				cei = 81
			else:
				cei = 86
		else:
			if subplot2 is not None and plotNo != TuPlot.VerticalProfile:
				y2labelsize = 7 if subplot2.get_ylabel() else subplot2.yaxis.get_label().get_size() + \
				                 subplot2.yaxis.get_ticklabels()[0].get_size() + \
				                 subplot2.yaxis.get_tick_padding()
				cei = int(100 - (subplot2.yaxis.get_tightbbox(figure.canvas.get_renderer()).width +
				                 y2labelsize +
				                 padding) / figure.bbox.width * 100)
			else:
				cei = 97

		# if user puts legend outside of plot, manually deal with placement otherwise margins can get really big for some reason
		if subplot.legend_ is not None:
			if viewToolbar.legendCustomPos.isChecked():
				xpos, ypos = viewToolbar.legendCustomPos.values()
				if subplot.legend_.get_window_extent().y1 > subplot.bbox.y1 and subplot.legend_.get_window_extent().height < figure.bbox.height:
					# target = rei - rsi
					target = rei - 3
					height = rei - rsi
					gap = int(height * (ypos - 1.)) + int(subplot.legend_.get_window_extent().height / figure.bbox.height * 100)
					while height + gap > target and height > 1:
						height -= 1
						gap = int(height * (ypos - 1.)) + int(subplot.legend_.get_window_extent().height / figure.bbox.height * 100)
					rsi = rei - height
					if rsi >= rei:
						rsi = rei - 1
				if ypos < 0:
					height = rei - rsi
					gap = height * abs(ypos)
					target = 100 - rsi - 3
					while height + gap > target and height > 1:
						height -= 1
						gap = height * abs(ypos)
					rei = height + rsi
					if rei <= rsi:
						rei = rsi + 1
				if subplot.legend_.get_window_extent().x1 > subplot.bbox.x1 and subplot.legend_.get_window_extent().width < figure.bbox.width:
					target = 100 - csi - 2
					width = cei - csi
					gap = int(width * (xpos - 1.)) + int(subplot.legend_.get_window_extent().width / figure.bbox.width * 100)
					while width + gap > target and width > 1:
						width -= 1
						gap = int(width * (xpos - 1.)) + int(subplot.legend_.get_window_extent().width / figure.bbox.width * 100)
					cei = width + csi
					if cei <= csi:
						cei = csi + 1
				if xpos < 0:
					width = cei - csi
					gap = width * abs(xpos)
					target = cei - 1
					while width + gap > target and width > 1:
						width -= 1
						gap = width * abs(xpos)
					csi = cei - width
					if csi > cei:
						csi = cei - 1

		gs_pos = gs[rsi:rei, csi:cei]
		pos = gs_pos.get_position(figure)
		subplot.set_position(pos)
		subplot.set_subplotspec(gs_pos)

		if subplot2 is not None:
			subplot2.set_position(pos)
			subplot2.set_subplotspec(gs_pos)

		return gs, rsi, rei, csi, cei
	
	def clearPlot(self, plotNo, **kwargs):
		"""
		Clears and resets the plotting window

		:param plotNo: int enumerator
						0: time series plot
						1: long profile plot
						2: cross section plot
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		
		# get axis limits
		xLimits = subplot.get_xlim()
		yLimits = subplot.get_ylim()
		if isSecondaryAxis[0]:
			subplot2 = self.getSecondaryAxis(plotNo)
			yLimits2 = subplot2.get_ylim()
			
		# get axis labels
		xLabel = subplot.get_xlabel()
		yLabel = subplot.get_ylabel()
		if isSecondaryAxis[0]:
			yLabel2 = subplot2.get_ylabel()
			
		# get legend labels and artists
		flowKeptXAll = []  # if retaining flow results- this is because extracting flow takes time unlike point TS
		flowKeptYAll = []
		flowKeptLabels = []
		#lab, lab2, line, line2 = [], [], [], []
		line, lab = subplot.get_legend_handles_labels()
		#if labels[0] and not lab:
		#	lab = labels[0][:]
		#	line = artists[0][:]
		for i, l in enumerate(lab):
			if '2d map flow' in l.lower():
				x, y = line[i].get_data()
				flowKeptXAll.append(x)
				flowKeptYAll.append(y)
				flowKeptLabels.append(l)
		if isSecondaryAxis[0]:
			line2, lab2 = subplot2.get_legend_handles_labels()
			if labels[1] and not lab2:
				lab2 = labels[1][:]
				line2 = artists[1][:]
			for i, l in enumerate(lab2):
				if '2d map flow' in l.lower():
					x, y = line2[i].get_data()
					flowKeptXAll.append(x)
					flowKeptYAll.append(y)
					flowKeptLabels.append(l)
		#if not self.tuView.tuMenuBar.freezeLegendLabels_action.isChecked():
		#	lab, lab2, line, line2 = [], [], [], []
		#labs = [lab, lab2]
		#lines = [line, line2]
		retainFlow = kwargs['retain_flow'] if 'retain_flow' in kwargs.keys() else False
		if not retainFlow:  # reset back to zero if not retaining
			flowKeptXAll = []
			flowKeptYAll = []
			flowKeptLabels = []
		
		# reset units
		for u in unit:
			u.clear()
		for label in yAxisLabelTypes:
			label.clear()
		
		# reset multi line plotting
		if plotNo == TuPlot.TimeSeries:
			self.clearedTimeSeriesPlot = True
			self.tuPlot2D.resetMultiPointCount()
			self.tuPlot2D.resetMultiFlowLineCount()
		elif plotNo == TuPlot.CrossSection:
			self.clearedLongPlot = True
			self.tuPlot2D.resetMultiLineCount()
		elif plotNo == TuPlot.CrossSection1D:
			self.clearedCrossSectionPlot = True
		elif plotNo == TuPlot.VerticalProfile:
			self.clearedVerticalProfilePlot = True
		
		# reset plot - but keep flow results if "retain_flow=True"
		for i, label in enumerate(labels):
			label.clear()
		for i, artist in enumerate(artists):
			artist.clear()
		for label in yAxisLabels:
			label.clear()
		for label in xAxisLabels:
			label.clear()
		for limit in xAxisLimits:
			limit.clear()
		for limit in yAxisLimits:
			limit.clear()
		subplot.cla()
		#fmt = matplotlib.ticker.ScalarFormatter()
		#subplot.xaxis.set_major_formatter(fmt)
		if isSecondaryAxis[0]:
			subplot2 = self.getSecondaryAxis(plotNo)
			if subplot2 is not None:
				subplot2.cla()
			if not self.tuView.tuResults.secondaryAxisTypes:
				figure.delaxes(subplot2)
				isSecondaryAxis[0] = False
		self.manageMatplotlibAxe(subplot)
		if self.tuView.tuMenuBar.freezeAxisXLimits_action.isChecked():
			subplot.set_xbound(xLimits)
		if self.tuView.tuMenuBar.freezeAxisYLimits_action.isChecked():
			subplot.set_ybound(yLimits)
			if isSecondaryAxis[0]:
				subplot2.set_ybound(yLimits2)
		if self.tuView.tuMenuBar.freezeAxisLabels_action.isChecked():
			subplot.set_xlabel(xLabel)
			subplot.set_ylabel(yLabel)
			if isSecondaryAxis[0]:
				subplot2.set_ylabel(yLabel2)
		figure.tight_layout()
		plotWidget.draw()
		
		# Clear markers and rubber bands as well - only really used through view >> clear plot and view >> clear graphics
		if 'clear_rubberband' in kwargs.keys():
			if kwargs['clear_rubberband']:
				for dataType in self.plotDataPlottingTypes:
					if self.plotDataToPlotType[dataType] == plotNo:
						self.plotDataToGraphic[dataType].clearGraphics()
				if plotNo == TuPlot.CrossSection:
					self.tuPlot3D.curtainGeom.clear()

		if 'clear_selection' in kwargs.keys():
			if kwargs['clear_selection']:
				for dataType in self.plotDataPlottingTypes:
					if self.plotDataToPlotType[dataType] == plotNo:
						self.plotDataToSelection[dataType].clear()

			#if plotNo == TuPlot.CrossSection:
			#	self.tuView.crossSections1D.clear()

		# Retain 1D results
		retain1d = kwargs['retain_1d'] if 'retain_1d' in kwargs.keys() else False
		if retain1d:
			if plotNo == 0:
				self.updateTimeSeriesPlot(plot='1D Only')
			elif plotNo == 1:
				self.updateCrossSectionPlot(plot='1D Only')
		
		# Retain 2D results
		retain2d = kwargs['retain_2d'] if 'retain_2d' in kwargs.keys() else False
		if retain2d:
			if plotNo == 0:
				self.updateTimeSeriesPlot(plot='2D Only')
			elif plotNo == 1:
				self.updateCrossSectionPlot(plot='2D Only')
				
		# Retain flow results
		retainFlow = kwargs['retain_flow'] if 'retain_flow' in kwargs.keys() else False
		if retainFlow:
			if plotNo == 0:
				# little different method because flow extraction takes a lot longer than normal TS extraction
				data = list(zip(flowKeptXAll, flowKeptYAll))
				flowKeptTypes = ['2D Flow'] * len(flowKeptLabels)
				if data:
					self.drawPlot(0, data, flowKeptLabels, flowKeptTypes)
				
		# record axis limits
		xLimits = subplot.get_xlim()
		yLimits = subplot.get_ylim()
		xAxisLimits[0].clear()
		xAxisLimits[0].append(xLimits)
		yAxisLimits[0].clear()
		yAxisLimits[0].append(yLimits)
		if isSecondaryAxis[0]:
			subplot2 = self.getSecondaryAxis(plotNo)
			yLimits2 = subplot2.get_ylim()
			yAxisLimits[1].append(yLimits2)
				
		return True
	
	def clearPlotLastDatasetOnly(self, plotNo):
		"""
		

		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:return: bool -> True for successful, False for unsuccessful
		"""

		activeMeshLayers = self.tuView.tuResults.tuResults2D.activeMeshLayers
		secondaryAxisTypes = self.tuView.tuResults.secondaryAxisTypes
		
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		
		# get axis limits
		xLimits = subplot.get_xlim()
		yLimits = subplot.get_ylim()
		if isSecondaryAxis[0]:
			subplot2 = self.getSecondaryAxis(plotNo)
			yLimits2 = subplot2.get_ylim()
		
		# remove last point entry if any entry exists
		if artists[0] or artists[1]:
			
			# do so for every selected result
			for j in range(len(activeMeshLayers)):
				
				# do so for every result rtype
				for i, rtype in enumerate(self.tuPlotToolbar.getCheckedItemsFromPlotOptions(plotNo)):
					
					if rtype not in secondaryAxisTypes:
						
						# first axis
						if labels[0]:
							if '2d map flow' not in labels[0][-1].lower() and 'user plot data' not in labels[0][-1].lower():
								if labels[0][-1] != 'Current Time':
									artists[0].pop()
									labels[0].pop()
									del subplot.lines[-1]
								else:
									artists[0].pop(-2)
									labels[0].pop(-2)
									del subplot.lines[-2]
					
					else:
						
						# secondary axis
						if isSecondaryAxis[0]:
							subplot2 = self.getSecondaryAxis(plotNo)
							if labels[1]:
								if '2d map flow' not in labels[1][-1].lower():
									artists[1].pop()
									labels[1].pop()
									del subplot2.lines[-1]
			
			# reimplement legend
			subplot.legend_ = None
			self.updateLegend(plotNo)
		
		subplot.relim()
		subplot.autoscale()
		if self.tuView.tuMenuBar.freezeAxisXLimits_action.isChecked():
			subplot.set_xbound(xLimits)
		if self.tuView.tuMenuBar.freezeAxisYLimits_action.isChecked():
			subplot.set_ybound(yLimits)
			if isSecondaryAxis[0]:
				subplot2.set_ybound(yLimits2)

		figure.tight_layout()
		plotWidget.draw()
		
		# record axis limits
		xLimits = subplot.get_xlim()
		yLimits = subplot.get_ylim()
		xAxisLimits[0].clear()
		xAxisLimits[0].append(xLimits)
		yAxisLimits[0].clear()
		yAxisLimits[0].append(yLimits)
		if isSecondaryAxis[0]:
			subplot2 = self.getSecondaryAxis(plotNo)
			yLimits2 = subplot2.get_ylim()
			yAxisLimits[1].append(yLimits2)
		
		return True
	
	def showCurrentTime(self, plotNo, **kwargs):
		"""
		Manages the red time slider.

		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:return: bool -> True for successful, False for unsuccessful
		"""

		qv = Qgis.QGIS_VERSION_INT

		# deal with kwargs
		time = kwargs['time'] if 'time' in kwargs.keys() else None
		showCurrentTime = kwargs['show_current_time'] if 'show_current_time' in kwargs.keys() else False

		# only show for time series plot
		if plotNo != 0:
			return
		
		# get plot from enumerator
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		
		# get axis limits
		xLimits = subplot.get_xlim()
		yLimits = subplot.get_ylim()
		if isSecondaryAxis[0]:
			subplot2 = self.getSecondaryAxis(plotNo)
			yLimits2 = subplot2.get_ylim()
		
		# check to see if current time already exists
		# i = True
		# while i is not None:
		# 	i = labels[0].index('Current Time') if 'Current Time' in labels[0] else None  # index for individual lists
		# 	lab = labels[0] + labels[1]
		# 	j = lab.index('Current Time') if 'Current Time' in lab else None  # index in all lines on figure
		# 	if i or i == 0:
		# 		artists[0].pop(i)
		# 		labels[0].pop(i)
		# 		del subplot.lines[j]
		# 		subplot.legend_ = None
		if self.plotData[TuPlot.DataCurrentTime]:
			for line in subplot.lines:
				if line._label.lower() == 'current time':
					subplot.lines.remove(line)
			if self.plotData[TuPlot.DataCurrentTime]:
				del self.plotData[TuPlot.DataCurrentTime][0]
			for lab in labels[0][:]:
				if lab.lower() == 'current time':
					labels[0].remove(lab)
			for line in artists[0][:]:
				if line._label.lower() == 'current time':
					artists[0].remove(line)
			#if self.plotData[TuPlot.DataCurrentTime][0] in subplot.lines:
			#	subplot.lines.remove(self.plotData[TuPlot.DataCurrentTime][0])
			#	del self.plotData[TuPlot.DataCurrentTime][0]
			#else:
			#	del self.plotData[TuPlot.DataCurrentTime][0]

		
		if self.tuView.cbShowCurrentTime.isChecked() or showCurrentTime:

			# get current Time
			if qv < 31600:
				if time is not None:  # use input time not current time
					x = [time] * 2
				else:
					try:
						x = [float(self.tuView.tuResults.activeTime)] * 2
					except TypeError:  # probably no times available
						return False

				# check time units
				if self.tuView.tuOptions.timeUnits == 's':
					if x:
						for i in range(len(x)):
							x[i] = x[i] / 60. / 60.

				# convert to date if needed
				if self.tuView.tuOptions.xAxisDates:
					x = self.convertTimeToDate(x)
			else:
				if time is None:
					time = self.tuView.tuResults.activeTime
				if not self.tuView.tuOptions.xAxisDates:
					time, ind = self.tuView.tuResults.dateToTimeInCombobox(time)
					# rt = self.tuView.tuOptions.zeroTime
					# for i in range(self.tuView.cboTime.count()):  # find closest
					# 	item = self.tuView.cboTime.itemText(i)
					# 	timeKey = convertFormattedTimeToTime(item)
					# 	t = self.tuView.tuResults.timekey2time[timeKey] if timeKey in self.tuView.tuResults.timekey2time else float(timeKey)
					# 	if self.tuView.tuOptions.timeUnits == 's':
					# 		date = rt + timedelta(seconds=t)
					# 	else:
					# 		try:
					# 			date = rt + timedelta(hours=t)
					# 		except OverflowError:
					# 			date = rt + timedelta(seconds=t)
					# 	if date == time:
					# 		time = t
					# 		break
					# 	if i == 0:
					# 		diff = abs((date - time).total_seconds())
					# 	if date > time:
					# 		diff2 = abs((date - time).total_seconds())
					# 		if diff <= diff2:
					# 			item = self.tuView.cboTime.itemText(max(0, i-1))
					# 			timeKey = convertFormattedTimeToTime(item)
					# 			time = self.tuView.tuResults.timekey2time[timeKey] if timeKey in self.tuView.tuResults.timekey2time else float(timeKey)
					# 			break
					# 		else:
					# 			time = t
					# 			break
					# 	else:
					# 		diff = abs((date - time).total_seconds())

				x = [time, time]
			
			# get current Y-Axis limits
			if not self.tuView.tuMenuBar.freezeAxisYLimits_action.isChecked():
				ylim = subplot.get_ylim()
				xlim = subplot.get_xlim()
				subplot.relim()
				subplot.autoscale()
				y = subplot.get_ylim()
			else:
				y = yAxisLimits[0][0]

			# add to plot
			label, artistTemplates = self.getNewPlotProperties(plotNo, ['Current Time'], None, rtype='lines')
			a, = subplot.plot(x, y, color='red', linewidth=2, label=label[0])
			self.plotData[TuPlot.DataCurrentTime].append({a: 'Current Time'})
			applyMatplotLibArtist(a, artistTemplates[0])
			artists[0].append(a)
			labels[0].append('Current Time')
			if self.tuView.tuMenuBar.freezeAxisXLimits_action.isChecked():
				subplot.set_xbound(xAxisLimits[0][0])
			if self.tuView.tuMenuBar.freezeAxisYLimits_action.isChecked():
				subplot.set_ybound(yAxisLimits[0][0])
			else:
				# subplot.set_ybound(y)
				subplot.set_ybound(ylim)
				subplot.set_xbound(xlim)
			subplot.legend_ = None
			
		return True

	def showVertMesh(self, plotNo, data, label, plotVertMesh):
		"""Shows vertical mesh/levels on vertical profile plot"""

		if plotNo != TuPlot.VerticalProfile:
			return

		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)

		# get axis limits
		xLimits = subplot.get_xlim()
		yLimits = subplot.get_ylim()
		if isSecondaryAxis[0]:
			subplot2 = self.getSecondaryAxis(plotNo)
			xLimits2 = subplot2.get_xlim()

		# del any existing vertical mesh
		if self.plotData[TuPlot.DataVerticalMesh]:
			for line in self.plotData[TuPlot.DataVerticalMesh][:]:
				if line in subplot.lines:
					subplot.lines.remove(line)
					self.plotData[TuPlot.DataVerticalMesh].remove(line)
				else:
					self.plotData[TuPlot.DataVerticalMesh].remove(line)

		if self.verticalMesh_action.isChecked():
			vmydata = [data[i][1] for i, x in enumerate(plotVertMesh) if x]
			vmlabels = [label[i] for i, x in enumerate(plotVertMesh) if x]

			# get x axis limits
			if not self.tuView.tuMenuBar.freezeAxisXLimits_action.isChecked():
				subplot.relim()
				subplot.autoscale()
				xlim = subplot.get_xlim()
			else:
				xlim = xAxisLimits[0][0]
			vmdata = []
			for vm in vmydata:
				x, y = [], []
				for vlayer in vm:
					x.extend(xlim)
					x.append(-99999.)
					y.extend([vlayer, vlayer, -99999.])
				x = ma.array(x)
				y = ma.array(y)
				x = ma.masked_where(x == -99999., x)
				y = ma.masked_where(y == -99999., y)
				vmdata.append((x, y))

			# add to plot
			label, artistTemplates = self.getNewPlotProperties(plotNo, vmlabels, None, rtype='lines')
			for i, d in enumerate(vmdata):
				x = d[0]
				y = d[1]
				lab = label[i]
				a, = subplot.plot(x, y, color='black', linewidth=1.2, linestyle='--', label=lab, zorder=2)
				applyMatplotLibArtist(a, artistTemplates[i])
				self.plotData[TuPlot.DataVerticalMesh].append({a: 'Vertical Mesh'})
				artists[0].append(a)
				labels[0].append(lab)
			if self.tuView.tuMenuBar.freezeAxisXLimits_action.isChecked():
				subplot.set_xbound(xAxisLimits[0][0])
			if self.tuView.tuMenuBar.freezeAxisYLimits_action.isChecked():
				subplot.set_ybound(yAxisLimits[0][0])
			else:
				subplot.set_xbound(xlim)
			subplot.legend_ = None

			# bring non-mesh lines to front
			z = 10
			for line in self.plotData[TuPlot.DataVerticalProfile][:]:
				if type(line) is dict:
					artist = list(line.keys())[0]
				else:
					artist = line
				artist.zorder = z
				z += 5
	
	def showStatResult(self, plotNo, statType):
		"""
		Show the median time series result
		
		:param statType: str
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if plotNo != 0:
			return False


		# get plot from enumerator
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		
		if (statType == 'Median' and not self.tuView.tuMenuBar.showMedianEvent_action.isChecked()) or (statType == 'Mean' and not self.tuView.tuMenuBar.showMeanEvent_action.isChecked()):
			# check to see if current time already exists
			for i, label in enumerate(labels[0][:]):
				if statType in label:
					artists[0].pop(i)
					labels[0].pop(i)
					del subplot.lines[i]
					self.updateLegend(plotNo)
					plotWidget.draw()
			return True
		
		# get list of max values from all time series
		maxes = []
		for i, artist in enumerate(artists[0]):
			if 'Median' not in labels[0][i] and 'Mean' not in labels[0][i]:
				x, y = artist.get_data()
				maxes.append(np.nanmax(y))
		maxesOrdered = sorted(maxes)
		
		if len(maxes) < 3:
			return False
		
		# get stat rtype from maxes
		if statType == 'Median':
			if len(maxes) % 2 == 0:
				n = int(len(maxes) / 2)  # +1 but this is taken into consideration because python starts at zero
				n = maxes.index(maxesOrdered[n])
			else:
				n = int((len(maxes) - 1) / 2)  # -1 because python starts at zero
				n = maxes.index(maxesOrdered[n])
		elif statType == 'Mean':
			mean, n = getMean(maxes, event_selection=self.tuView.tuOptions.meanEventSelection)
		else:
			n = None
			
		# add to plot
		if n is not None:
			x, y = artists[0][n].get_data()
			label = '{0}: {1}'.format(statType, labels[0][n])
			colour = 'black' if statType == 'Median' else 'Blue'
			a, = subplot.plot(x, y, color=colour, linestyle=':', linewidth=3, label=label)
			artists[0].append(a)
			labels[0].append(label)
			self.updateLegend(plotNo)
			plotWidget.draw()
			
		return True

	def setAxisNames(self, plotNo, types, plotAsCollection=(), plotAsQuiver=(), return_unit_only=False, unit_system=None):
		"""
		Manages the axis labels including units and secondary axis.

		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:param types: list -> str of result types
		:return: str -> x axis label
		:return: str -> y axis 1 label
		:return: str -> y axis 2 label
		"""

		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		
		# Units  (SI, Imperial, ..place holders.. , blank)
		# can use regular expressions
		units = {
			r'Time of Peak.*': ('hrs', 'hrs', ''),
			r'.*elevation.*': ('m RL', 'ft RL', ''),
			r'level': ('m RL', 'ft RL', ''),
			r'obvert': ('m RL', 'ft RL', ''),
			r'us levels': ('m RL', 'ft RL', ''),
			r'(bed elevation)$': ('m RL', 'ft RL', ''),
			r'flow': ('m$^3$/s', 'ft$^3$/s', ''),
			r'2d flow': ('m$^3$/s', 'ft$^3$/s', ''),
			r'atmospheric pressure': ('hPA', 'hPa', ''),
			r'bed shear stress': ('N/m$^2$', 'lbf/ft$^2$', 'pdl/ft%^2$', ''),
			r'depth': ('m', 'ft', ''),
			r'([^a-z]|^)vel': ('m/s', 'ft/s', ''),
			r'cumulative infiltration': ('mm', 'inches', ''),
			r'depth to groundwater': ('m', 'ft', ''),
			r'infiltration rate': ('mm/hr', 'in/hr', ''),
			r'mb\d*': ('%', '%', ''),
			r'unit flow': ('m$^2$/s', 'ft$^2$/s', ''),
			r'z0': ('m$^2$/s', 'ft$^2$/s', ''),
			r'cumulative rainfall': ('mm', 'inches', ''),
			r'rfml': ('mm', 'inches', ''),
			r'rainfall rate': ('mm/hr', 'in/hr', ''),
			r'stream power': ('W/m$^2$', 'lbf/ft$^2$', 'pdl/ft$^2$', ''),
			r'sink': ('m$^3$/s', 'ft$^3$/s', ''),
			r'source': ('m$^3$/s', 'ft$^3$/s', ''),
			r'flow regime': ('', '', ''),
			r'flow area': ('m$^2$', 'ft$^2$', ''),
			r'time of max h': ('hrs', 'hrs', ''),
			r'([^a-z]|^)sal': ('ppt', 'ppt', ''),
			r'([^a-z]|^)sal.*flux': ('ppt m$^3$/s', 'ppt ft$^3$/s', ''),
			r'([^a-z]|^)temp': ('$^o$C', 'N/A', ''),
			r'([^a-z]|^)temp.*flux': ('$^o$C m$^3$/s', 'N/A', ''),
			r'bed elevation change': ('m', 'ft', ''),
			r'downward .* wave radiaton flux': ('W/m$^2$', 'N/A', ''),
			r'evaporation rate': ('m/day', 'N/A', ''),
			r'mean sea level pressure': ('hPA', 'hPa', ''),
			r'particle group \d* concentration': ('mg/L', 'N/A', ''),
			r'particle group \d* bed concentration': ('g/m$^2$', 'N/A', ''),
			r'precipitation rate': ('mm/hr', 'in/hr', ''),
			r'relative humidity': ('%', '%', ''),
			r'significant wave height': ('m', 'ft', ''),
			r'surface shear stress': ('N/m$^2$', 'lbf/ft$^2$', 'pdl/ft$^2$', ''),
			r'tracer \d*': ('units/m$^3$', 'units/ft$^3$', ''),
			r'trace[\s_]\d*[\s_]flux': ('units m$^3$/s', 'units ft$^3$/s', ''),
			r'sediment fraction \d*': ('mg/L', 'lb/gal', ''),
			r'sed[\s_]\d*[\s_]flux': ('10^-3 kg/s', 'lb/s', ''),
			r'water density': ('kg/m$^3$', 'N/A', ''),
			r'wave direction.*': ('$^o$C', '$^o$C', ''),
			r'wave force': ('N/m$^2$', 'N/A', ''),
			r'wave peak period': ('s', 's', ''),
			r'minimum dt': ('s', 's', ''),
		}
		
		shortNames = {
			r'Time of Peak.*': 't',
			r'.*elevation.*': 'h',
			r'flow': 'Q',
			r'2d flow': 'Q',
			r'bed shear stress': 'BSS',
			r'(bed elevation)$': 'h',
			r'depth': 'd',
			r'([^a-z]|^)vel': 'V',
			r'cumulative infiltration': 'CI',
			r'level': 'h',
			r'bed level': 'h',
			r'infiltration rate': 'IR',
			r'mb\d*': 'MB',
			r'unit flow': 'q',
			r'z0': 'Z0',
			r'cumulative rainfall': 'CR',
			r'rfml': 'RFML',
			r'rainfall rate': 'RR',
			r'stream power': 'SP',
			r'flow area': 'QA',
			r'time of max h': 't',
			r'time of max v': 't',
			r'losses': 'LC',
			r'flow regime': 'F',
			r'([^a-z]|^)sal': 'SAL',
			r'([^a-z]|^)sal.*flux': 'Q SAL',
			r'([^a-z]|^)temp': 'TEMP',
			r'bed elevation change' : 'DZB',
			r'downward .* wave radiaton flux': 'LW_Rad',
			r'evaporation rate': 'EVAP',
			r'mean sea level pressure' : 'MSLP',
			r'particle group \d* concentration': 'PTM',
			r'particle group \d* bed concentration': 'PTM_BED',
			r'precipitation rate': 'PRECIP',
			r'relative humidity': 'Rel_hum',
			r'significant wave height': 'Hsig',
			r'surface shear stress': 'Taus',
			r'tracer \d*': 'TRACE',
			r'trace[\s_]\d*[\s_]flux': 'Q TRACE',
			r'sediment fraction \d*': 'SED',
			r'sed[\s_]\d*[\s_]flux': 'Q SED',
			r'water density': 'RHOW',
			r'wave direction.*': 'Wvdir',
			r'wave force': 'Wvstr',
			r'wave peak period': 'Wvper',
			r'wind velocity': 'W10',
			r'minimum dt': 'dt',
		}

		# determine units i.e. metric, imperial, or unknown / blank
		u, m = -1, ''
		if unit_system is None:
			if self.canvas is not None:
				if self.canvas.mapUnits() == QgsUnitTypes.DistanceMeters or self.canvas.mapUnits() == QgsUnitTypes.DistanceKilometers or \
						self.canvas.mapUnits() == QgsUnitTypes.DistanceCentimeters or self.canvas.mapUnits() == QgsUnitTypes.DistanceMillimeters:  # metric
					u, m = 0, 'm'
				elif self.canvas.mapUnits() == QgsUnitTypes.DistanceFeet or self.canvas.mapUnits() == QgsUnitTypes.DistanceNauticalMiles or \
						self.canvas.mapUnits() == QgsUnitTypes.DistanceYards or self.canvas.mapUnits() == QgsUnitTypes.DistanceMiles:  # imperial
					u, m = 1, 'ft'
		elif unit_system == 'si':
			u, m = 0, 'm'
		else:
			u, m = 1, 'ft'

		if return_unit_only:
			if type(types) is list:
				for i, name in enumerate(types):
					return regex_dict_val(units, name)[u] if regex_dict_val(units, name) is not None else ''
			else:
				return regex_dict_val(units, types)[u] if regex_dict_val(units, types) is not None else ''

		# clear existing values
		yAxisLabelTypes[0].clear()
		yAxisLabelTypes[1].clear()
		unit[0].clear()
		unit[1].clear()

		# get all plot data types
		types = []
		plotAsCollection = []
		plotAsQuiver = []
		for plotData, plotType in self.plotDataToPlotType.items():
			if plotType == plotNo:
				for line in self.plotData[plotData]:
					if type(line) is dict:
						types.append([val for k, val in line.items()][0])
						if plotData == TuPlot.DataCurtainPlot:
							if 'vector' in [val for k, val in line.items()][0].lower():
								plotAsQuiver.append(True)
								plotAsCollection.append(False)
							else:
								plotAsCollection.append(True)
								plotAsQuiver.append(False)
						else:
							plotAsCollection.append(False)
							plotAsQuiver.append(False)

		# create a copy of types - keep any changes local
		# curtain plot y-axis needs to be changed to elevation
		# types = types[:]
		for i, t in enumerate(types[:]):
			if plotAsQuiver and plotAsQuiver[i]:
				types[i] = ''
			elif plotAsCollection and plotAsCollection[i]:
				types[i] = 'water level'

		if self.tuView.tuMenuBar.freezeAxisLabels_action.isChecked():
			xAxisLabel = subplot.get_xlabel()
			yAxisLabelNewFirst = subplot.get_ylabel()
			if isSecondaryAxis[0]:
				subplot2 = self.getSecondaryAxis(plotNo)
				yAxisLabelNewSecond = subplot2.get_ylabel()
			else:
				yAxisLabelNewSecond = ''
			return xAxisLabel, yAxisLabelNewFirst, yAxisLabelNewSecond

		# # determine units i.e. metric, imperial, or unknown / blank
		# u, m = -1, ''
		# if self.canvas is not None:
		# 	if self.canvas.mapUnits() == QgsUnitTypes.DistanceMeters or self.canvas.mapUnits() == QgsUnitTypes.DistanceKilometers or \
		# 			self.canvas.mapUnits() == QgsUnitTypes.DistanceCentimeters or self.canvas.mapUnits() == QgsUnitTypes.DistanceMillimeters:  # metric
		# 		u, m = 0, 'm'
		# 	elif self.canvas.mapUnits() == QgsUnitTypes.DistanceFeet or self.canvas.mapUnits() == QgsUnitTypes.DistanceNauticalMiles or \
		# 			self.canvas.mapUnits() == QgsUnitTypes.DistanceYards or self.canvas.mapUnits() == QgsUnitTypes.DistanceMiles:  # imperial
		# 		u, m = 1, 'ft'
		# else:  # use blank
		# 	u, m = -1, ''

		x = ''
		y1 = ''
		y2 = ''
		# get x axis name
		if plotNo == TuPlot.TimeSeries:
			if self.tuView.tuOptions.xAxisDates:
				x = 'Date'
			else:
				x = 'Time (hr)'
		elif plotNo == TuPlot.CrossSection:
			x = 'Offset ({0})'.format(m)
		elif plotNo == TuPlot.CrossSection1D:
			pass
		elif plotNo == TuPlot.VerticalProfile:
			x = 'Elevation ({0})'.format(m)
		
		# get y axis name
		for i, name in enumerate(types):
			if name not in self.tuView.tuResults.secondaryAxisTypes:
				
				# remove '_1d' from name of 1d types
				if '_1d' in name:
					name = name.strip('_1d')
				
				# first axis label
				# if name.lower() in shortNames.keys():
				if regex_dict_val(shortNames, name) is not None:
					#shortName = shortNames[name.lower()]
					shortName = regex_dict_val(shortNames, name)
					if shortName not in yAxisLabelTypes[0]:
						yAxisLabelTypes[0].append(shortName)  # add to list of labels so no double ups
				# unitNew = units[name.lower()][u] if name.lower() in units.keys() else ''
				unitNew = regex_dict_val(units, name)[u] if regex_dict_val(units, name) is not None else ''
				if not unit[0]:
					unit[0].append(unitNew)
				else:
					if unitNew:
						if unitNew != unit[0][0]:
							unit[0][0] = ''
			else:
				
				# remove '_1d' from name of 1d types
				if '_1d' in name:
					name = name.strip('_1d')
				
				# secondary axis label
				# if name.lower() in shortNames.keys():
				if regex_dict_val(shortNames, name) is not None:
					# shortName = shortNames[name.lower()]
					shortName = regex_dict_val(shortNames, name)
					if shortName not in yAxisLabelTypes[1]:
						yAxisLabelTypes[1].append(shortName)
				# unitNew = units[name.lower()][u] if name.lower() in units.keys() else ''
				unitNew = regex_dict_val(units, name)[u] if regex_dict_val(units, name) is not None else ''
				if not unit[1]:
					unit[1].append(unitNew)
				else:
					if unitNew:
						if unitNew != unit[1][0]:
							unit[1][0] = ''
		
		# set final axis label for first axis
		for i, label in enumerate(yAxisLabelTypes[0]):
			if i == 0:
				y1 = '{0}'.format(label)
			else:
				y1 = '{0}, {1}'.format(y1, label)
		if unit[0]:
			if unit[0][0]:
				y1 = '{0} ({1})'.format(y1, unit[0][0])
		
		# set final axis label for second axis
		for i, label in enumerate(yAxisLabelTypes[1]):
			if i == 0:
				y2 = '{0}'.format(label)
			else:
				y2 = '{0}, {1}'.format(y2, label)
		if unit[1]:
			if unit[1][0]:
				y2 = '{0} ({1})'.format(y2, unit[1][0])

		# finalise axis labels depending on plot type
		if plotNo != TuPlot.VerticalProfile:
			xAxisLabel = x
			yAxisLabelNewFirst = y1
			yAxisLabelNewSecond = y2
		else:
			xAxisLabel = y1
			yAxisLabelNewFirst = x
			yAxisLabelNewSecond = y2
		
		return xAxisLabel, yAxisLabelNewFirst, yAxisLabelNewSecond
	
	def createSecondaryAxisAnnotation(self, plotNo, ax):
		if plotNo == TuPlot.TimeSeries:
			self.timeSeriesAnnot2 = ax.annotate("debug", xy=(15, 15),
			                                    xycoords='data',
			                                    textcoords="offset points",
			                                    bbox=dict(boxstyle="round", fc="w"))
			self.timeSeriesAnnot2.set_visible(False)
			self.timeSeriesHoverPoint2 = ax.scatter(0, 0, 20, 'red')
			self.timeSeriesHoverPoint2.set_visible(False)
			return

		if plotNo == TuPlot.CrossSection:
			self.longPlotAnnot2 = ax.annotate("debug", xy=(15, 15),
			                                    xycoords='data',
			                                    textcoords="offset points",
			                                    bbox=dict(boxstyle="round", fc="w"))
			self.longPlotAnnot2.set_visible(False)
			self.longPlotHoverPoint2 = ax.scatter(0, 0, 20, 'red')
			self.longPlotHoverPoint2.set_visible(False)
			return

		if plotNo == TuPlot.VerticalProfile:
			self.verticalProfileAnnot2 = ax.annotate("debug", xy=(15, 15),
			                                    xycoords='data',
			                                    textcoords="offset points",
			                                    bbox=dict(boxstyle="round", fc="w"))
			self.verticalProfileAnnot2.set_visible(False)
			self.verticalProfileHoverPoint2 = ax.scatter(0, 0, 20, 'red')
			self.verticalProfileHoverPoint2.set_visible(False)
			return

	def getSecondaryAxis(self, plotNo, create=True):
		"""
		Collect secondary Y axis. Will create the axis if it does not exist.

		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:return: matplotlib.axis object
		"""
		
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		
		if not isSecondaryAxis[0]:
			if create:
				isSecondaryAxis[0] = True
				if plotNo == TuPlot.TimeSeries:
					self.axis2TimeSeries = subplot.twinx()
					self.createSecondaryAxisAnnotation(plotNo, self.axis2TimeSeries)
					return self.axis2TimeSeries
				elif plotNo == TuPlot.CrossSection:
					self.axis2LongPlot = subplot.twinx()
					self.createSecondaryAxisAnnotation(plotNo, self.axis2LongPlot)
					return self.axis2LongPlot
				elif plotNo == TuPlot.VerticalProfile:
					self.axis2VerticalPlot = subplot.twiny()
					self.createSecondaryAxisAnnotation(plotNo, self.axis2VerticalPlot)
					return self.axis2VerticalPlot
			else:
				return None
		else:
			if plotNo == TuPlot.TimeSeries:
				return self.axis2TimeSeries
			elif plotNo == TuPlot.CrossSection:
				return self.axis2LongPlot
			elif plotNo == TuPlot.VerticalProfile:
				return self.axis2VerticalPlot
			
	def reorderByAxis(self, types, data, label, plotAsPoints, plotAsPatch, flowRegime, flowRegimeTied, plotAsCollection,
	                  plotAsQuiver, plotVertMesh, dataTypes):
		"""
		Reorders the data for plotting so that it is ordered by axis - axis 1 then axis 2. This is so that is
		consistent with how the legend is going to be plotted when freezing the plotting style.
		
		:param types: list -> str result types
		:param data: list all data -> list dataset -> list coordinates -> float coordinate e.g. [ [ [ x values ], [ y values ] ] ]
		:param label: list -> str labels
		:return: list, list, list
		"""

		types1, types2, typesOrdered = [], [], []
		data1, data2, dataOrdered = [], [], []
		label1, label2, labelOrdered = [], [], []
		plotAsPoints1, plotAsPoints2, plotAsPointsOrdered = [], [], []
		plotAsPatch1, plotAsPatch2, plotAsPatchOrdered = [], [], []
		flowRegime1, flowRegime2, flowRegimeOrdered = [], [], []
		flowRegimeTied1, flowRegimeTied2, flowRegimeTiedOrdered = [], [], []
		plotAsCollection1, plotAsCollection2, plotAsCollectionOrdered = [], [], []
		plotAsQuiver1, plotAsQuiver2, plotAsQuiverOrdered = [], [], []
		plotVertMesh1, plotVertMesh2, plotVertMeshOrdered = [], [], []
		dataTypes1, dataTypes2, dataTypesOrdered = [], [], []

		for i, rtype in enumerate(types):
			if plotAsCollection[i] or plotAsQuiver[i] or len(data[i][0]) > 0:
				secondaryAxis = False
				if rtype in self.tuView.tuResults.secondaryAxisTypes:
					if not plotAsCollection[i] or not plotAsQuiver:
						secondaryAxis = True
				elif re.findall(r"flow regime_\d_", rtype, re.IGNORECASE):
					j = int(re.findall(r"\d", rtype)[0])
					if types[j] in self.tuView.tuResults.secondaryAxisTypes:
						secondaryAxis = True
				if secondaryAxis:
					types2.append(rtype)
					data2.append(data[i])
					label2.append(label[i])
					plotAsPoints2.append(plotAsPoints[i])
					plotAsPatch2.append(plotAsPatch[i])
					flowRegime2.append(flowRegime[i])
					flowRegimeTied2.append(flowRegimeTied[i])
					plotAsCollection2.append(plotAsCollection[i])
					plotAsQuiver2.append(plotAsQuiver[i])
					plotVertMesh2.append(plotVertMesh[i])
					dataTypes2.append(dataTypes[i])
				else:
					types1.append(rtype)
					data1.append(data[i])
					label1.append(label[i])
					plotAsPoints1.append(plotAsPoints[i])
					plotAsPatch1.append(plotAsPatch[i])
					flowRegime1.append(flowRegime[i])
					flowRegimeTied1.append(flowRegimeTied[i])
					plotAsCollection1.append(plotAsCollection[i])
					plotAsQuiver1.append(plotAsQuiver[i])
					plotVertMesh1.append(plotVertMesh[i])
					dataTypes1.append(dataTypes[i])

		typesOrdered = types1 + types2
		dataOrdered = data1 + data2
		labelOrdered = label1 + label2
		plotAsPointsOrdered = plotAsPoints1 + plotAsPoints2
		plotAsPatchOrdered = plotAsPatch1 + plotAsPatch2
		flowRegimeOrdered = flowRegime1 + flowRegime2
		flowRegimeTiedOrdered = flowRegimeTied1 + flowRegimeTied2
		plotAsCollectionOrdered = plotAsCollection1 + plotAsCollection2
		plotAsQuiverOrdered = plotAsQuiver1 + plotAsQuiver2
		plotVertMeshOrdered = plotVertMesh1 + plotVertMesh2
		dataTypesOrdered = dataTypes1 + dataTypes2

		# loop through a second time to fix flow regime indexes
		for i, rtype in enumerate(typesOrdered[:]):
			if plotAsCollection[i] or len(data[i][0]) > 0:
				if re.findall(r"flow regime_\d_", rtype, re.IGNORECASE):
					j = int(re.findall(r"\d", rtype)[0])
					j2 = labelOrdered.index(label[j])
					rtypeNew = re.sub(r"flow regime_\d_", f"flow regime_{j2}_", rtype, flags=re.IGNORECASE)
					typesOrdered[i] = rtypeNew
					flowRegimeTiedOrdered[i] = j2

		return typesOrdered, dataOrdered, labelOrdered, plotAsPointsOrdered, \
		       plotAsPatchOrdered, flowRegimeOrdered, flowRegimeTiedOrdered, \
			   plotAsCollectionOrdered, plotAsQuiverOrdered, plotVertMeshOrdered, \
			   dataTypesOrdered
	
	def drawPlot(self, plotNo, data, label, types, dataTypes, **kwargs):
		"""
		Will draw the plot based on plot enumerator, x y data, and labels

		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:param data: list all data -> list x, y -> list axis data -> float value e.g. [ [ [ x1, x2, .. ], [ y1, y2, .. ] ] ]
		:param label: list - str
		:return: bool -> True for successful, False for unsuccessful
		"""

		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		subplot2 = None
		toolbar, viewToolbar, mplToolbar = self.tuPlotToolbar.plotNoToToolbar[plotNo]
		isSecondaryAxisLocal = False  # local version because time series and map outputs are treated separately
		
		# deal with kwargs
		refreshOnly = kwargs['refresh_only'] if 'refresh_only' in kwargs.keys() else False  # essentially add time
		plotAsPoints = kwargs['plot_as_points'] if 'plot_as_points' in kwargs.keys() else [False] * len(data)
		plotAsPatch = kwargs['plot_as_patch'] if 'plot_as_patch' in kwargs.keys() else [False] * len(data)
		export = kwargs['export'] if 'export' in kwargs.keys() else None
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		time = kwargs['time'] if 'time' in kwargs.keys() else None
		showCurrentTime = kwargs['show_current_time'] if 'show_current_time' in kwargs.keys() else False
		flowRegime = kwargs['flow_regime'] if 'flow_regime' in kwargs.keys() else [False] * len(data)
		flowRegimeTied = kwargs['flow_regime_tied'] if 'flow_regime_tied' in kwargs.keys() else [-1] * len(data)
		plotAsCollection = kwargs['plot_as_collection'] if 'plot_as_collection' in kwargs else [False] * len(data)
		plotAsQuiver = kwargs['plot_as_quiver'] if 'plot_as_quiver' in kwargs else [False] * len(data)
		plotVertMesh = kwargs['plot_vert_mesh'] if 'plot_vert_mesh' in kwargs else [False] * len(data)
		geom = kwargs['geom'] if 'geom' in kwargs else None
		pipeNames = kwargs['pipe_names'] if 'pipe_names' in kwargs else []

		flowRegimeTiedMult = 0.1

		yLimits2 = None

		# background colour
		rect = figure.patch
		rect.set_facecolor(self.tuView.tuOptions.plotBackgroundColour)

		# get axis limits
		xLimits = subplot.get_xlim()
		yLimits = subplot.get_ylim()
		if export:  # override axis object for exporting
			figure, subplot = plt.subplots()
			self.manageMatplotlibAxe(subplot)
		if isSecondaryAxis[0]:
			subplot2 = self.getSecondaryAxis(plotNo)
			yLimits2 = subplot2.get_ylim()
			#if export:  # override axis object for exporting
			#	subplot2 = subplot.twinx()

		# get labels
		if data:
			types, data, label, plotAsPoints, \
			plotAsPatch, flowRegime, flowRegimeTied, \
			plotAsCollection, plotAsQuiver, plotVertMesh,\
			dataTypes                                     = self.reorderByAxis(types, data, label,
                                                                               plotAsPoints, plotAsPatch,
                                                                               flowRegime, flowRegimeTied,
                                                                               plotAsCollection, plotAsQuiver,
			                                                                   plotVertMesh, dataTypes)  # orders the data by axis (axis 1 then axis 2)
			labelsOriginal = label[:]  # save a copy as original labels so it can be referenced later
			label, artistTemplates = self.getNewPlotProperties(plotNo, label, data, rtype='lines')  # check if there are any new names and styling
		
		# Get data
		secondYAxisInUse = False  # this is for an empty secondary axis
		if not refreshOnly:  # only if it's not refresh only
			if data:
				nPipe = -1  # used for culvert/pipe id labelling on the plot
			for i in range(len(data)):
				# determine which axis it belongs on
				rtype = types[i]
				axis = 1
				if rtype in self.tuView.tuResults.secondaryAxisTypes:
					if not plotAsCollection[i]:
						axis = 2
				elif re.findall(r"flow regime_\d_", rtype, re.IGNORECASE):
					j = int(re.findall(r"\d", rtype)[0])
					if types[j] in self.tuView.tuResults.secondaryAxisTypes:
						axis = 2
				if axis == 2:
					#axis = 2
					#if len(subplot.get_shared_x_axes().get_siblings(subplot)) < 2:
					subplot2 = self.getSecondaryAxis(plotNo)
					if export:  # override axis object for exporting
						subplot2 = subplot.twinx()
					if not isSecondaryAxis[0]:
						isSecondaryAxis[0] = True
						isSecondaryAxisLocal = True
				#else:
				#	axis = 1

				# colour
				ci = len(subplot.lines)
				if isSecondaryAxis[0]:
					ci += len(subplot2.lines)
				while ci + 1 > len(self.colours):
					self.colours += generateRandomMatplotColours2(10)
				colour = self.colours[ci]

				# data
				if self.tuView.tuOptions.xAxisDates and plotNo == TuPlot.TimeSeries:
					if data[i]:
						if plotAsCollection is None or not plotAsCollection[i]:
							if type(data[i][0]) is np.ndarray:
								if type(data[i][0][0]) is datetime:
									x = data[i][0]
								else:
									x = self.convertTimeToDate(data[i][0])
							else:
								if type(data[i][0][0]) is datetime:
									x = data[i][0]
								else:
									x = self.convertTimeToDate(data[i][0])
				else:
					if plotAsCollection is None or not plotAsCollection[i]:
						x = data[i][0]
				if plotAsCollection is None or not plotAsCollection[i]:
					y = data[i][1]

				# add data to plot
				if axis == 1:
					if plotVertMesh is not None and plotVertMesh[i]:  # skip vertical mesh plotting for now
						continue
					if plotAsPatch is None or not plotAsPatch[i]:  # normal X, Y data
						if plotAsPoints is None or not plotAsPoints[i]:  # plot as line
							a, = subplot.plot(x, y, label=label[i], color=colour)
							applyMatplotLibArtist(a, artistTemplates[i])
							self.plotData[dataTypes[i]].append({a: types[i]})
							if geom is not None:
								self.cursorMarker.addTracker(labelsOriginal[i], a, geom)
						else:  # plot as points only
							if flowRegime[i]:
								if flowRegimeTied[i] > -1:
									y2 = data[flowRegimeTied[i]][1]
									if type(y2) is list:
										add = (max(y2) - min(y2)) * flowRegimeTiedMult
									else:
										add = (np.nanmax(y2) - np.nanmin(y2)) * flowRegimeTiedMult
									y2 = [x + add for x in data[flowRegimeTied[i]][1]]
								else:
									y2 = self.convertFlowRegimeToInt(y)
								if type(y[0]) is not np.int32:
									for j, n in enumerate(y[:]):
										if not re.findall(r"[a-z]", n, re.IGNORECASE):
											y[j] = n.strip().replace("", "G")
										else:
											y[j] = n.upper()
								if flowRegimeTied[i] > -1:
									for j, n in enumerate(x):
										a, = subplot.plot(n, y2[j], marker=f"${y[j]}$", color='grey', label=label[i], markeredgewidth=0.1, linestyle='None')
										self.plotData[dataTypes[i]].append({a: types[i]})
								else:
									a, = subplot.plot(x, y2, marker='o', linestyle='None', label=label[i], color=colour)
									self.plotData[dataTypes[i]].append({a: types[i]})
							else:
								a, = subplot.plot(x, y, marker='o', linestyle='None', label=label[i], color=colour)
								self.plotData[dataTypes[i]].append({a: types[i]})
							applyMatplotLibArtist(a, artistTemplates[i])
						if not export:
							artists[0].append(a)
							labels[0].append(labelsOriginal[i])
						#subplot.hold(True)
					else:  # plot as patch
						if plotAsCollection is not None and plotAsCollection[i]:  # curtain plot
							a = subplot.add_collection(data[i], autolim=True)
							applyMatplotLibArtist(a, artistTemplates[i])
							self.plotData[dataTypes[i]].append({a: types[i]})
							subplot.autoscale_view()
							if not export:
								artists[0].append(a)
								labels[0].append(labelsOriginal[i])
							if geom is not None:
								self.cursorMarker.addTracker('{0}__curtain__'.format(labelsOriginal[i]), a, geom)
							#self.plotData[dataTypes[i]].append({a: types[i]})
						elif plotAsQuiver is not None and plotAsQuiver[i]:
							q = data[i]
							config = q[4]
							config['label'] = label[i]
							# quiver = Quiver(subplot, q[0], q[1], q[2], q[3], scale=0.0025, scale_units='x', width=0.0025, headwidth=2.5, headlength=3, label=label[i])
							quiver = Quiver(subplot, q[0], q[1], q[2], q[3], **config)
							self.quiver_U = q[5]
							a = subplot.add_collection(quiver, autolim=True)
							self.plotData[dataTypes[i]].append({a: types[i]})
							subplot.autoscale_view()
							# quiver.set_offsets(q[0])
							# quiver.set_UVC(q[1], q[2])
						else:  # culvert layer
							nPipe += 1
							pipeArtists = []
							for j, verts in enumerate(x):
								if verts:
									poly = TuflowPipe(verts, facecolor='0.9', edgecolor='0.5', label=label[i])
									if len(pipeNames) >= nPipe + 1 and len(pipeNames[nPipe]) >= j + 1:
										poly.channel_id = pipeNames[nPipe][j]
									a = subplot.add_patch(poly)
									self.plotData[dataTypes[i]].append({a: types[i]})
									pipeArtists.append(a)
				elif axis == 2:
					secondYAxisInUse = True
					if plotAsPatch is None or not plotAsPatch[i]:  # normal X, Y data
						if plotAsPoints is None or not plotAsPoints[i]:
							a, = subplot2.plot(x, y, marker='x', label=label[i], color=colour)
							applyMatplotLibArtist(a, artistTemplates[i])
							self.plotData[dataTypes[i]].append({a: types[i]})
							if geom is not None:
								self.cursorMarker.addTracker(labelsOriginal[i], a, geom)
						else:
							if flowRegime[i]:
								if flowRegimeTied[i] > -1:
									y2 = data[flowRegimeTied[i]][1]
									if type(y2) is list:
										add = (max(y2) - min(y2)) * flowRegimeTiedMult
									else:
										add = (np.nanmax(y2) - np.nanmin(y2)) * flowRegimeTiedMult
									y2 = [x + add for x in data[flowRegimeTied[i]][1]]
								else:
									y2 = self.convertFlowRegimeToInt(y)
								if type(y[0]) is not np.int32:
									for j, n in enumerate(y[:]):
										if not re.findall(r"[a-z]", n, re.IGNORECASE):
											y[j] = n.strip().replace("", "G")
										else:
											y[j] = n.upper()
								if flowRegimeTied[i] > -1:
									for j, n in enumerate(x):
										a, = subplot2.plot(n, y2[j], marker=f"${y[j]}$", color='grey', label=label[i], markeredgewidth=0.1, linestyle='None')
										self.plotData[dataTypes[i]].append({a: types[i]})
								else:
									a, = subplot2.plot(x, y2, marker='D', linestyle='None', label=label[i], color=colour)
									self.plotData[dataTypes[i]].append({a: types[i]})
							else:
								a, = subplot2.plot(x, y, marker='D', linestyle='None', label=label[i], color=colour)
								self.plotData[dataTypes[i]].append({a: types[i]})
							applyMatplotLibArtist(a, artistTemplates[i])
						if not export:
							artists[1].append(a)
							labels[1].append(labelsOriginal[i])
						#subplot2.hold(True)
					else:  # plot as patch i.e. culvert
						nPipe += 1
						pipeArtists = []
						for j, verts in enumerate(x):
							if verts:
								poly = TuflowPipe(verts, facecolor='0.9', edgecolor='0.5', label=label[i])
								if len(pipeNames) >= nPipe + 1 and len(pipeNames[nPipe]) >= j + 1:
									poly.channel_id = pipeNames[nPipe][j]
								a = subplot2.add_patch(poly)
								self.plotData[dataTypes[i]].append({a: types[i]})
								pipeArtists.append(a)
		
		# get secondary axis if refresh only
		if isSecondaryAxis[0] and refreshOnly:
			subplot2 = self.getSecondaryAxis(plotNo)
		
		# user plot data
		self.plotUserData(plotNo)
		
		# check if show current time is selected
		self.showCurrentTime(plotNo, time=time, show_current_time=showCurrentTime)

		# show vertical mesh
		self.showVertMesh(plotNo, data, label, plotVertMesh)
		
		# get axis labels
		if data:
			xAxisLabel, yAxisLabelFirst, yAxisLabelSecond = self.setAxisNames(plotNo, types, plotAsCollection, plotAsQuiver)
			xAxisLabels[0].append(xAxisLabel)
			yAxisLabels[0].append(yAxisLabelFirst)
			yAxisLabels[1].append(yAxisLabelSecond)
			# Get user axis labels
			oldLabels = [xAxisLabel, yAxisLabelFirst, yAxisLabelSecond]
			newLabels = self.getNewPlotProperties(plotNo, oldLabels, None, rtype='axis labels')
			if newLabels:
				xAxisLabel = newLabels[0]
			if len(newLabels) > 1:
				yAxisLabelFirst = newLabels[1]
			if len(newLabels) > 2:
				yAxisLabelSecond = newLabels[2]

		# remove secondary axis if not necessary
		if not secondYAxisInUse:
			pass  # reserve spot to remove secondary axis - haven't figured out how to yet :(

		# draw plot
		if export:
			if len(subplot.get_shared_x_axes().get_siblings(subplot)) < 2:
				subplot2 = None
			self.updateLegend(plotNo, redraw=False, ax=subplot, ax2=subplot2)
		else:
			if draw:
				self.updateLegend(plotNo, redraw=False)
		if data:
			axisLabelFontSize = viewToolbar.axisLabelFontSize_action.value(0)
			if xAxisLabel:
				subplot.set_xlabel(xAxisLabel, fontsize=axisLabelFontSize)
			if yAxisLabelFirst or yAxisLabelSecond:
				if yAxisLabelFirst:
					subplot.set_ylabel(yAxisLabelFirst, fontsize=axisLabelFontSize)
				if isSecondaryAxis[0]:
					#if not isSecondaryAxisLocal:
					#	subplot2 = self.getSecondaryAxis(plotNo)
					if plotNo != TuPlot.VerticalProfile:
						subplot2.set_ylabel(yAxisLabelSecond, fontsize=axisLabelFontSize)
					else:
						subplot2.set_xlabel(yAxisLabelSecond, fontsize=axisLabelFontSize)
		
		# check if there is user plot data
		userPlotData = False
		for status in [v.status for k, v in sorted(self.userPlotData.datasets.items(), key=lambda x: x[-1].number)]:
			if status:
				userPlotData = True
				break
		isData = False
		if data or userPlotData:
			isData = True

		if isData and self.tuView.tuOptions.xAxisDates and plotNo == TuPlot.TimeSeries:
			fmt = mdates.DateFormatter(self.tuView.tuOptions.dateFormat)
			subplot.xaxis.set_major_formatter(fmt)
			if subplot.get_xlim()[0] < 1:
				# this happens when there is an empty data set on either primary or secondary axis
				# - causes issues with date formatting - need to correct
				for ax in subplot.get_shared_x_axes().get_siblings(subplot):
					if not ax.lines:
						ax.autoscale(True)
						ax.relim()

				# repalced below with the above - hopefully better
				# if subplot.get_xlim()[0] < 1:
				# 	xmin_manual = 9999999999
				# 	xmax_manual = -99999
				# 	lines = subplot.lines
				# 	for l in lines:
				# 		if [x for x in l.get_xdata()]:
				# 			if type([x for x in l.get_xdata()][0]) is float or type([x for x in l.get_xdata()][0]) is np.float64:
				# 				xmin_manual = min(xmin_manual, min(l.get_xdata()))
				# 				xmax_manual = max(xmin_manual, max(l.get_xdata()))
				# 			else:
				# 				xmin_manual = min(xmin_manual, min([convert_datetime_to_float(x) for x in l.get_xdata()]))
				# 				xmax_manual = max(xmin_manual, max([convert_datetime_to_float(x) for x in l.get_xdata()]))
				# 	if xmin_manual >= 1:
				# 		subplot.set_xlim(xmin_manual, xmax_manual)
				# 	else:
				# 		subplot.set_xlim(1,2)  # hopefully doesn't get here
			try:
				for tick in subplot.get_xticklabels():
					tick.set_rotation(self.tuView.tuOptions.xAxisLabelRotation)
					if self.tuView.tuOptions.xAxisLabelRotation > 0 and self.tuView.tuOptions.xAxisLabelRotation < 90:
						tick.set_horizontalalignment('right')
					elif self.tuView.tuOptions.xAxisLabelRotation > 90 and self.tuView.tuOptions.xAxisLabelRotation < 180:
						tick.set_horizontalalignment('left')
					elif self.tuView.tuOptions.xAxisLabelRotation > 180 and self.tuView.tuOptions.xAxisLabelRotation < 270:
						tick.set_horizontalalignment('right')
					elif self.tuView.tuOptions.xAxisLabelRotation > 270 and self.tuView.tuOptions.xAxisLabelRotation < 360:
						tick.set_horizontalalignment('left')
					elif self.tuView.tuOptions.xAxisLabelRotation > -90 and self.tuView.tuOptions.xAxisLabelRotation < 0:
						tick.set_horizontalalignment('left')
					elif self.tuView.tuOptions.xAxisLabelRotation > -180 and self.tuView.tuOptions.xAxisLabelRotation < -90:
						tick.set_horizontalalignment('right')
					elif self.tuView.tuOptions.xAxisLabelRotation > -270 and self.tuView.tuOptions.xAxisLabelRotation < -180:
						tick.set_horizontalalignment('left')
					elif self.tuView.tuOptions.xAxisLabelRotation > -360 and self.tuView.tuOptions.xAxisLabelRotation < -270:
						tick.set_horizontalalignment('right')
			except:
				pass
		elif self.tuView.tuOptions.xAxisDates and plotNo == TuPlot.TimeSeries:
			formatter = subplot.xaxis.get_major_formatter()
			if not isinstance(formatter, ScalarFormatter):
				fmt = mdates.DateFormatter(self.tuView.tuOptions.dateFormat)
				subplot.xaxis.set_major_formatter(fmt)
		# 		if subplot.get_xlim()[0] < 1:
		# 			for ax in subplot.get_shared_x_axes().get_siblings(subplot):
		# 				ax.autoscale(True)
		# 				ax.relim()
		#
		# 			if subplot.get_xlim()[0] < 1:
		# 				for ax in subplot.get_shared_x_axes().get_siblings(subplot):
		# 					ax.xaxis.set_major_formatter(ScalarFormatter())


					# if subplot.get_xlim()[0] < 1:
					# 	if subplot.get_xlim()[0] < 1:
					# 		xmin_manual = 9999999999
					# 		xmax_manual = -99999
					# 		lines = subplot.lines
					# 		for l in lines:
					# 			if [x for x in l.get_xdata()]:
					# 				if type([x for x in l.get_xdata()][0]) is float or type([x for x in l.get_xdata()][0]) is np.float64:
					# 					xmin_manual = min(xmin_manual, min(l.get_xdata()))
					# 					xmax_manual = max(xmin_manual, max(l.get_xdata()))
					# 				else:
					# 					xmin_manual = min(xmin_manual,
					# 					                  min([convert_datetime_to_float(x) for x in l.get_xdata()]))
					# 					xmax_manual = max(xmin_manual,
					# 					                  max([convert_datetime_to_float(x) for x in l.get_xdata()]))
					# 		if xmin_manual >= 1:
					# 			subplot.set_xlim(xmin_manual, xmax_manual)
					# 		else:
					# 			subplot.set_xlim(1, 2)  # hopefully doesn't get here

		try:
			if not self.lockAxis(plotNo, showCurrentTime):
				subplot.autoscale(True)
				subplot.relim()

				# fix because curtain plots aren't correctly relim'd
				if plotNo == TuPlot.CrossSection:
					self.relimCurtainPlot()

				if self.checkPlotForInconsistentUnits(subplot):
					subplot.xaxis.set_major_locator(matplotlib.ticker.AutoLocator())
					if not self.tuView.tuOptions.xAxisDates:
						subplot.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
					subplot.relim()
					subplot.autoscale(True)
					subplot.relim()

					# fix because curtain plots aren't correctly relim'd
					if plotNo == TuPlot.CrossSection:
						self.relimCurtainPlot()


			if isSecondaryAxis[0]:
				subplot2.relim()
				if self.checkPlotForInconsistentUnits(subplot2):
					subplot2.xaxis.set_major_locator(matplotlib.ticker.AutoLocator())
					if not self.tuView.tuOptions.xAxisDates:
						subplot2.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
					subplot2.relim()
					subplot2.autoscale(True)
					subplot2.relim()

		except:
			pass
		if self.tuView.tuMenuBar.freezeAxisXLimits_action.isChecked():
			subplot.set_xbound(xLimits)
		if self.tuView.tuMenuBar.freezeAxisYLimits_action.isChecked():
			subplot.set_ybound(yLimits)
			if isSecondaryAxis[0]:
				if yLimits2 is not None:
					subplot2.set_ybound(yLimits2)
		if types is not None and 'Flow Regime_1d' in types:
			if 'Flow Regime_1d' in self.tuView.tuResults.secondaryAxisTypes:
				subplot2.set_ybound((-4, 15))
				subplot2.set_yticks(np.arange(-4, 16, 1))
				subplot2.set_yticks([], minor=True)
				subplot2.set_yticklabels(['L', 'K', 'B', 'A', 'G', 'C', 'D', 'E', 'F', 'H', 'J', '*', '#', 'S', 'T', 'N', 'U', 'W', 'O', 'R'])
			else:
				subplot.set_ybound((-4, 15))
				subplot.set_yticks(np.arange(-4, 16, 1))
				subplot.set_yticks([], minor=True)
				subplot.set_yticklabels(['L', 'K', 'B', 'A', 'G', 'C', 'D', 'E', 'F', 'H', 'J', '*', '#', 'S', 'T', 'N', 'U', 'W', 'O', 'R'])

		subplot._label = "Primary Axis"
		if isSecondaryAxis[0]:
			subplot2._label = "Secondary Axis"

		# axis font size
		axisFontSize = viewToolbar.axisFontSize_action.value(0)
		subplot.tick_params(axis='both', which='both', labelsize=axisFontSize)
		if subplot2 is not None:
			subplot2.tick_params(axis='both', which='both', labelsize=axisFontSize)

		try:
			#subplot.autoscale(True)
			#subplot.relim()
			#if isSecondaryAxis[0]:
			#	subplot2.relim()
			figure.tight_layout()
			skipDraw = False
		except ValueError:  # something has gone wrong and trying to plot time (hrs) on a date formatted x axis
			skipDraw = True
			pass
		except Exception as e:
			skipDraw = True
			pass

		if export:
			# figure.suptitle(os.path.splitext(os.path.basename(export))[0])
			subplot.set_title(os.path.splitext(os.path.basename(export))[0])
			figure.savefig(export, bbox_inches='tight')
			if subplot2 is not None:
				subplot2.cla()
		else:
			if draw and not skipDraw:
				plotWidget.draw()

			# record axis limits
			xLimits = subplot.get_xlim()
			yLimits = subplot.get_ylim()
			xAxisLimits[0].clear()
			xAxisLimits[0].append(xLimits)
			yAxisLimits[0].clear()
			yAxisLimits[0].append(yLimits)
			if isSecondaryAxis[0]:
				#subplot2 = self.getSecondaryAxis(plotNo)
				yLimits2 = subplot2.get_ylim()
				yAxisLimits[1].clear()
				yAxisLimits[1].append(yLimits2)
		
		return True
	
	def updateTimeSeriesPlot(self, **kwargs):
		"""
		Update time series plot. Will go through all marker points and selected point features.

		:return: bool -> True for successful, False for unsuccessful
		"""

		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		update = kwargs['update'] if 'update' in kwargs.keys() else 'all'
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		time = kwargs['time'] if 'time' in kwargs.keys() else None
		showCurrentTime = kwargs['show_current_time'] if 'show_current_time' in kwargs.keys() else False
		retainFlow = kwargs['retain_flow'] if 'retain_flow' in kwargs.keys() else False
		meshRendered = kwargs['mesh_rendered'] if 'mesh_rendered' in kwargs.keys() else True
		plotActiveScalar = kwargs['plot_active_scalar'] if 'plot_active_scalar' in kwargs else False
		clearType = kwargs['clear_type'] if 'clear_type' in kwargs else None
		
		# if not plot:
		# 	if update == '1d only':
		# 		self.clearPlot(0, retain_2d=True, retain_flow=True)
		# 	elif update == '1d and 2d only':
		# 		self.clearPlot(0, retain_flow=True)
		# 	else:
		# 		self.clearPlot(0, retain_flow=retainFlow)

		self.clearPlot2(TuPlot.TimeSeries, clearType, clear_rubberband=False, clear_selection=False)
		
		if plot.lower() != '1d only' and plot.lower() != 'flow only' and update != '1d only':
			self.tuPlot2D.resetMultiPointCount()
			
			multi = False  # do labels need to be counted up e.g. point 1, point 2
			if len(self.tuTSPoint.points) + len(self.tuPlot2D.plotSelectionPointFeat) > 1:
				multi = True
			
			for i, point in enumerate(self.tuTSPoint.points):
				self.tuPlot2D.plotTimeSeriesFromMap(None, QgsPointXY(point), bypass=multi, plot='2D Only',
				                                    draw=draw, time=time, show_current_time=showCurrentTime,
				                                    retain_flow=retainFlow, mesh_rendered=meshRendered,
				                                    plot_active_scalar=plotActiveScalar, markerNo=i+1)
			
			for f in self.tuPlot2D.plotSelectionPointFeat:
				# get feature name from attribute
				iFeatName = self.tuView.tuOptions.iLabelField
				if len(f.attributes()) > iFeatName:
					featName = f.attributes()[iFeatName]
				else:
					featName = None

				self.tuPlot2D.plotTimeSeriesFromMap(None, f.geometry().asPoint(), bypass=multi, plot='2D Only',
				                                    draw=draw, time=time, show_current_time=showCurrentTime,
				                                    retain_flow=retainFlow, mesh_rendered=meshRendered,
				                                    plot_active_scalar=plotActiveScalar, featName=featName)
				
			if self.tuPlot2D.multiPointSelectCount > 1:
				self.tuPlot2D.reduceMultiPointCount(1)

			# 2D depth average options
			multi = False  # do labels need to be counted up e.g. point 1, point 2
			if len(self.tuTSPointDepAv.points) + len(self.tuPlot3D.plotSelectionPointFeat) > 1:
				multi = True
			for i, point in enumerate(self.tuTSPointDepAv.points):
				self.tuPlot3D.plotTimeSeriesFromMap(None, QgsPointXY(point), bypass=multi,
				                                    draw=draw, time=time, show_current_time=showCurrentTime,
				                                     mesh_rendered=meshRendered,
				                                    plot_active_scalar=plotActiveScalar, markerNo=i+1,
				                                    data_type=TuPlot.DataTimeSeriesDepAv)
			for f in self.tuPlot3D.plotSelectionPointFeat:
				# get feature name from attribute
				iFeatName = self.tuView.tuOptions.iLabelField
				if len(f.attributes()) > iFeatName:
					featName = f.attributes()[iFeatName]
				else:
					featName = None

				self.tuPlot3D.plotTimeSeriesFromMap(None, f.geometry().asPoint(), bypass=multi, plot='2D Only',
				                                    draw=draw, time=time, show_current_time=showCurrentTime,
				                                    retain_flow=retainFlow, mesh_rendered=meshRendered,
				                                    plot_active_scalar=plotActiveScalar, featName=featName,
				                                    data_type=TuPlot.DataTimeSeriesDepAv)
		
		# Flow
		if not retainFlow:  # if retain flow, no need to recalculate flow
			if plot.lower() != '1d only' and plot.lower() != '2d only' and update != '1d only' and update != '1d and 2d only':
				self.tuPlot2D.resetMultiFlowLineCount()
				multiFlow = False  # consider flow lines separately
				
				if len(self.tuFlowLine.rubberBands) + len(self.tuPlot2D.plotSelectionFlowFeat) > 1:
					multiFlow = True
				
				for i, line in enumerate(self.tuFlowLine.rubberBands):
					if line.asGeometry() is not None:
						if not line.asGeometry().isNull():
							geom = line.asGeometry().asPolyline()
							feat = QgsFeature()
							try:
								feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in geom]))
							except:
								feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x.x(), x.y()) for x in geom]))
							self.tuPlot2D.plotFlowFromMap(None, feat, bypass=multiFlow, plot='flow only', draw=draw, time=time,
							                              show_current_time=showCurrentTime, mesh_rendered=meshRendered)
					
				for feat in self.tuPlot2D.plotSelectionFlowFeat:
					self.tuPlot2D.plotFlowFromMap(None, feat, bypass=multiFlow, plot='flow only', draw=draw, time=time,
					                              show_current_time=showCurrentTime, mesh_rendered=meshRendered)
					
				if self.tuPlot2D.multiFlowLineSelectCount > 1:
					self.tuPlot2D.reduceMultiFlowLineCount(1)
		elif showCurrentTime:  # might need to update plot with updated time - for animation
			self.drawPlot(0, [], None, None, [TuPlot.DataCurrentTime], draw=draw, time=time, show_current_time=showCurrentTime)
		
		if plot.lower() != '2d only' and plot.lower() != 'flow only':
			self.tuPlot1D.plot1dTimeSeries(bypass=True, plot='1D Only', draw=draw, time=time, show_current_time=showCurrentTime)
			self.tuPlot1D.plot1dMaximums(plot='1D Only', draw=draw)
			
		if not plot:
			if self.tuView.tuMenuBar.showMedianEvent_action.isChecked():
				self.showStatResult(0, 'Median')
				
			if self.tuView.tuMenuBar.showMeanEvent_action.isChecked():
				self.showStatResult(0, 'Mean')
				
		if not self.artistsTimeSeriesFirst and not self.artistsCrossSectionSecond:
			if self.userPlotData.datasets:
				self.drawPlot(0, [], None, None, [TuPlot.DataUserData], draw=draw, time=time, show_current_time=showCurrentTime)
		
		return True
	
	def updateCrossSectionPlot(self, **kwargs):
		"""
		Update cross section plot. Will go through all rubberbands and selected line features.

		:return: bool -> True for successful, False for unsuccessful
		"""

		qv= Qgis.QGIS_VERSION_INT

		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		time = kwargs['time'] if 'time' in kwargs.keys() else None
		meshRendered = kwargs['mesh_rendered'] if 'mesh_rendered' in kwargs.keys() else True
		plotActiveScalar = kwargs['plot_active_scalar'] if 'plot_active_scalar' in kwargs else False
		
		if time is not None:
			if time != 'Maximum' and time != 99999 and time != 'Minimum' and time != -99999:
				if qv < 31600:
					time = '{0:.6f}'.format(kwargs['time']) if 'time' in kwargs.keys() else None
				else:
					if type(time) is str:
						if not self.tuView.tuOptions.xAxisDates:
							if time in self.tuView.tuResults.cboTime2timekey:
								time = self.tuView.tuResults.cboTime2timekey[time]
								time = self.tuView.tuResults.timekey2time[time]
							else:
								unit = self.tuView.tuOptions.timeUnits
								time = convertFormattedTimeToTime(time, unit=unit)
							zt = self.tuView.tuOptions.zeroTime
							time = zt + datetime.timedelta(hours=time)
						else:
							time = datetime.datetime.strptime(time, self.tuView.tuResults.dateFormat)
		
		# if not plot:
		# 	self.clearPlot(1)
		# 	#self.clearedLongPlot = False
		self.clearPlot2(TuPlot.CrossSection, clear_rubberband=False, clear_selection=False)
		
		if plot.lower() != '1d only':
			multi = False  # do labels need to be counted up e.g. line 1, line 2
			if len(self.tuCrossSection.rubberBands) > 1:
				multi = True
			elif len(self.tuPlot2D.plotSelectionLineFeat) > 1:
				multi = True
			elif len(self.tuCrossSection.rubberBands) + len(self.tuPlot2D.plotSelectionLineFeat) > 1:
				multi = True
			
			for i, rubberBand in enumerate(self.tuCrossSection.rubberBands):
				if rubberBand.asGeometry() is not None:
					if not rubberBand.asGeometry().isNull():
						geom = rubberBand.asGeometry().asPolyline()
						feat = QgsFeature()
						try:
							feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in geom]))
						except:
							feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x.x(), x.y()) for x in geom]))
						# if i == 0:
						self.tuPlot2D.plotCrossSectionFromMap(None, feat, bypass=multi, plot='2D Only', draw=draw,
						                                      time=time, mesh_rendered=meshRendered,
						                                      plot_active_scalar=plotActiveScalar, lineNo=i+1)
						# else:
						# 	self.tuPlot2D.plotCrossSectionFromMap(None, feat, bypass=True, plot='2D Only', draw=draw,
						# 	                                      time=time, mesh_rendered=meshRendered,
						# 	                                      plot_active_scalar=plotActiveScalar)
			
			for feat in self.tuPlot2D.plotSelectionLineFeat:
				# get feature name from attribute
				iFeatName = self.tuView.tuOptions.iLabelField
				if len(feat.attributes()) > iFeatName:
					featName = feat.attributes()[iFeatName]
				else:
					featName = None

				self.tuPlot2D.plotCrossSectionFromMap(None, feat, bypass=multi, plot='2D Only', draw=draw,
				                                      time=time, mesh_rendered=meshRendered,
				                                      plot_active_scalar=plotActiveScalar, featName=featName)
				
			if self.tuPlot2D.multiLineSelectCount > 1:
				self.tuPlot2D.reduceMultiLineCount(1)

			# depth averaged cross sections
			multi = False  # do labels need to be counted up e.g. line 1, line 2
			if len(self.tuCSLineDepAv.rubberBands) > 1:
				multi = True
			elif len(self.tuPlot3D.plotSelectionLineFeat) > 1:
				multi = True
			elif len(self.tuCSLineDepAv.rubberBands) + len(self.tuPlot3D.plotSelectionLineFeat) > 1:
				multi = True

			for i, rubberBand in enumerate(self.tuCSLineDepAv.rubberBands):
				if rubberBand.asGeometry() is not None:
					if not rubberBand.asGeometry().isNull():
						geom = rubberBand.asGeometry().asPolyline()
						feat = QgsFeature()
						try:
							feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in geom]))
						except:
							feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x.x(), x.y()) for x in geom]))
						# if i == 0:
						self.tuPlot3D.plotCrossSectionFromMap(None, feat, bypass=multi, draw=draw,
						                                      time=time, mesh_rendered=meshRendered,
						                                      plot_active_scalar=plotActiveScalar, lineNo=i + 1,
						                                      data_type=TuPlot.DataCrossSectionDepAv)
				# else:
				# 	self.tuPlot2D.plotCrossSectionFromMap(None, feat, bypass=True, plot='2D Only', draw=draw,
				# 	                                      time=time, mesh_rendered=meshRendered,
				# 	                                      plot_active_scalar=plotActiveScalar)

			for feat in self.tuPlot3D.plotSelectionLineFeat:
				# get feature name from attribute
				iFeatName = self.tuView.tuOptions.iLabelField
				if len(feat.attributes()) > iFeatName:
					featName = feat.attributes()[iFeatName]
				else:
					featName = None

				self.tuPlot3D.plotCrossSectionFromMap(None, feat, bypass=multi, draw=draw,
				                                      time=time, mesh_rendered=meshRendered,
				                                      plot_active_scalar=plotActiveScalar, featName=featName,
				                                      data_type=TuPlot.DataCrossSectionDepAv)

			if self.tuPlot3D.multiLineSelectCount > 1:
				self.tuPlot3D.reduceMultiLineCount(1)

			# curtain plots
			multi = False  # do labels need to be counted up e.g. line 1, line 2
			if len(self.tuCurtainLine.rubberBands) > 1:
				multi = True
			elif len(self.tuPlot3D.plotSelectionCurtainFeat) > 1:
				multi = True
			elif len(self.tuCurtainLine.rubberBands) + len(self.tuPlot3D.plotSelectionCurtainFeat) > 1:
				multi = True

			for i, rubberBand in enumerate(self.tuCurtainLine.rubberBands):
				if rubberBand.asGeometry() is not None:
					if not rubberBand.asGeometry().isNull():
						geom = rubberBand.asGeometry().asPolyline()
						feat = QgsFeature()
						try:
							feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in geom]))
						except:
							feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x.x(), x.y()) for x in geom]))
						# if i == 0:
						self.tuPlot3D.plotCurtainFromMap(None, feat, bypass=multi, draw=draw,
						                                 time=time,
						                                 plot_active_scalar=plotActiveScalar, lineNo=i+1,
						                                 update=True)
			for feat in self.tuPlot3D.plotSelectionCurtainFeat:
				iFeatName = self.tuView.tuOptions.iLabelField
				if len(feat.attributes()) > iFeatName:
					featName = feat.attributes()[iFeatName]
				else:
					featName = None
				self.tuPlot3D.plotCurtainFromMap(None, feat, bypass=multi, draw=draw, time=time, featName=featName, update=True)
		
		if plot.lower() != '2d only':
			self.tuPlot1D.plot1dLongPlot(bypass=True, plot='1D Only', draw=draw, time=time)
			self.tuPlot1D.plot1dCrossSection(bypass=True, draw=draw, time=time)
			self.tuPlot1D.plot1dHydProperty(bypass=True, draw=draw, time=time)

		if not self.artistsLongPlotFirst and not self.artistsLongPlotSecond:
			if self.userPlotData.datasets:
				self.drawPlot(1, [], [], None, None, draw=draw, time=time)
			
		return True

	def updateVerticalProfilePlot(self, **kwargs):
		"""

		"""

		qv = Qgis.QGIS_VERSION_INT

		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		time = kwargs['time'] if 'time' in kwargs.keys() else None
		meshRendered = kwargs['mesh_rendered'] if 'mesh_rendered' in kwargs.keys() else True
		plotActiveScalar = kwargs['plot_active_scalar'] if 'plot_active_scalar' in kwargs else False

		if time is not None:
			if time != 'Maximum' and time != 99999 and time != 'Minimum' and time != -99999:
				if qv < 31600:
					time = '{0:.6f}'.format(kwargs['time']) if 'time' in kwargs.keys() else None
				else:
					if type(time) is str:
						if not self.tuView.tuOptions.xAxisDates:
							if time in self.tuView.tuResults.cboTime2timekey:
								time = self.tuView.tuResults.cboTime2timekey[time]
								time = self.tuView.tuResults.timekey2time[time]
							else:
								unit = self.tuView.tuOptions.timeUnits
								time = convertFormattedTimeToTime(time, unit=unit)
							zt = self.tuView.tuOptions.zeroTime
							time = zt + datetime.timedelta(hours=time)
						else:
							time = datetime.datetime.strptime(time, self.tuView.tuResults.dateFormat)

		self.clearPlot2(TuPlot.VerticalProfile, clear_rubberband=False, clear_selection=False)

		multi = False  # do labels need to be counted up e.g. point 1, point 2
		if len(self.tuVPPoint.points) + len(self.tuPlot3D.plotSelectionVPFeat) > 1:
			multi = True
		for i, point in enumerate(self.tuVPPoint.points):
			self.tuPlot3D.plotVerticalProfileFromMap(None, QgsPointXY(point), bypass=multi, draw=draw,
			                                 time=time, plot_active_scalar=plotActiveScalar, markerNo=i + 1,
			                                 update=True)
		for f in self.tuPlot3D.plotSelectionVPFeat:
			# get feature name from attribute
			iFeatName = self.tuView.tuOptions.iLabelField
			if len(f.attributes()) > iFeatName:
				featName = f.attributes()[iFeatName]
			else:
				featName = None

			self.tuPlot3D.plotVerticalProfileFromMap(None, f.geometry().asPoint(), bypass=multi,
			                                         draw=draw, time=time,
			                                         mesh_rendered=meshRendered,
			                                         plot_active_scalar=plotActiveScalar, featName=featName)
	
	def updateCurrentPlot(self, plotNo=None, **kwargs):
		"""
		Will update plot based on current tab index.

		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		update = kwargs['update'] if 'update' in kwargs.keys() else 'all'
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		time = kwargs['time'] if 'time' in kwargs.keys() else None
		showCurrentTime = kwargs['show_current_time'] if 'show_current_time' in kwargs.keys() else False
		retainFlow = kwargs['retain_flow'] if 'retain_flow' in kwargs.keys() else False
		meshRendered = kwargs['mesh_rendered'] if 'mesh_rendered' in kwargs.keys() else True
		plotActiveScalar = kwargs['plot_active_scalar'] if 'plot_active_scalar' in kwargs else False

		success = False
		if plotNo is None:
			plotNo = self.tuView.tabWidget.currentIndex()
		
		if plotNo == TuPlot.TimeSeries:
			success = self.updateTimeSeriesPlot(update=update, retain_flow=retainFlow, draw=draw, time=time,
			                                    show_current_time=showCurrentTime, mesh_rendered=meshRendered,
			                                    plot_active_scalar=plotActiveScalar)
		elif plotNo == TuPlot.CrossSection:
			success = self.updateCrossSectionPlot(draw=draw, time=time, mesh_rendered=meshRendered,
			                                      plot_active_scalar=plotActiveScalar)
		elif plotNo == TuPlot.CrossSection1D:
			pass
		elif plotNo == TuPlot.VerticalProfile:
			success = self.updateVerticalProfilePlot(draw=draw, time=time, mesh_rendered=meshRendered,
			                                         plot_active_scalar=plotActiveScalar)
		
		# disconnect map canvas refresh if it is connected - used for rendering after loading from project
		try:
			self.tuView.canvas.mapCanvasRefreshed.disconnect(self.updateCurrentPlot)
		except:
			pass
		
		return success
	
	def updateAllPlots(self):
		"""
		Updates all plotting windows.

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		for i in range(4):
			self.updateCurrentPlot(i)
			
		return True
	
	def updateLegend(self, plotNo, **kwargs):
		"""
		Update plot legend.
		
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:return: bool -> True for successful, False for unsuccessful
		"""

		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		
		if 'ax' in kwargs.keys():
			subplot = kwargs['ax']  # override axis object - for exporting plots only
		subplot2 = kwargs['ax2'] if 'ax2'in kwargs.keys() else None
		
		toolbar, viewToolbar, mplToolbar = self.tuPlotToolbar.plotNoToToolbar[plotNo]
		
		redraw = kwargs['redraw'] if 'redraw' in kwargs.keys() else True
		
		if not viewToolbar.legendMenu.menuAction().isChecked():
			subplot.legend_ = None
			self.removeColourBar(plotNo)
			return True

		# get legend labels and artists
		uniqueNames, uniqueNames2, uniqueLines, uniqueLines2 = [], [], [], []
		line, lab = subplot.get_legend_handles_labels()
		# remove duplicates i.e. culvert and pipes only need to appear in legend once
		uniqueNames = []
		uniqueLines = []
		for i, l in enumerate(lab):
			if type(line[i]) is PolyCollection:
				l = '{0}__curtain__'.format(l)
			if l not in uniqueNames:
				uniqueNames.append(l)
				uniqueLines.append(line[i])
		if isSecondaryAxis[0] or subplot2:
			if not subplot2:
				subplot2 = self.getSecondaryAxis(plotNo)
			line2, lab2 = subplot2.get_legend_handles_labels()
			# remove duplicates i.e. culvert and pipes only need to appear in legend once
			uniqueNames2 = []
			uniqueLines2 = []
			for i, l in enumerate(lab2):
				if type(line2[i]) is PolyCollection:
					l = '{0}__curtain__'.format(l)
				if l not in uniqueNames2:
					uniqueNames2.append(l)
					uniqueLines2.append(line2[i])
		#labs = [uniqueNames, uniqueNames2]
		#lines = [uniqueLines, uniqueLines2]
	
		# apply
		legendPos = -1
		if viewToolbar.legendUR.isChecked():
			legendPos = 1
		elif viewToolbar.legendUL.isChecked():
			legendPos = 2
		elif viewToolbar.legendLL.isChecked():
			legendPos = 3
		elif viewToolbar.legendLR.isChecked():
			legendPos = 4
		elif viewToolbar.legendCL.isChecked():
			legendPos = 6
		elif viewToolbar.legendCR.isChecked():
			legendPos = 7
		elif viewToolbar.legendLC.isChecked():
			legendPos = 8
		elif viewToolbar.legendUC.isChecked():
			legendPos = 9
		elif viewToolbar.legendC.isChecked():
			legendPos = 10
		elif viewToolbar.legendCustomPos.isChecked():
			legendPos = 100
		if legendPos == -1 and not viewToolbar.legendAuto.isChecked():
			viewToolbar.legendAuto.setChecked(True)
		lines = uniqueLines + uniqueLines2
		lab = uniqueNames + uniqueNames2
		linesCopy, labCopy = [], []
		for i, l in enumerate(lines):
			if type(l) is PolyCollection:
				# if not isSecondaryAxis[0]:
				# 	divider = make_axes_locatable(subplot)
				# else:
				# 	subplot2 = self.getSecondaryAxis(plotNo)
				# 	divider = make_axes_locatable(subplot2)
				# self.cax = divider.append_axes("right", "5%", pad="3%")
				if viewToolbar.legendMenu.menuAction().isChecked():
					self.addColourBarAxes(plotNo)
					col_bar = ColourBar(l, self.cax)
					# label = lab[i]
					label = lab[i].split('__curtain__')[0]
					if '{0}__curtain_plot__'.format(label) in self.frozenLPProperties:
						label = self.frozenLPProperties['{0}__curtain_plot__'.format(label)][0]
					col_bar.ax.set_xlabel(label)
					l.set_label(label)
					plotWidget.draw()
				else:
					self.removeColourBar(plotNo)
			elif type(l) is Quiver:
				# self.qk = subplot.quiverkey(l, X=0.9, Y=0.95, U=1, label=lab[i], labelpos='W', coordinates='figure')
				if viewToolbar.legendMenu.menuAction().isChecked():
					self.addQuiverLegend(plotNo, l, 'vector')
				else:
					self.removeQuiverKey(plotNo)
			else:
				linesCopy.append(l)
				labCopy.append(lab[i])
		# if self.cax is None:
		# 	gs = gridspec.GridSpec(1, 1)
		# 	subplot.set_position(gs[0, 0].get_position(figure))
		# 	subplot.set_subplotspec(gs[0, 0])
		# 	if isSecondaryAxis[0]:
		# 		subplot2 = self.getSecondaryAxis(plotNo)
		# 		subplot2.set_position(gs[0, 0].get_position(figure))
		# 		subplot2.set_subplotspec(gs[0, 0])
		ncol = 1
		if viewToolbar.legendVertical.isChecked():
			ncol = 1
		elif viewToolbar.legendHorizontal.isChecked():
			ncol = max(1, len(labCopy))
		elif viewToolbar.legendCustomOrientation.isChecked():
			ncol = viewToolbar.legendCustomOrientation.value(0)
		fontsize = viewToolbar.legendFontSize.value(0)
		if linesCopy:
			if viewToolbar.legendAuto.isChecked():
				subplot.legend(linesCopy, labCopy, ncol=ncol, fontsize=fontsize)
			elif viewToolbar.legendCustomPos.isChecked():
				xpos, ypos = viewToolbar.legendCustomPos.values()
				subplot.legend(linesCopy, labCopy, loc=(xpos, ypos), ncol=ncol, fontsize=fontsize)
				if subplot.legend_ is not None:
					if subplot.legend_.get_window_extent().y1 > subplot.bbox.y1:
						self.reSpecPlot(plotNo)
					elif subplot.legend_.get_window_extent().y0 < subplot.bbox.y0:
						self.reSpecPlot(plotNo)
					elif subplot.legend_.get_window_extent().x1 > subplot.bbox.x1:
						self.reSpecPlot(plotNo)
					elif subplot.legend_.get_window_extent().x0 < subplot.bbox.x0:
						self.reSpecPlot(plotNo)
			else:
				subplot.legend(linesCopy, labCopy, loc=legendPos, ncol=ncol, fontsize=fontsize)
			if redraw:
				plotWidget.draw()
		
		return True

	def resize(self, e):
		"""

		"""

		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(1)

		# if isSecondaryAxis[0]:
		# 	self.removeColourBar(1)


	def setNewPlotProperties(self, plotNo):
		"""
		Freezes the figure options based on the current legend options - name and styling. Adds to dictionary object
		so that every time a result rtype is plotted, the frozen name and style can be applied.
		
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:return: bool -> True for successful, False for unsuccessful
		"""

		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		
		if plotNo == TuPlot.TimeSeries:
			viewToolbar = self.tuPlotToolbar.viewToolbarTimeSeries
		elif plotNo == TuPlot.CrossSection:
			viewToolbar = self.tuPlotToolbar.viewToolbarLongPlot
		elif plotNo == TuPlot.CrossSection1D:
			viewToolbar = self.tuPlotToolbar.viewToolbarCrossSection
		elif plotNo == TuPlot.VerticalProfile:
			viewToolbar = self.tuPlotToolbar.viewToolbarVerticalProfile
		
		# get new labels and styles
		lines, labs = subplot.get_legend_handles_labels()
		if not lines:
			return
		if isSecondaryAxis[0]:
			subplot2 = self.getSecondaryAxis(plotNo)
			lines2, labs2 = subplot2.get_legend_handles_labels()
		# get new axis names
		xLabel = subplot.get_xlabel()
		yLabel = subplot.get_ylabel()
		if isSecondaryAxis[0]:
			yLabel2 = subplot2.get_ylabel()
		# get new axis limits
		xLimits = subplot.get_xlim()
		yLimits = subplot.get_ylim()
		if isSecondaryAxis[0]:
			yLimits2 = subplot2.get_ylim()
		
		# store standard name with user name and style in dictionary
		for i, label in enumerate(labels[0]):
			label = label.split('[')[0].strip()  # remove any time values in the label e.g. 'water level [01:00:00]'
			if type(lines[i]) is PolyCollection:
				# lab = '{0}__curtain_plot__'.format(labs[i])
				lab = '{0}__curtain_plot__'.format(label)
			else:
				lab = label

			if plotNo == TuPlot.TimeSeries:
				self.frozenTSProperties[lab] = [labs[i], lines[i]]
			elif plotNo == TuPlot.CrossSection:
				self.frozenLPProperties[lab] = [labs[i], saveMatplotLibArtist(lines[i])]
			elif plotNo == TuPlot.CrossSection1D:
				self.frozenCSProperties[lab] = [labs[i], lines[i]]
			elif plotNo == TuPlot.VerticalProfile:
				self.frozenVPProperties[lab] = [labs[i], lines[i]]
		if isSecondaryAxis[0]:
			for i, label in enumerate(labels[1]):
				label = label.split('[')[0].strip()  # remove any time values in the label e.g. 'water level [01:00:00]'
				if plotNo == TuPlot.TimeSeries:
					self.frozenTSProperties[label] = [labs2[i], lines2[i]]
				elif plotNo == TuPlot.CrossSection:
					self.frozenLPProperties[label] = [labs2[i], lines2[i]]
				elif plotNo == TuPlot.CrossSection1D:
					self.frozenCSProperties[label] = [labs2[i], lines2[i]]
				elif plotNo == TuPlot.VerticalProfile:
					self.frozenVPProperties[label] = [labs2[i], lines2[i]]
					
		# store axis labels
		if plotNo == TuPlot.TimeSeries:
			if xAxisLabels[0]:
				self.frozenTSAxisLabels[xAxisLabels[0][0]] = xLabel
			if yAxisLabels[0]:
				self.frozenTSAxisLabels[yAxisLabels[0][0]] = yLabel
		elif plotNo == TuPlot.CrossSection:
			if xAxisLabels[0]:
				self.frozenLPAxisLabels[xAxisLabels[0][0]] = xLabel
			if yAxisLabels[0]:
				self.frozenLPAxisLabels[yAxisLabels[0][0]] = yLabel
		elif plotNo == TuPlot.CrossSection1D:
			if xAxisLabels[0]:
				self.frozenCSAxisLabels[xAxisLabels[0][0]] = xLabel
			if yAxisLabels[0]:
				self.frozenCSAxisLabels[yAxisLabels[0][0]] = yLabel
		elif plotNo == TuPlot.VerticalProfile:
			if xAxisLabels[0]:
				self.frozenVPAxisLabels[xAxisLabels[0][0]] = xLabel
			if yAxisLabels[0]:
				self.frozenVPAxisLabels[yAxisLabels[0][0]] = yLabel
		if isSecondaryAxis[0]:
			if plotNo == TuPlot.TimeSeries:
				if yAxisLabels[1]:
					self.frozenTSAxisLabels[yAxisLabels[1][0]] = yLabel2
			elif plotNo == TuPlot.CrossSection:
				if yAxisLabels[1]:
					self.frozenLPAxisLabels[yAxisLabels[1][0]] = yLabel2
			elif plotNo == TuPlot.CrossSection1D:
				if yAxisLabels[1]:
					self.frozenCSAxisLabels[yAxisLabels[1][0]] = yLabel2
			elif plotNo == TuPlot.VerticalProfile:
				if yAxisLabels[1]:
					self.frozenVPAxisLabels[yAxisLabels[1][0]] = yLabel2
				
		# check if axis limits have changed - if yes then auto lock axis limits
		if xLimits != xAxisLimits[0][0]:
			viewToolbar.freezeXAxisAction.setChecked(True)
		if yLimits != yAxisLimits[0][0]:
			viewToolbar.freezeYAxisAction.setChecked(True)
		if isSecondaryAxis[0]:
			if yLimits2 != yAxisLimits[1][0]:
				viewToolbar.freezeYAxisAction.setChecked(True)
		if viewToolbar.freezeXAxisAction.isChecked() and viewToolbar.freezeYAxisAction.isChecked():
			viewToolbar.freezeXYAxisAction.setChecked(True)

		return True

	def getNewPlotProperties(self, plotNo, labels, data, rtype):
		"""
		Looks up the new plot properties from the dictionary object added to in setNewPlotProperties.
		
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:param labels: list -> str rtype names e.g. Depth
		:param rtype: str plot property rtype 'lines' or 'axis labels'
		:return: list -> str new rtype name, list -> matplotlib line2D
		"""
		

		if rtype == 'lines':
			newLabels = []
			newArtists = []
			for i, label in enumerate(labels):
				labelparts = label.split('[')  # remove any time values in the label e.g. 'water level [01:00:00]'
				label = labelparts[0].strip()
				if len(labelparts) > 1:
					labelend = ' [{0}'.format(labelparts[-1])
				else:
					labelend = ''
				if data is not None:
					if type(data[i]) is PolyCollection:
						label = '{0}__curtain_plot__'.format(label)

				if plotNo == TuPlot.TimeSeries:
					if label in self.frozenTSProperties.keys():
						newLabels.append(self.frozenTSProperties[label][0])
						newArtists.append(self.frozenTSProperties[label][1])
					else:
						newLabels.append(label)
						newArtists.append(None)
				elif plotNo == TuPlot.CrossSection:
					if label in self.frozenLPProperties.keys():
						newLabels.append(self.frozenLPProperties[label][0])
						newArtists.append(self.frozenLPProperties[label][1])
					else:
						label = re.split(r'(__curtain_plot__)$', label, re.IGNORECASE)[0]
						newLabels.append(label + labelend)
						newArtists.append(None)
				elif plotNo == TuPlot.CrossSection1D:
					if label in self.frozenCSProperties.keys():
						newLabels.append(self.frozenCSProperties[label][0])
						newArtists.append(self.frozenCSProperties[label][1])
					else:
						newLabels.append(label)
						newArtists.append(None)
				elif plotNo == TuPlot.VerticalProfile:
					if label in self.frozenVPProperties.keys():
						newLabels.append(self.frozenVPProperties[label][0])
						newArtists.append(self.frozenVPProperties[label][1])
					else:
						newLabels.append(label)
						newArtists.append(None)
			
			return newLabels, newArtists
			
		elif rtype == 'axis labels':
			newLabels = []
			for label in labels:
				if plotNo == TuPlot.TimeSeries:
					if label in self.frozenTSAxisLabels.keys():
						newLabels.append(self.frozenTSAxisLabels[label])
					else:
						newLabels.append(label)
				elif plotNo == TuPlot.CrossSection:
					if label in self.frozenLPAxisLabels.keys():
						newLabels.append(self.frozenLPAxisLabels[label])
					else:
						newLabels.append(label)
				elif plotNo == TuPlot.CrossSection1D:
					if label in self.frozenCSAxisLabels.keys():
						newLabels.append(self.frozenCSAxisLabels[label])
					else:
						newLabels.append(label)
				elif plotNo == TuPlot.VerticalProfile:
					if label in self.frozenVPAxisLabels.keys():
						newLabels.append(self.frozenVPAxisLabels[label])
					else:
						newLabels.append(label)
			
			return newLabels

	def clearFrozenPlotProperties(self, plotNo=None, rtype=None):
		plots = [TuPlot.TimeSeries, TuPlot.CrossSection, TuPlot.VerticalProfile]
		if plotNo is not None:
			if type(plotNo) is int:
				plots = [plotNo]
			elif type(plotNo) is list:
				plots = plotNo

		for plot in plots:
			if plot == TuPlot.TimeSeries:
				if rtype == 'lines' or rtype is None:
					self.frozenTSProperties.clear()
				if rtype == 'axis labels' or rtype is None:
					self.frozenTSAxisLabels.clear()
			elif plot == TuPlot.CrossSection:
				if rtype == 'lines' or rtype is None:
					self.frozenLPProperties.clear()
				if rtype == 'axis labels' or rtype is None:
					self.frozenLPAxisLabels.clear()
			elif plot == TuPlot.VerticalProfile:
				if rtype == 'lines' or rtype is None:
					self.frozenVPProperties.clear()
				if rtype == 'axis labels' or rtype is None:
					self.frozenVPAxisLabels.clear()
	
	def exportCSV(self, plotNo, data, labels, types, outputFolder, fileName, **kwargs):
		"""
		Export data to CSV.
		
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:param data: list all data -> list x, y -> list axis data -> float value e.g. [ [ [ x1, x2, .. ], [ y1, y2, .. ] ] ]
		:param labels: list -> str dataset label
		:param outputFolder: str output folder location
		:param fileName: str name for file
		:return: bool -> True for successful, False for unsuccessful
		"""

		overwrite = kwargs['overwrite'] if 'overwrite' in kwargs else False

		# convert labels to user defined dataset labels (or default label if user has not changed it)
		newLabels, newArtists = self.getNewPlotProperties(plotNo, labels, None, rtype='lines')  # newArtists not used for csv
		
		# convert axis names to user defined labels (or default label if user has not changed it)
		xAxisLabel, yAxisLabelFirst, yAxisLabelSecond = self.setAxisNames(plotNo, types)
		oldAxisNames = [xAxisLabel, yAxisLabelFirst, yAxisLabelSecond]
		newAxisNames = self.getNewPlotProperties(plotNo, oldAxisNames, None, rtype='axis labels')  # only need X axis name for csv
		
		# sort data into format ready to write - first find any datasets that are different in length and index pos
		lengthChanges = []
		for i in range(len(data)):
			x = data[i][0]
			if i == 0:
				length = len(x)
				maxLength = len(x)
				lengthChanges.append(i)
			else:
				if len(x) != length:
					lengthChanges.append(i)
					length = len(x)
					maxLength = max(maxLength, len(x))
		# next format data into string
		datastring = ''
		for i in range(maxLength):  # iterate through longest series
			for j in range(len(data)):  # iterate through the different data sets
				x = data[j][0][i]
				y = data[j][1][i]
				if qIsNaN(x):
					x = ''
				if qIsNaN(y):
					y = ''
				if j in lengthChanges:  # where there are data length changes, include X axis values again
					datastring = '{0}{1},'.format(datastring, x)
				datastring = '{0}{1},'.format(datastring, y)  # add y value
				if j + 1 == len(data):  # include return character and remove last comma
					datastring = '{0}\n'.format(datastring[:-1])
					
		# column names
		header = ''
		for i, l in enumerate(newLabels):
			if i in lengthChanges:  # where there are data length changes, include X axis label again
				header = '{0}{1},'.format(header, newAxisNames[0])
			header = '{0}{1},'.format(header, l)  # add label
		header = '{0}\n'.format(header[:-1])  # add return character and remove last comma
			
		# unique output file name
		outFile = '{0}.csv'.format(os.path.join(outputFolder, fileName))
		iterator = 1
		if not overwrite:
			while os.path.exists(outFile):
				outFile = '{0}_{1}.csv'.format(os.path.join(outputFolder, fileName), iterator)
				iterator += 1
			
		# write data
		with open(outFile, 'w') as fo:
			fo.write(header)
			fo.write(datastring)
			
		return True
		
	def plotUserData(self, plotNo):
		"""
		Plots user input data
		
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:return: bool -> True for successful, False for unsuccessful
		"""

		qv = Qgis.QGIS_VERSION_INT
		
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		
		# get user data in order it appears in the manager
		for name in [k for k, v in sorted(self.userPlotData.datasets.items(), key=lambda x: x[-1].number)]:
			data = self.userPlotData.datasets[name]
			if data.status:
				if (data.plotType == 'Time Series Plot' and plotNo == TuPlot.TimeSeries) or (data.plotType == 'Cross Section / Long Plot' and plotNo == TuPlot.CrossSection):
					labelOriginal = 'User Plot Data: {0}'.format(data.name)
					label, artistTemplates = self.getNewPlotProperties(plotNo, [labelOriginal], None, rtype='lines')
					if labelOriginal not in labels[0]:
						if qv < 31600:
							x = data.x[:]
							if self.tuView.tuOptions.xAxisDates and plotNo == TuPlot.TimeSeries:
								if data.dates is None:
									x = self.convertTimeToDate(x)
								else:
									x = data.dates[:]
						else:
							rt = data.referenceTime if data.referenceTime is not None else self.tuView.tuOptions.zeroTime
							if self.tuView.tuOptions.xAxisDates and plotNo == TuPlot.TimeSeries:
								if data.dates:
									x = data.dates[:]
								else:
									x = [rt + timedelta(hours=x) for x in data.x]
							else:
								x = data.x[:]

						y = data.y[:]
						a, = subplot.plot(x, y, label=label[0])
						self.plotData[TuPlot.DataUserData].append(a)
						applyMatplotLibArtist(a, artistTemplates[0])
						artists[0].append(a)
						labels[0].append(labelOriginal)
					
		return True
	
	def convertTimeToDate(self, data):
		"""
		Converts time (hrs) to date based on user specified zero hour.
		
		:param data: list -> float
		:return: list -> datetime
		"""

		x = []
		for datum in data:
			time = None
			# if datum in self.tuView.tuResults.time2date.keys():
			if datum in self.tuView.tuResults.time2date_tspec.keys():
				# time = self.tuView.tuResults.time2date[datum]
				time = self.tuView.tuResults.time2date_tspec[datum]
			elif '{0:.6f}'.format(datum) in self.tuView.tuResults.timekey2date_tspec.keys():
				time = self.tuView.tuResults.timekey2date_tspec['{0:.6f}'.format(datum)]
			else:
				time = datetime2timespec(self.tuView.tuOptions.zeroTime, self.tuView.tuResults.loadedTimeSpec, 1) \
				       + timedelta(hours=datum)
				time = roundSeconds(time, 2)
				modelDates = sorted([x for x in self.tuView.tuResults.date_tspec2time.keys()])
				if modelDates:
					time = self.tuView.tuResults.findTimeClosest(None, None, time, modelDates, True, 'closest')
			if time is None:
				break
			x.append(time)
			
		return x
	
	def convertDateToTime(self, data: str, unit: str='h') -> float:
		"""
		Converts date to time
		
		:param data: str
		:return: float time
		"""

		if type(data) is str:
			date = datetime.strptime(data, self.tuView.tuResults.dateFormat)
		else:
			date = data
		if date in self.tuView.tuResults.date_tspec2time:
			return self.tuView.tuResults.date_tspec2time[date]
		modelDates = sorted([x for x in self.tuView.tuResults.date_tspec2time.keys()])
		dateClosest = self.tuView.tuResults.findTimeClosest(None, None, date, modelDates, True, 'closest')
		if dateClosest in self.tuView.tuResults.date_tspec2time:
			return self.tuView.tuResults.date_tspec2time[dateClosest]
		if date in self.tuView.tuResults.date2time:
			return self.tuView.tuResults.date2time[date]
		else:
			return -99999.

	def convertFlowRegimeToInt(self, data: list) -> list:
		"""
		Converts flow regime letter to an integer value

		"""

		if type(data[0]) is np.int32:
			return data

		fr2int = {
			# inlet control below x axis
			'A': -1,
			'B': -2,
			'K': -3,
			'L': -4,
			# outlet control above x axis
			'C': 1,
			'D': 2,
			'E': 3,
			'F': 4,
			'H': 5,
			"J": 6,
			# channel flags
			'*': 7,
			'#': 8,
			'S': 9,
			'T': 10,
			'N': 11,
			'U': 12,
			'W': 13,
			# WEIR flags
			'O': 14,
			'R': 15,
			# no flow or flap gate closed = 0
			'G': 0,
			' ': 0,
			'  ': 0,
		}

		dataInt = []
		for d in data:
			if d:
				if d[0] in fr2int:
					dataInt.append(fr2int[d[0].upper()])
				else:
					dataInt.append(None)
			else:
				dataInt.append(0)

		return dataInt

	def formatCoord(self, x, y, z, x2=None, y2=None):
		x = x if x is not None else ' '
		y = y if y is not None else ' '
		z = f', Z: {z:.2f}' if z is not None else ''
		x2 = f', X2: {x2:.2f}' if x2 is not None else ''
		y2 = f', Y2: {y2:.2f}' if y2 is not None else ''

		try:
			value = f'X: {x:.2f}, Y: {y:.2f}{z}{x2}{y2}'
		except:
			value = 'X: Y: Z:'

		return value

	def onclick(self, e, plotNo):
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)

		subplot2 = self.getSecondaryAxis(plotNo, create=False)

		x, y, z = None, None, None
		x2, y2 = None, None
		if e.inaxes == subplot:
			# if e.button == MouseButton.LEFT and not e.dblclick:
			if e.guiEvent.type() == QEvent.MouseButtonPress and e.guiEvent.button() == Qt.LeftButton:
				x = e.xdata
				y = e.ydata
				x2 = None
				y2 = None
				if PolyCollection in [type(x) for x in artists[0]]:
					pc = [x for x in artists[0] if type(x) is PolyCollection][0]
					pci = polyCollectionPathIndexFromXY(pc, e.xdata, e.ydata)
					if pci is not None:
						z = pc.get_array()[pci]
		elif subplot2 is not None and e.inaxes == subplot2:
			if e.guiEvent.type() == QEvent.MouseButtonPress and e.guiEvent.button() == Qt.LeftButton:
				x2 = e.xdata
				y2 = e.ydata
				if PolyCollection in [type(x) for x in artists[0]]:
					pc = [x for x in artists[0] if type(x) is PolyCollection][0]
					pci = polyCollectionPathIndexFromXY(pc, e.xdata, e.ydata)
					if pci is not None:
						z = pc.get_array()[pci]
				x, y = subplot.transData.inverted().transform([e.x, e.y])
				if plotNo == TuPlot.VerticalProfile:
					y2 = None
				else:
					x2 = None
		self.tuView.plotCoords.setText(self.formatCoord(x, y, z, x2, y2))

	def vmeshToggled(self):
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(self.tuView.tabWidget.currentIndex())

		if self.tuView.tabWidget.currentIndex() == TuPlot.CrossSection:
			if PolyCollection in [type(x) for x in artists[0]]:
				self.updateCrossSectionPlot()
		elif self.tuView.tabWidget.currentIndex() == TuPlot.VerticalProfile:
			self.updateVerticalProfilePlot()

	def lockAxis(self, plotNo, showCurrentTime):
		"""return True if axis should not be relimed"""

		if plotNo == TuPlot.TimeSeries and showCurrentTime:
			return True

		if plotNo == TuPlot.VerticalProfile and self.verticalMesh_action.isChecked():
			return True

		return False

	def checkPlotForInconsistentUnits(self, ax):
		inconsistent = False
		dates = False
		time = False
		for line in ax.lines:
			if type(line) is plt.Line2D:
				x, y = line.get_data()
				if len(x) and type(x[0]) is datetime:
					dates = True
				else:
					time = True
		if dates and time:
			for line in ax.lines:
				if type(line) is plt.Line2D:
					x, y = line.get_data()
					if self.tuView.tuOptions.xAxisDates and len(x) and type(x[0]) is not datetime:
						xnew = self.convertTimeToDate(x)
						line.set_data(xnew, y)
					elif not self.tuView.tuOptions.xAxisDates and len(x) and type(x[0]) is datetime:
						xnew = [self.convertDateToTime(x) for x in x]
						line.set_data(xnew, y)

		return dates and time

	def relimCurtainPlot(self):
		"""
		Relim taking into consideration collections (curtain plots).

		Probably an issue with matplotlib that forces this to be required.
		"""

		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(TuPlot.CrossSection)

		fx = 0.05
		fy = 0.1
		xmin, xmax = subplot.get_xlim()
		ymin, ymax = subplot.get_ylim()
		x_updated = False
		y_updated = False
		artists, labels = subplot.get_legend_handles_labels()
		for a in artists:
			if type(a) == PolyCollection:
				if a not in subplot.artists:
					curtain_x = getPolyCollectionData(a, 'x')
					curtain_x_min = np.nanmin(curtain_x)
					curtain_x_max = np.nanmax(curtain_x)
					# if curtain_x_min < xmin or not subplot.artists:
						# xmin = curtain_x_min - (curtain_x_max - curtain_x_min) * f
					xmin = curtain_x_min
					x_updated = True
					# if curtain_x_max > xmax or not subplot.artists:
						# xmax = curtain_x_max + (curtain_x_max - curtain_x_min) * f
					xmax = curtain_x_max
					x_updated = True

					curtain_y = getPolyCollectionData(a, 'y')
					curtain_y_min = np.nanmin(curtain_y)
					curtain_y_max = np.nanmax(curtain_y)
					# if curtain_y_min < ymin or not subplot.artists:
						# ymin = curtain_y_min - (curtain_y_max - curtain_y_min) * f
					ymin = curtain_y_min
					y_updated = True
					# if curtain_y_max > ymax or not subplot.artists:
						# ymax = curtain_y_max + (curtain_y_max - curtain_y_min) * f
					ymax = curtain_y_max
					y_updated = True
		for a in artists:
			if type(a) == Quiver:
				if x_updated:
					xmin = min(np.nanmin(a.X), xmin)
					xmax = max(np.nanmax(a.X), xmax)
				else:
					xmin = np.nanmin(a.X)
					xmax = np.nanmax(a.X)
				if y_updated:
					ymin = min(np.nanmin(a.Y), ymin)
					ymax = max(np.nanmax(a.Y), ymax)
				else:
					ymin = np.nanmin(a.Y)
					ymax = np.nanmax(a.Y)
		if x_updated or y_updated:
			for a in artists:
				if type(a) == plt.Line2D:
					xmin = min(min(a.get_xdata()), xmin)
					xmax = max(max(a.get_xdata()), xmax)
					ymin = min(min(a.get_ydata()), ymin)
					ymax = max(max(a.get_ydata()), ymax)

		subplot.set_xlim([xmin, xmax])
		subplot.set_ylim([ymin, ymax])

		# add margins based on screen whitespace
		if x_updated:
			td0 = subplot.transData.transform((xmin, ymin))
			td1 = subplot.transData.transform((xmax, ymax))
			td2 = td0[0] - (td1[0] - td0[0]) * fx
			td3 = td1[0] + (td1[0] - td0[0]) * fx
			xmin = subplot.transData.inverted().transform((td2, td0[1]))[0]
			xmax = subplot.transData.inverted().transform((td3, td1[1]))[0]
			subplot.set_xlim([xmin, xmax])
		if y_updated:
			td0 = subplot.transData.transform((xmin, ymin))
			td1 = subplot.transData.transform((xmax, ymax))
			td2 = td0[1] - (td1[1] - td0[1]) * fy
			td3 = td1[1] + (td1[1] - td0[1]) * fy
			ymin = subplot.transData.inverted().transform((td0[0], td2))[1]
			ymax = subplot.transData.inverted().transform((td1[0], td3))[1]
			subplot.set_ylim([ymin, ymax])

	def getAnnotation(self, plotNo, axisNo):
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		if figure.texts:
			figure.texts.pop()
		if axisNo == 1:
			if plotNo == TuPlot.TimeSeries:
				if len(subplot.texts) > 1:
					[subplot.text.pop(i) for i in range(len(subplot.texts)) if i > 0]
				if len(subplot.texts) == 1:
					del self.timeSeriesAnnot
					self.timeSeriesAnnot = subplot.texts[0]
				else:
					del self.timeSeriesAnnot
					self.timeSeriesAnnot = subplot.annotate("debug", xy=(15, 15), xycoords='data',
					                                         textcoords="offset pixels",
					                                         bbox=dict(boxstyle="round", fc="w"))
					self.timeSeriesAnnot.set_visible(False)

				found = False
				for collection in subplot.collections[:]:
					if isinstance(collection, PathCollection):
						del self.timeSeriesHoverPoint
						self.timeSeriesHoverPoint = collection
						found = True
						continue
					if isinstance(collection, PathCollection) and found:
						subplot.collections.remove(collection)

				if not found:
					del self.timeSeriesHoverPoint
					xmin, xmax = subplot.get_xlim()
					x = (xmin + xmax) / 2.
					ymin, ymax = subplot.get_ylim()
					y = (ymin + ymax) / 2.
					self.timeSeriesHoverPoint = subplot.scatter(x, y, 20, 'red')
					self.timeSeriesHoverPoint.set_visible(False)

				return self.timeSeriesAnnot, self.timeSeriesHoverPoint

			if plotNo == TuPlot.CrossSection:
				if len(subplot.texts) > 1:
					[subplot.text.pop(i) for i in range(len(subplot.texts)) if i > 0]
				if len(subplot.texts) == 1:
					del self.longPlotAnnot
					self.longPlotAnnot = subplot.texts[0]
				else:
					del self.longPlotAnnot
					self.longPlotAnnot = subplot.annotate("debug", xy=(15, 15), xycoords='data',
					                                      textcoords="offset pixels",
					                                      bbox=dict(boxstyle="round", fc="w"))
					self.longPlotAnnot.set_visible(False)

				found = False
				for collection in subplot.collections[:]:
					if isinstance(collection, PathCollection):
						del self.longPlotHoverPoint
						self.longPlotHoverPoint = collection
						found = True
						continue
					if isinstance(collection, PathCollection) and found:
						subplot.collections.remove(collection)

				if not found:
					del self.longPlotHoverPoint
					xmin, xmax = subplot.get_xlim()
					x = (xmin + xmax) / 2.
					ymin, ymax = subplot.get_ylim()
					y = (ymin + ymax) / 2.
					self.longPlotHoverPoint = subplot.scatter(x, y, 20, 'red')
					self.longPlotHoverPoint.set_visible(False)

				return self.longPlotAnnot, self.longPlotHoverPoint

			if plotNo == TuPlot.CrossSection1D:
				if len(subplot.texts) > 1:
					[subplot.text.pop(i) for i in range(len(subplot.texts)) if i > 0]
				if len(subplot.texts) == 1:
					del self.crossSectionAnnot
					self.crossSectionAnnot = subplot.texts[0]
				else:
					del self.crossSectionAnnot
					self.crossSectionAnnot = subplot.annotate("debug", xy=(15, 15), xycoords='data',
					                                          textcoords="offset pixels",
					                                          bbox=dict(boxstyle="round", fc="w"))
					self.crossSectionAnnot.set_visible(False)

				found = False
				for collection in subplot.collections[:]:
					if isinstance(collection, PathCollection):
						del self.crossSectionHoverPoint
						self.crossSectionHoverPoint = collection
						found = True
						continue
					if isinstance(collection, PathCollection) and found:
						subplot.collections.remove(collection)

				if not found:
					del self.crossSectionHoverPoint
					xmin, xmax = subplot.get_xlim()
					x = (xmin + xmax) / 2.
					ymin, ymax = subplot.get_ylim()
					y = (ymin + ymax) / 2.
					self.crossSectionHoverPoint = subplot.scatter(x, y, 20, 'red')
					self.crossSectionHoverPoint.set_visible(False)

				return self.crossSectionAnnot, self.crossSectionHoverPoint

			if plotNo == TuPlot.VerticalProfile:
				if len(subplot.texts) > 1:
					[subplot.text.pop(i) for i in range(len(subplot.texts)) if i > 0]
				if len(subplot.texts) == 1:
					del self.verticalProfileAnnot
					self.verticalProfileAnnot = subplot.texts[0]
				else:
					del self.verticalProfileAnnot
					self.verticalProfileAnnot = subplot.annotate("debug", xy=(15, 15), xycoords='data',
					                                          textcoords="offset pixels",
					                                          bbox=dict(boxstyle="round", fc="w"))
					self.verticalProfileAnnot.set_visible(False)

				found = False
				for collection in subplot.collections[:]:
					if isinstance(collection, PathCollection):
						del self.verticalProfileHoverPoint
						self.verticalProfileHoverPoint = collection
						found = True
						continue
					if isinstance(collection, PathCollection) and found:
						subplot.collections.remove(collection)

				if not found:
					del self.verticalProfileHoverPoint
					xmin, xmax = subplot.get_xlim()
					x = (xmin + xmax) / 2.
					ymin, ymax = subplot.get_ylim()
					y = (ymin + ymax) / 2.
					self.verticalProfileHoverPoint = subplot.scatter(x, y, 20, 'red')
					self.verticalProfileHoverPoint.set_visible(False)

				return self.verticalProfileAnnot, self.verticalProfileHoverPoint
		elif axisNo == 2:
			subplot2 = self.getSecondaryAxis(plotNo, create=False)
			if subplot2 is None:
				return None, None

			if plotNo == TuPlot.TimeSeries:
				if len(subplot2.texts) > 1:
					[subplot2.text.pop(i) for i in range(len(subplot2.texts)) if i > 0]
				if len(subplot2.texts) == 1:
					del self.timeSeriesAnnot2
					self.timeSeriesAnnot2 = subplot2.texts[0]
				else:
					del self.timeSeriesAnnot2
					self.timeSeriesAnnot2 = subplot2.annotate("debug", xy=(15, 15), xycoords='data',
					                                          textcoords="offset pixels",
					                                          bbox=dict(boxstyle="round", fc="w"))
					self.timeSeriesAnnot2.set_visible(False)

				found = False
				for collection in subplot2.collections[:]:
					if isinstance(collection, PathCollection):
						del self.timeSeriesHoverPoint2
						self.timeSeriesHoverPoint2 = collection
						found = True
						continue
					if isinstance(collection, PathCollection) and found:
						subplot2.collections.remove(collection)

				if not found:
					del self.timeSeriesHoverPoint2
					xmin, xmax = subplot2.get_xlim()
					x = (xmin + xmax) / 2.
					ymin, ymax = subplot2.get_ylim()
					y = (ymin + ymax) / 2.
					self.timeSeriesHoverPoint2 = subplot2.scatter(x, y, 20, 'red')
					self.timeSeriesHoverPoint2.set_visible(False)

				return self.timeSeriesAnnot2, self.timeSeriesHoverPoint2

			if plotNo == TuPlot.CrossSection:
				if len(subplot2.texts) > 1:
					[subplot2.text.pop(i) for i in range(len(subplot2.texts)) if i > 0]
				if len(subplot2.texts) == 1:
					del self.longPlotAnnot2
					self.longPlotAnnot2 = subplot2.texts[0]
				else:
					del self.longPlotAnnot2
					self.longPlotAnnot2 = subplot2.annotate("debug", xy=(15, 15), xycoords='data',
					                                        textcoords="offset pixels",
					                                        bbox=dict(boxstyle="round", fc="w"))
					self.longPlotAnnot2.set_visible(False)

				found = False
				for collection in subplot2.collections[:]:
					if isinstance(collection, PathCollection):
						del self.longPlotHoverPoint2
						self.longPlotHoverPoint2 = collection
						found = True
						continue
					if isinstance(collection, PathCollection) and found:
						subplot2.collections.remove(collection)

				if not found:
					del self.longPlotHoverPoint2
					xmin, xmax = subplot2.get_xlim()
					x = (xmin + xmax) / 2.
					ymin, ymax = subplot2.get_ylim()
					y = (ymin + ymax) / 2.
					self.longPlotHoverPoint2 = subplot2.scatter(x, y, 20, 'red')
					self.longPlotHoverPoint2.set_visible(False)

				return self.longPlotAnnot2, self.longPlotHoverPoint2

			if plotNo == TuPlot.VerticalProfile:
				if len(subplot2.texts) > 1:
					[subplot2.text.pop(i) for i in range(len(subplot2.texts)) if i > 0]
				if len(subplot2.texts) == 1:
					del self.verticalProfileAnnot2
					self.verticalProfileAnnot2 = subplot2.texts[0]
				else:
					del self.verticalProfileAnnot2
					self.verticalProfileAnnot2 = subplot2.annotate("debug", xy=(15, 15), xycoords='data',
					                                          textcoords="offset pixels",
					                                          bbox=dict(boxstyle="round", fc="w"))
					self.verticalProfileAnnot2.set_visible(False)

				found = False
				for collection in subplot2.collections[:]:
					if isinstance(collection, PathCollection):
						del self.verticalProfileHoverPoint2
						self.verticalProfileHoverPoint2 = collection
						found = True
						continue
					if isinstance(collection, PathCollection) and found:
						subplot2.collections.remove(collection)

				if not found:
					del self.verticalProfileHoverPoint2
					xmin, xmax = subplot2.get_xlim()
					x = (xmin + xmax) / 2.
					ymin, ymax = subplot2.get_ylim()
					y = (ymin + ymax) / 2.
					self.verticalProfileHoverPoint2 = subplot2.scatter(x, y, 20, 'red')
					self.verticalProfileHoverPoint2.set_visible(False)

				return self.verticalProfileAnnot2, self.verticalProfileHoverPoint2


	def indata(self, artist, a, ax, ax_event, event):
		if ax is None or ax_event is None:
			return []
		if isinstance(artist, PolyCollection):
			contains, _ = artist.contains(event)
			return contains
		trans = ax.transData.transform
		trans_event = ax_event.transData.transform
		if isinstance(artist, plt.Line2D):
			d = list(zip(*artist.get_data()))
			if artist.get_xdata().any():
				if isinstance(artist.get_xdata()[0], datetime):
					d = [(date2num(x[0]), x[1]) for x in d]
			return [x for x in d if np.isclose(trans(x), trans_event(a), atol=5).all()]
		elif isinstance(artist, Polygon):
			# return [x for x in artist.get_xy() if np.isclose(trans(x), trans_event(a), atol=5).all()]
			contains, _ = artist.contains(event)
			if contains:
				return contains
			else:
				return [x for x in artist.get_xy() if np.isclose(trans(x), trans_event(a), atol=5).all()]

		return []

	def closest_point(self, artist, a, ax, ax_event, point_xy_ = None, dist_ = None):
		if ax is None or ax_event is None:
			return None
		trans = ax.transData.transform
		trans_event = ax_event.transData.transform
		if isinstance(artist, plt.Line2D):
			d = list(zip(*artist.get_data()))
			if artist.get_xdata().any():
				if isinstance(artist.get_xdata()[0], datetime):
					d = [(date2num(x[0]), x[1]) for x in d]
			close_points = np.array([(np.absolute(np.array(x) - np.array(a)).sum(), i) for i, x in enumerate(d) if np.isclose(trans(x), trans_event(a), atol=5).all()])
			i = np.where(close_points[:,0] == np.amin(close_points[:,0]))[0][0]
			point_xy = list(zip(*artist.get_data()))[int(close_points[:,1][i])]
			if isinstance(point_xy[0], datetime):
				pxy = (date2num(point_xy[0]), point_xy[1])
				dist = ((trans(pxy)[0] - trans_event(a)[0]) ** 2 + (trans(pxy)[1] - trans_event(a)[1]) ** 2) ** 0.5
			else:
				dist = ((trans(point_xy)[0] - trans_event(a)[0]) ** 2 + (trans(point_xy)[1] - trans_event(a)[1]) ** 2) ** 0.5
			if dist_ is None or point_xy_ is None or dist < dist_:
				return point_xy, dist
			else:
				return point_xy_, dist_
		elif isinstance(artist, Polygon):
			close_points = np.array(
				[(np.absolute(np.array(x) - np.array(a)).sum(), i) for i, x in enumerate(artist.get_xy())
				 if np.isclose(trans(x), trans_event(a), atol=5).all()])
			if not close_points.any():
				return point_xy_, dist_
			i = np.where(close_points[:, 0] == np.amin(close_points[:, 0]))[0][0]
			point_xy = artist.get_xy()[int(close_points[:, 1][i])]
			dist = ((trans(point_xy)[0] - trans_event(a)[0]) ** 2 + (trans(point_xy)[1] - trans_event(a)[1]) ** 2) ** 0.5
			if dist_ is None or point_xy_ is None or dist < dist_:
				return point_xy, dist
			else:
				return point_xy_, dist_

		return None

	def update_annotation(self, pos_xy, annotation, point, artist, ax, fig, event, dist):
		if pos_xy is None:
			return
		trans = ax.transData.transform
		transInv = ax.transData.inverted().transform
		annotation.xy = pos_xy
		point.set_zorder(100)
		if isinstance(artist, plt.Line2D):
			if isinstance(pos_xy[0], datetime):
				point.set_offsets([[date2num(pos_xy[0]), pos_xy[1]]])
				text = self.tuView.tuResults._dateFormat.format(pos_xy[0])
			else:
				point.set_offsets([pos_xy])
				text = '{0:.3f}'.format(pos_xy[0])
			text = '{0}, {1:.3f}'.format(text, pos_xy[-1])
			if isinstance(artist, plt.Line2D):
				annotation.get_bbox_patch().set_facecolor(artist.get_color())
			elif isinstance(artist, Polygon):
				annotation.get_bbox_patch().set_facecolor('0.9')
		elif type(artist) == PolyCollection:
			_, ind = artist.contains(event)
			if ind:
				z = artist.get_array()[ind['ind'][0]]
				text = '{0:.3f}'.format(z)
				annotation.get_bbox_patch().set_facecolor(artist.cmap(self.tuPlot3D.colSpec['norm'](z)))
			else:
				return
		elif isinstance(artist, Polygon):
			point.set_offsets([pos_xy])
			if type(dist) == int and dist == 5:
				try:
					text = artist.channel_id if artist.channel_id is not None else ''
				except AttributeError:
					text = ''
			else:
				text = '{0:.3f}, {1:.3f}'.format(*pos_xy[0:2])
			annotation.get_bbox_patch().set_facecolor('0.9')
		else:
			return

		annotation.set_text(text)
		annotation.get_bbox_patch().set_alpha(0.3)
		annotation.xyann = (10., 10.)
		vis = annotation.get_visible()
		annotation.set_visible(True)
		annotation.draw(fig.canvas.renderer)
		xy = annotation.xy
		if isinstance(xy[0], datetime):
			xy = (date2num(xy[0]), xy[1])
		if trans(xy)[0] + annotation.get_bbox_patch().get_width() + 15 > fig.bbox.width:
			annotation.xyann = (-annotation.get_bbox_patch().get_width() - 7, annotation.xyann[1])
		if trans(xy)[1] + annotation.get_bbox_patch().get_height() + 15 > fig.bbox.height:
			annotation.xyann = (annotation.xyann[0], -annotation.get_bbox_patch().get_height() - 7)
		annotation.set_visible(vis)

	def hover(self, event, plotNo):
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		xlim = subplot.get_xlim()
		ylim = subplot.get_ylim()
		annotation, point = self.getAnnotation(plotNo, 1)
		subplot.set_xlim(xlim)
		subplot.set_ylim(ylim)

		subplot2 = self.getSecondaryAxis(plotNo, create=False)
		annotation2, point2 = None, None
		xlim2, ylim2 = None, None
		if subplot2:
			xlim2 = subplot2.get_xlim()
			ylim2 = subplot2.get_ylim()
			annotation2, point2 = self.getAnnotation(plotNo, 2)
			subplot2.set_xlim(xlim2)
			subplot2.set_ylim(ylim2)

		found = False
		if event.inaxes == subplot or event.inaxes == subplot2:
			ax_event = subplot if event.inaxes == subplot else subplot2
			artists, labels = subplot.get_legend_handles_labels()
			if subplot2 is not None:
				artists2, labels2 = subplot2.get_legend_handles_labels()
				artists.extend(artists2)
				labels.extend(labels2)
			for artist in artists:
				if not isinstance(artist, PathCollection) and not isinstance(artist, plt.Text):
					if artist.axes == subplot:
						ax = subplot
						annot = annotation
						p = point
						annot_off = annotation2
						p_off = point2
					elif artist.axes == subplot2 and subplot2 is not None:
						ax = subplot2
						annot = annotation2
						p = point2
						annot_off = annotation
						p_off = point
					else:
						continue
					if self.indata(artist, [event.xdata, event.ydata], ax, ax_event, event):
						found = True
						if type(artist) == PolyCollection:
							closest_point = (event.xdata, event.ydata)
							if artist.axes != ax_event:
								closest_point = ax_event.transData.transform(closest_point)
								closest_point = subplot.transData.inverted().transform(closest_point)
							dist = 5
						else:
							closest_point, dist = None, None
							if type(artist) == Polygon or type(artist) == TuflowPipe:
								closest_point = (event.xdata, event.ydata)
								if artist.axes != ax_event:
									closest_point = ax_event.transData.transform(closest_point)
									closest_point = subplot.transData.inverted().transform(closest_point)
								dist = 5
							closest_point, dist = self.closest_point(artist, [event.xdata, event.ydata], ax, ax_event, closest_point, dist)
						self.update_annotation(closest_point, annot, p, artist, ax, figure, event, dist)
						annot.set_visible(True)
						if type(artist) == PolyCollection:
							p.set_visible(False)
						elif (type(artist) == Polygon or type(artist) == TuflowPipe) and type(dist) == int and dist == 5:
							p.set_visible(False)
						else:
							p.set_visible(True)
						if ax.texts:
							figure.texts.append(ax.texts.pop())
						if annot_off is not None:
							annot_off.set_visible(False)
						if p_off is not None:
							p_off.set_visible(False)

						figure.canvas.draw_idle()

						if dist < 3:
							return

		if not found:
			annotation.set_visible(False)
			point.set_visible(False)
			if annotation2 is not None:
				annotation2.set_visible(False)
			if point2 is not None:
				point2.set_visible(False)

			figure.canvas.draw_idle()

	def updateCursorMarker(self, event):
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists_, labels_, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(TuPlot.CrossSection)
		subplot2 = self.getSecondaryAxis(TuPlot.CrossSection, create=False)

		if event.inaxes == subplot or (subplot2 is not None and event.inaxes == subplot2):
			ax = event.inaxes
			artists, labels = subplot.get_legend_handles_labels()
			if subplot2 is not None:
				a, lab = subplot2.get_legend_handles_labels()
				artists.extend(a)
				labels.extend(lab)
			for i, artist in enumerate(artists):
				if artist in artists_[0]:
					j = artists_[0].index(artist)
					label = labels_[0][j]
					if type(artist) == PolyCollection:
						label = '{0}__curtain__'.format(label)
					self.cursorMarker.updateTracker(label, event.xdata)
				elif artist in artists_[1]:
					j = artists_[1].index(artist)
					label = labels_[1][j]
					if type(artist) == PolyCollection:
						label = '{0}__curtain__'.format(label)
					self.cursorMarker.updateTracker(label, event.xdata)
		else:
			self.cursorMarker.setVisible(False)


class TuflowPipe(Polygon):

	def __init__(self, xy, closed=True, **kwargs):
		Polygon.__init__(self, xy, closed, **kwargs)
		self.channel_id = None


class CursorMarker:

	def __init__(self, canvas):
		self.ids = {}
		self.canvas = canvas

	def addTracker(self, id_, artist, geom):
		geoms = [x for k, (_, x, _) in self.ids.items() if x == geom]
		if not geoms:
			self.ids[id_] = (artist, geom, None)

	def removeTracker(self, id_):
		if id_ in self.ids:
			_, _, marker = self.ids[id_]
			if self.canvas is not None:
				self.canvas.scene().removeItem(marker)
			del self.ids[id_]

	def clear(self):
		for id in list(self.ids.keys()):
			self.removeTracker(id)

	def updateTracker(self, id_, plot_x):
		if self.canvas is None:
			return
		if id_ in self.ids:
			artist, geom, marker = self.ids[id_]
			p = self.transform(artist, geom, plot_x)
			if marker is None:
				marker = QgsVertexMarker(self.canvas)
				marker.setColor(Qt.red)
				marker.setFillColor(Qt.red)
				marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
				marker.setIconSize(10)
				self.ids[id_] = (artist, geom, marker)
			if p is None:
				marker.setVisible(False)
			else:
				marker.setCenter(p)
				marker.setVisible(True)

	def setVisible(self, b):
		if self.canvas is None:
			return
		for id_, (_, _, marker) in self.ids.items():
			if marker is not None:
				marker.setVisible(b)

	def transform(self, artist, geom, plot_x):
		if isinstance(artist, matplotlib.lines.Line2D):
			xdata = artist.get_data()[0]
			min_ = min(xdata)
			max_ = max(xdata)
		elif isinstance(artist, PolyCollection):
			xdata = getPolyCollectionData(artist, 'x')
			min_ = np.nanmin(xdata)
			max_ = np.nanmax(xdata)
		else:
			return

		if min_ <= plot_x <= max_:
			s = (plot_x - min_) / (max_ - min_)
			dist = geom.length() * s
			return geom.interpolate(dist).asPoint()