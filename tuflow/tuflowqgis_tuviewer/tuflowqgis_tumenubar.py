import os
import webbrowser
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from qgis.gui import *
from PyQt5.QtWidgets import *
import tuflowqgis_tumenufunctions
from tuflow.tuflowqgis_library import about


class TuMenuBar():
	"""
	Class for handling main menu bar.
	
	"""
	
	def __init__(self, TuView, **kwargs):
		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		self.tuView = TuView
		self.tuPlot = TuView.tuPlot
		self.iface = TuView.iface
		self.connected = False
		
		# Set up menu bar widget
		self.window = QWidget()
		self.vbox = QVBoxLayout()
		self.window.setLayout(self.vbox)
		self.menuBar = QMenuBar()
		self.vbox.addWidget(self.menuBar)
		if "layout" in kwargs:
			layout = kwargs['layout']
		else:
			layout = self.tuView.mainMenu
		layout.addWidget(self.window)

		# menu function class
		self.tuMenuFunctions = tuflowqgis_tumenufunctions.TuMenuFunctions(TuView)
		
		self.removeTuview = kwargs['removeTuview'] if 'removeTuview' in kwargs else None
		self.reloadTuview = kwargs['reloadTuview'] if 'reloadTuview' in kwargs else None
		self.menu = kwargs['menu_bar'] if 'menu_bar' in kwargs else None

		self.plotNoToToolbar = self.tuPlot.tuPlotToolbar.plotNoToToolbar
		
	def __del__(self):
		self.disconnectMenu()
		
	def loadFileMenu(self):
		"""
		Loads File menu and menu items.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.fileMenu = self.menuBar.addMenu('&File')
		closeResultsIcon = QgsApplication.getThemeIcon("/mActionRemoveLayer.svg")
		
		# file menu
		if self.menu is None:
			self.load1d2dResults_action = QAction('Load Results', self.window)
			self.load2dResults_action = QAction('Load Results - Map Outputs', self.window)
			self.load1dResults_action = QAction('Load Results - Time Series', self.window)
			self.loadParticlesResults_action = QAction('Load Results - Particles', self.window)
			self.remove1d2dResults_action = QAction(closeResultsIcon, 'Close Results', self.window)
			self.remove2dResults_action = QAction('Close Results - Map Outputs', self.window)
			self.remove1dResults_action = QAction('Close Results - Time Series', self.window)
			self.removeParticlesResults_action = QAction('Close Results - Particles', self.window)
			self.fileMenu.addAction(self.load1d2dResults_action)
			self.fileMenu.addAction(self.load2dResults_action)
			self.fileMenu.addAction(self.load1dResults_action)
			self.fileMenu.addSeparator()
			self.fileMenu.addAction(self.remove1d2dResults_action)
			self.fileMenu.addAction(self.remove2dResults_action)
			self.fileMenu.addAction(self.remove1dResults_action)
			self.fileMenu.addSeparator()
			if self.removeTuview is not None:
				self.fileMenu.addAction(self.removeTuview)
			if self.reloadTuview is not None:
				self.fileMenu.addAction(self.reloadTuview)

			self.load2dResults_action.triggered.connect(self.tuMenuFunctions.load2dResults)
			self.load1dResults_action.triggered.connect(self.tuMenuFunctions.load1dResults)
			self.loadParticlesResults_action.triggered.connect(self.tuMenuFunctions.loadParticlesResults)
			self.load1d2dResults_action.triggered.connect(self.tuMenuFunctions.load1d2dResults)
			self.remove1d2dResults_action.triggered.connect(self.tuMenuFunctions.remove1d2dResults)
			self.remove2dResults_action.triggered.connect(self.tuMenuFunctions.remove2dResults)
			self.remove1dResults_action.triggered.connect(self.tuMenuFunctions.remove1dResults)
			self.removeParticlesResults_action.triggered.connect(self.tuMenuFunctions.removeParticlesResults)
		else:
			self.fileMenu.addAction(self.menu.load1d2dResults_action)
			self.fileMenu.addAction(self.menu.load2dResults_action)
			self.fileMenu.addAction(self.menu.load1dResults_action)
			self.fileMenu.addAction(self.menu.loadParticlesResults_action)
			self.fileMenu.addSeparator()
			self.fileMenu.addAction(self.menu.remove1d2dResults_action)
			self.fileMenu.addAction(self.menu.remove2dResults_action)
			self.fileMenu.addAction(self.menu.remove1dResults_action)
			self.fileMenu.addAction(self.menu.removeParticlesResults_action)
			self.fileMenu.addSeparator()
			if self.removeTuview is not None:
				self.fileMenu.addAction(self.removeTuview)
			if self.reloadTuview is not None:
				self.fileMenu.addAction(self.reloadTuview)
		
	def loadViewMenu(self, plotNo, **kwargs):
		"""
		Loads View menu and menu items
		
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:param kwargs: dict -> key word arguments
		:return: bool -> True for successful, False for unsuccessful
		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot
		
		update = kwargs['update'] if 'update' in kwargs.keys() else False
		
		# if plotNo == 0:
		# 	toolbar = self.tuView.tuPlot.tuPlotToolbar.lstActionsTimeSeries
		# 	viewToolbar = self.tuView.tuPlot.tuPlotToolbar.viewToolbarTimeSeries
		# elif plotNo == 1:
		# 	toolbar = self.tuView.tuPlot.tuPlotToolbar.lstActionsLongPlot
		# 	viewToolbar = self.tuView.tuPlot.tuPlotToolbar.viewToolbarLongPlot
		# elif plotNo == 2:
		# 	toolbar = self.tuView.tuPlot.tuPlotToolbar.lstActionsCrossSection
		# 	viewToolbar = self.tuView.tuPlot.tuPlotToolbar.viewToolbarCrossSection

		toolbar, viewToolbar, mplToolbar = self.plotNoToToolbar[plotNo]
		
		if not update:  # only create view menu if not just an update (updates when switching between plot type tabs)
			self.viewMenu = self.menuBar.addMenu('&View')
		iconRefresh = QgsApplication.getThemeIcon("/mActionRefresh.svg")
		iconRefreshPlot = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "refreshplotblack.png"))
		iconClearPlot = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "ClearPlot.png"))

		if self.menu is None:
			# view menu items
			self.freezeAxisLimits_action = viewToolbar.freezeXYAxisButton.defaultAction()
			self.freezeAxisXLimits_action = viewToolbar.freezeXAxisButton.defaultAction()
			self.freezeAxisYLimits_action = viewToolbar.freezeYAxisButton.defaultAction()
			self.freezeAxisLabels_action = QAction('Freeze Axis Labels', self.window)
			self.freezeAxisLabels_action.setCheckable(True)
			self.refreshMapWindow_action = QAction(iconRefresh, 'Refresh Map Window', self.window)
			self.refreshCurrentPlotWindow_action = QAction(iconRefreshPlot, 'Refresh Plot Window - Current', self.window)
			self.refreshAllPlotWindows_action = QAction(iconRefreshPlot, 'Refresh Plot Window - All', self.window)
			self.clearPlotWindow_action = QAction(iconClearPlot, 'Clear Plot Window - Current', self.window)
			self.clearAllPlotWindows_action = QAction(iconClearPlot, 'Clear Plot Window - All', self.window)
			self.viewMenu.addAction(toolbar[0])
			self.viewMenu.addAction(toolbar[1])
			self.viewMenu.addAction(toolbar[2])
			self.viewMenu.addAction(toolbar[4])
			self.viewMenu.addAction(toolbar[5])
			self.viewMenu.addSeparator()
			self.viewMenu.addAction(self.freezeAxisLimits_action)
			self.viewMenu.addAction(self.freezeAxisXLimits_action)
			self.viewMenu.addAction(self.freezeAxisYLimits_action)
			self.viewMenu.addSeparator()
			self.viewMenu.addAction(self.refreshMapWindow_action)
			self.viewMenu.addSeparator()
			self.viewMenu.addAction(self.refreshCurrentPlotWindow_action)
			self.viewMenu.addAction(self.refreshAllPlotWindows_action)
			self.viewMenu.addSeparator()
			self.viewMenu.addAction(self.clearPlotWindow_action)
			self.viewMenu.addAction(self.clearAllPlotWindows_action)

			self.freezeAxisLimits_action.triggered.connect(viewToolbar.freezeXYAxis)
			self.freezeAxisXLimits_action.triggered.connect(viewToolbar.freezeXAxis)
			self.freezeAxisYLimits_action.triggered.connect(viewToolbar.freezeYAxis)
			self.refreshMapWindow_action.triggered.connect(self.tuView.renderMap)
			self.refreshCurrentPlotWindow_action.triggered.connect(self.tuView.refreshCurrentPlot)
			self.refreshAllPlotWindows_action.triggered.connect(self.tuView.tuPlot.updateAllPlots)
			#self.clearPlotWindow_action.triggered.connect(
			#	lambda: self.tuView.tuPlot.clearPlot(self.tuView.tabWidget.currentIndex(), clear_rubberband=True,
			#	                                     clear_selection=True))
			self.clearPlotWindow_action.triggered.connect(
				lambda: self.tuView.tuPlot.clearPlot2(self.tuView.tabWidget.currentIndex()))
			self.clearAllPlotWindows_action.triggered.connect(self.tuView.tuPlot.clearAllPlots)
		else:
			self.viewMenu.addAction(toolbar[0])
			self.viewMenu.addAction(toolbar[1])
			self.viewMenu.addAction(toolbar[2])
			self.viewMenu.addAction(toolbar[4])
			self.viewMenu.addAction(toolbar[5])
			self.viewMenu.addSeparator()
			self.viewMenu.addAction(self.menu.freezeAxisLimits_action)
			self.viewMenu.addAction(self.menu.freezeAxisXLimits_action)
			self.viewMenu.addAction(self.menu.freezeAxisYLimits_action)
			self.viewMenu.addSeparator()
			self.viewMenu.addAction(self.menu.refreshMapWindow_action)
			self.viewMenu.addSeparator()
			self.viewMenu.addAction(self.menu.refreshCurrentPlotWindow_action)
			self.viewMenu.addAction(self.menu.refreshAllPlotWindows_action)
			self.viewMenu.addSeparator()
			self.viewMenu.addAction(self.menu.clearPlotWindow_action)
			self.viewMenu.addAction(self.menu.clearAllPlotWindows_action)
		
		return True
	
	def loadSettingsMenu(self, plotNo, **kwargs):
		"""
		Loads Edit menu and menu items.
		
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:param kwargs: dict -> key word arguments
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		update = kwargs['update'] if 'update' in kwargs.keys() else False
		
		# if plotNo == 0:
		# 	toolbar = self.tuView.tuPlot.tuPlotToolbar.lstActionsTimeSeries
		# 	viewToolbar = self.tuView.tuPlot.tuPlotToolbar.viewToolbarTimeSeries
		# elif plotNo == 1:
		# 	toolbar = self.tuView.tuPlot.tuPlotToolbar.lstActionsLongPlot
		# 	viewToolbar = self.tuView.tuPlot.tuPlotToolbar.viewToolbarLongPlot
		# elif plotNo == 2:
		# 	toolbar = self.tuView.tuPlot.tuPlotToolbar.lstActionsCrossSection
		# 	viewToolbar = self.tuView.tuPlot.tuPlotToolbar.viewToolbarCrossSection

		toolbar, viewToolbar, mplToolbar = self.plotNoToToolbar[plotNo]
			
		if not update:  # only create view menu if not just an update (updates when switching between plot type tabs)
			self.settingsMenu = self.menuBar.addMenu('&Settings')
		iconOptions = QgsApplication.getThemeIcon("/mActionOptions.svg")
		iconScalar = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "icon_contours.png"))
		iconVector = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons" "icon_vectors.png"))

		if self.menu is None:
			# settings menu items
			self.userPlotDataManager_action = viewToolbar.userPlotDataManagerButton.defaultAction()
			self.saveColorRampForActiveResult_action = QAction(iconScalar, 'Save Chosen Color Ramp', self.window)
			self.saveColorMapForActiveResult_action = QAction(iconScalar, 'Save Color Map (Exact Values and Colours)', self.window)
			self.saveStyleForVectorResult_action = QAction(iconVector, 'Save Vector Layer Style as Default', self.window)
			self.loadStyleForActiveResult_action = QAction(iconScalar, 'Reload Default Style for Active Layer', self.window)
			self.loadStyleForVectorResult_action = QAction(iconVector, 'Reload Default Style for VectorLayer', self.window)
			self.resetDefaultStyles_action = QAction('Reset Default Styles', self.window)
			self.options_action = QAction(iconOptions, 'Options', self.window)
			self.settingsMenu.addAction(self.userPlotDataManager_action)
			self.settingsMenu.addSeparator()
			self.settingsMenu.addAction(toolbar[7])
			self.settingsMenu.addSeparator()
			self.saveStyleMenu = self.settingsMenu.addMenu('Save Active Layer Style as Default for Result Type')
			self.saveStyleMenu.addAction(self.saveColorRampForActiveResult_action)
			self.saveStyleMenu.addAction(self.saveColorMapForActiveResult_action)
			self.settingsMenu.addAction(self.saveStyleForVectorResult_action)
			self.settingsMenu.addAction(self.loadStyleForActiveResult_action)
			self.settingsMenu.addAction(self.loadStyleForVectorResult_action)
			self.settingsMenu.addAction(self.resetDefaultStyles_action)
			self.settingsMenu.addSeparator()
			self.settingsMenu.addAction(self.options_action)

			#self.userPlotDataManager_action.triggered.connect(self.tuMenuFunctions.openUserPlotDataManager)
			self.tuView.tuPlot.tuPlotToolbar.lstActionsTimeSeries[7].triggered.connect(self.tuMenuFunctions.updateLegend)
			self.tuView.tuPlot.tuPlotToolbar.lstActionsLongPlot[7].triggered.connect(self.tuMenuFunctions.updateLegend)
			self.tuView.tuPlot.tuPlotToolbar.lstActionsCrossSection[7].triggered.connect(self.tuMenuFunctions.updateLegend)
			self.saveColorRampForActiveResult_action.triggered.connect(
				lambda: self.tuMenuFunctions.saveDefaultStyleScalar('color ramp'))
			self.saveColorMapForActiveResult_action.triggered.connect(
				lambda: self.tuMenuFunctions.saveDefaultStyleScalar('color map'))
			self.saveStyleForVectorResult_action.triggered.connect(self.tuMenuFunctions.saveDefaultStyleVector)
			self.loadStyleForActiveResult_action.triggered.connect(self.tuMenuFunctions.loadDefaultStyleScalar)
			self.loadStyleForVectorResult_action.triggered.connect(self.tuMenuFunctions.loadDefaultStyleVector)
			self.resetDefaultStyles_action.triggered.connect(self.tuMenuFunctions.resetDefaultStyles)
			self.options_action.triggered.connect(self.tuMenuFunctions.options)
		else:
			self.settingsMenu.addAction(self.menu.userPlotDataManager_action)
			self.settingsMenu.addSeparator()
			self.settingsMenu.addAction(toolbar[7])
			self.settingsMenu.addSeparator()
			self.saveStyleMenu = self.settingsMenu.addMenu('Save Active Layer Style as Default for Result Type')
			self.saveStyleMenu.addAction(self.menu.saveColorRampForActiveResult_action)
			self.saveStyleMenu.addAction(self.menu.saveColorMapForActiveResult_action)
			self.settingsMenu.addAction(self.menu.saveStyleForVectorResult_action)
			self.settingsMenu.addAction(self.menu.loadStyleForActiveResult_action)
			self.settingsMenu.addAction(self.menu.loadStyleForVectorResult_action)
			self.settingsMenu.addAction(self.menu.resetDefaultStyles_action)
			self.settingsMenu.addSeparator()
			self.settingsMenu.addAction(self.menu.options_action)
		
		return True
	
	def loadExportMenu(self, plotNo, **kwargs):
		"""
		Load Export menu and menu items
		
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:param kwargs: dict -> key word arguments
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		update = kwargs['update'] if 'update' in kwargs.keys() else False
		
		# if plotNo == 0:
		# 	toolbar = self.tuView.tuPlot.tuPlotToolbar.lstActionsTimeSeries
		# elif plotNo == 1:
		# 	toolbar = self.tuView.tuPlot.tuPlotToolbar.lstActionsLongPlot
		# elif plotNo == 2:
		# 	toolbar = self.tuView.tuPlot.tuPlotToolbar.lstActionsCrossSection

		toolbar, viewToolbar, mplToolbar = self.plotNoToToolbar[plotNo]
		
		if not update:  # only create view menu if not just an update (updates when switching between plot type tabs)
			self.exportMenu = self.menuBar.addMenu('&Export')
		lineFeatureIcon = QgsApplication.getThemeIcon("/mActionMoveFeatureLine.svg")
		pointFeatureIcon = QgsApplication.getThemeIcon("/mActionMoveFeaturePoint.svg")
		iconAnimation = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "icon_video.png"))

		if self.menu is None:
			# export menu items
			self.exportAsCSV_action = QAction('Export Plot As CSV', self.window)
			self.autoPlotExport_action = QAction('Batch Plot and Export Features in Shape File', self.window)
			self.exportDataToClipboard_action = QAction('Copy Data to Clipboard', self.window)
			self.exportImageToClipboard_action = QAction('Copy Image to Clipboard', self.window)
			self.exportTempLine_action = QAction(lineFeatureIcon, 'Export Temporary Line(s) to SHP', self.window)
			self.exportTempPoint_action = QAction(pointFeatureIcon, 'Export Temporary Point(s) to SHP', self.window)
			self.exportAnimation_action = QAction(iconAnimation, 'Export Animation (beta)', self.window)
			self.exportMaps_action = QAction('Export Maps (beta)', self.window)
			self.exportMenu.addAction(toolbar[9])
			self.exportMenu.addAction(self.exportAsCSV_action)
			self.exportMenu.addAction(self.autoPlotExport_action)
			self.exportMenu.addSeparator()
			self.exportMenu.addAction(self.exportDataToClipboard_action)
			self.exportMenu.addAction(self.exportImageToClipboard_action)
			self.exportMenu.addSeparator()
			self.exportMenu.addAction(self.exportTempLine_action)
			self.exportMenu.addAction(self.exportTempPoint_action)
			self.exportMenu.addSeparator()
			self.exportMenu.addAction(self.exportAnimation_action)
			self.exportMenu.addSeparator()
			self.exportMenu.addAction(self.exportMaps_action)

			self.exportAsCSV_action.triggered.connect(self.tuMenuFunctions.exportCSV)
			self.autoPlotExport_action.triggered.connect(self.tuMenuFunctions.batchPlotExportInitialise)
			self.exportDataToClipboard_action.triggered.connect(self.tuMenuFunctions.exportDataToClipboard)
			self.exportImageToClipboard_action.triggered.connect(self.tuMenuFunctions.exportImageToClipboard)
			self.exportTempLine_action.triggered.connect(self.tuMenuFunctions.exportTempLines)
			self.exportTempPoint_action.triggered.connect(self.tuMenuFunctions.exportTempPoints)
			self.exportAnimation_action.triggered.connect(self.tuMenuFunctions.exportAnimation)
			self.exportMaps_action.triggered.connect(self.tuMenuFunctions.exportMaps)
		else:
			self.exportMenu.addAction(toolbar[9])
			self.exportMenu.addAction(self.menu.exportAsCSV_action)
			self.exportMenu.addAction(self.menu.autoPlotExport_action)
			self.exportMenu.addSeparator()
			self.exportMenu.addAction(self.menu.exportDataToClipboard_action)
			self.exportMenu.addAction(self.menu.exportImageToClipboard_action)
			self.exportMenu.addSeparator()
			self.exportMenu.addAction(self.menu.exportTempLine_action)
			self.exportMenu.addAction(self.menu.exportTempPoint_action)
			self.exportMenu.addSeparator()
			self.exportMenu.addAction(self.menu.exportAnimation_action)
			self.exportMenu.addSeparator()
			self.exportMenu.addAction(self.menu.exportMaps_action)
		
		return True
	
	def loadResultsMenu(self):
		"""
		Load ARR2016 menu and menu items.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		resultsMenu = self.menuBar.addMenu('&Results')

		if self.menu is None:
			# ARR2016 menu items
			self.showSelectedElements_action = QAction('Show Selected Element Names', self.window)
			self.showMedianEvent_action = QAction('Show Median Event', self.window)
			self.showMedianEvent_action.setCheckable(True)
			self.showMeanEvent_action = QAction('Show Mean Event', self.window)
			self.showMeanEvent_action.setCheckable(True)
			resultsMenu.addAction(self.showSelectedElements_action)
			resultsMenu.addSeparator()
			arrMenu = resultsMenu.addMenu('&ARR2016')
			arrMenu.addAction(self.showMedianEvent_action)
			arrMenu.addAction(self.showMeanEvent_action)

			self.showSelectedElements_action.triggered.connect(self.tuMenuFunctions.showSelectedElements)
			self.showMedianEvent_action.triggered.connect(self.tuMenuFunctions.showMedianEvent)
			self.showMeanEvent_action.triggered.connect(self.tuMenuFunctions.showMeanEvent)
		else:
			resultsMenu.addAction(self.menu.showSelectedElements_action)
			resultsMenu.addSeparator()
			arrMenu = resultsMenu.addMenu('&ARR2016')
			arrMenu.addAction(self.menu.showMedianEvent_action)
			arrMenu.addAction(self.menu.showMeanEvent_action)
		
		return True
	
	def loadHelpMenu(self):
		"""
		Load Help menu and menu items.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		helpMenu = self.menuBar.addMenu('&Help')
		helpIcon = QgsApplication.getThemeIcon('/mActionHelpContents.svg')
		aboutIcon = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "tuview.png"))

		if self.menu is None:
			# Help Menu
			self.help_action = QAction(helpIcon, 'Help', self.window)
			self.about_action = QAction(aboutIcon, 'About', self.window)
			helpMenu.addAction(self.help_action)
			helpMenu.addSeparator()
			helpMenu.addAction(self.about_action)

			self.about_action.triggered.connect(self.about)
			self.help_action.triggered.connect(self.help)
		else:
			helpMenu.addAction(self.menu.help_action)
			helpMenu.addSeparator()
			helpMenu.addAction(self.menu.about_action)
		
	def about(self):
		"""
		
		:return:
		"""

		about(self.tuView)
		
	def help(self):
		"""
		
		:return:
		"""
		
		url = r'https://wiki.tuflow.com/index.php?title=TUFLOW_Viewer'
		webbrowser.open(url)