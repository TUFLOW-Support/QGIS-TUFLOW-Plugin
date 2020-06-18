from datetime import datetime
from PyQt5.QtCore import *


class TuOptions():
	
	def __init__(self):
		settings = QSettings()
		self.defaultZeroTime = datetime(1999, 12, 31, 14, 0, 0)
		self.liveMapTracking = False
		self.meanEventSelection = 'next higher'
		self.playDelay = 1.0
		self.resolution = 1.0
		self.iLabelField = 0
		self.showGrid = False
		self.showTriangles = False
		self.xAxisDates = False
		self.xAxisLabelRotation = 0
		self.timeUnits = 'h'
		self.writeMeshIntersects = False
		self.particlesWriteDebugInfo = False
		self.verticalProfileInterpolated = False
		if settings.contains("TUFLOW/tuview_defaultlayout"):
			self.defaultLayout = settings.value('TUFLOW/tuview_defaultlayout')
		else:
			self.defaultLayout = 'plot'
		zeroTime = settings.value('TUFLOW/tuview_zeroTime')
		if zeroTime:
			self.zeroTime = zeroTime
		else:
			# self.zeroTime = datetime(1990, 1, 1, 0, 0, 0)
			self.zeroTime = self.defaultZeroTime
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
	
	def saveProject(self, project):
		project.writeEntry("TUVIEW", "livemaptracking", str(self.liveMapTracking))
		
		project.writeEntry("TUVIEW", "meaneventselection", self.meanEventSelection)
		
		project.writeEntry("TUVIEW", "playdelay", str(self.playDelay))
		
		project.writeEntry("TUVIEW", "resolution", str(self.resolution))

		project.writeEntry("TUVIEW", "ilabelfield", str(self.iLabelField))
		
		project.writeEntry("TUVIEW", "showgrid", str(self.showGrid))
		
		project.writeEntry("TUVIEW", "showtriangles", str(self.showTriangles))
		
		project.writeEntry("TUVIEW", "xaxisdates", str(self.xAxisDates))
		
		project.writeEntry("TUVIEW", "xaxislabelrotation", str(self.xAxisLabelRotation))
		
		zeroTime = '{0}~~{1}~~{2}~~{3}~~{4}~~{5}'.format(self.zeroTime.year, self.zeroTime.month, self.zeroTime.day,
		                                                 self.zeroTime.hour, self.zeroTime.minute, self.zeroTime.second)
		project.writeEntry("TUVIEW", "zerotime", zeroTime)
		
		project.writeEntry("TUVIEW", "dateformat", self.dateFormat)
		
		project.writeEntry("TUVIEW", "_dateformat", self._dateFormat)
	
	def readProject(self, project):
		try:
			liveMapTracking = project.readEntry("TUVIEW", "livemaptracking")[0]
			self.liveMapTracking = True if liveMapTracking == 'True' else False
		except:
			pass

		try:
			self.meanEventSelection = project.readEntry("TUVIEW", "meaneventselection")[0]
		except:
			pass

		try:
			self.playDelay = float(project.readEntry("TUVIEW", "playdelay")[0])
		except:
			pass

		try:
			self.resolution = float(project.readEntry("TUVIEW", "resolution")[0])
		except:
			pass

		try:
			self.iLabelField = int(project.readEntry("TUVIEW", "ilabelfield")[0])
		except:
			pass

		try:
			showGrid = project.readEntry("TUVIEW", "showgrid")[0]
			self.showGrid = True if showGrid == 'True' else False
		except:
			pass

		try:
			showTriangles = project.readEntry("TUVIEW", "showtriangles")[0]
			self.showTriangles = True if showTriangles == 'True' else False
		except:
			pass

		try:
			xAxisDates = project.readEntry("TUVIEW", "xaxisdates")[0]
			self.xAxisDates = True if xAxisDates == 'True' else False
		except:
			pass

		try:
			self.xAxisLabelRotation = float(project.readEntry("TUVIEW", "xaxislabelrotation")[0])
		except:
			pass

		try:
			zeroTime = project.readEntry("TUVIEW", "zerotime")[0]
			zeroTime = zeroTime.split('~~')
			self.zeroTime = datetime(int(zeroTime[0]), int(zeroTime[1]), int(zeroTime[2]),
			                         int(zeroTime[3]), int(zeroTime[4]), int(zeroTime[5]))
		except:
			pass

		try:
			self.dateFormat = project.readEntry("TUVIEW", "dateformat")[0]
		except:
			pass

		try:
			self._dateFormat = project.readEntry("TUVIEW", "_dateformat")[0]
		except:
			pass