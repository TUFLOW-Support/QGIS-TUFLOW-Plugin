# -*- coding: utf-8 -*-
"""
/***************************************************************************
 tuflowqgis_menuDialog
                                 A QGIS plugin
 Initialises the TUFLOW menu system
                             -------------------
        begin                : 2013-08-27
        copyright            : (C) 2013 by Phillip Ryan
        email                : support@tuflow.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

#import csv
import os.path
import operator
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
import glob
import processing
from .tuflowqgis_library import *
from PyQt5.QtWidgets import *
from qgis.gui import QgsProjectionSelectionWidget
from datetime import datetime
import sys
import subprocess
import numpy as np
import matplotlib
try:
	import matplotlib.pyplot as plt
except:
	current_path = os.path.dirname(__file__)
	sys.path.append(os.path.join(current_path, '_tk\\DLLs'))
	sys.path.append(os.path.join(current_path, '_tk\\libs'))
	sys.path.append(os.path.join(current_path, '_tk\\Lib'))
	import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from tuflow.tuflowqgis_library import interpolate, convertStrftimToTuviewftim, convertTuviewftimToStrftim
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms")
currentFolder = os.path.dirname(os.path.abspath(__file__))


# ----------------------------------------------------------
#    tuflowqgis increment selected layer
# ----------------------------------------------------------

from ui_tuflowqgis_increment import *

class tuflowqgis_increment_dialog(QDialog, Ui_tuflowqgis_increment):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		cLayer = self.canvas.currentLayer()
		cName = None
		fname = ''
		fpath = None
		self.curr_file = None
		
		if cLayer:
			cName = cLayer.name()
			dp = cLayer.dataProvider()
			ds = dp.dataSourceUri()
			fpath = os.path.dirname(unicode(ds))
			basename = os.path.basename(unicode(ds))
			ind = basename.find('|')
			if (ind>0):
				fname = basename[0:ind]
			else:
				fname = basename
			self.curr_file = os.path.join(fpath,fname)
		else:
			QMessageBox.information( self.iface.mainWindow(),"Information", "No layer is currently selected in the layer control")
		#QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outfile)
		self.browseoutfile.clicked.connect(self.browse_outfile)
		#QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
		self.buttonBox.accepted.connect(self.run)
		#QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.sourcelayer_changed)
		self.sourcelayer.currentIndexChanged[int].connect(self.sourcelayer_changed)
		
		i = 0
		for name, layer in QgsProject.instance().mapLayers().items():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if layer.name() == cName:
					self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if (fpath):
			self.outfolder.setText(fpath)
			outfname = tuflowqgis_increment_fname(fname)
			self.outfilename.setText(outfname)
		else:
			self.outfolder.setText('No layer currently selected!')
			self.outfilename.setText('No layer currently selected!')

	def browse_outfile(self):
		outfolder = unicode(self.outfolder.displayText()).strip()
		newname = QFileDialog.getSaveFileName(None, "Output Shapefile", outfolder, "*.shp")
		if len(newname)>0:
			fpath, fname = os.path.split(newname[0])
			self.outfolder.setText(fpath)
			outfname = tuflowqgis_increment_fname(fname)
			self.outfilename.setText(outfname)

	def sourcelayer_changed(self):
		layername = unicode(self.sourcelayer.currentText())
		layer = tuflowqgis_find_layer(layername)
		try:
			dp = layer.dataProvider()
			ds = dp.dataSourceUri()
			fpath = os.path.dirname(unicode(ds))
			basename = os.path.basename(unicode(ds))
			ind = basename.find('|')
			if (ind>0):
				fname = basename[0:ind]
			else:
				fname = basename
			self.curr_file = os.path.join(fpath,fname)
			self.outfolder.setText(fpath)
			outfname = tuflowqgis_increment_fname(fname)
			self.outfilename.setText(outfname)
		except:
			QMessageBox.information( self.iface.mainWindow(),"Information", "Unexpected error")

	def run(self):
		if self.checkBox.isChecked():
			keepform = True
		else:
			keepform = False
		layername = unicode(self.sourcelayer.currentText())
		layer = tuflowqgis_find_layer(layername)
		outname = unicode(self.outfilename.displayText()).strip()
		if not outname[-4:].upper() == '.SHP':
			outname = outname+'.shp'
			QMessageBox.information( self.iface.mainWindow(),"Information", "Appending .shp to filename.")
		outfolder = unicode(self.outfolder.displayText()).strip()
		savename = os.path.join(outfolder,outname)
		if savename == self.curr_file:
			QMessageBox.critical( self.iface.mainWindow(),"ERROR", "Output filename is the same as the current layer.")
			return
		
		#check if file exists
		if os.path.isfile(savename):
			QMessageBox.critical( self.iface.mainWindow(),"ERROR", "Output file already exists \n"+savename)
			return
		message = tuflowqgis_duplicate_file(self.iface, layer, savename, keepform)
		if message != None:
			QMessageBox.critical(self.iface.mainWindow(), "Duplicating File", message)
		QgsProject.instance().removeMapLayer(layer.id())
		self.iface.addVectorLayer(savename, os.path.basename(savename)[:-4], "ogr")


# ----------------------------------------------------------
#    tuflowqgis import empty tuflow files
# ----------------------------------------------------------
from ui_tuflowqgis_import_empties import *
from .tuflowqgis_settings import TF_Settings
class tuflowqgis_import_empty_tf_dialog(QDialog, Ui_tuflowqgis_import_empty):
	def __init__(self, iface, project):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.tfsettings = TF_Settings()
		
		# load stored settings
		error, message = self.tfsettings.Load()
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", "Error Loading Settings: "+message)
			
		self.browsedir.clicked.connect(self.browse_empty_dir)
		self.emptydir.editingFinished.connect(self.dirChanged)
		self.buttonBox.accepted.connect(self.run)

		if self.tfsettings.combined.base_dir:
			#self.emptydir.setText(self.tfsettings.combined.base_dir+"\\TUFLOW\\model\\gis\\empty")
			self.emptydir.setText(os.path.join(self.tfsettings.combined.base_dir,"TUFLOW","model","gis","empty"))
		else:
			self.emptydir.setText("ERROR - Project not loaded")
			
		# load empty types
		self.emptyType.clear()
		if self.emptydir.text() == "ERROR - Project not loaded":
			self.emptyType.addItem('No empty directory')
		elif not os.path.exists(self.emptydir.text()):
			self.emptyType.addItem('Empty directory not valid')
		else:
			search_string = '{0}{1}*.shp'.format(self.emptydir.text(), os.path.sep)
			files = glob.glob(search_string)
			empty_list = []
			for file in files:
				if len(file.split('_empty')) < 2:
					continue
				empty_type = os.path.basename(file.split('_empty')[0])
				if empty_type not in empty_list:
					empty_list.append(empty_type)
					self.emptyType.addItem(empty_type)

	def browse_empty_dir(self):
		startDir = None
		dir = self.emptydir.text()
		while dir:
			if os.path.exists(dir):
				startDir = dir
				break
			else:
				dir = os.path.dirname(dir)
			
		newname = QFileDialog.getExistingDirectory(None, "Output Directory", startDir)
		if len(newname) > 0:
			self.emptydir.setText(newname)
			
			# load empty types
			self.emptyType.clear()
			if self.emptydir.text() == "ERROR - Project not loaded":
				self.emptyType.addItem('No empty directory')
			elif not os.path.exists(self.emptydir.text()):
				self.emptyType.addItem('Empty directory not valid')
			else:
				search_string = '{0}{1}*.shp'.format(self.emptydir.text(), os.path.sep)
				files = glob.glob(search_string)
				empty_list = []
				for file in files:
					if len(file.split('_empty')) < 2:
						continue
					empty_type = os.path.basename(file.split('_empty')[0])
					if empty_type not in empty_list:
						empty_list.append(empty_type)
						self.emptyType.addItem(empty_type)

	def dirChanged(self):
		# load empty types
		self.emptyType.clear()
		if self.emptydir.text() == "ERROR - Project not loaded":
			self.emptyType.addItem('No empty directory')
		elif not os.path.exists(self.emptydir.text()):
			self.emptyType.addItem('Empty directory not valid')
		else:
			search_string = '{0}{1}*.shp'.format(self.emptydir.text(), os.path.sep)
			files = glob.glob(search_string)
			empty_list = []
			for file in files:
				if len(file.split('_empty')) < 2:
					continue
				empty_type = os.path.basename(file.split('_empty')[0])
				if empty_type not in empty_list:
					empty_list.append(empty_type)
					self.emptyType.addItem(empty_type)
	
	def run(self):
		runID = unicode(self.txtRunID.displayText()).strip()
		basedir = unicode(self.emptydir.displayText()).strip()

		# Compile a list and header of selected attributes
		empty_types = []
		for x in range(0, self.emptyType.count()):
			list_item = self.emptyType.item(x)
			if list_item.isSelected():
				empty_types.append(list_item.text())

		# check which geometries are selected
		points = self.checkPoint.isChecked()
		lines = self.checkLine.isChecked()
		regions = self.checkRegion.isChecked()

		# run create dir script
		message = tuflowqgis_import_empty_tf(self.iface, basedir, runID, empty_types, points, lines, regions)
		#message = tuflowqgis_create_tf_dir(self.iface, crs, basedir)
		if message != None:
			QMessageBox.critical(self.iface.mainWindow(), "Importing TUFLOW Empty File(s)", message)

# ----------------------------------------------------------
#    tuflowqgis Run TUFLOW (Simple)
# ----------------------------------------------------------
from ui_tuflowqgis_run_tf_simple import *
from .tuflowqgis_settings import TF_Settings
class tuflowqgis_run_tf_simple_dialog(QDialog, Ui_tuflowqgis_run_tf_simple):
	def __init__(self, iface, project):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.tfsettings = TF_Settings()
		project_loaded = False
		
		# load stored settings
		error, message = self.tfsettings.Load()
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", "Error Loading Settings: "+message)
		
		
		if self.tfsettings.combined.tf_exe:
			tfexe = self.tfsettings.combined.tf_exe
			self.exefolder, dum  = os.path.split(tfexe)
			project_loaded = True
		else: #load last used exe
			tfexe = self.tfsettings.get_last_exe()
		if self.tfsettings.combined.base_dir:
			self.tffolder = self.tfsettings.combined.base_dir
			self.runfolder = os.path.join(self.tffolder,'TUFLOW','runs')
			project_loaded = True
		else: #load last used directory
			self.runfolder = self.tfsettings.get_last_run_folder()
		if not project_loaded:
			QMessageBox.information( self.iface.mainWindow(),"Information", "Project not loaded using last saved location.")
			
		self.TUFLOW_exe.setText(tfexe)
		
		#QObject.connect(self.browsetcffile, SIGNAL("clicked()"), self.browse_tcf)
		self.browsetcffile.clicked.connect(self.browse_tcf)
		#QObject.connect(self.browseexe, SIGNAL("clicked()"), self.browse_exe)
		self.browseexe.clicked.connect(self.browse_exe)
		#QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)
		self.buttonBox.accepted.connect(self.run)

		files = glob.glob(unicode(self.runfolder)+os.path.sep+"*.tcf")
		self.tcfin=''
		if (len(files) > 0):
			files.sort(key=os.path.getmtime, reverse=True)
			self.tcfin = files[0]
		if (len(self.tcfin)>3):
			self.tcf.setText(self.tcfin)


	def browse_tcf(self):
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW Control File', self.runfolder, "TUFLOW Control File (*.tcf)")
		inFileName = inFileName[0]
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.tcfin = inFileName
		#self.tfsettings.save_last_exe(self,last_exe)("TUFLOW_Run_TUFLOW/tcf", inFileName)
		
		self.tcf.setText(inFileName)
		head, tail = os.path.split(inFileName)
		if head != os.sep and head.lower() != 'c:\\' and head != '':
			self.tfsettings.save_last_run_folder(head)
			#self.tfsettings.setValue("TUFLOW_Run_TUFLOW/tcfDir", head)

	def browse_exe(self):
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW exe', self.exefolder, "TUFLOW Executable (*.exe)")
		inFileName = str(inFileName)
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.tfsettings.save_last_exe(inFileName)
		self.exe = inFileName
		#self.tfsettings.setValue("TUFLOW_Run_TUFLOW/exe", inFileName)
		self.TUFLOW_exe.setText(inFileName)
		#head, tail = os.path.split(inFileName)
		#if head <> os.sep and head.lower() <> 'c:\\' and head <> '':
		#	self.tfsettings.setValue("TUFLOW_Run_TUFLOW/exeDir", head)

	def run(self):
		tcf = unicode(self.tcf.displayText()).strip()
		tfexe = unicode(self.TUFLOW_exe.displayText()).strip()
		QMessageBox.information(self.iface.mainWindow(), "Running TUFLOW","Starting simulation: "+tcf+"\n Executable: "+tfexe)
		message = run_tuflow(self.iface, tfexe, tcf)
		if message != None:
			QMessageBox.critical(self.iface.mainWindow(), "Running TUFLOW", message)

# ----------------------------------------------------------
#    tuflowqgis points to lines
# ----------------------------------------------------------
from ui_tuflowqgis_line_from_points import *

class tuflowqgis_line_from_points(QDialog, Ui_tuflowqgis_line_from_point):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		cLayer = self.canvas.currentLayer()
		fname = ''
		fpath = None
		cName = ''
		
		if cLayer:
			cName = cLayer.name()
			dp = cLayer.dataProvider()
			datacolumns = dp.fields()
			ds = dp.dataSourceUri()
			fpath = os.path.dirname(unicode(ds))
			basename = os.path.basename(unicode(ds))
			ind = basename.find('|')
			if (ind>0):
				fname = basename[0:ind]
			else:
				fname = basename
			fields = cLayer.pendingFields()
			for (counter, field) in enumerate(fields):
				self.elev_attr.addItem(str(field.name()))
				if str(field.name()).lower() == 'z':
					self.elev_attr.setCurrentIndex(counter)
				elif str(field.name()).lower() == 'elevation':
					self.elev_attr.setCurrentIndex(counter)
			# below is for QGIS 1.8
			#for key,value in datacolumns.items():
			#	#print str(key) + " = " + str(value.name())
			#	self.elev_attr.addItem(str(value.name()))
			#	if str(value.name()).lower() == 'z':
			#		self.elev_attr.setCurrentIndex(key)
			#	elif str(value.name()).lower() == 'elevation':
			#		self.elev_attr.setCurrentIndex(key)

		i = 0
		for name, layer in QgsProject.instance().mapLayers().items():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if layer.name() == cName:
					self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if (i == 0):
			self.outfolder.setText(fpath)
			self.outfilename.setText(fpath + "/"+fname)

		# Connect signals and slots
		#QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.source_changed) 
		self.sourcelayer.currentIndexChanged[int].connect(self.source_changed)
		#QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outfile)
		self.browseoutfile.clicked.connect(self.browse_outfile)
		#QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
		self.buttonBox.accepted.connect(self.run)


	def browse_outfile(self):
		newname = QFileDialog.getSaveFileName(None, "Output Shapefile", 
		self.outfilename.displayText(), "*.shp")
		if newname != None:
			self.outfilename.setText(newname)

	def source_changed(self):
		layername = unicode(self.sourcelayer.currentText())
		self.cLayer = tuflowqgis_find_layer(layername)
		self.elev_attr.clear()
		if self.cLayer and (self.cLayer.type() == QgsMapLayer.VectorLayer):
			datacolumns = self.cLayer.dataProvider().fields()
			GType = self.cLayer.dataProvider().geometryType()
			if (GType == QGis.WKBPoint):
				QMessageBox.information(self.iface.mainWindow(), "Info", "Point geometry layer")
			else:
				QMessageBox.information(self.iface.mainWindow(), "Info", "Please select point layer type")
			fields = self.cLayer.pendingFields()
			for (counter, field) in enumerate(fields):
				self.elev_attr.addItem(str(field.name()))
				if str(field.name()).lower() == 'z':
					self.elev_attr.setCurrentIndex(counter)
				elif str(field.name()).lower() == 'elevation':
					self.elev_attr.setCurrentIndex(counter)
			

	def run(self):
		import math
		layername = unicode(self.sourcelayer.currentText())
		self.layer = tuflowqgis_find_layer(layername)
		savename = unicode(self.outfilename.displayText()).strip()
		z_col = self.elev_attr.currentIndex()
		dmax_str = unicode(self.dmax.displayText())
		try:
			dmax = float(dmax_str)
		except:
			QMessageBox.critical( self.iface.mainWindow(),"Error", "Error converting input distance to numeric data type.  Make sure a number is specified." )
		
		npt = 0
		x = []
		y = []
		z = []
		feature = QgsFeature()
		self.layer.dataProvider().select(self.layer.dataProvider().attributeIndexes())
		self.layer.dataProvider().rewind()
		feature_count = self.layer.dataProvider().featureCount()
		while self.layer.dataProvider().nextFeature(feature):
			npt = npt + 1
			geom = feature.geometry()
			xn = geom.asPoint().x()
			yn = geom.asPoint().y()
			x.append(xn)
			y.append(yn)
			zn = feature.attributeMap()[z_col].toString()
			z.append(float(zn))
		QMessageBox.information(self.iface.mainWindow(),"Info", "finished reading points \n npts read = "+str(npt))
		
		# Create output file
		v_layer = QgsVectorLayer("LineString", "line", "memory")
		pr = v_layer.dataProvider()
		
		# add fields
		fields = { 0 : QgsField("z", QVariant.Double),1 : QgsField("dz", QVariant.Double),2 : QgsField("width", QVariant.Double),3 : QgsField("Options", QVariant.String) }
	
		message = None
		if len(savename) <= 0:
			message = "Invalid output filename given"
		
		if QFile(savename).exists():
			if not QgsVectorFileWriter.deleteShapeFile(savename):
				message =  "Failure deleting existing shapefile: " + savename
	
		outfile = QgsVectorFileWriter(savename, "System", 
			fields, QGis.WKBLineString, self.layer.dataProvider().crs())
	
		if (outfile.hasError() != QgsVectorFileWriter.NoError):
			message = "Failure creating output shapefile: " + unicode(outfile.errorMessage())
		
		if message != None:
			QMessageBox.critical( self.iface.mainWindow(),"Error", message)
			
		line_num = 0
		pt_num = 0
		pol = 0
		newline = True


		point_list = []
		for pt in range(npt):
			pt2x = x[pt]
			pt2y = y[pt]
			qpt = QgsPoint(pt2x,pt2y)
			#if pt <= 10:
			if newline:
				pt1x = pt2x
				pt1y = pt2y
				pol = 1
				newline = False
				
			else:
				dist = math.sqrt(((pt2x - pt1x)**2)+((pt2y - pt1y)**2))
				#if pt <= 10:
				if dist <= dmax: #part of same line
					point_list.append(qpt)
					pt1x = pt2x
					pt1y = pt2y
					pol = pol+1
				else:
					seg = QgsFeature()
					if point_list != None and (pol > 2):
						seg.setGeometry(QgsGeometry.fromPolyline(point_list))
						outfile.addFeatures( [ seg ] )
						outfile.updateExtents()
					newline = True
					pt1x = pt2x
					pt1y = pt2y
					point_list = []
		del outfile
		#QgsMapLayerRegistry.instance().addMapLayers([v_layer])
		self.iface.addVectorLayer(savename, os.path.basename(savename), "ogr")
		#line_start = QgsPoint(x[0],y[0])
		#QMessageBox.information(self.iface.mainWindow(),"debug", "x1 = "+str(x[1])+", y0 = "+str(y[1]))
		#line_end = QgsPoint(x[1],y[1])
		#line = QgsGeometry.fromPolyline([line_start,line_end])
		# create a new memory layer
		#v_layer = QgsVectorLayer("LineString", "line", "memory")
		#pr = v_layer.dataProvider()
		# create a new feature
		#seg = QgsFeature()
		# add the geometry to the feature, 
		#seg.setGeometry(QgsGeometry.fromPolyline([line_start, line_end]))
		# ...it was here that you can add attributes, after having defined....
		# add the geometry to the layer
		#pr.addFeatures( [ seg ] )
		# update extent of the layer (not necessary)
		#v_layer.updateExtents()
		# show the line  
		#QgsMapLayerRegistry.instance().addMapLayers([v_layer])

# ----------------------------------------------------------
#    tuflowqgis configure tuflow project
# ----------------------------------------------------------
from ui_tuflowqgis_configure_tuflow_project import *		
from .tuflowqgis_settings import TF_Settings
from qgis.gui import QgsProjectionSelectionTreeWidget
class tuflowqgis_configure_tf_dialog(QDialog, Ui_tuflowqgis_configure_tf):
	def __init__(self, iface, project):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		#self.project = project
		cLayer = self.canvas.currentLayer()
		self.tfsettings = TF_Settings()
		self.crs = None
		fname = ''
		#message, tffolder, tfexe, tf_prj = load_project(self.project)
		#dont give error here as it may be the first occurence
		#if message != None:
		#	QMessageBox.critical( self.iface.mainWindow(),"Error", message)
		
		# load global tfsettings
		#QMessageBox.information( self.iface.mainWindow(),"debug", "loading gloabal settings")
		error, message = self.tfsettings.Load()
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", "Error Loading Global Settings: "+message)
		
		#set fields
		if self.tfsettings.project_settings.base_dir:
			self.outdir.setText(self.tfsettings.project_settings.base_dir)
		elif self.tfsettings.global_settings.base_dir:
			self.outdir.setText(self.tfsettings.global_settings.base_dir)
		else:
			self.outdir.setText("Not Yet Set")
		
		if self.tfsettings.project_settings.tf_exe:
			self.TUFLOW_exe.setText(self.tfsettings.project_settings.tf_exe)
		elif self.tfsettings.global_settings.tf_exe:
			self.TUFLOW_exe.setText(self.tfsettings.global_settings.tf_exe)
		else:
			self.TUFLOW_exe.setText("Not Yet Set")

		if self.tfsettings.project_settings.CRS_ID:
			self.form_crsID.setText(self.tfsettings.project_settings.CRS_ID)
			self.crs = QgsCoordinateReferenceSystem()
			success = self.crs.createFromString(self.tfsettings.project_settings.CRS_ID)
			if success:
				self.crsDesc.setText(self.crs.description())
		elif self.tfsettings.global_settings.CRS_ID:
			self.form_crsID.setText(self.tfsettings.global_settings.CRS_ID)
			self.crs = QgsCoordinateReferenceSystem()
			success = self.crs.createFromString(self.tfsettings.global_settings.CRS_ID)
			if success:
				self.crsDesc.setText(self.crs.description())
		else:
			#self.form_crsID.setText("Not Yet Set")
			if cLayer:
				cName = cLayer.name()
				self.crs = cLayer.crs()
				self.form_crsID.setText(self.crs.authid())
				self.crsDesc.setText(self.crs.description())
			else:
				self.crsDesc.setText("Please select CRS")
				self.form_crsID.setText("Please select CRS")
				self.crs = None

		if self.crs:
			self.sourcelayer.addItem("Use saved projection")
			cLayer = False
			self.sourcelayer.setCurrentIndex(0)
		
		#add vector data as options in dropbox
		i = 0
		for name, layer in QgsProject.instance().mapLayers().items():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if cLayer:
					if layer.name() == cName:
						self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if i == 0:
			self.sourcelayer.addItem("No Vector Data Open - use Set CRS Below")				
		

		#QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outdir)
		self.browseoutfile.clicked.connect(self.browse_outdir)
		#QObject.connect(self.browseexe, SIGNAL("clicked()"), self.browse_exe)
		self.browseexe.clicked.connect(self.browse_exe)
		#QObject.connect(self.pbSelectCRS, SIGNAL("clicked()"), self.select_CRS)
		self.pbSelectCRS.clicked.connect(self.select_CRS)
		#QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.layer_changed)
		self.sourcelayer.currentIndexChanged[int].connect(self.layer_changed)
		#QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)
		self.buttonBox.accepted.connect(self.run)


			#QMessageBox.critical(self.iface.mainWindow(), "Setting Projection", "No vector data open, a shapefile is required for setting the model projection. \nPlease open or create a file in the desired projection.")


	def browse_outdir(self):
		#newname = QFileDialog.getExistingDirectory(None, QString.fromLocal8Bit("Output Directory"))
		newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		if newname != None:
			#self.outdir.setText(QString(newname))
			self.outdir.setText(newname)
	
	def select_CRS(self):
		projSelector = QgsProjectionSelectionWidget()
		projSelector.selectCrs()
		try:
			authid = projSelector.crs().authid()
			description = projSelector.crs().description()
			self.crs = projSelector.crs()
			success = projSelector.crs()
			if not success:
				self.crs = None
			else:
				self.crsDesc.setText(description)
				self.form_crsID.setText(authid)
		except:
			self.crs = None
	def browse_exe(self):
	
		#get last used dir
		last_exe = self.tfsettings.get_last_exe()			
		if last_exe:
			last_dir, tail = os.path.split(last_exe)
		else:
			last_dir = ''
			
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW exe', last_dir, "TUFLOW Executable (*.exe)")
		inFileName = inFileName[0]
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.TUFLOW_exe.setText(inFileName)
		self.tfsettings.save_last_exe(inFileName)

	def layer_changed(self):
		layername = unicode(self.sourcelayer.currentText()) 
		if layername != "Use saved projection":
			layer = tuflowqgis_find_layer(layername)
			if layer != None:
				self.crs = layer.crs()
				self.form_crsID.setText(self.crs.authid())
				self.crsDesc.setText(self.crs.description())
	def run(self):
		tf_prj = unicode(self.form_crsID.displayText()).strip()
		basedir = unicode(self.outdir.displayText()).strip()
		tfexe = unicode(self.TUFLOW_exe.displayText()).strip()
		
		#Save Project Settings
		self.tfsettings.project_settings.CRS_ID = tf_prj
		self.tfsettings.project_settings.tf_exe = tfexe
		self.tfsettings.project_settings.base_dir = basedir
		error, message = self.tfsettings.Save_Project()
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", "Error Saving Project Settings. Message: "+message)
		else:
			QMessageBox.information( self.iface.mainWindow(),"Information", "Project Settings Saved")
		
		#Save Global Settings
		if (self.cbGlobal.isChecked()):
			self.tfsettings.global_settings.CRS_ID = tf_prj
			self.tfsettings.global_settings.tf_exe = tfexe
			self.tfsettings.global_settings.base_dir = basedir
			error, message = self.tfsettings.Save_Global()
			if error:
				QMessageBox.information( self.iface.mainWindow(),"Error", "Error Saving Global Settings. Message: "+message)
			else:
				QMessageBox.information( self.iface.mainWindow(),"Information", "Global Settings Saved")
		
		if (self.cbCreate.isChecked()):
			crs = QgsCoordinateReferenceSystem()
			crs.createFromString(tf_prj)
	
			#QMessageBox.information( self.iface.mainWindow(),"Creating TUFLOW directory", basedir)
			message = tuflowqgis_create_tf_dir(self.iface, crs, basedir)
			if message != None:
				QMessageBox.critical(self.iface.mainWindow(), "Creating TUFLOW Directory ", message)
		
		if (self.cbRun.isChecked()):
				#tcf = os.path.join(basedir+"\\TUFLOW\\runs\\Create_Empties.tcf")
				tcf = os.path.join(basedir,"TUFLOW","runs","Create_Empties.tcf")
				QMessageBox.information(self.iface.mainWindow(), "Running TUFLOW","Starting simulation: "+tcf+"\n Executable: "+tfexe)
				message = run_tuflow(self.iface, tfexe, tcf)
				if message != None:
					QMessageBox.critical(self.iface.mainWindow(), "Running TUFLOW ", message)
			
			
# ----------------------------------------------------------
#    tuflowqgis splitMI into shapefiles
# ----------------------------------------------------------
from ui_tuflowqgis_splitMI import *
from .splitMI_mod import *
class tuflowqgis_splitMI_dialog(QDialog, Ui_tuflowqgis_splitMI):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		cLayer = self.canvas.currentLayer()
		fname = ''
		cName = 'not defined'
		fpath = None
		
	#	if cLayer:
	#		cName = cLayer.name()
	#		dp = cLayer.dataProvider()
	#		ds = dp.dataSourceUri()
	#		try:
	#			fpath, fname = os.path.split(unicode(ds))
	#			ind = fname.find('|')
	#			if (ind>0):
	#				fname = fname[0:ind]
	#			fext, fname_noext, message = get_file_ext(fname)
	#		except:
	#			fpath = None
	#			fname = ''

		#QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outdir)
		self.browseoutfile.clicked.connect(self.browse_outdir)
		#QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
		self.buttonBox.accepted.connect(self.run)
		#QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.layer_changed)
		self.sourcelayer.currentIndexChanged[int].connect(self.layer_changed)
		i = 0
		for name, layer in QgsProject.instance().mapLayers().items():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if layer.name() == cName:
					self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if cLayer == None:
			self.sourcelayer.setCurrentIndex(0)
		
		layername = unicode(self.sourcelayer.currentText()) 
		if layername != "Undefined":
			layer = tuflowqgis_find_layer(layername)
			if layer != None:
				dp = layer.dataProvider()
				ds = dp.dataSourceUri()
				try:
					fpath, fname = os.path.split(unicode(ds))
					ind = fname.find('|')
					if (ind>0):
						fname = fname[0:ind]
					fext, fname_noext, message = get_file_ext(fname)
				except:
					fpath = None
					fname = ''
				self.outfolder.setText(fpath)
				self.outprefix.setText(fname_noext)
		if (fpath):
			self.outfolder.setText(fpath)
			self.outprefix.setText(fname_noext)
		else:
			self.outfolder.setText('No layer currently open!')
			self.outprefix.setText('No layer currently open!')

	def browse_outdir(self):
		newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		if newname != None:
			self.outfolder.setText(newname)
	
	def layer_changed(self):
		layername = unicode(self.sourcelayer.currentText()) 
		if layername != "Undefined":
			layer = tuflowqgis_find_layer(layername)
			if layer != None:
				dp = layer.dataProvider()
				ds = dp.dataSourceUri()
				try:
					fpath, fname = os.path.split(unicode(ds))
					ind = fname.find('|')
					if (ind>0):
						fname = fname[0:ind]
					fext, fname_noext, message = get_file_ext(fname)
				except:
					fpath = None
					fname = ''
				self.outfolder.setText(fpath)
				self.outprefix.setText(fname_noext)
	def run(self):
		layername = unicode(self.sourcelayer.currentText())
		layer = tuflowqgis_find_layer(layername)
		fext = "unknown"
		if layer != None:
			dp = layer.dataProvider()
			ds = unicode(dp.dataSourceUri())
			ind = ds.find('|')
			if (ind>0):
				fname = ds[0:ind]
			else:
				fname = ds
			fext, fname_noext, message = get_file_ext(fname)
		else:
			QMessageBox.critical(self.iface.mainWindow(), "ERROR", "Layer name is blank, or unable to find layer")
		outfolder = unicode(self.outfolder.displayText()).strip()
		outprefix = unicode(self.outprefix.displayText()).strip()
		message, ptshp, lnshp, rgshp, npt, nln, nrg = split_MI_util(self.iface, fname, outfolder, outprefix)
		
		if message != None:
			QMessageBox.critical(self.iface.mainWindow(), "Error Splitting file", message)
		QgsProject.instance().removeMapLayer(layer.id())
		
# ----------------------------------------------------------
#    tuflowqgis flow trace
# ----------------------------------------------------------

# ----------------------------------------------------------
#    tuflowqgis splitMI into shapefiles
# ----------------------------------------------------------
from ui_tuflowqgis_splitMI_folder import *
from .tuflowqgis_settings import TF_Settings
from .splitMI_func import *
from .splitMI_mod2 import *
import os
import fnmatch

class tuflowqgis_splitMI_folder_dialog(QDialog, Ui_tuflowqgis_splitMI_folder):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.tfsettings = TF_Settings()
		self.last_mi = self.tfsettings.get_last_mi_folder()
		
		#QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outdir)
		self.browseoutfile.clicked.connect(self.browse_outdir)
		#QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
		self.buttonBox.accepted.connect(self.run)
		


	def browse_outdir(self):
		#newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		newname = QFileDialog.getExistingDirectory(None, "Output Directory",self.last_mi)
		if newname != None:
			self.outfolder.setText(newname)
			self.tfsettings.save_last_mi_folder(newname)
	
	def run(self):
		QMessageBox.information( self.iface.mainWindow(),"debug", "run" )
		folder = unicode(self.outfolder.displayText()).strip()
		QMessageBox.information( self.iface.mainWindow(),"debug", "Folder: \n"+folder)

		mif_files = []
		if self.cbRecursive.isChecked(): #look in subfolders:
			for root, dirnames, filenames in os.walk(folder):
				for filename in fnmatch.filter(filenames, '*.mif'):
					mif_files.append(os.path.join(root, filename))
		else: #only specified folder
			filenames = os.listdir(folder)
			for filename in fnmatch.filter(filenames, '*.mif'):
				mif_files.append(os.path.join(folder, filename))
		
		nF = len(mif_files)
		#QMessageBox.information( self.iface.mainWindow(),"debug", "Number of mif files = :"+str(nF))
		
		for mif_file in mif_files:
			message, fname_P, fname_L, fname_R, npts, nln, nrg = split_MI_util2(mif_file)
			
			if message != None:
				QMessageBox.information( self.iface.mainWindow(),"ERROR", message)
				QMessageBox.information( self.iface.mainWindow(),"point file", fname_P)
			else:
				QMessageBox.information( self.iface.mainWindow(),"ERROR", "Success")
		
# ----------------------------------------------------------
#    tuflowqgis flow trace
# ----------------------------------------------------------

from ui_tuflowqgis_flowtrace import *

class tuflowqgis_flowtrace_dialog(QDialog, Ui_tuflowqgis_flowtrace):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		self.cLayer = self.canvas.currentLayer()
		self.lw_Log.insertItem(0,'Creating Dialogue')
		
		if self.cLayer:
			cName = self.cLayer.name()
			self.lw_Log.insertItem(0,'Current Layer: '+cName)
			self.dp = self.cLayer.dataProvider()
			self.ds = self.dp.dataSourceUri()
		else:
			QMessageBox.information( self.iface.mainWindow(),"ERROR", "No layer selected.")
			#QDialog.close(self) #close dialogue
			#QDialog.accept()
			#sys.exit()
			#exit()
			#self.done(int(1))
			#self.reject()
			QDialog.done(self,0)
			

		#QObject.connect(self.pb_Run, SIGNAL("clicked()"), self.run_clicked)
		self.pb_Run.clicked.connect(self.run_clicked)
		#QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
		self.buttonBox.accept.connect(self.run)
#
	def run_clicked(self):
		#tolerance = 1.00
		try:
			dt_str = self.le_dt.displayText()
			dt = float(dt_str)
			self.lw_Log.insertItem(0,'Snap Tolerance: '+str(dt))
		except:
			QMessageBox.critical( self.iface.mainWindow(),"ERROR", "Unable to convert dt to number.  Line: "+dt_str)
		try:
			#self.cLayer = self.canvas.currentLayer()
			features = self.cLayer.selectedFeatures()
			self.lw_Log.insertItem(0,'Number of feaures selected: '+str(len(features)))
		except:
			QMessageBox.information( self.iface.mainWindow(),"ERROR", "Error getting selected features")
		
		#load all 1st and last node locations
		start_nd = []
		end_nd = []
		start_x = []
		end_x = []
		fid = []
		tf_selected = []
		self.lw_Log.insertItem(0,'Loading all start and end nodes')
		for f in self.cLayer.getFeatures():
			fid.append(f.id()) # list of fids
			tf_selected.append(False) #not selected by default
			nodes = f.geometry().asPolyline()
			start_nd.append(nodes[0])
			start_x.append(nodes[0][0])
			end_nd.append(nodes[-1])
			end_x.append(nodes[-1][0])
		self.lw_Log.insertItem(0,'Loaded all end vertex data. Total number of features loaded = '+str(len(fid)))
		
		#start doing stuff
		selection_list = []
		final_list = []
		tmp_selection = []
		self.lw_Log.insertItem(0,'Processing selected features...')
		for feature in features:
			self.lw_Log.insertItem(0,'FID: '+str(feature.id()))
			selection_list.append(feature.id())
			final_list.append(feature.id())
			tf_selected[feature.id()-1] = True
		self.lw_Log.insertItem(0,'Done')
		
		if self.cb_US.isChecked():
			tmp_selection = selection_list
			self.lw_Log.insertItem(0,'Beginning upstream search')	
			while tmp_selection:
				self.lw_Log.insertItem(0,'selected id: '+str(tmp_selection[0]))
				ind = fid.index(tmp_selection[0])
				self.lw_Log.insertItem(0,'index: '+str(ind))
				node = start_nd[ind]
				distance = QgsDistanceArea()
				for i, id in enumerate(fid):
					#self.lw_Log.insertItem(0,'id: '+str(id))
					if not tf_selected[i]:
						dist = distance.measureLine(node, end_nd[i])
						#self.lw_Log.insertItem(0,'dist = '+str(dist))	
						if dist < dt:
							self.lw_Log.insertItem(0,'Connected fid: '+str(id))	
							final_list.append(id)
							tmp_selection.append(id)
							tf_selected[i] = True
					
				tmp_selection.pop(0)
				
			self.lw_Log.insertItem(0,'Finished upstream search')

		if self.cb_DS.isChecked():
			for feature in features: #re-select original
				tmp_selection.append(feature.id())
			
			self.lw_Log.insertItem(0,'Beginning downstream search')	
			self.lw_Log.insertItem(0,'len tmp = '+str(len(tmp_selection)))
			self.lw_Log.insertItem(0,'len features = '+str(len(features)))
			while tmp_selection:
				self.lw_Log.insertItem(0,'selected id: '+str(tmp_selection[0]))
				ind = fid.index(tmp_selection[0])
				self.lw_Log.insertItem(0,'index: '+str(ind))
				node = end_nd[ind]
				distance = QgsDistanceArea()
				for i, id in enumerate(fid):
					#self.lw_Log.insertItem(0,'id: '+str(id))
					if not tf_selected[i]:
						dist = distance.measureLine(node, start_nd[i])
						#self.lw_Log.insertItem(0,'dist = '+str(dist))	
						if dist < dt:
							self.lw_Log.insertItem(0,'Connected fid: '+str(id))	
							final_list.append(id)
							tmp_selection.append(id)
							tf_selected[i] = True
					
				tmp_selection.pop(0)
			self.lw_Log.insertItem(0,'Finished downstream search')
		self.cLayer.setSelectedFeatures(final_list)	

	def run(self):
		#if self.cb_DS.isChecked():
		#	QMessageBox.information( self.iface.mainWindow(),"debug", "Downstream")
		#if self.cb_US.isChecked():
		#	QMessageBox.information( self.iface.mainWindow(),"debug", "Upstream")
		QMessageBox.information( self.iface.mainWindow(),"Information", "Use RUN button")
  
  
 # MJS added 11/02 
# ----------------------------------------------------------
#    tuflowqgis import check files
# ----------------------------------------------------------
from ui_tuflowqgis_import_check import *
from .tuflowqgis_settings import TF_Settings
class tuflowqgis_import_check_dialog(QDialog, Ui_tuflowqgis_import_check):
	def __init__(self, iface, project):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.tfsettings = TF_Settings()

		# load stored settings
		self.last_chk_folder = self.tfsettings.get_last_chk_folder()
		error, message = self.tfsettings.Load() #exe, tuflow dircetory and projection
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", "Error Loading Settings: "+message)

		#QObject.connect(self.browsedir, SIGNAL("clicked()"), self.browse_empty_dir)
		self.browsedir.clicked.connect(self.browse_empty_dir)
		#QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)
		self.buttonBox.accepted.connect(self.run)

		if (self.last_chk_folder == "Undefined"):
			if self.tfsettings.combined.base_dir:
				self.last_chk_folder = os.path.join(self.tfsettings.combined.base_dir,"TUFLOW","Check")
				self.emptydir.setText(self.last_chk_folder)
		#	self.emptydir.setText(self.tfsettings.combined.base_dir+"\\TUFLOW\\check")
		else:
			self.emptydir.setText(self.last_chk_folder)
		#self.emptydir.setText = self.tfsettings.get_last_mi_folder()

	def browse_empty_dir(self):
		newname = QFileDialog.getExistingDirectory(None, "Output Directory",self.last_chk_folder)
		if newname != None:
			try:
				self.emptydir.setText(newname)
				self.tfsettings.save_last_chk_folder(newname)
			except:
				self.emptydir.setText("Problem Saving Settings")


	def run(self):
		runID = unicode(self.txtRunID.displayText()).strip()
		basedir = unicode(self.emptydir.displayText()).strip()
		showchecks = self.showchecks.isChecked()


		# run create dir script
		#message = tuflowqgis_import_check_tf(self.iface, basedir, runID, empty_types, points, lines, regions)
		message = tuflowqgis_import_check_tf(self.iface, basedir, runID,showchecks)
		#message = tuflowqgis_create_tf_dir(self.iface, crs, basedir)
		if message != None:
			QMessageBox.critical(self.iface.mainWindow(), "Importing TUFLOW Empty File(s)", message)
			
# ----------------------------------------------------------
#    tuflowqgis extract ARR2016
# ----------------------------------------------------------
from ui_tuflowqgis_arr2016 import *
from .tuflowqgis_settings import TF_Settings
import webbrowser

class tuflowqgis_extract_arr2016_dialog(QDialog, Ui_tuflowqgis_arr2016):

	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		self.tfsettings = TF_Settings()
		
		# Set up Input Catchment File ComboBox
		for name, layer in QgsProject.instance().mapLayers().items():
				if layer.type() == QgsMapLayer.VectorLayer:
					if layer.geometryType() == 0 or layer.geometryType() == 2:
						self.comboBox_inputCatchment.addItem(layer.name())
							
		layerName = unicode(self.comboBox_inputCatchment.currentText())
		layer = tuflowqgis_find_layer(layerName)
						
		# Set up Catchment Field ID ComboBox
		if layer is not None:
			for f in layer.fields():
				#QMessageBox.information(self.iface.mainWindow(), "Debug", '{0}'.format(f.name()))
				self.comboBox_CatchID.addItem(f.name())
				
		# Set up Catchment Area Field ComboBox
		if self.radioButton_ARF_auto.isChecked():
			self.comboBox_CatchArea.setEnabled(False)
		else:
			self.comboBox_CatchArea.setEnabled(True)
			self.comboBox_CatchArea.addItem('-None-')
			if layer is not None:
				for f in layer.fields():
					self.comboBox_CatchArea.addItem(f.name())
					
		# Set up MAR and Static Value box
		self.mar_staticValue.setEnabled(False)
		
		self.commandLinkButton_BOMconditions.clicked.connect(self.open_BOMconditions)
		self.commandLinkButton_BOMcaveat.clicked.connect(self.open_BOMcaveat)
		self.comboBox_inputCatchment.currentIndexChanged.connect(self.catchmentLayer_changed)
		self.pushButton_browse.clicked.connect(self.browse_outFolder)
		self.checkBox_aepAll.clicked.connect(self.aep_all)
		self.checkBox_durAll.clicked.connect(self.dur_all)
		self.radioButton_ARF_auto.clicked.connect(self.toggle_comboBox_CatchArea)
		self.radioButton_ARF_manual.clicked.connect(self.toggle_comboBox_CatchArea)
		self.comboBox_ilMethod.currentIndexChanged.connect(self.ilMethod_changed)
		self.buttonBox.accepted.connect(self.run)
	
	def open_BOMconditions(self):
		webbrowser.open(r'http://www.bom.gov.au/other/disclaimer.shtml')
		
	def open_BOMcaveat(self):
		webbrowser.open(r'http://www.bom.gov.au/water/designRainfalls/revised-ifd/?content=caveat')
	
	def catchmentLayer_changed(self):
		layerName = unicode(self.comboBox_inputCatchment.currentText())
		layer = tuflowqgis_find_layer(layerName)
		
		# Set up Catchment Field ID ComboBox
		self.comboBox_CatchID.clear()
		if layer is not None:
			for f in layer.fields():
				self.comboBox_CatchID.addItem(f.name())
		
		# Set up Catchment Area Field ComboBox
		if self.radioButton_ARF_auto.isChecked():
			self.comboBox_CatchArea.setEnabled(False)
		else:
			self.comboBox_CatchArea.setEnabled(True)
			self.comboBox_CatchArea.clear()
			self.comboBox_CatchArea.addItem('-None-')
			if layer is not None:
				for f in layer.pendingFields():
					self.comboBox_CatchArea.addItem(f.name())
				
	def browse_outFolder(self):
		self.last_arr_outFolder = self.tfsettings.get_last_arr_outFolder()
		new_outFolder = QFileDialog.getExistingDirectory(None, "Output Directory", self.last_arr_outFolder)
		if new_outFolder != None:
			try:
				self.outfolder.setText(new_outFolder)
				self.tfsettings.save_last_arr_outFolder(new_outFolder)
			except:
				self.outfolder.setText("Problem Saving Settings")
				
	def toggle_comboBox_CatchArea(self):
		layerName = unicode(self.comboBox_inputCatchment.currentText())
		layer = tuflowqgis_find_layer(layerName)
		
		if self.radioButton_ARF_auto.isChecked():
			self.comboBox_CatchArea.setEnabled(False)
		else:
			self.comboBox_CatchArea.setEnabled(True)
			self.comboBox_CatchArea.clear()
			self.comboBox_CatchArea.addItem('-None-')
			if layer is not None:
				for f in layer.pendingFields():
					self.comboBox_CatchArea.addItem(f.name())
					
	def ilMethod_changed(self):
		ilMethod = unicode(self.comboBox_ilMethod.currentText())
		
		if ilMethod == 'Hill et al 1996: 1998' or ilMethod == 'Static Value':
			self.mar_staticValue.setEnabled(True)
		else:
			self.mar_staticValue.setEnabled(False)
				
	def run(self):
		# Check BOM Conditions of Use and Conditions Caveat have been ticked
		if not self.checkBox_BOMconditions.isChecked() or not self.checkBox_BOMcaveat.isChecked():
			QMessageBox.critical(self.iface.mainWindow(),"ERROR", 
								 "Must accept BOM Conditions of Use and Conditions Caveat before you can continue.")
			return
		
		# Check vector layer has been specified
		layerName = unicode(self.comboBox_inputCatchment.currentText())
		layer = tuflowqgis_find_layer(layerName)
		if layer is None:
			QMessageBox.critical(self.iface.mainWindow(),"ERROR", "Must select a layer.")
			return
		
		# get AEPs
		rare_events = 'false'
		frequent_events = 'false'
		AEP_list = ''
		if self.checkBox_1p.isChecked():
			AEP_list += '1AEP '
		if self.checkBox_2p.isChecked():
			AEP_list += '2AEP '
		if self.checkBox_5p.isChecked():
			AEP_list += '5AEP '
		if self.checkBox_10p.isChecked():
			AEP_list += '10AEP '
		if self.checkBox_20p.isChecked():
			AEP_list += '20AEP '
		if self.checkBox_50p.isChecked():
			AEP_list += '50AEP '
		if self.checkBox_63p.isChecked():
			AEP_list += '63.2AEP '
		if self.checkBox_200y.isChecked():
			AEP_list += '200ARI '
			rare_events = 'true'
		if self.checkBox_500y.isChecked():
			AEP_list += '500ARI '
			rare_events = 'true'
		if self.checkBox_1000y.isChecked():
			AEP_list += '1000ARI '
			rare_events = 'true'
		if self.checkBox_2000y.isChecked():
			AEP_list += '2000ARI '
			rare_events = 'true'
		if self.checkBox_12ey.isChecked():
			AEP_list += '12EY '
			frequent_events = 'true'
		if self.checkBox_6ey.isChecked():
			AEP_list += '6EY '
			frequent_events = 'true'
		if self.checkBox_4ey.isChecked():
			AEP_list += '4EY '
			frequent_events = 'true'
		if self.checkBox_3ey.isChecked():
			AEP_list += '3EY '
			frequent_events = 'true'
		if self.checkBox_2ey.isChecked():
			AEP_list += '2EY '
			frequent_events = 'true'
		if self.checkBox_05ey.isChecked():
			AEP_list += '0.5EY '
			frequent_events = 'true'
		if self.checkBox_02ey.isChecked():
			AEP_list += '0.2EY '
			frequent_events = 'true'
		if len(AEP_list) < 1:
			QMessageBox.critical(self.iface.mainWindow(),"ERROR", "Must select at least one AEP.")
			return
		
		# get durations
		dur_list = 'none'
		nonstnd_list = 'none'
		if self.checkBox_10m.isChecked():
			dur_list += '10m '
		if self.checkBox_15m.isChecked():
			dur_list += '15m '
		if self.checkBox_20m.isChecked():
			nonstnd_list += '20m '
		if self.checkBox_25m.isChecked():
			nonstnd_list += '25m '
		if self.checkBox_30m.isChecked():
			dur_list += '30m '
		if self.checkBox_45m.isChecked():
			nonstnd_list += '45m '
		if self.checkBox_60m.isChecked():
			dur_list += '60m '
		if self.checkBox_90m.isChecked():
			nonstnd_list += '90m '
		if self.checkBox_120m.isChecked():
			dur_list += '2h '
		if self.checkBox_180m.isChecked():
			dur_list += '3h '
		if self.checkBox_270m.isChecked():
			nonstnd_list += '270m '
		if self.checkBox_6h.isChecked():
			dur_list += '6h '
		if self.checkBox_9h.isChecked():
			nonstnd_list += '9h '
		if self.checkBox_12h.isChecked():
			dur_list += '12h '
		if self.checkBox_18h.isChecked():
			nonstnd_list += '18h '
		if self.checkBox_24h.isChecked():
			dur_list += '24h '
		if self.checkBox_30h.isChecked():
			nonstnd_list += '30h '
		if self.checkBox_36h.isChecked():
			nonstnd_list += '36h '
		if self.checkBox_48h.isChecked():
			dur_list += '48h '
		if self.checkBox_72h.isChecked():
			dur_list += '72h '
		if self.checkBox_96h.isChecked():
			dur_list += '96h '
		if self.checkBox_120h.isChecked():
			dur_list += '120h '
		if self.checkBox_144h.isChecked():
			dur_list += '144h '
		if self.checkBox_168h.isChecked():
			dur_list += '168h '
		if len(dur_list) > 4 or len(nonstnd_list) > 4:
			if len(dur_list) > 4:
				dur_list = dur_list[4:]
			if len(nonstnd_list) > 4:
				nonstnd_list = nonstnd_list[4:]
		else:
			QMessageBox.critical(self.iface.mainWindow(),"ERROR", "Must select at least one duration.")
			return
		
		# get climate change parameters
		cc_years = 'none'
		cc_rcp = 'none'
		cc = 'false'
		if self.checkBox_2030.isChecked():
			cc_years += '2030 '
		if self.checkBox_2040.isChecked():
			cc_years += '2040 '
		if self.checkBox_2050.isChecked():
			cc_years += '2050 '
		if self.checkBox_2060.isChecked():
			cc_years += '2060 '
		if self.checkBox_2070.isChecked():
			cc_years += '2070 '
		if self.checkBox_2080.isChecked():
			cc_years += '2080 '
		if self.checkBox_2090.isChecked():
			cc_years += '2090 '
		if self.checkBox_45rcp.isChecked():
			cc_rcp += '4.5 '
		if self.checkBox_6rcp.isChecked():
			cc_rcp += '6 '
		if self.checkBox_85rcp.isChecked():
			cc_rcp += '8.5 '
		if len(cc_years) > 4 and len(cc_rcp) > 4:
			cc = 'true'
			cc_years = cc_years[4:]
			cc_rcp = cc_rcp[4:]
		elif len(cc_years) > 4:
			QMessageBox.critical(self.iface.mainWindow(),"ERROR", 
								 "Must select at least one RCP when opting for Climate Change.")
			return
		elif len(cc_rcp) > 4:
			QMessageBox.critical(self.iface.mainWindow(),"ERROR", 
								 "Must select at least one Year when opting for Climate Change.")
			return
		
		# Get format
		format = unicode(self.comboBox_outputF.currentText())
		
		# Get output notation
		output_notation = unicode(self.comboBox_outputN.currentText())
		
		# Get output folder
		outFolder = unicode(self.outfolder.displayText()).strip()
		if not os.path.exists(outFolder):  # check output directory exists
			os.mkdir(outFolder)
			
		# Get preburst percentile
		preburst = unicode(self.comboBox_preBurstptile.currentText())
		if preburst == 'Median':
			preburst = '50%'
			
		# Get IL method < 60min
		mar = '0'
		staticValue = '0'
		
		ilMethod = unicode(self.comboBox_ilMethod.currentText())
		if ilMethod == 'Interpolate to zero':
			ilMethod = 'interpolate'
		elif ilMethod == 'Rahman et al 2002':
			ilMethod = 'rahman'
		elif ilMethod == 'Hill et al 1996: 1998':
			ilMethod = 'hill'
			mar = unicode(self.mar_staticValue.displayText())
			if mar == '':
				QMessageBox.critical(self.iface.mainWindow(),"ERROR", "Mean Annual Rainfall (MAR) must be specified for Hill et al loss method and must be greater than 0")
			if float(mar) <= 0:
				QMessageBox.critical(self.iface.mainWindow(),"ERROR", "Mean Annual Rainfall (MAR) must be specified for Hill et al loss method and must be greater than 0")
		elif ilMethod == 'Static Value':
			ilMethod = 'static'
			staticValue = unicode(self.mar_staticValue.displayText())
			if staticValue == '':
				QMessageBox.critical(self.iface.mainWindow(),"ERROR", "A value must be specified when using the Static Loss Method")
			if float(staticValue) < 0:
				QMessageBox.critical(self.iface.mainWindow(),"ERROR", "Static Loss value must be greater than 0")
		elif ilMethod == 'Use 60min Losses':
			ilMethod = '60min'
			
		# Get additional Temporal Patterns
		addTp = []
		
		for x in range(self.listWidget_tpRegions.count()):
			list_item = self.listWidget_tpRegions.item(x)
			if list_item.isSelected():
				addTp.append(list_item.text())
		
		if len(addTp) > 0:
			addTp = ','.join(addTp)
		else:
			addTp = 'false'
			
		# Get Minimum ARF Value
		minArf = self.minArf.displayText()
		if float(minArf) < 0:
			QMessageBox.critical(self.iface.mainWindow(),"ERROR", "Minimum ARF Value cannot be negative")
		
		# Get area and ID from input layer
		idField = unicode(self.comboBox_CatchID.currentText())
		area_list = []
		name_list = []
		for feature in layer.getFeatures():
			area_list.append(str(feature.geometry().area() / 1000000))
			name_list.append(str(feature[idField]))
		
		areaField = unicode(self.comboBox_CatchArea.currentText())
		if not self.radioButton_ARF_auto.isChecked():
			if areaField == '-None-':
				area_list = ['0'] * len(name_list)
			else:
				area_list = []
				for feature in layer.getFeatures():
					try:
						a = float(feature[areaField])
					except:
						QMessageBox.critical(self.iface.mainWindow(),"ERROR", 
								 "Area Field must contain numbers only.")
						return
					area_list.append(str(a))
		
		# Convert layer to long/lat and get centroid
		temp_shp = os.path.join(outFolder, '_reproject.shp')
		parameters = {'INPUT': layer, 'TARGET_CRS': 'epsg:4203', 'OUTPUT': temp_shp}
		reproject = processing.run("qgis:reprojectlayer", parameters)
		#reproject = processing.run("qgis:reprojectlayer", layer, "epsg:4203", None)
		reproject_layer = QgsVectorLayer(reproject['OUTPUT'], 'reproject_layer', 'ogr')
		centroid_list = []
		for feature in reproject_layer.getFeatures():
			centroid = []
			centroid.append('{0:.4f}'.format(feature.geometry().centroid().asPoint()[0]))
			centroid.append('{0:.4f}'.format(feature.geometry().centroid().asPoint()[1]))
			centroid_list.append(centroid)
		del reproject
		del reproject_layer
		QgsVectorFileWriter.deleteShapeFile(temp_shp)
		
		script = os.path.join(currentFolder, 'ARR2016', 'ARR_to_TUFLOW.py')
		QMessageBox.information(self.iface.mainWindow(), "information", 
							   'Starting ARR2016 to TUFLOW. Depending on how many catchments are being input, this can take a few minutes.\n\nA window will appear once finished.')
		for i in range(len(name_list)):
			sys_args = ['python3', script, '-out', outFolder, '-name', name_list[i], 
						'-coords', centroid_list[i][0], centroid_list[i][1], '-mag', AEP_list, 
						'-frequent', frequent_events, '-rare', rare_events, '-dur', dur_list, '-nonstnd', nonstnd_list,
						'-area', area_list[i], '-cc', cc, '-year', cc_years, '-rcp', cc_rcp, '-format', format, 
						'-catchment_no', str(i), '-output_notation', output_notation, '-preburst', preburst, 
						'-lossmethod', ilMethod, '-mar', mar, '-lossvalue', staticValue, '-minarf', minArf,
						'-addtp', addTp]
			if i == 0:
				logfile = open(os.path.join(outFolder, 'log.txt'), 'wb')
			else:
				logfile = open(os.path.join(outFolder, 'log.txt'), 'ab')
			CREATE_NO_WINDOW = 0x08000000 # suppresses python console window
			error = False
			try:
				proc = subprocess.Popen(sys_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
				                        creationflags=CREATE_NO_WINDOW)
				out, err = proc.communicate()
				logfile.write(out)
				logfile.write(err)
				logfile.close()
			except:
				try:
					proc = subprocess.Popen(sys_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
					out, err = proc.communicate()
					logfile.write(out)
					logfile.write(err)
					logfile.close()
				except:
					proc = subprocess.Popen(sys_args)
					error = True
					logfile.close()
		if error:
			QMessageBox.information(self.iface.mainWindow(), "Error", 'Process Complete. Error writing log file.')
		else:
			QMessageBox.information(self.iface.mainWindow(), "Message",
			                        'Process Complete. Please see\n{0}\nfor warning and error messages.' \
			                        .format(os.path.join(outFolder, 'log.txt')))
		
		return

	def aep_all(self):
		if self.checkBox_aepAll.isChecked():
			self.checkBox_1p.setChecked(True)
			self.checkBox_2p.setChecked(True)
			self.checkBox_5p.setChecked(True)
			self.checkBox_10p.setChecked(True)
			self.checkBox_20p.setChecked(True)
			self.checkBox_50p.setChecked(True)
			self.checkBox_63p.setChecked(True)
			self.checkBox_200y.setChecked(True)
			self.checkBox_500y.setChecked(True)
			self.checkBox_1000y.setChecked(True)
			self.checkBox_2000y.setChecked(True)
			self.checkBox_12ey.setChecked(True)
			self.checkBox_6ey.setChecked(True)
			self.checkBox_4ey.setChecked(True)
			self.checkBox_3ey.setChecked(True)
			self.checkBox_2ey.setChecked(True)
			self.checkBox_05ey.setChecked(True)
			self.checkBox_02ey.setChecked(True)
		else:
			self.checkBox_1p.setChecked(False)
			self.checkBox_2p.setChecked(False)
			self.checkBox_5p.setChecked(False)
			self.checkBox_10p.setChecked(False)
			self.checkBox_20p.setChecked(False)
			self.checkBox_50p.setChecked(False)
			self.checkBox_63p.setChecked(False)
			self.checkBox_200y.setChecked(False)
			self.checkBox_500y.setChecked(False)
			self.checkBox_1000y.setChecked(False)
			self.checkBox_2000y.setChecked(False)
			self.checkBox_12ey.setChecked(False)
			self.checkBox_6ey.setChecked(False)
			self.checkBox_4ey.setChecked(False)
			self.checkBox_3ey.setChecked(False)
			self.checkBox_2ey.setChecked(False)
			self.checkBox_05ey.setChecked(False)
			self.checkBox_02ey.setChecked(False)
			
	def dur_all(self):
		if self.checkBox_durAll.isChecked():
			self.checkBox_10m.setChecked(True)
			self.checkBox_15m.setChecked(True)
			self.checkBox_20m.setChecked(True)
			self.checkBox_25m.setChecked(True)
			self.checkBox_30m.setChecked(True)
			self.checkBox_45m.setChecked(True)
			self.checkBox_60m.setChecked(True)
			self.checkBox_90m.setChecked(True)
			self.checkBox_120m.setChecked(True)
			self.checkBox_180m.setChecked(True)
			self.checkBox_270m.setChecked(True)
			self.checkBox_6h.setChecked(True)
			self.checkBox_9h.setChecked(True)
			self.checkBox_12h.setChecked(True)
			self.checkBox_18h.setChecked(True)
			self.checkBox_24h.setChecked(True)
			self.checkBox_30h.setChecked(True)
			self.checkBox_36h.setChecked(True)
			self.checkBox_48h.setChecked(True)
			self.checkBox_72h.setChecked(True)
			self.checkBox_96h.setChecked(True)
			self.checkBox_120h.setChecked(True)
			self.checkBox_144h.setChecked(True)
			self.checkBox_168h.setChecked(True)
		else:
			self.checkBox_10m.setChecked(False)
			self.checkBox_15m.setChecked(False)
			self.checkBox_20m.setChecked(False)
			self.checkBox_25m.setChecked(False)
			self.checkBox_30m.setChecked(False)
			self.checkBox_45m.setChecked(False)
			self.checkBox_60m.setChecked(False)
			self.checkBox_90m.setChecked(False)
			self.checkBox_120m.setChecked(False)
			self.checkBox_180m.setChecked(False)
			self.checkBox_270m.setChecked(False)
			self.checkBox_6h.setChecked(False)
			self.checkBox_9h.setChecked(False)
			self.checkBox_12h.setChecked(False)
			self.checkBox_18h.setChecked(False)
			self.checkBox_24h.setChecked(False)
			self.checkBox_30h.setChecked(False)
			self.checkBox_36h.setChecked(False)
			self.checkBox_48h.setChecked(False)
			self.checkBox_72h.setChecked(False)
			self.checkBox_96h.setChecked(False)
			self.checkBox_120h.setChecked(False)
			self.checkBox_144h.setChecked(False)
			self.checkBox_168h.setChecked(False)

# ----------------------------------------------------------
#    tuflowqgis insert tuflow attributes
# ----------------------------------------------------------
from ui_tuflowqgis_insert_tuflow_attributes import *
from .tuflowqgis_settings import TF_Settings

class tuflowqgis_insert_tuflow_attributes_dialog(QDialog, Ui_tuflowqgis_insert_tuflow_attributes):
	def __init__(self, iface, project):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.tfsettings = TF_Settings()
		
		# Set up Input Catchment File ComboBox
		for name, layer in QgsProject.instance().mapLayers().items():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.comboBox_inputLayer.addItem(layer.name())						
		
		# load stored settings
		error, message = self.tfsettings.Load()
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", "Error Loading Settings: "+message)			
			return
		
		# Get empty dir
		if self.tfsettings.combined.base_dir:
			self.emptydir.setText(os.path.join(self.tfsettings.combined.base_dir, "TUFLOW", "model", "gis", "empty"))
		else:
			self.emptydir.setText("ERROR - Project not loaded")
			
		# load empty types
		self.comboBox_tfType.clear()
		if self.emptydir.text() == "ERROR - Project not loaded":
			self.comboBox_tfType.addItem('No empty directory')
		elif not os.path.exists(self.emptydir.text()):
			self.comboBox_tfType.addItem('Empty directory not valid')
		else:
			search_string = '{0}{1}*.shp'.format(self.emptydir.text(), os.path.sep)
			files = glob.glob(search_string)
			empty_list = []
			for file in files:
				if len(file.split('_empty')) < 2:
					continue
				empty_type = os.path.basename(file.split('_empty')[0])
				if empty_type not in empty_list:
					empty_list.append(empty_type)
					self.comboBox_tfType.addItem(empty_type)
									
		self.browsedir.clicked.connect(lambda: self.browse_empty_dir(unicode(self.emptydir.displayText()).strip()))
		self.emptydir.editingFinished.connect(self.dirChanged)
		self.buttonBox.accepted.connect(self.run)


	def browse_empty_dir(self, oldName):
		startDir = None
		dir = self.emptydir.text()
		while dir:
			if os.path.exists(dir):
				startDir = dir
				break
			else:
				dir = os.path.dirname(dir)
		
		newname = QFileDialog.getExistingDirectory(None, "Output Directory", startDir)
		if len(newname) > 0:
			self.emptydir.setText(newname)
			
			# load empty types
			self.comboBox_tfType.clear()
			if self.emptydir.text() == "ERROR - Project not loaded":
				self.comboBox_tfType.addItem('No empty directory')
			elif not os.path.exists(self.emptydir.text()):
				self.comboBox_tfType.addItem('Empty directory not valid')
			else:
				search_string = '{0}{1}*.shp'.format(self.emptydir.text(), os.path.sep)
				files = glob.glob(search_string)
				empty_list = []
				for file in files:
					if len(file.split('_empty')) < 2:
						continue
					empty_type = os.path.basename(file.split('_empty')[0])
					if empty_type not in empty_list:
						empty_list.append(empty_type)
						self.comboBox_tfType.addItem(empty_type)
	
	def dirChanged(self):
		# load empty types
		self.comboBox_tfType.clear()
		if self.emptydir.text() == "ERROR - Project not loaded":
			self.comboBox_tfType.addItem('No empty directory')
		elif not os.path.exists(self.emptydir.text()):
			self.comboBox_tfType.addItem('Empty directory not valid')
		else:
			search_string = '{0}{1}*.shp'.format(self.emptydir.text(), os.path.sep)
			files = glob.glob(search_string)
			empty_list = []
			for file in files:
				if len(file.split('_empty')) < 2:
					continue
				empty_type = os.path.basename(file.split('_empty')[0])
				if empty_type not in empty_list:
					empty_list.append(empty_type)
					self.comboBox_tfType.addItem(empty_type)
	
	def run(self):
		runID = unicode(self.txtRunID.displayText()).strip()
		basedir = unicode(self.emptydir.displayText()).strip()
		template = unicode(self.comboBox_tfType.currentText())
		
		inputFile = unicode(self.comboBox_inputLayer.currentText())
		inputLayer = tuflowqgis_find_layer(inputFile)
		lenFields = len(inputLayer.fields())
		
		# run insert tuflow attributes script
		message = tuflowqgis_insert_tf_attributes(self.iface, inputLayer, basedir, runID, template, lenFields)
		if message is not None:
			QMessageBox.critical(self.iface.mainWindow(), "Importing TUFLOW Empty File(s)", message)


# ----------------------------------------------------------
#    tuflowqgis tuplot axis editor
# ----------------------------------------------------------
from ui_tuflowqgis_tuplotAxisEditor import *


class tuflowqgis_tuplotAxisEditor(QDialog, Ui_tuplotAxisEditor):
	def __init__(self, iface, xLim, yLim, xAuto, yAuto, xInc, yInc, axis2, x2Lim, y2Lim, x2Inc, y2Inc, x2Auto, y2Auto):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.xLim = xLim
		self.yLim = yLim
		self.xInc = xInc
		self.yInc = yInc
		self.x2Lim = x2Lim
		self.y2Lim = y2Lim
		self.x2Inc = x2Inc
		self.y2Inc = y2Inc
		
		
		# Set tabs enabled and secondary axis group boxes
		if axis2 is None:
			self.tabWidget.setTabEnabled(1, False)
		else:
			if axis2 == 'sharex':
				self.groupBox_2.setEnabled(False)
				self.yMin_sb_2.setValue(y2Lim[0])
				self.yMax_sb_2.setValue(y2Lim[1])
				self.yInc_sb_2.setValue(y2Inc)
			elif axis2 == 'sharey':
				self.groupBox.setEnabled(False)
				self.xMin_sb_2.setValue(x2Lim[0])
				self.xMax_sb_2.setValue(x2Lim[1])
				self.xInc_sb_2.setValue(x2Inc)
				
		# Set Radio Buttons
		if xAuto:
			self.xAxisAuto_rb.setChecked(True)
			self.xAxisCustom_rb.setChecked(False)
		else:
			self.xAxisAuto_rb.setChecked(False)
			self.xAxisCustom_rb.setChecked(True)
		if yAuto:
			self.yAxisAuto_rb.setChecked(True)
			self.yAxisCustom_rb.setChecked(False)
		else:
			self.yAxisAuto_rb.setChecked(False)
			self.yAxisCustom_rb.setChecked(True)
		if x2Auto:
			self.xAxisAuto_rb_2.setChecked(True)
			self.xAxisCustom_rb_2.setChecked(False)
		else:
			self.xAxisAuto_rb_2.setChecked(False)
			self.xAxisCustom_rb_2.setChecked(True)
		if y2Auto:
			self.yAxisAuto_rb_2.setChecked(True)
			self.yAxisCustom_rb_2.setChecked(False)
		else:
			self.yAxisAuto_rb_2.setChecked(False)
			self.yAxisCustom_rb_2.setChecked(True)
	
		# Assign Limit values to primary axis dialog box
		self.xMin_sb.setValue(xLim[0])
		self.xMax_sb.setValue(xLim[1])
		self.yMin_sb.setValue(yLim[0])
		self.yMax_sb.setValue(yLim[1])
		self.xInc_sb.setValue(xInc)
		self.yInc_sb.setValue(yInc)
		
		# Signals
		self.buttonBox.accepted.connect(self.run)
		self.buttonBox.rejected.connect(lambda: self.cancel(xAuto, yAuto, x2Auto, y2Auto))
		self.xMin_sb.valueChanged.connect(self.value_xChanged)
		self.xMax_sb.valueChanged.connect(self.value_xChanged)
		self.xInc_sb.valueChanged.connect(self.value_xChanged)
		self.yMin_sb.valueChanged.connect(self.value_yChanged)
		self.yMax_sb.valueChanged.connect(self.value_yChanged)
		self.yInc_sb.valueChanged.connect(self.value_yChanged)
		self.xMin_sb_2.valueChanged.connect(self.value_x2Changed)
		self.xMax_sb_2.valueChanged.connect(self.value_x2Changed)
		self.xInc_sb_2.valueChanged.connect(self.value_x2Changed)
		self.yMin_sb_2.valueChanged.connect(self.value_y2Changed)
		self.yMax_sb_2.valueChanged.connect(self.value_y2Changed)
		self.yInc_sb_2.valueChanged.connect(self.value_y2Changed)
		
		
	def value_xChanged(self):
		self.xAxisAuto_rb.setChecked(False)
		self.xAxisCustom_rb.setChecked(True)
		
		
	def value_yChanged(self):
		self.yAxisAuto_rb.setChecked(False)
		self.yAxisCustom_rb.setChecked(True)
		
		
	def value_x2Changed(self):
		self.xAxisAuto_rb_2.setChecked(False)
		self.xAxisCustom_rb_2.setChecked(True)
		
		
	def value_y2Changed(self):
		self.yAxisAuto_rb_2.setChecked(False)
		self.yAxisCustom_rb_2.setChecked(True)
	
	
	def run(self):
		if self.xAxisCustom_rb.isChecked():
			self.xLim = [self.xMin_sb.value(), self.xMax_sb.value()]
			self.xInc = self.xInc_sb.value()
		if self.yAxisCustom_rb.isChecked():
			self.yLim = [self.yMin_sb.value(), self.yMax_sb.value()]
			self.yInc = self.yInc_sb.value()
		if self.xAxisCustom_rb_2.isChecked():
			self.x2Lim = [self.xMin_sb_2.value(), self.xMax_sb_2.value()]
			self.x2Inc = self.xInc_sb_2.value()
		if self.yAxisCustom_rb_2.isChecked():
			self.y2Lim = [self.yMin_sb_2.value(), self.yMax_sb_2.value()]
			self.y2Inc = self.yInc_sb_2.value()
		return
	
	
	def cancel(self, xAuto, yAuto, x2Auto, y2Auto):
		# revert back to original values
		if xAuto:
			self.xAxisAuto_rb.setChecked(True)
			self.xAxisCustom_rb.setChecked(False)
		else:
			self.xAxisAuto_rb.setChecked(False)
			self.xAxisCustom_rb.setChecked(True)
		if yAuto:
			self.yAxisAuto_rb.setChecked(True)
			self.yAxisCustom_rb.setChecked(False)
		else:
			self.yAxisAuto_rb.setChecked(False)
			self.yAxisCustom_rb.setChecked(True)
		if x2Auto:
			self.xAxisAuto_rb_2.setChecked(True)
			self.xAxisCustom_rb_2.setChecked(False)
		else:
			self.xAxisAuto_rb_2.setChecked(False)
			self.xAxisCustom_rb_2.setChecked(True)
		if y2Auto:
			self.yAxisAuto_rb_2.setChecked(True)
			self.yAxisCustom_rb_2.setChecked(False)
		else:
			self.yAxisAuto_rb_2.setChecked(False)
			self.yAxisCustom_rb_2.setChecked(True)


# ----------------------------------------------------------
#    tuflowqgis tuplot axis labels
# ----------------------------------------------------------
from ui_tuflowqgis_tuplotAxisLabels import *


class tuflowqgis_tuplotAxisLabels(QDialog, Ui_tuplotAxisLabel):
	def __init__(self, iface, xLabel, yLabel, xLabel2, yLabel2, title, xAxisAuto_cb, yAxisAuto_cb, xAxisAuto2_cb,
	             yAxisAuto2_cb):
		QDialog.__init__(self)
		self.iface = iface
		self.xLabel = xLabel
		self.yLabel = yLabel
		self.xLabel2 = xLabel2
		self.yLabel2 = yLabel2
		self.title = title
		self.setupUi(self)
		# Setup Axis 1 defaults
		self.chartTitle.setText(self.title)
		self.xAxisLabel.setText(self.xLabel)
		self.yAxisLabel.setText(self.yLabel)
		if xAxisAuto_cb:
			self.xAxisAuto_cb.setChecked(True)
		else:
			self.xAxisAuto_cb.setChecked(False)
		if yAxisAuto_cb:
			self.yAxisAuto_cb.setChecked(True)
		else:
			self.yAxisAuto_cb.setChecked(False)
		# Setup Axis 2 defaults
		if self.xLabel2 is not None:
			self.xAxisAuto2_cb.setEnabled(True)
			self.xAxisLabel2.setEnabled(True)
			self.xAxisLabel2.setText(self.xLabel2)
			if xAxisAuto2_cb:
				self.xAxisAuto2_cb.setChecked(True)
			else:
				self.xAxisAuto2_cb.setChecked(False)
		else:
			self.xAxisAuto2_cb.setEnabled(False)
			self.xAxisLabel2.setEnabled(False)
		if self.yLabel2 is not None:
			self.yAxisAuto2_cb.setEnabled(True)
			self.yAxisLabel2.setEnabled(True)
			self.yAxisLabel2.setText(self.yLabel2)
			if yAxisAuto2_cb:
				self.yAxisAuto2_cb.setChecked(True)
			else:
				self.yAxisAuto2_cb.setChecked(False)
		else:
			self.yAxisAuto2_cb.setEnabled(False)
			self.yAxisLabel2.setEnabled(False)
		# Signals
		self.buttonBox.rejected.connect(lambda: self.cancel(xAxisAuto_cb, yAxisAuto_cb, xAxisAuto2_cb, yAxisAuto2_cb))
		self.buttonBox.accepted.connect(self.run)
		self.xAxisLabel.textChanged.connect(lambda: self.auto_label(self.xAxisAuto_cb))
		self.yAxisLabel.textChanged.connect(lambda: self.auto_label(self.yAxisAuto_cb))
		self.xAxisLabel2.textChanged.connect(lambda: self.auto_label(self.xAxisAuto2_cb))
		self.yAxisLabel2.textChanged.connect(lambda: self.auto_label(self.yAxisAuto2_cb))
	
	
	def auto_label(self, cb):
		cb.setChecked(True)
	
	def run(self):
		self.xLabel = self.xAxisLabel.text()
		self.yLabel = self.yAxisLabel.text()
		self.xLabel2 = self.xAxisLabel2.text()
		self.yLabel2 = self.yAxisLabel2.text()
		self.title = self.chartTitle.text()
	
	def cancel(self, xAxisAuto_cb, yAxisAuto_cb, xAxisAuto2_cb, yAxisAuto2_cb):
		if xAxisAuto_cb:
			self.xAxisAuto_cb.setChecked(True)
		else:
			self.xAxisAuto_cb.setChecked(False)
		if yAxisAuto_cb:
			self.yAxisAuto_cb.setChecked(True)
		else:
			self.yAxisAuto_cb.setChecked(False)
		if xAxisAuto2_cb:
			self.xAxisAuto2_cb.setChecked(True)
		else:
			self.xAxisAuto2_cb.setChecked(False)
		if yAxisAuto2_cb:
			self.yAxisAuto2_cb.setChecked(True)
		else:
			self.yAxisAuto2_cb.setChecked(False)


# ----------------------------------------------------------
#    tuflowqgis scenario selection
# ----------------------------------------------------------
from ui_tuflowqgis_scenarioSelection import *


class tuflowqgis_scenarioSelection_dialog(QDialog, Ui_scenarioSelection):
	def __init__(self, iface, tcf, scenarios):
		QDialog.__init__(self)
		self.iface = iface
		self.tcf = tcf
		self.scenarios = scenarios
		self.setupUi(self)
		
		for scenario in self.scenarios:
			self.scenario_lw.addItem(scenario)
		
		self.ok_button.clicked.connect(self.run)
		self.cancel_button.clicked.connect(self.cancel)
		self.selectAll_button.clicked.connect(self.selectAll)
	
	def cancel(self):
		self.reject()
	
	def selectAll(self):
		for i in range(self.scenario_lw.count()):
			item = self.scenario_lw.item(i)
			item.setSelected(True)
	
	def run(self):
		self.scenarios = []
		for i in range(self.scenario_lw.count()):
			item = self.scenario_lw.item(i)
			if item.isSelected():
				self.scenarios.append(item.text())
		self.accept()  # destroy dialog window


# ----------------------------------------------------------
#    tuflowqgis event selection
# ----------------------------------------------------------
from ui_tuflowqgis_eventSelection import *


class tuflowqgis_eventSelection_dialog(QDialog, Ui_eventSelection):
	def __init__(self, iface, tcf, events):
		QDialog.__init__(self)
		self.iface = iface
		self.tcf = tcf
		self.events = events
		self.setupUi(self)
		
		for event in self.events:
			self.events_lw.addItem(event)
		
		self.ok_button.clicked.connect(self.run)
		self.cancel_button.clicked.connect(self.cancel)
		self.selectAll_button.clicked.connect(self.selectAll)
	
	def cancel(self):
		self.reject()
	
	def selectAll(self):
		for i in range(self.events_lw.count()):
			item = self.events_lw.item(i)
			item.setSelected(True)
	
	def run(self):
		self.events = []
		for i in range(self.events_lw.count()):
			item = self.events_lw.item(i)
			if item.isSelected():
				self.events.append(item.text())
		self.accept()  # destroy dialog window


# ----------------------------------------------------------
#    tuflowqgis mesh selection
# ----------------------------------------------------------
from ui_tuflowqgis_meshSelection import *


class tuflowqgis_meshSelection_dialog(QDialog, Ui_meshSelection):
	def __init__(self, iface, meshes):
		QDialog.__init__(self)
		self.setupUi(self)
		self.iface = iface
		self.meshes = meshes
		self.selectedMesh = None
		
		for mesh in self.meshes:
			self.mesh_lw.addItem(mesh.name())
		
		self.ok_button.clicked.connect(self.run)
		self.cancel_button.clicked.connect(self.cancel)
	
	def cancel(self):
		self.reject()

	def run(self):
		selection = self.mesh_lw.selectedItems()
		if selection:
			self.selectedMesh = selection[0].text()
			self.accept()  # destroy dialog window
		else:
			QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'Please select a result layer to save style.')
		

# ----------------------------------------------------------
#    tuView Options Dialog
# ----------------------------------------------------------
from ui_tuflowqgis_TuOptionsDialog import *


class TuOptionsDialog(QDialog, Ui_TuViewOptions):
	def __init__(self, TuOptions):
		QDialog.__init__(self)
		self.setupUi(self)
		self.tuOptions = TuOptions
		
		# mesh rendering
		if self.tuOptions.showGrid:
			self.cbShowGrid.setChecked(True)
		else:
			self.cbShowGrid.setChecked(False)
		if self.tuOptions.showTriangles:
			self.cbShowTriangles.setChecked(True)
		else:
			self.cbShowTriangles.setChecked(False)
		
		# plot live cursor tracking
		if self.tuOptions.liveMapTracking:
			self.rbLiveCursorTrackingOn.setChecked(True)
		else:
			self.rbLiveCursorTrackingOff.setChecked(True)
		
		# x axis dates
		self.cbDates.setChecked(self.tuOptions.xAxisDates)
		
		# zero date
		d = QDate(self.tuOptions.zeroTime.year, self.tuOptions.zeroTime.month, self.tuOptions.zeroTime.day)
		t = QTime(self.tuOptions.zeroTime.hour, self.tuOptions.zeroTime.minute, self.tuOptions.zeroTime.second)
		dt = QDateTime(d, t)
		self.dteZeroDate.setDateTime(dt)
		
		# date format
		self.leDateFormat.setText(convertStrftimToTuviewftim(self.tuOptions.dateFormat))
		
		# date format preview
		self.date = datetime.now()
		self.datePreview.setText(self.tuOptions._dateFormat.format(self.date))
		
		# x axis label rotation
		self.sbXAxisLabelRotation.setValue(self.tuOptions.xAxisLabelRotation)
			
		# play time delay
		self.sbPlaySpeed.setValue(self.tuOptions.playDelay)
		
		# cross section and flux line resolution
		self.sbResolution.setValue(self.tuOptions.resolution)
		
		# ARR mean event selection
		if self.tuOptions.meanEventSelection == 'next higher':
			self.rbARRNextHigher.setChecked(True)
		else:
			self.rbARRClosest.setChecked(True)
		
		# Signals
		self.leDateFormat.textChanged.connect(self.updatePreview)
		self.buttonBox.rejected.connect(self.cancel)
		self.buttonBox.accepted.connect(self.run)
		
	def updatePreview(self):
		self.tuOptions.dateFormat, self.tuOptions._dateFormat = convertTuviewftimToStrftim(self.leDateFormat.text())
		self.datePreview.setText(self.tuOptions._dateFormat.format(self.date))
		
	def legendOptionsChanged(self, checkBox):
		if self.rbLegendOn.isChecked():
			for position, cb in self.positionDict.items():
				cb.setEnabled(True)
				if checkBox is None:
					if position == self.legendPos:
						cb.setChecked(True)
					else:
						cb.setChecked(False)
				else:
					if cb == checkBox:
						self.legendPos = position
						cb.setChecked(True)
					else:
						cb.setChecked(False)
		else:
			for position, cb in self.positionDict.items():
				cb.setEnabled(False)
		
	def cancel(self):
		return
	
	def run(self):
		settings = QSettings()
		# mesh rendering
		if self.cbShowGrid.isChecked():
			self.tuOptions.showGrid = True
		else:
			self.tuOptions.showGrid = False
		if self.cbShowTriangles.isChecked():
			self.tuOptions.showTriangles = True
		else:
			self.tuOptions.showTriangles = False
		
		# plot live cursor tracking
		if self.rbLiveCursorTrackingOn.isChecked():
			self.tuOptions.liveMapTracking = True
		else:
			self.tuOptions.liveMapTracking = False
		
		# x axis dates
		self.tuOptions.xAxisDates = self.cbDates.isChecked()
		
		# zero time
		d = [self.dteZeroDate.date().year(), self.dteZeroDate.date().month(), self.dteZeroDate.date().day()]
		t = [self.dteZeroDate.time().hour(), self.dteZeroDate.time().minute(), self.dteZeroDate.time().second()]
		self.tuOptions.zeroTime = datetime(d[0], d[1], d[2], t[0], t[1], t[2])
		settings.setValue('TUFLOW/tuview_zeroTime', self.tuOptions.zeroTime)
		
		# format time
		self.tuOptions.dateFormat, self.tuOptions._dateFormat = convertTuviewftimToStrftim(self.leDateFormat.text())
		settings.setValue('TUFLOW/tuview_dateFormat', self.tuOptions.dateFormat)
		settings.setValue('TUFLOW/tuview__dateFormat', self.tuOptions._dateFormat)
		
		# x axis label rotation
		self.tuOptions.xAxisLabelRotation = self.sbXAxisLabelRotation.value()
		
		# play time delay
		self.tuOptions.playDelay = self.sbPlaySpeed.value()
		
		# cross section and flux line resolution
		self.tuOptions.resolution = self.sbResolution.value()
		
		# ARR mean event selection
		if self.rbARRNextHigher.isChecked():
			self.tuOptions.meanEventSelection = 'next higher'
		else:
			self.tuOptions.meanEventSelection = 'closest'
			

# ----------------------------------------------------------
#    tuView Selected Elements Dialog
# ----------------------------------------------------------
from ui_tuflowqgis_selectedElements import *


class TuSelectedElementsDialog(QDialog, Ui_selectedElements):
	def __init__(self, iface, elements):
		QDialog.__init__(self)
		self.setupUi(self)
		self.iface = iface
		
		# populate text box with results
		for element in elements:
			self.elementList.addItem(element)
		
		# Signals
		self.pbSelectElements.clicked.connect(self.newSelectionFromSelection)
		self.pbCloseWindow.clicked.connect(self.accept)
		self.elementList.setContextMenuPolicy(Qt.CustomContextMenu)
		self.elementList.customContextMenuRequested.connect(self.showMenu)
		
	def showMenu(self, pos):
		self.selectedElementsMenu = QMenu(self)
		self.newSelection_action = QAction('Selected Elements on Map', self.selectedElementsMenu)
		self.selectedElementsMenu.addAction(self.newSelection_action)
		self.newSelection_action.triggered.connect(self.newSelectionFromSelection)
		
		self.selectedElementsMenu.popup(self.elementList.mapToGlobal(pos))
		
	def newSelectionFromSelection(self):
		"""
		Select elements from id List

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		selIds = []
		for item in self.elementList.selectedItems():
			selIds.append(item.text())
		
		for layer in self.iface.mapCanvas().layers():
			if layer.type() == 0:
				if ' plot ' in layer.name().lower() or '_plot_' in layer.name().lower():
					layer.removeSelection()
					for feature in layer.getFeatures():
						if feature.attributes()[0] in selIds:
							layer.select(feature.id())
		
		return True
	

