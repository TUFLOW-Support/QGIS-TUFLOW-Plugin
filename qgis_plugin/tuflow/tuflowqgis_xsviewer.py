
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
from ui_tuflowqgis_1d_xs import Ui_tuflowqgis_1d_xs

class TUFLOW_XS_Dock(QDockWidget, Ui_tuflowqgis_1d_xs):
    
	def __init__(self, iface):
        
		QDockWidget.__init__(self)
		Ui_tuflowqgis_1d_xs.__init__(self)
		self.setupUi(self)
		self.iface = iface
		self.canvas = self.iface.mapCanvas()
		self.handler = None
		self.selected_layer = None
		self.IDs = []
		self.showIt()		
		self.cLayer = self.canvas.currentLayer()
		self.layerChanged(self.cLayer)

		# Connect signals and slots
		QObject.connect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.connect(self.pbClearSelection, SIGNAL("clicked()"), self.clear_selection)
		QObject.connect(self.pbLoadAll, SIGNAL("clicked()"), self.load_all)
		QObject.connect(self.pbClearStatus, SIGNAL("clicked()"), self.clear_status)
		QObject.connect(self.cbDeactivate, SIGNAL("stateChanged(int)"), self.deactivate_changed)
		QObject.connect(self, SIGNAL("visibilityChanged(bool)"), self.visChanged)
		
		
		
	def __del__(self):
		# Disconnect signals and slots
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "entering  __del__")
		QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.disconnect(self.pbClearSelection, SIGNAL("clicked()"), self.clear_selection)
		QObject.disconnect(self.pbLoadAll, SIGNAL("clicked()"), self.load_all)
		QObject.disconnect(self.pbClearStatus, SIGNAL("clicked()"), self.clear_status)
		QObject.disconnect(self.cbDeactivate, SIGNAL("stateChanged(int)"), self.deactivate_changed)
		QObject.disconnect(self, SIGNAL("visibilityChanged(bool)"), self.visChanged)
	
	def visChanged(self, vis):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Vis is " + str(vis))
		#if vis:
		#	QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Vis true")
		if not vis:
			QMessageBox.information(self.iface.mainWindow(), "Information", "Dock visibility turned off - deactivating dock.")
			self.deactivate()


	def deactivate(self):
		QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.disconnect(self.pbClearSelection, SIGNAL("clicked()"), self.clear_selection)
		QObject.disconnect(self.pbLoadAll, SIGNAL("clicked()"), self.load_all)
		QObject.disconnect(self.pbClearStatus, SIGNAL("clicked()"), self.clear_status)
		QObject.disconnect(self, SIGNAL("visibilityChanged(bool)"), self.visChanged)
		self.lwStatus.insertItem(0,'Disconnected')
        
	def refresh(self):
		"""
			Refresh is usually called when the selected layer changes in the legend
			Refresh clears and repopulates the dock widgets, restoring them to their correct values
		"""
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "refresh()")
		self.cLayer = self.canvas.currentLayer()
		self.layerChanged(self.cLayer)
		self.select_changed()
		


	def load_all(self):
		"""
			Load all cross-sections from files
		"""
		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "The aim is to load all data from the .csv files here and store...")
		
	def clear_status(self):
		"""
			Clears the status list wdiget
		"""
		QMessageBox.information(self.iface.mainWindow(), "Information", "Clearing the status list above.")
		self.lwStatus.clear()
		self.lwStatus.insertItem(0,'Status cleared')

	def deactivate_changed(self):
		"""
			Deactivate checkbox has changed status
		"""
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Deactivate has been toggled")
		
		if (self.cbDeactivate.isChecked()):
			self.lwStatus.insertItem(0,'Viewer deactivated')
			QMessageBox.information(self.iface.mainWindow(), "Information", "Deactivate Enabled")
			QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
			QObject.disconnect(self.pbClearSelection, SIGNAL("clicked()"), self.clear_selection)
			QObject.disconnect(self.pbClearStatus, SIGNAL("clicked()"), self.clear_status)
			QObject.disconnect(self.pbLoadAll, SIGNAL("clicked()"), self.load_all)
			try:
				#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "selectionChanged disconnect")
				QObject.disconnect(self.selected_layer, SIGNAL("selectionChanged()"),self.select_changed)
			except:
				QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Issue disconnecting selection.")
		else:
			self.lwStatus.insertItem(0,'Viewer re-activated')
			QObject.connect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
			QObject.connect(self.pbClearSelection, SIGNAL("clicked()"), self.clear_selection)
			QObject.connect(self.pbLoadAll, SIGNAL("clicked()"), self.load_all)
			QObject.connect(self.pbClearStatus, SIGNAL("clicked()"), self.clear_status)
			if self.cLayer:
				self.layerChanged(self.cLayer)
			
	def clear_selection(self):
		"""
			Clear all selected sections (unselect the items, is this possible)
		"""
		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "The aim is to clear the selection in QGIS, this can already be done with the - deselect features from all layers.")
		
	def layerChanged(self, layer):
		"""
			Layer has been changed in TOC
		"""
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "layer has been changed, need to check if this is 1d_xs format")
		self.lwStatus.insertItem(0,'Layer Changed')
		self.cLayer = self.canvas.currentLayer()
		
		self.lvXSID.clear()
		if self.cLayer and (self.cLayer.type() == QgsMapLayer.VectorLayer):
			valid = False
			dp = self.cLayer.dataProvider()		
			GType = dp.geometryType()
			if (GType == QGis.WKBPoint) or (GType == QGis.WKBLineString):
				valid = True
			elif (GType == QGis.WKBPolygon):
				message = "Not expecting polygon data"
			else:
				message = "Expecting points or lines for 1d_tab format"
		else:
			valid = False
			message = "Invalid layer or no layer selected"
		
		xs_format = True
		if valid: # geometry is valid, check for correct attributes
			xs_format = True
			if (dp.fieldNameIndex('Source') != 0):
				xs_format = False
			if (dp.fieldNameIndex('Type') != 1):
				xs_format = False
			if (dp.fieldNameIndex('Flags') != 2):
				xs_format = False
		else:
			#QMessageBox.information(self.iface.mainWindow(), "1D XS Viewer", "Message: "+message)
			self.lwStatus.insertItem(0,'Message: '+message)
		
		if (xs_format != True):
			#QMessageBox.information(self.iface.mainWindow(), "1D XS Viewer", "Selected layer is not a 1d_xs layer. ")
			self.lwStatus.insertItem(0,'Selected layer is not a 1d_xs layer.')
			
		if self.handler:
			QObject.disconnect(self.selected_layer, SIGNAL("selectionChanged()"),self.select_changed)
			self.handler = False
			self.selected_layer = None
		if layer is not None:
			if layer.isValid():
				QObject.connect(layer,SIGNAL("selectionChanged()"),self.select_changed)
				self.selected_layer = layer

	def select_changed(self):
		self.lwStatus.insertItem(0,'Selection Changed')
		self.cLayer = self.canvas.currentLayer()
		dp = self.cLayer.dataProvider()
		ds = dp.dataSourceUri()
		self.fpath = os.path.dirname(unicode(ds))
		self.sourcecsv = []
		self.xsType = []
		self.xsFlags = []
		self.xsCol1 = []
		self.xsCol2 = []
		self.xsCol3 = []
		self.xsCol4 = []
		self.xsdata = []
		self.lvXSID.clear()
		nxs = 0
		if (self.cLayer.selectedFeatures()):
			for feature in self.cLayer.selectedFeatures():
				try:
					nxs = nxs + 1
					source = feature['Source']
					self.sourcecsv.append(feature['Source']) # 1st column is source
					self.xsType.append(feature['Type']) # 2nd column is type
					flags = feature['Flags']
					if not flags:
						flags = None
					self.xsFlags.append(flags)
					col1 = feature['Column_1']
					if not col1:
						self.xsCol1.append(None)
					else:
						self.xsCol1.append(col1.upper())
					col2 = feature['Column_2']
					if not col2:
						self.xsCol2.append(None)
					else:
						self.xsCol2.append(col2.upper())
					col3 = feature['Column_3']
					if not col3:
						self.xsCol3.append(None)
					else:
						self.xsCol3.append(col3.upper())
					col4 = feature['Column_4']
					if not col4:
						self.xsCol4.append(None)
					else:
						self.xsCol4.append(col4.upper())
					#QMessageBox.information(self.iface.mainWindow(), "Debug", self.sourcecsv[nxs-1])
					#QMessageBox.information(self.iface.mainWindow(), "Debug", self.self.xsType[nxs-1])
					#myXS = XS_Data(self.iface,self.fpath,self.sourcecsv[nxs-1],self.xsType[nxs-1],self.xsFlags[nxs-1])
					myXS = XS_Data(self.iface,self.fpath,self.sourcecsv[nxs-1],self.xsType[nxs-1],self.xsFlags[nxs-1],self.xsCol1[nxs-1],self.xsCol2[nxs-1],self.xsCol3[nxs-1])
					self.xsdata.append(myXS)
					self.lvXSID.addItem(myXS.fname)
				except:
					QMessageBox.information(self.iface.mainWindow(), "WARNING", "Problem occurred reading data for Feature ID %d: " % feature.id())
			
		# call update plot
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
		
		self.fig = Figure( (1.0, 1.0), linewidth=0.0, subplotpars = matplotlib.figure.SubplotParams(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0))
			
		font = {'family' : 'arial', 'weight' : 'normal', 'size'   : 12}
		
		rect = self.fig.patch
		rect.set_facecolor((0.9,0.9,0.9))
		self.subplot = self.fig.add_axes((0.10, 0.15, 0.85,0.82))
		#self.subplot = self.fig.add_axes((0.10, 0.15, 0.75,0.82))
		self.subplot.set_xbound(0,1000)
		self.subplot.set_ybound(0,1000)			
		self.manageMatplotlibAxe(self.subplot)
		#self.subplot2 = self.subplot.twinx()
		canvas = FigureCanvasQTAgg(self.fig)
		sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		sizePolicy.setHorizontalStretch(0)
		sizePolicy.setVerticalStretch(0)
		canvas.setSizePolicy(sizePolicy)
		self.plotWdg = canvas
		
		self.gridLayout.addWidget(self.plotWdg)
		mpltoolbar = matplotlib.backends.backend_qt4agg.NavigationToolbar2QTAgg(self.plotWdg, self.frame_for_toolbar)
		lstActions = mpltoolbar.actions()
		mpltoolbar.removeAction( lstActions[ 7 ] ) #remove customise sub-plot
			
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
		self.lwStatus.insertItem(0,'Updating Figure')
		self.subplot.clear()
		try:
			self.axis2.clear()
		except:
			self.ax2_exists = False
		xmin=0.0
		xmax=0.0
		ymin=0.0
		ymax=0.0
		mmin=0.0
		mmax=0.0
		self.artists = []
		labels = []
		
		# Compile Selected Cross-Sections
		reslist = []
		resnames = []
		nXS = len(self.xsdata)
		
		# work out if we need dual y axis plot
		dual_axis = False
		if (self.cbRoughness.isChecked()): # if not checked not dual axis needed
			#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "CB is checked")
			for xs in self.xsdata:
				if xs.flags:
					#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Dual axis figure needed...")
					dual_axis = True
					if self.ax2_exists == False:
						#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Dual axis doesn't exist yet")
						self.axis2 = self.subplot.twinx()
						self.ax2_exists = True
					#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Dual axis created")
		
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Dual axis delete 1")
		
		if dual_axis == False and self.ax2_exists == True: #axis 2 exists and shouldn't
			#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Need to delete axis")
			try:
				#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "before del")
				self.fig.delaxes(self.axis2)
				#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "after del")
				self.ax2_exists = False
				#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Axis deleted")
			except:
				QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Error deleting axis2")
				
		for xs in self.xsdata:
			xmin=round(min(xs.x), 0) - 1
			xmax=round(max(xs.x), 0) + 1
			ymin=round(min(xs.y), 0) - 1
			ymax=round(max(xs.y), 0) + 1
			label = xs.fname
			self.subplot.set_xbound(lower=xmin, upper=xmax)
			self.subplot.set_ybound(lower=ymin, upper=ymax)
			a, = self.subplot.plot(xs.x, xs.y)
			self.artists.append(a)
			labels.append(label)
			self.subplot.hold(True)
			if dual_axis and xs.flags:
				#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Dual axis stuff")
				a2, = self.axis2.plot(xs.x, xs.mat, '--')
				mmin=round(min(xs.mat), 0) - 1
				mmax=round(max(xs.mat), 0) + 1
				self.axis2.set_xbound(lower=xmin, upper=xmax)				
				self.axis2.set_ybound(lower=mmin, upper=mmax)
				self.axis2.set_ylabel('Material or Roughness')
		self.subplot.set_xlabel('Distance')
		self.subplot.set_ylabel('Elevation')
		if self.cbShowLegend.isChecked():
			self.subplot.legend(self.artists, labels, bbox_to_anchor=(0, 0, 1, 1))
		self.subplot.hold(False)
		self.subplot.grid(True)
		self.plotWdg.draw()
		
