

class TuResultsIndex():
	"""
	Class for helping get indexed results.
	
	"""
	
	def __init__(self, result, resultType, timestep, max, min=False):
		if resultType == 'Bed Elevation' or resultType == 'Time of Peak h' or resultType == 'Time of Peak V':
			self.result = result
			self.resultType = resultType
			self.timestep = '0.000000' if timestep is not None else timestep
		else:
			self.result = result
			if resultType == 'Minimum dt':
				self.resultType = '{0}/Final'.format(resultType) if max else resultType
			else:
				self.resultType = '{0}/Maximums'.format(resultType) if max else resultType
			self.timestep = '-99999' if max else timestep
			self.timestep = '99999' if min else timestep
