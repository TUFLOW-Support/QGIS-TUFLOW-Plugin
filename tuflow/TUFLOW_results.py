import os
import numpy
import csv
import ctypes
import re
from tuflow.tuflowqgis_library import (getOSIndependentFilePath, NC_Error,
									   NcDim, NcVar, getNetCDFLibrary)
version = '2018-03-AA' #added reporting location regions



class LP():
	def __init__(self): #initialise the LP data
		self.chan_list = [] #list of channel IDs
		self.chan_index = []  # list of index values in the ChanInfo class
		self.node_list = []
		self.node_index = []
		self.node_bed = []
		self.node_top = []
		self.H_nd_index = []
		self.dist_nodes = []
		self.dist_chan_inverts = []
		self.dist_inverts= []
		self.Hmax = []
		self.Hdata = []
		self.Emax = []
		self.Edata = []
		self.tHmax = []
		self.chan_inv = []
		self.chan_LB = []
		self.chan_RB = []
		self.pit_dist = []
		self.pit_z = []
		self.npits = int(0)
		self.connected = False
		self.static = False
		self.culv_verts = []
		self.adverseH = LP_Adverse()
		self.adverseE = LP_Adverse()

class LP_Adverse():
	"""
	adverse gradient checks for long profile data
	"""
	def __init__(self):
		self.nLocs = 0
		self.chainage = []
		self.elevation = []
		self.node = []

class Data_1D():
	def __init__(self): #initialise the 1D data
		self.nNode = 0
		self.nChan = 0
		self.H = Timeseries()
		self.E = Timeseries()
		self.V = Timeseries()
		self.Q = Timeseries()
		self.A = Timeseries()
		self.Node_Max = Node_Max()
		self.Chan_Max = Chan_Max()

		# 2019 release updates
		self.MB = Timeseries()  # 1D mass balance error
		self.NF = Timeseries()  # 1D node flow regime
		self.CF = Timeseries()  # 1D channel flow regime
		self.CL = Timeseries()  # 1D channel losses

class Data_2D():
	def __init__(self): #initialise the 2D data
		self.H = Timeseries()
		self.V = Timeseries()
		self.Q = Timeseries()
		self.GL = Timeseries()
		self.QA = Timeseries()
		self.QI = Timeseries()
		self.Vx = Timeseries()
		self.Vy = Timeseries()
		self.Vu = Timeseries()
		self.Vv = Timeseries()
		self.VA = Timeseries()
		self.Qx = Timeseries()
		self.Qy = Timeseries()
		self.QS = Timeseries() #structure flow
		self.HUS = Timeseries() #structure U/S level
		self.HDS = Timeseries() #structure D/S level
		self.HAvg = Timeseries() #2017-09-AA average water level in region
		self.HMax = Timeseries() #2017-09-AA max water level in region
		self.QIn = Timeseries() #2017-09-AA flow into a region
		self.QOut = Timeseries() #2017-09-AA flow out of a region
		self.SS = Timeseries() #2017-09-AA Sink / Source within a region
		self.Vol = Timeseries() #2017-09-AA Volume within a region

class Data_RL():
	def __init__(self): #initialise the Reporting Locations
		self.nPoint = 0
		self.nLine = 0
		self.nRegion = 0
		self.H_P = Timeseries()
		self.Q_L = Timeseries()
		self.Vol_R = Timeseries()
		self.P_Max = RL_P_Max()
		self.L_Max = RL_L_Max()
		self.R_Max = RL_R_Max()

class GIS():
	def __init__(self): #initialise the 1D data
		self.P = None
		self.L = None
		self.R = None
		self.RL_P = None
		self.RL_L = None
		self.RL_R = None

class PlotObjects():
	"""
	Hold the plot objects data
	"""
	def __init__(self,fullpath): #read the file
		error = False
		message = ''
		try:
			with open(fullpath, 'r') as csvfile:
				reader = csv.reader(csvfile, delimiter=',', quotechar='"')
				self.ID = []
				self.domain = []
				self.dat_type = []
				self.geom = []
				for row in reader:
					self.ID.append(row[0].strip())
					self.domain.append(row[1])
					self.dat_type.append(row[2])
					self.geom.append(row[3])

			csvfile.close()
			self.nPoints = self.geom.count('P') #2017-08-AA
			self.nLines = self.geom.count('L') #2017-08-AA
			self.nRegions = self.geom.count('R') #2017-08-AA
		except IOError:
			error = True
			message = 'Cannot find the following file: \n{0}'.format(fullpath)
		except:
			error = True
			message = 'ERROR - Error reading data from: '+fullpath

	def find_data(self,ID, domain, geom, dat_type):
		# see if the data exists in the file
		try:
			indA = []
			indB = []
			indC = []
			indD = []
			for i, id in enumerate(self.ID): # have to enumerate rather than index as index only returns a single entry there could be the same ID in 1D and 2D
				if id == ID:
					indA.append(i)
			if len(indA)>0: #ID found - check that 1D/2D is correct
				for ind in indA:
					if self.domain[ind]==domain:
						indB.append(ind)
			if len(indB)>0: #id and domain match
				for ind in indB:
					if self.geom[ind]==geom:
						indC.append(ind)
			if len(indC)>0: #id, domain and geom match
				for ind in indC:
					if (self.dat_type[ind].find(dat_type)>=0):
						indD.append(ind)
			if len(indD)==1:
				#data found
				return True, indD
			elif len(indD)>1:
				print('WARNING - More than 1 matching dataset - using 1st occurence.')
				return True, indD[0]
			else:
				return False, 0
		except:
			print('WARNING - Unknown exception finding data in res.find_data().')
			return False, -99 #error shouldn't really be here

class Timeseries():
	"""
	Timeseries - used for both 1D and 2D data
	"""
	def __init__(self):
		self.loaded = False
		self.ID = []
		self.Header = None
		self.Values =None
		self.nVals = 0
		self.nLocs = 0
		self.null_data = -99999.
		self.nCols = []  # number of columns - added for losses incase more than one column associated with any channel
		self.uID = []  # unique ids - added for losses
		self.lossNames = []  # record loss names because this will be useful later

	def Load(self,fullpath,prefix, simID):
		error = False
		message = ''
		try:
			with open(fullpath, 'r') as csvfile:
				reader = csv.reader(csvfile, delimiter=',', quotechar='"')
				header = next(reader)
		except:
			message = '"ERROR - Error reading header from: '+fullpath
			error = True
			return error, message
		header[0] = 'Timestep'
		header[1] = 'Time'
		self.ID.clear()
		i = 1
		nCol = 1
		rSimID = simID.replace("+", r"\+")  # simID with special re characters returned
		for col in header[2:]:
			i += 1
			a = col[len(prefix)+1:]
			# strip simulation name - highly unlikely more than one match
			a = "".join(re.split(r"\[{0}]".format(rSimID), col, re.IGNORECASE)).strip()
			# strip prefix - only take the first occurrence just in case there's more than one match
			rx = re.search(r"{0}\s".format(prefix), a, re.IGNORECASE)
			if rx is None:
				message = "ERROR - Error reading header data in: {0}".format(fullpath)
				error = True
				return error, message
			if prefix == "LC":
				if rx.span()[0]:
					self.lossNames.append(a[:rx.span()[0]])
				else:
					self.lossNames.append(prefix)
			a = a[rx.span()[1]:]
			self.ID.append(a)
			header[i] = a
			if a == header[i - 1]:
				nCol += 1
			elif i > 2:  # first column with element names
				self.nCols.append(nCol)
				self.uID.append(header[i - 1])
				nCol = 1
			if i + 1 == len(header):  # last column
				self.nCols.append(nCol)
				self.uID.append(header[i - 1])
		self.Header = header
		try:
			if prefix == "F":
				values = numpy.genfromtxt(fullpath, delimiter=",", skip_header=1, dtype=str)
			else:
				values = numpy.genfromtxt(fullpath, delimiter=",", skip_header=1)
			null_array = values == self.null_data
			self.Values = numpy.ma.masked_array(values,null_array)
		except:
			message = 'ERROR - Error reading data from: '+fullpath
			error = True
			return error, message
		try:
			self.nVals = len(self.Values[:,2])
			self.nLocs = len(self.Header)-2
			self.loaded = True
		except IOError:
			message = 'Cannot find the following file: \n{0}'.format(fullpath)
			error = True
			return error, message
		except:
			message = 'ERROR - Error reading data from file. Check file, there may not be any data: {0}'.format(fullpath)
			error = True
			return error, message

		return error, message

	def loadFromNetCDF(self, fullpath, resName, resType, nclib, ncopen, ncid, ncdll, ncDims, ncVars):
		error = False
		message = ""
		if nclib == "python":
			error, message = self.loadFromNetCDFPython(fullpath, resName, resType, ncopen, ncDims, ncVars)
		elif nclib == "c_netcdf.dll":
			error, message = self.loadFromNetCDFCDLL(fullpath, resName, resType, ncid, ncdll, ncDims, ncVars)

		return error, message

	def loadFromNetCDFPython(self, fullpath, resName, resType, ncopen, ncDims, ncVars):
		error = False
		message = ""
		var = None
		for v in ncVars:
			if v.name == resName:
				var = v
				break
		if var is None:
			return False, ""

		values = []
		# ids
		if resType in [x.name for x in ncVars]:
			dims = ncVars[[x.name for x in ncVars].index(resType)].dimLens
			self.nLocs = dims[0]
			self.ID.clear()
			for i in range(self.nLocs):
				self.ID.append("".join([x.decode("utf-8") for x in ncopen[resType][i,:].tolist()]).strip())
		else:
			return False, ""
		self.Header = ['Timestep', 'Time'] + self.ID[:]

		# times
		if "time" in [x.name for x in ncVars]:
			dims = ncVars[[x.name for x in ncVars].index("time")].dimLens
			self.nVals = dims[0]
			v = [x + 1 for x in range(self.nVals)]
			values.append(v)
			v = ncopen["time"][:].tolist()
			values.append(v)
			values = numpy.array(values)
			values = numpy.ma.masked_array(values, False)
		else:
			return False, ""

		# values
		if resName in [x.name for x in ncVars]:
			a = ncopen[resName][:,:]
			self.Values = numpy.insert(a, 0, values, axis=0)
			self.Values = numpy.transpose(self.Values)
		else:
			return False, ""

		self.loaded = True

		return error, message

	def loadFromNetCDFCDLL(self, fullpath, resName, resType, ncid, ncdll, ncDims, ncVars):
		error = False
		message = ""
		var = None
		for v in ncVars:
			if v.name == resName:
				var = v
				break
		if var is None:
			return False, ""

		values = []
		# ids
		if resType in [x.name for x in ncVars]:
			id = ncVars[[x.name for x in ncVars].index(resType)].id
			dims = ncVars[[x.name for x in ncVars].index(resType)].dimLens
			cstr_array = ((ctypes.c_char * dims[1]) * dims[0])()
			err = ncdll.nc_get_var(ncid, id, ctypes.byref(cstr_array))
			if err:
				if ncid.value > 0:
					ncdll.nc_close(ncid)
				return True, "ERROR: error data from netcdf. Error: {0}".format(NC_Error.message(err))
			try:
				self.ID = [x.value.strip().decode('utf-8') for x in cstr_array]
			except UnicodeDecodeError:  # 1D loss headers are written at end of TUFLOW and if unclean exit don't bother loading
				return False, ""
		else:
			return False, ""
		self.Header = ['Timestep', 'Time'] + self.ID[:]
		self.nLocs = dims[0]
		if resName == 'losses_1d':
			self.lossNames = self.ID[:]
			self.ID.clear()
			self.Header = self.Header[:2]
			nCol = 1
			i = 1
			# loop and find channel ids
			for id in self.lossNames[:]:
				i += 1
				rx = re.search(r"LC\s", id, re.IGNORECASE)
				a = id[rx.span()[1]:]
				self.ID.append(a)
				self.Header.append(a)
				if a == self.Header[i - 1]:
					nCol += 1
				elif i > 2:  # first column with element names
					self.nCols.append(nCol)
					self.uID.append(self.Header[i - 1])
					nCol = 1
				if i - 1 == len(self.lossNames):  # last column
					self.nCols.append(nCol)
					self.uID.append(self.Header[i - 1])

		# times
		if "time" in [x.name for x in ncVars]:
			id = ncVars[[x.name for x in ncVars].index("time")].id
			dims = ncVars[[x.name for x in ncVars].index("time")].dimLens
			cdouble_array = ( ctypes.c_double * dims[0] )()
			err = ncdll.nc_get_var(ncid, id, ctypes.byref(cdouble_array))
			if err:
				if ncid.value > 0:
					ncdll.nc_close(ncid)
				return True, "ERROR: error data from netcdf. Error: {0}".format(NC_Error.message(err))
			self.nVals = dims[0]
			v = [x + 1 for x in range(self.nVals)]
			values.append(v)
			v = [x for x in cdouble_array]
			values.append(v)
		else:
			return False, ""

		# values
		if resName in [x.name for x in ncVars]:
			id = ncVars[[x.name for x in ncVars].index(resName)].id
			dims = ncVars[[x.name for x in ncVars].index(resName)].dimLens
			if "flow_regime_1d" in resName:
				cstr_array =  ( ( ( ctypes.c_char * dims[2] ) * dims[1] ) * dims[0] )()
				err = ncdll.nc_get_var(ncid, id, ctypes.byref(cstr_array))
			else:
				cfloat_array = ( ( ctypes.c_float * dims[1] ) * dims[0] )()
				err = ncdll.nc_get_var(ncid, id, ctypes.byref(cfloat_array))
			if err:
				if ncid.value > 0:
					ncdll.nc_close(ncid)
				return True, "ERROR: error data from netcdf. Error: {0}".format(NC_Error.message(err))
			if "flow_regime_1d" in resName:
				for ch in cstr_array:
					v = []
					for x in ch:
						try:
							v.append(x.value.strip().decode('utf-8'))
						except UnicodeDecodeError:
							v.append("G")
					#v = [x.value.strip().decode('utf-8') for x in ch]
					values += [v]
				#v = [x[:] for x in cchar_array]
			else:
				v = [x[:] for x in cfloat_array]
				values += v
			values = numpy.transpose(numpy.array(values))
			null_array = values == self.null_data
			self.Values = numpy.ma.masked_array(values, null_array)
		else:
			return False, ""

		self.loaded = True

		return error, message