class XS_Data():
	"""
	XS_Data class
	"""
	def __init__(self, iface, fpath,fname,type,flags,col1,col2,col3):
		self.fpath = str(fpath)
		self.fname = str(fname)
		self.fullpath = os.path.join(str(fpath),str(fname))
		self.type = type
		self.flags = flags
		self.col1 = col1
		self.col2 = col2
		self.col3 = col3
		self.col4 = None

		# check file exists
		if not os.path.isfile(self.fullpath):
			QMessageBox.information(iface.mainWindow(), "ERROR", "Unable to open / read file: "+self.fullpath)

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
		

		# find column data
		if (self.col1 == None):
			c1_ind = 0
		else:
			try:
				c1_ind  = header.index(self.col1)
			except:
				QMessageBox.critical(iface.mainWindow(), "WARNING", "Unable to find "+self.col1+ " in header. Using data in column 1")
		if (self.col2 == None):
			c2_ind = 1
		else:
			try:
				c2_ind  = header.index(self.col2)
			except:
				QMessageBox.critical(iface.mainWindow(), "WARNING", "Unable to find "+self.col2+ " in header. Using data in column 2")
		if self.flags:
			#QMessageBox.critical(iface.mainWindow(), "debug", "looking for additional data")
			if self.col3 == None:
				c3_ind = 2
			else:
				try:
					c3_ind  = header.index(self.col3)
				except:
					QMessageBox.information(iface.mainWindow(), "WARNING", "Unable to find "+self.col3+ " in header. Using data in column 3")				

		
		# actually read the data:
		#QMessageBox.information(iface.mainWindow(), "debug", "col3 index: "+str(c3_ind))
		self.x = []
		self.y = []
		self.mat = []
		with open(self.fullpath, 'rb') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			try:
				for i in range(0,nheader):
					reader.next()
				for line in reader:
					xstr = line[c1_ind]
					self.x.append(float(line[c1_ind]))
					self.y.append(float(line[c2_ind]))
					if self.flags:
						self.mat.append(float(line[c3_ind]))
			except:
				QMessageBox.information(iface.mainWindow(), "Error", "Error reading cross section "+self.fullpath)
		csvfile.close()
