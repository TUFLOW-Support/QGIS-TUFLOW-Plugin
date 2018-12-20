


class TuPlot1D():
	"""
	Class for handling 1D specific plotting.
	
	"""
	
	def __init__(self, TuPlot):
		self.tuPlot = TuPlot
		self.tuView = TuPlot.tuView
	
	def plot1dResults(self):
		"""
		Plot 1D results.

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if self.tuView.tabWidget.currentIndex() == 0:
			self.plot1dTimeSeries()
		elif self.tuView.tabWidget.currentIndex() == 1:
			self.plot1dLongPlot()
		
		return True
	
	def plot1dTimeSeries(self, **kwargs):
		"""
		Plots 1D time series based on selected features, results, and result types.

		:param kwargs: dict -> keyword arguments
		:return: bool -> True for successful, False for unsuccessful
		"""

		activeMeshLayers = self.tuView.tuResults.tuResults2D.activeMeshLayers  # list
		tuResults1D = self.tuView.tuResults.tuResults1D  # TuResults1D object
		
		# deal with kwargs
		bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		time = kwargs['time'] if 'time' in kwargs.keys() else None
		showCurrentTime = kwargs['show_current_time'] if 'show_current_time' in kwargs.keys() else False
		
		# clear the plot based on kwargs
		if bypass:
			pass
		else:
			if plot.lower() == '1d only':
				self.tuPlot.clearPlot(0)
			else:
				self.tuPlot.clearPlot(0, retain_2d=True, retain_flow=True)
		
		labels = []
		types = []
		xAll = []
		yAll = []
		
		# iterate through all selected results
		for result in self.tuView.OpenResults.selectedItems():
			result = result.text()
			
			if result in tuResults1D.results1d.keys():
				res = tuResults1D.results1d[result]
				
				# get result types for all selected types
				for type in tuResults1D.typesTS:
					
					# get result for each selected element
					for i, id in enumerate(tuResults1D.ids):
						types.append('{0}_1d'.format(type))
						
						# get data
						if res.formatVersion == 1:  # 2013
							found, ydata, message = res.getTSData(id, type)
							xdata = res.times
						elif res.formatVersion == 2:  # 2015
							dom = tuResults1D.domains[i]
							source = tuResults1D.sources[i].upper()
							if dom == '2D':
								if type.upper().find('STRUCTURE FLOWS') >= 0 and source == 'QS':
									typename = 'QS'
								elif type.upper().find('STRUCTURE LEVELS') >= 0 and source == 'HU':
									typename = 'HU'
								elif type.upper().find('STRUCTURE LEVELS') >= 0 and source == 'HD':
									typename = 'HD'
							found, ydata, message = res.getTSData(id, dom, type, 'Geom')
							xdata = res.times
							if len(xdata) != len(ydata):
								xAll.append([])
								yAll.append([])
								continue
						else:
							continue
						label = '{0} - {1}'.format(id, type) if len(self.tuView.OpenResults.selectedItems()) < 2 \
							else '{0} - {1} - {2}'.format(result, id, type)
						xAll.append(xdata)
						yAll.append(ydata)
						labels.append(label)
		
		data = list(zip(xAll, yAll))
		if data:
			self.tuPlot.drawPlot(0, data, labels, types, draw=draw, time=time, show_current_time=showCurrentTime)
		
		return True
	
	def plot1dLongPlot(self, **kwargs):
		"""
		Plots 1D long plots based on selected features, results, and result types.

		:param kwargs: dict -> keyword arguments
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		activeMeshLayers = self.tuView.tuResults.tuResults2D.activeMeshLayers  # list
		tuResults1D = self.tuView.tuResults.tuResults1D  # TuResults1D object
		
		# deal with kwargs
		bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		timestep = kwargs['time'] if 'time' in kwargs.keys() else None
		
		# clear the plot based on kwargs
		if bypass:
			pass
		else:
			if plot.lower() == '1d only':
				self.tuPlot.clearPlot(1)
			else:
				self.tuPlot.clearPlot(1, retain_2d=True)
		
		labels = []
		xAll = []
		yAll = []
		types = []
		plotAsPoints = []
		plotAsPatch = []
		
		# iterate through all selected results
		for result in self.tuView.OpenResults.selectedItems():
			result = result.text()
			
			if result in tuResults1D.results1d.keys():
				res = tuResults1D.results1d[result]
				error = tuResults1D.getLongPlotConnectivity(res)
				if not error:
					
					# get result types for all selected types
					for type in tuResults1D.typesLP:
						types.append('{0}_1d'.format(type))
						
						if '{0}_1d'.format(type) in self.tuView.tuResults.maxResultTypes:
							type = '{0}/Maximums'.format(type)
							time = -99999
						else:
							if timestep is None:
								timestep = self.tuView.tuResults.activeTime
							if timestep not in self.tuView.tuResults.timekey2time.keys():
								continue
							time = self.tuView.tuResults.timekey2time[timestep]
						x, y = res.getLongPlotXY(type, time)
						
						if x is not None and y is not None:
							# treat differently if adverse gradients
							if 'adverse gradients (if any)' in type.lower():
								if x[0]:
									xAll.append(x[0])
									yAll.append(x[1])
									label = 'Adverse Water Level Gradient' \
										if len(self.tuView.OpenResults.selectedItems()) < 2 \
										else '{0} - Adverse Water Level Gradient'.format(result)
									labels.append(label)
									plotAsPoints.append(True)
									plotAsPatch.append(False)
								if y[0]:
									xAll.append(y[0])
									yAll.append(y[1])
									label = 'Adverse Energy Level Gradient' \
										if len(self.tuView.OpenResults.selectedItems()) < 2 \
										else '{0} - Adverse Energy Level Gradient'.format(result)
									labels.append(label)
									plotAsPoints.append(True)
									plotAsPatch.append(False)
							# treat differently if culverts and pipes
							elif 'culverts and pipes' in type.lower():
								if x:
									xAll.append(x)
									yAll.append(y)
									label = 'Culverts and Pipes' \
										if len(self.tuView.OpenResults.selectedItems()) < 2 \
										else '{0} - Culverts and Pipes'.format(result)
									labels.append(label)
									plotAsPoints.append(False)
									plotAsPatch.append(True)
							# else normal X, Y data
							else:
								xAll.append(x)
								yAll.append(y)
								if type == 'Water Level' or type == 'Bed Elevation':  # add 1D to label if name also in 2D results
									label = '{0} 1D'.format(type) if len(
										self.tuView.OpenResults.selectedItems()) < 2 else '{0} - {1} 1D'.format(
										result, type)
								else:
									label = '{0}'.format(type) if len(
										self.tuView.OpenResults.selectedItems()) < 2 else '{0} - {1}'.format(
										result, type)
								labels.append(label)
								if 'pit ground levels' in type.lower():
									plotAsPoints.append(True)
								else:
									plotAsPoints.append(False)
								plotAsPatch.append(False)
		
		data = list(zip(xAll, yAll))
		if data:
			self.tuPlot.drawPlot(1, data, labels, types, plot_as_points=plotAsPoints, plot_as_patch=plotAsPatch, draw=draw)
			self.tuPlot.profilePlotFirst = False
		
		return True