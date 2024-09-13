from qgis.core import Qgis
from datetime import timedelta
from tuflow.tuflowqgis_library import roundSeconds


class TuResultsIndex():
	"""
	Class for helping get indexed results.
	
	"""
	
	def __init__(self, result, resultType, timestep=None, ismax=False, ismin=False, tuResults=None, units='h'):
		qv = qv = Qgis.QGIS_VERSION_INT
		if qv < 31600:
			self.initialise_old(result, resultType, timestep, ismax, ismin)
		else:
			self.initialise_31600(result, resultType, timestep, ismax, ismin, tuResults, units)

	def initialise_old(self, result, resultType, timestep, ismax, ismin):

		if resultType == 'Bed Elevation' or resultType == 'Time of Peak h' or resultType == 'Time of Peak V':
			self.result = result
			self.resultType = resultType
			self.timestep = '0.000000' if timestep is not None else timestep
		else:
			self.result = result
			# if resultType == 'Minimum dt':
			# 	self.resultType = '{0}/Final'.format(resultType) if ismax else resultType
			#else:
			if ismax:
				self.resultType = '{0}/Maximums'.format(resultType)
				self.timestep = '99999'
			elif ismin:
				self.resultType = '{0}/Minimums'.format(resultType)
				self.timestep = '-99999'
			else:
				self.resultType = resultType
				self.timestep = timestep

	def initialise_31600(self, result, resultType, timestep, ismax, ismin, tuResults, units):
		if resultType == 'Bed Elevation' or resultType == 'Time of Peak h' or resultType == 'Time of Peak V':
			self.result = result
			self.resultType = resultType
			self.timestep = '0.000000' if timestep is not None else timestep
		else:
			self.result = result
			if ismax:
				self.resultType = '{0}/Maximums'.format(resultType)
				self.timestep = '99999'
			elif ismin:
				self.resultType = '{0}/Minimums'.format(resultType)
				self.timestep = '-99999'
			else:
				self.resultType = resultType
				if result in tuResults.results and '_nc_grid' in tuResults.results[result] and result == resultType:
					self.resultType = '_nc_grid'
				self.timestep = self.findTimeClosest_31600(tuResults, result, self.resultType, timestep, units=units)

	@staticmethod
	def findTimeClosest_31600(tuResults, key1, key2, key3, times=(), method='lower', units='h'):
		"""
        Finds the next available time after specified time
        """

		# for 1d results change key2 so it can be found in results dict
		if key1 is not None and key2 is not None:
			if key1 in tuResults.results:
				if '_1d' in key2:
					for type_1d in ['point_ts', 'line_ts', 'region_ts', 'line_lp']:
						if type_1d in tuResults.results[key1]:
							if 'times' in tuResults.results[key1][type_1d]:
								key2 = type_1d
								break

		if not times:
			if key1 not in tuResults.results:
				return
			if key2 not in tuResults.results[key1]:
				return
		if key3 is None:
			return

		if not times:
			if 'times' not in tuResults.results[key1][key2]:
				return
			times = sorted(y[0] for x, y in tuResults.results[key1][key2]['times'].items())

		if 'referenceTime' not in tuResults.results[key1][key2]:
			return
		rt = tuResults.results[key1][key2]['referenceTime']
		for i, time in enumerate(times):
			if units == 's':
				date = rt + timedelta(seconds=float(time))
			else:
				try:
					date = rt + timedelta(hours=float(time))
				except OverflowError:
					date = rt + timedelta(seconds=float(time))
			date = roundSeconds(date, 2)
			if method == 'higher':
				if date >= key3:
					return time
			elif method == 'lower':
				if date == key3:
					return time
				elif date > key3:
					return times[max(0, i - 1)]
			else:  # closest
				if date == key3:
					return time
				if i == 0:
					diff = abs((date - key3).total_seconds())
				if time > key3:
					diff2 = abs((date - key3).total_seconds())
					if diff <= diff2:
						return times[max(0, i - 1)]
					else:
						return time
				else:
					diff = abs((date - key3).total_seconds())
		if not times:
			return None
		else:
			return time
