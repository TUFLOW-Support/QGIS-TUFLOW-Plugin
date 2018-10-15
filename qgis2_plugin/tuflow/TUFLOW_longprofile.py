# coding=utf-8
import sys
import numpy as np
from qgis.core import NULL
from tuflowqgis_library import *
sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2018.1\debug-eggs')
sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2018.1\helpers\pydev')
sys.path.append(r'C:\Users\Ellis\.p2\pool\plugins\org.python.pydev.core_6.3.2.201803171248\pysrc')



class DownstreamConnectivity():
	"""
	Class for storing downstream connectivity information
	"""
	
	def __init__(self, dsLines, startLines, inLyrs, angleLimit, lineDrape, coverLimit, lineDict, units):
		self.bug = False
		self.dsLines = dsLines  # dictionary {name: [[dns network channels], [us invert, ds invert], [angle], [dns-dns connected channels], [upsnetworks}, [ups-ups channels]]
		self.startLines = startLines  # list of initial starting lines for plotting
		self.inLyrs = inLyrs  # list of nwk line layers
		self.angleLimit = angleLimit  # angle limit to for integrity checks
		self.lineDrape = lineDrape  # dict {name: [[QgsPoint - line vertices], [vertex chainage], [elevations]]}
		self.coverLimit = coverLimit  # pipe obvert to ground depth limit for integrity checks
		self.lineDict = lineDict
		self.units = units
		self.processed_nwks = []  # list of processed networks so there is no repetition
		self.log = ''  # string for output log
		self.warningType = []  # list for storing the continuity warning type
		self.warningInformation = []  # pipe name, other information
		self.warningLocation = []  # list for storing the continuity warning location
		self.warningChainage = []  # list for stroing the continuity warning chainage for plotting
		self.bWarningChainage = []  # list for stroing the continuity warning chainage for plotting locally for branch
		self.pathsWarningChainage = []
		self.type = []  # list of network types e.g. C R S
		self.name = []  # list of network IDs
		self.branchName = []  # list of branch names
		self.usInvert = []  # list of network upstream inverts
		self.dsInvert = []  # list of network downstream inverts
		self.angle = []  # list of downstream network connection angle
		self.length = []  # list of network lengths
		self.no = []  # list of number of networks e.g. 2 pipes
		self.width = []  # list of network width
		self.height = []  # list of network heights
		self.area = []  # list of calculated area
		self.groundCh = []  # list of chainages where ground elevations are in relation to
		self.ground = []  # list of ground elevations along pipe
		self.obvert = []  # list of pipe obverts along pipe at same locations as ground
		self.coverDepth = []  # list of cover depths along pipe
		self.adverseGradient = []  # list of flags for adverse gradients
		self.adverseInvert = []  # list of flags for adverse inverts at pipe junctions
		self.decreaseFlowArea = []  # list of flags for decreased flow area
		self.sharpAngle = []  # list of flags for sharp angles
		self.insffCover = []  # list of flags for insufficient cover
		self.branchCounter = 1  # int used for generating branch names e.g. branch 1 branch2
		self.branchExists = False  # bool to determine if branch has been considered already
		self.branchDnsConnectionPipe = []  # list of a branch's downstream connection pipe name
		self.joiningOutlet = []  # list of other networks joining at an outlet
		self.upsBranches = []  # list of upstream branches (index from branch name)
		self.dnsBranches = []  # list of downstream branches (index from branch name)
		self.pathsName = []  # list of path names e.g. path 1 path 2
		self.paths = []  # list of connecting branches from upstream to downstream by branch name
		self.pathsNwks = []  # list of connecting networks from upstream to downstream by network name
		self.pathsLen = []  # list of total path lengths (index by path names)
		self.pathsNwksLen = []  # list of individual network lengths in the paths
		self.pathsX = []  # list of X coordinates used for plotting the paths
		self.pathsArea = []  # list of areas used for plotting the paths
		self.pathsUsInvert = []  # list of upstream inverts for plotting the paths
		self.pathsDsInvert = []  # list of downstream inverts for plotting the paths
		self.pathsInvert = []  # list of Y coordinates for network inverts for plotting the paths
		self.pathsPipe = []  # list of pipe data for plotting (matplotlib patch format)
		self.pathsGroundCh = []  # list of X coordinates for ground levels for the paths
		self.pathsGround = []  # list of Y coordinates for ground levels for the paths
		self.pathsObvert = []  # list of Y coordinates for pipe obverts for the paths
		self.pathsCover = []  # list of cover depths for plotting
		self.pathsGroundX = []  # list of X coordinates for plotting relative to other paths (final plotting)
		self.pathsGroundY = []  # list of Y coordinates for plotting relative to other paths (final plotting)
		self.pathsAdverseInvert = []  # list of flags for adverse inverts at junctions relative to the paths
		self.pathsAdverseGradient = []  # list of flags for adverse gradients relative to the paths
		self.pathsDecreaseFlowArea = []  # list of flags for decreased flow area relative to the paths
		self.pathsSharpAngle = []  # list of flags for sharp angles relative to the paths
		self.pathsInsffCover = []  # list of flags for insufficient cover depth relative to the paths
		self.pathsPlotAdvI = []  # list of adverse Inverts X, Y coords for plotting
		self.pathsPlotAdvG = []  # list of adverse gradient X, Y coords for plotting
		self.pathsPlotDecA = []  # list of decreased area X, Y coords for plotting
		self.pathsPlotSharpA = []  # list of sharp angle X, Y coords for plotting
		self.pathsPlotInCover = []  # list of insufficient cover X, Y coords for plotting
		self.network = []  # list of branched networks used for creating branches
		self.bType = []  # list of network types used locally per branch within branch routine
		self.bName = []  # list of network IDs used locally per branch within branch routine
		self.bUsInvert = []  # list of network upstream inverts used locally per branch within branch routine
		self.bDsInvert = []  # list of network downstream inverts used locally per branch within branch routine
		self.bAngle = []  # list of downstream network connection angle used locally per branch within branch routine
		self.bLength = []  # list of network lengths used locally per branch within branch routine
		self.bNo = []  # list of number of networks used locally per branch within branch routine
		self.bWidth = []  # list of network width used locally per branch within branch routine
		self.bHeight = []  # list of network heights used locally per branch within branch routine
		self.bArea = []  # list of calculated area used locally per branch within branch routine
		self.bGroundCh = []  # list of chainages where ground elevations are in relation to used locally per branch within branch routine
		self.bGround = []  # list of ground elevations along pipe used locally per branch within branch routine
		self.bObvert = []  # list of pipe obverts along pipe at same locations as ground used locally per branch within branch routine
		self.bCoverDepth = []  # list of cover depths along pipe used locally per branch within branch routine
		self.bDnsConnectionPipe = []  # list of a branch's downstream connection pipe name used locally per branch within branch routine
		self.bAdverseGradient = []  # list of flags for adverse gradients used locally per branch within branch routine
		self.bAdverseInvert = []  # list of flags for adverse inverts at pipe junctions used locally per branch within branch routine
		self.bDecreaseFlowArea = []  # list of flags for decreased flow area used locally per branch within branch routine
		self.bSharpAngle = []  # list of flags for sharp angles used locally per branch within branch routine
		self.bInsffCover = []  # list of flags for insufficient cover used locally per branch within branch routine
		
	def getDownstreamConnectivity(self, network):
		"""
		Determines the 1D network branch and gets the pipe data for it.
		
		:return: void
		"""

		# Clear branch variables
		self.bType = []
		self.bName = []
		self.bUsInvert = []
		self.bDsInvert = []
		self.bAngle = []
		self.bLength = []
		self.bNo = []
		self.bWidth = []
		self.bHeight = []
		self.bArea = []
		self.bGroundCh = []
		self.bGround = []
		self.bObvert = []
		self.bCoverDepth = []
		self.bDnsConnectionPipe = []
		self.bAdverseGradient = []
		self.bAdverseInvert = []
		self.bDecreaseFlowArea = []
		self.bSharpAngle = []
		self.bInsffCover = []
		self.bWarningChainage = []
		self.first_sel = True
		name_prev = None
		area_prev = 0
		dsInv_prev = 99999
		bn = []
		# Determine if there are pipes downstream of starting locations
		dns = True
		if type(network) != list:
			network = [network]
		while dns:
			# Get QgsFeature layers for start lines
			adverseGradient = False
			adverseInvert = False
			decreaseFlowArea = False
			sharpAngle = False
			insffCover = False
			features = []
			ground = []
			groundCh = []
			obvert = []
			coverDepth = []
			warningChainage = None
			for lyr in self.inLyrs:
				fld = lyr.fields()[0]
				typFld = lyr.fields()[1]
				for nwk in network:
					if '__connector' in nwk:
						filter = '"{0}" = \'{1}\' OR "{0}" = \'{2}\''.format(typFld.name(), 'X', 'x')
					else:
						filter = '"{0}" = \'{1}\''.format(fld.name(), nwk)
					request = QgsFeatureRequest().setFilterExpression(filter)
					for f in lyr.getFeatures(request):
						if '__connector' in nwk:
							if nwk in self.lineDict.keys():
								if lyr == self.lineDict[nwk][2]:
									if f.id()== self.lineDict[nwk][1]:
										features.append(f)
						else:
							features.append(f)
			# Get data for starting lines
			if len(network) == 1:  # dealing with one channel
				self.first_sel = False
				self.branchExists = True
				if network[0] in self.processed_nwks:
					if len(self.bName) == 0:
						self.branchExists = False
						dns = False
						break
					self.branchDnsConnectionPipe.append([network[0]])
					self.joiningOutlet.append('JOINING EXISTING BRANCH')
					dns = False
					break
				typ = features[0].attributes()[1]
				length = features[0].attributes()[4]
				if length <= 0:
					length = getLength(features[0])
				name = network[0]
				no = features[0].attributes()[15]
				width = features[0].attributes()[13]
				height = features[0].attributes()[14]
				usInv = self.dsLines[network[0]][1][0]
				dsInv = self.dsLines[network[0]][1][1]
				if network[0] in self.dsLines.keys():
					if len(self.dsLines[network[0]][2]) > 0:
						angle = min(self.dsLines[network[0]][2])
					else:
						angle = 0
				else:
					angle = 0
				if typ.lower() == 'r':
					if width != NULL:
						if height != NULL:
							if no != NULL:
								area = float(no) * width * height
							else:
								area = width * height
						else:
							area = 0
					else:
						area = 0
					if self.coverLimit is not None:
						groundCh = self.lineDrape[name][1]
						ground = self.lineDrape[name][2]
						obvert = interpolateObvert(usInv, dsInv, height, groundCh)
						coverDepth = []
						for i, g in enumerate(ground):
							cover = g - obvert[i]
							coverDepth.append(cover)
							if cover < self.coverLimit:
								insffCover = True
								self.warningLocation.append(self.lineDrape[name][0][i])
								warningChainage = groundCh[i]
								self.warningType.append('Cover Warning')
								self.warningInformation.append([network[0], warningChainage])
								break
				elif typ.lower() == 'c':
					if width != NULL:
						if no != NULL:
							area = float(no) * (width / 2) ** 2 * 3.14
						else:
							area = (width / 2) ** 2 * 3.14
					else:
						area = 0
					if self.coverLimit is not None:
						groundCh = self.lineDrape[name][1]
						ground = self.lineDrape[name][2]
						obvert = interpolateObvert(usInv, dsInv, width, groundCh)
						coverDepth = []
						for i, g in enumerate(ground):
							cover = g - obvert[i]
							coverDepth.append(cover)
							if cover < self.coverLimit:
								insffCover = True
								self.warningLocation.append(self.lineDrape[name][0][i])
								warningChainage = groundCh[i]
								self.warningType.append('Cover Warning')
								self.warningInformation.append([network[0], warningChainage])
								break
				else:
					area = 0
					if self.coverLimit is not None:
						groundCh = self.lineDrape[name][1]
						ground = self.lineDrape[name][2]
						obvert = []
						coverDepth = []
				if (dsInv > usInv and usInv != -99999.00):
					adverseGradient = True
					point = getNetworkMidLocation(features[0])
					self.warningLocation.append(point)
					self.warningType.append('Gradient Warning')
					self.warningInformation.append([network[0], usInv, dsInv])
				if usInv > dsInv_prev and dsInv_prev != -99999.00:
					adverseInvert = True
					point = self.lineDict[network[0]][0][0]
					self.warningLocation.append(point)
					self.warningType.append('Invert Warning')
					self.warningInformation.append([name_prev, dsInv_prev, network[0], usInv])
				if area < area_prev and area != 0:
					decreaseFlowArea = True
					point = self.lineDict[network[0]][0][0]
					self.warningLocation.append(point)
					self.warningType.append('Area Warning')
					self.warningInformation.append([name_prev, area_prev, network[0], area])
				if angle < self.angleLimit and angle != 0:
					sharpAngle = True
					point = self.lineDict[network[0]][0][1]
					self.warningLocation.append(point)
					self.warningType.append('Angle Warning')
					self.warningInformation.append([network[0], angle])
				self.bType.append(typ)
				self.bLength.append(length)
				self.bName.append(name)
				self.bNo.append(no)
				self.bWidth.append(width)
				self.bHeight.append(height)
				self.bUsInvert.append(usInv)
				self.bDsInvert.append(dsInv)
				self.bAngle.append(angle)
				self.bArea.append(area)
				self.bGroundCh.append(groundCh)
				self.bGround.append(ground)
				self.bObvert.append(obvert)
				self.bCoverDepth.append(coverDepth)
				self.bAdverseGradient.append(adverseGradient)
				self.bAdverseInvert.append(adverseInvert)
				self.bDecreaseFlowArea.append(decreaseFlowArea)
				self.bSharpAngle.append(sharpAngle)
				self.bInsffCover.append(insffCover)
				self.bWarningChainage.append(warningChainage)
				if network[0] in self.dsLines.keys():
					if len(self.dsLines[network[0]][0]) == 0:
						self.joiningOutlet.append(self.dsLines[network[0]][3])
						self.branchDnsConnectionPipe.append('OUTLET')
						self.processed_nwks.append(network[0])
						dns = False
					else:
						self.processed_nwks.append(network[0])
						name_prev = network[0]
						area_prev = area
						dsInv_prev = dsInv
						network = self.dsLines[network[0]][0]
				else:
					self.joiningOutlet.append(self.dsLines[network[0]][3])
					self.branchDnsConnectionPipe.append('OUTLET')
					self.processed_nwks.append(network[0])
					dns = False
			elif len(network) > 1:  # consider what happens if there are 2 downstream channels
				# get channels accounting for X connectors
				nwks = []
				for nwk in network:
					if 'connector' in nwk:
						nwk = self.dsLines[nwk][0][0]
					nwks.append(nwk)
				# get next downstream channels accounting for X connectors
				dns_nwks = []
				for nwk in nwks:
					if nwk in self.dsLines.keys():
						if len(self.dsLines[nwk][0]) == 0:
							dns_nwks.append('DOWNSTREAM NODE')
						else:
							dns_nwk = self.dsLines[nwk][0][0]
							if 'connector' in dns_nwk:
								dns_nwk = self.dsLines[dns_nwk][0][0]
							dns_nwks.append(dns_nwk)
					else:
						dns_nwks.append('DOWNSTREAM NODE')
				# check if dns nwk is the same
				# if it is the same dns nwk, then it is probably part of the same network branch
				# if it is different, then the network has probably split into a second branch
				branches = []  # split downstream channels into branches
				for i, dns_nwk in enumerate(dns_nwks):
					for i2, dns_nwk2 in enumerate(dns_nwks):
						already = False
						if i != i2:
							for j, b in enumerate(branches):
								if i in b:
									already = True
								elif i2 in b:
									if dns_nwk != 'DOWNSTREAM NODE':
										if dns_nwk == dns_nwk2:
											branches[j].append(i)
											already = True
							if not already:
								if dns_nwk == dns_nwk2 and dns_nwk != 'DOWNSTREAM NODE':
									branches.append([i, i2])
								else:
									branches.append([i])
				for branch in branches:
					a = []
					for bi in branch:
						a.append(nwks[bi])
					bn.append(a)
				if len(branches) == 1:
					bn.pop()
					features = []
					for lyr in self.inLyrs:
						for nwk in nwks:
							fld = lyr.fields()[0]
							filter = '"{0}" = \'{1}\''.format(fld.name(), nwk)
							request = QgsFeatureRequest().setFilterExpression(filter)
							for f in lyr.getFeatures(request):
								features.append(f)
					name = []
					typ = []
					no = []
					width = []
					height = []
					usInv = []
					dsInv = []
					area = []
					groundCh = []
					ground = []
					obvert = []
					coverDepth = []
					angle = []
					length = []
					inProcessedNwks = False
					skip_advG = False
					skip_advI = False
					skip_decA = False
					skip_sharpA = False
					skip_insffC = False
					for nwk in nwks:
						for f in features:
							id = f.attributes()[0]
							if nwk == id:
								self.first_sel = False
								self.branchExists = True
								if nwk in self.processed_nwks:	
									self.branchDnsConnectionPipe.append([nwk])
									self.joiningOutlet.append('JOINING EXISTING BRANCH')
									dns = False
									inProcessedNwks = True
									break
								t = f.attributes()[1]
								l = f.attributes()[4]
								if l <= 0:
									l = getLength(f)
								na = id
								n = f.attributes()[15]
								w = f.attributes()[13]
								h = f.attributes()[14]
								uI = self.dsLines[nwk][1][0]
								dI = self.dsLines[nwk][1][1]
								if nwk in self.dsLines.keys():
									if len(self.dsLines[nwk][2]) > 0:
										ang = min(self.dsLines[nwk][2])
								else:
									ang = 0
								gc = []
								gr = []
								o = []
								cd = []
								if t.lower() == 'r':
									if w != NULL and h != NULL:
										if n != NULL:
											a = float(n) * w * h
										else:
											a = w * h
									else:
										a = 0
									if self.coverLimit is not None:
										gc = self.lineDrape[na][1]
										gr = self.lineDrape[na][2]
										o = interpolateObvert(uI, dI, h, gc)
										cd = []
										for i, g in enumerate(gr):
											c = g - o[i]
											cd.append(c)
											if c < self.coverLimit:
												insffCover = True
												if not skip_insffC:
													point = self.lineDrape[na][0][i]
													self.warningLocation.append(point)
													warningChainage = gc[i]
													self.warningType.append('Cover Warning')
													self.warningInformation.append([nwk, warningChainage])
													skip_insffC = True
												break
								elif t.lower() == 'c':
									if w != NULL:
										if n != NULL:
											a = float(n) * (w / 2) ** 2 * 3.14
										else:
											a = (w / 2) ** 2 * 3.14
									else:
										a = 0
									if self.coverLimit is not None:
										gc = self.lineDrape[na][1]
										gr = self.lineDrape[na][2]
										o = interpolateObvert(uI, dI, h, gc)
										cd = []
										for i, g in enumerate(gr):
											c = g - o[i]
											cd.append(c)
											if c < self.coverLimit:
												insffCover = True
												if not skip_insffC:
													point = self.lineDrape[na][0][i]
													self.warningLocation.append(point)
													warningChainage = gc[i]
													self.warningType.append('Cover Warning')
													self.warningInformation.append([nwk, warningChainage])
													skip_insffC = True
												break
								else:
									a = 0
									if self.coverLimit is not None:
										gc = self.lineDrape[na][1]
										gr = self.lineDrape[na][2]
										o = []
										cd = []
								if dI > uI and uI != -99999.00:
									if not skip_advG:
										adverseGradient = True
										point = getNetworkMidLocation(f)
										self.warningLocation.append(point)
										self.warningType.append('Gradient Warning')
										self.warningInformation.append([nwk, uI, dI])
										skip_advG = True
								elif dI <= uI and uI != -99999.00:
									skip_advG = True
								if uI > dsInv_prev and dsInv_prev != -99999.00:
									if not skip_advI:
										adverseInvert = True
										point = self.lineDict[nwk][0][0]
										self.warningLocation.append(point)
										self.warningType.append('Invert Warning')
										self.warningInformation.append([name_prev, dsInv_prev, nwk, uI])
										skip_advI = True
								elif uI <= dsInv_prev and dsInv_prev != -99999:
									skip_advI = True
								if a < area_prev and a != 0:
									decFlowArea = True
									if not skip_decA:
										point = self.lineDict[nwk][0][0]
										self.warningLocation.append(point)
										self.warningType.append('Area Warning')
										self.warningInformation.append([name_prev, area_prev, nwk, a])
										skip_decA = True
								if ang < self.angleLimit and ang != 0:
									if not skip_sharpA:
										sharpAngle = True
										point = self.lineDict[nwk][0][1]
										self.warningLocation.append(point)
										self.warningType.append('Angle Warning')
										self.warningInformation.append([nwk, ang])
										skip_sharpA = True
								elif ang >= self.angleLimit and ang != 0:
									skip_sharpA = True
								name.append(na)
								typ.append(t)
								no.append(n)
								width.append(w)
								height.append(h)
								usInv.append(uI)
								dsInv.append(dI)
								area.append(a)
								groundCh.append(gc)
								ground.append(gr)
								obvert.append(o)
								coverDepth.append(cd)
								angle.append(ang)
								length.append(l)
						if inProcessedNwks:
							break
					if inProcessedNwks:
							break
					self.bType.append(typ)
					self.bLength.append(max(length))
					self.bName.append(name)
					self.bNo.append(no)
					self.bWidth.append(max(width))
					self.bHeight.append(max(height))
					self.bUsInvert.append(min(usInv))
					self.bDsInvert.append(min(dsInv))
					self.bAngle.append(max(angle))
					self.bArea.append(sum(area))
					self.bGroundCh.append(groundCh[0])
					self.bGround.append(ground[0])
					self.bObvert.append(obvert[0])
					self.bCoverDepth.append(coverDepth[0])
					self.bAdverseGradient.append(adverseGradient)
					self.bAdverseInvert.append(adverseInvert)
					self.bDecreaseFlowArea.append(decreaseFlowArea)
					self.bSharpAngle.append(sharpAngle)
					self.bInsffCover.append(insffCover)
					self.bWarningChainage.append(warningChainage)
					if nwks[0] in self.dsLines.keys():
						if len(self.dsLines[nwks[0]][0]) == 0:
							self.joiningOutlet.append(self.dsLines[nwks[0]][3])
							self.branchDnsConnectionPipe.append('OUTLET')
							for nwk in nwks:
								self.processed_nwks.append(nwk)
							dns = False
						else:
							for nwk in nwks:
								self.processed_nwks.append(nwk)
							name_prev = nwks
							area_prev = sum(area)
							dsInv_prev = min(dsInv)
							network = self.dsLines[nwks[0]][0]
					else:
						self.joiningOutlet.append(self.dsLines[nwks[0]][3])
						self.branchDnsConnectionPipe.append('OUTLET')
						for nwk in nwks:
							self.processed_nwks.append(nwk)
						dns = False
				elif len(branches) > 1:
					if not self.first_sel:
						self.joiningOutlet.append('BRANCHED')
						self.branchDnsConnectionPipe.append(nwks)
					for nwk in nwks:
						if nwk in self.processed_nwks:
							nwks.remove(nwk)
					for nwk in nwks:
						self.network.append(nwk)
					dns = False
	
	def getBranches(self):
		"""
		Gets the downstream connectivity using a list of starting line names
		
		:return: void
		"""

		self.getDownstreamConnectivity(self.startLines)
		if self.branchExists:
			self.branchName.append('Branch {0}'.format(self.branchCounter))
			self.branchCounter += 1
			self.type.append(self.bType)
			self.length.append(self.bLength)
			self.name.append(self.bName)
			self.no.append(self.bNo)
			self.width.append(self.bWidth)
			self.height.append(self.bHeight)
			self.usInvert.append(self.bUsInvert)
			self.dsInvert.append(self.bDsInvert)
			self.angle.append(self.bAngle)
			self.area.append(self.bArea)
			self.groundCh.append(self.bGroundCh)
			self.ground.append(self.bGround)
			self.obvert.append(self.bObvert)
			self.coverDepth.append(self.bCoverDepth)
			self.adverseGradient.append(self.bAdverseGradient)
			self.adverseInvert.append(self.bAdverseInvert)
			self.decreaseFlowArea.append(self.bDecreaseFlowArea)
			self.sharpAngle.append(self.bSharpAngle)
			self.insffCover.append(self.bInsffCover)
			self.warningChainage.append(self.bWarningChainage)
		while len(self.network) > 0:
			nwk = self.network[0]
			self.branchExists = False
			self.getDownstreamConnectivity(nwk)
			if self.branchExists:
				self.branchName.append('Branch {0}'.format(self.branchCounter))
				self.branchCounter += 1
				self.type.append(self.bType)
				self.length.append(self.bLength)
				self.name.append(self.bName)
				self.no.append(self.bNo)
				self.width.append(self.bWidth)
				self.height.append(self.bHeight)
				self.usInvert.append(self.bUsInvert)
				self.dsInvert.append(self.bDsInvert)
				self.angle.append(self.bAngle)
				self.area.append(self.bArea)
				self.groundCh.append(self.bGroundCh)
				self.ground.append(self.bGround)
				self.obvert.append(self.bObvert)
				self.coverDepth.append(self.bCoverDepth)
				self.adverseGradient.append(self.bAdverseGradient)
				self.adverseInvert.append(self.bAdverseInvert)
				self.decreaseFlowArea.append(self.bDecreaseFlowArea)
				self.sharpAngle.append(self.bSharpAngle)
				self.insffCover.append(self.bInsffCover)
				self.warningChainage.append(self.bWarningChainage)
			self.network.remove(nwk)
			
			
	def reportLog(self):
		"""
		log branch results
		
		:return:
		"""

		for i, msg in enumerate(self.warningInformation):
			if self.warningType[i] == 'Cover Warning':
				self.log += '{0} cover depth is below input limit {1} at {2:.1f}{3} along network\n' \
					        .format(msg[0], self.coverLimit, msg[1], self.units)
			elif self.warningType[i] == 'Gradient Warning':
				self.log += '{0} has an adverse gradient (upstream {1:.3f}{2}RL, downstream {3:.3f}{2}RL)\n' \
						    .format(msg[0], msg[1], self.units, msg[2])
			elif self.warningType[i] == 'Invert Warning':
				self.log += '{0} outlet ({1:.3f}{2}RL) is lower than downstream {3} inlet ({4:.3f}{2}RL)\n' \
						    .format(msg[0], msg[1], self.units, msg[2], msg[3])
			elif self.warningType[i] == 'Area Warning':
				self.log += '{0} decreases in area downstream ({0} {1:.1f}{2}2, {3} {4:.1f}{2}2)\n' \
						    .format(msg[0], msg[1], self.units, msg[2], msg[3])
			elif self.warningType[i] == 'Angle Warning':
				self.log += '{0} outlet angle ({1:.1f} deg) is less than input angle limit ({2:.1f} deg)\n' \
						    .format(msg[0], msg[1], self.angleLimit)

				
	def checkDnsNwks(self):
		"""
		Check that all downstream network have been accounted for in branchDnsConnectionPipe
		
		:return: a completed branchDnsConnectionPipe
		"""
	
		for i, branch in enumerate(self.name):
			lastNwk = branch[-1]
			dnsConns = self.dsLines[lastNwk][0]
			for dnsNwk in dnsConns:
				if dnsNwk not in self.branchDnsConnectionPipe[i]:
					self.branchDnsConnectionPipe[i].append(dnsNwk)
				
	
	def getBranchConnectivity(self):
		"""
		Populates the upstream and downstream branch attribute type for each branch
		
		:return:
		"""

		for i, branch in enumerate(self.branchName):
			if self.branchDnsConnectionPipe[i] == 'OUTLET':
				self.dnsBranches.append([None])
			else:
				branches = []
				for j, name in enumerate(self.name):
					if type(name) == list:
						for n in name:
							if type(n) == list:
								for na in n:
									if na in self.branchDnsConnectionPipe[i]:
										branches.append(self.branchName[j])
										break
							if n in self.branchDnsConnectionPipe[i]:
								branches.append(self.branchName[j])
					elif name in self.branchDnsConnectionPipe[i]:
						branches.append(self.branchName[j])
				self.dnsBranches.append(branches)
			ups = True
			branches = []
			for j, branchDnsConnection in enumerate(self.branchDnsConnectionPipe):
				if type(self.name[i][0]) == list:
					for name in self.name[i][0]:
						if name in branchDnsConnection:
							branches.append(self.branchName[j])
							ups = False
							break
				elif self.name[i][0] in branchDnsConnection:
					branches.append(self.branchName[j])
					ups = False
			if ups:
				self.upsBranches.append([None])
			else:
				self.upsBranches.append(branches)
				
	def getAllPathsByBranch(self):
		"""
		Gets all the path combinations by branch
		
		:return:
		"""

		upsBranches = []  # get a list of the most upstream branches
		for i, branch in enumerate(self.branchName):
			if self.upsBranches[i] == [None]:
				upsBranches.append(branch)
		
		pathCounter = 0
		todos = upsBranches  # todos are paths to be considered
		todosPath = [None] * len(upsBranches)  # todosPaths are the path numbers where todos came from
		todosSplit = [None] * len(upsBranches)  # todosSplits are where on the path the split occurred
		# loop through adding and removing todos until there are none left
		while todos:
			dns = False
			todo = todos[0]
			todoPath = todosPath[0]
			todoSplit = todosSplit[0]
			if todoPath is None:
				path = []
				counter = 0
			else:
				path = self.paths[todoPath][:todoSplit+1]
				counter = len(path)
			while not dns:
				# loop through until downtream is reached
				index = self.branchName.index(todo)
				next = self.dnsBranches[index]
				if len(next) > 1:
					todos += next[1:]
					todosPath += [pathCounter] * len(next[1:])
					todosSplit += [counter] * len(next[1:])
				next = next[0]
				if next is None:
					dns = True
				path.append(todo)
				todo = next
				counter += 1
			pathCounter += 1
			self.paths.append(path)
			self.pathsName.append('Path {0}'.format(pathCounter))
			todos = todos[1:]
			todosPath = todosPath[1:]
			todosSplit = todosSplit[1:]
			
	def getAllPathsByNwk(self):
		"""
		Get all paths listed by nwk name
		
		:return:
		"""

		for path in self.paths:
			pathsNwks = []
			pathsLen = []
			pathsGroundCh = []
			pathsGround = []
			pathsAdvG = []
			pathsAdvI = []
			pathsDecA = []
			pathsSharpA = []
			pathsInsffCover = []
			pathsWarningChainage = []
			for i, branch in enumerate(path):
				if i + 1 < len(path):
					dnsB = path[i+1]
				else:
					dnsB = None
				connNwk = False  # Connection pipe - the pipe that the branch connects to in the downstream branch
				if i == 0:
					connNwkName = None
					connNwk = True  # most upstream and therefore no connection pipe
				bInd = self.branchName.index(branch)  # Branch index
				for j, nwk in enumerate(self.name[bInd]):
					if nwk == connNwkName:
						connNwk = True
					if connNwk:
						pathsNwks.append(nwk)
						pathsLen.append(self.length[bInd][j])
						pathsAdvG.append(self.adverseGradient[bInd][j])
						pathsAdvI.append(self.adverseInvert[bInd][j])
						pathsDecA.append(self.decreaseFlowArea[bInd][j])
						pathsSharpA.append(self.sharpAngle[bInd][j])
						pathsInsffCover.append(self.insffCover[bInd][j])
						pathsWarningChainage.append(self.warningChainage[bInd][j])
						if self.coverLimit is not None:
							pathsGroundCh.append(self.groundCh[bInd][j])
							if None not in self.ground[bInd][j]:
								pathsGround.append(self.ground[bInd][j])
							else:
								ground = []
								for x in self.ground[bInd][j]:
									if x is not None:
										ground.append(x)
									else:
										ground.append(np.nan)
								pathsGround.append(ground)
					if j + 1 == len(self.name[bInd]):
						connNwkNames = self.branchDnsConnectionPipe[bInd]
						if dnsB is not None:
							bdInd = self.branchName.index(dnsB)
						if connNwkNames is not 'OUTLET':
							if connNwkNames in self.name[bdInd]:
								connNwkName = connNwkNames
							else:
								for c in connNwkNames:
									if c in self.name[bdInd]:
										connNwkName = c
										break
			self.pathsNwks.append(pathsNwks)
			self.pathsLen.append(sum(pathsLen))
			self.pathsNwksLen.append(pathsLen)
			self.pathsGroundCh.append(pathsGroundCh)
			self.pathsGround.append(pathsGround)
			self.pathsAdverseGradient.append(pathsAdvG)
			self.pathsAdverseInvert.append(pathsAdvI)
			self.pathsDecreaseFlowArea.append(pathsDecA)
			self.pathsSharpAngle.append(pathsSharpA)
			self.pathsInsffCover.append(pathsInsffCover)
			self.pathsWarningChainage.append(pathsWarningChainage)
	
	def addX(self, ind, start, insertInd):
		"""
		Create X values path for plotting.

		:param ind: path index
		:param start: start value for the path
		:return: populates x plotting values
		"""
		
		x = [start]
		length = start
		path = self.pathsNwks[ind]
		
		for i, nwk in enumerate(path):
			found = False
			for j, name in enumerate(self.name):
				for k, nwk2 in enumerate(name):
					if nwk == nwk2:
						found = True
						break
				if found:
					break
			length += self.length[j][k]
			if i + 1 == len(path):
				x.append(length)
			else:
				x.append(length)
				x.append(length)
		self.pathsX.insert(insertInd, x)
		
	def addInv(self, ind, insertInd):
		"""
		Create Y values for the nwk inverts
		
		:param ind: path index
		:return: populates y invert plotting values
		"""
		
		usInvert = []
		dsInvert = []
		invert = []
		path = self.pathsNwks[ind]
		for i, nwk in enumerate(path):
			found = False
			for j, name in enumerate(self.name):
				for k, nwk2 in enumerate(name):
					if nwk == nwk2:
						found = True
						break
				if found:
					break
			usInvert.append(self.usInvert[j][k])
			dsInvert.append(self.dsInvert[j][k])
			if self.usInvert[j][k] == -99999:
				invert.append(np.nan)
			else:
				invert.append(self.usInvert[j][k])
			if self.dsInvert[j][k] == -99999:
				invert.append(np.nan)
			else:
				invert.append(self.dsInvert[j][k])
		self.pathsInvert.insert(insertInd, invert)
		self.pathsUsInvert.insert(insertInd, usInvert)
		self.pathsDsInvert.insert(insertInd, dsInvert)
	
	def addGround(self, ind, xInd):
		"""
		Create Y values for the ground levels

		:param ind: path index
		:return: populates y ground plotting values
		"""

		groundX = []
		ground = []
		path = self.pathsGroundCh[ind]
		x = self.pathsX[xInd][0]
		for i, chainages in enumerate(path):
			for j, ch in enumerate(chainages):
				groundX.append(x + ch)
				ground.append(self.pathsGround[ind][i][j])
			x += ch
		self.pathsGroundX.insert(xInd, groundX)
		self.pathsGroundY.insert(xInd, ground)
		
	def addPipes(self, ind, xInd):
		"""
		Create patch object for pipes for plotting
		
		:param ind: path index
		:param xInd: index of X values
		:return: populates pipe plotting values
		"""

		pipes = []
		areas = []
		path = self.pathsNwks[ind]
		for i, nwk in enumerate(path):
			pipe = False
			found = False
			area = 0
			for j, name in enumerate(self.name):
				for k, nwk2 in enumerate(name):
					if nwk == nwk2:
						found = True
						break
				if found:
					break
			if type(self.type[j][k]) == list:  # unbranched dual channel
				if 'c' in self.type[j][k] or 'C' in self.type[j][k]:
					y = self.width[j][k]
					pipe = True
				if 'r' in self.type[j][k] or 'R' in self.type[j][k]:
					y = self.height[j][k]
					pipe = True
			else:  # single channel
				if self.type[j][k].lower() == 'c':
					y = self.width[j][k]
					pipe = True
				elif self.type[j][k].lower() == 'r':
					y = self.height[j][k]
					pipe = True
			if self.pathsInvert[xInd][i*2] == -99999 or self.pathsInvert[xInd][i*2+1] == -99999:
				pipe = False
			if pipe:
				area = self.area[j][k]
				xStart = self.pathsX[xInd][i*2]
				xEnd = self.pathsX[xInd][i*2+1]
				yStartInv = self.pathsInvert[xInd][i*2]
				yStartObv = yStartInv + y
				yEndInv = self.pathsInvert[xInd][i*2+1]
				yEndObv = yEndInv + y
				xPatch = [xStart, xEnd, xEnd, xStart]
				yPatch = [yStartInv, yEndInv, yEndObv, yStartObv]
				pipes.append(zip(xPatch, yPatch))
				areas.append(area)
			else:
				pipes.append([])
		self.pathsPipe.insert(xInd, pipes)
		self.pathsArea.insert(xInd, areas)
		
	def addFlags(self, ind, xInd):
		"""
		Create X and Y Coords for integrity flags
		
		:param ind: path index
		:param xInd: index of X values
		:return: populates integrity plotting values
		"""

		advG = [[], []]  # X list, Y List
		advI = [[], []]  # X list, Y List
		decA = [[], []]  # X list, Y List
		sharpA = [[], []]  # X list, Y List
		insffC = [[], []]  # X list, Y List
		path = self.pathsNwks[ind]
		for i, nwk in enumerate(path):
			count = 1  # use to stack the flags on top of one another
			if self.pathsAdverseGradient[ind][i]:
				xStart = self.pathsX[xInd][i * 2]
				xEnd = self.pathsX[xInd][i * 2 + 1]
				x = (xStart + xEnd) / 2
				if len(self.pathsPipe[xInd][i]) > 0:
					yStart = self.pathsPipe[xInd][i][3][1] + (0.1 * count)
					yEnd = self.pathsPipe[xInd][i][2][1] + (0.1 * count)
				else:
					yStart = self.pathsInvert[xInd][i * 2] + (0.1 * count)
					yEnd = self.pathsInvert[xInd][i * 2 + 1] + (0.1 * count)
				y = (yStart + yEnd) / 2
				advG[0].append(x)
				advG[1].append(y)
				count += 1
			if self.pathsAdverseInvert[ind][i]:
				x = self.pathsX[xInd][i * 2]
				if len(self.pathsPipe[xInd][i]) > 0:
					y = self.pathsPipe[xInd][i][3][1] + (0.1 * count)
				else:
					y = self.pathsInvert[xInd][i * 2] + (0.1 * count)
				advI[0].append(x)
				advI[1].append(y)
				count += 1
			if self.pathsDecreaseFlowArea[ind][i]:
				x = self.pathsX[xInd][i * 2]
				if len(self.pathsPipe[xInd][i]) > 0:
					y = self.pathsPipe[xInd][i][3][1] + (0.1 * count)
				else:
					y = self.pathsInvert[xInd][i * 2] + (0.1 * count)
				decA[0].append(x)
				decA[1].append(y)
				count += 1
			if self.pathsSharpAngle[ind][i]:
				x = self.pathsX[xInd][i * 2 + 1]
				if len(self.pathsPipe[xInd][i]) > 0:
					y = self.pathsPipe[xInd][i][2][1] + (0.1 * count)
				else:
					y = self.pathsInvert[xInd][i * 2 + 1] + (0.1 * count)
				sharpA[0].append(x)
				sharpA[1].append(y)
				count += 1
			if self.pathsInsffCover[ind][i]:
				xStart = self.pathsX[xInd][i * 2]
				xEnd = self.pathsX[xInd][i * 2 + 1]
				x = xStart + self.pathsWarningChainage[ind][i]
				if len(self.pathsPipe[xInd][i]) > 0:
					yStart = self.pathsPipe[xInd][i][3][1] + (0.1 * count)
					yEnd = self.pathsPipe[xInd][i][2][1] + (0.1 * count)
				else:
					yStart = self.pathsInvert[xInd][i * 2] + (0.1 * count)
					yEnd = self.pathsInvert[xInd][i * 2 + 1] + (0.1 * count)
				y = (yStart - yEnd) / (xStart - xEnd) * (x - xStart) + yStart
				insffC[0].append(x)
				insffC[1].append(y)
				count += 1
		self.pathsPlotAdvG.insert(xInd, advG)
		self.pathsPlotAdvI.insert(xInd, advI)
		self.pathsPlotDecA.insert(xInd, decA)
		self.pathsPlotSharpA.insert(xInd, sharpA)
		self.pathsPlotInCover.insert(xInd, insffC)
		
	def getPlotFormat(self):
		"""
		Arrays data into plottable format
		
		:return:
		"""
		
		self.checkDnsNwks()
		self.getBranchConnectivity()
		self.getAllPathsByBranch()
		self.getAllPathsByNwk()
		
		pathsLen = self.pathsLen[:]  # create a copy of the variable for looping
		usedPathNwks = []
		usedPathInds = []
		while pathsLen:
			found = False
			commonNwk = None
			maxPathLen = max(pathsLen)  # start at longest and then next longest and so on
			pathInd = self.pathsLen.index(maxPathLen)  # index of longest path in class path list
			pathInd2 = pathsLen.index(maxPathLen)  # index of longest path in local path list
			# determine if path shares a common nwk with an existing path
			for nwk in self.pathsNwks[pathInd]:
				for i, usedPath in enumerate(usedPathNwks):
					if nwk in usedPath:
						commonNwk = nwk
						found = True
						break
				if found:
					break
			if commonNwk is not None:
				# find X value of processed path
				comNwkInd = usedPathNwks[i].index(commonNwk)
				existPathX = self.pathsX[i][comNwkInd*2]
				# find X of new path
				comNwkInd = self.pathsNwks[pathInd].index(commonNwk)
				currentPathX = sum(self.pathsNwksLen[pathInd][:comNwkInd])
				s = existPathX - currentPathX  # start path X value
			else:
				s = 0  # starting chainage if there is no common pipes
			usedPathInds.append(pathInd)
			seq = sorted(usedPathInds)
			pathInd3 = seq.index(pathInd)
			self.addX(pathInd, s, pathInd3)
			self.addInv(pathInd, pathInd3)
			if self.coverLimit is not None:
				self.addGround(pathInd, pathInd3)
			self.addPipes(pathInd, pathInd3)
			self.addFlags(pathInd, pathInd3)
			del pathsLen[pathInd2]
			usedPathNwks.insert(pathInd, self.pathsNwks[pathInd])
