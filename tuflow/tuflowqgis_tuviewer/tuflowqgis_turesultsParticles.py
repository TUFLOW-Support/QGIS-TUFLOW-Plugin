import os
import glob
from datetime import timedelta
from qgis.core import *
from PyQt5.QtCore import Qt, QVariant
from qgis.core import QgsVectorLayer, QgsFeature, QgsPointXY, QgsGeometry, QgsField

try:
	from tuflow.TUFLOW_particles_data_provider import TuParticlesDataProvider
	have_netCDF4 = True
except ImportError:
	have_netCDF4 = False

class TuResultsParticles():
	"""
	Class for handling Particles results
	"""
	
	def __init__(self, TuView):
		self.tuView = TuView
		self.iface = TuView.iface
		self.resultsParticles = {} # display name -> [particles data provider, vectorLayer, [relative_times_in_hour]]
	
	def importResults(self, inFileNames):
		"""
		Imports function that opens result particles layer

		:param inFileNames: list -> str - full path to particles result file
		:return: bool -> True for successful, False for unsuccessful
		"""

		if not have_netCDF4:
			return False

		# disconnect incoming signals for load step
		skipConnect = False
		try:
			self.tuView.project.layersAdded.disconnect(self.tuView.layersAdded)
		except:
			skipConnect = True

		for j, f in enumerate(inFileNames):
			# Load Particles
			if type(inFileNames) is dict:
				m = inFileNames[f]['particles']
				mLayer, name = self._load_file(m)
			else:
				mLayer, name = self._load_file(f)

			if mLayer is None or name is None:
				if not skipConnect:
					self.tuView.project.layersAdded.connect(self.tuView.layersAdded)
				return False

			# Open layer in map
			self.tuView.project.addMapLayer(mLayer)
			name = mLayer.name()
			mLayer.nameChanged.connect(lambda: self.layerNameChanged(mLayer, name, mLayer.name()))  # if name is changed can capture this in indexing
			
			# add to result list widget
			names = []
			for i in range(self.tuView.OpenResults.count()):
				if self.tuView.OpenResults.item(i).text() not in names:
					names.append(self.tuView.OpenResults.item(i).text())
			if name not in names:
				self.tuView.OpenResults.addItem(name)  # add to widget
			k = self.tuView.OpenResults.findItems(name, Qt.MatchRecursive)[0]
			k.setSelected(True)
			self.tuView.resultChangeSignalCount = 0  # reset signal count back to 0
		
		# connect load signals
		if not skipConnect:
			self.tuView.project.layersAdded.connect(self.tuView.layersAdded)

		return True

	def _load_file(self, filename):
		if not filename:
			return None, None

		particles_data_provider = TuParticlesDataProvider()
		if particles_data_provider.load_file(filename):
			# create vector layer with correct attributes
			displayname = os.path.basename(filename)
			self.tuView.tuResults.results[displayname] = {}
			vlayer = QgsVectorLayer("PointZ", displayname, "memory")
			vlayer.dataProvider().addAttributes(self._get_attributes_list(particles_data_provider))
			vlayer.updateFields()

			# add styles
			dir_path = os.path.dirname(os.path.realpath(__file__))
			styles_folder = os.path.join(dir_path, os.pardir, "QGIS_Styles", "particles", "*.qml")
			styles = glob.glob(styles_folder)
			style_manager = vlayer.styleManager()
			for style in styles:
				style_name = os.path.basename(style).strip('.qml')
				(_, success) = vlayer.loadNamedStyle(style)
				if not success:
					style_manager.removeStyle(style)

				style_manager.addStyleFromLayer(style_name)
			style_manager.setCurrentStyle("default")

			# populate resdata
			timekey2time = self.tuView.tuResults.timekey2time  # dict
			timekey2date = self.tuView.tuResults.timekey2date  # dict
			time2date = self.tuView.tuResults.time2date  # dict
			date2timekey = self.tuView.tuResults.date2timekey
			date2time = self.tuView.tuResults.date2time
			zeroTime = self.tuView.tuOptions.zeroTime  # datetime
			if not zeroTime:
				zeroTime = particles_data_provider.getReferenceTime()

			timesteps = particles_data_provider.timeSteps(zeroTime)
			for t in timesteps:
				timekey2time['{0:.6f}'.format(t)] = t
				timekey2date['{0:.6f}'.format(t)] = zeroTime + timedelta(hours=t)
				time2date[t] = zeroTime + timedelta(hours=t)
				date2timekey[zeroTime + timedelta(hours=t)] = '{0:.6f}'.format(t)
				date2time[zeroTime + timedelta(hours=t)] = t

			self.tuView.tuResults.results[displayname]["_particles"] = [timesteps]

			# add to internal storage
			self.resultsParticles[displayname] = [particles_data_provider, vlayer, timesteps]

			# load first step
			self.updateActiveTime()

			# Return
			return vlayer, displayname

		# Failure
		return None, None

	def removeResults(self, resList):
		"""
		Removes the Particles results from the indexed results and ui.

		:param resList: list -> str result name e.g. M01_5m_001
		:return: bool -> True for successful, False for unsuccessful
		"""

		results = self.tuView.tuResults.results

		for res in resList:
			if res in results:
				del results[res]

			if res in self.resultsParticles:
				del self.resultsParticles[res]

			for i in range(self.tuView.OpenResults.count()):
				item = self.tuView.OpenResults.item(i)
				if item is not None and item.text() == res:
					if res not in results:
						self.tuView.OpenResults.takeItem(i)

		return True

	def updateActiveTime(self):
		"""
		Loads a new set of particles for next timestep
		"""

		active_time = self.tuView.tuResults.activeTime
		if active_time is None:
			global_relative_time = 0
		else:
			global_relative_time = self.tuView.tuResults.timekey2time[active_time]

		for _, data in self.resultsParticles.items():
			particles_data_provider = data[0]
			vlayer = data[1]
			timesteps = data[2]

			# find nearest lower time
			time_index = 0
			for i, relative_time in enumerate(timesteps):
				time_index = i
				relative_time = timesteps[i]
				if relative_time > global_relative_time:
					break

			# re-populate particles
			if vlayer is not None:
				points = self._get_features(particles_data_provider, vlayer, time_index)
				vlayer.dataProvider().truncate()
				vlayer.dataProvider().addFeatures(points)
				vlayer.updateExtents()
				vlayer.triggerRepaint()


	def _get_attributes_list(self, particles_data_provider):
		attrs = []

		# add mandatory attributes
		attrs.extend([
			QgsField("id", QVariant.Int),
			QgsField("stat", QVariant.Int),
			QgsField("groupID", QVariant.Int)
		])

		# add optional attributes (variables) that are in file
		dataset_vars = particles_data_provider.get_all_variable_names()
		for var in dataset_vars:
			attrs.append(QgsField(var, QVariant.Double))

		return attrs


	def _get_features(self, particles_data_provider, vlayer, time_index):
		points = []

		data = particles_data_provider.read_data_at_time(time_index)
		if data is None:
			return points

		x = data.pop('x')
		y = data.pop('y')
		z = data.pop('z')
		stats = data.get('stat')

		for i, stat in enumerate(stats):
			# ignore inactive particles
			if int(stat) > 0:
				feat = QgsFeature()
				point = QgsPoint(x[i], y[i], z[i])
				feat.setGeometry(QgsGeometry(point))
				feat.setFields(vlayer.fields())
				for attr in data.keys():
					feat['id'] = i
					feat[attr] = float(
						data.get(attr)[i])  # must be converted to primitive type, otherwise feature data wont be stored
				points.append(feat)

		return points