import os
from datetime import datetime, timedelta
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets import *
import tuflow.TUFLOW_results as TuflowResults
import tuflow.TUFLOW_results2013 as TuflowResults2013
from tuflow.tuflowqgis_library import getPathFromRel, tuflowqgis_apply_check_tf_clayer


class TuResults1D():
	"""
	Class for handling 1D results
	
	"""
	
	def __init__(self, TuView):
		self.tuView = TuView
		self.iface = self.tuView.iface
		self.results1d = {}  # dict -> converting result name to 1d results
		self.ids = []  # list -> str selected time series result lists
		self.domains = []  # list -> str selected time series result domains i.e. 1d, 2d, RL
		self.sources = []  # list -> str selected time series sources i.e. HU
		self.items1d = []  # list -> Dataset_View Tree node selected dataset view tree node item
		self.typesTS = []  # list -> str selected 1D time series result types
		self.pointTS = []
		self.lineTS = []
		self.regionTS = []
		self.activeType = -1  # -1 null, 0 pointTS, 1 lineTS, 2 RegionTS, 3 XS
		self.typesLP = []  # list -> str selected 1D long plot result types
		self.typesXS = []  # 1D cross section types
		self.lineXS = []  # 1D cross section line types
		self.typesXSRes = []  # store results that can be plotted on XS (i.e. water level)

	def importResults(self, inFilePaths):
		"""
		Loads in the 1D result class.

		:param inFileNames: list -> str tpc file paths
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		openResults = self.tuView.OpenResults  # QListWidget
		results = self.tuView.tuResults.results  # dict of indexed results
		
		for filePath in inFilePaths:
			
			# parse file names, ext, directory
			fdir, fname = os.path.split(filePath)
			root, ext = os.path.splitext(filePath)
			
			# 2013 results
			if ext.upper() == '.INFO':
				res = TuflowResults2013.ResData()
				res.Load(filePath, self.iface)
			
			# post 2013 results
			elif ext.upper() == '.TPC':
				res = TuflowResults.ResData()
				error, message = res.Load(filePath)
				if error:
					QMessageBox.critical(self.tuView, "TUFLOW Viewer", message)
					return False
				
			else:
				return False
			
			# index results
			index = self.getResultMetaData(res)
			self.results1d[res.displayname] = res
			
			# add result to list widget
			openResultNames = []
			for i in range(openResults.count()):
				openResultNames.append(openResults.item(i).text())
			if res.displayname not in openResultNames:
				openResults.addItem(res.displayname)  # add to widget
			k = openResults.findItems(res.displayname, Qt.MatchRecursive)[0]
			k.setSelected(True)
			
		return True
		
	def openGis(self, tpc):
		"""
		Opens 1D gis files. Will check if there are any features in the layer before loading into QGIS.

		:param tpc: str -> file path to tpc file
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# Initialise variables
		fpath = os.path.dirname(tpc)
		gisPoints = None
		gisLines = None
		gisRegions = None
		
		# get gis file location from tpc
		with open(tpc, 'r') as fo:
			for line in fo:
				if '==' in line:
					command, value = line.split('==')
					command = command.strip()
					value = value.strip()
					if 'gis plot layer points' in command.lower():
						gisPoints = getPathFromRel(fpath, value)
					elif 'gis plot layer lines' in command.lower():
						gisLines = getPathFromRel(fpath, value)
					elif 'gis plot layer regions' in command.lower():
						gisRegions = getPathFromRel(fpath, value)
		
		# load points gis file
		if gisPoints is not None:
			layer, basename = self.loadVectorLayer(gisPoints)
			if not layer.isValid():
				return False
			if layer.featureCount():  # only load if there are any features
				self.tuView.project.addMapLayer(layer)
				tuflowqgis_apply_check_tf_clayer(self.iface, layer=layer)
		# load lines gis file
		if gisLines is not None:
			layer, basename = self.loadVectorLayer(gisLines)
			if not layer.isValid():
				return False
			if layer.featureCount():  # only load if there are any features
				self.tuView.project.addMapLayer(layer)
				tuflowqgis_apply_check_tf_clayer(self.iface, layer=layer)
		# load regions gis file
		if gisRegions is not None:
			layer, basename = self.loadVectorLayer(gisRegions)
			if not layer.isValid():
				return False
			if layer.featureCount():  # only load if there are any features
				self.tuView.project.addMapLayer(layer)
				tuflowqgis_apply_check_tf_clayer(self.iface, layer=layer)
				
		return True
	
	def loadVectorLayer(self, fpath):
		"""
		Load the vector layer i.e. .shp or .mif

		:param fpath: str
		:return: QgsVectorLayer
		:return: str -> layer name e.g. 2d_bc_M01_001_L
		"""
		
		# Parse out file names
		basepath, fext = os.path.splitext(fpath)
		basename = os.path.basename(basepath)
		
		# Load vector
		layer = QgsVectorLayer(fpath, basename, 'ogr')
		
		return layer, basename
	
	def getResultMetaData(self, result):
		"""
		Get result types and timesteps for 1D results
		
		:param result: TUFLOW_results.ResData
		:return: bool -> True for successful, False for unsuccessful
		"""

		results = self.tuView.tuResults.results  # dict
		timekey2time = self.tuView.tuResults.timekey2time  # dict
		timekey2date = self.tuView.tuResults.timekey2date  # dict
		time2date = self.tuView.tuResults.time2date  # dict
		date2timekey = self.tuView.tuResults.date2timekey
		date2time = self.tuView.tuResults.date2time
		zeroTime = self.tuView.tuOptions.zeroTime  # datetime
		
		if result.displayname not in results.keys():
			results[result.displayname] = {}
		
		timesteps = result.timeSteps()
		for t in timesteps:
			timekey2time['{0:.6f}'.format(t)] = t
			timekey2date['{0:.6f}'.format(t)] = zeroTime + timedelta(hours=t)
			time2date[t] = zeroTime + timedelta(hours=t)
			date2timekey[zeroTime + timedelta(hours=t)] = '{0:.6f}'.format(t)
			date2time[zeroTime + timedelta(hours=t)] = t

		if 'point_ts' not in results[result.displayname].keys():
			resultTypes = result.pointResultTypesTS()
			metadata1d = (resultTypes, timesteps)
			results[result.displayname]['point_ts'] = metadata1d
		
		if 'line_ts' not in results[result.displayname].keys():
			resultTypes = result.lineResultTypesTS()
			if 'Velocity' in resultTypes and 'Velocity' in result.pointResultTypesTS():
				resultTypes.remove('Velocity')
			metadata1d = (resultTypes, timesteps)
			results[result.displayname]['line_ts'] = metadata1d
		
		if 'region_ts' not in results[result.displayname].keys():
			resultTypes = result.regionResultTypesTS()
			metadata1d = (resultTypes, timesteps)
			results[result.displayname]['region_ts'] = metadata1d
		
		if 'line_lp' not in results[result.displayname].keys():
			resultTypes = result.lineResultTypesLP()
			metadata1d = (resultTypes, timesteps)
			results[result.displayname]['line_lp'] = metadata1d
		
		return True
	
	def updateSelectedResults(self, layer):
		"""
		Updates selected 1D elements and 1D result class.
		
		:param layer: QgsVectorLayer
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# reset variables
		self.ids = []
		self.domains = []
		self.sources = []
		
		resVersion = []
		for result in self.tuView.OpenResults.selectedItems():
			if result.text() in self.tuView.tuResults.tuResults1D.results1d.keys():
				resVersion.append(self.tuView.tuResults.tuResults1D.results1d[result.text()].formatVersion)
		
		# collect ids and domain types
		for f in layer.selectedFeatures():
			if 1 not in resVersion:
				if 'ID' in f.fields().names() and 'Type' in f.fields().names() and 'Source' in f.fields().names():
					self.ids.append(f['ID'].strip())
					self.sources.append(f['Source'].strip())
					type = f['Type'].strip()
					if 'node' in type.lower() or 'chan' in type.lower():
						self.domains.append('1D')
					else:
						self.domains.append(type)  # 2D or RL
			elif 2 not in resVersion:
				id = f.attributes()[0]
				id = id.strip()
				self.ids.append(id)
				self.domains.append('1D')
			else:  # try both
				if 'ID' in f.fields().names() and 'Type' in f.fields().names() and 'Source' in f.fields().names():
					self.ids.append(f['ID'].strip())
					self.sources.append(f['Source'].strip())
					type = f['Type'].strip()
					if 'node' in type.lower() or 'chan' in type.lower():
						self.domains.append('1D')
					else:
						self.domains.append(type)  # 2D or RL
				else:
					id = f.attributes()[0]
					id = id.strip()
					self.ids.append(id)
					self.domains.append('1D')
					
		return True
	
	def getLongPlotConnectivity(self, res):
		"""
		Check and collect the 1D long profile connectivity.

		:param res: TUFLOW_results or TUFLOW_results2013
		:return: bool -> True if error has occured
		"""
		
		# make sure there is between 1 and 2 selections
		if len(self.ids) < 3 and self.ids:
			res.LP.connected = False
			res.LP.static = False
			error = False
			
			# one selection
			if len(self.ids) == 1:
				if res.formatVersion == 1:  # 2013 version only supports 1D
					error, message = res.LP_getConnectivity(self.ids[0], None)
				elif res.formatVersion == 2:
					if self.domains[0] == '1D':
						error, message = res.LP_getConnectivity(self.ids[0], None)
			
			# two selections
			elif len(self.ids) == 2:
				if res.formatVersion == 1:
					error, message = res.LP_getConnectivity(self.ids[0], self.ids[1])
				elif res.formatVersion == 2:
					if self.domains[0] == '1D' and self.domains[1] == '1D':
						error, message = res.LP_getConnectivity(self.ids[0], self.ids[1])
			
			# if error -> break
			if not error:
				error, message = res.LP_getStaticData()
				if not error:
					return False
		
		return True
	
	def removeResults(self, resList):
		"""
		Removes the 1D results from the indexed results and ui.

		:param resList: list -> str result name e.g. M01_5m_001
		:return: bool -> True for successful, False for unsuccessful
		"""

		results = self.tuView.tuResults.results
		
		for res in resList:
			if res in results.keys():
				# remove from indexed results
				for resultType in list(results[res].keys()):
					if '_ts' in resultType or '_lp' in resultType:
						del results[res][resultType]
				
				# check if result type is now empty
				if len(results[res]) == 0:
					del results[res]
							
			if res in self.results1d:
				del self.results1d[res]
			
			for i in range(self.tuView.OpenResults.count()):
				item = self.tuView.OpenResults.item(i)
				if item is not None and item.text() == res:
					if res not in results:
						self.tuView.OpenResults.takeItem(i)
		
		return True