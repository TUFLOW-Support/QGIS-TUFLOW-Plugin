from qgis.core import Qgis
from .tuflowqgis_turesults import TuResults


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
				self.timestep = TuResults.findTimeClosest_31600(tuResults, result, resultType, timestep, units=units)

