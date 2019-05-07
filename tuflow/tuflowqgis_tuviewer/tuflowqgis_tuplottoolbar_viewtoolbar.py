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
		# toolbar settings
		self.viewToolbar = QToolBar('View Toolbar', self.tuView.ViewToolbarFrame)
		self.viewToolbar.setIconSize(QSize(20, 20))
		self.viewToolbar.resize(QSize(250, 30))
		
		# icons
		dir = os.path.dirname(os.path.dirname(__file__))
		refreshIcon = QIcon(os.path.join(dir, "icons", "refreshplotblack.png"))
		clearIcon = QIcon(os.path.join(dir, "icons", "ClearPlot.png"))
		freezeXYAxisIcon = QIcon(os.path.join(dir, "icons", "freeze_xyaxis.png"))
		freezeXAxisIcon = QIcon(os.path.join(dir, "icons", "freeze_xaxis.png"))
		freezeYAxisIcon = QIcon(os.path.join(dir, "icons", "freeze_yaxis.png"))
		legendIcon = QIcon(os.path.join(dir, "icons", "legend_icon.png"))
		userPlotDataIcon = QIcon(os.path.join(dir, "icons", "userPlotData.png"))
		
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
		
		self.legendMenu = QMenu('Legend')
		self.legendMenu.menuAction().setIcon(legendIcon)
		self.legendMenu.menuAction().setCheckable(True)
		self.legendMenu.menuAction().setChecked(True)
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
		self.legendUR = QAction('Upper Right', self.legendMenu)
		self.legendUR.setCheckable(True)
		self.legendMenu.addAction(self.legendUR)
		self.legendLR = QAction('Lower Right', self.legendMenu)
		self.legendLR.setCheckable(True)
		self.legendMenu.addAction(self.legendLR)
		
		self.userPlotDataManagerButton = QToolButton(self.viewToolbar)
		self.userPlotDataManagerAction = QAction(userPlotDataIcon, 'User Plot Data Manager', self.userPlotDataManagerButton)
		self.userPlotDataManagerButton.setDefaultAction(self.userPlotDataManagerAction)
		
		# add buttons to toolbar
		self.viewToolbar.addWidget(self.refreshPlotButton)
		self.viewToolbar.addSeparator()
		self.viewToolbar.addWidget(self.clearPlotButton)
		self.viewToolbar.addSeparator()
		self.viewToolbar.addWidget(self.freezeXYAxisButton)
		self.viewToolbar.addWidget(self.freezeXAxisButton)
		self.viewToolbar.addWidget(self.freezeYAxisButton)
		self.viewToolbar.addSeparator()
		self.viewToolbar.addSeparator()
		self.viewToolbar.addAction(self.legendMenu.menuAction())
		self.viewToolbar.addSeparator()
		self.viewToolbar.addSeparator()
		self.viewToolbar.addWidget(self.userPlotDataManagerButton)
		
		# connect buttons
		self.refreshPlotButton.released.connect(self.tuView.refreshCurrentPlot)
		self.clearPlotButton.released.connect(lambda: self.tuView.tuPlot.clearPlot(self.plotNo, clear_rubberband=True, clear_selection=True))
		self.freezeXYAxisButton.released.connect(self.freezeXYAxis)
		self.freezeXAxisButton.released.connect(self.freezeXAxis)
		self.freezeYAxisButton.released.connect(self.freezeYAxis)
		self.legendMenu.menuAction().triggered.connect(lambda: self.legendPosChanged(None))
		self.legendAuto.triggered.connect(lambda: self.legendPosChanged(self.legendAuto))
		self.legendUL.triggered.connect(lambda: self.legendPosChanged(self.legendUL))
		self.legendLL.triggered.connect(lambda: self.legendPosChanged(self.legendLL))
		self.legendUR.triggered.connect(lambda: self.legendPosChanged(self.legendUR))
		self.legendLR.triggered.connect(lambda: self.legendPosChanged(self.legendLR))
		self.userPlotDataManagerAction.triggered.connect(self.tuMenuFunctions.openUserPlotDataManager)
	
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
			
	def legendPosChanged(self, posAction, index=None):
		actions = {self.legendAuto: 0, self.legendUL: 2, self.legendLL: 3, self.legendUR: 1, self.legendLR: 4}
		
		if posAction is not None:
			for action in actions:
				if action == posAction:
					if not posAction.isChecked():
						posAction.setChecked(True)  # cannot toggle off position - must choose a new one
				else:
					action.setChecked(False)
		elif index is not None:
			for action, i in actions.items():
				if i == index:
					action.setChecked(True)
				else:
					action.setChecked(False)
		
		self.tuView.refreshCurrentPlot()
				
		return True
		
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