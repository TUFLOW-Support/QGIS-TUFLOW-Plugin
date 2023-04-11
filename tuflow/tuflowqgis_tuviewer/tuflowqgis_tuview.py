import os
import re
import sys
from datetime import datetime
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from qgis.gui import *
from PyQt5.QtWidgets import *
from ..forms.tuflow_plotting_dock import Ui_Tuplot
from ..dataset_view import DataSetModel
from .tuflowqgis_turesults import TuResults
from .tuflowqgis_tuplot import TuPlot
from .tuflowqgis_tumenubar import TuMenuBar
from .tuflowqgis_tuoptions import TuOptions
from .tuflowqgis_tumenucontext import TuContextMenu
from .tuflowqgis_tuproject import TuProject
from ..tuflowqgis_library import (tuflowqgis_find_layer, findAllMeshLyrs, convertTimeToFormattedTime,
                                       is1dTable, findTableLayers, is1dNetwork, isPlotLayer, isTSLayer)
from ..tuflowqgis_dialog import tuflowqgis_meshSelection_dialog
from ..TUFLOW_XS import XS
from ..TUFLOW_1dTa import HydTables
from datetime import timedelta
from ..TUFLOW_FM_data_provider import FM_XS
import numpy as np
try:
	from pathlib import Path
except ImportError:
	from ..pathlib_ import Path_ as Path


