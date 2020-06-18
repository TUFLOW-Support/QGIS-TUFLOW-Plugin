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
    Abstract class for rubberband - allows user to draw graphic line on screen.
    Can be subclassed e.g. for cross section or flowline

    Subclass required override methods:
        clearPlot()
        plotFromRubberBand()
        unpressButton()

    Subclass can set properties after initialisation such as:
        self.colour
        self.symbol
        self.allowLiveTracking
    """

	def __init__(self, TuPlot, plotNo, dataType, button, plotFunction,
	             colour=Qt.red, symbol=QgsVertexMarker.ICON_BOX, bAllowLiveTracking=False):
		self.tuPlot = TuPlot
		self.tuView = TuPlot.tuView
		self.iface = TuPlot.iface
		self.canvas = TuPlot.canvas
		self.rubberBands = []  # list -> QgsRubberBand temp polyline
		self.linePoints = []  # list -> QgsVertexMarker vertex for temp polyline
		self.points = []  # list -> QgsPoint line geometry
		self.cursorTrackingConnected = False
		self.prevMapTool = None
		self.colour = colour
		self.symbol = symbol
		self.plotNo = plotNo
		self.dataType = dataType
		self.plotFunction = plotFunction
		self.firstTimePlotting = ["timeSeriesPlotFirst", "profilePlotFirst", "crossSectionFirst", "verticalProfileFirst"]
		self.holdPlot = ["holdTimeSeriesPlot", "holdLongProfilePlot", "holdCrossSectionPlot", "holdVerticalProfilePlot"]
		self.clearedPlot = ["clearedTimeSeriesPlot", "clearedLongPlot", "clearedVerticalProfilePlot","clearedVerticalProfilePlot"]
		self.allowLiveTracking = bAllowLiveTracking

		if isinstance(button, QMenu):
			self.button = button.menuAction()
		else:
			self.button = button

	def startRubberBand(self):
		"""
        Creates a graphic polyline that can be drawn on the map canvas

        :return: bool -> True for successful, False for unsuccessful
        """

		# determine if multi select
		multi = False
		if self.tuView.cboSelectType.currentText() == 'From Map Multi':
			multi = True

		# only start if not already clicked
		if not self.cursorTrackingConnected:

			if not multi:  # simple, can remove previous flow lines and start again
				self.clearPlot(False)
				for rubberBand in self.rubberBands:
					self.canvas.scene().removeItem(rubberBand)  # Remove previous temp layers
				self.rubberBands = []
				exec("self.tuPlot.{0} = False".format(self.firstTimePlotting[self.plotNo]))
			else:
				# multi select so only clear plot if plotting for the first time
				if eval("self.tuPlot.{0}".format(self.firstTimePlotting[self.plotNo])):  # first plot so need to remove test line
					self.clearPlot(True)
					exec("self.tuPlot.{0} = False".format(self.firstTimePlotting[self.plotNo]))
				else:
					exec("self.tuPlot.{0} = True".format(self.holdPlot[self.plotNo]))

			# remove line vertex points regardless
			for linePoint in self.linePoints:
				self.canvas.scene().removeItem(linePoint)  # Remove previous temp layer
			self.linePoints = []

			# initialise rubberband
			rubberBand = QgsRubberBand(self.canvas, False)  # setup rubberband class for drawing
			rubberBand.setWidth(2)
			rubberBand.setColor(self.colour)
			self.points = []  # list of x, y coords of line
			rubberBand.setToGeometry(QgsGeometry.fromPolyline(self.points), None)
			self.rubberBands.append(rubberBand)

			# setup maptool and set
			self.line = canvasEvent(self.iface, self.canvas)
			self.prevMapTool = self.canvas.mapTool()
			self.canvas.setMapTool(self.line)
			self.mouseTrackConnect()  # start the tuflowqgis_bridge_rubberband

		return True

	def clearPlot(self, firstTimePlotting: bool) -> None:
		"""
		Requires subclassing.
		Which plot to clear and what settings.

		:param firstTimePlotting: True if first time plot is being used
		"""

		self.tuPlot.clearPlot2(self.plotNo, self.dataType)

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
			self.line.doubleClicked.connect(self.rightClick)
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

			# create memory polyline layer
			if self.tuView.tuOptions.liveMapTracking and self.allowLiveTracking:
				if not rubberBand.asGeometry().isNull():
					points = self.points[:] + [point]
					self.createMemoryLayer(points=points)

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
		marker.setColor(self.colour)
		marker.setIconSize(12)
		marker.setIconType(self.symbol)
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
		self.unpressButton()

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
		if key.key() == Qt.Key_Escape:  # Escape key
			self.canvas.scene().removeItem(rubberBand)  # Remove previous temp layer
			self.mouseTrackDisconnect()

			# unpress button
			self.unpressButton()

		return True

	def createMemoryLayer(self, **kwargs):
		"""
        Creates a polyline feature from the rubberband so that it can then be used to extract values

        :param tracking: bool - True means cursor tracking, False means use final finished line
        :param *args: list - list of points
        :return: bool -> True for successful, False for unsuccessful
        """

		self.tuPlot.tuPlot2D.multiFlowLineSelectCount = len(
			self.rubberBands)  # force counting to match number of rubberbands
		if self.rubberBands:  # force counting if there are rubberbands
			exec("self.tuPlot.{0} = False".format(self.clearedPlot[self.plotNo]))

		points = kwargs['points'] if 'points' in kwargs else self.points[:]
		if points is None:
			return

		# create feature layer
		feat = QgsFeature()
		try:
			feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in points]))
		except:
			feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x.x(), x.y()) for x in points]))

		if eval("self.tuPlot.{0}".format(self.holdPlot[self.plotNo])):
			if eval("self.tuPlot.{0}".format(self.clearedPlot[self.plotNo])) and \
					eval("self.tuPlot.{0}".format(self.tuView.tuOptions.liveMapTracking)) and self.allowLiveTracking:
				worked = self.plotFromRubberBand(feat)
				if not worked:
					self.escape(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
					self.clearRubberBand()
					return False
				exec("self.tuPlot.{0} = False".format(self.clearedPlot[self.plotNo]))
			else:
				worked = self.plotFromRubberBand(feat, bypass=True)
				if not worked:
					self.escape(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
					self.clearGraphics()
					return False
			exec("self.tuPlot.{0} = False".format(self.holdPlot[self.plotNo]))
		else:
			worked = self.plotFromRubberBand(feat)
			if not worked:
				self.escape(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
				self.clearGraphics()
				return False
			exec("self.tuPlot.{0} = False".format(self.clearedPlot[self.plotNo]))

		return True

	def plotFromRubberBand(self, feat: QgsFeature, bypass: bool = False) -> bool:
		"""
        Requires subclassing.
        Tell tuflow viewer what to plot with rubberband.

        :param feat: feature to plot
        :param bypass: True will bypass clearing plot before drawing
        :return: True if successful
        """

		return self.plotFunction(None, feat, bypass=bypass, lineNo=len(self.rubberBands), data_type=self.dataType)

	def unpressButton(self) -> None:
		"""
		Requires subclassing

		Which button to unpress when finished plotting.
		"""

		self.button.setChecked(False)

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


class TuMarker():

	def __init__(self, tuPlot, plotNo, dataType, button, plotFunction,
	             colour=Qt.red, symbol=QgsVertexMarker.ICON_BOX, bAllowLiveTracking=False):
		self.tuPlot = tuPlot
		self.tuView = tuPlot.tuView
		self.iface = tuPlot.iface
		self.canvas = tuPlot.canvas
		self.point = None  # single point for time series
		self.points = []  # list of x, y coords of line
		self.marker = QgsVertexMarker(self.canvas)
		self.markers = []  # list -> QgsMarkers
		self.cursorTrackingConnected = False
		self.prevMapTool = None
		self.colour = colour
		self.symbol = symbol
		self.plotNo = plotNo
		self.dataType = dataType
		self.plotFunction = plotFunction
		self.firstTimePlotting = ["timeSeriesPlotFirst", "profilePlotFirst", "crossSectionFirst",
		                          "verticalProfileFirst"]
		self.holdPlot = ["holdTimeSeriesPlot", "holdLongProfilePlot", "holdCrossSectionPlot", "holdVerticalProfilePlot"]
		self.clearedPlot = ["clearedTimeSeriesPlot", "clearedLongPlot", "clearedVerticalProfilePlot",
		                    "clearedVerticalProfilePlot"]
		self.allowLiveTracking = bAllowLiveTracking

		if isinstance(button, QMenu):
			self.button = button.menuAction()
		else:
			self.button = button

	def startRubberBand(self):
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

			# remove previous temporary point layer
			if not multi:

				# single selection
				# self.tuPlot.plotSelectionPointFeat.clear()  # clear features from selected plot list
				# self.tuPlot.clearPlot(0, retain_1d=True, retain_flow=True)
				self.clearPlot(True, False)
				self.points.clear()
				for marker in self.markers:
					self.canvas.scene().removeItem(marker)  # Remove previous temp
				self.markers.clear()  # list of QgsVertexMarker
				self.canvas.scene().removeItem(self.marker)  # Remove previous temp layer
				exec("self.tuPlot.{0} = False".format(self.firstTimePlotting[self.plotNo]))
				exec("self.tuPlot.{0} = False".format(self.holdPlot[self.plotNo]))

			else:  # do not clear existing plot

				# multi select so only clear plot if plotting for the first time
				if eval("self.tuPlot.{0}".format(self.firstTimePlotting[self.plotNo])):
					# self.tuPlot.clearPlot(0, retain_1d=True, retain_flow=True)
					self.clearPlot(True, False)
					exec("self.tuPlot.{0} = False".format(self.firstTimePlotting[self.plotNo]))
				else:
					if self.markers:
						exec("self.tuPlot.{0} = True".format(self.holdPlot[self.plotNo]))

			# initialise markers
			self.marker = QgsVertexMarker(self.canvas)
			self.marker.setColor(self.colour)
			self.marker.setIconSize(10)
			self.marker.setIconType(QgsVertexMarker.ICON_CROSS)

			# setup maptool and set
			self.point = canvasEvent(self.iface, self.canvas)
			self.prevMapTool = self.canvas.mapTool()
			self.canvas.setMapTool(self.point)
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

			self.point.moved.connect(self.moved)
			self.point.rightClicked.connect(self.rightClick)
			self.point.leftClicked.connect(self.leftClick)
			self.point.doubleClicked.connect(self.doubleClick)
			self.point.keyPressed.connect(self.escape)

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
			if self.prevMapTool is not None:
				self.canvas.setMapTool(self.prevMapTool)

			self.point.moved.disconnect()
			self.point.rightClicked.disconnect()
			self.point.leftClicked.disconnect()
			self.point.doubleClicked.disconnect()
			self.point.keyPressed.disconnect()
			self.canvas.scene().removeItem(self.marker)

		return True

	def clearPlot(self, firstTimePlotting: bool, lastOnly: bool) -> None:
		"""
		Requires subclassing.
		Which plot to clear and what settings.

		:param firstTimePlotting: True if first time plot is being used
		:param lastOnly: True if remove last plotted dataset only
		"""

		resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(self.dataType)
		activeMeshLayers = self.tuView.tuResults.tuResults2D.activeMeshLayers

		self.tuPlot.clearPlot2(self.plotNo, self.dataType, last_only=lastOnly,
		                       remove_no=len(resultTypes) * len(activeMeshLayers))

	def moved(self, position):
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

		if eval("self.tuPlot.{0}".format(self.holdPlot[self.plotNo])):
			if self.tuView.tuOptions.liveMapTracking and self.allowLiveTracking:
				worked = self.plotFromMarker(QgsPointXY(point), bypass=True)
				if not worked:
					self.escape({'key': Qt.Key_Escape})
					return False
			exec("self.tuPlot.{0} = False".format(self.holdPlot[self.plotNo]))  # turn off after first signal
		else:
			if self.tuView.tuOptions.liveMapTracking and self.allowLiveTracking:
				worked = self.plotFromMarker(QgsPointXY(point))
				if not worked:
					self.escape({'key': Qt.Key_Escape})
					return False

		return True

	def leftClick(self, position):
		"""
		Time Series Left Clicked - Signal sent when canvas is left clicked

		:param position: dict -> event signal position
		:return: bool -> True for successful, False for unsuccessful
		"""

		# get location
		x = position['x']
		y = position['y']
		point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
		self.points.append(point)

		# set up new marker and add to list so that if multi select is on, multi markers are also displayed
		marker = QgsVertexMarker(self.canvas)
		marker.setColor(self.colour)
		marker.setFillColor(self.colour)
		marker.setIconSize(10)
		marker.setIconType(self.symbol)
		marker.setCenter(QgsPointXY(point))
		self.markers.append(marker)

		# plot and worry about disconnecting canvas tracking
		if self.tuView.cboSelectType.currentText() == 'From Map Multi':
			# plot point and do not disconnect because multi location is on, bypass on so plotting is frozen for location
			worked = self.plotFromMarker(QgsPointXY(point), bypass=True)
			if not worked:
				self.escape({'key': Qt.Key_Escape})
				return False
		else:
			# plot and disconnect because only single location needed
			self.mouseTrackDisconnect()
			self.canvas.scene().removeItem(self.marker)
			worked = self.plotFromMarker(QgsPointXY(point))
			if not worked:
				self.escape({'key': Qt.Key_Escape})
				return False

			# unpress time series button
			# self.tuPlot.tuPlotToolbar.plotTimeSeriesButton.setChecked(False)
			# self.tuPlot.tuPlotToolbar.plotTSMenu.menuAction().setChecked(False)
			self.unpressButton()

		return True

	def rightClick(self, position):
		"""
		Time Series Right Clicked - signal sent when canvas is right clicked. For time series will end.

		:param position: dict -> event signal position
		:return: bool -> True for successful, False for unsuccessful

		"""

		# clear last plot location so that cursor tracking plot is not kept
		if self.tuView.tuOptions.liveMapTracking and self.allowLiveTracking:
			# self.tuPlot.clearPlotLastDatasetOnly(self.plotNo)
			self.clearPlot(True, True)
		self.canvas.scene().removeItem(self.marker)

		# diconnect cursor tracking
		self.mouseTrackDisconnect()

		# reset multi point numbering back to one
		# self.tuPlot.tuPlot2D.reduceMultiPointCount(1)

		# unpress time series button
		#self.tuPlot.tuPlotToolbar.plotTSMenu.menuAction().setChecked(False)
		self.unpressButton()

		return True

	def doubleClick(self, position):
		"""
		Signal sent when canvas is double clicked. For time series will end.

		:param position: dict -> event signal position
		:return: bool -> True for successful, False for unsuccessful

		"""

		# clear last plot location so that cursor tracking plot is not kept
		if self.tuView.tuOptions.liveMapTracking and self.allowLiveTracking:
			# self.tuPlot.clearPlotLastDatasetOnly(self.plotNo)
			self.clearPlot(True, True)
		# self.tuPlot.clearPlotLastDatasetOnly(self.plotNo)
		self.clearPlot(True, True)
		self.canvas.scene().removeItem(self.marker)

		# diconnect cursor tracking
		self.mouseTrackDisconnect()

		# unpress time series button
		# self.tuPlot.tuPlotToolbar.plotTSMenu.menuAction().setChecked(False)
		self.unpressButton()

		# reset multi point numbering back to one
		# self.tuPlot.tuPlot2D.reduceMultiPointCount(2)

		return True

	def escape(self, key):
		"""
		Time Series Escape - signal sent when a key is pressed in qgis. For time series will end.

		:param key: dict -> key press event
		:return: bool -> True for successful, False for unsuccessful
		"""

		if key['key'] == Qt.Key_Escape:
			# clear last plot location so that cursor tracking plot is not kept
			if self.tuView.tuOptions.liveMapTracking and self.allowLiveTracking:
				# self.tuPlot.clearPlotLastDatasetOnly(self.plotNo)
				self.clearPlot(True, True)
			self.canvas.scene().removeItem(self.marker)

			# diconnect cursor tracking
			self.mouseTrackDisconnect()

			# unpress time series button
			self.unpressButton()

			# reset multi point numbering back to one
			# self.tuPlot.tuPlot2D.resetMultiPointCount()

		return True

	def clearGraphics(self):
		"""
		Clear markers on canvas

		:return: bool -> True for successful, False for unsuccessful
		"""

		for marker in self.markers:
			self.canvas.scene().removeItem(marker)
		self.points.clear()
		self.markers.clear()
		self.canvas.scene().removeItem(self.marker)

		return True

	def plotFromMarker(self, point: QgsPointXY, bypass: bool = False) -> bool:
		"""
		Requires subclassing.
        Tell tuflow viewer what to plot with marker.

        :param point: point to plot
        :param bypass: True will bypass clearing plot before drawing
        :return: True if successful
		"""

		return self.plotFunction(None, point, bypass=bypass, markerNo=len(self.points), data_type=self.dataType)

	def unpressButton(self) -> None:
		"""
		Requires subclassing

		Which button to unpress when finished plotting.
		"""

		self.button.setChecked(False)


class TuCrossSection(TuRubberBand):

	def __init__(self, tuView, plotNo):
		TuRubberBand.__init__(self, tuView, plotNo)
		self.colour = Qt.red
		self.symbol = QgsVertexMarker.ICON_BOX
		self.allowLiveTracking = True

	def clearPlot(self, firstTimePlotting):
		"""
        Overrides clearPlot method with specific plot clearing settings.

        :param firstTimePlotting: True if first time plot is being used
        """

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		self.tuPlot.clearPlot2(TuPlot.CrossSection, TuPlot.DataCrossSection2D)

	def plotFromRubberBand(self, feat, bypass=False):
		"""
        Overrides plotFromRubberBand method with specific plotting function.
        """

		return self.tuPlot.tuPlot2D.plotCrossSectionFromMap(None, feat, bypass=bypass, lineNo=len(self.rubberBands))

	def unpressButton(self):
		"""
		Overrides pressButton method with specific button
		"""

		self.tuPlot.tuPlotToolbar.plotLPMenu.menuAction().setChecked(False)



class TuTimeSeriesPoint(TuMarker):

	def __init__(self, tuView, plotNo):
		TuMarker.__init__(self, tuView, plotNo)
		self.colour = Qt.red
		self.symbol = QgsVertexMarker.ICON_CIRCLE
		self.allowLiveTracking = True

	def clearPlot(self, firstTimePlotting: bool, lastOnly: bool = False) -> None:
		"""

		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		if firstTimePlotting:
			# self.tuPlot.clearPlot(0, retain_1d=True, retain_flow=True)
			resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(TuPlot.DataTimeSeries2D)
			activeMeshLayers = self.tuView.tuResults.tuResults2D.activeMeshLayers
			self.tuPlot.clearPlot2(TuPlot.TimeSeries, TuPlot.DataTimeSeries2D, last_only=lastOnly,
			                       remove_no=len(resultTypes)*len(activeMeshLayers))

	def plotFromMarker(self, point: QgsPointXY, bypass: bool = False) -> bool:
		"""

		"""

		return self.tuPlot.tuPlot2D.plotTimeSeriesFromMap(None, point, bypass=bypass, markerNo=len(self.points))

	def unpressButton(self) -> None:
		"""

		"""

		self.tuPlot.tuPlotToolbar.plotTSMenu.menuAction().setChecked(False)