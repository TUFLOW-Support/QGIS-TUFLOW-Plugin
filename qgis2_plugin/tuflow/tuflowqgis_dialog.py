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
import logging
#import csv
import os.path
import operator
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import processing
import glob
from datetime import datetime, timedelta
from tuflowqgis_library import *
from tuflowqgis_TuPlot import *
import TUFLOW_longprofile

import sys
import subprocess
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms")
currentFolder = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(currentFolder, 'forms'))

sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2018.2\debug-eggs')
sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2018.2\helpers\pydev')


sys.path.append(r'C:\Users\Ellis\.p2\pool\plugins\org.python.pydev.core_6.3.2.201803171248\pysrc')


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
		self.outname = None
		
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
		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outfile)
		QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
		QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.sourcelayer_changed)
		
		i = 0
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
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
			fpath, fname = os.path.split(newname)
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
			self.outname = outname
			outname = outname+'.shp'
			QMessageBox.information( self.iface.mainWindow(),"Information", "Appending .shp to filename.")
		else:
			self.outname = outname[:-4]
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
		if message <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Duplicating File", message)
		QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
		self.iface.addVectorLayer(savename, os.path.basename(savename)[:-4], "ogr")


# ----------------------------------------------------------
#    tuflowqgis import empty tuflow files
# ----------------------------------------------------------
from ui_tuflowqgis_import_empties import *
from tuflowqgis_settings import TF_Settings
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
		
		basepath = self.tfsettings.combined.base_dir
		if basepath:
			path_split = basepath.split('\\')
			if path_split[-1].lower() == 'tuflow':
				basepath = '\\'.join(path_split[:-1])
			self.emptydir.setText(os.path.join(basepath,"TUFLOW","model","gis","empty"))
		else:
			self.emptydir.setText("ERROR - Project not loaded")
		
		QObject.connect(self.browsedir, SIGNAL("clicked()"), lambda: self.browse_empty_dir(unicode(self.emptydir.displayText()).strip()))
		QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)

	def browse_empty_dir(self, oldName):
		newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		if len(newname) > 0:
			self.emptydir.setText(newname)
		else:
			self.emptydir.setText(oldName)


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
		if message <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Importing TUFLOW Empty File(s)", message)

# ----------------------------------------------------------
#    tuflowqgis Run TUFLOW (Simple)
# ----------------------------------------------------------
from ui_tuflowqgis_run_tf_simple import *
from tuflowqgis_settings import TF_Settings
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
		
		QObject.connect(self.browsetcffile, SIGNAL("clicked()"), self.browse_tcf)
		QObject.connect(self.browseexe, SIGNAL("clicked()"), self.browse_exe)
		QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)

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
		inFileName = str(inFileName)
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.tcfin = inFileName
		#self.tfsettings.save_last_exe(self,last_exe)("TUFLOW_Run_TUFLOW/tcf", inFileName)
		
		self.tcf.setText(inFileName)
		head, tail = os.path.split(inFileName)
		if head <> os.sep and head.lower() <> 'c:\\' and head <> '':
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
		if message <> None:
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
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if layer.name() == cName:
					self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if (i == 0):
			self.outfolder.setText(fpath)
			self.outfilename.setText(fpath + "/"+fname)

		# Connect signals and slots
		QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.source_changed) 
		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outfile)
		QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)


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
		
		if message <> None:
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
					if point_list <> None and (pol > 2):
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


# ----------------------------------------------------------
#    tuflowqgis configure tuflow project
# ----------------------------------------------------------
from ui_tuflowqgis_configure_tuflow_project import *		
from tuflowqgis_settings import TF_Settings
from qgis.gui import QgsGenericProjectionSelector
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
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if cLayer:
					if layer.name() == cName:
						self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if i == 0:
			self.sourcelayer.addItem("No Vector Data Open - use Set CRS Below")				
		

		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outdir)
		QObject.connect(self.browseexe, SIGNAL("clicked()"), self.browse_exe)
		QObject.connect(self.pbSelectCRS, SIGNAL("clicked()"), self.select_CRS)
		QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.layer_changed)
		QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)
		


			#QMessageBox.critical(self.iface.mainWindow(), "Setting Projection", "No vector data open, a shapefile is required for setting the model projection. \nPlease open or create a file in the desired projection.")


	def browse_outdir(self):
		#newname = QFileDialog.getExistingDirectory(None, QString.fromLocal8Bit("Output Directory"))
		newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		if newname != None:
			#self.outdir.setText(QString(newname))
			self.outdir.setText(newname)
	
	def select_CRS(self):
		projSelector = QgsGenericProjectionSelector()
		projSelector.exec_()
		try:
			authid = projSelector.selectedAuthId()
			self.crs = QgsCoordinateReferenceSystem()
			success = self.crs.createFromString(authid)
			if not success:
				self.crs = None
			else:
				self.crsDesc.setText(self.crs.description())
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
		inFileName = str(inFileName)
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
		path_split = basedir.split('\\')
		if path_split[-1].lower() == 'tuflow':
			basedir = '\\'.join(path_split[:-1])
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
			if message <> None:
				QMessageBox.critical(self.iface.mainWindow(), "Creating TUFLOW Directory ", message)
		
		if (self.cbRun.isChecked()):
				#tcf = os.path.join(basedir+"\\TUFLOW\\runs\\Create_Empties.tcf")
				tcf = os.path.join(basedir,"TUFLOW","runs","Create_Empties.tcf")
				QMessageBox.information(self.iface.mainWindow(), "Running TUFLOW","Starting simulation: "+tcf+"\n Executable: "+tfexe)
				message = run_tuflow(self.iface, tfexe, tcf)
				if message <> None:
					QMessageBox.critical(self.iface.mainWindow(), "Running TUFLOW ", message)
			
			
# ----------------------------------------------------------
#    tuflowqgis splitMI into shapefiles
# ----------------------------------------------------------
from ui_tuflowqgis_splitMI import *
from splitMI_mod import *
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

		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outdir)
		QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
		QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.layer_changed)
		i = 0
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
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
		
		if message <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Error Splitting file", message)
		QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
		
# ----------------------------------------------------------
#    tuflowqgis flow trace
# ----------------------------------------------------------

# ----------------------------------------------------------
#    tuflowqgis splitMI into shapefiles
# ----------------------------------------------------------
from ui_tuflowqgis_splitMI_folder import *
from tuflowqgis_settings import TF_Settings
from splitMI_func import *
from splitMI_mod2 import *
import os
import fnmatch