class Node_Max():
	"""
	Maximum values at nodes
	"""
	def __init__(self):
		self.ID = []
		self.HMax = []
		self.tHmax = []
		self.EMax = []
		self.nLocs = 0
		self.loaded = False

	def Load(self,fullpath):
		error = False
		message = ''
		hMax = True
		tHmax = True
		EMax = True
		try:
			with open(fullpath, 'r') as csvfile:
				reader = csv.reader(csvfile, delimiter=',', quotechar='"')
				header = next(reader)
				# find out what's in the file
				header = [element.upper() for element in header] # convert to upper just in case
				try:
					ind_H = header.index('HMAX')
				except:
					hMax = False
					self.HMax = None
				try:
					ind_tH = header.index('TIME HMAX')
				except:
					thMax = False
					self.tHmax = None
				try:
					ind_E = header.index('EMAX')
				except:
					EMax = False
					self.EMax = None

				#read remainder of file
				for row in reader:
					#print row
					self.ID.append(row[1])
					if hMax:
						try:
							self.HMax.append(float(row[ind_H]))
						except:
							self.HMax.append(float('Nan'))
					if tHmax:
						try:
							self.tHmax.append(float(row[ind_tH]))
						except:
							self.tHmax.append(float('Nan'))
					if EMax:
						try:
							self.EMax.append(float(row[ind_E]))
						except:
							self.EMax.append(float('Nan'))
			#close file
			csvfile.close()

		except IOError:
			message = 'Cannot find the following file: \n{0}'.format(fullpath)
			error = True
			return error, message
		except:
			message = 'ERROR - Error reading data from: '+fullpath
			error = True
			return error, message

		#normal end
		self.nLocs = len(self.ID)
		self.loaded = True
		return error, message

class Chan_Max():
	"""
	Maximum values at channels
	"""
	def __init__(self):
		self.ID = []
		self.QMax = []
		self.tQmax = []
		self.VMax = []
		self.tVmax = []
		self.nLocs = 0
		self.loaded = False

	def Load(self,fullpath):
		error = False
		message = ''
		qmax = True
		tqmax = True
		vmax = True
		tvmax = True
		try:
			with open(fullpath, 'r') as csvfile:
				reader = csv.reader(csvfile, delimiter=',', quotechar='"')
				header = next(reader)
				# find out what's in the file
				header = [element.upper() for element in header] # convert to upper just in case
				try:
					ind_Q = header.index('QMAX')
				except:
					qmax = False
					self.QMax = None
				try:
					ind_tQ = header.index('TIME QMAX')
				except:
					tqmax = False
					self.tQmax = None
				try:
					ind_V = header.index('VMAX')
				except:
					vmax = False
					self.VMax = None
				try:
					ind_tV = header.index('TIME VMAX')
				except:
					tvmax = False
					self.tVmax = None

				#read remainder of file
				for row in reader:
					#print row
					self.ID.append(row[1])
					if qmax:
						try:
							self.QMax.append(float(row[ind_Q]))
						except:
							self.QMax.append(float('Nan'))
					if tqmax:
						try:
							self.tQmax.append(float(row[ind_tQ]))
						except:
							self.tQmax.append(float('Nan'))
					if vmax:
						try:
							self.VMax.append(float(row[ind_V]))
						except:
							self.VMax.append(float('Nan'))
					if tvmax:
						try:
							self.tVmax.append(float(row[ind_tV]))
						except:
							self.tVmax.append(float('Nan'))

			# close file
			csvfile.close()
		except IOError:
			message = 'Cannot find the following file: \n{0}'.format(fullpath)
			error = True
			return error, message
		except:
			message = 'ERROR - Error reading header from: '+fullpath
			error = True
			return error, message

		# normal return
		self.nLocs = len(self.ID)
		self.loaded = True
		return error, message

class RL_P_Max():
	"""
	Maximum values at Reporting level points
	"""
	def __init__(self):
		self.ID = []
		self.HMax = []
		self.tHmax = []
		self.dHMax = []
		self.tdHmax = []
		self.Q = []
		self.nLocs = 0

	def Load(self,fullpath):
		error = False
		message = ''
		try:
			with open(fullpath, 'r') as csvfile:
				reader = csv.reader(csvfile, delimiter=',', quotechar='"')
				header = next(reader)
				for row in reader:
					#print row
					self.ID.append(row[1])
					try:
						self.HMax.append(float(row[2]))
					except:
						self.HMax.append(float('Nan'))
					try:
						self.tHmax.append(float(row[3]))
					except:
						self.tHmax.append(float('Nan'))
					try:
						self.dHMax.append(float(row[4]))
					except:
						self.dHMax.append(float('Nan'))
					try:
						self.tdHmax.append(float(row[5]))
					except:
						self.tdHmax.append(float('Nan'))
					try:
						self.Q.append(float(row[6]))
					except:
						self.Q.append(float('Nan'))
			#csvfile.close()
		except IOError:
			message = 'Cannot find the following file: \n{0}'.format(fullpath)
			error = True
			return error, message
		except:
			message = 'ERROR - Error reading header from: '+fullpath
			error = True
			return error, message
		if len(header)>7:
			error = True
			message = 'ERROR - More than seven columns in node maximums file: '+fullpath
			return error, message
		if not (header[2].upper()=='HMAX'):
			error = True
			message = 'ERROR - Expecting HMax in column 3 of file: '+fullpath
			return error, message
		if not (header[3].upper()=='TIME HMAX'):
			error = True
			message = 'ERROR - Expecting Time Hmax in column 4 of file: '+fullpath
			return error, message
		if not (header[4].upper()=='DHMAX'):
			error = True
			message = 'ERROR - Expecting dHmax in column 5 of file: '+fullpath
			return error, message
		if not (header[5].upper()=='TIME DHMAX'):
			error = True
			message = 'ERROR - Expecting Time dHmax in column 6 of file: '+fullpath
			return error, message
		self.nLocs = len(self.ID)
		return error, message

class RL_L_Max():
	"""
	Maximum values at Reporting level lines
	"""
	def __init__(self):
		self.ID = []
		self.QMax = []
		self.tQmax = []
		self.dQMax = []
		self.tdQmax = []
		self.H = []
		self.nLocs = 0

	def Load(self,fullpath):
		error = False
		message = ''
		try:
			with open(fullpath, 'r') as csvfile:
				reader = csv.reader(csvfile, delimiter=',', quotechar='"')
				header = next(reader)
				for row in reader:
					#print row
					self.ID.append(row[1])
					try:
						self.QMax.append(float(row[2]))
					except:
						self.QMax.append(float('Nan'))
					try:
						self.tQmax.append(float(row[3]))
					except:
						self.tQmax.append(float('Nan'))
					try:
						self.dQMax.append(float(row[4]))
					except:
						self.dQMax.append(float('Nan'))
					try:
						self.tdQmax.append(float(row[5]))
					except:
						self.tdQmax.append(float('Nan'))
					try:
						self.H.append(float(row[6]))
					except:
						self.H.append(float('Nan'))
			#csvfile.close()
		except IOError:
			message = 'Cannot find the following file: \n{0}'.format(fullpath)
			error = True
			return error, message
		except:
			message = 'ERROR - Error reading header from: '+fullpath
			error = True
			return error, message
		if len(header)>7:
			error = True
			message = 'ERROR - More than 7 columns RLL_Qmx file: '+fullpath
			return error, message
		if not (header[2].upper()=='QMAX'):
			error = True
			message = 'ERROR - Expecting HMax in column 3 of file: '+fullpath
			return error, message
		if not (header[3].upper()=='TIME QMAX'):
			error = True
			message = 'ERROR - Expecting Time Hmax in column 4 of file: '+fullpath
			return error, message
		if not (header[4].upper()=='DQMAX'):
			error = True
			message = 'ERROR - Expecting dHmax in column 5 of file: '+fullpath
			return error, message
		if not (header[5].upper()=='TIME DQMAX'):
			error = True
			message = 'ERROR - Expecting Time dHmax in column 6 of file: '+fullpath
			return error, message
		if not (header[6].upper()=='H'):
			error = True
			message = 'ERROR - Expecting H in column 7 of file: '+fullpath
			return error, message
		self.nLocs = len(self.ID)
		return error, message

class RL_R_Max():
	"""
	Maximum values at Reporting level regions
	"""
	def __init__(self):
		self.ID = []
		self.VolMax = []
		self.tVolMax = []
		self.dVolMax = []
		self.tdVolMax = []
		self.H = []
		self.nLocs = 0

	def Load(self,fullpath):
		error = False
		message = ''
		try:
			with open(fullpath, 'r') as csvfile:
				reader = csv.reader(csvfile, delimiter=',', quotechar='"')
				header = next(reader)
				for row in reader:
					#print row
					self.ID.append(row[1])
					try:
						self.VolMax.append(float(row[2]))
					except:
						self.VolMax.append(float('Nan'))
					try:
						self.tVolMax.append(float(row[3]))
					except:
						self.tVolMax.append(float('Nan'))
					try:
						self.dVolMax.append(float(row[4]))
					except:
						self.dVolMax.append(float('Nan'))
					try:
						self.tdVolMax.append(float(row[5]))
					except:
						self.tdVolMax.append(float('Nan'))
					try:
						self.H.append(float(row[6]))
					except:
						self.H.append(float('Nan'))
			#csvfile.close()
		except IOError:
			message = 'Cannot find the following file: \n{0}'.format(fullpath)
			error = True
			return error, message
		except:
			message = 'ERROR - Error reading header from: '+fullpath
			error = True
			return error, message
		if len(header)>7:
			error = True
			message = 'ERROR - More than 7 columns RLL_Volmx file: '+fullpath
			return error, message
		if not (header[2].upper()=='VOL MAX'):
			error = True
			message = 'ERROR - Expecting HMax in column 3 of file: '+fullpath
			return error, message
		if not (header[3].upper()=='TIME VOL MAX'):
			error = True
			message = 'ERROR - Expecting Time Hmax in column 4 of file: '+fullpath
			return error, message
		if not (header[4].upper()=='DVOLMAX'):
			error = True
			message = 'ERROR - Expecting dHmax in column 5 of file: '+fullpath
			return error, message
		if not (header[5].upper()=='TIME DVOLMAX'):
			error = True
			message = 'ERROR - Expecting Time dHmax in column 6 of file: '+fullpath
			return error, message
		if not (header[6].upper()=='H'):
			error = True
			message = 'ERROR - Expecting H in column 7 of file: '+fullpath
			return error, message
		self.nLocs = len(self.ID)
		return error, message

class NodeInfo():
	"""
	Node Info data class
	"""
	def __init__(self,fullpath):
		self.node_num = []
		self.node_name = []
		self.node_bed = []
		self.node_top = []
		self.node_nChan = []
		self.node_channels = []
		self.message = ''
		self.error = False
		try:
			with open(fullpath, 'r') as csvfile:
				reader = csv.reader(csvfile, delimiter=',', quotechar='"')
				header = next(reader)
				for (counter, row) in enumerate(reader):
					self.node_num.append(int(row[0]))
					self.node_name.append(row[1])
					try:
						self.node_bed.append(float(row[2]))
					except ValueError:
						self.error = True
						self.message = "ERROR reading in Node Bed Level in\n{0}\n[Node ID: {1}, level: {2}]".format(fullpath, row[1], row[2])
						return
					try:
						self.node_top.append(float(row[3]))
					except ValueError:
						self.error = True
						self.message = "ERROR reading in Node Top Level in\n{0}\n[Node ID: {1}, level: {2}]".format(fullpath, row[1], row[3])
						return
					try:
						self.node_nChan.append(int(row[4]))
					except ValueError:
						self.error = True
						self.message = "ERROR reading in Number of Channels in\n{0}\n[Node ID: {1}, nChannels: {2}]".format(fullpath, row[1], row[4])
						return
					chan_list = row[5:]
					if len(chan_list) != int(row[4]):
						if int(row[4]) != 0:
							print('ERROR - Number of channels connected to ID doesnt match. ID: ' + str(row[1]))
					else:
						self.node_channels.append(chan_list)
			csvfile.close()
		except IOError:
			self.message = 'Cannot find the following file: \n{0}'.format(fullpath)
			self.error = True
		except:
			self.message = 'ERROR reading file: \n{0}'.format(fullpath)
			self.error = True

