from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt import QtGui
from qgis.core import *
from qgis.PyQt.QtWidgets  import *
from ..dataset_menu import DatasetMenu, DatasetMenuDepAv
import sys
import os
import matplotlib
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.patches import Polygon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from .tuflowqgis_tumenufunctions import TuMenuFunctions
from .tuflowqgis_tuplottoolbar_viewtoolbar import ViewToolbar
from ..spinbox_action import SingleSpinBoxAction, DoubleSpinBoxAction
import numpy as np

from ..compatibility_routines import is_qt6



class TuPlotToolbar():
	"""
	Class for handling plotting toolbar.
	
	"""
	
	def __init__(self, tuPlot):
		from .tuflowqgis_tuplot import TuPlot

		self.tuPlot = tuPlot
		self.tuView = tuPlot.tuView
		self.tuMenuFunctions = TuMenuFunctions(self.tuView)
		self.averageMethodActions = []

		self.initialiseMplToolbars()
		self.initialiseMapOutputPlottingToolbar()
		self.initialiseViewToolbar()

		self.plotNoToToolbar = {
			TuPlot.TimeSeries: [self.lstActionsTimeSeries,
			                    self.viewToolbarTimeSeries,
			                    self.mpltoolbarTimeSeries],
			TuPlot.CrossSection: [self.lstActionsLongPlot,
			                      self.viewToolbarLongPlot,
			                      self.mpltoolbarLongPlot],
			TuPlot.CrossSection1D: [self.lstActionsCrossSection,
			                        self.viewToolbarCrossSection,
			                        self.mpltoolbarCrossSection],
			TuPlot.VerticalProfile: [self.lstActionsVerticalProfile,
			                         self.viewToolbarVerticalProfile,
			                         self.mpltoolbarVerticalProfile]
		}
		
	def initialiseMplToolbars(self):
		"""
		Initialises the mpl toolbars for all plot windows.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		qv = Qgis.QGIS_VERSION_INT

		w = self.tuView.tuOptions.iconSize
		if qv >= 31600:
			w = int(QgsApplication.scaleIconSize(self.tuView.tuOptions.iconSize, True))

		w2 = int(np.ceil(w*1.5))
		w3 = int(np.ceil(w2 * 6))
		w4 = int(np.ceil(w3 + w2 * 2))
		self.tuView.mplToolbarFrame.setMinimumHeight(w2)
		self.tuView.mplToolbarFrame.setMinimumWidth(w3)

		# Plotting Toolbar - Time series
		self.mpltoolbarTimeSeries = matplotlib.backends.backend_qt5agg.NavigationToolbar2QT(
			self.tuPlot.plotWidgetTimeSeries,
			self.tuView.mplToolbarFrame)
		self.mpltoolbarTimeSeries.setIconSize(QSize(w, w))
		self.mpltoolbarTimeSeries.resize(QSize(w4, w2))
		self.lstActionsTimeSeries = self.mpltoolbarTimeSeries.actions()
		#self.mpltoolbarTimeSeries.removeAction(self.lstActionsTimeSeries[6])  # remove customise subplot
		self.mpltoolbarTimeSeries.removeAction(self.lstActionsTimeSeries[-1])
		self.mpltoolbarTimeSeries.removeAction(self.lstActionsTimeSeries[8])
		self.mpltoolbarTimeSeries.removeAction(self.lstActionsTimeSeries[6])
		self.mpltoolbarTimeSeries.removeAction(self.lstActionsTimeSeries[3])

		
		# Plotting Toolbar - Long plot
		self.mpltoolbarLongPlot = matplotlib.backends.backend_qt5agg.NavigationToolbar2QT(
			self.tuPlot.plotWidgetLongPlot,
			self.tuView.mplToolbarFrame)
		self.mpltoolbarLongPlot.setIconSize(QSize(w, w))
		self.mpltoolbarLongPlot.resize(QSize(w4, w2))
		self.lstActionsLongPlot = self.mpltoolbarLongPlot.actions()
		# self.mpltoolbarLongPlot.removeAction(self.lstActionsLongPlot[6])  # remove customise subplot
		self.mpltoolbarLongPlot.removeAction(self.lstActionsLongPlot[-1])
		self.mpltoolbarLongPlot.removeAction(self.lstActionsLongPlot[8])
		self.mpltoolbarLongPlot.removeAction(self.lstActionsLongPlot[6])
		self.mpltoolbarLongPlot.removeAction(self.lstActionsLongPlot[3])
		self.mpltoolbarLongPlot.setVisible(False)
		
		# Plotting Toolbar - Cross section
		self.mpltoolbarCrossSection = matplotlib.backends.backend_qt5agg.NavigationToolbar2QT(
			self.tuPlot.plotWidgetCrossSection,
			self.tuView.mplToolbarFrame)
		self.mpltoolbarCrossSection.setIconSize(QSize(w, w))
		self.mpltoolbarCrossSection.resize(QSize(w4, w2))
		self.lstActionsCrossSection = self.mpltoolbarCrossSection.actions()
		# self.mpltoolbarCrossSection.removeAction(self.lstActionsCrossSection[6])  # remove customise subplot
		self.mpltoolbarCrossSection.removeAction(self.lstActionsCrossSection[-1])
		self.mpltoolbarCrossSection.removeAction(self.lstActionsCrossSection[8])
		self.mpltoolbarCrossSection.removeAction(self.lstActionsCrossSection[6])
		self.mpltoolbarCrossSection.removeAction(self.lstActionsCrossSection[3])
		self.mpltoolbarCrossSection.setVisible(False)

		# Plotting Toolbar - vertical profile
		self.mpltoolbarVerticalProfile = matplotlib.backends.backend_qt5agg.NavigationToolbar2QT(
			self.tuPlot.plotWidgetVerticalProfile,
			self.tuView.mplToolbarFrame)
		self.mpltoolbarVerticalProfile.setIconSize(QSize(w, w))
		self.mpltoolbarVerticalProfile.resize(QSize(w4, w2))
		self.lstActionsVerticalProfile = self.mpltoolbarVerticalProfile.actions()
		# self.mpltoolbarVerticalProfile.removeAction(self.lstActionsVerticalProfile[6])  # remove customise subplot
		self.mpltoolbarVerticalProfile.removeAction(self.lstActionsVerticalProfile[-1])
		self.mpltoolbarVerticalProfile.removeAction(self.lstActionsVerticalProfile[8])
		self.mpltoolbarVerticalProfile.removeAction(self.lstActionsVerticalProfile[6])
		self.mpltoolbarVerticalProfile.removeAction(self.lstActionsVerticalProfile[3])
		self.mpltoolbarVerticalProfile.setVisible(False)

		# self.mpltoolbarTimeSeries.iconSizeChanged.connect(lambda e: self.tuView.toolbarIconSizeChanged(e, self.mpltoolbarTimeSeries, self.tuView.mplToolbarFrame))
		# self.mpltoolbarLongPlot.iconSizeChanged.connect(lambda e: self.tuView.toolbarIconSizeChanged(e, self.mpltoolbarLongPlot, self.tuView.mplToolbarFrame))
		# self.mpltoolbarCrossSection.iconSizeChanged.connect(lambda e: self.tuView.toolbarIconSizeChanged(e, self.mpltoolbarCrossSection, self.tuView.mplToolbarFrame))
		# self.mpltoolbarVerticalProfile.iconSizeChanged.connect(lambda e: self.tuView.toolbarIconSizeChanged(e, self.mpltoolbarVerticalProfile, self.tuView.mplToolbarFrame))

		return True
		
	def initialiseMapOutputPlottingToolbar(self):
		"""
		Initialises toolbar for the map output plotting i.e. time series, cross section / long plot, flux
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		from .tuflowqgis_tuplot import TuPlot

		qv = Qgis.QGIS_VERSION_INT

		w = self.tuView.tuOptions.iconSize
		if qv >= 31600:
			w = int(QgsApplication.scaleIconSize(self.tuView.tuOptions.iconSize, True))

		w2 = int(np.ceil(w * 1.5))
		w3 = int(np.ceil(w2 * 6))
		w4 = int(np.ceil(w3 + w2 * 2))

		# toolbar settings
		self.mapOutputPlotToolbar = QToolBar('Map Output Plotting', self.tuView.MapOutputPlotFrame)
		self.mapOutputPlotToolbar.setIconSize(QSize(w, w))
		self.tuView.MapOutputPlotFrame.setMinimumHeight(w2)
		self.mapOutputPlotToolbar.resize(QSize(w4, w2))

		# 3D mesh averaging plotting
		self.mesh3dPlotToolbar = QToolBar('3D Mesh Plotting', self.tuView.Mesh3DToolbarFrame)
		self.mesh3dPlotToolbar.setIconSize(QSize(w, w))
		self.tuView.Mesh3DToolbarFrame.setMinimumHeight(w2)
		self.tuView.Mesh3DToolbarFrame.setMinimumWidth(w3)
		self.mesh3dPlotToolbar.resize(QSize(w4, w2))
		
		# icons
		dir = os.path.dirname(os.path.dirname(__file__))
		tsIcon = QIcon(os.path.join(dir, "icons", "results.svg"))
		csIcon = QIcon(os.path.join(dir, "icons", "cross_section.svg"))
		fluxIcon = QIcon(os.path.join(dir, "icons", "flux_line.svg"))
		fluxSecAxisIcon = QIcon(os.path.join(dir, "icons", "2nd_axis.svg"))
		cursorTrackingIcon = QIcon(os.path.join(dir, "icons", "cursor_tracking.svg"))
		meshGridIcon = QIcon(os.path.join(dir, "icons", "mesh_grid.svg"))
		#meshAveragingIcon = QgsApplication.getThemeIcon('/propertyicons/meshaveraging.svg')
		tsDepthAvIcon = QIcon(os.path.join(dir, "icons", "results_ts_3d.svg"))
		csDepthAvIcon = QIcon(os.path.join(dir, "icons", "results_xs_3d.svg"))
		curtainPlotIcon = QIcon(os.path.join(dir, "icons", "curtain_plot.svg"))
		verticalProfileIcon = QIcon(os.path.join(dir, "icons", "vertical_profile.svg"))
		
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
		self.meshGridButton.setToolTip('Toggle Mesh')
		self.meshGridAction = QAction(meshGridIcon, 'Toggle Mesh Rendering', self.meshGridButton)
		self.meshGridAction.setCheckable(True)
		self.meshGridButton.setDefaultAction(self.meshGridAction)
		self.averageMethodTSMenu = DatasetMenuDepAv("3D to 2D Averaging Time Series")
		self.averageMethodTSMenu.menuAction().setIcon(tsDepthAvIcon)
		self.averageMethodTSMenu.menuAction().setCheckable(True)
		self.averageMethodCSMenu = DatasetMenuDepAv("3D to 2D Averaging Cross Section")
		self.averageMethodCSMenu.menuAction().setIcon(csDepthAvIcon)
		self.averageMethodCSMenu.menuAction().setCheckable(True)
		self.addAverageMethods(self.averageMethodTSMenu)
		self.addAverageMethods(self.averageMethodCSMenu)
		self.curtainPlotMenu = DatasetMenu("Curtain Plot")
		self.curtainPlotMenu.menuAction().setIcon(curtainPlotIcon)
		self.curtainPlotMenu.menuAction().setCheckable(True)
		self.plotVPMenu = DatasetMenu("Vertical Profile")
		self.plotVPMenu.menuAction().setIcon(verticalProfileIcon)
		self.plotVPMenu.menuAction().setCheckable(True)

		# add buttons to toolbar
		self.mapOutputPlotToolbar.addAction(self.plotTSMenu.menuAction())
		self.mapOutputPlotToolbar.addAction(self.plotLPMenu.menuAction())
		self.mapOutputPlotToolbar.addWidget(self.plotFluxButton)
		self.mapOutputPlotToolbar.addWidget(self.fluxSecAxisButton)
		self.mapOutputPlotToolbar.addWidget(self.cursorTrackingButton)
		self.mapOutputPlotToolbar.addWidget(self.meshGridButton)
		self.mesh3dPlotToolbar.addAction(self.averageMethodTSMenu.menuAction())
		self.mesh3dPlotToolbar.addAction(self.averageMethodCSMenu.menuAction())
		self.mesh3dPlotToolbar.addAction(self.curtainPlotMenu.menuAction())
		self.mesh3dPlotToolbar.addAction(self.plotVPMenu.menuAction())
		
		# connect buttons
		self.plotTSMenu.menuAction().triggered.connect(lambda: self.mapOutputPlottingButtonClicked(TuPlot.DataTimeSeries2D))
		self.plotLPMenu.menuAction().triggered.connect(lambda: self.mapOutputPlottingButtonClicked(TuPlot.DataCrossSection2D))
		self.plotFluxButton.released.connect(lambda: self.mapOutputPlottingButtonClicked(TuPlot.DataFlow2D))
		self.cursorTrackingButton.released.connect(self.cursorTrackingToggled)
		self.meshGridAction.triggered.connect(self.tuMenuFunctions.toggleMeshRender)
		self.curtainPlotMenu.menuAction().triggered.connect(lambda: self.mapOutputPlottingButtonClicked(TuPlot.DataCurtainPlot))
		self.averageMethodTSMenu.menuAction().triggered.connect(lambda: self.mapOutputPlottingButtonClicked(TuPlot.DataTimeSeriesDepAv))
		self.averageMethodCSMenu.menuAction().triggered.connect(lambda: self.mapOutputPlottingButtonClicked(TuPlot.DataCrossSectionDepAv))
		self.plotVPMenu.menuAction().triggered.connect(lambda: self.mapOutputPlottingButtonClicked(TuPlot.DataVerticalProfile))

		self.plotDataToPlotMenu = {
			TuPlot.DataTimeSeries2D: self.plotTSMenu.menuAction(),
			TuPlot.DataCrossSection2D: self.plotLPMenu.menuAction(),
			TuPlot.DataFlow2D: self.plotFluxButton,
			TuPlot.DataTimeSeries1D: None,
			TuPlot.DataCrossSection1D: None,
			TuPlot.DataUserData: None,
			TuPlot.DataCurrentTime: None,
			TuPlot.DataTimeSeriesStartLine: None,
			TuPlot.DataCrossSectionStartLine: None,
			TuPlot.DataCrossSectionStartLine1D: None,
			TuPlot.DataCurtainPlot: self.curtainPlotMenu.menuAction(),
			TuPlot.DataTimeSeriesDepAv: self.averageMethodTSMenu.menuAction(),
			TuPlot.DataCrossSectionDepAv: self.averageMethodCSMenu.menuAction(),
			TuPlot.DataVerticalProfileStartLine: None,
			TuPlot.DataVerticalProfile: self.plotVPMenu.menuAction(),
			TuPlot.DataCrossSection1DViewer: None,
			TuPlot.DataHydraulicProperty: None,
			TuPlot.DataVerticalMesh: None,
		}

		# self.mapOutputPlotToolbar.iconSizeChanged.connect(lambda e: self.tuView.toolbarIconSizeChanged(e, self.mapOutputPlotToolbar, self.tuView.MapOutputPlotFrame))
		# self.mesh3dPlotToolbar.iconSizeChanged.connect(lambda e: self.tuView.toolbarIconSizeChanged(e, self.mesh3dPlotToolbar, self.tuView.Mesh3DToolbarFrame))

		return True
	
	def initialiseViewToolbar(self):

		from .tuflowqgis_tuplot import TuPlot
		
		# view menu - time series
		self.viewToolbarTimeSeries = ViewToolbar(self, TuPlot.TimeSeries)
		
		# view menu - long plot
		self.viewToolbarLongPlot = ViewToolbar(self, TuPlot.CrossSection)
		self.viewToolbarLongPlot.setVisible(False)
		
		# view menu - 1D cross section plot
		self.viewToolbarCrossSection = ViewToolbar(self, TuPlot.CrossSection1D)
		self.viewToolbarCrossSection.setVisible(False)

		# view menu - vertical profile plot
		self.viewToolbarVerticalProfile = ViewToolbar(self, TuPlot.VerticalProfile)
		self.viewToolbarVerticalProfile.setVisible(False)
		
		return True
		
	def setToolbarActive(self, plotNo):
		"""
		Sets the toolbar active based on the enumerator.
		
		:param plotNo: int enumerator -> 0: time series plot
										 1: long profile plot
										 2: cross section plot
		:return: bool -> True for successful, False for unsuccessful
		"""
		

		toolbar, viewToolbar, mplToolbar = self.plotNoToToolbar[plotNo]
		viewToolbar.setVisible(True)
		mplToolbar.setVisible(True)
		for pn, tb in self.plotNoToToolbar.items():
			if pn != plotNo:
				tb[1].setVisible(False)
				tb[2].setVisible(False)
		
		# menubar
		self.tuView.tuMenuBar.viewMenu.clear()
		self.tuView.tuMenuBar.loadViewMenu(plotNo, update=True)
		self.tuView.tuMenuBarSecond.viewMenu.clear()
		self.tuView.tuMenuBarSecond.loadViewMenu(plotNo, update=True)

		self.tuView.tuMenuBar.settingsMenu.clear()
		self.tuView.tuMenuBar.loadSettingsMenu(plotNo, update=True)
		self.tuView.tuMenuBarSecond.settingsMenu.clear()
		self.tuView.tuMenuBarSecond.loadSettingsMenu(plotNo, update=True)

		self.tuView.tuMenuBar.exportMenu.clear()
		self.tuView.tuMenuBar.loadExportMenu(plotNo, update=True)
		self.tuView.tuMenuBarSecond.exportMenu.clear()
		self.tuView.tuMenuBarSecond.loadExportMenu(plotNo, update=True)

		# context menu
		self.tuView.tuContextMenu.plotMenu.clear()
		self.tuView.tuContextMenu.loadPlotMenu(plotNo, update=True)

		return True
	
	def mapOutputPlottingButtonClicked(self, dataType, **kwargs):

		from .tuflowqgis_tuplot import TuPlot

		menu = self.plotDataToPlotMenu[dataType]
		graphic = self.tuPlot.plotDataToGraphic[dataType]
		if menu.isChecked():
			for dtp in self.tuPlot.plotDataPlottingTypes:
				menu2 = self.plotDataToPlotMenu[dtp]
				graphic2 = self.tuPlot.plotDataToGraphic[dtp]
				if menu != menu2:
					if menu2 is not None: menu2.setChecked(False)
				if graphic != graphic2:
					if graphic2 is not None:
						if graphic2.cursorTrackingConnected:
							graphic2.mouseTrackDisconnect()
			if self.getCheckedItemsFromPlotOptions(dataType):
				self.tuView.tabWidget.setCurrentIndex(self.tuPlot.plotDataToPlotType[dataType])
				if self.tuView.cboSelectType.currentText() == 'Layer Selection':
					self.tuPlot.tuPlotSelection.useSelection(dataType, **kwargs)
				else:
					graphic.startRubberBand()
			else:
				menu.setChecked(False)
		else:
			if graphic.cursorTrackingConnected:
				graphic.mouseTrackDisconnect()

		return False
	
	def addItemToPlotOptions(self, type, dataType=None, static=False):

		from .tuflowqgis_tuplot import TuPlot

		if dataType is None:
			for dataType in self.tuPlot.plotDataPlottingTypes:
				if static and dataType in self.tuPlot.plotDataTemporalPlottingTypes:
					continue
				self.addItemToPlotOption(type, dataType)
		else:
			self.addItemToPlotOption(type, dataType)
		
		return True

	def addItemToPlotOption(self, type, dataType):

		from .tuflowqgis_tuplot import TuPlot

		menu = self.plotDataToPlotMenu[dataType]

		if menu is not None:
			if isinstance(menu, QAction):
				if is_qt6:
					menu = menu.parent()
				else:
					menu = menu.parentWidget()

			action = QAction(type, menu)
			action.setCheckable(True)
			if dataType == TuPlot.DataTimeSeriesDepAv or dataType == TuPlot.DataCrossSectionDepAv:
				menu.addActionToSubMenus(action)
			else:
				menu.addAction(action)
	
	def getItemsFromPlotOptions(self, plotNo, method='plot'):

		from .tuflowqgis_tuplot import TuPlot

		if method == 'plot':
			if plotNo == TuPlot.TimeSeries:
				menu = self.plotTSMenu
			elif plotNo == TuPlot.CrossSection:
				menu = self.plotLPMenu
			else:
				return []
		elif method == 'data type':
			if plotNo == TuPlot.DataTimeSeries2D:
				menu = self.plotTSMenu
			elif plotNo == TuPlot.DataCrossSection2D:
				menu = self.plotLPMenu
			elif plotNo == TuPlot.DataCurtainPlot:
				menu = self.curtainPlotMenu
			elif plotNo == TuPlot.DataTimeSeriesDepAv:
				menu = self.averageMethodTSMenu
			elif plotNo == TuPlot.DataCrossSectionDepAv:
				menu = self.averageMethodCSMenu
			elif plotNo == TuPlot.DataVerticalProfile:
				menu = self.plotVPMenu
			else:
				return []

		if method == 'data type' and (plotNo == TuPlot.DataTimeSeriesDepAv or plotNo == TuPlot.DataCrossSectionDepAv):
			return [x for x in menu.resultTypes()]

		return [x.text() for x in menu.actions()]

	def getCheckedItemsFromPlotOptions(self, dataType, *args, **kwargs):

		from .tuflowqgis_tuplot import TuPlot

		if dataType not in self.plotDataToPlotMenu:
			return False

		menu = self.plotDataToPlotMenu[dataType]
		if isinstance(menu, QAction):
			if is_qt6:
				menu = menu.parent()
			else:
				menu = menu.parentWidget()
		elif isinstance(menu, QToolButton):
			return True

		return menu.checkedActions(*args, **kwargs)

	def setCheckedItemsPlotOptions(self, dataType, items):

		from .tuflowqgis_tuplot import TuPlot

		menu = self.plotDataToPlotMenu[dataType]
		if isinstance(menu, QAction):
			if is_qt6:
				menu = menu.parent()
			else:
				menu = menu.parentWidget()
		elif isinstance(menu, QToolButton):
			return True

		return menu.setCheckedActions(items)
	
	def cursorTrackingToggled(self):
		if self.cursorTrackingButton.isChecked():
			self.tuView.tuOptions.liveMapTracking = True
		else:
			self.tuView.tuOptions.liveMapTracking = False
			
		return True

	def addAverageMethods(self, parentMenu):
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

		parentMenu.clear()
		for method in methods:
			menu = DatasetMenu(method, self.averageMethodTSMenu)
			menu.menuAction().setCheckable(True)

			if "Single Vertical Level" in method:
				self.singleVerticalLevelMethod(menu, False)
			elif 'Multi Vertical Level' in method:
				self.multiVerticalLevelMethod(menu, False)
			elif 'Sigma' in method:
				self.sigmaMethod(menu, False)
			elif 'relative to' in method:
				self.relativeDepthMethod(menu, False)
			elif 'absolute to' in method:
				self.absoluteElevationMethod(menu, False)

			parentMenu.addAction(menu.menuAction())
			self.averageMethodActions.append(menu)

	def generateDepthAveragingAction(self, avType, parentMenu, bAdd=False):
		from .tuflowqgis_tuplot import TuPlot

		if not [x for x in parentMenu.menu().actions() if avType.lower() in x.text().lower()]:
			return None
		menu = [x for x in parentMenu.menu().actions() if avType.lower() in x.text().lower()][0]
		if 'single vertical level' in avType.lower():
			action = SingleSpinBoxAction(menu, bAdd, "Vertical Layer Index", range=(1, 99999))
		elif 'multi vertical level' in avType.lower():
			action = SingleSpinBoxAction(menu, bAdd, "Start Vertical Layer Index", "End Vertical Layer Index",
			                             range=(1, 99999))
		elif 'sigma' in avType.lower():
			action = DoubleSpinBoxAction(menu, bAdd, "Start Fraction", "End Fraction",
			                             range=(0, 99999), decimals=2, single_step=0.1,
			                             value=(0, 1))
		elif 'relative to' in avType.lower():
			action = DoubleSpinBoxAction(menu, bAdd, "Start Depth", "End Depth",
			                             range=(0, 99999), decimals=2, single_step=1.0,
			                             value=(0, 10))
		elif 'absolute to' in avType.lower():
			action = DoubleSpinBoxAction(menu, bAdd, "Start Elevation", "End Elevation",
			                             range=(-99999, 99999), decimals=2, single_step=1.0,
			                             value=(0, -10))

		items = []
		while True:
			if is_qt6:
				parentMenu0 = parentMenu.parent()
			else:
				parentMenu0 = parentMenu.parentWidget()
			if parentMenu0 is None:
				break
			parentMenu = parentMenu0
		if isinstance(parentMenu, QMenu):
			if 'time series' in parentMenu.menuAction().text().lower():
				items = self.getItemsFromPlotOptions(TuPlot.DataTimeSeries2D, 'data type')
			else:
				items = self.getItemsFromPlotOptions(TuPlot.DataCrossSection2D, 'data type')
		elif isinstance(parentMenu, QAction):
			if 'time series' in parentMenu.text().lower():
				items = self.getItemsFromPlotOptions(TuPlot.DataTimeSeries2D, 'data type')
			else:
				items = self.getItemsFromPlotOptions(TuPlot.DataCrossSection2D, 'data type')

		action.cboSetItems(items)
		return action

	def singleVerticalLevelMethod(self, menu: QMenu, bAdd: bool) -> None:
		if bAdd:
			action = SingleSpinBoxAction(menu, bAdd, "Vertical Layer Index", range=(1, 99999))
			action.setCheckable(True)
			action.removeActionRequested.connect(lambda e: self.removeAveragingMethod(e, menu))
			lastAction = menu.actions()[-2]  # insert before separator
			menu.insertAction(lastAction, action)
			if len(menu.actions()) > 3:
				if not menu.actions()[0].bCheckBox:
					menu.actions()[0].insertCheckbox()
				items = menu.actions()[0].cboItems()
				ci = menu.actions()[-4].cboCurrentItem()
				action.cboSetItems(items, set_cbo_current_item=ci)
		else:
			action = SingleSpinBoxAction(menu, bAdd, "Vertical Layer Index", range=(1, 99999))
			action.setCheckable(True)
			action.removeActionRequested.connect(lambda e: self.removeAveragingMethod(e, menu))
			menu.addAction(action)
			menu.addSeparator()
			action = QAction("Add Additional...", menu)
			menu.addAction(action)
			action.triggered.connect(lambda e: self.singleVerticalLevelMethod(menu, True))

	def multiVerticalLevelMethod(self, menu: QMenu, bAdd: bool) -> None:
		if bAdd:
			action = SingleSpinBoxAction(menu, bAdd, "Start Vertical Layer Index", "End Vertical Layer Index",
			                             range=(1, 99999))
			action.setCheckable(True)
			action.removeActionRequested.connect(lambda e: self.removeAveragingMethod(e, menu))
			lastAction = menu.actions()[-2]  # insert before separator
			menu.insertAction(lastAction, action)
			if len(menu.actions()) > 3:
				if not menu.actions()[0].bCheckBox:
					menu.actions()[0].insertCheckbox()
				items = menu.actions()[0].cboItems()
				ci = menu.actions()[-4].cboCurrentItem()
				action.cboSetItems(items, set_cbo_current_item=ci)
		else:
			action = SingleSpinBoxAction(menu, bAdd, "Start Vertical Layer Index", "End Vertical Layer Index",
			                             range=(1, 99999))
			action.setCheckable(True)
			action.removeActionRequested.connect(lambda e: self.removeAveragingMethod(e, menu))
			menu.addAction(action)
			menu.addSeparator()
			action = QAction("Add Additional...", menu)
			menu.addAction(action)
			action.triggered.connect(lambda e: self.multiVerticalLevelMethod(menu, True))

	def sigmaMethod(self, menu: QMenu, bAdd: bool) -> None:
		if bAdd:
			action = DoubleSpinBoxAction(menu, bAdd, "Start Fraction", "End Fraction",
			                             range=(0, 99999), decimals=2, single_step=0.1,
			                             value=(0, 1))
			action.setCheckable(True)
			action.removeActionRequested.connect(lambda e: self.removeAveragingMethod(e, menu))
			lastAction = menu.actions()[-2]  # insert before separator
			menu.insertAction(lastAction, action)
			if len(menu.actions()) > 3:
				if not menu.actions()[0].bCheckBox:
					menu.actions()[0].insertCheckbox()
				items = menu.actions()[0].cboItems()
				ci = menu.actions()[-4].cboCurrentItem()
				action.cboSetItems(items, set_cbo_current_item=ci)
		else:
			action = DoubleSpinBoxAction(menu, bAdd, "Start Fraction", "End Fraction",
			                             range=(0, 99999), decimals=2, single_step=0.1,
			                             value=(0, 1))
			action.setCheckable(True)
			action.removeActionRequested.connect(lambda e: self.removeAveragingMethod(e, menu))
			menu.addAction(action)
			menu.addSeparator()
			action = QAction("Add Additional...", menu)
			menu.addAction(action)
			action.triggered.connect(lambda e: self.sigmaMethod(menu, True))

	def relativeDepthMethod(self, menu: QMenu, bAdd: bool) -> None:
		if bAdd:
			action = DoubleSpinBoxAction(menu, bAdd, "Start Depth", "End Depth",
			                             range=(0, 99999), decimals=2, single_step=1.0,
			                             value=(0, 10))
			action.setCheckable(True)
			action.removeActionRequested.connect(lambda e: self.removeAveragingMethod(e, menu))
			lastAction = menu.actions()[-2]  # insert before separator
			menu.insertAction(lastAction, action)
			if len(menu.actions()) > 3:
				if not menu.actions()[0].bCheckBox:
					menu.actions()[0].insertCheckbox()
				items = menu.actions()[0].cboItems()
				ci = menu.actions()[-4].cboCurrentItem()
				action.cboSetItems(items, set_cbo_current_item=ci)
		else:
			action = DoubleSpinBoxAction(menu, bAdd, "Start Depth", "End Depth",
			                             range=(0, 99999), decimals=2, single_step=1.0,
			                             value=(0, 10))
			action.setCheckable(True)
			action.removeActionRequested.connect(lambda e: self.removeAveragingMethod(e, menu))
			menu.addAction(action)
			menu.addSeparator()
			action = QAction("Add Additional...", menu)
			menu.addAction(action)
			action.triggered.connect(lambda e: self.relativeDepthMethod(menu, True))

	def absoluteElevationMethod(self, menu: QMenu, bAdd: bool) -> None:
		if bAdd:
			action = DoubleSpinBoxAction(menu, bAdd, "Start Elevation", "End Elevation",
			                             range=(-99999, 99999), decimals=2, single_step=1.0,
			                             value=(0, -10))
			action.setCheckable(True)
			action.removeActionRequested.connect(lambda e: self.removeAveragingMethod(e, menu))
			lastAction = menu.actions()[-2]  # insert before separator
			menu.insertAction(lastAction, action)
			if len(menu.actions()) > 3:
				if not menu.actions()[0].bCheckBox:
					menu.actions()[0].insertCheckbox()
				items = menu.actions()[0].cboItems()
				ci = menu.actions()[-4].cboCurrentItem()
				action.cboSetItems(items, set_cbo_current_item=ci)
		else:
			action = DoubleSpinBoxAction(menu, bAdd, "Start Elevation", "End Elevation",
			                             range=(-99999, 99999), decimals=2, single_step=1.0,
			                             value=(0, -10))
			action.setCheckable(True)
			action.removeActionRequested.connect(lambda e: self.removeAveragingMethod(e, menu))
			menu.addAction(action)
			menu.addSeparator()
			action = QAction("Add Additional...", menu)
			menu.addAction(action)
			action.triggered.connect(lambda e: self.absoluteElevationMethod(menu, True))

	def removeAveragingMethod(self, p, menu):
		if len(menu.actions()) > 3:
			action = menu.actionAt(p)
			menu.removeAction(action)
			if len(menu.actions()) <= 3:
				if menu.actions()[0].bCheckBox:
					menu.actions()[0].removeCheckbox()

	def getAveragingMethods(self, dataType, groupMetadata):
		"""

		"""

		from .tuflowqgis_tuplot import TuPlot

		# if groupMetadata.maximumVerticalLevelsCount() < 2: return [None]

		if dataType == TuPlot.DataTimeSeriesDepAv or dataType == TuPlot.DataCrossSectionDepAv:
			if isinstance(self.plotDataToPlotMenu[dataType], (QAction, QWidgetAction)) and is_qt6:
				menu = self.plotDataToPlotMenu[dataType].parent()
			else:
				menu = self.plotDataToPlotMenu[dataType].parentWidget()
		else:
			return [None]

		averagingMethods = []
		for action in menu.actions():
			if action.isChecked():
				counter = 0
				for action2 in action.menu().actions():
					if action2.isChecked():
						if groupMetadata.maximumVerticalLevelsCount() < 2:
							averagingMethods.append(None)
						else:
							averagingMethods.append('{0}_{1}'.format(action.text(), counter))
							counter += 1

		if averagingMethods:
			return averagingMethods
		else:
			return [None]

	def getAveragingParameters(self, dataType, averagingMethod):
		if isinstance(self.plotDataToPlotMenu[dataType], (QAction, QWidgetAction)) and is_qt6:
			menu = self.plotDataToPlotMenu[dataType].parent()
		else:
			menu = self.plotDataToPlotMenu[dataType].parentWidget()

		for action in menu.actions():
			if action.text() in averagingMethod:
				counter = 0
				for action2 in action.menu().actions():
					if action2.isChecked():
						if counter == int(averagingMethod[-1]):
							return action2.values()
						else:
							counter += 1

		return None

	def qgisDisconnect(self):
		# mpl toolbar
		try:
			self.plotTSMenu.menuAction().triggered.disconnect()
		except:
			pass
		try:
			self.plotLPMenu.menuAction().triggered.disconnect()
		except:
			pass
		try:
			self.plotFluxButton.released.disconnect()
		except:
			pass
		try:
			self.cursorTrackingButton.released.disconnect(self.cursorTrackingToggled)
		except:
			pass
		try:
			self.meshGridAction.triggered.disconnect(self.tuMenuFunctions.toggleMeshRender)
		except:
			pass
		try:
			self.curtainPlotMenu.menuAction().triggered.disconnect()
		except:
			pass
		try:
			self.averageMethodTSMenu.menuAction().triggered.disconnect()
		except:
			pass
		try:
			self.averageMethodCSMenu.menuAction().triggered.disconnect()
		except:
			pass
		try:
			self.plotVPMenu.menuAction().triggered.disconnect()
		except:
			pass
		# view toolbars
		self.viewToolbarTimeSeries.qgisDisconnect()
		self.viewToolbarLongPlot.qgisDisconnect()
		self.viewToolbarCrossSection.qgisDisconnect()
		self.viewToolbarVerticalProfile.qgisDisconnect()
		# map plotting toolbar
		try:
			self.plotTSMenu.menuAction().triggered.disconnect()
		except:
			pass
		try:
			self.plotLPMenu.menuAction().triggered.disconnect()
		except:
			pass
		try:
			self.plotFluxButton.released.disconnect()
		except:
			pass
		try:
			self.cursorTrackingButton.released.disconnect(self.cursorTrackingToggled)
		except:
			pass
		try:
			self.meshGridAction.triggered.disconnect(self.tuMenuFunctions.toggleMeshRender)
		except:
			pass
		try:
			self.curtainPlotMenu.menuAction().triggered.disconnect()
		except:
			pass
		try:
			self.averageMethodTSMenu.menuAction().triggered.disconnect()
		except:
			pass
		try:
			self.averageMethodCSMenu.menuAction().triggered.disconnect()
		except:
			pass
		try:
			self.plotVPMenu.menuAction().triggered.disconnect()
		except:
			pass







