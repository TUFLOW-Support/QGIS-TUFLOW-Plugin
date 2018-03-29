import os
import numpy
import csv
import sys
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
		except:
			print('ERROR - Error reading data from: '+fullpath)

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

	def Load(self,fullpath,prefix, simID):
		error = False
		message = ''
		try:
			with open(fullpath, 'r') as csvfile:
				reader = csv.reader(csvfile, delimiter=',', quotechar='"')
				header = next(reader)
			csvfile.close()
		except:
			message = '"ERROR - Error reading header from: '+fullpath
			error = True
			return error, message
		header[0]='Timestep'
		header[1]='Time'
		self.ID = []
		i=1
		for col in header[2:]:
			i= i+1
			a = col[len(prefix)+1:]
			indA = a.find(simID)
			indB = a.rfind('[') #find last occurrence of [
			if (indA >= 0) and (indB >= 0): # strip simulation ID from header
				a = a[0:indB-1]
			self.ID.append(a)
			header [i] = a
		self.Header = header
		try:
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
		except:
			message = 'ERROR - Error reading data from file. Check file, there may not be any data: {0}'.format(fullpath)
			error = True
			return error, message
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
		with open(fullpath, 'r') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			header = next(reader)
			for (counter, row) in enumerate(reader):
				self.node_num.append(int(row[0]))
				self.node_name.append(row[1])
				self.node_bed.append(float(row[2]))
				self.node_top.append(float(row[3]))
				self.node_nChan.append(int(row[4]))
				chan_list = row[5:]
				if len(chan_list) != int(row[4]):
					if int(row[4]) != 0:
						print('ERROR - Number of channels connected to ID doesnt match. ID: ' + str(row[1]))
				else:
					self.node_channels.append(chan_list)
		csvfile.close()

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
				self.chan_Length.append(float(row[7]))
				self.chan_FormLoss.append(float(row[8]))
				self.chan_n.append(float(row[9]))
				self.chan_slope.append(float(row[10]))
				self.chan_US_Inv.append(float(row[11]))
				self.chan_DS_Inv.append(float(row[12]))
				self.chan_LBUS_Obv.append(float(row[13]))
				self.chan_RBUS_Obv.append(float(row[14]))
				self.chan_LBDS_Obv.append(float(row[15]))
				self.chan_RBDS_Obv.append(float(row[16]))
				self.chan_Blockage.append(float(row[17]))
		self.nChan = counter+1
		csvfile.close()

