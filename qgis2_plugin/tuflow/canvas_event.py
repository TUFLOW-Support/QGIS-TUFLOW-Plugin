from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *

class canvasEvent(QgsMapTool):
	
	moved = pyqtSignal(dict)
	rightClicked = pyqtSignal(dict)
	leftClicked = pyqtSignal(dict)
	doubleClicked = pyqtSignal(dict)
	desactivate = pyqtSignal()
	
	def __init__(self, iface, canvas):
		QgsMapTool.__init__(self, canvas)
		self.canvas = canvas
	
	def canvasPressEvent(self, event):
		pass
	
	def canvasMoveEvent(self, event):
		self.moved.emit({'x': event.pos().x(), 'y': event.pos().y()})
	
	def canvasReleaseEvent(self, event):
		# Get the click
		if event.button() == Qt.RightButton:
			self.rightClicked.emit({'x': event.pos().x(), 'y': event.pos().y()})
		elif event.button() == Qt.LeftButton:
			self.leftClicked.emit({'x': event.pos().x(), 'y': event.pos().y()})
	
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