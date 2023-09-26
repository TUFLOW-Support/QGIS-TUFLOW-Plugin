import os
import sys
from datetime import datetime, timedelta
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets import *
from qgis.PyQt.QtXml import QDomDocument
from .tuflowqgis_turesultsindex import TuResultsIndex
from ..tuflowqgis_library import tuflowqgis_find_layer, findAllMeshLyrs, loadSetting, roundSeconds, \
	getPropertiesFrom2dm, qdt2dt, dt2qdt, datetime2timespec
import re



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
		self.layer_reloaded_signals = {}
		self.layer_style_changed_signals = {}
		self.active_style = None
		self.active_style_group_name = -1
		self.layer_averaging_methods = {}
	
	def importResults(self, inFileNames):
		"""
		Imports function that opens result mesh layer

		:param inFileNames: list -> str - full path to mesh result file
		:return: bool -> True for successful, False for unsuccessful
		"""

		qv = Qgis.QGIS_VERSION_INT

		# disconnect incoming signals for load step
		skipConnect = False
		try:
			self.tuView.project.layersAdded.disconnect(self.tuView.layersAdded)
		except:
			skipConnect = True
			pass
		skipConnect2 = False
		try:
			self.tuView.OpenResults.itemSelectionChanged.disconnect(self.tuView.resultSelectionChangeSignal)
		except:
			pass
		meshLayers = findAllMeshLyrs()
		for ml in meshLayers:
			layer = tuflowqgis_find_layer(ml)
			try:
				layer.dataProvider().datasetGroupsAdded.disconnect(self.datasetGroupsAdded)
			except:
				pass
			try:
				layer.repaintRequested.disconnect(self.repaintRequested)
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
				self.tuView.resultSelectionChangeSignal = self.tuView.OpenResults.itemSelectionChanged.connect(
					lambda: self.tuView.resultsChanged('item clicked'))
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
			QgsProject.instance().layerTreeRoot().findLayer(mLayer.id()).visibilityChanged.connect(self.layerVisibilityChanged)
			signal = mLayer.rendererChanged.connect(lambda: self.layerStyleChanged(mLayer))
			self.layer_style_changed_signals[mLayer.id()] = signal
			if qv >= 32800:
				signal = mLayer.reloaded.connect(lambda: self.layerReloaded(mLayer))
				self.layer_reloaded_signals[mLayer.id()] = signal
			
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
				self.tuView.resultSelectionChangeSignal = self.tuView.OpenResults.itemSelectionChanged.connect(
					lambda: self.tuView.resultsChanged('item clicked'))
				return False

			if qv >= 31600:
				self.tuView.tuResults.updateDateTimes(get_metadata=False)
			
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
		self.tuView.resultSelectionChangeSignal = self.tuView.OpenResults.itemSelectionChanged.connect(
			lambda: self.tuView.resultsChanged('item clicked'))
		meshLayers = findAllMeshLyrs()
		for ml in meshLayers:
			layer = tuflowqgis_find_layer(ml)
			layer.dataProvider().datasetGroupsAdded.connect(self.datasetGroupsAdded)
			layer.repaintRequested.connect(self.repaintRequested)

			
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
			if self.iface is not None:
				QMessageBox.information(self.iface.mainWindow(), "TUFLOW Viewer",
				                        "Must select a .xmdf .dat .sup .nc or .2dm file type")
			else:
				print("Must select a .xmdf .dat .sup .nc or .2dm file type")
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
					if self.iface is not None:
						QMessageBox.information(self.iface, "TUFLOW Viewer", "Could not find mesh file")
					else:
						print("Could not find mesh file")
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

		if self.iface is not None:
			QMessageBox.information(self.iface.mainWindow(), "TUFLOW Viewer", "Could not load mesh file. Please check validity of this file (e.g. not empty):\n {0}".format(mesh))
		else:
			print("Could not load mesh file. Please check validity of this file (e.g. not empty):\n {0}".format(mesh))
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
	
	def getResultMetaData(self, name, layer, ext='', hadtp=None, loadRenderStyle=True):
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
			self.tuView.tuOptions.zeroTime = datetime2timespec(self.getReferenceTime(layer, self.tuView.tuOptions.defaultZeroTime),
			                                                   1, self.tuView.tuResults.timeSpec)
			if qv >= 31300:
				if self.iface is not None:
					self.tuView.tuOptions.timeSpec = self.iface.mapCanvas().temporalRange().begin().timeSpec()
					self.tuView.tuResults.loadedTimeSpec = self.iface.mapCanvas().temporalRange().begin().timeSpec()
				else:
					self.tuView.tuOptions.timeSpec = 1
					self.tuView.tuResults.loadedTimeSpec = 1

		# turn on temporal properties - record whether original layer had a reference time
		if name in results and [x for x in results[name].keys()]:
			restype = [x for x in results[name].keys()][0]
			if 'hadTemporalProperties' in results[name][restype]:
				hadtp = results[name][restype]['hadTemporalProperties']
		if hadtp is None:
			if qv >= 31300:
				tp = layer.temporalProperties()
				if tp.isActive():
					hadtp = True
				else:
					hadtp = False
			else:
				hadtp = False
		if self.tuView.tuProject is not None:
			if type(self.tuView.tuProject.hastp) is bool:
				hadtp = self.tuView.tuProject.hastp
			elif type(self.tuView.tuProject.hastp) is dict:
				if name in self.tuView.tuProject.hastp:
					hadtp = self.tuView.tuProject.hastp[name]  # override hadtp with this
		self.configTemporalProperties(layer)

		# this is to capture minimums - loop through the result names once and figure out if there are double ups that are static
		mdGroupNames = []
		for i in range(layer.datasetGroupCount()):
			mdGroupNames.append(layer.datasetGroupMetadata(QgsMeshDatasetIndex(i, -1)).name())
		for i, name_ in enumerate(mdGroupNames):
			if 'minimum dt' in name_.lower():
				if self.tuView.tuResults.isMaximumResultType(name_, layer, i):
					if '/Maximum' not in name_:
						if '/Final' in name_:
							mdGroupNames[i] = re.sub(r'/Final', '/Maximums', name_)
						else:
							mdGroupNames[i] = '{0}/Maximums'.format(name_)
						continue
			count = mdGroupNames.count(name_)
			if count > 1:
				if self.tuView.tuResults.isStatic(name_, layer, i):
					if ext.upper() == '.XMDF':
						mdGroupNames[i] = '{0}/Minimums'.format(name_)

		# for i in range(dp.datasetGroupCount()):
		for i, name_ in enumerate(mdGroupNames):
			# Get result type e.g. depth, velocity, max depth
			mdGroup = layer.datasetGroupMetadata(QgsMeshDatasetIndex(i,-1))  # Group Metadata
			id, id2 = self.getResultTypeNames(mdGroup, ext, resultTypes, name_)

			# special case for minimum dt
			if 'minimum dt' in id.lower():
				if self.tuView.tuResults.isMaximumResultType(id, layer, i):
					if '/Maximum' not in id:
						id = f'{id}/Maximums'

			# add to temporal result type list
			resultTypes.append(id)
			if id2 is not None:
				resultTypes.append(id2)

			# initiate in result dict
			results[name][id] = {'times': {},
			                     'is3dDataset': self.is3dDataset(i, layer),
			                     'timeUnit': self.getTimeUnit(layer),
			                     # 'referenceTime': self.tuView.tuOptions.zeroTime,
			                     'referenceTime': self.getReferenceTime(layer, self.tuView.tuOptions.zeroTime),
			                     'isMax': self.tuView.tuResults.isMaximumResultType(id, layer, i),
			                     'isMin':self.tuView.tuResults.isMinimumResultType(id, layer, i),
			                     'isStatic': self.tuView.tuResults.isStatic(id, layer, i),
			                     'isTemporal': self.tuView.tuResults.isTemporal(id, layer, i),
			                     'hadTemporalProperties': hadtp,
			                     'ext': ext,
			                     'isMesh': True,
			                     #'averagingMethod': None,
			                     }  # add result type to results dictionary
			if id2 is not None:
				results[name][id2] = {'times': {},
				                      'is3dDataset': self.is3dDataset(i, layer),
				                      'timeUnit': self.getTimeUnit(layer),
				                      # 'referenceTime': self.tuView.tuOptions.zeroTime,
				                      'referenceTime': self.getReferenceTime(layer, self.tuView.tuOptions.zeroTime),
				                      'isMax': self.tuView.tuResults.isMaximumResultType(id, layer, i),
				                      'isMin':self.tuView.tuResults.isMinimumResultType(id, layer, i),
				                      'isStatic': self.tuView.tuResults.isStatic(id, layer, i),
				                      'isTemporal': self.tuView.tuResults.isTemporal(id, layer, i),
				                      'hadTemporalProperties': hadtp,
				                      'ext': ext,
				                      'isMesh': True,
				                      #'averagingMethod': None,
				                      }  # add result type to results dictionary

			# apply any default rendering styles to datagroup
			if loadRenderStyle:
				if id:
					resultType = self.tuView.tuResults.stripMaximumName(mdGroup.name())
					resultType = self.tuView.tuResults.stripMaximumName(resultType)
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
					if vectorProperties and len(vectorProperties) >= 27 and vectorProperties[:27] == '<!DOCTYPE tuflow_meshlayer>':
						self.applyVectorRenderSettings(layer, i, vectorProperties)
					# if vectorProperties:
					# 	self.applyVectorRenderSettings(layer, i, vectorProperties)

			# record datasetindex for each timestep
			for j in range(layer.datasetCount(QgsMeshDatasetIndex(i,-1))):
				md = layer.datasetMetadata(QgsMeshDatasetIndex(i, j))  # metadata for individual timestep

				# TUFLOW special timesteps
				st = self.recordSpecialTime(name, md.time(), id, id2, i, j, ext)

				if not st:
					self.recordTime(layer, mdGroup, md, name, id, id2, i, j)

		# align first timestep values
		# e.g. if first temporal timestep is 1 hr
		# bed elevation has timestep 0 hrs by default
		# 0 hrs will show up in the time slider which is not ideal (that isn't when the output starts)
		# change all instances of this to the first temporal output
		self.alignFirstTimestepValues(name)

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

	def is3dDataset(self, mdi, lyr):
		"""

		"""

		for i in range(lyr.datasetCount(QgsMeshDatasetIndex(mdi, -1))):
			try:
				return lyr.dataset3dValues(QgsMeshDatasetIndex(mdi, i), 0, 1).verticalLevelsCount()[0] > 1
			except:
				continue

		return False

	def recordTime(self, layer, mdg, md, name, id, id2, i, j):
		qv = Qgis.QGIS_VERSION_INT

		if qv < 31600:
			self.recordTime_old(layer, mdg, md, name, id, id2, i, j)
		else:
			self.recordTime_31600(layer, mdg, md, name, id, id2, i, j)

	def recordTime_old(self, layer, mdg, md, name, id, id2, i, j):
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

		# t = md.time() - (zeroTime - qdt2dt(layer.temporalProperties().referenceTime())).total_seconds() / 60. / 60.
		t = md.time()
		# if self.getReferenceTime(layer) != self.tuView.tuOptions.zeroTime:
		if self.getReferenceTime(layer) != \
				datetime2timespec(self.tuView.tuOptions.zeroTime,
				                  self.tuView.tuResults.loadedTimeSpec,
				                  1):
			# dt = self.getReferenceTime(layer) - self.tuView.tuOptions.zeroTime
			if self.tuView.tuOptions.timeUnits == 's':
				factor = 60. * 60.
			else:  # 'h'
				factor = 1.
			# t += dt.total_seconds() / factor
			t /= factor

			t += (self.getReferenceTime(layer)
			      - datetime2timespec(self.tuView.tuOptions.zeroTime,
			                          self.tuView.tuResults.loadedTimeSpec,
			                          1)).total_seconds() / 60. / 60.

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
					#date = self.getReferenceTime(layer) + timedelta(seconds=t)
					# date = datetime2timespec(self.tuView.tuOptions.zeroTime,
					#                          self.tuView.tuResults.loadedTimeSpec,
					#                          self.tuView.tuResults.timeSpec) \
					#        + timedelta(seconds=t)
				else:
					try:
						date = zeroTime + timedelta(hours=t)
						#date = datetime2timespec(self.tuView.tuOptions.zeroTime,
			            #              self.tuView.tuResults.loadedTimeSpec,
			            #              self.tuView.tuResults.timeSpec)\
						#       + timedelta(hours=t)
					except OverflowError:
						date = zeroTime + timedelta(seconds=t)
						# date = datetime2timespec(self.tuView.tuOptions.zeroTime,
						#                          self.tuView.tuResults.loadedTimeSpec,
						#                          self.tuView.tuResults.timeSpec) \
						#        + timedelta(seconds=t)
				date = roundSeconds(date, 2)
				timekey2date['{0:.6f}'.format(t)] = date
				time2date[t] = date
				date2timekey[date] = '{0:.6f}'.format(t)
				date2time[date] = t

				if qv >= 31300:
					# date_tspec = datetime2timespec(date, self.tuView.tuResults.loadedTimeSpec, 1)
					date_tspec = datetime2timespec(date, self.tuView.tuResults.loadedTimeSpec, 1)
				else:
					date_tspec = date
				self.tuView.tuResults.timekey2date_tspec['{0:.6f}'.format(t)] = date_tspec
				self.tuView.tuResults.time2date_tspec[t] = date_tspec
				self.tuView.tuResults.date_tspec2timekey[date_tspec] = '{0:.6f}'.format(t)
				self.tuView.tuResults.date_tspec2time[date_tspec] =  t
				self.tuView.tuResults.date2date_tspec[date] = date_tspec
				self.tuView.tuResults.date_tspec2date[date_tspec] = date

	def recordTime_31600(self, layer, mdg, md, name, id, id2, i, j):
		"""

		"""

		results = self.tuView.tuResults.results  # dict
		timekey2time = self.tuView.tuResults.timekey2time  # dict

		t = md.time()
		if self.tuView.tuOptions.timeUnits == 's':
			factor = 60. * 60.
		else:  # 'h'
			factor = 1.
		t /= factor

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

	def copyResults2dDict(self, d1):
		"""copy dictionary values from d1 to d2"""

		return {k: v for k, v in d1.items()}

	def defaultResults2dDict(self):

		return {'times': {},
		        'is3dDataset': False,
		        'timeUnit': 'h',
		        'referenceTime': self.tuView.tuOptions.zeroTime,
		        'isMax': False,
		        'isMin': False,
		        'isStatic': False,
		        'isTemporal': False,
		        'hadTemporalProperties': False,
		        'ext': '.dat',
		        'isMesh': True,
		        'averagingMethod': None,
		        }

	def recordSpecialTime(self, name, t, id, id2, i, j, ext):
		"""

		"""

		results = self.tuView.tuResults.results  # dict

		if ext.upper() == '.DAT':
			# ri = TuResultsIndex(name, id)
			ri = TuResultsIndex(name, id, None, False, False, self.tuView.tuResults, self.tuView.tuOptions.timeUnits)
			timeUnits = self.tuView.tuResults.getTimeUnit(ri)  # is the same for the whole layer
			if t == 900001.0 and timeUnits == 'h':  # time of peak h
				specialName = 'Time of Peak h'
				self.checkRecordSpecialTime(t, specialName)
				if self.bRecordSpecialTime:
					if id in results[name]:
						results[name][specialName] = self.copyResults2dDict(results[name][id])
						del results[name][id]
					else:
						results[name][specialName] = self.defaultResults2dDict()
					# results[name][specialName] = {'times': {'0.000000': (0, 1, QgsMeshDatasetIndex(i, j))}}
					results[name][specialName]['times'] = {'0.000000': (0, 1, QgsMeshDatasetIndex(i, j))}
					results[name][specialName]['isTemporal'] = False
					results[name][specialName]['isStatic'] = True
					return True
			elif t == 900002.0 and timeUnits == 'h':  # time of peak V
				specialName = 'Time of Peak V'
				self.checkRecordSpecialTime(t, specialName)
				if self.bRecordSpecialTime:
					if id in results[name]:
						results[name][specialName] = self.copyResults2dDict(results[name][id])
						del results[name][id]
					else:
						results[name][specialName] = self.defaultResults2dDict()
					# results[name][specialName] = {'times': {'0.000000': (0, 1, QgsMeshDatasetIndex(i, j))}}
					results[name][specialName]['times'] = {'0.000000': (0, 1, QgsMeshDatasetIndex(i, j))}
					results[name][specialName]['isTemporal'] = False
					results[name][specialName]['isStatic'] = True
					return True
			elif 100000 < t < 200000 and t != 111111.0 and timeUnits == 'h':
				value = t - 100000.0
				specialName = 'Time of Cutoff {0}'.format(value)
				self.checkRecordSpecialTime(t, specialName)
				if self.bRecordSpecialTime:
					if id in results[name]:
						results[name][specialName] = self.copyResults2dDict(results[name][id])
						del results[name][id]
					else:
						results[name][specialName] = self.defaultResults2dDict()
					# results[name][specialName] = {'times': {'0.000000': (0, 1, QgsMeshDatasetIndex(i, j))}}
					results[name][specialName]['times'] = {'0.000000': (0, 1, QgsMeshDatasetIndex(i, j))}
					results[name][specialName]['isTemporal'] = False
					results[name][specialName]['isStatic'] = True
					return True
			elif 200000 < t < 300000 and t != 222222.0 and timeUnits == 'h':
				value = t - 200000.0
				specialName = 'Time Exc Cutoff {0}'.format(value)
				self.checkRecordSpecialTime(t, specialName)
				if self.bRecordSpecialTime:
					if id in results[name]:
						results[name][specialName] = self.copyResults2dDict(results[name][id])
						del results[name][id]
					else:
						results[name][specialName] = self.defaultResults2dDict()
					value = t - 200000.0
					# results[name][specialName] = {'times': {'0.000000': (0, 1, QgsMeshDatasetIndex(i, j))}}
					results[name][specialName]['times'] = {'0.000000': (0, 1, QgsMeshDatasetIndex(i, j))}
					results[name][specialName]['isTemporal'] = False
					results[name][specialName]['isStatic'] = True
					return True
			elif int(t) == 99999 and timeUnits == 'h':
				if not self.tuView.tuResults.isMaximumResultType(id):
					specialName = '{0}/Maximums'.format(id)
					results[name][specialName] = self.copyResults2dDict(results[name][id])
					results[name][specialName]['times'] = {'99999.000000': (99999, 1, QgsMeshDatasetIndex(i, j))}
					results[name][specialName]['isTemporal'] = False
					results[name][specialName]['isStatic'] = True
					results[name][specialName]['isMax'] = True
					if id2 is not None:
						if not self.tuView.tuResults.isMaximumResultType(id2):
							specialName = '{0}/Maximums'.format(id2)
							results[name][specialName] = self.copyResults2dDict(results[name][id2])
							results[name][specialName]['times'] = {'99999.000000': (99999, 2, QgsMeshDatasetIndex(i, j))}
							results[name][specialName]['isTemporal'] = False
							results[name][specialName]['isStatic'] = True
							results[name][specialName]['isMax'] = True
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

	def getResultTypeNames(self, mdg, ext, ids, name_=None):
		"""

		"""

		id = None
		id2 = None

		if name_ is None:
			name_ = mdg.name()

		if re.findall(r'^max_(?!time)', name_):
			name__ = re.split(r'^max_(?!time)', name_)
			if len(name__) > 1:
				name_ = '{0}/Maximums'.format(name__[-1])
		elif re.findall(r'^min_(?!time)', name_):
			name__ = re.split(r'^min_(?!time)', name_)
			if len(name__) > 1:
				name_ = '{0}/Minimums'.format(name__[-1])

		# if ext.upper() != ".XMDF":
		if ext.upper() == ".XMDF" and (mdg.name() == 'Velocity' or mdg.name() == 'Velocity/Maximums' or
				mdg.name() == 'Unit Flow' or mdg.name() == 'Unit Flow/Maximums' or
				mdg.name() == 'Vector Unit Flow' or mdg.name() == 'Vector Unit Flow/Maximums' or
				mdg.name() == 'Vector Velocity' or mdg.name() == 'Vector Velocity/Maximums'):
			id = self.addCounter(name_, ids)
		else:
			if mdg.isScalar():
				id = self.addCounter(name_, ids)

			if mdg.isVector():
				if id is None:
					# if name is not None
					id = self.addCounter(name_, ids)
					if self.tuView.tuResults.isMaximumResultType(name_) or self.tuView.tuResults.isMinimumResultType(name_):
						id2 = self.addCounter('{0}'.format(' Vector/'.join(name_.split('/'))), ids)
					else:
						id2 = self.addCounter('{0} Vector'.format(name_), ids)
					# else:
					# 	id = self.addCounter(mdg.name(), ids)
					# 	if TuResults.isMaximumResultType(mdg.name()) or TuResults.isMinimumResultType(mdg.name()):
					# 		id2 = self.addCounter('{0}'.format(' Vector/'.join(mdg.name().split('/'))), ids)
					# 	else:
					# 		id2 = self.addCounter('{0} Vector'.format(mdg.name()), ids)
				else:
					# if name is not None
					if self.tuView.tuResults.isMaximumResultType(name_) or self.tuView.tuResults.isMinimumResultType(name_):
						id2 = self.addCounter('{0}'.format(' Vector/'.join(name_.split('/'))), ids)
					else:
						id2 = self.addCounter('{0} Vector'.format(name_), ids)
					# else:
					# 	if TuResults.isMaximumResultType(mdg.name()) or TuResults.isMinimumResultType(mdg.name()):
					# 		id2 = self.addCounter('{0}'.format(' Vector/'.join(mdg.name().split('/'))), ids)
					# 	else:
					# 		id2 = self.addCounter('{0} Vector'.format(mdg.name()), ids)
		# else:
		# 	if name_ is not None:
		# 		id = self.addCounter(name_, ids)
		# 	else:
		# 		id = self.addCounter(mdg.name(), ids)

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

	def updateActiveMeshLayers(self, *args):
		"""
		Updates the list of selected 2D results.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.activeMeshLayers.clear()
		openResults = self.tuView.OpenResults  # QListWidget

		# disconnect some signals
		meshLayers = findAllMeshLyrs()
		nodes = []
		for ml in meshLayers:
			layer = tuflowqgis_find_layer(ml)
			node = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
			if not node:
				continue
			try:
				node.visibilityChanged.disconnect(self.layerVisibilityChanged)
			except Exception:
				pass
			nodes.append(node)
		
		for r in range(openResults.count()):
			item = openResults.item(r)
			
			# find selected layer
			layer = tuflowqgis_find_layer(item.text())
			if layer is not None:
				continue_ = False
				for a in args:
					if isinstance(a, list) and a and isinstance(a[0], str):
						layer_for_removal = [x for x in a if tuflowqgis_find_layer(x, search_type='layerId') and tuflowqgis_find_layer(x, search_type='layerId') == layer]
						if layer_for_removal:
							continue_ = True
							break
				if continue_:
					continue
				if isinstance(layer, QgsMeshLayer):
					if item.isSelected():
						self.activeMeshLayers.append(layer)
					else:
						self.renderMap(layers=[layer], turn_off=True)

		self.renderMap()

		# connect signals back up
		for node in nodes:
			node.visibilityChanged.connect(self.layerVisibilityChanged)
		
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
			try:
				node = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
			except RuntimeError:
				try:
					self.activeMeshLayers.remove(layer)
				except ValueError:
					pass
				except RuntimeError:
					pass
				continue
			if turn_off:
				activeScalarIndex = None
				activeVectorIndex = None
				if node is not None and not turn_off:
					node.setItemVisibilityChecked(False)
			else:
				if node is not None:
					node.setItemVisibilityChecked(True)
				activeScalarIndex = TuResultsIndex(layer.name(), self.activeScalar,
				                                   self.tuView.tuResults.activeTime, self.tuView.tuResults.isMax('scalar'),
				                                   self.tuView.tuResults.isMin('scalar'), self.tuView.tuResults, self.tuView.tuOptions.timeUnits)
				activeVectorIndex = TuResultsIndex(layer.name(), self.activeVector,
				                                   self.tuView.tuResults.activeTime, self.tuView.tuResults.isMax('vector'),
				                                   self.tuView.tuResults.isMin('vector'), self.tuView.tuResults, self.tuView.tuOptions.timeUnits)
			activeScalarMeshIndex = self.tuView.tuResults.getResult(activeScalarIndex, force_get_time='next lower',
			                                                        mesh_index_only=True)
			activeVectorMeshIndex = self.tuView.tuResults.getResult(activeVectorIndex, force_get_time='next lower',
			                                                        mesh_index_only=True)
			# render active datasets
			rs = layer.rendererSettings()
			setActiveScalar, setActiveVector = TuResults2D.meshRenderVersion(rs)
			setActiveScalar(activeScalarMeshIndex)
			setActiveVector(activeVectorMeshIndex)

			# override averaging method for velocity in 2D stacked NetCDF meshes
			self.averingMethodOverride(activeScalarIndex, activeVectorIndex, rs)

			# turn on / off mesh and triangles
			self.renderNativeMesh(layer, rs)

			layer.setRendererSettings(rs)

		# disconnect map canvas refresh if it is connected - used for rendering after loading from project
		try:
			self.tuView.canvas.mapCanvasRefreshed.disconnect(self.renderMap)
		except:
			pass
			
		return True

	def averingMethodOverride(self, activeScalarIndex, activeVectorIndex, rs):
		"""
		Issue with QGIS 3.28 where velocity maximum in 2D stacked NetCDF meshes isn't rendered correctly.
		This routine will override the averaging method to 'single layer from top' for velocity in these cases.
		If not velocity then then the averaging method will be set to the previous method.
		"""

		av_method_override = False
		broken_result_types = ['velocity']

		# start with basic checks to see if we want to continue
		if Qgis.QGIS_VERSION_INT < 31300:
			return

		if (activeScalarIndex and activeScalarIndex.result and activeScalarIndex.resultType and
				self.tuView.tuResults.results[activeScalarIndex.result].get(activeScalarIndex.resultType) and
				self.tuView.tuResults.results[activeScalarIndex.result][activeScalarIndex.resultType]['ext'] == '.nc') or \
				(activeVectorIndex and activeVectorIndex.result and activeVectorIndex.resultType and
				 self.tuView.tuResults.results[activeVectorIndex.result].get(activeVectorIndex.resultType) and
				 self.tuView.tuResults.results[activeVectorIndex.result][activeVectorIndex.resultType]['ext'] == '.nc'):
			pass
		else:
			return

		# get the results
		if activeScalarIndex.result and activeScalarIndex.resultType:
			result_name = activeScalarIndex.result
			res = self.tuView.tuResults.results[activeScalarIndex.result][activeScalarIndex.resultType]
		elif activeVectorIndex.result and activeVectorIndex.resultType:
			result_name = activeVectorIndex.result
			res = self.tuView.tuResults.results[activeVectorIndex.result][activeVectorIndex.resultType]
		else:
			result_name = ''
			res = None

		if (self.tuView.tuResults.isMax('scalar') or self.tuView.tuResults.isMax('vector')) and \
				res and not res['is3dDataset']:
			cur_av_method = rs.averagingMethod()
			if not self.is_single_layer_from_top(cur_av_method):
				self.layer_averaging_methods[result_name] = cur_av_method.clone()
			new_av_method = QgsMeshMultiLevelsAveragingMethod(1, 1, True)
			rs.setAveragingMethod(new_av_method)
		elif self.layer_averaging_methods.get(result_name):
			rs.setAveragingMethod(self.layer_averaging_methods.get(result_name))
			self.layer_averaging_methods[result_name] = None

	def is_single_layer_from_top(self, av_method):
		return isinstance(av_method, QgsMeshMultiLevelsAveragingMethod) and \
			av_method.isSingleLevel() and av_method.countedFromTop() and \
			av_method.startVerticalLevel() == 1
	
	def removeResults(self, resList):
		"""
		Removes the 2D results from the indexed results and ui.
		
		:param resList: list -> str result name e.g. M01_5m_001
		:return: bool -> True for successful, False for unsuccessful
		"""

		results = self.tuView.tuResults.results

		try:
			self.tuView.OpenResults.itemSelectionChanged.disconnect(self.tuView.resultSelectionChangeSignal)
		except:
			pass

		for res in resList:
			if res in results.keys():
				# remove from indexed results
				for resultType in list(results[res].keys()):
					# if '_ts' not in resultType and '_lp' not in resultType:
					if self.tuView.tuResults.isMapOutputType(resultType):
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

		self.tuView.resultSelectionChangeSignal = self.tuView.OpenResults.itemSelectionChanged.connect(
			lambda: self.tuView.resultsChanged('item clicked'))
						
		return True
	
	def loadOpenMeshLayers(self, **kwargs):
		"""
		Checks the workspace for already open mesh layers and adds datasets to mesh and loads into interface.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		qv = Qgis.QGIS_VERSION_INT
		layer = kwargs['layer'] if 'layer' in kwargs.keys() else None

		try:
			self.tuView.OpenResults.itemSelectionChanged.disconnect(self.tuView.resultSelectionChangeSignal)
			need2connect = True
		except:
			need2connect = False
		
		if layer:
			meshLayers = [layer]
		else:
			meshLayers = findAllMeshLyrs()
		
		for ml in meshLayers:
			# layer = tuflowqgis_find_layer(ml)
			layer = None
			for layer_ in QgsProject.instance().mapLayersByName(ml):
				if isinstance(layer_, QgsMeshLayer):
					layer = layer_
			if layer is not None:
				
				if layer.dataProvider().datasetGroupCount() == 0:
					return
				elif layer.dataProvider().datasetGroupCount() > 0:
					self.getResultMetaData(ml, layer, loadRenderStyle=False)
					self.tuView.OpenResults.addItem(ml)

					k = self.tuView.OpenResults.findItems(layer.name(), Qt.MatchRecursive)[0]
					k.setSelected(True)
				
				layer.dataProvider().datasetGroupsAdded.connect(self.datasetGroupsAdded)
				try:
					layer.nameChanged.disconnect()
				except:
					pass
				name = layer.name()
				layer.nameChanged.connect(lambda: self.layerNameChanged(layer, name, layer.name()))

		if need2connect:
			self.tuView.resultSelectionChangeSignal = self.tuView.OpenResults.itemSelectionChanged.connect(
				lambda: self.tuView.resultsChanged('item clicked'))
			self.tuView.resultsChanged('item clicked')

	def layerReloaded(self, layer):
		results = self.tuView.tuResults.results
		for result_name, result_items in results.items():
			if isinstance(result_items, dict):
				for rtype in list(result_items.keys()):
					if self.tuView.tuResults.isMapOutputType(rtype):
						del result_items[rtype]

		if layer.dataProvider().datasetGroupCount() > 0:
			self.getResultMetaData(layer.name(), layer)
			self.tuView.tuResults.updateResultTypes()

		self.tuView.resultsChanged()

	def layerStyleChanged(self, layer):
		if Qgis.QGIS_VERSION_INT < 31600:
			return

		active_group = layer.rendererSettings().activeScalarDatasetGroup()
		if active_group < 0:
			self.active_style_group_name = None
			self.active_style = None
			return

		renderer_settings = layer.rendererSettings()
		active_dataset = layer.datasetGroupMetadata(QgsMeshDatasetIndex(renderer_settings.activeScalarDatasetGroup())).name()
		active_dataset = self.tuView.tuResults.stripMaximumName(active_dataset)
		active_dataset = self.tuView.tuResults.stripMinimumName(active_dataset)
		if active_dataset != self.active_style_group_name:
			self.active_style_group_name = active_dataset
			self.active_style = self.scalarDatasetStyleXml(renderer_settings, renderer_settings.activeScalarDatasetGroup())
			return

		new_style = self.scalarDatasetStyleXml(renderer_settings, renderer_settings.activeScalarDatasetGroup())
		if new_style != self.active_style:
			self.active_style = new_style
			for i in range(layer.datasetGroupCount()):
				if i == active_group:
					continue

				dataset = layer.datasetGroupMetadata(QgsMeshDatasetIndex(i)).name()
				dataset = self.tuView.tuResults.stripMaximumName(dataset)
				dataset = self.tuView.tuResults.stripMinimumName(dataset)
				if dataset == active_dataset:
					doc = QDomDocument('tuflow_meshlayer')
					statusOK, errorStr, errorLine, errorColumn = doc.setContent(self.active_style, True)
					if not statusOK:
						print('ERROR reading style xml')
						return

					scalar_settings = renderer_settings.scalarSettings(i)

					scalar_settings.readXml(doc.documentElement())
					renderer_settings.setScalarSettings(i, scalar_settings)
					layer.setRendererSettings(renderer_settings)

	def scalarDatasetStyleXml(self, renderer_settings, scalar_group):
		if scalar_group < 0:
			return

		scalar_settings = renderer_settings.scalarSettings(scalar_group)
		doc = QDomDocument('tuflow_meshlayer')
		doc.appendChild(scalar_settings.writeXml(doc))
		return doc.toString()

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

	def repaintRequested(self, *args, **kwargs):
		"""
		Redoes all the dates.
		"""

		qv = Qgis.QGIS_VERSION_INT
		results = self.tuView.tuResults.results

		signalConnected = False
		meshLayers = findAllMeshLyrs()
		for ml in meshLayers:
			layer = tuflowqgis_find_layer(ml)
			try:
				layer.repaintRequested.disconnect(self.repaintRequested)
				signalConnected = True
			except:
				pass

		updated = False
		for r in results:
			if tuflowqgis_find_layer(r) is not None:
				layer = tuflowqgis_find_layer(r)
				if not isinstance(layer, QgsMeshLayer):
					continue
				for restype in results[r]:
					if self.tuView.tuResults.isMapOutputType(restype):
						# see if reference time has been changed
						if qv >= 31600:
							if 'referenceTime' in results[r][restype]:
								if results[r][restype]['referenceTime'] != self.getReferenceTime(layer):
									updated = True
									results[r][restype]['referenceTime'] = self.getReferenceTime(layer)

		if updated:
			self.tuView.tuResults.updateDateTimes()
			self.tuView.tuResults.updateResultTypes()

		# for QGIS 3.18.1 hack to force mesh to show
		meshLayers = findAllMeshLyrs()
		for ml in meshLayers:
			layer = tuflowqgis_find_layer(ml)
			if layer in self.activeMeshLayers:
				rs = layer.rendererSettings()
				rsMesh = rs.nativeMeshSettings()
				rsMesh.setEnabled(self.tuView.tuOptions.showGrid)
				rs.setNativeMeshSettings(rsMesh)
				layer.setRendererSettings(rs)
			else:
				rs = layer.rendererSettings()
				rsMesh = rs.nativeMeshSettings()
				rsMesh.setEnabled(False)
				rs.setNativeMeshSettings(rsMesh)
				layer.setRendererSettings(rs)

		if signalConnected:
			meshLayers = findAllMeshLyrs()
			for ml in meshLayers:
				layer = tuflowqgis_find_layer(ml)
				layer.repaintRequested.connect(self.repaintRequested)

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
		if qv < 31600:
			return False

		rs = layer.rendererSettings()
		rsVector = rs.vectorSettings(datasetGroupIndex)

		doc = QDomDocument('tuflow_meshlayer')
		statusOK, errorStr, errorLine, errorColumn = doc.setContent(vectorProperties, True)
		if not statusOK:
			return False

		rsVector.readXml(doc.documentElement())
		rs.setVectorSettings(datasetGroupIndex, rsVector)
		layer.setRendererSettings(rs)
		
		return True
	
	def layerNameChanged(self, layer, oldName, newName):
		"""
		
		
		:param layer:
		:return:
		"""
		
		layer.nameChanged.disconnect()

		# change name in results dict
		results = self.tuView.tuResults.results
		for key, entry in results.copy().items():
			if key == oldName:
				results[newName] = entry
				del results[oldName]

		if isinstance(layer, QgsRasterLayer):
			self.tuView.tuResults.tuResultsNcGrid.layerNameChanged(oldName, newName)
		
		# change name in list widget
		selectedItems = self.tuView.OpenResults.selectedItems()
		for i in range(self.tuView.OpenResults.count()):
			item = self.tuView.OpenResults.item(i)
			if item.text() == oldName:
				self.tuView.OpenResults.takeItem(i)
				self.tuView.OpenResults.insertItem(i, newName)
				if item in selectedItems:
					self.tuView.OpenResults.item(i).setSelected(True)
					
		# # change name in results dict
		# results = self.tuView.tuResults.results
		# for key, entry in results.items():
		# 	if key == oldName:
		# 		results[newName] = entry
		# 		del results[oldName]
				
		layer.nameChanged.connect(lambda: self.layerNameChanged(layer, newName, layer.name()))
				
		return True
	
	def alignFirstTimestepValues(self, result):
		"""
		If first temporal output is not zero, change all single
		datatimesteps with zero value to first timestep
		
		:return:
		"""

		qv = Qgis.QGIS_VERSION_INT

		results = self.tuView.tuResults.results
		firstTime = None
		
		# iterate through each result set
		# for result in results:
		# find temporal data and get first timestep
		for resultType in results[result]:
			if firstTime is not None:
				break
			if self.tuView.tuResults.isMapOutputType(resultType):
			# elif '_ts' not in resultType and '_lp' not in resultType and '_particles' not in resultType:
				if len(results[result][resultType]['times']) > 1:
					for i in results[result][resultType]['times']:
						firstTime = results[result][resultType]['times'][i][0]
						break

		if firstTime is not None:
			#if firstTime == 0:
			#	continue  # move onto next result dataset
			#else:  # find time 0 values and change to firstTime
			for resultType in results[result]:
				#if '_ts' not in resultType and '_lp' not in resultType:
				if self.tuView.tuResults.isMapOutputType(resultType):
					if len(results[result][resultType]['times']) == 1:
						for i in list(results[result][resultType]['times'].keys())[:]:
							#if results[result][resultType]['times'][i][0] == 0:
							timeKey = '{0:.6f}'.format(firstTime)
							dataType = results[result][resultType]['times'][i][1]
							meshIndex = results[result][resultType]['times'][i][2]
							if timeKey != i:
								results[result][resultType]['times'][timeKey] = (firstTime, dataType, meshIndex)
								del results[result][resultType]['times'][i]

							# also delete from dicts
							if qv < 31600:
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
							else:
								a = sorted([x for x in self.tuView.tuResults.timekey2time.keys()])
								if a[0] != timeKey:
									del self.tuView.tuResults.timekey2time[a[0]]

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

		if layer not in self.activeMeshLayers:
			if rs.nativeMeshSettings().isEnabled() or self.tuView.tuOptions.showGrid:
				rsMesh = rs.nativeMeshSettings()
				rsMesh.setEnabled(False)
				rs.setNativeMeshSettings(rsMesh)
				# layer.setRendererSettings(rs)
			if rs.triangularMeshSettings().isEnabled() or self.tuView.tuOptions.showTriangles:
				rsTriangles = rs.triangularMeshSettings()
				rsTriangles.setEnabled(False)
				rs.setTriangularMeshSettings(rsTriangles)
				# layer.setRendererSettings(rs)
		else:
			if rs.nativeMeshSettings().isEnabled() != self.tuView.tuOptions.showGrid:
				rsMesh = rs.nativeMeshSettings()
				rsMesh.setEnabled(self.tuView.tuOptions.showGrid)
				rs.setNativeMeshSettings(rsMesh)
				# layer.setRendererSettings(rs)
			self.tuView.tuPlot.tuPlotToolbar.meshGridAction.setChecked(self.tuView.tuOptions.showGrid)
			if rs.triangularMeshSettings().isEnabled() != self.tuView.tuOptions.showTriangles:
				rsTriangles = rs.triangularMeshSettings()
				rsTriangles.setEnabled(self.tuView.tuOptions.showTriangles)
				rs.setTriangularMeshSettings(rsTriangles)
				# layer.setRendererSettings(rs)

	def getReferenceTime(self, layer, defaultZeroTime=None):
		"""

		"""
		qv = Qgis.QGIS_VERSION_INT

		rt = None
		if qv >= 31300:
			rt = layer.temporalProperties().referenceTime()  # assume reference time is always timespec 1
		else:
			try:  # unclear what version this was introduced
				rt = layer.timeSettings().absoluteTimeReferenceTime()
			except:
				pass

		if rt is not None and rt.isValid():
			return qdt2dt(rt)
		else:
			if defaultZeroTime is not None:
				# return datetime2timespec(defaultZeroTime, 1, self.tuView.tuResults.timeSpec)
				return defaultZeroTime
			else:
				# return datetime2timespec(self.tuView.tuOptions.zeroTime, self.tuView.tuResults.loadedTimeSpec, self.tuView.tuResults.timeSpec)
				return datetime2timespec(self.tuView.tuOptions.zeroTime, self.tuView.tuResults.loadedTimeSpec, 1)

	def configTemporalProperties(self, layer):
		"""

		"""
		qv = Qgis.QGIS_VERSION_INT

		if qv >= 31300:
			tp = layer.temporalProperties()
			if not tp.isActive():
				tp.setIsActive(True)

			if not tp.referenceTime().isValid() or self.tuView.tuResults.loadedTimeSpec != self.tuView.tuResults.timeSpec:
				layer.setReferenceTime(dt2qdt(self.getReferenceTime(layer), 1))

	def getBedAndWLNames(self, layer, isMax=False, isMin=False):
		possibleWlNames = ['water level', 'water surface elevation', 'h']
		possibleBdNames = ['bed elevation']
		wlname = None
		bdname = None
		for i in range(layer.dataProvider().datasetGroupCount()):
			name = layer.dataProvider().datasetGroupMetadata(i).name()
			if name.lower() in possibleBdNames:
				bdname = name
				continue
			if isMax:
				if self.tuView.tuResults.isMaximumResultType(name):
					name = self.tuView.tuResults.stripMaximumName(name)
					if name.lower() in possibleWlNames:
						wlname = name
			elif isMin:
				if self.tuView.tuResults.isMinimumResultType(name):
					name = self.tuView.tuResults.stripMinimumName(name)
					if name.lower() in possibleWlNames:
						wlname = name
			else:
				if name.lower() in possibleWlNames:
					wlname = name
			if wlname is not None and bdname is not None:
				break

		return bdname, wlname

	def layerVisibilityChanged(self):
		# disconnect some signals
		skipConnect = False
		try:
			self.tuView.project.layersAdded.disconnect(self.tuView.layersAdded)
		except:
			skipConnect = True
			pass
		skipConnect2 = False
		try:
			self.tuView.OpenResults.itemSelectionChanged.disconnect(self.tuView.resultSelectionChangeSignal)
		except:
			pass
		meshLayers = findAllMeshLyrs()
		for ml in meshLayers:
			layer = tuflowqgis_find_layer(ml)
			try:
				layer.dataProvider().datasetGroupsAdded.disconnect(self.datasetGroupsAdded)
			except:
				pass
			try:
				layer.repaintRequested.disconnect(self.repaintRequested)
			except:
				pass

		for res in self.results2d:
			layer = tuflowqgis_find_layer(res)
			if layer is None:
				continue
			node = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
			k = self.tuView.OpenResults.findItems(res, Qt.MatchRecursive)[0]
			k.setSelected(node.itemVisibilityChecked())

		updated = self.updateActiveMeshLayers()  # update list of active mesh layers
		self.tuView.resultsChanged('item clicked')  # update tuflow viewer

		# connect load signals
		if not skipConnect:
			self.tuView.project.layersAdded.connect(self.tuView.layersAdded)
		self.tuView.resultSelectionChangeSignal = self.tuView.OpenResults.itemSelectionChanged.connect(
			lambda: self.tuView.resultsChanged('item clicked'))
		meshLayers = findAllMeshLyrs()
		for ml in meshLayers:
			layer = tuflowqgis_find_layer(ml)
			layer.dataProvider().datasetGroupsAdded.connect(self.datasetGroupsAdded)
			layer.repaintRequested.connect(self.repaintRequested)
