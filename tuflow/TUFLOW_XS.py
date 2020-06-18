
import sys
import os
import csv
import numpy.ma as ma
from .tuflowqgis_library import interpolate
version = '2018-04-AA'


class XS_Data():
	def __init__(self,fpath,fname,xs_type,flags,col1,col2,col3,col4,col5,col6, feat):
		self.source = fname
		self.feature = feat
		#self.type = xs_type
		self.flags = flags
		self.col1 = col1
		self.col2 = col2
		self.col3 = col3
		self.col4 = col4
		self.col5 = col5
		self.col6 = col6
		self.np = 0
		self.loaded = False
		#def load(self,fpath,fname,xs_type,flags,col1,col2,col3):
		#print('Loading section: '+fname)
		self.fullpath = os.path.join(fpath,fname)
		#print('Fullpath: '+self.fullpath)
		self.x = []
		self.z = []
		self.mat = []
		self.has_mat = False
		self.mat_type = None #
		self.area = []
		self.has_area = False
		self.perim = []
		self.has_perim = False

		#error initialisation
		self.error = False
		self.message = None

		# check types
		xs_type = xs_type.upper()
		if flags:
			flags = flags.upper()
		if xs_type in ('XZ'):
			self.type = 'XZ'
			if flags:
				flags = flags.upper()
				if 'M' in flags:
					self.has_mat = True
					self.mat_type= 'M'
				elif 'N' in flags:
					self.has_mat = True
					self.mat_type= 'N'
				elif 'R' in flags:
					self.has_mat = True
					self.mat_type= 'R'
		elif xs_type in ('HW','CS'):
			self.type = 'HW'
			if flags:
				if 'F' in flags:
					self.has_mat = True
					self.mat_type= 'F'
				elif 'N' in flags:
					self.has_mat = True
					self.mat_type= 'N'
				if 'A' in flags:
					self.has_area = True
				if 'P' in flags:
					self.has_perim = True
		elif xs_type in ('BG','LC'):
			self.type = 'LC'
			# no flags recognised
		elif xs_type in ('NA'):
			self.type = 'NA'
			# no flags recognised
		else:
			self.error = True
			self.message = 'ERROR - Unexpected section type: '+xs_type

		self.type = xs_type
		# check file exists
		if not os.path.isfile(self.fullpath):
			self.error = True
			self.message = 'ERROR Unable to load'+self.fullpath
			return

		# read header
		with open(self.fullpath, 'r') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			nheader = 0
			for line in reader:
				try:
					for i in line[0:3]:
						if len(i) > 0:
							float(i)
					break
				except:
					nheader = nheader + 1
					header = line
		csvfile.close()
		header = [element.upper() for element in header]

		# find which columns data is in
		if (self.col1 == None):
			c1_ind = 0
		else:
			try:
				c1_ind  = header.index(self.col1)
			except:
				self.error = True
				self.message = 'ERROR - Unable to find '+self.col1+ ' in header.'
				return
		if (self.col2 == None):
			c2_ind = 1
		else:
			try:
				c2_ind  = header.index(self.col2)
			except:
				self.error = True
				self.message = 'ERROR - Unable to find '+self.col2+ ' in header.'
				return
		if self.flags:
			if self.col3 == None:
				c3_ind = 2
			else:
				try:
					c3_ind  = header.index(self.col3)
				except:
					self.error = True
					self.message = 'ERROR - Unable to find '+self.col3+ ' in header.'
					return
			if self.col4 == None:
				c4_ind = 3
			else:
				try:
					c4_ind  = header.index(self.col4)
				except:
					self.error = True
					self.message = 'ERROR - Unable to find '+self.col4+ ' in header.'
					return
			if self.col5 == None:
				c5_ind = 4
			else:
				try:
					c5_ind  = header.index(self.col5)
				except:
					self.error = True
					self.message = 'ERROR - Unable to find '+self.col5+ ' in header.'
					return
			if self.col6 == None:
				c6_ind = 5
			else:
				try:
					c6_ind  = header.index(self.col6)
				except:
					self.error = True
					self.message = 'ERROR - Unable to find '+self.col6+ ' in header.'
					return

		with open(self.fullpath, 'r') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			try:
				for i in range(0,nheader):
					next(reader)
				for line in reader:
					if self.type.upper() == 'XZ':
						self.x.append(float(line[c1_ind]))
						self.z.append(float(line[c2_ind]))
					else:
						self.z.append(float(line[c1_ind]))
						self.x.append(float(line[c2_ind]))
					if self.flags:
						if self.type == 'XZ':
							if self.has_mat:
								self.mat.append(float(line[c3_ind]))
						elif self.type == 'HW':
							if self.has_area:
								self.area.append(float(line[c3_ind]))
							if self.has_perim:
								self.perim.append(float(line[c4_ind]))
							if self.has_mat:
								self.mat.append(float(line[c5_ind]))
			except:
				self.error = True
				self.message = 'ERROR - Error reading cross section '+self.fullpath
				return
		csvfile.close()

		#checks
		if len(self.x)!=len(self.z):
			self.error = True
			self.message = 'ERROR - Size of tabular data for primary columns does not match'
		if self.has_mat:
			if len(self.x)!=len(self.mat):
				self.error = True
				self.message = 'ERROR - Size of tabular data for roughness column does not match'
		if self.has_area:
			if len(self.x)!=len(self.area):
				self.error = True
				self.message = 'ERROR - Size of tabular data for area column does not match'
		if self.has_perim:
			if len(self.x)!=len(self.perim):
				self.error = True
				self.message = 'ERROR - Size of tabular data for perimeter column does not match'

		# normal return
		if not self.error:
			self.loaded = True
			self.np = len(self.x)


