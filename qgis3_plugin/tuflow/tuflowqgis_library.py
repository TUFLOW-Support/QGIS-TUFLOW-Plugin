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
from datetime import datetime, timedelta
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.gui import *
from qgis.core import *
from PyQt5.QtWidgets import *
from math import *
import numpy
import matplotlib
from datetime import datetime
import glob # MJS 11/02

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import tuflowqgis_styles

# --------------------------------------------------------
#    tuflowqgis Utility Functions
# --------------------------------------------------------

def tuflowqgis_find_layer(layer_name, **kwargs):
	
	search_type = kwargs['search_type'] if 'search_type' in kwargs.keys() else 'name'

	for name, search_layer in QgsProject.instance().mapLayers().items():
		if search_type.lower() == 'name':
			if search_layer.name() == layer_name:
				return search_layer
		elif search_type.lower() == 'layerid':
			if name == layer_name:
				return search_layer

	return None

def tuflowqgis_find_plot_layers():

	plotLayers = []

	for name, search_layer in QgsProject.instance().mapLayers().items():
		if '_PLOT_P' in search_layer.name() or 'PLOT_L' in search_layer.name():
			plotLayers.append(search_layer)
		if len(plotLayers) == 2:
			return plotLayers

	if len(plotLayers) == 1:
		return plotLayers
	else:
		return None


def findAllRasterLyrs():
	"""
	Finds all open raster layers

	:return: list -> str layer name
	"""
	
	rasterLyrs = []
	for name, search_layer in QgsProject.instance().mapLayers().items():
		if search_layer.type() == 1:
			rasterLyrs.append(search_layer.name())
	
	return rasterLyrs


def findAllMeshLyrs():
	"""
	Finds all open mesh layers
	
	:return: list -> str layer name
	"""
	
	meshLyrs = []
	for name, search_layer in QgsProject.instance().mapLayers().items():
		if search_layer.type() == 3:
			meshLyrs.append(search_layer.name())
	
	return meshLyrs

	
def tuflowqgis_duplicate_file(qgis, layer, savename, keepform):
	if (layer == None) and (layer.type() != QgsMapLayer.VectorLayer):
		return "Invalid Vector Layer " + layer.name()
		
	# Create output file
	if len(savename) <= 0:
		return "Invalid output filename given"
	
	if QFile(savename).exists():
		if not QgsVectorFileWriter.deleteShapeFile(savename):
			return "Failure deleting existing shapefile: " + savename
	
	outfile = QgsVectorFileWriter(vectorFileName=savename, fileEncoding="System", 
		fields=layer.dataProvider().fields(), geometryType=layer.wkbType(), srs=layer.dataProvider().sourceCrs(), driverName="ESRI Shapefile")
	
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
			layer.saveNamedStyle(qml)
	
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
			print("Directory Exists")
		else:
			print("Creating Directory")
			os.makedirs(tmppath)

			
	# Write Projection.prj Create a file ('w' for write, creates if doesnt exit)
	prjname = os.path.join(basepath+"\\TUFLOW\\model\\gis\Projection.shp")
	if len(prjname) <= 0:
		return "Error creating projection filename"

	if QFile(prjname).exists():
		return "Projection file already exists: "+prjname

	fields = QgsFields()
	fields.append( QgsField( "notes", QVariant.String ) )
	outfile = QgsVectorFileWriter(prjname, "System", fields, 1, crs, "ESRI Shapefile")
	
	if (outfile.hasError() != QgsVectorFileWriter.NoError):
		return "Failure creating output shapefile: " + unicode(outfile.errorMessage())	

	del outfile

	# Write .tcf file
	tcf = os.path.join(basepath+"\\TUFLOW\\runs\\Create_Empties.tcf")
	f = open(tcf, 'w')
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
				outfile = QgsVectorFileWriter(vectorFileName=savename, fileEncoding="System", 
					fields=layer.dataProvider().fields(), geometryType=layer.wkbType(), srs=layer.dataProvider().sourceCrs(), driverName="ESRI Shapefile")
				if (outfile.hasError() != QgsVectorFileWriter.NoError):
					QMessageBox.critical(qgis.mainWindow(),"Info", ("Error Creating: "+savename))
				del outfile
				qgis.addVectorLayer(savename, name[:-4], "ogr")

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
		py_modules.append('PyQt5')
		import PyQt5
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
	
	#QMessageBox.Information(qgis.mainWindow(),"debug", "Running TUFLOW - tcf: "+tcf)
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
		QMessageBox.information(qgis.mainWindow(),"Information", message)

	try:
		tfexe = project.readEntry("configure_tuflow", "exe", "Not yet set")[0]
	except:
		message = "Error - Reading from project file."
		QMessageBox.information(qgis.mainWindow(),"Information", message)

	try:
		tf_prj = project.readEntry("configure_tuflow", "projection", "Undefined")[0]
	except:
		message = "Error - Reading from project file."
		QMessageBox.information(qgis.mainWindow(),"Information", message)
	
	error = False
	if (tffolder == "Not yet set"):
		error = True
		QMessageBox.information(qgis.mainWindow(),"Information", "Not set tffolder")
	if (tfexe == "Not yet set"):
		error = True
		QMessageBox.information(qgis.mainWindow(),"Information", "Not set tfexe")
	if (tf_prj == "Undefined"):
		error = True
		QMessageBox.information(qgis.mainWindow(),"Information", "tf_prj")
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
	check_files = glob.glob(basepath +  '\*'+ runID +'*.shp') + glob.glob(basepath +  '\*'+ runID +'*.mif')

	if len(check_files) > 100:
		QMessageBox.critical(qgis.mainWindow(),"Info", ("You have selected over 100 check files. You can use the RunID to reduce this selection."))
		return "Too many check files selected"

	#if not check_files:
	#	check_files = glob.glob(basepath +  '\*'+ runID +'*.mif')
	#	if len(check_files) > 0: 
	#		return ".MIF Files are not supported, only .SHP files."
	#	else:
	#		return "No check files found for this RunID in this location."

	# Get the legend interface (qgis.legendInterface() no longer supported)
	legint = QgsProject.instance().layerTreeRoot()

	# Add each layer to QGIS and style
	for chk in check_files:
		pfft,fname = os.path.split(chk)
		fname = fname[:-4]
		layer = qgis.addVectorLayer(chk, fname, "ogr")
		if layer is None:  # probably a mif file with 2 geometry types, have to redefine layer object
			for layer_name, layer_object in QgsProject.instance().mapLayers().items():
				if fname in layer_name:
					layer = layer_object
		renderer = region_renderer(layer)
		if renderer: #if the file requires a attribute based rendered (e.g. BC_Name for a _sac_check_R)
			layer.setRenderer(renderer)
			layer.triggerRepaint()
		else: # use .qml style using tf_styles
			error, message, slyr = tf_styles.Find(fname, layer) #use tuflow styles to find longest matching 
			if error:
				QMessageBox.critical(qgis.mainWindow(),"ERROR", message)
				return message
			if slyr: #style layer found:
				layer.loadNamedStyle(slyr)
				#if os.path.split(slyr)[1][:-4] == '_zpt_check':
				#	legint.setLayerVisible(layer, False)   # Switch off by default
				#elif '_uvpt_check' in fname or '_grd_check' in fname:
				#	legint.setLayerVisible(layer, False)
				#if not showchecks:
				#	legint.setLayerVisible(layer, False)
				for item in legint.children():
					if 'zpt check' in item.name().lower() or 'uvpt check' in item.name().lower() or 'grd check' in item.name().lower() or \
					'zpt_check' in item.name().lower() or 'uvpt_check' in item.name().lower() or 'grd_check' in item.name().lower():
						item.setItemVisibilityChecked(False)
					elif not showchecks:
						item.setItemVisibilityChecked(False)

	message = None #normal return
	return message


