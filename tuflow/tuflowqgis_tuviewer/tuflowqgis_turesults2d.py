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
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesults import TuResults
from tuflow.tuflowqgis_library import tuflowqgis_find_layer, findAllMeshLyrs, loadSetting, roundSeconds, \
	getPropertiesFrom2dm, qdt2dt, dt2qdt



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
		self.bRecordSpecialTime = None
	
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
			if os.path.splitext(f)[1].lower() != '.nc':
				if type(inFileNames) is dict:  # being loaded in from a sup file
					datasets = inFileNames[f]['datasets']
					for d in datasets:
						l = self.loadDataGroup(d, mLayer, preExisting)
				else:
					loaded = self.loadDataGroup(f, mLayer, preExisting)
			else:
				pass
				#self.tuView.tuResults.tuResults3D.importResults([f])
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
		elif fext.lower() == '.nc':
			mesh = fpath
		else:
			QMessageBox.information(self.iface.mainWindow(), "TUFLOW Viewer",
			                        "Must select a .xmdf .dat .sup .nc or .2dm file type")
			return None, None, False

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

			
		# Load mesh if layer does not exist already
		name = basename if name is None else name
		layer = QgsMeshLayer(mesh, name, 'mdal')
		if layer.isValid():
			if fext.lower() == '.nc':
				return layer, name, False
			else:
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
		
		QMessageBox.information(self.iface.mainWindow(), "TUFLOW Viewer", "Could not load mesh file. Please check validity of this file (e.g. not empty):\n {0}".format(mesh))
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

		qv = Qgis.QGIS_VERSION_INT

		results = self.tuView.tuResults.results  # dict
		timekey2time = self.tuView.tuResults.timekey2time  # dict
		timekey2date = self.tuView.tuResults.timekey2date  # dict
		time2date = self.tuView.tuResults.time2date  # dict
		date2timekey = self.tuView.tuResults.date2timekey  # dict
		date2time = self.tuView.tuResults.date2time  # dict
		zeroTime = self.tuView.tuOptions.zeroTime


		if name not in results.keys():  # add results to dict
			results[name] = {}
		
		resultTypes = []
		dp = layer.dataProvider()  # QgsMeshDataProvider
		if self.tuView.OpenResults.count() == 0:
			self.tuView.tuOptions.zeroTime = self.getReferenceTime(layer, self.tuView.tuOptions.defaultZeroTime)

		# turn on temporal properties
		self.configTemporalProperties(layer)

		for i in range(dp.datasetGroupCount()):
			# Get result type e.g. depth, velocity, max depth
			mdGroup = dp.datasetGroupMetadata(i)  # Group Metadata
			id, id2 = self.getResultTypeNames(mdGroup, ext, resultTypes)

			# add to temporal result type list
			resultTypes.append(id)
			if id2 is not None:
				resultTypes.append(id2)

			# initiate in result dict
			results[name][id] = {'times': {},
			                     'is3dDataset': self.is3dDataset(i, dp),
			                     'timeUnit': self.getTimeUnit(layer),
			                     'referenceTime': self.tuView.tuOptions.zeroTime,
			                     'isMax': TuResults.isMaximumResultType(id, dp, i),
			                     'isMin':TuResults.isMinimumResultType(id, dp, i),
			                     'isStatic': TuResults.isStatic(id, dp, i),
			                     'isTemporal': TuResults.isTemporal(id, dp, i),
			                     }  # add result type to results dictionary
			if id2 is not None:
				results[name][id2] = {'times': {},
				                      'is3dDataset': self.is3dDataset(i, dp),
				                      'timeUnit': self.getTimeUnit(layer),
				                      'referenceTime': self.tuView.tuOptions.zeroTime,
				                      'isMax': TuResults.isMaximumResultType(id, dp, i),
				                      'isMin':TuResults.isMinimumResultType(id, dp, i),
				                      'isStatic': TuResults.isStatic(id, dp, i),
				                      'isTemporal': TuResults.isTemporal(id, dp, i),
				                      }  # add result type to results dictionary

			# apply any default rendering styles to datagroup
			if id:
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
			if mdGroup.isVector() or id2:
				vectorProperties = QSettings().value('TUFLOW_vectorRenderer/vector')
				if vectorProperties:
					self.applyVectorRenderSettings(layer, i, vectorProperties)

			# record datasetindex for each timestep
			for j in range(dp.datasetCount(i)):
				md = dp.datasetMetadata(QgsMeshDatasetIndex(i, j))  # metadata for individual timestep

				# TUFLOW special timesteps
				st = self.recordSpecialTime(name, md.time(), id, id2, i, j, ext)

				if not st:
					self.recordTime(layer, mdGroup, md, name, id, id2, i, j)

		# align first timestep values
		# e.g. if first temporal timestep is 1 hr
		# bed elevation has timestep 0 hrs by default
		# 0 hrs will show up in the time slider which is not ideal (that isn't when the output starts)
		# change all instances of this to the first temporal output
		self.alignFirstTimestepValues()

		return True
	
	def getTimeUnit(self, lyr):
		"""

		"""

		qv = Qgis.QGIS_VERSION_INT

		if 31100 <= qv < 31300:
			tu2text = {
				QgsMeshTimeSettings.seconds: 's',
				QgsMeshTimeSettings.minutes: 'm',
				QgsMeshTimeSettings.hours: 'h',
				QgsMeshTimeSettings.days: 'd',
			}
			return tu2text[lyr.timeSettings().providerTimeUnit()]
		else:
			return 'h'

	def is3dDataset(self, mdi, dp):
		"""

		"""

		for i in range(dp.datasetCount(mdi)):
			try:
				return dp.dataset3dValues(QgsMeshDatasetIndex(mdi, i), 0, 1).verticalLevelsCount()[0] > 1
			except:
				continue

		return False

	def recordTime(self, layer, mdg, md, name, id, id2, i, j):
		"""

		"""

		qv = Qgis.QGIS_VERSION_INT

		results = self.tuView.tuResults.results  # dict
		timekey2time = self.tuView.tuResults.timekey2time  # dict
		timekey2date = self.tuView.tuResults.timekey2date  # dict
		time2date = self.tuView.tuResults.time2date  # dict
		date2timekey = self.tuView.tuResults.date2timekey  # dict
		date2time = self.tuView.tuResults.date2time  # dict
		zeroTime = self.tuView.tuOptions.zeroTime

		t = md.time()
		if self.getReferenceTime(layer) != self.tuView.tuOptions.zeroTime:
			dt = self.getReferenceTime(layer) - self.tuView.tuOptions.zeroTime
			if self.tuView.tuOptions.timeUnits == 'h':
				factor = 60. * 60.
			else:  # 's'
				factor = 1.
			t += dt.total_seconds() / factor

		for k, x in enumerate([id, id2]):
			if x is not None:
				if id and id2 and k == 0:
					v = 1
				elif id and id2 and k == 1:
					v = 2
				elif mdg.isScalar():
					v = 1
				elif mdg.isVector():
					v = 2
				else:
					v = 1
				results[name][x]['times']['{0:.6f}'.format(t)] = (t, v, QgsMeshDatasetIndex(i, j))
				timekey2time['{0:.6f}'.format(t)] = t
				if self.tuView.tuOptions.timeUnits == 's':
					date = zeroTime + timedelta(seconds=t)
				else:
					try:
						date = zeroTime + timedelta(hours=t)
					except OverflowError:
						date = zeroTime + timedelta(seconds=t)
				date = roundSeconds(date)
				timekey2date['{0:.6f}'.format(t)] = date
				time2date[t] = date
				date2timekey[date] = '{0:.6f}'.format(t)
				date2time[date] = t

	def recordSpecialTime(self, name, t, id, id2, i, j, ext):
		"""

		"""

		results = self.tuView.tuResults.results  # dict

		if ext.upper() == '.DAT':
			ri = TuResultsIndex(name, id)
			timeUnits = self.tuView.tuResults.getTimeUnit(ri)  # is the same for the whole layer
			if t == 900001.0 and timeUnits == 'h':  # time of peak h
				specialName = 'Time of Peak h'
				self.checkRecordSpecialTime(t, specialName)
				if self.bRecordSpecialTime:
					if id in results[name]:
						del results[name][id]
					results[name][specialName] = {'times': {'0.000000': (0, 1, QgsMeshDatasetIndex(i, j))}}
					return True
			elif t == 900002.0 and timeUnits == 'h':  # time of peak V
				specialName = 'Time of Peak V'
				self.checkRecordSpecialTime(t, specialName)
				if self.bRecordSpecialTime:
					if id in results[name]:
						del results[name][id]
					results[name][specialName] = {'times': {'0.000000': (0, 1, QgsMeshDatasetIndex(i, j))}}
					return True
			elif 100000 < t < 200000 and t != 111111.0 and timeUnits == 'h':
				value = t - 100000.0
				specialName = 'Time of Cutoff {0}'.format(value)
				self.checkRecordSpecialTime(t, specialName)
				if self.bRecordSpecialTime:
					if id in results[name]:
						del results[name][id]
					results[name][specialName] = {'times': {'0.000000': (0, 1, QgsMeshDatasetIndex(i, j))}}
					return True
			elif 200000 < t < 300000 and t != 222222.0 and timeUnits == 'h':
				value = t - 200000.0
				specialName = 'Time Exc Cutoff {0}'.format(value)
				self.checkRecordSpecialTime(t, specialName)
				if self.bRecordSpecialTime:
					if id in results[name]:
						del results[name][id]
					value = t - 200000.0
					results[name][specialName] = {'times': {'0.000000': (0, 1, QgsMeshDatasetIndex(i, j))}}
					return True

		return False

	def checkRecordSpecialTime(self, time, specialName):
		"""

		"""

		if self.bRecordSpecialTime is None:
			btn1 = QPushButton()
			btn1.setText("Special Times")
			btn2 = QPushButton()
			btn2.setText("Skip")
			msg = QMessageBox(QMessageBox.Question, "Special Times", "Found potential special times in results. "
			                                                         "Would you like TUFLOW Viewer to interpret these "
			                                                         "as special times or leave as is?:"
			                                                         "\n{0}-> {1}\n".format(time, specialName))
			msg.addButton(btn1, QMessageBox.AcceptRole)
			msg.addButton(btn2, QMessageBox.RejectRole)
			msg.exec()
			if msg.clickedButton() == btn1:
				self.bRecordSpecialTime = True
			else:
				self.bRecordSpecialTime = False

	def getResultTypeNames(self, mdg, ext, ids):
		"""

		"""

		id = None
		id2 = None

		if ext.upper() != ".XMDF":
			if mdg.isScalar():
				id = self.addCounter(mdg.name(), ids)
			if mdg.isVector():
				if id is None:
					id = self.addCounter(mdg.name(), ids)
					id2 = self.addCounter('{0} Vector'.format(mdg.name()), ids)
				else:
					id2 = self.addCounter('{0} Vector'.format(mdg.name()), ids)
		else:
			id = self.addCounter(mdg.name(), ids)

		return id, id2

	def addCounter(self, id, ids):
		"""

		"""

		if id in ids:
			counter = 1
			newId = '{0} [{1}]'.format(id, counter)
			while newId in ids:
				newId = newId.replace('[{0}]'.format(counter), '[{0}]'.format(counter + 1))
				counter += 1
		else:
			newId = id

		return newId

	def updateActiveMeshLayers(self):
		"""
		Updates the list of selected 2D results.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.activeMeshLayers.clear()
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
						self.renderMap(layers=[layer], turn_off=True)

		self.renderMap()
		
		return True
	
	
	def renderMap(self, layers=(), turn_off=False):
		"""
		Renders the active scalar and vector layers.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		# first make sure selected result types match active result types
		self.tuView.tuResults.checkSelectedResults()

		if not layers:
			layers = self.activeMeshLayers[:]

		for layer in layers:
			if turn_off:
				activeScalarIndex = None
				activeVectorIndex = None
			else:
				activeScalarIndex = TuResultsIndex(layer.name(), self.activeScalar,
				                                   self.tuView.tuResults.activeTime, self.tuView.tuResults.isMax('scalar'),
				                                   self.tuView.tuResults.isMin('scalar'))
				activeVectorIndex = TuResultsIndex(layer.name(), self.activeVector,
				                                   self.tuView.tuResults.activeTime, self.tuView.tuResults.isMax('vector'),
				                                   self.tuView.tuResults.isMin('vector'))
			activeScalarMeshIndex = self.tuView.tuResults.getResult(activeScalarIndex, force_get_time='next lower',
			                                                        mesh_index_only=True)
			activeVectorMeshIndex = self.tuView.tuResults.getResult(activeVectorIndex, force_get_time='next lower',
			                                                        mesh_index_only=True)
			# render active datasets
			rs = layer.rendererSettings()
			setActiveScalar, setActiveVector = TuResults2D.meshRenderVersion(rs)
			setActiveScalar(activeScalarMeshIndex)
			setActiveVector(activeVectorMeshIndex)
			layer.setRendererSettings(rs)

			# turn on / off mesh and triangles
			self.renderNativeMesh(layer, rs)

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

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesults import TuResults

		results = self.tuView.tuResults.results

		for res in resList:
			if res in results.keys():
				# remove from indexed results
				for resultType in list(results[res].keys()):
					# if '_ts' not in resultType and '_lp' not in resultType:
					if TuResults.isMapOutputType(resultType):
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

		qv = Qgis.QGIS_VERSION_INT
		
		rs = layer.rendererSettings()
		rsVector = rs.vectorSettings(datasetGroupIndex)
		if qv >= 31100:
			rsVectorArrow = rsVector.arrowSettings()
		
		if 'arrow head length ratio' in vectorProperties:
			if qv < 31100:
				rsVector.setArrowHeadLengthRatio(vectorProperties['arrow head length ratio'])
			else:
				rsVectorArrow.setArrowHeadLengthRatio(vectorProperties['arrow head length ratio'])
		if 'arrow head width ratio' in vectorProperties:
			if qv < 31100:
				rsVector.setArrowHeadWidthRatio(vectorProperties['arrow head width ratio'])
			else:
				rsVectorArrow.setArrowHeadWidthRatio(vectorProperties['arrow head width ratio'])
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

			if qv < 31100:
				rsVector.setShaftLengthMethod(method)
			else:
				rsVectorArrow.setShaftLengthMethod(method)
		
			if method == 0:  # min max
				if qv < 31100:
					rsVector.setMaxShaftLength(vectorProperties['max shaft length'])
					rsVector.setMinShaftLength(vectorProperties['min shaft length'])
				else:
					rsVectorArrow.setMaxShaftLength(vectorProperties['max shaft length'])
					rsVectorArrow.setMinShaftLength(vectorProperties['min shaft length'])
			elif method == 1:  # scaled
				if qv < 31100:
					rsVector.setScaleFactor(vectorProperties['scale factor'])
				else:
					rsVectorArrow.setScaleFactor(vectorProperties['scale factor'])
			elif method == 2:  # fixed
				if qv < 31100:
					rsVector.setFixedShaftLength(vectorProperties['fixed shaft length'])
				else:
					rsVectorArrow.setFixedShaftLength(vectorProperties['fixed shaft length'])
			else:
				return False

		if qv >= 31100:
			rsVector.setArrowsSettings(rsVectorArrow)

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

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesults import TuResults

		results = self.tuView.tuResults.results
		firstTime = None
		
		# iterate through each result set
		for result in results:
			# find temporal data and get first timestep
			for resultType in results[result]:
				if firstTime is not None:
					break
				if TuResults.isMapOutputType(resultType):
				# elif '_ts' not in resultType and '_lp' not in resultType and '_particles' not in resultType:
					if len(results[result][resultType]['times']) > 1:
						for i in results[result][resultType]['times']:
							firstTime = results[result][resultType]['times'][i][0]
							break

			if firstTime is not None:
				if firstTime == 0:
					continue  # move onto next result dataset
				else:  # find time 0 values and change to firstTime
					for resultType in results[result]:
						#if '_ts' not in resultType and '_lp' not in resultType:
						if TuResults.isMapOutputType(resultType):
							if len(results[result][resultType]['times']) == 1:
								for i in results[result][resultType]['times']:
									if results[result][resultType]['times'][i][0] == 0:
										timeKey = '{0:.6f}'.format(firstTime)
										dataType = results[result][resultType]['times'][i][1]
										meshIndex = results[result][resultType]['times'][i][2]
										results[result][resultType]['times'][timeKey] = (firstTime, dataType, meshIndex)
										del results[result][resultType]['times'][i]

										# also delete from dicts
										a = sorted([x for x in self.tuView.tuResults.time2date.keys()])
										if a[0] != firstTime:
											del self.tuView.tuResults.time2date[a[0]]

											a = sorted([x for x in self.tuView.tuResults.timekey2date.keys()])
											del self.tuView.tuResults.timekey2date[a[0]]

											a = sorted([x for x in self.tuView.tuResults.timekey2time.keys()])
											del self.tuView.tuResults.timekey2time[a[0]]

											a = sorted([x for x in self.tuView.tuResults.date2time.keys()])
											del self.tuView.tuResults.date2time[a[0]]

											a = sorted([x for x in self.tuView.tuResults.date2timekey.keys()])
											del self.tuView.tuResults.date2timekey[a[0]]

	@staticmethod
	def meshRenderVersion(rs):
		"""
		API changes between versions
		"""

		# get version
		qv = Qgis.QGIS_VERSION_INT

		if qv < 31300:
			setActiveScalar = rs.setActiveScalarDataset
			setActiveVector = rs.setActiveVectorDataset
		else:
			setActiveScalar = rs.setActiveScalarDatasetGroup
			setActiveVector = rs.setActiveVectorDatasetGroup

		return setActiveScalar, setActiveVector

	def renderNativeMesh(self, layer, rs):
		"""

		"""

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

	def getReferenceTime(self, layer, defaultZeroTime=None):
		"""

		"""
		qv = Qgis.QGIS_VERSION_INT

		rt = None
		if qv >= 31300:
			rt = layer.temporalProperties().referenceTime()
			rt = rt.toTimeSpec(self.tuView.tuResults.timeSpec)
		else:
			try:  # unclear what version this was introduced
				rt = layer.timeSettings().absoluteTimeReferenceTime()
			except:
				pass

		if rt is not None and rt.isValid():
			return qdt2dt(rt)
		else:
			if defaultZeroTime is not None:
				return defaultZeroTime
			else:
				return self.tuView.tuOptions.zeroTime

	def configTemporalProperties(self, layer):
		"""

		"""
		qv = Qgis.QGIS_VERSION_INT

		if qv >= 31300:
			tp = layer.temporalProperties()
			if not tp.isActive():
				tp.setIsActive(True)

			if not tp.referenceTime().isValid():
				layer.setReferenceTime(dt2qdt(self.getReferenceTime(layer),
				                              self.tuView.tuResults.timeSpec))