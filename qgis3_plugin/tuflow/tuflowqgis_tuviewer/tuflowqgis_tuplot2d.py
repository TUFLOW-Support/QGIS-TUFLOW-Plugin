import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets  import *
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesultsindex import TuResultsIndex
from tuflow.tuflowqgis_library import lineToPoints, getDirection


class TuPlot2D():
	"""
	Class for handling 2D specific plotting.
	
	"""
	
	def __init__(self, TuPlot):
		self.tuPlot = TuPlot
		self.tuView = TuPlot.tuView
		self.tuResults = self.tuView.tuResults
		self.iface = self.tuView.iface
		self.canvas = self.tuView.canvas
		self.multiPointSelectCount = 1
		self.multiLineSelectCount = 1
		self.multiFlowLineSelectCount = 1
		self.clearedLongPlot = False
		self.plotSelectionPointFeat = []  # store feat for ts plotting so can update outside of active layer
		self.plotSelectionLineFeat = []  # store feat for cross section plotting so can update outside of active layer
		self.plotSelectionFlowFeat = []  # store feat for flow plotting so can update outside of active layer
		self.flowProgressBar = None
	
	def plotTimeSeriesFromMap(self, vLayer, point, **kwargs):
		"""
		Initiate plotting by using an XY location

		:param point: QgsPointXY
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		activeMeshLayers = self.tuResults.tuResults2D.activeMeshLayers  # list
		results = self.tuResults.results  # dict
		
		# Check that layer is points
		if vLayer is not None:  # if none then memory layer
			if vLayer.geometryType() != 0:
				return
			
		if type(point) is QgsFeature:
			point = point.geometry().asPoint()  # if feature is passed in as argument, convert to QgsPointXY
		
		# deal with kwargs
		bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		resultTypes = kwargs['types'] if 'types' in kwargs.keys() else []  # export kwarg
		resultMesh = kwargs['mesh'] if 'mesh' in kwargs.keys() else []  # export kwarg
		export = kwargs['export'] if 'export' in kwargs.keys() else None  # 'csv' or 'image'
		exportOut = kwargs['export_location'] if 'export_location' in kwargs.keys() else None
		exportFormat = kwargs['export_format'] if 'export_format' in kwargs.keys() else None
		name = kwargs['name'] if 'name' in kwargs.keys() else None
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		time = kwargs['time'] if 'time' in kwargs.keys() else None
		showCurrentTime = kwargs['show_current_time'] if 'show_current_time' in kwargs.keys() else False
		
		# clear the plot based on kwargs
		if bypass:
			pass
		elif self.tuView.cboSelectType.currentText() == 'From Map Multi':  # only clear last entry
			self.tuPlot.clearPlotLastDatasetOnly(0)
		else:
			if plot.lower() == '2d only':
				self.tuPlot.clearPlot(0)
			else:
				self.tuPlot.clearPlot(0, retain_1d=True, retain_flow=True)
		
		# Initialise variables
		xAll = []
		yAll = []
		labels = []
		types = []
		
		# iterate through all selected results
		if not resultMesh:  # specified result meshes can be passed through kwargs (used for batch export not normal plotting)
			resultMesh = activeMeshLayers
		for layer in resultMesh:  # get plotting for all selected result meshes
			
			# get plotting for all checked result types
			if not resultTypes:  # specified result types can be passed through kwargs (used for batch export not normal plotting)
				resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(0)
			for rtype in resultTypes:
				types.append(rtype)
				
				# get result data for open mesh results and selected scalar dataset
				tuResultsIndex = TuResultsIndex(layer.name(), rtype, None, False)
				r = self.tuView.tuResults.getResult(tuResultsIndex)  # r = dict - { str time: [ float time, QgsMeshDatasetIndex ] }
				if not r:
					return
				
				# iterate through result timesteps to get time series
				x = []
				y = []
				for key, item in r.items():
					x.append(item[0])
					y.append(layer.datasetValue(item[-1], point).scalar())
				
				# add to overall data list
				xAll.append(x)
				yAll.append(y)
				
				# legend label for multi points
				if export:
					label = '{0}'.format(rtype) if len(resultMesh) == 1 else '{1}: {0}'.format(rtype, layer.name())
				elif bypass or self.tuView.cboSelectType.currentText() == 'From Map Multi':
					label = '{0} - point {1}'.format(rtype, self.multiPointSelectCount) if len(
						activeMeshLayers) < 2 else '{0} - {1} - point {2}'.format(layer.name(), rtype,
					                                                              self.multiPointSelectCount)
				# normal single point click
				else:
					label = '{0}'.format(rtype) if len(activeMeshLayers) < 2 else '{0} - {1}'.format(layer.name(),
					                                                                                rtype)
				if label is not None:
					labels.append(label)
		
		# increment point count for multi select
		if bypass:  # multi select click
			self.multiPointSelectCount += 1

		data = list(zip(xAll, yAll))
		if data:
			if export is None:  # normal plot i.e. in tuview
				self.tuPlot.drawPlot(0, data, labels, types, draw=draw, time=time, show_current_time=showCurrentTime)
			elif export == 'image':  # plot through drawPlot however instead of drawing, save figure
				# unique output file name
				outFile = '{0}{1}'.format(os.path.join(exportOut, name), exportFormat)
				iterator = 1
				while os.path.exists(outFile):
					outFile = '{0}_{2}{1}'.format(os.path.join(exportOut, name), exportFormat, iterator)
					iterator += 1
				self.tuPlot.drawPlot(0, data, labels, types, export=outFile)
			elif export == 'csv':  # export to csv, don't plot
				self.tuPlot.exportCSV(0, data, labels, types, exportOut, name)
			else:  # catch all other cases and just do normal, although should never be triggered
				self.tuPlot.drawPlot(0, data, labels, types, draw=draw, time=time, show_current_time=showCurrentTime)
			
		return True
	
	def plotCrossSectionFromMap(self, vLayer, feat, **kwargs):
		"""
		Initiate plotting using XY coordinates

		:param vLayer: QgsVectorLayer
		:param feat: QgsFeature
		:param kwargs: bool bypass
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		activeMeshLayers = self.tuResults.tuResults2D.activeMeshLayers  # list
		results = self.tuResults.results  # dict
		
		# Check that line is a polyline
		if vLayer is not None:  # if none then memory layer
			if vLayer.geometryType() != 1:
				return False
		
		# deal with the kwargs
		bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		resultTypes = kwargs['types'] if 'types' in kwargs.keys() else []  # export kwarg
		resultMesh = kwargs['mesh'] if 'mesh' in kwargs.keys() else []  # export kwarg
		timestep = kwargs['time'] if 'time' in kwargs.keys() else None  # export kwarg
		timestepFormatted = kwargs['time_formatted'] if 'time_formatted' in kwargs.keys() else ''
		export = kwargs['export'] if 'export' in kwargs.keys() else None  # 'csv' or 'image'
		exportOut = kwargs['export_location'] if 'export_location' in kwargs.keys() else None
		exportFormat = kwargs['export_format'] if 'export_format' in kwargs.keys() else None
		name = kwargs['name'] if 'name' in kwargs.keys() else None
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		
		# clear the plot based on kwargs
		if bypass:
			pass
		elif self.tuView.cboSelectType.currentText() == 'From Map Multi':  # only clear last entry
			self.tuPlot.clearPlotLastDatasetOnly(1)
		else:
			if plot.lower() == '2d only':
				self.tuPlot.clearPlot(1)
			else:
				self.tuPlot.clearPlot(1, retain_1d=True)
		
		# get extraction points
		resolution = self.tuView.tuOptions.resolution
		points, chainage, direction = lineToPoints(feat, resolution)
		
		# initialise plotting variables
		xAll = []
		yAll = []
		labels = []
		types = []
		
		# iterate through all selected results
		if not resultMesh:  # specified result meshes can be passed through kwargs (used for batch export not normal plotting)
			resultMesh = activeMeshLayers
		for layer in resultMesh:
			
			# get plotting for all checked result types
			if not resultTypes:  # specified result types can be passed through kwargs (used for batch export not normal plotting)
				resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(1)
			for rtype in resultTypes:
				types.append(rtype)
				
				if not timestep:
					timestep = self.tuView.tuResults.activeTime
				if timestep == 'Maximum':
					isMax = True
				else:
					isMax = self.tuView.tuResults.isMax(rtype)
				# get result data for open mesh results, selected scalar datasets, and active time
				tuResultsIndex = TuResultsIndex(layer.name(), rtype, timestep, isMax)
				if not self.tuView.tuResults.getResult(tuResultsIndex, force_get_time='next lower'):
					continue
				meshDatasetIndex = self.tuView.tuResults.getResult(tuResultsIndex, force_get_time='next lower')[-1]
				if self.tuView.tuResults.isMax(rtype):
					rtype = '{0}/Maximums'.format(rtype)  # for label entry
				
				# iterate through points and extract data
				x = []
				y = []
				for i in range(len(points)):
					x.append(chainage[i])
					y.append(layer.datasetValue(meshDatasetIndex, QgsPointXY(points[i])).scalar())
				
				# add to overall data list
				xAll.append(x)
				yAll.append(y)
				# legend label for multi lines
				if export:
					label = '{0} [{1}]'.format(
						rtype, timestepFormatted) if len(resultMesh) == 1 else '{2}: {0} [{1}]'.format(rtype, timestepFormatted, layer.name())
				elif bypass or self.tuView.cboSelectType.currentText() == 'From Map Multi':
					label = '{0} - line {1}'.format(rtype, self.multiLineSelectCount) if len(
						activeMeshLayers) < 2 else '{0} - {1} - line {2}'.format(layer.name(), rtype,
					                                                             self.multiLineSelectCount)
				else:
					label = '{0}'.format(rtype) if len(activeMeshLayers) < 2 else '{0} - {1}'.format(layer.name(),
					                                                                                rtype)
				
				labels.append(label)
		
		# increment line count for multi select - for updateLongPlot function
		if bypass:  # multi select click
			self.multiLineSelectCount += 1

		data = list(zip(xAll, yAll))
		if data:
			if export is None:  # normal plot i.e. in tuview
				self.tuPlot.drawPlot(1, data, labels, types, draw=draw)
			elif export == 'image':  # plot through drawPlot however instead of drawing, save figure
				# unique output file name
				outFile = '{0}{1}'.format(os.path.join(exportOut, name), exportFormat)
				iterator = 1
				while os.path.exists(outFile):
					outFile = '{0}_{2}{1}'.format(os.path.join(exportOut, name), exportFormat, iterator)
					iterator += 1
				self.tuPlot.drawPlot(1, data, labels, types, export=outFile)
			elif export == 'csv':  # export to csv, don't plot
				self.tuPlot.exportCSV(1, data, labels, types, exportOut, name)
			else:  # catch all other cases and just do normal, although should never be triggered
				self.tuPlot.drawPlot(1, data, labels, types, draw=draw)
		
		return True
	
	def plotFlowFromMap(self, vLayer, feat, **kwargs):
		"""
		Initiate flow plotting using XY coordinates

		:param vLayer: QgsVectorLayer
		:param feat: QgsFeature
		:param kwargs: bool bypass
		:return: bool -> True for successful, False for unsuccessful
		"""

		activeMeshLayers = self.tuResults.tuResults2D.activeMeshLayers  # list
		results = self.tuResults.results  # dict
		
		# Check that line is a polyline
		if vLayer is not None:  # if none then memory layer
			if vLayer.geometryType() != 1:
				return
				
		# deal with the kwargs
		bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		time = kwargs['time'] if 'time' in kwargs.keys() else None
		showCurrentTime = kwargs['show_current_time'] if 'show_current_time' in kwargs.keys() else False
		
		# clear the plot based on kwargs
		if bypass:
			pass
		else:
			if plot.lower() == 'flow only':
				self.tuPlot.clearPlot(1)
			else:
				self.tuPlot.clearPlot(1, retain_1d=True, retain_2d=True)
				
		# get extraction points
		resolution = self.tuView.tuOptions.resolution
		points, chainages, directions = lineToPoints(feat, resolution)
		
		# initialise plotting variables
		xAll = []
		yAll = []
		labels = []
		types = ['2D Flow']
		
		# initialise progress bar
		noFeatures = 1
		noResults = len(activeMeshLayers)
		noPoints = len(points)
		noTimesteps = []
		for layer in activeMeshLayers:
			for resultType in results[layer.name()]:
				if '_ts' not in resultType and '_lp' not in resultType and 'Maximum' not in resultType and 'bed elevation' not in resultType.lower():
					tuResultsIndex = TuResultsIndex(layer.name(), resultType, None, False)
					res = self.tuView.tuResults.getResult(tuResultsIndex)
					noTimesteps.append(len(res))
					break
		maxProgress = 0
		for ts in noTimesteps:
			maxProgress += noFeatures * noResults * noPoints * ts
		if maxProgress:
			self.iface.messageBar().clearWidgets()
			progressWidget = self.iface.messageBar().createMessage("Tuview",
			                                               " Extracting Flow . . .")
			messageBar = self.iface.messageBar()
			progress = QProgressBar()
			progress.setMaximum(100)
			progressWidget.layout().addWidget(progress)
			messageBar.pushWidget(progressWidget, duration=1)
			self.iface.mainWindow().repaint()
			pComplete = 0
			complete = 0
		else:
			return False
		
		# iterate through all selected results
		for layer in activeMeshLayers:
			
			# get velocity and either depth or water level
			depth = None
			velocity = None
			waterLevel = None
			bedElevation = None
			for resultType in results[layer.name()]:
				if '_ts' not in resultType and '_lp' not in resultType and 'Maximum' not in resultType:
					if 'vel' in resultType.lower():  # make sure it's vector dataset
						velocityTRI = TuResultsIndex(layer.name(), resultType, None, False)
						velRes = self.tuView.tuResults.getResult(velocityTRI)
						for time in velRes:
							mdGroup = layer.dataProvider().datasetGroupMetadata(velRes[time][-1])
							break  # only need first one to get group index
						if mdGroup.isVector():
							velocity = resultType
					elif 'dep' in resultType.lower():
						depth = resultType
					elif 'water level' in resultType.lower():
						waterLevel = resultType
					elif resultType[0] == 'h':
						waterLevel = resultType
					elif 'bed elevation' in resultType.lower():
						bedElevation = resultType
			
			# get results using index
			velocityTRI = TuResultsIndex(layer.name(), velocity, None, False)  # velocity TuResultsIndex
			velRes = self.tuView.tuResults.getResult(velocityTRI)  # r = dict - { str time: [ float time, QgsMeshDatasetIndex ] }
			if depth is not None:
				depthTRI = TuResultsIndex(layer.name(), depth, None, False)
				depthRes = self.tuView.tuResults.getResult(depthTRI)
			else:
				wlTRI = TuResultsIndex(layer.name(), waterLevel, None, False)
				wlRes = self.tuView.tuResults.getResult(wlTRI)
				bedTRI = TuResultsIndex(layer.name(), bedElevation, None, False)
				bedRes = self.tuView.tuResults.getResult(bedTRI)
				
			# iterate through result timesteps to get time series
			x = []
			y = []
			for key, velItem in velRes.items():
				x.append(velItem[0])
				
				# iterate across line to get flow
				sumFlow = 0
				for i, point in enumerate(points):
					chainage = chainages[i]
					direction = directions[i]
					
					# get velocity mag, x value, y value
					velMag = layer.datasetValue(velItem[-1], QgsPointXY(point)).scalar()
					if qIsNaN(velMag):
						velMag = 0
					velX = layer.datasetValue(velItem[-1], QgsPointXY(point)).x()
					velY = layer.datasetValue(velItem[-1], QgsPointXY(point)).y()
					
					# get depth - either directly or through water level and bed elevation
					if depth is not None:
						depthMag = layer.datasetValue(results[layer.name()][depth][key][-1], QgsPointXY(point)).scalar()
					else:
						wlMag = layer.datasetValue(results[layer.name()][waterLevel][key][-1], QgsPointXY(point)).scalar()
						bedMag = layer.datasetValue(results[layer.name()][bedElevation][key][-1], QgsPointXY(point)).scalar()
						depthMag = wlMag - bedMag
					if qIsNaN(depthMag):
						depthMag = 0
					
					# calculate flux across line segment
					if i == 0:  # can't get flux at first point since there's no flow area
						prevChainage = chainage
						prevVelMag = velMag
						prevVelX = velX
						prevVelY = velY
						prevDepthMag = depthMag
						prevFlowDirection = None
						complete += 1
						pComplete = complete / maxProgress * 100
						progress.setValue(pComplete)
					
					elif i > 0:
						directionOpposite = direction + 180.0
						if directionOpposite > 360.0:
							directionOpposite -= 360.0
						
						# get average values from current and previous values
						avVelMag = (velMag + prevVelMag) / 2
						if qIsNaN(prevVelX):
							avVelX = velX
						elif qIsNaN(velX):
							avVelX = prevVelX
						else:
							avVelX = (velX + prevVelX) / 2
						if qIsNaN(prevVelY):
							avVelY = velY
						elif qIsNaN(velY):
							avVelY = prevVelY
						else:
							avVelY = (velY + prevVelY) / 2
						avDepthMag = (depthMag + prevDepthMag) / 2
						
						flowDirection = getDirection(None, None, x=avVelX, y=avVelY)
						if flowDirection is None:
							flowDirection = prevFlowDirection
							if flowDirection is None:
								prevChainage = chainage
								prevVelMag = velMag
								prevVelX = velX
								prevVelY = velY
								prevDepthMag = depthMag
								prevFlowDirection = flowDirection
								complete += 1
								pComplete = complete / maxProgress * 100
								progress.setValue(pComplete)
								continue
						if flowDirection == direction or flowDirection == directionOpposite:
							flow = 0  # zero flow if flow is running parallel to line
						else:
							width = chainage - prevChainage
							flow = avDepthMag * width * avVelMag
							# determine direction
							# need to consider what happens when line direction is > 180deg i.e. there is a
							# spot where angle resets to zero when tracking round to the opposite direction
							if direction > 180 and flowDirection < 180:
								flowDirectionAdd = flowDirection + 360.0
								if flowDirectionAdd > direction and flowDirection < directionOpposite:  # positive
									sumFlow += flow
								else:  # negative
									sumFlow -= flow
							elif direction > 180 and flowDirection > 180:
								directionOppositeAdd = directionOpposite + 360.0
								if flowDirection > direction and flowDirection < directionOppositeAdd:  # positive
									sumFlow += flow
								else:  # negativve
									sumFlow -= flow
							else:  # don't need to consider what happens when one of the direction exceed 360
								if flowDirection > direction and flowDirection < directionOpposite:  # positive
									sumFlow += flow
								else:  # negative
									sumFlow -= flow
						
						prevChainage = chainage
						prevVelMag = velMag
						prevVelX = velX
						prevVelY = velY
						prevDepthMag = depthMag
						prevFlowDirection = flowDirection
						complete += 1
						pComplete = complete / maxProgress * 100
						progress.setValue(pComplete)
						
				# summed all flow, can append to timestep
				y.append(sumFlow)
			
			# add to overall data list
			xAll.append(x)
			yAll.append(y)
			
			if bypass or self.tuView.cboSelectType.currentText() == 'From Map Multi':
				label = '2D Map Flow - Location {0}'.format(self.multiFlowLineSelectCount) if len(activeMeshLayers) < 2 \
					else '{0} - 2D Map Flow - location {1}'.format(layer.name(), self.multiFlowLineSelectCount)
				self.multiFlowLineSelectCount += 1
			else:
				label = '2D Map Flow' if len(activeMeshLayers) < 2 else '{0} - 2D Map Flow'.format(layer.name())
			labels.append(label)
		
		data = list(zip(xAll, yAll))
		self.tuPlot.drawPlot(0, data, labels, types, draw=draw, time=time, show_current_time=showCurrentTime)

		return True
	
	def resetMultiPointCount(self):
		"""
		Resets the multi point time series count back to 1
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.multiPointSelectCount = 1
		
		return True
	
	def resetMultiLineCount(self):
		"""
		Resets the multi line long plot count back to 1

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.multiLineSelectCount = 1
		
		return True
	
	def resetMultiFlowLineCount(self):
		"""
		Resets the multi flow line count for time series plot back to 1.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.multiFlowLineSelectCount = 1
		
		return True
	
	def reduceMultiPointCount(self, quantity):
		"""
		Reduce the multi point time series count by an amount
		
		:param quantity: int
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.multiPointSelectCount -= quantity
		
		return True
	
	def reduceMultiLineCount(self, quantity):
		"""
		Reduce the multi line long plot count by an amount

		:param quantity: int
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.multiLineSelectCount -= quantity
		
		return True
	
	def reduceMultiFlowLineCount(self, quantity):
		"""
		Reduce the multi line flow plot count by an amount

		:param quantity: int
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.multiFlowLineSelectCount -= quantity
		
		return True