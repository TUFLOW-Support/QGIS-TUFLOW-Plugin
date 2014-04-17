
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import sys
import os
import csv
#from PyQt4.Qwt5 import *
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
import numpy
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms")
from ui_tuflowqgis_1d_res import Ui_tuflowqgis_1d_res
#from time import sleep
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
		QObject.connect(self.pbAnimateLP, SIGNAL("clicked()"), self.animate_LP)
		QObject.connect(self, SIGNAL("visibilityChanged(bool)"), self.visChanged)
		QObject.connect(self.listTime, SIGNAL("currentRowChanged(int)"), self.timeChanged) 
		
	def __del__(self):
		# Disconnect signals and slots
		QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.disconnect(self.locationDrop, SIGNAL("currentIndexChanged(int)"), self.loc_changed)       
		QObject.disconnect(self.ResTypeList, SIGNAL("currentRowChanged(int)"), self.res_type_changed) 
		QObject.disconnect(self.AddRes, SIGNAL("clicked()"), self.add_res)
		QObject.disconnect(self.CloseRes, SIGNAL("clicked()"), self.close_res)
		QObject.disconnect(self.pbAnimateLP, SIGNAL("clicked()"), self.animate_LP)
		QObject.disconnect(self, SIGNAL("visibilityChanged(bool)"), self.visChanged)
		QObject.disconnect(self.listTime, SIGNAL("currentRowChanged(int)"), self.timeChanged)

		try:
			QObject.disconnect(layer,SIGNAL("selectionChanged()"),self.select_changed)
		except:
			#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Disconnecting selectionChanged Signal ")
			warning = True

	def visChanged(self, vis):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Vis is " + str(vis))
		#if vis:
		#	QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Vis true")
		if not vis:
			QMessageBox.information(self.iface.mainWindow(), "Information", "Dock visibility turned off - deactivating dock.")
			self.deactivate()
			QMessageBox.information(self.iface.mainWindow(), "Information", "Exiting")
			return

	def deactivate(self):
		# Disconnect signals and slots
		QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.disconnect(self.locationDrop, SIGNAL("currentIndexChanged(int)"), self.loc_changed)       
		QObject.disconnect(self.ResTypeList, SIGNAL("currentRowChanged(int)"), self.res_type_changed) 
		QObject.disconnect(self.AddRes, SIGNAL("clicked()"), self.add_res)
		QObject.disconnect(self.CloseRes, SIGNAL("clicked()"), self.close_res)
		QObject.disconnect(self.pbAnimateLP, SIGNAL("clicked()"), self.animate_LP)
		QObject.disconnect(self, SIGNAL("visibilityChanged(bool)"), self.visChanged)
		QObject.disconnect(self.listTime, SIGNAL("currentRowChanged(int)"), self.timeChanged)
		try:
			QObject.disconnect(layer,SIGNAL("selectionChanged()"),self.select_changed)
		except:
			#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "error disconnecting()")
			warning = True
			
	def refresh(self):
		"""
			Refresh is usually called when the selected layer changes in the legend
			Refresh clears and repopulates the dock widgets, restoring them to their correct values
		"""
		self.cLayer = self.canvas.currentLayer()
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
		lastFolder = str(settings.value("TUFLOW_Res_Dock/lastFolder", os.sep))
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
		myres=ResData(inFileName,self.iface)
		QMessageBox.information(self.iface.mainWindow(), "Opened", "Successfully Opened - "+myres.displayname)
		self.res.append(myres)
		self.update_reslist()
	def update_reslist(self):
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
		for x in range(0, self.ResList.count()):
			list_item = self.ResList.item(x)
			if list_item.isSelected():
				res = self.res[x]
				self.res.remove(res)
				self.update_reslist()

	def layerChanged(self, layer):
		self.cLayer = self.canvas.currentLayer()
		self.sourcelayer.clear()
		self.locationDrop.clear()
		self.IDs = []
		self.IDList.clear()
		if self.cLayer and (self.cLayer.type() == QgsMapLayer.VectorLayer):
			self.sourcelayer.addItem(self.cLayer.name())
			self.sourcelayer.setCurrentIndex(0)
			GType = self.cLayer.dataProvider().geometryType()
			if (GType == QGis.WKBPoint):
				self.locationDrop.addItem("Node") #this triggers loc_changed which populates data fields
			elif (GType == QGis.WKBLineString):
				self.locationDrop.addItem("Channel")
				self.locationDrop.addItem("Long Profile")
				self.locationDrop.setCurrentIndex(0)
			else:
				self.sourcelayer.clear()
				self.sourcelayer.addItem("Not a line or point geometry (plot disabled)")
			
			#index to ID
			self.idx = self.cLayer.fieldNameIndex('ID')
			if (self.idx < 0):
				self.locationDrop.clear()
				self.locationDrop.addItem("No field named ID in layer (plot disabled)")
		else:
			self.sourcelayer.addItem("Invalid layer or no layer selected (plot disabled)")
			self.sourcelayer.setCurrentIndex(0)
			self.locationDrop.addItem("No field named ID in layer (plot disabled)")

		if self.handler:
			QObject.disconnect(self.selected_layer, SIGNAL("selectionChanged()"),self.select_changed)
			self.handler = False
			self.selected_layer = None
		if layer is not None:
			if layer.isValid():
				QObject.connect(layer,SIGNAL("selectionChanged()"),self.select_changed)
				self.selected_layer = layer
		self.refresh()
		
	def select_changed(self):
		self.IDs = []
		self.IDList.clear()
		if self.idx >= 0:
			if self.cLayer:
				try:
					for feature in self.cLayer.selectedFeatures():
						try:
							fieldvalue=feature['ID']
							self.IDs.append(fieldvalue)
							self.IDList.addItem(fieldvalue)
						except:
							warning = True #suppress the warning below, most likely due to a "X" type channel or blank name
				except:
					error = True
		
		# call file writer
		self.start_draw()
	def timeChanged(self):
		self.start_draw()
	def res_type_changed(self):
		# call redraw
		self.select_changed()
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
			self.ResTypeList.addItem("Max Water Level")
			self.ResTypeList.addItem("Water Level at Time")
			self.ResTypeList.addItem("Bed Level")
			self.ResTypeList.addItem("Left Bank Obvert")
			self.ResTypeList.addItem("Right Bank Obvert")
			self.ResTypeList.addItem("Pit Ground Levels (if any)")
			# add times
			nDec = 4
			try:
				times = self.res[0].getXData()
				self.listTime.clear()
				for time in times:
					self.listTime.addItem("%.4f" % time)
				item = self.listTime.item(0)
				self.listTime.setItemSelected(item, True)
			except:
				QMessageBox.information(self.iface.mainWindow(), "WARNING", "Unable to populate times, check results loaded.")
		else:
			self.ResTypeList.clear()
		item = self.ResTypeList.item(0) # select 1st item by default
		self.ResTypeList.setItemSelected(item, True)
		self.start_draw()

	def animate_LP(self):
		start = True
		
		# check if long profile type is selected
		loc = self.locationDrop.currentText()
		if (loc!="Long Profile"): # LP
			QMessageBox.critical(self.iface.mainWindow(), "ERROR", "Please choose Long Profile type before animating.")
			start = False
		
		# check for valid selection
		if len (self.IDs) == 0:
			QMessageBox.critical(self.iface.mainWindow(), "ERROR", "No elements selected.")
			start = False
		elif len (self.IDs) > 2:
			QMessageBox.critical(self.iface.mainWindow(), "ERROR", "More than 2 ID's selected.")
			start = False
		
		# Compile of output types (bed level, max wse)
		restype = []
		for x in range(0, self.ResTypeList.count()):
			list_item = self.ResTypeList.item(x)
			if list_item.isSelected():
				restype.append(list_item.text())
				
		# results:
		ResIndexs = []
		if self.ResList.count() == 0:
			QMessageBox.critical(self.iface.mainWindow(), "ERROR", "No results open...")
			start = False
		else:
			for x in range(0, self.ResList.count()):
				list_item = self.ResList.item(x)
				if list_item.isSelected():
					ResIndexs.append(x)
		# times
		if self.listTime.count() == 0:
			QMessageBox.critical(self.iface.mainWindow(), "ERROR", "No output times detected.")
			start = False
		
		nWidth = 5
		if self.listTime.count() < 11:
			nWidth = 1
		elif self.listTime.count() < 101:
			nWidth = 2
		elif self.listTime.count() < 1001:
			nWidth = 3
		elif self.listTime.count() < 10001:
			nWidth = 4
		if start:
			try:
				QMessageBox.information(self.iface.mainWindow(), "Information", "Saving images to: "+self.res[0].fpath+"\nAfter selecting ok, please wait while the images are created.\nYou will be notified when this has finished.")
				for x in range(0, self.listTime.count()):
					item = self.listTime.item(x)
					self.listTime.setItemSelected(item, True)
					self.draw_figure()
					filenum = str(x+1)
					filenum = filenum.zfill(nWidth)
					fname = 'QGIS_LP_'+filenum+'.png'
					fullpath = os.path.join(self.res[0].fpath,fname)
					self.plotWdg.figure.savefig(fullpath)
					self.listTime.setItemSelected(item, False)
				QMessageBox.information(self.iface.mainWindow(), "Information", "Processing Complete")
			except:
				QMessageBox.critical(self.iface.mainWindow(), "ERROR", "An error occurred processing long profile")
			
	def start_draw(self):
		loc = self.locationDrop.currentText()
		type = []
		
		# Compile of output types
		for x in range(0, self.ResTypeList.count()):
			list_item = self.ResTypeList.item(x)
			if list_item.isSelected():
				type.append(list_item.text())
		draw = True
		if len(type) == 0:
			draw = False
		if len (self.IDs) == 0:
			draw = False
		
		if (draw):
			self.draw_figure()
	def showIt(self):
		self.layout = self.frame_for_plot.layout()
		minsize = self.minimumSize()
		maxsize = self.maximumSize()
		self.setMinimumSize(minsize)
		self.setMaximumSize(maxsize)

		self.iface.mapCanvas().setRenderFlag(True)
		
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
		self.subplot.clear()
		xmin=0.0
		xmax=0.0
		ymin=0.0
		ymax=0.0

		self.artists = []
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
		nRes = len(reslist)
		
		for i, resno in enumerate(reslist):
			res = self.res[resno]
			name = resnames[i]
			#Long Profiles___________________________________________________________________
			if (loc=="Long Profile"): # LP
				plot = True
				if (len(ydataids)==0):
					plot = False
				elif (len(ydataids)==1):
					chanList,chanIDs = res.getLPData(ydataids[0],None,self.iface)
				elif (len(ydataids)==2):
					chanList,chanIDs = res.getLPData(ydataids[0],ydataids[1],self.iface)
				else:
					QMessageBox.information(self.iface.mainWindow(), "WARNING", "Maximum of 2 channels used for long profile plotting.")			
					chanList,chanIDs = res.getLPData(ydataids[0],ydataids[1],self.iface)
				
				# if data returned from above do stuff, else bail
				if chanList:				
					xdata = res.LP_xval
					ydata = res.LP_yval
					zb_zdata = res.LP_bed
					zb_ch_data = res.LP_chainage
					lb_data = res.LP_LB
					rb_data = res.LP_RB
					pitx = res.pitx
					pitz = res.pitz
					npits = res.npits
					xmin=round(min(xdata), 0) - 1
					xmax=round(max(xdata), 0) + 1
					ymin=round(min(zb_zdata), 0) - 1
					ymax=round(max(ydata), 0) + 1
					self.subplot.set_xbound(lower=xmin, upper=xmax)
					self.subplot.set_ybound(lower=ymin, upper=ymax)

					
					# plot max water level
					if typenames.count('Max Water Level')<>0:
						a, = self.subplot.plot(xdata, ydata)
						self.artists.append(a)
						label = 'Max Water Level'
						if nRes > 1:
							labels.append(label +" - "+name)
						else:
							labels.append(label)
						self.subplot.hold(True)
					
					#plot bed
					if typenames.count('Bed Level')<>0:
						a, = self.subplot.plot(zb_ch_data, zb_zdata)
						self.artists.append(a)
						label = 'Bed Level'
						if nRes > 1:
							labels.append(label +" - "+name)
						else:
							labels.append(label)
						self.subplot.hold(True)

					#plot LB
					if typenames.count('Left Bank Obvert')<>0:
						a, = self.subplot.plot(zb_ch_data, lb_data)
						self.artists.append(a)
						label = 'Left Bank'
						if nRes > 1:
							labels.append(label +" - "+name)
						else:
							labels.append(label)
						self.subplot.hold(True)

					#plot RB
					if typenames.count('Right Bank Obvert')<>0:
						a, = self.subplot.plot(zb_ch_data, rb_data)
						self.artists.append(a)
						label = 'Right Bank'
						if nRes > 1:
							labels.append(label +" - "+name)
						else:
							labels.append(label)
						self.subplot.hold(True)
						
					#plot LP at time
					if typenames.count('Water Level at Time')<>0:
						timeInd = 0
						list_item = self.listTime.item(0)
						timeStr = list_item.text()
						for x in range(0, self.listTime.count()):
							list_item = self.listTime.item(x)
							if list_item.isSelected():
								timeInd = x
								timeStr = list_item.text()
						temporalLP = res.getLPatTime(timeInd,self.iface)
						a, = self.subplot.plot(xdata, temporalLP)
						self.artists.append(a)
						label = 'Water Level at '+timeStr
						if nRes > 1:
							labels.append(label +" - "+name)
						else:
							labels.append(label)
						self.subplot.hold(True)
					
					#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "plotting pit")
					#plot pits
					if typenames.count('Pit Ground Levels (if any)')<>0:
						if npits > 0:
							a, = self.subplot.plot(pitx, pitz, marker='o', linestyle='None', color='r')
							self.artists.append(a)
							labels.append("Pit Invert (grate) levels")
					#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "success")
					
			#Timeseries______________________________________________________________________
			else:
				xdata = res.getXData()
				breakloop = False
				for ydataid in self.IDs:
					if ydataid:
						for typename in typenames:
							#QMessageBox.information(self.iface.mainWindow(), "DEBUG", ydataid)
							if not breakloop:
								found, ydata=res.getYData(ydataid,typename,loc, self.iface)
								if not found:
									ydata = xdata * 0.0 # keep the same dimensions other the plot will fail
									QMessageBox.information(self.iface.mainWindow(), "ERROR", "Exiting plot update - plot may be partially updated.")
									breakloop = True
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
		
		if self.cbShowLegend.isChecked():
			self.subplot.legend(self.artists, labels, bbox_to_anchor=(0, 0, 1, 1))
			
		self.subplot.hold(False)
		self.subplot.grid(True)
		self.plotWdg.draw()

		
