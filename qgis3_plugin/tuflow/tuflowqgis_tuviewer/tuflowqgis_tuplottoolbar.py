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
	sys.path.append(os.path.join(current_path, '_tk\\DLLs'))
	sys.path.append(os.path.join(current_path, '_tk\\libs'))
	sys.path.append(os.path.join(current_path, '_tk\\Lib'))
	import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.patches import Polygon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tumenufunctions import TuMenuFunctions
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplottoolbar_viewtoolbar import ViewToolbar


class TuPlotToolbar():
	"""
	Class for handling plotting toolbar.
	
	"""
	
	def __init__(self, TuPlot):
		self.tuPlot = TuPlot
		self.tuView = TuPlot.tuView
		self.tuMenuFunctions = TuMenuFunctions(self.tuView)
		
		self.initialiseMplToolbars()
		self.initialiseMapOutputPlottingToolbar()
		self.initialiseViewToolbar()
		
	def initialiseMplToolbars(self):
		"""
		Initialises the mpl toolbars for all plot windows.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# Plotting Toolbar - Time series
		self.mpltoolbarTimeSeries = matplotlib.backends.backend_qt5agg.NavigationToolbar2QT(
			self.tuPlot.plotWidgetTimeSeries,
			self.tuView.mplToolbarFrame)
		self.mpltoolbarTimeSeries.setIconSize(QSize(20, 20))
		self.mpltoolbarTimeSeries.resize(QSize(250, 30))
		self.lstActionsTimeSeries = self.mpltoolbarTimeSeries.actions()
		self.mpltoolbarTimeSeries.removeAction(self.lstActionsTimeSeries[6])  # remove customise subplot
		
		# Plotting Toolbar - Long plot
		self.mpltoolbarLongPlot = matplotlib.backends.backend_qt5agg.NavigationToolbar2QT(
			self.tuPlot.plotWidgetLongPlot,
			self.tuView.mplToolbarFrame)
		self.mpltoolbarLongPlot.setIconSize(QSize(20, 20))
		self.mpltoolbarLongPlot.resize(QSize(250, 30))
		self.lstActionsLongPlot = self.mpltoolbarLongPlot.actions()
		self.mpltoolbarLongPlot.removeAction(self.lstActionsLongPlot[6])  # remove customise subplot
		self.mpltoolbarLongPlot.setVisible(False)
		
		# Plotting Toolbar - Cross section
		self.mpltoolbarCrossSection = matplotlib.backends.backend_qt5agg.NavigationToolbar2QT(
			self.tuPlot.plotWidgetCrossSection,
			self.tuView.mplToolbarFrame)
		self.mpltoolbarCrossSection.setIconSize(QSize(20, 20))
		self.mpltoolbarCrossSection.resize(QSize(250, 30))
		self.lstActionsCrossSection = self.mpltoolbarCrossSection.actions()
		self.mpltoolbarCrossSection.removeAction(self.lstActionsCrossSection[6])  # remove customise subplot
		self.mpltoolbarCrossSection.setVisible(False)
		
		return True
		
	def initialiseMapOutputPlottingToolbar(self):
		"""
		Initialises toolbar for the map output plotting i.e. time series, cross section / long plot, flux
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# toolbar settings
		self.mapOutputPlotToolbar = QToolBar('Map Output Plotting', self.tuView.MapOutputPlotFrame)
		self.mapOutputPlotToolbar.setIconSize(QSize(20, 20))
		self.mapOutputPlotToolbar.resize(QSize(250, 30))
		
		# icons
		tsIcon = QIcon(os.path.dirname(os.path.dirname(__file__)) + "\\icons\\results_2.png")
		csIcon = QIcon(os.path.dirname(os.path.dirname(__file__)) + "\\icons\\CrossSection_2.png")
		fluxIcon = QIcon(os.path.dirname(os.path.dirname(__file__)) + "\\icons\\FluxLine.png")
		fluxSecAxisIcon = QIcon(os.path.dirname(os.path.dirname(__file__)) + "\\icons\\2nd_axis_2.png")
		cursorTrackingIcon = QIcon(os.path.dirname(os.path.dirname(__file__)) + "\\icons\\live_cursor_tracking.png")
		meshGridIcon = QIcon(os.path.dirname(os.path.dirname(__file__)) + "\\icons\\meshGrid.png")
		
		# buttons
		self.plotTSMenu = QMenu('Plot Time Series From Map Output')
		self.plotTSMenu.menuAction().setIcon(tsIcon)
		self.plotTSMenu.menuAction().setCheckable(True)
		self.plotLPMenu = QMenu('Plot Cross Section / Long PLot From Map Output')
		self.plotLPMenu.menuAction().setIcon(csIcon)
		self.plotLPMenu.menuAction().setCheckable(True)
		self.plotFluxButton = QToolButton(self.mapOutputPlotToolbar)
		self.plotFluxButton.setCheckable(True)
		self.plotFluxButton.setIcon(fluxIcon)
		self.plotFluxButton.setToolTip('Plot Flux From Map Output')
		self.fluxSecAxisButton = QToolButton(self.mapOutputPlotToolbar)
		self.fluxSecAxisButton.setCheckable(True)
		self.fluxSecAxisButton.setIcon(fluxSecAxisIcon)
		self.fluxSecAxisButton.setToolTip('Flux Plot Secondary Axis')
		self.cursorTrackingButton = QToolButton(self.mapOutputPlotToolbar)
		self.cursorTrackingButton.setCheckable(True)
		self.cursorTrackingButton.setChecked(True)
		self.cursorTrackingButton.setIcon(cursorTrackingIcon)
		self.cursorTrackingButton.setToolTip('Live Map Tracking')
		self.meshGridButton = QToolButton(self.mapOutputPlotToolbar)
		self.meshGridButton.setCheckable(True)
		self.meshGridAction = QAction(meshGridIcon, 'Toggle Mesh Rendering', self.meshGridButton)
		self.meshGridAction.setCheckable(True)
		self.meshGridButton.setDefaultAction(self.meshGridAction)

		# add buttons to toolbar
		self.mapOutputPlotToolbar.addAction(self.plotTSMenu.menuAction())
		self.mapOutputPlotToolbar.addAction(self.plotLPMenu.menuAction())
		self.mapOutputPlotToolbar.addSeparator()
		self.mapOutputPlotToolbar.addWidget(self.plotFluxButton)
		self.mapOutputPlotToolbar.addWidget(self.fluxSecAxisButton)
		self.mapOutputPlotToolbar.addSeparator()
		self.mapOutputPlotToolbar.addSeparator()
		self.mapOutputPlotToolbar.addWidget(self.cursorTrackingButton)
		self.mapOutputPlotToolbar.addSeparator()
		self.mapOutputPlotToolbar.addSeparator()
		self.mapOutputPlotToolbar.addWidget(self.meshGridButton)
		
		# connect buttons
		self.plotTSMenu.menuAction().triggered.connect(lambda: self.mapOutputPlottingButtonClicked(0))
		self.plotLPMenu.menuAction().triggered.connect(lambda: self.mapOutputPlottingButtonClicked(1))
		self.plotFluxButton.released.connect(lambda: self.mapOutputPlottingButtonClicked(10))
		self.cursorTrackingButton.released.connect(self.cursorTrackingToggled)
		self.meshGridAction.triggered.connect(self.tuMenuFunctions.toggleMeshRender)
		
		return True
	
	def initialiseViewToolbar(self):
		
		# view menu - time series
		self.viewToolbarTimeSeries = ViewToolbar(self, 0)
		
		# view menu - long plot
		self.viewToolbarLongPlot = ViewToolbar(self, 1)
		self.viewToolbarLongPlot.setVisible(False)
		
		# view menu - 1D cross section plot
		self.viewToolbarCrossSection = ViewToolbar(self, 2)
		self.viewToolbarCrossSection.setVisible(False)
		
		return True
		
	def setToolbarActive(self, plotNo):
		"""
		Sets the toolbar active based on the enumerator.
		
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# Time series
		if plotNo == 0:
			# toolbar
			self.mpltoolbarLongPlot.setVisible(False)
			self.mpltoolbarCrossSection.setVisible(False)
			self.mpltoolbarTimeSeries.setVisible(True)
			
			# view toolbar
			self.viewToolbarTimeSeries.setVisible(True)
			self.viewToolbarLongPlot.setVisible(False)
			self.viewToolbarCrossSection.setVisible(False)
		
		# Long plot
		elif plotNo == 1:
			# toolbar
			self.mpltoolbarTimeSeries.setVisible(False)
			self.mpltoolbarCrossSection.setVisible(False)
			self.mpltoolbarLongPlot.setVisible(True)
			
			# view toolbar
			self.viewToolbarTimeSeries.setVisible(False)
			self.viewToolbarLongPlot.setVisible(True)
			self.viewToolbarCrossSection.setVisible(False)
	
	# Cross section
		elif plotNo == 2:
			# toolbar
			self.mpltoolbarTimeSeries.setVisible(False)
			self.mpltoolbarLongPlot.setVisible(False)
			self.mpltoolbarCrossSection.setVisible(True)
			
			# view toolbar
			self.viewToolbarTimeSeries.setVisible(False)
			self.viewToolbarLongPlot.setVisible(False)
			self.viewToolbarCrossSection.setVisible(True)
		
		# menubar
		self.tuView.tuMenuBar.viewMenu.clear()
		self.tuView.tuMenuBar.loadViewMenu(plotNo, update=True)
		
		self.tuView.tuMenuBar.exportMenu.clear()
		self.tuView.tuMenuBar.loadExportMenu(plotNo, update=True)
		
		# context menu
		self.tuView.tuContextMenu.plotMenu.clear()
		self.tuView.tuContextMenu.loadPlotMenu(plotNo, update=True)
		
		return True
	
	def mapOutputPlottingButtonClicked(self, plotNo):
	
		# unpress buttons if already pressed
		if plotNo == 0:
			if self.plotTSMenu.menuAction().isChecked():
				# turn other buttons off
				self.plotLPMenu.menuAction().setChecked(False)
				self.plotFluxButton.setChecked(False)
				# turn off other plotting instances
				if self.tuPlot.tuRubberBand.cursorTrackingConnected:
					self.tuPlot.tuRubberBand.mouseTrackDisconnect()
				if self.tuPlot.tuFlowLine.cursorTrackingConnected:
					self.tuPlot.tuFlowLine.mouseTrackDisconnect()
				# turn on time series plot
				#if self.tuView.mcboResultType.checkedItems():
				if self.getCheckedItemsFromPlotOptions(0):
					self.tuView.tabWidget.setCurrentIndex(0)
					if self.tuView.cboSelectType.currentText() == 'Layer Selection':
						self.tuPlot.tuPlotSelection.useSelection(plotNo)
					else:
						self.tuPlot.tuRubberBand.startRubberBand(plotNo)
				else:
					self.plotTSMenu.menuAction().setChecked(False)
			else:
				# turn off self plotting instance
				self.tuPlot.tuRubberBand.mouseTrackDisconnect()
		elif plotNo == 1:
			if self.plotLPMenu.menuAction().isChecked():
				# turn other buttons off
				self.plotTSMenu.menuAction().setChecked(False)
				self.plotFluxButton.setChecked(False)
				# turn off other plotting instances
				if self.tuPlot.tuRubberBand.cursorTrackingConnected:
					self.tuPlot.tuRubberBand.mouseTrackDisconnect()
				if self.tuPlot.tuFlowLine.cursorTrackingConnected:
					self.tuPlot.tuFlowLine.mouseTrackDisconnect()
				# turn on long plot
				#if self.tuView.mcboResultType.checkedItems():
				if self.getCheckedItemsFromPlotOptions(1):
					self.tuView.tabWidget.setCurrentIndex(1)
					if self.tuView.cboSelectType.currentText() == 'Layer Selection':
						self.tuPlot.tuPlotSelection.useSelection(plotNo)
					else:
						self.tuPlot.tuRubberBand.startRubberBand(plotNo)
				else:
					self.plotLPMenu.menuAction().setChecked(False)
			else:
				# turn off self plotting instance
				self.tuPlot.tuRubberBand.mouseTrackDisconnect()
		elif plotNo == 10:
			if self.plotFluxButton.isChecked():
				# turn other buttons off
				self.plotTSMenu.menuAction().setChecked(False)
				self.plotLPMenu.menuAction().setChecked(False)
				# turn off other plotting instances
				if not self.tuPlot.tuRubberBand.cursorTrackingConnected:
					self.tuPlot.tuRubberBand.mouseTrackDisconnect()
				# turn on flux plot
				if self.tuView.tuResults.tuResults2D.activeMeshLayers:
					self.tuView.tabWidget.setCurrentIndex(0)
					if self.tuView.cboSelectType.currentText() == 'Layer Selection':
						self.tuPlot.tuPlotSelection.useSelection(0, type='flow')
					else:
						self.tuPlot.tuFlowLine.startRubberBand()
				else:
					self.plotFluxButton.setChecked(False)
			else:
				# turn off self plotting instance
				self.tuPlot.tuFlowLine.mouseTrackDisconnect()
				
		return False
	
	def addItemToPlotOptions(self, type, plotNo):
		if plotNo == 0:
			menu = self.plotTSMenu
		elif plotNo == 1:
			menu = self.plotLPMenu
		else:
			return False
		
		action = QAction(type, menu)
		action.setCheckable(True)
		menu.addAction(action)
		
		return True
	
	def getItemsFromPlotOptions(self, plotNo):
		if plotNo == 0:
			menu = self.plotTSMenu
		elif plotNo == 1:
			menu = self.plotLPMenu
		else:
			return []
		
		actions = []
		for action in menu.actions():
			actions.append(action.text())
		
		return actions
	
	def getCheckedItemsFromPlotOptions(self, plotNo):
		if plotNo == 0:
			menu = self.plotTSMenu
		elif plotNo == 1:
			menu = self.plotLPMenu
		else:
			return []
		
		actions = []
		for action in menu.actions():
			if action.isChecked():
				actions.append(action.text())
			
		return actions
	
	def setCheckedItemsPlotOptions(self, types, plotNo):
		if plotNo == 0:
			menu = self.plotTSMenu
		elif plotNo == 1:
			menu = self.plotLPMenu
		else:
			return False
		
		for action in menu.actions():
			if action.text() in types:
				action.setChecked(True)
				
		return True
	
	def cursorTrackingToggled(self):
		if self.cursorTrackingButton.isChecked():
			self.tuView.tuOptions.liveMapTracking = True
		else:
			self.tuView.tuOptions.liveMapTracking = False
			
		return True
