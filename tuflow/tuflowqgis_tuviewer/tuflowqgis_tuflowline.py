import sys
import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets import *
from tuflow.canvas_event import *
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turubberband import TuRubberBand


class TuFlowLine(TuRubberBand):


	def startRubberBand(self):
		# check for velocity and one of depth or water level - to see if it is possible to get flow
		if not self.checkIsPossible():
			QMessageBox.information(self.tuView, "Flux Calculation",
			                        "Flux Calculation Requires Depth and Velocity Results.")
			return False
		else:
			TuRubberBand.startRubberBand(self)

	def checkIsPossible(self):
		"""
		Checks if flow calculation is possible i.e. need velocity and one of depth or water level.

		:return: bool -> True is possible, False not possible
		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesults import TuResults

		results = self.tuView.tuResults.results

		possible = False
		for meshLayer in self.tuView.tuResults.tuResults2D.activeMeshLayers:
			foundDepth = False
			foundWL = False
			foundVel = False
			result = results[meshLayer.name()]
			for resultType in result:
				if TuResults.isMapOutputType(resultType) and not TuResults.isMaximumResultType(resultType) \
						and not TuResults.isMinimumResultType(resultType):
				#if '_ts' not in resultType and '_lp' not in resultType and 'Maximum' not in resultType:  # not a 1D result
					if 'dep' in resultType.lower() and 'time' not in resultType.lower() and \
							'dur' not in resultType.lower():
						foundDepth = True
					elif resultType[0].lower() == 'd' and 'time' not in resultType.lower() and \
							'dur' not in resultType.lower():
						foundDepth = True
					elif 'vel' in resultType.lower() and 'time' not in resultType.lower() and \
							'dur' not in resultType.lower():
						foundVel = True
					elif resultType[0].lower() == 'v' and 'time' not in resultType.lower() and \
							'dur' not in resultType.lower():
						foundVel = True
					elif 'water level' in resultType.lower() and 'time' not in resultType.lower() and \
							'dur' not in resultType.lower():
						foundWL = True
					elif resultType[0].lower() == 'h' and 'time' not in resultType.lower() and \
							'dur' not in resultType.lower():
						foundWL = True
			if foundVel:
				if foundDepth or foundWL:
					possible = True
					break

		return possible



class TuFlowLine2():
	"""
	Class for handling rubberband flow line and calculating flow.
	
	"""
	
	def __init__(self, TuPlot):
		self.tuPlot = TuPlot
		self.tuView = TuPlot.tuView
		self.iface = TuPlot.iface
		self.canvas = TuPlot.canvas
		self.rubberBands = []  # list -> QgsRubberBand temp polyline
		self.linePoints = []  # list -> QgsVertexMarker vertex for temp polyline
		self.points = []  # list -> QgsPoint line geometry
		self.cursorTrackingConnected = False
		self.prevMapTool = None

	def checkIsPossible(self):
		"""
		Checks if flow calculation is possible i.e. need velocity and one of depth or water level.
		
		:return: bool -> True is possible, False not possible
		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesults import TuResults
		
		results = self.tuView.tuResults.results
		
		possible = False
		for meshLayer in self.tuView.tuResults.tuResults2D.activeMeshLayers:
			foundDepth = False
			foundWL = False
			foundVel = False
			result = results[meshLayer.name()]
			for resultType in result:
				if TuResults.isMapOutputType(resultType) and not TuResults.isMaximumResultType(resultType) \
						and not TuResults.isMinimumResultType(resultType):  # not a 1D result
					if 'dep' in resultType.lower() and 'time' not in resultType.lower() and \
							'dur' not in resultType.lower():
						foundDepth = True
					elif resultType[0].lower() == 'd' and 'time' not in resultType.lower() and \
							'dur' not in resultType.lower():
						foundDepth = True
					elif 'vel' in resultType.lower() and 'time' not in resultType.lower() and \
							'dur' not in resultType.lower():
						foundVel = True
					elif resultType[0].lower() == 'v' and 'time' not in resultType.lower() and \
					     'dur' not in resultType.lower():
						foundVel = True
					elif 'water level' in resultType.lower() and 'time' not in resultType.lower() and \
							'dur' not in resultType.lower():
						foundWL = True
					elif resultType[0].lower() == 'h' and 'time' not in resultType.lower() and \
							'dur' not in resultType.lower():
						foundWL = True
			if foundVel:
				if foundDepth or foundWL:
					possible = True
					break
					
		return possible
	
	def startRubberBand(self):
		"""
		Creates a graphic polyline that can be drawn on the map canvas

		:return: bool -> True for successful, False for unsuccessful
		"""

		# check for velocity and one of depth or water level - to see if it is possible to get flow
		if not self.checkIsPossible():
			QMessageBox.information(self.tuView, "Flux Calculation", "Flux Calculation Requires Depth and Velocity Results.")
			return False
		
		# determine if multi select
		multi = False
		if self.tuView.cboSelectType.currentText() == 'From Map Multi':
			multi = True
			
		# only start if not already clicked
		if not self.cursorTrackingConnected:
			
			if not multi:  # simple, can remove previous flow lines and start again
				self.tuPlot.clearPlot(0, retain_1d=True, retain_2d=True)  # clear plot of flow results only
				for rubberBand in self.rubberBands:
					self.canvas.scene().removeItem(rubberBand)  # Remove previous temp layers
				self.rubberBands = []
				self.tuPlot.timeSeriesPlotFirst = False
			else:
				# multi select so only clear plot if plotting for the first time
				if self.tuPlot.timeSeriesPlotFirst:  # first plot so need to remove test line
					self.tuPlot.clearPlot(0)
					self.tuPlot.timeSeriesPlotFirst = False
				
			# remove line vertex points regardless
			for linePoint in self.linePoints:
				self.canvas.scene().removeItem(linePoint)  # Remove previous temp layer
			self.linePoints = []
			
			# initialise rubberband
			rubberBand = QgsRubberBand(self.canvas, False)  # setup rubberband class for drawing
			rubberBand.setWidth(2)
			rubberBand.setColor(QtGui.QColor(Qt.blue))
			self.points = []  # list of x, y coords of line
			rubberBand.setToGeometry(QgsGeometry.fromPolyline(self.points), None)
			self.rubberBands.append(rubberBand)
			
			# setup maptool and set
			self.line = canvasEvent(self.iface, self.canvas)
			self.prevMapTool = self.canvas.mapTool()
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

			self.line.moved.connect(self.moved)
			self.line.rightClicked.connect(self.rightClick)
			self.line.leftClicked.connect(self.leftClick)
			self.line.doubleClicked.connect(self.doubleClick)
			self.canvas.keyPressed.connect(self.escape)
		
		return True
	
	def mouseTrackDisconnect(self):
		"""
		Disconnects signals from the custom map tool

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if self.cursorTrackingConnected:
			self.cursorTrackingConnected = False
			for i in range(self.cursorPrev):
				QApplication.restoreOverrideCursor()  # have to call for everytime it is overwritten to get back to default
			if self.prevMapTool is not None:
				self.canvas.setMapTool(self.prevMapTool)
			
			self.line.moved.disconnect()
			self.line.rightClicked.disconnect()
			self.line.leftClicked.disconnect()
			self.line.doubleClicked.disconnect()
			self.canvas.keyPressed.disconnect()
		
		return True
	
	def moved(self, position):
		"""
		Flow Line Moved - signal sent when cursor is moved on the map canvas

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
			try:
				rubberBand.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.points]), None)
			except:
				rubberBand.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(x.x(), x.y()) for x in self.points]), None)
			# add cursor position
			rubberBand.addPoint(point)
			
		return True
	
	def leftClick(self, position):
		"""
		Flow Line Left Clicked - signal sent when canvas is left clicked

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
		marker.setColor(Qt.blue)
		marker.setIconSize(12)
		marker.setIconType(QgsVertexMarker.ICON_DOUBLE_TRIANGLE)
		marker.setCenter(QgsPointXY(point))
		self.linePoints.append(marker)
		
		return True
	
	def rightClick(self, position):
		"""
		Flow Line Right Click - signal sent when canvas is right clicked

		:param position: dict -> event signal position
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		rubberBand = self.rubberBands[-1]
		
		# draw line up to last locked in point and disconnect
		try:
			rubberBand.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.points]), None)
		except:
			rubberBand.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(x.x(), x.y()) for x in self.points]), None)
		self.mouseTrackDisconnect()
		
		# unpress button
		self.tuPlot.tuPlotToolbar.plotFluxButton.setChecked(False)
		
		if not rubberBand.asGeometry().isNull():
			# create memory polyline layer
			self.createMemoryLayer()
		else:
			self.rubberBands.pop()
		
		return True
	
	def doubleClick(self, event):
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
		try:
			rubberBand.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.points]), None)
		except:
			rubberBand.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(x.x(), x.y()) for x in self.points]), None)
		self.mouseTrackDisconnect()
		
		# unpress button
		self.tuPlot.tuPlotToolbar.plotFluxButton.setChecked(False)
		
		if not rubberBand.asGeometry().isNull():
			# create memory polyline layer
			self.createMemoryLayer()
		else:
			self.rubberBands.pop()
		
		return True
	
	def escape(self, key):
		"""
		Flow Line Escape - signal sent when a key is pressed in qgis. Will cancel the line if escape is pressed

		:param key: dict -> key press event
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		rubberBand = self.rubberBands[-1]
		
		# if key is escape draw line up to last locked in point and disconnect
		if key.key() == 16777216:  # Escape key
			self.canvas.scene().removeItem(rubberBand)  # Remove previous temp layer
			self.mouseTrackDisconnect()
			
			# unpress button
			self.tuPlot.tuPlotToolbar.plotFluxButton.setChecked(False)
		
		return True
	
	def createMemoryLayer(self):
		"""
		Creates a polyline feature from the rubberband so that it can then be used to extract values

		:param tracking: bool - True means cursor tracking, False means use final finished line
		:param *args: list - list of points
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuPlot.tuPlot2D.multiFlowLineSelectCount = len(self.rubberBands)  # force counting to match number of rubberbands
		
		# create feature layer
		feat = QgsFeature()
		try:
			feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.points]))
		except:
			feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x.x(), x.y()) for x in self.points]))
		worked = self.tuPlot.tuPlot2D.plotFlowFromMap(None, feat)
		if not worked:
			self.escape(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
			self.clearGraphics()
			return False
		
		return True
	
	def clearGraphics(self):
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
	