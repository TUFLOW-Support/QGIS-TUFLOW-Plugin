import os
import re
import numpy as np
from PyQt5.QtWidgets import QMessageBox
from ..tuflowqgis_library import (findPlotLayers, findIntersectFeat, is1dTable, is1dNetwork, isTSLayer)
from ..TUFLOW_XS import XS_results
from .tuflowqgis_turesultsindex import TuResultsIndex
from qgis.core import Qgis


class TuPlot1D():
	"""
	Class for handling 1D specific plotting.
	
	"""
	
	def __init__(self, TuPlot):
		self.tuPlot = TuPlot
		self.tuView = TuPlot.tuView
		self.tuResults = TuPlot.tuView.tuResults
	
	def plot1dResults(self):
		"""
		Plot 1D results.

		:return: bool -> True for successful, False for unsuccessful
		"""

		from .tuflowqgis_tuplot import TuPlot
		
		if self.tuView.tabWidget.currentIndex() == TuPlot.TimeSeries:
			self.plot1dTimeSeries()
			self.plot1dMaximums()
			self.plot1dMinimums()
		elif self.tuView.tabWidget.currentIndex() == TuPlot.CrossSection:
			self.plot1dLongPlot()
			self.plot1dCrossSection()
			self.plot1dHydProperty()
		
		return True
	
	def plot1dHydProperty(self, **kwargs):
		"""

		"""

		from .tuflowqgis_tuplot import TuPlot
		tuResults1D = self.tuView.tuResults.tuResults1D  # TuResults1D object

		# deal with kwargs
		bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		timestep = kwargs['time'] if 'time' in kwargs.keys() else None

		i = 0
		if self.tuView.currentLayer is not None:
			i = 1 if '.gpkg|layername=' in self.tuView.currentLayer.dataProvider().dataSourceUri() else 0

		if is1dTable(self.tuView.currentLayer):
			ids = [os.path.basename(x.attributes()[i].lower()) for x in self.tuView.currentLayer.selectedFeatures()]
		elif is1dNetwork(self.tuView.currentLayer):
			ids = [os.path.basename(x.attributes()[i].lower()) for x in self.tuView.currentLayer.selectedFeatures()]
		elif self.tuView.currentLayer in findPlotLayers(geom='L'):
			ids = [os.path.basename(x.attributes()[i].lower()) for x in self.tuView.currentLayer.selectedFeatures()]
		else:
			ids = []

		# clear the plot based on kwargs
		if bypass:
			pass
		else:
			self.tuPlot.clearPlot2(TuPlot.CrossSection, TuPlot.DataHydraulicProperty)

		# initialise plot data
		labels = []
		types = []
		xAll = []
		yAll = []

		for result in self.tuView.OpenResults.selectedItems():
			result = result.text()
			if result in self.tuResults.results.keys():
				rtypes = tuResults1D.typesXS[:]
				for id in ids:
					for rtype in rtypes:
						if 'line_cs' in self.tuResults.results[result] and \
								rtype in self.tuResults.results[result]['line_cs'] and \
								id.lower() in [x.lower() for x in self.tuResults.results[result]['line_cs'][rtype]]:
							ta = self.tuView.hydTables.getData(result)
							if ta is None:
								continue
							x, y = ta.plotProperty(id, rtype)
							xAll.append(x)
							yAll.append(y)
							labels.append('{0} - {1}'.format(id, rtype))
							types.append('{0}_CS'.format(rtype))

							# x, y, label, typ = self.plotResultsOnXS(xs, timestep)
							# xAll += x
							# yAll += y
							# labels += label
							# types += typ

		data = list(zip(xAll, yAll))
		dataTypes = [TuPlot.DataHydraulicProperty] * len(data)
		if data:
			self.tuPlot.drawPlot(TuPlot.CrossSection, data, labels, types, dataTypes, draw=draw)
			self.tuPlot.profilePlotFirst = False

	def plot1dCrossSection(self, **kwargs):
		"""

		"""

		from .tuflowqgis_tuplot import TuPlot
		tuResults1D = self.tuView.tuResults.tuResults1D  # TuResults1D object

		# deal with kwargs
		bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		timestep = kwargs['time'] if 'time' in kwargs.keys() else None

		if is1dTable(self.tuView.currentLayer):
			self.tuView.loadXsSelections()

		# clear the plot based on kwargs
		if bypass:
			pass
		else:
			self.tuPlot.clearPlot2(TuPlot.CrossSection, TuPlot.DataCrossSection1DViewer)

		# initialise plot data
		labels = []
		types = []
		xAll = []
		yAll = []

		for result in self.tuView.OpenResults.selectedItems():
			result = result.text()
			if result in self.tuResults.results.keys():
				rtypes = tuResults1D.typesXS[:]

				crossSections = [self.tuView.crossSections1D, self.tuView.crossSectionsFM]

				for crossSection in crossSections:
					for xs in crossSection.data:
						if xs.type.upper() in [x.upper() for x in rtypes]:
							if 'line_cs' in self.tuResults.results[result] and \
									xs.type in self.tuResults.results[result]['line_cs'] and \
									xs.source.lower() in self.tuResults.results[result]['line_cs'][xs.type]:
								# xAll.append(xs.x)
								# yAll.append(xs.z)
								section = xs.crossSectionPlot(self.tuView.tuOptions.plotInactiveAreas)
								if section.any():
									xAll.append(section[:,0])
									yAll.append(section[:,1])
								else:
									xAll.append([])
									yAll.append([])
								labels.append(xs.source)
								types.append('{0}_CS'.format(xs.type))

								x, y, label, typ = self.plotResultsOnXS(xs, timestep)
								xAll += x
								yAll += y
								labels += label
								types += typ

		data = list(zip(xAll, yAll))
		dataTypes = [TuPlot.DataCrossSection1DViewer] * len(data)
		if data:
			self.tuPlot.drawPlot(TuPlot.CrossSection, data, labels, types, dataTypes, draw=draw)
			self.tuPlot.profilePlotFirst = False

	def plotResultsOnXS(self, xs, timestep):
		"""

		"""

		from .tuflowqgis_tuplot import TuPlot
		tuResults1D = self.tuView.tuResults.tuResults1D  # TuResults1D object

		xAll, yAll = [], []
		labels = []
		typs = []
		ids = []

		plyrs = findPlotLayers('P')  # plot layers
		if not plyrs:
			return xAll, yAll, labels, typs

		acceptedResults = ['level', 'water level', 'max water level']
		rtypes = tuResults1D.typesXSRes
		rtypes = list(filter(lambda x: x.lower() in acceptedResults, rtypes))

		for rtype in rtypes:
			# get time
			if '{0}_1d'.format(rtype) in self.tuView.tuResults.maxResultTypes:
				rtypeLabel = '{0}/Maximums'.format(rtype)
				time = -99999
				isMax = True
			elif rtype.lower() == 'max water level':  # has to go before block below otherwise isn't triggered correctly
				time = -99999
				isMax = True
				rtypeLabel = rtype
				rtype = 'level'
			elif 'max' in rtype.lower():
				time = -99999
				rtypeLabel = rtype
				isMax = True
			elif rtype.lower() == 'water level':
				if timestep is None:
					timestep = self.tuView.tuResults.activeTime
				rtypeLabel = rtype
				isMax = False
				rtype = 'level'
			else:
				if timestep is None:
					timestep = self.tuView.tuResults.activeTime
				# if timestep not in self.tuView.tuResults.timekey2time.keys():
				# 	continue
				# time = self.tuView.tuResults.timekey2time[timestep]
				rtypeLabel = rtype
				isMax = False

			for plyr in plyrs:
				feat = findIntersectFeat(xs.feature, plyr)
				if feat is None:
					return xAll, yAll, labels, typs
				id = feat.attributes()[0].strip()
				#if id not in ids:
				for result in self.tuView.OpenResults.selectedItems():
					result = result.text()
					if result in self.tuResults.tuResults1D.results1d:
						res = self.tuResults.tuResults1D.results1d[result]
						if id in res.nodes.node_name:
							if res.formatVersion > 1:

								tuResultsIndex = TuResultsIndex(result, '{0}_1d'.format(rtype), timestep, isMax,
																False,
																self.tuView.tuResults,
																self.tuView.tuOptions.timeUnits)
								time = tuResultsIndex.timestep

								h = res.getResAtTime(id, '1D', rtype, time)
								if h is None or np.isnan(h):
									continue
								x, y = XS_results.fitResToXS2(xs, h)
								label = '{0} - {1}'.format(id, rtypeLabel) if len(
									self.tuView.OpenResults.selectedItems()) < 2 \
									else '{0} - {1} - {2}'.format(result, id, rtypeLabel)
								xAll.append(x)
								yAll.append(y)
								labels.append(label)
								typs.append(rtype)
								ids.append(id)

		return xAll, yAll, labels, typs

	def plot1dTimeSeries(self, **kwargs):
		"""
		Plots 1D time series based on selected features, results, and result types.

		:param kwargs: dict -> keyword arguments
		:return: bool -> True for successful, False for unsuccessful
		"""

		from .tuflowqgis_tuplot import TuPlot

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
			# if plot.lower() == '1d only':
			# 	self.tuPlot.clearPlot(0)
			# else:
			# 	self.tuPlot.clearPlot(0, retain_2d=True, retain_flow=True)
			self.tuPlot.clearPlot2(TuPlot.TimeSeries, TuPlot.DataTimeSeries1D)
		
		labels = []
		types = []
		xAll = []
		yAll = []
		plotAsPoints = []  # 2019 for flow regime
		flowRegime = []  # 2019
		flowRegimeTied = []  # 2020 flow regime tied to specific result type
		
		# iterate through all selected results
		#results = [x.text() for x in self.tuView.OpenResults.selectedItems()]
		#for result in results:
		for result in self.tuView.OpenResults.selectedItems():
			result = result.text()
			#result = result.name()

			if result in tuResults1D.results1d.keys():
				res = tuResults1D.results1d[result]

				# get result types for all selected types
				if re.findall(r'_TS(MB|MB1d2d)?(_[PLR])?$', result, flags=re.IGNORECASE) and isTSLayer(self.tuView.currentLayer):
					i = 1 if '.gpkg|layername=' in self.tuView.currentLayer.dataProvider().dataSourceUri().lower() else 0
					rtypes = [f.attribute(i)[0] for f in self.tuView.currentLayer.selectedFeatures()]
				elif re.findall(r'_TS(MB|MB1d2d)?(_[PLR])?$', result, flags=re.IGNORECASE):
					continue
				else:
					rtypes = tuResults1D.typesTS[:]
				#for rtype in tuResults1D.typesTS:
				for rtype in rtypes:
					# get result for each selected element
					for i, id in enumerate(tuResults1D.ids):
						#types.append('{0}_1d'.format(rtype))
						if rtype.lower() == "flow regime":
							plotAsPoints.append(True)
							flowRegime.append(True)
							types.append('{0}_1d'.format(rtype))
							flowRegimeTied.append(-1)
						elif re.findall(r"flow regime_\d", rtype, flags=re.IGNORECASE):
							f_id = re.split(r".*_\d_", rtype, flags=re.IGNORECASE)[1]
							if f_id == id:
								plotAsPoints.append(True)
								flowRegime.append(True)
								types.append('{0}_1d'.format(rtype))
								flowRegimeTied.append(int(re.findall(r"\d", rtype)[0]))
							else:
								continue
						elif rtype.lower() == "losses":
							if id not in res.Data_1D.CL.uID:
								continue
							iun = res.Data_1D.CL.uID.index(id)  # index unique name
							nCol = res.Data_1D.CL.nCols[iun]  # number of columns associated with element losses
							for j in range(nCol):
								plotAsPoints.append(False)
								flowRegime.append(False)
								types.append('{0}_1d'.format(rtype))
								flowRegimeTied.append(-1)
						else:
							plotAsPoints.append(False)
							flowRegime.append(False)
							types.append('{0}_1d'.format(rtype))
							flowRegimeTied.append(-1)
						
						# get data
						if res.formatVersion == 1:  # 2013
							found, ydata, message = res.getTSData(id, rtype)
							xdata = res.times
						elif res.formatVersion == 2:  # 2015
							dom = tuResults1D.domains[i]
							source = tuResults1D.sources[i].upper()
							if dom == '2D':
								if rtype.upper().find('STRUCTURE FLOWS') >= 0 and 'QS' in source:
									typename = 'QS'
								elif rtype.upper().find('STRUCTURE LEVELS') >= 0 and 'HU' in source:
									typename = 'HU'
								elif rtype.upper().find('STRUCTURE LEVELS') >= 0 and 'HD' in source:
									typename = 'HD'
								else:
									typename = rtype
							else:
								if re.findall("flow regime", rtype, re.IGNORECASE):
									typename = "Flow Regime"
								else:
									typename = rtype
							found, ydata, message = res.getTSData(id, dom, typename, 'Geom')
							xdata = res.times if found else []
						elif res.formatVersion == 0:  # _TS
							xdata, ydata = res.getTSData(self.tuView.currentLayer, id)
							rtype = ''
						else:
							continue
						if type(ydata) is list:
							if len(xdata) != len(ydata):
								xAll.append([])
								yAll.append([])
								labels.append('')
								continue
						else:  # ndarray
							if len(xdata) != ydata.shape[0]:
								xAll.append([])
								yAll.append([])
								labels.append('')
								continue
						if rtype != "Losses":
							if re.findall(r"flow regime", rtype, re.IGNORECASE):
								rtypelab = "Flow Regime_"
								label = '{0} - {1}'.format(id, rtypelab) if len(
									self.tuView.OpenResults.selectedItems()) < 2 \
									else '{0} - {1} - {2}'.format(result, id, rtypelab)
							else:
								if rtype:
									label = '{0} - {1}'.format(id, rtype) if len(self.tuView.OpenResults.selectedItems()) < 2 \
										else '{0} - {1} - {2}'.format(result, id, rtype)
								else:
									label = id
							xAll.append(xdata)
							yAll.append(ydata)
							labels.append(label)
						else:
							for i in range(ydata.shape[1]):
								xAll.append(xdata)
								yAll.append(ydata[:,i])
								j = res.Data_1D.CL.ID.index(id)
								lossName = res.Data_1D.CL.lossNames[j+i].strip()
								label = '{0} - {1} LC'.format(id, lossName) if len(self.tuView.OpenResults.selectedItems()) < 2 \
									else "{0} - {1} - {2} LC".format(result, id, lossName)
								labels.append(label)
								#if i > 0:
								#	types.append('{0}_1d'.format(rtype))
								#	plotAsPoints.append(False)
								#	flowRegime.append(False)

						tsResultTypes = [x for x in self.tuView.OpenResultTypes.model().timeSeriesItem.children()]
						if rtype.lower() in [x.ds_name.lower() for x in tsResultTypes]:
							irtype = [x.ds_name.lower() for x in tsResultTypes].index(rtype.lower())
							if tsResultTypes[irtype].isFlowRegime:
								rtypes.append('Flow Regime_{0}_{1}'.format(len(xAll) - 1, id))
		data = list(zip(xAll, yAll))
		dataTypes = [TuPlot.DataTimeSeries1D] * len(data)
		if data:
			self.tuPlot.drawPlot(TuPlot.TimeSeries, data, labels, types, dataTypes,
			                     draw=draw, time=time, show_current_time=showCurrentTime,
			                     plot_as_points=plotAsPoints, flow_regime=flowRegime, flow_regime_tied=flowRegimeTied)
		
		return True
	
	def plot1dLongPlot(self, **kwargs):
		"""
		Plots 1D long plots based on selected features, results, and result types.

		:param kwargs: dict -> keyword arguments
		:return: bool -> True for successful, False for unsuccessful
		"""

		from .tuflowqgis_tuplot import TuPlot

		qv = Qgis.QGIS_VERSION_INT

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
			#if plot.lower() == '1d only':
			#	self.tuPlot.clearPlot(1)
			#else:
			#	self.tuPlot.clearPlot(1, retain_2d=True)
			self.tuPlot.clearPlot2(TuPlot.CrossSection, TuPlot.DataCrossSection1D)
		
		labels = []
		xAll = []
		yAll = []
		types = []
		plotAsPoints = []
		plotAsPatch = []
		dataTypes = []
		pipeNames = []
		chanNames = {}

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

						if qv < 31600:
							if '{0}_1d'.format(type) in self.tuView.tuResults.maxResultTypes:
								type = '{0}/Maximums'.format(type)
								time = 99999
							if 'max' in type.lower():
								time = -99999
							else:
								if timestep is None:
									timestep = self.tuView.tuResults.activeTime
								if timestep not in self.tuView.tuResults.timekey2time.keys():
									xAll.append([])
									yAll.append([])
									labels.append('')
									plotAsPatch.append(False)
									plotAsPoints.append(False)
									continue
								time = self.tuView.tuResults.timekey2time[timestep]
						else:
							if timestep is None:
								timestep = self.tuView.tuResults.activeTime
							isMin = False
							isMax = False
							if '{0}_1d'.format(type) in self.tuView.tuResults.maxResultTypes:
								isMax = True
							elif 'max' in type.lower():
								isMax = True
							tuResultsIndex = TuResultsIndex(result, '{0}_1d'.format(type), timestep, isMax, isMin,
							                                self.tuView.tuResults, self.tuView.tuOptions.timeUnits)
							time = tuResultsIndex.timestep
							if time is None:
								xAll.append([])
								yAll.append([])
								labels.append('')
								plotAsPatch.append(False)
								plotAsPoints.append(False)
								continue

						x, y = res.getLongPlotXY(type, time)
						
						if x is not None and y is not None:
							# treat differently if adverse gradients
							if 'adverse gradients (if any)' in type.lower():
								#if x[0]:
								xAll.append(x[0])
								yAll.append(x[1])
								label = 'Adverse Water Level Gradient' \
									if len(self.tuView.OpenResults.selectedItems()) < 2 \
									else '{0} - Adverse Water Level Gradient'.format(result)
								labels.append(label)
								plotAsPoints.append(True)
								plotAsPatch.append(False)
								#if y[0]:
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
									# pipeNames.append(res.LP.chan_ids[:])
									pipeNames.append(res.LP.chan_list[:])
							# else normal X, Y data
							else:
								if len(x) != len(y):
									xAll.append([])
									yAll.append([])
									labels.append('')
									continue
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
								if type == 'Bed Level':
									chanNames[label] = res.LP.chan_list[:]
		
		data = list(zip(xAll, yAll))
		dataTypes = [TuPlot.DataCrossSection1D] * len(data)
		if data:
			self.tuPlot.drawPlot(TuPlot.CrossSection, data, labels, types, dataTypes,
			                     plot_as_points=plotAsPoints, plot_as_patch=plotAsPatch, draw=draw,
			                     pipe_names=pipeNames, chan_names=chanNames)
			self.tuPlot.profilePlotFirst = False
		
		return True

	def plot1dMaximums(self, **kwargs):
		"""
		Plots 1D maximums based on selected features, results, and result types.

		:param kwargs: dict -> keyword arguments
		:return: bool -> True for successful, False for unsuccessful
		"""

		from .tuflowqgis_tuplot import TuPlot

		activeMeshLayers = self.tuView.tuResults.tuResults2D.activeMeshLayers  # list
		tuResults1D = self.tuView.tuResults.tuResults1D  # TuResults1D object

		# deal with kwargs
		bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
		bypass = True
		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True

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
		plotAsPoints = []
		dataTypes = []

		# iterate through all selected results
		for result in self.tuView.OpenResults.selectedItems():
			# for result in self.tuView.tuResults.tuResults2D.activeMeshLayers:
			result = result.text()
			# result = result.name()

			if result in tuResults1D.results1d.keys():
				res = tuResults1D.results1d[result]

				# get result types for all selected types
				if re.findall(r'_TS(_[PLR])?$', result, flags=re.IGNORECASE) and isTSLayer(self.tuView.currentLayer):
					i = 1 if '.gpkg|layername=' in self.tuView.currentLayer.dataProvider().dataSourceUri().lower() else 0
					rtypes = [f.attribute(i)[0] for f in self.tuView.currentLayer.selectedFeatures()]
				else:
					rtypes = tuResults1D.typesTS[:]

				# get result types for all selected types
				for type in rtypes:

					if '{0}_1d'.format(type) in self.tuResults.maxResultTypes or isTSLayer(result, self.tuResults.results):

						# get result for each selected element
						for i, id in enumerate(tuResults1D.ids):
							types.append('{0}_1d'.format(type))

							# get data
							if res.formatVersion == 1:  # 2013
								found, ydata, message = res.getMAXData(id, type)
								xdata = res.times
							elif res.formatVersion == 2:  # 2015
								dom = tuResults1D.domains[i]
								source = tuResults1D.sources[i].upper()
								typename = type
								found, xydata, message = res.getMAXData(id, dom, typename)
								if len(xydata) != 2:
									xAll.append([])
									yAll.append([])
									labels.append('')
									plotAsPoints.append(True)
									continue
								xdata = [xydata[0]]
								ydata = [xydata[1]]
							elif res.formatVersion == 0:  # _TS
								xdata, ydata = res.getMaxData(self.tuView.currentLayer, id)
								type = ''
							else:
								continue
							if type:
								label = '{0} - {1} Max'.format(id, type) if len(self.tuView.OpenResults.selectedItems()) < 2 \
									else '{0} - {1} - {2} Max'.format(result, id, type)
							else:
								label = '{0} - Max'.format(id)
							xAll.append(xdata)
							yAll.append(ydata)
							labels.append(label)
							plotAsPoints.append(True)

		data = list(zip(xAll, yAll))
		dataTypes = [TuPlot.DataTimeSeries1D] * len(data)
		if data:
			self.tuPlot.drawPlot(TuPlot.TimeSeries, data, labels, types, dataTypes, plot_as_points=plotAsPoints, draw=draw)

		return True

	def plot1dMinimums(self, **kwargs):
		"""
		Plots 1D maximums based on selected features, results, and result types.

		:param kwargs: dict -> keyword arguments
		:return: bool -> True for successful, False for unsuccessful
		"""

		from .tuflowqgis_tuplot import TuPlot

		activeMeshLayers = self.tuView.tuResults.tuResults2D.activeMeshLayers  # list
		tuResults1D = self.tuView.tuResults.tuResults1D  # TuResults1D object

		# deal with kwargs
		bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
		bypass = True
		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True

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
		plotAsPoints = []
		dataTypes = []

		# iterate through all selected results
		for result in self.tuView.OpenResults.selectedItems():
			# for result in self.tuView.tuResults.tuResults2D.activeMeshLayers:
			result = result.text()
			# result = result.name()

			if result in tuResults1D.results1d.keys():
				res = tuResults1D.results1d[result]

				# get result types for all selected types
				if re.findall(r'_TS(_[PLR])?$', result, flags=re.IGNORECASE) and isTSLayer(self.tuView.currentLayer):
					i = 1 if '.gpkg|layername=' in self.tuView.currentLayer.dataProvider().dataSourceUri().lower() else 0
					rtypes = [f.attribute(i)[0] for f in self.tuView.currentLayer.selectedFeatures()]
				else:
					rtypes = tuResults1D.typesTS[:]

				# get result types for all selected types
				for type in rtypes:

					if '{0}_1d'.format(type) in self.tuResults.minResultTypes or isTSLayer(result, self.tuResults.results):

						# get result for each selected element
						for i, id in enumerate(tuResults1D.ids):
							types.append('{0}_1d'.format(type))

							# get data
							if res.formatVersion == 1:  # 2013
								# found, ydata, message = res.getMAXData(id, type)
								# xdata = res.times
								continue
							elif res.formatVersion == 2:  # 2015
								# dom = tuResults1D.domains[i]
								# source = tuResults1D.sources[i].upper()
								# typename = type
								# found, xydata, message = res.getMAXData(id, dom, typename)
								# if len(xydata) != 2:
								# 	xAll.append([])
								# 	yAll.append([])
								# 	labels.append('')
								# 	plotAsPoints.append(True)
								# 	continue
								# xdata = [xydata[0]]
								# ydata = [xydata[1]]
								continue
							elif res.formatVersion == 0:  # _TS
								xdata, ydata = res.getMinData(self.tuView.currentLayer, id)
								type = ''
							else:
								continue
							if type:
								label = '{0} - {1} Min'.format(id, type) if len(self.tuView.OpenResults.selectedItems()) < 2 \
									else '{0} - {1} - {2} Min'.format(result, id, type)
							else:
								label = '{0} - Min'.format(id)
							xAll.append(xdata)
							yAll.append(ydata)
							labels.append(label)
							plotAsPoints.append(True)

		data = list(zip(xAll, yAll))
		dataTypes = [TuPlot.DataTimeSeries1D] * len(data)
		if data:
			self.tuPlot.drawPlot(TuPlot.TimeSeries, data, labels, types, dataTypes, plot_as_points=plotAsPoints, draw=draw)

		return True