class XS_layer():
	"""
	Class object to store XS_data objects in memory.
	"""

	def __init__(self, xsLayer):
		self.xsLayer = xsLayer
		self.name = xsLayer.name()
		self.source = xsLayer.source()
		self.xs = []
		self.xsName = []
		self.xsTypes = []

		for feature in self.xsLayer.getFeatures():
			a = feature[0]
			b = self.addfromfeature(os.path.dirname(self.source), self.xsLayer.fields(), feature)
			self.xs.append(b)
			self.xsName.append(a)
			if b.type not in self.xsTypes:
				self.xsTypes.append(b.type)

	def addfromfeature(self, fpath, fields, feature):
		error = False
		message = None
		# get field info
		if len(fields) < 9:
			error = True
			message = 'ERROR - Expecting at least 9 fields in 1d_xs layer'
			return error, message
		try:
			f1 = str(fields.field(0).name())  # source
			f2 = str(fields.field(1).name())  # type
			f3 = str(fields.field(2).name())  # flags
			f4 = str(fields.field(3).name())  # column_1
			f5 = str(fields.field(4).name())  # column_2
			f6 = str(fields.field(5).name())  # column_3
			f7 = str(fields.field(6).name())  # column_4
			f8 = str(fields.field(7).name())  # column_5
			f9 = str(fields.field(8).name())  # column_6
		except:
			error = True
			message = 'ERROR - Unable to extract field names'
			return error, message

		# get information from fields
		try:
			source = feature[f1]
			xs_type = feature[f2].upper()
			flags = feature[f3]
			if not flags:  # is QGIS variant null
				flags = None
			col1 = feature[f4]
			if not col1:  # is QGIS variant null
				col1 = None
			col2 = feature[f5]
			if not col2:  # is QGIS variant null
				col2 = None
			col3 = feature[f6]
			if not col3:  # is QGIS variant null
				col3 = None
			col4 = feature[f7]
			if not col4:  # is QGIS variant null
				col4 = None
			col5 = feature[f8]
			if not col5:  # is QGIS variant null
				col5 = None
			col6 = feature[f9]
			if not col6:  # is QGIS variant null
				col6 = None
		except:
			error = True
			message = 'ERROR extract attribute data from fields'
			return error, message

		try:
			return XS_Data(fpath, source, xs_type, flags, col1, col2, col3, col4, col5, col6)
		except:
			error = True
			message = 'ERROR - Adding XS data for ' + source
			return message


