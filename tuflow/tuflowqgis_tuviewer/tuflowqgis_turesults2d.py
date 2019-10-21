import os
import sys
from datetime import datetime, timedelta
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets import *
from qgis.PyQt.QtXml import QDomDocument
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesultsindex import TuResultsIndex
from tuflow.tuflowqgis_library import tuflowqgis_find_layer, findAllMeshLyrs, loadSetting, roundSeconds, \
	getPropertiesFrom2dm



class TuResults2D():
	"""
	Class for handling 2D results
	
	"""
	
	def __init__(self, TuView):
		self.tuView = TuView
		self.iface = TuView.iface
		self.rsScalar = QgsMeshRendererScalarSettings()
		self.rsVector = QgsMeshRendererVectorSettings()
		self.activeMeshLayers = []  # list of selected QgsMeshLayer (layer.type() == 3)
		self.activeScalar = None  # active scalar to be rendered e.g. depth
		self.activeVector = None  # active vector to be rendered e.g. velocity vector
		self.activeDatasets = []  # list of active result datasets including time series and long plots
		self.activeScalar, self.activeVector = None, None
		self.meshProperties = {}
		self.results2d = {}  # holds 2d properties e.g. 'path'
	
	def importResults(self, inFileNames):
		"""
		Imports function that opens result mesh layer

		:param inFileNames: list -> str - full path to mesh result file
		:return: bool -> True for successful, False for unsuccessful
		"""

		# disconnect incoming signals for load step
		skipConnect = False
		try:
			self.tuView.project.layersAdded.disconnect(self.tuView.layersAdded)
		except:
			skipConnect = True
			pass
		meshLayers = findAllMeshLyrs()
		for ml in meshLayers:
			layer = tuflowqgis_find_layer(ml)
			try:
				layer.dataProvider().datasetGroupsAdded.disconnect(self.datasetGroupsAdded)
			except:
				pass

		for j, f in enumerate(inFileNames):

			# Load Mesh
			if type(inFileNames) is dict:  # being loaded in from a sup file
				m = inFileNames[f]['mesh']
				mLayer, name, preExisting = self.loadMeshLayer(m, name=f)
			else:
				mLayer, name, preExisting = self.loadMeshLayer(f)
			if mLayer is None or name is None:
				if not skipConnect:
					self.tuView.project.layersAdded.connect(self.tuView.layersAdded)
				return False
			
			# Load Results
			if type(inFileNames) is dict:  # being loaded in from a sup file
				datasets = inFileNames[f]['datasets']
				for d in datasets:
					l = self.loadDataGroup(d, mLayer, preExisting)
			else:
				loaded = self.loadDataGroup(f, mLayer, preExisting)
			#res = {'path': f}
			#self.results2d[mLayer.name()] = res
			
			# Open layer in map
			self.tuView.project.addMapLayer(mLayer)
			name = mLayer.name()
			mLayer.nameChanged.connect(lambda: self.layerNameChanged(mLayer, name, mLayer.name()))  # if name is changed can capture this in indexing
			
			rs = mLayer.rendererSettings()
			rsMesh = rs.nativeMeshSettings()
			rsMesh.setEnabled(self.tuView.tuOptions.showGrid)
			rs.setNativeMeshSettings(rsMesh)
			mLayer.setRendererSettings(rs)
			#mLayer.repaintRequested.connect(lambda: self.tuView.repaintRequested(mLayer))
			
			# Index results
			ext = os.path.splitext(f)[-1]  # added because .dat scalar and vector need to be combined
			index = self.getResultMetaData(name, mLayer, ext)
			if not index:
				if not skipConnect:
					self.tuView.project.layersAdded.connect(self.tuView.layersAdded)
				return False
			
			# add to result list widget
			names = []
			for i in range(self.tuView.OpenResults.count()):
				if self.tuView.OpenResults.item(i).text() not in names:
					names.append(self.tuView.OpenResults.item(i).text())
			if name not in names:
				self.tuView.OpenResults.addItem(name)  # add to widget
			k = self.tuView.OpenResults.findItems(name, Qt.MatchRecursive)[0]
			k.setSelected(True)
			updated = self.updateActiveMeshLayers()  # update list of active mesh layers
			if not updated:
				if not skipConnect:
					self.tuView.project.layersAdded.connect(self.tuView.layersAdded)
				return False
			self.tuView.resultChangeSignalCount = 0  # reset signal count back to 0
		
		# connect load signals
		if not skipConnect:
			self.tuView.project.layersAdded.connect(self.tuView.layersAdded)
		meshLayers = findAllMeshLyrs()
		for ml in meshLayers:
			layer = tuflowqgis_find_layer(ml)
			layer.dataProvider().datasetGroupsAdded.connect(self.datasetGroupsAdded)

			
		return True
		
	def loadMeshLayer(self, fpath, **kwargs):
		"""
		Load the mesh layer i.e. .xmdf

		:param fpath: str
		:return: QgsMeshLayer
		:return: str
		"""

		# deal with kwargs
		name = kwargs['name'] if 'name' in kwargs else None

		# Parse out file names
		basepath, fext = os.path.splitext(fpath)
		basename = os.path.basename(basepath)
		dirname = os.path.dirname(basepath)
		
		# does mesh layer already exist in workspace
		layer = tuflowqgis_find_layer(basename)
		if layer is not None:
			return layer, basename, True
		# TUFLOW FV 2dm is named differently so also check provided name does not exist
		if name is not None:
			layer_alternative = tuflowqgis_find_layer(name)
			if layer_alternative is not None:
				return layer_alternative, name, True
		
		if fext.lower() == '.xmdf' or fext.lower() == '.dat' or fext.lower() == '.2dm':
			mesh = '{0}.2dm'.format(basepath)
			basename_copy = basename
			while not os.path.exists(mesh):  # put in for res_to_res results e.g. M01_5m_002_V_va.xmdf (velocity angle)
				components = basename_copy.split('_')
				components.pop()
				if not components:
					break
				basename_copy = '_'.join(components)
				mesh = '{0}.2dm'.format(os.path.join(dirname, basename_copy))
			if not os.path.exists(mesh):
				# ask user for location
				inFileNames = QFileDialog.getOpenFileNames(self.tuView.iface.mainWindow(), 'Mesh file location', fpath,
				                                           "TUFLOW Mesh File (*.2dm)")
				if not inFileNames[0]:  # empty list
					return None, None, False
				else:
					if os.path.exists(inFileNames[0][0]):
						mesh = inFileNames[0][0]
					else:
						QMessageBox.information(self.iface, "TUFLOW Viewer", "Could not find mesh file")
						return None, None, False
		else:
			QMessageBox.information(self.iface.mainWindow(), "TUFLOW Viewer", "Must select a .xmdf .dat .sup or .2dm file type")
			return None, None, False
			
		# Load mesh if layer does not exist already
		name = basename if name is None else name
		layer = QgsMeshLayer(mesh, name, 'mdal')
		if layer.isValid():
			prop = {}
			cellSize, wllVerticalOffset, origin, orientation, gridSize = getPropertiesFrom2dm(mesh)
			prop['cell size'] = cellSize
			prop['wll vertical offset'] = wllVerticalOffset
			prop['origin'] = origin
			prop['orientation'] = orientation
			prop['grid size'] = gridSize
			self.meshProperties[name] = prop
			self.tuView.tuOptions.resolution = cellSize
			return layer, name, False
		
		QMessageBox.information(self.iface.mainWindow(), "TUFLOW Viewer", "Could not load mesh file")
		return None, None, False
	
	def loadDataGroup(self, fpath, layer, preExisting):
		"""
		Add results to mesh layer

		:param fpath: str
		:param layer: QgsMeshLayer
		:param preExisting: bool -> if the mesh is pre-existingi in workspace
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# Parse out file names
		basepath, fext = os.path.splitext(fpath)
		basename = os.path.basename(basepath)
		mesh = '{0}.2dm'.format(basepath)
		if fext.lower() == '.xmdf' or fext.lower() == '.dat':
			dataGroup = fpath
		else:
			return False  # No datasets loaded because extension not recognised
		
		# check if datagroup has already been loaded
		if preExisting:
			if layer.dataProvider().datasetGroupCount() > 1:
				if fext.lower() == '.xmdf':
					# return False  # most likely already loaded
					pass  # better off leaving this until better logic is possible
					
		# load results onto mesh
		dp = layer.dataProvider()
		try:
			dp.addDataset(dataGroup)
			return True  # successful
		except:
			return False  # unsuccessful
		
	def getDatasetGroupTypes(self, layer):
		"""
		Collects dataset group types i.e. depth. Will ignore Bed Elevation. Will accept both file path or QgsMeshLayer
		
		:param layer: QgsMeshLayer or str -> mesh location i.e. .xmdf
		:return: list -> str types
		"""
		
		types = []
		
		if type(layer) == QgsMeshLayer:
			for i in range(layer.dataProvider().datasetGroupCount()):
				groupName = layer.dataProvider().datasetGroupMetadata(i).name()
				if groupName.lower() != 'bed elevation':
					types.append(groupName)
					
		elif type(layer) == str:
			# load mesh layer
			mLayer, basename, preExisting = self.loadMeshLayer(layer)
			# load dataset group assuming it's not pre-existing
			self.loadDataGroup(layer, mLayer, False)
			# loop through dataset groups as per above loop
			for i in range(mLayer.dataProvider().datasetGroupCount()):
				groupName = mLayer.dataProvider().datasetGroupMetadata(i).name()
				if groupName.lower() != 'bed elevation':
					types.append(groupName)
					
		return types
	
	def getResultMetaData(self, name, layer, ext=''):
		"""
		Get all the result types and timesteps for 2D results.

		:param layer: QgsMeshLayer
		:return: bool -> True for successful, False for unsuccessful
		"""

		results = self.tuView.tuResults.results  # dict
		timekey2time = self.tuView.tuResults.timekey2time  # dict
		timekey2date = self.tuView.tuResults.timekey2date  # dict
		time2date = self.tuView.tuResults.time2date  # dict
		date2timekey = self.tuView.tuResults.date2timekey  # dict
		date2time = self.tuView.tuResults.date2time  # dict
		zeroTime = self.tuView.tuOptions.zeroTime
		
		if name not in results.keys():  # add results to dict
			results[name] = {}
		
		timesteps, maxResultTypes, temporalResultTypes = [], [], []
		dp = layer.dataProvider()  # QgsMeshDataProvider
		
		for i in range(dp.datasetGroupCount()):
			
			# Get result type e.g. depth, velocity, max depth
			mdGroup = dp.datasetGroupMetadata(i)  # Group Metadata
			if mdGroup.isScalar() or ext.upper() == '.DAT':
				type = 1
			else:
				type = 2

			if self.tuView.tuResults.isMaximumResultType(mdGroup.name(), dp, i):
				# get result group name
				rt = mdGroup.name().split('/')[0]
				if 'max_' in rt:
					rt = rt.split('max_')[1]
					mdGroupName = '{0}/Maximums'.format(rt)  # FV
				elif 'minimum dt' in rt.lower():
					mdGroupName = '{0}/Final'.format(rt)  # special treatment for Minimum dt
				else:
					mdGroupName = mdGroup.name()
				
				# check for duplicates - if there are duplicates add [1] or [2] ... [n] to name
				if mdGroupName in maxResultTypes:
					counter = 1
					mdGroupName = '{0} [{1}]'.format(mdGroupName, counter)
					while mdGroupName in maxResultTypes:
						mdGroupName = mdGroupName.replace('[{0}]'.format(counter), '[{0}]'.format(counter + 1))
						counter += 1
				
				# add to max result type list
				maxResultTypes.append(mdGroupName)
				#rt = mdGroup.name().split('/')[0]
				#if 'max_' in rt:
				#	rt = rt.split('max_')[1]
				#	mdGroupName = '{0}/Maximums'.format(rt)  # FV
				#else:
				#	mdGroupName = mdGroup.name()
				#maxResultTypes.append(rt)
				
				# initiate in results dict
				results[name][mdGroupName] = {}  # add result type to results dictionary
				
				# add max result as time -99999
				results[name][mdGroupName]['-99999'] = (-99999, type, QgsMeshDatasetIndex(i, 0))
				timekey2time['-99999'] = -99999
				timekey2date['-99999'] = -99999
				time2date['-99999'] = -99999
				date2timekey[-99999] = '-99999'
				date2time[-99999] = '-99999'
				
				# apply any default rendering styles to datagroup
				if mdGroup.isScalar() or ext.upper() == '.DAT':
					resultType = mdGroup.name().split('/')[0]
					if 'max_' in resultType:
						resultType = resultType.split('max_')[1]
					# try finding if style has been saved as a ramp first
					key = 'TUFLOW_scalarRenderer/{0}_ramp'.format(resultType)
					file = QSettings().value(key)
					if file:
						self.applyScalarRenderSettings(layer, i, file, type='ramp')
					# else try map
					key = 'TUFLOW_scalarRenderer/{0}_map'.format(resultType)
					file = QSettings().value(key)
					if file:
						self.applyScalarRenderSettings(layer, i, file, type='map')
				if mdGroup.isVector():
					vectorProperties = QSettings().value('TUFLOW_vectorRenderer/vector')
					if vectorProperties:
						self.applyVectorRenderSettings(layer, i, vectorProperties)
						
			else:
				mdGroupName = mdGroup.name()
				if mdGroupName in temporalResultTypes:
					counter = 1
					mdGroupName = '{0} [{1}]'.format(mdGroupName, counter)
					while mdGroupName in maxResultTypes:
						mdGroupName = mdGroupName.replace('[{0}]'.format(counter), '[{0}]'.format(counter + 1))
						counter += 1
					
				# add to temporal result type list
				if ext.upper() == '.DAT' and mdGroup.isVector():  # because dat files need to load in as both vector and scalar
					temporalResultTypes.append('{0} Vector'.format(mdGroupName))
					temporalResultTypes.append(mdGroupName)
				else:
					temporalResultTypes.append(mdGroupName)
				
				# initiate in result dict
				if ext.upper() == '.DAT' and mdGroup.isVector():  # because dat files need to load in as both vector and scalar
					results[name][mdGroupName] = {}
					results[name]['{0} Vector'.format(mdGroupName)] = {}
				else:
					results[name][mdGroupName] = {}  # add result type to results dictionary
				
				# apply any default rendering styles to datagroup
				if mdGroup.isScalar() or ext.upper() == '.DAT':
					resultType = mdGroupName
					# try finding if style has been saved as a ramp first
					key = 'TUFLOW_scalarRenderer/{0}_ramp'.format(resultType)
					file = QSettings().value(key)
					if file:
						self.applyScalarRenderSettings(layer, i, file, type='ramp')
					# else try map
					key = 'TUFLOW_scalarRenderer/{0}_map'.format(resultType)
					file = QSettings().value(key)
					if file:
						self.applyScalarRenderSettings(layer, i, file, type='map')
				if mdGroup.isVector():
					vectorProperties = QSettings().value('TUFLOW_vectorRenderer/vector')
					if vectorProperties:
						self.applyVectorRenderSettings(layer, i, vectorProperties)

				for j in range(dp.datasetCount(i)):
					md = dp.datasetMetadata(QgsMeshDatasetIndex(i, j))  # metadata for individual timestep
					if md.time() == 900001.0 and self.tuView.tuOptions.timeUnits == 'h':  # time of peak h
						if mdGroupName in results[name]:
							del results[name][mdGroupName]
						results[name]['Time of Peak h'] = {'0.000000': (0, type, QgsMeshDatasetIndex(i, j))}
					elif md.time() == 900002.0 and self.tuView.tuOptions.timeUnits == 'h':  # time of peak V
						if mdGroupName in results[name]:
							del results[name][mdGroupName]
						results[name]['Time of Peak V'] = {'0.000000': (0, type, QgsMeshDatasetIndex(i, j))}
						
					elif md.time() > 100000 and md.time() < 200000 and not md.time() == 111111.0 \
							and self.tuView.tuOptions.timeUnits == 'h':
						if mdGroupName in results[name]:
							del results[name][mdGroupName]
						value = md.time() - 100000.0
						results[name]['Time of Cutoff {0}'.format(value)] = {'0.000000': (0, type, QgsMeshDatasetIndex(i, j))}
					elif md.time() > 200000 and md.time() < 300000 and not md.time() == 222222.0 \
							and self.tuView.tuOptions.timeUnits == 'h':
						if mdGroupName in results[name]:
							del results[name][mdGroupName]
						value = md.time() - 200000.0
						results[name]['Time Exc Cutoff {0}'.format(value)] = {'0.000000': (0, type, QgsMeshDatasetIndex(i, j))}
					else:  # not a special time
						results[name][mdGroupName]['{0:.6f}'.format(md.time())] = \
							(md.time(), type, QgsMeshDatasetIndex(i, j))  # add result index to results dict
						timekey2time['{0:.6f}'.format(md.time())] = md.time()
						if self.tuView.tuOptions.timeUnits == 's':
							date = zeroTime + timedelta(seconds=md.time())
						else:
							try:
								date = zeroTime + timedelta(hours=md.time())
							except OverflowError:
								date = zeroTime + timedelta(seconds=md.time())
						date = roundSeconds(date)
						timekey2date['{0:.6f}'.format(md.time())] = date
						time2date[md.time()] = date
						date2timekey[date] = '{0:.6f}'.format(md.time())
						date2time[date] = md.time()
						if ext.upper() == '.DAT' and mdGroup.isVector():  # need to add result type again as vector type
							md = dp.datasetMetadata(QgsMeshDatasetIndex(i, j))  # metadata for individual timestep
							results[name]['{0} Vector'.format(mdGroupName)]['{0:.6f}'.format(md.time())] = \
								(md.time(), 2, QgsMeshDatasetIndex(i, j))  # add result index to results dict
							timekey2time['{0:.6f}'.format(md.time())] = md.time()
							if self.tuView.tuOptions.timeUnits == 's':
								date = zeroTime + timedelta(seconds=md.time())
							else:
								date = zeroTime + timedelta(hours=md.time())
							date = roundSeconds(date)
							timekey2date['{0:.6f}'.format(md.time())] = date
							time2date[md.time()] = date
							date2timekey[date] = '{0:.6f}'.format(md.time())
							date2time[date] = md.time()
							
		# align first timestep values
		# e.g. if first temporal timestep is 1 hr
		# bed elevation has timestep 0 hrs by default
		# 0 hrs will show up in the time slider which is not ideal (that isn't when the output starts)
		# change all instances of this to the first temporal output
		self.alignFirstTimestepValues()

		return True
	
	def updateActiveMeshLayers(self):
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
				if isinstance(layer, QgsMeshLayer):
					if item.isSelected():
						self.activeMeshLayers.append(layer)
					else:
						rs = layer.rendererSettings()
						rs.setActiveScalarDataset(QgsMeshDatasetIndex(-1, -1))
						layer.setRendererSettings(rs)
						rs.setActiveVectorDataset(QgsMeshDatasetIndex(-1, -1))
						layer.setRendererSettings(rs)
		
		return True
	
	
	def renderMap(self):
		"""
		Renders the active scalar and vector layers.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# first make sure selected result types match active result types
		self.tuView.tuResults.checkSelectedResults()

		for layer in self.activeMeshLayers:

			rs = layer.rendererSettings()
			
			# Get result index
			activeScalarIndex = TuResultsIndex(layer.name(), self.activeScalar,
			                                   self.tuView.tuResults.activeTime, self.tuView.tuResults.isMax('scalar'))
			activeVectorIndex = TuResultsIndex(layer.name(), self.activeVector,
			                                   self.tuView.tuResults.activeTime, self.tuView.tuResults.isMax('vector'))
			
			# Get QgsMeshLayerIndex from result index
			activeScalarMeshIndex = self.tuView.tuResults.getResult(activeScalarIndex, force_get_time='next lower')
			activeVectorMeshIndex = self.tuView.tuResults.getResult(activeVectorIndex, force_get_time='next lower')
			
			# render results
			if activeScalarMeshIndex and type(activeScalarMeshIndex) == tuple:
				rs.setActiveScalarDataset(activeScalarMeshIndex[-1])
			else:  # if it doesn't return tuple then turn render off since there is no available timestep
				rs.setActiveScalarDataset()  # blank
			layer.setRendererSettings(rs)
			if activeVectorMeshIndex and type(activeVectorMeshIndex) == tuple:
				rs.setActiveVectorDataset(activeVectorMeshIndex[-1])
			else:
				rs.setActiveVectorDataset()  # blank
			layer.setRendererSettings(rs)
				
			# turn on / off mesh and triangles
			if rs.nativeMeshSettings().isEnabled() != self.tuView.tuOptions.showGrid:
				rsMesh = rs.nativeMeshSettings()
				rsMesh.setEnabled(self.tuView.tuOptions.showGrid)
				rs.setNativeMeshSettings(rsMesh)
				layer.setRendererSettings(rs)
			self.tuView.tuPlot.tuPlotToolbar.meshGridAction.setChecked(self.tuView.tuOptions.showGrid)
			if rs.triangularMeshSettings().isEnabled() != self.tuView.tuOptions.showTriangles:
				rsTriangles = rs.triangularMeshSettings()
				rsTriangles.setEnabled(self.tuView.tuOptions.showTriangles)
				rs.setTriangularMeshSettings(rsTriangles)
				layer.setRendererSettings(rs)
		
		# disconnect map canvas refresh if it is connected - used for rendering after loading from project
		try:
			self.tuView.canvas.mapCanvasRefreshed.disconnect(self.renderMap)
		except:
			pass
			
		return True
	
	def removeResults(self, resList):
		"""
		Removes the 2D results from the indexed results and ui.
		
		:param resList: list -> str result name e.g. M01_5m_001
		:return: bool -> True for successful, False for unsuccessful
		"""

		results = self.tuView.tuResults.results

		for res in resList:
			if res in results.keys():
				# remove from indexed results
				for resultType in list(results[res].keys()):
					if '_ts' not in resultType and '_lp' not in resultType:
						del results[res][resultType]

				# remove from map
				#layer = tuflowqgis_find_layer(res)
				#self.tuView.project.removeMapLayer(layer)
				#self.tuView.canvas.refresh()
				
				# check if result type is now empty
				if len(results[res]) == 0:
					del results[res]
					for i in range(self.tuView.OpenResults.count()):
						item = self.tuView.OpenResults.item(i)
						if item is not None and item.text() == res:
							self.tuView.OpenResults.takeItem(i)
							
				if res in self.results2d:
					del self.results2d[res]
						
		return True
	
	def loadOpenMeshLayers(self, **kwargs):
		"""
		Checks the workspace for already open mesh layers and adds datasets to mesh and loads into interface.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		layer = kwargs['layer'] if 'layer' in kwargs.keys() else None
		
		if layer:
			meshLayers = [layer]
		else:
			meshLayers = findAllMeshLyrs()
		
		for ml in meshLayers:
			layer = tuflowqgis_find_layer(ml)
			if layer is not None:
				
				if layer.dataProvider().datasetGroupCount() == 0:
					return
				elif layer.dataProvider().datasetGroupCount() > 0:
					self.getResultMetaData(ml, layer)
					self.tuView.OpenResults.addItem(ml)
				
				layer.dataProvider().datasetGroupsAdded.connect(self.datasetGroupsAdded)
					
	def datasetGroupsAdded(self):
		"""
		Re-indexes results because a new dataset (xmdf or dat) has been added through layer properties and not through
		the plugin.
		
		:return:
		"""

		meshLayers = findAllMeshLyrs()
		for ml in meshLayers:
			layer = tuflowqgis_find_layer(ml)
			if layer is not None:
				if layer.dataProvider().datasetGroupCount() == 0:
					return
				elif layer.dataProvider().datasetGroupCount() > 0:
					self.getResultMetaData(ml, layer)
					self.tuView.tuResults.updateResultTypes()

	def applyScalarRenderSettings(self, layer, datasetGroupIndex, file, type, save_type='xml'):
		"""
		Applies scalar renderer settings to a datagroup based on a color ramp properties.
		
		:param layer: QgsMeshLayer
		:param datasetGroupIndex: int
		:param file: str
		:param type: str -> 'ramp'
						    'map'
		:return: bool -> True for successful, False for unsuccessful
		"""

		rs = layer.rendererSettings()
		rsScalar = rs.scalarSettings(datasetGroupIndex)
		
		if type == 'ramp':
			if rsScalar.colorRampShader().colorRampItemList():
				minValue = rsScalar.colorRampShader().colorRampItemList()[0].value
				maxValue = rsScalar.colorRampShader().colorRampItemList()[-1].value
				shader = rsScalar.colorRampShader()
				doc = QDomDocument()
				xml = QFile(file)
				statusOK, errorStr, errorLine, errorColumn = doc.setContent(xml, True)
				if statusOK:
					element = doc.documentElement()
					shader.readXml(element)
					shader.setMinimumValue(minValue)
					shader.setMaximumValue(maxValue)
					shader.setColorRampType(0)
					shader.classifyColorRamp(5, -1, QgsRectangle(), None)
					rsScalar.setColorRampShader(shader)
				else:
					return False
			else:
				return False
		elif type == 'map':
			doc = QDomDocument()
			xml = QFile(file) if save_type == 'xml' else file
			statusOK, errorStr, errorLine, errorColumn = doc.setContent(xml, True)
			if statusOK:
				element = doc.documentElement()
				rsScalar.readXml(element)
			else:
				return False
		else:
			return False

		rs.setScalarSettings(datasetGroupIndex, rsScalar)
		layer.setRendererSettings(rs)
		
		return True
	
	def applyVectorRenderSettings(self, layer, datasetGroupIndex, vectorProperties):
		"""
		Applies vector renderer settings to a vector datset group based on vector properties.
		
		:param layer: QgsMeshLayer
		:param datasetGroupIndex: int
		:param vectorProperties: dict
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		rs = layer.rendererSettings()
		rsVector = rs.vectorSettings(datasetGroupIndex)
		
		if 'arrow head length ratio' in vectorProperties:
			rsVector.setArrowHeadLengthRatio(vectorProperties['arrow head length ratio'])
		if 'arrow head width ratio' in vectorProperties:
			rsVector.setArrowHeadWidthRatio(vectorProperties['arrow head width ratio'])
		if 'color' in vectorProperties:
			rsVector.setColor(vectorProperties['color'])
		if 'filter max' in vectorProperties:
			rsVector.setFilterMax(vectorProperties['filter max'])
		if 'filter min' in vectorProperties:
			rsVector.setFilterMin(vectorProperties['filter min'])
		if 'line width' in vectorProperties:
			rsVector.setLineWidth(vectorProperties['line width'])
		
		if 'shaft length method' in vectorProperties:
			method = vectorProperties['shaft length method']
			rsVector.setShaftLengthMethod(method)
		
			if method == 0:  # min max
				rsVector.setMaxShaftLength(vectorProperties['max shaft length'])
				rsVector.setMinShaftLength(vectorProperties['min shaft length'])
			elif method == 1:  # scaled
				rsVector.setScaleFactor(vectorProperties['scale factor'])
			elif method == 2:  # fixed
				rsVector.setFixedShaftLength(vectorProperties['fixed shaft length'])
			else:
				return False
		
		rs.setVectorSettings(datasetGroupIndex, rsVector)
		layer.setRendererSettings(rs)
		
		return True
	
	def layerNameChanged(self, layer, oldName, newName):
		"""
		
		
		:param layer:
		:return:
		"""
		
		layer.nameChanged.disconnect()
		
		# change name in list widget
		selectedItems = self.tuView.OpenResults.selectedItems()
		for i in range(self.tuView.OpenResults.count()):
			item = self.tuView.OpenResults.item(i)
			if item.text() == oldName:
				self.tuView.OpenResults.takeItem(i)
				self.tuView.OpenResults.insertItem(i, newName)
				if item in selectedItems:
					self.tuView.OpenResults.item(i).setSelected(True)
					
		# change name in results dict
		results = self.tuView.tuResults.results
		for key, entry in results.items():
			if key == oldName:
				results[newName] = entry
				del results[oldName]
				
		layer.nameChanged.connect(lambda: self.layerNameChanged(layer, newName, layer.name()))
				
		return True
	
	def alignFirstTimestepValues(self):
		"""
		If first temporal output is not zero, change all single
		datatimesteps with zero value to first timestep
		
		:return:
		"""
		
		results = self.tuView.tuResults.results
		firstTime = None
		
		# iterate through each result set
		for result in results:
			# find temporal data and get first timestep
			for resultType in results[result]:
				if firstTime is not None:
					break
				if '_ts' not in resultType and '_lp' not in resultType:
					if len(results[result][resultType]) > 1:
						for i in results[result][resultType]:
							firstTime = results[result][resultType][i][0]
							break

			if firstTime is not None:
				if firstTime == 0:
					continue  # move onto next result dataset
				else:  # find time 0 values and change to firstTime
					for resultType in results[result]:
						if '_ts' not in resultType and '_lp' not in resultType:
							if len(results[result][resultType]) == 1:
								for i in results[result][resultType]:
									if results[result][resultType][i][0] == 0:
										timeKey = '{0:.6f}'.format(firstTime)
										dataType = results[result][resultType][i][1]
										meshIndex = results[result][resultType][i][2]
										results[result][resultType][timeKey] = (firstTime, dataType, meshIndex)
										del results[result][resultType][i]