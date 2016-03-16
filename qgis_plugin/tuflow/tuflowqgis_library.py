"""
 --------------------------------------------------------
		tuflowqgis_library - tuflowqgis operation functions
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

import csv
import sys
import time
import os.path
import operator

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from math import *
import numpy
import matplotlib
import glob # MJS 11/02
import tuflowqgis_styles

# --------------------------------------------------------
#    tuflowqgis Utility Functions
# --------------------------------------------------------

def tuflowqgis_find_layer(layer_name):

	for name, search_layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
		if search_layer.name() == layer_name:
			return search_layer

	return None
	
def tuflowqgis_duplicate_file(qgis, layer, savename, keepform):
	if (layer == None) and (layer.type() != QgsMapLayer.VectorLayer):
		return "Invalid Vector Layer " + layer.name()
		
	# Create output file
	if len(savename) <= 0:
		return "Invalid output filename given"
	
	if QFile(savename).exists():
		if not QgsVectorFileWriter.deleteShapeFile(savename):
			return "Failure deleting existing shapefile: " + savename
	
	outfile = QgsVectorFileWriter(savename, "System", 
		layer.dataProvider().fields(), layer.dataProvider().geometryType(), layer.dataProvider().crs())
	
	if (outfile.hasError() != QgsVectorFileWriter.NoError):
		return "Failure creating output shapefile: " + unicode(outfile.errorMessage())	
		
	# Iterate through each feature in the source layer
	feature_count = layer.dataProvider().featureCount()

	#feature = QgsFeature()
	#layer.dataProvider().select(layer.dataProvider().attributeIndexes())
	#layer.dataProvider().rewind()
	for f in layer.getFeatures():
	#while layer.dataProvider().nextFeature(feature):
		outfile.addFeature(f)
		
	del outfile
	
	# create qml from input layer
	if keepform:
		qml = savename.replace('.shp','.qml')
		if QFile(qml).exists():
			return "QML File for output already exists."
		else:
			QMessageBox.information(qgis.mainWindow(),"Info", "Creating QML")
			layer.saveNamedStyle(qml)
			QMessageBox.information(qgis.mainWindow(),"Info", "Done")
	
	return None

def tuflowqgis_create_tf_dir(qgis, crs, basepath):
	if (crs == None):
		return "No CRS specified"

	if (basepath == None):
		return "Invalid location specified"
	
	# Create folders, ignore top level (e.g. model, as these are create when the subfolders are created)
	TUFLOW_Folders = ["\\bc_dbase","\\check", "\\model\gis\\empty", "\\results", "\\runs\\log"]
	for x in TUFLOW_Folders:
		tmppath = os.path.join(basepath+"\\TUFLOW"+x)
		if os.path.isdir(tmppath):
			print "Directory Exists"
		else:
			print "Creating Directory"
			os.makedirs(tmppath)

			
	# Write Projection.prj Create a file ('w' for write, creates if doesnt exit)
	prjname = os.path.join(basepath+"\\TUFLOW\\model\\gis\Projection.shp")
	if len(prjname) <= 0:
		return "Error creating projection filename"

	if QFile(prjname).exists():
		return "Projection file already exists: "+prjname

	fields = QgsFields()
	fields.append( QgsField( "notes", QVariant.String ) )
	outfile = QgsVectorFileWriter(prjname, "System", fields, QGis.WKBPoint, crs, "ESRI Shapefile")
	
	if (outfile.hasError() != QgsVectorFileWriter.NoError):
		return "Failure creating output shapefile: " + unicode(outfile.errorMessage())	

	del outfile

	# Write .tcf file
	tcf = os.path.join(basepath+"\\TUFLOW\\runs\\Create_Empties.tcf")
	f = file(tcf, 'w')
	f.write("GIS FORMAT == SHP\n")
	f.write("SHP Projection == ..\model\gis\projection.prj\n")
	f.write("Write Empty GIS Files == ..\model\gis\empty\n")
	f.flush()
	f.close()
	QMessageBox.information(qgis.mainWindow(),"Information", "TUFLOW folder successfully created: "+basepath)
	return None

def tuflowqgis_import_empty_tf(qgis, basepath, runID, empty_types, points, lines, regions):
	if (len(empty_types) == 0):
		return "No Empty File T specified"

	if (basepath == None):
		return "Invalid location specified"
	
	if ((not points) and (not lines) and (not regions)):
		return "No Geometry types selected"
	
	geom_type = []
	if (points):
		geom_type.append('_P')
	if (lines):
		geom_type.append('_L')
	if (regions):
		geom_type.append('_R')
	
	gis_folder = basepath.replace('\empty','')
	# Create folders, ignore top level (e.g. model, as these are create when the subfolders are created)
	for type in empty_types:
		for geom in geom_type:
			fpath = os.path.join(basepath+"\\"+type+"_empty"+geom+".shp")
			#QMessageBox.information(qgis.mainWindow(),"Creating TUFLOW directory", fpath)
			if (os.path.isfile(fpath)):
				layer = QgsVectorLayer(fpath, "tmp", "ogr")
				name = str(type)+'_'+str(runID)+str(geom)+'.shp'
				savename = os.path.join(gis_folder+"\\"+name)
				if QFile(savename).exists():
					QMessageBox.critical(qgis.mainWindow(),"Info", ("File Exists: "+savename))
				#outfile = QgsVectorFileWriter(QString(savename), QString("System"), 
				outfile = QgsVectorFileWriter(savename, "System", 
					layer.dataProvider().fields(), layer.dataProvider().geometryType(), layer.dataProvider().crs())
				if (outfile.hasError() != QgsVectorFileWriter.NoError):
					QMessageBox.critical(qgis.mainWindow(),"Info", ("Error Creating: "+savename))
				del outfile
				qgis.addVectorLayer(savename, name, "ogr")

	return None
	
def tuflowqgis_get_selected_IDs(qgis,layer):
	QMessageBox.information(qgis.mainWindow(),"Info", "Entering tuflowqgis_get_selected_IDs")
	IDs = []
	if (layer == None) and (layer.type() != QgsMapLayer.VectorLayer):
		return None, "Invalid Vector Layer " + layer.name()

	dataprovider = layer.dataProvider()
	idx = layer.fieldNameIndex('ID')
	QMessageBox.information(qgis.mainWindow(),"IDX", str(idx))
	if (idx == -1):
		QMessageBox.critical(qgis.mainWindow(),"Info", "ID field not found in current layer")
		return None, "ID field not found in current layer"
	
	for feature in layer.selectedFeatures():
		id = feature.attributeMap()[idx].toString()
		IDs.append(id)
	return IDs, None

def check_python_lib(qgis):
	error = False
	py_modules = []
	try:
		py_modules.append('numpy')
		import numpy
	except:
		error = True
		QMessageBox.critical(qgis.mainWindow(),"Error", "python library 'numpy' not installed.")
	try:
		py_modules.append('csv')
		import csv
	except:
		error = True
		QMessageBox.critical(qgis.mainWindow(),"Error", "python library 'csv' not installed.")
	try:
		py_modules.append('matplotlib')
		import matplotlib
	except:
		error = True
		QMessageBox.critical(qgis.mainWindow(),"Error", "python library 'matplotlib' not installed.")
	try:
		py_modules.append('PyQt4')
		import PyQt4
	except:
		error = True
		QMessageBox.critical(qgis.mainWindow(),"Error", "python library 'PyQt4' not installed.")
	try:
		py_modules.append('osgeo.ogr')
		import osgeo.ogr as ogr
	except:
		error = True
		QMessageBox.critical(qgis.mainWindow(),"Error", "python library 'osgeo.ogr' not installed.")
	try:
		py_modules.append('glob')
		import glob
	except:
		error = True
		QMessageBox.critical(qgis.mainWindow(),"Error", "python library 'glob' not installed.")
	try:
		py_modules.append('os')
		import os
	except:
		error = True
		QMessageBox.critical(qgis.mainWindow(),"Error", "python library 'os' not installed.")
	msg = 'Modules tested: \n'
	for mod in py_modules:
		msg = msg+mod+'\n'
	QMessageBox.information(qgis.mainWindow(),"Information", msg)
	
	if error:
		return True
	else:
		return None
		
def run_tuflow(qgis,tfexe,tcf):
	
	#QMessageBox.Information(qgis.mainWindow(),"debug", "Running TUFLOW")
	try:
		from subprocess import Popen
		tfarg = [tfexe, '-b',tcf]
		tf_proc = Popen(tfarg)
	except:
		return "Error occurred starting TUFLOW"
	#QMessageBox.Information(qgis.mainWindow(),"debug", "TUFLOW started")
	return None

def config_set(project,tuflow_folder,tfexe,projection):
	message = None
	try:
		f = file(config_file, 'w')
		f.write('TUFLOW Folder =='+tuflow_folder+'\n')
		f.write('TUFLOW Exe =='+tfexe+'\n')
		f.write('PROJECTION =='+proj+'\n')
		f.flush()
		f.close()
	except:
		message = "Unable to write TUFLOW config file: "+config_file

	return message
	
def extract_all_points(qgis,layer,col):
	
	#QMessageBox.Information(qgis.mainWindow(),"debug", "starting to extract points")
	try:
		iter = layer.getFeatures()
		npt = 0
		x = []
		y = []
		z = []
		for feature in iter:
			npt = npt + 1
			geom = feat.geometry()
			#QMessageBox.Information(qgis.mainWindow(),"debug", "x = "+str(geom.x())+", y = "+str(geom.y()))
			x.append(geom.x())
			y.append(geom.y())
			zt = feature.attributeMap()[col]
			#QMessageBox.Information(qgis.mainWindow(),"debug", "z = "+str(zt))
			z.append(zt)
		return x, y, z, message
	except:
		return None, None, None, "Error extracting point data"

def get_file_ext(fname):
	try:
		ind = fname.find('|')
		if (ind>0):
			fname = fname[0:ind]
	except:
		return None, None, "Error trimming filename"
	try:
		ind = fname.rfind('.')
		if (ind>0):
			fext = fname[ind+1:]
			fext = fext.upper()
			fname_noext = fname[0:ind]
			return fext, fname_noext, None
		else:
			return None, None, "Could not find . in filename"
	except:
		return None, None, "Error trimming filename"

def load_project(project):
	message = None
	try:
		tffolder = project.readEntry("configure_tuflow", "folder", "Not yet set")[0]
	except:
		message = "Error - Reading from project file."

	try:
		tfexe = project.readEntry("configure_tuflow", "exe", "Not yet set")[0]
	except:
		message = "Error - Reading from project file."

	try:
		tf_prj = project.readEntry("configure_tuflow", "projection", "Undefined")[0]
	except:
		message = "Error - Reading from project file."
	
	error = False
	if (tffolder == "Not yet set"):
		error = True
	if (tfexe == "Not yet set"):
		error = True
	if (tf_prj == "Undefined"):
		error = True
	if error:
		message = "Project does not appear to be configured.\nPlease run TUFLOW >> Editing >> Configure Project from the plugin menu."
	
	return message, tffolder, tfexe, tf_prj
 
#  tuflowqgis_import_check_tf added MJS 11/02
def tuflowqgis_import_check_tf(qgis, basepath, runID,showchecks):
	#import check file styles using class
	tf_styles = tuflowqgis_styles.TF_Styles()
	error, message = tf_styles.Load()
	if error:
		QMessageBox.critical(qgis.mainWindow(),"Error", message)
		return message

	if (basepath == None):
		return "Invalid location specified"

	# Get all the check files in the given directory
	check_files = glob.glob(basepath +  '\*'+ runID +'*.shp')

	if len(check_files) > 100:
		QMessageBox.critical(qgis.mainWindow(),"Info", ("You have selected over 100 check files. You can use the RunID to reduce this selection."))
		return "Too many check files selected"

	if not check_files:
		check_files = glob.glob(basepath +  '\*'+ runID +'*.mif')
		if len(check_files) > 0: 
			return ".MIF Files are not supported, only .SHP files."
		else:
			return "No check files found for this RunID in this location."

	# Get the legend interface
	legint = qgis.legendInterface()

	# Add each layer to QGIS and style
	for chk in check_files:
		pfft,fname = os.path.split(chk)
		#QMessageBox.information(qgis.mainWindow(),"Debug", fname)
		fname = fname[:-4]
		layer = qgis.addVectorLayer(chk, fname, "ogr")
		renderer = region_renderer(layer)
		if renderer: #if the file requires a attribute based rendered (e.g. BC_Name for a _sac_check_R)
			layer.setRendererV2(renderer)
			layer.triggerRepaint()
		else: # use .qml style using tf_styles
			error, message, slyr = tf_styles.Find(fname) #use tuflow styles to find longest matching 
			if error:
				QMessageBox.critical(qgis.mainWindow(),"ERROR", message)
				return message
			if slyr: #style layer found:
				layer.loadNamedStyle(slyr)
				if os.path.split(slyr)[1][:-4] == '_zpt_check':
					legint.setLayerVisible(layer, False)   # Switch off by default
				elif '_uvpt_check' in fname or '_grd_check' in fname:
					legint.setLayerVisible(layer, False)
				if not showchecks:
					legint.setLayerVisible(layer, False)

	message = None #normal return
	return message


#  region_renderer added MJS 11/02
def region_renderer(layer):
	from random import randrange

	#check if layer needs a renderer
	fsource = layer.source() #includes full filepath and extension
	fname = os.path.split(fsource)[1][:-4] #without extension
	
	if '_bcc_check_R' in fname:
		field_name = 'Source'
	elif '_1d_to_2d_check_R' in fname:
		field_name = 'Primary_No'
	elif '_2d_to_2d_R' in fname:
		field_name = 'Primary_No'
	elif '_sac_check_R' in fname:
		field_name = 'BC_Name'
	else: #render not needed
		return None
		
	# Thankyou Detlev  @ http://gis.stackexchange.com/questions/175068/apply-symbol-to-each-feature-categorized-symbol

	
	# get unique values
	vals = layer.fieldNameIndex(field_name)
	unique_values = layer.dataProvider().uniqueValues(vals)
	#QgsMessageLog.logMessage('These values have been identified: ' + vals, "TUFLOW")

	# define categories
	categories = []
	for unique_value in unique_values:
		# initialize the default symbol for this geometry type
		symbol = QgsSymbolV2.defaultSymbol(layer.geometryType())

		# configure a symbol layer
		layer_style = {}
		layer_style['color'] = '%d, %d, %d' % (randrange(0,256), randrange(0,256), randrange(0,256))
		layer_style['outline'] = '#000000'
		symbol_layer = QgsSimpleFillSymbolLayerV2.create(layer_style)

		# replace default symbol layer with the configured one
		if symbol_layer is not None:
			symbol.changeSymbolLayer(0, symbol_layer)

		# create renderer object
		category = QgsRendererCategoryV2(unique_value, symbol, str(unique_value))
		# entry for the list of category items
		categories.append(category)

	# create renderer object
	return QgsCategorizedSymbolRendererV2(field_name, categories)
	
def tuflowqgis_apply_check_tf(qgis):
	#apply check file styles to all open shapefiles
	error = False
	message = None

	#load style layers using tuflowqgis_styles
	tf_styles = tuflowqgis_styles.TF_Styles()
	error, message = tf_styles.Load()
	if error:
		return error, message
		
	for layer_name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
		if layer.type() == QgsMapLayer.VectorLayer:
			if (layer.source()[-4:].upper() == '.SHP'):
				layer_fname = os.path.split(layer.source())[1][:-4]
				#QMessageBox.information(qgis.mainWindow(), "DEBUG", "shp layer name = "+layer.name())
				renderer = region_renderer(layer)
				if renderer: #if the file requires a attribute based rendered (e.g. BC_Name for a _sac_check_R)
					layer.setRendererV2(renderer)
					layer.triggerRepaint()
				else: # use .qml style using tf_styles
					error, message, slyr = tf_styles.Find(layer_fname) #use tuflow styles to find longest matching 
					if error:
						return error, message
					if slyr: #style layer found:
						layer.loadNamedStyle(slyr)
						layer.triggerRepaint()
	return error, message
	

def tuflowqgis_apply_check_tf_clayer(qgis):
	error = False
	message = None
	try:
		canvas = qgis.mapCanvas()
	except:
		error = True
		message = "ERROR - Unexpected error trying to  QGIS canvas layer."
		return error, message
	try:
		cLayer = canvas.currentLayer()
	except:
		error = True
		message = "ERROR - Unable to get current layer, ensure a selection is made"
		return error, message
	
	#load style layers using tuflowqgis_styles
	tf_styles = tuflowqgis_styles.TF_Styles()
	error, message = tf_styles.Load()
	if error:
		return error, message
		

	if cLayer.type() == QgsMapLayer.VectorLayer:
		if (cLayer.source()[-4:].upper() == '.SHP'):
			layer_fname = os.path.split(cLayer.source())[1][:-4]
			#QMessageBox.information(qgis.mainWindow(), "DEBUG", "shp layer name = "+cLayer.name())
			renderer = region_renderer(cLayer)
			if renderer: #if the file requires a attribute based rendered (e.g. BC_Name for a _sac_check_R)
				cLayer.setRendererV2(renderer)
				cLayer.triggerRepaint()
			else: # use .qml style using tf_styles
				error, message, slyr = tf_styles.Find(layer_fname) #use tuflow styles to find longest matching 
				if error:
					return error, message
				if slyr: #style layer found:
					cLayer.loadNamedStyle(slyr)
					cLayer.triggerRepaint()
		else:
			error = True
			message = 'ERROR - Layer is not a shapefile: '+cLayer.source()
			return error, message
	else:
		error = True
		message = 'ERROR - Layer is not a vector layer: '+cLayer.source()
		return error, message
	return error, message