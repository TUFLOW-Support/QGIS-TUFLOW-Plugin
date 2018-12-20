from datetime import datetime
from PyQt5.QtCore import *


class TuOptions():
	
	def __init__(self):
		settings = QSettings()
		self.liveMapTracking = True
		self.meanEventSelection = 'next higher'
		self.playDelay = 1.0
		self.resolution = 1.0
		self.showGrid = False
		self.showTriangles = False
		self.xAxisDates = False
		self.xAxisLabelRotation = 0
		zeroTime = settings.value('TUFLOW/tuview_zeroTime')
		if zeroTime:
			self.zeroTime = zeroTime
		else:
			self.zeroTime = datetime(2000, 1, 1, 12, 0, 0)
		dateFormat = settings.value('TUFLOW/tuview_dateFormat')
		if dateFormat:
			self.dateFormat = dateFormat
		else:
			self.dateFormat = '%H:%M'
		_dateFormat = settings.value('TUFLOW/tuview__dateFormat')
		if _dateFormat:
			self._dateFormat = _dateFormat
		else:
			self._dateFormat = '{0:%H}:{0:%M}'