#  region_renderer added MJS 11/02
def region_renderer(layer):
	from random import randrange
	registry = QgsSymbolLayerRegistry()
	symbol_layer2 = None

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
	elif '2d_bc' in fname or '2d_mat' in fname or '2d_soil' in fname or '1d_bc' in fname:
		for i, field in enumerate(layer.fields()):
			if i == 0:
				field_name = field.name()
	elif '1d_nwk' in fname or '1d_nwkb' in fname or '1d_nwke' in fname or '1d_mh' in fname or '1d_pit' in fname or \
		 '1d_nd' in fname:
		for i, field in enumerate(layer.fields()):
			if i == 1:
				field_name = field.name()
	else: #render not needed
		return None

			
	# Thankyou Detlev  @ http://gis.stackexchange.com/questions/175068/apply-symbol-to-each-feature-categorized-symbol

	
	# get unique values
	vals = layer.dataProvider().fieldNameIndex(field_name)
	unique_values = layer.dataProvider().uniqueValues(vals)
	#QgsMessageLog.logMessage('These values have been identified: ' + vals, "TUFLOW")

	# define categories
	categories = []
	for unique_value in unique_values:
		# initialize the default symbol for this geometry type
		symbol = QgsSymbol.defaultSymbol(layer.geometryType())

		# configure a symbol layer
		layer_style = {}
		color = '%d, %d, %d' % (randrange(0,256), randrange(0,256), randrange(0,256))
		layer_style['color'] = color
		layer_style['outline'] = '#000000'
		symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
		if '2d_bc' in fname:
			if layer.geometryType() == 1:
				#QMessageBox.information(qgis.mainWindow(), "DEBUG", 'line 446')
				symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
				symbol_layer.setWidth(1)
			elif layer.geometryType() == 0:
				symbol_layer = QgsSimpleMarkerSymbolLayer.create(layer_style)
				symbol_layer.setSize(2)
				symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Circle)
		elif '1d_nwk' in fname or '1d_nwkb' in fname or '1d_nwke' in fname or '1d_pit' in fname or '1d_nd' in fname:
			if layer.geometryType() == 1:
				#QMessageBox.information(qgis.mainWindow(), "DEBUG", 'line 446')
				symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
				symbol_layer.setWidth(1)
				symbol_layer2 = QgsMarkerLineSymbolLayer.create({'placement': 'lastvertex'})
				layer_style['color_border'] = color
				markerSymbol = QgsSimpleMarkerSymbolLayer.create(layer_style)
				markerSymbol.setShape(QgsSimpleMarkerSymbolLayerBase.ArrowHeadFilled)
				markerSymbol.setSize(5)
				marker =  QgsMarkerSymbol()
				marker.changeSymbolLayer(0, markerSymbol)
				symbol_layer2.setSubSymbol(marker)
				#symbol_layer.changeSymbolLayer(0, symbol_layer2)
				#markerMeta = registry.symbolLayerMetadata("MarkerLine")
				#markerLayer = markerMeta.createSymbolLayer({'width': '0.26', 'color': color, 'rotate': '1', 'placement': 'lastvertex'})
				#subSymbol = markerLayer.subSymbol()
				#subSymbol.deleteSymbolLayer(0)
				#triangle = registry.symbolLayerMetadata("SimpleMarker").createSymbolLayer({'name': 'filled_arrowhead', 'color': color, 'color_border': color, 'offset': '0,0', 'size': '4', 'angle': '0'})
				#subSymbol.appendSymbolLayer(triangle)
			elif layer.geometryType() == 0:
				symbol_layer = QgsSimpleMarkerSymbolLayer.create(layer_style)
				symbol_layer.setSize(1.5)
				if unique_value == 'NODE':
					symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Circle)
				else:
					symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Square)
		elif '2d_mat' in fname:
			symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
			layer.setOpacity(0.25)
		elif '2d_soil' in fname:
			symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
			layer.setOpacity(0.25)
		elif '1d_bc' in fname:
			if layer.geometryType() == 0:
				symbol_layer = QgsSimpleMarkerSymbolLayer.create(layer_style)
				symbol_layer.setSize(1.5)
				symbol_layer.setShape(QgsSimpleMarkerSymbolLayerBase.Circle)
			else:
				layer_syle['style'] = 'no'
				symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
				color = QColor(randrange(0,256), randrange(0,256), randrange(0,256))
				symbol_layer.setBorderColor(color)
				symbol_layer.setBorderWidth(1)
		else:
			symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)

		# replace default symbol layer with the configured one
		if symbol_layer is not None:
			symbol.changeSymbolLayer(0, symbol_layer)
			if symbol_layer2 is not None:
				symbol.appendSymbolLayer(symbol_layer2)

		# create renderer object
		category = QgsRendererCategory(unique_value, symbol, str(unique_value))
		# entry for the list of category items
		categories.append(category)

	# create renderer object
	return QgsCategorizedSymbolRenderer(field_name, categories)
	
def tuflowqgis_apply_check_tf(qgis):
	#apply check file styles to all open shapefiles
	error = False
	message = None

	#load style layers using tuflowqgis_styles
	tf_styles = tuflowqgis_styles.TF_Styles()
	error, message = tf_styles.Load()
	if error:
		return error, message
		
	for layer_name, layer in QgsProject.instance().mapLayers().items():
		if layer.type() == QgsMapLayer.VectorLayer:
			layer_fname = os.path.split(layer.source())[1][:-4]
			#QMessageBox.information(qgis.mainWindow(), "DEBUG", "shp layer name = "+layer.name())
			renderer = region_renderer(layer)
			if renderer: #if the file requires a attribute based rendered (e.g. BC_Name for a _sac_check_R)
				layer.setRenderer(renderer)
				layer.triggerRepaint()
			else: # use .qml style using tf_styles
				error, message, slyr = tf_styles.Find(layer_fname, layer) #use tuflow styles to find longest matching 
				if error:
					return error, message
				if slyr: #style layer found:
					layer.loadNamedStyle(slyr)
					layer.triggerRepaint()
	return error, message
	

def tuflowqgis_apply_check_tf_clayer(qgis, **kwargs):
	error = False
	message = None
	try:
		canvas = qgis.mapCanvas()
	except:
		error = True
		message = "ERROR - Unexpected error trying to  QGIS canvas layer."
		return error, message
	try:
		if 'layer' in kwargs.keys():
			cLayer = kwargs['layer']
		else:
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
		layer_fname = os.path.split(cLayer.source())[1][:-4]
		renderer = region_renderer(cLayer)
		if renderer: #if the file requires a attribute based rendered (e.g. BC_Name for a _sac_check_R)
			cLayer.setRenderer(renderer)
			cLayer.triggerRepaint()
		else: # use .qml style using tf_styles
			error, message, slyr = tf_styles.Find(layer_fname, cLayer) #use tuflow styles to find longest matching 
			if error:
				return error, message
			if slyr: #style layer found:
				cLayer.loadNamedStyle(slyr)
				cLayer.triggerRepaint()
	else:
		error = True
		message = 'ERROR - Layer is not a vector layer: '+cLayer.source()
		return error, message
	return error, message
	
def tuflowqgis_increment_fname(infname):
	#check for file extension (shapefile only, not expecting .mif)
	fext = ''
	if infname[-4:].upper() == '.SHP':
		fext = infname[-4:]
		fname = infname[0:-4]
	else:
		fname = infname

	# check for TUFLOW geometry suffix
	geom = ''
	if fname[-2:].upper() == '_P':
		tmpstr = fname[0:-2]
		geom = fname[-2:]
	elif fname[-2:].upper() == '_L':
		tmpstr = fname[0:-2]
		geom = fname[-2:]
	elif fname[-2:].upper() == '_R':
		tmpstr = fname[0:-2]
		geom = fname[-2:]
	else:
		tmpstr = fname

	#try to find version as integer at end of string
	rind = tmpstr.rfind('_')
	if rind >= 0:
		verstr = tmpstr[rind+1:]
		ndig = len(verstr)
		lstr = tmpstr[0:rind+1]
		try:
			verint = int(verstr)
			verint = verint + 1
			newver = str(verint)
			newverstr = newver.zfill(ndig)
			outfname =lstr+newverstr+geom+fext
		except:
			outfname = tmpstr
	else:
		outfname = tmpstr

	return outfname

def tuflowqgis_insert_tf_attributes(qgis, inputLayer, basedir, runID, template, lenFields):
	message = None
	
	if inputLayer.geometryType() == 0:
		geomType = '_P'
	elif inputLayer.geometryType() == 2:
		geomType = '_R'
	else:
		geomType = '_L'
		
	
	gis_folder = basedir.replace('\empty', '')
	
	# Create new vector file from template with appended attribute fields
	if template == '1d_nwk':
		if lenFields >= 10:
			template2 = '1d_nwke'
			fpath = os.path.join(basedir, '{0}_empty{1}.shp'.format(template2, geomType))
		else:
			fpath = os.path.join(basedir, '{0}_empty{1}.shp'.format(template, geomType))
	else:
		fpath = os.path.join(basedir, '{0}_empty{1}.shp'.format(template, geomType))
	if os.path.isfile(fpath):
		layer = QgsVectorLayer(fpath, "tmp", "ogr")
		name = '{0}_{1}{2}.shp'.format(template, runID, geomType)
		savename = os.path.join(gis_folder, name)
		if QFile(savename).exists():
			QMessageBox.critical(qgis.mainWindow(),"Info", ("File Exists: {0}".format(savename)))
			message = 'Unable to complete utility because file already exists'
			return message
		outfile = QgsVectorFileWriter(vectorFileName=savename, fileEncoding="System", 
		                              fields=layer.dataProvider().fields(), geometryType=layer.wkbType(), 
		                              srs=layer.dataProvider().sourceCrs(), driverName="ESRI Shapefile",)
			
		if outfile.hasError() != QgsVectorFileWriter.NoError:
			QMessageBox.critical(qgis.mainWindow(),"Info", ("Error Creating: {0}".format(savename)))
			message = 'Error writing output file. Check output location and output file.'
			return message
		outfile = QgsVectorLayer(savename, "tmp", "ogr")
		outfile.dataProvider().addAttributes(inputLayer.dataProvider().fields())
		
		# Get attribute names of input layers
		layer_attributes = [field.name() for field in layer.fields()]
		inputLayer_attributes = [field.name() for field in inputLayer.fields()]
		
		# Create 2D attribute value list and add features to new file
		row_list = []
		for feature in inputLayer.getFeatures():
			row = [''] * len(layer_attributes)
			for name in inputLayer_attributes:
				row.append(feature[name])
			row_list.append(row)
			outfile.dataProvider().addFeatures([feature])
		
		# correct field values
		for i, feature in enumerate(outfile.getFeatures()):
			row_dict = {}
			for j in range(len(row_list[0])):
				row_dict[j] = row_list[i][j]
			outfile.dataProvider().changeAttributeValues({i: row_dict})
		
		qgis.addVectorLayer(savename, name[:-4], "ogr")
	
	return message
	
