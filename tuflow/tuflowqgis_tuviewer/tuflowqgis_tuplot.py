from datetime import datetime, timedelta
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets  import *
import sys
import os
import matplotlib
import numpy as np
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
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplottoolbar import TuPlotToolbar
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplotselection import TuPlotSelection
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turubberband import TuRubberBand
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuflowline import TuFlowLine
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot2d import TuPlot2D
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot1d import TuPlot1D
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuuserplotdata import TuUserPlotDataManager
from tuflow.tuflowqgis_library import applyMatplotLibArtist, getMean, roundSeconds


class TuPlot():
	"""
	Class for plotting.
	
	"""
	
	def __init__(self, TuView):
		self.tuView = TuView
		self.iface = self.tuView.iface
		self.canvas = self.tuView.canvas
		
		# Initialise figures
		# time series
		self.layoutTimeSeries = self.tuView.TimeSeriesFrame.layout()
		self.figTimeSeries, self.subplotTimeSeries = plt.subplots()
		self.plotWidgetTimeSeries = FigureCanvasQTAgg(self.figTimeSeries)
		
		# long plot
		self.layoutLongPlot = self.tuView.LongPlotFrame.layout()
		self.figLongPlot, self.subplotLongPlot = plt.subplots()
		self.plotWidgetLongPlot = FigureCanvasQTAgg(self.figLongPlot)
		
		# cross section
		self.layoutCrossSection = self.tuView.CrossSectionFrame.layout()
		self.figCrossSection, self.subplotCrossSection = plt.subplots()
		self.plotWidgetCrossSection = FigureCanvasQTAgg(self.figCrossSection)
		
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
		self.frozenCSProperties = {}  # dictionary object to save user defined names and styles
		self.frozenCSAxisLabels = {}  # dictionary object to save user defined axis labels
		
		# Draw Plots
		self.initialisePlot(0)  # time series
		
		self.initialisePlot(1)  # long profile / cross section
		
		self.initialisePlot(2)  # cross section editor
		
		# plot toolbar class
		self.tuPlotToolbar = TuPlotToolbar(self)
		
		# user selection plot class
		self.tuPlotSelection = TuPlotSelection(self)
		
		# rubberband class plot class
		self.tuRubberBand = TuRubberBand(self)
		self.tuFlowLine = TuFlowLine(self)
		
		# TuPlot2D class
		self.tuPlot2D = TuPlot2D(self)
		
		# TuPlot1D class
		self.tuPlot1D = TuPlot1D(self)
		
		# User Plot Data Manager
		self.userPlotData = TuUserPlotDataManager()
	
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
			    (self.yAxisLimitsCrossSectionFirst, self.yAxisLimitsCrossSectionSecond)]
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
		
		return parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabel,  xAxisLabel, xAxisLimits, yAxisLimits
	
	def initialisePlot(self, plotNo):
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
		rect.set_facecolor((0.9, 0.9, 0.9))
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
		
		axe1.grid()
		axe1.tick_params(axis="both", which="major", direction="out", length=10, width=1, bottom=True, top=False,
		                 left=True, right=False)
		axe1.minorticks_on()
		axe1.tick_params(axis="both", which="minor", direction="out", length=5, width=1, bottom=True, top=False,
		                 left=True, right=False)
		
		return True
	
	def clearAllPlots(self):
		"""
		Clear all plots.

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		for i in range(3):
			self.clearPlot(i, clear_rubberband=True)
		
		self.tuPlot2D.plotSelectionPointFeat = []
		self.tuPlot2D.plotSelectionLineFeat = []
		self.tuPlot2D.plotSelectionFlowFeat = []
		
		return True
	
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
		if plotNo == 0:
			self.tuPlot2D.resetMultiPointCount()
			self.tuPlot2D.resetMultiFlowLineCount()
		elif plotNo == 1:
			self.clearedLongPlot = True
			self.tuPlot2D.resetMultiLineCount()
		
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
				if plotNo == 0:
					self.tuRubberBand.clearMarkers()
					self.tuFlowLine.clearRubberBand()
				elif plotNo == 1:
					self.tuRubberBand.clearRubberBand()
		if 'clear_selection' in kwargs.keys():
			if kwargs['clear_selection']:
				if plotNo == 0:
					self.tuPlot2D.plotSelectionPointFeat = []
					self.tuPlot2D.plotSelectionFlowFeat = []
				elif plotNo == 1:
					self.tuPlot2D.plotSelectionLineFeat = []
		
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
		i = True
		while i is not None:
			i = labels[0].index('Current Time') if 'Current Time' in labels[0] else None  # index for individual lists
			lab = labels[0] + labels[1]
			j = lab.index('Current Time') if 'Current Time' in lab else None  # index in all lines on figure
			if i or i == 0:
				artists[0].pop(i)
				labels[0].pop(i)
				del subplot.lines[j]
				subplot.legend_ = None
		
		if self.tuView.cbShowCurrentTime.isChecked() or showCurrentTime:

			# get current Time
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
			
			# get current Y-Axis limits
			if not self.tuView.tuMenuBar.freezeAxisYLimits_action.isChecked():
				subplot.relim()
				subplot.autoscale()
				y = subplot.get_ylim()
			else:
				y = yAxisLimits[0][0]

			# add to plot
			label, artistTemplates = self.getNewPlotProperties(plotNo, ['Current Time'], rtype='lines')
			a, = subplot.plot(x, y, color='red', linewidth=2, label=label[0])
			applyMatplotLibArtist(a, artistTemplates[0])
			artists[0].append(a)
			labels[0].append('Current Time')
			if self.tuView.tuMenuBar.freezeAxisXLimits_action.isChecked():
				subplot.set_xbound(xAxisLimits[0][0])
			if self.tuView.tuMenuBar.freezeAxisYLimits_action.isChecked():
				subplot.set_ybound(yAxisLimits[0][0])
			else:
				subplot.set_ybound(y)
			subplot.legend_ = None
			
		return True
	
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

	def setAxisNames(self, plotNo, types):
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
		units = {
			'level': ('m RL', 'ft RL', ''),
			'max water level': ('m RL', 'ft RL', ''),
			'bed level': ('m RL', 'ft RL', ''),
			'left bank obvert': ('m RL', 'ft RL', ''),
			'right bank obvert': ('m RL', 'ft RL', ''),
			'us levels': ('m RL', 'ft RL', ''),
			'ds levels': ('m RL', 'ft RL', ''),
			'bed elevation': ('m RL', 'ft RL', ''),
			'flow': ('m$^3$/s', 'ft$^3$/s', ''),
			'2d flow': ('m$^3$/s', 'ft$^3$/s', ''),
			'atmospheric pressure': ('hPA', 'hPa', ''),
			'bed shear stress': ('N/m$^2$', 'lbf/ft$^2$', 'pdl/ft%^2$', ''),
			'depth': ('m', 'ft', ''),
			'velocity': ('m/s', 'ft/s', ''),
			'cumulative infiltration': ('mm', 'inches', ''),
			'depth to groundwater': ('m', 'ft', ''),
			'water level': ('m RL', 'ft RL', ''),
			'infiltration rate': ('mm/hr', 'in/hr', ''),
			'mb': ('%', '%', ''),
			'mb1': ('%', '%', ''),
			'mb2': ('%', '%', ''),
			'unit flow': ('m%^2$/s', 'ft$^2$/s', ''),
			'cumulative rainfall': ('mm', 'inches', ''),
			'rfml': ('mm', 'inches', ''),
			'rainfall rate': ('mm/hr', 'in/hr', ''),
			'stream power': ('W/m$^2%', 'lbf/ft$^2$', 'pdl/ft%^2$', ''),
			'sink': ('m$^3$/s', 'ft$^3$/s', ''),
			'source': ('m$^3$/s', 'ft$^3$/s', ''),
			'flow area': ('m$^2$', 'ft$^2$', ''),
			'time of max h': ('hrs', 'hrs', '')
		}
		
		shortNames = {
			'flow': 'Q',
			'2d flow': 'Q',
			'bed shear stress': 'BSS',
			'depth': 'd',
			'velocity': 'V',
			'cumulative infiltration': 'CI',
			'water level': 'h',
			'max water level': 'h',
			'level': 'h',
			'bed level': 'h',
			'us levels': 'h',
			'ds levels': 'h',
			'infiltration rate': 'IR',
			'mb': 'MB',
			'mb1': 'MB1',
			'mb2': 'MB2',
			'unit flow': 'q',
			'cumulative rainfall': 'CR',
			'rfml': 'RFML',
			'rainfall rate': 'RR',
			'stream power': 'SP',
			'flow area': 'QA',
			'time of max h': 't',
			'losses': 'LC',
			'flow regime': 'F'
		}
		
		if self.tuView.tuMenuBar.freezeAxisLabels_action.isChecked():
			xAxisLabel = subplot.get_xlabel()
			yAxisLabelNewFirst = subplot.get_ylabel()
			if isSecondaryAxis[0]:
				subplot2 = self.getSecondaryAxis(plotNo)
				yAxisLabelNewSecond = subplot2.get_ylabel()
			else:
				yAxisLabelNewSecond = ''
			return xAxisLabel, yAxisLabelNewFirst, yAxisLabelNewSecond

		# determine units i.e. metric, imperial, or unknown / blank
		if self.canvas.mapUnits() == QgsUnitTypes.DistanceMeters or self.canvas.mapUnits() == QgsUnitTypes.DistanceKilometers or \
				self.canvas.mapUnits() == QgsUnitTypes.DistanceCentimeters or self.canvas.mapUnits() == QgsUnitTypes.DistanceMillimeters:  # metric
			u, m = 0, 'm'
		elif self.canvas.mapUnits() == QgsUnitTypes.DistanceFeet or self.canvas.mapUnits() == QgsUnitTypes.DistanceNauticalMiles or \
				self.canvas.mapUnits() == QgsUnitTypes.DistanceYards or self.canvas.mapUnits() == QgsUnitTypes.DistanceMiles:  # imperial
			u, m = 1, 'ft'
		else:  # use blank
			u, m = -1, ''
		
		# get x axis name
		xAxisLabel = ''
		if plotNo == 0:
			if self.tuView.tuOptions.xAxisDates:
				xAxisLabel = 'Date'
			else:
				xAxisLabel = 'Time (hr)'
		elif plotNo == 1:
			xAxisLabel = 'Offset ({0})'.format(m)
		
		# get y axis name
		yAxisLabelNewFirst = ''
		yAxisLabelNewSecond = ''
		for i, name in enumerate(types):
			if name not in self.tuView.tuResults.secondaryAxisTypes:
				
				# remove '_1d' from name of 1d types
				if '_1d' in name:
					name = name.strip('_1d')
				
				# first axis label
				if name.lower() in shortNames.keys():
					shortName = shortNames[name.lower()]
					if shortName not in yAxisLabelTypes[0]:
						yAxisLabelTypes[0].append(shortName)  # add to list of labels so no double ups
				unitNew = units[name.lower()][u] if name.lower() in units.keys() else ''
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
				if name.lower() in shortNames.keys():
					shortName = shortNames[name.lower()]
					if shortName not in yAxisLabelTypes[1]:
						yAxisLabelTypes[1].append(shortName)
				unitNew = units[name.lower()][u] if name.lower() in units.keys() else ''
				if not unit[1]:
					unit[1].append(unitNew)
				else:
					if unitNew:
						if unitNew != unit[1][0]:
							unit[1][0] = ''
		
		# set final axis label for first axis
		for i, label in enumerate(yAxisLabelTypes[0]):
			if i == 0:
				yAxisLabelNewFirst = '{0}'.format(label)
			else:
				yAxisLabelNewFirst = '{0}, {1}'.format(yAxisLabelNewFirst, label)
		if unit[0]:
			if unit[0][0]:
				yAxisLabelNewFirst = '{0} ({1})'.format(yAxisLabelNewFirst, unit[0][0])
		
		# set final axis label for second axis
		for i, label in enumerate(yAxisLabelTypes[1]):
			if i == 0:
				yAxisLabelNewSecond = '{0}'.format(label)
			else:
				yAxisLabelNewSecond = '{0}, {1}'.format(yAxisLabelNewSecond, label)
		if unit[1]:
			if unit[1][0]:
				yAxisLabelNewSecond = '{0} ({1})'.format(yAxisLabelNewSecond, unit[1][0])
		
		return xAxisLabel, yAxisLabelNewFirst, yAxisLabelNewSecond
	
	def getSecondaryAxis(self, plotNo):
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
			isSecondaryAxis[0] = True
			if plotNo == 0:
				self.axis2TimeSeries = subplot.twinx()
				return self.axis2TimeSeries
			elif plotNo == 1:
				self.axis2LongPlot = subplot.twinx()
				return self.axis2LongPlot
		else:
			if plotNo == 0:
				return self.axis2TimeSeries
			elif plotNo == 1:
				return self.axis2LongPlot
			
	def reorderByAxis(self, types, data, label, plotAsPoints, plotAsPatch, flowRegime):
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

		for i, rtype in enumerate(types):
			if len(data[i][0]) > 0:
				if rtype in self.tuView.tuResults.secondaryAxisTypes:
					types2.append(rtype)
					data2.append(data[i])
					label2.append(label[i])
					plotAsPoints2.append(plotAsPoints[i])
					plotAsPatch2.append(plotAsPatch[i])
					flowRegime2.append(flowRegime[i])
				else:
					types1.append(rtype)
					data1.append(data[i])
					label1.append(label[i])
					plotAsPoints1.append(plotAsPoints[i])
					plotAsPatch1.append(plotAsPatch[i])
					flowRegime1.append(flowRegime[i])
		
		typesOrdered = types1 + types2
		dataOrdered = data1 + data2
		labelOrdered = label1 + label2
		plotAsPointsOrdered = plotAsPoints1 + plotAsPoints2
		plotAsPatchOrdered = plotAsPatch1 + plotAsPatch2
		flowRegimeOrdered = flowRegime1 + flowRegime2
		
		return typesOrdered, dataOrdered, labelOrdered, plotAsPointsOrdered, plotAsPatchOrdered, flowRegimeOrdered
	
	def drawPlot(self, plotNo, data, label, types, **kwargs):
		"""
		Will draw the plot based on plot enumerator, x y data, and labels

		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:param data: list all data -> list x, y -> list axis data -> float value e.g. [ [ [ x1, x2, .. ], [ y1, y2, .. ] ] ]
		:param label: list - str
		:return: bool -> True for successful, False for unsuccessful
		"""
		#import pydevd_pycharm
		#pydevd_pycharm.settrace('localhost', port=53100, stdoutToServer=True, stderrToServer=True)
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
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
			types, data, label, plotAsPoints, plotAsPatch, flowRegime = self.reorderByAxis(types, data, label,
			                                                                               plotAsPoints, plotAsPatch,
			                                                                               flowRegime)  # orders the data by axis (axis 1 then axis 2)
			labelsOriginal = label[:]  # save a copy as original labels so it can be referenced later
			label, artistTemplates = self.getNewPlotProperties(plotNo, label, rtype='lines')  # check if there are any new names and styling
		
		# Get data
		if not refreshOnly:  # only if it's not refresh only
			for i in range(len(data)):
				
				# determine which axis it belongs on
				rtype = types[i]
				if rtype in self.tuView.tuResults.secondaryAxisTypes:
					axis = 2
					#if len(subplot.get_shared_x_axes().get_siblings(subplot)) < 2:
					subplot2 = self.getSecondaryAxis(plotNo)
					if export:  # override axis object for exporting
						subplot2 = subplot.twinx()
					if not isSecondaryAxis[0]:
						isSecondaryAxis[0] = True
						isSecondaryAxisLocal = True
				else:
					axis = 1
				
				# data
				if self.tuView.tuOptions.xAxisDates and plotNo == 0:
					if data[i]:
						if type(data[i][0]) is np.ndarray:
							if type(data[i][0][0]) is datetime:
								x = data[i][0]
							else:
								x = self.convertTimeToDate(data[i][0])
						else:
							x = self.convertTimeToDate(data[i][0])
				else:
					x = data[i][0]
				y = data[i][1]
				
				# add data to plot
				if axis == 1:
					if plotAsPatch is None or not plotAsPatch[i]:  # normal X, Y data
						if plotAsPoints is None or not plotAsPoints[i]:  # plot as line
							a, = subplot.plot(x, y, label=label[i])
							applyMatplotLibArtist(a, artistTemplates[i])
						else:  # plot as points only
							if flowRegime[i]: y = self.convertFlowRegimeToInt(y)
							a, = subplot.plot(x, y, marker='o', linestyle='None', label=label[i])
							applyMatplotLibArtist(a, artistTemplates[i])
						if not export:
							artists[0].append(a)
							labels[0].append(labelsOriginal[i])
						#subplot.hold(True)
					else:  # plot as patch i.e. culvert
						for verts in x:
							if verts:
								poly = Polygon(verts, facecolor='0.9', edgecolor='0.5', label=label[i])
								subplot.add_patch(poly)
				elif axis == 2:
					if plotAsPatch is None or not plotAsPatch[i]:  # normal X, Y data
						if plotAsPoints is None or not plotAsPoints[i]:
							a, = subplot2.plot(x, y, marker='x', label=label[i])
							applyMatplotLibArtist(a, artistTemplates[i])
						else:
							if flowRegime[i]: y = self.convertFlowRegimeToInt(y)
							a, = subplot2.plot(x, y, marker='o', linestyle='None', label=label[i])
							applyMatplotLibArtist(a, artistTemplates[i])
						if not export:
							artists[1].append(a)
							labels[1].append(labelsOriginal[i])
						#subplot2.hold(True)
					else:  # plot as patch i.e. culvert
						for verts in x:
							if verts:
								poly = Polygon(verts, facecolor='0.9', edgecolor='0.5', label=label[i])
								subplot2.add_patch(poly)
		
		# get secondary axis if refresh only
		if isSecondaryAxis[0] and refreshOnly:
			subplot2 = self.getSecondaryAxis(plotNo)
		
		# user plot data
		self.plotUserData(plotNo)
		
		# check if show current time is selected
		self.showCurrentTime(plotNo, time=time, show_current_time=showCurrentTime)
		
		# get axis labels
		if data:
			xAxisLabel, yAxisLabelFirst, yAxisLabelSecond = self.setAxisNames(plotNo, types)
			xAxisLabels[0].append(xAxisLabel)
			yAxisLabels[0].append(yAxisLabelFirst)
			yAxisLabels[1].append(yAxisLabelSecond)
			# Get user axis labels
			oldLabels = [xAxisLabel, yAxisLabelFirst, yAxisLabelSecond]
			newLabels = self.getNewPlotProperties(plotNo, oldLabels, rtype='axis labels')
			if newLabels:
				xAxisLabel = newLabels[0]
			if len(newLabels) > 1:
				yAxisLabelFirst = newLabels[1]
			if len(newLabels) > 2:
				yAxisLabelSecond = newLabels[2]

		# draw plot
		if export:
			if len(subplot.get_shared_x_axes().get_siblings(subplot)) < 2:
				subplot2 = None
			self.updateLegend(plotNo, redraw=False, ax=subplot, ax2=subplot2)
		else:
			self.updateLegend(plotNo, redraw=False)
		if data:
			if xAxisLabel:
				subplot.set_xlabel(xAxisLabel)
			if yAxisLabelFirst or yAxisLabelSecond:
				if yAxisLabelFirst:
					subplot.set_ylabel(yAxisLabelFirst)
				if isSecondaryAxis[0]:
					#if not isSecondaryAxisLocal:
					#	subplot2 = self.getSecondaryAxis(plotNo)
					subplot2.set_ylabel(yAxisLabelSecond)
		
		# check if there is user plot data
		userPlotData = False
		for status in [v.status for k, v in sorted(self.userPlotData.datasets.items(), key=lambda x: x[-1].number)]:
			if status:
				userPlotData = True
				break
		isData = False
		if data or userPlotData:
			isData = True

		if isData and self.tuView.tuOptions.xAxisDates and plotNo == 0:
			fmt = mdates.DateFormatter(self.tuView.tuOptions.dateFormat)
			subplot.xaxis.set_major_formatter(fmt)
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
		if self.tuView.tuMenuBar.freezeAxisXLimits_action.isChecked():
			subplot.set_xbound(xLimits)
		if self.tuView.tuMenuBar.freezeAxisYLimits_action.isChecked():
			subplot.set_ybound(yLimits)
			if isSecondaryAxis[0]:
				subplot2.set_ybound(yLimits2)
		if 'Flow Regime_1d' in types:
			if 'Flow Regime_1d' in self.tuView.tuResults.secondaryAxisTypes:
				subplot2.set_ybound((-4, 6))
				subplot2.set_yticks(np.arange(-4, 7, 1))
				subplot2.set_yticks([], minor=True)
				subplot2.set_yticklabels(['A', 'B', 'K', 'L', 'G', 'C', 'D', 'E', 'F', 'H', 'J'])
			else:
				subplot.set_ybound((-4, 6))
				subplot.set_yticks(np.arange(-4, 7, 1))
				subplot.set_yticks([], minor=True)
				subplot.set_yticklabels(['A', 'B', 'K', 'L', 'G', 'C', 'D', 'E', 'F', 'H', 'J'])
		try:
			figure.tight_layout()
		except ValueError:  # something has gone wrong and trying to plot time (hrs) on a date formatted x axis
			pass
			
		if export:
			figure.suptitle(os.path.splitext(os.path.basename(export))[0])
			figure.savefig(export)
			if subplot2 is not None:
				subplot2.cla()
		else:
			if draw:
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
		
		if not plot:
			if update == '1d only':
				self.clearPlot(0, retain_2d=True, retain_flow=True)
			elif update == '1d and 2d only':
				self.clearPlot(0, retain_flow=True)
			else:
				self.clearPlot(0, retain_flow=retainFlow)
		
		if plot.lower() != '1d only' and plot.lower() != 'flow only' and update != '1d only':
			self.tuPlot2D.resetMultiPointCount()
			
			multi = False  # do labels need to be counted up e.g. point 1, point 2
			if len(self.tuRubberBand.markerPoints) + len(self.tuPlot2D.plotSelectionPointFeat) > 1:
				multi = True
			
			for i, point in enumerate(self.tuRubberBand.markerPoints):
				self.tuPlot2D.plotTimeSeriesFromMap(None, QgsPointXY(point), bypass=multi, plot='2D Only',
				                                    draw=draw, time=time, show_current_time=showCurrentTime,
				                                    retain_flow=retainFlow, mesh_rendered=meshRendered,
				                                    plot_active_scalar=plotActiveScalar)
			
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
			self.drawPlot(0, [], None, None, draw=draw, time=time, show_current_time=showCurrentTime)
		
		if plot.lower() != '2d only' and plot.lower() != 'flow only':
			self.tuPlot1D.plot1dTimeSeries(bypass=True, plot='1D Only', draw=draw, time=time, show_current_time=showCurrentTime)
			
		if not plot:
			if self.tuView.tuMenuBar.showMedianEvent_action.isChecked():
				self.showStatResult(0, 'Median')
				
			if self.tuView.tuMenuBar.showMeanEvent_action.isChecked():
				self.showStatResult(0, 'Mean')
				
		if not self.artistsTimeSeriesFirst and not self.artistsCrossSectionSecond:
			if self.userPlotData.datasets:
				self.drawPlot(0, [], None, None, draw=draw, time=time, show_current_time=showCurrentTime)
		
		return True
	
	def updateCrossSectionPlot(self, **kwargs):
		"""
		Update cross section plot. Will go through all rubberbands and selected line features.

		:return: bool -> True for successful, False for unsuccessful
		"""

		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		time = kwargs['time'] if 'time' in kwargs.keys() else None
		meshRendered = kwargs['mesh_rendered'] if 'mesh_rendered' in kwargs.keys() else True
		plotActiveScalar = kwargs['plot_active_scalar'] if 'plot_active_scalar' in kwargs else False
		
		if time is not None:
			if time != 'Maximum' and time != 99999:
				time = '{0:.6f}'.format(kwargs['time']) if 'time' in kwargs.keys() else None
		
		if not plot:
			self.clearPlot(1)
			#self.clearedLongPlot = False
		
		if plot.lower() != '1d only':
			multi = False  # do labels need to be counted up e.g. line 1, line 2
			if len(self.tuRubberBand.rubberBands) > 1:
				multi = True
			elif len(self.tuPlot2D.plotSelectionLineFeat) > 1:
				multi = True
			elif len(self.tuRubberBand.rubberBands) + len(self.tuPlot2D.plotSelectionLineFeat) > 1:
				multi = True
			
			for i, rubberBand in enumerate(self.tuRubberBand.rubberBands):
				if rubberBand.asGeometry() is not None:
					if not rubberBand.asGeometry().isNull():
						geom = rubberBand.asGeometry().asPolyline()
						feat = QgsFeature()
						try:
							feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in geom]))
						except:
							feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x.x(), x.y()) for x in geom]))
						if i == 0:
							self.tuPlot2D.plotCrossSectionFromMap(None, feat, bypass=multi, plot='2D Only', draw=draw,
							                                      time=time, mesh_rendered=meshRendered,
							                                      plot_active_scalar=plotActiveScalar)
						else:
							self.tuPlot2D.plotCrossSectionFromMap(None, feat, bypass=True, plot='2D Only', draw=draw,
							                                      time=time, mesh_rendered=meshRendered,
							                                      plot_active_scalar=plotActiveScalar)
			
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
		
		if plot.lower() != '2d only':
			self.tuPlot1D.plot1dLongPlot(bypass=True, plot='1D Only', draw=draw, time=time)
			
		if not self.artistsLongPlotFirst and not self.artistsLongPlotSecond:
			if self.userPlotData.datasets:
				self.drawPlot(1, [], None, None, draw=draw, time=time)
			
		return True
	
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

		if plotNo is None:
			plotNo = self.tuView.tabWidget.currentIndex()
		
		if plotNo == 0:
			success = self.updateTimeSeriesPlot(update=update, retain_flow=retainFlow, draw=draw, time=time,
			                                    show_current_time=showCurrentTime, mesh_rendered=meshRendered,
			                                    plot_active_scalar=plotActiveScalar)
		elif plotNo == 1:
			success = self.updateCrossSectionPlot(draw=draw, time=time, mesh_rendered=meshRendered,
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
		
		for i in range(2):
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
		
		if plotNo == 0:
			viewToolbar = self.tuPlotToolbar.viewToolbarTimeSeries
		elif plotNo == 1:
			viewToolbar = self.tuPlotToolbar.viewToolbarLongPlot
		elif plotNo == 2:
			viewToolbar = self.tuPlotToolbar.viewToolbarCrossSection
		
		redraw = kwargs['redraw'] if 'redraw' in kwargs.keys() else True
		
		if not viewToolbar.legendMenu.menuAction().isChecked():
			subplot.legend_ = None
			return True

		# get legend labels and artists
		uniqueNames, uniqueNames2, uniqueLines, uniqueLines2 = [], [], [], []
		line, lab = subplot.get_legend_handles_labels()
		# remove duplicates i.e. culvert and pipes only need to appear in legend once
		uniqueNames = []
		uniqueLines = []
		for i, l in enumerate(lab):
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
				if l not in uniqueNames:
					uniqueNames2.append(l)
					uniqueLines2.append(line2[i])
		#labs = [uniqueNames, uniqueNames2]
		#lines = [uniqueLines, uniqueLines2]
	
		# apply
		if viewToolbar.legendUR.isChecked():
			legendPos = 1
		elif viewToolbar.legendUL.isChecked():
			legendPos = 2
		elif viewToolbar.legendLL.isChecked():
			legendPos = 3
		elif viewToolbar.legendLR.isChecked():
			legendPos = 4
		lines = uniqueLines + uniqueLines2
		lab = uniqueNames + uniqueNames2
		if viewToolbar.legendAuto.isChecked():
			subplot.legend(lines, lab)
		else:
			subplot.legend(lines, lab, loc=legendPos)
		if redraw:
			plotWidget.draw()
		
		return True
	
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
		
		if plotNo == 0:
			viewToolbar = self.tuPlotToolbar.viewToolbarTimeSeries
		elif plotNo == 1:
			viewToolbar = self.tuPlotToolbar.viewToolbarLongPlot
		elif plotNo == 2:
			viewToolbar = self.tuPlotToolbar.viewToolbarCrossSection
		
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
			if plotNo == 0:
				self.frozenTSProperties[label] = [labs[i], lines[i]]
			elif plotNo == 1:
				self.frozenLPProperties[label] = [labs[i], lines[i]]
			elif plotNo == 2:
				self.frozenCSProperties[label] = [labs[i], lines[i]]
		if isSecondaryAxis[0]:
			for i, label in enumerate(labels[1]):
				label = label.split('[')[0].strip()  # remove any time values in the label e.g. 'water level [01:00:00]'
				if plotNo == 0:
					self.frozenTSProperties[label] = [labs2[i], lines2[i]]
				elif plotNo == 1:
					self.frozenLPProperties[label] = [labs2[i], lines2[i]]
				elif plotNo == 2:
					self.frozenCSProperties[label] = [labs2[i], lines2[i]]
					
		# store axis labels
		if plotNo == 0:
			if xAxisLabels[0]:
				self.frozenTSAxisLabels[xAxisLabels[0][0]] = xLabel
			if yAxisLabels[0]:
				self.frozenTSAxisLabels[yAxisLabels[0][0]] = yLabel
		elif plotNo == 1:
			if xAxisLabels[0]:
				self.frozenLPAxisLabels[xAxisLabels[0][0]] = xLabel
			if yAxisLabels[0]:
				self.frozenLPAxisLabels[yAxisLabels[0][0]] = yLabel
		elif plotNo == 2:
			if xAxisLabels[0]:
				self.frozenCSAxisLabels[xAxisLabels[0][0]] = xLabel
			if yAxisLabels[0]:
				self.frozenCSAxisLabels[yAxisLabels[0][0]] = yLabel
		if isSecondaryAxis[0]:
			if plotNo == 0:
				if yAxisLabels[1]:
					self.frozenTSAxisLabels[yAxisLabels[1][0]] = yLabel2
			elif plotNo == 1:
				if yAxisLabels[1]:
					self.frozenLPAxisLabels[yAxisLabels[1][0]] = yLabel2
			elif plotNo == 2:
				if yAxisLabels[1]:
					self.frozenCSAxisLabels[yAxisLabels[1][0]] = yLabel2
				
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

	def getNewPlotProperties(self, plotNo, labels, rtype):
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
			for label in labels:
				labelparts = label.split('[')  # remove any time values in the label e.g. 'water level [01:00:00]'
				label = labelparts[0].strip()
				if len(labelparts) > 1:
					labelend = ' [{0}'.format(labelparts[-1])
				else:
					labelend = ''
				if plotNo == 0:
					if label in self.frozenTSProperties.keys():
						newLabels.append(self.frozenTSProperties[label][0])
						newArtists.append(self.frozenTSProperties[label][1])
					else:
						newLabels.append(label)
						newArtists.append(None)
				elif plotNo == 1:
					if label in self.frozenLPProperties.keys():
						newLabels.append(self.frozenLPProperties[label][0])
						newArtists.append(self.frozenLPProperties[label][1])
					else:
						newLabels.append(label + labelend)
						newArtists.append(None)
				elif plotNo == 2:
					if label in self.frozenCSProperties.keys():
						newLabels.append(self.frozenCSProperties[label][0])
						newArtists.append(self.frozenCSProperties[label][1])
					else:
						newLabels.append(label)
						newArtists.append(None)
			
			return newLabels, newArtists
			
		elif rtype == 'axis labels':
			newLabels = []
			for label in labels:
				if plotNo == 0:
					if label in self.frozenTSAxisLabels.keys():
						newLabels.append(self.frozenTSAxisLabels[label])
					else:
						newLabels.append(label)
				elif plotNo == 1:
					if label in self.frozenLPAxisLabels.keys():
						newLabels.append(self.frozenLPAxisLabels[label])
					else:
						newLabels.append(label)
				elif plotNo == 2:
					if label in self.frozenCSAxisLabels.keys():
						newLabels.append(self.frozenCSAxisLabels[label])
					else:
						newLabels.append(label)
			
			return newLabels
	
	def exportCSV(self, plotNo, data, labels, types, outputFolder, fileName):
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

		# convert labels to user defined dataset labels (or default label if user has not changed it)
		newLabels, newArtists = self.getNewPlotProperties(plotNo, labels, rtype='lines')  # newArtists not used for csv
		
		# convert axis names to user defined labels (or default label if user has not changed it)
		xAxisLabel, yAxisLabelFirst, yAxisLabelSecond = self.setAxisNames(plotNo, types)
		oldAxisNames = [xAxisLabel, yAxisLabelFirst, yAxisLabelSecond]
		newAxisNames = self.getNewPlotProperties(plotNo, oldAxisNames, rtype='axis labels')  # only need X axis name for csv
		
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
		
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.plotEnumerator(plotNo)
		
		# get user data in order it appears in the manager
		for name in [k for k, v in sorted(self.userPlotData.datasets.items(), key=lambda x: x[-1].number)]:
			data = self.userPlotData.datasets[name]
			if data.status:
				if (data.plotType == 'time series' and plotNo == 0) or (data.plotType == 'long plot' and plotNo == 1):
					labelOriginal = 'User Plot Data: {0}'.format(data.name)
					label, artistTemplates = self.getNewPlotProperties(plotNo, [labelOriginal], rtype='lines')
					if labelOriginal not in labels[0]:
						x = data.x[:]
						if self.tuView.tuOptions.xAxisDates and plotNo == 0:
							if data.dates is None:
								x = self.convertTimeToDate(x)
							else:
								x = data.dates[:]
						y = data.y[:]
						a, = subplot.plot(x, y, label=label[0])
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
			if datum in self.tuView.tuResults.time2date.keys():
				time = self.tuView.tuResults.time2date[datum]
			else:
				time = self.tuView.tuOptions.zeroTime + timedelta(hours=datum)
				time = roundSeconds(time)
			x.append(time)
			
		return x
	
	def convertDateToTime(self, data: str, unit: str='h') -> float:
		"""
		Converts date to time
		
		:param data: str
		:return: float time
		"""

		date = datetime.strptime(data, self.tuView.tuResults.dateFormat)
		if date in self.tuView.tuResults.date2time:
			return self.tuView.tuResults.date2time[date]
		else:
			return -99999.

	def convertFlowRegimeToInt(self, data: list) -> list:
		"""
		Converts flow regime letter to an integer value

		"""

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
			# no flow or flap gate closed = 0
			'G': 0,
			' ': 0,
			'  ': 0,
		}

		dataInt = []
		for d in data:
			if d:
				dataInt.append(fr2int[d[0].upper()])
			else:
				dataInt.append(0)

		return dataInt

