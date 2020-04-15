

class TuResultsIndex():
	"""
	Class for helping get indexed results.
	
	"""
	
	def __init__(self, result, resultType, timestep=None, ismax=False, ismin=False):
		if resultType == 'Bed Elevation' or resultType == 'Time of Peak h' or resultType == 'Time of Peak V':
			self.result = result
			self.resultType = resultType
			self.timestep = '0.000000' if timestep is not None else timestep
		else:
			self.result = result
			if resultType == 'Minimum dt':
				self.resultType = '{0}/Final'.format(resultType) if ismax else resultType
			else:
				if ismax:
					self.resultType = '{0}/Maximums'.format(resultType)
					self.timestep = '99999'
				elif ismin:
					self.resultType = '{0}/Minimums'.format(resultType)
					self.timestep = '-99999'
				else:
					self.resultType = resultType
					self.timestep = timestep