# ----------------------------------------------------------
#    Auto Plot and Export Dialog
# ----------------------------------------------------------
from ui_BatchExportPlotDialog import *


class TuBatchPlotExportDialog(QDialog, Ui_BatchPlotExport):
	def __init__(self, TuView):
		QDialog.__init__(self)
		self.setupUi(self)
		self.tuView = TuView
		self.iface = TuView.iface
		self.project = TuView.project
		self.canvas = TuView.canvas
		folderIcon = QgsApplication.getThemeIcon('\mActionFileOpen.svg')
		self.btnBrowse.setIcon(folderIcon)
		self.populateGISLayers()
		self.populateNameAttributes()
		self.populateResultMesh()
		self.populateResultTypes()
		self.populateTimeSteps()
		self.populateImageFormats()
		self.selectionEnabled()
		
		self.canvas.selectionChanged.connect(self.selectionEnabled)
		self.project.layersAdded.connect(self.populateGISLayers)
		self.cbGISLayer.currentIndexChanged.connect(self.populateTimeSteps)
		self.cbGISLayer.currentIndexChanged.connect(self.populateNameAttributes)
		self.mcbResultMesh.checkedItemsChanged.connect(self.populateResultTypes)
		self.mcbResultMesh.checkedItemsChanged.connect(self.populateTimeSteps)
		self.btnBrowse.clicked.connect(self.browse)
		self.buttonBox.accepted.connect(self.check)
		self.buttonBox.rejected.connect(self.reject)
		
	def populateGISLayers(self):
		for name, layer in QgsProject.instance().mapLayers().items():
			if layer.type() == QgsMapLayer.VectorLayer:
				if layer.geometryType() == 0 or layer.geometryType() == 1:
					self.cbGISLayer.addItem(layer.name())
					
	def populateNameAttributes(self):
		self.cbNameAttribute.clear()
		self.cbNameAttribute.addItem('-None-')
		layer = tuflowqgis_find_layer(self.cbGISLayer.currentText())
		if layer is not None:
			self.cbNameAttribute.addItems(layer.fields().names())
					
	def populateResultMesh(self):
		for resultName, result in self.tuView.tuResults.results.items():
			for type, items in result.items():
				if '_ts' not in type and '_lp' not in type:  # check if there is at least one 2D result type
					self.mcbResultMesh.addItem(resultName)
					break
	
	def populateResultTypes(self):
		self.mcbResultTypes.clear()
		resultTypes = []
		for mesh in self.mcbResultMesh.checkedItems():
			r = self.tuView.tuResults.results[mesh]
			for type, t in r.items():
				if '/Maximums' not in type:
					if type not in resultTypes:
						resultTypes.append(type)
		self.mcbResultTypes.addItems(resultTypes)
		
	def populateTimeSteps(self):
		self.cbTimesteps.setEnabled(False)
		timesteps = []
		timestepsFormatted = []
		maximum = False
		layer = tuflowqgis_find_layer(self.cbGISLayer.currentText())
		if layer is not None:
			if layer.geometryType() == 0:
				self.cbTimesteps.setEnabled(False)
			elif layer.geometryType() == 1:
				self.cbTimesteps.setEnabled(True)
				for mesh in self.mcbResultMesh.checkedItems():
					r = self.tuView.tuResults.results[mesh]
					for type, t in r.items():
						for time, items in t.items():
							if time == '-99999':
								maximum = True
							elif items[0] not in timesteps:
								timesteps.append(items[0])
				timesteps = sorted(timesteps)
				if timesteps:
					if timesteps[-1] < 100:
						timestepsFormatted = ['{0:02d}:{1:02.0f}:{2:05.2f}'.format(int(x), (x - int(x)) * 60,
						                                                           (x - int(x) - (x - int(x))) * 3600)
						                                                           for x in timesteps]
					else:
						timestepsFormatted = ['{0:03d}:{1:02.0f}:{2:05.2f}'.format(int(x), (x - int(x)) * 60,
						                                                           (x - int(x) - (x - int(x))) * 3600)
						                                                           for x in timesteps]
					if maximum:
						timestepsFormatted.insert(0, 'Maximum')
		self.cbTimesteps.addItems(timestepsFormatted)
	
	def populateImageFormats(self):
		formats = plt.gcf().canvas.get_supported_filetypes()
		self.cbImageFormat.addItems(['.{0}'.format(x) for x in formats.keys()])
		
	def selectionEnabled(self):
		self.rbSelectedFeatures.setEnabled(False)
		layer = tuflowqgis_find_layer(self.cbGISLayer.currentText())
		if layer is not None:
			sel = layer.selectedFeatures()
			if sel:
				self.rbSelectedFeatures.setEnabled(True)
		
	def browse(self):
		settings = QSettings()
		outFolder = settings.value('TUFLOW/batch_export')
		startDir = None
		if outFolder:  # if outFolder no longer exists, work backwards in directory until find one that does
			while outFolder:
				if os.path.exists(outFolder):
					startDir = outFolder
					break
				else:
					outFolder = os.path.dirname(outFolder)
		outFolder = QFileDialog.getExistingDirectory(self, 'Ouput Folder', startDir)
		if outFolder:
			self.outputFolder.setText(outFolder)
			settings.setValue('TUFLOW/batch_export', outFolder)
			
	def check(self):
		if not self.cbGISLayer.currentText():
			QMessageBox.information(self, 'Missing Data', 'Missing GIS Layer')
		elif not self.mcbResultMesh.checkedItems():
			QMessageBox.information(self, 'Missing Data', 'Missing Result Mesh')
		elif not self.mcbResultTypes.checkedItems():
			QMessageBox.information(self, 'Missing Data', 'Missing Result Types')
		elif self.cbTimesteps.isEnabled() and not self.cbTimesteps.currentText():
			QMessageBox.information(self, 'Missing Data', 'Missing Time Step')
		elif not self.outputFolder.text():
			QMessageBox.information(self, 'Missing Data', 'Missing Output Folder')
		elif not os.path.exists(self.outputFolder.text()):
			QMessageBox.information(self, 'Missing Data', 'Output Folder Does Not Exist')
		else:  # made it through the checks :)
			self.run()
		
	def run(self):
		# first save output folder directory - can have changed if they edit through line edit not browser
		settings = QSettings()
		settings.setValue('TUFLOW/batch_export', self.outputFolder.text())
		
		# get parameters
		gisLayer = self.cbGISLayer.currentText()  # str
		nameField = self.cbNameAttribute.currentText()  # str
		resultMesh = self.mcbResultMesh.checkedItems()  # list -> str
		resultTypes = self.mcbResultTypes.checkedItems()  # list -> str
		timestep = self.cbTimesteps.currentText()  # str
		features = 'all' if self.rbAllFeatures.isChecked() else 'selection'  # str
		format = 'csv' if self.rbCSV.isChecked() else 'image'  # str
		imageFormat = self.cbImageFormat.currentText()
		outputFolder = self.outputFolder.text()  # str
		
		# run process
		successful = self.tuView.tuMenuBar.tuMenuFunctions.batchPlotExport(gisLayer, resultMesh, resultTypes, timestep, features, format, outputFolder, nameField, imageFormat)
		
		if successful:
			QMessageBox.information(self, 'Batch Export', 'Successfully Exported Data')
		else:
			QMessageBox.information(self, 'Batch Export', 'Error Exporting Data')
		
		# finally destroy dialog
		self.accept()


