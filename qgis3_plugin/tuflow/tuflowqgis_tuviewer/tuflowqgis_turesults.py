from datetime import datetime, timedelta
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets import *
import tuflowqgis_turesults1d
import tuflowqgis_turesults2d
from tuflow.dataset_view import DataSetModel
from tuflow.tuflowqgis_library import tuflowqgis_find_layer


class TuResults():
	"""
	Parent class for handling 1D and 2D results classes.
	
	"""
	
	def __init__(self, TuView):
		self.tuView = TuView
		self.results = {}  # dict - e.g. { M01_5m_001: { depth: { '0.0000': ( timestep, type, QgsMeshDatasetIndex )}, point_ts: ( types, timesteps ) } }
		self.timekey2time = {}  # e.g. {'1.8333': 1.8333333}
		self.timekey2date = {}  # e.g. {'1.8333': '01/01/2000 09:00:00'}
		self.time2date = {}
		self.date2timekey = {}
		self.date2time = {}
		self.secondaryAxisTypes = []
		self.maxResultTypes = []
		self.activeTime = None  # active time for rendering
		self.activeResults = []  # str result type names
		self.activeResultsTypes = []  # int result types (e.g. 1 - scalar, 2 - vector...)
		self.activeResultsIndexes = []  # QModelIndex
		self.activeResultsItems = []  # DataSetTreeNode
		self.dateFormat = '%d/%m/%Y %H:%M:%S'  # for time combobox not plotting
		self._dateFormat = '{0:%d}/{0:%m}/{0:%Y} {0:%H}:{0:%M}:{0:%S}'  # for time combobox not plotting
		
		# 1D results
		self.tuResults1D = tuflowqgis_turesults1d.TuResults1D(TuView)
		
		# 2D results
		self.tuResults2D = tuflowqgis_turesults2d.TuResults2D(TuView)
	
	def importResults(self, type, inFileNames):
		"""
		Import results 1D or 2D
		
		:param type: str -> 'mesh' or 'timeseries'
		:param inFileNames: list -> str file path
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		result = False
		if type.lower() == 'mesh':
			result = self.tuResults2D.importResults(inFileNames)
		elif type.lower() == 'timeseries':
			result = self.tuResults1D.importResults(inFileNames)
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
				self.activeTime = self.activeTime.split(':')
				self.activeTime = float(self.activeTime[0]) + (float(self.activeTime[1]) / 60.) + (
						float(self.activeTime[2]) / 3600.)
				self.activeTime = '{0:.4f}'.format(self.activeTime)
			else:
				self.activeTime = datetime.strptime(self.activeTime, self.dateFormat)
				self.activeTime = self.date2timekey[self.activeTime]
	
	def resetResultTypes(self):
		"""
		Resets the result types in the tree widget

		:return: bool -> True for succssful, False for unsuccessful
		"""
		
		# Remove all children of Map Outputs and time series
		self.tuView.initialiseDataSetView()
		
		# Reset multi combobox to empty
		#self.tuView.mcboResultType.clear()
		self.tuView.tuPlot.tuPlotToolbar.plotTSMenu.clear()
		self.tuView.tuPlot.tuPlotToolbar.plotLPMenu.clear()
		
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
		
		timesteps, maxResultTypes, temporalResultTypes, pTypeTS, lTypeTS, rTypeTS, lTypeLP = [], [], [], [], [], [], []
		timestepsTS = []
		timestepsLP = []

		r = self.results[resultName]
		for type, t in r.items():
			info = ()  # (name, type, haMax) e.g. (depth, 1, True) 1=Scalar 2=Vector, 3=none
			if '/Maximums' in type:
				if type not in maxResultTypes:
					maxResultTypes.append(type.strip('/Maximums'))
			elif '_ts' in type:
				timestepsTS = t[-1]
				if type == 'point_ts':
					pTypeTS = [(x, 4, False) for x in t[0]]
				elif type == 'line_ts':
					lTypeTS = [(x, 5, False) for x in t[0]]
				elif type == 'region_ts':
					rTypeTS = [(x, 6, False) for x in t[0]]
			elif '_lp' in type:
				timestepsLP = t[-1]
				for x in t[0]:
					if x == 'Water Level' or x == 'Energy Level':
						lTypeLP.append((x, 7, True))
					else:
						lTypeLP.append((x, 7, False))
			else:
				temporalResultTypes.append(type)
				for i, (time, values) in enumerate(t.items()):
					if values[0] not in timesteps:
						timesteps.append(float(values[0]))
		
		if not self.tuView.lock2DTimesteps:
			timesteps = self.joinResultTypes(timesteps, timestepsTS, timestepsLP, type='time')
		
		return timesteps, maxResultTypes, temporalResultTypes, pTypeTS, lTypeTS, rTypeTS, lTypeLP
	
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
					if float('{0:.6f}'.format(item)) not in [float('{0:.6f}'.format(x)) for x in final]:
						final.append(item)
				else:
					if item not in final:
						final.append(item)
		
		# make sure times are sorted ascendingly
		if 'type' in kwargs.keys() and kwargs['type'] == 'time':
			final = sorted(final)
		
		return final
	
	def applyPreviousResultTypeSelections(self, namesTS, namesLP, time):
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
		self.activeResultsIndexes = []
		for item in self.activeResultsItems:
			index = openResultTypes.model().item2index(item)
			self.activeResultsIndexes.append(index)
		
		# if there are no active results assume first dataset and select first result
		if not self.activeResults:
			openResultTypes = self.tuView.OpenResultTypes
			ind = openResultTypes.model().index(0, 0)
			index = openResultTypes.indexBelow(ind)
			if index.internalPointer().ds_name != 'None':
				self.tuView.tuResults.activeResultsIndexes.append(index)
				self.tuView.tuResults.activeResultsItems.append(index.internalPointer())
				self.tuView.tuResults.activeResultsTypes.append(index.internalPointer().ds_type)
				self.tuView.tuResults.activeResults.append(index.internalPointer().ds_name)
				if index.internalPointer().ds_type == 1:
					self.tuResults2D.activeScalar = index.internalPointer().ds_name
				elif index.internalPointer().ds_type == 2:
					self.tuResults2D.activeVector = index.internalPointer().ds_name
			
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
		self.tuView.tuPlot.tuPlotToolbar.setCheckedItemsPlotOptions(namesTS, 0)
		self.tuView.tuPlot.tuPlotToolbar.setCheckedItemsPlotOptions(namesLP, 1)
		
		# apply active time
		if time is not None:
			date = self.timekey2date[time]
			#dateProper = datetime.strptime(date, self.tuView.tuOptions.dateFormat)  # datetime object
			timeProper = self.timekey2time[time]
			if not self.tuView.tuOptions.xAxisDates:
				timeFormatted = '{0:02d}:{1:02.0f}:{2:05.2f}'.format(int(timeProper), (timeProper - int(timeProper)) * 60,
				                                                    (timeProper - int(timeProper) - (
							                                         timeProper - int(timeProper))) * 3600)
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
						timeConverted = cboTime.itemText(i).split(':')
						timeConverted = float(timeConverted[0]) + float(timeConverted[1]) / 60 + float(timeConverted[2]) / 3600
						timeDiff = abs(timeConverted - timeProper)
					else:
						timeConverted = datetime.strptime(cboTime.itemText(i), self.dateFormat)
						timeDiff = abs(timeConverted - date)
					closestTimeDiff = min(closestTimeDiff, timeDiff)
					if closestTimeDiff == timeDiff:
						closestTimeIndex = i
			if not timeFound and closestTimeIndex is not None:
				cboTime.setCurrentIndex(closestTimeIndex)
		
		changed = self.updateActiveResultTypes(None)
		if not changed:
			return False
		
		return True
	
	def updateResultTypes(self):
		"""
		Populates the plotting ui with available result types in the selected open mesh results

		:return: bool -> True for successful, False for unsuccessful
		"""

		sliderTime = self.tuView.sliderTime  # QSlider
		cboTime = self.tuView.cboTime  # QComboBox
		#mcboResultType = self.tuView.mcboResultType  # QgsCheckableComboBox
		openResults = self.tuView.OpenResults  # QListWidget
		openResultTypes = self.tuView.OpenResultTypes  # DataSetView
		
		# record existing plotting 2D result types and time so it can be re-applied after the update
		#currentNames = mcboResultType.checkedItems()
		currentNamesTS = self.tuView.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(0)
		currentNamesLP = self.tuView.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(1)
		
		currentTime = str(self.activeTime) if self.activeTime is not None else None
		
		# reset types
		reset = self.resetResultTypes()  # reset result types
		if not reset:
			return False
		timesteps, maxResultTypes, temporalResultTypes = [], [], []
		pointTypesTS, lineTypesTS, regionTypesTS, lineTypesLP = [], [], [], []
		
		for result in openResults.selectedItems():
			# Populate metadata lists
			ts, mResTypes, tResTypes, pTypesTS, lTypesTS, rTypesTS, lTypesLP = self.getDataFromResultsDict(result.text())

			# Join already open result types with new types
			timesteps = self.joinResultTypes(timesteps, ts, type='time')
			maxResultTypes = self.joinResultTypes(maxResultTypes, mResTypes)
			temporalResultTypes = self.joinResultTypes(temporalResultTypes, tResTypes)
			pointTypesTS = self.joinResultTypes(pointTypesTS, pTypesTS)
			lineTypesTS = self.joinResultTypes(lineTypesTS, lTypesTS)
			regionTypesTS = self.joinResultTypes(regionTypesTS, rTypesTS)
			lineTypesLP = self.joinResultTypes(lineTypesLP, lTypesLP)
		
		# Populate tuview interface
		mapOutputs = []
		if openResults.selectedItems():
			result = openResults.selectedItems()[0]  # just take the first selection
			for type in temporalResultTypes:
				if type not in self.results[result.text()].keys():
					# find the selected result that has it
					for result in openResults.selectedItems():
						if type in self.results[result.text()].keys():
							break
				t = self.results[result.text()][type]
				for i, (time, values) in enumerate(t.items()):
					if i == 0:  # get the data type from the first timestep i.e. scalar or vector
						if type in maxResultTypes:
							info = (type, values[1], True)
						else:
							info = (type, values[1], False)
						mapOutputs.append(info)
					else:
						break
				self.tuView.tuPlot.tuPlotToolbar.addItemToPlotOptions(type, 0)
				self.tuView.tuPlot.tuPlotToolbar.addItemToPlotOptions(type, 1)
				#mcboResultType.addItem(type)
		if not mapOutputs:
			mapOutputs = [("None", 3, False)]
		
		timeSeries = []
		timeSeries = timeSeries + pointTypesTS + lineTypesTS + regionTypesTS + lineTypesLP
		if not timeSeries:
			timeSeries = [("None", 3, False)]
		openResultTypes.setModel(DataSetModel(mapOutputs, timeSeries))
		openResultTypes.expandAll()
		
		# timesteps
		cboTime.clear()
		if timesteps:
			if not self.tuView.tuOptions.xAxisDates:  # use Time (hrs)
				if timesteps[-1] < 100:
					cboTime.addItems(['{0:02d}:{1:02.0f}:{2:05.2f}'.format(int(x), (x - int(x)) * 60,
					                                                      (x - int(x) - (x - int(x))) * 3600)
					                                                      for x in timesteps])
				else:
					cboTime.addItems(['{0:03d}:{1:02.0f}:{2:05.2f}'.format(int(x), (x - int(x)) * 60.,
					                                                      (x - int(x) - (x - int(x))) * 3600)
					                                                      for x in timesteps])
			else:  # use datetime format
				cboTime.addItems([self.tuView.tuResults._dateFormat.format(self.time2date[x]) for x in timesteps])
			sliderTime.setMaximum(len(timesteps) - 1)  # slider
		
		# Apply selection
		self.applyPreviousResultTypeSelections(currentNamesTS, currentNamesLP, currentTime)
		
		# Update viewport with enabled / disabled items
		self.tuView.currentLayerChanged()
		
		return True
	
	def updateActiveResultTypes(self, resultIndex):
		"""
		Updates the active results based on the selected result types in DataSetView

		:param resultIndex: QModelIndex
		:return: bool -> True for successful, False for unsuccessful
		"""

		openResultTypes = self.tuView.OpenResultTypes
		
		# if not a map output item there is no need to rerender the map
		layer = self.tuResults2D.activeMeshLayers[0] if self.tuResults2D.activeMeshLayers else None
		skip = False
		if resultIndex is None or resultIndex.internalPointer() is None or resultIndex.internalPointer().ds_name == 'None' or resultIndex.internalPointer().parentItem == openResultTypes.model().rootItem:  # don't need to update active result lists
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
				elif item.ds_type == 4 or item.ds_type == 5 or item.ds_type == 6 or item.ds_type == 7:  # 1d result
					self.tuResults1D.items1d.append(item)
					if item.ds_type == 4 or item.ds_type == 5 or item.ds_type == 6:  # time series
						self.tuResults1D.typesTS.append(item.ds_name)
					elif item.ds_type == 7:  # long plot
						self.tuResults1D.typesLP.append(item.ds_name)
				# if result type is vector or scalar, need to remove previous vector or scalar results
				if item.ds_type == 1 or item.ds_type == 2:
					for i, result in enumerate(self.activeResults):
						if item.ds_type == self.activeResultsTypes[i]:
							self.activeResults.pop(i)
							self.activeResultsTypes.pop(i)
							self.activeResultsIndexes.pop(i)
							self.activeResultsItems.pop(i)
							break  # there will only be one to remove
				# finally add clicked result type to generic active lists - applicable regardless of result type
				self.activeResults.append(item.ds_name)
				self.activeResultsTypes.append(item.ds_type)
				self.activeResultsIndexes.append(resultIndex)
				self.activeResultsItems.append(item)
			else:  # already in lists so click is a deselect and types need to be removed from lists
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
		
		# force selected result types in widget to be active types
		openResultTypes.selectionModel().clear()
		selection = QItemSelection()
		flags = QItemSelectionModel.Select
		for index in self.activeResultsIndexes:
			selection.select(index, index)
			openResultTypes.selectionModel().select(selection, flags)
		
		if not skip:
			# rerender map
			if layer is not None:
				rs = layer.rendererSettings()
				# if no scalar or vector turn off dataset
				if self.tuResults2D.activeScalar is None:
					rs.setActiveScalarDataset(QgsMeshDatasetIndex(-1, -1))
					layer.setRendererSettings(rs)
				if self.tuResults2D.activeVector is None:
					rs.setActiveVectorDataset(QgsMeshDatasetIndex(-1, -1))
					layer.setRendererSettings(rs)
				self.tuView.renderMap()
		else:
			# redraw plot
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
					self.secondaryAxisTypes.append('{0}_1d'.format(item.ds_name))
					
		if self.tuView.tuPlot.tuPlotToolbar.fluxSecAxisButton.isChecked():
			self.secondaryAxisTypes.append('2D Flow')
					
		return True
		
	def updateMaxTypes(self, clickedItem):
		"""
		Updates the list of result types that should plot max.
		
		:param clickedItem: dict -> { 'parent': DataSetTreeNode, 'index': DataSetTreeNode }
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		openResultTypes = self.tuView.OpenResultTypes
		
		if clickedItem is not None:
			openResultTypes.model().setActiveMax(clickedItem['parent'], clickedItem['index'])
		
		self.maxResultTypes = []
		for item in openResultTypes.model().mapOutputsItem.children():
			if item.enabled:
				if item.isMax:
					self.maxResultTypes.append(item.ds_name)
		
		for item in openResultTypes.model().timeSeriesItem.children():
			if item.enabled:
				if item.isMax:
					self.maxResultTypes.append('{0}_1d'.format(item.ds_name))
					
		return True
	
	def getResult(self, index, **kwargs):
		"""
		Gets data from the indexed results.

		:param index: TuResultsIndex
		:return: tuple -> result metadata
		"""

		forceGetTime = kwargs['force_get_time'] if 'force_get_time' in kwargs.keys() else None
		results = self.tuView.tuResults.results  # dict
		
		key1 = index.result
		key2 = index.resultType
		key3 = index.timestep
		
		if key1 not in results.keys():
			return False
		
		if key2 not in results[key1].keys():
			return False
		
		if key3 is not None:
			if key3 not in results[key1][key2].keys():
				if forceGetTime == 'next lower':
					key3 = self.findTimeNextLower(key1, key2, key3)
		
		if key3 is not None:
			return results[key1][key2][key3]
		else:
			return results[key1][key2]
	
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
		for i, (timekey, time) in enumerate(self.results[key1][key2].items()):
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
	
	def isMax(self, type):
		"""
		Returns whether the result type is max or not. Can put 'scalar' or 'vector' to auto get active scalar or vector.

		:param type: str
		:return: bool -> True for max, False for not max
		"""
		
		maxResultTypes = self.tuView.tuResults.maxResultTypes  # list -> str
		
		if type == 'scalar':
			return True if self.tuResults2D.activeScalar in maxResultTypes else False
		elif type == 'vector':
			return True if self.tuResults2D.activeVector in maxResultTypes else False
		else:
			return True if type in maxResultTypes else False
	
	def removeResults(self, resList):
		"""
		Removes the results from the indexed results and ui.

		:param resList: list -> str result name e.g. M01_5m_001
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		results = self.tuView.tuResults.results
		
		for res in resList:
			if res in results.keys():
				# remove from indexed results
				del results[res]
				
				#layer = tuflowqgis_find_layer(res)
				#self.tuView.project.removeMapLayer(layer)
				#self.tuView.canvas.refresh()
				
				# remove from ui
				for i in range(self.tuView.OpenResults.count()):
					item = self.tuView.OpenResults.item(i)
					if item is not None and item.text() == res:
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
