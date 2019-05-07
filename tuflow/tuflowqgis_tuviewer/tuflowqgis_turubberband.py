import sys
import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets import *
from tuflow.canvas_event import *


class TuRubberBand():
	"""
	Class for rubberband.
	
	"""
	
	def __init__(self, TuPlot):
		self.tuPlot = TuPlot
		self.tuView = TuPlot.tuView
		self.iface = self.tuView.iface
		self.canvas = self.tuView.canvas
		self.cursorPrev = 0  # count how many times the cursor has been overwritten - need this to restore default cursor
		self.rubberBand = QgsRubberBand(self.canvas, False)  # temporary polyline or point
		self.rubberBands = []  # list of QgsRubberBand
		self.marker = QgsVertexMarker(self.canvas)
		self.markers = []  # list -> QgsMarkers
		self.markerPoints = []  # list -> QgsPoint
		self.point = None  # single point for time series
		self.points = []  # list of x, y coords of line
		self.linePoints = []  # list of QgsVertexMarkers for line vertices
		self.line = None  # line for cross section
		self.cursorTrackingConnected = False
		
	def startRubberBand(self, plotNo):
		"""
		Creates a graphic polyline or point that can be drawn on the map canvas

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# determine if multi select
		multi = False
		if self.tuView.cboSelectType.currentText() == 'From Map Multi':
			multi = True
		
		# only start if not already clicked
		if not self.cursorTrackingConnected:
			
			# only start if a result type is selected
			#if self.tuView.mcboResultType.checkedItems():
				
			# determine plot type i.e. time series or long plot
			if plotNo == 0:  # time series
				
				# remove previous temporary point layer
				if not multi:
					
					# single selection
					self.tuPlot.plotSelectionPointFeat = []  # clear features from selected plot list
					self.tuPlot.clearPlot(0, retain_1d=True, retain_flow=True)
					self.markerPoints = []
					for marker in self.markers:
						self.canvas.scene().removeItem(marker)  # Remove previous temp
					self.markers = []  # list of QgsVertexMarker
					self.canvas.scene().removeItem(self.marker)  # Remove previous temp layer
					self.tuPlot.timeSeriesPlotFirst = False
					self.tuPlot.holdTimeSeriesPlot = False
				
				else:  # do not clear existing plot
					
					# multi select so only clear plot if plotting for the first time
					if self.tuPlot.timeSeriesPlotFirst:
						self.tuPlot.clearPlot(0, retain_1d=True, retain_flow=True)
						self.tuPlot.timeSeriesPlotFirst = False
					else:
						if self.markers:
							self.tuPlot.holdTimeSeriesPlot = True
				
				# initialise markers
				self.marker = QgsVertexMarker(self.canvas)
				self.marker.setColor(Qt.red)
				self.marker.setIconSize(10)
				self.marker.setIconType(QgsVertexMarker.ICON_CROSS)
				
				# setup maptool and set
				self.point = canvasEvent(self.iface, self.canvas)
				self.canvas.setMapTool(self.point)
				self.mouseTrackConnect()  # start the tuflowqgis_bridge_rubberband
			
			# else long profile / cross section i.e. line
			elif plotNo == 1:
				
				# remove previous temporary point layer
				if not multi:
					
					# single select so clear plot
					self.tuPlot.plotSelectionLineFeat = []  # clear features from selected plot list
					self.tuPlot.clearPlot(1, retain_1d=True, retain_flow=True)
					for rubberBand in self.rubberBands:
						self.canvas.scene().removeItem(rubberBand)  # Remove previous temp layer
					self.rubberBands = []
					self.tuPlot.profilePlotFirst = False
				
				else:
					
					# multi select so only clear plot if plotting for the first time
					if self.tuPlot.profilePlotFirst:  # first plot so need to remove test line
						self.tuPlot.clearPlot(1)
						self.tuPlot.profilePlotFirst = False
					else:
						self.tuPlot.holdLongProfilePlot = True
				
				# remove line vertex points regardless
				for linePoint in self.linePoints:
					self.canvas.scene().removeItem(linePoint)  # Remove previous temp layer
				self.linePoints = []
				
				# initialise rubberband
				rubberBand = QgsRubberBand(self.canvas, False)  # setup rubberband class for drawing
				rubberBand.setWidth(2)
				rubberBand.setColor(QtGui.QColor(Qt.red))
				linePoints = []  # list of QgsVertexMarkers for vertex marking
				self.points = []  # list of x, y coords of line
				rubberBand.setToGeometry(QgsGeometry.fromPolyline(self.points), None)
				self.rubberBands.append(rubberBand)
				
				# setup maptool and set
				self.line = canvasEvent(self.iface, self.canvas)
				self.canvas.setMapTool(self.line)
				self.mouseTrackConnect()  # start the tuflowqgis_bridge_rubberband
			
		return True
	
	def mouseTrackConnect(self):
		"""
		Captures signals from the custom map tool

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if not self.cursorTrackingConnected:
			
			self.cursorTrackingConnected = True
			self.cursorPrev = 1
			QApplication.setOverrideCursor(Qt.CrossCursor)
			
			if self.tuView.tabWidget.currentIndex() == 0:  # time series i.e. single point
				self.point.moved.connect(self.tsMoved)
				self.point.rightClicked.connect(self.tsRightClick)
				self.point.leftClicked.connect(self.tsLeftClick)
				self.point.doubleClicked.connect(self.tsDoubleClick)
				self.point.keyPressed.connect(self.tsEscape)
			
			elif self.tuView.tabWidget.currentIndex() == 1:  # long profile / cross section i.e. line
				self.line.moved.connect(self.csMoved)
				self.line.rightClicked.connect(self.csRightClick)
				self.line.leftClicked.connect(self.csLeftClick)
				self.line.doubleClicked.connect(self.csDoubleClick)
				self.canvas.keyPressed.connect(self.csEscape)
				
		return True
	
	def mouseTrackDisconnect(self):
		"""
		Turn off capturing of the custom map tool

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if self.cursorTrackingConnected:
			self.cursorTrackingConnected = False
			for i in range(self.cursorPrev):
				QApplication.restoreOverrideCursor()  # have to call for everytime it is overwritten to get back to default
			
			if self.tuView.tabWidget.currentIndex() == 0:  # time series i.e. single point
				self.point.moved.disconnect()
				self.point.rightClicked.disconnect()
				self.point.leftClicked.disconnect()
				self.point.doubleClicked.disconnect()
				self.point.keyPressed.disconnect()
				self.canvas.scene().removeItem(self.marker)
			
			elif self.tuView.tabWidget.currentIndex() == 1:  # long profile / cross section i.e. line
				self.line.moved.disconnect()
				self.line.rightClicked.disconnect()
				self.line.leftClicked.disconnect()
				self.line.doubleClicked.disconnect()
				self.canvas.keyPressed.disconnect()
				
		return True
	
	def tsMoved(self, position):
		"""
		Time Series moved - signal sent when cursor is moved on the map canvas

		:param position: dict -> event signal position
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if QApplication.overrideCursor() != Qt.CrossCursor:
			QApplication.setOverrideCursor(Qt.CrossCursor)
			self.cursorPrev += 1
		
		x = position['x']
		y = position['y']
		point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
		self.marker.setCenter(QgsPointXY(point))
		
		if self.tuPlot.holdTimeSeriesPlot:
			if self.tuView.tuOptions.liveMapTracking:
				self.tuPlot.tuPlot2D.plotTimeSeriesFromMap(None, QgsPointXY(point), bypass=True)
			self.tuPlot.holdTimeSeriesPlot = False  # turn off after first signal
		else:
			if self.tuView.tuOptions.liveMapTracking:
				self.tuPlot.tuPlot2D.plotTimeSeriesFromMap(None, QgsPointXY(point))
			
		return True
	
	def tsLeftClick(self, position):
		"""
		Time Series Left Clicked - Signal sent when canvas is left clicked

		:param position: dict -> event signal position
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		
		# get location
		x = position['x']
		y = position['y']
		point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
		self.markerPoints.append(point)
		
		# set up new marker and add to list so that if multi select is on, multi markers are also displayed
		marker = QgsVertexMarker(self.canvas)
		marker.setColor(Qt.red)
		marker.setFillColor(Qt.red)
		marker.setIconSize(10)
		marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
		marker.setCenter(QgsPointXY(point))
		self.markers.append(marker)
		
		# plot and worry about disconnecting canvas tracking
		if self.tuView.cboSelectType.currentText() == 'From Map Multi':
			
			# plot point and do not disconnect because multi location is on, bypass on so plotting is frozen for location
			self.tuPlot.tuPlot2D.plotTimeSeriesFromMap(None, QgsPointXY(point), bypass=True)
		
		else:
			
			# plot and disconnect because only single location needed
			self.mouseTrackDisconnect()
			self.canvas.scene().removeItem(self.marker)
			self.tuPlot.tuPlot2D.plotTimeSeriesFromMap(None, QgsPointXY(point))
			
			# unpress time series button
			#self.tuPlot.tuPlotToolbar.plotTimeSeriesButton.setChecked(False)
			self.tuPlot.tuPlotToolbar.plotTSMenu.menuAction().setChecked(False)
			
		return True
	
	def tsRightClick(self, position):
		"""
		Time Series Right Clicked - signal sent when canvas is right clicked. For time series will end.

		:param position: dict -> event signal position
		:return: bool -> True for successful, False for unsuccessful

		"""
		
		# clear last plot location so that cursor tracking plot is not kept
		if self.tuView.tuOptions.liveMapTracking:
			self.tuPlot.clearPlotLastDatasetOnly(0)
		self.canvas.scene().removeItem(self.marker)
		
		# diconnect cursor tracking
		self.mouseTrackDisconnect()
		
		# reset multi point numbering back to one
		self.tuPlot.tuPlot2D.reduceMultiPointCount(1)
		
		# unpress time series button
		self.tuPlot.tuPlotToolbar.plotTSMenu.menuAction().setChecked(False)
		
		return True
	
	def tsDoubleClick(self, position):
		"""
		Signal sent when canvas is double clicked. For time series will end.

		:param position: dict -> event signal position
		:return: bool -> True for successful, False for unsuccessful

		"""
		
		# clear last plot location so that cursor tracking plot is not kept
		self.tuPlot.clearPlotLastDatasetOnly(0)
		self.tuPlot.clearPlotLastDatasetOnly(0)
		self.canvas.scene().removeItem(self.marker)
		
		# diconnect cursor tracking
		self.mouseTrackDisconnect()
		
		# unpress time series button
		self.tuPlot.tuPlotToolbar.plotTSMenu.menuAction().setChecked(False)
		
		# reset multi point numbering back to one
		self.tuPlot.tuPlot2D.reduceMultiPointCount(2)
		
		return True
	
	def tsEscape(self, key):
		"""
		Time Series Escape - signal sent when a key is pressed in qgis. For time series will end.

		:param key: dict -> key press event
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if key['key'] == 16777216:  # Escape key
			# clear last plot location so that cursor tracking plot is not kept
			self.tuPlot.clearPlotLastDatasetOnly(0)
			
			# diconnect cursor tracking
			self.mouseTrackDisconnect()
			
			# unpress time series button
			self.tuPlot.tuPlotToolbar.plotTSMenu.menuAction().setChecked(False)
			
			# reset multi point numbering back to one
			self.tuPlot.tuPlot2D.resetMultiPointCount()
			
		return True
	
	def csMoved(self, position):
		"""
		Cross Section Moved - signal sent when cursor is moved on the map canvas

		:param position: dict -> event signal position
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if QApplication.overrideCursor() != Qt.CrossCursor:
			QApplication.setOverrideCursor(Qt.CrossCursor)
			self.cursorPrev += 1
		
		# get position
		x = position['x']
		y = position['y']
		point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
		points = []
		
		rubberBand = self.rubberBands[-1]
		
		# reset line and draw new line based on cursor position
		if self.points:
			try:  # QGIS 2
				if QGis.QGIS_VERSION >= 10900:
					rubberBand.reset(QGis.Line)
				else:
					rubberBand.reset(False)
			except:  # QGIS 3
				rubberBand.reset(QgsWkbTypes.LineGeometry)
			# draw up to locked in points
			rubberBand.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.points]), None)
			points = self.points[:]  # for live cursor tracking
			# add cursor position
			rubberBand.addPoint(point)
			points.append(point)  # for live cursor tracking
			
			# create memory polyline layer
			if self.tuView.tuOptions.liveMapTracking:
				self.createMemoryLayer(True, points=points)
			
		return True
	
	def csLeftClick(self, position):
		"""
		Cross Section Left Clicked - signal sent when canvas is left clicked

		:param position: dict -> event signal position
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# get position
		x = position['x']
		y = position['y']
		point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
		
		rubberBand = self.rubberBands[-1]
		
		# add clicked position to locked in points (i.e. line vertices)
		self.points.append(point)
		rubberBand.addPoint(point)
		
		# add vertex marker for locked in point
		marker = QgsVertexMarker(self.canvas)
		marker.setColor(Qt.red)
		marker.setIconSize(10)
		marker.setIconType(QgsVertexMarker.ICON_BOX)
		marker.setCenter(QgsPointXY(point))
		self.linePoints.append(marker)
		
		return True
	
	def csRightClick(self, position):
		"""
		Cross Section Right Click - signal sent when canvas is right clicked

		:param position: dict -> event signal position
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		rubberBand = self.rubberBands[-1]
		
		# draw line up to last locked in point and disconnect
		rubberBand.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.points]), None)
		self.mouseTrackDisconnect()
		
		# unpress time series button
		self.tuPlot.tuPlotToolbar.plotLPMenu.menuAction().setChecked(False)
		
		# create memory polyline layer
		self.createMemoryLayer(False)
		
		return True
	
	def csDoubleClick(self, event):
		"""
		Cross Section Double Click - signal sent when canvas is double clicked. Finish line - same as right click.

		:param position: dict -> event signal position
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		rubberBand = self.rubberBands[-1]
		
		# remove last entry because double click will record a single click location
		self.points.pop()
		self.canvas.scene().removeItem(self.linePoints[-1])
		
		# draw line up to last locked in point and disconnect
		rubberBand.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.points]), None)
		self.mouseTrackDisconnect()
		
		# unpress time series button
		self.tuPlot.tuPlotToolbar.plotLPMenu.menuAction().setChecked(False)
		
		# create memory polyline layer
		self.createMemoryLayer(False)
		
		return  True
	
	def csEscape(self, key):
		"""
		Cross Section Escape - signal sent when a key is pressed in qgis. Will cancel the line if escape is pressed

		:param key: dict -> key press event
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		rubberBand = self.rubberBands[-1]
		
		# if key is escape draw line up to last locked in point and disconnect
		if key.key() == 16777216:  # Escape key
			self.canvas.scene().removeItem(rubberBand)  # Remove previous temp layer
			self.mouseTrackDisconnect()
			
			# unpress time series button
			self.tuPlot.tuPlotToolbar.plotLPMenu.menuAction().setChecked(False)
			
		return True
	
	def createMemoryLayer(self, tracking, **kwargs):
		"""
		Creates a polyline feature from the rubberband so that it can then be used to extract values

		:param tracking: bool - True means cursor tracking, False means use final finished line
		:param *args: list - list of points
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuPlot.tuPlot2D.multiLineSelectCount = len(self.rubberBands)  # force counting to match number of rubberbands
		if self.rubberBands:  # force counting if there are rubberbands
			self.tuPlot.clearedLongPlot = False

		# deal with kwargs
		points = kwargs['points'] if 'points' in kwargs.keys() else []
		
		# create feature layer
		feat = QgsFeature()
		if tracking:
			if points:
				feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in points]))
		else:
			feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.points]))
		
		# plot
		if self.tuPlot.holdLongProfilePlot:
			if self.tuPlot.clearedLongPlot and self.tuView.tuOptions.liveMapTracking:  # long plot just cleared, don't bypass which will countup the numbering (only if live tracking).
				self.tuPlot.tuPlot2D.plotCrossSectionFromMap(None, feat)
				self.tuPlot.clearedLongPlot = False
			else:
				self.tuPlot.tuPlot2D.plotCrossSectionFromMap(None, feat, bypass=True)
			self.tuPlot.holdLongProfilePlot = False
		else:
			self.tuPlot.tuPlot2D.plotCrossSectionFromMap(None, feat)
			self.tuPlot.clearedLongPlot = False
			
		return True
	
	def clearRubberBand(self):
		"""
		Clear rubber band line layers and any vertex markers

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		for rubberBand in self.rubberBands:
			self.canvas.scene().removeItem(rubberBand)
		self.rubberBands = []
		
		for linePoint in self.linePoints:
			self.canvas.scene().removeItem(linePoint)
		self.linePoints = []
		self.points = []
		
		return True
	
	def clearMarkers(self):
		"""
		Clear markers on canvas

		:return: bool -> True for successful, False for unsuccessful
		"""

		for marker in self.markers:
			self.canvas.scene().removeItem(marker)
		self.markerPoints = []
		self.markers = []
		self.canvas.scene().removeItem(self.marker)
		
		return True