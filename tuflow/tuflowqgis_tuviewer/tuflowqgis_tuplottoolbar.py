from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets  import *
from tuflow.dataset_menu import DatasetMenu
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
from tuflow.spinbox_action import SingleSpinBoxAction



class TuPlotToolbar():
	"""
	Class for handling plotting toolbar.
	
	"""
	
	def __init__(self, TuPlot):
		self.tuPlot = TuPlot
		self.tuView = TuPlot.tuView
		self.tuMenuFunctions = TuMenuFunctions(self.tuView)
		self.averageMethodActions = []
		
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

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		# toolbar settings
		self.mapOutputPlotToolbar = QToolBar('Map Output Plotting', self.tuView.MapOutputPlotFrame)
		self.mapOutputPlotToolbar.setIconSize(QSize(20, 20))
		self.mapOutputPlotToolbar.resize(QSize(250, 30))

		# 3D mesh averaging plotting
		self.mesh3dPlotToolbar = QToolBar('3D Mesh Plotting', self.tuView.Mesh3DToolbarFrame)
		self.mesh3dPlotToolbar.setIconSize(QSize(20, 20))
		self.mesh3dPlotToolbar.resize(QSize(250, 30))
		
		# icons
		dir = os.path.dirname(os.path.dirname(__file__))
		tsIcon = QIcon(os.path.join(dir, "icons", "results_2.png"))
		csIcon = QIcon(os.path.join(dir, "icons", "CrossSection_2.png"))
		fluxIcon = QIcon(os.path.join(dir, "icons", "FluxLine.png"))
		fluxSecAxisIcon = QIcon(os.path.join(dir, "icons", "2nd_axis_2.png"))
		cursorTrackingIcon = QIcon(os.path.join(dir, "icons", "live_cursor_tracking.png"))
		meshGridIcon = QIcon(os.path.join(dir, "icons", "meshGrid.png"))
		meshAveragingIcon = QgsApplication.getThemeIcon('/propertyicons/meshaveraging.svg')
		curtainPlotIcon = QIcon(os.path.join(dir, "icons", "curtain_plot.png"))
		
		# buttons
		self.plotTSMenu = DatasetMenu('Plot Time Series From Map Output')
		self.plotTSMenu.menuAction().setIcon(tsIcon)
		self.plotTSMenu.menuAction().setCheckable(True)
		self.plotLPMenu = DatasetMenu('Plot Cross Section / Long PLot From Map Output')
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
		self.cursorTrackingButton.setChecked(False)
		self.cursorTrackingButton.setIcon(cursorTrackingIcon)
		self.cursorTrackingButton.setToolTip('Live Map Tracking')
		self.meshGridButton = QToolButton(self.mapOutputPlotToolbar)
		self.meshGridButton.setCheckable(True)
		self.meshGridAction = QAction(meshGridIcon, 'Toggle Mesh Rendering', self.meshGridButton)
		self.meshGridAction.setCheckable(True)
		self.meshGridButton.setDefaultAction(self.meshGridAction)
		self.averageMethodMenu = DatasetMenu("3D to 2D Averaging Method")
		self.averageMethodMenu.menuAction().setIcon(meshAveragingIcon)
		self.averageMethodMenu.menuAction().setCheckable(True)
		self.addAverageMethods()
		self.curtainPlotMenu = DatasetMenu("Curtain Plot")
		self.curtainPlotMenu.menuAction().setIcon(curtainPlotIcon)
		self.curtainPlotMenu.menuAction().setCheckable(True)

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
		self.mesh3dPlotToolbar.addAction(self.averageMethodMenu.menuAction())
		self.mesh3dPlotToolbar.addAction(self.curtainPlotMenu.menuAction())
		
		# connect buttons
		self.plotTSMenu.menuAction().triggered.connect(lambda: self.mapOutputPlottingButtonClicked(TuPlot.DataTimeSeries2D))
		self.plotLPMenu.menuAction().triggered.connect(lambda: self.mapOutputPlottingButtonClicked(TuPlot.DataCrossSection2D))
		self.plotFluxButton.released.connect(lambda: self.mapOutputPlottingButtonClicked(TuPlot.DataFlow2D))
		self.cursorTrackingButton.released.connect(self.cursorTrackingToggled)
		self.meshGridAction.triggered.connect(self.tuMenuFunctions.toggleMeshRender)
		self.curtainPlotMenu.menuAction().triggered.connect(lambda: self.mapOutputPlottingButtonClicked(TuPlot.DataCurtainPlot))
		
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
		self.tuView.tuMenuBarSecond.viewMenu.clear()
		self.tuView.tuMenuBarSecond.loadViewMenu(plotNo, update=True)

		self.tuView.tuMenuBar.exportMenu.clear()
		self.tuView.tuMenuBar.loadExportMenu(plotNo, update=True)
		self.tuView.tuMenuBarSecond.exportMenu.clear()
		self.tuView.tuMenuBarSecond.loadExportMenu(plotNo, update=True)

		# context menu
		self.tuView.tuContextMenu.plotMenu.clear()
		self.tuView.tuContextMenu.loadPlotMenu(plotNo, update=True)

		return True
	
	def mapOutputPlottingButtonClicked(self, dataType):

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		# unpress buttons if already pressed
		if dataType == TuPlot.DataTimeSeries2D:
			if self.plotTSMenu.menuAction().isChecked():
				# turn other buttons off
				self.plotLPMenu.menuAction().setChecked(False)
				self.plotFluxButton.setChecked(False)
				self.curtainPlotMenu.menuAction().setChecked(False)
				# turn off other plotting instances
				if self.tuPlot.tuCrossSection.cursorTrackingConnected:
					self.tuPlot.tuCrossSection.mouseTrackDisconnect()
				if self.tuPlot.tuFlowLine.cursorTrackingConnected:
					self.tuPlot.tuFlowLine.mouseTrackDisconnect()
				if self.tuPlot.tuCurtainLine.cursorTrackingConnected:
					self.tuPlot.tuCurtainLine.mouseTrackDisconnect()
				# turn on time series plot
				#if self.tuView.mcboResultType.checkedItems():
				if self.getCheckedItemsFromPlotOptions(dataType):
					self.tuView.tabWidget.setCurrentIndex(TuPlot.TimeSeries)
					if self.tuView.cboSelectType.currentText() == 'Layer Selection':
						self.tuPlot.tuPlotSelection.useSelection(dataType)
					else:
						self.tuPlot.tuTSPoint.startRubberBand()
				else:
					self.plotTSMenu.menuAction().setChecked(False)
			else:
				# turn off self plotting instance
				self.tuPlot.tuTSPoint.mouseTrackDisconnect()
		elif dataType == TuPlot.DataCrossSection2D:
			if self.plotLPMenu.menuAction().isChecked():
				# turn other buttons off
				self.plotTSMenu.menuAction().setChecked(False)
				self.plotFluxButton.setChecked(False)
				self.curtainPlotMenu.menuAction().setChecked(False)
				# turn off other plotting instances
				if self.tuPlot.tuTSPoint.cursorTrackingConnected:
					self.tuPlot.tuTSPoint.mouseTrackDisconnect()
				if self.tuPlot.tuFlowLine.cursorTrackingConnected:
					self.tuPlot.tuFlowLine.mouseTrackDisconnect()
				if self.tuPlot.tuCurtainLine.cursorTrackingConnected:
					self.tuPlot.tuCurtainLine.mouseTrackDisconnect()
				# turn on long plot
				#if self.tuView.mcboResultType.checkedItems():
				if self.getCheckedItemsFromPlotOptions(dataType):
					self.tuView.tabWidget.setCurrentIndex(TuPlot.CrossSection)
					if self.tuView.cboSelectType.currentText() == 'Layer Selection':
						self.tuPlot.tuPlotSelection.useSelection(dataType)
					else:
						# started = self.tuPlot.tuRubberBand.startRubberBand(plotNo)
						started = self.tuPlot.tuCrossSection.startRubberBand()
						if not started:
							# turn off self plotting instance
							self.plotLPMenu.menuAction().setChecked(False)
				else:
					self.plotLPMenu.menuAction().setChecked(False)
			else:
				# turn off self plotting instance
				# self.tuPlot.tuRubberBand.mouseTrackDisconnect()
				self.tuPlot.tuCrossSection.mouseTrackDisconnect()
		elif dataType == TuPlot.DataFlow2D:
			if self.plotFluxButton.isChecked():
				# turn other buttons off
				self.plotTSMenu.menuAction().setChecked(False)
				self.plotLPMenu.menuAction().setChecked(False)
				self.curtainPlotMenu.menuAction().setChecked(False)
				# turn off other plotting instances
				if self.tuPlot.tuTSPoint.cursorTrackingConnected:
					self.tuPlot.tuTSPoint.mouseTrackDisconnect()
				if self.tuPlot.tuCrossSection.cursorTrackingConnected:
					self.tuPlot.tuCrossSection.mouseTrackDisconnect()
				if self.tuPlot.tuCurtainLine.cursorTrackingConnected:
					self.tuPlot.tuCurtainLine.mouseTrackDisconnect()
				# turn on flux plot
				if self.tuView.tuResults.tuResults2D.activeMeshLayers:
					self.tuView.tabWidget.setCurrentIndex(TuPlot.TimeSeries)
					if self.tuView.cboSelectType.currentText() == 'Layer Selection':
						self.tuPlot.tuPlotSelection.useSelection(TuPlot.DataFlow2D)
					else:
						started = self.tuPlot.tuFlowLine.startRubberBand()
						if not started:
							# turn off self plotting instance
							self.plotFluxButton.setChecked(False)
				else:
					self.plotFluxButton.setChecked(False)
			else:
				# turn off self plotting instance
				self.tuPlot.tuFlowLine.mouseTrackDisconnect()
		elif dataType == TuPlot.DataCurtainPlot:
			if self.curtainPlotMenu.menuAction().isChecked():
				# turn other buttons off
				self.plotTSMenu.menuAction().setChecked(False)
				self.plotLPMenu.menuAction().setChecked(False)
				self.plotFluxButton.setChecked(False)
				# turn off other plotting instances
				if self.tuPlot.tuTSPoint.cursorTrackingConnected:
					self.tuPlot.tuTSPoint.mouseTrackDisconnect()
				if self.tuPlot.tuCrossSection.cursorTrackingConnected:
					self.tuPlot.tuCrossSection.mouseTrackDisconnect()
				if self.tuPlot.tuFlowLine.cursorTrackingConnected:
					self.tuPlot.tuFlowLine.mouseTrackDisconnect()
				# turn on curtain plot
				if self.getCheckedItemsFromPlotOptions(dataType):
					self.tuView.tabWidget.setCurrentIndex(TuPlot.CrossSection)
					if self.tuView.cboSelectType.currentText() == 'Layer Selection':
						self.tuPlot.tuPlotSelection.useSelection(TuPlot.DataCurtainPlot)
					else:
						started = self.tuPlot.tuCurtainLine.startRubberBand()
						if not started:
							# turn off self plotting instance
							self.curtainPlotMenu.menuAction().setChecked(False)
				else:
					self.curtainPlotMenu.menuAction().setChecked(False)
			else:
				# turn off self plotting instance
				self.tuPlot.tuCurtainLine.mouseTrackDisconnect()
				
		return False
	
	def addItemToPlotOptions(self, type, plotNo):
		if plotNo == 0:
			menu = self.plotTSMenu
		elif plotNo == 1:
			menu = self.plotLPMenu
		elif plotNo == 20:
			menu = self.curtainPlotMenu
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
	
	def getCheckedItemsFromPlotOptions(self, dataType):

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		if dataType == TuPlot.DataTimeSeries2D:
			menu = self.plotTSMenu
		elif dataType == TuPlot.DataCrossSection2D:
			menu = self.plotLPMenu
		elif dataType == TuPlot.DataCurtainPlot:
			menu = self.curtainPlotMenu
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

	def addAverageMethods(self):
		methods = [
			"Single Vertical Level (from top)",
			"Single Vertical Level (from bottom)",
			"Multi Vertical Level (from top)",
			"Multi Vertical Level (from bottom)",
			"Sigma",
			"Depth (relative to surface)",
			"Height (relative to bed level)",
			"Elevation (absolute to model's datum)"
		]

		self.averageMethodActions.clear()
		for method in methods:
			menu = DatasetMenu(method, self.averageMethodMenu)
			menu.menuAction().setCheckable(True)

			if method == "Single Vertical Level (from top)":
				self.singleVerticalLevelMethod(menu, False)

			self.averageMethodMenu.addAction(menu.menuAction())
			self.averageMethodActions.append(menu)

	def singleVerticalLevelMethod(self, menu: QMenu, bAdd: bool) -> None:
		if bAdd:
			action = SingleSpinBoxAction(menu, True, "Vertical Layer Index", range=(0, 99999))
			action.setCheckable(True)
			action.removeActionRequested.connect(lambda e: self.removeAveragingMethod(e, menu))
			lastAction = menu.actions()[-2]  # insert before separator
			menu.insertAction(lastAction, action)
			if len(menu.actions()) > 3:
				if not menu.actions()[0].bCheckBox:
					menu.actions()[0].insertCheckbox()
		else:
			action = SingleSpinBoxAction(menu, False, "Vertical Layer Index", range=(0, 99999))
			action.setCheckable(True)
			action.removeActionRequested.connect(lambda e: self.removeAveragingMethod(e, menu))
			menu.addAction(action)
			menu.addSeparator()
			action = QAction("Add Additional...", menu)
			menu.addAction(action)
			action.triggered.connect(lambda e: self.singleVerticalLevelMethod(menu, True))

	def removeAveragingMethod(self, p, menu):
		if len(menu.actions()) > 3:
			action = menu.actionAt(p)
			menu.removeAction(action)
			if len(menu.actions()) <= 3:
				if menu.actions()[0].bCheckBox:
					menu.actions()[0].removeCheckbox()

	def getAveragingMethods(self, groupMetadata):
		if groupMetadata.maximumVerticalLevelsCount() < 2: return [None]
		if not self.averageMethodMenu.menuAction().isChecked(): return [None]

		averagingMethods = []
		for action in self.averageMethodMenu.actions():
			if action.isChecked():
				counter = 0
				for action2 in action.menu().actions():
					if action2.isChecked():
						averagingMethods.append('{0}_{1}'.format(action.text(), counter))
						counter += 1

		if averagingMethods:
			return averagingMethods
		else:
			return [None]

	def getAveragingParameters(self, averagingMethod):
		for action in self.averageMethodMenu.actions():
			if action.text() in averagingMethod:
				counter = 0
				for action2 in action.menu().actions():
					if action2.isChecked():
						if counter == int(averagingMethod[-1]):
							return action2.values()
						else:
							counter += 1

		return None