class ChanInfo():
	"""
	Channel Info data class
	"""
	def __init__(self,fullpath):
		self.chan_num = []
		self.chan_name = []
		self.chan_US_Node = []
		self.chan_DS_Node = []
		self.chan_US_Chan = []
		self.chan_DS_Chan = []
		self.chan_Flags = []
		self.chan_Length = []
		self.chan_FormLoss = []
		self.chan_n = []
		self.chan_slope = []
		self.chan_US_Inv = []
		self.chan_DS_Inv = []
		self.chan_LBUS_Obv = []
		self.chan_RBUS_Obv = []
		self.chan_LBDS_Obv = []
		self.chan_RBDS_Obv = []
		self.chan_Blockage = []

		self.message = ''
		self.error = False
		try:
			with open(fullpath, 'r') as csvfile:
				reader = csv.reader(csvfile, delimiter=',', quotechar='"')
				header = next(reader)
				for (counter, row) in enumerate(reader):
					self.chan_num.append(int(row[0]))
					self.chan_name.append(row[1])
					self.chan_US_Node.append(row[2])
					self.chan_DS_Node.append(row[3])
					self.chan_US_Chan.append(row[4])
					self.chan_DS_Chan.append(row[5])
					self.chan_Flags.append(row[6])
					try:
						self.chan_Length.append(float(row[7]))
					except ValueError:
						# caused when tuflow outputs ****** for steep slopes
						self.chan_Length.append(0)
					try:
						self.chan_FormLoss.append(float(row[8]))
					except ValueError:
						# caused when tuflow outputs ****** for steep slopes
						self.chan_FormLoss.append(0)
					try:
						self.chan_n.append(float(row[9]))
					except ValueError:
						# caused when tuflow outputs ****** for steep slopes
						self.chan_n.append(0)
					try:
						self.chan_slope.append(float(row[10]))
					except ValueError:
						# caused when tuflow outputs ****** for steep slopes
						self.chan_slope.append(0)
					try:
						self.chan_US_Inv.append(float(row[11]))
					except ValueError:
						# caused when tuflow outputs ****** for steep slopes
						self.message = "ERROR reading in Channel Upstream Invert in\n{0}\n[Channel ID: {1}, invert: {2}]".format(fullpath, row[1], row[11])
						self.error = True
						return
					try:
						self.chan_DS_Inv.append(float(row[12]))
					except ValueError:
						# caused when tuflow outputs ****** for steep slopes
						self.message = "ERROR reading in Channel Downstream Invert in\n{0}\n[Channel ID: {1}, invert: {2}]".format(fullpath, row[1], row[12])
						self.error = True
						return
					try:
						self.chan_LBUS_Obv.append(float(row[13]))
					except ValueError:
						# caused when tuflow outputs ****** for steep slopes
						self.chan_LBUS_Obv.append(0)
					try:
						self.chan_RBUS_Obv.append(float(row[14]))
					except ValueError:
						# caused when tuflow outputs ****** for steep slopes
						self.chan_RBUS_Obv.append(0)
					try:
						self.chan_LBDS_Obv.append(float(row[15]))
					except ValueError:
						# caused when tuflow outputs ****** for steep slopes
						self.chan_LBDS_Obv.append(0)
					try:
						self.chan_RBDS_Obv.append(float(row[16]))
					except ValueError:
						# caused when tuflow outputs ****** for steep slopes
						self.chan_RBDS_Obv.append(0)
					try:
						self.chan_Blockage.append(float(row[17]))
					except ValueError:
						# caused when tuflow outputs ****** for steep slopes
						self.chan_Blockage.append(0)
			self.nChan = counter+1
			csvfile.close()
		except IOError:
			self.message = 'Cannot find the following file: \n{0}'.format(fullpath)
			self.error = True
		except:
			self.message = 'ERROR reading file: \n{0}'.format(fullpath)
			self.error = True

