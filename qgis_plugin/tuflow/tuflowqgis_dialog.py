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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import glob
from tuflowqgis_library import *

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms")


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
		fname = ''
		fpath = None
		
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

		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outfile)
		QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
		i = 0
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if layer.name() == cName:
					self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if (fpath):
			self.outfolder.setText(fpath)
			self.outfilename.setText(fpath + "/"+fname)
		else:
			self.outfolder.setText('No layer currently open!')
			self.outfilename.setText('No layer currently open!')

        def browse_outfile(self):
		newname = QFileDialog.getSaveFileName(None, "Output Shapefile", 
			self.outfilename.displayText(), "*.shp")
                if newname != None:
                	self.outfilename.setText(newname)


	def run(self):
		if self.checkBox.isChecked():
			keepform = True
		else:
			keepform = False
		layername = unicode(self.sourcelayer.currentText())
		layer = tuflowqgis_find_layer(layername)
		savename = unicode(self.outfilename.displayText()).strip()
		#QMessageBox.information( self.iface.mainWindow(),"Info", savename )
		message = tuflowqgis_duplicate_file(self.iface, layer, savename, keepform)
		if message <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Duplicating File", message)
		QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
		self.iface.addVectorLayer(savename, os.path.basename(savename), "ogr")


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
		self.settings = TF_Settings()
		
		# load stored settings
		error, message = self.settings.Load()
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", "Error Loading Settings: "+message)
		
		#QMessageBox.information( self.iface.mainWindow(),"debug", "project: "+str(self.settings.project_settings.base_dir))
		#QMessageBox.information( self.iface.mainWindow(),"debug", "global: "+str(self.settings.global_settings.base_dir))
		#QMessageBox.information( self.iface.mainWindow(),"debug", "combined: "+str(self.settings.combined.base_dir))
		
		QObject.connect(self.browsedir, SIGNAL("clicked()"), self.browse_empty_dir)
		QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)

		if self.settings.combined.base_dir:
			self.emptydir.setText(self.settings.combined.base_dir+"\\TUFLOW\\model\\gis\\empty")
		else:
			self.emptydir.setText("ERROR - Project not loaded")

	def browse_empty_dir(self):
		newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		if newname != None:
			self.emptydir.setText(newname)


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
class tuflowqgis_run_tf_simple_dialog(QDialog, Ui_tuflowqgis_run_tf_simple):
	def __init__(self, iface, project):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)

		# load settting from project file
		message, tffolder, tfexe, tf_prj = load_project(project)
		self.runfolder = tffolder+"\\TUFLOW\\runs\\"
		self.exefolder = os.path.dirname(tfexe)
		if message != None:
			QMessageBox.critical( self.iface.mainWindow(),"Error", message)
		self.TUFLOW_exe.setText(tfexe)
		
		QObject.connect(self.browsetcffile, SIGNAL("clicked()"), self.browse_tcf)
		QObject.connect(self.browseexe, SIGNAL("clicked()"), self.browse_exe)
		QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)

		files = glob.glob(unicode(tffolder)+"\\TUFLOW\\runs\\*.tcf")
		self.tcfin=''
		if (len(files) > 0):
			files.sort(key=os.path.getmtime, reverse=True)
			self.tcfin = files[0]
		if (len(self.tcfin)>3):
			self.tcf.setText(self.tcfin)
		# open settings for previous instances
		#self.settings = QSettings()
		#self.exe = str(self.settings.value("TUFLOW_Run_TUFLOW/exe", os.sep).toString())
		#self.exe_dir = str(self.settings.value("TUFLOW_Run_TUFLOW/exeDir", os.sep).toString())
		#self.tcfin = str(self.settings.value("TUFLOW_Run_TUFLOW/tcf", os.sep).toString())
		#self.tcfdir = str(self.settings.value("TUFLOW_Run_TUFLOW/tcfDir", os.sep).toString())
		

		
		#if (len(self.exe)>3): # use last folder if stored
		#	self.TUFLOW_exe.setText(self.exe)

	def browse_tcf(self):
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW Control File', self.runfolder, "TUFLOW Control File (*.tcf)")
		inFileName = str(inFileName)
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.tcfin = inFileName
		self.settings.setValue("TUFLOW_Run_TUFLOW/tcf", inFileName)
		self.tcf.setText(inFileName)
		head, tail = os.path.split(inFileName)
		if head <> os.sep and head.lower() <> 'c:\\' and head <> '':
			self.settings.setValue("TUFLOW_Run_TUFLOW/tcfDir", head)

	def browse_exe(self):
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW exe', self.exefolder, "TUFLOW Executable (*.exe)")
		inFileName = str(inFileName)
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.exe = inFileName
		self.settings.setValue("TUFLOW_Run_TUFLOW/exe", inFileName)
		self.TUFLOW_exe.setText(inFileName)
		head, tail = os.path.split(inFileName)
		if head <> os.sep and head.lower() <> 'c:\\' and head <> '':
			self.settings.setValue("TUFLOW_Run_TUFLOW/exeDir", head)

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
			QMessageBox.information(self.iface.mainWindow(), "DEBUG", "populate columns layers")
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

		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "populate source layers")
		i = 0
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
			QMessageBox.information(self.iface.mainWindow(), "DEBUG", "populate source layers")
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
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Source Changed")
		layername = unicode(self.sourcelayer.currentText())
		self.cLayer = tuflowqgis_find_layer(layername)
		self.elev_attr.clear()
		if self.cLayer and (self.cLayer.type() == QgsMapLayer.VectorLayer):
			#QMessageBox.information(self.iface.mainWindow(), "DEBUG", self.cLayer.name())
			datacolumns = self.cLayer.dataProvider().fields()
			GType = self.cLayer.dataProvider().geometryType()
			if (GType == QGis.WKBPoint):
				QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Point geometry layer")
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
			QMessageBox.criticl( self.iface.mainWindow(),"Error", "Error converting input distance to numeric data type.  Make sure a number is specified." )
		QMessageBox.information( self.iface.mainWindow(),"debug", "starting" )
		
		npt = 0
		x = []
		y = []
		z = []
		feature = QgsFeature()
		self.layer.dataProvider().select(self.layer.dataProvider().attributeIndexes())
		self.layer.dataProvider().rewind()
		feature_count = self.layer.dataProvider().featureCount()
		QMessageBox.information(self.iface.mainWindow(),"debug", "count = "+str(feature_count))
		while self.layer.dataProvider().nextFeature(feature):
			npt = npt + 1
			geom = feature.geometry()
			xn = geom.asPoint().x()
			yn = geom.asPoint().y()
			x.append(xn)
			y.append(yn)
			zn = feature.attributeMap()[z_col].toString()
			if npt == 1:
				QMessageBox.information(self.iface.mainWindow(),"debug", "x = "+str(xn)+", y = "+str(yn))
				QMessageBox.information(self.iface.mainWindow(),"debug", "z = "+zn)
			z.append(float(zn))
		QMessageBox.information(self.iface.mainWindow(),"debug", "finished reading points")	
		QMessageBox.information(self.iface.mainWindow(),"debug", "npts read = "+str(npt))
		
		# Create output file
		v_layer = QgsVectorLayer("LineString", "line", "memory")
		pr = v_layer.dataProvider()
		
		# add fields
		fields = { 0 : QgsField("z", QVariant.Double),1 : QgsField("dz", QVariant.Double),2 : QgsField("width", QVariant.Double),3 : QgsField("Options", QVariant.String) }
		#pr.addAttributes( [ QgsField("Z", QVariant.Double),
		#	QgsField("dz",  QVariant.Double),
		#	QgsField("width",  QVariant.Double),
		#	QgsField("Options", QVariant.String) ] )
					
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
			#	QMessageBox.information(self.iface.mainWindow(),"debug", "pt2x = "+str(pt2x)+", pt2y = "+str(pt2y))
			if newline:
				pt1x = pt2x
				pt1y = pt2y
				pol = 1
				newline = False
				
			else:
				dist = math.sqrt(((pt2x - pt1x)**2)+((pt2y - pt1y)**2))
				#if pt <= 10:
				#	QMessageBox.information(self.iface.mainWindow(),"debug", "dist = "+str(dist))
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
		self.settings = TF_Settings()
		self.crs = None
		fname = ''
		#message, tffolder, tfexe, tf_prj = load_project(self.project)
		#dont give error here as it may be the first occurence
		#if message != None:
		#	QMessageBox.critical( self.iface.mainWindow(),"Error", message)
		
		# load global settings
		#QMessageBox.information( self.iface.mainWindow(),"debug", "loading gloabal settings")
		error, message = self.settings.Load()
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", "Error Loading Global Settings: "+message)
		
		#set fields
		if self.settings.project_settings.base_dir:
			self.outdir.setText(self.settings.project_settings.base_dir)
		elif self.settings.global_settings.base_dir:
			self.outdir.setText(self.settings.global_settings.base_dir)
		else:
			self.outdir.setText("Not Yet Set")
		
		if self.settings.project_settings.tf_exe:
			self.TUFLOW_exe.setText(self.settings.project_settings.tf_exe)
		elif self.settings.global_settings.tf_exe:
			self.TUFLOW_exe.setText(self.settings.global_settings.tf_exe)
		else:
			self.TUFLOW_exe.setText("Not Yet Set")

		if self.settings.project_settings.CRS_ID:
			self.form_crsID.setText(self.settings.project_settings.CRS_ID)
			self.crs = QgsCoordinateReferenceSystem()
			success = self.crs.createFromString(self.settings.project_settings.CRS_ID)
			if success:
				self.crsDesc.setText(self.crs.description())
		elif self.settings.global_settings.CRS_ID:
			self.form_crsID.setText(self.settings.global_settings.CRS_ID)
			self.crs = QgsCoordinateReferenceSystem()
			success = self.crs.createFromString(self.settings.global_settings.CRS_ID)
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
		#QMessageBox.information( self.iface.mainWindow(),"debug", "Opening Projection Selector")
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
		last_exe = self.settings.get_last_exe()			
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
		self.settings.save_last_exe(inFileName)

	def layer_changed(self):
		layername = unicode(self.sourcelayer.currentText()) 
		if layername != "Use saved projection":
			layer = tuflowqgis_find_layer(layername)
			if layer != None:
				self.crs = layer.crs()
				self.form_crsID.setText(self.crs.authid())
				self.crsDesc.setText(self.crs.description())
	def run(self):
		#QMessageBox.information( self.iface.mainWindow(),"debug", "Saving TUFLOW configuration to project file")
		tf_prj = unicode(self.form_crsID.displayText()).strip()
		basedir = unicode(self.outdir.displayText()).strip()
		tfexe = unicode(self.TUFLOW_exe.displayText()).strip()
		
		#Save Project Settings
		self.settings.project_settings.CRS_ID = tf_prj
		self.settings.project_settings.tf_exe = tfexe
		self.settings.project_settings.base_dir = basedir
		error, message = self.settings.Save_Project()
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", "Error Saving Project Settings. Message: "+message)
		else:
			QMessageBox.information( self.iface.mainWindow(),"Information", "Project Settings Saved")
		
		#Save Global Settings
		if (self.cbGlobal.isChecked()):
			self.settings.global_settings.CRS_ID = tf_prj
			self.settings.global_settings.tf_exe = tfexe
			self.settings.global_settings.base_dir = basedir
			error, message = self.settings.Save_Global()
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
				tcf = os.path.join(basedir+"\\TUFLOW\\runs\\Create_Empties.tcf")
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
		#QMessageBox.information( self.iface.mainWindow(),"debug", "run" )
		layername = unicode(self.sourcelayer.currentText())
		#QMessageBox.information( self.iface.mainWindow(),"debug", "layer name = :"+layername)
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
		#QMessageBox.information( self.iface.mainWindow(),"debug", "file extension = :"+fext)
		outfolder = unicode(self.outfolder.displayText()).strip()
		#QMessageBox.information( self.iface.mainWindow(),"debug", "folder = :"+outfolder)
		outprefix = unicode(self.outprefix.displayText()).strip()
		#QMessageBox.information( self.iface.mainWindow(),"debug", "prefix = :"+outprefix)
		#message = tuflowqgis_duplicate_file(self.iface, layer, savename, keepform)
		message, ptshp, lnshp, rgshp, npt, nln, nrg = split_MI_util(self.iface, fname, outfolder, outprefix)
		
		if message <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Error Splitting file", message)
		#QMessageBox.information( self.iface.mainWindow(),"debug", ptshp)
		#QMessageBox.information( self.iface.mainWindow(),"debug", "npts: "+str(npt))
		QMessageBox.information( self.iface.mainWindow(),"debug", "Removing existing layer")
		QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
		#self.iface.addVectorLayer(savename, os.path.basename(savename), "ogr")
		
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
		self.settings = TF_Settings()
		self.last_mi = self.settings.get_last_mi_folder()
		
		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outdir)
		QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run)
		


	def browse_outdir(self):
		#newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		newname = QFileDialog.getExistingDirectory(None, "Output Directory",self.last_mi)
		if newname != None:
			self.outfolder.setText(newname)
			self.settings.save_last_mi_folder(newname)
	
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
		QMessageBox.information( self.iface.mainWindow(),"debug", "Number of mif files = :"+str(nF))
		
		for mif_file in mif_files:
			QMessageBox.information( self.iface.mainWindow(),"debug", "mif file = \n"+mif_file)
			#error, message, points, lines, regions = splitMI_func(mif_file)
			message, fname_P, fname_L, fname_R, npts, nln, nrg = split_MI_util2(mif_file)
			
			QMessageBox.information( self.iface.mainWindow(),"debug", "done")
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
		#QMessageBox.information( self.iface.mainWindow(),"debug", "Starting flow-trace dialogue")
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		self.cLayer = self.canvas.currentLayer()
		self.lw_Log.insertItem(0,'Creating Dialogue')
		
		#QMessageBox.information( self.iface.mainWindow(),"debug", "Starting flow-trace dialogue")
		
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
		#QMessageBox.information( self.iface.mainWindow(),"debug", "Starting flow-trace run")
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
			QMessageBox.information( self.iface.mainWindow(),"debug", "Error getting selected features")
		
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
							#QMessageBox.information( self.iface.mainWindow(),"debug", "connected")
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
							#QMessageBox.information( self.iface.mainWindow(),"debug", "connected")
							final_list.append(id)
							tmp_selection.append(id)
							tf_selected[i] = True
					
				tmp_selection.pop(0)
			self.lw_Log.insertItem(0,'Finished downstream search')
		#QMessageBox.information( self.iface.mainWindow(),"debug", "Here A")
		self.cLayer.setSelectedFeatures(final_list)	
		#QMessageBox.information( self.iface.mainWindow(),"debug", "Here B")

	def run(self):
		#if self.cb_DS.isChecked():
		#	QMessageBox.information( self.iface.mainWindow(),"debug", "Downstream")
		#if self.cb_US.isChecked():
		#	QMessageBox.information( self.iface.mainWindow(),"debug", "Upstream")
		QMessageBox.information( self.iface.mainWindow(),"debug", "Use RUN button")
  
  
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
		self.settings = TF_Settings()

		# load stored settings
		self.last_chk_folder = self.settings.get_last_chk_folder()
		error, message = self.settings.Load() #exe, tuflow dircetory and projection
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", "Error Loading Settings: "+message)

		QObject.connect(self.browsedir, SIGNAL("clicked()"), self.browse_empty_dir)
		QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)

		if (self.last_chk_folder == "Undefined"):
			if self.settings.combined.base_dir:
				self.last_chk_folder = os.path.join(self.settings.combined.base_dir,"TUFLOW","Check")
				self.emptydir.setText(self.last_chk_folder)
		#	self.emptydir.setText(self.settings.combined.base_dir+"\\TUFLOW\\check")
		else:
			self.emptydir.setText(self.last_chk_folder)
		#self.emptydir.setText = self.settings.get_last_mi_folder()

	def browse_empty_dir(self):
		newname = QFileDialog.getExistingDirectory(None, "Output Directory",self.last_chk_folder)
		if newname != None:
			try:
				self.emptydir.setText(newname)
				self.settings.save_last_chk_folder(newname)
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