class XS_results():
	"""
	XS class to store results
	"""

	def __init__(self, nodeList, channelList, xsData, nodeResults):
		self.nodeList = nodeList
		self.channelList = channelList
		self.xsData = xsData
		self.nodeResults = nodeResults
		self.maxH = []
		self.h = []
		self.xsName = []
		self.maxHx = []
		self.maxHz = []
		self.hx = []
		self.hz = []
		self.rb = []
		self.lb = []
		self.rbx = []
		self.lbx = []
		self.message = []
		self.error = False

		# Get Cross Section Source
		for xs in self.xsData:
			try:
				self.xsName.append(xs.source)
			except:
				self.error = True
				self.message = 'cross section did not load in correctly'
				return

		for j, id in enumerate(self.nodeList):
			if id is not None:
				i = self.nodeResults.Data_1D.Node_Max.ID.index(id)
				# Get Max water level results
				self.maxH.append(self.nodeResults.Data_1D.Node_Max.HMax[i])
				# Get temporal water level results
				timestep = []
				for h in self.nodeResults.Data_1D.H.Values:
					timestep.append(h[i+2])
				self.h.append(timestep)
				# Get right and left bank
				if self.nodeResults.nodes.node_nChan[i] == 2:
					usChannel = self.nodeResults.nodes.node_channels[i][0]
					dsChannel = self.nodeResults.nodes.node_channels[i][1]
				elif self.nodeResults.nodes.node_nChan[i] == 1 and self.nodeResults.nodes.node_name[i][-2:] == '.1':
					dsChannel = self.nodeResults.nodes.node_channels[i][0]
				elif self.nodeResults.nodes.node_nChan[i] == 1 and self.nodeResults.nodes.node_name[i][-2:] == '.2':
					usChannel = self.nodeResults.nodes.node_channels[i][0]
				elif self.nodeResults.nodes.node_nChan[i] > 2:
					usChannel = self.nodeResults.nodes.node_channels[i][0]
				try:
					j = self.nodeResults.Channels.chan_name.index(usChannel)
					self.lb.append([self.nodeResults.Channels.chan_LBDS_Obv[j]])
					self.rb.append([self.nodeResults.Channels.chan_RBDS_Obv[j]])
				except:
					j = self.nodeResults.Channels.chan_name.index(dsChannel)
					self.lb.append([self.nodeResults.Channels.chan_LBUS_Obv[j]])
					self.rb.append([self.nodeResults.Channels.chan_RBUS_Obv[j]])
			elif self.channelList[j] is not None:
				id = self.channelList[j]
				i = self.nodeResults.Channels.chan_name.index(id)
				usNode = self.nodeResults.Channels.chan_US_Node[i]
				dsNode = self.nodeResults.Channels.chan_DS_Node[i]
				iUs = self.nodeResults.Data_1D.Node_Max.ID.index(usNode)
				iDs = self.nodeResults.Data_1D.Node_Max.ID.index(dsNode)
				# Get Max water level results
				maxHUs = self.nodeResults.Data_1D.Node_Max.HMax[iUs]
				maxHDs = self.nodeResults.Data_1D.Node_Max.HMax[iDs]
				maxHMid = (maxHUs + maxHDs) / 2
				self.maxH.append(maxHMid)
				# Get temporal water level results
				timestep = []
				for h in self.nodeResults.Data_1D.H.Values:
					hUs = h[iUs+2]
					hDs = h[iDs+2]
					hMid = (hUs + hDs) / 2
					timestep.append(hMid)
				self.h.append(timestep)
			else:
				self.maxH.append(None)


	@staticmethod
	def fitResToXS2(xs, h):
		"""

		"""

		xmin, xmax = min(xs.x), max(xs.x)
		ymin, ymax = min(xs.z), max(xs.z)

		if xs.type.upper() != 'XZ':
			x = [xmin, xmax]
			y = [h, h]
		else:
			if h >= ymax:
				x = [xmin, xmax]
				y = [h, h]
			elif h <= ymin:
				y = [ymin]
				i = xs.z.index(ymin)
				x = [xs.x[i]]
			else:
				x = []
				y = []
				waswet = xs.z[0] <= h
				if waswet:
					x.append(xs.x[0])
					y.append(h)
				mi = []
				i = 0
				for c in xs.x[1:]:
					i += 1
					wet = xs.z[i] <= h
					if waswet != wet:
						if xs.z[i] == h:
							x.append(c)
							y.append(h)
						else:
							x.append(interpolate(h, xs.z[i-1], xs.z[i], xs.x[i-1], xs.x[i]))
							y.append(h)
						if waswet:
							x.append(c)
							y.append(h)
							mi.append(len(y) - 1)
						waswet = wet
				if wet:
					x.append(xmax)
					y.append(h)
				y = ma.array(y)
				for i in mi:
					y[i] = ma.masked

		return x, y

	def fitResToXs(self):
		"""
		generates x and y plot of water level results with respect to XS

		void return:
		"""

		for i, wl in enumerate(self.maxH):
			if wl is not None:
				if self.xsData[i].type.upper() == 'XZ':
					# Cross Section minimum and maximum
					xsMax = max(self.xsData[i].z)
					xsMin = min(self.xsData[i].z)
					minIndex = self.xsData[i].z.index(xsMin)
					leftBank = max(self.xsData[i].z[:minIndex])
					leftBankIndex = self.xsData[i].z[:minIndex].index(leftBank)
					rightBank = max(self.xsData[i].z[minIndex:])
					rightBankIndex = self.xsData[i].z[minIndex:].index(rightBank) + minIndex
					if wl <= xsMin:
						wlx = [self.xsData[i].x[minIndex]]
						wlz = xsMin
					elif wl >= xsMax:  # water level is higher than cross section
						wlx = [self.xsData[i].x[0], self.xsData[i].x[-1]]
						wlz = wl
					elif wl <= leftBank and wl <= rightBank:  # Water level is completely within XSection
						wlz = wl
						# Get X minimum value
						zPrev = -99999
						for j, z in enumerate(self.xsData[i].z[leftBankIndex:minIndex+1]):
							j = j + leftBankIndex
							if z == wl:
								# don't need to interpolate as there is an exact match
								xMin = self.xsData[i].x[j]
								break
							elif z < wl and zPrev > wl:
								# Interpolate x value
								xMin = (self.xsData[i].x[j] - self.xsData[i].x[j-1]) / \
									   (self.xsData[i].z[j] - self.xsData[i].z[j-1]) * \
									   (wl - self.xsData[i].z[j-1]) + self.xsData[i].x[j-1]
								break
							else:
								zPrev = z
						# Get X maximum value
						zPrev = 99999
						for j, z in enumerate(self.xsData[i].z[minIndex:rightBankIndex+1]):
							j = j + minIndex
							if z == wl:
								# don't need to interpolate as there is an exact match
								xMax = self.xsData[i].x[j]
								break
							elif z > wl and zPrev < wl:
								# Interpolate x value
								xMax = (self.xsData[i].x[j] - self.xsData[i].x[j-1]) / \
									   (self.xsData[i].z[j] - self.xsData[i].z[j-1]) * \
									   (wl - self.xsData[i].z[j-1]) + self.xsData[i].x[j-1]
								break
							else:
								zPrev = z
						wlx = [xMin, xMax]
					elif wl >= leftBank:  # Water Level is higher than the left bank but within the right bank
						wlz = wl
						xMin = self.xsData[i].x[0]
						# Get X maximum value
						zPrev = 99999
						for j, z in enumerate(self.xsData[i].z[minIndex:rightBankIndex+1]):
							j = j + minIndex
							if z == wl:
								# don't need to interpolate as there is an exact match
								xMax = self.xsData[i].x[j]
								break
							elif z > wl and zPrev < wl:
								# Interpolate x value
								xMax = (self.xsData[i].x[j] - self.xsData[i].x[j - 1]) / \
									   (self.xsData[i].z[j] - self.xsData[i].z[j - 1]) * \
									   (wl - self.xsData[i].z[j - 1]) + self.xsData[i].x[j - 1]
								break
							else:
								zPrev = z
						wlx = [xMin, xMax]
					elif wl >= rightBank:  # Water Level is higher than the right bank but within the left bank
						wlz = wl
						# Get X minimum value
						zPrev = -99999
						for j, z in enumerate(self.xsData[i].z[leftBankIndex:minIndex+1]):
							j = j + leftBankIndex
							if z == wl:
								# don't need to interpolate as there is an exact match
								xMin = self.xsData[i].x[j]
								break
							elif z < wl and zPrev > wl:
								# Interpolate x value
								xMin = (self.xsData[i].x[j] - self.xsData[i].x[j - 1]) / \
									   (self.xsData[i].z[j] - self.xsData[i].z[j - 1]) * \
									   (wl - self.xsData[i].z[j - 1]) + self.xsData[i].x[j - 1]
								break
							else:
								zPrev = z
						xMax = self.xsData[i].x[-1]
						wlx = [xMin, xMax]
				else:
					wlx = self.xsData[i].z
					wlz = wl
				wlz = [wlz] * len(wlx)
				self.maxHx.append(wlx)
				self.maxHz.append(wlz)


		for i, timestep in enumerate(self.h):
			if timestep is not None:
				xsMax = max(self.xsData[i].z)
				xsMin = min(self.xsData[i].z)
				minIndex = self.xsData[i].z.index(xsMin)
				leftBank = max(self.xsData[i].z[:minIndex])
				leftBankIndex = self.xsData[i].z[:minIndex].index(leftBank)
				rightBank = max(self.xsData[i].z[minIndex:])
				rightBankIndex = self.xsData[i].z[minIndex:].index(rightBank) + minIndex
				hx = []
				hz = []
				for wl in timestep:
					if self.xsData[i].type.upper() == 'XZ':
						# Cross Section minimum and maximum
						if wl <= xsMin:
							wlx = [self.xsData[i].x[minIndex]]
							wlz = xsMin
						elif wl >= xsMax:  # water level is higher than cross section
							wlz = wl
							wlx = [self.xsData[i].x[0], self.xsData[i].x[-1]]
						elif wl <= leftBank and wl <= rightBank:  # Water level is completely within XSection
							wlz = wl
							# Get X minimum value
							zPrev = -99999
							for j, z in enumerate(self.xsData[i].z[leftBankIndex:minIndex+1]):
								j = j + leftBankIndex
								if z == wl:
									# don't need to interpolate as there is an exact match
									xMin = self.xsData[i].x[j]
									break
								elif z < wl and zPrev > wl:
									# Interpolate x value
									xMin = (self.xsData[i].x[j] - self.xsData[i].x[j-1]) / \
										   (self.xsData[i].z[j] - self.xsData[i].z[j-1]) * \
										   (wl - self.xsData[i].z[j-1]) + self.xsData[i].x[j-1]
									break
								else:
									zPrev = z
							# Get X maximum value
							zPrev = 99999
							for j, z in enumerate(self.xsData[i].z[minIndex:rightBankIndex+1]):
								j = j + minIndex
								if z == wl:
									# don't need to interpolate as there is an exact match
									xMax = self.xsData[i].x[j]
									break
								elif z > wl and zPrev < wl:
									# Interpolate x value
									xMax = (self.xsData[i].x[j] - self.xsData[i].x[j-1]) / \
										   (self.xsData[i].z[j] - self.xsData[i].z[j-1]) * \
										   (wl - self.xsData[i].z[j-1]) + self.xsData[i].x[j-1]
									break
								else:
									zPrev = z
							wlx = [xMin, xMax]
						elif wl >= leftBank:  # Water Level is higher than the left bank but within the right bank
							wlz = wl
							xMin = self.xsData[i].x[0]
							# Get X maximum value
							zPrev = 99999
							for j, z in enumerate(self.xsData[i].z[minIndex:rightBankIndex+1]):
								j = j + minIndex
								if z == wl:
									# don't need to interpolate as there is an exact match
									xMax = self.xsData[i].x[j]
									break
								elif z > wl and zPrev < wl:
									# Interpolate x value
									xMax = (self.xsData[i].x[j] - self.xsData[i].x[j - 1]) / \
										   (self.xsData[i].z[j] - self.xsData[i].z[j - 1]) * \
										   (wl - self.xsData[i].z[j - 1]) + self.xsData[i].x[j - 1]
									break
								else:
									zPrev = z
							wlx = [xMin, xMax]
						elif wl >= rightBank:  # Water Level is higher than the right bank but within the left bank
							wlz = wl
							# Get X minimum value
							zPrev = -99999
							for j, z in enumerate(self.xsData[i].z[leftBankIndex:minIndex+1]):
								j = j + leftBankIndex
								if z == wl:
									# don't need to interpolate as there is an exact match
									xMin = self.xsData[i].x[j]
									break
								elif z < wl and zPrev > wl:
									# Interpolate x value
									xMin = (self.xsData[i].x[j] - self.xsData[i].x[j - 1]) / \
										   (self.xsData[i].z[j] - self.xsData[i].z[j - 1]) * \
										   (wl - self.xsData[i].z[j - 1]) + self.xsData[i].x[j - 1]
									break
								else:
									zPrev = z
							xMax = self.xsData[i].x[-1]
							wlx = [xMin, xMax]
					else:
						wlx = self.xsData[i].z
						wlz = wl
					wlz = [wlz] * len(wlx)
					hx.append(wlx)
					hz.append(wlz)
				self.hx.append(hx)
				self.hz.append(hz)

		# Get x coordinates for left abd right bank
		for i, z in enumerate(self.rb):
			if self.xsData[i].type.upper() == 'XZ':
				self.rbx.append([self.xsData[i].x[-1]])
				self.lbx.append([self.xsData[i].x[0]])