class TuView(QDockWidget, Ui_Tuplot):
	
	def __init__(self, iface=None, **kwargs):

		qv = Qgis.QGIS_VERSION_INT

		# initialise the dock and ui
		QDockWidget.__init__(self)
		self.setupUi(self)
		self.wdg = Ui_Tuplot.__init__(self)  # Initialise tuplot dock ui
		self.iface = iface  # QgsInterface
		if self.iface is not None:
			self.canvas = self.iface.mapCanvas()  # QgsMapCanvas
		else:
			self.canvas = None
		self.project = QgsProject().instance()  # QgsProject
		if self.iface is not None:
			self.currentLayer = self.iface.activeLayer()
		else:
			self.currentLayer = None
		self.doubleClickEvent = False
		playIcon = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "play_button.png"))
		self.btnTimePlay.setIcon(playIcon)
		lock2DIcon = QgsApplication.getThemeIcon("/locked.svg")
		self.btn2dLock.setIcon(lock2DIcon)
		self.lock2DTimesteps = True
		self.resultChangeSignalCount = 0
		self.progressBar.setVisible(False)

		self.in_results_changed = False

		# project
		self.tuProject = None

		# options
		self.tuOptions = TuOptions()

		# results class
		self.tuResults = TuResults(self)

		# plot class
		self.tuPlot = TuPlot(self)
		
		# main menu bar
		removeTuview = kwargs['removeTuview'] if 'removeTuview' in kwargs else None
		reloadTuview = kwargs['reloadTuview'] if 'reloadTuview' in kwargs else None
		self.tuMenuBar = TuMenuBar(self, removeTuview=removeTuview, reloadTuview=reloadTuview, layout=self.mainMenu)
		self.tuMenuBar.loadFileMenu()
		self.tuMenuBar.loadViewMenu(0)
		self.tuMenuBar.loadSettingsMenu(0)
		self.tuMenuBar.loadExportMenu(0)
		self.tuMenuBar.loadResultsMenu()
		self.tuMenuBar.loadHelpMenu()
		#self.tuMenuBar.connectMenu()

		# secondary menu bar
		self.tuMenuBarSecond = TuMenuBar(self, removeTuview=removeTuview, reloadTuview=reloadTuview,
		                                 menu_bar=self.tuMenuBar, layout=self.mainMenuSecond)
		self.tuMenuBarSecond.loadFileMenu()
		self.tuMenuBarSecond.loadViewMenu(0)
		self.tuMenuBarSecond.loadSettingsMenu(0)
		self.tuMenuBarSecond.loadExportMenu(0)
		self.tuMenuBarSecond.loadHelpMenu()
		self.tuMenuBarSecond.loadResultsMenu()

		# context menu
		self.tuContextMenu = TuContextMenu(self)
		self.tuContextMenu.loadPlotMenu(0)
		self.tuContextMenu.loadResultsMenu()
		self.tuContextMenu.loadResultTypesMenu()
		self.tuContextMenu.connectMenu()
		
		# options
		#self.tuOptions = tuflowqgis_tuoptions.TuOptions()
		
		# Expand result type tree
		self.initialiseDataSetView()

		# 1D cross sections
		self.selectionChangeConnected = False
		self.crossSections1D = XS()
		self.crossSectionsFM = FM_XS()
		self.loadXSLayers()
		self.hydTables = HydTables()
		
		# Activate signals
		self.connected = False  # Signal connection
		self.connectSave = False
		self.firstConnection = True
		self.layer_selection_signals = []
		self.qgisConnect()
		
		# check for already open mesh layers
		self.tuResults.tuResults2D.loadOpenMeshLayers()

		# check for already open _TS layers
		self.tuResults.tuResults1D.loadOpenTSLayers()
		
		# set disabled tabs to be invisible
		self.setStyleSheet("QTabBar::tab::disabled {width: 0; height: 0; margin: 0; padding: 0; border: none;} ")

		# set 1D cross section tab invisible - no longer using a separate tab so may never be used
		self.setTabVisible(TuPlot.CrossSection1D, False)

		self.SecondMenu.setVisible(False)

		# show as dates
		self.cbShowAsDates.setChecked(self.tuOptions.xAxisDates)

		narrowWidth = self.pbShowPlotWindow.minimumSizeHint().width() + \
		              self.mainMenuSecond_2.minimumSizeHint().width()
		self.dockWidgetContents.setMinimumWidth(narrowWidth)

		if qv >= 31600:
			self.tuResults.initialiseTemporalController()

		if QSettings().value("TUFLOW/tuview_defaultlayout", "previous_state") == "narrow" or \
				(QSettings().value("TUFLOW/tuview_defaultlayout", "previous_state") == 'previous_state' and
				QSettings().value("TUFLOW/tuview_previouslayout", "plot") == "narrow"):
			self.plotWindowVisibilityToggled(initialisation=True)
		
	def __del__(self):
		self.qgisDisconnect()
		self.tuMenuBar.disconnectMenu()
		self.tuMenuBar.clear()
		self.tuMenuBarSecond.disconnectMenu()
		self.tuMenuBarSecond.clear()
		self.tuResults.removeResults([self.OpenResults.item(i).text() for i in range(self.OpenResults.count()) if self.OpenResults.item(i).text()],
		                             ignore_mesh_results=True)

	def setTabVisible(self, index, visible):
		"""

		"""

		self.tabWidget.setTabEnabled(index, visible)
		self.style().unpolish(self)
		self.style().polish(self)

	def closeEvent(self, event):
		"""
		Is called when dock window is closed

		:param event: QtGui.QCloseEvent
		:return:
		"""
		
		QDockWidget.closeEvent(self, event)
		self.qgisDisconnect()
	
	def currentLayerChanged(self):
		"""
		Triggered when current layer is changed in QGIS Layers Panel.

		:return:
		"""

		# disconnect layer
		# if self.selectionChangeConnected:
		# 	try:
		# 		if self.currentLayer is not None:
		# 			self.currentLayer.selectionChanged.disconnect(self.selectionChanged)
		# 	except:
		# 		pass
		# 	self.selectionChangeConnected = False
		
		# get the active layer
		if self.iface is not None:
			self.currentLayer = self.iface.activeLayer()

			if isPlotLayer(self.currentLayer):
				if self.currentLayer.id() not in self.layer_selection_signals:
					self.currentLayer.selectionChanged.connect(self.selectionChanged)
					self.layer_selection_signals.append(self.currentLayer.id())
		
		if self.currentLayer is not None:
			# self.setTsTypesEnabled()
			self.loadXsType()
			# self.tuPlot.tuPlot1D.plot1dCrossSection(bypass=True, draw=True)

		# repaint viewport to reflect changes
		self.OpenResultTypes.viewport().update()
		
		# reconfig secondary axis list - disabled result types should not appear in secondary axis list
		#self.secondaryAxisResultTypesChanged(None)
	
	def loadXsType(self, lyr=None):
		"""
		Load TUFLOW 1D cross section in plotter if available.
		"""

		if lyr is None:
			lyr = self.currentLayer

		if is1dTable(lyr):
			self.loadXsSelections(lyr)
			#if lyr not in self.xsConnectedLayers:
			self.tuResults.addCrossSectionLayerToResults(lyr)
				# self.currentLayer.selectionChanged.connect(self.loadXsSelections)
				# self.xsConnectedLayers.append(self.currentLayer)
		# else:
		# 	for lyr in self.xsConnectedLayers:
		# 		try:
		# 			lyr.selectionChanged.disconnect(self.loadXsSelections)
		# 		except:
		# 			pass
		# 	self.xsConnectedLayers.clear()

	def loadXSLayers(self):
		"""

		"""

		xsLayers = findTableLayers()
		for lyr in xsLayers:
			self.loadXsType(lyr)

	def loadXsSelections(self, lyr=None):
		"""
		Load TUFLOW 1D cross sections from selected features
		"""

		crossSections = [self.crossSections1D, self.crossSectionsFM]

		if lyr is None:
			lyr = self.currentLayer
		i = 0
		if re.findall(re.escape(r'.gpkg|layername='), lyr.dataProvider().dataSourceUri(), flags=re.IGNORECASE):
			i = 1
		if is1dTable(lyr):
			for crossSection in crossSections:
				crossSection.removeByFeaturesNotIncluded(lyr.selectedFeatures(), i)
				for sel in lyr.selectedFeatures():
					source = sel.attributes()[i]
					if sel.attributes()[i+3] != NULL:
						source = '{0}_{1}'.format(source, sel.attributes()[i+3])
					if source not in crossSection.source or not crossSection.data[crossSection.source.index(source)].loaded:
						if source in crossSection.source:
							i = crossSection.source.index(source)
							crossSection.source.remove(source)
							crossSection.data.pop(i)
						dir = os.path.dirname(lyr.source())
						crossSection.addFromFeature(dir, lyr.fields(), sel, lyr)

	def setTsTypesEnabled(self, context=None):
		"""
		Sets time series types to disabled or enabled based on selected layer
		"""

		if self.currentLayer is None:
			# for lyrid, lyr in QgsProject.instance().mapLayers().items():
			# 	if isPlotLayer(lyr):
			# 		self.currentLayer = lyr
			# 		break
			# self.OpenResultTypes.model().setEnabled(0)
			# self.tuResults.tuResults1D.activeType = -1
			return

		if isinstance(self.currentLayer, QgsVectorLayer):
			self.OpenResultTypes.model().setEnabled(4, 5, 6, 7, 8)
			try:
				if self.currentLayer.geometryType() not in self.tuResults.tuResults1D.activeType:
					self.tuResults.tuResults1D.activeType.append(self.currentLayer.geometryType())
			except:
				pass
		else:
			return

		if context == 'update_active_1d_types':
			return

		if is1dTable(self.currentLayer) or is1dNetwork(self.currentLayer) or isPlotLayer(self.currentLayer) or \
				isTSLayer(self.currentLayer, self.tuResults.results):
			#self.OpenResultTypes.model().setEnabled(4, 5, 6, 7, 8)
			#self.tuResults.tuResults1D.activeType = 3
			self.tuResults.updateActiveResultTypes(None, geomType=self.currentLayer.geometryType())
			if not self.selectionChangeConnected:
				if self.currentLayer is not None:
					self.currentLayer.selectionChanged.connect(self.selectionChanged)
					self.selectionChangeConnected = True


		## Change the enabled/disabled status based on selected layer
		#if self.currentLayer.type() == QgsMapLayer.VectorLayer:  # vector layer
		#	resVersion = []
		#	for result in self.OpenResults.selectedItems():
		#		if result.text() in self.tuResults.tuResults1D.results1d.keys():
		#			resVersion.append(self.tuResults.tuResults1D.results1d[result.text()].formatVersion)
		#	if 2 in resVersion:
		#		if ' PLOT ' in self.currentLayer.name() or '_PLOT_' in self.currentLayer.name():
		#			if self.tabWidget.currentIndex() == 0:
		#				if self.currentLayer.geometryType() == 0:
		#					self.OpenResultTypes.model().setEnabled(4, 5, 6, 7, 8)
		#					self.tuResults.tuResults1D.activeType = 0
		#				elif self.currentLayer.geometryType() == 1:
		#					self.OpenResultTypes.model().setEnabled(4, 5, 6, 7, 8)
		#					self.tuResults.tuResults1D.activeType = 1
		#				elif self.currentLayer.geometryType() == 2:
		#					self.OpenResultTypes.model().setEnabled(4, 5, 6, 7, 8)
		#					self.tuResults.tuResults1D.activeType = 2
		#				self.tuResults.updateActiveResultTypes(None, geomType=self.currentLayer.geometryType())
		#			elif self.tabWidget.currentIndex() == 1:
		#				if self.currentLayer.geometryType() == 0:
		#					self.OpenResultTypes.model().setEnabled(4, 5, 6, 7, 8)
		#					self.tuResults.tuResults1D.activeType = 0
		#				elif self.currentLayer.geometryType() == 1:
		#					self.OpenResultTypes.model().setEnabled(4, 5, 6, 7, 8)
		#					self.tuResults.tuResults1D.activeType = 1
		#				elif self.currentLayer.geometryType() == 2:
		#					self.OpenResultTypes.model().setEnabled(4, 5, 6, 7, 8)
		#					self.tuResults.tuResults1D.activeType = 2
		#				# else:
		#				# 	self.OpenResultTypes.model().setEnabled(0)  # i.e. none
		#				# 	self.tuResults.tuResults1D.activeType = -1
		#				self.tuResults.updateActiveResultTypes(None, geomType=self.currentLayer.geometryType())
		#			if not self.selectionChangeConnected:
		#				self.currentLayer.selectionChanged.connect(self.selectionChanged)
		#				self.selectionChangeConnected = True
		#				self.selectionChanged()
		#		elif 1 not in resVersion:
		#			self.OpenResultTypes.model().setEnabled(0)  # i.e. none
		#	if 1 in resVersion:
		#		if self.tabWidget.currentIndex() == 0:
		#			if self.currentLayer.geometryType() == 0:
		#				self.OpenResultTypes.model().setEnabled(4)
		#				self.tuResults.tuResults1D.activeType = 0
		#			elif self.currentLayer.geometryType() == 1:
		#				self.OpenResultTypes.model().setEnabled(5)
		#				self.tuResults.tuResults1D.activeType = 1
		#			elif self.currentLayer.geometryType() == 2:
		#				self.OpenResultTypes.model().setEnabled(6)
		#				self.tuResults.tuResults1D.activeType = 2
		#		elif self.tabWidget.currentIndex() == 1:
		#			if self.currentLayer.geometryType() == 1:
		#				self.OpenResultTypes.model().setEnabled(7)
		#				self.tuResults.tuResults1D.activeType = 1
		#			else:
		#				self.OpenResultTypes.model().setEnabled(0)  # i.e. none
		#				self.tuResults.tuResults1D.activeType = -1
		#		if not self.selectionChangeConnected:
		#			self.currentLayer.selectionChanged.connect(self.selectionChanged)
		#			self.selectionChangeConnected = True
		#else:
		#	self.OpenResultTypes.model().setEnabled(0)  # i.e. none

	def initialiseDataSetView(self):
		"""
		Initialise the dataset view for result types.

		:return:
		"""
		
		mapOutputs = [("None", 3, False, False)]
		timeSeries = [("None", 3, False, False)]
		self.OpenResultTypes.setModel(DataSetModel(mapOutputs, timeSeries))
		self.OpenResultTypes.expandAll()
		
	def layersAdded(self, addedLayers):
		"""
		Triggered when layers are added to the project. Will check if they are mesh layers and add to tuview if
		they are.
		
		:param addedLayers: list -> QgsMapLayer
		:return: bool -> True for successful, False for unsuccessful
		"""

		for layer in addedLayers:
			if isinstance(layer, QgsMeshLayer):
				self.tuResults.tuResults2D.loadOpenMeshLayers(layer=layer.name())
			elif isinstance(layer, QgsVectorLayer):
				self.tuResults.tuResults1D.loadTSResultLayer(layer)
				
		return True
	
	def layersRemoved(self, removedLayers):
		"""
		Triggered when layers are removed from the project. Will check if they are mesh layers and will remove from ui
		if they are.
		
		:param removedLayers: list -> QgsMapLayer
		:return: bool -> True for successful, False for unsuccessful
		"""

		update_1d_ids = True
		for rlayer in removedLayers:
			if rlayer in self.layer_selection_signals:
				update_1d_ids = True
				self.layer_selection_signals.remove(rlayer)
			layer = tuflowqgis_find_layer(rlayer, search_type='layerId')
			if layer == self.currentLayer:
				self.currentLayer = None
			if layer is not None and isinstance(layer, QgsMeshLayer):
				for i in reversed(range(self.OpenResults.count())):
					item = self.OpenResults.item(i)
					itemName = item.text()
					if itemName == layer.name():
						self.tuResults.tuResults2D.removeResults([itemName])
			elif layer is not None and layer.name() in self.tuResults.tuResultsParticles.resultsParticles:
				self.tuResults.tuResultsParticles.removeResults([layer.name()], remove_vlayer=False)
			elif layer is not None and layer.name() in self.tuResults.tuResultsNcGrid.results:
				self.tuResults.tuResultsNcGrid.removeResults([layer.name()], remove_layer=False)
			elif layer is not None and isTSLayer(layer, self.tuResults.results):
				name = layer.dataProvider().dataSourceUri()
				if re.findall(re.escape(r'.gpkg|layername='), name, flags=re.IGNORECASE):
					name = re.split(re.escape(r'.gpkg|layername='), name, flags=re.IGNORECASE)[-1]
					name = name.split('|')[0]
				elif re.findall(r'^memory', name):
					name = layer.name()
				else:
					name = Path(name).stem

				del self.tuResults.tuResults1D.results1d[name]
				del self.tuResults.results[name]

				for i in reversed(range(self.OpenResults.count())):
					item = self.OpenResults.item(i)
					itemName = item.text()
					if itemName == name:
						self.OpenResults.takeItem(i)

		self.resultsChanged('force refresh', removedLayers)
		if update_1d_ids:
			self.tuResults.tuResults1D.updateSelectedResults(removedLayers)
				
		return True
	
	def loadProject(self):
		"""
		Load TUVIEW project
		
		:return:
		"""

		self.tuProject = TuProject(self)
		self.tuProject.load()
		self.tuResults.updateTimeUnits()
	
	def maxResultTypesChanged(self, event):
		"""
		Toggles the maximum result for selected type.

		:param event: dict -> { 'parent': DataSetTreeNode, 'index': DataSetTreeNode }
		:return:
		"""

		from .tuflowqgis_tuplot import TuPlot

		# update list of types with max activated
		self.tuResults.updateMinMaxTypes(event, 'max')

		# force selected result types in widget to be active types
		self.OpenResultTypes.selectionModel().clear()
		selection = QItemSelection()
		flags = QItemSelectionModel.Select
		for index in self.tuResults.activeResultsIndexes:
			selection.select(index, index)
			self.OpenResultTypes.selectionModel().select(selection, flags)

		# redraw plot and re-render map
		self.tuPlot.updateCrossSectionPlot()
		self.tuPlot.updateTimeSeriesPlot()
		self.renderMap()

	def minResultTypesChanged(self, event):
		"""
		Toggles the minimum result for selected type.

		:param event: dict -> { 'parent': DataSetTreeNode, 'index': DataSetTreeNode }
		:return:
		"""

		# update list of types with max activated
		self.tuResults.updateMinMaxTypes(event, 'min')

		# force selected result types in widget to be active types
		self.OpenResultTypes.selectionModel().clear()
		selection = QItemSelection()
		flags = QItemSelectionModel.Select
		for index in self.tuResults.activeResultsIndexes:
			selection.select(index, index)
			self.OpenResultTypes.selectionModel().select(selection, flags)

		# redraw plot and re-render map
		self.tuPlot.updateCrossSectionPlot()
		self.renderMap()

	def nextTimestep(self):
		"""
		Sets the current timestep to the next timestep.
		
		:return:
		"""
	
		cIndex = self.cboTime.currentIndex()
		nextIndex = cIndex + 1
		if nextIndex + 1 <= self.cboTime.count():
			self.cboTime.setCurrentIndex(nextIndex)
		else:
			self.timer.stop()
			self.btnTimePlay.setChecked(False)
			
		
	def playThroughTimesteps(self):
		"""
		Auto play through the timesteps (starting at current timestep).
		
		:return:
		"""
		
		if self.btnTimePlay.isChecked():
			if self.tuResults.activeResults:
				self.timer = QTimer()
				self.timer.setInterval(self.tuOptions.playDelay * 1000)  # sec to ms
				self.timer.setSingleShot(False)
				self.timer.timeout.connect(self.nextTimestep)
				self.timer.start()
			else:
				self.btnTimePlay.setChecked(False)
		else:
			try:
				self.timer.stop()
			except:
				pass
	
	def plottingViewChanged(self):
		"""
		Sets visible the relevant toolbar for active plot.

		:return:
		"""

		# update active toolbar
		self.tuPlot.tuPlotToolbar.setToolbarActive(self.tabWidget.currentIndex())
		
		# update the enabled result types
		# self.currentLayerChanged()
		# self.setTsTypesEnabled()
		# self.tuPlot.updateCurrentPlot(self.tabWidget.currentIndex(), plot='1d only')

	def moveOpenResults(self, layoutType):
		"""
		Moves open results list widget.

		layoutType:
			"plot": original position with plot visible
			"narrow": place under result types
		"""

		if layoutType.lower() == "narrow":
			self.ResultTypeSplitter.addWidget(self.OpenResultsLayout)
			totalHeight = self.ResultTypeSplitter.sizeHint().height()
			self.ResultTypeSplitter.setSizes([totalHeight * 9/10, totalHeight * 1/10])
		elif layoutType.lower() == "plot":
			self.PlotOptionSplitter.insertWidget(0, self.OpenResultsLayout)

	def onDockLocationChange(self, area=None):
		"""
		Saves the new location of TUFLOW Viewer dock. Only used, however, if
		the default layout is "narrow", otherwise initial location is the bottom.
		"""

		if area is None or area == Qt.NoDockWidgetArea:
			return

		if self.PlotLayout.isVisible():
			return

		QSettings().setValue("TUFLOW/tuview_docklocation", area)

		if self.iface is not None:
			if self.iface.mainWindow().tabifiedDockWidgets(self):
				QSettings().setValue("TUFLOW/tuview_isdocktabified", True)
				tabifiedWith = [x.windowTitle() for x in self.iface.mainWindow().tabifiedDockWidgets(self)]
				QSettings().setValue("TUFLOW/tuview_tabifiedwith", tabifiedWith)
			else:
				QSettings().setValue("TUFLOW/tuview_isdocktabified", False)
				QSettings().setValue("TUFLOW/tuview_tabifiedwith", [])

	def onTopLevelChange(self, topLevel=None):
		"""
		Saves the location of TUFLOW Viewer if the dock is floating
		or not.
		"""

		if topLevel is None:
			return

		if self.PlotLayout.isVisible():
			return

		QSettings().setValue("TUFLOW/tuview_isdockfloating", topLevel)

	def plotWindowVisibilityToggled(self, initialisation=False):
		"""
		Sets the plot window visible / not visible
		"""

		if initialisation:
			self.originalWidth = self.PlotLayout.minimumSizeHint().width() + self.ResultLayout.minimumSizeHint().width()
			self.PlotLayout.setVisible(False)
			self.SecondMenu.setVisible(True)
			self.OpenResultsWidget.setVisible(False)
			self.moveOpenResults("narrow")
			narrowWidth = self.pbShowPlotWindow.minimumSizeHint().width() + \
			              self.mainMenuSecond_2.minimumSizeHint().width()
			self.dockWidgetContents.setMinimumWidth(narrowWidth)
			self.label_5.setMinimumWidth(self.label_5.minimumSizeHint().width())
			if self.iface is not None:
				docks = [x.windowTitle() for x in self.iface.mainWindow().findChildren(QDockWidget)]
				if "TUFLOW Viewer" in docks:
					self.iface.mainWindow().resizeDocks([self], [narrowWidth], Qt.Horizontal)

			return

		if self.PlotLayout.isVisible():
			QSettings().setValue("TUFLOW/tuview_previouslayout", "narrow")
			self.PlotLayout.setVisible(False)
			self.SecondMenu.setVisible(True)
			self.OpenResultsWidget.setVisible(False)
			self.moveOpenResults("narrow")
			narrowWidth = self.pbShowPlotWindow.minimumSizeHint().width() + \
			              self.mainMenuSecond_2.minimumSizeHint().width()
			self.dockWidgetContents.setMinimumWidth(narrowWidth)
			self.label_5.setMinimumWidth(self.label_5.minimumSizeHint().width())
			if self.iface is not None:
				docks = [x.windowTitle() for x in self.iface.mainWindow().findChildren(QDockWidget)]
				if "TUFLOW Viewer" in docks:
					self.iface.mainWindow().resizeDocks([self], [narrowWidth], Qt.Horizontal)
		else:
			QSettings().setValue("TUFLOW/tuview_previouslayout", "plot")
			self.PlotLayout.setVisible(True)
			self.SecondMenu.setVisible(False)
			self.OpenResultsWidget.setVisible(True)
			self.moveOpenResults("plot")
			# self.dockWidgetContents.setMinimumWidth(self.originalWidth)
			# self.iface.mainWindow().resizeDocks([self], [self.originalWidth], Qt.Horizontal)
			plotWidth = self.PlotLayout.minimumSizeHint().width() + self.ResultLayout.minimumSizeHint().width()
			if self.iface is not None:
				self.iface.mainWindow().resizeDocks([self], [plotWidth], Qt.Horizontal)
		
	def projectCleared(self):
		"""
		Clears 1D results when project is cleared. 2D results should be auto cleared when layers are removed.
		
		:return:
		"""
		
		self.tuResults.results.clear()
		self.tuResults.tuResults2D.results2d.clear()
		self.tuResults.tuResults1D.results1d.clear()
		self.OpenResults.clear()
		self.tuResults.resetResultTypes()
	
	def saveProject(self):
		"""
		Saves the project. Use QAction to save project rather than QgsProject write() method since this seems
		to cause issues when writing to .qgs
		
		:return:
		"""

		if self.iface is not None:
			self.iface.mainWindow().findChild(QAction, 'mActionSaveProject').trigger()
		self.project.projectSaved.connect(self.projectSaved)
	
	def projectSaved(self):
		"""
		Saves Tuview settings to project

		:return:
		"""
		
		self.project.projectSaved.disconnect(self.projectSaved)
		
		tuProject = TuProject(self)
		tuProject.save()
		
		# need to resave .qgz or .qgs file since
		# the above steps are done after the original
		# save - but to stop from crashing need to add delay
		self.saveTimer = QTimer()
		self.saveTimer.setInterval(200)
		self.saveTimer.setSingleShot(True)
		self.saveTimer.timeout.connect(self.saveProject)
		self.saveTimer.start()
	
	def qgisConnect(self):
		"""
		Connect signals

		:return:
		"""

		qv = Qgis.QGIS_VERSION_INT
		# self.firstConnection = False

		if not self.connected:

			# dock widget location changed
			self.dockLocationChanged.connect(self.onDockLocationChange)
			self.topLevelChanged.connect(self.onTopLevelChange)
			
			# hide/show plot window
			self.pbHidePlotWindow.clicked.connect(self.plotWindowVisibilityToggled)
			self.pbShowPlotWindow.clicked.connect(self.plotWindowVisibilityToggled)

			# time
			self.cboTime.currentIndexChanged.connect(self.timeSliderChanged)
			self.sliderTime.valueChanged.connect(lambda: self.timeComboChanged(0))
			self.btnFirst.clicked.connect(lambda: self.timeComboChanged(-2))
			self.btnPrev.clicked.connect(lambda: self.timeComboChanged(-1))
			self.btnNext.clicked.connect(lambda: self.timeComboChanged(1))
			self.btnLast.clicked.connect(lambda: self.timeComboChanged(2))
			self.btnTimePlay.clicked.connect(self.playThroughTimesteps)
			self.btn2dLock.clicked.connect(self.timestepLockChanged)
			self.cbShowAsDates.clicked.connect(self.showAsDatesToggled)

			# qgis time controller
			if qv >= 31300:
				if self.iface is not None:
					self.iface.mapCanvas().temporalRangeChanged.connect(self.qgsTimeChanged)
			
			# results
			# self.OpenResults.itemClicked.connect(lambda: self.resultsChanged('item clicked'))
			self.resultSelectionChangeSignal = self.OpenResults.itemSelectionChanged.connect(lambda: self.resultsChanged('selection changed'))
			
			# result types
			self.OpenResultTypes.secondAxisClicked.connect(self.secondaryAxisResultTypesChanged)
			self.OpenResultTypes.maxClicked.connect(self.maxResultTypesChanged)
			self.OpenResultTypes.minClicked.connect(self.minResultTypesChanged)
			self.OpenResultTypes.doubleClicked.connect(self.resultTypeDoubleClicked)
			self.OpenResultTypes.leftClicked.connect(self.resultTypesChanged)
			
			# Plotting buttons
			self.cbShowCurrentTime.stateChanged.connect(lambda: self.tuPlot.clearPlot2(TuPlot.TimeSeries, TuPlot.DataCurrentTime))
			self.tuPlot.tuPlotToolbar.fluxSecAxisButton.released.connect(lambda: self.secondaryAxisResultTypesChanged(None))
			
			# switching between plots
			self.tabWidget.currentChanged.connect(self.plottingViewChanged)
			
			# interface
			if self.iface is not None:
				self.iface.currentLayerChanged.connect(self.currentLayerChanged)
			
			# project
			if self.firstConnection:
				self.project.layersWillBeRemoved.connect(self.layersRemoved)
				if not self.connectSave:
					self.project.projectSaved.connect(self.projectSaved)
					self.connectSave = True
			self.project.layersAdded.connect(self.layersAdded)
			self.project.cleared.connect(self.projectCleared)

			# layer
			self.selectionChangeConnected = False
			self.currentLayerChanged()
			# 1D cross sections
			self.xsConnectedLayers = []
			
			self.connected = True

		self.firstConnection = False
	
	def qgisDisconnect(self, completely_remove=False):
		"""
		Disconnect signals


		:return:
		"""

		qv = Qgis.QGIS_VERSION_INT

		if completely_remove:
			self.tuMenuBar.qgisDisconnect()
			self.tuMenuBar.clear()
			self.tuMenuBarSecond.qgisDisconnect()
			self.tuMenuBarSecond.clear()
			self.tuContextMenu.qgisDisconnect()
			self.tuPlot.tuPlotToolbar.qgisDisconnect()

		if self.connected or completely_remove:

			# dock widget location changed
			try:
				self.dockLocationChanged.disconnect(self.onDockLocationChange)
			except:
				pass
			try:
				self.topLevelChanged.disconnect(self.onTopLevelChange)
			except:
				pass

			# time
			try:
				self.cboTime.currentIndexChanged.disconnect()
			except:
				pass
			try:
				self.sliderTime.valueChanged.disconnect()
			except:
				pass
			try:
				self.btnFirst.clicked.disconnect()
			except:
				pass
			try:
				self.btnPrev.clicked.disconnect()
			except:
				pass
			try:
				self.btnNext.clicked.disconnect()
			except:
				pass
			try:
				self.btnLast.clicked.disconnect()
			except:
				pass
			try:
				self.btnTimePlay.clicked.disconnect()
			except:
				pass
			try:
				self.btn2dLock.clicked.disconnect()
			except:
				pass

			# qgis time controller
			if qv >= 31300:
				try:
					if self.iface is not None:
						self.iface.mapCanvas().temporalRangeChanged.disconnect(self.qgsTimeChanged)
				except:
					pass
			
			# results
			try:
				self.OpenResults.itemSelectionChanged.disconnect()
			except:
				pass
			# try:
			# 	self.OpenResults.itemClicked.disconnect()
			# except:
			# 	pass
			
			# result types
			try:
				self.OpenResultTypes.secondAxisClicked.disconnect()
			except:
				pass
			try:
				self.OpenResultTypes.maxClicked.disconnect()
			except:
				pass
			try:
				self.OpenResultTypes.doubleClicked.disconnect()
			except:
				pass
			try:
				self.OpenResultTypes.leftClicked.disconnect()
			except:
				pass
			
			# Plotting buttons
			try:
				self.cbShowCurrentTime.clicked.disconnect()
			except:
				pass
			try:
				self.tuPlot.tuPlotToolbar.fluxSecAxisButton.released.disconnect()
			except:
				pass
			
			# switching between plots
			try:
				self.tabWidget.currentChanged.disconnect()
			except:
				pass
			
			# interface
			try:
				if self.iface is not None:
					self.iface.currentLayerChanged.disconnect(self.currentLayerChanged)
			except:
				pass
			
			# project
			try:
				self.project.layersAdded.disconnect(self.layersAdded)
			except:
				pass
			if completely_remove:
				try:
					self.project.layersWillBeRemoved.disconnect(self.layersRemoved)
				except:
					pass
				try:
					self.project.projectSaved.disconnect(self.projectSaved)
				except:
					pass
			try:
				self.project.cleared.disconnect(self.projectCleared)
			except:
				pass
			
			# layer
			if self.selectionChangeConnected or completely_remove:
				try:
					self.currentLayer.selectionChanged.disconnect(self.selectionChanged)
				except:
					pass
				try:
					self.selectionChangeConnected = False
				except:
					pass

			for layer in findAllMeshLyrs():
				try:
					layer.nameChanged.disconnect()
				except:
					pass
				try:
					signal = self.tuView.tuResults.tuResults2D.layer_style_changed_signals.get(layer.id())
					if signal is not None:
						layer.rendererChanged.disconnect(signal)
						del self.tuView.tuResults.tuResults2D.layer_style_changed_signals[layer.id()]
				except:
					pass
				if Qgis.QGIS_VERSION_INT >= 32800:
					try:
						signal = self.tuView.tuResults.tuResults2D.layer_reloaded_signals.get(layer.id())
						if signal is not None:
							layer.reloaded.disconnect(signal)
							del self.tuView.tuResults.tuResults2D.layer_reloaded_signals[layer.id()]
					except:
						pass
			
			if completely_remove:
				meshLayers = findAllMeshLyrs()
				for ml in meshLayers:
					layer = tuflowqgis_find_layer(ml)
					try:
						layer.dataProvider().datasetGroupsAdded.disconnect(self.datasetGroupsAdded)
					except:
						pass

			# plotting
			try:
				self.tuPlot.verticalMesh_action.triggered.disconnect(self.tuPlot.vmeshToggled)
			except:
				pass
			
			self.connected = False
	
	def refreshCurrentPlot(self, **kwargs):
		"""
		Update the current plot

		:return:
		"""

		update = kwargs['update'] if 'update' in kwargs.keys() else 'all'
		
		plotNo = self.tabWidget.currentIndex()
		self.tuPlot.updateCurrentPlot(plotNo, update=update)
	
	def renderMap(self):
		"""
		Renders the mesh layer based on selected mesh results, result types, and current time

		:return:
		"""

		self.tuResults.tuResults2D.renderMap()
		
	def repaintRequested(self, layer):
		"""
		
		
		:return:
		"""

		if layer in self.tuResults.tuResults2D.activeMeshLayers:
			rs = layer.rendererSettings()
			if rs.nativeMeshSettings().isEnabled():
				self.tuOptions.showGrid = True
				self.tuPlot.tuPlotToolbar.meshGridAction.setChecked(True)
			else:
				self.tuOptions.showGrid = False
				self.tuPlot.tuPlotToolbar.meshGridAction.setChecked(False)
			if rs.triangularMeshSettings().isEnabled():
				self.tuOptions.showTriangles = True
			else:
				self.tuOptions.showTriangles = False
			
	
	def resultsChanged(self, *args):
		"""
		Updates the list of selected results when selected mesh layers in list widget is changed.

		:return:
		"""

		if self.in_results_changed:
			return

		self.in_results_changed = True

		# check if routine has been called already - there are 2 signals and no point doubling up
		if self.resultChangeSignalCount == 0:
			self.resultChangeSignalCount += 1
			
			# render only selected results
			self.tuResults.tuResults2D.updateActiveMeshLayers(*args)
			
			# update 2D results class
			self.tuResults.updateResultTypes(select_first_dataset=False)
			# self.timeSliderChanged()
			
			# render map
			self.renderMap()
			
			if not self.OpenResults.selectedItems():
				self.resultChangeSignalCount = 0
			if args:
				if args[0] == 'item clicked' or self.iface == None:
					self.resultChangeSignalCount = 0
		else:
			if args:
				if args[0] == 'force refresh':
					# render only selected results
					self.tuResults.tuResults2D.updateActiveMeshLayers()
					
					# update 2D results class
					self.tuResults.updateResultTypes()
					
					# render map
					self.renderMap()
					
			self.resultChangeSignalCount = 0

		self.in_results_changed = False
		
	def resultTypesChanged(self, event):
		"""
		Updates the active scalar and active vector datasets based on selected result types in tree widget

		:param event: dict -> 'modelIndex': QModelIndex
							  'button': mouse button e.g. Qt.RightButton
		:return:
		"""

		# update 1D and 2D results - map re-render and plot re-draw is in method
		if event['button'] == Qt.LeftButton:
			if not self.doubleClickEvent:
				self.tuResults.updateActiveResultTypes(event['modelIndex'], skip_already_selected=event['drag_event'])
		self.doubleClickEvent = False
	
	def resultTypeDoubleClicked(self, event):
		"""
		Event triggered when a result type is double clicked. Open properties dialog if a mesh layer result type.
		
		:param event: dict -> 'parent': parent DataSetTreeNode
		                      'item': clicked DataSetTreeNode
		:return:
		"""
		
		#self.doubleClickEvent = True
		
		# what happens if there is more than one active mesh layer
		if len(self.tuResults.tuResults2D.activeMeshLayers) > 1:
			if self.iface is not None:
				self.meshDialog = tuflowqgis_meshSelection_dialog(self.iface, self.tuResults.tuResults2D.activeMeshLayers,
				                                                  'Select Which Result To Open Properties For...')
				self.meshDialog.exec_()
				if self.meshDialog.selectedMesh is None:
					return False
				else:
					meshLayer = tuflowqgis_find_layer(self.meshDialog.selectedMesh)
		else:
			meshLayer = self.tuResults.tuResults2D.activeMeshLayers[0]
		
		if event is not None:
			if event['parent'].ds_name == 'Map Outputs':
				if self.iface is not None:
					self.iface.showLayerProperties(meshLayer)
		else:  # context menu
			if self.tuContextMenu.resultTypeContextItem.parentItem.ds_name == 'Map Outputs':
				if self.iface is not None:
					self.iface.showLayerProperties(meshLayer)
		
		return True
	
	def secondaryAxisResultTypesChanged(self, event):
		"""
		Updates when secondary axis box is clicked.

		:param event: dict -> { 'parent': DataSetTreeNode, 'index': DataSetTreeNode }
		:return:
		"""

		# update list of types sitting on secondary axis
		self.tuResults.updateSecondaryAxisTypes(event)
		
		# redraw plot
		# self.tuPlot.updateCurrentPlot(self.tabWidget.currentIndex(), update='1d only')
		self.tuPlot.changeLineAxis(event)
		
		# force selected result types in widget to be active types
		#self.OpenResultTypes.selectionModel().clear()
		#selection = QItemSelection()
		#flags = QItemSelectionModel.Select
		#for index in self.tuResults.activeResultsIndexes:
		#	selection.select(index, index)
		#	self.OpenResultTypes.selectionModel().select(selection, flags)
	
	def selectionChanged(self):
		"""
		Updates the plotting based on the selection.

		:return:
		"""

		# update 1D results class
		self.tuResults.tuResults1D.updateSelectedResults()
		
		# make sure selected result match active results
		self.tuResults.checkSelectedResults()
		
		# plot
		self.tuPlot.tuPlot1D.plot1dResults()
	
	def timeComboChanged(self, enum):
		"""
		Update the displayed time in the combobox based on the time slider

		:param enum: int -> 0: set to slider position
							1: set to next time
							2: set to end time
						   -1: set to previous time
						   -2: set to first time
		:return:
		"""

		if enum == 0:  # set to slider position
			i = self.sliderTime.sliderPosition()
			self.cboTime.setCurrentIndex(i)
		
		elif enum == -2:  # set to first time
			self.cboTime.setCurrentIndex(0)
		
		elif enum == -1:  # set to prev time
			i = self.cboTime.currentIndex()
			if i > 0:
				self.cboTime.setCurrentIndex(i - 1)
		
		elif enum == 1:  # set to next time
			i = self.cboTime.currentIndex()
			if i + 1 < self.cboTime.count():
				self.cboTime.setCurrentIndex(i + 1)
		
		elif enum == 2:  # set to last time
			self.cboTime.setCurrentIndex(self.cboTime.count() - 1)
	
	def timeSliderChanged(self):
		"""
		Update the time slider to current time in time combobox and update the active time

		:return:
		"""

		self.tuResults.updateActiveTime()
		
		self.renderMap()
		
		# update red time slider on plot
		# if not self.tuPlot.timeSeriesPlotFirst:
		if self.cbShowCurrentTime.isChecked():
			self.tuPlot.clearPlot2(TuPlot.TimeSeries, TuPlot.DataCurrentTime, clear_selection=False)
			# self.tuPlot.drawPlot(TuPlot.TimeSeries, [], [], [], [], refresh_only=True)
		# update long profile / cross section plots with new timestep
		if not self.tuPlot.profilePlotFirst:
			self.tuPlot.updateCrossSectionPlot()
		# vertical profile
		if not self.tuPlot.verticalProfileFirst:
			self.tuPlot.updateVerticalProfilePlot()
			
	def timestepLockChanged(self, event=None, switch=True):
		"""
		Toggles the lock for displaying Map Output timesteps only.
		
		:return:
		"""
		
		if switch:
			self.lock2DTimesteps = False if self.lock2DTimesteps else True
		svg = "/locked.svg" if self.lock2DTimesteps else "/unlocked.svg"
		lock2DIcon = QgsApplication.getThemeIcon(svg)
		self.btn2dLock.setIcon(lock2DIcon)
		
		self.tuResults.updateResultTypes()

	def qgsTimeChanged(self):
		qv = Qgis.QGIS_VERSION_INT
		if qv < 31600:
			self.qgsTimeChanged_old()
		else:
			self.qgsTimeChanged_31600()

	def qgsTimeChanged_old(self):
		"""

		"""

		if self.iface is not None:
			if self.tuResults.timeSpec != self.iface.mapCanvas().temporalRange().begin().timeSpec():
				self.tuResults.updateTemporalProperties()
				return

			t = self.tuResults.getTuViewTimeFromQgsTime()
			tf = None
			if type(t) is datetime:
				if self.tuOptions.xAxisDates:
					tf = self.tuResults._dateFormat.format(t)  # time formatted
				else:
					if t in self.tuResults.date2time:
						t = self.tuResults.date2time[t]
					elif t in self.tuResults.date_tspec2date:
						t = self.tuResults.date_tspec2time[t]
			if tf is None:
				tf = convertTimeToFormattedTime(t, unit=self.tuOptions.timeUnits)  # time formatted
			for i in range(self.cboTime.count()):
				if self.cboTime.itemText(i) == tf:
					self.cboTime.setCurrentIndex(i)
					return

	def qgsTimeChanged_31600(self):
		"""

		"""

		if self.iface is not None:
			if self.tuResults.timeSpec != self.iface.mapCanvas().temporalRange().begin().timeSpec():
				self.tuResults.updateTemporalProperties()
				return

		t = self.tuResults.getTuViewTimeFromQgsTime()
		tf = None
		if type(t) is datetime:
			if self.tuOptions.xAxisDates:
				tf = self.tuResults._dateFormat.format(t)  # time formatted
			else:
				for i, (cboTime, timeKey) in enumerate(self.tuResults.cboTime2timekey.items()):
					time = self.tuResults.timekey2time[timeKey]
					tf = cboTime
					if self.tuOptions.timeUnits == 's':
						date = self.tuOptions.zeroTime + timedelta(seconds=time)
					else:
						try:
							date = self.tuOptions.zeroTime + timedelta(hours=time)
						except OverflowError:
							date = self.tuOptions.zeroTime + timedelta(seconds=time)
					if t == date:
						break
					if i == 0:
						diff = abs((t - date).total_seconds())
					if date > t:
						diff2 = abs((t - date).total_seconds())
						if diff < diff2:
							tf = [x for x in self.tuResults.cboTime2timekey][max(0, i-1)]
							break
						else:
							break
					else:
						diff = abs((t - date).total_seconds())

		for i in range(self.cboTime.count()):
			if self.cboTime.itemText(i) == tf:
				self.cboTime.setCurrentIndex(i)
				return

	def showAsDatesToggled(self):
		self.tuOptions.xAxisDates = self.cbShowAsDates.isChecked()
		self.tuResults.updateTimeUnits()

	def iconSizeChanged(self, size):
		self.toolbarIconSizeChanged(size, self.tuPlot.tuPlotToolbar.mpltoolbarTimeSeries, self.mplToolbarFrame)
		self.toolbarIconSizeChanged(size, self.tuPlot.tuPlotToolbar.mpltoolbarLongPlot, self.mplToolbarFrame)
		self.toolbarIconSizeChanged(size, self.tuPlot.tuPlotToolbar.mpltoolbarLongPlot, self.mplToolbarFrame)
		self.toolbarIconSizeChanged(size, self.tuPlot.tuPlotToolbar.mpltoolbarVerticalProfile, self.mplToolbarFrame)
		self.toolbarIconSizeChanged(size, self.tuPlot.tuPlotToolbar.mapOutputPlotToolbar, self.MapOutputPlotFrame)
		self.toolbarIconSizeChanged(size, self.tuPlot.tuPlotToolbar.mesh3dPlotToolbar, self.Mesh3DToolbarFrame)
		for i in range(4):
			_, viewToolbar, _ = self.tuPlot.tuPlotToolbar.plotNoToToolbar[i]
			self.toolbarIconSizeChanged(size, viewToolbar.viewToolbar, self.ViewToolbarFrame)

	def toolbarIconSizeChanged(self, size=None, toolbar=None, frame=None):
		qv = Qgis.QGIS_VERSION_INT

		w = self.tuOptions.iconSize
		if qv >= 31600:
			w = int(QgsApplication.scaleIconSize(self.tuOptions.iconSize, True))

		if toolbar is None or frame is None:
			return

		w2 = int(np.ceil(w * 1.5))
		w3 = int(np.ceil(w2 * len(toolbar.actions())))
		w4 = int(np.ceil(w3 + w2 * 2))

		frame.setMinimumWidth(w4)
		frame.setMinimumHeight(w2)
		toolbar.setIconSize(QSize(w, w))
		toolbar.resize(QSize(w4, w2))

		actions = [x for x in toolbar.actions()]
		toolbar.clear()
		[toolbar.addAction(x) for x in actions]

		toolbar.update()
		toolbar.repaint()

	def reorderOpenResults(self, index, action):
		selection = [x.text() for x in self.OpenResults.selectedItems()]

		# disconnect item changed signal
		try:
			self.OpenResults.disconnect(self.resultSelectionChangeSignal)
			self.resultSelectionChangeSignal = None
		except:
			pass

		item = self.OpenResults.takeItem(index.row())
		if action == 'up':
			self.OpenResults.insertItem(max(index.row() - 1, 0), item)
		elif action == 'down':
			self.OpenResults.insertItem(min(index.row() + 1, self.OpenResults.count()), item)
		elif action == 'top':
			self.OpenResults.insertItem(0, item)
		elif action == 'bottom':
			self.OpenResults.addItem(item)

		for i in range(self.OpenResults.count()):  # reapply selection
			if self.OpenResults.item(i).text() in selection:
				self.OpenResults.item(i).setSelected(True)

		# reconnect signal
		self.resultSelectionChangeSignal = self.OpenResults.itemSelectionChanged.connect(lambda: self.resultsChanged('selection changed'))