def get_tuflow_labelName(layer):
	fsource = layer.source() #includes full filepath and extension
	fname = os.path.split(fsource)[1][:-4] #without extension
	
	if '1d_bc' in fname or '2d_bc' in fname:
		field_name1 = layer.fields().field(0).name()
		field_name2 = layer.fields().field(2).name()
		field_name = "'Name: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\"".format(field_name2, field_name1)
	elif '1d_mh' in fname or '1d_nd' in fname or '1d_pit' in fname:
		field_name1 = layer.fields().field(0).name()
		field_name2 = layer.fields().field(1).name()
		field_name = "'ID: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\"".format(field_name1, field_name2)
	elif '1d_nwk' in fname:
		field_name1 = layer.fields().field(0).name()
		field_name2 = layer.fields().field(1).name()
		field_name3 = layer.fields().field(13).name()
		field_name4 = layer.fields().field(14).name()
		field_name = "'ID: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\"".format(field_name1, field_name2)
	elif '2d_fc_' in fname:
		field_name1 = layer.fields().field(0).name()
		field_name2 = layer.fields().field(1).name()
		field_name3 = layer.fields().field(2).name()
		field_name4 = layer.fields().field(5).name()
		field_name = "'Type: ' + \"{0}\" + '\n' + 'Invert: ' + if(\"{1}\">-1000000, to_string(\"{1}\"), \"{1}\") +" \
		             "'\n' + 'Obvert: ' + if(\"{2}\">-100, to_string(\"{2}\"), \"{2}\") + '\n' + 'FLC: ' + " \
		             "if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\")".format(field_name1, field_name2, field_name3, 
		                                                                  field_name4)
	elif '2d_fcsh' in fname:
		field_name1 = layer.fields().field(0).name()
		field_name2 = layer.fields().field(1).name()
		field_name3 = layer.fields().field(5).name()
		field_name4 = layer.fields().field(6).name()
		field_name = "'Invert: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'Obvert: ' + " \
		             "if(\"{1}\">-100, to_string(\"{1}\"), \"{1}\") + '\n'" \
		             " + 'pBlockage: ' + if(\"{2}\">-100, to_string(\"{2}\"), \"{2}\") + '\n' + 'FLC: ' + " \
		             "if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\")".format(field_name1, field_name2, field_name3, 
		                                                                  field_name4)
	elif '2d_lfcsh' in fname:
		field_name1 = layer.fields().field(0).name()
		field_name2 = layer.fields().field(4).name()
		field_name3 = layer.fields().field(5).name()
		field_name4 = layer.fields().field(6).name()
		field_name5 = layer.fields().field(7).name()
		field_name6 = layer.fields().field(8).name()
		field_name7 = layer.fields().field(9).name()
		field_name8 = layer.fields().field(10).name()
		field_name9 = layer.fields().field(11).name()
		field_name10 = layer.fields().field(12).name()
		field_name = "'Invert: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'L1 Obvert: ' + " \
		             "if(\"{1}\">-100, to_string(\"{1}\"), \"{1}\") + '\n'" \
		             " + 'L1 pBlockage: ' + if(\"{2}\">-100, to_string(\"{2}\"), \"{2}\") + '\n' + 'L1 FLC: ' + " \
		             "if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\") + '\n' + 'L2 Depth: ' + " \
		             "if(\"{4}\">=0, to_string(\"{4}\"), \"{4}\") + '\n' + 'L2 pBlockage: ' + " \
		             "if(\"{5}\">=0, to_string(\"{5}\"), \"{5}\") + '\n' + 'L2 FLC: ' + " \
		             "if(\"{6}\">=0, to_string(\"{6}\"), \"{6}\") + '\n' + 'L3 Depth: ' + " \
		             "if(\"{7}\">=0, to_string(\"{7}\"), \"{7}\") + '\n' + 'L3 pBlockage: ' + " \
		             "if(\"{8}\">=0, to_string(\"{8}\"), \"{8}\") + '\n' + 'L3 FLC: ' + " \
		             "if(\"{9}\">=0, to_string(\"{9}\"), \"{9}\")".format(field_name1, field_name2, field_name3, 
		                                                                  field_name4, field_name5, field_name6, 
		                                                                  field_name7, field_name8, field_name9,
		                                                                  field_name10)
	elif '2d_po' in fname or '2d_lp' in fname:
		field_name1 = layer.fields().field(0).name()
		field_name2 = layer.fields().field(1).name()
		field_name = "'Type: ' + \"{0}\" + '\n' + 'Label: ' + \"{1}\"".format(field_name1, field_name2)
	elif '2d_sa_rf' in fname:
		field_name1 = layer.fields().field(0).name()
		field_name2 = layer.fields().field(1).name()
		field_name3 = layer.fields().field(2).name()
		field_name4 = layer.fields().field(3).name()
		field_name5 = layer.fields().field(4).name()
		field_name = "'Name: ' + \"{0}\" + '\n' + 'Catchment Area: ' + if(\"{1}\">0, to_string(\"{1}\"), \"{1}\") + " \
		             "'\n' + 'Rain Gauge: ' + \"{2}\" + '\n' + 'IL: ' + if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\") " \
		             " + '\n' + 'CL: ' + if(\"{4}\">=0, to_string(\"{4}\"), \"{4}\")".format(field_name1, field_name2, 
		                                                                                     field_name3, field_name4,
		                                                                                     field_name5)
	elif '2d_sa_tr' in fname:
		field_name1 = layer.fields().field(0).name()
		field_name2 = layer.fields().field(1).name()
		field_name3 = layer.fields().field(2).name()
		field_name4 = layer.fields().field(3).name()
		field_name = "'Name: ' + \"{0}\" + '\n' + 'Trigger Type: ' + \"{1}\" + '\n' + 'Trigger Location: ' + \"{2}\"" \
		             "+ '\n' + 'Trigger Value: ' + if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\")".format(field_name1, 
		                                                                                               field_name2, 
		                                                                                               field_name3,
		                                                                                               field_name4)
	elif '2d_vzsh' in fname:
		field_name1 = layer.fields().field(0).name()
		field_name2 = layer.fields().field(3).name()
		field_name3 = layer.fields().field(4).name()
		field_name4 = layer.fields().field(5).name()
		field_name5 = layer.fields().field(6).name()
		field_name6 = layer.fields().field(7).name()
		field_name = "'Z: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'Shape Options: ' + \"{1}\"" \
		             "+ '\n' + 'Trigger 1: ' + \"{2}\" + '\n' + 'Trigger 2: ' + \"{3}\" + '\n' + 'Trigger Value: ' "\
		             "+ if(\"{4}\">0, to_string(\"{4}\"), \"{4}\") + '\n' + 'Period: ' + " \
		             "if(\"{5}\">0, to_string(\"{5}\"), \"{5}\")".format(field_name1, field_name2, field_name3,
		                                                                 field_name4, field_name5, field_name6)
	elif '2d_zshr' in fname:
		field_name1 = layer.fields().field(0).name()
		field_name2 = layer.fields().field(3).name()
		field_name3 = layer.fields().field(4).name()
		field_name4 = layer.fields().field(5).name()
		field_name5 = layer.fields().field(6).name()
		field_name = "'Z: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'Shape Options: ' + \"{1}\"" \
		             "+ '\n' + 'Route Name: ' + \"{2}\" + '\n' + 'Cut Off Type: ' + \"{3}\" + '\n' + " \
		             "'Cut Off Values: ' + if(\"{4}\">-1000000, to_string(\"{4}\"), \"{4}\")".format(field_name1, 
		                                                                                             field_name2, 
		                                                                                             field_name3,
		                                                                                             field_name4, 
		                                                                                             field_name5)
	elif '2d_zsh' in fname:
		if layer.geometryType() == 0:
			field_name1 = layer.fields().field(0).name()
			field_name = "'{0}: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\")".format(field_name1)
		elif layer.geometryType() == 1:
			field_name1 = layer.fields().field(0).name()
			field_name2 = layer.fields().field(2).name()
			field_name = "'Z: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'Shape Width: ' + " \
			             "if(\"{1}\">-1000000, to_string(\"{1}\"), \"{1}\")".format(field_name1, field_name2)
		elif layer.geometryType() == 2:
			field_name1 = layer.fields().field(0).name()
			field_name2 = layer.fields().field(3).name()
			field_name = "'Z: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'Shape Options: ' + " \
			             "\"{1}\"".format(field_name1, field_name2)
	elif '_RCP' in fname:
		field_name1 = layer.fields().field(0).name()
		field_name2 = layer.fields().field(1).name()
		field_name3 = layer.fields().field(2).name()
		field_name4 = layer.fields().field(3).name()
		field_name5 = layer.fields().field(4).name()
		field_name = "'Route Name: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\") + '\n' + 'Cut Off Value: ' " \
		             "+ if(\"{1}\">-1000000, to_string(\"{1}\"), \"{1}\") + '\n' + 'First Cut Off Time: ' + " \
		             "if(\"{2}\">-1000000, to_string(\"{2}\"), \"{2}\") + '\n' + 'Last Cutoff Time: ' + " \
		             "if(\"{3}\">-1000000, to_string(\"{3}\"), \"{3}\") + '\n' + 'Duration of Cutoff: ' + " \
		             "if(\"{4}\">-1000000, to_string(\"{4}\"), \"{4}\")".format(field_name1, field_name2, field_name3, 
		                                                                        field_name4, field_name5)
	elif '1d_mmH_P' in fname:
		field_name = ""
		for i, field in enumerate(layer.fields()):
			if i == 0 or i == 1 or i == 3:
				field_name1 = "'{0}: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\")".format(field.name())
				if i != 3:
					field_name = field_name + field_name1 + "+ '\n' +"
				else:
					field_name = field_name + field_name1
	elif '1d_mmQ_P' in fname or '1d_mmV_P' in fname:
		field_name = ""
		for i, field in enumerate(layer.fields()):
			if i == 0 or i == 1 or i == 2 or i == 4 or i == 5:
				field_name1 = "'{0}: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\")".format(field.name())
				if i != 5:
					field_name = field_name + field_name1 + "+ '\n' +"
				else:
					field_name = field_name + field_name1
	elif '1d_ccA_L' in fname:
		field_name = ""
		for i, field in enumerate(layer.fields()):
			if i == 0 or i == 1:
				field_name1 = "'{0}: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\")".format(field.name())
				if i != 1:
					field_name = field_name + field_name1 + "+ '\n' +"
				else:
					field_name = field_name + field_name1
	else:
		field_name1 = layer.fields().field(0).name()
		field_name = "'{0}: ' + if(\"{0}\">-1000000, to_string(\"{0}\"), \"{0}\")".format(field_name1)
	return field_name
	