class XS():
	"""
	XS class for reading and storing section / tabular data
	"""
	def __init__(self):
		self.script_version = version
		self.results = []
		self.xsLayers = []
		self.data = []
		self.all_loaded = False
		self.nXS = 0
		self.source = []
		self.all_types = []
		self.layer = None

	def clear(self):
		self.nXS = 0
		self.all_loaded = False
		self.data.clear()
		self.source.clear()
		self.all_types.clear()
		self.results.clear()

	def add(self,fpath,fname,xs_type,flags,col1,col2,col3,col4,col5,col6):
		self.nXS = self.nXS + 1
		self.source.append(fname)

		self.data.append(XS_Data(fpath,fname,xs_type,flags,col1,col2,col3,col4,col5,col6))
		if self.data[-1].error:
			#print('error')
			return self.data[-1].error, self.data[-1].message
		else:
			#print('success - np = '+str( self.data[-1].np))
			if self.all_types.count(self.data[-1].type)<1:
				self.all_types.append(self.data[-1].type)
			return False, None

	def removeByFeaturesNotIncluded(self, features):
		selSource = [x.attributes()[0] for x in features]
		l = len(self.source)
		for i, s in enumerate(reversed(self.source[:])):
			j = l - i - 1
			if s not in selSource:
				try:
					self.source.pop(j)
				except:
					pass
				try:
					self.data.pop(j)
				except:
					pass
				self.nXS -= 1
				if self.nXS < 0:
					self.nXS = 0
		self.all_types = list(set([x.type for x in self.data]))

	def addFromFeature(self,fpath,fields,feature, lyr):
		error = False
		message = None
		# get field info
		if len(fields) < 9:
			error = True
			message = 'ERROR - Expecting at least 9 fields in 1d_xs layer'
			return error, message
		try:
			f1 = str(fields.field(0).name()) #source
			f2 = str(fields.field(1).name()) #type
			f3 = str(fields.field(2).name()) #flags
			f4 = str(fields.field(3).name()) #column_1
			f5 = str(fields.field(4).name()) #column_2
			f6 = str(fields.field(5).name()) #column_3
			f7 = str(fields.field(6).name()) #column_4
			f8 = str(fields.field(7).name()) #column_5
			f9 = str(fields.field(8).name()) #column_6
		except:
			error = True
			message = 'ERROR - Unable to extract field names'
			return error, message

		# get information from fields
		try:
			source = feature[f1]
			xs_type = feature[f2].upper()
			flags = feature[f3]
			if not flags: # is QGIS variant null
				flags = None
			col1 = feature[f4]
			if not col1: # is QGIS variant null
				col1 = None
			col2 = feature[f5]
			if not col2: # is QGIS variant null
				col2 = None
			col3 = feature[f6]
			if not col3: # is QGIS variant null
				col3 = None
			col4 = feature[f7]
			if not col4: # is QGIS variant null
				col4 = None
			col5 = feature[f8]
			if not col5: # is QGIS variant null
				col5 = None
			col6 = feature[f9]
			if not col6: # is QGIS variant null
				col6 = None

		except:
			error = True
			message = 'ERROR extract attribute data from fields'
			return error, message

		#does type exist in self.all_types
		try:
			if self.all_types.count(xs_type)<1:
				self.all_types.append(xs_type)
		except:
			error = True
			message = 'ERROR updating all section type list'
			return error, message

		try:
			self.nXS = self.nXS + 1
			self.source.append(source)
			self.data.append(XS_Data(fpath,source,xs_type,flags,col1,col2,col3,col4,col5,col6, feature))
			if self.data[-1].error:
				return self.data[-1].error, self.data[-1].message
			else: # check if we have seen this type of section before
				if self.all_types.count(self.data[-1].type)<1:
					self.all_types.append(self.data[-1].type)
		except:
			error = True
			message = 'ERROR - Adding XS data for '+source
			return error, message

		#normal termination
		self.lyr = lyr
		return error, message

	def set_axis_titles(self,units):
		error  =False
		message = None
		x_title = ''
		y_title = ''
		if units:
			if units.upper() == 'METRIC':
				dist_unit = '(m)'
				area_unit = '(m2)'
			elif units.upper() == 'ENGLISH':
				dist_unit = '(ft)'
				area_unit = '(ft2)'
			else:
				dist_unit = ''
				area_unit = ''
		else:
			dist_unit = ''
			area_unit = ''

		if self.nXS == 0:
			error = True
			message = 'ERROR - Trying to set title, when no data loaded'
			return error, message, x_title, y_title
		if len(self.all_types)==0:
			error = True
			message = 'ERROR - Data loaded but no items in all_types'
			return error, message, x_title, y_title
		elif len(self.all_types)==1:
			if self.all_types[0]=='XZ':
				x_title = 'Distance '+dist_unit
				y_title = 'Elevation '+dist_unit
			elif self.all_types[0]=='HW':
				x_title = 'Height '+dist_unit
				y_title = 'Width '+dist_unit
			elif self.all_types[0]=='NA':
				x_title = 'Height '+dist_unit
				y_title = 'Area '+area_unit
			elif self.all_types[0]=='LC':
				x_title = 'Height '+dist_unit
				y_title = 'Loss Coefficient'
			else:
				x_title = 'Unknown'
				y_title = 'Unknown'
		else: # more than one type
			for i, xs_type in enumerate(self.all_types):
				if i > 0:
					x_title = x_title+', '
					y_title = y_title+', '
				if xs_type=='XZ':
					x_title = x_title+'Distance '+dist_unit+' (XZ)'
					y_title = y_title+'Elevation '+dist_unit+' (XZ)'
				elif xs_type=='HW':
					x_title = x_title+'Height '+dist_unit+' (HW)'
					y_title = y_title+'Width '+dist_unit+' (HW)'
				elif xs_type=='NA':
					x_title = x_title+'Height '+dist_unit +' (NA)'
					y_title = y_title+'Area '+area_unit+' (NA)'
				elif xs_type=='LC':
					x_title = x_title+'Height '+dist_unit+' (LC)'
					y_title = y_title+'Loss Coefficient'+' (LC)'
		return error, message, x_title, y_title

	def getResults(self, nodeList, channelList, results, selXs):
		"""
		Loads tuflow results for cross sections.

		:param idList: (list) result nodes
		:param results: (list) of TUFLOW_results objects
		:return: cross section results for plotting
		"""

		#for result in results:
		#	xs_res = XS_results(idList, self.data, result)
		#	xs_res.fitResToXs()
		#	self.results.append(xs_res)

		self.results = []  # clear results list

		selData = []
		for data in selXs:
			index = self.xsLayer.xsName.index(data)
			selData.append(self.xsLayer.xs[index])

		for result in results:
			xs_res = XS_results(nodeList, channelList, selData, result)
			xs_res.fitResToXs()
			self.results.append(xs_res)

	def loadIntoMemory(self, xsLayer):
		"""
		Loads 1d_xs layer cross sections into memory

		:param xsLayer: QgisVectorLayer of TUFLOW cross sections
		:return: Cross Section Layer object
		"""

		self.xsLayer = XS_layer(xsLayer)

	@staticmethod
	def getAllSourcesForType(lyr, t):
		"""
		Gets all source names for type e.g. 'XZ'
		"""

		return [x.attributes()[0].lower() for x in list(filter(lambda x: x.attributes()[1].lower() == t.lower(), lyr.getFeatures()))]

	@staticmethod
	def getAllTypes(lyr):
		"""

		"""

		return list(set([x.attributes()[1].upper() for x in lyr.getFeatures()]))
