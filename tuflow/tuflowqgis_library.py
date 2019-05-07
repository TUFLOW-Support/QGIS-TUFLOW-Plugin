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
import sys, re
import time
import os.path
import operator
import tempfile
import shutil
import zipfile
from datetime import datetime, timedelta
import itertools
import subprocess
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.gui import *
from qgis.core import *
from PyQt5.QtWidgets import *
from PyQt5.QtXml import *
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import QgsNetworkAccessManager
from math import *
import numpy
import matplotlib
import glob # MJS 11/02
from tuflow.utm.utm import from_latlon, to_latlon
from tuflow.__version__ import version

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import tuflowqgis_styles

# --------------------------------------------------------
#    tuflowqgis Utility Functions
# --------------------------------------------------------
#build_vers = build_vers
#build_type = 'release' #release / developmental

def about(window):
	build_type, build_vers = version()
	QMessageBox.information(window, "TUFLOW",
	                        "This is a {0} version of the TUFLOW QGIS utility\n"
	                        "Build: {1}".format(build_type, build_vers))


def tuflowqgis_find_layer(layer_name, **kwargs):
	
	search_type = kwargs['search_type'] if 'search_type' in kwargs.keys() else 'name'
	return_type = kwargs['return_type'] if 'return_type' in kwargs else 'layer'

	for name, search_layer in QgsProject.instance().mapLayers().items():
		if search_type.lower() == 'name':
			if search_layer.name() == layer_name:
				if return_type == 'layer':
					return search_layer
				else:
					return name
		elif search_type.lower() == 'layerid':
			if name == layer_name:
				if return_type == 'layer':
					return search_layer
				else:
					return name

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

def tuflowqgis_create_tf_dir(qgis, crs, basepath, engine, tutorial):
	if crs is None:
		return "No CRS specified"

	if basepath is None:
		return "Invalid location specified"
	
	parent_folder_name = "TUFLOWFV" if engine == 'flexible mesh' else "TUFLOW"
	# linux case sensitive tuflow directory
	for p in os.walk(basepath):
		for d in p[1]:
			if d.lower() == parent_folder_name.lower():
				parent_folder_name = d
				break
		break
	
	# Create folders, ignore top level (e.g. model, as these are create when the subfolders are created)
	TUFLOW_Folders = ["bc_dbase",
	                  "check",
	                  "model{0}gis{0}empty".format(os.sep),
	                  "results",
	                  "runs{0}log".format(os.sep)]
	if engine == 'flexible mesh':
		TUFLOW_Folders.append("model{0}geo".format(os.sep))
	for x in TUFLOW_Folders:
		tmppath = os.path.join(basepath, parent_folder_name, x)
		if os.path.isdir(tmppath):
			print("Directory Exists")
		else:
			print("Creating Directory")
			os.makedirs(tmppath)

			
	# Write Projection.prj Create a file ('w' for write, creates if doesnt exit)
	prjname = os.path.join(basepath, parent_folder_name, "model", "gis", "Projection.shp")
	if len(prjname) <= 0:
		return "Error creating projection filename"

	if QFile(prjname).exists():
		return "Projection file already exists: "+prjname

	fields = QgsFields()
	fields.append( QgsField( "notes", QVariant.String ) )
	outfile = QgsVectorFileWriter(prjname, "System", fields, 1, crs, "ESRI Shapefile")
	
	if outfile.hasError() != QgsVectorFileWriter.NoError:
		return "Failure creating output shapefile: " + outfile.errorMessage()

	del outfile

	# Write .tcf file
	ext = '.fvc' if engine == 'flexible mesh' else '.tcf'
	runfile = os.path.join(basepath, parent_folder_name, "runs", "Create_Empties{0}".format(ext))
	f = open(runfile, 'w')
	f.write("GIS FORMAT == SHP\n")
	f.write("SHP Projection == ..{0}model{0}gis{0}projection.prj\n".format(os.sep))
	if tutorial:
		f.write("Tutorial Model == ON\n")
	f.write("Write Empty GIS Files == ..{0}model{0}gis{0}empty\n".format(os.sep))
	f.flush()
	f.close()
	#QMessageBox.information(qgis.mainWindow(),"Information", "{0} folder successfully created: {1}".format(parent_folder_name, basepath))
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
	
	empty_folder = 'empty'
	for p in os.walk(os.path.dirname(basepath)):
		for d in p[1]:
			if d.lower() == empty_folder:
				empty_folder = d
				break
		break
	gis_folder = basepath.replace('/', os.sep).replace('{0}{1}'.format(os.sep, empty_folder), '')
	# Create folders, ignore top level (e.g. model, as these are create when the subfolders are created)
	for type in empty_types:
		for geom in geom_type:
			fpath = os.path.join(basepath, "{0}_empty{1}.shp".format(type, geom))
			#QMessageBox.information(qgis.mainWindow(),"Creating TUFLOW directory", fpath)
			if (os.path.isfile(fpath)):
				layer = QgsVectorLayer(fpath, "tmp", "ogr")
				name = '{0}_{1}{2}.shp'.format(type, runID, geom)
				savename = os.path.join(gis_folder, name)
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
		
def run_tuflow(qgis, tfexe, runfile):

	#QMessageBox.Information(qgis.mainWindow(),"debug", "Running TUFLOW - tcf: "+tcf)
	try:
		from subprocess import Popen
		dir, ext = os.path.splitext(runfile)
		dir = os.path.dirname(dir)
		fname = os.path.basename(runfile)
		#tfarg = [tfexe, '-b',runfile] if ext[-1] == '.tcf' else [tfexe, runfile]
		if ext.lower() == ".tcf":
			tfarg = [tfexe, '-b', runfile]
		elif ext.lower() == '.fvc':
			tfarg = [tfexe, fname]
			os.chdir(dir)
		else:
			return "Error input file extension is not TCF or FVC"
		tf_proc = Popen(tfarg)
		#tf_proc = Popen(tfarg, cwd=os.path.dirname(runfile))
	except:
		return "Error occurred starting TUFLOW"
	#QMessageBox.Information(qgis.mainWindow(),"debug", "TUFLOW started")
	return None

def config_set(project, tuflow_folder, tfexe, projection):
	message = None
	try:
		f = open(config_file, 'w')
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

	if basepath is None:
		return "Invalid location specified"

	# Get all the check files in the given directory
	check_files = glob.glob(basepath +  '/*'+ runID +'*.shp') + glob.glob(basepath +  '/*'+ runID +'*.mif') + \
				  glob.glob(basepath + '/*' + runID + '*.SHP') + glob.glob(basepath + '/*' + runID + '*.MIF')

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
	if not check_files:
		return "No check files found to import"
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
				layer_style['style'] = 'no'
				symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
				color = QColor(randrange(0,256), randrange(0,256), randrange(0,256))
				symbol_layer.setStrokeColor(color)
				symbol_layer.setStrokeWidth(1)
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
	
	empty_folder = 'empty'
	for p in os.walk(os.path.dirname(basedir)):
		for d in p[1]:
			if d.lower() == empty_folder:
				empty_folder = d
				break
		break
	gis_folder = basedir.replace(os.sep, '/').replace('{0}{1}'.format(os.sep, empty_folder), '')
	
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
			field_name_1 = cLayer.fields().field(1).name()
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
			rule1.setFilterExpression("\"{0}\" LIKE '%C%' OR \"{0}\" LIKE '%W%'".format(field_name_1))
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
			rule2.setFilterExpression("\"{0}\" LIKE '%R%'".format(field_name_1))
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
			rule3.setFilterExpression("\"{0}\" LIKE '%S%' OR \"{0}\" LIKE '%B%' OR \"{0}\" LIKE '%I%' OR \"{0}\"" \
			                          "LIKE '%P%' OR \"{0}\" LIKE '%G%' OR \"{0}\" LIKE '%M%' OR \"{0}\" LIKE '%Q%'" \
			                          "OR \"{0}\" LIKE '%X%'".format(field_name_1))
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


def lineToPoints(feat, spacing, mapUnits):
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
				length = calculateLength(p, pPrev, mapUnits)
				if length < spacing:
					points.append(p)
					chainage += length
					chainages.append(chainage)
					directions.append(getDirection(pPrev, p))
					pPrev = p
					usedPoint = True
				else:
					#angle = asin((p.y() - pPrev.y()) / length)
					#x = pPrev.x() + (spacing * cos(angle)) if p.x() - pPrev.x() >= 0 else pPrev.x() - (spacing * cos(angle))
					#y = pPrev.y() + (spacing * sin(angle))
					#newPoint = QgsPoint(x, y)
					newPoint = createNewPoint(p, pPrev, length, spacing, mapUnits)
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
	
	if len(relPath) >= 2:
		if relPath[1] == ':':
			return relPath
		relPath = relPath.replace('/', os.sep)
		if relPath[:2] == "\\\\":
			return relPath

	outputDrive = kwargs['output_drive'] if 'output_drive' in kwargs.keys() else None
	variables_on = kwargs['variables_on'] if 'variables_on' in kwargs else False
	
	_components = relPath.split(os.sep)
	components = []
	for c in _components:
		components += c.split('\\')
	path = dir
	
	if outputDrive:
		components[0] = outputDrive
	
	for c in components:
		if c == '..':
			path = os.path.dirname(path)
		elif c == '.':
			continue
		else:
			found = False
			for p in os.walk(path):
				for d in p[1]:  # directory
					if c.lower() == d.lower():
						path = os.path.join(path, d)
						found = True
						break
				if found:
					break
				for f in p[2]:  # files
					if c.lower() == f.lower():
						path = path = os.path.join(path, f)
						found = True
						break
				if found:
					break
				# not found if it reaches this point
				path = os.path.join(path, c)
				break
	
	return path