class tuflowqgis_splitMI_folder_dialog(QDialog, Ui_tuflowqgis_splitMI_folder):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.tfsettings = TF_Settings()
		self.last_mi = self.tfsettings.get_last_mi_folder()
		
		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outdir)
		QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
		


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
			
			if message <> None:
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
			

		QObject.connect(self.pb_Run, SIGNAL("clicked()"), self.run_clicked)
		QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
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
from tuflowqgis_settings import TF_Settings
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

		QObject.connect(self.browsedir, SIGNAL("clicked()"), self.browse_empty_dir)
		QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)

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
		if message <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Importing TUFLOW Empty File(s)", message)
			
# ----------------------------------------------------------
#    tuflowqgis extract ARR2016
# ----------------------------------------------------------
from ui_tuflowqgis_arr2016 import *
from tuflowqgis_settings import TF_Settings
import webbrowser

class tuflowqgis_extract_arr2016_dialog(QDialog, Ui_tuflowqgis_arr2016):

	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		self.tfsettings = TF_Settings()
		
		# Set up Input Catchment File ComboBox
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
				if layer.type() == QgsMapLayer.VectorLayer:
					if layer == 0 or layer.geometryType() == 2:
						self.comboBox_inputCatchment.addItem(layer.name())
							
		layerName = unicode(self.comboBox_inputCatchment.currentText())
		layer = tuflowqgis_find_layer(layerName)
						
		# Set up Catchment Field ID ComboBox
		if layer is not None:
			for f in layer.pendingFields():
				#QMessageBox.information(self.iface.mainWindow(), "Debug", '{0}'.format(f.name()))
				self.comboBox_CatchID.addItem(f.name())
				
		# Set up Catchment Area Field ComboBox
		if self.radioButton_ARF_auto.isChecked():
			self.comboBox_CatchArea.setEnabled(False)
		else:
			self.comboBox_CatchArea.setEnabled(True)
			self.comboBox_CatchArea.addItem('-None-')
			if layer is not None:
				for f in layer.pendingFields():
					self.comboBox_CatchArea.addItem(f.name())
					
		# Set up MAR and Static Value box
		self.mar_staticValue.setEnabled(False)
		
		#QObject.connect(self.commandLinkButton_BOMconditions, SIGNAL("clicked()"), self.open_BOMconditions)
		#QObject.connect(self.commandLinkButton_BOMcaveat, SIGNAL("clicked()"), self.open_BOMcaveat)
		QObject.connect(self.comboBox_inputCatchment, SIGNAL("currentIndexChanged(int)"), self.catchmentLayer_changed)
		QObject.connect(self.pushButton_browse, SIGNAL("clicked()"), self.browse_outFolder)
		QObject.connect(self.checkBox_aepAll, SIGNAL("clicked()"), self.aep_all)
		QObject.connect(self.checkBox_durAll, SIGNAL("clicked()"), self.dur_all)
		QObject.connect(self.radioButton_ARF_auto, SIGNAL("clicked()"), self.toggle_comboBox_CatchArea)
		QObject.connect(self.radioButton_ARF_manual, SIGNAL("clicked()"), self.toggle_comboBox_CatchArea)
		QObject.connect(self.comboBox_ilMethod, SIGNAL("currentIndexChanged(int)"), self.ilMethod_changed)
		QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
	
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
			for f in layer.pendingFields():
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
		reproject = processing.runalg("qgis:reprojectlayer", layer, "epsg:4203", None)
		reproject_layer = QgsVectorLayer(reproject['OUTPUT'], 'reproject_layer', 'ogr')
		centroid_list = []
		for feature in reproject_layer.getFeatures():
			centroid = []
			centroid.append('{0:.4f}'.format(feature.geometry().centroid().asPoint()[0]))
			centroid.append('{0:.4f}'.format(feature.geometry().centroid().asPoint()[1]))
			centroid_list.append(centroid)
		
		script = os.path.join(currentFolder, 'ARR2016', 'ARR_to_TUFLOW.py')
		QMessageBox.information(self.iface.mainWindow(), "information", 
							   'Starting ARR2016 to TUFLOW. Depending on how many catchments are being input, this can take a few minutes.\n\nA window will appear once finished.')
		for i in range(len(name_list)):
			sys_args = ['python', script, '-out', outFolder, '-name', name_list[i], 
						'-coords', centroid_list[i][0], centroid_list[i][1], '-mag', AEP_list, 
						'-frequent', frequent_events, '-rare', rare_events, '-dur', dur_list, '-nonstnd', nonstnd_list,
						'-area', area_list[i], '-cc', cc, '-year', cc_years, '-rcp', cc_rcp, '-format', format, 
						'-catchment_no', str(i), '-output_notation', output_notation, '-preburst', preburst, 
						'-lossmethod', ilMethod, '-mar', mar, '-lossvalue', staticValue, '-minarf', minArf,
						'-addtp', addTp]
			if i == 0:
				logfile = open(os.path.join(outFolder, 'log.txt'), 'w')
			else:
				logfile = open(os.path.join(outFolder, 'log.txt'), 'a')
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
				#try:
				#	proc = subprocess.Popen(sys_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				#	out, err = proc.communicate()
				#	logfile.write(out)
				#	logfile.write(err)
				#	logfile.close()
				#except:
				proc = subprocess.Popen(sys_args)
				error = True
				logfile.close()
		if error:
			QMessageBox.information(self.iface.mainWindow(), "Error", 'Process Complete. Error writing log file.')
		else:
			QMessageBox.information(self.iface.mainWindow(), "Message",
								   'Process Complete. Please see\n{0}\nfor warning and error messages.'\
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
from tuflowqgis_settings import TF_Settings

class tuflowqgis_insert_tuflow_attributes_dialog(QDialog, Ui_tuflowqgis_insert_tuflow_attributes):
	def __init__(self, iface, project):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.tfsettings = TF_Settings()
		
		# Set up Input Catchment File ComboBox
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
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
									
		QObject.connect(self.browsedir, SIGNAL("clicked()"), lambda: self.browse_empty_dir(unicode(self.emptydir.displayText()).strip()))
		QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)


	def browse_empty_dir(self, oldName):
		newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		if len(newname) > 0:
			self.emptydir.setText(newname)
		else:
			self.emptydir.setText(oldName)
		
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
#    tuflowqgis 1D integrity output window
# ----------------------------------------------------------
from ui_tuflowqgis_integrityOutput import *


class tuflowqgis_1d_integrity_output(QDialog, Ui_integrityOutput):
	def __init__(self, iface, results):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		
		# populate text box with results
		self.textBrowser.append(results)
		
		# Signals
		self.buttonBox.accepted.connect(self.run)
		
	def run(self):
		return


# ----------------------------------------------------------
#    tuflowqgis check 1D network integrity
# ----------------------------------------------------------
from ui_tuflowqgis_check1dIntegrity import *