class NodeInfo():
	"""
	Node Info data class
	"""
	def __init__(self,fullpath,iface):
		#QMessageBox.information(iface.mainWindow(),"debug", "well here we are in NodeInfo / init")
		self.node_num = []
		self.node_name = []
		self.node_bed = []
		self.node_top = []
		self.node_nChan = []
		self.node_channels = []
		with open(fullpath, 'rb') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			header = reader.next()
			for (counter, row) in enumerate(reader):
				self.node_num.append(int(row[0]))
				self.node_name.append(row[1])
				self.node_bed.append(float(row[2]))
				self.node_top.append(float(row[3]))
				self.node_nChan.append(int(row[4]))
				chanlist = row[5:]
				if len(chanlist) != int(row[4]):
					QMessageBox.information(iface.mainWindow(),"ERROR", ("Number of channels connected to ID doesn't match. ID: " + str(row[1])))
				else:
					self.node_channels.append(chanlist)
		csvfile.close()

class ChanInfo():
	"""
	Channel Info data class
	"""
	def __init__(self,fullpath,iface):		
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
		
		with open(fullpath, 'rb') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			header = reader.next()
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
class ResData():
	"""
	ResData class for reading a processing results
	"""

	def getXData(self):
		return self.Head[:,1]

	def getYData(self, id,typeid,loc, iface):
		#QMessageBox.information(iface.mainWindow(), "DEBUG", id)
		if (loc=="Node"): #nodes
			if (typeid=="Level"): # head
				if id: #not NULL
					a = id.strip()
					try:
						ind = self.nodeH_Header.index(str(a))
					except:
						QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + a))
						return False, [0.0]
					#get data
					try:
						return True, self.Head[:,ind]
					except:
						QMessageBox.information(iface.mainWindow(),"ERROR", ("Extracting head for index: " + str(ind)))
						return False, [0.0]
				else: #null item, don't error just return nothing
					return False, [0.0]
			else:
				QMessageBox.critical(iface.mainWindow(),"ERROR", ("Should not be here: getYData()"))
		else: # channels
			if (typeid=="Flow"): # Flow
				# find data
				if id: #not null
					a = id.strip()
					try:
						ind = self.chanQ_Header.index(str(a))
					except:
						QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(id)))
						return False, [0.0]
				else: # NULL id
					return False, [0.0]
				# extract data
				try:
					flow = self.Flow[:,ind]
				except:
					QMessageBox.information(iface.mainWindow(),"Error", ("Unable to extract data from self.Flow, index is: " + str(ind)))
					return False, [0.0]
				# normal return
				return True, flow
			elif (typeid=="Velocity"):
				# find data
				if id: # not NULL
					a = id.strip()
					try:
						ind = self.chanV_Header.index(str(a))
					except:
						QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(id)))
						return False, [0.0]
				else: # NULL id 
					return False, [0.0]
					
				# extract data
				try:
					vel = self.Velocity[:,ind]
				except:
					QMessageBox.information(iface.mainWindow(),"Error", ("Unable to extract data from self.Flow, index is: " + str(ind)))
					return False, [0.0]
				# normal return
				return True, vel
				
			elif (typeid=="US Levels"): # upstream level
				#chan_list = tuple(self.Info['Channel'])
				chan_list = tuple(self.Channels.chan_name)
				ind = chan_list.index(str(id))
				#a = str(self.Info['US_Node'][ind])
				a = str(self.Channels.chan_US_Node[ind])
				try:
					ind = self.nodeH_Header.index(a)
				except:
					QMessageBox.information(iface.mainWindow(),"Error", ("Unable to find US node: ",+a+" for channel "+ id))
				try:
					return True, self.Head[:,ind]
				except:
					QMessageBox.information(iface.mainWindow(),"Error", ("Unable to extract data for US node: ",+a+" for channel "+ id))
					return False, [0.0]
			elif (typeid=="DS Levels"): # dowsntream level
				#chan_list = tuple(self.Info['Channel'])
				chan_list = tuple(self.Channels.chan_name)
				ind = chan_list.index(str(id))
				#a = str(self.Info['DS_Node'][ind])
				a = str(self.Channels.chan_DS_Node[ind])
				try:
					ind = self.nodeH_Header.index(a)
				except:
					QMessageBox.information(iface.mainWindow(),"Error", ("Unable to find DS node: ",+a+" for channel "+ id))
				try:
					return True, self.Head[:,ind]
				except:
					QMessageBox.information(iface.mainWindow(),"Error", ("Unable to extract data for US node: ",+a+" for channel "+ id))
					return False, [0.0]
			else:
				raise RuntimeError("Should not be here")

	def getLPData(self,id1,id2, iface):
		self.LP_chanlist = []
		if (id2 == None): # only one channel selected
			finished = False
			i = 0
			chan_list = tuple(self.Channels.chan_name)
			try:
				ind1 = chan_list.index(str(id1))
			except:
				QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(id1)))
				return [], []
			self.LP_chanlist = [id1]
			self.LP_chanID = [ind1]
			self.LP_ndlist = [(self.Channels.chan_US_Node[ind1])]
			self.LP_ndlist.append(self.Channels.chan_DS_Node[ind1])
			self.LP_xval = [0.0]
			self.LP_xval.append(self.Channels.chan_Length[ind1])
			id = ind1
			while not finished:
				i = i + 1
				chan = self.Channels.chan_DS_Chan[id]
				if(chan=='------'):
					finished = True
				else:
					self.LP_chanlist.append(chan)
					#id = int(numpy.where(self.Info['Channel']==chan)[0])
					try:
						id = self.Channels.chan_name.index(chan)
						self.LP_chanID.append(id)
						cur_len = self.LP_xval[len(self.LP_xval)-1]
						cur_len = cur_len + self.Channels.chan_Length[id]
						self.LP_xval.append(cur_len)
						self.LP_ndlist.append(self.Channels.chan_DS_Node[id])
					except:
						QMessageBox.information(iface.mainWindow(),"ERROR", ("Unable to process channel: "+chan))
		else: # two channels selected (check for more than two in main routine)
			#QMessageBox.information(iface.mainWindow(), "DEBUG", "Two channels selected.")
			finished = False
			found = False
			i = 0
			chan_list = tuple(self.Channels.chan_name)
			try:
				ind1 = chan_list.index(str(id1))
			except:
				QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(id1)))
				return [], []
			try:
				ind2 = chan_list.index(str(id2))
			except:
				QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(id1)))
				return [], []
			endchan = id2
			self.LP_chanlist = [id1]
			self.LP_chanID = [ind1]
			#self.LP_ndlist = [self.Info['US_Node'][ind1]]
			self.LP_ndlist = [(self.Channels.chan_US_Node[ind1])]
			#self.LP_ndlist.append(self.Info['DS_Node'][ind1])
			self.LP_ndlist.append(self.Channels.chan_DS_Node[ind1])
			self.LP_xval = [0.0]
			#self.LP_xval.append(self.Info['Length'][ind1])
			self.LP_xval.append(self.Channels.chan_Length[ind1])
			id = ind1
			while not finished:
				i = i + 1
				chan = self.Channels.chan_DS_Chan[id]
				if(chan=='------'):
					finished = True
				elif(chan==endchan):
					found = True
					finished = True
					self.LP_chanlist.append(chan)
					try:
						id = self.Channels.chan_name.index(chan)
						self.LP_chanID.append(id)
						cur_len = self.LP_xval[len(self.LP_xval)-1]
						cur_len = cur_len + self.Channels.chan_Length[id]
						self.LP_xval.append(cur_len)
						self.LP_ndlist.append(self.Channels.chan_DS_Node[id])
					except:
						QMessageBox.information(iface.mainWindow(),"ERROR", ("Unable to process channel: "+chan))
				else:
					self.LP_chanlist.append(chan)
					try:
						id = self.Channels.chan_name.index(chan)
						self.LP_chanID.append(id)
						cur_len = self.LP_xval[len(self.LP_xval)-1]
						cur_len = cur_len + self.Channels.chan_Length[id]
						self.LP_xval.append(cur_len)
						self.LP_ndlist.append(self.Channels.chan_DS_Node[id])
					except:
						QMessageBox.information(iface.mainWindow(),"ERROR", ("Unable to process channel: "+chan))

			if not (found): # id2 is not downstream of 1d1, reverse direction and try again...
				#QMessageBox.information(iface.mainWindow(), "DEBUG", "reverse direction and try again")
				finished = False
				found = False
				i = 0
				endchan = id1
				self.LP_chanlist = [id2]
				self.LP_chanID = [ind2]
				self.LP_ndlist = [(self.Channels.chan_US_Node[ind2])]
				self.LP_ndlist.append(self.Channels.chan_DS_Node[ind2])
				self.LP_xval = [0.0]
				self.LP_xval.append(self.Channels.chan_Length[ind2])
				id = ind2
				while not finished:
					i = i + 1
					chan = self.Channels.chan_DS_Chan[id]
					if(chan=='------'):
						finished = True
					elif(chan==endchan):
						found = True
						finished = True
						self.LP_chanlist.append(chan)
						try:
							id = self.Channels.chan_name.index(chan)
							self.LP_chanID.append(id)
							cur_len = self.LP_xval[len(self.LP_xval)-1]
							cur_len = cur_len + self.Channels.chan_Length[id]
							self.LP_xval.append(cur_len)
							self.LP_ndlist.append(self.Channels.chan_DS_Node[id])
						except:
							QMessageBox.information(iface.mainWindow(),"ERROR", ("Unable to process channel: "+chan))
					else:
						self.LP_chanlist.append(chan)
						try:
							id = self.Channels.chan_name.index(chan)
							self.LP_chanID.append(id)
							cur_len = self.LP_xval[len(self.LP_xval)-1]
							cur_len = cur_len + self.Channels.chan_Length[id]
							self.LP_xval.append(cur_len)
							self.LP_ndlist.append(self.Channels.chan_DS_Node[id])
						except:
							QMessageBox.information(iface.mainWindow(),"ERROR", ("Unable to process channel: "+chan))						
			if not (found): # id1 and 1d2 not connected
				QMessageBox.information(iface.mainWindow(), "Information", "Channels " +id1 + " and "+id2+" not connected.")
				self.LP_xval = [0.0]
				self.LP_yval = [0.0]
				return [], []
				
		self.LP_yval = []
		for nd in self.LP_ndlist:
			try:
				ind = self.nodeH_Header.index(nd)
			except:
				QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(nd)))
			#get data
			try:
				yvals =  self.Head[:,ind]
				self.LP_yval.append(max(yvals))
			except:
				QMessageBox.information(iface.mainWindow(),"ERROR", ("Extracting data for node id: " + str(nd)))

		#QMessageBox.information(iface.mainWindow(), "DEBUG", "starting pit search")
		self.pitx = []
		self.pitz = []
		self.npits = int(0)
		for (z, nd) in enumerate(self.LP_ndlist):
			#QMessageBox.information(iface.mainWindow(), "DEBUG", "node = " + nd)
			indN = self.nodes.node_name.index(nd)
			#QMessageBox.information(iface.mainWindow(), "DEBUG", "type(ind) = " + str(type(ind)))
			#QMessageBox.information(iface.mainWindow(), "DEBUG", "ind = " + str(indN))
			nchan = self.nodes.node_nChan[indN]
			#QMessageBox.information(iface.mainWindow(), "DEBUG", "nchan = " + str(nchan))
			for i in range(nchan):
				#QMessageBox.information(iface.mainWindow(), "DEBUG", "i = " + str(i))
				chanlist = self.nodes.node_channels[indN]
				chan = chanlist[i]
				#QMessageBox.information(iface.mainWindow(), "DEBUG", "chan = " + str(chan))
				indC = self.Channels.chan_name.index(chan)
				#QMessageBox.information(iface.mainWindow(), "DEBUG", "indC = " + str(indC))
				usC = self.Channels.chan_US_Chan[indC]
				dsC = self.Channels.chan_DS_Chan[indC]
				#QMessageBox.information(iface.mainWindow(), "DEBUG", "us = " + usC+" ds = "+dsC)
				if usC == "------" and dsC == "------":
					#QMessageBox.information(iface.mainWindow(), "DEBUG", "found pit chan = " + chan)
					self.pitx.append(self.LP_xval[z])
					self.pitz.append(self.Channels.chan_US_Inv[indC])
					self.npits = self.npits + 1
					
			#except:
			#	QMessageBox.information(iface.mainWindow(), "Error ", "Error = " + nd)
		#QMessageBox.information(iface.mainWindow(), "DEBUG", "n pits = " + str(self.npits))
		
		# get long profile elevations:
		#QMessageBox.information(iface.mainWindow(), "DEBUG", "extracting LP info.")
		self.LP_bed = []
		self.LP_LB = []
		self.LP_RB = []
		self.LP_chainage =[0.0]

		# get infor from channels
		for (counter, chan_index) in enumerate(self.LP_chanID):
