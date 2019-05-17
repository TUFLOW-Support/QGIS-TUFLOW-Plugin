import os
import numpy as np
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
		self.progress = QProgressBar()
	
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
		retainFlow = kwargs['retain_flow'] if 'retain_flow' in kwargs.keys() else False
		meshRendered = kwargs['mesh_rendered'] if 'mesh_rendered' in kwargs.keys() else True
		
		# clear the plot based on kwargs
		if bypass:
			pass
		elif self.tuView.cboSelectType.currentText() == 'From Map Multi':  # only clear last entry
			self.tuPlot.clearPlotLastDatasetOnly(0)
		else:
			if plot.lower() == '2d only':
				self.tuPlot.clearPlot(0, retain_flow=retainFlow)
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
			if not meshRendered:
				dp = layer.dataProvider()
				mesh = QgsMesh()
				dp.populateMesh(mesh)
			
			# get plotting for all checked result types
			if not resultTypes:  # specified result types can be passed through kwargs (used for batch export not normal plotting)
				resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(0)
			for i, rtype in enumerate(resultTypes):
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
					if self.tuView.tuOptions.timeUnits == 's':
						x.append(item[0] / 3600)
					else:
						x.append(item[0])
					if meshRendered:  # easy
						y.append(layer.datasetValue(item[-1], point).scalar())
					else:  # not so easy
						# pre-render means that we need to
						# manually go get mesh face indexes
						# then interpolate value from mesh vertices
						if i == 0:
							# first round - go get mesh faces that
							# point fall in. If graphing for more than
							# one result - don't need to do this step again
							success = self.getFaceIndexes(mesh, layer, [point])
							if not success:
								return False
							if len(self.faceIndexes) != 1:
								return False
						y.append(self.preRenderDatasetValue(mesh, layer, item[-1], self.faceIndexes[0], point))
				# check if y data has any values in it or if all nan
				# seems to error when x axis is dates and y axis all nan
				if self.tuView.tuOptions.xAxisDates:
					allNaN = True
					for a in y:
						if not qIsNaN(a):
							allNaN = False
							break
					if allNaN:
						# insert one dummy value
						y[0] = 0
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
		meshRendered = kwargs['mesh_rendered'] if 'mesh_rendered' in kwargs.keys() else True
		
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
		points, chainage, direction = lineToPoints(feat, resolution, self.iface.mapCanvas().mapUnits())
		if points is None or chainage is None or direction is None:
			QMessageBox.critical(self.tuView, "TUFLOW Viewer", "Error Converting Cross Section From Long \ Lat\n"
			                                                   "Double Check the Projection of the Workspace and Input"
			                                                   " Files are Correct.")
			return False
		
		# initialise plotting variables
		xAll = []
		yAll = []
		labels = []
		types = []
		
		# iterate through all selected results
		if not resultMesh:  # specified result meshes can be passed through kwargs (used for batch export not normal plotting)
			resultMesh = activeMeshLayers
		for layer in resultMesh:
			if not meshRendered:
				dp = layer.dataProvider()
				mesh = QgsMesh()
				dp.populateMesh(mesh)
			
			# get plotting for all checked result types
			if not resultTypes:  # specified result types can be passed through kwargs (used for batch export not normal plotting)
				resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(1)
			for j, rtype in enumerate(resultTypes):
				types.append(rtype)
				
				if not timestep:
					timestep = self.tuView.tuResults.activeTime
				if timestep == 'Maximum' or timestep == -99999 or timestep == '-99999.0000':
					isMax = True
				else:
					isMax = self.tuView.tuResults.isMax(rtype)
				# get result data for open mesh results, selected scalar datasets, and active time
				tuResultsIndex = TuResultsIndex(layer.name(), rtype, timestep, isMax)
				if not self.tuView.tuResults.getResult(tuResultsIndex, force_get_time='next lower'):
					continue
				elif type(self.tuView.tuResults.getResult(tuResultsIndex, force_get_time='next lower')) is dict:
					continue
				meshDatasetIndex = self.tuView.tuResults.getResult(tuResultsIndex, force_get_time='next lower')[-1]
				if self.tuView.tuResults.isMax(rtype):
					rtype = '{0}/Maximums'.format(rtype)  # for label entry
				
				# iterate through points and extract data
				x = []
				y = []
				for i in range(len(points)):
					x.append(chainage[i])
					if meshRendered:  # easy
						y.append(layer.datasetValue(meshDatasetIndex, QgsPointXY(points[i])).scalar())
					else:  # not as easy
						# pre-render means that we need to
						# manually go get mesh face indexes
						# then interpolate value from mesh vertices
						if j == 0 and i == 0:
							# first round - go get mesh faces that
							# points fall in. If graphing for more than
							# one result - don't need to do this step again
							success = self.getFaceIndexes(mesh, layer, points)
							if not success:
								return False
							if len(self.faceIndexes) != len(points):
								return False
						y.append(self.preRenderDatasetValue(mesh, layer, meshDatasetIndex,
						                                    self.faceIndexes[i], points[i]))
				
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
		meshRendered = kwargs['mesh_rendered'] if 'mesh_rendered' in kwargs.keys() else True
		
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
		points, chainages, directions = lineToPoints(feat, resolution, self.iface.mapCanvas().mapUnits())
		if points is None or chainages is None or directions is None:
			QMessageBox.critical(self.tuView, "TUFLOW Viewer", "Error Converting Cross Section From Long \ Lat\n"
			                                                   "Double Check the Projection of the Workspace and Input"
			                                                   " Files are Correct.")
			return False

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
				if '_ts' not in resultType and '_lp' not in resultType and 'Maximum' not in resultType and \
						'bed elevation' not in resultType.lower() and 'time' not in resultType and \
						'dur' not in resultType:
					tuResultsIndex = TuResultsIndex(layer.name(), resultType, None, False)
					res = self.tuView.tuResults.getResult(tuResultsIndex)
					if len(res) > 1:
						noTimesteps.append(len(res))
						break
		maxProgress = 0
		for ts in noTimesteps:
			maxProgress += noFeatures * noResults * noPoints * ts
		if maxProgress:
			#self.iface.messageBar().clearWidgets()
			#progressWidget = self.iface.messageBar().createMessage("TUFLOW Viewer",
			#                                               " Extracting Flow . . .")
			#messageBar = self.iface.messageBar()
			#self.progress = QProgressBar()
			self.progress.setValue(0)
			self.progress.setMaximum(100)
			#progressWidget.layout().addWidget(self.progress)
			#messageBar.pushWidget(progressWidget, duration=1)
			#self.iface.mainWindow().statusBar().showMessage("Extracting Flow . . .", 1)
			self.iface.mainWindow().statusBar().addWidget(self.progress)
			self.iface.mainWindow().repaint()
			pComplete = 0
			complete = 0
		else:
			return False
		
		# iterate through all selected results
		for layer in activeMeshLayers:
			if not meshRendered:
				dp = layer.dataProvider()
				mesh = QgsMesh()
				dp.populateMesh(mesh)
			
			# get velocity and either depth or water level
			depth = None
			velocity = None
			waterLevel = None
			bedElevation = None
			for resultType in results[layer.name()]:
				if '_ts' not in resultType and '_lp' not in resultType and 'Maximum' not in resultType:
					if 'vel' in resultType.lower() and 'time' not in resultType.lower() and 'dur' not in resultType.lower():  # make sure it's vector dataset
						velocityTRI = TuResultsIndex(layer.name(), resultType, None, False)
						velRes = self.tuView.tuResults.getResult(velocityTRI)
						for time in velRes:
							mdGroup = layer.dataProvider().datasetGroupMetadata(velRes[time][-1])
							break  # only need first one to get group index
						if mdGroup.isVector():
							velocity = resultType
					elif resultType[0].lower() == 'v' and 'time' not in resultType.lower() and 'dur' not in resultType.lower():
						velRes = resultType
						velocityTRI = TuResultsIndex(layer.name(), resultType, None, False)
						velRes = self.tuView.tuResults.getResult(velocityTRI)
						for time in velRes:
							mdGroup = layer.dataProvider().datasetGroupMetadata(velRes[time][-1])
							break  # only need first one to get group index
						if mdGroup.isVector():
							velocity = resultType
					elif 'dep' in resultType.lower() and 'time' not in resultType.lower() and 'dur' not in resultType.lower():
						depth = resultType
					elif resultType[0].lower() == 'd' and 'time' not in resultType.lower() and 'dur' not in resultType.lower():
						depth = resultType
					elif 'water level' in resultType.lower() and 'time' not in resultType.lower() and 'dur' not in resultType.lower():
						waterLevel = resultType
					elif resultType[0].lower() == 'h' and 'time' not in resultType.lower() and 'dur' not in resultType.lower():
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
				if self.tuView.tuOptions.timeUnits == 's':
					x.append(velItem[0] / 3600)
				else:
					x.append(velItem[0])
				
				# iterate across line to get flow
				sumFlow = 0
				for i, point in enumerate(points):
					if not meshRendered:
						# pre-render means that we need to
						# manually go get mesh face indexes
						# then interpolate value from mesh vertices
						if i == 0:
							# first round - go get mesh faces that
							# points fall in. If graphing for more than
							# one result - don't need to do this step again
							success = self.getFaceIndexes(mesh, layer, points)
							if not success:
								return False
							if len(self.faceIndexes) != len(points):
								return False
					
					chainage = chainages[i]
					direction = directions[i]

					# get velocity mag, x value, y value
					if meshRendered:
						velMag = layer.datasetValue(velItem[-1], QgsPointXY(point)).scalar()
					else:
						velMag = self.preRenderDatasetValue(mesh, layer, velItem[-1], self.faceIndexes[i], point)
					if qIsNaN(velMag):
						velMag = 0
					if meshRendered:
						velX = layer.datasetValue(velItem[-1], QgsPointXY(point)).x()
						velY = layer.datasetValue(velItem[-1], QgsPointXY(point)).y()
					else:
						velX = self.preRenderDatasetValue(mesh, layer, velItem[-1], self.faceIndexes[i], point, value='x')
						velY = self.preRenderDatasetValue(mesh, layer, velItem[-1], self.faceIndexes[i], point, value='y')
					
					# get depth - either directly or through water level and bed elevation
					if depth is not None:
						if meshRendered:
							depthMag = layer.datasetValue(results[layer.name()][depth][key][-1],
							                              QgsPointXY(point)).scalar()
						else:
							depthMag = self.preRenderDatasetValue(mesh, layer, results[layer.name()][depth][key][-1],
							                                      self.faceIndexes[i], point)
					else:
						if meshRendered:
							wlMag = layer.datasetValue(results[layer.name()][waterLevel][key][-1],
							                           QgsPointXY(point)).scalar()
							bedMag = layer.datasetValue(results[layer.name()][bedElevation][key][-1],
							                            QgsPointXY(point)).scalar()
						else:
							wlMag = self.preRenderDatasetValue(mesh, layer, results[layer.name()][waterLevel][key][-1],
							                                   self.faceIndexes[i], point)
							bedMag = self.preRenderDatasetValue(mesh, layer, results[layer.name()][bedElevation][key][-1],
							                                    self.faceIndexes[i], point)
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
						self.progress.setValue(pComplete)
					
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
								self.progress.setValue(pComplete)
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
						self.progress.setValue(pComplete)
						
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
	
	def getFaceIndexes(self, mesh, layer, points):
		"""
		Works out which mesh face each point falls in.
		
		:param mesh: QgsMesh
		:param layer: QgsMeshLayer
		:param points: list -> QgsPoint or QgsPointXY
		:return: bool
		"""

		# convert points to QgsPointsXY if not already
		if not points:
			return False
		points = [QgsPointXY(x) for x in points]
		# use first point as locator
		reference = points[0]
		
		# manually populate pre-rendered mesh
		dp = layer.dataProvider()
		#mesh = QgsMesh()
		#dp.populateMesh(mesh)
		
		# instead of looping through each mesh
		# face try first and last mesh face
		# then try middle and keep halfing until
		# within tolerance
		tolerance = 100
		
		# try first and last mesh face
		lowerIndex = 0
		upperIndex = mesh.faceCount() - 1
		face1 = mesh.face(lowerIndex)
		face2 = mesh.face(upperIndex)
		m1 = self.faceMax(mesh, face1)  # max x and y
		d1 = self.distance(m1, reference)  # distance
		m2 = self.faceMax(mesh, face2)
		d2 = self.distance(m2, reference)
		if d1 < tolerance:
			start = lowerIndex
		elif d2 < tolerance:
			start = upperIndex
		else:
			# else keep splitting index in half until
			# within tolerance
			count = 0
			faceIndex = int((lowerIndex + upperIndex) / 2)
			while 1:
				face = mesh.face(faceIndex)
				m = self.faceMax(mesh, face)
				d = self.distance(m, reference)  # distance
				if d < tolerance:
					start = faceIndex
					break
				else:
					# see which half is closest
					try1 = int((upperIndex + faceIndex) / 2)
					face1 = mesh.face(try1)
					m1 = self.faceMax(mesh, face1)
					d1 = self.distance(m1, reference)
					try2 = int((lowerIndex + faceIndex) / 2)
					face2 = mesh.face(try2)
					m2 = self.faceMax(mesh, face2)
					d2 = self.distance(m2, reference)
					if d1 < d2:
						lowerIndex = faceIndex
						faceIndex = try1
					else:
						upperIndex = faceIndex
						faceIndex = try2
				if try1 == try2:  # converged to a solution that isn't within buffer which can happen
					start = lowerIndex
					break
				count += 1
				if count > 1000:  # clearly something has gone wrong and the solution has diverged
					start = 0
					break
						
		# now that we have a starting point
		# progress outward in positive and negative
		# direction until we have found all points
		# first generate list of indexes to loop through
		indexes = [x for x in range(start, mesh.faceCount())]  # indexes above start
		revIndexes = [x for x in range(start - 1, -1, -1)]  # indexes below start
		staggered = [x for x in range(1, len(indexes) * 2, 2)]  # insertion points for indexes below
		# insert reverse indexes so that final list alternates between
		# increasing and decreasing from start point
		steps = min(len(indexes), len(revIndexes))
		extraStep = False
		if len(indexes) < len(revIndexes):
			extraStep = True
		for i in range(steps):
			indexes.insert(staggered[i], revIndexes[i])
		if extraStep:
			indexes += revIndexes[i + 1:]
		# loop through index list and check against point list
		self.faceIndexes = []
		faceIndexes = []
		faceIndexOrder = []
		pss = []
		count = 0
		for i in indexes:
			count += 1
			face = mesh.face(i)
			ps, inds = self.faceToPoint(mesh, face, points, pss)
			pss += ps
			faceIndexOrder += inds
			faceIndexes += [i] * len(inds)
			if len(faceIndexes) == len(points):
				break
			if len(faceIndexes) > len(points):
				return False  # something has gone wrong
		self.faceIndexes = [-1 for x in faceIndexes]
		# reorder to the same as the points
		for i in range(len(faceIndexes)):
			fi = faceIndexes[i]
			pos = faceIndexOrder[i]
			self.faceIndexes.pop(pos)
			self.faceIndexes.insert(pos, fi)
				
		return count
		
	def faceMax(self, mesh, face):
		"""
		Get x, y coords of face centroid
		
		:param face: QgsMeshFace
		:return: QgsPointXY
		"""
		
		xmax, ymax = 0, 0
		for i, v in enumerate(face):
			if i == 0:
				xmax = mesh.vertex(v).x()
				ymax = mesh.vertex(v).y()
			else:
				xmax = max(xmax, mesh.vertex(v).x())
				ymax = max(ymax, mesh.vertex(v).y())
				
		return QgsPointXY(xmax, ymax)
	
	def distance(self, point1, point2):
		"""
		Determine the distance between 2 points.
		
		:param point1: QgsPointXY
		:param point2: QgsPointXY
		:return: float distance
		"""
		
		x = point2.x() - point1.x()
		y = point2.y() - point1.y()
		
		return ( x ** 2 + y ** 2 ) ** 0.5
	
	def faceToPoint(self, mesh, face, points, pss):
		"""
		checks the mesh face against points and return a point if any fall within mesh face
		
		:param mesh: QgsMesh
		:param face: QgsMeshFace
		:param points: list -> QgsPointXY
		:param pss: list -> QgsPointXY points already found a mesh face for - needed where 1D mesh overlaps 2D mesh
		:return: QgsPointXY, int index in point list
		"""
		
		# convert mesh face into polygon
		f = self.meshToPolygon(mesh, face)
		
		# loop through points and check if point falls within mesh face
		indexes = []
		ps = []
		for i, point in enumerate(points):
			if point not in pss:
				if f.geometry().contains(point):
					indexes.append(i)
					ps.append(point)
				
		return ps, indexes
	
	def meshToPolygon(self, mesh, face):
		"""
		converts a mesh to QgsFeature polygon
		
		:param mesh: QgsMesh
		:param face: QgsMeshFace
		:return: QgsFeature
		"""
		
		# convert mesh face into polygon
		w = 'POLYGON (('
		for i, v in enumerate(face):
			if i == 0:
				w = '{0}{1} {2}'.format(w, mesh.vertex(v).x(), mesh.vertex(v).y())
			else:
				w = '{0}, {1} {2}'.format(w, mesh.vertex(v).x(), mesh.vertex(v).y())
		w += '))'
		f = QgsFeature()
		f.setGeometry(QgsGeometry.fromWkt(w))
		
		return f
	
	def preRenderDatasetValue(self, mesh, layer, result, faceIndex, point, value='scalar'):
		"""
		Interpolate result value from face index
		
		:param mesh: QgsMesh
		:param layer: QgsMeshLayer
		:param result: QgsMeshDatasetIndex
		:param faceIndex: int face index
		:param point: QgsPointXY or QgsPoint
		:return: float value
		"""
		
		# convert point to QgsPointXY
		point = QgsPointXY(point)
		
		# manually populate pre-rendered mesh
		dp = layer.dataProvider()
		
		# get face
		face = mesh.face(faceIndex)
		if not dp.isFaceActive(result, faceIndex):
			return np.nan
		
		# double check point falls in mesh (it should!)
		f = self.meshToPolygon(mesh, face)
		if not f.geometry().contains(point):
			return np.nan
		
		# use Barycentric Coordinates and triangles to get interpolated value
		# https://codeplea.com/triangular-interpolation
		# so first get triangle
		if len(face) == 4:
			# split into triangles and determine which
			# triangle point falls in
			triangle1 = face[:3]
			ftri1 = self.meshToPolygon(mesh, triangle1)
			if ftri1.geometry().contains(point):
				tri = triangle1
			else:
				triangle2 = face[2:] + face[0:1]
				ftri2 = self.meshToPolygon(mesh, triangle2)
				if ftri2.geometry().contains(point):
					tri = triangle2
				else:
					return np.nan
		elif len(face) == 3:
			tri = face
		else:
			return np.nan
		# get traingle vertex weightings
		try:
			w = self.triangleVertexWeighting(mesh, tri, point)
		except AssertionError:
			return np.nan
		# apply weightings
		z = 0
		for i, v in enumerate(tri):
			if value == 'scalar':
				z += dp.datasetValue(result, v).scalar() * w[i]
			elif value == 'x':
				z += dp.datasetValue(result, v).x() * w[i]
			elif value == 'y':
				z += dp.datasetValue(result, v).y() * w[i]
			
		return z
		
	def triangleVertexWeighting(self, mesh, triangle, point):
		"""
		Use Barycentric Coordinates to get vertex weightings from triangles.
		
		:param mesh: QgsMesh
		:param triangle: QgsMeshFace
		:param point: QgsPointXY
		:return: list -> float weightings
		"""
		
		v1x = mesh.vertex(triangle[0]).x()  # vertex 1 x coord
		v1y = mesh.vertex(triangle[0]).y()  # vertex 1 y coord
		v2x = mesh.vertex(triangle[1]).x()  # vertex 2 x
		v2y = mesh.vertex(triangle[1]).y()  # vertex 2 y
		v3x = mesh.vertex(triangle[2]).x()  # vertex 3 x
		v3y = mesh.vertex(triangle[2]).y()  # vertex 3 y
		px = point.x()  # point x
		py = point.y()  # point y
		
		# weighting vertex 1
		w1numer = (v2y - v3y) * (px - v3x) + (v3x - v2x) * (py - v3y)
		w1denom = (v2y - v3y) * (v1x - v3x) + (v3x - v2x) * (v1y - v3y)
		w1 = w1numer / w1denom
		assert(w1 >= 0)
		
		# weighting vertex 2
		w2numer = (v3y - v1y) * (px - v3x) + (v1x - v3x) * (py - v3y)
		w2denom = (v2y - v3y) * (v1x - v3x) + (v3x - v2x) * (v1y - v3y)
		w2 = w2numer / w2denom
		assert(w2 >= 0)
		
		# weighting vertex 3
		w3 = 1.0 - w1 - w2
		assert(w3 >= 0)
		
		return [w1, w2, w3]
	
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
	