def get_1d_nwk_labelName(layer, type):
	field_name1 = layer.fields().field(0).name()
	field_name2 = layer.fields().field(1).name()
	field_name3 = layer.fields().field(13).name()
	field_name4 = layer.fields().field(14).name()
	#QMessageBox.information(qgis.mainWindow(),"Info", ("{0}".format(field_name2)))
	if type == 'C':
		field_name = "'ID: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\" + '\n' + 'Width: ' + " \
		             "if(\"{2}\">=0, to_string(\"{2}\"), \"{2}\")".format(field_name1, field_name2, field_name3)
	elif type == 'R':
		field_name = "'ID: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\" + '\n' + 'Width: ' + " \
		             "if(\"{2}\">=0, to_string(\"{2}\"), \"{2}\") + '\n' + 'Height: ' + " \
		             "if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\")".format(field_name1, field_name2, field_name3,
		                                                                 field_name4)
	else:
		field_name = "'ID: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\"".format(field_name1, field_name2)
		
	return field_name
def tuflowqgis_apply_autoLabel_clayer(qgis):
	#QMessageBox.information(qgis.mainWindow(),"Info", ("{0}".format(enabled)))
	
	error = False
	message = None
	canvas = qgis.mapCanvas()
	#canvas.mapRenderer().setLabelingEngine(QgsPalLabeling())
	
	cLayer = canvas.currentLayer()
	fsource = cLayer.source() #includes full filepath and extension
	fname = os.path.split(fsource)[1][:-4] #without extension
	
	if cLayer.labelsEnabled() == False:
		# demonstration of rule based labeling
		if '1d_nwk' in fname:
			# setup blank rule object
			label = QgsPalLayerSettings()
			rule = QgsRuleBasedLabeling.Rule(label)
			# setup label rule 1
			labelName1 = get_1d_nwk_labelName(cLayer, 'C')
			label1 = QgsPalLayerSettings()
			label1.isExpression = True
			label1.multilineAlign = 0
			label1.bufferDraw = True
			label1.drawLabels = True
			label1.fieldName = labelName1
			if cLayer.geometryType() == 0:
				label1.placement = 0
			elif cLayer.geometryType() == 1:
				label1.placement = 2
			elif cLayer.geometryType() == 2:
				label1.placement = 1
			rule1 = QgsRuleBasedLabeling.Rule(label1)
			rule1.setFilterExpression("\"Type\" LIKE '%C%' OR \"Type\" LIKE '%W%'")
			# setup label rule 2
			label2 = QgsPalLayerSettings()
			label2.isExpression = True
			label2.multilineAlign = 0
			label2.bufferDraw = True
			label2.drawLabels = True
			if cLayer.geometryType() == 0:
				label2.placement = 0
			elif cLayer.geometryType() == 1:
				label2.placement = 2
			elif cLayer.geometryType() == 2:
				label2.placement = 1
			labelName2 = get_1d_nwk_labelName(cLayer, 'R')
			label2.fieldName = labelName2
			rule2 = QgsRuleBasedLabeling.Rule(label2)
			rule2.setFilterExpression("\"Type\" LIKE '%R%'")
			# setup label rule 3
			label3 = QgsPalLayerSettings()
			label3.isExpression = True
			label3.multilineAlign = 0
			label3.bufferDraw = True
			label3.drawLabels = True
			if cLayer.geometryType() == 0:
				label3.placement = 0
			elif cLayer.geometryType() == 1:
				label3.placement = 2
			elif cLayer.geometryType() == 2:
				label3.placement = 1
			labelName3 = get_1d_nwk_labelName(cLayer, 'other')
			label3.fieldName = labelName3
			rule3 = QgsRuleBasedLabeling.Rule(label3)
			rule3.setFilterExpression("\"Type\" LIKE '%S%' OR \"Type\" LIKE '%B%' OR \"Type\" LIKE '%I%' OR \"Type\"" \
			                          "LIKE '%P%' OR \"Type\" LIKE '%G%' OR \"Type\" LIKE '%M%' OR \"Type\" LIKE '%Q%'" \
			                          "OR \"Type\" LIKE '%X%'")
			# append rule 1, 2, 3 to blank rule object
			rule.appendChild(rule1)
			rule.appendChild(rule2)
			rule.appendChild(rule3)
		else:
			# simple labeling (no rules)
			labelName = get_tuflow_labelName(cLayer)
			label = QgsPalLayerSettings()
			label.isExpression = True
			label.multilineAlign = 0
			label.bufferDraw = True
			label.drawLabels = True
			label.fieldName = labelName
			if cLayer.geometryType() == 0:
				label.placement = 0
			elif cLayer.geometryType() == 1:
				label.placement = 2
			elif cLayer.geometryType() == 2:
				label.placement = 1
		if '1d_nwk' in fname:
			labeling = QgsRuleBasedLabeling(rule)
		else:
			labeling = QgsVectorLayerSimpleLabeling(label)
		cLayer.setLabeling(labeling)
		cLayer.setLabelsEnabled(True)
	else:
		cLayer.setLabelsEnabled(False)

	canvas.refresh()

	return error, message

def find_waterLevelPoint(selection, plotLayer):
	"""Finds snapped PLOT_P layer to selected XS layer

	QgsFeatureLayer selection: current selection in map window
	QgsVectorLayer plotLayer: PLOT_P layer
	"""

	message = ''
	error = False
	intersectedPoints = []
	intersectedLines = []
	plotP = None
	plotL = None

	if plotLayer is None:
		error = True
		message = 'Could not find result gis layers.'
		return intersectedPoints, intersectedLines, message, error

	for plot in plotLayer:
		if '_PLOT_P' in plot.name():
			plotP = plot
		elif '_PLOT_L' in plot.name():
			plotL = plot
	if plotP is None and plotL is None:
		error = True
		message = 'Could not find result gis layers.'
		return intersectedPoints, intersectedLines, message, error

	for xSection in selection:
		if plotP is not None:
			found_intersect = False
			for point in plotP.getFeatures():
				if point.geometry().intersects(xSection.geometry()):
					intersectedPoints.append(point['ID'].strip())
					found_intersect = True
			if found_intersect:
				intersectedLines.append(None)
				continue
			else:
				intersectedPoints.append(None)
				if plotL is not None:
					for line in plotL.getFeatures():
						if line.geometry().intersects(xSection.geometry()):
							intersectedLines.append(line['ID'].strip())
							found_intersect = True
				if not found_intersect:
					intersectedLines.append(None)
		else:
			intersectedPoints.append(None)
			if plotL is not None:
				found_intersect = False
				for line in plotL.getFeatures():
					if line.geometry().intersects(xSection.geometry()):
						intersectedLines.append(line['ID'].strip())
						found_intersect = True
			if not found_intersect:
				intersectedLines.append(None)

	return intersectedPoints, intersectedLines, message, error


