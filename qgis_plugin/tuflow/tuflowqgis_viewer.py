
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import sys
import os
import csv
from PyQt4.Qwt5 import *
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
import numpy
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms")
from ui_tuflowqgis_1d_res import Ui_tuflowqgis_1d_res

class TUFLOW_Res_Dock(QDockWidget, Ui_tuflowqgis_1d_res):
    
	def __init__(self, iface):
        
		QDockWidget.__init__(self)
		Ui_tuflowqgis_1d_res.__init__(self)
		self.setupUi(self)
		self.iface = iface
		self.canvas = self.iface.mapCanvas()
		self.handler = None
		self.selected_layer = None
		self.IDs = []
		self.res = []
		self.idx = -1 #initial
		self.showIt()		

		# Connect signals and slots
		QObject.connect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.connect(self.locationDrop, SIGNAL("currentIndexChanged(int)"), self.loc_changed)       
		QObject.connect(self.ResTypeList, SIGNAL("currentRowChanged(int)"), self.res_type_changed) 
		QObject.connect(self.AddRes, SIGNAL("clicked()"), self.add_res)
		QObject.connect(self.CloseRes, SIGNAL("clicked()"), self.close_res)
		
		
	def __del__(self):
		# Disconnect signals and slots
		QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.disconnect(self.locationDrop, SIGNAL("currentIndexChanged(int)"), self.loc_changed)       
		QObject.disconnect(self.ResTypeList, SIGNAL("currentRowChanged(int)"), self.res_type_changed) 
		QObject.disconnect(self.AddRes, SIGNAL("clicked()"), self.add_res)
		QObject.disconnect(self.CloseRes, SIGNAL("clicked()"), self.close_res)
		try:
			QObject.disconnect(layer,SIGNAL("selectionChanged()"),self.select_changed)
		except:
			QMessageBox.information(self.iface.mainWindow(), "DEBUG", "error disconnecting()")
        
	def refresh(self):
		"""
			Refresh is usually called when the selected layer changes in the legend
			Refresh clears and repopulates the dock widgets, restoring them to their correct values
		"""
		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "refresh()")
		self.cLayer = self.canvas.currentLayer()
		self.layerChanged(self.cLayer)
		self.select_changed()

	def closeup(self):
		"""
			Close up and remove the dock
		"""
		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "closeup()")

	def add_res(self):
		"""
			Add results file
		"""
		# Retrieve the last place we looked if stored
		settings = QSettings()
		lastFolder = str(settings.value("TUFLOW_Res_Dock/lastFolder", os.sep).toString())
		if (len(lastFolder)>0): # use last folder if stored
			fpath = lastFolder
		else:
			cLayer = self.canvas.currentLayer()
			if cLayer: # if layer selected use the path to this
				dp = cLayer.dataProvider()
				ds = dp.dataSourceUri()
				fpath = os.path.dirname(unicode(ds))
			else: # final resort to current working directory
				fpath = os.getcwd()
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Open TUFLOW .info file', fpath, "TUFLOW 1D Results (*.info)")
		inFileName = str(inFileName)
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the path we just looked in
		head, tail = os.path.split(inFileName)
		if head <> os.sep and head.lower() <> 'c:\\' and head <> '':
			settings.setValue("TUFLOW_Res_Dock/lastFolder", head)
		myres=ResData(inFileName)
		QMessageBox.information(self.iface.mainWindow(), "Opened", "Successfully Opened - "+myres.displayname)
		self.res.append(myres)
		self.update_reslist()
	def update_reslist(self):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "update_reslist()")
		self.ResList.clear()
		for res in self.res:
			self.ResList.addItem(res.displayname)
		if (len(self.res)==1):
			item = self.ResList.item(0)
			self.ResList.setItemSelected(item, True)
	def close_res(self):
		"""
			Close results file
		"""
		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "CloseRes()")
		for x in range(0, self.ResList.count()):
			list_item = self.ResList.item(x)
			if list_item.isSelected():
				QMessageBox.information(self.iface.mainWindow(), "DEBUG", "CloseRes()")
				res = self.res[x]
				self.res.remove(res)
				self.update_reslist()

	def layerChanged(self, layer):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "layerChanged()")
		self.cLayer = self.canvas.currentLayer()
		self.sourcelayer.clear()
		self.locationDrop.clear()
		self.IDList.clear()
		if self.cLayer and (self.cLayer.type() == QgsMapLayer.VectorLayer):
			#QMessageBox.information(self.iface.mainWindow(), "DEBUG", self.cLayer.name())
			self.sourcelayer.addItem(self.cLayer.name())
			self.sourcelayer.setCurrentIndex(0)
			GType = self.cLayer.dataProvider().geometryType()
			if (GType == QGis.WKBPoint):
				self.locationDrop.addItem("Node") #this triggers loc_changed which populates data fields
			elif (GType == QGis.WKBLineString):
				self.locationDrop.addItem("Channel")
				self.locationDrop.addItem("Long Profile")
				self.locationDrop.setCurrentIndex(0)
			elif (GType == QGis.WKBPolygon):
				QMessageBox.information(self.iface.mainWindow(), "Information", "Expecting point or line geometry type, not polygon.")
			else:
				QMessageBox.information(self.iface.mainWindow(), "Information", "Expecting point or line geometry type.")
			#index to ID
			self.idx = self.cLayer.fieldNameIndex('ID')
			if (self.idx < 0):
				QMessageBox.information(self.iface.mainWindow(), "Information", "Layer has no field named ID, please choose another layer.")
		else:
			self.sourcelayer.addItem("Invalid layer or no layer selected")
			self.sourcelayer.setCurrentIndex(0)

		if self.handler:
			QObject.disconnect(self.selected_layer, SIGNAL("selectionChanged()"),self.select_changed)
			self.handler = False
			self.selected_layer = None
		if layer is not None:
			if layer.isValid():
				QObject.connect(layer,SIGNAL("selectionChanged()"),self.select_changed)
				self.selected_layer = layer

	def select_changed(self):
		self.IDs = []
		self.IDList.clear()
		if self.idx >= 0:
			for feature in self.cLayer.selectedFeatures():
				#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Feature ID %d: " % feature.id())
				try:
					self.IDs.append(feature.attributeMap()[self.idx].toString()) #extract id for selected feature (from column self.idx) to string
					self.IDList.addItem(feature.attributeMap()[self.idx].toString())
				except:
					QMessageBox.information(self.iface.mainWindow(), "WARNING", "Problem occurred getting data for Feature ID %d: " % feature.id())
		
		# call file writer
		self.start_draw()

	def res_type_changed(self):
		# call redraw
		self.start_draw()
		
	def loc_changed(self):
		loc = self.locationDrop.currentText()
		if (loc == "Node"):
			self.ResTypeList.clear()
			self.ResTypeList.addItem("Level")
		elif (loc == "Channel"):
			self.ResTypeList.clear()
			self.ResTypeList.addItem("Flow")
			self.ResTypeList.addItem("Velocity")
			self.ResTypeList.addItem("US Levels")
			self.ResTypeList.addItem("DS Levels")
		elif (loc == "Long Profile"):
			self.ResTypeList.clear()
			self.ResTypeList.addItem("Level")
		else:
			self.ResTypeList.clear()
		if (len(self.ResTypeList)==1):
			item = self.ResTypeList.item(0)
			self.ResTypeList.setItemSelected(item, True)
		self.start_draw()
	def start_draw(self):
		loc = self.locationDrop.currentText()
		type = []
		
		# Compile of output types
		for x in range(0, self.ResTypeList.count()):
			list_item = self.ResTypeList.item(x)
			if list_item.isSelected():
				type.append(list_item.text())
				#QMessageBox.information(self.iface.mainWindow(), "DEBUG", list_item.text())
		
		# Write .txt file
		draw = True
		if len(type) == 0:
			#QMessageBox.information(self.iface.mainWindow(), "Information", "No results type selected.")
			draw = False
		if len (self.IDs) == 0:
			#QMessageBox.information(self.iface.mainWindow(), "Information", "No elements selected.")
			draw = False
		
		if (draw):
			#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "drawing...")
			self.draw_figure()
	def showIt(self):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "showIt()")
		self.layout = self.frame_for_plot.layout()
		minsize = self.minimumSize()
		maxsize = self.maximumSize()
		self.setMinimumSize(minsize)
		self.setMaximumSize(maxsize)

		self.iface.mapCanvas().setRenderFlag(True)
		
		# matlab figure
		self.artists = []
		labels = []
		
		fig = Figure( (1.0, 1.0), linewidth=0.0, subplotpars = matplotlib.figure.SubplotParams(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0))
			
		font = {'family' : 'arial', 'weight' : 'normal', 'size'   : 12}
		
		rect = fig.patch
		rect.set_facecolor((0.9,0.9,0.9))
		self.subplot = fig.add_axes((0.10, 0.15, 0.85,0.82))
		self.subplot.set_xbound(0,1000)
		self.subplot.set_ybound(0,1000)			
		self.manageMatplotlibAxe(self.subplot)
		canvas = FigureCanvasQTAgg(fig)
		sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		sizePolicy.setHorizontalStretch(0)
		sizePolicy.setVerticalStretch(0)
		canvas.setSizePolicy(sizePolicy)
		self.plotWdg = canvas
		
		self.gridLayout.addWidget(self.plotWdg)
		mpltoolbar = matplotlib.backends.backend_qt4agg.NavigationToolbar2QTAgg(self.plotWdg, self.frame_for_plot)
			
		#create curve
		label = "test"
		x=numpy.linspace(-numpy.pi, numpy.pi, 201)
		y=numpy.sin(x)
		a, = self.subplot.plot(x, y)
		self.artists.append(a)
		labels.append(label)
		self.subplot.hold(True)
		self.plotWdg.draw()
	
	def manageMatplotlibAxe(self, axe1):
		axe1.grid()
		axe1.tick_params(axis = "both", which = "major", direction= "out", length=10, width=1, bottom = True, top = False, left = True, right = False)
		axe1.minorticks_on()
		axe1.tick_params(axis = "both", which = "minor", direction= "out", length=5, width=1, bottom = True, top = False, left = True, right = False)
	
	def draw_figure(self):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "draw_figure()")
		self.subplot.clear()
		xmin=0.0
		xmax=0.0
		ymin=0.0
		ymax=0.0

		rtists = []
		labels = []
		
		loc = self.locationDrop.currentText()
		ydataids = self.IDs
		typeids = []
		typenames = []
		for x in range(0,self.ResTypeList.count()):
			list_item = self.ResTypeList.item(x)
			if list_item.isSelected():
				typeids.append(x)
				typenames.append(list_item.text())
		
		# Compile Selected Results Files
		reslist = []
		resnames = []
		for x in range(0, self.ResList.count()):
			list_item = self.ResList.item(x)
			if list_item.isSelected():
				reslist.append(x)
				resnames.append(list_item.text())

		for resno in reslist:
			res = self.res[resno]
			#Long Profiles___________________________________________________________________
			if (loc=="Long Profile"): # LP
				if (len(ydataids)==0):
					skip = True
				elif (len(ydataids)==1):
					chanList,chanIDs = res.getLPData(ydataids[0],None,self.iface)
					xdata = res.LP_xval
					ydata =res.LP_yval
				elif (len(ydataids)==2):
					chanList,chanIDs = res.getLPData(ydataids[0],ydataids[1],self.iface)
					xdata = res.LP_xval
					ydata =res.LP_yval
				else:
					#print 'WARNING - Maximum of 2 channels used for long profile plotting.'
					QMessageBox.information(self.iface.mainWindow(), "WARNING", "Maximum of 2 channels used for long profile plotting.")
					
					chanList,chanIDs = res.getLPData(ydataids[0],ydataids[1],self.iface)
					xdata = res.LP_xval
					ydata =res.LP_yval

				xmin=round(min(xdata), 0) - 1
				xmax=round(max(xdata), 0) + 1
				ymin=round(min(ydata), 0) - 1
				ymax=round(max(ydata), 0) + 1
				label = 'lp testing'
				self.subplot.set_xbound(lower=xmin, upper=xmax)
				self.subplot.set_ybound(lower=ymin, upper=ymax)
				a, = self.subplot.plot(xdata, ydata)
				self.artists.append(a)
				labels.append(label)
				self.subplot.hold(True)


			#Timeseries______________________________________________________________________
			else:
				xdata = res.getXData()
				for ydataid in self.IDs:
					for typename in typenames:
						#QMessageBox.information(self.iface.mainWindow(), "DEBUG", ydataid)
						found, ydata=res.getYData(ydataid,typename,loc, self.iface)
						if not found:
							ydata = xdata * 0.0 # keep the same dimensions other the plot will fail
						if (len(reslist) > 1):
							label = res.displayname + ": " + ydataid + " - " + typename
						else:
							label = ydataid + " - " + typename

						xmin=round(min(xdata), 0) - 1
						xmax=round(max(xdata), 0) + 1
						ymin=round(min(ydata), 0) - 1
						ymax=round(max(ydata), 0) + 1
						self.subplot.set_xbound(lower=xmin, upper=xmax)
						self.subplot.set_ybound(lower=ymin, upper=ymax)
						a, = self.subplot.plot(xdata, ydata)
						self.artists.append(a)
						labels.append(label)
						self.subplot.hold(True)

			#Set axis labels
			if (loc=="Long Profile"): # LP
				if (res.units == 'METRIC'):
					self.subplot.set_xlabel('Distance (m)')
				elif (res.units == 'ENGLISH'):
					self.subplot.set_xlabel('Distance (ft)')
				else:
					self.subplot.set_xlabel('Distance')
			else:
				self.subplot.set_xlabel('Time (hours)')

			if (len(typeids) == 1):
				self.subplot.set_ylabel(typenames[0])
			else:
				self.subplot.set_title("")

		self.subplot.hold(False)
		self.subplot.grid(True)
		self.plotWdg.draw()
		
