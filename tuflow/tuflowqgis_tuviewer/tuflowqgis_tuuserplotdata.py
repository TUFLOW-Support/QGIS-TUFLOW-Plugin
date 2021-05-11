from datetime import datetime


class TuUserPlotDataManager():
	"""
	Class for managing user input plot data sets.
	
	"""
	
	def __init__(self):
		self.error = ''
		self.datasets = {}  # dict - { dataset name: TuUserPlotDataSet }
		self.count = 0
		
	def addDataSet(self, name, data, plotType, dates=None, referenceTime=None):
		"""
		
		:param name:
		:param data:
		:param plotType:
		:return:
		"""
		
		if name in self.datasets.keys():
			self.error = 'Dataset Name Already Exists'
			return False
		dataset = TuUserPlotDataSet(name, data, plotType, True, self.count, dates, referenceTime)
		self.count += 1
		self.datasets[name] = dataset
		if dataset.error:
			self.error = '{0}: {1}'.format(name, dataset.error)
		
	def editDataSet(self, name, newname=None, data=None, plotType=None, status=None, dates=None):
		"""
		
		:param name:
		:param newname:
		:param data:
		:param plotType:
		:return:
		"""
		
		if name in self.datasets.keys():
			dataset = self.datasets[name]
			
			if newname is not None:
				if newname != dataset.name:
					copyDataset = TuUserPlotDataSet(newname, [dataset.x, dataset.y], dataset.plotType, dataset.status, dataset.number, dataset.dates, dataset.referenceTime)
					self.datasets[newname] = copyDataset
					del self.datasets[name]
					dataset = self.datasets[newname]
					if dataset.error:
						self.error = '{0}: {1}'.format(name, dataset.error)
				
			if data is not None:
				dataset.setData(data, dates=dates)
				if dataset.error:
					self.error = '{0}: {1}'.format(name, dataset.error)
				
			if plotType is not None:
				dataset.setPlotType(plotType)
				if dataset.error:
					self.error = '{0}: {1}'.format(name, dataset.error)
					
			if status is not None:
				dataset.setStatus(status)
				if dataset.error:
					self.error = '{0}: {1}'.format(name, dataset.error)
			
	def removeDataSet(self, name):
		"""
		
		
		:param name:
		:return:
		"""
		
		if name in self.datasets.keys():
			del self.datasets[name]
			
	def saveProject(self, project):
		"""
		
		:param project: QgsProject
		:return:
		"""
		
		i = -1
		for i, dataset in enumerate([k for k, v in sorted(self.datasets.items(), key=lambda x: x[-1].number)]):
			self.datasets[dataset].saveProject(project, i)
			
		project.writeEntry("TUVIEW", "userplotdatano", str(i + 1))
	
	def loadProject(self, project):
		"""
		
		:param project: QgsProject
		:return:
		"""
		
		no  = int(project.readEntry("TUVIEW", "userplotdatano")[0])
		for i in range(no):
			dataset = TuUserPlotDataSet()
			dataset.loadProject(project, i)
			if not dataset.error:
				self.datasets[dataset.name] = dataset
				self.count += 1
		
