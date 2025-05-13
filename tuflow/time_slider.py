from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt import QtGui
from qgis.PyQt.QtWidgets import *



from .compatibility_routines import QT_LEFT_BUTTON, QT_STYLE_CC_SLIDER, QT_STYLE_SC_SLIDER_HANDLE, is_qt6


class TimeSlider(QSlider):
	
	def __init__(self, parent=None):
		QSlider.__init__(self, parent)
		#self.setOrientation(Horizontal)
		
	def mousePressEvent(self, e):
		
		option = QStyleOptionSlider()
		self.initStyleOption(option)
		sr = self.style().subControlRect(QT_STYLE_CC_SLIDER, option, QT_STYLE_SC_SLIDER_HANDLE)
		
		if e.button() == QT_LEFT_BUTTON:
			if not sr.contains(e.pos()):
				if is_qt6:
					value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), int(e.position().x()), self.width())
				else:
					value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), e.x(), self.width())
				self.setValue(value)
				self.valueChanged.emit(value)
			else:
				QSlider.mousePressEvent(self, e)
		else:
			QSlider.mousePressEvent(self, e)