def checkForOutputDrive(tcf, scenarios=()):
	"""
	Checks for an output drive.
	
	:param tcf: str full tcf filepath
	:return: str output drive
	"""
	
	drive = None
	read = True
	with open(tcf, 'r') as fo:
		for f in fo:
			if 'if scenario' in f.lower():
				ind = f.lower().find('if scenario')
				if '!' not in f[:ind]:
					command, scenario = f.split('==')
					command = command.strip()
					scenario = scenario.split('!')[0]
					scenario = scenario.strip()
					scenarios_ = scenario.split('|')
					found = False
					if scenarios == 'all':
						found = True
					else:
						for scenario in scenarios_:
							scenario = scenario.strip()
							if scenario in scenarios:
								found = True
					if found:
						read = True
					else:
						read = False
			if 'end if' in f.lower():
				ind = f.lower().find('end if')
				if '!' not in f[:ind]:
					read = True
			if not read:
				continue
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
	variables = kwargs['variables'] if 'variables' in kwargs else {}
	scenarios = kwargs['scenarios'] if 'scenarios' in kwargs else []
	events = kwargs['events'] if 'events' in kwargs else []
	
	outputFolder1D = []
	outputFolder2D = []
	
	read = True
	with open(tcf, 'r') as fo:
		for f in fo:
			if 'if scenario' in f.lower():
				ind = f.lower().find('if scenario')
				if '!' not in f[:ind]:
					command, scenario = f.split('==')
					command = command.strip()
					scenario = scenario.split('!')[0]
					scenario = scenario.strip()
					scenarios_ = scenario.split('|')
					found = False
					if scenarios == 'all':
						found = True
					else:
						for scenario in scenarios_:
							scenario = scenario.strip()
							if scenario in scenarios:
								found = True
					if found:
						read = True
					else:
						read = False
			if 'end if' in f.lower():
				ind = f.lower().find('end if')
				if '!' not in f[:ind]:
					read = True
			if not read:
				continue
			
			# check for 1D domain heading
			if 'start 1d domain' in f.lower():
				ind = f.lower().find('start 1d domain')  # get index in string of command
				if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
					subread = True
					for subline in fo:
						if 'end 1d domain' in subline.lower():
							ind = subline.lower().find('end 1d domain')  # get index in string of command
							if '!' not in subline[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
								break
						if 'if scenario' in f.lower():
							ind = f.lower().find('if scenario')
							if '!' not in f[:ind]:
								command, scenario = f.split('==')
								command = command.strip()
								scenario = scenario.split('!')[0]
								scenario = scenario.strip()
								scenarios_ = scenario.split('|')
								found = False
								if scenarios == 'all':
									found = True
								else:
									for scenario in scenarios_:
										scenario = scenario.strip()
										if scenario in scenarios:
											found = True
								if found:
									subread = True
								else:
									subread = False
						if 'end if' in f.lower():
							ind = f.lower().find('end if')
							if '!' not in f[:ind]:
								subread = True
						if not subread:
							continue
						if 'output folder' in subline.lower():  # check if there is an 'if scenario' command
							ind = subline.lower().find('output folder')  # get index in string of command
							if '!' not in subline[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
								command, folder = subline.split('==')  # split at == to get command and value
								command = command.strip()  # strip blank spaces and new lines \n
								folder = folder.split('!')[0]  # split string by ! and take first entry i.e. remove any comments after command
								folder = folder.strip()  # strip blank spaces and new lines \n
								folders = getAllFolders(os.path.dirname(tcf), folder, variables,
								                        scenarios, events, outputDrive)
								outputFolder1D += folders
			
			# normal output folder
			if 'output folder' in f.lower():  # check if there is an 'if scenario' command
				ind = f.lower().find('output folder')  # get index in string of command
				if '!' not in f[:ind]:  # check to see if there is an ! before command (i.e. has been commented out)
					command, folder = f.split('==')  # split at == to get command and value
					command = command.strip()  # strip blank spaces and new lines \n
					folder = folder.split('!')[0]  # split string by ! and take first entry i.e. remove any comments after command
					folder = folder.strip()  # strip blank spaces and new lines \n
					folders = getAllFolders(os.path.dirname(tcf), folder, variables, scenarios, events, outputDrive)
					if '1D' in command:
						#folder = getPathFromRel(os.path.dirname(tcf), folder, output_drive=outputDrive)
						outputFolder1D += folders
					else:
						#folder = getPathFromRel(os.path.dirname(tcf), folder, output_drive=outputDrive)
						outputFolder2D += folders
			
			# check for output folder in ECF
			if 'estry control file' in f.lower():
				ind = f.lower().find('estry control file')
				if '!' not in f[:ind]:
					if 'estry control file auto' in f.lower():
						path = '{0}.ecf'.format(os.path.splitext(tcf)[0])
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					files = getAllFolders(os.path.dirname(tcf), relPath, variables, scenarios, events, outputDrive)
					#path = getPathFromRel(os.path.dirname(tcf), relPath, output_drive=outputDrive)
					for file in files:
						outputFolder1D += getOutputFolderFromTCF(file)
	
	if outputFolder2D is not None:
		if outputFolder1D is None:
			outputFolder1D = outputFolder2D[:]
	
	return [outputFolder1D, outputFolder2D]
	
def getResultPathsFromTCF(fpath, **kwargs):
	"""
	Get the result path locations from TCF
	
	:param fpaths: str full file path to tcf
	:return: str XMDF, str TPC
	"""

	scenarios = kwargs['scenarios'] if 'scenarios' in kwargs.keys() else []
	events = kwargs['events'] if 'events' in kwargs.keys() else []
	outputZones = kwargs['output_zones'] if 'output_zones' in kwargs else []
	
	results2D = []
	results1D = []
	messages = []
	
	# check for output drive
	outputDrive = checkForOutputDrive(fpath, scenarios)
	
	# check for variables
	variables = getVariableNamesFromTCF(fpath, scenarios)
	
	# get output folders
	outputFolder1D, outputFolder2D = getOutputFolderFromTCF(fpath, variables=variables, output_drive=outputDrive,
	                                                        scenarios=scenarios, events=events)
	outputFolders2D = []
	if outputZones:
		for opz in outputZones:
			if 'output folder' in opz:
				outputFolders2D.append(opz['output folder'])
			else:
				for opf2D in outputFolder2D:
					outputFolders2D.append(os.path.join(opf2D, opz['name']))
	else:
		outputFolders2D += outputFolder2D
	
	# get 2D output
	basename = os.path.splitext(os.path.basename(fpath))[0]
	
	# split out event and scenario wildcards
	basenameComponents2D = basename.split('~')
	basenameComponents2D += scenarios
	basenameComponents2D += events
	for i, x in enumerate(basenameComponents2D):
		x = x.lower()
		if x == 's' or x == 's1' or x == 's2' or x == 's3' or x == 's4' or x == 's5' or x == 's5' or x == 's6' or \
			x == 's7' or x == 's8' or x == 's9' or x == 'e' or x == 'e1' or x == 'e2' or x == 'e3' or x == 'e4' or \
			x == 'e5' or x == 'e6' or x == 'e7' or x == 'e8' or x == 'e9':
			basenameComponents2D.pop(i)
	basenameComponents1D = basenameComponents2D[:]
	for opz in outputZones:  # only 2D results are output to output zone folder
		basenameComponents2D.append('{' + '{0}'.format(opz['name']) + '}')
	
	# search in folder for files that match name, scenarios, and events
	for opf2D in outputFolders2D:
		
		if opf2D is not None:
			if os.path.exists(opf2D):
				
				# if there are scenarios or events will have to do it the long way since i don't know what hte output name will be
				# if scenarios or events or outputZones:
				# try looking for xmdf and dat files
				for file in os.listdir(opf2D):
					name, ext = os.path.splitext(file)
					if ext.lower() == '.xmdf' or ext.lower() == '.dat':
						matches = True
						for x in basenameComponents2D:
							if x not in name:
								matches = False
								break
						if matches:
							results2D.append(os.path.join(opf2D, file))
				if not results2D:
					messages.append("Could not find any matching mesh files for {0} in folder {1}".format(basename,
					                                                                                      opf2D))

			else:
				messages.append("2D output folder does not exist: {0}".format(opf2D))

	# get 1D output
	for opf2D in outputFolder2D:
		if opf2D is not None:
			outputFolderTPC = os.path.join(opf2D, 'plot')
			if os.path.exists(outputFolderTPC):
				matches = False
				for file in os.listdir(outputFolderTPC):
					name, ext = os.path.splitext(file)
					if ext.lower() == '.tpc':
						matches = True
						for x in basenameComponents1D:
							if x not in name:
								matches = False
								break
						if matches:
							if check1DResultsForData(os.path.join(outputFolderTPC, file)):
								results1D.append(os.path.join(outputFolderTPC, file))
							break
			#	if not results1D:
			#		messages.append("Could not find any matching TPC files for {0} in folder {1}".format(basename,
			#		                                                                                     opf2D))
			#else:
			#	messages.append('Plot folder does not exist: {0}'.format(opf2D))
	
	return results1D, results2D, messages


def check1DResultsForData(tpc):
	"""
	Checks to see if there is any 1D result data
	
	:param tpc: str full path to TPC file
	:return: bool True if there is data, False if there isn't
	"""
	
	with open(tpc, 'r') as fo:
		for line in fo:
			if 'number 1d' in line.lower():
				property, value = line.split('==')
				value = int(value.split('!')[0].strip())
				if value > 0:
					return True
			elif 'number reporting location' in line.lower():
				property, value = line.split('==')
				value = int(value.split('!')[0].strip())
				if value > 0:
					return True
			elif '2d' in line.lower():
				return True
			
	return False


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
	variables = getVariableNamesFromTCF(tcf, 'all')
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
						if os.path.exists(path):
							scenarios = getScenariosFromControlFile(path, scenarios)
						else:
							error = True
							message += '{0}\n'.format(path)
					else:
						command, relPath = f.split('==')
						command = command.strip()
						relPath = relPath.split('!')[0]
						relPath = relPath.strip()
						paths = getAllFolders(dir, relPath, variables, scenarios, [])
						for path in paths:
							scenarios = getScenariosFromControlFile(path, scenarios)
			if 'geometry control file' in f.lower():
				ind = f.lower().find('geometry control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					paths = getAllFolders(dir, relPath, variables, scenarios, [])
					for path in paths:
						scenarios = getScenariosFromControlFile(path, scenarios)
			if 'bc control file' in f.lower():
				ind = f.lower().find('bc control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					paths = getAllFolders(dir, relPath, variables, scenarios, [])
					for path in paths:
						scenarios = getScenariosFromControlFile(path, scenarios)
			if 'event control file' in f.lower():
				ind = f.lower().find('event control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					paths = getAllFolders(dir, relPath, variables, scenarios, [])
					for path in paths:
						scenarios = getScenariosFromControlFile(path, scenarios)
			if 'read file' in f.lower():
				ind = f.lower().find('read file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					paths = getAllFolders(dir, relPath, variables, scenarios, [])
					for path in paths:
						scenarios = getScenariosFromControlFile(path, scenarios)
			if 'read operating controls file' in f.lower():
				ind = f.lower().find('read operating controls file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					paths = getAllFolders(dir, relPath, variables, scenarios, [])
					for path in paths:
						scenarios = getScenariosFromControlFile(path, scenarios)

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
						
						
def getOutputZonesFromTCF(tcf, **kwargs):
	"""
	Extracts available output zones from TCF
	
	:param tcf: str full file path to file
	:param kwargs: dict
	:return: list -> dict -> { name: str, output folder: str }
	"""
	
	dir = os.path.dirname(tcf)
	outputZones = kwargs['output_zones'] if 'output_zones' in kwargs else []
	variables = kwargs['variables'] if 'variables' in kwargs else []
	
	with open(tcf, 'r') as fo:
		for f in fo:
			if 'define output zone' in f.lower():
				ind = f.lower().find('define output zone')
				if '!' not in f[:ind]:
					outputProp = {}
					command, name = f.split('==')
					command = command.strip()
					name = name.split('!')[0].strip()
					if name not in outputProp:
						outputProp['name'] = name
					for subf in fo:
						if 'end define' in subf.lower():
							subind = subf.lower().find('end define')
							if '!' not in subf[:subind]:
								break
						elif 'output folder' in subf.lower():
							subind = subf.lower().find('output folder')
							if '!' not in subf[:subind]:
								command, relPath = subf.split('==')
								command = command.strip()
								relPath = relPath.split('!')[0].strip()
								path = getPathFromRel(dir, relPath)
								outputProp['output folder'] = path
					outputZones.append(outputProp)
			if 'read file' in f.lower():
				ind = f.lower().find('read file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						outputZones = getOutputZonesFromTCF(path, output_zones=outputZones)
	
	return outputZones


def removeLayer(lyr):
	"""
	Removes the layer from the TOC once only. This is for when it the same layer features twice in the TOC.

	:param lyr: QgsVectorLayer
	:return: void
	"""
	
	if lyr is not None:
		legint = QgsProject.instance().layerTreeRoot()
		
		# grab all nodes that are QgsMapLayers - get to node bed rock i.e. not a group
		nodes = []
		for child in legint.children():
			children = [child]
			while children:
				nd = children[0]
				if nd.children():
					children += nd.children()
				else:
					nodes.append(nd)
				children = children[1:]
		# now loop through nodes and turn on/off visibility based on settings
		for i, child in enumerate(nodes):
			lyrName = lyr.name()
			childName = child.name()
			if child.name() == lyr.name() or child.name() == '{0} Point'.format(
					lyr.name()) or child.name() == '{0} LineString'.format(
					lyr.name()) or child.name() == '{0} Polygon'.format(lyr.name()):
				legint.removeChildNode(child)
				
				
def getVariableNamesFromControlFile(controlFile, variables, scenarios=()):
	"""
	Gets all variable names and values from control file based on seleected scenarios.
	
	:param controlFile: str full path to control file
	:param variables: dict already collected variables
	:param scenarios: list -> str scenario name
	:return: dict { variable name: [ value list ] }
	"""
	
	read = True
	with open(controlFile, 'r') as fo:
		for f in fo:
			if 'if scenario' in f.lower():
				ind = f.lower().find('if scenario')
				if '!' not in f[:ind]:
					command, scenario = f.split('==')
					command = command.strip()
					scenario = scenario.split('!')[0]
					scenario = scenario.strip()
					scenarios_ = scenario.split('|')
					found = False
					if scenarios == 'all':
						found = True
					else:
						for scenario in scenarios_:
							scenario = scenario.strip()
							if scenario in scenarios:
								found = True
					if found:
						read = True
					else:
						read = False
			elif 'end if' in f.lower():
				ind = f.lower().find('end if')
				if '!' not in f[:ind]:
					read = True
			elif not read:
				continue
			elif 'set variable' in f.lower():
				ind = f.lower().find('set variable')
				if '!' not in f[:ind]:
					command, value = f.split('==')
					command = command.strip()
					variable = command[12:].strip()
					value = value.split('!')[0]
					value = value.strip()
					if variable.lower() not in variables:
						variables[variable.lower()] = []
					variables[variable.lower()].append(value)
	
	return variables
				

def getVariableNamesFromTCF(tcf, scenarios=()):
	"""
	Gets all variable names and values from tcf based on selected scenarios
	
	:param tcf: str full path to control file
	:param scenarios: list -> str scenario name
	:return: dict { variable name: [ value list ] }
	"""
	
	dir = os.path.dirname(tcf)
	variables = {}
	# first look for variables in tcf
	variables = getVariableNamesFromControlFile(tcf, variables, scenarios)
	# then look for variables in other control files
	read = True
	with open(tcf, 'r') as fo:
		for f in fo:
			if 'if scenario' in f.lower():
				ind = f.lower().find('if scenario')
				if '!' not in f[:ind]:
					command, scenario = f.split('==')
					command = command.strip()
					scenario = scenario.split('!')[0]
					scenario = scenario.strip()
					scenarios_ = scenario.split('|')
					found = False
					if scenarios == 'all':
						found = True
					else:
						for scenario in scenarios_:
							scenario = scenario.strip()
							if scenario in scenarios:
								found = True
					if found:
						read = True
					else:
						read = False
			if 'end if' in f.lower():
				ind = f.lower().find('end if')
				if '!' not in f[:ind]:
					read = True
			if not read:
				continue
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
							variables = getVariableNamesFromControlFile(path, variables, scenarios)
			if 'geometry control file' in f.lower():
				ind = f.lower().find('geometry control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						variables = getVariableNamesFromControlFile(path, variables, scenarios)
			if 'bc control file' in f.lower():
				ind = f.lower().find('bc control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						variables = getVariableNamesFromControlFile(path, variables, scenarios)
			if 'event control file' in f.lower():
				ind = f.lower().find('event control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						variables = getVariableNamesFromControlFile(path, variables, scenarios)
			if 'read file' in f.lower():
				ind = f.lower().find('read file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						variables = getVariableNamesFromControlFile(path, variables, scenarios)
			if 'read operating controls file' in f.lower():
				ind = f.lower().find('read operating controls file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					path = getPathFromRel(dir, relPath)
					if os.path.exists(path):
						variables = getVariableNamesFromControlFile(path, variables, scenarios)
						
	return variables


def loadGisFile(iface, path, group, processed_paths, processed_layers, error, log):
	"""
	Load GIS file (vector or raster). If layer is already is processed_paths, layer won't be loaded again.
	
	:param iface: QgsInterface
	:param path: str full path to file
	:param group: QgsNodeTreeGroup
	:param processed_paths: list -> str file paths already processed
	:param processed_layers: list -> QgsMapLayer
	:param error: bool
	:param log: str
	:return: list -> str processed path, list -> QgsMapLayer, bool, str
	"""
	
	ext = os.path.splitext(path)[1]
	if ext.lower() == '.mid':
		path = '{0}.mif'.format(os.path.splitext(path)[0])
		ext = '.mif'
	if ext.lower() == '.shp':
		try:
			if os.path.exists(path):
				lyr = iface.addVectorLayer(path, os.path.basename(os.path.splitext(path)[0]),
				                           'ogr')
				group.addLayer(lyr)
				processed_paths.append(path)
				processed_layers.append(lyr)
			else:
				error = True
				log += '{0}\n'.format(path)
		except:
			error = True
			log += '{0}\n'.format(path)
	elif ext.lower() == '.mif':
		try:
			if os.path.exists(path):
				lyr = iface.addVectorLayer(path, os.path.basename(os.path.splitext(path)[0]),
				                           'ogr')
				lyrName = os.path.basename(os.path.splitext(path)[0])
				for name, layer in QgsProject.instance().mapLayers().items():
					if lyrName in layer.name():
						group.addLayer(layer)
						processed_paths.append(path)
						processed_layers.append(layer)
			else:
				error = True
				log += '{0}\n'.format(path)
		except:
			error = True
			log += '{0}\n'.format(path)
	elif ext.lower() == '.asc' or ext.lower() == '.flt' or ext.lower() == '.dem' or ext.lower() == '.txt':
		try:
			if os.path.exists(path):
				lyr = iface.addRasterLayer(path, os.path.basename(os.path.splitext(path)[0]),
				                           'gdal')
				group.addLayer(lyr)
				processed_paths.append(path)
				processed_layers.append(lyr)
			else:
				error = True
				log += '{0}\n'.format(path)
		except:
			error = True
			log += '{0}\n'.format(path)
	else:
		error = True
		log += '{0}\n'.format(path)
		
	return processed_paths, processed_layers, error, log
	

def loadGisFromControlFile(controlFile, iface, processed_paths, processed_layers, scenarios, variables):
	"""
	Opens all vector layers from the specified tuflow control file

	:param controlFile: string - file location
	:param iface: QgisInterface
	:return: bool, string
	"""
	
	error = False
	log = ''
	dir = os.path.dirname(controlFile)
	root = QgsProject.instance().layerTreeRoot()
	group = root.addGroup(os.path.basename(controlFile))
	read = True
	with open(controlFile, 'r') as fo:
		for f in fo:
			if 'if scenario' in f.lower():
				ind = f.lower().find('if scenario')
				if '!' not in f[:ind]:
					command, scenario = f.split('==')
					command = command.strip()
					scenario = scenario.split('!')[0]
					scenario = scenario.strip()
					scenarios_ = scenario.split('|')
					found = False
					for scenario in scenarios_:
						scenario = scenario.strip()
						if scenario in scenarios:
							found = True
					if found:
						read = True
					else:
						read = False
			if 'end if' in f.lower():
				ind = f.lower().find('end if')
				if '!' not in f[:ind]:
					read = True
			if not read:
				continue
			if 'read' in f.lower():
				ind = f.lower().find('read')
				if '!' not in f[:ind]:
					if 'read materials file' not in f.lower() and 'read file' not in f.lower() and 'read operating controls file' not in f.lower():
						command, relPath = f.split('==')
						command = command.strip()
						relPath = relPath.split('!')[0]
						relPath = relPath.strip()
						relPaths = relPath.split("|")
						for relPath in relPaths:
							relPath = relPath.strip()
							paths = getAllFolders(dir, relPath, variables, scenarios, [])
							for path in paths:
								if path not in processed_paths:
									processed_paths, processed_layers, error, log = \
										loadGisFile(iface, path, group, processed_paths, processed_layers, error, log)
							
	lyrs = [c.layer() for c in group.children()]
	lyrs_sorted = sorted(lyrs, key=lambda x: x.name())
	for i, lyr in enumerate(lyrs_sorted):
		treeLyr = group.insertLayer(i, lyr)
	group.removeChildren(len(lyrs), len(lyrs))
	return error, log, processed_paths, processed_layers


def openGisFromTcf(tcf, iface, scenarios=()):
	"""
	Opens all vector layers from the tuflow model from the TCF

	:param tcf: string - TCF location
	:param iface: QgisInterface
	:return: void - opens all files in qgis window
	"""

	dir = os.path.dirname(tcf)
	
	# get variable names and corresponding values
	variables = getVariableNamesFromTCF(tcf, scenarios)
	
	processed_paths = []
	processed_layers = []
	couldNotReadFile = False
	message = 'Could not open file:\n'
	error, log, pPaths, pLayers = loadGisFromControlFile(tcf, iface, processed_paths, processed_layers,
	                                                     scenarios, variables)
	processed_paths += pPaths
	processed_layers += pLayers
	if error:
		couldNotReadFile = True
		message += log
	read = True
	with open(tcf, 'r') as fo:
		for f in fo:
			if 'if scenario' in f.lower():
				ind = f.lower().find('if scenario')
				if '!' not in f[:ind]:
					command, scenario = f.split('==')
					command = command.strip()
					scenario = scenario.split('!')[0]
					scenario = scenario.strip()
					scenarios_ = scenario.split('|')
					found = False
					for scenario in scenarios_:
						scenario = scenario.strip()
						if scenario in scenarios:
							found = True
					if found:
						read = True
					else:
						read = False
			if 'end if' in f.lower():
				ind = f.lower().find('end if')
				if '!' not in f[:ind]:
					read = True
			if not read:
				continue
			if 'estry control file' in f.lower():
				ind = f.lower().find('estry control file')
				if '!' not in f[:ind]:
					if 'estry control file auto' in f.lower():
						path = '{0}.ecf'.format(os.path.splitext(tcf)[0])
						error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths,
						                                                     processed_layers,
						                                                     scenarios, variables)
						processed_paths += pPaths
						processed_layers += pLayers
						if error:
							couldNotReadFile = True
							message += log
					else:
						command, relPath = f.split('==')
						command = command.strip()
						relPath = relPath.split('!')[0]
						relPath = relPath.strip()
						paths = getAllFolders(dir, relPath, variables, scenarios, [])
						for path in paths:
							error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths,
							                                                     processed_layers,
							                                                     scenarios, variables)
							processed_paths += pPaths
							processed_layers += pLayers
							if error:
								couldNotReadFile = True
								message += log
			if 'geometry control file' in f.lower():
				ind = f.lower().find('geometry control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					paths = getAllFolders(dir, relPath, variables, scenarios, [])
					for path in paths:
						error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths, processed_layers,
						                                                     scenarios, variables)
						processed_paths += pPaths
						processed_layers += pLayers
						if error:
							couldNotReadFile = True
							message += log
			if 'bc control file' in f.lower():
				ind = f.lower().find('bc control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					paths = getAllFolders(dir, relPath, variables, scenarios, [])
					for path in paths:
						error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths,
						                                                     processed_layers,
						                                                     scenarios, variables)
						processed_paths += pPaths
						processed_layers += pLayers
						if error:
							couldNotReadFile = True
							message += log
			if 'event control file' in f.lower():
				ind = f.lower().find('event control file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					paths = getAllFolders(dir, relPath, variables, scenarios, [])
					for path in paths:
						error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths,
						                                                     processed_layers,
						                                                     scenarios, variables)
						processed_paths += pPaths
						processed_layers += pLayers
						if error:
							couldNotReadFile = True
							message += log
			if 'read file' in f.lower():
				ind = f.lower().find('read file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					paths = getAllFolders(dir, relPath, variables, scenarios, [])
					for path in paths:
						error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths,
						                                                     processed_layers,
						                                                     scenarios, variables)
						processed_paths += pPaths
						processed_layers += pLayers
						if error:
							couldNotReadFile = True
							message += log
			if 'read operating controls file' in f.lower():
				ind = f.lower().find('read operating controls file')
				if '!' not in f[:ind]:
					command, relPath = f.split('==')
					command = command.strip()
					relPath = relPath.split('!')[0]
					relPath = relPath.strip()
					paths = getAllFolders(dir, relPath, variables, scenarios, [])
					for path in paths:
						error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths,
						                                                     processed_layers,
						                                                     scenarios, variables)
						processed_paths += pPaths
						processed_layers += pLayers
						if error:
							couldNotReadFile = True
							message += log
	for layer in processed_layers:
		removeLayer(layer)
	if couldNotReadFile:
		QMessageBox.information(iface.mainWindow(), "Message", message)
	else:
		QMessageBox.information(iface.mainWindow(), "Message", "Successfully Loaded All TUFLOW Layers")


def applyMatplotLibArtist(line, artist):
	
	if artist:
		if type(artist) is dict:
			line.set_color(artist['color'])
			line.set_linewidth(artist['linewidth'])
			line.set_linestyle(artist['linestyle'])
			line.set_drawstyle(artist['drawstyle'])
			line.set_marker(artist['marker'])
			line.set_markersize(artist['markersize'])
			line.set_markeredgecolor(artist['markeredgecolor'])
			line.set_markerfacecolor(artist['markerfacecolor'])
		else:
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


def getPropertiesFrom2dm(file):
	"""Get some basic properties from TUFLOW classic 2dm file"""
	
	cellSize = 1
	wllVerticalOffset = 0
	origin = ()
	orientation = 0
	gridSize = ()
	
	count = 0
	with open(file, 'r') as fo:
		for line in fo:
			if 'MESH2D' in line.upper():
				components = line.split(' ')
				properties = []
				for c in components:
					if c != '':
						properties.append(c)
				if len(components) >= 3:
					origin = (float(properties[1]), float(properties[2]))
				if len(properties) >= 4:
					orientation = float(properties[3])
				if len(properties) >= 6:
					gridSize = (int(properties[4]), int(properties[5]))
				if len(properties) >= 8:
					cellSize = min(float(properties[6]), float(properties[7]))
				if len(properties) >= 9:
					wllVerticalOffset = float(properties[8])
				return cellSize, wllVerticalOffset, origin, orientation, gridSize
			if count > 10:  # should be at the start and don't want to waste time if there is an error
				return cellSize, wllVerticalOffset, origin, orientation, gridSize
			count += 1
	
	return cellSize, wllVerticalOffset, origin, orientation, gridSize


def bndryBinProperties(file):
	"""
	Get xf file precision 4 or 8
	
	:param file: str full path to file
	return: int xf version, int precision, int number of rows, int number of columns, int boundary file type
	"""
	
	xf_iparam = -1
	xf_fparam = -1
	xf_iparam_1 = -1  # xf file version
	xf_iparam_2 =  -1 # precision (4 or 8)
	xf_iparam_3 = -1  # number of rows
	xf_iparam_4 = -1  # number of columns
	xf_iparam_5 = -1  # 1 = csv, 2 = ts1
	
	with open(file, 'rb') as fo:
		for line in fo:
			for i in range(0, len(line), 4):  # data located at either a multiple of 4 or 8
				a = line[i]
				if i == 0:
					xf_iparam_1 = a
				elif i == 4 and a == 4:
					xf_iparam_2 = a
				elif i == 4 and a == 8 and xf_iparam_2 == -1:
					xf_iparam_2 = a
				
				if xf_iparam_2 > -1:
					if i == 4 * 2:
						xf_iparam_3 = a  # number of rows
						
					if i == 4 * 3:
						xf_iparam_4 = a  # number of columns
						
					if i == 4 * 4:
						xf_iparam_5 = a  # 1 = csv, 2 = ts1
						break
			break
					
	
	return xf_iparam_1, xf_iparam_2, xf_iparam_3, xf_iparam_4, xf_iparam_5


def bndryBinHeaders(file, ncol, precision):
	"""
	Get header names from boundary xf file
	
	:param file: str full path to file
	:param ncol: int number of columns
	:param precision: int 4 or 8
	:return: list -> str column header name
	"""
	
	headers = []
	array_size = 20
	char_size = 1000
	
	with open(file, 'rb') as fo:
		for line in fo:
			start = (array_size * 4) + (array_size * precision) + (ncol * 4)
			for j in range(ncol):
				bname = line[start:start + char_size]
				name = bname.decode('ascii')
				name = name.strip()
				if name:
					headers.append(name)
				start += char_size
	
	return headers


def bndryBinData(file, ncol, nrow, precision):
	"""
	Get data from boundary xf file
	
	:param file: str full path to file
	:param ncol: int number of columns
	:param nrow: int number of rows
	:param precision: int 4 or 8
	:return: ndarray
	"""
	
	array_size = 20
	header_size = 1000
	#start = int(40 + ncol + (ncol * header_size) / precision)
	start = int(((array_size * 4) + (array_size * precision) + (ncol * 4) + (ncol * header_size)) / precision)
	end = int(start + (ncol * nrow))
	data_type = numpy.float32 if precision == 4 else numpy.float64
	shape = (nrow, ncol)
	data = numpy.zeros(shape)  # dummy data
	
	with open(file, 'rb') as fo:
		extract = numpy.fromfile(fo, dtype=data_type, count=end)
	
	for i in range(ncol):
		d = extract[start:start + nrow]
		d = numpy.reshape(d, (nrow, 1))
		if i == 0:
			data = d
		else:
			data = numpy.append(data, d, 1)
		start += nrow
	
	return data


def readBndryBin(file):
	"""
	Reads TUFLOW bounadry csv .xf file
	
	:param file: str full path to file
	:return list -> str column header, ndarray
	"""
	
	# get xf file properties
	xf_iparam_1, xf_iparam_2, xf_iparam_3, xf_iparam_4, xf_iparam_5 = bndryBinProperties(file)
	
	# get headers
	headers = bndryBinHeaders(file, xf_iparam_4, xf_iparam_2)
	
	# get data values
	data = bndryBinData(file, xf_iparam_4, xf_iparam_3, xf_iparam_2)
	
	return headers, data


def changeDataSource(iface, layer, newDataSource):
	"""
	Changes map layer datasource - like arcmap
	
	:param iface: QgsInterface
	:param layer: QgsMapLayer
	:param newSource: str full file path
	:return: void
	"""
	
	
	name = layer.name()
	newName = os.path.basename(os.path.splitext(newDataSource)[0])
	
	# create dom document to store layer properties
	doc = QDomDocument("styles")
	element = doc.createElement("maplayer")
	layer.writeLayerXml(element, doc, QgsReadWriteContext())
	
	# change datasource
	element.elementsByTagName("datasource").item(0).firstChild().setNodeValue(newDataSource)
	layer.readLayerXml(element, QgsReadWriteContext())
	
	# reload layer
	layer.reload()
	
	# rename layer in layers panel
	legint = QgsProject.instance().layerTreeRoot()
	# grab all nodes that are QgsMapLayers - get to node bed rock i.e. not a group
	nodes = []
	for child in legint.children():
		children = [child]
		while children:
			nd = children[0]
			if nd.children():
				children += nd.children()
			else:
				nodes.append(nd)
			children = children[1:]
	# now loop through nodes and turn on/off visibility based on settings
	for nd in nodes:
		if nd.name() == name:
			nd.setName(newName)
	
	# refresh map and legend
	layer.triggerRepaint()
	iface.layerTreeView().refreshLayerSymbology(layer.id())
	
	
def copyLayerStyle(iface, layerCopyFrom, layerCopyTo):
	"""
	Copies styling from one layer to another.
	
	:param layerCopyFrom: QgsMapLayer
	:param layerCopyTo: QgsMapLayer
	:return: void
	"""
	
	# create dom document to store layer style
	doc = QDomDocument("styles")
	element = doc.createElement("maplayer")
	errorCopy = ''
	errorRead = ''
	layerCopyFrom.writeStyle(element, doc, errorCopy, QgsReadWriteContext())
	
	# set style to new layer
	layerCopyTo.readStyle(element, errorRead, QgsReadWriteContext())
	
	# refresh map and legend
	layerCopyTo.triggerRepaint()
	iface.layerTreeView().refreshLayerSymbology(layerCopyTo.id())
	
	
def getAllFilePaths(dir):
	"""
	Get all file paths in directory including any subdirectories in parent directory.
	
	:param dir: str full path to directory
	:return: dict -> { lower case file path: actual case sensitive file path }
	"""
	
	files = {}
	for r in os.walk(dir):
		for f in r[2]:
			file = os.path.join(r[0], f)
			files[file.lower()] = file
		
	return files


def getOSIndependentFilePath(dir, folders):
	"""
	Returns a case sensitive file path from a case insenstive file path. Assumes dir is already correct.
	
	:param dir: str full path to working directory
	:param folders: str or list -> subfolders and file
	:return: str full case sensitive file path
	"""
	
	if type(folders) is list:
		folders = os.sep.join(folders)
		
	return getPathFromRel(dir, folders)


def getOpenTUFLOWLayers(layer_type='input_types'):
	"""
	Returns a list of open tuflow layer types, tuflow layers, or tuflow check layers
	
	:param layer_type: str layer type - options: 'input_all', 'input_types' or 'check_all'
	:return: list -> str layer name
	"""
	
	tuflowLayers = []
	for name, layer in QgsProject.instance().mapLayers().items():
		if layer.type() == 0:  # vector layer
			if '1d_check' in layer.name().lower() or '2d_check' in layer.name().lower():
				if layer_type == 'check_all':
					tuflowLayers.append(layer.name())
			elif layer.name().lower()[:3] == '1d_' or layer.name().lower()[:3] == '2d_' \
					or layer.name().lower()[:3] == '0d_':
				if layer_type == 'input_all':
					tuflowLayers.append(layer.name())
				elif layer_type == 'input_types':
					components = layer.name().split('_')
					tuflow_type = '_'.join(components[:2]).lower()
					if tuflow_type not in tuflowLayers:
						tuflowLayers.append(tuflow_type)
	
	return sorted(tuflowLayers)


def getMapLayersFromRoot(root):
	
	# grab all nodes that are QgsMapLayers - get to node bed rock i.e. not a group
	nodes = []
	for child in root.children():
		children = [child]
		while children:
			nd = children[0]
			if nd.children():
				children += nd.children()
			else:
				nodes.append(nd)
			children = children[1:]
	
	return nodes

def turnLayersOnOff(settings):
	"""
	Turn layers in the workspace on/off based on settings. If layer is not specified in settings, left as 'current'.
	
	:param settings: dict -> { 'layer': 'on' or 'current' or 'off' }
	:return: void
	"""
	
	legint = QgsProject.instance().layerTreeRoot()
	
	# grab all nodes that are QgsMapLayers - get to node bed rock i.e. not a group
	nodes = legint.findLayers()
	
	# now loop through nodes and turn on/off visibility based on settings
	for nd in nodes:
		if nd.name() in settings:
			if settings[nd.name()] == 'on':
				if not nd.itemVisibilityChecked():
					nd.setItemVisibilityChecked(True)
				parent = nd.parent()
				while parent:
					if not parent.itemVisibilityChecked():
						
						children = getMapLayersFromRoot(parent)
						for child in children:
							if child.name() in settings:
								if settings[child.name()] == 'on':
									child.setItemVisibilityChecked(True)
								else:
									child.setItemVisibilityChecked(False)
							else:
								child.setItemVisibilityChecked(False)
							
						parent.setItemVisibilityChecked(True)
					parent = parent.parent()
			elif settings[nd.name()] == 'off':
				if nd.itemVisibilityChecked():
					nd.setItemVisibilityChecked(False)


def sortNodesInGroup(nodes, parent):
	"""
	Sorts layers in a qgstree group alphabetically. DEMs will be put at bottom and Meshes will be just above DEMs.
	
	:param nodes: list -> QgsLayerTreeNode
	:param parent: QgsLayerTreeNode
	:return: void
	"""
	
	# first sort nodes alphabetically by name
	nodes_sorted = sorted(nodes, key=lambda x: x.name())
	
	# then move rasters and mesh layers to end
	rasters = []
	meshes = []
	empty = []  # layer that have failed to load or are not there i.e. (?)
	for node in nodes_sorted:
		layer = tuflowqgis_find_layer(node.name())
		if layer is not None:
			if layer.type() == 1:  # raster
				rasters.append(node)
			elif layer.type() == 3:  # mesh
				meshes.append(node)
		else:
			empty.append(node)
	for mesh in meshes:
		nodes_sorted.remove(mesh)
		nodes_sorted.append(mesh)
	for raster in rasters:
		nodes_sorted.remove(raster)
		nodes_sorted.append(raster)
		
	# finally order layers in panel based on sorted list
	for i, node in enumerate(nodes_sorted):
		if node not in empty:
			layer = tuflowqgis_find_layer(node.name())
			node_new = QgsLayerTreeLayer(layer)
			node_new.setItemVisibilityChecked(node.itemVisibilityChecked())
			parent.insertChildNode(i, node_new)
			node.parent().removeChildNode(node)
		else:
			# if node is empty, remove from map
			node.parent().removeChildNode(node)
	
					
def sortLayerPanel(sort_locally=False):
	"""
	Sort layers alphabetically in layer panel. Option to sort locally i.e. if layers
	have been grouped they will be kept in groups and sorted. Otherwise layers will be removed from the groups and
	sorted. DEMs will be put at bottom and Meshes will be just above DEMs.
	
	:param sort_locally: bool
	:return: void
	"""
	
	legint = QgsProject.instance().layerTreeRoot()
	
	# grab all nodes that are QgsMapLayers - get to node bed rock i.e. not a group
	nodes = legint.findLayers()
	
	if sort_locally:
		# get all groups
		groups = []
		groupedNodes = []
		for node in nodes:
			parent = node.parent()
			if parent not in groups:
				groups.append(parent)
				groupedNodes.append([node])
			else:
				i = groups.index(parent)
				groupedNodes[i].append(node)
				
	# sort by group
	if sort_locally:
		for i, group in enumerate(groups):
			sortNodesInGroup(groupedNodes[i], group)
	else:
		sortNodesInGroup(nodes, legint)
		# delete now redundant groups in layer panel
		groups = legint.findGroups()
		for group in groups:
			legint.removeChildNode(group)
			
			
def getAllFolders(dir, relPath, variables, scenarios, events, output_drive=None):
	"""
	Gets all possible existing folder combinations from << >> wild cards and possible options.
	
	:param dir: str path to directory
	:param relPath: str relative path
	:param variables: dict { IL: [ '5m' ] }
	:param scenarios: list -> str scenario name
	:param events: list -> str event name
	:param output_drive: str
	:return: list -> str file path
	"""
	
	folders = []
	count = 0
	rpath = relPath
	for c in rpath.replace('\\', os.sep).split(os.sep):
		if c.find('<<') > -1:
			count += 1
	dirs = [dir]
	if count == 0:
		folders.append(getPathFromRel(dir, relPath, output_drive=output_drive))
	else:
		for m in range(count):
			i = rpath.find('<<')
			j = rpath.find('>>')
			vname = rpath[i:j+2]  # variable name
			path_components = rpath.replace('\\', os.sep).split(os.sep)
			for k, pc in enumerate(path_components):
				if vname in pc:
					break
			
			# what happens if there are multiple <<variables>> in path component e.g. ..\<<~s1~>>_<<~s2~>>\2d
			vname2 = []
			j2 = j + 2
			if pc.count('<<') > 1:
				for n in range(pc.count('<<')):
					if n > 0:  # ignore first instance since this is already vname
						k2 = j2
						i2 = rpath[j2:].find('<<')
						j2 = rpath[j2:].find('>>') + 2
						vname2.append(rpath[i2+k2:j2+k2])
				vnames = [vname] + vname2
			else:
				vnames = [vname]
				
			# get all possible combinations
			combinations = getVariableCombinations(vnames, variables, scenarios, events)
			
			new_relPath = os.sep.join(path_components[:k+1])
			for d in dirs[:]:
				new_path = getPathFromRel(d, new_relPath, output_drive=output_drive)
				
				for combo in combinations:
					p = new_path
					for n, vname in enumerate(vnames):
						# check if variable name is start of absolute reference
						# i.e. <<variable>>\results = C:\tuflow\results which means
						# we don't need anything before the <<variable>>
						if len(combo[n]) > 2:
							combo[n] = combo[n].replace('/', os.sep)
							if combo[n][1] == ':' or combo[n][:2] == '\\\\':
								b = p.find("<<")
								p = p[b:]
						p = p.replace(vname, combo[n])
				
					if os.path.exists(p):
						if m + 1 == count:
							path_rest = os.sep.join(path_components[k + 1:])
							p = getPathFromRel(p, path_rest, output_drive=output_drive)
							if os.path.exists(p):
								folders.append(p)
						else:
							dirs.append(p)
				
				dirs = dirs[1:]
				
			rpath = os.sep.join(path_components[k+1:])
							
	return folders


def getVariableCombinations(vnames, variables, scenarios, events):
	"""
	Get all possible combinations from << >> replacement
	
	:param vnames: list -> str wild card <<~s1~>>
	:param variables: dict { variable name: [ variable value ] }
	:param scenarios: list -> str scenario name
	:param events: list -> str event name
	:return: list -> list -> str
	"""
	
	# collect lists to loop through
	combo_list = []
	for vname in vnames:
		# if defined variable
		if vname[2:-2].lower() in variables:
			combo_list.append(variables[vname[2:-2].lower()])
		
		# if <<s>>
		elif vname.lower()[2:5] == '~s~':
			combo_list.append(scenarios)
			
		# if <<~s1~>>
		elif vname.lower()[2:4] == '~s' and vname.lower()[5] == '~':
			combo_list.append(scenarios)
			
		# if <<~e~>>
		elif vname.lower()[2:5] == '~e~':
			combo_list.append(events)
			
		# if <<~e1~>>
		elif vname.lower()[2:4] == '~e' and vname.lower()[5] == '~':
			combo_list.append(events)
			
	no = 1
	for c in combo_list:
		no *= len(c)
	combinations = [['' for y in range(len(combo_list))] for x in range(no)]  # blank combination list
	# populate combinations list with components from each combo_list
	for i, combo in enumerate(combo_list):
		if i == 0:
			proceding_no = 1
			for c in combo_list[i + 1:]:
				proceding_no *= len(c)
			components = combo * proceding_no
		elif i + 1 == len(combo_list):
			preceding_no = 1
			for c in combo_list[:i]:
				preceding_no *= len(c)
			components = []
			for x in combo:
				components += [x] * preceding_no
		else:
			preceding_no = 1
			for c in combo_list[:i]:
				preceding_no *= len(c)
			proceding_no = 1
			for c in combo_list[i+1:]:
				proceding_no *= len(c)
			components = []
			for x in combo:
				components += [x] * preceding_no
			components *= proceding_no
		for j, comp in enumerate(components):
			combinations[j][i] = comp
		
	return combinations


def ascToAsc(exe, function, workdir , grids, **kwargs):
	"""
	Runs common funtions in the asc_to_asc utility.
	
	:param exe: str full path to executable
	:param function: str function type e.g. 'diff' or 'max'
	:param workdir: str path to working directory folder
	:param grids: list -> QgsMapLayer or str layer name or str file path to layer
	:param kwargs: dict keyword arguments
	:return: bool error, str message
	"""

	inputs = []
	for grid in grids:
		if type(grid) is QgsMapLayer:
			inputs.append(grid.dataProvider().dataSourceUri())
		elif grid.replace('/', os.sep).count(os.sep) == 0:
			layer = tuflowqgis_find_layer(grid)
			if layer is not None:
				inputs.append(layer.dataProvider().dataSourceUri())
		elif os.path.exists(grid):
			inputs.append(grid)
	
	args = [exe, '-b']
	if function.lower() == 'diff':
		if len(inputs) == 2:
			args.append('-dif')
			args.append(inputs[0])
			args.append(inputs[1])
		else:
			return True, 'Need exactly 2 input grids'
	elif function.lower() == 'max':
		if len(inputs) >= 2:
			args.append('-max')
			for input in inputs:
				args.append(input)
		else:
			return True, 'Need at least 2 input grids'
	elif function.lower() == 'stat':
		if len(inputs) >= 2:
			args.append('-statALL')
			for input in inputs:
				args.append(input)
		else:
			return True, 'Need at least 2 input grids'
	elif function.lower() == 'conv':
		if len(inputs) >= 1:
			args.append('-conv')
			for input in inputs:
				args.append(input)
		else:
			return True, 'Need at least one input grid'
	
	if 'out' in kwargs:
		if kwargs['out']:
			args.append('-out')
			args.append(kwargs['out'])
	
	if workdir:
		proc = subprocess.Popen(args, cwd=workdir)
	else:
		proc = subprocess.Popen(args)
	proc.wait()
	return False, ''
	#out = ''
	#for line in iter(proc.stdout.readline, ""):
	#	if line == b"":
	#		break
	#	out += line.decode('utf-8')
	#	if b'Fortran Pause' in line or b'ERROR' in line or b'Press Enter' in line or b'Please Enter' in line:
	#		proc.kill()
	#		return True, out
	#out, err = proc.communicate()
	#if err:
	#	return True, out.decode('utf-8')
	#else:
	#	return False, out.decode('utf-8')
	
	
def tuflowToGis(exe, function, workdir, mesh, dataType, timestep, **kwargs):
	"""
	Runs common funtions in the tuflow_to_gis utility.
	
	:param exe: str full path to executable
	:param function: str function type e.g. 'grid' 'points' 'vectors'
	:param workdir: str path to working directory
	:param mesh: str full path to mesh file
	:param dataType: str datatype for xmdf files
	:param timestep: str timestep
	:param kwargs: dict keyword arguments
	:return: bool error, str message
	"""
	
	dataType2flag = {'depth': '-typed', 'water level': '-typeh', 'velocity': '-typev', 'z0': '-typez0'}
	
	args = [exe, '-b', mesh]
	if timestep.lower() == 'max' or timestep.lower() == 'maximum':
		args.append('-max')
	elif timestep.lower() == 'all':
		args.append('tall')
	else:
		args.append('-t{0}'.format(timestep))
	if os.path.splitext(mesh)[1].upper() == '.XMDF':
		if dataType.lower() in dataType2flag:
			args.append(dataType2flag[dataType.lower()])
		else:
			args.append('-type{0}'.format(dataType))
	if function.lower() == 'grid':
		args.append('-asc')
	elif function.lower() == 'points':
		args.append('-shp')
	elif function.lower() == 'vectors':
		args.append('-shp')
		args.append('-vector')

	if workdir:
		proc = subprocess.Popen(args, cwd=workdir)
	else:
		proc = subprocess.Popen(args)
	proc.wait()
	return False, ''
	#out = ''
	#for line in iter(proc.stdout.readline, ""):
	#	if line == b"":
	#		break
	#	out += line.decode('utf-8')
	#	if b'Fortran Pause' in line or b'ERROR' in line or b'Press Enter' in line or b'Please Enter' in line:
	#		proc.kill()
	#		return True, out
	#out, err = proc.communicate()
	#if err:
	#	return True, out.decode('utf-8')
	#else:
	#	return False, out.decode('utf-8')
	
	
def resToRes(exe, function, workdir, meshes, dataType, **kwargs):
	"""
	Runs common functions in the res_to_res utility
	
	:param exe: str full path to executable
	:param function: str function type e.g. 'info' or 'convert' ..
	:param workdir: str path to working directory
	:param meshes: list -> str full path to mesh
	:param dataType: str dataset type for xmdf files
	:param kwargs: dict keyword arguments
	:return: bool error, str message
	"""
	
	dataType2flag = {'depth': '-typed', 'water level': '-typeh', 'velocity': '-typev', 'z0': '-typez0'}
	
	args = [exe, '-b']
	if meshes:
		if os.path.splitext(meshes[0])[1].upper() == '.XMDF':
			if dataType.lower() in dataType2flag:
				args.append(dataType2flag[dataType.lower()])
			else:
				args.append('-type{0}'.format(dataType))
		if function.lower() == 'info':
			args.append('-xnfo')
			args.append(meshes[0])
			args.append('-out')
			tmpdir = tempfile.mkdtemp(suffix='res_to_res')
			file = os.path.join(tmpdir, 'info.txt')
			args.append(file)
		elif function.lower() == 'conv':
			args.append('-conv')
			args.append(meshes[0])
		elif function.lower() == 'max':
			args.append('-max')
			args += meshes
		elif function.lower() == 'conc':
			args.append('-con')
			args += meshes
	else:
		return True, 'No input meshes'
	
	if 'out' in kwargs:
		if kwargs['out']:
			if function.lower() != 'info':
				args.append('-out')
				args.append(kwargs['out'])
	
	if workdir:
		proc = subprocess.Popen(args, cwd=workdir)
	else:
		proc = subprocess.Popen(args)
	#out = ''
	#for line in iter(proc.stdout.readline, ""):
	#	if line == b"":
	#		break
	#	out += line.decode('utf-8')
	#	if b'Fortran Pause' in line or b'ERROR' in line or b'Press Enter' in line or b'Please Enter' in line:
	#		proc.kill()
	#		return True, out
	#out, err = proc.communicate()
	#if err:
	#	return True, out.decode('utf-8')
	#else:
	proc.wait()
	if function.lower() == 'info':
		info = ''
		with open(file, 'r') as f:
			for line in f:
				info += line
		shutil.rmtree(tmpdir)
		return False, info  # return info instead of process log
	else:
		return False, ''
		#return False, out.decode('utf-8')
	
def tuflowUtility(exe, workdir, flags):
	"""
	
	:param exe: str full path to executable
	:param workdir: str path to working directory
	:param flags: str flags or list -> str flags
	:return: bool error, str message
	"""
	
	args = [exe, '-b']
	if type(flags) is list:
		args += flags
	else:
		f = flags.strip().split(' ')
		for a in f:
			if a != '':
				args.append(a)

	if workdir:
		#proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workdir)
		proc = subprocess.Popen(args, cwd=workdir)
	else:
		proc = subprocess.Popen(args)
	proc.wait()
	return False, ''
	#out = ''
	#for line in iter(proc.stdout.readline, ""):
	#	if line == b"":
	#		break
	#	out += line.decode('utf-8')
	#	if b'Fortran Pause' in line or b'ERROR' in line or b'Press Enter' in line or b'Please Enter' in line:
	#		proc.kill()
	#		return True, out
	#out, err = proc.communicate()
	#if err:
	#	return True, out.decode('utf-8')
	#else:
	#	return False, out.decode('utf-8')


def downloadBinPackage(packageUrl, destinationFileName):
	request = QNetworkRequest(QUrl(packageUrl))
	request.setRawHeader(b'Accept-Encoding', b'gzip,deflate')
	
	reply = QgsNetworkAccessManager.instance().get(request)
	evloop = QEventLoop()
	reply.finished.connect(evloop.quit)
	evloop.exec_(QEventLoop.ExcludeUserInputEvents)
	content_type = reply.rawHeader(b'Content-Type')
	# if content_type == QByteArray().append('application/zip'):
	if content_type == b'application/x-zip-compressed':
		if os.path.isfile(destinationFileName):
			os.unlink(destinationFileName)
		
		destinationFile = open(destinationFileName, 'wb')
		destinationFile.write(bytearray(reply.readAll()))
		destinationFile.close()
	else:
		ret_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
		raise IOError("{} {}".format(ret_code, packageUrl))


def downloadUtility(utility, parent_widget=None):
	latestUtilities = {'asc_to_asc': 'asc_to_asc.2018-03-AA.zip', 'tuflow_to_gis': 'TUFLOW_to_GIS.2018-05-AA.zip',
	                   'res_to_res': '2016-10-AA.zip', '12da_to_from_gis': '12da_to_from_gis.zip',
	                   'convert_to_ts1': 'convert_to_ts1.2018-05-AA.zip', 'tin_to_tin': 'tin_to_tin.zip',
	                   'xsgenerator': 'xsGenerator.zip'}
	exe = latestUtilities[utility.lower()]
	name = os.path.splitext(exe)[0]
	utilityNames = {'asc_to_asc': '{0}/asc_to_asc_w64.exe'.format(name),
	                'tuflow_to_gis': '{0}/TUFLOW_to_GIS_w64.exe'.format(name),
	                'res_to_res': '{0}/res_to_res_w64.exe'.format(name), '12da_to_from_gis': '12da_to_from_gis.exe',
	                'convert_to_ts1': 'convert_to_ts1.exe', 'tin_to_tin': 'tin_to_tin.exe',
	                'xsgenerator': 'xsGenerator.exe'}
	
	downloadBaseUrl = 'https://www.tuflow.com/Download/TUFLOW/Utilities/'
	
	destFolder = os.path.join(os.path.dirname(__file__), '_utilities')
	if not os.path.exists(destFolder):
		os.mkdir(destFolder)
	exePath = os.path.join(destFolder, exe)
	url = downloadBaseUrl + exe

	qApp.setOverrideCursor(QCursor(Qt.WaitCursor))
	try:
		downloadBinPackage(url, exePath)
		z = zipfile.ZipFile(exePath)
		z.extractall(destFolder)
		z.close()
		os.unlink(exePath)
		qApp.restoreOverrideCursor()
		return os.path.join(destFolder, utilityNames[utility.lower()])
	except IOError as err:
		qApp.restoreOverrideCursor()
		QMessageBox.critical(parent_widget,
		                     'Could Not Download {0}',
		                     "Download of {0} failed. Please try again or contact support@tuflow.com for "
		                     "further assistance.\n\n(Error: {1})".format(utility, err))


def convertTimeToFormattedTime(time, hour_padding=2, unit='h'):
	"""
	Converts time (hours or seconds) to formatted time hh:mm:ss.ms
	
	:param time: float
	:return: str
	"""
	
	if unit == 's':
		d = timedelta(seconds=time)
	else:
		d = timedelta(hours=time)
	h = int(d.total_seconds() / 3600)
	m = int((d.total_seconds() % 3600) / 60)
	s = float(d.total_seconds() % 60)
	
	if hour_padding == 2:
		t = '{0:02d}:{1:02d}:{2:05.02f}'.format(h, m, s)
	elif hour_padding == 3:
		t = '{0:03d}:{1:02d}:{2:05.02f}'.format(h, m, s)
	elif hour_padding == 4:
		t = '{0:04d}:{1:02d}:{2:05.02f}'.format(h, m, s)
	else:
		t = '{0:05d}:{1:02d}:{2:05.02f}'.format(h, m, s)
	
	return t


def convertFormattedTimeToTime(formatted_time, hour_padding=2, unit='h'):
	"""
	Converts formatted time hh:mm:ss.ms to time (hours or seconds)
	
	:param formatted_time: str
	:return: float
	"""

	t = formatted_time.split(':')
	h = int(t[0])
	m = int(t[1])
	s = float(t[2])
	
	d = timedelta(hours=h, minutes=m, seconds=s)
	
	if unit == 's':
		return d.total_seconds()
	else:
		return d.total_seconds() / 3600


def findToolTip(text, engine="classic"):
	"""
	Finds relevant tool tips if file exists
	
	:param text: empty type
	:return: dict -> { command: value, description: value, wiki link: value, manual link: value, manual page: value }
	"""
	
	if engine.lower() == 'flexible mesh':
		dir = os.path.join(os.path.dirname(__file__), 'empty_tooltips', 'fv')
	else:
		dir = os.path.join(os.path.dirname(__file__), 'empty_tooltips')
	properties = {'location': None,
				  'command': None,
	              'description': None,
	              'wiki link': None,
	              'manual link': None,
	              'manual page': None
	              }
	
	glob_search = ('{0}{1}*.txt'.format(dir, os.sep))
	files = glob.glob(glob_search)
	for file in files:
		name = os.path.splitext(os.path.basename(file))[0]
		if name.lower() == text.lower():
			with open(os.path.join(dir, file), 'r') as f:
				for line in f:
					if '==' in line:
						command, value = line.split('==')
						command = command.strip()
						value = value.strip()
						value = value.replace('\\n', '\n')
						value = value.replace('\\t', '\t')
						properties[command.lower()] = value
			break
		
	return properties


def calculateLength(p1, p2, mapUnits, desiredUnits='m'):
	"""
	Calculate cartesian length between 2 points
	
	:param p1: QgsPoint point 1
	:param p2: QgsPoint point 2 - this is previous point
	:param mapUnits: Enumerator QgsUnitTypes::DistanceUnit
	:param desiredUnits: str 'm' or 'ft'
	:return: float distance
	"""
	
	
	if mapUnits != QgsUnitTypes.DistanceDegrees:
		return ((p1.y() - p2.y()) ** 2. + (p1.x() - p2.x()) ** 2.) ** 0.5  # simple trig
	else:
		# do some spherical conversions
		p1Converted = from_latlon(p1.y(), p1.x())
		p2Converted = from_latlon(p2.y(), p2.x())
		metres = ((p1Converted[1] - p2Converted[1]) ** 2. + (p1Converted[0] - p2Converted[0]) ** 2.) ** 0.5
		if desiredUnits == 'm':
			return metres
		elif desiredUnits == 'ft':
			return metres * 3.28084
	
	
def createNewPoint(p1, p2, length, new_length, mapUnits):
	"""
	Create new QgsPoint at a desired length between 2 points
	
	:param p1: QgsPoint point 1
	:param p2: QgsPoint point 2 - this is previous point
	:param length: float existing length between 2 input points
	:param new_length: float length to insert new point
	:param mapUnits: Enumerator QgsUnitTypes::DistanceUnit
	:return: QgsPoint new point
	"""

	if mapUnits != QgsUnitTypes.DistanceDegrees:
		# simple trig
		angle = asin((p1.y() - p2.y()) / length)
		x = p2.x() + (new_length * cos(angle)) if p1.x() - p2.x() >= 0 else p2.x() - (new_length * cos(angle))
		y = p2.y() + (new_length * sin(angle))
		return QgsPoint(x, y)
	else:
		# do some spherical conversions
		p1Converted = from_latlon(p1.y(), p1.x())
		p2Converted = from_latlon(p2.y(), p2.x())
		angle = asin((p1Converted[1] - p2Converted[1]) / length)
		x = p2Converted[0] + (new_length * cos(angle)) if p1Converted[0] - p2Converted[0] >= 0 else p2Converted[0] - (new_length * cos(angle))
		y = p2Converted[1] + (new_length * sin(angle))
		pointBackConveted = to_latlon(x, y, p1Converted[2], p1Converted[3])
		return QgsPoint(pointBackConveted[1], pointBackConveted[0])

if __name__ == '__main__':
	a = r"C:\Users\Ellis.Symons\Desktop\Tuview_Debugging\190305\runs\Oakey_PFAS_L_~s1~_~e1~_~e2~_~s2~_18-PW.tcf"
	b = ['AD']
	c = ['100y', '60m']
	res1D, res2D, messages = getResultPathsFromTCF(a, scenarios=b, events=c)
	print("res1D: {0}".format(res1D))
	print("res2D: {0}".format(res2D))
	print("messages: {0}".format(messages))
	