class TuUserPlotDataSet():
	"""
	Class for handling individual user input data sets.
	
	"""
	
	def __init__(self, name=None, data=[], plotType=None, status=False, number=-1, dates=None, referenceTime=None):
		self.error = ''
		self.number = number
		self.status = status
		self.hasReferenceTime = False
		self.referenceTime = None
		self.dates = []

		if name is not None:
			self.name = '{0}'.format(name)
		else:
			self.name = name
		
		if plotType is not None:
			if plotType.lower() == 'time series plot' or plotType.lower() == 'cross section / long plot':
				self.plotType = plotType
			else:
				plotType = None
		
		
		self.x = []  # list -> float  [ x1, x2, ... ]
		self.y = []  # list -> float  [ y1, y2, ... ]
		if len(data) == 2:
			if data[0]:
				self.x = data[0]
			if data[1]:
				self.y = data[1]
		#if self.x is not None or self.y is not None:
		#	if self.x is None:
		#		self.error = 'X, Y data set lengths do not match'
		#	if self.y is None:
		#		self.error = 'X, Y data set lengths do not match'
		if self.x is not None and self.y is not None:
			if len(self.x) != len(self.y):
				self.error = 'X, Y data set lengths do not match'
		
		self.dates = None
		if not self.error:
			if type(dates) is list:
				if dates:
					if len(dates) == len(self.x):
						self.dates = dates
						self.referenceTime = referenceTime
						self.hasReferenceTime = True
					else:
						self.error = 'Date data length does not match Y data'

	def __eq__(self, other):
		eq = False
		if isinstance(other, TuUserPlotDataSet):
			if self.error != other.error:
				return eq
			if self.number != other.number:
				return eq
			if self.status != other.status:
				return eq
			if self.hasReferenceTime != other.hasReferenceTime:
				return eq
			if self.referenceTime != other.referenceTime:
				return eq
			if self.dates != other.dates:
				return eq
			if self.x != other.x:
				return eq
			if self.y != other.y:
				return eq
			eq = True

		return eq
		
	def setPlotType(self, plotType):
		"""
		
		:param plotType: str plot type 'time series' or 'long plot'
		:return:
		"""
		
		self.error = ''
		
		if plotType.lower() == 'time series plot' or plotType.lower() == 'cross section / long plot':
			self.plotType = plotType
		else:
			self.plotType = None
		
	def setName(self, name):
		"""
		
		:param name: str
		:return:
		"""
		
		self.error = ''
		
		if name is not None:
			self.name = '{0}'.format(name)
		else:
			self.name = None
			
	def setData(self, data=None, dates=None):
		"""
		
		
		:param data: list -> list axis data -> float  [ [ x1, x2, ... ], [ y1, y2, ... ] ]
		:return:
		"""
		
		self.error = ''
		
		if data is not None:
			if len(data) == 2:
				if data[0]:
					self.x = data[0]
				else:
					self.x = None
				if data[1]:
					self.y = data[1]
				else:
					self.y = None
			else:
				self.x = None
				self.y = None
			
			if self.x is not None or self.y is not None:
				if self.x is None:
					self.error = 'X, Y data set lengths do not match'
				if self.y is None:
					self.error = 'X, Y data set lengths do not match'
			elif len(self.x) != len(self.y):
				self.error = 'X, Y data set lengths do not match'
			
		if not self.error:
			if dates:
				self.dates = dates
		
	def setStatus(self, status):
		"""
		
		
		:param status:
		:return:
		"""
		
		self.error = ''
		
		if status is not None:
			self.status = status
			
	def saveProject(self, project, no):
		"""
		
		:param project: QgsProject
		:param no: int
		:return:
		"""
		
		if not self.error:
			# name
			project.writeEntry("TUVIEW", "userplotdata{0}name".format(no), self.name)
			
			# data and dates
			x = ''
			y = ''
			datesyear = ''
			datesmonth = ''
			datesday = ''
			dateshour = ''
			datesminute = ''
			datessecond = ''
			for i in range(len(self.x)):
				if i == 0:
					x += '{0}'.format(self.x[i])
					y += '{0}'.format(self.y[i])
					if self.dates:
						datesyear += '{0}'.format(self.dates[i].year)
						datesmonth += '{0}'.format(self.dates[i].month)
						datesday += '{0}'.format(self.dates[i].day)
						dateshour += '{0}'.format(self.dates[i].hour)
						datesminute += '{0}'.format(self.dates[i].minute)
						datessecond += '{0}'.format(self.dates[i].second)
				else:
					x += '~~{0}'.format(self.x[i])
					y += '~~{0}'.format(self.y[i])
					if self.dates:
						datesyear += '~~{0}'.format(self.dates[i].year)
						datesmonth += '~~{0}'.format(self.dates[i].month)
						datesday += '~~{0}'.format(self.dates[i].day)
						dateshour += '~~{0}'.format(self.dates[i].hour)
						datesminute += '~~{0}'.format(self.dates[i].minute)
						datessecond += '~~{0}'.format(self.dates[i].second)
			project.writeEntry("TUVIEW", "userplotdata{0}x".format(no), x)
			project.writeEntry("TUVIEW", "userplotdata{0}y".format(no), y)
			project.writeEntry("TUVIEW", "userplotdata{0}datesyear".format(no), datesyear)
			project.writeEntry("TUVIEW", "userplotdata{0}datesmonth".format(no), datesmonth)
			project.writeEntry("TUVIEW", "userplotdata{0}datesday".format(no), datesday)
			project.writeEntry("TUVIEW", "userplotdata{0}dateshour".format(no), dateshour)
			project.writeEntry("TUVIEW", "userplotdata{0}datesminute".format(no), datesminute)
			project.writeEntry("TUVIEW", "userplotdata{0}datessecond".format(no), datessecond)
			
			# plot type
			project.writeEntry("TUVIEW", "userplotdata{0}plottype".format(no), self.plotType)
			
			# status
			project.writeEntry("TUVIEW", "userplotdata{0}status".format(no), str(self.status))
			
			# number
			project.writeEntry("TUVIEW", "userplotdata{0}number".format(no), str(self.number))

			# reference time
			project.writeEntry("TUVIEW", "userplotdata{0}hasreferencetime".format(no), str(self.hasReferenceTime))
			if self.hasReferenceTime and self.referenceTime is not None:
				project.writeEntry("TUVIEW", "userplotdata{0}referencetimeyear".format(no), str(self.referenceTime.year))
				project.writeEntry("TUVIEW", "userplotdata{0}referencetimemonth".format(no), str(self.referenceTime.month))
				project.writeEntry("TUVIEW", "userplotdata{0}referencetimeday".format(no), str(self.referenceTime.day))
				project.writeEntry("TUVIEW", "userplotdata{0}referencetimehour".format(no), str(self.referenceTime.hour))
				project.writeEntry("TUVIEW", "userplotdata{0}referencetimeminute".format(no), str(self.referenceTime.minute))
				project.writeEntry("TUVIEW", "userplotdata{0}referencetimesecond".format(no), str(self.referenceTime.second))

	def loadProject(self, project, no):
		"""
		
		:param project: QgsProject
		:param no: int
		:return:
		"""
		
		# name
		self.name = project.readEntry("TUVIEW", "userplotdata{0}name".format(no))[0]
		
		# data and dates
		x = project.readEntry("TUVIEW", "userplotdata{0}x".format(no))[0]
		y = project.readEntry("TUVIEW", "userplotdata{0}y".format(no))[0]
		datesyear = project.readEntry("TUVIEW", "userplotdata{0}datesyear".format(no))[0]
		datesmonth = project.readEntry("TUVIEW", "userplotdata{0}datesmonth".format(no))[0]
		datesday = project.readEntry("TUVIEW", "userplotdata{0}datesday".format(no))[0]
		dateshour = project.readEntry("TUVIEW", "userplotdata{0}dateshour".format(no))[0]
		datesminute = project.readEntry("TUVIEW", "userplotdata{0}datesminute".format(no))[0]
		datessecond = project.readEntry("TUVIEW", "userplotdata{0}datessecond".format(no))[0]
		d = []
		if x:
			x = x.split('~~')
			y = y.split('~~')
			if datesyear:
				datesyear = datesyear.split('~~')
				datesmonth = datesmonth.split('~~')
				datesday = datesday.split('~~')
				dateshour = dateshour.split('~~')
				datesminute = datesminute.split('~~')
				datessecond = datessecond.split('~~')
			for i in range(len(x)):
				self.x.append(float(x[i]))
				self.y.append(float(y[i]))
				if datesyear:
					d.append(datetime(int(datesyear[i]), int(datesmonth[i]), int(datesday[i]),
					                  int(dateshour[i]), int(datesminute[i]), int(datessecond[i])))
		if d:
			self.setData(dates=d)
		
		# plot type
		self.plotType = project.readEntry("TUVIEW", "userplotdata{0}plottype".format(no))[0]
		
		# status
		self.status = True if project.readEntry("TUVIEW", "userplotdata{0}status".format(no))[0] == 'True' else False
		
		# number
		self.number = int(project.readEntry("TUVIEW", "userplotdata{0}number".format(no))[0])

		# reference time
		self.hasReferenceTime = True if project.readEntry("TUVIEW", "userplotdata{0}hasreferencetime".format(no))[0] == 'True' else False
		if self.hasReferenceTime:
			try:
				year = int(project.readEntry("TUVIEW", "userplotdata{0}referencetimeyear".format(no))[0])
				month = int(project.readEntry("TUVIEW", "userplotdata{0}referencetimemonth".format(no))[0])
				day = int(project.readEntry("TUVIEW", "userplotdata{0}referencetimeday".format(no))[0])
				hour = int(project.readEntry("TUVIEW", "userplotdata{0}referencetimehour".format(no))[0])
				minute = int(project.readEntry("TUVIEW", "userplotdata{0}referencetimeminute".format(no))[0])
				second = int(project.readEntry("TUVIEW", "userplotdata{0}referencetimesecond".format(no))[0])
				self.referenceTime = datetime(year, month, day, hour, minute, second)
			except:
				self.referenceTime = None
				self.hasReferenceTime = False