# ----------------------------------------------------------
#    User Plot Data Plot View
# ----------------------------------------------------------
from ui_UserPlotDataPlotView import *


class TuUserPlotDataPlotView(QDialog, Ui_UserPlotData):
	def __init__(self, iface, TuUserPlotData):
		QDialog.__init__(self)
		self.setupUi(self)
		self.iface = iface
		self.tuUserPlotData = TuUserPlotData
		if self.tuUserPlotData.dates:
			self.cbDisplayDates.setEnabled(True)
		else:
			self.cbDisplayDates.setEnabled(False)

		#self.layout = self.plotFrame.layout()
		self.layout = QGridLayout(self.plotFrame)
		self.fig, self.ax = plt.subplots()
		self.plotWidget = FigureCanvasQTAgg(self.fig)
		self.layout.addWidget(self.plotWidget)
		self.manageAx()
		
		name = self.tuUserPlotData.name
		x = self.tuUserPlotData.x
		y = self.tuUserPlotData.y
		dates = self.tuUserPlotData.dates
		self.ax.plot(x, y, label=name)
		self.plotWidget.draw()
		self.refresh()
		
		self.pbRefresh.clicked.connect(self.refresh)
		self.pbOK.clicked.connect(self.accept)
		self.cbDisplayDates.clicked.connect(self.refresh)
	
	def manageAx(self):
		self.ax.grid()
		self.ax.tick_params(axis="both", which="major", direction="out", length=10, width=1, bottom=True, top=False,
		                    left=True, right=False)
		self.ax.minorticks_on()
		self.ax.tick_params(axis="both", which="minor", direction="out", length=5, width=1, bottom=True, top=False,
		                    left=True, right=False)
		
	def refresh(self):
		self.ax.cla()
		self.manageAx()
		name = self.tuUserPlotData.name
		x = self.tuUserPlotData.x
		y = self.tuUserPlotData.y
		dates = self.tuUserPlotData.dates
		self.ax.plot(x, y, label=name)
		self.fig.tight_layout()
		if self.cbDisplayDates.isChecked():
			self.addDates()
		self.plotWidget.draw()
		
	def addDates(self):
		xlim = self.ax.get_xlim()
		xmin = min(self.tuUserPlotData.x)
		xmax = max(self.tuUserPlotData.x)
		labels = self.ax.get_xticklabels()
		userLabels = []
		for label in labels:
			try:
				x = label.get_text()
				x = float(x)
			except ValueError:
				try:
					x = label.get_text()
					x = x[1:]
					x = float(x) * -1
				except ValueError:
					QMessageBox.information(self.iface.mainWindow(), 'Error', 'Error converting X axis value to float: {0}'.format(label.get_text()))
					self.cbDisplayDates.setChecked(False)
					return
			userLabels.append(self.convertTimeToDate(x))

		if len(userLabels) == len(labels):
			self.ax.set_xlim(xlim)
			self.ax.set_xticklabels(userLabels)
			loc, xLabels = plt.xticks(rotation=45, horizontalalignment='right')
			self.fig.tight_layout()
		else:
			QMessageBox.information(self.iface.mainWindow(), 'Error', 'Error converting X labes to dates.')
			
	def convertTimeToDate(self, time):
		for i, x in enumerate(self.tuUserPlotData.x):
			if i == 0:
				if time < x:
					return interpolate(time, x, self.tuUserPlotData.x[i+1], self.tuUserPlotData.dates[i], self.tuUserPlotData.dates[i+1])
				iPrev = i
				xPrev = x
			if x == time:
				return self.tuUserPlotData.dates[i]
			elif x > time and xPrev < time:
				return interpolate(time, xPrev, x, self.tuUserPlotData.dates[iPrev], self.tuUserPlotData.dates[i])
			elif i + 1 == len(self.tuUserPlotData.x):
				if time > x:
					return interpolate(time, self.tuUserPlotData.x[i-1], x, self.tuUserPlotData.dates[i-1], self.tuUserPlotData.dates[i])
			else:
				iPrev = i
				xPrev = x
				continue
			

