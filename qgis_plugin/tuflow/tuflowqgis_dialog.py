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
		newname = QFileDialog.getSaveFileName(None, QString.fromLocal8Bit("Output Shapefile"), 
			self.outfilename.displayText(), "*.shp")
                if newname != None:
                	self.outfilename.setText(QString(newname))


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
#    tuflowqgis create tuflow directory structure
# ----------------------------------------------------------
from ui_tuflowqgis_create_tf_dir import *		
class tuflowqgis_create_tf_dir_dialog(QDialog, Ui_tuflowqgis_create_tf_dir):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		cLayer = self.canvas.currentLayer()
		fname = ''
		
		if cLayer:
			cName = cLayer.name()
			crs = cLayer.crs()
			crs_id = crs.authid()
			dp = cLayer.dataProvider()
			ds = dp.dataSourceUri()	
			fpath = os.path.dirname(unicode(ds))
			basename = os.path.basename(unicode(ds))
			self.outdir.setText(fpath)
			self.sourceCRS.setText(crs_id)
			ind = basename.find('|')
			if (ind>0):
				fname = basename[0:ind]
			else:
				fname = basename
		#else:
		#	QMessageBox.warning(self.iface.mainWindow(), "Setting Projection", "No layer selected, a shapefile is required for setting the model projection.")
		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outdir)
		QObject.connect(self.browseexe, SIGNAL("clicked()"), self.browse_exe)
		QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.layer_changed)
		QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)
		
		self.settings = QSettings()
		self.exe = str(self.settings.value("TUFLOW_Create_Dir/exe", os.sep).toString())
		self.exe_dir = str(self.settings.value("TUFLOW_Create_Dir/exeDir", os.sep).toString())
		
		if (len(self.exe)>3): # use last folder if stored
			self.TUFLOW_exe.setText(self.exe)
		i = 0
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if cLayer:
					if layer.name() == cName:
						self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if i == 0:
			QMessageBox.critical(self.iface.mainWindow(), "Setting Projection", "No vector data open, a shapefile is required for setting the model projection.")


	def browse_outdir(self):
		newname = QFileDialog.getExistingDirectory(None, QString.fromLocal8Bit("Output Directory"))
		if newname != None:
			self.outdir.setText(QString(newname))
	
	def browse_exe(self):
	
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW exe', self.exe_dir, "TUFLOW Executable (*.exe)")
		inFileName = str(inFileName)
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.exe = inFileName
		self.settings.setValue("TUFLOW_Create_Dir/exe", inFileName)
		self.TUFLOW_exe.setText(inFileName)
		head, tail = os.path.split(inFileName)
		if head <> os.sep and head.lower() <> 'c:\\' and head <> '':
			self.settings.setValue("TUFLOW_Create_Dir/exeDir", head)

	def layer_changed(self):
		layername = unicode(self.sourcelayer.currentText()) 
		layer = tuflowqgis_find_layer(layername)
		crs = layer.crs()
		crs_id = crs.authid()
		self.sourceCRS.setText(crs_id)
	def run(self):
		layername = unicode(self.sourcelayer.currentText())
		layer = tuflowqgis_find_layer(layername)
		crs = layer.crs()
		basedir = unicode(self.outdir.displayText()).strip()
		tfexe = unicode(self.TUFLOW_exe.displayText()).strip()
		
		QMessageBox.information( self.iface.mainWindow(),"Creating TUFLOW directory", basedir)
		
		message = tuflowqgis_create_tf_dir(self.iface, crs, basedir)
		if message <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Creating TUFLOW Directory", message)
		if (self.checkBox.isChecked()):
			tcf = os.path.join(basedir+"\\TUFLOW\\runs\\Create_Empties.tcf")
			message = run_tuflow(self.iface, tfexe, tcf)
			if message <> None:
				QMessageBox.critical(self.iface.mainWindow(), "Running TUFLOW", message)