def getDirection(point1, point2, **kwargs):
	"""
	Returns the direction the from the first point to the second point.
	
	:param point1: QgsPoint
	:param point2: QgsPoint
	:param kwargs: dict -> key word arguments
	:return: float direction (0 - 360 deg)
	"""
	
	from math import atan, pi
	
	if 'x' in kwargs.keys():
		x = kwargs['x']
	else:
		x = point2.x() - point1.x()
	if 'y' in kwargs.keys():
		y = kwargs['y']
	else:
		y = point2.y() - point1.y()
	
	if x == y:
		if x > 0 and y > 0:  # first quadrant
			angle = 45.0
		elif x < 0 and y > 0:  # second quadrant
			angle = 135.0
		elif x < 0 and y < 0:  # third quadrant
			angle = 225.0
		elif x > 0 and y < 0:  # fourth quadrant
			angle = 315.0
		else:
			angle = None  # x and y are both 0 so point1 == point2
			
	elif abs(x) > abs(y):  # y is opposite, x is adjacent
		if x > 0 and y == 0:  # straight right
			angle = 0.0
		elif x > 0 and y > 0:  # first quadrant
			a = atan(abs(y) / abs(x))
			angle = a * 180.0 / pi
		elif x < 0 and y > 0:  # seond quadrant
			a = atan(abs(y) / abs(x))
			angle = 180.0 - (a * 180.0 / pi)
		elif x < 0 and y == 0:  # straight left
			angle = 180.0
		elif x < 0 and y < 0:  # third quadrant
			a = atan(abs(y) / abs(x))
			angle = 180.0 + (a * 180.0 / pi)
		elif x > 0 and y < 0:  # fourth quadrant
			a = atan(abs(y) / abs(x))
			angle = 360.0 - (a * 180.0 / pi)
		else:
			angle = None  # should never arise
			
	elif abs(y) > abs(x):  # x is opposite, y is adjacent
		if x > 0 and y > 0:  # first quadrant
			a = atan(abs(x) / abs(y))
			angle = 90.0 - (a * 180.0 / pi)
		elif x == 0 and y > 0:  # straighth up
			angle = 90.0
		elif x < 0 and y > 0:  # second quadrant
			a = atan(abs(x) / abs(y))
			angle = 90.0 + (a * 180.0 / pi)
		elif x < 0 and y < 0:  # third quadrant
			a = atan(abs(x) / abs(y))
			angle = 270.0 - (a * 180.0 / pi)
		elif x == 0 and y < 0:  # straight down
			angle = 270.0
		elif x > 0 and y < 0:  # fourth quadrant
			a = atan(abs(x) / abs(y))
			angle = 270.0 + (a * 180.0 / pi)
		else:
			angle = None  # should never arise
			
	else:
		angle = None  # should never arise
		
	return angle


def lineToPoints(feat, spacing):
	"""
	Takes a line and converts it to points with additional vertices inserted at the max spacing

	:param feat: QgsFeature - Line to be converted to points
	:param spacing: float - max spacing to use when converting line to points
	:return: List, List - QgsPoint, Chainages
	"""
	
	from math import sin, cos, asin
	
	if feat.geometry().wkbType() == QgsWkbTypes.LineString:
		geom = feat.geometry().asPolyline()
	elif feat.geometry().wkbType() == QgsWkbTypes.MultiLineString:
		mGeom = feat.geometry().asMultiPolyline()
		geom = []
		for g in mGeom:
			for p in g:
				geom.append(p)
	pPrev = None
	points = []  # X, Y coordinates of point in line
	chainage = 0
	chainages = []  # list of chainages along the line that the points are located at
	directions = []  # list -> direction between the previous point and the current point
	for i, p in enumerate(geom):
		usedPoint = False  # point has been used and can move onto next point
		while not usedPoint:
			if i == 0:
				points.append(p)
				chainages.append(chainage)
				pPrev = p
				directions.append(None)  # no previous point so cannot have a direction
				usedPoint = True
			else:
				length = ((p.y() - pPrev.y()) ** 2. + (p.x() - pPrev.x()) ** 2.) ** 0.5
				if length < spacing:
					points.append(p)
					chainage += length
					chainages.append(chainage)
					directions.append(getDirection(pPrev, p))
					pPrev = p
					usedPoint = True
				else:
					angle = asin((p.y() - pPrev.y()) / length)
					x = pPrev.x() + (spacing * cos(angle)) if p.x() - pPrev.x() >= 0 else pPrev.x() - (spacing * cos(angle))
					y = pPrev.y() + (spacing * sin(angle))
					newPoint = QgsPoint(x, y)
					points.append(newPoint)
					chainage += spacing
					chainages.append(chainage)
					directions.append(getDirection(pPrev, newPoint))
					pPrev = newPoint
	
	return points, chainages, directions


def getPathFromRel(dir, relPath, **kwargs):
	"""
	return the full path from a relative reference

	:param dir: string -> directory
	:param relPath: string -> relative path
	:return: string - full path
	"""
	
	outputDrive = kwargs['output_drive'] if 'output_drive' in kwargs.keys() else None
	
	components = relPath.split('\\')
	path = dir
	
	if outputDrive:
		components[0] = outputDrive
	
	for c in components:
		if c == '..':
			path = os.path.dirname(path)
		elif c == '.':
			continue
		else:
			path = os.path.join(path, c)
	return path


def checkForOutputDrive(tcf):
	"""
	Checks for an output drive.
	
	:param tcf: str full tcf filepath
	:return: str output drive
	"""
	
	drive = None
	
	with open(tcf, 'r') as fo:
		for f in fo:
			if 'output drive' in f.lower():  # check if there is an 'if scenario' command
				ind = f.lower().find('output drive')  # get index in string of command
				if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
					command, drive = f.split('==')  # split at == to get command and value
					command = command.strip()  # strip blank spaces and new lines \n
					drive = drive.split('!')[0]  # split string by ! and take first entry i.e. remove any comments after command
					drive = drive.strip()  # strip blank spaces and new lines \n
					
	return drive


