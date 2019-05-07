# coding=utf-8

def interpolate(a, b, c, d, e):
	"""
	Linear interpolation

	:param a: known mid point
	:param b: known lower value
	:param c: known upper value
	:param d: unknown lower value
	:param e: unknown upper value
	:return: float
	"""
	
	a = float(a)
	b = float(b)
	c = float(c)
	d = float(d)
	e = float(e)
	
	return (e - d) / (c - b) * (a - b) + d


def lookupPierLoss(pierConfig, blockage):
	"""
	Vertical lookup of pier loss. Will interpolate or extrapolate as necessary.
	
	:param pierConfig: int - pier configuration enumerator
	:param blockage: float - waterway blockage due to piers
	:return: float - FLC value
	"""
	
	# j (waterway blockage) for pier configurations
	j1 = [0, 0.01, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12]
	j2 = j1[:]
	j3 = j1[:]
	j4 = j1[:]
	j5 = j1[:-2]
	j6 = j1[:-2]
	j7 = j1[:-3]
	j8 = j1[:-4]
	
	# delta K values for pier configurations
	k1 = [0, 0.01, 0.018, 0.04, 0.07, 0.102, 0.135, 0.17]
	k2 = [0, 0.012, 0.025, 0.062, 0.105, 0.15, 0.2, 0.245]
	k3 = [0, 0.015, 0.03, 0.075, 0.125, 0.175, 0.225, 0.275]
	k4 = [0, 0.018, 0.04, 0.095, 0.155, 0.215, 0.28, 0.34]
	k5 = [0, 0.02, 0.046, 0.115, 0.185, 0.26]
	k6 = [0, 0.024, 0.056, 0.135, 0.225, 0.315]
	k7 = [0, 0.034, 0.08, 0.205, 0.34]
	k8 = [0, 0.048, 0.1, 0.26]
	
	# select pier configuration j and k values
	pierDict = {1: [j1, k1], 2: [j2, k2], 3: [j3, k3], 4: [j4, k4], 5: [j5, k5], 6: [j6, k6], 7: [j7, k7], 8: [j8, k8]}
	j = pierDict[pierConfig][0]
	k = pierDict[pierConfig][1]
	
	# Get k value through interpolation or extrapolation
	if blockage <= max(j):  # interpolate delta k value
		for i, b in enumerate(j):
			loss = k[i]
			if i == 0:
				if b == blockage:
					return loss
				bPrev = b
				lossPrev = loss
			else:
				if b == blockage:
					return loss
				if b > blockage and bPrev < blockage:
					return interpolate(blockage, bPrev, b, lossPrev, loss)
				bPrev = b
				lossPrev = loss
	else:  # extrapolate delta k value
		return interpolate(blockage, j[-2], j[-1], k[-2], k[-1])