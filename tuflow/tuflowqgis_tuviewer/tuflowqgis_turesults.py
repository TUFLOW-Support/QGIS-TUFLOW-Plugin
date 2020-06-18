from datetime import datetime, timedelta
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets import *
import tuflowqgis_turesults1d
import tuflowqgis_turesults2d
import tuflowqgis_turesultsParticles
from tuflow.dataset_view import DataSetModel
from tuflow.tuflowqgis_library import tuflowqgis_find_layer, convertFormattedTimeToTime, convertTimeToFormattedTime, \
	findAllMeshLyrs, roundSeconds, isSame_float, dt2qdt
from tuflow.dataset_menu import DatasetMenuDepAv
from tuflow.TUFLOW_XS import XS


class TuResults():
	"""
	Parent class for handling 1D, 2D and Particles results classes.
	
	"""

	Results2D = [1, 2]
	Results1D = [4, 5, 6, 7, 8]
	TimePrecision = 0.000001
	OtherTypes = ['_ts', '_lp', '_particles', '_cs']

	def __init__(self, TuView=None):
		if TuView is not None:
			self.tuView = TuView
			self.iface = TuView.iface
			self.results = {}  # dict - e.g. { M01_5m_001: { depth: { '0.000000': ( timestep, type, QgsMeshDatasetIndex )}, point_ts: ( types, timesteps ) } }
			self.cboTime2timekey = {}
			self.timekey2time = {}  # e.g. {'1.833333': 1.8333333}
			self.timekey2date = {}  # e.g. {'1.833333': '01/01/2000 09:00:00'}
			self.time2date = {}
			self.date2timekey = {}
			self.date2time = {}
			self.secondaryAxisTypes = []
			self.maxResultTypes = []
			self.minResultTypes = []
			self.activeTime = None  # active time for rendering
			self.activeResults = []  # str result type names
			self.activeResultsTypes = []  # int result types (e.g. 1 - scalar, 2 - vector...)
			self.activeResultsIndexes = []  # QModelIndex
			self.activeResultsItems = []  # DataSetTreeNode
			self.dateFormat = '%d/%m/%Y %H:%M:%S'  # for time combobox not plotting
			self._dateFormat = '{0:%d}/{0:%m}/{0:%Y} {0:%H}:{0:%M}:{0:%S}'  # for time combobox not plotting
			self.timeSpec = self.iface.mapCanvas().temporalRange().begin().timeSpec()
			
			# 1D results
			self.tuResults1D = tuflowqgis_turesults1d.TuResults1D(TuView)
			
			# 2D results
			self.tuResults2D = tuflowqgis_turesults2d.TuResults2D(TuView)

			# Particles results
			self.tuResultsParticles = tuflowqgis_turesultsParticles.TuResultsParticles(TuView)

	def importResults(self, type, inFileNames):
		"""
		Import results 1D or 2D or Particles
		
		:param type: str -> 'mesh' or 'timeseries' or 'particles'
		:param inFileNames: list -> str file path
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		result = False
		if type.lower() == 'mesh':
			result = self.tuResults2D.importResults(inFileNames)
		elif type.lower() == 'timeseries':
			result = self.tuResults1D.importResults(inFileNames)
		elif type.lower() == 'particles':
			result = self.tuResultsParticles.importResults(inFileNames)
		if not result:
			return False

		update = self.updateResultTypes()
		
		if not update:
			return False
		
		return True
	
	def updateActiveTime(self):
		"""
		Updates the active time based on the time in the ui.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		i = self.tuView.cboTime.currentIndex()
		self.tuView.sliderTime.setSliderPosition(i)
		
		self.activeTime = None
		if i != -1:
			self.activeTime = self.tuView.cboTime.currentText()
			if not self.tuView.tuOptions.xAxisDates:
				#unit = self.tuView.tuOptions.timeUnits
				#self.activeTime = '{0:.6f}'.format(convertFormattedTimeToTime(self.activeTime, unit=unit))
				if self.activeTime in self.cboTime2timekey:
					self.activeTime = self.cboTime2timekey[self.activeTime]
				else:
					unit = self.tuView.tuOptions.timeUnits
					self.activeTime = '{0:.6f}'.format(convertFormattedTimeToTime(self.activeTime, unit=unit))
			else:
				self.activeTime = datetime.strptime(self.activeTime, self.dateFormat)
				self.activeTime = self.date2timekey[self.activeTime]

		self.updateQgsTime()
		self.tuResultsParticles.updateActiveTime()

	def updateOpenResults(self, *args):
		"""

		"""

		sel = []
		for i in range(self.tuView.OpenResults.count()):
			item = self.tuView.OpenResults.item(i)
			if item.isSelected():
				sel.append(item.text())

		self.tuView.OpenResults.clear()
		self.tuView.OpenResults.addItems(self.results.keys())

		for i in range(self.tuView.OpenResults.count()):
			item = self.tuView.OpenResults.item(i)
			if item.text() in sel:
				item.setSelected(True)
			if item.text() in args:
				item.setSelected(True)

		self.updateResultTypes()

	def resetResultTypes(self):
		"""
		Resets the result types in the tree widget

		:return: bool -> True for succssful, False for unsuccessful
		"""

		# Remove all children of Map Outputs and time series
		self.tuView.initialiseDataSetView()

		# Reset multi combobox to empty
		for dataType in self.tuView.tuPlot.plotDataPlottingTypes:
			menu = self.tuView.tuPlot.tuPlotToolbar.plotDataToPlotMenu[dataType]
			if isinstance(menu, QAction):
				menu = menu.parentWidget()
			if isinstance(menu, DatasetMenuDepAv):
				menu.clearAllSubMenus()
				continue
			elif isinstance(menu, QToolButton):
				continue

			menu.clear()

		return True
	
	def getDataFromResultsDict(self, resultName):
		"""
		Returns list of meta data available in the results dictionary

		:param resultName: str - name of open result mesh layer
		:return: list -> float timestep
		:return: list -> str maximum result type e.g. 'depth'
		:return: list -> str temporal result type e.g. 'depth'
		:return: list -> tuple -> ( str type, int type, bool hasMax ) point time series type  e.g. ( 'water level', 4, False )
		:return: list -> tuple -> ( str type, int type, bool hasMax ) line time series type  e.g. ( 'flow', 5, False )
		:return: list -> tuple -> ( str type, int type, bool hasMax ) region time series type  e.g. ( 'volume', 6, False )
		:return: list -> tuple -> ( str type, int type, bool hasMax ) line long plot type  e.g. ( 'water level', 7, True )
		"""

		timesteps, minResultTypes, maxResultTypes, temporalResultTypes, pTypeTS, lTypeTS, rTypeTS, lTypeLP, csTypes = [], [], [], [], [], [], [], [], []
		timestepsTS = []
		timestepsLP = []
		timestepsParticles = []

		r = self.results[resultName]
		for type, t in r.items():
			info = ()  # (name, type, haMax) e.g. (depth, 1, True) 1=Scalar 2=Vector, 3=none
			if TuResults.isMaximumResultType(type):
				if type not in maxResultTypes:
					rt = TuResults.stripMaximumName(type)
					maxResultTypes.append(rt)
			elif TuResults.isMinimumResultType(type):
				if type not in minResultTypes:
					rt = TuResults.stripMinimumName(type)
					minResultTypes.append(rt)
			elif '_ts' in type:
				timestepsTS = t[-1]
				if type == 'point_ts':
					pTypeTS = [[x, 4, True] for x in t[0]]
					if ['MB', 4, True] in pTypeTS:
						index = pTypeTS.index(['MB', 4, True])
						info = pTypeTS[index]
						info[2] = False
					if ['Flow Regime', 4, True] in pTypeTS:
						index = pTypeTS.index(['Flow Regime', 4, True])
						info = pTypeTS[index]
						info[2] = False
				elif type == 'line_ts':
					lTypeTS = [[x, 5, True] for x in t[0]]
					if ['Flow Area', 5, True] in lTypeTS:
						index = lTypeTS.index(['Flow Area', 5, True])
						info = lTypeTS[index]
						info[2] = False
					if ['Losses', 5, True] in lTypeTS:
						index = lTypeTS.index(['Losses', 5, True])
						info = lTypeTS[index]
						info[2] = False
					if ['Flow Regime', 4, False] in pTypeTS and ['Flow Regime', 5, True] in lTypeTS:
						lTypeTS.remove(['Flow Regime', 5, True])
				elif type == 'region_ts':
					rTypeTS = [(x, 6, True) for x in t[0]]
			elif '_lp' in type:
				timestepsLP = t[-1]
				for x in t[0]:
					#if x == 'Water Level' or x == 'Energy Level':
					#	lTypeLP.append((x, 7, True))
					#else:
					lTypeLP.append((x, 7, False))
			elif '_cs' in type:
				if type == 'line_cs':
					for x in t:
						csTypes.append((x, 8, False))
			elif '_particles' in type:
				timestepsParticles = t[0]
			else:
				temporalResultTypes.append(type)
				for i, (time, values) in enumerate(t['times'].items()):
					if values[0] != 9999.0:
						if values[0] not in timesteps:
							timesteps.append(float(values[0]))
		
		if not self.tuView.lock2DTimesteps:
			timesteps = self.joinResultTypes(timesteps, timestepsTS, timestepsLP, timestepsParticles, type='time')
		
		return timesteps, minResultTypes, maxResultTypes, temporalResultTypes, pTypeTS, lTypeTS, rTypeTS, lTypeLP, csTypes
	
	def joinResultTypes(self, *args, **kwargs):
		"""
		Joins open result type lists so that there is no duplicates

		:param args: list -> list
		:param kwargs: dict
		:return: list
		"""
		
		final = []
		
		for arg in args:
			for item in arg:
				if 'type' in kwargs.keys() and kwargs['type'] == 'time':
					# if float('{0:.6f}'.format(item)) not in [float('{0:.6f}'.format(x)) for x in final]:
					if not [item for x in final if isSame_float(item, x, prec=TuResults.TimePrecision)]:
						final.append(item)
				else:
					if item not in final:
						final.append(item)
		
		# make sure times are sorted ascendingly
		if 'type' in kwargs.keys() and kwargs['type'] == 'time':
			final = sorted(final)
		
		return final
	
	def applyPreviousResultTypeSelections(self, currentPlotData, time):
		"""
		Applies the previously selected result types to updated DataSetView.

		:param names: list -> str result type
		:param time: str -> time key
		:return: bool -> True for successful, False for unsuccessful
		"""

		openResultTypes = self.tuView.OpenResultTypes  # DataSetView
		#mcboResultType = self.tuView.mcboResultType  # QgsCheckableComboBox
		cboTime = self.tuView.cboTime  # QgsComboBox
		
		# repopulate active results with new model indexes
		self.activeResultsIndexes = []  # QModelIndex
		self.activeResultsItems = []  # DataSetTreeNode
		for item in openResultTypes.model().mapOutputsItem.children():
			name = item.ds_name
			index = openResultTypes.model().item2index(item)
			if name in self.activeResults:
				openResultTypes.selectionModel().select(index, QItemSelectionModel.Select)
				if item.ds_type == 1:
					openResultTypes.activeScalarIdx = index
				elif item.ds_type == 2:
					openResultTypes.activeVectorIdx = index
				self.activeResultsItems.append(item)
				self.activeResultsIndexes.append(index)
		for item in openResultTypes.model().timeSeriesItem.children():
			nameAppend = ''
			if item.ds_type == 4 or item.ds_type == 5 or item.ds_type == 6:
				nameAppend = '_TS'
			elif item.ds_type == 7:
				nameAppend = '_LP'
			elif item.ds_type == 8:
				nameAppend = '_CS'
			name = item.ds_name + nameAppend
			index = openResultTypes.model().item2index(item)
			if name in self.activeResults:
				openResultTypes.selectionModel().select(index, QItemSelectionModel.Select)
				self.activeResultsItems.append(item)
				self.activeResultsIndexes.append(openResultTypes.model().item2index(item))
		
		# if there are no active results assume first dataset and select first result
		if not self.activeResults:
			openResultTypes = self.tuView.OpenResultTypes
			ind = openResultTypes.model().index(0, 0)
			index = openResultTypes.indexBelow(ind)
			if index.internalPointer().ds_name != 'None':
				openResultTypes.selectionModel().select(index, QItemSelectionModel.Select)
				self.tuView.tuResults.activeResultsIndexes.append(index)
				self.tuView.tuResults.activeResultsItems.append(index.internalPointer())
				self.tuView.tuResults.activeResultsTypes.append(index.internalPointer().ds_type)
				self.tuView.tuResults.activeResults.append(index.internalPointer().ds_name)
				if index.internalPointer().ds_type == 1:
					self.tuResults2D.activeScalar = index.internalPointer().ds_name
					openResultTypes.activeScalarIdx = index
					openResultTypes.activeScalarName = index.internalPointer().ds_name
				elif index.internalPointer().ds_type == 2:
					self.tuResults2D.activeVector = index.internalPointer().ds_name
					openResultTypes.activeVectorIdx = index
					openResultTypes.activeVectorName = index.internalPointer().ds_name
			
		self.updateActiveResultTypes(None)

		# apply max and secondary axis toggle to result types
		for item in openResultTypes.model().mapOutputsItem.children():
			if item.ds_name in self.secondaryAxisTypes:
				item.toggleSecondaryActive()
			if item.ds_name in self.maxResultTypes:
				item.toggleMaxActive()
		for item in openResultTypes.model().timeSeriesItem.children():
			if '{0}_1d'.format(item.ds_name) in self.secondaryAxisTypes:
				item.toggleSecondaryActive()
			if '{0}_1d'.format(item.ds_name) in self.maxResultTypes:
				item.toggleMaxActive()
		
		# apply selection to plotting result types
		#mcboResultType.setCheckedItems(names)
		#self.tuView.tuPlot.tuPlotToolbar.setCheckedItemsPlotOptions(namesTS, 0)
		#self.tuView.tuPlot.tuPlotToolbar.setCheckedItemsPlotOptions(namesLP, 1)
		for dataType, plotData in currentPlotData.items():
			self.tuView.tuPlot.tuPlotToolbar.setCheckedItemsPlotOptions(dataType, plotData)

		# apply active time
		if time is not None:
			date = self.timekey2date[time]
			#dateProper = datetime.strptime(date, self.tuView.tuOptions.dateFormat)  # datetime object
			timeProper = self.timekey2time[time]
			if not self.tuView.tuOptions.xAxisDates:
				unit = self.tuView.tuOptions.timeUnits
				timeFormatted = convertTimeToFormattedTime(timeProper, unit=unit)
				closestTimeDiff = 99999
			else:
				timeFormatted = self.tuView.tuOptions.dateFormat.format(date)
				closestTimeDiff = timedelta(days=99999)
			timeFound = False
			closestTimeIndex = None
			for i in range(cboTime.count()):
				if cboTime.itemText(i) == timeFormatted:
					cboTime.setCurrentIndex(i)
					timeFound = True
					break
				else:
					# record the closest time index so it can be applied if no exact match is found
					if not self.tuView.tuOptions.xAxisDates:
						unit = self.tuView.tuOptions.timeUnits
						timeConverted = convertFormattedTimeToTime(cboTime.itemText(i), unit=unit)
						timeDiff = abs(timeConverted - timeProper)
					else:
						timeConverted = datetime.strptime(cboTime.itemText(i), self.dateFormat)
						timeDiff = abs(timeConverted - date)
					closestTimeDiff = min(closestTimeDiff, timeDiff)
					if closestTimeDiff == timeDiff:
						closestTimeIndex = i
			if not timeFound and closestTimeIndex is not None:
				cboTime.setCurrentIndex(closestTimeIndex)
			else:
				self.activeTime = time
		else:
			if cboTime.count():
				#self.activeTime = '{0:.6f}'.format(convertFormattedTimeToTime(cboTime.currentText()))
				if cboTime.currentText() in self.cboTime2timekey:
					self.activeTime = self.cboTime2timekey[cboTime.currentText()]
				else:
					# if self.cboTime2timekey is empty reset active time to none
					if not self.cboTime2timekey:
						self.activeTime = None
					else:  # set it to the first value
						self.activeTime = self.cboTime2timekey[[x for x in sorted(self.cboTime2timekey)][0]]
		
		changed = self.updateActiveResultTypes(None)
		if not changed:
			return False
		
		return True
	
	def updateResultTypes(self):
		"""
		Populates the plotting ui with available result types in the selected open mesh results

		:return: bool -> True for successful, False for unsuccessful
		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		sliderTime = self.tuView.sliderTime  # QSlider
		cboTime = self.tuView.cboTime  # QComboBox
		#mcboResultType = self.tuView.mcboResultType  # QgsCheckableComboBox
		openResults = self.tuView.OpenResults  # QListWidget
		openResultTypes = self.tuView.OpenResultTypes  # DataSetView
		
		# record existing plotting 2D result types and time so it can be re-applied after the update
		#currentNames = mcboResultType.checkedItems()
		#currentNamesTS = self.tuView.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(TuPlot.DataTimeSeries2D)
		#currentNamesLP = self.tuView.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(TuPlot.DataCrossSection2D)
		currentPlotData = {}
		for dataType in self.tuView.tuPlot.plotDataPlottingTypes:
			plotData = self.tuView.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(dataType, all_details=True)
			if plotData:
				currentPlotData[dataType] = plotData
		currentTime = str(self.activeTime) if self.activeTime is not None else None
		
		# reset types
		reset = self.resetResultTypes()  # reset result types
		if not reset:
			return False
		timesteps, minResultTypes, maxResultTypes, temporalResultTypes = [], [], [], []
		pointTypesTS, lineTypesTS, regionTypesTS, lineTypesLP, crossSectionTypes = [], [], [], [], []
		for result in openResults.selectedItems():
			# Populate metadata lists
			ts, minResTypes, maxResTypes, tResTypes, pTypesTS, lTypesTS, rTypesTS, lTypesLP, csTypes = self.getDataFromResultsDict(result.text())

			# Join already open result types with new types
			timesteps = self.joinResultTypes(timesteps, ts, type='time')
			minResultTypes = self.joinResultTypes(minResultTypes, minResTypes)
			maxResultTypes = self.joinResultTypes(maxResultTypes, maxResTypes)
			temporalResultTypes = self.joinResultTypes(temporalResultTypes, tResTypes)
			pointTypesTS = self.joinResultTypes(pointTypesTS, pTypesTS)
			lineTypesTS = self.joinResultTypes(lineTypesTS, lTypesTS)
			regionTypesTS = self.joinResultTypes(regionTypesTS, rTypesTS)
			lineTypesLP = self.joinResultTypes(lineTypesLP, lTypesLP)
			crossSectionTypes = self.joinResultTypes(crossSectionTypes, csTypes)

		# Populate tuview interface
		mapOutputs = []
		if openResults.selectedItems():
			result = openResults.selectedItems()[0]  # just take the first selection
			for rtype in temporalResultTypes:
				if rtype not in self.results[result.text()].keys():
					# find the selected result that has it
					for result in openResults.selectedItems():
						if rtype in self.results[result.text()].keys():
							break
				t = self.results[result.text()][rtype]
				for i, (time, values) in enumerate(t['times'].items()):
					if i == 0:  # get the data type from the first timestep i.e. scalar or vector
						info = (rtype, values[1], rtype in maxResultTypes, rtype in minResultTypes)
						mapOutputs.append(info)
					else:
						break
				self.tuView.tuPlot.tuPlotToolbar.addItemToPlotOptions(rtype)

				#mcboResultType.addItem(type)
			for rtype in maxResultTypes:  # check - there may be results that only have maximums
				if rtype not in temporalResultTypes:
					mrtype = self.findMaxResultType(result.text(), rtype)
					if not mrtype:
						# find the selected result that has it
						for result in openResults.selectedItems():
							mrtype = self.findMaxResultType(result.text(), rtype)
							if mrtype:
								break
					if not mrtype:  # couldn't be found - hopefully not the case!
						continue
					t = self.results[result.text()][mrtype]
					for i, (time, values) in enumerate(t['times'].items()):
						if i == 0:  # get the data type from the first timestep i.e. scalar or vector
							info = (rtype, values[1], True, False)
							mapOutputs.append(info)
						else:
							break
		if not mapOutputs:
			mapOutputs = [("None", 3, False)]
			
		timeSeries = []
		timeSeries = timeSeries + pointTypesTS + lineTypesTS + regionTypesTS + lineTypesLP + crossSectionTypes
		if not timeSeries:
			timeSeries = [("None", 3, False, False)]
		openResultTypes.setModel(DataSetModel(mapOutputs, timeSeries))
		openResultTypes.expandAll()
		
		# timesteps
		connected = True
		try:
			self.tuView.cboTime.currentIndexChanged.disconnect(self.tuView.timeSliderChanged)
		except:
			# if dock is closed cboTime will already be disconnected
			# record this fact so we don't connect it back up after this
			# function when we don't want to
			connected = False
		cboTime.clear()
		self.cboTime2timekey.clear()
		if timesteps:
			if not self.tuView.tuOptions.xAxisDates:  # use Time (hrs)
				unit = self.tuView.tuOptions.timeUnits
				if (unit == 'h' and timesteps[-1] < 100) or (unit == 's' and timesteps[-1] / 3600 < 100):
					#cboTime.addItems([convertTimeToFormattedTime(x, unit=unit) for x in timesteps])
					for x in timesteps:
						timeformatted = convertTimeToFormattedTime(x, unit=unit)
						cboTime.addItem(timeformatted)
						self.cboTime2timekey[timeformatted] = '{0:.6f}'.format(x)
				else:
					#cboTime.addItems([convertTimeToFormattedTime(x, hour_padding=3, unit=unit) for x in timesteps])
					for x in timesteps:
						timeformatted = convertTimeToFormattedTime(x, unit=unit, hour_padding=3)
						cboTime.addItem(timeformatted)
						self.cboTime2timekey[timeformatted] = '{0:.6f}'.format(x)
			else:  # use datetime format
				cboTime.addItems([self._dateFormat.format(self.time2date[x]) for x in timesteps])
			sliderTime.setMaximum(len(timesteps) - 1)  # slider
		if connected:
			self.tuView.cboTime.currentIndexChanged.connect(self.tuView.timeSliderChanged)
		
		# Apply selection
		self.applyPreviousResultTypeSelections(currentPlotData, currentTime)
		
		# Update viewport with enabled / disabled items
		# self.tuView.currentLayerChanged()
		self.tuView.setTsTypesEnabled()
		
		return True
	
	def updateActiveResultTypes(self, resultIndex, geomType=None, skip_already_selected=False):
		"""
		Updates the active results based on the selected result types in DataSetView

		:param resultIndex: QModelIndex
		:return: bool -> True for successful, False for unsuccessful
		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot
		openResultTypes = self.tuView.OpenResultTypes
		
		# if geomtype then change the TS result options
		if geomType is not None:
			if geomType == QgsWkbTypes.PointGeometry:
				self.tuResults1D.typesTS = self.tuResults1D.pointTS[:]
				self.tuResults1D.typesXS = self.tuResults1D.lineXS[:]
			elif geomType == QgsWkbTypes.LineGeometry:
				self.tuResults1D.typesTS = self.tuResults1D.lineTS[:] + self.tuResults1D.pointTS[:]
				self.tuResults1D.typesXS = self.tuResults1D.lineXS[:]
			elif geomType == QgsWkbTypes.PolygonGeometry:
				self.tuResults1D.typesTS = self.tuResults1D.regionTS[:]
				self.tuResults1D.typesXS = self.tuResults1D.lineXS[:]
			else:
				self.tuResults1D.typesTS = []
				
			return True
				
		
		# if not a map output item there is no need to rerender the map
		layer = self.tuResults2D.activeMeshLayers[0] if self.tuResults2D.activeMeshLayers else None
		skip = False
		if resultIndex is None or resultIndex.internalPointer() is None or \
				resultIndex.internalPointer().ds_name == 'None' or \
				resultIndex.internalPointer().parentItem == openResultTypes.model().rootItem:  # don't need to update active result lists
			pass
		else:
			# check if clicked result type is a map output or a time series
			item = resultIndex.internalPointer()
			parent = item.parentItem
			if parent.ds_name != 'Map Outputs':
				skip = True  # click occured on a time series result not map output
			
			# update active result type lists - start by figuring out what type it is and add to specific lists
			if item not in self.activeResultsItems:
				if item.ds_type == 1:  # scalar
					self.tuResults2D.activeScalar = item.ds_name
				elif item.ds_type == 2:  # vector
					self.tuResults2D.activeVector = item.ds_name
				#elif item.ds_type == 4 or item.ds_type == 5 or item.ds_type == 6 or item.ds_type == 7:  # 1d result
				elif item.ds_type in TuResults.Results1D:  # 1d result
					self.tuResults1D.items1d.append(item)
					#if item.ds_type == 4 or item.ds_type == 5 or item.ds_type == 6:  # time series
					if item.ds_type == 4:  # point
						if item.ds_name not in self.tuResults1D.pointTS:
							self.tuResults1D.pointTS.append(item.ds_name)
					elif item.ds_type == 5:  # line
						if item.ds_name not in self.tuResults1D.lineTS:
							self.tuResults1D.lineTS.append(item.ds_name)
					elif item.ds_type == 6:
						if item.ds_name not in self.tuResults1D.regionTS:
							self.tuResults1D.regionTS.append(item.ds_name)
					elif item.ds_type == 7:  # long plot
						if item.ds_name not in self.tuResults1D.typesLP:
							self.tuResults1D.typesLP.append(item.ds_name)
					elif item.ds_type == 8:  # XS
						if item.ds_name not in self.tuResults1D.typesXS:
							self.tuResults1D.lineXS.append(item.ds_name)
					if self.tuResults1D.activeType == 0:
						self.tuResults1D.typesTS = self.tuResults1D.pointTS[:]
						self.tuResults1D.typesXSRes = self.tuResults1D.pointTS[:]
					elif self.tuResults1D.activeType == 1:
						self.tuResults1D.typesTS = self.tuResults1D.lineTS[:] + self.tuResults1D.pointTS[:]
						self.tuResults1D.typesXS = self.tuResults1D.lineXS[:]
						self.tuResults1D.typesXSRes = self.tuResults1D.pointTS[:]
					elif self.tuResults1D.activeType == 2:
						self.tuResults1D.typesTS = self.tuResults1D.regionTS[:]
						self.tuResults1D.typesXSRes = self.tuResults1D.pointTS[:]
					# elif self.tuResults1D.activeType == 3:
					# 	self.tuResults1D.typesXS = self.tuResults1D.lineXS[:]
					# 	self.tuResults1D.typesXSRes = self.tuResults1D.pointTS[:]
					#else:
					#	self.tuResults1D.typesTS = []
					#elif item.ds_type == 7:  # long plot
					#	self.tuResults1D.typesLP.append(item.ds_name)
				# if result type is vector or scalar, need to remove previous vector or scalar results
				if item.ds_type == 1 or item.ds_type == 2:
					for i, result in enumerate(self.activeResults):
						if item.ds_type == self.activeResultsTypes[i]:
							self.activeResults.pop(i)
							self.activeResultsTypes.pop(i)
							if self.activeResultsIndexes:
								self.activeResultsIndexes.pop(i)
								self.activeResultsItems.pop(i)
							break  # there will only be one to remove
				# finally add clicked result type to generic active lists - applicable regardless of result type
				nameAppend = ''
				if item.ds_type == 4 or item.ds_type == 5 or item.ds_type == 6:
					nameAppend = '_TS'
				elif item.ds_type == 7:
					nameAppend = '_LP'
				elif item.ds_type == 8:
					nameAppend = '_CS'
				self.activeResults.append(item.ds_name + nameAppend)
				self.activeResultsTypes.append(item.ds_type)
				self.activeResultsIndexes.append(resultIndex)
				self.activeResultsItems.append(item)
			elif not skip_already_selected:  # already in lists so click is a deselect and types need to be removed from lists
				# remove 2D from lists
				i = self.activeResultsItems.index(item)
				self.activeResults.pop(i)
				self.activeResultsTypes.pop(i)
				self.activeResultsIndexes.pop(i)
				self.activeResultsItems.pop(i)
				if item.ds_type == 1:
					self.tuResults2D.activeScalar = None
				elif item.ds_type == 2:
					self.tuResults2D.activeVector = None
				# remove 1D from lists
				if item in self.tuResults1D.items1d:
					self.tuResults1D.items1d.remove(item)
				if item.ds_name in self.tuResults1D.typesTS:
					self.tuResults1D.typesTS.remove(item.ds_name)
				elif item.ds_name in self.tuResults1D.typesLP:
					self.tuResults1D.typesLP.remove(item.ds_name)
				elif item.ds_name in self.tuResults1D.typesXS:
					self.tuResults1D.typesXS.remove(item.ds_name)
				if item.ds_name in self.tuResults1D.pointTS:
					self.tuResults1D.pointTS.remove(item.ds_name)
					if item.ds_name in self.tuResults1D.typesXSRes:
						self.tuResults1D.typesXSRes.remove(item.ds_name)
				elif item.ds_name in self.tuResults1D.lineTS:
					self.tuResults1D.lineTS.remove(item.ds_name)
				elif item.ds_name in self.tuResults1D.regionTS:
					self.tuResults1D.regionTS.remove(item.ds_name)
				elif item.ds_name in self.tuResults1D.lineXS:
					self.tuResults1D.lineXS.remove(item.ds_name)

		if not skip:
			# rerender map
			if layer is not None:
				# rs = layer.rendererSettings()
				# # if no scalar or vector turn off dataset
				# if self.tuResults2D.activeScalar is None:
				# 	rs.setActiveScalarDataset(QgsMeshDatasetIndex(-1, -1))
				# 	layer.setRendererSettings(rs)
				# if self.tuResults2D.activeVector is None:
				# 	rs.setActiveVectorDataset(QgsMeshDatasetIndex(-1, -1))
				# 	layer.setRendererSettings(rs)
				self.tuView.renderMap()

				# update default item in the depth averaging methods
				self.tuView.tuPlot.tuPlotToolbar.averageMethodTSMenu.updateDefaultItem(self.tuResults2D.activeScalar)
		else:
			# redraw plot
			if item.ds_type == 4 or item.ds_type == 5 or item.ds_type == 6:
				self.tuView.tuPlot.updateCurrentPlot(TuPlot.TimeSeries)
				if self.tuResults1D.typesXS:
					self.tuView.tuPlot.updateCurrentPlot(TuPlot.CrossSection)
			elif item.ds_type == 7:
				self.tuView.tuPlot.updateCurrentPlot(TuPlot.CrossSection)
			elif item.ds_type == 8:
				self.tuView.tuPlot.updateCurrentPlot(TuPlot.CrossSection)
			else:
				self.tuView.tuPlot.updateCurrentPlot(self.tuView.tabWidget.currentIndex(), update='1d only')

				
		return True
	
	def updateSecondaryAxisTypes(self, clickedItem):
		"""
		Updates the list of result types to be plotted on the secondary axis.
		
		:param clickedItem: dict -> { 'parent': DataSetTreeNode, 'index': DataSetTreeNode }
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		openResultTypes = self.tuView.OpenResultTypes
		
		if clickedItem is not None:
			openResultTypes.model().setActiveSecondaryIndex(clickedItem['parent'], clickedItem['index'])
		
		self.secondaryAxisTypes = []
		for i in range(openResultTypes.model().mapOutputsItem.childCount()):
			item = openResultTypes.model().dsindex2item[i]
			if item.enabled:
				if item.secondaryActive:
					self.secondaryAxisTypes.append(item.ds_name)
		
		for item in openResultTypes.model().timeSeriesItem.children():
			if item.enabled:
				if item.secondaryActive:
					if item.ds_type == 8:
						self.secondaryAxisTypes.append('{0}_CS'.format(item.ds_name))
					else:
						self.secondaryAxisTypes.append('{0}_1d'.format(item.ds_name))
					
		if self.tuView.tuPlot.tuPlotToolbar.fluxSecAxisButton.isChecked():
			self.secondaryAxisTypes.append('2D Flow')
					
		return True
		
	def updateMinMaxTypes(self, clickedItem, mtype):
		"""
		Updates the list of result types that should plot max.
		
		:param clickedItem: dict -> { 'parent': DataSetTreeNode, 'index': DataSetTreeNode }
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		openResultTypes = self.tuView.OpenResultTypes
		
		if clickedItem is not None:
			if mtype == 'max':
				openResultTypes.model().setActiveMax(clickedItem['parent'], clickedItem['index'])
			elif  mtype == 'min':
				openResultTypes.model().setActiveMin(clickedItem['parent'], clickedItem['index'])
		
		self.maxResultTypes = []
		for item in openResultTypes.model().mapOutputsItem.children():
			if item.enabled:
				if item.isMax:
					self.maxResultTypes.append(item.ds_name)
		self.minResultTypes = []
		for item in openResultTypes.model().mapOutputsItem.children():
			if item.enabled:
				if item.isMin:
					self.minResultTypes.append(item.ds_name)

		for item in openResultTypes.model().timeSeriesItem.children():
			if item.enabled:
				if item.isMax:
					self.maxResultTypes.append('{0}_1d'.format(item.ds_name))
				if item.isMin:
					self.minResultTypes.append('{0}_1d'.format(item.ds_name))

		return True

	def getResult(self, index, **kwargs):
		"""
		Gets data from the indexed results.

		:param index: TuResultsIndex
		:return: tuple -> result metadata
		"""

		# get version
		qv = Qgis.QGIS_VERSION_INT

		forceGetTime = kwargs['force_get_time'] if 'force_get_time' in kwargs.keys() else None
		meshIndexOnly = kwargs['mesh_index_only'] if 'mesh_index_only' in kwargs else False
		results = self.tuView.tuResults.results  # dict

		if index is None:
			if qv < 31300:
				return QgsMeshDatasetIndex(-1, -1)
			else:
				return -1
		
		key1 = index.result if 'result_name' not in kwargs else kwargs['result_name']
		key2 = index.resultType if 'result_type' not in kwargs else kwargs['result_type']
		key3 = index.timestep if 'timestep' not in kwargs else kwargs['timestep']
		
		if key1 not in results.keys():
			if qv < 31300:
				return QgsMeshDatasetIndex(-1, -1)
			else:
				return -1
		
		if key2 not in results[key1].keys():
			if qv < 31300:
				return QgsMeshDatasetIndex(-1, -1)
			else:
				return -1
		
		if key3 is not None:
			if key3 not in results[key1][key2]['times'].keys():
				if len(results[key1][key2]['times']) == 1:
					for k in results[key1][key2]['times']:
						key3 = k
				elif forceGetTime == 'next lower':
					key3 = self.findTimeNextLower(key1, key2, key3)
		
		if key3 is not None:
			res = results[key1][key2]['times'][key3]
			if qv < 31300:
				if meshIndexOnly:
					if res and type(res) is tuple:
						return res[-1]
					else:
						return QgsMeshDatasetIndex(-1, -1)
				else:
					return results[key1][key2]['times'][key3]
			else:
				if meshIndexOnly:
					if res and type(res) is tuple:
						return res[-1].group()
					else:
						return -1
				else:
					return res
		else:
			if meshIndexOnly:
				if qv < 31300:
					return QgsMeshDatasetIndex(-1, -1)
				else:
					return -1
			else:
				return results[key1][key2]['times']

	def is3d(self, index, **kwargs):
		"""

		"""

		results = self.tuView.tuResults.results  # dict
		key1 = index.result if 'result_name' not in kwargs else kwargs['result_name']
		key2 = index.resultType if 'result_type' not in kwargs else kwargs['result_type']

		if key1 not in results.keys():
			return False
		if key2 not in results[key1].keys():
			return False

		return results[key1][key2]['is3dDataset']

	def getTimeUnit(self, index, **kwargs):
		"""

		"""

		results = self.tuView.tuResults.results  # dict
		key1 = index.result if 'result_name' not in kwargs else kwargs['result_name']
		key2 = index.resultType if 'result_type' not in kwargs else kwargs['result_type']

		if key1 not in results.keys():
			return 'h'
		if key2 not in results[key1].keys():
			return 'h'

		return results[key1][key2]['timeUnit']
	
	def findTimeNextLower(self, key1, key2, key3):
		"""
		Finds the previous available 2D timestep.

		:param key1: str -> result name e.g. M01_5m_001
		:param key2: str -> result type e.g. 'depth'
		:param key3: str -> time e.g. '1.0000'
		:return: str -> next lower time
		"""
		
		timePrev = None
		higher = False
		for i, (timekey, time) in enumerate(self.results[key1][key2]['times'].items()):
			# timekey -> str e.g. '1.0000'
			# time -> dict e.g. ( timestep, type, QgsMeshDatasetIndex )}
			
			if i == 0:
				# if first time step is not lower than requested then return None because there is no next lower
				if time[0] < float(key3):
					timePrev = timekey
				else:
					return None
			else:
				if time[0] > float(key3):
					higher = True  # found point where overlap occurs
				else:
					timePrev = timekey
			if higher:
				return timePrev
		
		# return time prev if higher is never found
		return timePrev

	def findTimeNext(self, key1, key2, key3, times=(), is_date=False):
		"""
		Finds the next available time after specified time
		"""

		if is_date:
			if type(key3) is str:
				rt = datetime.strptime(key3, self.dateFormat)
			else:
				rt = key3
		else:
			if type(key3) is str:
				rt = float(key3)
			else:
				rt = key3

		if not times:
			times = [y for x, y in self.results[key1][key2]['times'].items()]

		assert(len(times) > 0)
		for time in times:
			if time >= rt:
				return time

		return time

	def isMax(self, typ):
		"""
		Returns whether the result type is max or not. Can put 'scalar' or 'vector' to auto get active scalar or vector.

		:param type: str
		:return: bool -> True for max, False for not max
		"""
		
		maxResultTypes = self.tuView.tuResults.maxResultTypes  # list -> str
		
		if typ == 'scalar':
			return True if self.tuResults2D.activeScalar in maxResultTypes else False
		elif typ == 'vector':
			return True if self.tuResults2D.activeVector in maxResultTypes else False
		else:
			return True if typ in maxResultTypes else False

	def isMin(self, typ):
		"""
		Returns whether the result type is max or not. Can put 'scalar' or 'vector' to auto get active scalar or vector.

		:param type: str
		:return: bool -> True for max, False for not max
		"""

		minResultTypes = self.tuView.tuResults.minResultTypes  # list -> str

		if typ == 'scalar':
			return True if self.tuResults2D.activeScalar in minResultTypes else False
		elif typ == 'vector':
			return True if self.tuResults2D.activeVector in minResultTypes else False
		else:
			return True if typ in minResultTypes else False
	
	def removeResults(self, resList):
		"""
		Removes the results from the indexed results and ui.

		:param resList: list -> str result name e.g. M01_5m_001
		:return: bool -> True for successful, False for unsuccessful
		"""

		results = self.tuView.tuResults.results
		results2d = self.tuView.tuResults.tuResults2D.results2d
		results1d = self.tuView.tuResults.tuResults1D.results1d
		resultsParticles = self.tuView.tuResults.tuResultsParticles.resultsParticles

		for res in resList:
			if res in results.keys():
				# remove from indexed results
				del results[res]
				if res in results2d:
					del results2d[res]
				if res in results1d:
					del results1d[res]
				if res in resultsParticles:
					del resultsParticles[res]

				#layer = tuflowqgis_find_layer(res)
				#self.tuView.project.removeMapLayer(layer)
				#self.tuView.canvas.refresh()
				
			# remove from ui
			for i in range(self.tuView.OpenResults.count()):
				item = self.tuView.OpenResults.item(i)
				if item is not None and item.text() == res:
					if res not in results:
						self.tuView.OpenResults.takeItem(i)
		
		return True
	
	def updateActiveResults(self):
		"""
		Updates the list of selected 2D results.

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.activeMeshLayers = []
		openResults = self.tuView.OpenResults  # QListWidget
		
		for r in range(openResults.count()):
			item = openResults.item(r)
			
			# find selected layer
			layer = tuflowqgis_find_layer(item.text())
			if layer is not None:
				if layer.type() == 3:
					if item.isSelected():
						self.activeMeshLayers.append(layer)
					else:
						rs = layer.rendererSettings()
						rs.setActiveScalarDataset(QgsMeshDatasetIndex(-1, -1))
						layer.setRendererSettings(rs)
						rs.setActiveVectorDataset(QgsMeshDatasetIndex(-1, -1))
						layer.setRendererSettings(rs)
		
		return True

	def updateTimeUnits(self):
		# turn off x axis freezing on time series plot
		self.tuView.tuPlot.tuPlotToolbar.viewToolbarTimeSeries.freezeXAxisAction.setChecked(False)
		self.tuView.tuPlot.tuPlotToolbar.viewToolbarTimeSeries.freezeXYAxisAction.setChecked(False)

		meshLayers = findAllMeshLyrs()
		for ml in meshLayers:
			layer = tuflowqgis_find_layer(ml)
			self.tuResults2D.getResultMetaData(ml, layer)
		self.updateResultTypes()
	
	def checkSelectedResults(self):
		"""
		Checks the selected results match active result types.
		
		:return:
		"""
		
		openResultTypes = self.tuView.OpenResultTypes
		selectedIndexes = sorted(openResultTypes.selectedIndexes())
		
		if selectedIndexes != sorted(self.activeResultsIndexes[:]):
			# Reset active results so it matches selection
			self.tuResults2D.activeScalar = None
			self.tuResults2D.activeVector = None
			self.activeResults.clear()  # str result type names
			self.activeResultsTypes.clear()  # int result types (e.g. 1 - scalar, 2 - vector...)
			self.activeResultsIndexes.clear()  # QModelIndex
			self.activeResultsItems.clear()  # DataSetTreeNode
			self.tuResults1D.items1d.clear()  # list -> Dataset_View Tree node selected dataset view tree node item
			self.tuResults1D.typesTS.clear()  # list -> str selected 1D time series result types
			self.tuResults1D.pointTS.clear()
			self.tuResults1D.lineTS.clear()
			self.tuResults1D.regionTS.clear()
			self.tuResults1D.typesLP.clear()  # list -> str selected 1D long plot result types
			self.tuResults1D.typesXS.clear()
			for index in selectedIndexes:
				item = index.internalPointer()
				if item.ds_type == 1:  # scalar
					self.tuResults2D.activeScalar = item.ds_name
				elif item.ds_type == 2:  # vector
					self.tuResults2D.activeVector = item.ds_name
				# elif item.ds_type == 4 or item.ds_type == 5 or item.ds_type == 6 or item.ds_type == 7:  # 1d result
				elif item.ds_type in TuResults.Results1D:  # 1d result
					self.tuResults1D.items1d.append(item)
					if item.ds_type == 4 or item.ds_type == 5 or item.ds_type == 6:  # time series
						if item.ds_type == 4:  # point
							self.tuResults1D.pointTS.append(item.ds_name)
						elif item.ds_type == 5:  # line
							self.tuResults1D.lineTS.append(item.ds_name)
						elif item.ds_type == 6:
							self.tuResults1D.regionTS.append(item.ds_name)
						if self.tuResults1D.activeType == 0:
							self.tuResults1D.typesTS = self.tuResults1D.pointTS[:]
						elif self.tuResults1D.activeType == 1:
							self.tuResults1D.typesTS = self.tuResults1D.lineTS[:] + self.tuResults1D.pointTS[:]
						elif self.tuResults1D.activeType == 2:
							self.tuResults1D.typesTS = self.tuResults1D.regionTS[:]
						else:
							self.tuResults1D.typesTS = []
					elif item.ds_type == 7:  # long plot
						self.tuResults1D.typesLP.append(item.ds_name)
					elif item.ds_type == 8:  # cross section
						self.tuResults1D.typesXS = self.tuResults1D.lineTS[:]
						self.tuResults1D.activeType = 3

	def findMaxResultType(self, result: str, resultType: str) -> str:
		"""
		Find maximum result type in results.
		Used when only maximum result type exists (no temporal results)
		
		It is assumed that there is no temporal output for result type.
		
		:param result: str result name e.g. 'M03_5m_001'
		:param resultType: str result type e.g. 'depth'
		:return: str max result type e.g. 'depth/Maximums'
		"""
		
		for rtype in self.results[result]:
			if TuResults.isMaximumResultType(rtype):
				if TuResults.stripMaximumName(rtype) == resultType:
					return rtype
				
		return ''

	@staticmethod
	def stripMaximumName(resultType: str) -> str:
		"""
		Strips the maximum identifier from the name.

		e.g. 'depth/Maximum' will return 'depth'

		:param resultType: str
		:return: str
		"""

		rtype = resultType.split('/')[0]
		if 'max_' in rtype and 'time' not in rtype:
			rtype = rtype.split('max_')[1]

		return rtype

	@staticmethod
	def stripMinimumName(resultType: str) -> str:
		"""
		Strips the minimum identifier from the name.

		e.g. 'depth/Maximum' will return 'depth'

		:param resultType: str
		:return: str
		"""

		rtype = resultType.split('/')[0]
		if 'min_' in rtype and 'time' not in rtype:
			rtype = rtype.split('min_')[1]

		return rtype

	@staticmethod
	def isMaximumResultType(resultType: str,
	                        dp: QgsMeshDataProvider = QgsMeshLayer().dataProvider(),
	                        groupIndex: int = -1) -> bool:
		"""
		Determines if the result type is a maximum or not.
		
		e.g. Depth/Maximums will return True
		
		:param resultType: str
		:param dp: QgsMeshDataProvider
		:param groupIndex: int
		:return: bool
		"""
		
		if '/Maximums' in resultType or ('max_' in resultType and 'time' not in resultType):
			return True
		
		if '/Final' in resultType:
			return True
		
		# special case for 'Minimum dt'
		# this is recorded as 'Final/Minimum dt' in xmdf - MDAL does not retain folder name
		# will treat this as 'max'
		# if only only one timestep, then this is the final / max value
		if 'minimum dt' in resultType.lower():
			if dp is not None:
				if dp.isValid():
					if dp.datasetCount(groupIndex) == 1:
						return True
		
		return False

	@staticmethod
	def isMinimumResultType(resultType: str,
	                        dp: QgsMeshDataProvider = QgsMeshLayer().dataProvider(),
	                        groupIndex: int = -1) -> bool:
		"""
		Determines if the result type is a minimum or not.

		e.g. Depth/Minimums will return True

		:param resultType: str
		:param dp: QgsMeshDataProvider
		:param groupIndex: int
		:return: bool
		"""

		if '/Minimums' in resultType or ('min_' in resultType and 'time' not in resultType):
			return True

		return False

	@staticmethod
	def isStatic(resultType: str,
                dp: QgsMeshDataProvider = QgsMeshLayer().dataProvider(),
                groupIndex: int = -1) -> bool:
		"""
        Determines if the result type is a static or not

        e.g. bed elevation

        :param resultType: str
        :param dp: QgsMeshDataProvider
        :param groupIndex: int
        :return: bool
        """

		if TuResults.isMaximumResultType(resultType, dp, groupIndex) \
				or TuResults.isMinimumResultType(resultType, dp, groupIndex):
			return True

		if dp is not None:
			if dp.isValid():
				if dp.datasetCount(groupIndex) == 1:
					return True

		return False

	@staticmethod
	def isTemporal(resultType: str,
	               dp: QgsMeshDataProvider = QgsMeshLayer().dataProvider(),
	               groupIndex: int = -1) -> bool:
		"""
        Determines if the result type is a static or not

        e.g. bed elevation

        :param resultType: str
        :param dp: QgsMeshDataProvider
        :param groupIndex: int
        :return: bool
        """

		return not TuResults.isStatic(resultType, dp, groupIndex)
	
	def updateDateTimes(self):
		"""
		Updates date2time dictionary and time2date dictionary
		
		:return: None
		"""

		self.date2timekey.clear()
		self.date2time.clear()
		self.timekey2date.clear()
		
		zeroDate = self.tuView.tuOptions.zeroTime
		for t in self.time2date:
			if t == '-99999' or t == -99999:
				self.time2date[t] = -99999
				self.timekey2date[t] = -99999
				self.date2time[-99999] = t
				self.date2timekey[-99999] = t
			else:
				if self.tuView.tuOptions.timeUnits == 's':
					date = zeroDate + timedelta(seconds=t)
				else:
					date = zeroDate + timedelta(hours=t)
				
				# format date to 2 decimal places i.e. dd/mm/yyyy hh:mm:ss.ms
				date = roundSeconds(date)
				
				self.time2date[t] = date
				self.timekey2date['{0:.6f}'.format(t)] = date
				self.date2time[date] = t
				self.date2timekey[date] = '{0:.6f}'.format(t)
			
		self.tuView.cboTime.clear()
		timeCopy = [x for x in self.time2date.keys()]
		if '-99999' in timeCopy:
			timeCopy.remove('-99999')
		if -99999 in timeCopy:
			timeCopy.remove(-99999)

		self.tuView.cboTime.addItems([self._dateFormat.format(self.time2date[x]) for x in timeCopy])

	def updateQgsTime(self, time=None, qgsObject=None, timeSpec=None):
		"""

		"""

		qv = Qgis.QGIS_VERSION_INT

		if time is None:
			time = float(self.activeTime)
		if qgsObject is None:
			qgsObject = self.iface.mapCanvas()
		if timeSpec is None:
			timeSpec = self.iface.mapCanvas().temporalRange().begin().timeSpec()

		if qv >= 31300:
			zt = self.tuView.tuOptions.zeroTime
			rt = dt2qdt(zt, self.iface.mapCanvas().temporalRange().begin().timeSpec())
			rt = rt.toTimeSpec(timeSpec)
			# rt = QDateTime(QDate(zt.year, zt.month, zt.day),
			#                QTime(zt.hour, zt.minute, zt.second, zt.microsecond / 1000.))
			# rt.setTimeSpec(self.iface.mapCanvas().temporalRange().begin().timeSpec())
			begin = rt.addSecs(time * 60. * 60 - 1)
			end = begin.addSecs(60.*60.)
			dtr = QgsDateTimeRange(begin, end)


			#self.iface.mapCanvas().setTemporalRange(dtr)
			#self.iface.mapCanvas().refresh()
			qgsObject.setTemporalRange(dtr)
			qgsObject.refresh()

	def getTuViewTimeFromQgsTime(self):
		"""

		"""

		qv = Qgis.QGIS_VERSION_INT

		if qv >= 31300:
			qdt = self.iface.mapCanvas().temporalRange().begin()  # QDateTime
			if not qdt.isValid():
				return float(self.activeTime)
			else:
				modelDates = sorted([x for x in self.date2time.keys()])
				if modelDates:
					# fdt = modelDates[0]  # first datetime
					# ldt = modelDates[-1]  # last datetime
					# modelBegin = QDateTime(QDate(fdt.year, fdt.month, fdt.day),
					#                        QTime(fdt.hour, fdt.minute, fdt.second, fdt.microsecond / 1000.))
					# modelBegin.setTimeSpec(self.iface.mapCanvas().temporalRange().begin().timeSpec())
					# modelEnd = QDateTime(QDate(ldt.year, ldt.month, ldt.day),
					#                      QTime(ldt.hour, ldt.minute, ldt.second, ldt.microsecond / 1000.))
					# modelEnd.setTimeSpec(self.iface.mapCanvas().temporalRange().begin().timeSpec())
					# modelRange = QgsDateTimeRange(modelBegin, modelEnd)
					# qdt = self.iface.mapCanvas().temporalRange().begin()  # QDateTime
					pdt = datetime(qdt.date().year(), qdt.date().month(), qdt.date().day(),     # python datetime
					               qdt.time().hour(), qdt.time().minute(), qdt.time().second(),
					               int(round(qdt.time().msec(), -1) * 1000.))
					# qgsEnd = self.iface.mapCanvas().temopralRange().end()

					return self.findTimeNext(None, None, pdt, modelDates, True)
				else:
					return 0

	def addCrossSectionLayerToResults(self, lyr):
		"""

		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		updateOpenResults = False
		if lyr.name() not in self.results:
			self.results[lyr.name()] = {}
			updateOpenResults = True
		if 'line_cs' not in self.results[lyr.name()]:
			self.results[lyr.name()]['line_cs'] = {}

		for t in XS.getAllTypes(lyr):
			self.results[lyr.name()]['line_cs'][t] = XS.getAllSourcesForType(lyr, t)

		if updateOpenResults:
			self.updateOpenResults(lyr.name())
		else:
			self.tuView.tuPlot.updateCurrentPlot(TuPlot.CrossSection, plot='1d only')

	def add1dHydTableToResults(self, displayName, table):
		"""

		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		if displayName not in self.results:
			self.results[displayName] = {}
		if 'line_cs' not in self.results[displayName]:
			self.results[displayName]['line_cs'] = {}

		for t in sorted(table.getAllTypes()):
			self.results[displayName]['line_cs'][t] = table.getAllIdsForType(t)

		self.updateOpenResults(displayName)

	def remove1dHydTable(self, displayName):
		"""

		"""

		if displayName in self.results:
			del self.results[displayName]

		self.updateOpenResults(displayName)

	@staticmethod
	def isMapOutputType(resultType):
		"""Returns true if resultType is a Map Output"""

		a = [True for x in TuResults.OtherTypes if x in resultType]
		return len(a) == 0

	def updateTemporalProperties(self):
		for res, val in self.results.items():
			for restype in val:
				if TuResults.isMapOutputType(restype):
					layer = tuflowqgis_find_layer(res)
					layer.setReferenceTime(dt2qdt(self.tuResults2D.getReferenceTime(layer),
				                                  self.iface.mapCanvas().temporalRange().begin().timeSpec()))
					break
		self.timeSpec = self.iface.mapCanvas().temporalRange().begin().timeSpec()
		self.updateQgsTime()





