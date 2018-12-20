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
from tuflow.tuflowqgis_library import tuflowqgis_find_layer, findAllMeshLyrs, loadSetting, roundSeconds



class TuResults2D():
	"""
	Class for handling 2D results
	
	"""
	
	def __init__(self, TuView):
		self.tuView = TuView
		self.rsScalar = QgsMeshRendererScalarSettings()
		self.rsVector = QgsMeshRendererVectorSettings()
		self.activeMeshLayers = []  # list of selected QgsMeshLayer (layer.type() == 3)
		self.activeScalar = None  # active scalar to be rendered e.g. depth
		self.activeVector = None  # active vector to be rendered e.g. velocity vector
		self.activeDatasets = []  # list of active result datasets including time series and long plots
		self.activeScalar, self.activeVector = None, None
		self.cellSize = 2
	
	def importResults(self, inFileNames):
		"""
		Imports function that opens result mesh layer

		:param inFileNames: list -> str - full path to mesh result file
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuView.project.layersAdded.disconnect(self.tuView.layersAdded)

		for j, f in enumerate(inFileNames):

			# Load Mesh
			mLayer, name, preExisting = self.loadMeshLayer(f)
			if mLayer is None or name is None:
				self.tuView.project.layersAdded.connect(self.tuView.layersAdded)
				return False
			
			# Load Results
			loaded = self.loadDataGroup(f, mLayer, preExisting)
			if not loaded:
				self.tuView.project.layersAdded.connect(self.tuView.layersAdded)
				return False
			
			# Open layer in map and add to result list widget
			self.tuView.project.addMapLayer(mLayer)
			if name not in self.tuView.tuResults.results.keys():
				self.tuView.OpenResults.addItem(name)  # add to widget
			k = self.tuView.OpenResults.findItems(name, Qt.MatchRecursive)[0]
			k.setSelected(True)
			updated = self.updateActiveMeshLayers()  # update list of active mesh layers
			if not updated:
				self.tuView.project.layersAdded.connect(self.tuView.layersAdded)
				return False
			
			rs = mLayer.rendererSettings()
			rsMesh = rs.nativeMeshSettings()
			rsMesh.setEnabled(self.tuView.tuOptions.showGrid)
			rs.setNativeMeshSettings(rsMesh)
			mLayer.setRendererSettings(rs)
			mLayer.repaintRequested.connect(lambda: self.tuView.repaintRequested(mLayer))
			
			# Index results
			index = self.getResultMetaData(mLayer)
			if not index:
				self.tuView.project.layersAdded.connect(self.tuView.layersAdded)
				return False
			
		self.tuView.project.layersAdded.connect(self.tuView.layersAdded)
			
		return True
		
	def loadMeshLayer(self, fpath):
		"""
		Load the mesh layer i.e. .xmdf

		:param fpath: str
		:return: QgsMeshLayer
		:return: str
		"""
		
		# Parse out file names
		basepath, fext = os.path.splitext(fpath)
		basename = os.path.basename(basepath)
		dirname = os.path.dirname(basepath)
		if fext.lower() == '.xmdf':
			mesh = '{0}.2dm'.format(basepath)
		elif fext.lower() == '.dat':
			components = basename.split('_')
			components.pop()
			basename = '_'.join(components)
			mesh = '{0}.2dm'.format(os.path.join(dirname, basename))
		else:
			return None, None, False
		
		# does mesh layer already exist in workspace
		layer = tuflowqgis_find_layer(basename)
		if layer is not None:
			return layer, basename, True
		
		# Load mesh if layer does not exist already
		layer = QgsMeshLayer(mesh, basename, 'mdal')
		if layer.isValid():
			return layer, basename, False
	
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
					return False  # most likely already loaded
					
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
	
	def getResultMetaData(self, layer):
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
		
		if layer.name() not in results.keys():  # add results to dict
			results[layer.name()] = {}
		
		timesteps, maxResultTypes, temporalResultTypes = [], [], []
		dp = layer.dataProvider()  # QgsMeshDataProvider
		
		for i in range(dp.datasetGroupCount()):
			
			# Get result type e.g. depth, velocity, max depth
			mdGroup = dp.datasetGroupMetadata(i)  # Group Metadata
			type = 1 if mdGroup.isScalar() else 2
			if '/Maximums' in mdGroup.name():
				if mdGroup.name() not in maxResultTypes:
					
					# add to max result type list
					maxResultTypes.append(mdGroup.name().strip('/Maximums'))
					
					# initiate in results dict
					results[layer.name()][mdGroup.name()] = {}  # add result type to results dictionary
					
					# add max result as time -99999
					results[layer.name()][mdGroup.name()]['-99999'] = (-99999, type, QgsMeshDatasetIndex(i, 0))
					timekey2time['-99999'] = -99999
					timekey2date['-99999'] = -99999
					time2date['-99999'] = -99999
					date2timekey[-99999] = '-99999'
					date2time[-99999] = '-99999'
					
					# apply any default rendering styles to datagroup
					if mdGroup.isScalar():
						resultType = mdGroup.name().strip('/Maximums')
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
					elif mdGroup.isVector():
						vectorProperties = QSettings().value('TUFLOW_vectorRenderer/vector')
						if vectorProperties:
							self.applyVectorRenderSettings(layer, i, vectorProperties)
						
			else:
				if mdGroup.name() not in temporalResultTypes:
					
					# add to temporal result type list
					temporalResultTypes.append(mdGroup.name())
					
					# initiate in result dict
					results[layer.name()][mdGroup.name()] = {}  # add result type to results dictionary
					
					# apply any default rendering styles to datagroup
					if mdGroup.isScalar():
						resultType = mdGroup.name()
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
					elif mdGroup.isVector():
						vectorProperties = QSettings().value('TUFLOW_vectorRenderer/vector')
						if vectorProperties:
							self.applyVectorRenderSettings(layer, i, vectorProperties)
				
				# Get timesteps
				if not timesteps:  # only if not populated yet
					for j in range(dp.datasetCount(i)):
						md = dp.datasetMetadata(QgsMeshDatasetIndex(i, j))  # metadata for individual timestep
						timesteps.append(md.time())  # only difference between this and below code block
						results[layer.name()][mdGroup.name()]['{0:.4f}'.format(md.time())] = \
							(md.time(), type, QgsMeshDatasetIndex(i, j))  # add result index to results dict
						timekey2time['{0:.4f}'.format(md.time())] = md.time()
						date = zeroTime + timedelta(hours=md.time())
						date = roundSeconds(date)
						timekey2date['{0:.4f}'.format(md.time())] = date
						time2date[md.time()] = date
						date2timekey[date] = '{0:.4f}'.format(md.time())
						date2time[date] = md.time()
				else:
					for j in range(dp.datasetCount(i)):
						md = dp.datasetMetadata(QgsMeshDatasetIndex(i, j))  # metadata for individual timestep
						results[layer.name()][mdGroup.name()]['{0:.4f}'.format(md.time())] = \
							(md.time(), type, QgsMeshDatasetIndex(i, j))  # add result index to results dict
						timekey2time['{0:.4f}'.format(md.time())] = md.time()
						date = zeroTime + timedelta(hours=md.time())
						date = roundSeconds(date)
						timekey2date['{0:.4f}'.format(md.time())] = date
						time2date[md.time()] = date
						date2timekey[date] = '{0:.4f}'.format(md.time())
						date2time[date] = md.time()
						
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
	
	
	def renderMap(self):
		"""
		Renders the active scalar and vector layers.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		for layer in self.activeMeshLayers:
			
			rs = layer.rendererSettings()
			
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
				layer.setRendererSettings(rs)
			if activeVectorMeshIndex and type(activeVectorMeshIndex) == tuple:
				rs.setActiveVectorDataset(activeVectorMeshIndex[-1])
				layer.setRendererSettings(rs)
				
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
				mesh = layer.source()
				
				# check for xmdf
				xmdf = '{0}.xmdf'.format(os.path.splitext(mesh)[0])
				results2D = []
				if os.path.exists(xmdf):
					results2D.append(xmdf)
				# check for dat
				else:
					outputFolder2D = os.path.dirname(mesh)
					if os.path.exists(outputFolder2D):
						for file in os.listdir(outputFolder2D):
							name, ext = os.path.splitext(file)
							# name = os.path.basename(f)
							if ext.lower() == '.dat' and ml.lower() in name.lower():
								results2D.append(os.path.join(outputFolder2D, file))
				
				loaded = self.tuView.tuMenuBar.tuMenuFunctions.load2dResults(result_2D=[results2D])
				
				# if not loaded it may mean that results are already loaded in so index results and add to gui, else at least load in bed elevation
				if not loaded:
					self.getResultMetaData(layer)
					self.tuView.OpenResults.addItem(ml)

	def applyScalarRenderSettings(self, layer, datasetGroupIndex, file, type):
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
		elif type == 'map':
			doc = QDomDocument()
			xml = QFile(file)
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
		
		rsVector.setArrowHeadLengthRatio(vectorProperties['arrow head length ratio'])
		rsVector.setArrowHeadWidthRatio(vectorProperties['arrow head width ratio'])
		rsVector.setColor(vectorProperties['color'])
		rsVector.setFilterMax(vectorProperties['filter max'])
		rsVector.setFilterMin(vectorProperties['filter min'])
		rsVector.setLineWidth(vectorProperties['line width'])
		
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