from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from PyQt5.QtWidgets import *


class TimeSlider(QSlider):
	
	def __init__(self, parent=None):
		QSlider.__init__(self, parent)
		#self.setOrientation(Horizontal)
		
	def mousePressEvent(self, e):
		
		option = QStyleOptionSlider()
		self.initStyleOption(option)
		sr = self.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle)
		
		if e.button() == Qt.LeftButton:
			if not sr.contains(e.pos()):
				value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), e.x(), self.width())
				self.setValue(value)
				self.valueChanged.emit(value)
			else:
				QSlider.mousePressEvent(self, e)
		else:
			QSlider.mousePressEvent(self, e)