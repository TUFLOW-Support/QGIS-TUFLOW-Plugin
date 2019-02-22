import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from qgis.gui import *
from PyQt5.QtWidgets import *
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tumenufunctions import TuMenuFunctions


class TuContextMenu():
	"""
	Class for handling Tuview context menus.
	
	"""
	
	def __init__(self, TuView):
		self.tuView = TuView
		self.tuPlot = TuView.tuPlot
		self.iface = TuView.iface
		self.resultTypeContextItem = None  # stores clicked result type for context menu
		
		# menu function class
		self.tuMenuFunctions = TuMenuFunctions(TuView)
		
	def loadPlotMenu(self, plotNo, **kwargs):
		"""
		Load context plot menu and items.
		
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:param kwargs: dict -> key word arguments
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		update = kwargs['update'] if 'update' in kwargs.keys() else False
		
		if plotNo == 0:
			toolbar = self.tuPlot.tuPlotToolbar.lstActionsTimeSeries
			viewToolbar = self.tuPlot.tuPlotToolbar.viewToolbarTimeSeries
		elif plotNo == 1:
			toolbar = self.tuView.tuPlot.tuPlotToolbar.lstActionsLongPlot
			viewToolbar = self.tuPlot.tuPlotToolbar.viewToolbarLongPlot
		elif plotNo == 2:
			toolbar = self.tuView.tuPlot.tuPlotToolbar.lstActionsCrossSection
			viewToolbar = self.tuPlot.tuPlotToolbar.viewToolbarCrossSection
		
		if not update:  # only create menu if not just an update (updates when switching between plot type tabs)
			self.plotMenu = QMenu(self.tuView)
		iconRefreshPlot = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "RefreshPlotBlack.png"))
		iconClearPlot = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons" "ClearPlot.png"))
		
		self.userPlotDataManager_action = viewToolbar.userPlotDataManagerButton.defaultAction()
		self.freezeAxisLimits_action = viewToolbar.freezeXYAxisButton.defaultAction()
		self.freezeAxisXLimits_action = viewToolbar.freezeXAxisButton.defaultAction()
		self.freezeAxisYLimits_action = viewToolbar.freezeYAxisButton.defaultAction()
		self.refreshCurrentPlotWindow_action = QAction(iconRefreshPlot, 'Refresh Plot Window', self.plotMenu)
		self.clearPlotWindow_action = QAction(iconClearPlot, 'Clear Plot Window', self.plotMenu)
		self.exportAsCSV_action = QAction('Export Plot As CSV', self.plotMenu)
		
		self.plotMenu.addAction(self.userPlotDataManager_action)
		self.plotMenu.addSeparator()
		self.plotMenu.addAction(toolbar[0])
		self.plotMenu.addAction(toolbar[4])
		self.plotMenu.addAction(toolbar[5])
		self.plotMenu.addAction(toolbar[7])
		self.plotMenu.addSeparator()
		self.plotMenu.addAction(self.freezeAxisLimits_action)
		self.plotMenu.addAction(self.freezeAxisXLimits_action)
		self.plotMenu.addAction(self.freezeAxisYLimits_action)
		self.plotMenu.addSeparator()
		self.plotMenu.addAction(self.refreshCurrentPlotWindow_action)
		self.plotMenu.addAction(self.clearPlotWindow_action)
		self.plotMenu.addSeparator()
		copyMenu = self.plotMenu.addMenu('&Copy')
		copyMenu.addAction(self.tuView.tuMenuBar.exportDataToClipboard_action)
		copyMenu.addAction(self.tuView.tuMenuBar.exportImageToClipboard_action)
		exportMenu = self.plotMenu.addMenu('&Export')
		exportMenu.addAction(self.tuView.tuPlot.tuPlotToolbar.lstActionsTimeSeries[9])
		exportMenu.addAction(self.exportAsCSV_action)
		
		#self.userPlotDataManager_action.triggered.connect(self.tuMenuFunctions.openUserPlotDataManager)
		self.freezeAxisLimits_action.triggered.connect(viewToolbar.freezeXYAxis)
		self.freezeAxisXLimits_action.triggered.connect(viewToolbar.freezeXAxis)
		self.freezeAxisYLimits_action.triggered.connect(viewToolbar.freezeYAxis)
		self.refreshCurrentPlotWindow_action.triggered.connect(self.tuView.refreshCurrentPlot)
		self.clearPlotWindow_action.triggered.connect(
			lambda: self.tuView.tuPlot.clearPlot(self.tuView.tabWidget.currentIndex(), clear_rubberband=True, clear_selection=True))
		self.exportAsCSV_action.triggered.connect(self.tuMenuFunctions.exportCSV)
		
		return True
	
	def showPlotMenu(self, pos, plotNo):
		"""
		Context menus for plot windows.
		
		:param pos: QPoint
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if plotNo == 0:
			self.plotMenu.popup(self.tuPlot.plotWidgetTimeSeries.mapToGlobal(pos))
		elif plotNo == 1:
			self.plotMenu.popup(self.tuPlot.plotWidgetLongPlot.mapToGlobal(pos))
		elif plotNo == 2:
			self.plotMenu.popup(self.tuPlot.plotWidgetCrossSection.mapToGlobal(pos))
		else:
			return False
		
		return True
	
	def loadResultsMenu(self):
		"""
		Load context plot menu and items.

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.resultsMenu = QMenu(self.tuView)
		closeResultsIcon = QgsApplication.getThemeIcon("/mActionRemoveLayer.svg")
		
		self.load1d2dResults_action = QAction('Load Results', self.resultsMenu)
		self.load2dResults_action = QAction('Load Results - Map Outputs', self.resultsMenu)
		self.load1dResults_action = QAction('Load Results - Time Series', self.resultsMenu)
		self.remove1d2dResults_action = QAction(closeResultsIcon, 'Close Results', self.resultsMenu)
		self.remove2dResults_action = QAction('Close Results - Map Outputs', self.resultsMenu)
		self.remove1dResults_action = QAction('Close Results - Time Series', self.resultsMenu)
		
		self.resultsMenu.addAction(self.load1d2dResults_action)
		self.resultsMenu.addAction(self.load2dResults_action)
		self.resultsMenu.addAction(self.load1dResults_action)
		self.resultsMenu.addSeparator()
		self.resultsMenu.addAction(self.remove1d2dResults_action)
		self.resultsMenu.addAction(self.remove2dResults_action)
		self.resultsMenu.addAction(self.remove1dResults_action)
		
		self.load2dResults_action.triggered.connect(self.tuMenuFunctions.load2dResults)
		self.load1dResults_action.triggered.connect(self.tuMenuFunctions.load1dResults)
		self.load1d2dResults_action.triggered.connect(self.tuMenuFunctions.load1d2dResults)
		self.remove1d2dResults_action.triggered.connect(self.tuMenuFunctions.remove1d2dResults)
		self.remove2dResults_action.triggered.connect(self.tuMenuFunctions.remove2dResults)
		self.remove1dResults_action.triggered.connect(self.tuMenuFunctions.remove1dResults)
		
		return True
	
	def showResultsMenu(self, pos):
		"""
		Context menu for open results list widget.
		
		:param pos: QPoint
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.resultsMenu.popup(self.tuView.OpenResults.mapToGlobal(pos))
		
		return True
	
	def loadResultTypesMenu(self):
		"""
		Load context menu and items for the result types dataview
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.resultTypesMenu = QMenu(self.tuView)
		
		self.setToMaximumResult_action = QAction('Maximum', self.resultTypesMenu)
		self.setToMaximumResult_action.setCheckable(True)
		self.setToSecondaryAxis_action = QAction('Secondary Axis', self.resultTypesMenu)
		self.setToSecondaryAxis_action.setCheckable(True)
		self.saveDefaultStyleRamp_action = QAction('Colour Ramp', self.resultTypesMenu)
		self.saveDefaultStyleMap_action = QAction('Colour Map (Exact Values and Colours)', self.resultTypesMenu)
		self.saveDefaultVectorStyle_action = QAction('Save Vector Style as Default', self.resultTypesMenu)
		self.loadDefaultStyle_action = QAction('Load Default Style', self.resultTypesMenu)
		self.loadDefaultVectorStyle_action = QAction('Load Default Vector Style', self.resultTypesMenu)
		self.propertiesDialog_action = QAction('Properties', self.resultTypesMenu)
		
		self.resultTypesMenu.addAction(self.setToMaximumResult_action)
		self.resultTypesMenu.addAction(self.setToSecondaryAxis_action)
		self.resultTypesMenu.addSeparator()
		self.saveStyleMenu = self.resultTypesMenu.addMenu('Save Style as Default')
		self.saveStyleMenu.addAction(self.saveDefaultStyleRamp_action)
		self.saveStyleMenu.addAction(self.saveDefaultStyleMap_action)
		self.resultTypesMenu.addAction(self.saveDefaultVectorStyle_action)
		self.resultTypesMenu.addAction(self.loadDefaultStyle_action)
		self.resultTypesMenu.addAction(self.loadDefaultVectorStyle_action)
		self.resultTypesMenu.addSeparator()
		self.resultTypesMenu.addAction(self.propertiesDialog_action)
		
		self.setToMaximumResult_action.triggered.connect(self.tuMenuFunctions.toggleResultTypeToMax)
		self.setToSecondaryAxis_action.triggered.connect(self.tuMenuFunctions.toggleResultTypeToSecondaryAxis)
		self.saveDefaultStyleRamp_action.triggered.connect(lambda: self.tuMenuFunctions.saveDefaultStyleScalar('color ramp', use_clicked=True))
		self.saveDefaultStyleMap_action.triggered.connect(lambda: self.tuMenuFunctions.saveDefaultStyleScalar('color map', use_clicked=True))
		self.saveDefaultVectorStyle_action.triggered.connect(lambda: self.tuMenuFunctions.saveDefaultStyleVector(use_clicked=True))
		self.loadDefaultStyle_action.triggered.connect(lambda: self.tuMenuFunctions.loadDefaultStyleScalar(use_clicked=True))
		self.loadDefaultVectorStyle_action.triggered.connect(lambda: self.tuMenuFunctions.loadDefaultStyleVector(use_clicked=True))
		self.propertiesDialog_action.triggered.connect(lambda: self.tuView.resultTypeDoubleClicked(None))
		
		return True
	
	def showResultTypesMenu(self, pos):
		"""
		Context menu for open result types dataview.
		
		:param pos: QPoint
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		modelIndex = self.tuView.OpenResultTypes.indexAt(pos)
		if modelIndex.isValid():
			item = self.tuView.OpenResultTypes.model().index2item(modelIndex)
		else:
			item = None
		
		if item is None:
			self.resultTypeContextItem = None
			return False
		else:
			if item.ds_name.lower() == 'none':
				self.resultTypeContextItem = None
				return False
			elif item.parentItem == self.tuView.OpenResultTypes.model().rootItem:
				self.resultTypeContextItem = None
				return False
			else:
				# secondary axis
				self.setToSecondaryAxis_action.setEnabled(True)
				if item.secondaryActive:
					self.setToSecondaryAxis_action.setChecked(True)
				else:
					self.setToSecondaryAxis_action.setChecked(False)
				# maximum
				if item.hasMax:
					self.setToMaximumResult_action.setEnabled(True)
					if item.isMax:
						self.setToMaximumResult_action.setChecked(True)
					else:
						self.setToMaximumResult_action.setChecked(False)
				else:
					self.setToMaximumResult_action.setEnabled(False)
				# save and load styling
				if item.ds_type == 1:  # scalar
					self.saveStyleMenu.menuAction().setVisible(True)
					self.loadDefaultStyle_action.setVisible(True)
					self.saveDefaultVectorStyle_action.setVisible(False)
					self.loadDefaultVectorStyle_action.setVisible(False)
					self.propertiesDialog_action.setVisible(True)
				elif item.ds_type == 2:  # vector
					self.saveStyleMenu.menuAction().setVisible(False)
					self.loadDefaultStyle_action.setVisible(False)
					self.saveDefaultVectorStyle_action.setVisible(True)
					self.loadDefaultVectorStyle_action.setVisible(True)
					self.propertiesDialog_action.setVisible(True)
				else:  # time series or long plot
					self.saveStyleMenu.menuAction().setVisible(False)
					self.loadDefaultStyle_action.setVisible(False)
					self.saveDefaultVectorStyle_action.setVisible(False)
					self.loadDefaultVectorStyle_action.setVisible(False)
					self.propertiesDialog_action.setVisible(False)
		
		self.resultTypeContextItem = item
		self.resultTypesMenu.popup(self.tuView.OpenResultTypes.mapToGlobal(pos))
		
		return True
	
	def connectMenu(self):
		"""
		Connects menu items to their functions.

		:return: bool -> True for successful, False for unsuccessful
		"""

		self.tuPlot.plotWidgetTimeSeries.setContextMenuPolicy(Qt.CustomContextMenu)
		self.tuPlot.plotWidgetLongPlot.setContextMenuPolicy(Qt.CustomContextMenu)
		self.tuPlot.plotWidgetCrossSection.setContextMenuPolicy(Qt.CustomContextMenu)
		self.tuView.OpenResults.setContextMenuPolicy(Qt.CustomContextMenu)
		self.tuView.OpenResultTypes.setContextMenuPolicy(Qt.CustomContextMenu)
		self.tuPlot.plotWidgetTimeSeries.customContextMenuRequested.connect(lambda pos: self.showPlotMenu(pos, 0))
		self.tuPlot.plotWidgetLongPlot.customContextMenuRequested.connect(lambda pos: self.showPlotMenu(pos, 1))
		self.tuPlot.plotWidgetCrossSection.customContextMenuRequested.connect(lambda pos: self.showPlotMenu(pos, 2))
		self.tuView.OpenResults.customContextMenuRequested.connect(self.showResultsMenu)
		self.tuView.OpenResultTypes.customContextMenuRequested.connect(self.showResultTypesMenu)
		
		return True