class tuflowqgis_check_1d_integrity_dialog(QDialog, Ui_check1dIntegrity):
	def __init__(self, iface, dockOpened, resdock):
		QDialog.__init__(self)
		self.iface = iface
		self.dockOpened = dockOpened
		self.resdock = resdock
		self.project = QgsProject.instance()
		self.setupUi(self)
		
		# Set up input line and point layer combobox
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
			if layer.type() == QgsMapLayer.VectorLayer:
				if layer.geometryType() == 0:
					self.addPoint_combo.addItem(layer.name())
				elif layer.geometryType() == 1:
					self.addLine_combo.addItem(layer.name())
					self.addTa_combo.addItem(layer.name())
		
		# signals
		self.addLine_button.clicked.connect(lambda: self.addLyr(self.addLine_combo, self.lineLyrs_lw))
		self.addPoint_button.clicked.connect(lambda: self.addLyr(self.addPoint_combo, self.pointLyrs_lw))
		self.addTa_button.clicked.connect(lambda: self.addLyr(self.addTa_combo, self.taLyrs_lw))
		self.removeLine_button.clicked.connect(lambda: self.removeLyr(self.lineLyrs_lw))
		self.removePoint_button.clicked.connect(lambda: self.removeLyr(self.pointLyrs_lw))
		self.removeTa_button.clicked.connect(lambda: self.removeLyr(self.taLyrs_lw))
		self.addStartNwk_button.clicked.connect(self.addFeature)
		self.removeStartNwk_button.clicked.connect(self.removeFeature)
		self.addLine_button.clicked.connect(self.toggleStartElement)
		self.browse_button.clicked.connect(self.browse)
		self.outTxtFile_cb.clicked.connect(self.toggleOutFile)
		self.autoSnap_cb.clicked.connect(self.toggleSearchRadius_sb)
		self.groupBox_3.clicked.connect(self.toggleStartElement)
		self.checkAngle_cb.clicked.connect(self.toggleAngleLimit)
		self.checkCover_cb.clicked.connect(self.toggleCoverLimit)
		self.groupBox_3.clicked.connect(
			lambda: self.toggleGroupBox(self.groupBox_3, self.groupBox_4, self.groupBox_6, self.groupBox_7))
		self.groupBox_4.clicked.connect(
			lambda: self.toggleGroupBox(self.groupBox_4, self.groupBox_3, self.groupBox_6, self.groupBox_7))
		self.groupBox_6.clicked.connect(
			lambda: self.toggleGroupBox(self.groupBox_6, self.groupBox_4, self.groupBox_3, self.groupBox_7))
		self.groupBox_7.clicked.connect(
			lambda: self.toggleGroupBox(self.groupBox_7, self.groupBox_4, self.groupBox_6, self.groupBox_3))
		self.addLine_button.clicked.connect(self.toggleStartElement)
		self.getGroundElev_cb.clicked.connect(self.toggleDemSel)
		self.buttonBox.accepted.connect(self.preRunCheck)
		
		# Populate List Boxes with saved project values
		try:
			saveLineLyrs = self.project.readListEntry('TUFLOW', 'line_layers')[0]
			for lyr in saveLineLyrs:
				if tuflowqgis_find_layer(lyr) is not None:
					self.lineLyrs_lw.addItem(lyr)
		except:
			pass
		try:
			savePointLyrs = self.project.readListEntry('TUFLOW', 'point_layers')[0]
			for lyr in savePointLyrs:
				if tuflowqgis_find_layer(lyr) is not None:
					self.pointLyrs_lw.addItem(lyr)
		except:
			pass
		try:
			saveTableLyrs = self.project.readListEntry('TUFLOW', 'table_layers')[0]
			for lyr in saveTableLyrs:
				if tuflowqgis_find_layer(lyr) is not None:
					self.taLyrs_lw.addItem(lyr)
		except:
			pass
	
	def addLyr(self, combo, lw):
		inLyrs = []
		for i in range(lw.count()):
			a = lw.item(i).text()
			inLyrs.append(a)
		inLyr = combo.currentText()
		if inLyr is not None and len(inLyr) > 0:
			if inLyr not in inLyrs:
				lw.insertItem(0, inLyr)
				item = lw.item(0)
				lw.setItemSelected(item, True)
	
	def removeLyr(self, lw):
		removeIndex = []
		for i in range(lw.count()):
			if lw.item(i).isSelected():
				removeIndex.append(i)
		for i in reversed(removeIndex):
			lw.takeItem(i)
				
	def addFeature(self):
		inFeatures = []
		for i in range(self.startNwk_lw.count()):
			a = self.startNwk_lw.item(i).text()
			inFeatures.append(a)
		inFeat = self.name1d_combo.currentText()
		if inFeat not in inFeatures:
			self.startNwk_lw.insertItem(0, inFeat)
		
	def removeFeature(self):
		removeIndex = []
		for i in range(self.startNwk_lw.count()):
			if self.startNwk_lw.item(i).isSelected():
				removeIndex.append(i)
		for i in reversed(removeIndex):
			self.startNwk_lw.takeItem(i)

	def browse(self):
		outFile_old = None
		if len(self.outFile.text()) > 0:
			outFile_old = self.outFile.text()
		settings = QSettings()
		lastFolder = str(settings.value("check1dIntegrity", os.sep))
		if len(lastFolder) > 0:  # use last folder if stored
			fpath = lastFolder
		else:
			fpath = os.getcwd()
		outFile = QFileDialog.getSaveFileName(self, 'Output File', fpath, '*.txt')
		if outFile is None or len(outFile) < 3 or outFile == os.sep or outFile == 'c:\\':
			if outFile_old is not None:
				self.outFile.setText(outFile_old)
		else:
			settings.setValue("check1dIntegrity", os.path.dirname(outFile))
			self.outFile.setText(outFile)
	
	def toggleOutFile(self):
		if self.outTxtFile_cb.isChecked():
			self.outFile.setEnabled(True)
			self.browse_button.setEnabled(True)
		else:
			self.outFile.setEnabled(False)
			self.browse_button.setEnabled(False)

	def toggleAngleLimit(self):
		if self.checkAngle_cb.isChecked():
			self.label_10.setEnabled(True)
			self.angle2_sb.setEnabled(True)
			self.label_14.setEnabled(True)
		else:
			self.label_10.setEnabled(False)
			self.angle2_sb.setEnabled(False)
			self.label_14.setEnabled(False)

	def toggleCoverLimit(self):
		if self.checkCover_cb.isChecked():
			self.dem_combo.clear()
			self.label_11.setEnabled(True)
			self.coverDepth2_sb.setEnabled(True)
			self.label_13.setEnabled(True)
			self.label_12.setEnabled(True)
			self.dem_combo_2.setEnabled(True)
			rasterLyrs = findAllRasterLyrs()
			if len(rasterLyrs) > 0:
				for raster in rasterLyrs:
					self.dem_combo_2.addItem(raster)
		else:
			self.label_11.setEnabled(False)
			self.coverDepth2_sb.setEnabled(False)
			self.label_13.setEnabled(False)
			self.label_12.setEnabled(False)
			self.dem_combo_2.setEnabled(False)
	
	def toggleSearchRadius_sb(self):
		if self.autoSnap_cb.isChecked():
			self.snapSearchDis_sb.setEnabled(True)
		else:
			self.snapSearchDis_sb.setEnabled(False)

	def toggleStartElement(self):
		if self.groupBox_3.isChecked():
			self.name1d_combo.setEnabled(True)
			self.addStartNwk_button.setEnabled(True)
			self.removeStartNwk_button.setEnabled(True)
			self.label_3.setEnabled(True)
			self.label_9.setEnabled(True)
			self.angle_sb.setEnabled(True)
			self.startNwk_lw.setEnabled(True)
			self.plotDsConn_cb.setEnabled(True)
			self.getGroundElev_cb.setEnabled(True)
			features = []
			for i in range(self.startNwk_lw.count()):
				a = self.startNwk_lw.item(i).text()
				features.append(a)
			if self.lineLyrs_lw.count() > 0:
				for i in range(self.lineLyrs_lw.count()):
					name = self.lineLyrs_lw.item(i).text()
					lyr = tuflowqgis_find_layer(name)
					if lyr is not None:
						for feature in lyr.getFeatures():
							try:
								self.name1d_combo.addItem(feature.attributes()[0])
							except:
								pass
				#cLyr = self.iface.mapCanvas().currentLayer()
				selFeatures = []
				for i in range(self.lineLyrs_lw.count()):
					name = self.lineLyrs_lw.item(i).text()
					lyr = tuflowqgis_find_layer(name)
					selFeat = lyr.selectedFeatures()
					selFeatures.append(selFeat)
				txt = None
				for selFeat in selFeatures:
					for f in selFeat:
						txt = f.attributes()[0]
						if txt is not None:
							index = self.name1d_combo.findText(txt, Qt.MatchFixedString)
							if index >= 0:
								self.name1d_combo.setCurrentIndex(index)
							if txt not in features:
								self.startNwk_lw.insertItem(0, txt)
		else:
			self.name1d_combo.clear()
			self.name1d_combo.setEnabled(False)
			self.addStartNwk_button.setEnabled(False)
			self.removeStartNwk_button.setEnabled(False)
			self.label_3.setEnabled(False)
			self.label_9.setEnabled(False)
			self.angle_sb.setEnabled(False)
			self.startNwk_lw.setEnabled(False)
			self.plotDsConn_cb.setEnabled(False)
			self.getGroundElev_cb.setEnabled(False)
			
	def toggleDemSel(self):
		self.dem_combo.clear()
		if self.getGroundElev_cb.isChecked():
			self.dem_combo.setEnabled(True)
			self.label_15.setEnabled(True)
			self.label_16.setEnabled(True)
			self.coverDepth_sb.setEnabled(True)
			self.label_17.setEnabled(True)
			rasterLyrs = findAllRasterLyrs()
			if len(rasterLyrs) > 0:
				for raster in rasterLyrs:
					self.dem_combo.addItem(raster)
		else:
			self.dem_combo.setEnabled(False)
			self.label_15.setEnabled(False)
			self.label_16.setEnabled(False)
			self.coverDepth_sb.setEnabled(False)
			self.label_17.setEnabled(False)
			
	def toggleGroupBox(self, clickedGB, *args):
		if clickedGB.isChecked():
			for gb in args:
				gb.setChecked(False)
	
	def saveInputLayers(self):
		saveLineLyrs = []
		for i in range(self.lineLyrs_lw.count()):
			saveLineLyrs.append(self.lineLyrs_lw.item(i).text())
		self.project.writeEntry("TUFLOW", "line_layers", saveLineLyrs)
		
		savePointLyrs = []
		for i in range(self.pointLyrs_lw.count()):
			savePointLyrs.append(self.pointLyrs_lw.item(i).text())
		self.project.writeEntry("TUFLOW", "point_layers", savePointLyrs)
		
		saveTableLyrs = []
		for i in range(self.taLyrs_lw.count()):
			saveTableLyrs.append(self.taLyrs_lw.item(i).text())
		self.project.writeEntry("TUFLOW", "table_layers", saveTableLyrs)
	
	def checkLayerType(self, lyr):
		error = False
		message = ''
		for feature in lyr.getFeatures():
			break
		if feature.fields().field(0).type() != QVariant.String:
			error = True
			message = '{0} must be in a 1D_nwk format: Error with ID Attribute'.format(lyr.name())
		elif feature.fields().field(1).type() != QVariant.String:
			error = True
			message = '{0} must be in a 1D_nwk format: Error with Type Attribute'.format(lyr.name())
		elif feature.fields().field(4).type() != QVariant.Double:
			error = True
			message = '{0} must be in a 1D_nwk format: Error with Length Attribute'.format(lyr.name())
		elif feature.fields().field(6).type() != QVariant.Double:
			error = True
			message = '{0} must be in a 1D_nwk format: Error with Upstream Invert Attribute'.format(lyr.name())
		elif feature.fields().field(7).type() != QVariant.Double:
			error = True
			message = '{0} must be in a 1D_nwk format: Error with Downstream Invert Attribute'.format(lyr.name())
		elif feature.fields().field(13).type() != QVariant.Double:
			error = True
			message = '{0} must be in a 1D_nwk format: Error with Width Attribute'.format(lyr.name())
		elif feature.fields().field(14).type() != QVariant.Double:
			error = True
			message = '{0} must be in a 1D_nwk format: Error with Height Attribute'.format(lyr.name())
		elif feature.fields().field(15).type() != QVariant.LongLong and \
				feature.fields().field(15).type() != QVariant.Int and feature.fields().field(15).type() != QVariant.Double:
			error = True
			message = '{0} must be in a 1D_nwk format: Error with Number Of Attribute'.format(lyr.name())
		return error, message
	
	def preRunCheck(self):
		error = False
		warning = False
		message = ''
		# Check inputs
		for i in range(self.lineLyrs_lw.count()):
			lyr = tuflowqgis_find_layer(self.lineLyrs_lw.item(i).text())
			error, message = self.checkLayerType(lyr)
			if error:
				break
		for i in range(self.pointLyrs_lw.count()):
			lyr = tuflowqgis_find_layer(self.pointLyrs_lw.item(i).text())
			error, message = self.checkLayerType(lyr)
			if error:
				break
		if error:
			pass
		elif self.lineLyrs_lw.count() < 1:
			error = True
			message = 'No 1d_nwk line layer has been input.'
		elif self.check1dPoint_cb.isChecked() and self.pointLyrs_lw.count() < 1:
			error = True
			message = 'No 1d_nwk point layer has been input.'
		elif self.getGroundElev_cb.isChecked() and len(self.dem_combo.currentText()) < 1:
			error = True
			message = 'No DEM has been input'
		elif self.checkCover_cb.isChecked() and len(self.dem_combo_2.currentText()) < 1:
			error = True
			message = 'No DEM has been input'
		# Check an output is selected
		elif not self.outMessBox_cb.isChecked() and not self.outSel_cb.isChecked() and \
		  not self.outTxtFile_cb.isChecked() and not self.outPLayer_cb.isChecked() and \
		  not self.plotDsConn_cb.isChecked():
			warning = True
			message = 'No output selected. Do you wish to continue?'
		# Check map projection
		elif self.iface.mapCanvas().mapUnits() != 0 and self.iface.mapCanvas().mapUnits() != 1:
			warning = True
			message = 'Map Projection may not be cartesian. This can cause an error in the tool. ' \
					  'Do you wish to continue?'
		if error:
			QMessageBox.information(self.iface.mainWindow(), 'Error', message)
		elif warning:
			run = QMessageBox.question(self.iface.mainWindow(), "Warning", message,
									   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
			if run == QMessageBox.Yes:
				self.run()
		else:
			self.run()


	def run(self):
		self.saveInputLayers()
		startTime = datetime.now()
		self.check1dIntegrity.accept()  # destroy dialog window
		# Get inputs
		if self.iface.mapCanvas().mapUnits() == 0:
			units = 'm'
		elif self.iface.mapCanvas().mapUnits() == 1:
			units = 'ft'
		else:
			units = ''
		checkLine = False
		checkPoint = False
		autoSnap = False
		correctPipeDir = False
		getDnsConn = False
		plotDnsConn = False
		getDemElev = False
		continuityCheck = False
		checkArea = False
		checkGradient = False
		checkAngle = False
		checkCover = False
		angleLimit = 90
		coverLimit = 0.5
		correctDirectionByGradient = False
		correctDirectionByContinuity = False
		outMsg = False
		outSel = False
		outTxt = False
		outLyr = False
		dem = None
		plotCoverDepth = None
		if self.check1dLine_cb.isChecked():
			checkLine = True
		if self.check1dPoint_cb.isChecked():
			checkPoint = True
		if self.autoSnap_cb.isChecked():
			autoSnap = True
			searchRadius = self.snapSearchDis_sb.value()
		if self.groupBox_3.isChecked():
			getDnsConn = True
			angleLimit = self.angle_sb.value()
			startElem = []
			for i in range(self.startNwk_lw.count()):
				a = self.startNwk_lw.item(i).text()
				startElem.append(a)
			if self.plotDsConn_cb.isChecked():
				plotDnsConn = True
			if self.getGroundElev_cb.isChecked():
				getDemElev = True
				dem = tuflowqgis_find_layer(self.dem_combo.currentText())
				plotCoverDepth = self.coverDepth_sb.value()
		if self.checkArea_cb.isChecked():
			continuityCheck = True
			checkArea = True
		if self.checkGradient_cb.isChecked():
			continuityCheck = True
			checkGradient = True
		if self.checkAngle_cb.isChecked():
			continuityCheck = True
			checkAngle = True
			angleLimit = self.angle2_sb.value()
		if self.checkCover_cb.isChecked():
			continuityCheck = True
			checkCover = True
			coverLimit = self.coverDepth2_sb.value()
			dem = tuflowqgis_find_layer(self.dem_combo_2.currentText())
		if self.correctPipeDir_inverts_cb.isChecked():
			correctDirectionByGradient = True
		if self.correctPipeDir_continuity_cb.isChecked():
			correctDirectionByContinuity = True
		if self.outMessBox_cb.isChecked():
			outMsg = True
		if self.outSel_cb.isChecked():
			outSel = True
		if self.outTxtFile_cb.isChecked():
			outTxt = True
		if self.outPLayer_cb.isChecked():
			outLyr = True
		toolTimes = []
		lineLyrs = []
		lineDict = {}
		for i in range(self.lineLyrs_lw.count()):
			lineLyrs.append(tuflowqgis_find_layer(self.lineLyrs_lw.item(i).text()))
		pointLyrs = []
		pointDict = {}
		for i in range(self.pointLyrs_lw.count()):
			pointLyrs.append(tuflowqgis_find_layer(self.pointLyrs_lw.item(i).text()))
		taLyrs = []
		for i in range(self.taLyrs_lw.count()):
			taLyrs.append(tuflowqgis_find_layer(self.taLyrs_lw.item(i).text()))
		# Start Line Check section
		if checkLine:
			toolStart = datetime.now()
			lineDict, lineDrape = getVertices(lineLyrs, dem)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append('Get Line Vertices: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
			                                                                    toolTime.total_seconds() % 60) if
			                 toolTime.total_seconds() >= 60 else 'Get Line Vertices: {0:.1f} secs\n'.format(
				toolTime.total_seconds()))
			toolStart = datetime.now()
			unsnappedLines, unsnappedLineNames, closestVLines, dsLines = checkSnapping(assessment='lines',
			                                                                           lines=lineDict, line_layers=lineLyrs,
			                                                                           points=pointDict,
			                                                                           dns_conn=getDnsConn)  # Get unsnapped line vertices
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append('Check Line Snapping: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
			                                                                    toolTime.total_seconds() % 60) if
			                 toolTime.total_seconds() >= 60 else 'Check Line Snapping: {0:.1f} secs\n'.format(
				toolTime.total_seconds()))
			if autoSnap:
				toolStart = datetime.now()
				editedLines, returnLogL = moveVertices(lineLyrs, closestVLines, searchRadius, units)  # perform auto snap routine
				toolEnd = datetime.now()
				toolTime = toolEnd - toolStart
				toolTimes.append('Snapping Lines: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
				                                                                      toolTime.total_seconds() % 60) if
				                 toolTime.total_seconds() >= 60 else 'Snapping Lines: {0:.1f} secs\n'.format(
					toolTime.total_seconds()))
				if checkPoint:
					toolStart = datetime.now()
					lineDict, lineDrape = getVertices(lineLyrs, dem)
					toolEnd = datetime.now()
					toolTime = toolEnd - toolStart
					toolTimes.append('Re-Collecting Line Vertices for Points analysis: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() /
					                                                                      60,
					                                                                      toolTime.total_seconds() %
					                                                                      60) if
					                 toolTime.total_seconds() >= 60 else 'Re-Collecting Line Vertices for Points analysis: {0:.1f} secs\n'.format(
						toolTime.total_seconds()))
		# Start Point Check Section
		if checkPoint:
			if len(lineDict) == 0:
				toolStart = datetime.now()
				lineDict, lineDrape = getVertices(lineLyrs, dem)
				toolEnd = datetime.now()
				toolTime = toolEnd - toolStart
				toolTimes.append('Get Line Vertices: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
				                                                                         toolTime.total_seconds() %
				                                                                         60) if
				                 toolTime.total_seconds() >= 60 else 'Get Line Vertices: {0:.1f} secs\n'.format(
					toolTime.total_seconds()))
			toolStart = datetime.now()
			pointDict, pointDrape = getVertices(pointLyrs, dem)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append('Get Point Vertices: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
			                                                                         toolTime.total_seconds() %
			                                                                         60) if
			                 toolTime.total_seconds() >= 60 else 'Get Point Vertices: {0:.1f} secs\n'.format(
				toolTime.total_seconds()))
			toolStart = datetime.now()
			unsnappedPoints, closestVPoints = checkSnapping(assessment='points', lines=lineDict, line_layers=lineLyrs,
				                                            points=pointDict)  # Get unsnapped points
			toolTimes.append('Check Point Snapping: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
			                                                                           toolTime.total_seconds() %
			                                                                           60) if
			                 toolTime.total_seconds() >= 60 else 'Check Point Snapping: {0:.1f} secs\n'.format(
				toolTime.total_seconds()))
			if autoSnap:
				toolStart = datetime.now()
				editedPoints, returnLogP = moveVertices(pointLyrs, closestVPoints, searchRadius, units)
				toolEnd = datetime.now()
				toolTime = toolEnd - toolStart
				toolTimes.append('Snapping Points: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
				                                                                      toolTime.total_seconds() % 60) if
				                 toolTime.total_seconds() >= 60 else 'Snapping Points: {0:.1f} secs\n'.format(
					toolTime.total_seconds()))
		if getDnsConn:
			if len(startElem) == 0:
				return
			toolStart = datetime.now()
			lineDict, lineDrape = getVertices(lineLyrs, dem)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append('Get Line Vertices: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
			                                                                         toolTime.total_seconds() %
			                                                                         60) if
			                 toolTime.total_seconds() >= 60 else 'Get Line Vertices: {0:.1f} secs\n'.format(
				toolTime.total_seconds()))
			if len(pointLyrs) > 0:
				toolStart = datetime.now()
				pointDict, pointDrape = getVertices(pointLyrs, dem)
				toolEnd = datetime.now()
				toolTime = toolEnd - toolStart
				toolTimes.append('Get Point Vertices: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() /
				                                                                          60,
				                                                                          toolTime.total_seconds() %
				                                                                          60) if
				                 toolTime.total_seconds() >= 60 else 'Get Point Vertices: {0:.1f} secs\n'.format(
					toolTime.total_seconds()))
			toolStart = datetime.now()
			unsnappedLines, unsnappedLineNames, closestVLines, dsLines = \
				checkSnappingFlowTrace(lines=lineDict, points=pointDict, line_layers=lineLyrs, point_layers=pointLyrs, dns_conn=getDnsConn, start_lines=startElem)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append('Check Line and Point Snapping: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
			                                                                           toolTime.total_seconds() %
			                                                                           60) if
			                 toolTime.total_seconds() >= 60 else 'Check Line and Point Snapping: {0:.1f} secs\n'.format(
				toolTime.total_seconds()))
			if len(taLyrs) > 0:
				toolStart = datetime.now()
				dsLines = getElevFromTa(lineDict, dsLines, lineLyrs, taLyrs)
				toolEnd = datetime.now()
				toolTime = toolEnd - toolStart
				toolTimes.append(
					'Get Elevations from Table Files: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
					                                                                    toolTime.total_seconds() %
					                                                                    60) if
					toolTime.total_seconds() >= 60 else 'Get Elevations from Table Files: {0:.1f} secs\n'.format(
						toolTime.total_seconds()))
			toolStart = datetime.now()
			longProfile = TUFLOW_longprofile.DownstreamConnectivity(dsLines, startElem, lineLyrs, angleLimit,
			                                                        lineDrape, plotCoverDepth, lineDict, units)
			longProfile.getBranches()
			longProfile.reportLog()
			if plotDnsConn:
				longProfile.getPlotFormat()
				if self.dockOpened:
					self.resdock.qgis_connect()
					self.resdock.show()
					self.resdock.layerChanged()
					self.resdock.add_profileIntTool(longProfile)
				else:
					self.dockOpened = True
					self.resdock = TuPlot(self.iface, profile_integerity_tool=longProfile)
					self.iface.addDockWidget(Qt.RightDockWidgetArea, self.resdock)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append(
				'Collecting Long Section: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
				                                                                      toolTime.total_seconds() %
				                                                                      60) if
				toolTime.total_seconds() >= 60 else 'Collecting Long Section: {0:.1f} secs\n'.format(
					toolTime.total_seconds()))
		# Check network continuity
		if continuityCheck:
			continuityLog = ''
			continuityError = []
			toolStart = datetime.now()
			lineDict, lineDrape = getVertices(lineLyrs, dem)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append('Get Line Vertices: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
			                                                                         toolTime.total_seconds() %
			                                                                         60) if
			                 toolTime.total_seconds() >= 60 else 'Get Line Vertices: {0:.1f} secs\n'.format(
				toolTime.total_seconds()))
			if len(pointLyrs) > 0:
				toolStart = datetime.now()
				pointDict, pointDrape = getVertices(pointLyrs, dem)
				toolEnd = datetime.now()
				toolTime = toolEnd - toolStart
				toolTimes.append('Get Point Vertices: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() /
				                                                                          60,
				                                                                          toolTime.total_seconds() %
				                                                                          60) if
				                 toolTime.total_seconds() >= 60 else 'Get Point Vertices: {0:.1f} secs\n'.format(
					toolTime.total_seconds()))
			toolStart = datetime.now()
			unsnappedLines, unsnappedLineNames, closestVLines, dsLines = checkSnapping(lines=lineDict,
																					     points=pointDict, line_layers=lineLyrs,
																					     dns_conn=continuityCheck)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append(
				'Check Line and Point Snapping: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
				                                                                    toolTime.total_seconds() %
				                                                                    60) if
				toolTime.total_seconds() >= 60 else 'Check Line and Point Snapping: {0:.1f} secs\n'.format(
					toolTime.total_seconds()))
			if len(taLyrs) > 0:
				toolStart = datetime.now()
				dsLines = getElevFromTa(lineDict, dsLines, lineLyrs, taLyrs)
				toolEnd = datetime.now()
				toolTime = toolEnd - toolStart
				toolTimes.append(
					'Get Elevations from Table Files: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() /
					                                                                      60,
					                                                                      toolTime.total_seconds() %
					                                                                      60) if
					toolTime.total_seconds() >= 60 else 'Get Elevations from Table Files: {0:.1f} secs\n'.format(
						toolTime.total_seconds()))
			toolStart = datetime.now()
			continuityLog, continiuityWarningTypes, continuityError = checkNetworkContinuity(lineDict, dsLines,
			                                                                                 lineDrape, angleLimit,
			                                                                                 coverLimit,
			                                                                                 [checkArea, checkGradient,
			                                                                                  checkAngle, checkCover],
			                                                                                 units)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append(
				'Check Continuity: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() /
				                                                                      60,
				                                                                      toolTime.total_seconds() %
				                                                                      60) if
				toolTime.total_seconds() >= 60 else 'Check Continuity: {0:.1f} secs\n'.format(
					toolTime.total_seconds()))
		# Correct Network Direction
		if correctDirectionByGradient:
			toolStart = datetime.now()
			lineDict, lineDrape = getVertices(lineLyrs, dem)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append('Get Line Vertices: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
			                                                                         toolTime.total_seconds() %
			                                                                         60) if
			                 toolTime.total_seconds() >= 60 else 'Get Line Vertices: {0:.1f} secs\n'.format(
				toolTime.total_seconds()))
			toolStart = datetime.now()
			correctDirectionGradLog, correctDirectionGradType, correctDirectionGradPoint = \
				correctPipeDirectionByInvert(lineLyrs, lineDict, units)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append('Correct Line Direction by Invert: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
			                                                                         toolTime.total_seconds() %
			                                                                         60) if
			                 toolTime.total_seconds() >= 60 else 'Correct Line Direction by Invert: {0:.1f} secs\n'.format(
				toolTime.total_seconds()))
		if correctDirectionByContinuity:
			toolStart = datetime.now()
			lineDict, lineDrape = getVertices(lineLyrs, dem)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append('Get Line Vertices: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
			                                                                         toolTime.total_seconds() %
			                                                                         60) if
			                 toolTime.total_seconds() >= 60 else 'Get Line Vertices: {0:.1f} secs\n'.format(
				toolTime.total_seconds()))
			if len(pointLyrs) > 0:
				toolStart = datetime.now()
				pointDict, pointDrape = getVertices(pointLyrs, dem)
				toolEnd = datetime.now()
				toolTime = toolEnd - toolStart
				toolTimes.append('Get Point Vertices: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() /
				                                                                          60,
				                                                                          toolTime.total_seconds() %
				                                                                          60) if
				                 toolTime.total_seconds() >= 60 else 'Get Point Vertices: {0:.1f} secs\n'.format(
					toolTime.total_seconds()))
			toolStart = datetime.now()
			unsnappedLines, unsnappedLineNames, closestVLines, dsLines = checkSnapping(lines=lineDict,
			                                                                           points=pointDict, line_layers=lineLyrs,
			                                                                           dns_conn=correctDirectionByContinuity)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append(
				'Check Line and Point Snapping: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
				                                                                    toolTime.total_seconds() %
				                                                                    60) if
				toolTime.total_seconds() >= 60 else 'Check Line and Point Snapping: {0:.1f} secs\n'.format(
					toolTime.total_seconds()))
			toolStart = datetime.now()
			correctDirectionContLog, correctDirectionContType, correctDirectionContPoint = \
				correctPipeDirectionFromConnections(lineDict, dsLines)
			toolEnd = datetime.now()
			toolTime = toolEnd - toolStart
			toolTimes.append(
				'Correct Line Direction by Continuity: {0:.0f} mins {1:.0f} secs\n'.format(toolTime.total_seconds() / 60,
				                                                                       toolTime.total_seconds() %
				                                                                       60) if
				toolTime.total_seconds() >= 60 else 'Correct Line Direction by Continuity: {0:.1f} secs\n'.format(
					toolTime.total_seconds()))
		finishTime = datetime.now()
		computationTime = finishTime - startTime
		# Output
		if outMsg or outTxt:
			if outMsg:
				results = '###############\n# 1D Integrity Output  #\n###############\n\n'
			else:
				results = '#######################\n# 1D Integrity Output #\n#######################\n\n'
			for toolTime in toolTimes:
				results += toolTime
			results += '\nTotal Computation Time: {0:.0f} mins {1:.0f} secs\n'.format(computationTime.total_seconds() / 60,
			                                                                    computationTime.total_seconds() % 60) \
				if computationTime.total_seconds() >= 60 else '\nTotal Computation Time: {0:.1f} secs\n'.format(
				computationTime.total_seconds())
			if checkLine:
				results += '\n' + r'\\ Unsnapped Lines \\' + '\n\n'
				if len(unsnappedLines) == 0:
					results += 'None\n'
				else:
					for line in unsnappedLines:
						results += '{0}\n'.format(line)
				if autoSnap:
					if len(returnLogL) < 1:
						results += '\n' + r'\\ Auto Snap Lines \\' + '\n\nNone\n'
					else:
						results += '\n' + r'\\ Auto Snap Lines \\' + '\n\n{0}\n'.format(returnLogL)
			if checkPoint:
				results += '\n' + r'\\ Unsnapped Nodes \\' + '\n\n'
				if len(unsnappedPoints) == 0:
					results += 'None\n'
				else:
					for node in unsnappedPoints:
						results += '{0}\n'.format(node)
				if autoSnap:
					if len(returnLogP) < 1:
						results += '\n' + r'\\ Auto Snap Points \\' + '\n\nNone\n'
					else:
						results += '\n' + r'\\ Auto Snap Points \\' + '\n\n{0}\n'.format(returnLogP)
			if getDnsConn:
				results += '\n' + r'\\ Downstream Connections \\' + '\n\n'
				results += longProfile.log
			if continuityCheck:
				results += '\n' + r'\\ Continuity Checks \\' + '\n\n{0}\n'.format(continuityLog)
			if correctDirectionByGradient or correctDirectionByContinuity:
				results += '\n' + r'\\ Correct Pipe Direction \\' + '\n\n'
				if correctDirectionByGradient:
					results += '# Pipes Corrected by Gradient\n\n{0}\n'.format(correctDirectionGradLog)
				if correctDirectionByContinuity:
					results += '# Pipes Corrected by Continuity\n\n{0}\n'.format(correctDirectionContLog)
			if outMsg:
				self.outDialog = tuflowqgis_1d_integrity_output(self.iface, results)
				self.outDialog.show()
			if outTxt:
				outFile = self.outFile.text()
				f = open(outFile, 'w')
				f.write(results)
				f.close()
		if outSel:
			# remove any current selection
			for layer in self.iface.mapCanvas().layers():
				if layer.type() == 0:
					layer.removeSelection()
			# select points
			if checkPoint:
				for layer in pointLyrs:
					for f in layer.getFeatures():
						if f.attributes()[0] in unsnappedPoints:
							fid = f.id()
							layer.select(fid)
			# select lines
			if checkLine:
				for layer in lineLyrs:
					for f in layer.getFeatures():
						if f.attributes()[0] in unsnappedLineNames:
							fid = f.id()
							layer.select(fid)
			if getDnsConn:
				names = longProfile.log.split('\n')
				for n in names:
					name = n.split(' ')[0].strip()
					if len(name) > 0:
						lyr = lineDict[name][2]
						fid = lineDict[name][1]
						idFld = lyr.fields()[0]
						filter = '"{0}" = \'{1}\''.format(idFld.name(), name)
						request = QgsFeatureRequest().setFilterExpression(filter)
						for f in lyr.getFeatures(request):
							if f.id() == fid:
								lyr.select(fid)
			if continuityCheck:
				names = continuityLog.split('\n')
				for n in names:
					name = n.split(' ')[0].strip()
					if len(name) > 0:
						lyr = lineDict[name][2]
						fid = lineDict[name][1]
						idFld = lyr.fields()[0]
						filter = '"{0}" = \'{1}\''.format(idFld.name(), name)
						request = QgsFeatureRequest().setFilterExpression(filter)
						for f in lyr.getFeatures(request):
							if f.id() == fid:
								lyr.select(fid)
			if correctDirectionByGradient:
				names = correctDirectionGradLog.split('\n')
				for n in names:
					name = n.split(' ')[0].strip()
					if len(name) > 0:
						lyr = lineDict[name][2]
						fid = lineDict[name][1]
						idFld = lyr.fields()[0]
						filter = '"{0}" = \'{1}\''.format(idFld.name(), name)
						request = QgsFeatureRequest().setFilterExpression(filter)
						for f in lyr.getFeatures(request):
							if f.id() == fid:
								lyr.select(fid)
			if correctDirectionByContinuity:
				names = correctDirectionContLog.split('\n')
				for n in names:
					name = n.split(' ')[0].strip()
					if len(name) > 0:
						lyr = lineDict[name][2]
						fid = lineDict[name][1]
						idFld = lyr.fields()[0]
						filter = '"{0}" = \'{1}\''.format(idFld.name(), name)
						request = QgsFeatureRequest().setFilterExpression(filter)
						for f in lyr.getFeatures(request):
							if f.id() == fid:
								lyr.select(fid)
		if outLyr:
			crs = lineLyrs[0].crs()
			crsId = crs.authid()
			outName = '_1D_integrity_check'
			outPath = os.path.join(os.path.dirname(lineLyrs[0].source()), '{0}.shp'.format(outName))
			messageLyr = QgsVectorLayer("Point?crs={0}".format(crsId), 'temp_points', 'memory')
			dp = messageLyr.dataProvider()
			dp.addAttributes([QgsField('Warning', QVariant.String), QgsField('message', QVariant.String)])
			messageLyr.updateFields()
			messageFeats = []  # list of QgsFeature objects
			# lines
			if autoSnap:
				if checkLine:
					loggedEdits = returnLogL.split('\n')
					for i, line in enumerate(editedLines):
						id, node = line.split('==')
						node = int(node)
						vertex = lineDict[id][0][node]
						feat = QgsFeature()
						feat.setGeometry(QgsGeometry.fromPoint(vertex))
						feat.setAttributes(['Line Snapping Edit', 'Moved Line Vertex: {0}'.format(loggedEdits[i])])
						messageFeats.append(feat)
				if checkPoint:
					loggedEdits = returnLogP.split('\n')
					for i, point in enumerate(editedPoints):
						vertex = pointDict[point][0][0]
						feat = QgsFeature()
						feat.setGeometry(QgsGeometry.fromPoint(vertex))
						feat.setAttributes(['Point Snapping Edit', 'Moved Point: {0}'.format(loggedEdits[i])])
						messageFeats.append(feat)
			if checkLine:
				for line in unsnappedLines:
					if 'upstream' in line:
						ind = line.find('upstream')
						node = 0
					elif 'downstream' in line:
						ind = line.find('downstream')
						node = 1
					else:
						return
					id = line[:ind].strip()
					vertex = lineDict[id][0][node]
					feat = QgsFeature()
					feat.setGeometry(QgsGeometry.fromPoint(vertex))
					feat.setAttributes(
						['Line Snapping Warning', 'Unsnapped Line: {0} at {1}, {2}'.format(line, vertex[0], vertex[1])])
					messageFeats.append(feat)
			if checkPoint:
				for point in unsnappedPoints:
					vertex = pointDict[point][0][0]
					feat = QgsFeature()
					feat.setGeometry(QgsGeometry.fromPoint(vertex))
					feat.setAttributes(['Point Snapping Warning',
					                    'Unsnapped Point: {0} at {1}, {2}'.format(point, vertex[0], vertex[1])])
					messageFeats.append(feat)
			if getDnsConn:
				loggedContinuityErrors = longProfile.log.split('\n')
				for i, vertex in enumerate(longProfile.warningLocation):
					feat = QgsFeature()
					feat.setGeometry(QgsGeometry.fromPoint(vertex))
					feat.setAttributes(['{0}'.format(longProfile.warningType[i]),
					                    'Continuity Warning: {0}'.format(loggedContinuityErrors[i])])
					messageFeats.append(feat)
			if continuityCheck:
				loggedContinuityErrors = continuityLog.split('\n')
				for i, vertex in enumerate(continuityError):
					feat = QgsFeature()
					feat.setGeometry(QgsGeometry.fromPoint(vertex))
					feat.setAttributes(['{0}'.format(continiuityWarningTypes[i]),
					                    'Continuity Warning: {0}'.format(loggedContinuityErrors[i])])
					messageFeats.append(feat)
			if correctDirectionByGradient:
				loggedDirectionChange = correctDirectionGradLog.split('\n')
				for i, vertex in enumerate(correctDirectionGradPoint):
					feat = QgsFeature()
					feat.setGeometry(QgsGeometry.fromPoint(vertex))
					feat.setAttributes(['{0}'.format(correctDirectionGradType[i]),
					                    'Line Direction Edit: {0}'.format(loggedDirectionChange[i])])
					messageFeats.append(feat)
			if correctDirectionByContinuity:
				loggedDirectionChange = correctDirectionContLog.split('\n')
				for i, vertex in enumerate(correctDirectionContPoint):
					feat = QgsFeature()
					feat.setGeometry(QgsGeometry.fromPoint(vertex))
					feat.setAttributes(['{0}'.format(correctDirectionContType[i]),
					                    'Line Direction Edit: {0}'.format(loggedDirectionChange[i])])
					messageFeats.append(feat)
			dp.addFeatures(messageFeats)
			messageLyr.updateExtents()
			QgsVectorFileWriter.writeAsVectorFormat(messageLyr, outPath, 'CP1250', crs, 'ESRI Shapefile')
			self.iface.addVectorLayer(outPath, outName, 'ogr')


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
		return
	
	def selectAll(self):
		for i in range(self.scenario_lw.count()):
			item = self.scenario_lw.item(i)
			self.scenario_lw.setItemSelected(item, True)
			
	def run(self):
		scenarios = []
		for i in range(self.scenario_lw.count()):
			item = self.scenario_lw.item(i)
			if item.isSelected():
				scenarios.append(item.text())
		openGisFromTcf(self.tcf, self.iface, scenarios)
		