# ----------------------------------------------------------
#    User Plot Data Table View
# ----------------------------------------------------------
from ui_UserPlotDataTableView import *
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuuserplotdata import TuUserPlotDataSet


class TuUserPlotDataTableView(QDialog, Ui_UserTableData):
	def __init__(self, iface, TuUserPlotData):
		QDialog.__init__(self)
		self.setupUi(self)
		self.iface = iface
		self.tuUserPlotData = TuUserPlotData
		
		if self.tuUserPlotData.dates:
			headers = ['Date', 'Time (hr)', self.tuUserPlotData.name]
			self.dataTable.setColumnCount(3)
		else:
			headers = ['Time (hr)', self.tuUserPlotData.name]
			self.dataTable.setColumnCount(2)
		self.dataTable.setHorizontalHeaderLabels(headers)
		
		self.dataTable.setRowCount(len(self.tuUserPlotData.x))
		
		for i in range(len(self.tuUserPlotData.x)):
			timeCol = 0
			if self.tuUserPlotData.dates:
				item = QTableWidgetItem(0)
				item.setText('{0}'.format(self.tuUserPlotData.dates[i]))
				self.dataTable.setItem(i, 0, item)
				timeCol = 1
			item = QTableWidgetItem(0)
			item.setText('{0}'.format(self.tuUserPlotData.x[i]))
			self.dataTable.setItem(i, timeCol, item)
			item = QTableWidgetItem(0)
			item.setText('{0}'.format(self.tuUserPlotData.y[i]))
			self.dataTable.setItem(i, timeCol + 1, item)
			
		self.pbPlot.clicked.connect(self.showPlot)
		self.buttonBox.accepted.connect(self.saveData)
		
	def convertStringToDatetime(self, s):
		date = s.split('-')
		d = []
		for c in date:
			d += c.split(' ')
		e = []
		for c in d:
			e += c.split(':')
		year = int(e[0])
		month = int(e[1])
		day = int(e[2])
		hour = int(e[3])
		minute = int(e[4])
		second = int(e[5])
		return datetime(year, month, day, hour, minute, second)
		
	def saveData(self, widget=None, dummy=False):
		x = []
		y = []
		dates = []
		
		if self.dataTable.columnCount() == 2:
			xCol = 0
			yCol = 1
			dateCol = None
		elif self.dataTable.columnCount() == 3:
			xCol = 1
			yCol = 2
			dateCol = 0
			
		for i in range(self.dataTable.rowCount()):
			if dateCol is not None:
				date = self.dataTable.item(i, dateCol).text()
				date = self.convertStringToDatetime(date)
				dates.append(date)
			x.append(float(self.dataTable.item(i, xCol).text()))
			y.append(float(self.dataTable.item(i, yCol).text()))
		
		if dummy:
			data = TuUserPlotDataSet('dummy', [x, y], 'time series', False, 100, dates)
			return data
		else:
			self.tuUserPlotData.setData([x, y], dates=dates)
		
		
	def showPlot(self):
		data = self.saveData(dummy=True)
		self.tableDialog = TuUserPlotDataPlotView(self.iface, data)
		self.tableDialog.exec_()
		
		
