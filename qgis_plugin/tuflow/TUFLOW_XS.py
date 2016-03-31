
import sys
import os
import csv
version = '2015-12-AA'

class XS_Data():
	def __init__(self,fpath,fname,xs_type,flags,col1,col2,col3,col4,col5,col6):
		self.source = fname
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
		print('Loading section: '+fname)
		self.fullpath = os.path.join(fpath,fname)
		print('Fullpath: '+self.fullpath)
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
		with open(self.fullpath, 'rb') as csvfile:
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

		with open(self.fullpath, 'rb') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			try:
				for i in range(0,nheader):
					reader.next()
				for line in reader:
					self.x.append(float(line[c1_ind]))
					self.z.append(float(line[c2_ind]))
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

class XS():
	"""
	XS class for reading and storing section / tabular data
	"""
	def __init__(self):
		self.script_version = version
		self.clear()


	def clear(self):
		self.nXS = 0
		self.all_loaded = False
		self.data = []
		self.source = []
		self.all_types = []

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

	def addfromfeature(self,fpath,fields,feature):
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
			self.data.append(XS_Data(fpath,source,xs_type,flags,col1,col2,col3,col4,col5,col6))
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