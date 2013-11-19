
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

		# Connect signals and slots
		QObject.connect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.connect(self.pbClearSelection, SIGNAL("clicked()"), self.clear_selection)
		QObject.connect(self.pbLoadAll, SIGNAL("clicked()"), self.load_all)
		#QObject.connect(self.tool, SIGNAL("deactivate"), self.deactivate)
		
		
	def __del__(self):
		# Disconnect signals and slots
		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "entering  __del__")
		QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.disconnect(self.pbClearSelection, SIGNAL("clicked()"), self.clear_selection)
		QObject.disconnect(self.pbLoadAll, SIGNAL("clicked()"), self.load_all)
	
	def unload(self):
		# Disconnect signals and slots
		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "entering unload")
		QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.disconnect(self.pbClearSelection, SIGNAL("clicked()"), self.clear_selection)
		QObject.disconnect(self.pbLoadAll, SIGNAL("clicked()"), self.load_all)

	def deactivate(self):
		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "entering deactivate")
		QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.disconnect(self.pbClearSelection, SIGNAL("clicked()"), self.clear_selection)
		QObject.disconnect(self.pbLoadAll, SIGNAL("clicked()"), self.load_all)
        
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
		self.deactivate()

	def load_all(self):
		"""
			Load all cross-sections from files
		"""
		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "The aim is to load all data from the .csv files here and store...")

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
		self.cLayer = self.canvas.currentLayer()
		
		self.lvXSID.clear()
		if self.cLayer and (self.cLayer.type() == QgsMapLayer.VectorLayer):
			valid = False
			dp = self.cLayer.dataProvider()		
			GType = dp.geometryType()
			if (GType == QGis.WKBPoint) or (GType == QGis.WKBLineString):
				valid = True
			elif (GType == QGis.WKBPolygon):
				message = "Not expecting polygon data here"
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
			QMessageBox.information(self.iface.mainWindow(), "1D XS Viewer", "Message: "+message)
		
		if (xs_format != True):
			QMessageBox.information(self.iface.mainWindow(), "1D XS Viewer", "Selected layer is not a 1d_xs layer. ")
			
		if self.handler:
			QObject.disconnect(self.selected_layer, SIGNAL("selectionChanged()"),self.select_changed)
			self.handler = False
			self.selected_layer = None
		if layer is not None:
			if layer.isValid():
				QObject.connect(layer,SIGNAL("selectionChanged()"),self.select_changed)
				self.selected_layer = layer

	def select_changed(self):
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
					self.sourcecsv.append(feature.attributeMap()[0].toString()) # 1st column is source
					self.xsType.append(feature.attributeMap()[1].toString()) # 2nd column is type
					flags = feature.attributeMap()[2].toString()
					if (len(flags) == 0):
						flags = None
					self.xsFlags.append(flags)
					col1 = feature.attributeMap()[3].toString()
					if (len(col1) == 0):
						col1 = None
					self.xsCol1.append(col1)
					col2 = feature.attributeMap()[4].toString()
					if (len(col2) == 0):
						col2 = None
					self.xsCol2.append(col2)
					col3 = feature.attributeMap()[5].toString()
					if (len(col3) == 0):
						col3 = None
					self.xsCol3.append(col3)
					self.xsCol4.append(feature.attributeMap()[6].toString())
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
		#mpltoolbar = matplotlib.backends.backend_qt4agg.NavigationToolbar2QTAgg(self.plotWdg, self.frame_for_plot)
			
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

		self.artists = []
		labels = []
		
		# Compile Selected Cross-Sections
		reslist = []
		resnames = []
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "before xs")
		nXS = len(self.xsdata)
		#QMessageBox.information(self.iface.mainWindow(), "nXS", str(nXS))
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


		self.subplot.set_xlabel('Distance')
		self.subplot.set_ylabel('Elevation')
		if self.cbShowLegend.isChecked():
			QMessageBox.information(self.iface.mainWindow(), "artists:", str(len(self.artists)))
			QMessageBox.information(self.iface.mainWindow(), "labels:", str(len(labels)))
			self.subplot.legend(self.artists, labels, bbox_to_anchor=(0, 0, 1, 1))
		self.subplot.hold(False)
		self.subplot.grid(True)
		self.plotWdg.draw()
		
class XS_Data():
	"""
	XS_Data class
	"""
	#def __init__(self, fpath,fname,type,flags,h1,h2,h3,h4):
	def __init__(self, iface, fpath,fname,type,flags,col1,col2,col3):
		#QMessageBox.information(iface.mainWindow(), "WARNING", "entering xs_data")
		self.fpath = str(fpath)
		self.fname = str(fname)
		self.fullpath = os.path.join(str(fpath),str(fname))
		self.type = type
		self.flags = flags
		self.col1 = col1
		self.col2 = col2
		self.col3 = col3
		self.col4 = None
		
		with open(self.fullpath, 'rb') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			nheader = 0
			for line in reader:
				try:
					for i in line:
						float(i)
					break
				except:
					nheader = nheader + 1
					header = line
		csvfile.close()
		data = numpy.genfromtxt(self.fullpath, delimiter=",", skip_header=nheader-1)
		if (col1 == None):
			self.x = data[:,0]
		else:
			try:
				ind = header.find(col1)
				self.x = data[:,ind]
			except:
				QMessageBox.information(iface.mainWindow(), "WARNING", "Finding col1"+col1)
		self.y = data[:,1]
