import os
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets  import *
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesultsindex import TuResultsIndex
from tuflow.tuflowqgis_library import (lineToPoints, getDirection, doLinesIntersect,
                                       intersectionPoint, calculateLength, getFaceIndexes3,
                                       findMeshIntersects, writeTempPoints, writeTempPolys,
                                       meshToPolygon, calcMidPoint)
import inspect
from datetime import datetime, timedelta


class TuPlot2D():
	"""
	Class for handling 2D specific plotting.
	
	"""
	
	def __init__(self, TuPlot=None):
		if TuPlot is not None:
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
			self.faceIndexes = []

	def plotTimeSeriesFromMap(self, vLayer, point, **kwargs):
		"""
		Initiate plotting by using an XY location

		:param point: QgsPointXY
		:return: bool -> True for successful, False for unsuccessful
		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		activeMeshLayers = self.tuResults.tuResults2D.activeMeshLayers  # list
		results = self.tuResults.results  # dict
		
		# Check that layer is points
		if vLayer is not None:  # if none then memory layer
			if vLayer.geometryType() != QgsWkbTypes.PointGeometry:
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
		plotActiveScalar = kwargs['plot_active_scalar'] if 'plot_active_scalar' in kwargs else False
		featName = kwargs['featName'] if 'featName' in kwargs else None
		markerNo = kwargs['markerNo'] if 'markerNo' in kwargs else 0
		dataType = kwargs['data_type'] if 'data_type' in kwargs else TuPlot.DataTimeSeries2D
		
		# clear the plot based on kwargs
		if bypass:
			pass
		# elif self.tuView.cboSelectType.currentText() == 'From Map Multi':  # only clear last entry
		# 	# self.tuPlot.clearPlotLastDatasetOnly(TuPlot.TimeSeries)
		else:
			# if plot.lower() == '2d only':
			# 	self.tuPlot.clearPlot(0, retain_flow=retainFlow)
			# else:
			# 	self.tuPlot.clearPlot(0, retain_1d=True, retain_flow=True)
			#if not resultTypes:  # specified result types can be passed through kwargs (used for batch export not normal plotting)
			#	resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(dataType)
			if not resultMesh:  # specified result meshes can be passed through kwargs (used for batch export not normal plotting)
				resultMesh = activeMeshLayers
			self.tuPlot.clearPlot2(TuPlot.TimeSeries, dataType,
			                       last_only=self.tuView.cboSelectType.currentText() == 'From Map Multi',
			                       remove_no=len(resultTypes)*len(resultMesh))

		# Initialise variables
		xAll = []
		yAll = []
		labels = []
		types = []
		dataTypes = []
		
		# iterate through all selected results
		if not resultMesh:  # specified result meshes can be passed through kwargs (used for batch export not normal plotting)
			resultMesh = activeMeshLayers
		for layer in resultMesh:  # get plotting for all selected result meshes
			if not meshRendered:
				dp = layer.dataProvider()
				mesh = QgsMesh()
				dp.populateMesh(mesh)
				si = QgsMeshSpatialIndex(mesh)
			else:
				dp = None
				mesh = None
				si = None
			
			# get plotting for all checked result types
			if not resultTypes:  # specified result types can be passed through kwargs (used for batch export not normal plotting)
				resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(dataType)
				
				# deal with active scalar plotting
				if plotActiveScalar:
					if plotActiveScalar == 'active scalar':
						if self.tuView.tuResults.tuResults2D.activeScalar not in resultTypes:
							resultTypes += [self.tuView.tuResults.tuResults2D.activeScalar]
					else:  # do both active scalar and [depth for water level] - tumap specific
						if plotActiveScalar not in resultTypes:
							resultTypes.append(plotActiveScalar)
						if plotActiveScalar == 'Depth' or plotActiveScalar == 'D':
							if 'Water Level' in self.tuResults.results[layer.name()]:
								if 'Water Level' not in resultTypes:
									resultTypes.append('Water Level')
							elif 'H' in self.tuResults.results[layer.name()]:
								if 'H' not in resultTypes:
									resultTypes.append('H')
			
			for i, rtype in enumerate(resultTypes):
				# get result data for open mesh results and selected scalar dataset
				tuResultsIndex = TuResultsIndex(layer.name(), rtype, None, False)
				r = self.tuView.tuResults.getResult(tuResultsIndex)  # r = dict - { str time: [ float time, QgsMeshDatasetIndex ] }
				if not r:
					continue
				gmd = None
				for key, item in r.items():
					gmd = layer.dataProvider().datasetGroupMetadata(item[-1].group())
					break
				if gmd is None:
					continue

				avgmethods = self.getAveragingMethods(dataType, gmd, resultTypes)
				am = avgmethods[i]

				# for am in avgmethods:
				types.append(rtype)

				# iterate through result timesteps to get time series
				x = []
				y = []
				for key, item in r.items():
					if self.tuView.tuOptions.timeUnits == 's':
						x.append(item[0] / 3600)
					else:
						x.append(item[0])
					y.append(self.datasetValue(layer, dp, si, mesh, item[-1], meshRendered, point, i, dataType, am))

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
				label = self.generateLabel(layer, resultMesh, rtype, markerNo, featName,
				                           activeMeshLayers, am, export, bypass, i, dataType)

				if label is not None:
					labels.append(label)
		
		# increment point count for multi select
		if bypass:  # multi select click
			self.multiPointSelectCount += 1

		data = list(zip(xAll, yAll))
		dataTypes = [dataType] * len(data)
		if data:
			if export is None:  # normal plot i.e. in tuview
				self.tuPlot.drawPlot(TuPlot.TimeSeries, data, labels, types, dataTypes, draw=draw, time=time, show_current_time=showCurrentTime)
			elif export == 'image':  # plot through drawPlot however instead of drawing, save figure
				# unique output file name
				outFile = '{0}{1}'.format(os.path.join(exportOut, name), exportFormat)
				iterator = 1
				while os.path.exists(outFile):
					outFile = '{0}_{2}{1}'.format(os.path.join(exportOut, name), exportFormat, iterator)
					iterator += 1
				self.tuPlot.drawPlot(TuPlot.TimeSeries, data, labels, types, dataTypes, export=outFile)
			elif export == 'csv':  # export to csv, don't plot
				self.tuPlot.exportCSV(TuPlot.TimeSeries, data, labels, types, exportOut, name)
			else:  # catch all other cases and just do normal, although should never be triggered
				self.tuPlot.drawPlot(TuPlot.TimeSeries, data, labels, types, dataTypes, draw=draw, time=time, show_current_time=showCurrentTime)
			
		return True
	
	def plotCrossSectionFromMap(self, vLayer, feat, **kwargs):
		"""
		Initiate plotting using XY coordinates

		:param vLayer: QgsVectorLayer
		:param feat: QgsFeature
		:param kwargs: bool bypass
		:return: bool -> True for successful, False for unsuccessful
		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		debug = self.tuView.tuOptions.writeMeshIntersects
		activeMeshLayers = self.tuResults.tuResults2D.activeMeshLayers  # list
		results = self.tuResults.results  # dict
		
		# Check that line is a polyline
		if vLayer is not None:  # if none then memory layer
			if vLayer.geometryType() != QgsWkbTypes.LineGeometry:
				return False
			crs = vLayer.sourceCrs()
		else:
			crs = self.tuView.project.crs()
		
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
		plotActiveScalar = kwargs['plot_active_scalar'] if 'plot_active_scalar' in kwargs else False
		featName = kwargs['featName'] if 'featName' in kwargs else None
		lineNo = kwargs['lineNo'] if 'lineNo' in kwargs else 0
		dataType = kwargs['data_type'] if 'data_type' in kwargs else TuPlot.DataCrossSection2D

		# clear the plot based on kwargs
		if bypass:
			pass
		# elif self.tuView.cboSelectType.currentText() == 'From Map Multi':  # only clear last entry
		# 	self.tuPlot.clearPlotLastDatasetOnly(TuPlot.CrossSection)
		else:
			# if plot.lower() == '2d only':
			# 	self.tuPlot.clearPlot(1)
			# else:
			# 	self.tuPlot.clearPlot(1, retain_1d=True)
			# if not resultTypes:  # specified result types can be passed through kwargs (used for batch export not normal plotting)
			# 	resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(dataType)
			if not resultMesh:  # specified result meshes can be passed through kwargs (used for batch export not normal plotting)
				resultMesh = activeMeshLayers
			self.tuPlot.clearPlot2(TuPlot.CrossSection, dataType,
			                       last_only=self.tuView.cboSelectType.currentText() == 'From Map Multi',
			                       remove_no=len(resultTypes)*len(resultMesh))

		# initialise plotting variables
		xAll = []
		yAll = []
		labels = []
		types = []
		dataTypes = []

		# iterate through all selected results
		if not resultMesh:  # specified result meshes can be passed through kwargs (used for batch export not normal plotting)
			resultMesh = activeMeshLayers
		for layer in resultMesh:
			dp = layer.dataProvider()
			mesh = QgsMesh()
			dp.populateMesh(mesh)
			si = QgsMeshSpatialIndex(mesh)

			# get plotting for all checked result types
			if not resultTypes:  # specified result types can be passed through kwargs (used for batch export not normal plotting)
				resultTypes = self.tuPlot.tuPlotToolbar.getCheckedItemsFromPlotOptions(dataType)
				
				# deal with active scalar plotting
				if plotActiveScalar:
					if plotActiveScalar == 'active scalar':
						if self.tuView.tuResults.tuResults2D.activeScalar not in resultTypes:
							resultTypes += [self.tuView.tuResults.tuResults2D.activeScalar]
					else:  # do both active scalar and [depth for water level] - tumap specific
						if plotActiveScalar not in resultTypes:
							resultTypes.append(plotActiveScalar)
						if plotActiveScalar == 'Depth' or plotActiveScalar == 'D':
							if 'Water Level' in self.tuResults.results[layer.name()]:
								if 'Water Level' not in resultTypes:
									resultTypes.append('Water Level')
							elif 'H' in self.tuResults.results[layer.name()]:
								if 'H' not in resultTypes:
									resultTypes.append('H')
				
			for j, rtype in enumerate(resultTypes):
				if not timestep:
					timestep = self.tuView.tuResults.activeTime
				if timestep == 'Maximum' or timestep == 99999 or timestep == '99999.000000':
					isMax = True
				else:
					isMax = self.tuView.tuResults.isMax(rtype)
				if timestep == 'Minimum' or timestep == -99999 or timestep == '-99999.000000':
					isMin = True
				else:
					isMin = self.tuView.tuResults.isMin(rtype)
				# get result data for open mesh results, selected scalar datasets, and active time
				tuResultsIndex = TuResultsIndex(layer.name(), rtype, timestep, isMax, isMin)
				if not self.tuView.tuResults.getResult(tuResultsIndex, force_get_time='next lower'):
					continue
				elif type(self.tuView.tuResults.getResult(tuResultsIndex, force_get_time='next lower')) is dict:
					continue
				types.append(rtype)
				meshDatasetIndex = self.tuView.tuResults.getResult(tuResultsIndex, force_get_time='next lower')[-1]
				if self.tuView.tuResults.isMax(rtype):
					if rtype.lower() == 'minimum dt':
						rtype = '{0}/Final'.format(rtype)
					else:
						rtype = '{0}/Maximums'.format(rtype)
				elif self.tuView.tuResults.isMin(rtype):
					rtype = '{0}/Minimums'.format(rtype)

				gmd = dp.datasetGroupMetadata(meshDatasetIndex.group())
				avgmethods = self.getAveragingMethods(dataType, gmd, resultTypes)
				am = avgmethods[j]

				if j == 0 or onVertices != (gmd.dataType() == QgsMeshDatasetGroupMetadata.DataOnVertices):
					onVertices = gmd.dataType() == QgsMeshDatasetGroupMetadata.DataOnVertices
					if j == 0:
						inters, ch, fcs = findMeshIntersects(si, dp, mesh, feat, crs,
						                                             self.tuView.project)
					#if gmd.dataType() == QgsMeshDatasetGroupMetadata.DataOnVertices:
					if onVertices:
						#points = inters[:]
						points = inters[0:1]
						points.extend([calcMidPoint(inters[i], inters[i + 1], crs) for i in range(len(inters) - 1)])
						points.append(inters[-1])
						chainage = ch[0:1]
						chainage.extend([(ch[i] + ch[i+1]) / 2. for i in range(len(ch) - 1)])
						chainage.append(ch[-1])
						faces = [None] * len(points)
						if debug:
							writeTempPoints(inters, self.tuView.project, crs, chainage, 'Chainage',
							                QVariant.Double)
					else:
						# points = faces[:]
						points = inters[:]
						chainage = ch[:]
						faces = fcs[:]
						if debug:
							polys = [meshToPolygon(mesh, mesh.face(x)) for x in faces]
							writeTempPolys(polys, self.tuView.project, crs)
							writeTempPoints(inters, self.tuView.project, crs, chainage, 'Chainage',
							                QVariant.Double)
				
				# iterate through points and extract data
				x = []
				y = []
				for i in range(len(faces)):
					x.append(chainage[i])
					v = self.datasetValue(layer, dp, si, mesh, meshDatasetIndex, meshRendered,
					                      points[i], j, dataType, am, faces[i])
					y.append(v)

					if faces[i] is not None:
						x.append(chainage[i+1])
						y.append(v)

				# add to overall data list
				xAll.append(x)
				yAll.append(y)

				label = self.generateLabel(layer, resultMesh, rtype, lineNo, featName,
				                           activeMeshLayers, am, export, bypass, j, dataType)
				labels.append(label)
		
		# increment line count for multi select - for updateLongPlot function
		if bypass:  # multi select click
			self.multiLineSelectCount += 1

		data = list(zip(xAll, yAll))
		dataTypes = [dataType] * len(data)
		if data:
			if export is None:  # normal plot i.e. in tuview
				self.tuPlot.drawPlot(TuPlot.CrossSection, data, labels, types, dataTypes, draw=draw)
			elif export == 'image':  # plot through drawPlot however instead of drawing, save figure
				# unique output file name
				outFile = '{0}{1}'.format(os.path.join(exportOut, name), exportFormat)
				iterator = 1
				while os.path.exists(outFile):
					outFile = '{0}_{2}{1}'.format(os.path.join(exportOut, name), exportFormat, iterator)
					iterator += 1
				self.tuPlot.drawPlot(TuPlot.CrossSection, data, labels, types, dataTypes, export=outFile)
			elif export == 'csv':  # export to csv, don't plot
				self.tuPlot.exportCSV(TuPlot.CrossSection, data, labels, types, exportOut, name)
			else:  # catch all other cases and just do normal, although should never be triggered
				self.tuPlot.drawPlot(TuPlot.CrossSection, data, labels, types, dataTypes, draw=draw)
		
		return True
	
	def plotFlowFromMap(self, vLayer, feat, **kwargs):
		"""
		Initiate flow plotting using XY coordinates

		:param vLayer: QgsVectorLayer
		:param feat: QgsFeature
		:param kwargs: bool bypass
		:return: bool -> True for successful, False for unsuccessful
		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot
		from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesults import TuResults

		debug = self.tuView.tuOptions.writeMeshIntersects
		activeMeshLayers = self.tuResults.tuResults2D.activeMeshLayers  # list
		results = self.tuResults.results  # dict
		
		# Check that line is a polyline
		if vLayer is not None:  # if none then memory layer
			if vLayer.geometryType() != QgsWkbTypes.LineGeometry:
				return
			crs = vLayer.sourceCrs()
		else:
			crs = self.tuView.project.crs()
				
		# deal with the kwargs
		bypass = kwargs['bypass'] if 'bypass' in kwargs.keys() else False  # bypass clearing any data from plot
		plot = kwargs['plot'] if 'plot' in kwargs.keys() else ''
		draw = kwargs['draw'] if 'draw' in kwargs.keys() else True
		time = kwargs['time'] if 'time' in kwargs.keys() else None
		showCurrentTime = kwargs['show_current_time'] if 'show_current_time' in kwargs.keys() else False
		#meshRendered = kwargs['mesh_rendered'] if 'mesh_rendered' in kwargs.keys() else True
		meshRendered = False  # finding values manually is a little quicker
		resolution = kwargs['resolution'] if 'resolution' in kwargs.keys() else self.tuView.tuOptions.resolution
		featName = kwargs['featName'] if 'featName' in kwargs else None
		
		# clear the plot based on kwargs
		if bypass:
			pass
		else:
			# if plot.lower() == 'flow only':
			# 	self.tuPlot.clearPlot(1)
			# else:
			# 	self.tuPlot.clearPlot(1, retain_1d=True, retain_2d=True)
			self.tuPlot.clearPlot2(TuPlot.TimeSeries, TuPlot.DataFlow2D)

		# initialise plotting variables
		xAll = []
		yAll = []
		labels = []
		types = []
		dataTypes = []

		# iterate through all selected results
		for layer in activeMeshLayers:
			dp = layer.dataProvider()
			mesh = QgsMesh()
			dp.populateMesh(mesh)
			si = QgsMeshSpatialIndex(mesh)

			# get velocity and either depth or water level
			depth = None
			velocity = None
			waterLevel = None
			bedElevation = None

			for resultType in results[layer.name()]:
				if TuResults.isMapOutputType(resultType) and not TuResults.isMaximumResultType(resultType) \
						and not TuResults.isMinimumResultType(resultType):
					if 'vel' in resultType.lower() and 'time' not in resultType.lower() and 'dur' not in resultType.lower():  # make sure it's vector dataset
						velocityTRI = TuResultsIndex(layer.name(), resultType, None, False)
						velRes = self.tuView.tuResults.getResult(velocityTRI)
						for t in velRes:
							mdGroup = layer.dataProvider().datasetGroupMetadata(velRes[t][-1])
							break  # only need first one to get group index
						if mdGroup.isVector():
							velocity = resultType
					elif resultType[0].lower() == 'v' and 'time' not in resultType.lower() and 'dur' not in resultType.lower():
						velRes = resultType
						velocityTRI = TuResultsIndex(layer.name(), resultType, None, False)
						velRes = self.tuView.tuResults.getResult(velocityTRI)
						for t in velRes:
							mdGroup = layer.dataProvider().datasetGroupMetadata(velRes[t][-1])
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

			# get mesh intercepts and faces
			gmd = None
			for key, item in velRes.items():
				gmd = layer.dataProvider().datasetGroupMetadata(item[-1].group())
				break
			inters, ch, faces = findMeshIntersects(si, dp, mesh, feat, crs,
			                                             self.tuView.project)
			if gmd.dataType() == QgsMeshDatasetGroupMetadata.DataOnVertices:
				points = inters[:]
				points = inters[0:1]
				points.extend([calcMidPoint(inters[i], inters[i + 1], crs) for i in range(len(inters) - 1)])
				points.append(inters[-1])
				chainages = ch[0:1]
				chainages.extend([(ch[i] + ch[i + 1]) / 2. for i in range(len(ch) - 1)])
				chainages.append(ch[-1])
				faces = [None] * len(points)
				if debug:
					writeTempPoints(inters, self.tuView.project, crs, chainages, 'Chainage',
					                QVariant.Double)
			else:
				points = faces[:]
				chainages = ch[:]
				if debug:
					polys = [meshToPolygon(mesh, mesh.face(x)) for x in faces]
					writeTempPolys(polys, self.tuView.project, crs)
					writeTempPoints(inters, self.tuView.project, crs, chainages, 'Chainage',
					                QVariant.Double)

			# get directions
			directions = [None]
			for j, point in enumerate(points[1:]):
				directions.append(getDirection(points[j], point))

			# initialise progress bar
			noFeatures = 1
			noPoints = len(points)
			noTimesteps = []
			for resultType in results[layer.name()]:
				if TuResults.isMapOutputType(resultType) and not TuResults.isMaximumResultType(resultType) \
						and not TuResults.isMinimumResultType(resultType) \
						and 'bed elevation' not in resultType.lower() and 'time' not in resultType and \
						'dur' not in resultType:
				# if '_ts' not in resultType and '_lp' not in resultType and 'Maximum' not in resultType and \
				# 		'bed elevation' not in resultType.lower() and 'time' not in resultType and \
				# 		'dur' not in resultType:
					tuResultsIndex = TuResultsIndex(layer.name(), resultType, None, False)
					res = self.tuView.tuResults.getResult(tuResultsIndex)
					if len(res) > 1:
						noTimesteps.append(len(res))
						break
			maxProgress = 0
			for ts in noTimesteps:
				maxProgress += noFeatures * noPoints * ts
			if maxProgress:
				self.tuView.progressBar.setVisible(True)
				self.tuView.progressBar.setRange(0, 100)
				self.tuView.progressBar.setValue(0)
				pComplete = 0
				complete = 0
			else:
				return False

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
					#if not meshRendered:
					#	# pre-render means that we need to
					#	# manually go get mesh face indexes
					#	# then interpolate value from mesh vertices
					#	if i == 0:
					#		# first round - go get mesh faces that
					#		# points fall in. If graphing for more than
					#		# one result - don't need to do this step again
					#		success = self.getFaceIndexes2(si, dp, points, mesh)
					#		if not success:
					#			return False
					#		if len(self.faceIndexes) != len(points):
					#			return False

					chainage = chainages[i]
					direction = directions[i]
					# qpoint = QgsPointXY(point)

					# get depth - either directly or through water level and bed elevation
					if depth is not None:
						depthMag = self.datasetValue(layer, dp, si, mesh, results[layer.name()][depth]['times'][key][-1],
						                           meshRendered, point, 0, TuPlot.DataFlow2D, None, faces[i])
					else:
						wlMag = self.datasetValue(layer, dp, si, mesh, results[layer.name()][waterLevel]['times'][key][-1],
						                          meshRendered, point, 0, TuPlot.DataFlow2D, None, faces[i])
						bedMag = self.datasetValue(layer, dp, si, mesh, results[layer.name()][bedElevation]['times'][key][-1],
						                           meshRendered, point, 0, TuPlot.DataFlow2D, None, faces[i])
						depthMag = wlMag - bedMag
					if qIsNaN(depthMag):
						depthMag = 0
						
					if depthMag > 0:
						velDataValue = self.datasetValue(layer, dp, si, mesh, velItem[-1], meshRendered, point, 0,
						                                 TuPlot.DataFlow2D, None, faces[i], value='vector')
						velMag = velDataValue[0]
						velX = velDataValue[1]
						velY = velDataValue[2]

						if qIsNaN(velMag):
							velMag = 0
					else:
						velMag = 0
						velX = 0
						velY = 0

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
						self.tuView.progressBar.setValue(pComplete)
						QgsApplication.processEvents()

				# summed all flow, can append to timestep
				y.append(sumFlow)

			# add to overall data list
			xAll.append(x)
			yAll.append(y)

			if featName is None:  # rubberband layer
				if bypass or self.tuView.cboSelectType.currentText() == 'From Map Multi':
					label = '2D Map Flow - Location {0}'.format(self.multiFlowLineSelectCount) if len(activeMeshLayers) < 2 \
						else '{0} - 2D Map Flow - location {1}'.format(layer.name(), self.multiFlowLineSelectCount)
					self.multiFlowLineSelectCount += 1
				else:
					label = '2D Map Flow' if len(activeMeshLayers) < 2 else '{0} - 2D Map Flow'.format(layer.name())
			else:  # use attribute from selected feature
				label = '2D Map Flow - {0}'.format(featName) if len(activeMeshLayers) < 2 else \
					'{0} - 2D Map Flow - {1}'.format(layer.name(), featName)
			labels.append(label)
			types.append('2D Flow')
		
		self.tuView.progressBar.setVisible(False)

		data = list(zip(xAll, yAll))
		dataTypes = [TuPlot.DataFlow2D] * len(data)
		self.tuPlot.drawPlot(0, data, labels, types, dataTypes, draw=draw, time=time, show_current_time=showCurrentTime)

		return True
	
	def findMeshFaceIntersects(self, p1, p2, si, dp, mesh, mapUnits):
		"""

		"""

		feat = QgsFeature()
		feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(p1.x(), p1.y()), QgsPoint(p2.x(), p2.y())]))
		points, chainages, directions = lineToPoints(feat, 1, mapUnits)
		return self.getFaceIndexes3(si, dp, points, mesh)

	def findMeshSideIntersects(self, p1, p2, faces, mesh):
		"""

		"""

		v_used = []
		p_intersects = [p1]
		for f in faces:
			vs = mesh.face(f)
			for i, v in enumerate(vs):
				if i == 0:
					f1 = v
				else:
					p3 = mesh.vertex(vs[i-1])
					p4 = mesh.vertex(v)
					if doLinesIntersect(p1, p2, p3, p4):
						if sorted([vs[i-1], v]) not in v_used:
							newPoint = intersectionPoint(p1, p2, p3, p4)
							p_intersects.append(newPoint)
							v_used.append(sorted([vs[i-1], v]))
					elif i + 1 == len(vs):
						p3 = mesh.vertex(v)
						p4 = mesh.vertex(f1)
						if doLinesIntersect(p1, p2, p3, p4):
							if sorted([f1, v]) not in v_used:
								newPoint = intersectionPoint(p1, p2, p3, p4)
								p_intersects.append(newPoint)
								v_used.append(sorted([f1, v]))

		return p_intersects

	def findMeshIntersects(self, si, dp, mesh, feat, mapUnits):
		"""

		"""

		if feat.geometry().wkbType() == QgsWkbTypes.LineString:
			geom = feat.geometry().asPolyline()
		elif feat.geometry().wkbType() == QgsWkbTypes.MultiLineString:
			mGeom = feat.geometry().asMultiPolyline()
			geom = []
			for g in mGeom:
				for p in g:
					geom.append(p)
		else:
			return

		points = []
		chainages = []
		for i, p in enumerate(geom):
			if i > 0:
				faces = self.findMeshFaceIntersects(geom[i-1], p, si, dp, mesh, mapUnits)
				inter = self.findMeshSideIntersects(geom[i-1], p, faces, mesh)
				if inter:
					points += inter
			if i + 1 == len(geom):
				points.append(p)

		chainage = 0
		chainages.append(chainage)
		for i, p in enumerate(points):
			if i > 0:
				chainage += calculateLength(p, points[i-1], mapUnits)
				chainages.append(chainage)

		# debug
		crs = self.tuView.project.crs()
		uri = "point?crs={0}".format(crs.authid().lower())
		lyr = QgsVectorLayer(uri, "check_face_intercepts", "memory")
		dp = lyr.dataProvider()
		dp.addAttributes([QgsField('Ch', QVariant.Double)])
		lyr.updateFields()
		feats = []
		for i, point in enumerate(points):
			feat = QgsFeature()
			feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
			feat.setAttributes([chainages[i]])
			feats.append(feat)
		dp.addFeatures(feats)
		lyr.updateExtents()
		self.tuView.project.addMapLayer(lyr)

	def findMeshIntersects2(self, si, dp, mesh, feat, mapUnits):
		"""

		"""

		if feat.geometry().wkbType() == QgsWkbTypes.LineString:
			geom = feat.geometry().asPolyline()
		elif feat.geometry().wkbType() == QgsWkbTypes.MultiLineString:
			mGeom = feat.geometry().asMultiPolyline()
			geom = []
			for g in mGeom:
				for p in g:
					geom.append(p)

		points = []
		chainages = []
		chainage = 0
		pPrev = None
		facePrev = None
		for i, p in enumerate(geom):
			if i == 0:
				points.append(p)
				chainages.append(0)
				pPrev = p
			else:
				nextPoint = False
				while not nextPoint:
					face = self.getFaceIndexes3(si, dp, pPrev, mesh, facePrev)
					found = False
					for j, fp in enumerate(mesh.face(face)):
						if j == 0:
							fpPrev = fp
							continue
						if j + 1 == len(mesh.face(face)):  # last vertex back to first vertex
							if doLinesIntersect(pPrev, p, mesh.vertex(mesh.face(face)[0]), mesh.vertex(fp)):
								newPoint = intersectionPoint(pPrev, p, mesh.vertex(fp), mesh.vertex(fpPrev))
								length = calculateLength(newPoint, pPrev, mapUnits)
								chainage += length
								points.append(newPoint)
								chainages.append(chainage)
								found = True
								break
						if doLinesIntersect(pPrev, p, mesh.vertex(fp), mesh.vertex(fpPrev)):
							newPoint = intersectionPoint(pPrev, p, mesh.vertex(fp), mesh.vertex(fpPrev))
							length = calculateLength(newPoint, pPrev, mapUnits)
							chainage += length
							points.append(newPoint)
							chainages.append(chainage)
							found = True
							break
					if found:
						pPrev = newPoint
						facePrev = face
					else:
						nextPoint = True
			if i + 1 == len(geom):
				points.append(p)
				length = calculateLength(newPoint, pPrev, mapUnits)
				chainage += length
				chainages.append(chainage)

		# debug
		printpoints = []
		for p in points:
			printpoints.append("({0:0.03f}, {1:0.03f}".format(p.x(), p.y()))
		QMessageBox.information(self.tuView, "Debug", "points:\n{0}".format('\n'.join(printpoints)))

	def getFaceIndexes3(self, si: QgsMeshSpatialIndex, dp: QgsMeshDataProvider, points: list, mesh: QgsMesh) -> list:
		"""


		:param si:
		:param dp:
		:param points:
		:return:
		"""

		if not points:
			return []
		points = [QgsPointXY(x) for x in points]

		faceIndexes = []
		for p in points:
			indexes = si.nearestNeighbor(p, 1)
			if indexes:
				if len(indexes) == 1:
					if indexes[0] not in faceIndexes:
						faceIndexes.append(indexes[0])
				else:
					for ind in indexes:
						f = self.meshToPolygon(mesh, mesh.face(ind))
						if f.geometry().contains(p):
							if ind not in faceIndexes:
								faceIndexes.append(ind)
							break

		return faceIndexes

	def getFaceIndexes2(self, si: QgsMeshSpatialIndex, dp: QgsMeshDataProvider, points: list, mesh: QgsMesh) -> bool:
		"""
		
		
		:param si:
		:param dp:
		:param points:
		:return:
		"""
		
		if not points:
			return False
		points = [QgsPointXY(x) for x in points]
		
		self.faceIndexes.clear()
		for p in points:
			indexes = si.nearestNeighbor(p, 1)
			if indexes:
				if len(indexes) == 1:
					self.faceIndexes.append(indexes[0])
				else:
					for ind in indexes:
						f = self.meshToPolygon(mesh, mesh.face(ind))
						if f.geometry().contains(p):
							self.faceIndexes.append(ind)
							break
			
		if len(self.faceIndexes) == len(points):
			return True
		else:
			return False
	
	
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
	
	def activeAvgMethod(self, rs):
		"""
		Returns active depth averaging method from QGIS (not anything in tuflow viewer)
		"""

		return rs.averagingMethod()

	def datasetValueAvgDep(self, layer, res, p, avgmethod, dataType, restype='scalar', face=None):
		"""
        Calculate depth average value. Not needed for 2D datasets, but will be required for subclassing
        when plotting from 3D datasets.
        """

		if face is None:
			dataset3d = layer.dataset3dValue(res, p)
		else:
			dataset3d = layer.dataProvider().dataset3dValues(res, face, 1)
		if isinstance(avgmethod, QgsMesh3dAveragingMethod):
			mdb = avgmethod.calculate(dataset3d)  # mesh data block
		else:
			mdb = self.calculateAverage(dataType, avgmethod, dataset3d)

		if mdb.isValid():
			if len(mdb.values()) > 1:
				if restype == 'scalar':
					return (mdb.values()[0] ** 2 + mdb.values()[1] ** 2) ** 0.5
				elif restype == 'x':
					return mdb.values()[0]
				elif restype == 'y':
					return mdb.values()[1]
			else:
				return mdb.values()[0]
		else:  # probably 2d result
			if face is None:
				mdb = layer.datasetValue(res, p)
			else:
				mdb = layer.dataProvider().datasetValue(res, face)
			return eval("mdb.{0}()".format(restype))

	def datasetValueAvgDep2(self, dp, res, v, f, avgmethod, restype, dataType):
		"""
		When the mesh hasn't been rendered yet, use this one.
		"""

		if f is not None:
			dataset3d = dp.dataset3dValues(res, f, 1)
			if isinstance(avgmethod, QgsMesh3dAveragingMethod):
				mdb = avgmethod.calculate(dataset3d)  # mesh data block
			else:
				mdb = self.calculateAverage(dataType, avgmethod, dataset3d)
			if not mdb.isValid(): return
			if len(mdb.values()) > 1:
				if restype == 'scalar':
					return (mdb.values()[0] ** 2 + mdb.values()[1] ** 2) ** 0.5
				elif restype == 'x':
					return mdb.values()[0]
				elif restype == 'y':
					return mdb.values()[1]
			else:
				return mdb.values()[0]

	def datasetValue(self, layer, dp, si, mesh, mdi, meshRendered, point, ind, dataType, avgmethod=None,
	                 face=None, value='scalar'):
		"""

		"""

		# if face, then cell centred results
		if face is not None:
			if avgmethod is None:
				avgmethod = self.activeAvgMethod(layer.rendererSettings())
			return self.datasetValueAvgDep(layer, mdi, point, avgmethod, dataType, value, face)

		if meshRendered:
			if avgmethod is None:
				return layer.datasetValue(mdi, QgsPointXY(point)).scalar()
			else:
				return self.datasetValueAvgDep(layer, mdi, QgsPointXY(point), avgmethod, dataType)
		else:
			if ind == 0:
				# first round - go get mesh faces that
				# point fall in. If graphing for more than
				# one result - don't need to do this step again
				success = self.getFaceIndexes2(si, dp, [QgsPointXY(point)], mesh)
				if not success:
					return
				if len(self.faceIndexes) != 1:
					return
			return self.preRenderDatasetValue(mesh, layer, si, mdi, self.faceIndexes[0], QgsPointXY(point), dataType, value)

	def preRenderDatasetValue(self, mesh, layer, si, result, faceIndex, point, dataType, value='scalar', avgmethod=None):
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

		if dp.datasetGroupMetadata(result.group()).dataType() == QgsMeshDatasetGroupMetadata.DataOnVertices:
			return self.interpolateFromVerts(mesh, dp, result, face, point, value, avgmethod)
		else:
			return self.dataFromMeshIndex(layer, dp, result, faceIndex, value, avgmethod, dataType)

	def dataFromMeshIndex(self, layer, dp, result, faceIndex, value, avgmethod, dataType):

		if avgmethod is None:
			avgmethod = self.activeAvgMethod(layer.rendererSettings())

		if value == 'vector':
			z = self.datasetValueAvgDep2(dp, result, None, faceIndex, avgmethod, 'scalar', dataType)
			x = self.datasetValueAvgDep2(dp, result, None, faceIndex, avgmethod, 'x', dataType)
			y = self.datasetValueAvgDep2(dp, result, None, faceIndex, avgmethod, 'y', dataType)
			return (z, x, y)
		else:
			return self.datasetValueAvgDep2(dp, result, None, faceIndex, avgmethod, value, dataType)

	def interpolateFromVerts(self, mesh, dp, result, face, point, value, avgmethod):

		# use Barycentric Coordinates and triangles to get interpolated value
		# https://codeplea.com/triangular-interpolation
		# so first get triangle
		if len(face) == 4:
			# split into triangles and determine which
			# triangle point falls in
			triangle1 = face[:3]
			ftri1 = self.meshToPolygon(mesh, triangle1)
			if ftri1.geometry().contains(point):
				#tri = triangle1
				tri = face[1::-1] + face[2:3]  # reorder so first 2 vertexes are one after the other e.g. [10, 11, x]
			else:
				triangle2 = face[2:] + face[0:1]
				ftri2 = self.meshToPolygon(mesh, triangle2)
				if ftri2.geometry().contains(point):
					tri = triangle2
				else:
					return np.nan
		elif len(face) == 3:
			if face[1] + 1 == face[0]:
				tri = face[1::-1] + face[2:3]  # reorder so first 2 vertexes are one after the other e.g. [10, 11, x]
			else:
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
		x = 0
		y = 0
		#for i, v in enumerate(tri):
		# re-did below func to call sequential vertexes in datasetValue(s) call so the number of times datasetValue is
		# called is reduced as this seems to be the time conuming part
		i = 0
		for j in range(2):
			v = tri[i]
			if j == 0:
				db = dp.datasetValues(result, v, 2)
				for k in range(2):
					if value == 'scalar':
						z += db.value(k).scalar() * w[i]
					elif value == 'vector':
						res = db.value(k)
						z += res.scalar() * w[i]
						x += res.x() * w[i]
						y += res.y() * w[i]
					i += 1
			else:
				if value == 'scalar':
					if avgmethod is None:
						z += dp.datasetValue(result, v).scalar() * w[i]
					else:
						z += self.datasetValueAvgDep2(dp, result, v, None, avgmethod, value) * w[i]
				elif value == 'x':
					if avgmethod is None:
						z += dp.datasetValue(result, v).x() * w[i]
					else:
						z += self.datasetValueAvgDep2(dp, result, v, None, avgmethod, value) * w[i]
				elif value == 'y':
					if avgmethod is None:
						z += dp.datasetValue(result, v).y() * w[i]
					else:
						z += self.datasetValueAvgDep2(dp, result, v, None, avgmethod, value) * w[i]
				elif value == 'vector':
					if avgmethod is None:
						res = dp.datasetValue(result, v)
						z += res.scalar() * w[i]
						x += res.x() * w[i]
						y += res.y() * w[i]
					else:
						z += self.datasetValueAvgDep2(dp, result, v, None, avgmethod, 'scalar') * w[i]
						x += self.datasetValueAvgDep2(dp, result, v, None, avgmethod, 'x') * w[i]
						y += self.datasetValueAvgDep2(dp, result, v, None, avgmethod, 'y') * w[i]

		if value == 'scalar':
			return z
		elif value == 'vector':
			return (z, x, y)
		
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

	def calculateAverage(self, dataType, averagingMethod, dataset3d, params=None):
		"""
        Calculate depth averaged result using averagingMethod

        """

		param = self.tuPlot.tuPlotToolbar.getAveragingParameters(dataType, averagingMethod)
		if param is None: return None

		if "Single Vertical Level" in averagingMethod:
			if len(param) < 1: return None
			param = param[0]
			ft = 'from top' in averagingMethod  # from top
			mam = QgsMeshMultiLevelsAveragingMethod(param, ft)  # mesh averaging method
		elif 'Multi Vertical Level' in averagingMethod:
			if len(param) < 2: return None
			a, b = param[:2]
			ft = 'from top' in averagingMethod  # from top
			mam = QgsMeshMultiLevelsAveragingMethod(a, b, ft)  # mesh averaging method
		elif 'Sigma' in averagingMethod:
			if len(param) < 2: return None
			a, b = param[:2]
			mam = QgsMeshSigmaAveragingMethod(a, b)  # mesh averaging method
		elif 'relative to' in averagingMethod:
			if len(param) < 2: return None
			a, b = param[:2]
			ft = 'surface' in averagingMethod  # from top
			mam = QgsMeshRelativeHeightAveragingMethod(a, b, ft)  # mesh averaging method
		elif 'absolute to' in averagingMethod:
			if len(param) < 2: return None
			a, b = param[:2]
			mam = QgsMeshElevationAveragingMethod(a, b)  # mesh averaging method

		return mam.calculate(dataset3d)

	def getAveragingMethods(self, dataType, gmd,  resultTypes):
		"""

		"""

		return [None] * len(resultTypes)

	def generateLabel(self, layer, resultMesh, rtype, markerNo, featName,
	                  activeMeshLayers, am, export, bypass, ia, dataType):
		"""

		"""

		if am is not None:
			menu = self.tuPlot.tuPlotToolbar.plotDataToPlotMenu[dataType].parentWidget()
			rtype = menu.checkedActionsParamsToText()[ia]

		label = None
		if export:
			if featName is None:
				label = '{0}'.format(rtype) if len(resultMesh) == 1 else '{1}: {0}'.format(rtype, layer.name())
			else:
				label = '{0}: {1}'.format(rtype, featName) if len(resultMesh) == 1 else \
					'{1}: {0}: {2}'.format(rtype, layer.name(), featName)
		else:
			if featName is None:
				if bypass or self.tuView.cboSelectType.currentText() == 'From Map Multi' and markerNo > 0:
					label = '{0} - point {1}'.format(rtype, markerNo) if len(
						activeMeshLayers) < 2 else '{0} - {1} - point {2}'.format(layer.name(), rtype,
					                                                              markerNo)
				# normal single point click
				else:
					label = '{0}'.format(rtype) if len(activeMeshLayers) < 2 else '{0} - {1}'.format(layer.name(),
					                                                                                 rtype)
			else:
				label = label = '{0}: {1}'.format(rtype, featName) if len(activeMeshLayers) < 2 else \
					'{0} - {1}: {2}'.format(layer.name(), rtype, featName)

		return label