# results class
class ResData():
	"""
	ResData class for reading and processing results
	"""

	def getTSData(self, id,dom,res,geom):
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
				if self.Data_2D.HMax.loaded:
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

	def LP_getConnectivity(self,id1,id2):
		print('determining LP connectivity')
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
				print('ERROR - ID not found: ' + str(id1))
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
						self.LP.Hmax.append(self.Data_1D.Node_Max.HMax[ind])
					elif i < len(self.LP.node_list) - 1:
						self.LP.Hmax.append(max(self.Data_1D.Node_Max.HMax[ind], self.LP.chan_inv[2*i-1]))
						self.LP.Hmax.append(self.Data_1D.Node_Max.HMax[ind])
					else:
						self.LP.Hmax.append(max(self.Data_1D.Node_Max.HMax[ind], self.LP.chan_inv[2*i-1]))
				if self.Data_1D.Node_Max.EMax:
					if i == 0:
						self.LP.Emax.append(self.Data_1D.Node_Max.EMax[ind])
					elif i < len(self.LP.node_list) - 1:
						self.LP.Emax.append(max(self.Data_1D.Node_Max.EMax[ind], self.LP.chan_inv[2*i-1]))
						self.LP.Emax.append(self.Data_1D.Node_Max.EMax[ind])
					else:
						self.LP.Emax.append(max(self.Data_1D.Node_Max.EMax[ind], self.LP.chan_inv[2*i-1]))
				if self.Data_1D.Node_Max.tHmax:
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
		if dat_type == 'Head':
			self.LP.Hdata = []
			if not self.Data_1D.H.loaded:
				error = True
				message = 'ERROR - No water level data loaded.'
				return error, message
			for i, h_ind in enumerate(self.LP.H_nd_index):
				if i == 0:
					self.LP.Hdata.append(self.Data_1D.H.Values[t_ind,h_ind])
				elif i < len(self.LP.H_nd_index) - 1:
					self.LP.Hdata.append(max(self.Data_1D.H.Values[t_ind,h_ind], self.LP.chan_inv[2*i-1]))
					self.LP.Hdata.append(self.Data_1D.H.Values[t_ind,h_ind])
				else:
					self.LP.Hdata.append(max(self.Data_1D.H.Values[t_ind,h_ind], self.LP.chan_inv[2*i-1]))
		elif dat_type == 'Energy':
			self.LP.Edata = []
			if not self.Data_1D.E.loaded:
				error = True
				message = 'ERROR - No energy level data loaded.'
				return error, message
			for h_ind in self.LP.H_nd_index:
				if i == 0:
					self.LP.Edata.append(self.Data_1D.E.Values[t_ind,h_ind])
				elif i < len(self.LP.H_nd_index) - 1:
					self.LP.Edata.append(max(self.Data_1D.E.Values[t_ind,h_ind], self.LP.chan_inv[2*i-1]))
					self.LP.Edata.append(self.Data_1D.E.Values[t_ind,h_ind])
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

	def Load(self, fname):
		error = False
		message = None
		self.filename = fname
		self.fpath = os.path.dirname(fname)
		try:
			data = numpy.genfromtxt(fname, dtype=str, delimiter="==")
		except:
			error = True
			message = 'ERROR - Unable to load data, check file exists.'
			return error, message

		for i in range (0,len(data)):
			tmp = data[i,0]
			dat_type = tmp.strip()
			tmp = data[i,1]
			rdata = tmp.strip()
			if (dat_type=='Format Version'):
				self.formatVersion = int(rdata)
			elif (dat_type=='Units'):
				self.units = rdata
			elif (dat_type=='Simulation ID'):
				self.displayname = rdata
			elif (dat_type=='GIS Plot Layer Points'):
				self.GIS.P = rdata[2:]
			elif (dat_type=='GIS Plot Layer Lines'):
				self.GIS.L = rdata[2:]
			elif (dat_type=='GIS Plot Layer Regions'):
				self.GIS.R = rdata[2:]
			elif (dat_type=='GIS Plot Objects'):
				fullpath = os.path.join(self.fpath,rdata[2:])
				self.Index = PlotObjects(fullpath)
			elif (dat_type=='GIS Reporting Location Points'):
				self.GIS.RL_P = rdata[2:]
			elif (dat_type=='GIS Reporting Location Lines'):
				self.GIS.RL_L = rdata[2:]
			elif (dat_type=='GIS Reporting Location Regions'):
				self.GIS.RL_R = rdata[2:]
			elif (dat_type=='Number 1D Channels'):
				#self.nChannels = int(rdata)
				self.Data_1D.nChan = int(rdata)
			elif (dat_type=='Number 1D Nodes'):
				self.Data_1D.nNode = int(rdata)
			elif (dat_type=='Number Reporting Location Points'):
				self.Data_RL.nPoint= int(rdata)
			elif (dat_type=='Number Reporting Location Lines'):
				self.Data_RL.nLine= int(rdata)
			elif (dat_type=='Number Reporting Location Regions'):
				self.Data_RL.nRegion= int(rdata)
			elif (dat_type=='1D Channel Info'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					self.Channels = ChanInfo(fullpath)
					if (self.Data_1D.nChan != self.Channels.nChan):
						error = True
						message = 'Number of Channels does not match value in .tpc'
						return error, message
			elif (dat_type=='1D Node Info'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					self.nodes = NodeInfo(fullpath)
			elif (dat_type=='1D Water Levels'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					error, message = self.Data_1D.H.Load(fullpath,'H',self.displayname)
					if error:
						return error, message
					self.nTypes = self.nTypes + 1
					self.Types.append('1D Water Levels')
					if self.nTypes == 1:
						self.times = self.Data_1D.H.Values[:,1]
			elif (dat_type=='1D Energy Levels'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					error, message = self.Data_1D.E.Load(fullpath,'H',self.displayname)
					if error:
						return error, message
					self.nTypes = self.nTypes + 1
					self.Types.append('1D Energy Levels')
					if self.nTypes == 1:
						self.times = self.Data_1D.H.Values[:,1]
			elif (dat_type=='Reporting Location Points Water Levels'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					error, message = self.Data_RL.H_P.Load(fullpath,'H',self.displayname)
					if error:
						return error, message
			elif (dat_type=='Reporting Location Lines Flows'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					error, message = self.Data_RL.Q_L.Load(fullpath,'Q',self.displayname)
					if error:
						return error, message
			elif (dat_type=='Reporting Location Regions Volumes'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata)
					error, message = self.Data_RL.Vol_R.Load(fullpath,'Q',self.displayname)
					if error:
						return error, message
			elif (dat_type=='1D Node Maximums'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					error, message = self.Data_1D.Node_Max.Load(fullpath)
					if error:
						return error, message
			elif (dat_type=='1D Channel Maximums'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					error, message = self.Data_1D.Chan_Max.Load(fullpath)
					if error:
						return error, message
			elif (dat_type=='1D Flows'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					error, message = self.Data_1D.Q.Load(fullpath,'Q',self.displayname)
					if error:
						return error, message
					self.nTypes = self.nTypes + 1
					self.Types.append('1D Flows')
					if self.nTypes == 1:
						self.times = self.Data_1D.Q.Values[:,1]
			elif (dat_type=='1D Flow Areas'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					error, message = self.Data_1D.A.Load(fullpath,'A',self.displayname)
					if error:
						return error, message
					self.nTypes = self.nTypes + 1
					self.Types.append('1D Flow Area')
					if self.nTypes == 1:
						self.times = self.Data_1D.Q.Values[:,1]
			elif (dat_type=='1D Velocities'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					error, message = self.Data_1D.V.Load(fullpath,'V',self.displayname)
					if error:
						return error, message
					self.nTypes = self.nTypes + 1
					self.Types.append('1D Velocities')
					if self.nTypes == 1:
						self.times = self.Data_1D.V.Values[:,1]
			elif (dat_type.find('2D Line Flow Area') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					indA = dat_type.index('[')
					indB = dat_type.index(']')
					#self.Data_2D.QA = Timeseries(fullpath,'QA',self.displayname)
					error, message = self.Data_2D.QA.Load(fullpath,'QA',self.displayname)
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
			elif (dat_type.find('2D Line Flow') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					indA = dat_type.index('[')
					indB = dat_type.index(']')
					#self.Data_2D.Q = Timeseries(fullpath,'Q',self.displayname)
					error, message = self.Data_2D.Q.Load(fullpath,'Q',self.displayname)
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
			elif (dat_type.find('2D Point Gauge Level') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					indA = dat_type.index('[')
					indB = dat_type.index(']')
					#self.Data_2D.GL = Timeseries(fullpath,'G',self.displayname)
					error, message = self.Data_2D.GL.Load(fullpath,'G',self.displayname)
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
			elif (dat_type.find('2D Point Water Level') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					indA = dat_type.index('[')
					indB = dat_type.index(']')
					#self.Data_2D.H = Timeseries(fullpath,'H',self.displayname)
					error, message = self.Data_2D.H.Load(fullpath,'H',self.displayname)
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
			elif (dat_type.find('2D Point X-Vel') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					indA = dat_type.index('[')
					indB = dat_type.index(']')
					#self.Data_2D.Vx = Timeseries(fullpath,'VX',self.displayname)
					error, message = self.Data_2D.Vx.Load(fullpath,'VX',self.displayname)
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
			elif (dat_type.find('2D Point Y-Vel') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					indA = dat_type.index('[')
					indB = dat_type.index(']')
					#self.Data_2D.Vy = Timeseries(fullpath,'VY',self.displayname)
					error, message = self.Data_2D.Vy.Load(fullpath,'VY',self.displayname)
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
			elif (dat_type.find('2D Point Velocity') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					indA = dat_type.index('[')
					indB = dat_type.index(']')
					#self.Data_2D.V = Timeseries(fullpath,'V',self.displayname)
					error, message = self.Data_2D.V.Load(fullpath,'V',self.displayname)
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
			elif (dat_type.find('2D Line Integral Flow') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					indA = dat_type.index('[')
					indB = dat_type.index(']')
					#self.Data_2D.QI = Timeseries(fullpath,'QI',self.displayname)
					error, message = self.Data_2D.QI.Load(fullpath,'QI',self.displayname)
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
			elif (dat_type.find('2D Line Structure Flow') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					indA = dat_type.index('[')
					indB = dat_type.index(']')
					#self.Data_2D.QI = Timeseries(fullpath,'QI',self.displayname)
					error, message = self.Data_2D.QS.Load(fullpath,'QS',self.displayname)
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
			elif (dat_type.find('2D Line U/S Structure Water') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					indA = dat_type.index('[')
					indB = dat_type.index(']')
					#self.Data_2D.QI = Timeseries(fullpath,'QI',self.displayname)
					error, message = self.Data_2D.HUS.Load(fullpath,'HU',self.displayname)
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
			elif (dat_type.find('2D Line D/S Structure Water') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					indA = dat_type.index('[')
					indB = dat_type.index(']')
					#self.Data_2D.QI = Timeseries(fullpath,'QI',self.displayname)
					error, message = self.Data_2D.HDS.Load(fullpath,'HD',self.displayname)
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
			elif (dat_type.find('2D Region Average Water Level') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					indA = dat_type.index('[')
					indB = dat_type.index(']')
					error, message = self.Data_2D.HAvg.Load(fullpath,'HA',self.displayname)
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
			elif (dat_type.find('2D Region Max Water Level') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
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
			elif (dat_type.find('2D Region Flow into Region') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
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
			elif (dat_type.find('2D Region Flow out of Region') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
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
			elif (dat_type.find('2D Region Volume') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
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
			elif (dat_type.find('Region Sink/Source') >= 0):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
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
			elif (dat_type=='Reporting Location Points Maximums'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata[2:])
					error, message = self.Data_RL.P_Max.Load(fullpath)
					if error:
						return error, message
			elif (dat_type=='Reporting Location Lines Maximums'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata)
					error, message = self.Data_RL.L_Max.Load(fullpath)
					if error:
						return error, message
			elif (dat_type=='Reporting Location Regions Maximums'):
				if rdata != 'NONE':
					fullpath = os.path.join(self.fpath,rdata)
					error, message = self.Data_RL.R_Max.Load(fullpath)
					if error:
						return error, message
			else:
				print('Warning - Unknown Data Type '+dat_type)
		#successful load
		return error, message