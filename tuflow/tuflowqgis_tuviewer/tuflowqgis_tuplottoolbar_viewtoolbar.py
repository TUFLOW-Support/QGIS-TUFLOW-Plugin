import os
import sys
import time
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from qgis.gui import *
from PyQt5.QtWidgets import *
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tumenufunctions import TuMenuFunctions
from tuflow.dataset_menu import DatasetMenu
from tuflow.spinbox_action import SingleSpinBoxAction, DoubleSpinBoxAction
import numpy as np


class ViewToolbar():
	"""
	Class for handling view toolbar since it has to be initiated for each plot window.
	
	"""
	
	
	def __init__(self, TuPlotToolbar, plotNo):
		self.tuPlotToolbar = TuPlotToolbar
		self.tuPlot = TuPlotToolbar.tuPlot
		self.tuView = self.tuPlot.tuView
		self.iface = self.tuView.iface
		self.plotNo = plotNo
		self.tuMenuFunctions = TuMenuFunctions(self.tuView)
		
		self.initialiseViewToolbar()
	
	def initialiseViewToolbar(self):
		qv = Qgis.QGIS_VERSION_INT

		w = self.tuView.tuOptions.iconSize
		if qv >= 31600:
			w = int(QgsApplication.scaleIconSize(self.tuView.tuOptions.iconSize, True))

		w2 = int(np.ceil(w * 1.5))
		w3 = int(np.ceil(w2 * 7))
		w4 = int(np.ceil(w3 + w2*2))

		# toolbar settings
		self.viewToolbar = QToolBar('View Toolbar', self.tuView.ViewToolbarFrame)
		self.viewToolbar.setIconSize(QSize(w, w))
		self.tuView.ViewToolbarFrame.setMinimumHeight(w2)
		self.tuView.ViewToolbarFrame.setMinimumWidth(w3)
		self.viewToolbar.resize(QSize(w4, w2))
		
		# icons
		dir = os.path.dirname(os.path.dirname(__file__))
		refreshIcon = QIcon(os.path.join(dir, "icons", "refresh_plot_black.svg"))
		clearIcon = QIcon(os.path.join(dir, "icons", "clear_plot.svg"))
		freezeXYAxisIcon = QIcon(os.path.join(dir, "icons", "freeze_xyaxis.svg"))
		freezeXAxisIcon = QIcon(os.path.join(dir, "icons", "freeze_xaxis.svg"))
		freezeYAxisIcon = QIcon(os.path.join(dir, "icons", "freeze_yaxis.svg"))
		legendIcon = QIcon(os.path.join(dir, "icons", "legend.svg"))
		userPlotDataIcon = QIcon(os.path.join(dir, "icons", "user_plot_data.svg"))
		
		# buttons
		self.refreshPlotButton = QToolButton(self.viewToolbar)
		self.refreshPlotButton.setIcon(refreshIcon)
		self.refreshPlotButton.setToolTip('Refresh Current Plot')
		self.clearPlotButton = QToolButton(self.viewToolbar)
		self.clearPlotButton.setIcon(clearIcon)
		self.clearPlotButton.setToolTip('Clear Current Plot')
		
		self.freezeXYAxisButton = QToolButton(self.viewToolbar)
		self.freezeXYAxisAction = QAction(freezeXYAxisIcon, 'Freeze Axis Limits', self.freezeXYAxisButton)
		self.freezeXYAxisAction.setCheckable(True)
		self.freezeXYAxisButton.setDefaultAction(self.freezeXYAxisAction)
		self.freezeXYAxisButton.setCheckable(True)

		self.freezeXAxisButton = QToolButton(self.viewToolbar)
		self.freezeXAxisButton.setCheckable(True)
		self.freezeXAxisAction = QAction(freezeXAxisIcon, 'Freeze X-Axis Limits Only', self.freezeXAxisButton)
		self.freezeXAxisAction.setCheckable(True)
		self.freezeXAxisButton.setDefaultAction(self.freezeXAxisAction)
		
		self.freezeYAxisButton = QToolButton(self.viewToolbar)
		self.freezeYAxisButton.setCheckable(True)
		self.freezeYAxisAction = QAction(freezeYAxisIcon, 'Freeze Y-Axis Limits Only', self.freezeYAxisButton)
		self.freezeYAxisAction.setCheckable(True)
		self.freezeYAxisButton.setDefaultAction(self.freezeYAxisAction)

		# grid lines
		self.hGridLines_action = QAction('Horizontal Grid Lines', None)
		self.hGridLines_action.setCheckable(True)
		self.hGridLines_action.setChecked(True)
		self.vGridLines_action = QAction('Vertical Grid Lines', None)
		self.vGridLines_action.setCheckable(True)
		self.vGridLines_action.setChecked(True)

		# axis font size
		# fontsize = self.tuPlot.subplotTimeSeries.xaxis.get_label().get_size()
		fontsize = self.tuView.tuOptions.defaultFontSize
		self.axisFontSize_action = SingleSpinBoxAction(None, False, "Axis Font Size: ",
		                                               range=(1, 128),
		                                               value=(fontsize), set_cbo_visible=False,
		                                               enable_menu_highlighting=True)

		# axis label font size
		self.axisLabelFontSize_action = SingleSpinBoxAction(None, False, "Axis Label Font Size: ",
		                                                    range=(1, 128),
		                                                    value=(fontsize), set_cbo_visible=False,
		                                                    enable_menu_highlighting=True)

		# self.legendMenu = QMenu('Legend')
		self.legendMenu = DatasetMenu('Legend')
		self.legendMenu.menuAction().setIcon(legendIcon)
		self.legendMenu.menuAction().setCheckable(True)
		self.legendMenu.menuAction().setChecked(True)
		self.legendFontSize = SingleSpinBoxAction(self.legendMenu, False, "Font Size: ",
		                                          range=(1, 128),
		                                          value=(fontsize), set_cbo_visible=False,
		                                          enable_menu_highlighting=True)
		self.legendMenu.addAction(self.legendFontSize)
		self.legendMenu.addSeparator()
		self.legendVertical = QAction('Vertical Legend', self.legendMenu)
		self.legendVertical.setCheckable(True)
		self.legendVertical.setChecked(True)
		self.legendMenu.addAction(self.legendVertical)
		self.legendHorizontal = QAction('Horizontal Legend', self.legendMenu)
		self.legendHorizontal.setCheckable(True)
		self.legendMenu.addAction(self.legendHorizontal)
		self.legendCustomOrientation = SingleSpinBoxAction(self.legendMenu, True, "No. Columns: ",
		                                                   range=(0, 10),
		                                                   value=(1), set_cbo_visible=False, cb_setChecked=False,
		                                                   enable_menu_highlighting=True)
		self.legendCustomOrientation.setCheckable(True)
		self.legendMenu.addAction(self.legendCustomOrientation)
		self.legendMenu.addSeparator()
		self.legendAuto = QAction('Auto', self.legendMenu)
		self.legendAuto.setCheckable(True)
		self.legendAuto.setChecked(True)
		self.legendMenu.addAction(self.legendAuto)
		self.legendUL = QAction('Upper Left', self.legendMenu)
		self.legendUL.setCheckable(True)
		self.legendMenu.addAction(self.legendUL)
		self.legendLL = QAction('Lower Left', self.legendMenu)
		self.legendLL.setCheckable(True)
		self.legendMenu.addAction(self.legendLL)
		self.legendCL = QAction('Centre Left', self.legendMenu)
		self.legendCL.setCheckable(True)
		self.legendMenu.addAction(self.legendCL)
		self.legendUR = QAction('Upper Right', self.legendMenu)
		self.legendUR.setCheckable(True)
		self.legendMenu.addAction(self.legendUR)
		self.legendLR = QAction('Lower Right', self.legendMenu)
		self.legendLR.setCheckable(True)
		self.legendMenu.addAction(self.legendLR)
		self.legendCR = QAction('Centre Right', self.legendMenu)
		self.legendCR.setCheckable(True)
		self.legendMenu.addAction(self.legendCR)
		self.legendLC = QAction('Lower Centre', self.legendMenu)
		self.legendLC.setCheckable(True)
		self.legendMenu.addAction(self.legendLC)
		self.legendUC = QAction('Upper Centre', self.legendMenu)
		self.legendUC.setCheckable(True)
		self.legendMenu.addAction(self.legendUC)
		self.legendC = QAction('Centre', self.legendMenu)
		self.legendC.setCheckable(True)
		self.legendMenu.addAction(self.legendC)
		self.legendCustomPos = DoubleSpinBoxAction(self.legendMenu, True, "Custom Pos X:", "Y:",
		                                           range=(-10, 10), decimals=2, single_step=0.1,
		                                           value=(0, 0), set_cbo_visible=False, cb_setChecked=False,
		                                           enable_menu_highlighting=True)
		self.legendCustomPos.setCheckable(True)
		self.legendMenu.addAction(self.legendCustomPos)
		
		self.userPlotDataManagerButton = QToolButton(self.viewToolbar)
		self.userPlotDataManagerAction = QAction(userPlotDataIcon, 'User Plot Data Manager', self.userPlotDataManagerButton)
		self.userPlotDataManagerButton.setDefaultAction(self.userPlotDataManagerAction)
		
		# add buttons to toolbar
		self.viewToolbar.addWidget(self.refreshPlotButton)
		self.viewToolbar.addWidget(self.clearPlotButton)
		self.viewToolbar.addWidget(self.freezeXYAxisButton)
		self.viewToolbar.addWidget(self.freezeXAxisButton)
		self.viewToolbar.addWidget(self.freezeYAxisButton)
		self.viewToolbar.addAction(self.legendMenu.menuAction())
		self.viewToolbar.addWidget(self.userPlotDataManagerButton)
		
		# connect buttons
		self.refreshPlotButton.released.connect(self.tuView.refreshCurrentPlot)
		self.clearPlotButton.released.connect(lambda: self.tuView.tuPlot.clearPlot2(self.plotNo, clear_rubberband=True))
		self.freezeXYAxisButton.released.connect(self.freezeXYAxis)
		self.freezeXAxisButton.released.connect(self.freezeXAxis)
		self.freezeYAxisButton.released.connect(self.freezeYAxis)
		self.legendFontSize.sbValueChanged.connect(self.legendFontSizeChanged)
		self.legendVertical.triggered.connect(lambda: self.legendOrientationChanged(self.legendVertical))
		self.legendHorizontal.triggered.connect(lambda: self.legendOrientationChanged(self.legendHorizontal))
		self.legendCustomOrientation.triggered.connect(lambda: self.legendOrientationChanged(self.legendCustomOrientation))
		self.legendCustomOrientation.sbValueChanged.connect(lambda: self.legendOrientationChanged(self.legendCustomOrientation))
		self.legendMenu.menuAction().triggered.connect(lambda: self.legendPosChanged(None))
		self.legendAuto.triggered.connect(lambda: self.legendPosChanged(self.legendAuto))
		self.legendUL.triggered.connect(lambda: self.legendPosChanged(self.legendUL))
		self.legendLL.triggered.connect(lambda: self.legendPosChanged(self.legendLL))
		self.legendUR.triggered.connect(lambda: self.legendPosChanged(self.legendUR))
		self.legendLR.triggered.connect(lambda: self.legendPosChanged(self.legendLR))
		self.legendCL.triggered.connect(lambda: self.legendPosChanged(self.legendCL))
		self.legendCR.triggered.connect(lambda: self.legendPosChanged(self.legendCR))
		self.legendLC.triggered.connect(lambda: self.legendPosChanged(self.legendLC))
		self.legendUC.triggered.connect(lambda: self.legendPosChanged(self.legendUC))
		self.legendC.triggered.connect(lambda: self.legendPosChanged(self.legendC))
		self.legendCustomPos.triggered.connect(lambda: self.legendPosChanged(self.legendCustomPos))
		self.legendCustomPos.sbValueChanged.connect(lambda: self.legendPosChanged(self.legendCustomPos))
		self.userPlotDataManagerAction.triggered.connect(self.tuMenuFunctions.openUserPlotDataManager)
		self.hGridLines_action.triggered.connect(self.gridLines_toggled)
		self.vGridLines_action.triggered.connect(self.gridLines_toggled)
		self.axisFontSize_action.sbValueChanged.connect(self.axisFontSizeChanged)
		self.axisLabelFontSize_action.sbValueChanged.connect(self.axisLabelFontSizeChanged)

		# self.viewToolbar.iconSizeChanged.connect(lambda e: self.tuView.toolbarIconSizeChanged(e, self.viewToolbar, self.tuView.ViewToolbarFrame))

	def freezeXYAxis(self):
		
		if self.freezeXYAxisButton.isChecked():
			self.freezeXAxisAction.setChecked(True)
			self.freezeYAxisAction.setChecked(True)
		else:
			self.freezeXAxisAction.setChecked(False)
			self.freezeYAxisAction.setChecked(False)
		
		return True
	
	def freezeXAxis(self):
		if not self.freezeXAxisAction.isChecked():
			if self.freezeXYAxisAction.isChecked():
				self.freezeXYAxisAction.setChecked(False)
			
		return True
	
	def freezeYAxis(self):
		if not self.freezeYAxisAction.isChecked():
			if self.freezeXYAxisAction.isChecked():
				self.freezeXYAxisAction.setChecked(False)
		
		return True
	
	def setVisible(self, visibility):
		if visibility:
			self.viewToolbar.setVisible(True)
		else:
			self.viewToolbar.setVisible(False)

	def legendOrientationChanged(self, orienAction):
		actions = [self.legendVertical, self.legendHorizontal, self.legendCustomOrientation]

		if orienAction is not None:
			for action in actions:
				if action == orienAction:
					if not orienAction.isChecked():
						orienAction.setChecked(True)
				else:
					action.setChecked(False)

		# self.tuView.refreshCurrentPlot()
		plotNo = self.tuView.tabWidget.currentIndex()
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.tuPlot.plotEnumerator(plotNo)
		self.tuPlot.updateLegend(plotNo)
		figure.tight_layout()
		plotWidget.draw()

		return True
			
	def legendPosChanged(self, posAction, index=None):
		actions = {self.legendAuto: 0, self.legendUL: 2, self.legendLL: 3, self.legendUR: 1, self.legendLR: 4,
		           self.legendCL: 6, self.legendCR: 7, self.legendLC: 8, self.legendUC: 9, self.legendC: 10,
		           self.legendCustomPos: 100}

		if posAction is not None:
			for action in actions:
				if action == posAction:
					if not posAction.isChecked():
						# posAction.setChecked(True)  # cannot toggle off position - must choose a new one
						self.legendMenu.menuAction().setChecked(False)
					else:
						self.legendMenu.menuAction().setChecked(True)
				else:
					action.setChecked(False)
		elif index is not None:
			for action, i in actions.items():
				if i == index:
					action.setChecked(True)
				else:
					action.setChecked(False)

		# self.tuView.refreshCurrentPlot()
		plotNo = self.tuView.tabWidget.currentIndex()
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.tuPlot.plotEnumerator(plotNo)
		self.tuPlot.updateLegend(plotNo)
		figure.tight_layout()
		plotWidget.draw()

		return True

	def legendFontSizeChanged(self):
		plotNo = self.tuView.tabWidget.currentIndex()
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.tuPlot.plotEnumerator(plotNo)
		self.tuPlot.updateLegend(plotNo)
		figure.tight_layout()
		plotWidget.draw()
		
	def legendCurrentIndex(self):
		if self.legendUR.isChecked():
			return 1
		elif self.legendUL.isChecked():
			return 2
		elif self.legendLL.isChecked():
			return 3
		elif self.legendLR.isChecked():
			return 4
		else:
			return 0

	def gridLines_toggled(self):
		plotNo = self.tuView.tabWidget.currentIndex()
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.tuPlot.plotEnumerator(plotNo)
		self.tuPlot.manageMatplotlibAxe(subplot)
		plotWidget.draw()

	def axisFontSizeChanged(self):
		plotNo = self.tuView.tabWidget.currentIndex()
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.tuPlot.plotEnumerator(plotNo)
		subplot2 = self.tuPlot.getSecondaryAxis(plotNo, create=False)

		axisFontSize = self.axisFontSize_action.value(0)
		subplot.tick_params(axis='both', which='both', labelsize=axisFontSize)
		if subplot2 is not None:
			subplot2.tick_params(axis='both', which='both', labelsize=axisFontSize)
		figure.tight_layout()
		plotWidget.draw()

	def axisLabelFontSizeChanged(self):
		plotNo = self.tuView.tabWidget.currentIndex()
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.tuPlot.plotEnumerator(plotNo)
		subplot2 = self.tuPlot.getSecondaryAxis(plotNo, create=False)

		axisLabelFontSize = self.axisLabelFontSize_action.value(0)
		subplot.xaxis.label.set_size(axisLabelFontSize)
		subplot.yaxis.label.set_size(axisLabelFontSize)
		if subplot2 is not None:
			if plotNo == 3:  # vertical profile
				subplot2.xaxis.label.set_size(axisLabelFontSize)
			else:
				subplot2.yaxis.label.set_size(axisLabelFontSize)
		figure.tight_layout()
		plotWidget.draw()

	def qgisDisconnect(self):
		try:
			self.refreshPlotButton.released.disconnect(self.tuView.refreshCurrentPlot)
		except:
			pass
		try:
			self.clearPlotButton.released.disconnect()
		except:
			pass
		try:
			self.freezeXYAxisButton.released.disconnect(self.freezeXYAxis)
		except:
			pass
		try:
			self.freezeXAxisButton.released.disconnect(self.freezeXAxis)
		except:
			pass
		try:
			self.freezeYAxisButton.released.disconnect(self.freezeYAxis)
		except:
			pass
		try:
			self.legendMenu.menuAction().triggered.disconnect()
		except:
			pass
		try:
			self.legendAuto.triggered.disconnect()
		except:
			pass
		try:
			self.legendUL.triggered.disconnect()
		except:
			pass
		try:
			self.legendLL.triggered.disconnect()
		except:
			pass
		try:
			self.legendUR.triggered.disconnect()
		except:
			pass
		try:
			self.legendLR.triggered.disconnect()
		except:
			pass
		try:
			self.userPlotDataManagerAction.triggered.disconnect(self.tuMenuFunctions.openUserPlotDataManager)
		except:
			pass
		try:
			self.hGridLines_action.triggered.disconnect(self.gridLines_toggled)
		except:
			pass
		try:
			self.vGridLines_action.triggered.disconnect(self.gridLines_toggled)
		except:
			pass