# ----------------------------------------------------------
#    User Plot Data Import Dialog
# ----------------------------------------------------------
from ui_UserPlotDataImportDialog import *


class TuUserPlotDataImportDialog(QDialog, Ui_UserPlotDataImportDialog):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.setupUi(self)
		self.iface = iface
		folderIcon = QgsApplication.getThemeIcon('\mActionFileOpen.svg')
		self.btnBrowse.setIcon(folderIcon)
		self.convertDate()
		self.convertZeroDate()
		self.ok = False
		
		self.btnBrowse.clicked.connect(self.browse)
		self.inFile.textChanged.connect(self.populateDataColumns)
		self.inFile.textChanged.connect(self.updatePreview)
		self.sbLines2Discard.valueChanged.connect(self.updateLabelRow)
		self.sbLines2Discard.valueChanged.connect(self.populateDataColumns)
		self.sbLines2Discard.valueChanged.connect(self.updatePreview)
		self.cbHeadersAsLabels.clicked.connect(self.populateDataColumns)
		self.sbLabelRow.valueChanged.connect(self.populateDataColumns)
		self.cbXColumn.currentIndexChanged.connect(self.updatePreview)
		self.mcbYColumn.checkedItemsChanged.connect(self.updatePreview)
		self.nullValue.textChanged.connect(self.updatePreview)
		self.rbCSV.clicked.connect(self.populateDataColumns)
		self.rbSpace.clicked.connect(self.populateDataColumns)
		self.rbTab.clicked.connect(self.populateDataColumns)
		self.rbOther.clicked.connect(self.populateDataColumns)
		self.delimiter.textChanged.connect(self.populateDataColumns)
		self.dateFormat.editingFinished.connect(self.convertDate)
		self.zeroHourDate.editingFinished.connect(self.convertZeroDate)
		self.buttonBox.accepted.connect(self.check)
		self.buttonBox.rejected.connect(self.reject)
		
	def browse(self):
		settings = QSettings()
		inFile = settings.value('TUFLOW/import_user_data')
		startDir = None
		if inFile:  # if outFolder no longer exists, work backwards in directory until find one that does
			while inFile:
				if os.path.exists(inFile):
					startDir = inFile
					break
				else:
					inFile = os.path.dirname(inFile)
		inFile = QFileDialog.getOpenFileName(self, 'Import Delimited File', startDir)[0]
		if inFile:
			self.inFile.setText(inFile)
			settings.setValue('TUFLOW/import_user_data', inFile)
			
	def getDelim(self):
		if self.rbCSV.isChecked():
			return ','
		elif self.rbSpace.isChecked():
			return ' '
		elif self.rbTab.isChecked():
			return '\t'
		elif self.rbOther.isChecked():
			return self.delimiter.text()
		
	def checkDateFormatLetters(self):
		for letter in self.dateFormat.text():
			if letter != 'D' and letter.lower() != 'm' and letter != 'Y' and letter != 'h' and letter != 's' \
					and letter != ' ' and letter != '/' and letter != '-' and letter != ':':
				return 'Character {0} not recognised as a date format'.format(letter)
		else:
			return ''
		
	def checkConsecutive(self, letter):
		f = self.dateFormat.text()
		for i in range(f.count(letter)):
			if i == 0:
				indPrev = f.find(letter)
			else:
				ind = f[indPrev+1:].find(letter)
				if ind != 0:
					return False
				indPrev += 1
				
		return True
	
	def getIndexes(self, letter):
		delim1 = None
		delim2 = None
		index = None
		a = None
		b = None
		f = self.dateFormat.text()
		if self.checkConsecutive(letter):
			i = f.find(letter)
			j = f.find(letter) + f.count(letter)
			if i > 0:
				delim1 = f[i-1]
				if delim1 == '/' or delim1 == '-' or delim1 == ' ' or delim1 == ':' or delim1 == ',' or delim1 == '.':
					a = f.split(delim1)
				else:  # use fixed field
					delim1 = None
					index = (i, j)
					return (delim1, delim2, index)
			if j < len(f):
				delim2 = f[j]
				if delim2 == '/' or delim2 == '-' or delim2 == ' ' or delim2 == ':' or delim2 == ',' or delim2 == '.':
					b = []
					if a is not None:
						for x in a:
							b += x.split(delim2)
					else:
						b = f.split(delim2)
				else:  # use fixed field
					delim2 = None
					index = (i, j)
					return (delim1, delim2, index)
			if b is None:
				if a is None:
					return 'Date Format is Ambiguous'
				else:
					b = a[:]
			for i, x in enumerate(b):
				if letter in x:
					index = i
					break
			return (delim1, delim2, index)
		else:
			return 'Date Format is Ambiguous'
	
	def convertDate(self):
		self.day = None
		self.month = None
		self.year = None
		self.hour = None
		self.minute = None
		self.second = None
		self.dateCanBeConverted = True
		f = self.dateFormat.text()
		if not f:
			self.dateCanBeConverted = False
		else:
			if self.checkDateFormatLetters():
				self.dateCanBeConverted = False
			else:
				# the following gives me a tuple with the delimiters on either side of the variable and the index of the
				# variable if string is split by both delimiters - or index can be tuple with fixed field indexes
				if f.count('D'):  # find D day
					self.day = self.getIndexes('D')
					if type(self.day) is str:
						self.dateCanBeConverted = False
				if f.count('M'):  # find M month
					self.month = self.getIndexes('M')
					if type(self.month) is str:
						self.dateCanBeConverted = False
				if f.count('Y'):  # find Y year
					self.year = self.getIndexes('Y')
					if type(self.year) is str:
						self.dateCanBeConverted = False
				if f.count('h'):  # find h hour
					self.hour = self.getIndexes('h')
					if type(self.hour) is str:
						self.dateCanBeConverted = False
				if f.count('m'):  # find m minutes
					self.minute = self.getIndexes('m')
					if type(self.minute) is str:
						self.dateCanBeConverted = False
				if f.count('s'):  # find s seconds
					self.second = self.getIndexes('s')
					if type(self.second) is str:
						self.dateCanBeConverted = False
						
		self.updatePreview()
	
	def convertZeroDate(self):
		self.zeroDay = (None, '/', 0)
		self.zeroMonth = ('/', '/', 1)
		self.zeroYear = ('/', ' ', 2)
		self.zeroHour = (' ', ':', 1)
		self.zeroMinute = (':', ':', 1)
		self.zeroSecond = (':', None, 2)
		self.zeroCanBeConverted = True
		f = self.zeroHourDate.text()
		if not f:
			self.zeroCanBeConverted = False
		
		self.updatePreview()
		
	def extractSpecificDateComponent(self, info, date):
		if info is not None:
			if type(info[2]) is tuple:  # fixed column
				i = info[2][0]
				j = info[2][1]
				try:
					a = int(date[i:j])
				except ValueError:
					a = None
				return a
			else:  # use delimiters
				delim1 = info[0]
				delim2 = info[1]
				index = info[2]
				if delim1 is not None:
					a = date.split(delim1)
				else:
					a = date[:]
				if delim2 is not None:
					b = []
					if delim1 is not None:
						for x in a:
							b += x.split(delim2)
					else:
						b = date.split(delim2)
				else:
					b = a[:]
				try:
					a = int(b[index])
				except ValueError:
					a = None
				except IndexError:
					a = None
				return a
				
		return None
	
	def convertZeroDateToTime(self):
		date = self.zeroHourDate.text()
		year = 2000  # default
		if self.zeroYear is not None:
			year = self.extractSpecificDateComponent(self.zeroYear, date)
			if year is not None:
				if year < 1000:
					year += 2000  # convert to YY to YYYY assuming it does not cross from one century to the next
			else:
				return 'Trouble converting year'
		month = 1  # default
		if self.zeroMonth is not None:
			month = self.extractSpecificDateComponent(self.zeroMonth, date)
			if month is None:
				return 'Trouble converting month'
		day = 1  # default
		if self.zeroDay is not None:
			day = self.extractSpecificDateComponent(self.zeroDay, date)
			if day is None:
				return 'Trouble converting day'
		hour = 12  # default
		if self.zeroHour is not None:
			hour = self.extractSpecificDateComponent(self.zeroHour, date)
			if hour is None:
				return 'Trouble converting hour'
		minute = 0
		if self.zeroMinute is not None:
			minute = self.extractSpecificDateComponent(self.zeroMinute, date)
			if minute is None:
				return 'Trouble converting minute'
		second = 0
		if self.zeroSecond is not None:
			second = self.extractSpecificDateComponent(self.zeroSecond, date)
			if second is None:
				return 'Trouble converting second'
		try:
			date = datetime(year, month, day, hour, minute, second)
			return date
		except ValueError:
			return 'Trouble converting date'
	
	def convertDateToTime(self, date, **kwargs):
		convertToDateTime = kwargs['convert_to_datetime'] if 'convert_to_datetime' in kwargs.keys() else False
		
		year = 2000  # default
		if self.year is not None:
			year = self.extractSpecificDateComponent(self.year, date)
			if year is not None:
				if year < 1000:
					year += 2000  # convert to YY to YYYY assuming it does not cross from one century to the next
			else:
				return 'Trouble converting year'
		month = 1  # default
		if self.month is not None:
			month = self.extractSpecificDateComponent(self.month, date)
			if month is None:
				return 'Trouble converting month'
		day = 1  # default
		if self.day is not None:
			day = self.extractSpecificDateComponent(self.day, date)
			if day is None:
				return 'Trouble converting day'
		hour = 12  # default
		if self.hour is not None:
			hour = self.extractSpecificDateComponent(self.hour, date)
			if hour is None:
				return 'Trouble converting hour'
		minute = 0
		if self.minute is not None:
			minute = self.extractSpecificDateComponent(self.minute, date)
			if minute is None:
				return 'Trouble converting minute'
		second = 0
		if self.second is not None:
			second = self.extractSpecificDateComponent(self.second, date)
			if second is None:
				return 'Trouble converting second'
		try:
			date = datetime(year, month, day, hour, minute, second)
		except ValueError:
			return 'Trouble converting date'
		if convertToDateTime:  # convert to datetime so don't worry about continuing to convert to hrs
			return date
		if self.zeroCanBeConverted:
			self.zeroDate = self.convertZeroDateToTime()
			if type(self.zeroDate) == str:
				QMessageBox.information(self.iface.mainWindow(), 'Error', 'Zero Hour Date: {0}'.format(self.zeroDate))
				return 0
			else:
				deltatime = date - self.zeroDate
				return float(deltatime.days * 24) + float(deltatime.seconds / 60 / 60)
		elif self.firstDataLine:
			self.zeroDate = date
			return 0.0
		else:
			deltatime = date - self.zeroDate
			return float(deltatime.days * 24) + float(deltatime.seconds / 60 / 60)
	
	def updateLabelRow(self):
		self.sbLabelRow.setMaximum(self.sbLines2Discard.value())
		if self.sbLines2Discard.value() == 0:
			self.cbHeadersAsLabels.setChecked(False)
		else:
			self.cbHeadersAsLabels.setChecked(True)
			self.sbLabelRow.setValue(self.sbLines2Discard.value())
			
	def populateDataColumns(self):
		self.cbXColumn.clear()
		self.mcbYColumn.clear()
		if self.inFile.text():
			if os.path.exists(self.inFile.text()):
				with open(self.inFile.text(), 'r') as fo:
					for i, line in enumerate(fo):
						header_line = max(self.sbLabelRow.value() - 1, 0)
						if i == header_line:
							delim = self.getDelim()
							if delim != '':
								headers = line.split(delim)
								headers[-1] = headers[-1].strip('\n')
								self.cbXColumn.addItems(headers)
								self.mcbYColumn.addItems(headers)
	
	def updatePreview(self):
		self.previewTable.clear()
		self.previewTable.setRowCount(0)
		self.previewTable.setColumnCount(0)
		if self.inFile.text():
			if os.path.exists(self.inFile.text()):
				if self.cbXColumn.count() and self.mcbYColumn.checkedItems():
					self.firstDataLine = True
					with open(self.inFile.text(), 'r') as fo:
						noIgnored = 1
						for i, line in enumerate(fo):
							header_line = max(self.sbLabelRow.value() - 1, 0)
							if i == header_line:
								delim = self.getDelim()
								headers = line.split(delim)
								xHeader = self.cbXColumn.currentText()
								try:
									xHeaderInd = headers.index(xHeader)
								except ValueError:
									xHeaderInd = headers.index('{0}\n'.format(xHeader))
								yHeaders = self.mcbYColumn.checkedItems()
								yHeaderInds = []
								for j, yHeader in enumerate(yHeaders):
									try:
										yHeaderInds.append(headers.index(yHeader))
									except ValueError:
										yHeaderInds.append(headers.index('{0}\n'.format(yHeader)))
								if not self.dateCanBeConverted:
									self.previewTable.setColumnCount(len(yHeaders) + 1)
								else:
									self.previewTable.setColumnCount(len(yHeaders) + 2)
								if self.cbHeadersAsLabels.isChecked():
									if not self.dateCanBeConverted:
										tableColumnNames = [xHeader] + yHeaders
									else:
										tableColumnNames = [xHeader, 'Time (hr)'] + yHeaders
								else:
									if not self.dateCanBeConverted:
										tableColumnNames = ['X'] + ['Y{0}'.format(x) for x in range(1, len(yHeaders) + 1)]
									else:
										tableColumnNames = ['Date', 'Time (hr)'] + ['Y{0}'.format(x) for x in range(1, len(yHeaders) + 1)]
								self.previewTable.setHorizontalHeaderLabels(tableColumnNames)
							elif i > header_line:
								if self.previewTable.rowCount() > 9:
									break
								self.previewTable.setRowCount(i - header_line - noIgnored + 1)
								self.previewTable.setVerticalHeaderLabels(['{0}'.format(x) for x in range(1, i - header_line + 1)])
								delim = self.getDelim()
								values = line.split(delim)
								if '{0}'.format(values[xHeaderInd]) == self.nullValue.text() or \
										'{0}'.format(values[xHeaderInd]) == '':
									noIgnored += 1
									continue
								for yHeaderInd in yHeaderInds:
									if '{0}'.format(values[yHeaderInd]) == self.nullValue.text() or \
										'{0}'.format(values[xHeaderInd]) == '':
										noIgnored += 1
										continue
								item = QTableWidgetItem(0)
								item.setText('{0}'.format(values[xHeaderInd]))
								self.previewTable.setItem((i - header_line - noIgnored), 0, item)
								k = 0
								if self.dateCanBeConverted:
									item = QTableWidgetItem(0)
									timeHr = self.convertDateToTime(values[xHeaderInd])
									if type(timeHr) is str:
										QMessageBox.information(self.iface.mainWindow(), 'Error', 'Line {0} - {1}'.format(i, timeHr))
										return
									item.setText('{0}'.format(timeHr))
									self.previewTable.setItem((i - header_line - noIgnored), 1, item)
									k = 1
								for j, yHeaderInd in enumerate(yHeaderInds):
									item = QTableWidgetItem(0)
									item.setText('{0}'.format(values[yHeaderInd]))
									self.previewTable.setItem((i - header_line - noIgnored), j + k + 1, item)
								self.firstDataLine = False
							
	def check(self):
		if not self.inFile.text():
			QMessageBox.information(self.iface.mainWindow(), 'Import User Plot Data', 'No Input File Specified')
		elif not os.path.exists(self.inFile.text()):
			QMessageBox.information(self.iface.mainWindow(), 'Import User Plot Data', 'Invalid Input File')
		elif self.cbXColumn.count() < 1:
			QMessageBox.information(self.iface.mainWindow(), 'Import User Plot Data', 'Invalid Delimiter or Input File is Empty')
		elif not self.mcbYColumn.checkedItems():
			QMessageBox.information(self.iface.mainWindow(), 'Import User Plot Data', 'No Y Column Values Selected')
		if self.checkDateFormatLetters():
				QMessageBox.information(self.iface.mainWindow(), 'Import User Plot Data',
				                        '{0}'.format(self.checkDateFormatLetters()))
		else:  # prelim checks out :)
			self.run()
		
	def run(self):
		self.names = []  # str data series names
		self.data = []  # tuple -> list x data, y data -> float
		x = []  # assumed all data share x axis
		y = []
		self.dates = []
		with open(self.inFile.text(), 'r') as fo:
			for i, line in enumerate(fo):
				header_line = max(self.sbLabelRow.value() - 1, 0)
				if i == header_line:
					delim = self.getDelim()
					headers = line.split(delim)
					xHeader = self.cbXColumn.currentText()
					try:
						xHeaderInd = headers.index(xHeader)
					except ValueError:
						xHeaderInd = headers.index('{0}\n'.format(xHeader))
					yHeaders = self.mcbYColumn.checkedItems()
					yHeaderInds = []
					for j, yHeader in enumerate(yHeaders):
						try:
							yHeaderInds.append(headers.index(yHeader))
						except ValueError:
							yHeaderInds.append(headers.index('{0}\n'.format(yHeader)))
					if self.cbHeadersAsLabels.isChecked():
						self.names = yHeaders
					else:
						self.names = ['Y{0}'.format(x) for x in range(1, len(yHeaders) + 1)]
					x = [[] for x in range(len(self.names))]
					y = [[] for x in range(len(self.names))]
					self.dates = [[] for x in range(len(self.names))]
					if not y:
						return
				elif i > header_line:
					delim = self.getDelim()
					values = line.split(delim)
					if '{0}'.format(values[xHeaderInd]) == self.nullValue.text() or \
							'{0}'.format(values[xHeaderInd]) == '':
						continue
					for yHeaderInd in yHeaderInds:
						if '{0}'.format(values[yHeaderInd]) == self.nullValue.text() or \
								'{0}'.format(values[xHeaderInd]) == '':
							continue
					if self.dateCanBeConverted:
						timeHr = self.convertDateToTime(values[xHeaderInd])
					for j, yHeaderInd in enumerate(yHeaderInds):
						if self.dateCanBeConverted:
							timeHr = self.convertDateToTime(values[xHeaderInd])
							self.dates[j].append(self.convertDateToTime(values[xHeaderInd], convert_to_datetime=True))
						else:
							timeHr = values[xHeaderInd]
						try:
							x[j].append(float(timeHr))
						except ValueError:
							x[j].append('')
						try:
							y[j].append(float(values[yHeaderInd]))
						except ValueError:
							y[j].append('')

		self.data = list(zip(x, y))
		
		# finally destroy dialog box
		self.ok = True
		self.accept()
		
		