# results class
class ResData():
	"""
	ResData class for reading and processing results
	"""

	def getResAtTime(self, id, dom, res, time, time_interpolate='previous'):
		"""

		"""

		if time == -99999:
			found, data, message = self.getMAXData(id, dom, res)
			if found:
				return data[1]
		else:
			if time not in self.times:
				if time_interpolate == 'previous':
					t = list(filter(lambda x: x < time, self.times))
					if t:
						time = t[-1]
					else:
						return None
				else:
					return None

			i = self.times.tolist().index(time)
			found, ydata, message = self.getTSData(id, dom, res, None)
			if found:
				return ydata[i]

		return None

	def getTSData(self, id, dom, res, geom):
		message = None
		if (dom.upper() == "1D"):
			if(res.upper() in ("H", "H_", "LEVEL","LEVELS")):
				if self.Data_1D.H.loaded:
					try:
						ind = self.Data_1D.H.Header.index(id)
						data = self.Data_1D.H.Values[:,ind]
						self.times = self.Data_1D.H.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 1D H with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 1D Water Level Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("E", "E_", "ENERGY LEVEL","ENERGY LEVELS")):
				if self.Data_1D.E.loaded:
					try:
						ind = self.Data_1D.E.Header.index(id)
						data = self.Data_1D.E.Values[:,ind]
						self.times = self.Data_1D.E.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 1D E with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 1D Energy Level Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("Q","Q_","FLOW","FLOWS")):
				if self.Data_1D.Q.loaded:
					try:
						ind = self.Data_1D.Q.Header.index(id)
						data = self.Data_1D.Q.Values[:,ind]
						self.times = self.Data_1D.Q.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 1D Q with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 1D Flow Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("V","V_","VELOCITY","VELOCITIES")):
				if self.Data_1D.V.loaded:
					try:
						ind = self.Data_1D.V.Header.index(id)
						data = self.Data_1D.V.Values[:,ind]
						return True, data, message
					except:
						message = 'Data not found for 1D V with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 1D Velocity Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("A","A_","FLOW AREA","FLOW AREAS")):
				if self.Data_1D.A.loaded:
					try:
						ind = self.Data_1D.A.Header.index(id)
						data = self.Data_1D.A.Values[:,ind]
						self.times = self.Data_1D.A.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 1D A with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 1D Flow Area Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("US_H", "US LEVELS")):
				chan_list = tuple(self.Channels.chan_name)
				ind = chan_list.index(str(id))
				a = str(self.Channels.chan_US_Node[ind])
				try:
					ind = self.Data_1D.H.Header.index(a)
				except:
					message = 'Unable to find US node: ',+a+' for channel '+ id
					return False, [0.0], message
				try:
					data = self.Data_1D.H.Values[:,ind]
					self.times = self.Data_1D.H.Values[:,1]
					return True, data, message
				except:
					message = 'Data not found for 1D H with ID: '+a
					return False, [0.0], message
			elif(res.upper() in ("DS_H","DS LEVELS")):
				chan_list = tuple(self.Channels.chan_name)
				ind = chan_list.index(str(id))
				a = str(self.Channels.chan_DS_Node[ind])
				try:
					ind = self.Data_1D.H.Header.index(a)
				except:
					message = 'Unable to find DS node: ',+a+' for channel '+ id
					return False, [0.0], message
				try:
					data = self.Data_1D.H.Values[:,ind]
					self.times = self.Data_1D.H.Values[:,1]
					return True, data, message
				except:
					message = 'Data not found for 1D H with ID: '+a
					return False, [0.0], message
			elif (res.upper() in ("MB")):
				if self.Data_1D.MB.loaded:
					try:
						ind = self.Data_1D.MB.Header.index(id)
						data = self.Data_1D.MB.Values[:, ind]
						return True, data, message
					except:
						message = 'Data not found for 1D MB with ID: ' + id
						return False, [0.0], message
				else:
					message = 'No 1D Velocity Data loaded for: ' + self.displayname
					return False, [0.0], message
			elif (res.upper() in ("FLOW REGIME", "NF", "CF")):
				if self.Data_1D.NF.loaded or self.Data_1D.CF.loaded:
					try:
						if id in self.Data_1D.NF.Header:
							ind = self.Data_1D.NF.Header.index(id)
							data = self.Data_1D.NF.Values[:, ind]
							return True, data, message
						elif id in self.Data_1D.CF.Header:
							ind = self.Data_1D.CF.Header.index(id)
							data = self.Data_1D.CF.Values[:, ind]
							return True, data, message
						else:
							return True, [0.0], message
					except:
						message = 'Data not found for 1D Regime with ID: ' + id
						return False, [0.0], message
				else:
					message = 'No 1D Regime Data loaded for: ' + self.displayname
					return False, [0.0], message
			elif (res.upper() in ("LOSSES", "CL")):
				if self.Data_1D.CL.loaded:
					try:
						ind = self.Data_1D.CL.Header.index(id)
						iun = self.Data_1D.CL.uID.index(id)  # index unique name
						nCol = self.Data_1D.CL.nCols[iun]  # number of columns associated with element losses
						data = self.Data_1D.CL.Values[:, ind:ind + nCol]
						return True, data, message
					except:
						message = 'Data not found for 1D Losses with ID: ' + id
						return False, [0.0], message
				else:
					message = 'No 1D Losses Data loaded for: ' + self.displayname
					return False, [0.0], message
			else:
				message = 'Warning - Expecting unexpected data type for 1D: '+res
				return False, [0.0], message

		elif (dom.upper() == "2D"):
			if(res.upper() in  ("H", "H_", "LEVEL","LEVELS","POINT WATER LEVEL")):
				if self.Data_2D.H.loaded:
					try:
						ind = self.Data_2D.H.Header.index(id)
						data = self.Data_2D.H.Values[:,ind]
						self.times = self.Data_2D.H.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D H with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Level Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("Q","Q_","FLOW","FLOWS")):
				if self.Data_2D.Q.loaded:
					try:
						ind = self.Data_2D.Q.Header.index(id)
						data = self.Data_2D.Q.Values[:,ind]
						self.times = self.Data_2D.Q.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D Q with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Flow Data loaded for: '+self.displayname
					return False, [0.0], message
			elif (res.upper() in ("X FLOW")):
				if self.Data_2D.Qx.loaded:
					try:
						ind = self.Data_2D.Qx.Header.index(id)
						data = self.Data_2D.Qx.Values[:, ind]
						self.times = self.Data_2D.Qx.Values[:, 1]
						return True, data, message
					except:
						message = 'Data not found for 2D Qx with ID: ' + id
						return False, [0.0], message
				else:
					message = 'No 2D X-Flow Data loaded for: ' + self.displayname
					return False, [0.0], message
			elif (res.upper() in ("Y FLOW")):
				if self.Data_2D.Qy.loaded:
					try:
						ind = self.Data_2D.Qy.Header.index(id)
						data = self.Data_2D.Qy.Values[:, ind]
						self.times = self.Data_2D.Qy.Values[:, 1]
						return True, data, message
					except:
						message = 'Data not found for 2D Qy with ID: ' + id
						return False, [0.0], message
				else:
					message = 'No 2D Y-Flow Data loaded for: ' + self.displayname
					return False, [0.0], message
			elif(res.upper() in ("V","V_","VELOCITY","VELOCITIES")):
				if self.Data_2D.V.loaded:
					try:
						ind = self.Data_2D.V.Header.index(id)
						data = self.Data_2D.V.Values[:,ind]
						self.times = self.Data_2D.V.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D Q with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Velocity Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("GL", "GAUGE LEVEL")):
				if self.Data_2D.GL.loaded:
					try:
						ind = self.Data_2D.GL.Header.index(id)
						data = self.Data_2D.GL.Values[:,ind]
						self.times = self.Data_2D.GL.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D GL with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Gauge Level Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("QA", "FLOW AREA")):
				if self.Data_2D.QA.loaded:
					try:
						ind = self.Data_2D.QA.Header.index(id)
						data = self.Data_2D.QA.Values[:,ind]
						self.times = self.Data_2D.QA.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D QA with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Flow Area Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("QS", "STRUCTURE FLOW")):
				if self.Data_2D.QS.loaded:
					try:
						ind = self.Data_2D.QS.Header.index(id)
						data = self.Data_2D.QS.Values[:,ind]
						self.times = self.Data_2D.QS.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D QS with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Structure Flow Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("HU", "US LEVELS")):
				if self.Data_2D.HUS.loaded:
					try:
						ind = self.Data_2D.HUS.Header.index(id)
						data = self.Data_2D.HUS.Values[:,ind]
						self.times = self.Data_2D.HUS.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D HU with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D U/S Structure Water Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("HD", "DS LEVELS")):
				if self.Data_2D.HDS.loaded:
					try:
						ind = self.Data_2D.HDS.Header.index(id)
						data = self.Data_2D.HDS.Values[:,ind]
						self.times = self.Data_2D.HDS.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D HD with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D D/S Structure Water Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("VX")):
				if self.Data_2D.Vx.loaded:
					try:
						ind = self.Data_2D.Vx.Header.index(id)
						data = self.Data_2D.Vx.Values[:,ind]
						self.times = self.Data_2D.Vx.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D Vx with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D V-X Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("VY")):
				if self.Data_2D.Vy.loaded:
					try:
						ind = self.Data_2D.Vy.Header.index(id)
						data = self.Data_2D.Vy.Values[:,ind]
						self.times = self.Data_2D.Vy.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D Vy with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D V-Y Data loaded for: '+self.displayname
					return False, [0.0], message
			elif (res.upper() in ("VU")):
				if self.Data_2D.Vu.loaded:
					try:
						ind = self.Data_2D.Vu.Header.index(id)
						data = self.Data_2D.Vu.Values[:, ind]
						self.times = self.Data_2D.Vu.Values[:, 1]
						return True, data, message
					except:
						message = 'Data not found for 2D Vu with ID: ' + id
						return False, [0.0], message
				else:
					message = 'No 2D Vu Data loaded for: ' + self.displayname
					return False, [0.0], message
			elif (res.upper() in ("VV")):
				if self.Data_2D.Vv.loaded:
					try:
						ind = self.Data_2D.Vv.Header.index(id)
						data = self.Data_2D.Vv.Values[:, ind]
						self.times = self.Data_2D.Vv.Values[:, 1]
						return True, data, message
					except:
						message = 'Data not found for 2D Vv with ID: ' + id
						return False, [0.0], message
				else:
					message = 'No 2D Vv Data loaded for: ' + self.displayname
					return False, [0.0], message
			elif (res.upper() in ("VA")):
				if self.Data_2D.VA.loaded:
					try:
						ind = self.Data_2D.VA.Header.index(id)
						data = self.Data_2D.VA.Values[:, ind]
						self.times = self.Data_2D.VA.Values[:, 1]
						return True, data, message
					except:
						message = 'Data not found for 2D VA with ID: ' + id
						return False, [0.0], message
				else:
					message = 'No 2D Vv Data loaded for: ' + self.displayname
					return False, [0.0], message
			elif(res.upper() in ("INTEGRAL FLOW","FLOW INTEGRAL")):
				if self.Data_2D.QI.loaded:
					try:
						ind = self.Data_2D.QI.Header.index(id)
						data = self.Data_2D.QI.Values[:,ind]
						self.times = self.Data_2D.QI.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D QI with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Integral Flow Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("HAVG","AVERAGE LEVEL", "AVERAGE WATER LEVEL")):
				if self.Data_2D.HAvg.loaded:
					try:
						ind = self.Data_2D.HAvg.Header.index(id)
						data = self.Data_2D.HAvg.Values[:,ind]
						self.times = self.Data_2D.HAvg.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D HAvg with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Average Water Level Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("HMAX","MAX LEVEL", "MAX WATER LEVEL")):
				if self.Data_2D.HMax.loaded:
					try:
						ind = self.Data_2D.HMax.Header.index(id)
						data = self.Data_2D.HMax.Values[:,ind]
						self.times = self.Data_2D.HMax.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D HMax with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Max Water Level Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("QIN","FLOW INTO REGION", "FLOW INTO")):
				if self.Data_2D.QIn.loaded:
					try:
						ind = self.Data_2D.QIn.Header.index(id)
						data = self.Data_2D.QIn.Values[:,ind]
						self.times = self.Data_2D.QIn.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D QIn with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Flow into Region Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("QOUT","FLOW OUT OF REGION", "FLOW OUT")):
				if self.Data_2D.QOut.loaded:
					try:
						ind = self.Data_2D.QOut.Header.index(id)
						data = self.Data_2D.QOut.Values[:,ind]
						self.times = self.Data_2D.QOut.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D QOut with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Flow out of Region Data loaded for: '+self.displayname
					return False, [0.0], message

			elif(res.upper() in ("VOL","VOLUME")):
				if self.Data_2D.Vol.loaded:
					try:
						ind = self.Data_2D.Vol.Header.index(id)
						data = self.Data_2D.Vol.Values[:,ind]
						self.times = self.Data_2D.Vol.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D Vol with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Volume Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("SS","SINK/SOURCE")):
				if self.Data_2D.SS.loaded:
					try:
						ind = self.Data_2D.SS.Header.index(id)
						data = self.Data_2D.SS.Values[:,ind]
						self.times = self.Data_2D.SS.Values[:,1]
						return True, data, message
					except:
						message = 'Data not found for 2D SS with ID: '+id
						return False, [0.0], message
				else:
					message = 'No 2D Sink/Source Data loaded for: '+self.displayname
					return False, [0.0], message
			else:
				message = 'Warning - Expecting Q, V, H, GL, QA, Vx or Vy for 2D data type.'
				return False, [0.0], message
		if (dom.upper() == "RL"):
			if(res.upper() in  ("H", "H_", "LEVEL","LEVELS","POINT WATER LEVEL","WATER LEVEL")):
				try:
					ind = self.Data_RL.H_P.Header.index(id)
					data = self.Data_RL.H_P.Values[:,ind]
					self.times = self.Data_RL.H_P.Values[:,1]
					return True, data, message
				except:
					message = 'Data not found for RL point with ID: '+id
					return False, [0.0], message
			elif(res.upper() in ("Q","Q_","FLOW","FLOWS")):
				try:
					ind = self.Data_RL.Q_L.Header.index(id)
					data = self.Data_RL.Q_L.Values[:,ind]
					self.times = self.Data_RL.Q_L.Values[:,1]
					return True, data, message
				except:
					message = 'Data not found for RL line with ID: '+id
					return False, [0.0], message
			elif(res.upper() in ("VOL","VOLUME","VOLUMES")):
				try:
					ind = self.Data_RL.Vol_R.Header.index(id)
					data = self.Data_RL.Vol_R.Values[:,ind]
					self.times = self.Data_RL.Vol_R.Values[:,1]
					return True, data, message
				except:
					message = 'Data not found for RL Region with ID: '+id
					return False, [0.0], message
			else:
				message = 'Warning - Expecting Q, H or Vol for RL data type.'
				return False, [0.0], message
		else:
			message = 'ERROR - Expecting model domain to be 1D or 2D.'
			return False, [0.0], message

	def getMAXData(self, id, dom, res):
		message = None
		if (dom.upper() == "1D"):
			if(res.upper() in ("H", "H_", "LEVEL","LEVELS")):
				if self.Data_1D.Node_Max.loaded:
					try:
						ind = self.Data_1D.Node_Max.ID.index(id)
						y = self.Data_1D.Node_Max.HMax[ind]
						x = self.Data_1D.Node_Max.tHmax[ind]
						return True, [x, y], message
					except:
						message = 'Data not found for maximum 1D H with ID: '+id
						return False, [0.0], message
				else:
					message = 'No maximum 1D Water Level Data loaded for: '+self.displayname
					return False, [0.0], message
			elif (res.upper() in ("E", "E_", "ENERGY LEVEL", "ENERGY LEVELS")):
				if self.Data_1D.Node_Max.loaded:
					try:
						ind = self.Data_1D.Node_Max.ID.index(id)
						y = self.Data_1D.Node_Max.EMax[ind]
						x = self.Data_1D.Node_Max.tHmax[ind]
						return True, [x, y], message
					except:
						message = 'Data not found for maximum 1D E with ID: ' + id
						return False, [0.0], message
				else:
					message = 'No maximum 1D Energy Level Data loaded for: ' + self.displayname
					return False, [0.0], message
			elif(res.upper() in ("Q","Q_","FLOW","FLOWS")):
				if self.Data_1D.Chan_Max.loaded:
					try:
						ind = self.Data_1D.Chan_Max.ID.index(id)
						y = self.Data_1D.Chan_Max.QMax[ind]
						x = self.Data_1D.Chan_Max.tQmax[ind]
						return True, [x, y], message
					except:
						message = 'Data not found for maximum 1D Q with ID: '+id
						return False, [0.0], message
				else:
					message = 'No maximum 1D Flow Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("V","V_","VELOCITY","VELOCITIES")):
				if self.Data_1D.Chan_Max.loaded:
					try:
						ind = self.Data_1D.Chan_Max.ID.index(id)
						y = self.Data_1D.Chan_Max.VMax[ind]
						x = self.Data_1D.Chan_Max.tVmax[ind]
						return True, [x, y], message
					except:
						message = 'Data not found for maximum 1D V with ID: '+id
						return False, [0.0], message
				else:
					message = 'No maximum 1D Velocity Data loaded for: '+self.displayname
					return False, [0.0], message
			elif(res.upper() in ("US_H", "US LEVELS")):
				chan_list = tuple(self.Channels.chan_name)
				ind = chan_list.index(str(id))
				a = str(self.Channels.chan_US_Node[ind])
				try:
					ind = self.Data_1D.Node_Max.ID.index(a)
				except:
					message = 'Unable to find US node: ',+a+' for channel '+ id
					return False, [0.0], message
				try:
					y = self.Data_1D.Node_Max.HMax[ind]
					x = self.Data_1D.Node_Max.tHmax[ind]
					return True, [x, y], message
				except:
					message = 'Data not found for maximum 1D H with ID: '+a
					return False, [0.0], message
			elif(res.upper() in ("DS_H","DS LEVELS")):
				chan_list = tuple(self.Channels.chan_name)
				ind = chan_list.index(str(id))
				a = str(self.Channels.chan_DS_Node[ind])
				try:
					ind = self.Data_1D.Node_Max.ID.index(a)
				except:
					message = 'Unable to find DS node: ',+a+' for channel '+ id
					return False, [0.0], message
				try:
					y = self.Data_1D.Node_Max.HMax[ind]
					x = self.Data_1D.Node_Max.tHmax[ind]
					return True, [x, y], message
				except:
					message = 'Data not found for maximum 1D H with ID: '+a
					return False, [0.0], message
			elif (res.upper() in ("A", "A_", "FLOW AREA", "FLOW AREAS")):
				if self.Data_1D.Chan_Max.loaded:
					try:
						ind = self.Data_1D.Chan_Max.ID.index(id)
						y = self.Data_1D.Chan_Max.HMax[ind]
						x = self.Data_1D.Chan_Max.tHmax[ind]
						return True, [x, y], message
					except:
						message = 'Data not found for maximum 1D A with ID: ' + id
						return False, [0.0], message
				else:
					message = 'No maximum 1D Flow Area Data loaded for: ' + self.displayname
					return False, [0.0], message
			else:
				message = 'Warning - Expecting unexpected data type for 1D: '+res
				return False, [0.0], message

		else:
			message = 'ERROR - Expecting model domain to be 1D.'
			return False, [0.0], message

	def LP_getConnectivity(self,id1,id2):
		#print('determining LP connectivity')
		message = None
		error = False
		self.LP.chan_list = []
		if (id2 == None): # only one channel selected
			finished = False
			i = 0
			chan_list = tuple(self.Channels.chan_name)
			try:
				ind1 = chan_list.index(str(id1))
			except:
				#QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(id1)))
				#print('ERROR - ID not found: ' + str(id1))
				message = 'ERROR - ID not found: ' + str(id1)
				error = True
				return error, message
			self.LP.chan_list = [id1]
			self.LP.chan_index = [ind1]
			self.LP.node_list = [(self.Channels.chan_US_Node[ind1])]
			self.LP.node_list.append(self.Channels.chan_DS_Node[ind1])
			id = ind1
			while not finished:
				i = i + 1
				chan = self.Channels.chan_DS_Chan[id]
				if(chan=='------'):
					finished = True
				else:
					self.LP.chan_list.append(chan)
					try:
						id = self.Channels.chan_name.index(chan)
						self.LP.chan_index.append(id)
						self.LP.node_list.append(self.Channels.chan_DS_Node[id])
					except:
						error = True
						message = 'ERROR - Unable to process channel: '+chan
						return error, message
			if not error:
				self.LP.connected = True
			return error, message

		else: # two channels selected (check for more than two in main routine)
			finished = False
			found = False
			i = 0
			chan_list = tuple(self.Channels.chan_name)
			# check 1st ID exists
			try:
				ind1 = chan_list.index(str(id1))
			except:
				error = True
				message = 'ERROR - ID not found: '+str(id1)
				return error, message
			# check 2nd ID exists
			try:
				ind2 = chan_list.index(str(id2))
			except:
				#QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(id2)))
				error = True
				message = 'ERROR - ID not found: '+str(id2)
				return error, message
			# assume ID2 is downstream of ID1
			endchan = id2
			self.LP.chan_list = [id1]
			self.LP.chan_index = [ind1]
			self.LP.node_list = [(self.Channels.chan_US_Node[ind1])]
			self.LP.node_list.append(self.Channels.chan_DS_Node[ind1])
			id = ind1
			while not finished:
				i = i + 1
				chan = self.Channels.chan_DS_Chan[id]
				if(chan=='------'):
					finished = True
				elif(chan==endchan):
					found = True
					finished = True
					self.LP.chan_list.append(chan)
					try:
						id = self.Channels.chan_name.index(chan)
						self.LP.chan_index.append(id)
						self.LP.node_list.append(self.Channels.chan_DS_Node[id])
					except:
						error = True
						message = 'ERROR - Unable to process channel: '+chan
						return error, message
				else:
					self.LP.chan_list.append(chan)
					try:
						id = self.Channels.chan_name.index(chan)
						self.LP.chan_index.append(id)
						self.LP.node_list.append(self.Channels.chan_DS_Node[id])
					except:
						error = True
						message = 'ERROR - ID not found: '+str(id)
						return error, message

			if not (found): # id2 is not downstream of 1d1, reverse direction and try again...
				#QMessageBox.information(iface.mainWindow(), "DEBUG", "reverse direction and try again")
				finished = False
				found = False
				i = 0
				endchan = id1
				self.LP.chan_list = [id2]
				self.LP.chan_index = [ind2]
				self.LP.node_list = [(self.Channels.chan_US_Node[ind2])]
				self.LP.node_list.append(self.Channels.chan_DS_Node[ind2])
				id = ind2
				while not finished:
					i = i + 1
					chan = self.Channels.chan_DS_Chan[id]
					if(chan=='------'):
						finished = True
					elif(chan==endchan):
						found = True
						finished = True
						self.LP.chan_list.append(chan)
						try:
							id = self.Channels.chan_name.index(chan)
							self.LP.chan_index.append(id)
							self.LP.node_list.append(self.Channels.chan_DS_Node[id])
						except:
							error = True
							message = 'ERROR - Unable to process channel: '+chan
							return error, message
					else:
						self.LP.chan_list.append(chan)
						try:
							id = self.Channels.chan_name.index(chan)
							self.LP.chan_index.append(id)
							self.LP.node_list.append(self.Channels.chan_DS_Node[id])
						except:
							error = True
							message = 'ERROR - Unable to process channel: '+chan
							return error, message
			if not (found): # id1 and 1d2 are not connected
				error = True
				message = 'Channels ' +id1 + ' and '+id2+' are not connected'
				return error, message
			else:
				if not error:
					self.LP.connected = True
			return error, message

	def LP_getStaticData(self):
		# get the channel and node properties length, elevations etc doesn't change with results
		print('Getting static data for LP')
		error = False
		message = None
		if (len(self.LP.chan_index)<1):
			error = True
			message = 'No LP channel data exists - Use .getLP_Connectivity to generate'
			return error, message

		# node info
		self.LP.node_bed = []
		self.LP.node_top = []
		self.LP.H_nd_index = []
		self.LP.node_index = []
		self.LP.Hmax = []
		self.LP.Emax = []
		self.LP.tHmax = []
		#long profile adverse grades
		self.LP.adverseH.nLocs = 0
		self.LP.adverseH.chainage = []
		self.LP.adverseH.node = []
		self.LP.adverseH.elevation = []
		self.LP.adverseE.nLocs = 0
		self.LP.adverseE.chainage = []
		self.LP.adverseE.node = []
		self.LP.adverseE.elevation = []

		#for nd in self.LP.node_list:
		#	try: #get node index and elevations
		#		ind = self.nodes.node_name.index(nd)
		#		self.LP.node_index.append(ind)
		#		self.LP.node_bed.append(self.nodes.node_bed[ind])
		#		self.LP.node_top.append(self.nodes.node_top[ind])
		#	except:
		#		error = True
		#		message = 'Unable to find node in _Nodes.csv file. Node: '+nd
		#		return error, message
		#	try: #get index to data in 1d_H.csv used when getting temporal data
		#		ind = self.Data_1D.H.Header.index(nd)
		#		self.LP.H_nd_index.append(ind)
		#	except:
		#		error = True
		#		message = 'Unable to find node in _1d_H.csv for node: '+nd
		#		return error, message
		#	try:
		#		ind = self.Data_1D.Node_Max.ID.index(nd)
		#		if self.Data_1D.Node_Max.HMax:
		#			self.LP.Hmax.append(self.Data_1D.Node_Max.HMax[ind])
		#		if self.Data_1D.Node_Max.EMax:
		#			self.LP.Emax.append(self.Data_1D.Node_Max.EMax[ind])
		#		if self.Data_1D.Node_Max.tHmax:
		#			self.LP.tHmax.append(self.Data_1D.Node_Max.tHmax[ind])
		#	except:
		#		error = True
		#		message = 'Unable to get maximum for node: '+nd
		#		return error, message
		#											
		#				  
        #
		#if len(self.LP.Hmax) == 0:
		#	self.LP.Hmax = None
		#if len(self.LP.Emax) == 0:
		#	self.LP.Emax = None
		#if len(self.LP.tHmax) == 0:
		#	self.LP.tHmax = None
		# channel info
		self.LP.dist_nodes = [0.0] # nodes only
		self.LP.dist_chan_inverts = [0.0] # at each channel end (no nodes)
		#self.LP.dist_inverts = [0.0] # nodes and channel ends
		#self.LP.chan_inv = [0.0]
		#self.LP.chan_LB = [0.0]
		#self.LP.chan_RB = [0.0]
		self.LP.dist_chan_inverts = [] # at each channel end (no nodes)
		self.LP.dist_inverts = [0.0] # nodes and channel ends
		self.LP.chan_inv = []
		self.LP.chan_LB = []
		self.LP.chan_RB = []
		self.LP.culv_verts = []

		for i, chan_index in enumerate(self.LP.chan_index):
			#length of current channel
			chan_len = self.Channels.chan_Length[chan_index] # length of current channel

			# distance at nodes
			cur_len = self.LP.dist_nodes[len(self.LP.dist_nodes)-1] #current length at node
			self.LP.dist_nodes.append(cur_len+chan_len)

			#distance at inverts
			if len(self.LP.dist_chan_inverts) == 0:
				cur_len = 0.
			else:
				cur_len = self.LP.dist_chan_inverts[len(self.LP.dist_chan_inverts)-1] #current length at invert locations
			self.LP.dist_chan_inverts.append(cur_len+0.0001) # dist for upstream invert
			new_len = cur_len + chan_len
			self.LP.dist_chan_inverts.append(new_len-0.0001) #dist for downstream invert

			#distance at both inverts and nodes
			cur_len = self.LP.dist_inverts[len(self.LP.dist_inverts)-1] #current length at invert locations
			self.LP.dist_inverts.append(cur_len+0.0001) # dist for upstream invert
			new_len = cur_len + self.Channels.chan_Length[chan_index]
			self.LP.dist_inverts.append(new_len-0.0001) #dist for downstream invert
			self.LP.dist_inverts.append(new_len) #dist at next node

			#elevations at channel inverts, left and right obverts
			self.LP.chan_inv.append(self.Channels.chan_US_Inv[chan_index])
			self.LP.chan_LB.append(self.Channels.chan_LBUS_Obv[chan_index])
			self.LP.chan_RB.append(self.Channels.chan_RBUS_Obv[chan_index])
			self.LP.chan_inv.append(self.Channels.chan_DS_Inv[chan_index])
			self.LP.chan_LB.append(self.Channels.chan_LBDS_Obv[chan_index])
			self.LP.chan_RB.append(self.Channels.chan_RBDS_Obv[chan_index])

			#distance polygons for culverts
			x = []
			y = []
			c_type = self.Channels.chan_Flags[chan_index]
			if c_type == "R" or c_type == "C" or c_type == "I":
				x.append(self.LP.dist_chan_inverts[-2])
				x.append(self.LP.dist_chan_inverts[-1])
				x.append(self.LP.dist_chan_inverts[-1])
				x.append(self.LP.dist_chan_inverts[-2])
				y.append(self.LP.chan_inv[-2])
				y.append(self.LP.chan_inv[-1])
				y.append(self.LP.chan_LB[-1])
				y.append(self.LP.chan_LB[-2])
				verts = list(zip(x,y))
				self.LP.culv_verts.append(verts)
			else:
				self.LP.culv_verts.append(None)

		for i, nd in enumerate(self.LP.node_list):
			try: #get node index and elevations
				ind = self.nodes.node_name.index(nd)
				self.LP.node_index.append(ind)
				self.LP.node_bed.append(self.nodes.node_bed[ind])
				self.LP.node_top.append(self.nodes.node_top[ind])
			except:
				error = True
				message = 'Unable to find node in _Nodes.csv file. Node: '+nd
				return error, message
			try: #get index to data in 1d_H.csv used when getting temporal data
				ind = self.Data_1D.H.Header.index(nd)
				self.LP.H_nd_index.append(ind)
			except:
				error = True
				message = 'Unable to find node in _1d_H.csv for node: '+nd
				return error, message
			try:
				ind = self.Data_1D.Node_Max.ID.index(nd)
				if self.Data_1D.Node_Max.HMax:
					if i == 0:
						self.LP.Hmax.append(max(self.Data_1D.Node_Max.HMax[ind], self.LP.chan_inv[i]))
					elif i < len(self.LP.node_list) - 1:
						self.LP.Hmax.append(max(self.Data_1D.Node_Max.HMax[ind], self.LP.chan_inv[2*i-1]))
						self.LP.Hmax.append(max(self.Data_1D.Node_Max.HMax[ind], self.LP.chan_inv[2*i]))
					else:
						self.LP.Hmax.append(max(self.Data_1D.Node_Max.HMax[ind], self.LP.chan_inv[2*i-1]))
				if self.Data_1D.Node_Max.EMax:
					if i == 0:
						self.LP.Emax.append(max(self.Data_1D.Node_Max.EMax[ind], self.LP.chan_inv[i]))
					elif i < len(self.LP.node_list) - 1:
						self.LP.Emax.append(max(self.Data_1D.Node_Max.EMax[ind], self.LP.chan_inv[2*i-1]))
						self.LP.Emax.append(max(self.Data_1D.Node_Max.EMax[ind], self.LP.chan_inv[2*i]))
					else:
						self.LP.Emax.append(max(self.Data_1D.Node_Max.EMax[ind], self.LP.chan_inv[2*i-1]))
				if self.Data_1D.Node_Max.tHmax:
					if i== 0:
						self.LP.tHmax.append(self.Data_1D.Node_Max.tHmax[ind])
					elif i < len(self.LP.node_list) - 1:
						self.LP.tHmax.append(self.Data_1D.Node_Max.tHmax[ind])
						self.LP.tHmax.append(self.Data_1D.Node_Max.tHmax[ind])
					else:
						self.LP.tHmax.append(self.Data_1D.Node_Max.tHmax[ind])
			except:
				error = True
				message = 'Unable to get maximum for node: '+nd
				return error, message
				
		if len(self.LP.Hmax) == 0:
			self.LP.Hmax = None
		if len(self.LP.Emax) == 0:
			self.LP.Emax = None
		if len(self.LP.tHmax) == 0:
			self.LP.tHmax = None
		#get infor about pits
		self.LP.npits = int(0)
		self.LP.pit_dist = []
		self.LP.pit_z = []
		for i, nd_ind in enumerate(self.LP.node_index):
			nchan = self.nodes.node_nChan[nd_ind]
			chan_list = self.nodes.node_channels[nd_ind]
			for j in range(nchan):
				chan = chan_list[j]
				indC = self.Channels.chan_name.index(chan)
				usC = self.Channels.chan_US_Chan[indC]
				dsC = self.Channels.chan_DS_Chan[indC]
				if usC == "------" and dsC == "------": #channel is pit channel
					self.LP.npits = self.LP.npits + 1
					self.LP.pit_dist.append(self.LP.dist_nodes[i])
					self.LP.pit_z.append(self.Channels.chan_US_Inv[indC])

		#adverse gradient stuff
		try:
			if self.LP.Hmax: #none type if no values
				for i in range(1,len(self.LP.node_list)):
					dh = self.LP.Hmax[i] - self.LP.Hmax[i-1]
					if dh > 0:
						self.LP.adverseH.nLocs = self.LP.adverseH.nLocs + 1
						self.LP.adverseH.elevation.append(self.LP.Hmax[i])
						self.LP.adverseH.node.append(self.LP.node_list[i])
						self.LP.adverseH.chainage.append(self.LP.dist_nodes[i])
		except:
			error = True
			message = 'ERROR processing adverse gradients from LP'
			return error, message
		try:
			if self.LP.Emax: #none type if no values
				for i in range(1,len(self.LP.node_list)):
					dh = self.LP.Emax[i] - self.LP.Emax[i-1]
					if dh > 0:
						self.LP.adverseE.nLocs = self.LP.adverseE.nLocs + 1
						self.LP.adverseE.elevation.append(self.LP.Emax[i])
						self.LP.adverseE.node.append(self.LP.node_list[i])
						self.LP.adverseE.chainage.append(self.LP.dist_nodes[i])
		except:
			error = True
			message = 'ERROR processing adverse gradients from LP'
			return error, message

		#normal return
		self.LP.static = True
		return error, message

	def LP_getData(self,dat_type,time,dt_tol):

		error = False
		message = None
		dt_abs = abs(self.times - time)
		t_ind = dt_abs.argmin()
		if (self.times[t_ind] - time)>dt_tol:
			error = True
			message = 'ERROR - Closest time: '+str(self.times[t_ind])+' outside time search tolerance: '+str(dt_tol)
			return  error, message
		if dat_type == 'Water Level':
			self.LP.Hdata = []
			if not self.Data_1D.H.loaded:
				error = True
				message = 'ERROR - No water level data loaded.'
				return error, message
			for i, h_ind in enumerate(self.LP.H_nd_index):
				if i == 0:
					self.LP.Hdata.append(max(self.Data_1D.H.Values[t_ind,h_ind], self.LP.chan_inv[i]))
				elif i < len(self.LP.H_nd_index) - 1:
					self.LP.Hdata.append(max(self.Data_1D.H.Values[t_ind,h_ind], self.LP.chan_inv[2*i-1]))
					self.LP.Hdata.append(max(self.Data_1D.H.Values[t_ind,h_ind], self.LP.chan_inv[2*i]))
				else:
					self.LP.Hdata.append(max(self.Data_1D.H.Values[t_ind,h_ind], self.LP.chan_inv[2*i-1]))
		elif dat_type == 'Energy Level':
			self.LP.Edata = []
			if not self.Data_1D.E.loaded:
				error = True
				message = 'ERROR - No energy level data loaded.'
				return error, message
			for i, h_ind in enumerate(self.LP.H_nd_index):
				if i == 0:
					self.LP.Edata.append(max(self.Data_1D.E.Values[t_ind,h_ind], self.LP.chan_inv[i]))
				elif i < len(self.LP.H_nd_index) - 1:
					self.LP.Edata.append(max(self.Data_1D.E.Values[t_ind,h_ind], self.LP.chan_inv[2*i-1]))
					self.LP.Edata.append(max(self.Data_1D.E.Values[t_ind,h_ind], self.LP.chan_inv[2*i]))
				else:
					self.LP.Edata.append(max(self.Data_1D.E.Values[t_ind,h_ind], self.LP.chan_inv[2*i-1]))
		else:
			error = True
			message = 'ERROR - Only head or energy supported for LP temporal data'
			return  error, message

		return error, message

	def __init__(self):
		self.script_version = version
		self.filename = None
		self.fpath = None
		self.nTypes = 0
		self.Types = []
		self.LP = LP()
		self.Data_1D = Data_1D()
		self.Data_2D = Data_2D()
		self.Data_RL = Data_RL()
		self.GIS = GIS()
		self.formatVersion = None
		self.units = None
		self.displayname = None
		self.Index = None
		self.nodes = None #contains 1D node information if it
		self.Channels = None #contains 1D channel information if it

		# 2019 release additions for netcdf output format
		self.resFileFormat = "CSV"
		self.netcdf_fpath = ""
		self.netCDFLibPath = None
		self.netCDFLib = None
		self.ncdll = None
		self.ncid = ctypes.c_int(0)
		self.ncopen = None
		self.ncDims = []
		self.ncVars = []

	def getResFileFormat(self):
		try:
			data = numpy.genfromtxt(self.filename, dtype=str, delimiter="==")
		except:
			error = True
			message = 'ERROR - Unexpected error, Unable to load data.'
			return error, message

		for i in range(0, len(data)):
			tmp = data[i, 0]
			dat_type = tmp.strip()
			tmp = data[i, 1]
			rdata = tmp.strip()

			if dat_type == "Time Series Output Format":
				rtypes = rdata.split(" ")
				if "CSV" in rtypes:
					return "CSV"
				if "NC" in rtypes:
					return "NC"
				return None

		return "CSV"

	def Load(self, fname):
		error = False
		message = None
		self.filename = fname
		self.fpath = os.path.dirname(fname)

		if not os.path.exists(fname):
			error = True
			message = "ERROR - TPC file does not exist: {0}".format(fname)
			return error, message

		self.resFileFormat = self.getResFileFormat()
		if self.resFileFormat == "CSV":  # use CSV if available
			pass
		elif self.resFileFormat == "NC":
			self.loadNetCDFHeader()
		else:
			return True, "ERROR: Unrecognised TS file format."

		error, message = self.loadTPC()
		return error, message

	def loadNetCDFHeader(self):
		error = False
		message = None
		if self.netCDFLibPath is None:
			self.netCDFLib, self.netCDFLibPath = getNetCDFLibrary()
		else:
			if os.path.exists(self.netCDFLibPath):
				self.netCDFLib = "c_netcdf.dll"
		if self.netCDFLib is None:
			return True, "ERROR: Could not find a valid netcdf library"

		# find netcdf filepath
		try:
			data = numpy.genfromtxt(self.filename, dtype=str, delimiter="==")
		except:
			error = True
			message = 'ERROR - Unexpected error, Unable to load data.'
			return error, message
		for i in range(0, len(data)):
			tmp = data[i, 0]
			dat_type = tmp.strip()
			tmp = data[i, 1]
			rdata = tmp.strip()
			if dat_type == "NetCDF Time Series":
				self.netcdf_fpath = os.path.abspath(os.path.join(self.fpath, rdata))
				break
		if self.netcdf_fpath is None:
			return True, "ERROR: could not find netcdf file path reference"

		if self.netCDFLib == "python":
			self.loadNetCDFHeaderPython()
		elif self.netCDFLib == "c_netcdf.dll":
			self.loadNetCDFHeaderCDLL()

	def loadNetCDFHeaderPython(self):
		from netCDF4 import Dataset
		# open .nc file
		self.ncopen = Dataset(self.netcdf_fpath)

		# get dimension data
		for i, d in enumerate(self.ncopen.dimensions):
			dim = NcDim()
			self.ncDims.append(dim)

			dim.id = i
			dim.name = self.ncopen.dimensions[d].name
			dim.len = self.ncopen.dimensions[d].size

		# get variable data
		for i, v in enumerate(self.ncopen.variables):
			var = NcVar()
			self.ncVars.append(var)

			var.id = i
			var.name = self.ncopen.variables[v].name
			var.type = self.ncopen.variables[v].dtype
			var.nDims = self.ncopen.variables[v].ndim
			var.dimLens = self.ncopen.variables[v].shape
			var.dimNames = self.ncopen.variables[v].dimensions
			dimIds = []
			for dimName in var.dimNames:
				for dim in self.ncDims:
					if dim.name == dimName:
						dimIds.append(dim.id)
			var.dimIds = tuple(dimIds)

	def loadNetCDFHeaderCDLL(self):
		# open .nc file
		self.ncdll = ctypes.cdll.LoadLibrary(self.netCDFLibPath)
		file = ctypes.c_char_p(str.encode(self.netcdf_fpath))
		NC_NOWRITE = ctypes.c_int(0)
		ncidp = ctypes.pointer(ctypes.c_int())
		err = self.ncdll.nc_open(file, NC_NOWRITE, ncidp)
		if err:
			return True, "ERROR: error reading netcdf file. Error: {0}".format(NC_Error.message(err))

		# query netcdf to get number of dimensions and variables
		self.ncid = ncidp.contents
		ndimsp = ctypes.pointer(ctypes.c_int())
		nvarsp = ctypes.pointer(ctypes.c_int())
		nattsp = ctypes.pointer(ctypes.c_int())
		unlimdimidp = ctypes.pointer(ctypes.c_int())
		err = self.ncdll.nc_inq(self.ncid, ndimsp, nvarsp, nattsp, unlimdimidp)
		if err:
			if self.ncid.value > 0:
				self.ncdll.nc_close(self.ncid)
			return True, "ERROR: error reading netcdf file. Error: {0}".format(NC_Error.message(err))

		# get info on dimensions
		cstr_array = (ctypes.c_char * 256)()
		cint_p = ctypes.pointer(ctypes.c_int())
		for i in range(ndimsp.contents.value):
			dim = NcDim()
			self.ncDims.append(dim)

			# gets dimension name and length
			err = self.ncdll.nc_inq_dim(self.ncid, ctypes.c_int(i), ctypes.byref(cstr_array), cint_p)
			if err:
				if self.ncid.value > 0:
					self.ncdll.nc_close(self.ncid)
				return True, "ERROR: error getting netcdf dimensions. Error: {0}".format(NC_Error.message(err))

			dim.id = i
			dim.name = cstr_array.value.decode('utf-8')
			dim.len = cint_p.contents.value

		# get info on variables
		for i in range(nvarsp.contents.value):
			var = NcVar()
			self.ncVars.append(var)

			# id
			var.id = i

			# variable name
			err = self.ncdll.nc_inq_varname(self.ncid, ctypes.c_int(i), ctypes.byref(cstr_array))
			if err:
				if self.ncid.value > 0:
					self.ncdll.nc_close(self.ncid)
				return True, "ERROR: error getting netcdf variable names. Error: {0}".format(NC_Error.message(err))
			var.name = cstr_array.value.decode('utf-8')

			# variable data type
			err = self.ncdll.nc_inq_vartype(self.ncid, ctypes.c_int(i), cint_p)
			if err:
				if self.ncid.value > 0:
					self.ncdll.nc_close(self.ncid)
				return True, "ERROR: error getting netcdf variable types. Error: {0}".format(NC_Error.message(err))
			var.type = cint_p.contents.value

			# number of dimensions
			err = self.ncdll.nc_inq_varndims(self.ncid, ctypes.c_int(i), cint_p)
			if err:
				if self.ncid.value > 0:
					self.ncdll.nc_close(self.ncid)
				return True, "ERROR: error getting netcdf variable dimensions. Error: {0}".format(NC_Error.message(err))
			var.nDims = cint_p.contents.value

			# dimension information
			cint_array = (ctypes.c_int * var.nDims)()
			err = self.ncdll.nc_inq_vardimid(self.ncid, ctypes.c_int(i), ctypes.byref(cint_array))
			if err:
				if self.ncid.value > 0:
					self.ncdll.nc_close(self.ncid)
				return True, "ERROR: error getting netcdf variable dimensions. Error: {0}".format(NC_Error.message(err))
			var.dimIds = tuple(cint_array[x] for x in range(var.nDims))
			var.dimNames = tuple(self.ncDims[x].name for x in var.dimIds)
			var.dimLens = tuple(self.ncDims[x].len for x in var.dimIds)

	def loadTPC(self):
		error = False
		message = ""
		try:
			data = numpy.genfromtxt(self.filename, dtype=str, delimiter="==")
		except IOError:
			message = 'Cannot find the following file: \n{0}'.format(self.fpath)
			error = True
			return error, message
		except:
			error = True
			message = 'ERROR - Unable to load data, check file exists.'
			return error, message

		for i in range (0,len(data)):
			tmp = data[i,0]
			dat_type = tmp.strip()
			tmp = data[i,1]
			rdata = tmp.strip()

			if dat_type == "Time Series Output Format":
				continue
			elif dat_type == "NetCDF Time Series":
				continue
			elif dat_type == 'Format Version':
				self.formatVersion = int(rdata)
			elif dat_type == 'Units':
				self.units = rdata
			elif dat_type == 'Simulation ID':
				self.displayname = rdata
			elif dat_type == 'GIS Plot Layer Points':
				self.GIS.P = rdata[2:]
			elif dat_type == 'GIS Plot Layer Lines':
				self.GIS.L = rdata[2:]
			elif dat_type == 'GIS Plot Layer Regions':
				self.GIS.R = rdata[2:]
			elif dat_type == 'GIS Plot Objects':
				fullpath = getOSIndependentFilePath(self.fpath, rdata)
				self.Index = PlotObjects(fullpath)
			elif dat_type == 'GIS Reporting Location Points':
				self.GIS.RL_P = rdata[2:]
			elif dat_type == 'GIS Reporting Location Lines':
				self.GIS.RL_L = rdata[2:]
			elif dat_type == 'GIS Reporting Location Regions':
				self.GIS.RL_R = rdata[2:]
			elif dat_type == 'Number 1D Channels':
				#self.nChannels = int(rdata)
				self.Data_1D.nChan = int(rdata)
			elif dat_type == 'Number 1D Nodes':
				self.Data_1D.nNode = int(rdata)
			elif dat_type == 'Number Reporting Location Points':
				self.Data_RL.nPoint= int(rdata)
			elif dat_type == 'Number Reporting Location Lines':
				self.Data_RL.nLine= int(rdata)
			elif dat_type == 'Number Reporting Location Regions':
				self.Data_RL.nRegion= int(rdata)
			elif dat_type == '1D Channel Info':
				if rdata != 'NONE':
					fullpath = getOSIndependentFilePath(self.fpath, rdata)
					self.Channels = ChanInfo(fullpath)
					if self.Channels.error:
						return self.Channels.error, self.Channels.message
					if self.Data_1D.nChan != self.Channels.nChan:
						error = True
						message = 'Number of Channels does not match value in .tpc'
						return error, message
			elif dat_type == '1D Node Info':
				if rdata != 'NONE':
					fullpath = getOSIndependentFilePath(self.fpath, rdata)
					self.nodes = NodeInfo(fullpath)
					if self.nodes.error:
						return self.nodes.error, self.nodes.message
			elif dat_type == '1D Water Levels':
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						error, message = self.Data_1D.H.Load(fullpath, 'H', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Water Levels')
						if self.nTypes == 1:
							self.times = self.Data_1D.H.Values[:,1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_1D.H.loadFromNetCDF(self.netcdf_fpath, "water_levels_1d", "node_names",
						                                               self.netCDFLib, self.ncopen, self.ncid, self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Water Levels')
						if self.nTypes == 1:
							self.times = self.Data_1D.H.Values[:, 1]
			elif dat_type == '1D Energy Levels':
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						error, message = self.Data_1D.E.Load(fullpath, 'E', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Energy Levels')
						if self.nTypes == 1:
							self.times = self.Data_1D.H.Values[:,1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_1D.E.loadFromNetCDF(self.netcdf_fpath, "energy_levels_1d", "node_names",
						                                               self.netCDFLib, self.ncopen, self.ncid, self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Energy Levels')
						if self.nTypes == 1:
							self.times = self.Data_1D.E.Values[:, 1]
			elif dat_type == 'Reporting Location Points Water Levels':
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						error, message = self.Data_RL.H_P.Load(fullpath, 'H', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('RL Water Levels')
						if self.nTypes == 1:
							self.times = self.Data_RL.H_P.Values[:, 1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_RL.H_P.loadFromNetCDF(self.netcdf_fpath, "water_levels_rl", "name_water_levels_rl",
						                                                 self.netCDFLib, self.ncopen, self.ncid,
						                                                 self.ncdll,
						                                                 self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('RL Water Levels')
						if self.nTypes == 1:
							self.times = self.Data_RL.H_P.Values[:, 1]
			elif dat_type == 'Reporting Location Lines Flows':
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						error, message = self.Data_RL.Q_L.Load(fullpath, 'Q', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('RL Flows')
						if self.nTypes == 1:
							self.times = self.Data_RL.Q_L.Values[:, 1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_RL.Q_L.loadFromNetCDF(self.netcdf_fpath, "flows_rl", "name_flows_rl",
						                                                 self.netCDFLib, self.ncopen, self.ncid,
						                                                 self.ncdll,
						                                                 self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('RL Flows')
						if self.nTypes == 1:
							self.times = self.Data_RL.Q_L.Values[:, 1]
			elif dat_type == 'Reporting Location Regions Volumes':
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						error, message = self.Data_RL.Vol_R.Load(fullpath, 'Vol', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('RL Region Volume')
						if self.nTypes == 1:
							self.times = self.Data_RL.Vol_R.Values[:, 1]
						try:
							chk_nLocs = self.Data_RL.nRegion
							if (chk_nLocs != self.Data_RL.Vol_R.nLocs):
								message = 'ERROR - number of locations in .csv doesn\'t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_RL.Vol_R.loadFromNetCDF(self.netcdf_fpath, "volumes_rl", "name_volumes_rl",
						                                                   self.netCDFLib, self.ncopen, self.ncid,
						                                                   self.ncdll,
						                                                   self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('RL Region Volume')
						if self.nTypes == 1:
							self.times = self.Data_RL.Vol_R.Values[:, 1]
			elif dat_type == '1D Node Maximums':
				if rdata != 'NONE':
					fullpath = getOSIndependentFilePath(self.fpath, rdata)
					error, message = self.Data_1D.Node_Max.Load(fullpath)
					if error:
						return error, message
			elif dat_type == '1D Channel Maximums':
				if rdata != 'NONE':
					fullpath = getOSIndependentFilePath(self.fpath, rdata)
					error, message = self.Data_1D.Chan_Max.Load(fullpath)
					if error:
						return error, message
			elif dat_type == '1D Flows':
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						error, message = self.Data_1D.Q.Load(fullpath, 'Q', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Flows')
						if self.nTypes == 1:
							self.times = self.Data_1D.Q.Values[:,1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_1D.Q.loadFromNetCDF(self.netcdf_fpath, "flow_1d",
						                                               "channel_names",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Flows')
						if self.nTypes == 1:
							self.times = self.Data_1D.Q.Values[:, 1]
			elif dat_type == '1D Flow Areas':
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						error, message = self.Data_1D.A.Load(fullpath, 'A', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Flow Area')
						if self.nTypes == 1:
							self.times = self.Data_1D.A.Values[:,1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_1D.A.loadFromNetCDF(self.netcdf_fpath, "flow_areas_1d",
						                                               "channel_names",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Flow Area')
						if self.nTypes == 1:
							self.times = self.Data_1D.A.Values[:, 1]
			elif dat_type == '1D Velocities':
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						error, message = self.Data_1D.V.Load(fullpath, 'V', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Velocities')
						if self.nTypes == 1:
							self.times = self.Data_1D.V.Values[:,1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_1D.V.loadFromNetCDF(self.netcdf_fpath, "velocities_1d",
						                                               "channel_names",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Velocities')
						if self.nTypes == 1:
							self.times = self.Data_1D.V.Values[:, 1]
			elif dat_type.find('2D Line Flow Area') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.QA = Timeseries(fullpath,'QA',self.displayname)
						error, message = self.Data_2D.QA.Load(fullpath, 'QA', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Line Flow Area')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.QA.nLocs):
								print('ERROR - number of locations in .csv doesn''t match value in .tpc')
								exit()
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_2D.QA.loadFromNetCDF(self.netcdf_fpath, "flow_areas_2d",
						                                                "name_flow_areas_2d",
						                                                self.netCDFLib, self.ncopen, self.ncid,
						                                                self.ncdll,
						                                                self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Line Flow Area')
						if self.nTypes == 1:
							self.times = self.Data_2D.QA.Values[:, 1]
			elif dat_type.find('2D Line Flow') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.Q = Timeseries(fullpath,'Q',self.displayname)
						error, message = self.Data_2D.Q.Load(fullpath, 'Q', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						if self.nTypes == 1:
							self.times = self.Data_2D.Q.Values[:,1]
						self.Types.append('2D Line Flow')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.Q.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_2D.Q.loadFromNetCDF(self.netcdf_fpath, "flows_2d",
						                                               "name_flows_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Line Flow')
						if self.nTypes == 1:
							self.times = self.Data_2D.Q.Values[:, 1]
			elif dat_type.find('2D Line X-Flow') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.Vx = Timeseries(fullpath,'VX',self.displayname)
						error, message = self.Data_2D.Qx.Load(fullpath, 'QX', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Line X-Flow')
						if self.nTypes == 1:
							self.times = self.Data_2D.Qx.Values[:, 1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						pass  # for now not written to netcdf
						error, message = self.Data_2D.Qx.loadFromNetCDF(self.netcdf_fpath, "x_direction_flows_2d",
						                                               "name_x_direction_flows_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Line X-Flow')
						if self.nTypes == 1:
							self.times = self.Data_2D.Qx.Values[:, 1]
			elif dat_type.find('2D Line Y-Flow') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.Vx = Timeseries(fullpath,'VX',self.displayname)
						error, message = self.Data_2D.Qy.Load(fullpath, 'QY', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Line Y-Flow')
						if self.nTypes == 1:
							self.times = self.Data_2D.Qy.Values[:, 1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						pass  # for now not written to netcdf
						error, message = self.Data_2D.Qy.loadFromNetCDF(self.netcdf_fpath, "y_direction_flows_2d",
						                                               "name_y_direction_flows_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Line Y-Flow')
						if self.nTypes == 1:
							self.times = self.Data_2D.Qy.Values[:, 1]
			elif dat_type.find('2D Point Gauge Level') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.GL = Timeseries(fullpath,'G',self.displayname)
						error, message = self.Data_2D.GL.Load(fullpath, 'G', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point Gauge Level')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.GL.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						pass  # for now not written to netcdf
						error, message = self.Data_2D.GL.loadFromNetCDF(self.netcdf_fpath, "gauge_levels_2d",
						                                                "name_gauge_levels_2d",
						                                                self.netCDFLib, self.ncopen, self.ncid,
						                                                self.ncdll,
						                                                self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point Gauge Level')
						if self.nTypes == 1:
							self.times = self.Data_2D.GL.Values[:, 1]
			elif dat_type.find('2D Point Water Level') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.H = Timeseries(fullpath,'H',self.displayname)
						error, message = self.Data_2D.H.Load(fullpath, 'H', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point Water Level')
						if self.nTypes == 1:
							self.times = self.Data_2D.H.Values[:,1]
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.H.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_2D.H.loadFromNetCDF(self.netcdf_fpath, "water_levels_2d",
						                                               "name_water_levels_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point Water Level')
						if self.nTypes == 1:
							self.times = self.Data_2D.H.Values[:, 1]
			elif dat_type.find('2D Point X-Vel') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.Vx = Timeseries(fullpath,'VX',self.displayname)
						error, message = self.Data_2D.Vx.Load(fullpath, 'VX', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point X-Vel')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.Vx.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						pass  # for now not written to netcdf
						error, message = self.Data_2D.Vx.loadFromNetCDF(self.netcdf_fpath, "x_direction_velocities_2d",
						                                               "name_x_direction_velocities_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point X-Vel')
						if self.nTypes == 1:
							self.times = self.Data_2D.Vx.Values[:, 1]
			elif dat_type.find('2D Point Y-Vel') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.Vy = Timeseries(fullpath,'VY',self.displayname)
						error, message = self.Data_2D.Vy.Load(fullpath, 'VY', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point Y-Vel')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.Vy.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						pass  # for now not written to netcdf
						error, message = self.Data_2D.Vy.loadFromNetCDF(self.netcdf_fpath, "y_direction_velocities_2d",
						                                               "name_y_direction_velocities_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point Y-Vel')
						if self.nTypes == 1:
							self.times = self.Data_2D.Vy.Values[:, 1]
			elif dat_type.find('2D Point u-Vel') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.Vx = Timeseries(fullpath,'VX',self.displayname)
						error, message = self.Data_2D.Vu.Load(fullpath, 'Vu', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point u-Vel')
						if self.nTypes == 1:
							self.times = self.Data_2D.Vu.Values[:, 1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						pass  # for now not written to netcdf
						error, message = self.Data_2D.Vu.loadFromNetCDF(self.netcdf_fpath, "u_velocities_2d",
						                                               "name_u_velocities_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point u-Vel')
						if self.nTypes == 1:
							self.times = self.Data_2D.Vu.Values[:, 1]
			elif dat_type.find('2D Point v-Vel') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.Vx = Timeseries(fullpath,'VX',self.displayname)
						error, message = self.Data_2D.Vv.Load(fullpath, 'Vv', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point v-Vel')
						if self.nTypes == 1:
							self.times = self.Data_2D.Vv.Values[:, 1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						pass  # for now not written to netcdf
						error, message = self.Data_2D.Vv.loadFromNetCDF(self.netcdf_fpath, "v_velocities_2d",
						                                               "name_v_velocities_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point v-Vel')
						if self.nTypes == 1:
							self.times = self.Data_2D.Vv.Values[:, 1]
			elif dat_type.find('2D Point Flow Direction') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.Vx = Timeseries(fullpath,'VX',self.displayname)
						error, message = self.Data_2D.VA.Load(fullpath, 'VA', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point Velocity Angle')
						if self.nTypes == 1:
							self.times = self.Data_2D.VA.Values[:, 1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						pass  # for now not written to netcdf
						error, message = self.Data_2D.VA.loadFromNetCDF(self.netcdf_fpath, "velocity_angle_2d",
						                                               "name_velocity_angle_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point Velocity Angle')
						if self.nTypes == 1:
							self.times = self.Data_2D.VA.Values[:, 1]
			elif dat_type.find('2D Point Velocity') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.V = Timeseries(fullpath,'V',self.displayname)
						error, message = self.Data_2D.V.Load(fullpath, 'V', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point Velocity')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.V.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_2D.V.loadFromNetCDF(self.netcdf_fpath, "velocities_2d",
						                                               "name_velocities_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Point Velocity')
						if self.nTypes == 1:
							self.times = self.Data_2D.V.Values[:, 1]
			elif dat_type.find('2D Line Integral Flow') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.QI = Timeseries(fullpath,'QI',self.displayname)
						error, message = self.Data_2D.QI.Load(fullpath, 'QI', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Line Integral Flow')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.QI.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_2D.QI.loadFromNetCDF(self.netcdf_fpath, "integral_flows_2d",
						                                               "name_integral_flows_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Line Integral Flow')
						if self.nTypes == 1:
							self.times = self.Data_2D.QI.Values[:, 1]
			elif dat_type.find('2D Line Structure Flow') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.QI = Timeseries(fullpath,'QI',self.displayname)
						error, message = self.Data_2D.QS.Load(fullpath, 'QS', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Line Structure Flow')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.QS.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_2D.QS.loadFromNetCDF(self.netcdf_fpath, "structure_flows_2d",
						                                               "name_structure_flows_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Line Structure Flow')
						if self.nTypes == 1:
							self.times = self.Data_2D.QS.Values[:, 1]
			elif dat_type.find('2D Line U/S Structure Water') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.QI = Timeseries(fullpath,'QI',self.displayname)
						error, message = self.Data_2D.HUS.Load(fullpath, 'HU', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Structure Levels')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.HUS.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_2D.HUS.loadFromNetCDF(self.netcdf_fpath, "upstream_water_levels_2d",
						                                               "name_upstream_water_levels_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Structure Levels')
						if self.nTypes == 1:
							self.times = self.Data_2D.HUS.Values[:, 1]
			elif dat_type.find('2D Line D/S Structure Water') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						#self.Data_2D.QI = Timeseries(fullpath,'QI',self.displayname)
						error, message = self.Data_2D.HDS.Load(fullpath, 'HD', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Structure Levels')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.HDS.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_2D.HDS.loadFromNetCDF(self.netcdf_fpath, "downstream_water_levels_2d",
						                                               "name_downstream_water_levels_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Structure Levels')
						if self.nTypes == 1:
							self.times = self.Data_2D.HDS.Values[:, 1]
			elif dat_type.find('2D Region Average Water Level') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						error, message = self.Data_2D.HAvg.Load(fullpath, 'HA', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Region Average Water Level')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.HAvg.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						pass  # for now not written to netcdf
						error, message = self.Data_2D.HAvg.loadFromNetCDF(self.netcdf_fpath, "average_water_levels_2d",
						                                               "name_average_water_levels_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Region Average Water Level')
						if self.nTypes == 1:
							self.times = self.Data_2D.HAvg.Values[:, 1]
			elif dat_type.find('2D Region Max Water Level') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						error, message = self.Data_2D.HMax.Load(fullpath,'HM',self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Region Max Water Level')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.HMax.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						pass  # for now not written to netcdf
						error, message = self.Data_2D.HMax.loadFromNetCDF(self.netcdf_fpath, "maximum_water_levels_2d",
						                                               "name_maximum_water_levels_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Region Max Water Level')
						if self.nTypes == 1:
							self.times = self.Data_2D.HMax.Values[:, 1]
			elif dat_type.find('2D Region Flow into Region') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						error, message = self.Data_2D.QIn.Load(fullpath,'FI',self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Region Flow into')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.QIn.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_2D.QIn.loadFromNetCDF(self.netcdf_fpath, "flows_into_region_2d",
						                                               "name_flows_into_region_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Region Flow into')
						if self.nTypes == 1:
							self.times = self.Data_2D.QIn.Values[:, 1]
			elif dat_type.find('2D Region Flow out of Region') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						error, message = self.Data_2D.QOut.Load(fullpath,'FO',self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Region Flow out of')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.QOut.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_2D.QOut.loadFromNetCDF(self.netcdf_fpath, "flows_out_of_region_2d",
						                                               "name_flows_out_of_region_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Region Flow out of')
						if self.nTypes == 1:
							self.times = self.Data_2D.QOut.Values[:, 1]
			elif dat_type.find('2D Region Volume') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						error, message = self.Data_2D.Vol.Load(fullpath,'VL',self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Region Volume')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.Vol.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_2D.Vol.loadFromNetCDF(self.netcdf_fpath, "volume_2d",
						                                               "name_volume_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Region Volume')
						if self.nTypes == 1:
							self.times = self.Data_2D.Vol.Values[:, 1]
			elif dat_type.find('Region Sink/Source') >= 0:
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						indA = dat_type.index('[')
						indB = dat_type.index(']')
						error, message = self.Data_2D.SS.Load(fullpath,'SS',self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Region Sink/Source')
						try:
							chk_nLocs = int(dat_type[indA+1:indB])
							if (chk_nLocs != self.Data_2D.SS.nLocs):
								message = 'ERROR - number of locations in .csv doesn''t match value in .tpc'
								error = True
								return error, message
						except:
							print('WARNING - Unable to extact number of values in .tpc file entry')
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_2D.SS.loadFromNetCDF(self.netcdf_fpath, "sink_source_2d",
						                                               "name_sink_source_2d",
						                                               self.netCDFLib, self.ncopen, self.ncid,
						                                               self.ncdll,
						                                               self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('2D Region Sink/Source')
						if self.nTypes == 1:
							self.times = self.Data_2D.SS.Values[:, 1]
			elif dat_type == 'Reporting Location Points Maximums':
				if rdata != 'NONE':
					fullpath = getOSIndependentFilePath(self.fpath, rdata)
					error, message = self.Data_RL.P_Max.Load(fullpath)
					if error:
						return error, message
			elif dat_type == 'Reporting Location Lines Maximums':
				if rdata != 'NONE':
					fullpath = getOSIndependentFilePath(self.fpath, rdata)
					error, message = self.Data_RL.L_Max.Load(fullpath)
					if error:
						return error, message
			elif dat_type == 'Reporting Location Regions Maximums':
				if rdata != 'NONE':
					fullpath = getOSIndependentFilePath(self.fpath, rdata)
					error, message = self.Data_RL.R_Max.Load(fullpath)
					if error:
						return error, message
			elif dat_type == "1D Mass Balance Errors":
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						error, message = self.Data_1D.MB.Load(fullpath, 'MB', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Mass Balance Error')
						if self.nTypes == 1:
							self.times = self.Data_1D.MB.Values[:, 1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_1D.MB.loadFromNetCDF(self.netcdf_fpath, "mass_balance_error_1d",
						                                                "node_names",
						                                                self.netCDFLib, self.ncopen, self.ncid,
						                                                self.ncdll,
						                                                self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Mass Balance Error')
						if self.nTypes == 1:
							self.times = self.Data_1D.MB.Values[:, 1]
			elif dat_type == "1D Node Regime":
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						error, message = self.Data_1D.NF.Load(fullpath, 'F', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Node Flow Regime')
						if self.nTypes == 1:
							self.times = self.Data_1D.NF.Values[:, 1].astype(float)
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_1D.NF.loadFromNetCDF(self.netcdf_fpath, "node_flow_regime_1d",
						                                                "node_names",
						                                                self.netCDFLib, self.ncopen, self.ncid,
						                                                self.ncdll,
						                                                self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Node Flow Regime')
						if self.nTypes == 1:
							self.times = self.Data_1D.NF.Values[:, 1]
			elif dat_type == "1D Channel Regime":
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						error, message = self.Data_1D.CF.Load(fullpath, 'F', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Channel Flow Regime')
						if self.nTypes == 1:
							self.times = self.Data_1D.CF.Values[:, 1].astype(float)
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_1D.CF.loadFromNetCDF(self.netcdf_fpath, "channel_flow_regime_1d",
						                                                "channel_names",
						                                                self.netCDFLib, self.ncopen, self.ncid,
						                                                self.ncdll,
						                                                self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Channel Flow Regime')
						if self.nTypes == 1:
							self.times = self.Data_1D.CF.Values[:, 1]
			elif dat_type == "1D Channel Losses":
				if self.resFileFormat == "CSV":
					if rdata != 'NONE':
						fullpath = getOSIndependentFilePath(self.fpath, rdata)
						error, message = self.Data_1D.CL.Load(fullpath, 'LC', self.displayname)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Channel Losses')
						if self.nTypes == 1:
							self.times = self.Data_1D.CL.Values[:, 1]
				elif self.resFileFormat == "NC":
					if self.netcdf_fpath:
						error, message = self.Data_1D.CL.loadFromNetCDF(self.netcdf_fpath, "losses_1d",
						                                                "names_losses_1d",
						                                                self.netCDFLib, self.ncopen, self.ncid,
						                                                self.ncdll,
						                                                self.ncDims, self.ncVars)
						if error:
							return error, message
						self.nTypes = self.nTypes + 1
						self.Types.append('1D Channel Losses')
						if self.nTypes == 1:
							self.times = self.Data_1D.CL.Values[:, 1]
			else:
				print('Warning - Unknown Data Type '+dat_type)
		#successful load
		if self.ncid.value > 0:
			self.ncdll.nc_close(self.ncid)
		if self.ncopen:
			self.ncopen.close()
			self.ncopen = None
		return error, message
	
	def pointResultTypesTS(self):
		"""
		Returns a list of all the available point result types.
		
		:return: list -> str result type e.g. 'flows'
		"""
		
		types = []
		
		for type in self.Types:
			if 'STRUCTURE LEVELS' in type.upper():
				types.append('Structure Levels')
			elif 'WATER LEVEL' in type.upper():
				types.append('Level')
			elif 'ENERGY LEVELS' in type.upper():
				types.append('Energy Level')
			elif 'POINT X-VEL' in type.upper():
				types.append('VX')
			elif 'POINT Y-VEL' in type.upper():
				types.append('VY')
			elif 'POINT U-VEL' in type.upper():
				types.append('Vu')
			elif 'POINT V-VEL' in type.upper():
				types.append('Vv')
			elif 'POINT V-VEL' in type.upper():
				types.append('Vv')
			elif '2D POINT VELOCITY ANGLE' in type.upper():
				types.append("VA")
			elif 'POINT VELOCITY' in type.upper():
				types.append('Velocity')
			elif '1D MASS BALANCE ERROR' in type.upper():
				types.append('MB')
			elif '1D NODE FLOW REGIME' in type.upper():
				if 'Flow Regime' not in types:
					types.append('Flow Regime')
				
		return types
	
	def lineResultTypesTS(self):
		"""
		Returns a list of all the available line result types.
		
		:return: list -> str result type e.g. 'flows'
		"""
		
		types = []
		
		for type in self.Types:
			if 'VELOCITIES' in type.upper():
				types.append('Velocity')
			elif 'LINE FLOW AREA' in type.upper():
				types.append('Flow Area')
			elif 'LINE INTEGRAL FLOW' in type.upper():
				types.append('Flow Integral')
			elif 'US LEVELS' in type.upper():
				types.append('US Levels')
			elif 'DS LEVELS' in type.upper():
				types.append('DS Levels')
			elif 'DS LEVELS' in type.upper():
				types.append('DS Levels')
			elif 'LINE STRUCTURE FLOW' in type.upper():
				types.append('Structure Flows')
			elif '1D Flow Area' in type:
				types.append('Flow Area')
			elif 'X-FLOW' in type.upper():
				types.append('X Flow')
			elif 'Y-FLOW' in type.upper():
				types.append('Y Flow')
			elif '1D CHANNEL FLOW REGIME' in type.upper():
				if 'Flow Regime' not in types:
					types.append('Flow Regime')
			elif '1D CHANNEL LOSSES' in type.upper():
				types.append('Losses')
			elif 'FLOW' in type.upper():
				types.append('Flow')

		if self.nodes is not None:
			point_types = self.pointResultTypesTS()
			if 'Level' in point_types:
				if 'US Levels' not in types:
					types.append('US Levels')
				if 'DS Levels' not in types:
					types.append('DS Levels')
		
		return types
	
	def regionResultTypesTS(self):
		"""
		Returns a list of all the available region result types.
		
		:return: list -> str result type e.g. 'flows'
		"""
		
		types = []
		
		for type in self.Types:
			if 'REGION AVERAGE WATER LEVEL' in type.upper():  # 2017-09-AA
				types.append('Average Level')
			elif 'REGION MAX WATER LEVEL' in type.upper():  # 2017-09-AA
				types.append('Max Level')
			elif 'REGION FLOW INTO' in type.upper():  # 2017-09-AA
				types.append('Flow Into')
			elif 'REGION FLOW OUT OF' in type.upper():  # 2017-09-AA
				types.append('Flow Out')
			elif 'REGION VOLUME' in type.upper():  # 2017-09-AA
				types.append('Volume')
			elif 'REGION SINK/SOURCE' in type.upper():  # 2017-09-AA
				types.append('Sink/Source')

		return types
	
	def lineResultTypesLP(self):
		"""
		Returns a list of all the available line result types for long plotting.

		:return: list -> str result type e.g. 'flows'
		"""
		
		types = []
		
		if self.nodes is not None:
			for type in self.Types:
				if 'WATER LEVELS' in type.upper():
					types.append('Water Level')
					types.append('Max Water Level')
					types.append('Time of Max H')
					#types.append('Water Level at Time')
				elif 'ENERGY LEVELS' in type.upper():
					types.append('Energy Level')
					types.append('Max Energy Level')
					#types.append('Energy Level at Time')
					
			types.append('Bed Level')
			types.append('Culverts and Pipes')
			types.append('Left Bank Obvert')
			types.append('Right Bank Obvert')
			types.append('Pit Ground Levels (if any)')
			types.append('Adverse Gradients (if any)')
		
		return types
	
	def timeSteps(self):
		"""
		Returns a list of the available time steps. Assumes all time series results have the same timesteps.
		
		:return: list -> float time (hr)
		"""
		
		if self.Data_1D.H.loaded:
			return self.Data_1D.H.Values[:,1]
		elif self.Data_1D.V.loaded:
			return self.Data_1D.V.Values[:,1]
		elif self.Data_1D.E.loaded:
			return self.Data_1D.E.Values[:,1]
		elif self.Data_1D.Q.loaded:
			return self.Data_1D.Q.Values[:,1]
		elif self.Data_1D.A.loaded:
			return self.Data_1D.A.Values[:,1]
		elif self.Data_2D.H.loaded:
			return self.Data_2D.H.Values[:,1]
		elif self.Data_2D.V.loaded:
			return self.Data_2D.V.Values[:,1]
		elif self.Data_2D.Q.loaded:
			return self.Data_2D.Q.Values[:,1]
		elif self.Data_2D.GL.loaded:
			return self.Data_2D.GL.Values[:,1]
		elif self.Data_2D.QA.loaded:
			return self.Data_2D.QA.Values[:,1]
		elif self.Data_2D.QI.loaded:
			return self.Data_2D.QI.Values[:,1]
		elif self.Data_2D.Vx.loaded:
			return self.Data_2D.Vx.Values[:,1]
		elif self.Data_2D.Vy.loaded:
			return self.Data_2D.Vy.Values[:,1]
		elif self.Data_2D.QS.loaded:
			return self.Data_2D.QS.Values[:,1]
		elif self.Data_2D.HUS.loaded:
			return self.Data_2D.HUS.Values[:,1]
		elif self.Data_2D.HDS.loaded:
			return self.Data_2D.HDS.Values[:,1]
		elif self.Data_2D.HAvg.loaded:
			return self.Data_2D.HAvg.Values[:,1]
		elif self.Data_2D.HMax.loaded:
			return self.Data_2D.HMax.Values[:,1]
		elif self.Data_2D.QIn.loaded:
			return self.Data_2D.QIn.Values[:,1]
		elif self.Data_2D.QOut.loaded:
			return self.Data_2D.QOut.Values[:,1]
		elif self.Data_2D.SS.loaded:
			return self.Data_2D.SS.Values[:,1]
		elif self.Data_2D.Vol.loaded:
			return self.Data_2D.Vol.Values[:,1]
		elif self.Data_RL.H_P.loaded:
			return self.Data_RL.H_P.Values[:,1]
		elif self.Data_RL.Q_L.loaded:
			return self.Data_RL.Q_L.Values[:,1]
		elif self.Data_RL.Vol_R.loaded:
			return self.Data_RL.Vol_R.Values[:,1]
		else:
			return []
		
	def getLongPlotXY(self, type, time):
		"""
		Generates long plot X, Y coordinates
		
		:param type: str -> result type e.g. 'Water Level'
		:param time: float
		:return: tuple -> list -> float e.g. (x, y)
		"""
		
		error = False
		message = ''
		
		if 'water level' in type.lower():
			if time == -99999:
				return (self.LP.dist_chan_inverts, self.LP.Hmax)
			else:
				error, message = self.LP_getData('Water Level', time, 0.01)
				return (self.LP.dist_chan_inverts, self.LP.Hdata)
		
		elif 'energy level' in type.lower():
			if time == -99999:
				return (self.LP.dist_chan_inverts, self.LP.Emax)
			else:
				error, message = self.LP_getData('Energy Level', time, 0.01)
				return (self.LP.dist_chan_inverts, self.LP.Edata)
			
		elif 'adverse gradients (if any)' in type.lower():
			return (self.LP.adverseH.chainage, self.LP.adverseH.elevation), \
			       (self.LP.adverseE.chainage, self.LP.adverseE.elevation)
		
		elif 'bed level' in type.lower():
			return (self.LP.dist_chan_inverts, self.LP.chan_inv)
		
		elif 'left bank obvert' in type.lower():
			return (self.LP.dist_chan_inverts, self.LP.chan_LB)
		
		elif 'right bank obvert' in type.lower():
			return (self.LP.dist_chan_inverts, self.LP.chan_RB)
		
		elif 'pit ground levels (if any)' in type.lower():
			return (self.LP.pit_dist, self.LP.pit_z)
		
		elif 'culverts and pipes' in type.lower():
			return self.LP.culv_verts, [0, 1, 2, 3, 4, 5]  # dummy y data - ultimately not used
		
		elif 'time of max h' in type.lower():
			return (self.LP.dist_chan_inverts, self.LP.tHmax)
		
		else:
			return (None, None)