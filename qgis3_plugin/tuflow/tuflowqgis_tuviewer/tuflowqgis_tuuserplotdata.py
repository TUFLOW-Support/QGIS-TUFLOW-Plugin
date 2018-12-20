


class TuUserPlotDataManager():
	"""
	Class for managing user input plot data sets.
	
	"""
	
	def __init__(self):
		self.error = ''
		self.datasets = {}  # dict - { dataset name: TuUserPlotDataSet }
		self.count = 0
		
	def addDataSet(self, name, data, plotType, dates=None):
		"""
		
		:param name:
		:param data:
		:param plotType:
		:return:
		"""
		
		if name in self.datasets.keys():
			self.error = 'Dataset Name Already Exists'
			return False
		dataset = TuUserPlotDataSet(name, data, plotType, True, self.count, dates)
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
					copyDataset = TuUserPlotDataSet(newname, [dataset.x, dataset.y], dataset.plotType, dataset.status, dataset.number)
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
		
		
class TuUserPlotDataSet():
	"""
	Class for handling individual user input data sets.
	
	"""
	
	def __init__(self, name, data, plotType, status, number, dates=None):
		self.error = ''
		self.number = number
		self.status = status

		if name is not None:
			self.name = '{0}'.format(name)
		else:
			self.name = name
		
		if plotType.lower() == 'time series' or plotType.lower() == 'long plot':
			self.plotType = plotType
		else:
			plotType = None
		
		
		self.x = None  # list -> float  [ x1, x2, ... ]
		self.y = None  # list -> float  [ y1, y2, ... ]
		if len(data) == 2:
			if data[0]:
				self.x = data[0]
			if data[1]:
				self.y = data[1]
		if self.x is not None or self.y is not None:
			if self.x is None:
				self.error = 'X, Y data set lengths do not match'
			if self.y is None:
				self.error = 'X, Y data set lengths do not match'
		if self.x is not None and self.y is not None:
			if len(self.x) != len(self.y):
				self.error = 'X, Y data set lengths do not match'
		
		self.dates = None
		if not self.error:
			if type(dates) is list:
				if dates:
					if len(dates) == len(self.x):
						self.dates = dates
					else:
						self.error = 'Date data length does not match Y data'
		
	def setPlotType(self, plotType):
		"""
		
		:param plotType: str plot type 'time series' or 'long plot'
		:return:
		"""
		
		self.error = ''
		
		if plotType.lower() == 'time series' or plotType.lower() == 'long plot':
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
			
	def setData(self, data, dates=None):
		"""
		
		
		:param data: list -> list axis data -> float  [ [ x1, x2, ... ], [ y1, y2, ... ] ]
		:return:
		"""
		
		self.error = ''
		
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