# ----------------------------------------------------------
#    tuflowqgis import empty tuflow files
# ----------------------------------------------------------
from ui_tuflowqgis_import_empties import *
class tuflowqgis_import_empty_tf_dialog(QDialog, Ui_tuflowqgis_import_empty):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)

		QObject.connect(self.browsedir, SIGNAL("clicked()"), self.browse_empty_dir)
		QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)

		self.emptydir.setText(os.getcwd())

	def browse_empty_dir(self):
		newname = QFileDialog.getExistingDirectory(None, QString.fromLocal8Bit("Output Directory"))
		if newname != None:
			self.emptydir.setText(QString(newname))


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
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)

		QObject.connect(self.browsetcffile, SIGNAL("clicked()"), self.browse_tcf)
		QObject.connect(self.browseexe, SIGNAL("clicked()"), self.browse_exe)
		QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)

		# open settings for previous instances
		self.settings = QSettings()
		self.exe = str(self.settings.value("TUFLOW_Run_TUFLOW/exe", os.sep).toString())
		self.exe_dir = str(self.settings.value("TUFLOW_Run_TUFLOW/exeDir", os.sep).toString())
		self.tcfin = str(self.settings.value("TUFLOW_Run_TUFLOW/tcf", os.sep).toString())
		self.tcfdir = str(self.settings.value("TUFLOW_Run_TUFLOW/tcfDir", os.sep).toString())
		
		if (len(self.tcfin)>3): # use last folder if stored
			self.tcf.setText(self.tcfin)
		
		if (len(self.exe)>3): # use last folder if stored
			self.TUFLOW_exe.setText(self.exe)

	def browse_tcf(self):
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW Control File', self.tcfdir, "TUFLOW Control File (*.tcf)")
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
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW exe', self.exe_dir, "TUFLOW Executable (*.exe)")
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
			for key,value in datacolumns.items():
				#print str(key) + " = " + str(value.name())
				self.elev_attr.addItem(str(value.name()))
				if str(value.name()).lower() == 'z':
					self.elev_attr.setCurrentIndex(key)
				elif str(value.name()).lower() == 'elevation':
					self.elev_attr.setCurrentIndex(key)

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
		newname = QFileDialog.getSaveFileName(None, QString.fromLocal8Bit("Output Shapefile"), 
			self.outfilename.displayText(), "*.shp")
                if newname != None:
                	self.outfilename.setText(QString(newname))

	def source_changed(self):
		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Source Chnaged")
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
			QMessageBox.information(self.iface.mainWindow(), "debug", "looking for z")
			for key,value in datacolumns.items():
				#print str(key) + " = " + str(value.name())
				self.elev_attr.addItem(str(value.name()))
				if str(value.name()).lower() == 'z':
					self.elev_attr.setCurrentIndex(key)
				elif str(value.name()).lower() == 'elevation':
					self.elev_attr.setCurrentIndex(key)
			

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
			if not QgsVectorFileWriter.deleteShapeFile(QString(savename)):
				message =  "Failure deleting existing shapefile: " + savename
	
		outfile = QgsVectorFileWriter(QString(savename), QString("System"), 
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
class tuflowqgis_configure_tf_dialog(QDialog, Ui_tuflowqgis_configure_tf):
	def __init__(self, iface, project):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		self.project = project
		cLayer = self.canvas.currentLayer()
		fname = ''
		try:		
			tffolder = project.readEntry("configure_tuflow", "folder", "Not yet set")[0]
			QMessageBox.information( self.iface.mainWindow(),"Directory", tffolder)
			self.outdir.setText(tffolder)
		except:
			QMessageBox.critical( self.iface.mainWindow(),"Error", "Reading from project file")
		try:		
			tfexe = project.readEntry("configure_tuflow", "exe", "Not yet set")[0]
			QMessageBox.information( self.iface.mainWindow(),"Exe", tfexe)
			self.TUFLOW_exe.setText(tfexe)
		except:
			QMessageBox.critical( self.iface.mainWindow(),"Error", "Reading from project file")
		try:
			tf_prj = project.readEntry("configure_tuflow", "projection", "Undefined")[0]
			self.sourceCRS.setText(tf_prj)
			QMessageBox.information( self.iface.mainWindow(),"Projection", tf_prj)
		except:
			QMessageBox.critical( self.iface.mainWindow(),"Error", "Reading from project file")
		#QgsProject.instance().writeEntry(plugin_name, property, value)
		QMessageBox.information( self.iface.mainWindow(),"Debug", "checking projection")
		if tf_prj == "Undefined":
			QMessageBox.information( self.iface.mainWindow(),"Debug", "undefined")
			if cLayer:
				cName = cLayer.name()
				crs = cLayer.crs()
				crs_id = crs.authid()
				crs_prj = crs.toProj4()
				self.sourceCRS.setText(crs_prj)
				# dp = cLayer.dataProvider()
				# ds = dp.dataSourceUri()	
				# basename = os.path.basename(unicode(ds))
				# ind = basename.find('|')
				# if (ind>0):
					# fname = basename[0:ind]
				# else:
					# fname = basename

		QObject.connect(self.browseoutfile, SIGNAL("clicked()"), self.browse_outdir)
		QObject.connect(self.browseexe, SIGNAL("clicked()"), self.browse_exe)
		QObject.connect(self.sourcelayer, SIGNAL("currentIndexChanged(int)"), self.layer_changed)
		QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.run)
		

		i = 0
		if tf_prj != "Undefined":
			self.sourcelayer.addItem("Use saved projection")
			cLayer = False
			self.sourcelayer.setCurrentIndex(0)
		for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
			if layer.type() == QgsMapLayer.VectorLayer:
				self.sourcelayer.addItem(layer.name())
				if cLayer:
					if layer.name() == cName:
						self.sourcelayer.setCurrentIndex(i)
				i = i + 1
		if i == 0:
			QMessageBox.critical(self.iface.mainWindow(), "Setting Projection", "No vector data open, a shapefile is required for setting the model projection.")


	def browse_outdir(self):
		newname = QFileDialog.getExistingDirectory(None, QString.fromLocal8Bit("Output Directory"))
		if newname != None:
			self.outdir.setText(QString(newname))
	
	def browse_exe(self):
	
		# Get the file name
		inFileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), 'Select TUFLOW exe', "", "TUFLOW Executable (*.exe)")
		inFileName = str(inFileName)
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.TUFLOW_exe.setText(inFileName)

	def layer_changed(self):
		layername = unicode(self.sourcelayer.currentText()) 
		if layername != "Use saved projection":
			layer = tuflowqgis_find_layer(layername)
			if layer != None:
				crs = layer.crs()
				crs_id = crs.authid()
				crs_prj = crs.toProj4()
				self.sourceCRS.setText(crs_prj)
	def run(self):
		QMessageBox.information( self.iface.mainWindow(),"debug", "Saving TUFLOW configuration to project file")
		tf_prj = unicode(self.sourceCRS.displayText()).strip()
		basedir = unicode(self.outdir.displayText()).strip()
		tfexe = unicode(self.TUFLOW_exe.displayText()).strip()
		#writes
		self.project.writeEntry("configure_tuflow", "exe", tfexe)
		self.project.writeEntry("configure_tuflow", "folder", basedir)
		self.project.writeEntry("configure_tuflow", "projection", tf_prj)
		QMessageBox.information( self.iface.mainWindow(),"Debug", "Done")
		
