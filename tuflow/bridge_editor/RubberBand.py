from qgis.core import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from ..canvas_event import *

from ..compatibility_routines import QT_CURSOR_CROSS, QT_RED, QT_KEY_ESCAPE


class RubberBand(QObject):
    """Class for handling the
    graphic 'rubberband' layer.
    
    Inherits from QObject so it can use signals."""
    
    finishedDrawing = pyqtSignal()
    
    def __init__(self, canvas=None, layer=None):
        QObject.__init__(self)
        self.canvas = canvas
        self.layer = layer
        
        # set up graphic layers
        self.linePoints = []
        self.lineMarkers = []
        self.rubberBand = QgsRubberBand(self.canvas)
        self.rubberBand.setWidth(2)
        self.rubberBand.setColor(QColor(QT_RED))
        self.rubberBand.setToGeometry(QgsGeometry.fromPolyline(self.linePoints), None)

        # setup maptool and set
        self.canvasEvent = canvasEvent(self.canvas)
        self.canvas.setMapTool(self.canvasEvent)
        self.cursorTrackingConnected = False
        self.mouseTrackConnect()

    def mouseMoved(self, e):
        """
        Mouse moved event
        
        :param e: dict { 'x': float pos, 'y': float pos }
        :return: void
        """

        # get position
        x = e['x']
        y = e['y']
        point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)

        # reset line and draw new line based on cursor position
        if self.linePoints:
            # reset line
            self.rubberBand.reset(QgsWkbTypes.LineGeometry)
            
            # draw up to locked in points
            self.rubberBand.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.linePoints]), None)
            
            # add cursor position
            self.rubberBand.addPoint(point)
        
    def mouseLeftClicked(self, e):
        """
        Mouse left clicked - add vertex to polyline
        
        :param e: dict { 'x': float pos, 'y': float pos }
        :return: void
        """

        # get position
        x = e['x']
        y = e['y']
        point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)

        # add clicked position to locked in points
        self.linePoints.append(point)
        self.rubberBand.addPoint(point)

        # add vertex marker for locked in point
        marker = QgsVertexMarker(self.canvas)
        marker.setColor(QT_RED)
        marker.setIconSize(10)
        marker.setIconType(QgsVertexMarker.ICON_BOX)
        marker.setCenter(QgsPointXY(point))
        self.lineMarkers.append(marker)
    
    def mouseRightClicked(self, e):
        """
        Mouse right clicked - finish line
        
        :param e: dict { 'x': float pos, 'y': float pos }
        :return: void
        """

        # draw line up to last locked in point and disconnect
        if len(self.linePoints) >= 2:
            self.rubberBand.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.linePoints]), None)
        else:
            self.deleteLine()
        self.mouseTrackDisconnect()
        
        # emit finished signal
        self.finishedDrawing.emit()
    
    def mouseDoubleClicked(self, e):
        """
        Mouse double clicked - finish line
        
        :param e: dict { 'x': float pos, 'y': float pos }
        :return: void
        """

        # draw line up to last locked in point and disconnect
        self.rubberBand.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in self.linePoints]), None)
        self.mouseTrackDisconnect()

        # emit finished signal
        self.finishedDrawing.emit()
    
    def keyPressed(self, e):
        """
        
        
        :param e: dict { 'key': QKeyEvent }
        :return: void
        """
        
        if e.key() == QT_KEY_ESCAPE:
            self.deleteLine()
            self.mouseTrackDisconnect()
            self.finishedDrawing.emit()

    def deleteLine(self):
        """
        Delete rubberband line
        """

        self.canvas.scene().removeItem(self.rubberBand)  # Remove previous temp layer
        for marker in self.lineMarkers:
            self.canvas.scene().removeItem(marker)
    
    def mouseTrackConnect(self):
        """
        Captures signals from the custom map tool

        :return: void
        """
    
        if not self.cursorTrackingConnected:
            QApplication.setOverrideCursor(QT_CURSOR_CROSS)
            
            self.canvasEvent.moved.connect(self.mouseMoved)
            self.canvasEvent.rightClicked.connect(self.mouseRightClicked)
            self.canvasEvent.leftClicked.connect(self.mouseLeftClicked)
            self.canvasEvent.doubleClicked.connect(self.mouseDoubleClicked)
            self.canvas.keyPressed.connect(self.keyPressed)

            self.cursorTrackingConnected = True

    def mouseTrackDisconnect(self):
        """
        Disconnects signals from the custom map tool

        :return: void
        """
    
        if self.cursorTrackingConnected:
            QApplication.restoreOverrideCursor()
        
            self.canvasEvent.moved.disconnect(self.mouseMoved)
            self.canvasEvent.rightClicked.disconnect(self.mouseRightClicked)
            self.canvasEvent.leftClicked.disconnect(self.mouseLeftClicked)
            self.canvasEvent.doubleClicked.disconnect(self.mouseDoubleClicked)
            self.canvas.keyPressed.disconnect(self.keyPressed)
        
            self.cursorTrackingConnected = False
        
    