#		for chan_index in self.LP_chanID:
			self.LP_bed.append(self.Channels.chan_US_Inv[chan_index])
			self.LP_LB.append(self.Channels.chan_LBUS_Obv[chan_index])
			self.LP_RB.append(self.Channels.chan_RBUS_Obv[chan_index])
			self.LP_bed.append(self.Channels.chan_DS_Inv[chan_index])
			self.LP_LB.append(self.Channels.chan_LBDS_Obv[chan_index])
			self.LP_RB.append(self.Channels.chan_RBDS_Obv[chan_index])
			if counter == 0: # first value
				self.LP_chainage.append(self.Channels.chan_Length[chan_index]-0.001)
			else:
				prev_len = self.LP_chainage[len(self.LP_chainage)-1]
				self.LP_chainage.append((prev_len+0.002))
				cur_len = self.Channels.chan_Length[chan_index]
				self.LP_chainage.append(prev_len+cur_len-0.001)

		
		return self.LP_chanlist, self.LP_chanID

	def getLPatTime(self, timeind, iface):
		#QMessageBox.information(iface.mainWindow(), "DEBUG", "getLPatTime")
		yvals = []
		for nd in self.LP_ndlist:
			try:
				ind = self.nodeH_Header.index(nd)
			except:
				QMessageBox.information(iface.mainWindow(),"ERROR", ("ID not found: " + str(nd)))
			#get data
			try:
				yval = self.Head[timeind,ind]
			except:
				QMessageBox.information(iface.mainWindow(),"ERROR", ("Extracting data for node id: " + str(nd)))
			yvals.append(yval)
		return yvals
	
	def __init__(self, fname, iface):
		self.filename = fname
		#print self.filename
		self.fpath = os.path.dirname(fname)
		self.nTypes = 0
		data = numpy.genfromtxt(fname, dtype=None, delimiter="==")
		for i in range (0,len(data)):
			tmp = data[i,0]
			dat_type = tmp.strip()
			tmp = data[i,1]
			rdata = tmp.strip()
			if (dat_type=='Simulation ID'):
				self.displayname = rdata
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
				self.Channels = ChanInfo(fullpath,iface) # 2014-04-AA, this has it's own class as there were issues if only a single channel existed

				if (self.nChannels != self.Channels.nChan):
					raise RuntimeError("Number of Channels does not match value in .1drf")

			elif (dat_type=='Node Info'):
				fullpath = os.path.join(self.fpath,rdata)
				self.nodes = NodeInfo(fullpath,iface) # this has it's own class as it needs to be read line by line due to different lengths (number of channels for each node)
			elif (dat_type=='Water Levels'):
				fullpath = os.path.join(self.fpath,rdata)
				try:
					with open(fullpath, 'rb') as csvfile:
						reader = csv.reader(csvfile, delimiter=',', quotechar='"')
						header = reader.next()
					csvfile.close()
				except:
					QMessageBox.critical(iface.mainWindow(), "ERROR", 'Error reading header from: '+fullpath)
				header[0]=u'Timestep'
				header[1]=u'Time'
				self.Nodes = []
				i=1
				for col in header[2:]:
					i= i+1
					a = col[2:]
					self.Nodes.append(a)
					header[i] = unicode(a)
				#self.nodeH_Header = unicode(header)
				self.nodeH_Header = header
				try: 
					self.Head = numpy.genfromtxt(fullpath, delimiter=",", skip_header=1)
				except: 
					QMessageBox.critical(iface.mainWindow(), "ERROR", 'Error reading data from: '+fullpath)

				if (self.nNodes != len(self.Nodes)):
					raise RuntimeError("Number of Nodes does not match value in .1drf")

				self.nTypes = self.nTypes + 1
				if (self.nTypes == 1):
					self.types = ['Head']
				else:
					self.types.append('Head')
			elif (dat_type=='Flows'):
				fullpath = os.path.join(self.fpath,rdata)
				try:
					with open(fullpath, 'rb') as csvfile:
						reader = csv.reader(csvfile, delimiter=',', quotechar='"')
						header = reader.next()
					csvfile.close()
				except:
					QMessageBox.critical(iface.mainWindow(), "ERROR", 'Error reading header from: '+fullpath)
				header[0]='Timestep'
				header[1]='Time'
				
				i=1
				for col in header[2:]:
					i= i+1
					a = col[2:] # trim "Q " from the start of name
					header[i] = a
				self.chanQ_Header = header # channel flow header, with no replacements
				try: 
					self.Flow = numpy.genfromtxt(fullpath, delimiter=",", skip_header=1)
				except:
					QMessageBox.critical(iface.mainWindow(), "ERROR", 'Error reading data from: '+fullpath)
				self.nTypes = self.nTypes + 1
				if (self.nTypes == 1):
					self.types = ['Flow']
				else:
					self.types.append('Flow')
			elif (dat_type=='Velocities'):
				fullpath = os.path.join(self.fpath,rdata)
				try:
					with open(fullpath, 'rb') as csvfile:
						reader = csv.reader(csvfile, delimiter=',', quotechar='"')
						header = reader.next()
					csvfile.close()
				except:
					QMessageBox.critical(iface.mainWindow(), "ERROR", 'Error reading header from: '+fullpath)
				header[0]='Timestep'
				header[1]='Time'
				
				i=1
				for col in header[2:]:
					i= i+1
					a = col[2:] # trim "V " from the start of name
					header[i] = a
				self.chanV_Header = header # channel velocity header, with no replacements
				try: 
					self.Velocity = numpy.genfromtxt(fullpath, delimiter=",", skip_header=1)
				except:
					QMessageBox.critical(iface.mainWindow(), "ERROR", 'Error reading data from: '+fullpath)
				self.nTypes = self.nTypes + 1
				if (self.nTypes == 1):
					self.types = ['Velocity']
				else:
					self.types.append('Velocity')
			else:
				QMessageBox.information(iface.mainWindow(), "Warning", 'Unknown Data Type '+dat_type)

