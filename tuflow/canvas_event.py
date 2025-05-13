from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.core import *
from qgis.gui import *


from .compatibility_routines import QT_LEFT_BUTTON, QT_RIGHT_BUTTON


class canvasEvent(QgsMapTool):
	
	moved = pyqtSignal(dict)
	rightClicked = pyqtSignal(dict)
	leftClicked = pyqtSignal(dict)
	doubleClicked = pyqtSignal(dict)
	keyPressed = pyqtSignal(dict)
	mousePressed = pyqtSignal(dict)
	desactivate = pyqtSignal()
	
	def __init__(self, canvas):
		QgsMapTool.__init__(self, canvas)
		self.canvas = canvas

	def canvasPressEvent(self, e):
		self.mousePressed.emit({'x': e.pos().x(), 'y': e.pos().y(), 'button': e.button()})
	
	def canvasMoveEvent(self, event):
		self.moved.emit({'x': event.pos().x(), 'y': event.pos().y()})
	
	def canvasReleaseEvent(self, event):
		# Get the click
		if event.button() == QT_RIGHT_BUTTON:
			self.rightClicked.emit({'x': event.pos().x(), 'y': event.pos().y()})
		elif event.button() == QT_LEFT_BUTTON:
			self.leftClicked.emit({'x': event.pos().x(), 'y': event.pos().y()})
			
	def canvasDoubleClickEvent(self, event):
		self.doubleClicked.emit({'x': event.pos().x(), 'y': event.pos().y()})
			
	def keyReleaseEvent(self, event):
		self.keyPressed.emit({'key': event.key()})
	
	def activate(self):
		pass
	
	def deactivate(self):
		pass
	
	def isZoomTool(self):
		return False
	
	def isTransient(self):
		return False
	
	def isEditTool(self):
		return True