# ----------------------------------------------------------
#    User Plot Data Manager
# ----------------------------------------------------------
from ui_UserPlotDataManagerDialog import *


class TuUserPlotDataManagerDialog(QDialog, Ui_UserPlotDataManagerDialog):
	def __init__(self, iface, TuUserPlotDataManager):
		QDialog.__init__(self)
		self.setupUi(self)
		self.tuUserPlotDataManager = TuUserPlotDataManager
		self.iface = iface
		self.loadedData = {}  # { name: [ combobox, checkbox ] }
		self.loadData()
		
		self.pbAddData.clicked.connect(self.addData)
		self.pbViewTable.clicked.connect(self.showDataTable)
		self.pbViewPlot.clicked.connect(self.showDataPlot)
		self.pbRemoveData.clicked.connect(self.removeData)
		self.pbOK.clicked.connect(self.accept)
		
	def loadData(self):
		# load data in correct order.. for dict means a little bit of manipulation
		for userData in [k for k, v in sorted(self.tuUserPlotDataManager.datasets.items(), key=lambda x: x[-1].number)]:
			name = self.tuUserPlotDataManager.datasets[userData].name
			plotType = self.tuUserPlotDataManager.datasets[userData].plotType
			status = Qt.Checked if self.tuUserPlotDataManager.datasets[userData].status else Qt.Unchecked
			self.UserPlotDataTable.setRowCount(self.UserPlotDataTable.rowCount() + 1)
			item = QTableWidgetItem(0)
			item.setText(name)
			item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
			item.setCheckState(status)
			combobox = QComboBox()
			combobox.setEditable(True)
			combobox.setMaximumHeight(30)
			combobox.setMaximumWidth(175)
			combobox.addItem('Time Series Plot')
			combobox.addItem('Cross Section / Long Plot')
			if plotType == 'long plot':
				combobox.setCurrentIndex(1)
			self.UserPlotDataTable.setItem(self.UserPlotDataTable.rowCount() - 1, 0, item)
			self.UserPlotDataTable.setCellWidget(self.UserPlotDataTable.rowCount() - 1, 1, combobox)
			self.loadedData[name] = [combobox, item]
			
			combobox.currentIndexChanged.connect(lambda: self.editData(combobox=combobox))
			self.UserPlotDataTable.itemClicked.connect(lambda: self.editData(item=item))
			self.UserPlotDataTable.itemChanged.connect(lambda item: self.editData(item=item))
		
	def addData(self):
		self.addDataDialog = TuUserPlotDataImportDialog(self.iface)
		self.addDataDialog.exec_()
		if self.addDataDialog.ok:
			for i, name in enumerate(self.addDataDialog.names):
				# add data to class
				counter = 1
				while name in self.tuUserPlotDataManager.datasets.keys():
					name = '{0}_{1}'.format(name, counter)
					counter += 1
				self.tuUserPlotDataManager.addDataSet(name, self.addDataDialog.data[i], 'time series', self.addDataDialog.dates[i])
				if not self.tuUserPlotDataManager.datasets[name].error:
					# add data to dialog
					self.UserPlotDataTable.setRowCount(self.UserPlotDataTable.rowCount() + 1)
					item = QTableWidgetItem(0)
					item.setText(name)
					item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
					item.setCheckState(Qt.Checked)
					combobox = QComboBox()
					combobox.setEditable(True)
					combobox.setMaximumHeight(30)
					combobox.setMaximumWidth(175)
					combobox.addItem('Time Series Plot')
					combobox.addItem('Cross Section / Long Plot')
					self.UserPlotDataTable.setItem(self.UserPlotDataTable.rowCount() - 1, 0, item)
					self.UserPlotDataTable.setCellWidget(self.UserPlotDataTable.rowCount() - 1, 1, combobox)
					self.loadedData[name] = [combobox, item]
					
					combobox.currentIndexChanged.connect(lambda: self.editData(combobox=combobox))
					self.UserPlotDataTable.itemClicked.connect(lambda item: self.editData(item=item))
					self.UserPlotDataTable.itemChanged.connect(lambda item: self.editData(item=item))
				else:
					QMessageBox.information(self.iface.mainWindow(), 'Import User Plot Data', self.tuUserPlotDataManager.datasets[name].error)
					
	def editData(self, **kwargs):
		combobox = kwargs['combobox'] if 'combobox' in kwargs.keys() else None
		item = kwargs['item'] if 'item' in kwargs.keys() else None
		
		if combobox is not None:
			for name, widgets in self.loadedData.items():
				if widgets[0] == combobox:
					plotType = 'time series' if combobox.currentText() == 'Time Series Plot' else 'long plot'
					self.tuUserPlotDataManager.editDataSet(name, plotType=plotType)
	
		elif item is not None:
			for name, widgets in self.loadedData.items():
				if widgets[-1] == item:
					status = True if item.checkState() == Qt.Checked else False
					self.tuUserPlotDataManager.editDataSet(name, newname=item.text(), status=status)
	
	def showDataTable(self):
		selectedItems = self.UserPlotDataTable.selectedItems()
		for item in selectedItems:
			data = self.tuUserPlotDataManager.datasets[item.text()]
			self.tableDialog = TuUserPlotDataTableView(self.iface, data)
			self.tableDialog.exec_()
			break  # just do first selection only
			
	def showDataPlot(self):
		selectedItems = self.UserPlotDataTable.selectedItems()
		for item in selectedItems:
			data = self.tuUserPlotDataManager.datasets[item.text()]
			self.tableDialog = TuUserPlotDataPlotView(self.iface, data)
			self.tableDialog.exec_()
			break  # just do first selection only
			
	def removeData(self):
		selectedItems = self.UserPlotDataTable.selectedItems()
		for item in selectedItems:
			name = item.text()
			self.tuUserPlotDataManager.removeDataSet(name)
			self.UserPlotDataTable.itemClicked.disconnect()
			self.UserPlotDataTable.itemChanged.disconnect()
		self.UserPlotDataTable.setRowCount(0)
		self.loadData()
		