def getOutputFolderFromTCF(tcf, **kwargs):
	"""
	Looks for output folder command in tcf, 1D output folder in tcf, start 2D domain in tcf, and output folder in ecf
	
	:param tcf: str full tcf filepath
	:return: list -> str full file path to output folder [ 1d, 2d ]
	"""
	
	outputDrive = kwargs['output_drive'] if 'output_drive' in kwargs.keys() else None
	
	outputFolder1D = None
	outputFolder2D = None
	
	with open(tcf, 'r') as fo:
		for f in fo:
			
			# check for 1D domain heading
			if 'start 1d domain' in f.lower():
				ind = f.lower().find('start 1d domain')  # get index in string of command
				if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
					for subline in fo:
						if 'end 1d domain' in subline.lower():
							ind = subline.lower().find('end 1d domain')  # get index in string of command
							if '!' not in subline[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
								break
						elif 'output folder' in subline.lower():  # check if there is an 'if scenario' command
							ind = subline.lower().find('output folder')  # get index in string of command
							if '!' not in subline[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
								command, folder = subline.split('==')  # split at == to get command and value
								command = command.strip()  # strip blank spaces and new lines \n
								folder = folder.split('!')[0]  # split string by ! and take first entry i.e. remove any comments after command
								folder = folder.strip()  # strip blank spaces and new lines \n
								outputFolder1D = folder
			
			# normal output folder
			elif 'output folder' in f.lower():  # check if there is an 'if scenario' command
				ind = f.lower().find('output folder')  # get index in string of command
				if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
					command, folder = f.split('==')  # split at == to get command and value
					command = command.strip()  # strip blank spaces and new lines \n
					folder = folder.split('!')[0]  # split string by ! and take first entry i.e. remove any comments after command
					folder = folder.strip()  # strip blank spaces and new lines \n
					if '1D' in command:
						outputFolder1D = folder
					else:
						outputFolder2D = folder
			
			# check for output folder in ECF
			elif 'estry control file' in f.lower():
				ind = f.lower().find('estry control file')
				if '!' not in f[:ind]:
					if 'estry control file auto' in f.lower():
						path = '{0}.ecf'.format(os.path.splitext(tcf)[0])
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(os.path.dirname(tcf), relPath)
					outputFolder1D = getOutputFolderFromTCF(path)[0]
	
	if outputFolder2D is not None:
		if outputFolder1D is None:
			outputFolder1D = outputFolder2D
	
	if outputFolder2D:
		if not os.path.exists(outputFolder2D):
			outputFolder2D = getPathFromRel(os.path.dirname(tcf), outputFolder2D, output_drive=outputDrive)
	if outputFolder1D:
		if not os.path.exists(outputFolder1D):
			outputFolder1D = getPathFromRel(os.path.dirname(tcf), outputFolder1D, output_drive=outputDrive)
	
	return [outputFolder1D, outputFolder2D]
	
def getResultPathsFromTCF(fpath, **kwargs):
	"""
	Get the result path locations from TCF
	
	:param fpaths: str full file path to tcf
	:return: str XMDF, str TPC
	"""

	scenarios = kwargs['scenarios'] if 'scenarios' in kwargs.keys() else []
	events = kwargs['events'] if 'events' in kwargs.keys() else []
	
	results2D = []
	results1D = []
	
	# check for output drive
	outputDrive = checkForOutputDrive(fpath)
	
	# get 2D output folder
	outputFolder1D, outputFolder2D = getOutputFolderFromTCF(fpath, output_drive=outputDrive)
	
	# get 2D output
	basename = os.path.splitext(os.path.basename(fpath))[0]
	
	# split out event and scenario wildcards
	basenameComponents = basename.split('~')
	for i, x in enumerate(basenameComponents):
		x = x.lower()
		if x == 's' or x == 's1' or x == 's2' or x == 's3' or x == 's4' or x == 's5' or x == 's5' or x == 's6' or \
			x == 's7' or x == 's8' or x == 's9' or x == 'e' or x == 'e1' or x == 'e2' or x == 'e3' or x == 'e4' or \
			x == 'e5' or x == 'e6' or x == 'e7' or x == 'e8' or x == 'e9':
			basenameComponents.pop(i)
	
	# search in folder for files that match name, scenarios, and events
	if os.path.exists(outputFolder2D):
		
		# if there are scenarios or events will have to do it the long way since i don't know what hte output name will be
		if scenarios or events:
			# try looking for xmdf and dat files
			for file in os.listdir(outputFolder2D):
				name, ext = os.path.splitext(file)
				if ext.lower() == '.xmdf' or ext.lower() == '.dat':
					matches = True
					for x in basenameComponents:
						if x not in name:
							matches = False
							break
					for i, scenario in enumerate(scenarios):
						if scenario in name:
							break
						elif i + 1 == len(scenarios):
							matches = False
					for i, event in enumerate(events):
						if event in name:
							break
						elif i + 1 == len(events):
							matches = False
					if matches:
						results2D.append(os.path.join(outputFolder2D, file))
		else:  # can guess xmdf name at least if there are no scenarios or events
			# check for xmdf
			xmdf = '{0}.xmdf'.format(os.path.join(outputFolder2D, basename))
			if os.path.exists(xmdf):
				results2D.append(xmdf)
			# check for dat
			else:
				for file in os.listdir(outputFolder2D):
					name, ext = os.path.splitext(file)
					if ext.lower() == '.dat' and basename.lower() in name.lower():
						results2D.append(os.path.join(outputFolder2D, file))

	# get 1D output
	if scenarios or events:
		# if there are scenarios or events will have to do it the long way since i don't know what hte output name will be
		outputFolderTPC = os.path.join(outputFolder2D, 'plot')
		if os.path.exists(outputFolderTPC):
			for file in os.listdir(outputFolderTPC):
				name, ext = os.path.splitext(file)
				if ext.lower() == '.tpc':
					matches = True
					for x in basenameComponents:
						if x not in name:
							matches = False
							break
					for i, scenario in enumerate(scenarios):
						if scenario in name:
							break
						elif i + 1 == len(scenarios):
							matches = False
					for i, event in enumerate(events):
						if event in name:
							break
						elif i + 1 == len(events):
							matches = False
					if matches:
						results1D.append(os.path.join(outputFolderTPC, file))
	else:  # can guess xmdf name at least if there are no scenarios or events
		tpc = '{0}.tpc'.format(os.path.join(outputFolder2D, 'plot', basename))
		info = '{0}_1d.info'.format(os.path.join(outputFolder1D, 'csv', basename))
		if os.path.exists(tpc):
			csv = '{0}_PLOT.csv'.format(os.path.join(outputFolder2D, 'plot', 'gis', basename))
			if os.path.exists(csv):
				if os.path.getsize(csv) > 0:
					results1D.append(tpc)
		elif os.path.exists(info):
			results1D.append(info)
	
	return results1D, results2D

def loadLastFolder(layer, key):
	"""
	Load the last folder location for user browsing

	:param layer: QgsVectorLayer or QgsMeshLayer or QgsRasterLayer
	:param key: str -> key value for settings
	:return: str
	"""
	
	settings = QSettings()
	lastFolder = str(settings.value(key, os.sep))
	if len(lastFolder) > 0:  # use last folder if stored
		fpath = lastFolder
	else:
		if layer:  # if layer selected use the path to this
			dp = layer.dataProvider()
			ds = dp.dataSourceUri()
			fpath = os.path.dirname(ds)
		else:  # final resort to current working directory
			fpath = os.getcwd()
	
	return fpath


def loadSetting(key):
	"""
	Load setting based on key.
	
	:param key: str
	:return: QVariant
	"""
	
	settings = QSettings()
	savedSetting = settings.value(key)
	
	return savedSetting

	
def saveSetting(key, value):
	"""
	Save setting using key
	
	:param key: str
	:param value: QVariant
	:return:
	"""
	
	settings = QSettings()
	settings.setValue(key, value)
	

def getScenariosFromControlFile(controlFile, processedScenarios):
	"""

	:param controlFile: string - control file location
	:param processedScenarios: list - list of already processed scenarios
	:return: list - processed and added scenarios
	"""
	
	with open(controlFile, 'r') as fo:
		for f in fo:
			if 'if scenario' in f.lower():  # check if there is an 'if scenario' command
				ind = f.lower().find('if scenario')  # get index in string of command
				if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
					command, scenario = f.split('==')  # split at == to get command and value
					command = command.strip()  # strip blank spaces and new lines \n
					scenario = scenario.split('!')[
						0]  # split string by ! and take first entry i.e. remove any comments after command
					scenario = scenario.strip()  # strip blank spaces and new lines \n
					scenarios = scenario.split('|')  # split scenarios by | in case there is more than one specified
					for scenario in scenarios:  # loop through scenarios and add to list if not already there
						scenario = scenario.strip()
						if scenario not in processedScenarios:
							processedScenarios.append(scenario)
	return processedScenarios


def getScenariosFromTcf(tcf):
	"""

	:param tcf: string - tcf location
	:param iface: QgisInterface
	:return: bool error
	:return: string message
	:return: list scenarios
	"""
	
	message = 'Could not find the following files:\n'
	error = False
	dir = os.path.dirname(tcf)
	scenarios = []
	scenarios = getScenariosFromControlFile(tcf, scenarios)
	with open(tcf, 'r') as fo:
		for f in fo:
			if 'estry control file' in f.lower():
				ind = f.lower().find('estry control file')
				if '!' not in f[:ind]:
					if 'estry control file auto' in f.lower():
						path = '{0}.ecf'.format(os.path.splitext(tcf)[0])
					else:
						command, relPath = f.split('==')
						command = command.strip()
						relPath = relPath.split('!')[0]
						relPath = relPath.strip()
						path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						scenarios = getScenariosFromControlFile(path, scenarios)
					else:
						error = True
						message += '{0}\n'.format(path)
			if 'geometry control file' in f.lower():
				ind = f.lower().find('geometry control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						scenarios = getScenariosFromControlFile(path, scenarios)
					else:
						error = True
						message += '{0}\n'.format(path)
			if 'bc control file' in f.lower():
				ind = f.lower().find('bc control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						scenarios = getScenariosFromControlFile(path, scenarios)
					else:
						error = True
						message += '{0}\n'.format(path)
			if 'event control file' in f.lower():
				ind = f.lower().find('event control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						scenarios = getScenariosFromControlFile(path, scenarios)
					else:
						error = True
						message += '{0}\n'.format(path)
			if 'read file' in f.lower():
				ind = f.lower().find('read file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						scenarios = getScenariosFromControlFile(path, scenarios)
					else:
						error = True
						message += '{0}\n'.format(path)
			if 'read operating controls file' in f.lower():
				ind = f.lower().find('read operating controls file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						scenarios = getScenariosFromControlFile(path, scenarios)
					else:
						error = True
						message += '{0}\n'.format(path)
	return error, message, scenarios


def getEventsFromTEF(tef):
	"""
	Extracts all the events from a tef.
	
	:param tef: str full filepath to tef
	:return: list -> str event names
	"""
	
	events = []
	
	with open(tef, 'r') as fo:
		for f in fo:
			if 'define event' in f.lower():
				ind = f.lower().find('define event')
				if '!' not in f[:ind]:
					command, event = f.split('==')
					command = command.strip()
					event = event.split('!')[0]
					event = event.strip()
					events.append(event)
	
	return events


def getEventsFromTCF(tcf):
	"""
	Extracts all the events from a TCF file.
	
	:param tcf: str full filepath to tcf
	:return: list -> str event names
	"""

	dir = os.path.dirname(tcf)
	events = []
	
	with open(tcf, 'r') as fo:
		for f in fo:
			if 'event file' in f.lower():
				ind = f.lower().find('event file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						events = getEventsFromTEF(path)
						
	return events


def getVariableFromControlFile(controlFile, variable, **kwargs):
	"""
	Get variable value from control file
	
	:param controlFile: str full filepath to control file
	:param variable: str variable name
	:return: str variable value
	"""
	
	chosen_scenario = kwargs['scenario'] if 'scenario' in kwargs.keys() else None
	
	value = None
	with open(controlFile, 'r') as fo:
		for f in fo:
			if chosen_scenario:
				if 'if scenario' in f.lower():  # check if there is an 'if scenario' command
					ind = f.lower().find('if scenario')  # get index in string of command
					if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
						command, scenario = f.split('==')  # split at == to get command and value
						command = command.strip()  # strip blank spaces and new lines \n
						scenario = scenario.split('!')[0]  # split string by ! and take first entry i.e. remove any comments after command
						scenario = scenario.strip()  # strip blank spaces and new lines \n
						scenarios = scenario.split('|')  # split scenarios by | in case there is more than one specified
						if chosen_scenario in scenarios:
							for sub_f in fo:
								if 'set variable' in sub_f.lower():  # check if there is an 'if scenario' command
									ind = sub_f.lower().find('set variable')  # get index in string of command
									if '!' not in sub_f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
										command, local_value = sub_f.split('==')  # split at == to get command and value
										command = command.strip()  # strip blank spaces and new lines \n
										if variable in command:
											value = local_value.split('!')[0]  # split string by ! and take first entry i.e. remove any comments after command
											value = value.strip()  # strip blank spaces and new lines \n
								if 'if scenario' in sub_f.lower() or 'else' in sub_f.lower() or 'end if' in sub_f.lower():
									break
			else:
				if 'set variable' in f.lower():  # check if there is an 'if scenario' command
					ind = f.lower().find('set variable')  # get index in string of command
					if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
						command, local_value = f.split('==')  # split at == to get command and value
						command = command.strip()  # strip blank spaces and new lines \n
						if variable in command:
							value = local_value.split('!')[0]  # split string by ! and take first entry i.e. remove any comments after command
							value = value.strip()  # strip blank spaces and new lines \n

	return value


def getVariableFromTCF(tcf, variable_name, **kwargs):
	"""
	Get a variable value from TCF
	
	:param tcf: str full filepath to TCF
	:param variable_name: str variable name can be with or without chevrons
	:return: str variable value
	"""
	
	scenario = kwargs['scenario'] if 'scenario' in kwargs.keys() else None
	
	message = 'Could not find the following files:\n'
	error = False
	dir = os.path.dirname(tcf)
	value = None
	variable = variable_name.strip('<<').strip('>>')
	
	# start with self
	value = getVariableFromControlFile(tcf, variable)
	if value is not None:
		return error, message, value
	
	with open(tcf, 'r') as fo:
		for f in fo:
			if 'estry control file' in f.lower():
				ind = f.lower().find('estry control file')
				if '!' not in f[:ind]:
					if 'estry control file auto' in f.lower():
						path = '{0}.ecf'.format(os.path.splitext(tcf)[0])
					else:
						command, relPath = f.split('==')
						command = command.strip()
						relPath = relPath.split('!')[0]
						relPath = relPath.strip()
						path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						value = getVariableFromControlFile(path, variable)
						if value is not None:
							return error, message, value
					else:
						error = True
						message += '{0}\n'.format(path)
			if 'geometry control file' in f.lower():
				ind = f.lower().find('geometry control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						value = getVariableFromControlFile(path, variable)
						if value is not None:
							return error, message, value
					else:
						error = True
						message += '{0}\n'.format(path)
			if 'bc control file' in f.lower():
				ind = f.lower().find('bc control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						value = getVariableFromControlFile(path, variable)
						if value is not None:
							return error, message, value
					else:
						error = True
						message += '{0}\n'.format(path)
			if 'event control file' in f.lower():
				ind = f.lower().find('event control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						value = getVariableFromControlFile(path, variable)
						if value is not None:
							return error, message, value
					else:
						error = True
						message += '{0}\n'.format(path)
			if 'read file' in f.lower():
				ind = f.lower().find('read file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						value = getVariableFromControlFile(path, variable, scenario=scenario)
						if value is not None:
							return error, message, value
					else:
						error = True
						message += '{0}\n'.format(path)
			if 'read operating controls file' in f.lower():
				ind = f.lower().find('read operating controls file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						value = getVariableFromControlFile(path, variable)
						if value is not None:
							return error, message, value
					else:
						error = True
						message += '{0}\n'.format(path)
	return error, message, value


def getCellSizeFromTGC(tgc):
	"""
	Extracts teh cell size from TGC
	
	:param tgc: str full filepath to TGC
	:return: float cell size
	"""
	cellSize = None
	error = True
	variable = False
	with open(tgc, 'r') as fo:
		for f in fo:
			if 'cell size' in f.lower():
				ind = f.lower().find('cell size')
				if '!' not in f[:ind]:
					command, size = f.split('==')
					command = command.strip()
					size = size.split('!')[0]
					size = size.strip()
					try:
						float(size)
						cellSize = size
						error = False
						variable = False
					except ValueError:
						# could be a variable <<cell_size>>
						if '<<' in size and '>>' in size:
							cellSize = size
							error = False
							variable = True
						else:
							cellSize = None
							error = True
							variable = False
					except:
						cellSize = None
						error = True
						variable = False
						
	return cellSize, variable, error


def getCellSizeFromTCF(tcf, **kwargs):
	"""
	Extracts the cell size from TCF.
	
	:param tcf: str full filepath to tcf
	:return: float cell size
	"""
	
	scenario = kwargs['scenario'] if 'scenario' in kwargs.keys() else None
	
	dir = os.path.dirname(tcf)
	cellSize = None
	
	with open(tcf, 'r') as fo:
		for f in fo:
			if 'geometry control file' in f.lower():
				ind = f.lower().find('geometry control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						cellSize, variable, error = getCellSizeFromTGC(path)
						if not error:
							if not variable:
								cellSize = float(cellSize)
								return cellSize  # return as float
							else:
								error, message, cellSize = getVariableFromTCF(tcf, cellSize, scenario=scenario)
								if not error:
									try:
										cellSize = float(cellSize)
										return cellSize
									except ValueError:
										return None
									except:
										return None
								else:
									return None
						else:
							return None

def applyMatplotLibArtist(line, artist):
	
	if artist:
		line.set_color(artist.get_color())
		line.set_linewidth(artist.get_linewidth())
		line.set_linestyle(artist.get_linestyle())
		line.set_drawstyle(artist.get_drawstyle())
		line.set_marker(artist.get_marker())
		line.set_markersize(artist.get_markersize())
		line.set_markeredgecolor(artist.get_markeredgecolor())
		line.set_markerfacecolor(artist.get_markerfacecolor())
		
		
def getMean(values, **kwargs):
	"""
	Returns the mean value and the position to the closest or next higher.
	
	:param values: list -> float
	:param kwargs: dict
	:return: float mean value, int index
	"""
	
	import statistics
	
	method = kwargs['event_selection'] if 'event_selection' in kwargs.keys() else None
	
	if not values:
		return None, None
	
	mean = statistics.mean(values)
	valuesOrdered = sorted(values)
	
	index = None
	if method.lower() == 'next higher':
		for i, v in enumerate(valuesOrdered):
			if i == 0:
				vPrev = v
			if v == mean:
				index = values.index(v)
				break
			elif vPrev < mean and v > mean:
				index = values.index(v)
				break
			else:
				vPrev = v
	elif method.lower() == 'closest':
		difference = 99999
		for i, v in enumerate(values):
			diff = abs(v - mean)
			difference = min(difference, diff)
			if diff == difference:
				index = i
	else:
		index = None
	
	return mean, int(index)


def getUnit(resultType, canvas, **kwargs):
	"""
	Returns units based on result type name and the map canvas units. If unrecognised returns blank.
	
	:param resultType: str
	:param canvas: QgsMapCanvas
	:return: str unit
	"""
	
	units = {
		'level': ('m RL', 'ft RL', ''),
		'bed level': ('m RL', 'ft RL', ''),
		'left bank obvert': ('m RL', 'ft RL', ''),
		'right bank obvert': ('m RL', 'ft RL', ''),
		'us levels': ('m RL', 'ft RL', ''),
		'ds levels': ('m RL', 'ft RL', ''),
		'bed elevation': ('m RL', 'ft RL', ''),
		'flow': ('m3/s', 'ft3/s', ''),
		'atmospheric pressure': ('hPA', 'hPa', ''),
		'bed shear stress': ('N/m2', 'lbf/ft2', 'pdl/ft2', ''),
		'depth': ('m', 'ft', ''),
		'velocity': ('m/s', 'ft/s', ''),
		'cumulative infiltration': ('mm', 'inches', ''),
		'depth to groundwater': ('m', 'ft', ''),
		'water level': ('m RL', 'ft RL', ''),
		'infiltration rate': ('mm/hr', 'in/hr', ''),
		'mb1': ('%', '%', ''),
		'mb2': ('%', '%', ''),
		'unit flow': ('m2/s', 'ft2/s', ''),
		'cumulative rainfall': ('mm', 'inches', ''),
		'rfml': ('mm', 'inches', ''),
		'rainfall rate': ('mm/hr', 'in/hr', ''),
		'stream power': ('W/m2', 'lbf/ft2', 'pdl/ft2', ''),
		'sink': ('m3/s', 'ft3/s', ''),
		'source': ('m3/s', 'ft3/s', '')
	}
	
	# determine units i.e. metric, imperial, or unknown / blank
	if canvas.mapUnits() == 0 or canvas.mapUnits() == 1 or canvas.mapUnits() == 7 or canvas.mapUnits() == 8:  # metric
		u, m = 0, 'm'
	elif canvas.mapUnits() == 2 or canvas.mapUnits() == 3 or canvas.mapUnits() == 4 or canvas.mapUnits() == 5:  # imperial
		u, m = 1, 'ft'
	else:  # use blank
		u, m = -1, ''
	
	unit = ''
	if resultType is not None:
		for key, item in units.items():
			if key in resultType.lower():
				unit = item[u]
				break
			elif resultType.lower() in key:
				unit = item[u]
				break
	
	if 'return_map_units' in kwargs.keys():
		if kwargs['return_map_units']:
			return m
		
	return unit


def interpolate(a, b, c, d, e):
	"""
	Linear interpolation

	:param a: known mid point
	:param b: known lower value
	:param c: known upper value
	:param d: unknown lower value
	:param e: unknown upper value
	:return: float
	"""
	
	a = float(a) if type(a) is not datetime else a
	b = float(b) if type(b) is not datetime else b
	c = float(c) if type(c) is not datetime else c
	d = float(d) if type(d) is not datetime else d
	e = float(e) if type(e) is not datetime else e
	
	return (e - d) / (c - b) * (a - b) + d


def roundSeconds(dateTimeObject):
	newDateTime = dateTimeObject
	
	if newDateTime.microsecond >= 500000:
		newDateTime = newDateTime + timedelta(seconds=1)
		
	return newDateTime.replace(microsecond=0)


def convertStrftimToTuviewftim(strftim):
	"""
	
	:param strftim: str standard datetime string format e.g. %d/%m/%Y %H:%M:%S
	:return: str user friendly style time string format used in tuview (similar to excel) e.g. DD/MM/YYYY hh:mm:ss
	"""
	
	tvftim = strftim
	tvftim = tvftim.replace('%a', 'DDD')
	tvftim = tvftim.replace('%A', 'DDDD')
	tvftim = tvftim.replace('%b', 'MMM')
	tvftim = tvftim.replace('%B', 'MMMM')
	tvftim = tvftim.replace('%d', 'DD')
	tvftim = tvftim.replace('%#d', 'D')
	tvftim = tvftim.replace('%H', 'hh')
	tvftim = tvftim.replace('%#H', 'h')
	tvftim = tvftim.replace('%I', 'hh')
	tvftim = tvftim.replace('%#I', 'h')
	tvftim = tvftim.replace('%m', 'MM')
	tvftim = tvftim.replace('%#m', 'M')
	tvftim = tvftim.replace('%M', 'mm')
	tvftim = tvftim.replace('%#M', 'm')
	tvftim = tvftim.replace('%p', 'AM/PM')
	tvftim = tvftim.replace('%S', 'ss')
	tvftim = tvftim.replace('%#S', 's')
	tvftim = tvftim.replace('%y', 'YY')
	tvftim = tvftim.replace('%Y', 'YYYY')
	
	return tvftim
	
def checkConsecutive(letter, string):
	"""
	check if a particular letter only appears consecutively - used for date formatting i.e. DD/MM/YYYY not D/M/DD
	or something silly like that. will ignore AM/PM
	
	:param letter:
	:param string:
	:return:
	"""
	
	f = string.replace('am', '')
	f = f.replace('AM', '')
	f = f.replace('pm', '')
	f = f.replace('PM', '')
	for i in range(f.count(letter)):
		if i == 0:
			indPrev = f.find(letter)
		else:
			ind = f[indPrev + 1:].find(letter)
			if ind != 0:
				
				return False
			indPrev += 1
	
	return True


def replaceString(string, letter, replacement):
	"""
	substitute to the replace function for the specific purpose of ignoring AM/PM when replacing 'M' or 'm' in strings.
	
	:param string: str string to search through
	:param letter: str string to search for
	:param replacement: str string to use as replacement
	:return: str after search and replace
	"""
	
	newstring = []
	for i, c in enumerate(string):
		if i == 0:
			if c == letter:
				newstring.append(replacement)
			else:
				newstring.append(c)
		else:
			if c == letter:
				if string[i-1].lower() == 'a' or string[i-1].lower() == 'p':
					newstring.append(c)
				else:
					newstring.append(replacement)
			else:
				newstring.append(c)
	return ''.join(newstring)


def convertStrftimToStrformat(strftim):
	"""
	
	:param strftim: str standard datetime string format e.g. %d/%m/%Y %H:%M:%S
	:return: str standard formatting e.g. {0:%d}/{0:%m}/{0:%Y} {0:%H}:{0:%M}:{0:%S}
	"""
	
	strformat = strftim
	strformat = strformat.replace('%a', '{0:%a}')
	strformat = strformat.replace('%A', '{0:%A}')
	strformat = strformat.replace('%b', '{0:%b}')
	strformat = strformat.replace('%B', '{0:%B}')
	strformat = strformat.replace('%d', '{0:%d}')
	strformat = strformat.replace('%#d', '{0:%#d}')
	strformat = strformat.replace('%H', '{0:%H}')
	strformat = strformat.replace('%#H', '{0:%#H}')
	strformat = strformat.replace('%I', '{0:%I}')
	strformat = strformat.replace('%#I', '{0:%#I}')
	strformat = strformat.replace('%m', '{0:%m}')
	strformat = strformat.replace('%#m', '{0:%#m}')
	strformat = strformat.replace('%M', '{0:%M}')
	strformat = strformat.replace('%#M', '{0:%#M}')
	strformat = strformat.replace('%p', '{0:%p}')
	strformat = strformat.replace('%S', '{0:%S}')
	strformat = strformat.replace('%#S', '{0:%#S}')
	strformat = strformat.replace('%y', '{0:%y}')
	strformat = strformat.replace('%Y', '{0:%Y}')
	
	return strformat


def convertTuviewftimToStrftim(tvftim):
	"""
	
	
	:param tvftim: str user friendly style time string format used in tuview (similar to excel) e.g. DD/MM/YYYY hh:mm:ss
	:return: str strftim standard datetime string format e.g. %d/%m/%Y %H:%M:%S
	"""
	
	strftim = tvftim
	for c in tvftim:
		if c != 'D' and c.upper() != 'M' and c != 'Y' and c != 'h' and c != 's' and c != ' ' and c != '/' and c != ':' \
			and c != '\\' and c != '-' and c != '|' and c != ';' and c != ',' and c != '.' and c != '&' and c != '*' \
			and c != '_' and c != '=' and c != '+' and c != '[' and c != ']' and c != '{' and c != '}' and c != "'" \
			and c != '"' and c != '<' and c != '>' and c != '(' and c != ')':
			if c.lower() == 'a' or c.lower() == 'p':
				ind = strftim.find('a')
				if ind != -1:
					if strftim[ind+1].lower() != 'm':
						return '', ''
				ind = strftim.find('p')
				if ind != -1:
					if strftim[ind + 1].lower() != 'm':
						return '', ''
			else:
				return '', ''
		
	f = strftim.find('Y')
	if f != -1:
		if checkConsecutive('Y', tvftim):
			count = tvftim.count('Y')
			replace = 'Y' * count
			if count == 1:
				strftim = strftim.replace(replace, '%y')
			elif count == 2:
				strftim = strftim.replace(replace, '%y')
			elif count == 3:
				strftim = strftim.replace(replace, '%Y')
			elif count >= 4:
				strftim = strftim.replace(replace, '%Y')
	f = strftim.find('M')
	if f != -1:
		if checkConsecutive('M', tvftim):
			temp = tvftim.replace('AM', '')
			temp = temp.replace('PM', '')
			count = temp.count('M')
			replace = 'M' * count
			if count == 1:
				strftim = replaceString(strftim, replace, '%#m')
			elif count == 2:
				strftim = strftim.replace(replace, '%m')
			elif count == 3:
				strftim = strftim.replace(replace, '%b')
			elif count >= 4:
				strftim = strftim.replace(replace, '%B')
	f = strftim.find('D')
	if f != -1:
		if checkConsecutive('D', tvftim):
			count = tvftim.count('D')
			replace = 'D' * count
			if count == 1:
				strftim = strftim.replace(replace, '%#d')
			elif count == 2:
				strftim = strftim.replace(replace, '%d')
			elif count == 3:
				strftim = strftim.replace(replace, '%a')
			elif count >= 4:
				strftim = strftim.replace(replace, '%A')
	f = strftim.find('h')
	if f != -1:
		if checkConsecutive('h', tvftim):
			replacement = 'H'
			if 'am' in tvftim.lower() or 'pm' in tvftim.lower():
				replacement = 'I'
			count = tvftim.count('h')
			replace = 'h' * count
			if count == 1:
				strftim = strftim.replace(replace, '%#{0}'.format(replacement))
			elif count >= 2:
				strftim = strftim.replace(replace, '%{0}'.format(replacement))
	f = strftim.find('m')
	if f != -1:
		if checkConsecutive('m', tvftim):
			temp = tvftim.replace('am', '')
			temp = temp.replace('pm', '')
			count = temp.count('m')
			replace = 'm' * count
			if count == 1:
				strftim = replaceString(strftim, replace, '%#M')
			elif count >= 2:
				strftim = strftim.replace(replace, '%M')
	f = strftim.find('s')
	if f != -1:
		if checkConsecutive('s', tvftim):
			count = tvftim.count('s')
			replace = 's' * count
			if count == 1:
				strftim = strftim.replace(replace, '%#S')
			elif count >= 2:
				strftim = strftim.replace(replace, '%S')
	f = strftim.lower().find('am/pm')
	if f != -1:
		strftim = strftim.replace('AM/PM', '%p')
		strftim = strftim.replace('am/pm', '%p')
	f = strftim.lower().find('am')
	if f != -1:
		strftim = strftim.replace('AM', '%p')
		strftim = strftim.replace('am', '%p')
	f = strftim.lower().find('pm')
	if f != -1:
		strftim = strftim.replace('PM', '%p')
		strftim = strftim.replace('pm', '%p')
	
	strformat = convertStrftimToStrformat(strftim)
	
	return strftim, strformat
	

if __name__ == '__main__':
	a = 'DD-M-YY hh:mm'
	
	b = convertTuviewftimToStrftim(a)
	print(b)