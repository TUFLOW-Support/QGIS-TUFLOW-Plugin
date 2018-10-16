
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtGui
from qgis.core import *
import sys
import os
import csv
import scipy
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.patches import Polygon
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
import numpy
import TUFLOW_results2013
import TUFLOW_results
import TUFLOW_XS
import TUFLOW_1dTa
import math
from collections import OrderedDict
from tuflowqgis_library import *
import tuflowqgis_dialog



# Debug using PyCharm
sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2018.2\debug-eggs')
sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2018.2\helpers\pydev')


sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms")
from ui_tuflowqgis_TuPlot import Ui_tuflowqgis_TuPlot
import tuflowqgis_styles

class TuPlot(QDockWidget, Ui_tuflowqgis_TuPlot):
    
	def __init__(self, iface, **kwargs):
        
		QDockWidget.__init__(self)
		self.wdg = Ui_tuflowqgis_TuPlot.__init__(self)
		self.setupUi(self)
		self.iface = iface
		self.canvas = self.iface.mapCanvas()
		self.handler = None
		self.selected_layer = None
		self.IDs = []
		self.res = []
		self.hydTables = TUFLOW_1dTa.HydTables()
		self.idx = -1 #initial
		self.showIt()		
		self.cLayer = None
		self.GeomType = None
		self.connected = False
		self.ts_types_P = []
		self.ts_types_L = []
		self.ts_types_P = []
		self.ax2_exists = True
		self.dockOpened = True
		self.is_xs = False
		self.XS=TUFLOW_XS.XS()
		self.geom_type = None
		self.ResTypeList_ax2.setEnabled(False)
		self.xsResults = False
		self.xsLoaded = []
		self.xsLoadedName = []
		self.xs_list = []
		self.labels = []
		self.customAxis = None
		self.customLabels = None
		self.profileIntTool = None
		self.is_intTool = False
		#self.setAttribute(Qt.WA_DeleteOnClose, True)
		
		#colour stuff
		self.qred = QtGui.QColor(int(255), int(0), int(0))
		self.qgrey = QtGui.QColor(int(192), int(192), int(192))
		self.qblue = QtGui.QColor(int(0), int(0), int(255))
		self.qgreen = QtGui.QColor(int(0), int(153), int(0))
		self.qblack = QtGui.QColor(int(0), int(0), int(0))
		
		self.qgis_connect()
		QObject.connect(self.cbDeactivate, SIGNAL("stateChanged(int)"), self.deactivate_changed) #this is seperate so multiple connections aren't created
		
		if 'profile_integerity_tool' in kwargs.keys():
			if kwargs['profile_integerity_tool'] is not None:
				self.profileIntTool = kwargs['profile_integerity_tool']
				self.layerChanged()
				self.select_changed()
		
	def __del__(self):
		# Disconnect signals and slots
		self.qgis_disconnect()
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "__del__")
		#opened = False
    
	def closeEvent(self,event):
		#self.saveSettings()
		#QDialog.closeEvent(self,event)
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "closeEvent")
		self.dockOpened = False
		self.__del__()
		
	def qgis_connect(self): #2015-04-AA
		if not self.connected:
			self.plotWdg.setContextMenuPolicy(Qt.CustomContextMenu)
			self.IDList.setContextMenuPolicy(Qt.CustomContextMenu)
			self.plotWdg.customContextMenuRequested.connect(self.showMenu)
			self.IDList.customContextMenuRequested.connect(self.showMenuSelElements)
			self.lwStatus.insertItem(0,'Creating QGIS connections')
			self.lwStatus.item(0).setTextColor(self.qgreen)
			QObject.connect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
			QObject.connect(self.locationDrop, SIGNAL("currentIndexChanged(int)"), self.loc_changed)       
			#QObject.connect(self.ResTypeList, SIGNAL("currentRowChanged(int)"), self.res_type_changed)
			QObject.connect(self.ResTypeList, SIGNAL("itemClicked(QListWidgetItem*)"), self.res_type_changed)
			QObject.connect(self.ResTypeList_ax2, SIGNAL("itemClicked(QListWidgetItem*)"), self.res_type_changed)
			QObject.connect(self.AddRes, SIGNAL("clicked()"), self.add_res)
			QObject.connect(self.pbAddRes_GIS, SIGNAL("clicked()"), self.add_res_gis)
			QObject.connect(self.CloseRes, SIGNAL("clicked()"), self.close_res)
			self.AddHydTab.clicked.connect(self.add_1dTa)
			self.CloseHydTab.clicked.connect(self.close_1dTa)
			QObject.connect(self.pbAnimatePlot, SIGNAL("clicked()"), self.animate_Plot)
			QObject.connect(self, SIGNAL("visibilityChanged(bool)"), self.visChanged)
			QObject.connect(self.listTime, SIGNAL("currentRowChanged(int)"), self.timeChanged)
			QObject.connect(self.listTime, SIGNAL("clicked(QModelIndex)"), self.timeChanged)
			QObject.connect(self.ResList, SIGNAL("currentRowChanged(int)"), self.timeChanged)
			QObject.connect(self.ResList, SIGNAL("clicked(QModelIndex)"), self.timeChanged)
			QObject.connect(self.pbClearStatus, SIGNAL("clicked()"), self.clear_status)
			QObject.connect(self.pbUpdate, SIGNAL("clicked()"), self.update_pressed)
			QObject.connect(self.pbHelp, SIGNAL("clicked()"), self.help_pressed)
			QObject.connect(self.cbForceXS, SIGNAL("stateChanged(int)"), self.changed_forcexs)
			QObject.connect(self.cbForceRes, SIGNAL("stateChanged(int)"), self.changed_forceres)
			QObject.connect(self.cbShowLegend, SIGNAL("stateChanged(int)"), self.update_pressed)
			QObject.connect(self.cbLegendUL, SIGNAL("stateChanged(int)"), self.LegendUL_pressed)
			QObject.connect(self.cbLegendUR, SIGNAL("stateChanged(int)"), self.LegendUR_pressed)
			QObject.connect(self.cbLegendLL, SIGNAL("stateChanged(int)"), self.LegendLL_pressed)
			QObject.connect(self.cbLegendLR, SIGNAL("stateChanged(int)"), self.LegendLR_pressed)
			QObject.connect(self.cbMeanAbove, SIGNAL("stateChanged(int)"), self.MeanAbove_pressed)
			QObject.connect(self.cbMeanClosest, SIGNAL("stateChanged(int)"), self.MeanClosest_pressed)
			QObject.connect(self.cb2ndAxis, SIGNAL("clicked()"), self.toggle_ax2_listWidget)
			
			#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "connecting")
			#QObject.connect(self, SIGNAL( "destroyed(PyQt_PyObject)" ), self.closeup)
			#try:
			#	QObject.connect(self, SIGNAL( "closeEvent(QCloseEvent)" ), self.closeup)
			#except:
			#	QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Cant connect to closeEvent'")
			#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "connected?")
			#QObject.connect(exitButton,SIGNAL("clicked()"),self.closeup)
			self.lwStatus.insertItem(0,'Connections created.')
			self.lwStatus.item(0).setTextColor(self.qgreen)
			self.connected = True
			self.populate_export_frmts()
	
	def qgis_disconnect(self): #2015-04-AA
		if self.connected:
			self.lwStatus.insertItem(0,'Removing QGIS connections')
			self.lwStatus.item(0).setTextColor(self.qgreen)
			self.plotWdg.customContextMenuRequested.disconnect(self.showMenu)
			self.IDList.customContextMenuRequested.disconnect(self.showMenuSelElements)
			QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
			QObject.disconnect(self.locationDrop, SIGNAL("currentIndexChanged(int)"), self.loc_changed)
			#QObject.disconnect(self.ResTypeList, SIGNAL("currentRowChanged(int)"), self.res_type_changed)
			QObject.disconnect(self.ResTypeList, SIGNAL("itemClicked(QListWidgetItem*)"), self.res_type_changed)
			QObject.disconnect(self.ResTypeList_ax2, SIGNAL("itemClicked(QListWidgetItem*)"), self.res_type_changed)
			QObject.disconnect(self.AddRes, SIGNAL("clicked()"), self.add_res)
			QObject.disconnect(self.pbAddRes_GIS, SIGNAL("clicked()"), self.add_res_gis)
			QObject.disconnect(self.CloseRes, SIGNAL("clicked()"), self.close_res)
			self.AddHydTab.clicked.disconnect(self.add_1dTa)
			self.CloseHydTab.clicked.disconnect(self.close_1dTa)
			QObject.disconnect(self.pbAnimatePlot, SIGNAL("clicked()"), self.animate_Plot)
			QObject.disconnect(self, SIGNAL("visibilityChanged(bool)"), self.visChanged)
			QObject.disconnect(self.listTime, SIGNAL("currentRowChanged(int)"), self.timeChanged)
			QObject.disconnect(self.listTime, SIGNAL("clicked(QModelIndex)"), self.timeChanged)
			QObject.disconnect(self.ResList, SIGNAL("currentRowChanged(int)"), self.timeChanged)
			QObject.disconnect(self.ResList, SIGNAL("clicked(QModelIndex)"), self.timeChanged)
			QObject.disconnect(self.pbClearStatus, SIGNAL("clicked()"), self.clear_status)
			QObject.disconnect(self.pbUpdate, SIGNAL("clicked()"), self.update_pressed)
			QObject.disconnect(self.cbForceXS, SIGNAL("stateChanged(int)"), self.changed_forcexs)
			QObject.disconnect(self.cbForceRes, SIGNAL("stateChanged(int)"), self.changed_forceres)
			QObject.disconnect(self.cbShowLegend, SIGNAL("stateChanged(int)"), self.update_pressed)
			QObject.disconnect(self.cbLegendUL, SIGNAL("stateChanged(int)"), self.LegendUL_pressed)
			QObject.disconnect(self.cbLegendUR, SIGNAL("stateChanged(int)"), self.LegendUR_pressed)
			QObject.disconnect(self.cbLegendLL, SIGNAL("stateChanged(int)"), self.LegendLL_pressed)
			QObject.disconnect(self.cbLegendLR, SIGNAL("stateChanged(int)"), self.LegendLR_pressed)
			QObject.disconnect(self.cbMeanAbove, SIGNAL("stateChanged(int)"), self.MeanAbove_pressed)
			QObject.disconnect(self.cbMeanClosest, SIGNAL("stateChanged(int)"), self.MeanClosest_pressed)
			QObject.disconnect(self.cb2ndAxis, SIGNAL("clicked()"), self.toggle_ax2_listWidget)
			#QObject.disconnect(self.cbDeactivate, SIGNAL("stateChanged(int)"), self.deactivate_changed)
			self.lwStatus.insertItem(0,'Disconnected.')
			self.lwStatus.item(0).setTextColor(self.qgreen)
		self.connected = False
	
	def populate_export_frmts(self):
		self.lwStatus.insertItem(0,'Detecting export formats in matplotlib')
		self.dropExportExt.clear()
		try:
			mpl_formats =plt.gcf().canvas.get_supported_filetypes()
			for key in mpl_formats:
				self.lwStatus.insertItem(0,'Supported export format: {0}'.format(key))
				self.dropExportExt.addItem(".{0}".format(key))
		except:
			self.lwStatus.insertItem(0,'ERROR - Extracting supported export formats')
		
		#default to .png if available
		try:
			ind = self.dropExportExt.findText('.png')
			if ind >= 0:
				self.lwStatus.insertItem(0,'Defaulting to .png format.')
				self.dropExportExt.setCurrentIndex(ind)
			else:
				self.dropExportExt.setCurrentIndex(0)
		except:
			self.lwStatus.insertItem(0,'Warning - Exception hit finding .png.')
		
	def help_pressed(self):
		message = 'This TuPlot utility is designed to view timeseries and long profile data from TUFLOW models.\n'
		message = message+'For some functionality, this utitlity relies on the output formats available in the 2016 version of TUFLOW.  Some of the functioalaity is available for the 2013 version of TUFLOW.\n'
		message = message+'For more information on using this please see http://wiki.tuflow.com/index.php?title=TuPlot'
		QMessageBox.information(self.iface.mainWindow(), "TuPlot Information", message)
		
	def clear_status(self):
		"""
			Clears the status list wdiget
		"""
		self.lwStatus.clear()
		self.lwStatus.insertItem(0,'Status cleared')
		self.lwStatus.item(0).setTextColor(self.qgreen)
		
	def visChanged(self, vis):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Vis is " + str(vis))
		#if vis:
		#	QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Vis true")
		if not vis:
			#QMessageBox.information(self.iface.mainWindow(), "Information", "Dock visibility turned off - deactivating dock.")
			#self.deactivate()
			
			#QMessageBox.information(self.iface.mainWindow(), "Information", "Exiting")
			#self.lwStatus.insertItem(0,'Visibility Changed')
			#self.qgis_disconnect()
			return
		#else:
		#	self.qgis_connect()

	def deactivate_changed(self):
		"""
			Deactivate checkbox has changed status
		"""
		
		if (self.cbDeactivate.isChecked()):
			self.lwStatus.insertItem(0,'Viewer deactivated')
			self.lwStatus.item(0).setTextColor(self.qgreen)
			self.qgis_disconnect()
		else:
			self.lwStatus.insertItem(0,'Viewer re-activated')
			self.lwStatus.item(0).setTextColor(self.qgreen)

			self.qgis_connect()
			if self.cLayer:
				self.layerChanged()
				
	def refresh(self):
		"""
			Refresh is usually called when the selected layer changes in the legend
			Refresh clears and repopulates the dock widgets, restoring them to their correct values
		"""
		#self.lwStatus.insertItem(0,'Refreshing')
		self.cLayer = self.canvas.currentLayer()
		self.select_changed()

	def closeup(self):
		"""
			Close up and remove the dock
		"""
		QMessageBox.information(self.iface.mainWindow(), "Information", "Closing and removing dock")
	
	def changed_forcexs(self):
		"""
			The Check button Force XS has been changed
		"""
		if self.cbForceXS.isChecked():
			if self.cbForceRes.isChecked(): # force res already checked
				self.cbForceRes.setChecked(False)

	def MeanAbove_pressed(self):
		"""
			The mean above check box has been toggled.
		"""
		if self.cbMeanAbove.isChecked():
			if self.cbMeanClosest.isChecked():
				self.cbMeanClosest.setChecked(False)
		else:
			if not self.cbMeanClosest.isChecked():
				self.cbMeanClosest.setChecked(True)
				
	def MeanClosest_pressed(self):
		"""
			The mean closest check box has been toggled.
		"""
		if self.cbMeanClosest.isChecked():
			if self.cbMeanAbove.isChecked():
				self.cbMeanAbove.setChecked(False)
		else:
			if not self.cbMeanAbove.isChecked():
				self.cbMeanAbove.setChecked(True)
				
	def LegendUL_pressed(self):
		"""
			The Legend Location UL has been pressed
		"""
		if self.cbLegendUL.isChecked():
			if self.cbLegendUR.isChecked():
				self.cbLegendUR.setChecked(False)
			if self.cbLegendLL.isChecked():
				self.cbLegendLL.setChecked(False)
			if self.cbLegendLR.isChecked():
				self.cbLegendLR.setChecked(False)
			self.update_pressed()

	def LegendUR_pressed(self):
		"""
			The Legend Location UR has been pressed
		"""
		if self.cbLegendUR.isChecked():
			if self.cbLegendUL.isChecked():
				self.cbLegendUL.setChecked(False)
			if self.cbLegendLL.isChecked():
				self.cbLegendLL.setChecked(False)
			if self.cbLegendLR.isChecked():
				self.cbLegendLR.setChecked(False)
			self.update_pressed()

	def LegendLL_pressed(self):
		"""
			The Legend Location LL has been pressed
		"""
		if self.cbLegendLL.isChecked():
			if self.cbLegendUL.isChecked():
				self.cbLegendUL.setChecked(False)
			if self.cbLegendUR.isChecked():
				self.cbLegendUR.setChecked(False)
			if self.cbLegendLR.isChecked():
				self.cbLegendLR.setChecked(False)
			self.update_pressed()

	def LegendLR_pressed(self):
		"""
			The Legend Location LR has been pressed
		"""
		if self.cbLegendLR.isChecked():
			if self.cbLegendUL.isChecked():
				self.cbLegendUL.setChecked(False)
			if self.cbLegendUR.isChecked():
				self.cbLegendUR.setChecked(False)
			if self.cbLegendLL.isChecked():
				self.cbLegendLL.setChecked(False)
			self.update_pressed()
				
	def changed_forceres(self):
		"""
			The Check button Force RES has been changed
		"""
		if self.cbForceRes.isChecked():
			if self.cbForceXS.isChecked():  # force xs already checked
				self.cbForceXS.setChecked(False)
				
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
		#inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Open TUFLOW results file', fpath, "TUFLOW 1D Results (*.info *.tpc)")
		#inFileName = str(inFileName)
		#if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
		#2017-06-AB Add support for multiple files
		inFileNames = QFileDialog.getOpenFileNames(self.iface.mainWindow(), 'Open TUFLOW results file', fpath, "TUFLOW Plot Results (*.info *.tpc)")
		if not inFileNames: #empty list
			return
		self.lwStatus.insertItem(0,'Number of files: '+str(len(inFileNames)))
		#else:
		#	for fname in inFileNames:
		#	self.lwStatus.insertItem(0,'File: {0}'.format(fname))
		# Store the path we just looked in
		#head, tail = os.path.split(inFileName)
		
		for x in range(len(inFileNames)):
			fpath, fname = os.path.split(inFileNames[x])
			if x == 0: #only save path for 1st file
				if fpath != os.sep and fpath.lower() != 'c:\\' and fpath != '':
					settings.setValue("TUFLOW_Res_Dock/lastFolder", fpath)
			self.lwStatus.insertItem(0,'Opening File: '+fname)
			self.lwStatus.item(0).setTextColor(self.qgreen)
			root, ext = os.path.splitext(inFileNames[x])
			if ext.upper()=='.INFO':
				self.lwStatus.insertItem(0,'.INFO file detected - using TUFLOW_Results2013.')
				self.lwStatus.item(0).setTextColor(self.qgreen)
				#self.lwStatus.insertItem(0,'Loading...')
				#try:
				#res=TUFLOW_results2013.ResData(inFileNames[x])
				res = TUFLOW_results2013.ResData()
				res.Load(inFileNames[x], self.iface)
				self.res.append(res)
					#self.lwStatus.insertItem(0,'Done')
				#except:
				#	self.lwStatus.insertItem(0,'ERROR - Loading Results')
				#	self.lwStatus.item(0).setTextColor(self.qred)
				
			elif ext.upper()=='.TPC':
				self.lwStatus.insertItem(0,'.TPC file detected - using TUFLOW_results')
				self.lwStatus.item(0).setTextColor(self.qgreen)
				try:
					#self.lwStatus.insertItem(0,'Loading...')
					res=TUFLOW_results.ResData()
					error, message = res.Load(inFileNames[x])
					if error:
						self.lwStatus.insertItem(0,message)
					else:
						self.res.append(res)
						#self.lwStatus.insertItem(0,'Done')
				except:
					self.lwStatus.insertItem(0,'ERROR - Loading Results')
					self.lwStatus.item(0).setTextColor(self.qred)
			
			#QMessageBox.information(self.iface.mainWindow(), "Opened", "Successfully Opened - "+myres.displayname)
			
		self.update_reslist()

	def add_res_gis(self):
		"""
			Add results file and loads the GIS layers into the project
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
		#inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Open TUFLOW results file (must be 2015 or newer)', fpath, "TUFLOW Results (*.tpc)")
		#inFileName = str(inFileName)
		#if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
		#	return
		#2017-06-AB
		inFileNames = QFileDialog.getOpenFileNames(self.iface.mainWindow(), 'Open TUFLOW results file', fpath, "TUFLOW Plot Results (*.tpc)")
		if not inFileNames: #empty list
			return
		self.lwStatus.insertItem(0,'Number of files: '+str(len(inFileNames)))
		
		for x in range(len(inFileNames)):
			# Store the path we just looked in
			inFileName = inFileNames[x]
			fpath, fname = os.path.split(inFileName)
			if x == 0:
				if fpath != os.sep and fpath.lower() != 'c:\\' and fpath != '':
					settings.setValue("TUFLOW_Res_Dock/lastFolder", fpath)
			#self.lwStatus.insertItem(0,'Opening File: '+fname)
			root, ext = os.path.splitext(inFileName)
			if ext.upper()=='.INFO':
				self.lwStatus.insertItem(0,'ERROR - .INFO file detected must be 2015 or newer TUFLOW')
				self.lwStatus.item(0).setTextColor(self.qgreen)
				#self.lwStatus.insertItem(0,'Not loading.')
				
			elif ext.upper()=='.TPC':
				self.lwStatus.insertItem(0,'.TPC file detected - using TUFLOW_results')
				self.lwStatus.item(0).setTextColor(self.qgreen)
				try:
					#self.lwStatus.insertItem(0,'Loading...')
					res=TUFLOW_results.ResData()
					error, message = res.Load(inFileName)
					if error:
						self.lwStatus.insertItem(0,message)
					self.res.append(res)
						#self.lwStatus.insertItem(0,'Done')
				except:
					self.lwStatus.insertItem(0,'ERROR - Loading Results')
					self.lwStatus.item(0).setTextColor(self.qred)
		
		self.update_reslist()
		
		#load the GIS layers
		if res.GIS.P:
			if res.Index.nPoints>0: #2017-08-AA added check for data in file
				fullfile = os.path.join(fpath,res.GIS.P)
				try:
					addLayer = self.iface.addVectorLayer(fullfile, os.path.basename(fullfile), "ogr")
					# apply tuflow style to imported gis layer
					tf_styles = tuflowqgis_styles.TF_Styles()
					error, message = tf_styles.Load()
					error, message, slyr = tf_styles.Find(os.path.basename(addLayer.source())[:-4], addLayer) #use tuflow styles to find longest matching 
					if error:
						return error, message
					if slyr: #style layer found:
						addLayer.loadNamedStyle(slyr)
						addLayer.triggerRepaint()
				except:
					self.lwStatus.insertItem(0,'Failed to load GIS layer')
					self.lwStatus.item(0).setTextColor(self.qblue)
			else:
				self.lwStatus.insertItem(0,'No points found in GIS Plot Objects .csv, skipping: {0}'.format(res.GIS.P))
				self.lwStatus.item(0).setTextColor(self.qblue)
		if res.GIS.L:
			if res.Index.nLines>0: #2017-08-AA added check for data in file
				fullfile = os.path.join(fpath,res.GIS.L)
				try:
					addLayer = self.iface.addVectorLayer(fullfile, os.path.basename(fullfile), "ogr")
					# apply tuflow style to imported gis layer
					tf_styles = tuflowqgis_styles.TF_Styles()
					error, message = tf_styles.Load()
					error, message, slyr = tf_styles.Find(os.path.basename(addLayer.source())[:-4], addLayer) #use tuflow styles to find longest matching 
					if error:
						return error, message
					if slyr: #style layer found:
						addLayer.loadNamedStyle(slyr)
						addLayer.triggerRepaint()
				except:
					self.lwStatus.insertItem(0,'Failed to load GIS layer')
					self.lwStatus.item(0).setTextColor(self.qblue)
			else:
				self.lwStatus.insertItem(0,'No lines found in GIS Plot Objects .csv, skipping: {0}'.format(res.GIS.L))
				self.lwStatus.item(0).setTextColor(self.qblue)
		if res.GIS.R:
			if res.Index.nRegions>0: #2017-08-AA added check for data in file
				fullfile = os.path.join(fpath,res.GIS.R)
				try:
					addLayer = self.iface.addVectorLayer(fullfile, os.path.basename(fullfile), "ogr")
					# apply tuflow style to imported gis layer
					tf_styles = tuflowqgis_styles.TF_Styles()
					error, message = tf_styles.Load()
					error, message, slyr = tf_styles.Find(os.path.basename(addLayer.source())[:-4], addLayer) #use tuflow styles to find longest matching 
					if error:
						return error, message
					if slyr: #style layer found:
						addLayer.loadNamedStyle(slyr)
						addLayer.triggerRepaint()
				except:
					self.lwStatus.insertItem(0,'Failed to load GIS layer')
					self.lwStatus.item(0).setTextColor(self.qblue)
			else:
				self.lwStatus.insertItem(0,'No regions found in GIS Plot Objects .csv, skipping: {0}'.format(res.GIS.R))
				self.lwStatus.item(0).setTextColor(self.qblue)
		if res.GIS.RL_P:
			#self.lwStatus.insertItem(0,'Loading GIS RL point layer:')
			fullfile = os.path.join(fpath,res.GIS.RL_P)
			#self.lwStatus.insertItem(0,'Debug - fullfile: '+fullfile)
			try:
				self.iface.addVectorLayer(fullfile, os.path.basename(fullfile), "ogr")
			except:
				self.lwStatus.insertItem(0,'Failed to load GIS layer')
		if res.GIS.RL_L:
			#self.lwStatus.insertItem(0,'Loading GIS RL line layer:')
			fullfile = os.path.join(fpath,res.GIS.RL_L)
			try:
				self.iface.addVectorLayer(fullfile, os.path.basename(fullfile), "ogr")
			except:
				self.lwStatus.insertItem(0,'Failed to load GIS layer')
				self.lwStatus.item(0).setTextColor(self.qblue)

	def update_reslist(self):
		#self.lwStatus.insertItem(0,'Updating results list')
		self.ResList.clear()
		for res in self.res:
			self.ResList.addItem(res.displayname)
			
		#set the items as selected:
		for x in range(0, self.ResList.count()):
			list_item = self.ResList.item(x)
			self.ResList.setItemSelected(list_item, True)

		#also update the types of results that are available
		self.ts_types_P = []
		self.ts_types_L = []
		self.ts_types_R = []
		tmp_list = []
		#self.lwStatus.insertItem(0,"res.Types: {0}".format(res.Types))
		for res in self.res:
			for restype in res.Types:
				#self.lwStatus.insertItem(0,"restype: {0}".format(restype))
				restype = restype.replace('1D ','')
				restype = restype.replace('2D ','')
				if restype.upper() == 'LINE FLOW':
					restype = 'Flows' #don't differentiate between 1D and 2D flows
				if restype.upper() == 'POINT WATER LEVEL':
					restype = 'Water Levels' #don't differentiate between 1D and 2D water levels
				tmp_list.append(restype)
			
			if res.Channels: #bug fix which would not load results with no 1D
				if res.Channels.nChan>0: #
					tmp_list.append('US Levels')
					tmp_list.append('DS Levels')
		
		#get unique
		#self.lwStatus.insertItem(0,'tmp_list: {0}'.format(tmp_list))
		unique_res = list(OrderedDict.fromkeys(tmp_list))
		for restype in unique_res:
			#self.lwStatus.insertItem(0,'Debug: '+restype)
			if restype.upper() in ('WATER LEVELS'):
				self.ts_types_P.append('Level')
			elif restype.upper() in ('ENERGY LEVELS'):
				self.ts_types_P.append('Energy Level')
			elif restype.upper() in ('POINT VELOCITY'):
				self.ts_types_P.append('Velocity')
			elif restype.upper() in ('POINT X-VEL'):
				self.ts_types_P.append('VX')
			elif restype.upper() in ('POINT Y-VEL'):
				self.ts_types_P.append('VY')
			elif restype.upper() in ('FLOWS'):
				self.ts_types_L.append('Flows')
			elif restype.upper() in ('VELOCITIES'):
				self.ts_types_L.append('Velocities')
			elif restype.upper() in ('LINE FLOW AREA'):
				self.ts_types_L.append('Flow Area')
			elif restype.upper() in ('LINE INTEGRAL FLOW'):
				self.ts_types_L.append('Flow Integral')
			elif restype.upper() in ('US LEVELS'):
				self.ts_types_L.append('US Levels')
			elif restype.upper() in ('DS LEVELS'):
				self.ts_types_L.append('DS Levels')
			elif restype.upper() in ('DS LEVELS'):
				self.ts_types_L.append('DS Levels')
			elif restype.upper() in ('LINE STRUCTURE FLOW'):
				self.ts_types_L.append('Structure Flows')
			elif restype.upper() in ('STRUCTURE LEVELS'):
				self.ts_types_L.append('Structure Levels')
			elif restype.upper() in ('REGION AVERAGE WATER LEVEL'): #2017-09-AA
				self.ts_types_R.append('Average Level')
			elif restype.upper() in ('REGION MAX WATER LEVEL'): #2017-09-AA
				self.ts_types_R.append('Max Level')
			elif restype.upper() in ('REGION FLOW INTO'): #2017-09-AA
				self.ts_types_R.append('Flow Into')
			elif restype.upper() in ('REGION FLOW OUT OF'): #2017-09-AA
				self.ts_types_R.append('Flow Out')
			elif restype.upper() in ('REGION VOLUME'): #2017-09-AA
				self.ts_types_R.append('Volume')
			elif restype.upper() in ('REGION SINK/SOURCE'): #2017-09-AA
				self.ts_types_R.append('Sink/Source')
			else:
				self.lwStatus.insertItem(0,'ERROR unhandled type: '+restype)
				self.lwStatus.item(0).setTextColor(self.qred)
				
		#add current time
		self.ts_types_P.append('Current Time')
		self.ts_types_L.append('Current Time')
		self.ts_types_R.append('Current Time')

	def close_res(self):
		"""
			Close results file
		"""
		for x in reversed(range(0, self.ResList.count())): #2017-06-AB reverse in case muiltiple results are selected
			list_item = self.ResList.item(x)
			if list_item.isSelected():
				res = self.res[x]
				self.res.remove(res)
		
		self.update_reslist() #2017-06-AB move out of for loop
	
	def add_1dTa(self):
		"""
		Add 1D hydraulic check tables for plotting

		:return: HydTables Class Object
		"""
		
		settings = QSettings()
		lastFolder = str(settings.value("TUFLOW_Res_Dock/1d_lastFolder", os.sep))
		if (len(lastFolder) > 0):  # use last folder if stored
			fpath = lastFolder
		else:
			cLayer = self.canvas.currentLayer()
			if cLayer:  # if layer selected use the path to this
				dp = cLayer.dataProvider()
				ds = dp.dataSourceUri()
				fpath = os.path.dirname(unicode(ds))
			else:  # final resort to current working directory
				fpath = os.getcwd()
		
		inFileNames = QFileDialog.getOpenFileNames(self.iface.mainWindow(), 'Open TUFLOW 1d_ta_tables_check', fpath,
		                                           "TUFLOW 1d_ta_tables_check (*.csv)")
		if not inFileNames:  # empty list
			return
		
		for x in range(len(inFileNames)):
			# Store the path we just looked in
			inFileName = inFileNames[x]
			fpath, fname = os.path.split(inFileName)
			if x == 0:
				if fpath != os.sep and fpath.lower() != 'c:\\' and fpath != '':
					settings.setValue("TUFLOW_Res_Dock/1d_lastFolder", fpath)
			
			try:
				self.hydTables.loadData(inFileNames[x])
				self.HydPropList.addItem(self.hydTables.loadedData[x].displayName)
				self.lwStatus.insertItem(0, 'Successfully loaded 1d_ta_Tables.csv')
			except:
				self.lwStatus.insertItem(0, 'ERROR - Loading Results')
		# set the items as selected:
		for x in range(0, self.HydPropList.count()):
			self.HydPropList.item(x).setSelected(True)
		
		self.loc_changed()
	
	def close_1dTa(self):
		"""
		Close 1D hydraulic check tables for plotting

		:return: Void
		"""
		
		for x in reversed(range(self.HydPropList.count())):
			if self.HydPropList.item(x).isSelected():
				self.hydTables.closeData(self.HydPropList.item(x).text())
				self.HydPropList.takeItem(x)
		
		self.loc_changed()
		
	def add_profileIntTool(self, profileIntTool):
		"""
		Open profile integrity tool in an existing tuplot.
		
		:param profileIntTool: longprofile class object
		:return:
		"""
		
		self.profileIntTool = profileIntTool
		self.layerChanged()
		self.select_changed()

	def layerChanged(self):
		self.is_intTool = False
		self.geom_type = None #store geometry type for later use
		if self.cbForceXS.isChecked():
			xs_format = True
		elif self.cbForceRes.isChecked():
			xs_format = False
		else: #determine if xs or results
			#self.lwStatus.insertItem(0,'Checking vector geometry')
			self.cLayer = self.canvas.currentLayer()
			if self.cLayer and (self.cLayer.type() == QgsMapLayer.VectorLayer):
				valid = False
				dp = self.cLayer.dataProvider()
				GType = dp.geometryType()
				if (GType == QGis.WKBPoint):
					self.geom_type = 'P'
					valid = True
				if (GType == QGis.WKBLineString):
					self.geom_type = 'L'
					valid = True
				if (GType == QGis.WKBPolygon):
					self.geom_type = 'R'
					#message = "Not expecting polygon data"
					valid = True
				else:
					message = "Expecting points or lines for 1d_tab format"
			else:
				valid = False
				message = "Invalid layer or no layer selected"
				self.lwStatus.insertItem(0,'Message: '+message)
			
			xs_format = False
			if valid: # geometry is valid, check for correct attributes
				xs_format = True
				if (dp.fieldNameIndex('Source') != 0):
					xs_format = False
					#self.lwStatus.insertItem(0,'First field is not named "Source" Field')
				if (dp.fieldNameIndex('Type') != 1):
					xs_format = False
					#self.lwStatus.insertItem(0,'Second field is not named "Type" Field')
				if (dp.fieldNameIndex('Flags') != 2):
					xs_format = False
					#self.lwStatus.insertItem(0,'Third field is not named "Flags" Field')
			else:
				#QMessageBox.information(self.iface.mainWindow(), "1D XS Viewer", "Message: "+message)
				self.lwStatus.insertItem(0,'Message: '+message)
		if xs_format: # need to get sections
			self.is_xs = True
			self.locationDrop.clear()
			self.IDs = []
			self.IDList.clear()
			if len(self.xsLoaded) > 0:
				if self.cLayer not in self.xsLoadedName:
					result = TUFLOW_XS.XS()
					result.loadIntoMemory(self.cLayer)
					self.xsLoaded.append(result)
					self.xsLoadedName.append(self.cLayer)
					self.lwStatus.insertItem(0, 'Successfully loaded in XS data')
			else:
				result = TUFLOW_XS.XS()
				result.loadIntoMemory(self.cLayer)
				self.xsLoaded.append(result)
				self.xsLoadedName.append(self.cLayer)
				self.lwStatus.insertItem(0, 'Successfully loaded in XS data')
			self.locationDrop.addItem("Tabular Data (Section)")
		elif self.profileIntTool is not None and self.cLayer in self.profileIntTool.inLyrs:  # might be from the 1D integrity check
			self.is_intTool = True
			self.locationDrop.clear()
			self.IDs = []
			self.IDList.clear()
			self.locationDrop.addItem('Check Downstream Integrity')
		else: #it might be a result file
			self.is_xs = False
			self.locationDrop.clear()
			if len(self.res) == 0 and not self.hydTables.loadedData:
				self.locationDrop.addItem('No Results Open / Not a TUFLOW layer')
				self.lwStatus.item(0).setTextColor(self.qblue)
				return
			self.cLayer = self.canvas.currentLayer()
			#self.sourcelayer.clear()
			self.locationDrop.clear()
			self.IDs = []
			self.IDList.clear()
			
			#determine latest version (if multiple results selected)
			version = 1
			if not self.res and self.hydTables.loadedData:
				self.res_version = 2
			else:
				for i in range(len(self.res)):
					#self.lwStatus.insertItem(0,'Results file '+str(i+1)+' has version: '+str(self.res[i].formatVersion))
					version = max(version,self.res[i].formatVersion)
					self.res_version = version
							
			if self.res_version>2:
				self.lwStatus.insertItem(0,'ERROR - Unxpected results version, expecting 1 or 2.')
				self.lwStatus.item(0).setTextColor(self.qred)
				self.qgis_disconnect()
					
			if self.cLayer and (self.cLayer.type() == QgsMapLayer.VectorLayer):
				GType = self.cLayer.dataProvider().geometryType()
				if (GType == QGis.WKBPoint):
					self.GeomType = "Point"
					if self.res_version == 1:
						self.locationDrop.addItem("Timeseries") #this triggers loc_changed which populates data fields
					elif self.res_version == 2:
						if (self.cLayer.name().find('_PLOT_')>-1):
							self.locationDrop.addItem("Timeseries") #this triggers loc_changed which populates data fields
						else:
							self.lwStatus.insertItem(0,'ERROR - Not a TUFLOW Layer Selected')
							self.lwStatus.item(0).setTextColor(self.qblue)
							self.locationDrop.addItem("Not a TUFLOW Layer Selected")
				elif (GType == QGis.WKBLineString):
					self.GeomType = "Line"
					if self.res_version == 1:
						self.locationDrop.addItem("Timeseries")
						self.locationDrop.addItem("Long Profile")
					elif self.res_version == 2:
						if (self.cLayer.name().find('_PLOT_')>-1):
							self.locationDrop.addItem("Timeseries")
							self.locationDrop.addItem("Long Profile")
							self.locationDrop.addItem("Hydraulic Properties")
						else:
							self.lwStatus.insertItem(0,'ERROR - Not a TUFLOW Layer Selected')
							self.lwStatus.item(0).setTextColor(self.qblue)
							self.locationDrop.addItem("Not a TUFLOW Layer Selected")
				elif (GType == QGis.WKBPolygon): #2017-09-AA polygon
					self.GeomType = "Polygon"
					if self.res_version == 1:
						self.lwStatus.insertItem(0,'ERROR - Polygons not supported for 2013 format results')
						self.locationDrop.addItem("Polygons not supported")
					elif self.res_version == 2:
						if (self.cLayer.name().find('_PLOT_')>-1):
							self.locationDrop.addItem("Timeseries")
						else:
							self.lwStatus.insertItem(0,'ERROR - Not a TUFLOW Layer Selected')
							self.lwStatus.item(0).setTextColor(self.qblue)
							self.locationDrop.addItem("Not a TUFLOW Layer Selected")

				else:
					self.GeomType = None
					self.clear_figure()
				self.locationDrop.setCurrentIndex(0)
				
				#index to ID
				self.idx = self.cLayer.fieldNameIndex('ID')
				if (self.idx < 0):
					self.locationDrop.clear()
					self.locationDrop.addItem("Not a TUFLOW Layer Selected")
				

			else:
				self.locationDrop.addItem("Not a TUFLOW Layer Selected")
				self.clear_figure()
				
		if self.handler:
			QObject.disconnect(self.selected_layer, SIGNAL("selectionChanged()"),self.select_changed)
			self.handler = False
			self.selected_layer = None
		if self.cLayer is not None:
			if self.cLayer.isValid():
				if self.cLayer.type() == QgsMapLayer.VectorLayer:
					QObject.connect(self.cLayer,SIGNAL("selectionChanged()"),self.select_changed)
					self.selected_layer = self.cLayer
		self.refresh()
		
	def select_changed(self):
		self.IDList.clear()
		available_types = []
		error = False 
		if self.is_xs: #dealing with tabular / section data
			self.xs_list = []
			for xs in self.cLayer.selectedFeatures():
				self.xs_list.append(xs[0])
			if self.ResList.count() > 0:
				selCount = 0
				for i in range(self.ResList.count()):
					if self.ResList.item(i).isSelected():
						selCount += 1
				if selCount > 0:
					plotLayer = tuflowqgis_find_plot_layers()
					xsNodes, xsChannels, message, error = find_waterLevelPoint(self.cLayer.selectedFeatures(), plotLayer)
					if error:
						self.lwStatus.insertItem(0, '{0}'.format(message))
						self.xsResults = False
						error = False  # reset error
					else:
						self.xsResults = True
						xsLayerIndex = self.xsLoadedName.index(self.cLayer)
						self.xsLoaded[xsLayerIndex].getResults(xsNodes, xsChannels, self.res, self.xs_list)
				# populate the selected elements
				self.IDList.clear()
				try:
					for xs in self.xs_list:
						self.IDList.addItem(xs)
				except:
					self.lwStatus.insertItem(0, 'Error updating xs source list')
		elif self.is_intTool:
			pass
		else: #dealing with results
			if len(self.res) == 0:
				self.lwStatus.insertItem(0,'No Results Open')
				self.lwStatus.item(0).setTextColor(self.qblue)
				return
			#self.lwStatus.insertItem(0,'Selection Changed')
			self.IDs = []
			self.Doms = []
			self.Source_Att = []
			self.IDList.clear()
			#self.lwStatus.insertItem(0,'Debug - GeomType: '+self.geom_type)
			if self.res_version == 1:
				#self.lwStatus.insertItem(0,'Debug - version 1')
				if self.idx >= 0:
					if self.cLayer:
						try:
							for feature in self.cLayer.selectedFeatures():
								try:
									fieldvalue=feature['ID']
									self.IDs.append(fieldvalue.strip())
									self.IDList.addItem(fieldvalue.strip())
								except:
									warning = True #suppress the warning below, most likely due to a "X" type channel or blank name
									
						except:
							error = True
			elif self.res_version == 2:
				if self.idx >= 0:
					if self.cLayer:
						try:
							for feature in self.cLayer.selectedFeatures():
								try: # get ID data
									fieldvalue=feature['ID']
									self.IDs.append(fieldvalue.strip())
									self.IDList.addItem(fieldvalue.strip())
								except:
									warning = True #suppress the warning below, most likely due to a "X" type channel or blank name
								try: # get Type (1D, 2D or RL)
									fieldvalue=feature['Type']
									dom = fieldvalue.strip().upper()
									if (dom.find('NODE') >= 0):
										dom = '1D'
									elif (dom.find('CHAN') >= 0):
										dom = '1D'
									self.Doms.append(dom)
									type_str = dom+'|'
								except:
									self.lwStatus.insertItem(0,'ERROR - Processing "Type" attribute '+str(fieldvalue))
									error = True
								try: # get Source
									fieldvalue=feature['Source']
									Source_Att = fieldvalue.strip().upper()
									
									if dom == 'RL': # ignore source attribute for RL as this contains information on the 
										if self.geom_type == 'P':
											Source_Att = 'H'
										elif self.geom_type == 'L':
											Source_Att = 'Q'
									self.Source_Att.append(Source_Att)
									type_str = type_str+Source_Att
									
									if available_types.count(type_str)<1:
										available_types.append(type_str)
									
								except:
									error = True
						except:
							error = True
			
			if self.locationDrop.currentText() == "Long Profile":
				for res in self.res:
					res.LP.connected = False
					res.LP.static = False
					if (len(self.IDs)==0):
						error = True
						message = 'No features selected - skipping'
					elif (len(self.IDs)==1):
						if self.res_version == 1: #2013 version only supports 1D
							self.Doms.append('1D')
						if self.Doms[0]=='1D':
							error, message = res.LP_getConnectivity(self.IDs[0],None)
						else:
							error = True
							message = 'Selected object is not 1D channel - type: '+self.Doms[0]
					elif (len(self.IDs)==2):
						if self.res_version == 1: #2013 version only supports 1D
							self.Doms.append('1D')
							self.Doms.append('1D')
						if self.Doms[0]=='1D' and self.Doms[1]=='1D':
							error, message = res.LP_getConnectivity(self.IDs[0],self.IDs[1])
						else:
							error = True
							message = 'Selected objects are not 1D channels - types: '+self.Doms[0]+' and '+self.Doms[0]
					else:
						self.lwStatus.insertItem(0,'WARNING - More than 2 objects selected.  Using only 2.')
						self.lwStatus.item(0).setTextColor(self.qblue)
						error, message = res.LP_getConnectivity(self.IDs[0],self.IDs[1])
					if error:
						self.lwStatus.insertItem(0,message)
						self.lwStatus.insertItem(0,'ERROR - Getting LP connectivity')
						self.lwStatus.item(0).setTextColor(self.qred)
					else:
						error, message = res.LP_getStaticData()
						if error:
							self.lwStatus.insertItem(0,message)
						if res.formatVersion > 1:
							if res.LP.adverseH.nLocs > 0 or res.LP.adverseE.nLocs > 0:
								self.lwStatus.insertItem(0,'WARNING - Adverse gradients detected along profile')
								self.lwStatus.item(0).setTextColor(self.qred)
		
		if ((not self.is_xs) and (self.locationDrop.currentText() == "Timeseries")):
			#grey out the types that are not in the current selection
			#self.lwStatus.insertItem(0,'Debug shading restypes')

			cleaned_types = []
			for type_str in available_types:
				dom, type = type_str.split('|')
				if dom == '2D':
					if type.find('QI')>=0:
						type.replace('QI','')
						if cleaned_types.count('Flow Integral')<1:
							cleaned_types.append('Flow Integral')
					if type.find('QA')>=0:
						type.replace('QA','')
						if cleaned_types.count('Flow Area')<1:
							cleaned_types.append('Flow Area')
					if type.find('QS')>=0:
						type.replace('QS','')
						if cleaned_types.count('Structure Flows')<1:
							cleaned_types.append('Structure Flows')
					if type.find('HU')>=0:
						type.replace('HU','')
						if cleaned_types.count('Structure Levels')<1:
							cleaned_types.append('Structure Levels')
					if type.find('HD')>=0:
						type.replace('HD','')
						if cleaned_types.count('Structure Levels')<1:
							cleaned_types.append('Structure Levels')
					if type.find('Q')>=0:
						type.replace('Q','')
						if cleaned_types.count('Flows')<1:
							cleaned_types.append('Flows')
				elif dom == 'RL':
					if self.geom_type=='P':
						if cleaned_types.count('Level')<1:
							cleaned_types.append('Level')
					elif self.geom_type=='L':
						if cleaned_types.count('Flows')<1:
							cleaned_types.append('Flows')
				elif dom == '1D':
					if self.geom_type=='P':
						if type.find('H')>=0:
							type.replace('H','')
							if cleaned_types.count('Level')<1:
								cleaned_types.append('Level')
					elif self.geom_type=='L':
						if type.find('Q_')>=0:
							type.replace('Q_','')
							if cleaned_types.count('Flows')<1:
								cleaned_types.append('Flows')
						if type.find('V_')>=0:
							type.replace('V_','')
							if cleaned_types.count('Velocities')<1:
								cleaned_types.append('Velocities')
						if cleaned_types.count('Flow Area')<1: #'QA' not coming through to GIS
							cleaned_types.append('Flow Area')
			#loop through all entries and colour as appropriate 2017-06-AD disabled
			#for x in range(0,self.ResTypeList.count()):
			#	list_item = self.ResTypeList.item(x)
			#	type_str = list_item.text()
			#	if cleaned_types.count(type_str) > 0:
			#		self.ResTypeList.item(x).setTextColor(self.qblack)
			#	else:
			#		self.ResTypeList.item(x).setTextColor(self.qgrey)

		if not error:
			self.start_draw()
			
	def timeChanged(self):
		self.start_draw()
		
	def res_type_changed(self):
		#self.lwStatus.insertItem(0,'Result type changed - use Update Plot to Update')
		#self.lwStatus.item(0).setTextColor(self.qgrey)
		#self.lwStatus.insertItem(0,'Current Items are : {0}'.format(self.ResTypeList.selectedItems()[0].text()))
		self.start_draw()

	def update_pressed(self):
		self.start_draw()
		
	def loc_changed(self):
		loc = self.locationDrop.currentText()
		self.ResTypeList.clear()
		self.ResTypeList_ax2.clear()
		if (loc == "Timeseries"):
			self.listTime.clear()
			if (self.GeomType == "Point"):
				for restype in self.ts_types_P:
					self.ResTypeList.addItem(restype)
					self.ResTypeList_ax2.addItem(restype)
			elif (self.GeomType == "Line"):
				for restype in self.ts_types_L:
					self.ResTypeList.addItem(restype)
					self.ResTypeList_ax2.addItem(restype)
			elif (self.GeomType == "Polygon"):
				for restype in self.ts_types_R:
					self.ResTypeList.addItem(restype)
					self.ResTypeList_ax2.addItem(restype)
			else:
				self.lwStatus.insertItem(0,'ERROR should not be here loc_changed_ts_A')
				self.lwStatus.item(0).setTextColor(self.qblue)
			
		elif (loc == "Long Profile"):
			self.ResTypeList.clear()
			self.ResTypeList.addItem("Max Water Level")
			self.ResTypeList.addItem("Water Level at Time")
			try: #if index fails no energy data available
				self.ts_types_P.index('Energy Level')
				self.ResTypeList.addItem("Max Energy Level")
				self.ResTypeList.addItem("Energy Level at Time")
			except:
				pass
			self.ResTypeList.addItem("Bed Level")
			self.ResTypeList.addItem("Left Bank Obvert")
			self.ResTypeList.addItem("Right Bank Obvert")
			self.ResTypeList.addItem("Pit Ground Levels (if any)")
			self.ResTypeList.addItem("Adverse Gradients (if any)")
			self.ResTypeList_ax2.addItem("Time Hmax")
			
			for res in self.res:
				res.LP.connected = False
				res.LP.static = False
				if (len(self.IDs)==0):
					error = True
					message = 'No features selected - skipping'
				elif (len(self.IDs)==1):
					if self.res_version == 1: #2013 version only supports 1D
						self.Doms.append('1D')
					if self.Doms[0]=='1D':
						error, message = res.LP_getConnectivity(self.IDs[0],None)
					else:
						error = True
						message = 'Selected object is not 1D channel - type: '+self.Doms[0]
				elif (len(self.IDs)==2):
					if self.res_version == 1: #2013 version only supports 1D
						self.Doms.append('1D')
						self.Doms.append('1D')
					if self.Doms[0]=='1D' and self.Doms[1]=='1D':
						error, message = res.LP_getConnectivity(self.IDs[0],self.IDs[1])
					else:
						error = True
						message = 'Selected objects are not 1D channels - types: '+self.Doms[0]+' and '+self.Doms[0]
				else:
					self.lwStatus.insertItem(0,'WARNING - More than 2 objects selected.  Using only 2.')
					self.lwStatus.item(0).setTextColor(self.qblue)
					error, message = res.LP_getConnectivity(self.IDs[0],self.IDs[1])
				if error:
					self.lwStatus.insertItem(0,message)
					self.lwStatus.insertItem(0,'ERROR - Getting LP connectivity')
					self.lwStatus.item(0).setTextColor(self.qred)
				else:
					error, message = res.LP_getStaticData()
					if error:
						self.lwStatus.insertItem(0,message)
					if res.formatVersion > 1:
						if res.LP.adverseH.nLocs > 0 or res.LP.adverseE.nLocs > 0:
							self.lwStatus.insertItem(0,'WARNING - Adverse gradients detected along profile')
							self.lwStatus.item(0).setTextColor(self.qred)
		elif loc == "Hydraulic Properties":
			if self.HydPropList.count() > 0:
				selCount = 0
				for i in range(self.HydPropList.count()):
					if self.HydPropList.item(i).isSelected():
						selCount += 1
				if selCount > 0:
					for h in self.hydTables.loadedData[0].channelHydTa_headers:
						if h.lower() != 'elevation':
							self.ResTypeList.addItem(h)
							self.ResTypeList_ax2.addItem(h)
				self.ResTypeList.addItem('US XSection')
				self.ResTypeList.addItem('DS XSection')
				self.ResTypeList_ax2.addItem('US XSection')
				self.ResTypeList_ax2.addItem('DS XSection')
			else:
				self.ResTypeList.addItem('Add 1d_ta_tables_check.csv')
				self.ResTypeList.addItem('to get properties')
		elif loc == "Tabular Data (Section)":
			xsLayerIndex = self.xsLoadedName.index(self.cLayer)
			for type in self.xsLoaded[xsLayerIndex].xsLayer.xsTypes:
				self.ResTypeList.addItem(type)
				self.ResTypeList_ax2.addItem(type)
			if self.ResList.count() > 0:
				selCount = 0
				for i in range(self.ResList.count()):
					if self.ResList.item(i).isSelected():
						selCount += 1
				if selCount > 0:
					self.ResTypeList.addItem('Max Water Level')
					self.ResTypeList.addItem('Water Level at Time')
					self.ResTypeList.addItem('Left Bank')
					self.ResTypeList.addItem('Right Bank')
					self.ResTypeList_ax2.addItem('Max Water Level')
					self.ResTypeList_ax2.addItem('Water Level at Time')
					self.ResTypeList_ax2.addItem('Left Bank')
					self.ResTypeList_ax2.addItem('Right Bank')
			if self.HydPropList.count() > 0:
				selCount = 0
				for i in range(self.HydPropList.count()):
					if self.HydPropList.item(i).isSelected():
						selCount += 1
				if selCount > 0:
					for h in self.hydTables.loadedData[0].xsHydTa_headers:
						if h.lower() != 'elevation':
							self.ResTypeList.addItem(h)
							self.ResTypeList_ax2.addItem(h)
		elif loc == 'Check Downstream Integrity':
			for path in self.profileIntTool.pathsName:
				self.ResTypeList.addItem(path)
			self.ResTypeList.addItem('Flags')
			if self.profileIntTool.coverLimit is not None:
				self.ResTypeList.addItem('Ground')
		else:
			self.ResTypeList.clear()
			
		# add times
		try:
			times = self.res[0].times
			self.listTime.clear()
			for time in times:
				self.listTime.addItem("%.4f" % time)
			item = self.listTime.item(0)
			self.listTime.setItemSelected(item, True)
		except:
			self.lwStatus.insertItem(0,'WARNING - Unable to populate times, check results loaded.')
			self.lwStatus.item(0).setTextColor(self.qblue)
		item = self.ResTypeList.item(0) # select 1st item by default
		self.ResTypeList.setItemSelected(item, True)
		self.start_draw()
		
	def toggle_ax2_listWidget(self):
		
		if self.cb2ndAxis.isChecked():
			self.ResTypeList_ax2.setEnabled(True)
		else:
			self.ResTypeList_ax2.setEnabled(False)

	def animate_Plot(self):
		start = True
		plot_LP = False
		plot_TS = False
		
		# check what type of plot is selected
		loc = self.locationDrop.currentText()
		if (loc=="Long Profile"):
			plot_LP = True
		elif (loc=="Timeseries"):
			plot_TS = True
		else:
			self.lwStatus.insertItem(0,'ERROR - Determing plot type when animating')
			self.lwStatus.item(0).setTextColor(self.qblue)
			start = False
			return
		
		#if (loc!="Long Profile"): # LP
		#	self.lwStatus.insertItem(0,'ERROR - Please choose Long Profile type before animating.')
		#	self.lwStatus.item(0).setTextColor(self.qblue)
		#	start = False
		#	return
		
		# Compile of output types (bed level, max wse)
		restype = []
		for x in range(0, self.ResTypeList.count()):
			list_item = self.ResTypeList.item(x)
			if list_item.isSelected():
				restype.append(list_item.text())
				
		if plot_LP: #check that valid LP data is selected
			fnam_add = 'LP'
			#one or two elements selected
			if len (self.IDs) == 0:
				self.lwStatus.insertItem(0,'ERROR - No elements selected.')
				start = False
				return
			elif len (self.IDs) > 2:
				self.lwStatus.insertItem(0,"ERROR - More than 2 ID's selected.")
				start = False
				return
			
			#one of the time varying datasets is on
			ntvarying = 0
			if restype.count('Water Level at Time')==0:
				ntvarying = ntvarying + 1
			if restype.count('Energy Level at Time')==0:
				ntvarying = ntvarying + 1
			if ntvarying == 0:
				self.lwStatus.insertItem(0,"ERROR - For Long Profile Energy or Water level at time not selected!")
				start = False
				return
		
		elif plot_TS:
			fnam_add = 'TS'
			if restype.count('Current Time')==0:
				self.lwStatus.insertItem(0,"ERROR - For Timeseries Current Time is not selected!")
				start = False
				return
			
		# results:
		ResIndexs = []
		if self.ResList.count() == 0:
			self.lwStatus.insertItem(0,'ERROR - No results open...')
			start = False
			return
		else:
			for x in range(0, self.ResList.count()):
				list_item = self.ResList.item(x)
				if list_item.isSelected():
					ResIndexs.append(x)
		# times
		if self.listTime.count() == 0:
			self.lwStatus.insertItem(0,'ERROR - No output times detected.')
			start = False
			return
			
		#get file extension from drop list
		fext = self.dropExportExt.currentText()
		
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
				QMessageBox.information(self.iface.mainWindow(), "Information", "Saving {0} images to: {1}\nAfter selecting ok, please wait while the images are created.\nYou will be notified when this has finished.".format(fext,self.res[0].fpath))
				
				for x in range(0, self.listTime.count()):
					item = self.listTime.item(x)
					self.listTime.setItemSelected(item, True)
					self.draw_figure()
					filenum = str(x+1)
					filenum = filenum.zfill(nWidth)
					#fname = 'QGIS_LP_'+filenum+'.pdf'
					fname = 'QGIS_{0}_{1}{2}'.format(fnam_add,filenum,fext)
					if not os.path.exists(os.path.join(self.res[0].fpath, "animation")):
						os.mkdir(os.path.join(self.res[0].fpath, "animation"))
					fullpath = os.path.join(self.res[0].fpath, "animation", fname)
					self.plotWdg.figure.savefig(fullpath)
					self.listTime.setItemSelected(item, False)
				QMessageBox.information(self.iface.mainWindow(), "Information", "Processing Complete")
			except:
				QMessageBox.critical(self.iface.mainWindow(), "ERROR", "An error occurred processing long profile")
			
	def start_draw(self):
		self.clear_figure()
		if self.is_xs: #dealing with tabular / section data
			if len(self.xs_list) > 0:
				draw = True
			else:
				draw = False
		elif self.is_intTool:
			draw = True
		else:
			loc = self.locationDrop.currentText()
			type = []
			
			# Compile of output types
			#self.lwStatus.insertItem(0,'Current Items are : {0}'.format(self.ResTypeList.selectedItems()[0].text()))
			items = self.ResTypeList.selectedItems()
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
			#self.lwStatus.insertItem(0,'call draw_figure()')
			self.draw_figure()
			
	def showIt(self):
		self.layout = self.frame_for_plot.layout()
		minsize = self.minimumSize()
		maxsize = self.maximumSize()
		self.setMinimumSize(minsize)
		self.setMaximumSize(maxsize)

		self.iface.mapCanvas().setRenderFlag(True)
		
		self.artists = []
		self.labels = []
		
		#self.fig = Figure( (1.0, 1.0), linewidth=0.0, subplotpars = matplotlib.figure.SubplotParams(left=0.125, bottom=0.1, right=0.9, top=0.9, wspace=0, hspace=0))
		self.fig, self.subplot = plt.subplots()
			
		font = {'family' : 'arial', 'weight' : 'normal', 'size'   : 12}
		
		rect = self.fig.patch
		rect.set_facecolor((0.9,0.9,0.9))
		#self.subplot = self.fig.add_axes((0.10, 0.15, 0.85,0.82))
		self.subplot.set_xbound(0,1000)
		self.subplot.set_ybound(0,1000)			
		self.manageMatplotlibAxe(self.subplot)
		canvas = FigureCanvasQTAgg(self.fig)
		sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		sizePolicy.setHorizontalStretch(0)
		sizePolicy.setVerticalStretch(0)
		canvas.setSizePolicy(sizePolicy)
		self.plotWdg = canvas
		
		self.gridLayout.addWidget(self.plotWdg)
		if matplotlib.__version__ < 1.5 :
			mpltoolbar = matplotlib.backends.backend_qt4agg.NavigationToolbar2QTAgg(self.plotWdg, self.frame_for_toolbar)
		else:
			mpltoolbar = matplotlib.backends.backend_qt4agg.NavigationToolbar2QT(self.plotWdg, self.frame_for_toolbar)
		lstActions = mpltoolbar.actions()
		mpltoolbar.removeAction( lstActions[ 7 ] ) #remove customise subplot
			
		#create curve
		label = "test"
		x=numpy.linspace(-numpy.pi, numpy.pi, 201)
		y=numpy.sin(x)
		a, = self.subplot.plot(x, y)
		self.artists.append(a)
		self.labels.append(label)
		self.subplot.hold(True)
		self.plotWdg.draw()
	
	def manageMatplotlibAxe(self, axe1):
		axe1.grid()
		axe1.tick_params(axis = "both", which = "major", direction= "out", length=10, width=1, bottom = True, top = False, left = True, right = False)
		axe1.minorticks_on()
		axe1.tick_params(axis = "both", which = "minor", direction= "out", length=5, width=1, bottom = True, top = False, left = True, right = False)
	
	def clear_figure(self):
		self.labels = []
		self.subplot.cla() #clear axis
		try:
			self.axis2.cla()
		except:
			self.ax2_exists = False
		
	def showMenu(self, pos):
		menu = QMenu(self)
		exportCsv_action = QAction("Export Plot Data to Csv", menu)
		setAxis_action = QAction("Set Axis Limits", menu)
		setLabels_action = QAction("Set Axis Labels", menu)
		exportCsv_action.triggered.connect(self.export_csv)
		setAxis_action.triggered.connect(self.set_axisLimits)
		setLabels_action.triggered.connect(self.set_axisLabels)
		menu.addAction(exportCsv_action)
		menu.addAction(setAxis_action)
		menu.addAction(setLabels_action)
		if self.locationDrop.currentText() == 'Check Downstream Integrity':
			selectPaths_action = QAction('Select Networks in Current Path(s) in Map Window', menu)
			selectPaths_action.triggered.connect(self.selectPaths)
			menu.addAction(selectPaths_action)
		menu.popup(self.plotWdg.mapToGlobal(pos))
		
	def showMenuSelElements(self, pos):
		menu = QMenu(self)
		if self.locationDrop.currentText() == 'Check Downstream Integrity':
			selectPaths_action = QAction('Select Networks in Current Path(s) in Map Window', menu)
			selectPaths_action.triggered.connect(self.selectPaths)
			menu.addAction(selectPaths_action)
		menu.popup(self.IDList.mapToGlobal(pos))
		
	def export_csv(self):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Export csv!")
		
		settings = QSettings()
		lastFolder = str(settings.value("TUFLOW_Res_Dock/export_csv", os.sep))
		if (len(lastFolder) > 0):  # use last folder if stored
			fpath = lastFolder
		else:
			fpath = os.getcwd()
		
		if self.locationDrop.currentText() == "Timeseries":
			# Get data headers
			nRes = self.ResList.count()
			dataHeader = ''
			resultFiles = []
			c = []  # index for change in result files or current time is selected
			for i, label in enumerate(self.labels):
				if nRes > 1:
					resultFile = label.split(":")
					if resultFile[0] not in resultFiles:
						resultFiles.append(resultFile[0])
						if self.cb2ndAxis.isChecked():
							c.append(int(i/2))  # removes results of axis 2. Should work in most cases
						else:
							c.append(i)
						dataHeader += 'Time (hr),'
					dataHeader += '{0},'.format(label)
				else:
					if i == 0:
						c.append(0)
						resultFiles.append(label)
						dataHeader += 'Time (hr),'
					dataHeader += '{0},'.format(label)
			# determine maximum data length from all result files
			maxLen = 0
			for i in c:
				maxLen = max(maxLen, len(self.subplot.lines[i].get_data()[0]))
			# Get data
			for i, resultFile in enumerate(resultFiles):
				if i == 0:
					data = self.subplot.lines[c[i]].get_data()[0]  # write X axis first
					data = numpy.reshape(data, [len(data), 1])
					if len(data) < maxLen:
						diff = maxLen - len(data)
						fill = numpy.zeros([diff, 1]) * numpy.nan
						data = numpy.append(data, fill, axis=0)
				else:
					dataX = self.subplot.lines[c[i]].get_data()[0]  # Write X axis again for new results
					dataX = numpy.reshape(dataX, [len(dataX), 1])
					if len(dataX) < maxLen:
						diff = maxLen - len(dataX)
						fill = numpy.zeros([diff, 1]) * numpy.nan
						dataX = numpy.append(dataX, fill, axis=0)
					data = numpy.append(data, dataX, axis=1)
				if i < len(c) - 1:  # isn't last result file
					for line in self.subplot.lines[c[i]:c[i+1]]:
						dataY = line.get_data()[1]
						dataY = numpy.reshape(dataY, [len(dataY), 1])
						if len(dataY) < maxLen:
							diff = maxLen - len(dataY)
							fill = numpy.zeros([diff, 1]) * numpy.nan
							dataY = numpy.append(dataY, fill, axis=0)
						data = numpy.append(data, dataY, axis=1)
					if self.cb2ndAxis.isChecked():
						for line in self.axis2.lines[c[i]:c[i+1]]:
							dataY = line.get_data()[1]
							dataY = numpy.reshape(dataY, [len(dataY), 1])
							if len(dataY) < maxLen:
								diff = maxLen - len(dataY)
								fill = numpy.zeros([diff, 1]) * numpy.nan
								dataY = numpy.append(dataY, fill, axis=0)
							data = numpy.append(data, dataY, axis=1)
				else:  # is last result file
					for line in self.subplot.lines[c[i]:]:
						dataY = line.get_data()[1]
						dataY = numpy.reshape(dataY, [len(dataY), 1])
						if len(dataY) < maxLen:
							diff = maxLen - len(dataY)
							fill = numpy.zeros([diff, 1]) * numpy.nan
							dataY = numpy.append(dataY, fill, axis=0)
						data = numpy.append(data, dataY, axis=1)
					if self.cb2ndAxis.isChecked():
						for line in self.axis2.lines[c[i]:]:
							dataY = line.get_data()[1]
							dataY = numpy.reshape(dataY, [len(dataY), 1])
							if len(dataY) < maxLen:
								diff = maxLen - len(dataY)
								fill = numpy.zeros([diff, 1]) * numpy.nan
								dataY = numpy.append(dataY, fill, axis=0)
							data = numpy.append(data, dataY, axis=1)
			# Save data out
			saveFile = QFileDialog.getSaveFileName(self, 'Save File', fpath)
			if len(saveFile) < 2:
				return
			else:
				if saveFile != os.sep and saveFile.lower() != 'c:\\' and saveFile != '':
					settings.setValue("TUFLOW_Res_Dock/export_csv", saveFile)
			if saveFile is not None:
				try:
					file = open(saveFile, 'w')
					file.write('{0}\n'.format(dataHeader))
					for i, row in enumerate(data):
						line = ''
						for j, value in enumerate(row):
							if not numpy.isnan(data[i][j]):
								line += '{0},'.format(data[i][j])
							else:
								line += '{0},'.format('')
						line += '\n'
						file.write(line)
					file.close()
				except IOError:
					self.lwStatus.insertItem(0, 'ERROR opening file')
					return
			self.lwStatus.insertItem(0, 'Successfully exported csv')
		
		else:  # other result types like long profile and hydraulic properties. assumes no shared x axis.
			# Create data headers
			dataHeader = ''
			for label in self.labels:
				if self.locationDrop.currentText() == "Long Profile":  # shared X axis
					dataHeader += 'Chainage (m), {0},'.format(label)
				else:  # Shared Y Axis - Hydraulic properties of channels and XSections
					dataHeader += '{0}, Elevation (mRL),'.format(label)
			# Get data
			maxLen = 0
			for line in self.subplot.lines:  # Get max data length so one numpy array can be set up
				maxLen = max(maxLen, len(line.get_data()[0]))
			if self.cb2ndAxis.isChecked():
				for line in self.axis2.lines:
					maxLen = max(maxLen, len(line.get_data()[0]))
			data = numpy.zeros([maxLen, 1]) * numpy.nan
			for line in self.subplot.lines:
				lineX = numpy.reshape(line.get_data()[0], [len(line.get_data()[0]), 1])
				lineY = numpy.reshape(line.get_data()[1], [len(line.get_data()[1]), 1])
				if len(lineX) < maxLen:  # if data is less than max length, pad with nan values
					diff = maxLen - len(lineX)
					fill = numpy.zeros([diff, 1]) * numpy.nan
					lineX = numpy.append(lineX, fill)
					lineX = numpy.reshape(lineX, [maxLen, 1])
					lineY = numpy.append(lineY, fill)
					lineY = numpy.reshape(lineY, [maxLen, 1])
				data = numpy.append(data, lineX, axis=1)
				data = numpy.append(data, lineY, axis=1)
			if self.cb2ndAxis.isChecked():
				for line in self.axis2.lines:
					lineX = numpy.reshape(line.get_data()[0], [len(line.get_data()[0]), 1])
					lineY = numpy.reshape(line.get_data()[1], [len(line.get_data()[1]), 1])
					if len(lineX) < maxLen:  # if data is less than max length, pad with nan values
						diff = maxLen - len(lineX)
						fill = numpy.zeros([diff, 1]) * numpy.nan
						lineX = numpy.append(lineX, fill)
						lineX = numpy.reshape(lineX, [maxLen, 1])
						lineY = numpy.append(lineY, fill)
						lineY = numpy.reshape(lineY, [maxLen, 1])
					data = numpy.append(data, lineX, axis=1)
					data = numpy.append(data, lineY, axis=1)
			data = numpy.delete(data, 0, axis=1)
			# Save data out
			saveFile = QFileDialog.getSaveFileName(self, 'Save File', fpath)
			if len(saveFile) < 2:
				return
			else:
				if saveFile != os.sep and saveFile.lower() != 'c:\\' and saveFile != '':
					settings.setValue("TUFLOW_Res_Dock/export_csv", saveFile)
			if saveFile is not None:
				try:
					file = open(saveFile, 'w')
					file.write('{0}\n'.format(dataHeader))
					for i, row in enumerate(data):
						line = ''
						for j, value in enumerate(row):
							if not numpy.isnan(data[i][j]):
								line += '{0},'.format(data[i][j])
							else:
								line += '{0},'.format('')
						line += '\n'
						file.write(line)
					file.close()
				except IOError:
					self.lwStatus.insertItem(0, 'ERROR opening file')
					return
			self.lwStatus.insertItem(0, 'Successfully exported csv')
	
	def set_axisLimits(self):
		"""
		sets the axis limits for the plot window

		:return: void
		"""
		
		# Get Axis limits
		xLim = self.subplot.get_xlim()
		yLim = self.subplot.get_ylim()
		
		# Get Axis Increments
		# xMajorTickLabels = self.subplot.xaxis.get_majorticklabels()
		# yMajorTickLabels = self.subplot.yaxis.get_majorticklabels()
		xTicks = self.subplot.get_xticks()
		yTicks = self.subplot.get_yticks()
		if len(xTicks) > 1:
			xInc = xTicks[1] - xTicks[0]
		else:
			xInc = 99999
		if len(yTicks) > 1:
			yInc = yTicks[1] - yTicks[0]
		else:
			yInc = 99999
		
		# Get radio buttons
		if self.customAxis is not None:
			if self.customAxis.xAxisAuto_rb.isChecked():
				xAuto = True
			else:
				xAuto = False
			if self.customAxis.yAxisAuto_rb.isChecked():
				yAuto = True
			else:
				yAuto = False
			if self.customAxis.xAxisAuto_rb_2.isChecked():
				x2Auto = True
			else:
				x2Auto = False
			if self.customAxis.yAxisAuto_rb_2.isChecked():
				y2Auto = True
			else:
				y2Auto = False
		else:
			xAuto = True
			yAuto = True
			x2Auto = True
			y2Auto = True
		
		# Get Secondary Axis
		axis2 = None
		y2Lim = None
		x2Lim = None
		y2Inc = None
		x2Inc = None
		if self.ax2_exists:
			if self.axis2._sharex is not None:
				axis2 = 'sharex'
				y2Lim = self.axis2.get_ylim()
				y2MajorTickLabels = self.axis2.yaxis.get_majorticklabels()
				y2Inc = y2MajorTickLabels[-2]._y - y2MajorTickLabels[-3]._y
			elif self.axis2._sharey is not None:
				axis2 = 'sharey'
				x2Lim = self.axis2.get_xlim()
				x2MajorTickLabels = self.axis2.xaxis.get_majorticklabels()
				x2Inc = x2MajorTickLabels[-2]._x - x2MajorTickLabels[-3]._x
		
		self.customAxis = tuflowqgis_dialog.tuflowqgis_tuplotAxisEditor(self.iface, xLim, yLim, xAuto, yAuto, xInc, yInc, axis2, x2Lim,
		                                              y2Lim, x2Inc, y2Inc, x2Auto, y2Auto)
		self.customAxis.exec_()
		self.start_draw()
	
	def set_axisLabels(self):
		"""
		Sets the axis labels for the plot area.

		:return: void
		"""
		
		# Get Current Labels
		xLabel = self.subplot.get_xlabel()
		yLabel = self.subplot.get_ylabel()
		title = self.subplot.get_title()
		# Secontdary axis
		xLabel2 = None
		yLabel2 = None
		if self.ax2_exists:
			if self.axis2._sharex is not None:
				yLabel2 = self.axis2.get_ylabel()
			elif self.axis2._sharey is not None:
				xLabel2 = self.axis2.get_xlabel()
		# Get previous settings
		xAxisAuto_cb = False
		yAxisAuto_cb = False
		xAxisAuto2_cb = False
		yAxisAuto2_cb = False
		try:
			xAxisAuto_cb = self.customLabels.xAxisAuto_cb.isChecked()
			yAxisAuto_cb = self.customLabels.yAxisAuto_cb.isChecked()
			xAxisAuto2_cb = self.customLabels.xAxisAuto2_cb.isChecked()
			yAxisAuto2_cb = self.customLabels.yAxisAuto2_cb.isChecked()
		except:
			pass
		self.customLabels = tuflowqgis_dialog.tuflowqgis_tuplotAxisLabels(self.iface, xLabel, yLabel, xLabel2, yLabel2, title,
		                                                xAxisAuto_cb, yAxisAuto_cb, xAxisAuto2_cb, yAxisAuto2_cb)
		self.customLabels.exec_()
		self.start_draw()
		
	def selectPaths(self):
		"""
		Select network layers in Map Window of current paths selected in tuplot
		
		:return: Qgs Selection
		"""

		cPaths = []
		for i in range(self.ResTypeList.count()):
			path = self.ResTypeList.item(i).text()
			if 'path' in path.lower():
				if self.ResTypeList.item(i).isSelected():
					cPaths.append(path)
		selectionNwks = []
		for path in cPaths:
			pInd = self.profileIntTool.pathsName.index(path)
			for nwk in self.profileIntTool.pathsNwks[pInd]:
				if type(nwk) == list:
					for n in nwk:
						if n not in selectionNwks:
							selectionNwks.append(n)
				else:
					if nwk not in selectionNwks:
						selectionNwks.append(nwk)
		for lyr in self.profileIntTool.inLyrs:
			id = lyr.fields()[0].name()
			filter = ''
			for i, nwk in enumerate(selectionNwks):
				if i == 0:
					filter += '"{0}" = \'{1}\''.format(id, nwk)
				else:
					filter += 'OR "{0}" = \'{1}\''.format(id, nwk)
			lyr.selectByExpression(filter)

	def draw_figure(self):
		self.clear_figure()
		
		# dual axis stuff
		if (self.cb2ndAxis.isChecked() or self.cbXSRoughness.isChecked()):  # if not checked not dual axis needed
			# self.lwStatus.insertItem(0,'dual axis needed')
			if self.ax2_exists == False:
				if self.is_xs:
					self.axis2 = self.subplot.twiny()  # Hold elevation y-axis constant for XS
				else:
					if self.locationDrop.currentText() == 'Hydraulic Properties':
						self.axis2 = self.subplot.twiny()
					else:
						self.axis2 = self.subplot.twinx()  # Hold time x-axis constant for time series
				self.ax2_exists = True
			else:
				self.fig.delaxes(self.axis2)
				if self.is_xs:
					self.axis2 = self.subplot.twiny()  # Hold elevation y-axis constant for XS
				else:
					if self.locationDrop.currentText() == 'Hydraulic Properties':
						self.axis2 = self.subplot.twiny()
					else:
						self.axis2 = self.subplot.twinx()  # Hold time x-axis constant for time series
		else:
			if self.ax2_exists:
				try:
					self.fig.delaxes(self.axis2)
					self.ax2_exists = False
				except:
					QMessageBox.critical(self.iface.mainWindow(), "ERROR",
					                     "Error deleting axis2\n Please contact support@tuflow.com")
		self.artists = []
		
		#ititialise limits
		xmin = 999999.
		xmax = -999999.
		ymin = 999999.
		ymax = -999999.
		mmin = 0
		mmax = 1
		# Innitialise axis names
		xTitle = None
		yTitle = None
		xTitle2 = None
		yTitle2 = None
		units = None
		try:
			for i, res in enumerate(self.res):
				if i == 0:
					if res.units.lower() == 'metric':
						units = 'm'
					else:
						units = 'ft'
				else:
					if res.units.lower() == 'metric' and units != 'm':
						units = None
					elif res.units.lower() != 'metric' and units != 'ft':
						units = None
		except:
			units = None
		
		if self.is_xs:  # drawing section
			# Get result types to plot
			yTitle = 'Elevation ({0} RL)'.format(units) if units is not None else 'Elevation'
			resFiles = []
			for i in range(self.ResList.count()):
				if self.ResList.item(i).isSelected():
					resFiles.append(self.ResList.item(i).text())
			nRes = len(resFiles)
			ydataids = self.IDs
			typeids = []
			typenames = []
			plot_current_time = False
			for x in range(0, self.ResTypeList.count()):
				list_item = self.ResTypeList.item(x)
				if list_item.isSelected():
					if list_item.text() == 'Current Time':
						plot_current_time = True
					else:
						typeids.append(x)
						typenames.append(list_item.text())
			# Secondary axis result types
			typenames2 = []
			if self.ax2_exists:
				for x in range(self.ResTypeList_ax2.count()):
					list_item = self.ResTypeList_ax2.item(x)
					if list_item.isSelected():
						typenames2.append(list_item.text())
			# 1D ta table check files
			tableFiles = []
			for i in range(self.HydPropList.count()):
				if self.HydPropList.item(i).isSelected():
					z = self.HydPropList.item(i)
					tableFiles.append(self.HydPropList.item(i).text())
			# Plot Xsection
			xsLayerIndex = self.xsLoadedName.index(self.cLayer)
			xs_data = []
			for xs in self.xs_list:
				xsDataIndex = self.xsLoaded[xsLayerIndex].xsLayer.xsName.index(xs)
				xs_data.append(self.xsLoaded[xsLayerIndex].xsLayer.xs[xsDataIndex])
			for xs in xs_data:
				if 'XZ' in typenames:
					try:
						if xs.type.upper() == 'XZ':
							xmin = round(min(xs.x), 0) - 1
							xmax = round(max(xs.x), 0) + 1
							ymin = round(min(xs.z), 0) - 1
							ymax = round(max(xs.z), 0) + 1
							label = xs.source + " - " + xs.type
							xTitle = 'Station ({0})'.format(units) if units is not None else 'Station'
							self.subplot.set_xbound(lower=xmin, upper=xmax)
							self.subplot.set_ybound(lower=ymin, upper=ymax)
							a, = self.subplot.plot(xs.x, xs.z)
							self.artists.append(a)
							self.labels.append(label)
							self.subplot.hold(True)
					except:
						self.lwStatus.insertItem(0, 'ERROR plotting XZ')
				if 'HW' in typenames or 'CS' in typenames:
					try:
						if xs.type.upper() == 'HW' or xs.type.upper() == 'CS' or xs.type.upper() == 'LC' or xs.type.upper() == 'BG':
							xmin = round(min(xs.z), 0) - 1
							xmax = round(max(xs.z), 0) + 1
							ymin = round(min(xs.x), 0) - 1
							ymax = round(max(xs.x), 0) + 1
							label = xs.source + " - " + xs.type
							xTitle = 'Width ({0})'.format(units) if units is not None else 'Width'
							self.subplot.set_xbound(lower=xmin, upper=xmax)
							self.subplot.set_ybound(lower=ymin, upper=ymax)
							a, = self.subplot.plot(xs.z, xs.x)
							self.artists.append(a)
							self.labels.append(label)
							self.subplot.hold(True)
					except:
						self.lwStatus.insertItem(0, 'ERROR plotting 1d ta')
				if 'LC' in typenames or 'BG' in typenames:
					try:
						if xs.type.upper() == 'HW' or xs.type.upper() == 'CS' or xs.type.upper() == 'LC' or xs.type.upper() == 'BG':
							xmin = round(min(xs.z), 0) - 1
							xmax = round(max(xs.z), 0) + 1
							ymin = round(min(xs.x), 0) - 1
							ymax = round(max(xs.x), 0) + 1
							label = xs.source + " - " + xs.type
							xTitle = 'Form Loss Factor'
							self.subplot.set_xbound(lower=xmin, upper=xmax)
							self.subplot.set_ybound(lower=ymin, upper=ymax)
							a, = self.subplot.plot(xs.z, xs.x)
							self.artists.append(a)
							self.labels.append(label)
							self.subplot.hold(True)
					except:
						self.lwStatus.insertItem(0, 'ERROR plotting 1d ta')
			for res in resFiles:
				for i, xsResult in enumerate(self.xsLoaded[xsLayerIndex].results):
					if xsResult.nodeResults.displayname == res:
						resIndex = i
						break
				xsResult = self.xsLoaded[xsLayerIndex].results[resIndex]
				if self.xsResults == True:
					# Add water level results
					if 'Max Water Level' in typenames:
						try:
							for i, result in enumerate(xsResult.maxHx):
								xTitle = 'Station ({0})'.format(units) if units is not None else 'Station'
								a, = self.subplot.plot(result, xsResult.maxHz[i])
								self.artists.append(a)
								if nRes < 2:
									label = "{0} - WL".format(xsResult.xsName[i])
								else:
									label = "{0}: {1} - WL".format(xsResult.nodeResults.displayname, xsResult.xsName[i])
								self.labels.append(label)
								self.subplot.hold(True)
						except:
							self.lwStatus.insertItem(0, 'ERROR plotting Max WL')
					# Add temporal water level results
					if 'Water Level at Time' in typenames:
						try:
							for x in range(self.listTime.count()):
								list_item = self.listTime.item(x)
								if list_item.isSelected():
									timeInd = x
									timeStr = list_item.text()
							for i, result in enumerate(xsResult.hx):
								xTitle = 'Station ({0})'.format(units) if units is not None else 'Station'
								a, = self.subplot.plot(result[timeInd], xsResult.hz[i][timeInd])
								self.artists.append(a)
								if nRes < 2:
									label = "{0} - WL at {1}".format(xsResult.xsName[i], timeStr)
								else:
									label = "{0}: {1} - WL at {2}".format(xsResult.nodeResults.displayname,
									                                      xsResult.xsName[i], timeStr)
								self.labels.append(label)
								self.subplot.hold(True)
						except:
							self.lwStatus.insertItem(0, 'ERROR plotting WL at time')
					# Add right and left bank results
					if 'Left Bank' in typenames:
						try:
							for i, result in enumerate(xsResult.lb):
								xTitle = 'Station ({0})'.format(units) if units is not None else 'Station'
								a, = self.subplot.plot(xsResult.lbx[i], result, marker='o',
								                       linestyle='None', color='r')
								self.artists.append(a)
								if nRes < 2:
									label = "{0} - left bank".format(xsResult.xsName[i])
								else:
									label = "{0}: {1} - left bank".format(xsResult.nodeResults.displayname,
									                                      xsResult.xsName[i])
								self.labels.append(label)
								self.subplot.hold(True)
						except:
							self.lwStatus.insertItem(0, 'ERROR plotting Left Bank')
					if 'Right Bank' in typenames:
						try:
							for i, result in enumerate(xsResult.rb):
								xTitle = 'Station ({0})'.format(units) if units is not None else 'Station'
								a, = self.subplot.plot(xsResult.rbx[i], result, marker='o',
								                       linestyle='None', color='r')
								self.artists.append(a)
								if nRes < 2:
									label = "{0} - right bank".format(xsResult.xsName[i])
								else:
									label = "{0}: {1} - right bank".format(xsResult.nodeResults.displayname,
									                                       xsResult.xsName[i])
								self.labels.append(label)
								self.subplot.hold(True)
						except:
							self.lwStatus.insertItem(0, 'ERROR plotting Right Bank')
			for i, tableFile in enumerate(tableFiles):
				for d in self.hydTables.loadedData:
					if tableFile == d.displayName:
						tableIndex = i
						break
				d = self.hydTables.loadedData[tableIndex]
				if 'Depth' in typenames or 'Width' in typenames or \
						'Eff Width' in typenames or 'Eff Area' in typenames or \
						'Eff Wet Per' in typenames or 'Radius' in typenames or \
						'Vert Res Factor' in typenames or 'K (n=1.000)' in typenames:
					for t in typenames:
						try:
							tIndex = d.xsHydTa_headers.index(t)
							for j in range(self.IDList.count()):
								if t.lower() == 'eff area':
									xTitle = 'Area ({0}2)'.format(units) if units is not None else 'Area'
								elif t.lower() == 'eff wet per' or t.lower() == 'radius' or t.lower() == 'depth':
									xTitle = '({0})'.format(units) if units is not None else None
								elif t.lower() == 'width' or t.lower() == 'eff width':
									xTitle = 'Width ({0})'.format(units) if units is not None else 'Width'
								else:
									xTitle = None
								jIndex = d.xsNames.index(self.IDList.item(j).text())
								a, = self.subplot.plot(d.xsHydTa[jIndex][:, tIndex], d.xsHydTa[jIndex][:, 0])
								self.artists.append(a)
								if len(tableFiles) < 2:
									label = "{0} - {1}".format(self.IDList.item(j).text(), t)
								else:
									label = "{0}: {1} - {2}".format(d.displayName, self.IDList.item(j).text(), t)
								self.labels.append(label)
								self.subplot.hold(True)
						except:
							pass
			if len(typenames) > 1:
				compatible_list = ['XZ', 'Max Water Level', 'Water Level at Time', 'Left Bank', 'Right Bank']
				compatible = True
				found = False
				for i, typename in enumerate(typenames):
					if i == 0 and typename not in compatible_list:
						break
					elif typename not in compatible_list:
						found = True
						compatible = False
						break
				compatible_list = ['HW', 'CS', 'Width', 'Eff Width']
				for i, typename in enumerate(typenames):
					if i == 0 and typename not in compatible_list:
						break
					elif typename not in compatible_list:
						found = True
						compatible = False
						break
				compatible_list = ['Eff Wet Per', 'Radius', 'Depth']
				for i, typename in enumerate(typenames):
					if i == 0 and typename not in compatible_list:
						break
					elif typename not in compatible_list:
						found = True
						compatible = False
						break
				if not compatible or not found:
					xTitle = None
			# AXIS 2
			if (self.cb2ndAxis.isChecked()):
				for xs in xs_data:
					if 'XZ' in typenames2:
						try:
							if xs.type.upper() == 'XZ':
								#self.axis2.xaxis.set_ticks_position("bottom")
								#self.axis2.xaxis.set_label_position("bottom")
								#self.axis2.spines['bottom'].set_position(("axes", -0.1))
								xmin = round(min(xs.x), 0) - 1
								xmax = round(max(xs.x), 0) + 1
								ymin = round(min(xs.z), 0) - 1
								ymax = round(max(xs.z), 0) + 1
								label = xs.source + " - " + xs.type + " (axis 2)"
								xTitle2 = 'Station ({0})'.format(units) if units is not None else 'Station'
								self.axis2.set_xbound(lower=xmin, upper=xmax)
								self.axis2.set_ybound(lower=ymin, upper=ymax)
								a2, = self.axis2.plot(xs.x, xs.z, marker='x')
								self.artists.append(a2)
								self.labels.append(label)
								self.axis2.hold(True)
						except:
							self.lwStatus.insertItem(0, 'ERROR plotting XZ')
					if 'HW' in typenames2 or 'CS' in typenames2 or 'LC' in typenames2 or 'BG' in typenames2:
						try:
							if xs.type.upper() == 'HW' or xs.type.upper() == 'CS' or xs.type.upper() == 'LC' or xs.type.upper() == 'BG':
								#self.axis2.xaxis.set_ticks_position("bottom")
								#self.axis2.xaxis.set_label_position("bottom")
								#self.axis2.spines['bottom'].set_position(("axes", -0.1))
								xmin = round(min(xs.z), 0) - 1
								xmax = round(max(xs.z), 0) + 1
								ymin = round(min(xs.x), 0) - 1
								ymax = round(max(xs.x), 0) + 1
								label = xs.source + " - " + xs.type + " (axis 2)"
								if xs.type.upper() == 'HW' or xs.type.upper() == 'CS':
									xTitle2 = 'Width ({0})'.format(units) if units is not None else 'Width'
								elif xs.type.upper() == 'LC' or xs.type.upper() == 'BG':
									xTitle2 = 'Form Loss Factor'
								self.axis2.set_xbound(lower=xmin, upper=xmax)
								self.axis2.set_ybound(lower=ymin, upper=ymax)
								a2, = self.axis2.plot(xs.z, xs.x, marker='x')
								self.artists.append(a2)
								self.labels.append(label)
								self.axis2.hold(True)
						except:
							self.lwStatus.insertItem(0, 'ERROR plotting 1d ta')
				for res in resFiles:
					for i, xsResult in enumerate(self.xsLoaded[xsLayerIndex].results):
						if xsResult.nodeResults.displayname == res:
							resIndex = i
							break
					xsResult = self.xsLoaded[xsLayerIndex].results[resIndex]
					if self.xsResults == True:
						# Add water level results
						if 'Max Water Level' in typenames2:
							try:
								for i, result in enumerate(xsResult.maxHx):
									xTitle2 = 'Station ({0})'.format(units) if units is not None else 'Station'
									#self.axis2.xaxis.set_ticks_position("bottom")
									#self.axis2.xaxis.set_label_position("bottom")
									#self.axis2.spines['bottom'].set_position(("axes", -0.1))
									a2, = self.axis2.plot(result, xsResult.maxHz[i], marker='x')
									self.artists.append(a2)
									if nRes < 2:
										label = "{0} - WL (axis 2)".format(xsResult.xsName[i])
									else:
										label = "{0}: {1} - WL (axis 2)".format(xsResult.nodeResults.displayname,
										                                        xsResult.xsName[i])
									self.labels.append(label)
									self.axis2.hold(True)
							except:
								self.lwStatus.insertItem(0, 'ERROR plotting Max WL')
						# Add temporal water level results
						if 'Water Level at Time' in typenames2:
							try:
								for x in range(self.listTime.count()):
									list_item = self.listTime.item(x)
									if list_item.isSelected():
										timeInd = x
										timeStr = list_item.text()
								for i, result in enumerate(xsResult.hx):
									#self.axis2.xaxis.set_ticks_position("bottom")
									#self.axis2.xaxis.set_label_position("bottom")
									#self.axis2.spines['bottom'].set_position(("axes", -0.1))
									a2, = self.axis2.plot(result[timeInd], xsResult.hz[i][timeInd], marker='x')
									self.artists.append(a2)
									if nRes < 2:
										label = "{0} - WL at {1} (axis 2)".format(xsResult.xsName[i], timeStr)
									else:
										label = "{0}: {1} - WL at {2} (axis 2)".format(xsResult.nodeResults.displayname,
										                                               xsResult.xsName[i], timeStr)
									self.labels.append(label)
									self.axis2.hold(True)
							except:
								self.lwStatus.insertItem(0, 'ERROR plotting WL at time')
						# Add right and left bank results
						if 'Left Bank' in typenames2:
							try:
								for i, result in enumerate(xsResult.lb):
									xTitle2 = 'Station ({0})'.format(units) if units is not None else 'Station'
									#self.axis2.xaxis.set_ticks_position("bottom")
									#self.axis2.xaxis.set_label_position("bottom")
									#self.axis2.spines['bottom'].set_position(("axes", -0.1))
									a2, = self.axis2.plot(xsResult.lbx[i], result, marker='o',
									                      linestyle='None', color='r')
									self.artists.append(a2)
									if nRes < 2:
										label = "{0} - left bank (axis 2)".format(xsResult.xsName[i])
									else:
										label = "{0}: {1} - left bank (axis 2)".format(xsResult.nodeResults.displayname,
										                                               xsResult.xsName[i])
									self.labels.append(label)
									self.axis2.hold(True)
							except:
								self.lwStatus.insertItem(0, 'ERROR plotting Left Bank')
						if 'Right Bank' in typenames2:
							try:
								for i, result in enumerate(xsResult.rb):
									xTitle2 = 'Station ({0})'.format(units) if units is not None else 'Station'
									#self.axis2.xaxis.set_ticks_position("bottom")
									#self.axis2.xaxis.set_label_position("bottom")
									#self.axis2.spines['bottom'].set_position(("axes", -0.1))
									a2, = self.axis2.plot(xsResult.rbx[i], result, marker='o',
									                      linestyle='None', color='r')
									self.artists.append(a2)
									if nRes < 2:
										label = "{0} - left bank (axis 2)".format(xsResult.xsName[i])
									else:
										label = "{0}: {1} - left bank (axis 2)".format(xsResult.nodeResults.displayname,
										                                               xsResult.xsName[i])
									self.labels.append(label)
									self.axis2.hold(True)
							except:
								self.lwStatus.insertItem(0, 'ERROR plotting Right Bank')
				for i, tableFile in enumerate(tableFiles):
					for d in self.hydTables.loadedData:
						if tableFile == d.displayName:
							tableIndex = i
							break
					d = self.hydTables.loadedData[tableIndex]
					if 'Depth' in typenames2 or 'Width' in typenames2 or 'Width' in typenames2 or \
							'Eff Width' in typenames2 or 'Eff Area' in typenames2 or \
							'Eff Wet Per' in typenames2 or 'Radius' in typenames2 or \
							'Vert Res Factor' in typenames2 or 'K (n=1.000)' in typenames2:
						for t in typenames2:
							try:
								tIndex = d.xsHydTa_headers.index(t)
								for j in range(self.IDList.count()):
									if t.lower() == 'eff area':
										xTitle2 = 'Area ({0}2)'.format(units) if units is not None else 'Area'
									elif t.lower() == 'eff wet per' or t.lower() == 'radius' or t.lower() == 'depth':
										xTitle2 = '({0})'.format(units) if units is not None else None
									elif t.lower() == 'width' or t.lower() == 'eff width':
										xTitle2 = 'Width ({0})'.format(units) if units is not None else 'Width'
									else:
										xTitle2 = None
									#self.axis2.xaxis.set_ticks_position("bottom")
									#self.axis2.xaxis.set_label_position("bottom")
									#self.axis2.spines['bottom'].set_position(("axes", -0.1))
									jIndex = d.xsNames.index(self.IDList.item(j).text())
									a2, = self.axis2.plot(d.xsHydTa[jIndex][:, tIndex],
									                      d.xsHydTa[jIndex][:, 0], marker='x')
									self.artists.append(a2)
									if len(tableFiles) < 2:
										label = "{0} - {1} (axis 2)".format(self.IDList.item(j).text(), t)
									else:
										label = "{0}: {1} - {2} (axis 2)".format(d.displayName,
										                                         self.IDList.item(j).text(), t)
									self.labels.append(label)
									self.axis2.hold(True)
							except:
								pass
				if len(typenames2) > 1:
					compatible_list = ['XZ', 'Max Water Level', 'Water Level at Time', 'Left Bank', 'Right Bank']
					compatible = True
					found = False
					for i, typename in enumerate(typenames2):
						if i == 0 and typename not in compatible_list:
							break
						elif typename not in compatible_list:
							found = True
							compatible = False
							break
					compatible_list = ['HW', 'CS', 'Width', 'Eff Width']
					for i, typename in enumerate(typenames2):
						if i == 0 and typename not in compatible_list:
							break
						elif typename not in compatible_list:
							found = True
							compatible = False
							break
					compatible_list = ['Eff Wet Per', 'Radius', 'Depth']
					for i, typename in enumerate(typenames2):
						if i == 0 and typename not in compatible_list:
							break
						elif typename not in compatible_list:
							found = True
							compatible = False
							break
					if not compatible or not found:
						xTitle2 = None
		elif self.is_intTool:
			units = self.profileIntTool.units
			xTitle = 'Chainage ({0})'.format(units) if units is not None else 'Chainage'
			yTitle = 'Elevation ({0} RL)'.format(units) if units is not None else 'Elevation'
			self.IDList.clear()
			typeids = []
			typenames = []
			plot_current_time = False
			for x in range(0, self.ResTypeList.count()):
				list_item = self.ResTypeList.item(x)
				if list_item.isSelected():
					if list_item.text() == 'Current Time':
						plot_current_time = True
					else:
						typeids.append(x)
						typenames.append(list_item.text())
			for typename in reversed(typenames):
				if 'Path' in typename:
					pInd = self.profileIntTool.pathsName.index(typename)
					if x > 0:
						self.IDList.insertItem(0, "")
					for nwk in reversed(self.profileIntTool.pathsNwks[pInd]):
						nInd = self.profileIntTool.pathsNwks[pInd].index(nwk)
						advG = ''
						advI = ''
						decA = ''
						sharpA = ''
						if self.profileIntTool.pathsAdverseGradient[pInd][nInd]:
							advG = ' -- Adverse Gradient'
						if self.profileIntTool.pathsAdverseInvert[pInd][nInd]:
							advI = ' -- Adverse Invert'
						if self.profileIntTool.pathsDecreaseFlowArea[pInd][nInd]:
							decA = ' -- Decrease in Area'
						if self.profileIntTool.pathsSharpAngle[pInd][nInd]:
							sharpA = ' -- Sharp Outflow Angle'
						if self.profileIntTool.pathsInsffCover[pInd][nInd]:
							sharpA = ' -- Insufficient Cover'
						self.IDList.insertItem(0, '{0}{1}{2}{3}'.format(nwk, advG, decA, sharpA))
					self.IDList.insertItem(0, "## {0} ##".format(typename))
			for path in typenames:
				if 'Path' in path:
					pInd = self.profileIntTool.pathsName.index(path)  # path index
					# pipes
					ymin = min(ymin, min(self.profileIntTool.pathsInvert[pInd]))
					ymax = max(ymax, max(self.profileIntTool.pathsInvert[pInd]))
					xmin = min(xmin, min(self.profileIntTool.pathsX[pInd]))
					xmax = max(xmax, max(self.profileIntTool.pathsX[pInd]))
					a, = self.subplot.plot(self.profileIntTool.pathsX[pInd], self.profileIntTool.pathsInvert[pInd])
					for poly in self.profileIntTool.pathsPipe[pInd]:
						if len(poly) > 0:
							for v in poly:
								ymax = max(ymax, v[1])
							p = Polygon(poly, facecolor='0.9', edgecolor='0.5')
							self.subplot.add_patch(p)
					self.artists.append(a)
					label = "{0}".format(path)
					self.labels.append(label)
					self.subplot.hold(True)
					# Ground
					if 'Ground' in typenames:
						if self.profileIntTool.coverLimit is not None:
							ymin = min(ymin, min(self.profileIntTool.pathsGroundY[pInd]))
							ymax = max(ymax, max(self.profileIntTool.pathsGroundY[pInd]))
							xmin = min(xmin, min(self.profileIntTool.pathsGroundX[pInd]))
							xmax = max(xmax, max(self.profileIntTool.pathsGroundX[pInd]))
							a, = self.subplot.plot(self.profileIntTool.pathsGroundX[pInd],
							                       self.profileIntTool.pathsGroundY[pInd])
							self.artists.append(a)
							label = "{0} Ground".format(path)
							self.labels.append(label)
							self.subplot.hold(True)
					# Adverse Gradient Flag
					if 'Flags' in typenames:
						if len(self.profileIntTool.pathsPlotAdvG[pInd][1]) > 0:
							a, = self.subplot.plot(self.profileIntTool.pathsPlotAdvG[pInd][0],
							                       self.profileIntTool.pathsPlotAdvG[pInd][1], marker='o',
							                       linestyle='None')
							ymax = max(ymax, max(self.profileIntTool.pathsPlotAdvG[pInd][1]))
							self.artists.append(a)
							label = "{0} Adverse Gradient".format(path)
							self.labels.append(label)
							self.subplot.hold(True)
						if len(self.profileIntTool.pathsPlotAdvI[pInd][1]) > 0:
							a, = self.subplot.plot(self.profileIntTool.pathsPlotAdvI[pInd][0],
							                       self.profileIntTool.pathsPlotAdvI[pInd][1], marker='o',
							                       linestyle='None')
							ymax = max(ymax, max(self.profileIntTool.pathsPlotAdvI[pInd][1]))
							self.artists.append(a)
							label = "{0} Adverse Invert".format(path)
							self.labels.append(label)
							self.subplot.hold(True)
						# Decrease in Area Flag
						if len(self.profileIntTool.pathsPlotDecA[pInd][1]) > 0:
							a, = self.subplot.plot(self.profileIntTool.pathsPlotDecA[pInd][0],
							                       self.profileIntTool.pathsPlotDecA[pInd][1], marker='o',
							                       linestyle='None')
							ymax = max(ymax, max(self.profileIntTool.pathsPlotDecA[pInd][1]))
							self.artists.append(a)
							label = "{0} Decrease in Area".format(path)
							self.labels.append(label)
							self.subplot.hold(True)
						# Sharp Angle Flag
						if len(self.profileIntTool.pathsPlotSharpA[pInd][1]) > 0:
							a, = self.subplot.plot(self.profileIntTool.pathsPlotSharpA[pInd][0],
							                       self.profileIntTool.pathsPlotSharpA[pInd][1], marker='o',
							                       linestyle='None')
							ymax = max(ymax, max(self.profileIntTool.pathsPlotSharpA[pInd][1]))
							self.artists.append(a)
							label = "{0} Sharp Angle".format(path)
							self.labels.append(label)
							self.subplot.hold(True)
						# Insufficient Cover Depth
						if len(self.profileIntTool.pathsPlotInCover[pInd][1]) > 0:
							a, = self.subplot.plot(self.profileIntTool.pathsPlotInCover[pInd][0],
							                       self.profileIntTool.pathsPlotInCover[pInd][1], marker='o',
							                       linestyle='None')
							ymax = max(ymax, max(self.profileIntTool.pathsPlotInCover[pInd][1]))
							self.artists.append(a)
							label = "{0} Insufficent Cover Depth".format(path)
							self.labels.append(label)
							self.subplot.hold(True)
		else: #results
			#self.lwStatus.insertItem(0,'drawing results')
			loc = self.locationDrop.currentText()
			ydataids = self.IDs
			typeids = []
			typenames = []
			plot_current_time = False
			for x in range(0,self.ResTypeList.count()):
				list_item = self.ResTypeList.item(x)
				if list_item.isSelected():
					if list_item.text() == 'Current Time':
						plot_current_time = True
					else:
						typeids.append(x)
						typenames.append(list_item.text())
					#self.lwStatus.insertItem(0,'Debug len(typenames) = ' + str(len(typenames)))
			#self.lwStatus.insertItem(0,'{0}'.format(typenames))
			typenames2 = []
			for x in range(0,self.ResTypeList_ax2.count()):
				list_item = self.ResTypeList_ax2.item(x)
				if list_item.isSelected():
					#typeids.append(x)
					typenames2.append(list_item.text())

			# Compile Selected Results Files
			reslist = []
			resnames = []
			for x in range(0, self.ResList.count()):
				list_item = self.ResList.item(x)
				if list_item.isSelected():
					reslist.append(x)
					resnames.append(list_item.text())
			nRes = len(reslist) #number selected not loaded

			#check if median is required
			calc_median = False
			if self.cbCalcMedian.isChecked():
				calc_median = True
				if nRes<3:
					calc_median = False
					self.lwStatus.insertItem(0,'Warning - Median requires at least three results selected')
				if len(self.IDs)!=1:
					calc_median = False
					self.lwStatus.insertItem(0,'Warning - Median only valid for a single output location')
				if loc!="Timeseries":
					calc_median = False
					self.lwStatus.insertItem(0,'Warning - Median only valid for a timeseries plot type')
				if len(typenames)!=1:
					calc_median = False
					self.lwStatus.insertItem(0,'Warning - Median only valid for a single output parameter')

			#check if mean is required
			calc_mean = False
			if self.cbCalcMean.isChecked():
				calc_mean = True
				if nRes<3:
					calc_mean = False
					self.lwStatus.insertItem(0,'Warning - Mean requires at least three results selected')
				if len(self.IDs)!=1:
					calc_mean = False
					self.lwStatus.insertItem(0,'Warning - Mean only valid for a single output location')
				if loc!="Timeseries":
					calc_mean = False
					self.lwStatus.insertItem(0,'Warning - Mean only valid for a timeseries plot type')
				if len(typenames)!=1:
					calc_mean = False
					self.lwStatus.insertItem(0,'Warning - Mean only valid for a single output parameter')
				meanAbove = self.cbMeanAbove.isChecked()
				if meanAbove:
					self.lwStatus.insertItem(0,'Using 1st value above mean.')
				else:
					self.lwStatus.insertItem(0,'Using closest value to mean.')
				
			#numpy array for calculation of median / mean
			if calc_median or calc_mean:
				try:
					max_vals = numpy.zeros([nRes])
				except:
					self.lwStatus.insertItem(0,'Error - setting up numpy array for mean/median.')
					calc_median = False
					calc_mean = False

			# Long Profiles___________________________________________________________________
			if loc == "Long Profile": # LP
				xTitle = 'Chainage ({0})'.format(units) if units is not None else 'Chainage'
				yTitle = 'Elevation ({0} RL)'.format(units) if units is not None else 'Elevation'
				nres_used = 0
				for resno in reslist:
					nres_used = nres_used + 1
					res = self.res[resno]
					name = res.displayname
					plot = True
					
					# if LP data has been processed (should both always be True)
					if res.LP.connected and res.LP.static:
						#update limits
						xmin = 0.0 # should always start at 0
						tmp_xmax=max(res.LP.dist_nodes)
						xmax = max(xmax,tmp_xmax)
						tmp_ymin=min(res.LP.node_bed)
						ymin = min(ymin, tmp_ymin)
						#tmp_ymax=max(res.LP.Hmax)
						#tmp_ymax2=max(res.LP.Emax)
						#ymax = max(ymax,tmp_ymax,tmp_ymax2)
						
						
						# plot max water level
						if typenames.count('Max Water Level')!=0:
							a, = self.subplot.plot(res.LP.dist_chan_inverts, res.LP.Hmax)
							self.artists.append(a)
							label = 'Max Water Level'
							if nRes > 1:
								self.labels.append(label +" - "+name)
							else:
								self.labels.append(label)
							self.subplot.hold(True)
							ymax = max(ymax,max(res.LP.Hmax))

						# plot max energy level
						if typenames.count('Max Energy Level')!=0:
							if res.formatVersion == 1:
								self.lwStatus.insertItem(0,'Energy output only available in 2015 or newer results')
							else:
								if res.LP.Emax:
									a, = self.subplot.plot(res.LP.dist_chan_inverts, res.LP.Emax)
									self.artists.append(a)
									label = 'Max Energy Level'
									if nRes > 1:
										self.labels.append(label +" - "+name)
									else:
										self.labels.append(label)
									self.subplot.hold(True)
									ymax = max(ymax,max(res.LP.Emax))
								else:
									self.lwStatus.insertItem(0,'Warning - No Maximum Energy Levels stored for '+name)

							
						#plot LP water level at time
						if typenames.count('Water Level at Time')!=0:
							for x in range(0, self.listTime.count()):
								list_item = self.listTime.item(x)
								if list_item.isSelected():
									timeInd = x
									timeStr = list_item.text()
									time = res.times[x]
									#self.lwStatus.insertItem(0,'timeStr = '+timeStr)
							error, message = res.LP_getData('Head',time,0.01)
							if error:
								self.lwStatus.insertItem(0,'ERROR - Extracting temporal data for LP')
								self.lwStatus.insertItem(0,message)
							else:
								a, = self.subplot.plot(res.LP.dist_chan_inverts, res.LP.Hdata)
								self.artists.append(a)
								label = 'Water Level at '+timeStr
								if nRes > 1:
									self.labels.append(label +" - "+name)
								else:
									self.labels.append(label)
								self.subplot.hold(True)
								ymax = max(ymax,max(res.LP.Hdata))

						#plot LP energy at time
						if typenames.count('Energy Level at Time')!=0:
							if res.formatVersion == 1:
								self.lwStatus.insertItem(0,'Energy output only available in 2015 or newer results')
							else:
								for x in range(0, self.listTime.count()):
									list_item = self.listTime.item(x)
									if list_item.isSelected():
										timeInd = x
										timeStr = list_item.text()
										time = res.times[x]
										#self.lwStatus.insertItem(0,'timeStr = '+timeStr)
								error, message = res.LP_getData('Energy',time,0.01)
								if error:
									self.lwStatus.insertItem(0,'ERROR - Extracting temporal data for LP')
									self.lwStatus.insertItem(0,message)
								else:
									a, = self.subplot.plot(res.LP.dist_chan_inverts, res.LP.Edata)
									self.artists.append(a)
									label = 'Energy Level at '+timeStr
									if nRes > 1:
										self.labels.append(label +" - "+name)
									else:
										self.labels.append(label)
									self.subplot.hold(True)
									ymax = max(ymax,max(res.LP.Edata))

						#plot adverse sections
						if typenames.count('Adverse Gradients (if any)')!=0:
							if res.formatVersion == 1:
								self.lwStatus.insertItem(0,'Adverse gradient plots not available Pre-2016')
							else:
								if res.LP.adverseH.nLocs > 0:
									a, = self.subplot.plot(res.LP.adverseH.chainage, res.LP.adverseH.elevation, marker='o', linestyle='None', color='r')
									self.artists.append(a)
									self.labels.append("Adverse Water Level")
									#self.lwStatus.insertItem(0,'WARNING - Adverse gradients detected along profile')
									if self.cbShowLegend.isChecked():
										for i in range(res.LP.adverseH.nLocs):
											self.subplot.text(res.LP.adverseH.chainage[i],res.LP.adverseH.elevation[i]+0.25,res.LP.adverseH.node[i],rotation=90,verticalalignment='bottom',fontsize=12)
									else:
										self.lwStatus.insertItem(0,'Turn on legend to get more information about adverse grades')
								if res.LP.adverseE.nLocs > 0:
									a, = self.subplot.plot(res.LP.adverseE.chainage, res.LP.adverseE.elevation, marker='o', linestyle='None', color='y')
									self.artists.append(a)
									self.labels.append("Adverse Energy Level")
									#self.lwStatus.insertItem(0,'WARNING - Adverse gradients detected along profile')
									if self.cbShowLegend.isChecked():
										for i in range(res.LP.adverseE.nLocs):
											self.subplot.text(res.LP.adverseE.chainage[i],res.LP.adverseE.elevation[i]+0.25,res.LP.adverseE.node[i],rotation=90,verticalalignment='bottom',fontsize=12)
									else:
										self.lwStatus.insertItem(0,'Turn on legend to get more information about adverse grades')

						#plot bed / culverts
						if typenames.count('Bed Level')!=0 and nres_used==len(reslist):
							a, = self.subplot.plot(res.LP.dist_chan_inverts, res.LP.chan_inv)
							self.artists.append(a)
							label = 'Bed Level'
							if nRes > 1:
								self.labels.append(label +" - "+name)
							else:
								self.labels.append(label)
							self.subplot.hold(True)
							ymax = max(ymax,max(res.LP.chan_inv))
							
							#tag on culverts if bed is shown (2015 or later)
							if res.formatVersion >= 2: #2015
								for verts in res.LP.culv_verts:
									if verts:
										poly = Polygon(verts, facecolor='0.9', edgecolor='0.5')
										self.subplot.add_patch(poly)

						#plot LB
						if typenames.count('Left Bank Obvert')!=0 and nres_used==len(reslist):
							a, = self.subplot.plot(res.LP.dist_chan_inverts, res.LP.chan_LB)
							self.artists.append(a)
							label = 'Left Bank'
							if nRes > 1:
								self.labels.append(label +" - "+name)
							else:
								self.labels.append(label)
							self.subplot.hold(True)
							ymax = max(ymax,max(res.LP.chan_LB))

						#plot RB
						if typenames.count('Right Bank Obvert')!=0 and nres_used==len(reslist):
							a, = self.subplot.plot(res.LP.dist_chan_inverts, res.LP.chan_RB)
							self.artists.append(a)
							label = 'Right Bank'
							if nRes > 1:
								self.labels.append(label +" - "+name)
							else:
								self.labels.append(label)
							self.subplot.hold(True)
							ymax = max(ymax,max(res.LP.chan_RB))

						#plot pits
						if typenames.count('Pit Ground Levels (if any)')!=0 and nres_used==len(reslist):
							if res.LP.npits > 0:
								a, = self.subplot.plot(res.LP.pit_dist, res.LP.pit_z, marker='o', linestyle='None', color='r')
								self.artists.append(a)
								self.labels.append("Pit Invert (grate) levels")
							else:
								self.lwStatus.insertItem(0,'No Pit objects to plot')
						
				nres_used = 0
				for resno in reslist:
					nres_used = nres_used + 1
					res = self.res[resno]
					name = res.displayname
					if (self.cb2ndAxis.isChecked()): # if not checked not dual axis needed
						if typenames2.count('Time Hmax')!=0:
							if res.formatVersion == 1: #2013
								message = "Time of H Max not available for Pre 2016 TUFLOW"
								self.lwStatus.insertItem(0,message)
								self.lwStatus.item(0).setTextColor(self.qred)
							else:
								a2, = self.axis2.plot(res.LP.dist_nodes, res.LP.tHmax)
								self.artists.append(a2)
								label = 'Time H Max (axis 2)'
								if nRes > 1:
									self.labels.append(label +" - "+name)
								else:
									self.labels.append(label)
								self.axis2.hold(True)
								#ymax = max(ymax,max(res.LP.chan_inv))
								self.axis2.set_ylabel("Time of Peak Level")
			# Timeseries______________________________________________________________________
			elif loc == "Timeseries":
				xTitle = 'Time (hrs)'
				nres_used = 0
				for resno in reslist:
					nres_used = nres_used + 1
					res = self.res[resno]
					name = res.displayname
					# AXIS 1
					#xdata = res.getXData()
					breakloop = False
					for i, ydataid in enumerate(self.IDs):
						if ydataid:
							for typename in typenames:
								found = False
								message = 'ERROR - Unable to extract data'
								if not breakloop:
									if res.formatVersion == 1: #2013
										found, ydata, message = res.getTSData(ydataid,typename)
										xdata = res.times
									elif res.formatVersion == 2: #2015
										dom = self.Doms[i]
										source = self.Source_Att[i].upper()
										if (dom == '2D'):
											if typename.upper().find('STRUCTURE FLOWS')>= 0 and source=='QS':
												typename = 'QS'
												yTitle = 'Flow ({0}$^3$/s)'.format(units) if units is not None else 'Flow'
											elif typename.upper().find('STRUCTURE LEVELS')>= 0 and source=='HU':
												typename = 'HU'
												yTitle = 'Elevation ({0} RL)'.format(
													units) if units is not None else 'Elevation'
											elif typename.upper().find('STRUCTURE LEVELS')>= 0 and source=='HD':
												typename = 'HD'
												yTitle = 'Elevation ({0} RL)'.format(
													units) if units is not None else 'Elevation'
										try:
											found, ydata, message = res.getTSData(ydataid,dom,typename, 'Geom')
											xdata = res.times
										except:
											self.lwStatus.insertItem(0,'ERROR - Extracting results')
											self.lwStatus.insertItem(0,'res = '+res.displayname)
											self.lwStatus.insertItem(0,'ID: '+ydataid)
											self.lwStatus.insertItem(0,'i: '+str(i))
										if calc_median or calc_mean:
											try:
												#self.lwStatus.insertItem(0,'Appending to median')
												#self.lwStatus.insertItem(0,'Debug [nres_used] = {0}'.format(nres_used-1))
												#self.lwStatus.insertItem(0,'Debug [nres_used] = {0}'.format(nres_used-1))
												max_vals[nres_used-1] = ydata.max()
											except:
												if calc_median:
													calc_median = False
													self.lwStatus.insertItem(0,'ERROR - Calcuating Median, suppressing median output')
												if calc_mean:
													calc_mean = False
													self.lwStatus.insertItem(0,'ERROR - Calcuating mean, suppressing mean output')
									else:
										found = False
										message = 'Unexpected Format Version:'+str(res.formatVersion)
									if not found:
										self.lwStatus.insertItem(0,message)
										if res.formatVersion == 1:
											message = "No data for "+ydataid + " (1D) - " + typename
										else:
											message = "No data for "+ydataid + " ("+dom+") - " + typename
										self.lwStatus.insertItem(0,message)
									else:
										if res.formatVersion == 1:
											if (len(reslist) > 1):
												label = res.displayname + ": " +ydataid + " (1D) - " + typename
											else:
												label = ydataid + " - " + typename
										else:
											if (len(reslist) > 1):
												label = res.displayname + ": " +ydataid + "("+dom+") - " + typename
											else:
												label = ydataid + " ("+dom+") - " + typename

										tmp_xmin=min(xdata)
										xmin = min(xmin,tmp_xmin)
										tmp_xmax=max(xdata)
										xmax = max(xmax,tmp_xmax)
										tmp_ymin=ydata.min()
										ymin = min(ymin,tmp_ymin)
										tmp_ymax=ydata.max()
										ymax = max(ymax,tmp_ymax)
										
										#self.subplot.set_xbound(lower=xmin, upper=xmax)
										#self.subplot.set_ybound(lower=ymin, upper=ymax)
										if len(xdata)==len(ydata):
											a, = self.subplot.plot(xdata, ydata)
											self.artists.append(a)
											self.labels.append(label)
											self.subplot.hold(True)
											if 'flow' in typename.lower():
												yTitle = 'Flow ({0}$^3$/s)'.format(units) if units is not None else 'Flow'
											elif 'velocities' in typename.lower():
												yTitle = 'Velocity ({0}/s)'.format(
													units) if units is not None else 'Velocity'
											elif 'level' in typename.lower():
												yTitle = 'Elevation ({0} RL)'.format(
													units) if units is not None else 'Elevation'
											else:
												yTitle = None
										else:
											self.lwStatus.insertItem(0,'ERROR - Size of x and y data doesnt match')
					if len(typenames) > 1:
						if len(typenames) > 2:
							yTitle = None
						elif len(typenames) == 2 and not ('US Levels' in typenames and 'DS Levels' in typenames):
							yTitle = None
					# AXIS 2
					#xdata = res.getXData()
					if (self.cb2ndAxis.isChecked()): # if not checked not dual axis needed
						breakloop = False
						for i, ydataid in enumerate(self.IDs):
							if ydataid:
								for typename in typenames2:
									found = False
									message = 'ERROR - Unable to extract data'
									if not breakloop:
										if res.formatVersion == 1: #2013
											found, ydata, message = res.getTSData(ydataid,typename)
											xdata = res.times
										elif res.formatVersion == 2: #2015
											#self.lwStatus.insertItem(0,'domain: '+self.Doms[i])
											dom = self.Doms[i].upper()
											source = self.Source_Att[i].upper()
											if (dom == '2D'):
												if typename.upper().find('STRUCTURE FLOWS')>= 0 and source=='QS':
													typename = 'QS'
													yTitle2 = 'Flow ({0}$^3$/s)'.format(
														units) if units is not None else 'Flow'
												elif typename.upper().find('STRUCTURE LEVELS')>= 0 and source=='HU':
													typename = 'HU'
													yTitle2 = 'Elevation ({0} RL)'.format(
														units) if units is not None else 'Elevation'
												elif typename.upper().find('STRUCTURE LEVELS')>= 0 and source=='HD':
													typename = 'HD'
													yTitle2 = 'Elevation ({0} RL)'.format(
														units) if units is not None else 'Elevation'
											try:
												found, ydata, message = res.getTSData(ydataid,dom,typename, 'Geom')
												xdata = res.times
											except:
												self.lwStatus.insertItem(0,'ERROR - Extracting results')
												self.lwStatus.insertItem(0,'res = '+res.displayname)
												self.lwStatus.insertItem(0,'ID: '+ydataid)
												self.lwStatus.insertItem(0,'i: '+str(i))
										else:
											found = False
											message = 'Unexpected Format Version:'+str(res.formatVersion)
										if not found:
											ydata = xdata * 0.0 # keep the same dimensions other the plot will fail
											self.lwStatus.insertItem(0,message)
											if res.formatVersion == 1:
												message = "No data for "+ydataid + " (1D) - " + typename
											else:
												message = "No data for "+ydataid + " ("+dom+") - " + typename
											self.lwStatus.insertItem(0,message)
										else:
											if res.formatVersion == 1:
												if (len(reslist) > 1):
													label = res.displayname + ": " + ydataid + " (1D) - " + typename +" (Axis 2)"
												else:
													label = ydataid + " (1D) - " + typename +" (Axis 2)"
											else:
												if (len(reslist) > 1):
													label = res.displayname + ": " + ydataid + " ("+dom+") - " + typename +" (Axis 2)"
												else:
													label = ydataid + " ("+dom+") - " + typename +" (Axis 2)"
											if len(xdata)==len(ydata):
												a2, = self.axis2.plot(xdata, ydata, marker='x')
												self.artists.append(a2)
												self.labels.append(label)
												self.axis2.hold(True)
												if 'flow' in typename.lower():
													yTitle2 = 'Flow ({0}$^3$/s)'.format(
														units) if units is not None else 'Flow'
												elif 'velocities' in typename.lower():
													yTitle2 = 'Velocity ({0}/s)'.format(
														units) if units is not None else 'Velocity'
												elif 'level' in typename.lower():
													yTitle2 = 'Elevation ({0} RL)'.format(
														units) if units is not None else 'Elevation'
												else:
													yTitle = None
											else:
												self.lwStatus.insertItem(0,'ERROR - Number of x and y data points doesnt match')
					if len(typenames2) > 1:
						if len(typenames2) > 2:
							yTitle2 = None
						elif len(typenames2) == 2 and not ('US Levels' in typenames2 and 'DS Levels' in typenames2):
							yTitle2 = None
					#add time if time enabled
					if plot_current_time and nres_used==len(reslist): #only add time for last active result so it shows last in legend
						for x in range(0, self.listTime.count()):
							list_item = self.listTime.item(x)
							ax1y1, ax1y2 = self.subplot.get_ylim() #get current limits
							if list_item.isSelected():
								#timeInd = x
								#timeStr = list_item.text()
								try:
									curT = float(list_item.text())
									a, = self.subplot.plot([curT,curT], [-9e37, 9e37],color='red',linewidth=2)
									self.artists.append(a)
									self.labels.append('Current time ({0})'.format(list_item.text()))
									self.subplot.set_ylim([ax1y1, ax1y2])
									#self.subplot.hold(True)
								except:
									self.lwStatus.insertItem(0,'Unable to add current time')
					
				# add median data
				if calc_median:
					try:
						argsort = max_vals.argsort()
						med_rnk = int(nRes / 2)  # +1 not requried as python uses 0 rank
						self.lwStatus.insertItem(0, 'For {0} results using rank {1} for median'.format(
							nRes, med_rnk + 1))
						med_ind = argsort[med_rnk]
						res = self.res[med_ind]
						if res.formatVersion == 1:
							self.lwStatus.insertItem(0, 'ERROR - Median not valid for Pre 2016 results')
						elif res.formatVersion == 2:
							name = res.displayname
							ydataid = self.IDs[0]  # only works for 1 ID
							typename = typenames[0]  # and 1 data type
							dom = self.Doms[0]
							source = self.Source_Att[0].upper()
							found, ydata, message = res.getTSData(ydataid, dom, typename, 'Geom')
							if not found:
								self.lwStatus.insertItem(0, 'ERROR - Extracting median data.')
							else:
								xdata = res.times
								label = 'Median - {0}'.format(name)
								a, = self.subplot.plot(xdata, ydata, color='black', linewidth=3,
								                       linestyle=':')
								self.artists.append(a)
								self.labels.append(label)
					except:
						self.lwStatus.insertItem(0, 'ERROR - Adding Median data, skipping')
				# add mean data (2017-06-AD)
				if calc_mean:
					try:
						argsort = max_vals.argsort()
						meanVal = max_vals.mean()
						ms = numpy.sort(max_vals)
						if meanAbove:
							ms_ind = ms.searchsorted(meanVal, side='right')
						else:
							ms_ind = (numpy.abs(ms - meanVal)).argmin()
						mean_ind = argsort[ms_ind]
						self.lwStatus.insertItem(0,
						                         'Mean value is {0}, rank index is {1}'.format(meanVal,
						                                                                       ms_ind + 1))
						res = self.res[mean_ind]
						if res.formatVersion == 1:
							self.lwStatus.insertItem(0, 'ERROR - Mean not valid for Pre 2016 results')
						elif res.formatVersion == 2:
							name = res.displayname
							ydataid = self.IDs[0]  # only works for 1 ID
							typename = typenames[0]  # and 1 data type
							dom = self.Doms[0]
							source = self.Source_Att[0].upper()
							found, ydata, message = res.getTSData(ydataid, dom, typename, 'Geom')
							if not found:
								self.lwStatus.insertItem(0, 'ERROR - Extracting median data.')
							else:
								xdata = res.times
								label = 'Mean - {0}'.format(name)
								a, = self.subplot.plot(xdata, ydata, color='blue', linewidth=3,
								                       linestyle=':')
								self.artists.append(a)
								self.labels.append(label)
					except:
						self.lwStatus.insertItem(0, 'ERROR - Adding Mean data, skipping')
			# Hydraulic properties______________________________________________________________________
			elif loc == "Hydraulic Properties":
				yTitle = 'Elevation ({0} RL)'.format(units) if units is not None else 'Elevation'
				# 1D ta table check files
				tableFiles = []
				for i in range(self.HydPropList.count()):
					if self.HydPropList.item(i).isSelected():
						tableFiles.append(self.HydPropList.item(i).text())
				k = ''
				k2 = ''
				if len(typenames) > 0:
					k = typenames[-1]
				if len(typenames2) > 0:
					k2 = typenames2[-1]
				for i, tableFile in enumerate(tableFiles):
					for d in self.hydTables.loadedData:
						if tableFile == d.displayName:
							tableIndex = i
							break
					d = self.hydTables.loadedData[tableIndex]
					if 'Depth' in typenames or 'Storage Width' in typenames or 'Flow Width' in typenames or \
							'Area' in typenames or 'P' in typenames or 'Radius' in typenames or \
							'Vert Res Factor' in typenames or 'K (n=' in k:
						for t in typenames:
							try:
								tIndex = d.channelHydTa_headers.index(t)
								for j in range(self.IDList.count()):
									jIndex = d.channelNames.index(self.IDList.item(j).text())
									xmin = round(min(d.channelHydTa[jIndex][:, tIndex]), 0) - 1
									xmax = round(max(d.channelHydTa[jIndex][:, tIndex]), 0) + 1
									ymin = round(min(d.channelHydTa[jIndex][:, 0]), 0) - 1
									ymax = round(max(d.channelHydTa[jIndex][:, 0]), 0) + 1
									a, = self.subplot.plot(d.channelHydTa[jIndex][:, tIndex],
									                       d.channelHydTa[jIndex][:, 0])
									self.artists.append(a)
									if len(tableFiles) < 2:
										label = "{0} - {1}".format(self.IDList.item(j).text(), t)
									else:
										label = "{0}: {1} - {2}".format(d.displayName, self.IDList.item(j).text(), t)
									self.labels.append(label)
									self.subplot.hold(True)
									if 'Storage Width' in typenames or 'Flow Width' in typenames:
										xTitle = 'Station ({0})'.format(units) if units is not None else 'Station'
									elif 'Area' in typenames:
										xTitle = 'Area ({0}$^2$)'.format(units) if units is not None else 'Area'
									elif 'Vert Res Factor' in typenames or 'K (n=' in k:
										xTitle = None
									else:
										xTitle = '{0}'.format(units) if units is not None else None
							except:
								pass
					if 'US XSection' in typenames:
						for j in range(self.IDList.count()):
							try:
								jIndex = d.channelNames.index(self.IDList.item(j).text())
								usSection = d.channelXs[jIndex][0]
								usIndex = d.xsNos.index(usSection)
								xmin = round(min(d.xsSections[usIndex][:, 0]), 0) - 1
								xmax = round(max(d.xsSections[usIndex][:, 0]), 0) + 1
								ymin = round(min(d.xsSections[usIndex][:, 1]), 0) - 1
								ymax = round(max(d.xsSections[usIndex][:, 1]), 0) + 1
								a, = self.subplot.plot(d.xsSections[usIndex][:, 0], d.xsSections[usIndex][:, 1])
								self.artists.append(a)
								if len(tableFiles) < 2:
									label = "US XSection - {0}".format(self.IDList.item(j).text())
								else:
									label = "{0}: US XSection - {1}".format(d.displayName, self.IDList.item(j).text())
								self.labels.append(label)
								self.subplot.hold(True)
								xTitle = 'Station ({0})'.format(units) if units is not None else 'Station'
							except:
								self.lwStatus.insertItem(0, "can't find XS for channel")
					if 'DS XSection' in typenames:
						for j in range(self.IDList.count()):
							try:
								jIndex = d.channelNames.index(self.IDList.item(j).text())
								if len(d.channelXs[jIndex]) == 2:
									dsSection = d.channelXs[jIndex][1]
								else:
									dsSection = d.channelXs[jIndex][0]
								dsIndex = d.xsNos.index(dsSection)
								xmin = round(min(d.xsSections[dsIndex][:, 0]), 0) - 1
								xmax = round(max(d.xsSections[dsIndex][:, 0]), 0) + 1
								ymin = round(min(d.xsSections[dsIndex][:, 1]), 0) - 1
								ymax = round(max(d.xsSections[dsIndex][:, 1]), 0) + 1
								a, = self.subplot.plot(d.xsSections[dsIndex][:, 0], d.xsSections[dsIndex][:, 1])
								self.artists.append(a)
								if len(tableFiles) < 2:
									label = "DS XSection - {0}".format(self.IDList.item(j).text())
								else:
									label = "{0}: DS XSection - {1}".format(d.displayName, self.IDList.item(j).text())
								self.labels.append(label)
								self.subplot.hold(True)
								xTitle = 'Station ({0})'.format(units) if units is not None else 'Station'
							except:
								self.lwStatus.insertItem(0, "can't find XS for channel")
				if len(typenames) > 1:
					compatible_list = ['Storage Width', 'Flow Width', 'US XSection', 'DS XSection']
					compatible = True
					for typename in typenames:
						if typename not in compatible_list:
							compatible = False
							break
					if not compatible:
						xTitle = None
				# AXIS 2
				if (self.cb2ndAxis.isChecked()):
					for i, tableFile in enumerate(tableFiles):
						for d in self.hydTables.loadedData:
							if tableFile == d.displayName:
								tableIndex = i
								break
						if 'Depth' in typenames2 or 'Storage Width' in typenames2 or 'Flow Width' in typenames2 or \
								'Area' in typenames2 or \
								'P' in typenames2 or 'Radius' in typenames2 or \
								'Vert Res Factor' in typenames2 or 'K (n=' in k2:
							for t in typenames2:
								try:
									tIndex = d.channelHydTa_headers.index(t)
									for j in range(self.IDList.count()):
										#self.axis2.xaxis.set_ticks_position("bottom")
										#self.axis2.xaxis.set_label_position("bottom")
										#self.axis2.spines['bottom'].set_position(("axes", -0.1))
										jIndex = d.channelNames.index(self.IDList.item(j).text())
										a2, = self.axis2.plot(d.channelHydTa[jIndex][:, tIndex],
										                      d.channelHydTa[jIndex][:, 0], marker='x')
										self.artists.append(a2)
										if len(tableFiles) < 2:
											label = "{0} - {1} (axis 2)".format(self.IDList.item(j).text(), t)
										else:
											label = "{0}: {1} - {2} (axis 2)".format(d.displayName, self.IDList.item(j).text(), t)
										self.labels.append(label)
										self.axis2.hold(True)
										if 'Storage Width' in typenames2 or 'Flow Width' in typenames2:
											xTitle2 = 'Station ({0})'.format(units) if units is not None else 'Station'
										elif 'Area' in typenames2:
											xTitle2 = 'Area ({0}$^2$)'.format(units) if units is not None else 'Area'
										elif 'Vert Res Factor' in typenames2 or 'K (n=' in k2:
											xTitle2 = None
										else:
											xTitle2 = '{0}'.format(units) if units is not None else None
								except:
									pass
						if 'US XSection' in typenames2:
							for j in range(self.IDList.count()):
								try:
									jIndex = d.channelNames.index(self.IDList.item(j).text())
									usSection = d.channelXs[jIndex][0]
									usIndex = d.xsNos.index(usSection)
									#self.axis2.xaxis.set_ticks_position("bottom")
									#self.axis2.xaxis.set_label_position("bottom")
									#self.axis2.spines['bottom'].set_position(("axes", -0.1))
									a2, = self.axis2.plot(d.xsSections[usIndex][:, 0],
									                       d.xsSections[usIndex][:, 1], marker='x')
									self.artists.append(a2)
									if len(tableFiles) < 2:
										label = "US XSection - {0} (axis 2)".format(self.IDList.item(j).text())
									else:
										label = "{0}: US XSection - {1} (axis 2)".format(d.displayName, self.IDList.item(j).text())
									self.labels.append(label)
									self.axis2.hold(True)
									xTitle2 = 'Station ({0})'.format(units) if units is not None else 'Station'
								except:
									self.lwStatus.insertItem(0, "can't find XS for channel")
						if 'DS XSection' in typenames2:
							for j in range(self.IDList.count()):
								try:
									jIndex = d.channelNames.index(self.IDList.item(j).text())
									if len(d.channelXs[jIndex]) == 2:
										dsSection = d.channelXs[jIndex][1]
									else:
										dsSection = d.channelXs[jIndex][0]
									dsIndex = d.xsNos.index(dsSection)
									#self.axis2.xaxis.set_ticks_position("bottom")
									#self.axis2.xaxis.set_label_position("bottom")
									#self.axis2.spines['bottom'].set_position(("axes", -0.1))
									a2, = self.axis2.plot(d.xsSections[dsIndex][:, 0],
									                       d.xsSections[dsIndex][:, 1], marker='x')
									self.artists.append(a2)
									if len(tableFiles) < 2:
										label = "DS XSection - {0} (axis 2)".format(self.IDList.item(j).text())
									else:
										label = "{0}: DS XSection - {1} (axis 2)".format(d.displayName, self.IDList.item(j).text())
									self.labels.append(label)
									self.axis2.hold(True)
									xTitle2 = 'Station ({0})'.format(units) if units is not None else 'Station'
								except:
									self.lwStatus.insertItem(0, "can't find XS for channel")
					if len(typenames2) > 1:
						compatible_list = ['Storage Width', 'Flow Width', 'US XSection', 'DS XSection']
						compatible = True
						for typename in typenames2:
							if typename not in compatible_list:
								compatible = False
								break
						if not compatible:
							xTitle = None
		if self.cbShowLegend.isChecked():
			if self.cbLegendUR.isChecked():
				self.subplot.legend(self.artists, self.labels, loc=1)
			elif self.cbLegendUL.isChecked():
				self.subplot.legend(self.artists, self.labels, loc=2)
			elif self.cbLegendLL.isChecked():
				self.subplot.legend(self.artists, self.labels, loc=3)
			elif self.cbLegendLR.isChecked():
				self.subplot.legend(self.artists, self.labels, loc=4)
			else:
				self.subplot.legend(self.artists, self.labels, bbox_to_anchor=(0, 0, 1, 1))
		
		self.subplot.hold(False)
		self.subplot.grid(True)
			
		if self.customAxis is not None and self.customAxis.xAxisCustom_rb.isChecked():
			xmin = self.customAxis.xLim[0]
			xmax = self.customAxis.xLim[1]
			xinc = self.customAxis.xInc
			self.subplot.set_xbound(lower=xmin, upper=xmax)
			if (xmax * 1000 + xinc * 1000) % (xinc * 1000) != 0:
				self.subplot.set_xticks(scipy.arange(xmin, xmax, xinc))
			else:
				self.subplot.set_xticks(scipy.arange(xmin, xmax + xinc, xinc))
		else:
			xmin = math.floor(xmin)
			xmax = math.ceil(xmax)
			self.subplot.set_xbound(lower=xmin, upper=xmax)
		if self.customAxis is not None and self.customAxis.yAxisCustom_rb.isChecked():
			ymin = self.customAxis.yLim[0]
			ymax = self.customAxis.yLim[1]
			yinc = self.customAxis.yInc
			self.subplot.set_ybound(lower=ymin, upper=ymax)
			if (ymax * 1000 + yinc * 1000) % (yinc * 1000) != 0:
				self.subplot.set_yticks(scipy.arange(ymin, ymax, yinc))
			else:
				self.subplot.set_yticks(scipy.arange(ymin, ymax + yinc, yinc))
		else:
			ymin = math.floor(ymin)
			
			if ymax - ymin < 10:
				yinc = 1
			elif ymax - ymin < 30:
				yinc = 5
			elif ymax - ymin < 100:
				yinc = 10
			elif ymax - ymin < 300:
				yinc = 50
			elif ymax - ymin < 1000:
				yinc = 100
			elif ymax - ymin < 3000:
				yinc = 500
			elif ymax - ymin < 10000:
				yinc = 1000
			elif ymax - ymin < 30000:
				yinc = 5000
			elif ymax - ymin < 100000:
				yinc = 10000
			elif ymax - ymin < 300000:
				yinc = 50000
			elif ymax - ymin < 1000000:
				yinc = 100000
			elif ymax - ymin < 10000000:
				yinc = 1000000
			elif ymax - ymin < 100000000:
				yinc = 10000000
			elif ymax - ymin < 1000000000:
				yinc = 100000000
			elif ymax - ymin < 10000000000:
				yinc = 1000000000
			ymax = math.ceil(ymax / yinc) * yinc  # round upper to nearest xinc
			self.subplot.set_ybound(lower=ymin, upper=ymax)
		if xTitle is not None:
			self.subplot.set_xlabel(xTitle)
		else:
			self.subplot.set_xlabel('')
		if yTitle is not None:
			self.subplot.set_ylabel(yTitle)
		else:
			self.subplot.set_ylabel('')
		try:
			if self.customLabels.xAxisAuto_cb.isChecked():
				self.subplot.set_xlabel(self.customLabels.xLabel)
			if self.customLabels.yAxisAuto_cb.isChecked():
				self.subplot.set_ylabel(self.customLabels.yLabel)
		except:
			pass
		# Secondary axis
		if self.ax2_exists:
			if self.axis2._sharey is not None:
				if self.customAxis is not None and self.customAxis.xAxisCustom_rb_2.isChecked():
					x2min = self.customAxis.x2Lim[0]
					x2max = self.customAxis.x2Lim[1]
					x2inc = self.customAxis.x2Inc
					self.axis2.set_xbound(lower=x2min, upper=x2max)
					if (x2max * 1000 + x2inc * 1000) % (x2inc * 1000) != 0:
						self.axis2.set_xticks(scipy.arange(x2min, x2max, x2inc))
					else:
						self.axis2.set_xticks(scipy.arange(x2min, x2max + x2inc, x2inc))
				if xTitle2 is not None:
					self.axis2.set_xlabel(xTitle2)
				else:
					self.axis2.set_xlabel('')
				try:
					if self.customLabels.xAxisAuto2_cb.isChecked():
						self.axis2.set_xlabel(self.customLabels.xLabel2)
				except:
					pass
			elif self.axis2._sharex is not None:
				if self.customAxis is not None and self.customAxis.yAxisCustom_rb_2.isChecked():
					y2min = self.customAxis.y2Lim[0]
					y2max = self.customAxis.y2Lim[1]
					y2inc = self.customAxis.y2Inc
					self.axis2.set_ybound(lower=y2min, upper=y2max)
					if (y2max * 1000 + y2inc * 1000) % (y2inc * 1000) != 0:
						self.axis2.set_yticks(scipy.arange(y2min, y2max, y2inc))
					else:
						self.axis2.set_yticks(scipy.arange(y2min, y2max + y2inc, y2inc))
				if yTitle2 is not None:
					self.axis2.set_ylabel(yTitle2)
				else:
					self.axis2.set_ylabel('')
				try:
					if self.customLabels.yAxisAuto2_cb.isChecked():
						self.axis2.set_ylabel(self.customLabels.yLabel2)
				except:
					pass
		try:
			if self.customLabels.title:
				self.subplot.set_title(self.customLabels.title)
			else:
				self.subplot.set_title('')
		except:
			pass
		self.fig.tight_layout()
		self.plotWdg.draw()