class ResData():
	"""
	ResData class
	"""

	def getXData(self):
		return self.Head['Time']

	def getYData(self, id,typeid,loc, iface):
		#QMessageBox.information(iface.mainWindow(), "DEBUG", id)
		if (loc=="Node"): #nodes
			if (typeid=="Level"): # head
				try:
					cleanname = str(id.replace('.','p')) #dtype.name cannot handle decimals in names, these have been replaced with 'p'
					cleanname = cleanname.strip()        # remove leading / trailing whitespace
					return True, self.Head[cleanname]
				except:
					QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(id)))
					return False, [0.0]
			else:
				QMessageBox.critical(iface.mainWindow(),"ERROR", ("Should not be here: getYData()"))
		else: # channels
			if (typeid=="Flow"): # Flow
				try:
					cleanname = str(id.replace('.','p')) #dtype.name cannot handle decimals in names, these have been replaced with 'p'
					cleanname = cleanname.strip()        # remove leading / trailing whitespace
					return True, self.Flow[cleanname]
				except:
					QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(id)))
					return False, [0.0]
			elif (typeid=="Velocity"):
				try:
					cleanname = str(id.replace('.','p')) #dtype.name cannot handle decimals in names, these have been replaced with 'p'
					cleanname = cleanname.strip()        # remove leading / trailing whitespace
					return True, self.Velocity[cleanname]
				except:
					QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(id)))
					return False, [0.0]
			elif (typeid=="US Levels"): # upstream level
				chan_list = tuple(self.Info['Channel'])
				ind = chan_list.index(str(id))
				a = str(self.Info['US_Node'][ind])
				cleanname = str(a.replace('.','p')) #dtype.name cannot handle decimals in names, these have been replaced with 'p'
				cleanname = cleanname.strip()        # remove leading / trailing whitespace
				try:
					return True, self.Head[cleanname]
				except:
					QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(a)))
					return False, [0.0]
			elif (typeid=="DS Levels"): # dowsntream level
				chan_list = tuple(self.Info['Channel'])
				ind = chan_list.index(str(id))
				a = str(self.Info['DS_Node'][ind])
				cleanname = str(a.replace('.','p')) #dtype.name cannot handle decimals in names, these have been replaced with 'p'
				cleanname = cleanname.strip()        # remove leading / trailing whitespace
				try:
					return True, self.Head[cleanname]
				except:
					QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(a)))
					return False, [0.0]
			else:
				raise RuntimeError("Should not be here")

	def getLPData(self,id1,id2, iface):
		self.LP_chanlist = []
		if (id2 == None): # only one channel selected
			finished = False
			i = 0
			chan_list = tuple(self.Info['Channel'])
			ind1 = chan_list.index(str(id1))
			self.LP_chanlist = [id1]
			self.LP_chanID = [ind1]
			self.LP_ndlist = [self.Info['US_Node'][ind1]]
			self.LP_ndlist.append(self.Info['DS_Node'][ind1])
			self.LP_xval = [0.0]
			self.LP_xval.append(self.Info['Length'][ind1])
			id = ind1
			while not finished:
				i = i + 1
				chan = self.Info['DS_Channel'][id]
				if(chan=='------'):
					finished = True
				else:
					self.LP_chanlist.append(chan)
					id = int(numpy.where(self.Info['Channel']==chan)[0])
					self.LP_chanID.append(id)
					cur_len = self.LP_xval[len(self.LP_xval)-1]
					cur_len = cur_len + self.Info['Length'][id]
					self.LP_xval.append(cur_len)
					self.LP_ndlist.append(self.Info['DS_Node'][id])
		else:
			#QMessageBox.information(iface.mainWindow(), "DEBUG", "Two channels selected.")
			finished = False
			found = False
			i = 0
			chan_list = tuple(self.Info['Channel'])
			ind1 = chan_list.index(str(id1))
			ind2 = chan_list.index(str(id2))
			endchan = id2
			self.LP_chanlist = [id1]
			self.LP_chanID = [ind1]
			self.LP_ndlist = [self.Info['US_Node'][ind1]]
			self.LP_ndlist.append(self.Info['DS_Node'][ind1])
			self.LP_xval = [0.0]
			self.LP_xval.append(self.Info['Length'][ind1])
			id = ind1
			while not finished:
				i = i + 1
				chan = self.Info['DS_Channel'][id]
				#QMessageBox.information(iface.mainWindow(), "DEBUG", chan)
				if(chan=='------'):
					finished = True
				elif(chan==endchan):
					found = True
					finished = True
					self.LP_chanlist.append(chan)
					id = int(numpy.where(self.Info['Channel']==chan)[0])
					self.LP_chanID.append(id)
					cur_len = self.LP_xval[len(self.LP_xval)-1]
					cur_len = cur_len + self.Info['Length'][id]
					self.LP_xval.append(cur_len)
					self.LP_ndlist.append(self.Info['DS_Node'][id])
				else:
					self.LP_chanlist.append(chan)
					id = int(numpy.where(self.Info['Channel']==chan)[0])
					self.LP_chanID.append(id)
					cur_len = self.LP_xval[len(self.LP_xval)-1]
					cur_len = cur_len + self.Info['Length'][id]
					self.LP_xval.append(cur_len)
					self.LP_ndlist.append(self.Info['DS_Node'][id])

			if not (found): # id2 is not downstream of 1d1, reverse direction and try again...
				#QMessageBox.information(iface.mainWindow(), "DEBUG", "reverse direction and try again")
				finished = False
				found = False
				i = 0
				endchan = id1
				self.LP_chanlist = [id2]
				self.LP_chanID = [ind2]
				self.LP_ndlist = [self.Info['US_Node'][ind2]]
				self.LP_ndlist.append(self.Info['DS_Node'][ind2])
				self.LP_xval = [0.0]
				self.LP_xval.append(self.Info['Length'][ind2])
				id = ind2
				while not finished:
					i = i + 1
					chan = self.Info['DS_Channel'][id]
					#QMessageBox.information(iface.mainWindow(), "DEBUG", chan)
					if(chan=='------'):
						finished = True
					elif(chan==endchan):
						found = True
						finished = True
						self.LP_chanlist.append(chan)
						id = int(numpy.where(self.Info['Channel']==chan)[0])
						self.LP_chanID.append(id)
						cur_len = self.LP_xval[len(self.LP_xval)-1]
						cur_len = cur_len + self.Info['Length'][id]
						self.LP_xval.append(cur_len)
						self.LP_ndlist.append(self.Info['DS_Node'][id])
					else:
						self.LP_chanlist.append(chan)
						id = int(numpy.where(self.Info['Channel']==chan)[0])
						self.LP_chanID.append(id)
						cur_len = self.LP_xval[len(self.LP_xval)-1]
						cur_len = cur_len + self.Info['Length'][id]
						self.LP_xval.append(cur_len)
						self.LP_ndlist.append(self.Info['DS_Node'][id])
			if not (found): # id1 and 1d2 not connected
				QMessageBox.information(iface.mainWindow(), "Information", "Channels not connected")
				self.LP_xval = [0.0]
				self.LP_yval = [0.0]
				return [], []
				
		self.LP_yval = []
		for nd in self.LP_ndlist:
			a = nd.replace('.','p')
			yvals = self.Head[a]
			self.LP_yval.append(max(yvals))

		return self.LP_chanlist, self.LP_chanID

	def __init__(self, fname):
		self.filename = fname
		#print self.filename
		self.fpath = os.path.dirname(fname)
		self.nTypes = 0
		data = numpy.genfromtxt(fname, dtype=None, delimiter="==")
		for i in range (0,len(data)):
			tmp = data[i,0]
			dat_type = tmp.strip()
			#print dat_type
			tmp = data[i,1]
			rdata = tmp.strip()
			if (dat_type=='Simulation ID'):

				self.displayname = rdata
				#print 'Run ID = ' + self.displayname
			elif (dat_type=='Number Channels'):
				self.nChannels = int(rdata)
			elif (dat_type=='Units'):
				self.units = rdata
			elif (dat_type=='Format Version'):
				self.formatVersion = int(rdata)
			elif (dat_type=='Number Nodes'):
				self.nNodes = int(rdata)
			elif (dat_type=='Channel Info'):
				fullpath = os.path.join(self.fpath,rdata)
				self.Info = numpy.genfromtxt(fullpath, dtype=None, delimiter=",",names=True)
				#print'Done.'

                #Clean double quotes ('"data"' become 'data') from the info.csv, otherwise this causes issues later
				self.Channels = []
				for chan in self.Info['Channel']:
					tmp = chan.replace('"','')
					self.Channels.append(tmp)
				self.Info['Channel'] = self.Channels

				tmpUS_nodes = []
				for node in self.Info['US_Node']:
					tmp = node.replace('"','')
					tmpUS_nodes.append(tmp)
				self.Info['US_Node'] = tmpUS_nodes

				tmpDS_nodes = []
				for node in self.Info['DS_Node']:
					tmp = node.replace('"','')
					tmpDS_nodes.append(tmp)
				self.Info['DS_Node'] = tmpDS_nodes

				tmpUS_chan = []
				for chan in self.Info['US_Channel']:
					tmp = chan.replace('"','')
					tmpUS_chan.append(tmp)
				self.Info['US_Channel'] = tmpUS_chan

				tmpDS_chan = []
				for chan in self.Info['DS_Channel']:
					tmp = chan.replace('"','')
					tmpDS_chan.append(tmp)
				self.Info['DS_Channel'] = tmpDS_chan

				tmpFlag = []
				for flag in self.Info['Flags']:
					tmp = flag.replace('"','')
					tmpFlag.append(tmp)
				self.Info['Flags'] = tmpFlag

				if (self.nChannels != len(self.Channels)):
					raise RuntimeError("Number of Channels does not match value in .1drf")

			elif (dat_type=='Node Info'):
				fullpath = os.path.join(self.fpath,rdata)
				#print 'Extracting info from: '+ fullpath
				#print 'WARNING - Node Info not yet implemented'
				# due to variable number of channels, need to write custom read not use numpy
				# chat with Bill about using another seperator ((|)
				#self.ndInfo = numpy.genfromtxt(fullpath, dtype=None, delimiter=",",names=True)
				#print'Done.'

			elif (dat_type=='Water Levels'):
				fullpath = os.path.join(self.fpath,rdata)
				#print 'Extracting header information from: '+ fullpath
				with open(fullpath, 'rb') as csvfile:
					reader = csv.reader(csvfile, delimiter=',', quotechar='"')
					header = reader.next()
					print header
				csvfile.close()
				#print 'Done extracting header.'
				header[0]='Timestep'
				header[1]='Time'
				types = ['']
				types[0]='i8'
				types.append('d')
				self.Nodes = []
				i=1
				for col in header[2:]:
					i= i+1
					a = col[2:]
					self.Nodes.append(a)
					b = a.replace('.','p')
					header[i] = b
					types.append('d')
				dt = numpy.dtype({'names':header,'formats':types})
				#print 'Extracting data from: '+ fullpath
				self.Head = numpy.genfromtxt(fullpath, dtype=dt, delimiter=",", skip_header=1)
				#print'Done extracting data.'

				if (self.nNodes != len(self.Nodes)):
					raise RuntimeError("Number of Nodes does not match value in .1drf")

				self.nTypes = self.nTypes + 1
				if (self.nTypes == 1):
					self.types = ['Head']
				else:
					self.types.append('Head')
			elif (dat_type=='Flows'):
				fullpath = os.path.join(self.fpath,rdata)
				#print 'Extracting header information from: '+ fullpath
				with open(fullpath, 'rb') as csvfile:
					reader = csv.reader(csvfile, delimiter=',', quotechar='"')
					header = reader.next()
					print header
				csvfile.close()
				#print 'Done extracting header.'
				header[0]='Timestep'
				header[1]='Time'
				types = ['']
				types[0]='i8'
				types.append('d')
				i=1
				for col in header[2:]:
					i= i+1
					a = col[2:]
					b = a.replace('.','p')
					header[i] = b
					types.append('d')
				dt = numpy.dtype({'names':header,'formats':types})
				#print 'Extracting data from: '+ fullpath
				self.Flow = numpy.genfromtxt(fullpath, dtype=dt, delimiter=",", skip_header=1)
				#print'Done extracting data.'
				self.nTypes = self.nTypes + 1
				if (self.nTypes == 1):
					self.types = ['Flow']
				else:
					self.types.append('Flow')
			elif (dat_type=='Velocities'):
				fullpath = os.path.join(self.fpath,rdata)
				#print 'Extracting header information from: '+ fullpath
				with open(fullpath, 'rb') as csvfile:
					reader = csv.reader(csvfile, delimiter=',', quotechar='"')
					header = reader.next()
					#print header
				csvfile.close()
				#print 'Done extracting header.'
				header[0]='Timestep'
				header[1]='Time'
				types = ['']
				types[0]='i8'
				types.append('d')
				i=1
				for col in header[2:]:
					i= i+1
					a = col[2:]
					b = a.replace('.','p')
					header[i] = b
					types.append('d')
				dt = numpy.dtype({'names':header,'formats':types})
				#print 'Extracting data from: '+ fullpath
				self.Velocity = numpy.genfromtxt(fullpath, dtype=dt, delimiter=",", skip_header=1)
				#print'Done extracting data.'
				self.nTypes = self.nTypes + 1
				if (self.nTypes == 1):
					self.types = ['Velocity']
				else:
					self.types.append('Velocity')
		print 'Read '+str(self.nTypes)+' data types.'