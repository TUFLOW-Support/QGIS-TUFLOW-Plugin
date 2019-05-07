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
from __builtin__ import True

sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2018.2\debug-eggs')
sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2018.2\helpers\pydev')



# --------------------------------------------------------
#    tuflowqgis Utility Functions
# --------------------------------------------------------

def tuflowqgis_find_layer(layer_name):

	for name, search_layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
		if search_layer.name() == layer_name:
			return search_layer

	return None

def tuflowqgis_find_plot_layers():

	plotLayers = []

	for name, search_layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
		if '_PLOT_P' in search_layer.name() or 'PLOT_L' in search_layer.name():
			plotLayers.append(search_layer)
		if len(plotLayers) == 2:
			return plotLayers

	if len(plotLayers) == 1:
		return plotLayers
	else:
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
		layer.dataProvider().fields(), layer.wkbType(), layer.dataProvider().crs())
	
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
	QMessageBox.information(qgis.mainWindow(),"Information", "TUFLOW folder successfully created: "+basepath+'\\TUFLOW')
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
			error, message, slyr = tf_styles.Find(fname, layer) #use tuflow styles to find longest matching 
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
	registry = QgsSymbolLayerV2Registry.instance()
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
		field_name = layer.fields().field(0).name()
	elif '1d_nwk' in fname or '1d_nwkb' in fname or '1d_nwke' in fname or '1d_mh' in fname or '1d_pit' in fname or \
		 '1d_nd' in fname:
		field_name = layer.fields().field(1).name()
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
		color = '%d, %d, %d' % (randrange(0,256), randrange(0,256), randrange(0,256))
		layer_style['color'] = color
		layer_style['outline'] = '#000000'
		if '2d_bc' in fname:
			if layer.geometryType() == 1:
				#QMessageBox.information(qgis.mainWindow(), "DEBUG", 'line 446')
				symbol_layer = QgsSimpleLineSymbolLayerV2.create(layer_style)
				symbol_layer.setWidth(1)
			elif layer.geometryType() == 0:
				symbol_layer = QgsSimpleMarkerSymbolLayerV2.create(layer_style)
				symbol_layer.setSize(1.5)
				symbol_layer.setName('circle')
			else:
				symbol_layer = QgsSimpleFillSymbolLayerV2.create(layer_style)
		elif '1d_nwk' in fname or '1d_nwkb' in fname or '1d_nwke' in fname or '1d_pit' in fname or '1d_nd' in fname:
			if layer.geometryType() == 1:
				#QMessageBox.information(qgis.mainWindow(), "DEBUG", 'line 446')
				symbol_layer = QgsSimpleLineSymbolLayerV2.create(layer_style)
				symbol_layer.setWidth(1)
				symbol_layer2 = QgsMarkerLineSymbolLayerV2.create({'placement': 'lastvertex'})
				markerMeta = registry.symbolLayerMetadata("MarkerLine")
				markerLayer = markerMeta.createSymbolLayer({'width': '0.26', 'color': color, 'rotate': '1', 'placement': 'lastvertex'})
				subSymbol = markerLayer.subSymbol()
				subSymbol.deleteSymbolLayer(0)
				triangle = registry.symbolLayerMetadata("SimpleMarker").createSymbolLayer({'name': 'filled_arrowhead', 'color': color, 'color_border': color, 'offset': '0,0', 'size': '4', 'angle': '0'})
				subSymbol.appendSymbolLayer(triangle)
			elif layer.geometryType() == 0:
				symbol_layer = QgsSimpleMarkerSymbolLayerV2.create(layer_style)
				symbol_layer.setSize(1.5)
				if unique_value == 'NODE':
					symbol_layer.setName('circle')
				else:
					symbol_layer.setName('square')
		elif '2d_mat' in fname:
			symbol_layer = QgsSimpleFillSymbolLayerV2.create(layer_style)
			layer.setLayerTransparency(75)
		elif '2d_soil' in fname:
			symbol_layer = QgsSimpleFillSymbolLayerV2.create(layer_style)
			layer.setLayerTransparency(75)
		elif '1d_bc' in fname:
			if layer.geometryType() == 0:
				symbol_layer = QgsSimpleMarkerSymbolLayerV2.create(layer_style)
				symbol_layer.setSize(1.5)
				symbol_layer.setName('circle')
			else:
				layer_syle['style'] = 'no'
				symbol_layer = QgsSimpleFillSymbolLayerV2.create(layer_style)
				color = QColor(randrange(0,256), randrange(0,256), randrange(0,256))
				symbol_layer.setBorderColor(color)
				symbol_layer.setBorderWidth(1)
		else:
			symbol_layer = QgsSimpleFillSymbolLayerV2.create(layer_style)

		# replace default symbol layer with the configured one
		if symbol_layer is not None:
			symbol.changeSymbolLayer(0, symbol_layer)
			if symbol_layer2 is not None:
				symbol.appendSymbolLayer(markerLayer)
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
			layer_fname = os.path.split(layer.source())[1][:-4]
			#QMessageBox.information(qgis.mainWindow(), "DEBUG", "shp layer name = "+layer.name())
			renderer = region_renderer(layer)
			if renderer: #if the file requires a attribute based rendered (e.g. BC_Name for a _sac_check_R)
				layer.setRendererV2(renderer)
				layer.triggerRepaint()
			else: # use .qml style using tf_styles
				error, message, slyr = tf_styles.Find(layer_fname, layer) #use tuflow styles to find longest matching 
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
		layer_fname = os.path.split(cLayer.source())[1][:-4]
		renderer = region_renderer(cLayer)
		if renderer: #if the file requires a attribute based rendered (e.g. BC_Name for a _sac_check_R)
			cLayer.setRendererV2(renderer)
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
	
	if inputLayer.dataProvider().geometryType() == QGis.WKBPoint:
		geomType = '_P'
	elif inputLayer.dataProvider().geometryType() == QGis.WKBPolygon:
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
		name = '{0}_{1}{2}'.format(template, runID, geomType)
		savename = os.path.join(gis_folder, '{0}.shp'.format(name))
		if QFile(savename).exists():
			QMessageBox.critical(qgis.mainWindow(),"Info", ("File Exists: {0}".format(savename)))
			message = 'Unable to complete utility because file already exists'
			return message
		outfile = QgsVectorFileWriter(savename, "System", 
			layer.dataProvider().fields(), layer.dataProvider().geometryType(), layer.dataProvider().crs())
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
		
		qgis.addVectorLayer(savename, name, "ogr")
	
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
		field_name = "'ID: ' + \"{0}\" + '\n' + 'Type: ' + \"{1}\" + '\n' + 'Width: ' + " \
		             "if(\"{2}\">=0, to_string(\"{2}\"), \"{2}\") + '\n' + 'Height: ' + " \
		             "if(\"{3}\">=0, to_string(\"{3}\"), \"{3}\")".format(field_name1, field_name2, field_name3,
		                                                                  field_name4)
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
	
def tuflowqgis_apply_autoLabel_clayer(qgis):
	#QMessageBox.information(qgis.mainWindow(),"Info", ("{0}".format(enabled)))
	
	error = False
	message = None
	canvas = qgis.mapCanvas()
	#canvas.mapRenderer().setLabelingEngine(QgsPalLabeling())
	
	cLayer = canvas.currentLayer()
	
	labelName = get_tuflow_labelName(cLayer)
	label = QgsPalLayerSettings()
	label.readFromLayer(cLayer)
	if label.enabled == False:
		label.enabled = True
		label.fieldName = labelName
		label.isExpression = True
		if cLayer.geometryType() == 0:
			label.placement = 0
		elif cLayer.geometryType() == 1:
			label.placement = 2
		elif cLayer.geometryType() == 2:
			label.placement = 1
		label.multilineAlign = 0
		label.bufferDraw = True
		label.writeToLayer(cLayer)
		label.drawLabels = True
	else:
		label.enabled = False
		label.fieldIndex = 2
		label.writeToLayer(cLayer)
		label.drawLabels = False
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


def getAngle(line1, line2):
	"""
	Gets the angle between 2 lines
	
	:param line1: list of 2 vertices [start vertex, end vertex]
	:param line2: list of 2 vertices [start vertex, end vertex]
	:return: float angle
	"""
	from math import acos, pi
	
	a = ((line1[1][1] - line1[0][1]) ** 2 + (line1[1][0] - line1[0][0]) ** 2) ** 0.5  # triangle side a
	b = ((line2[1][1] - line2[0][1]) ** 2 + (line2[1][0] - line2[0][0]) ** 2) ** 0.5  # triangle side b
	c = ((line2[1][1] - line1[0][1]) ** 2 + (line2[1][0] - line1[0][0]) ** 2) ** 0.5  # triangle side c
	if a != 0 and b != 0:
		cosC = float(str((a ** 2 + b ** 2 - c ** 2) / (2 * a * b)))  # cosine rule - annoyingly wasn't working without convert to string then convert back to float!
		angle = acos(cosC) * 180 / pi  # convert to degrees
	else:
		angle = 0
	
	return angle


def getLength(feature):
	"""
	Gets the length of a line from the geometry
	
	:param feature: QgsFeature
	:return: float
	"""
	
	length = 0
	pPrev = None
	geom = feature.geometry().asPolyline()
	for i, p in enumerate(geom):
		if i == 0:
			pPrev = p
		else:
			length += ((pPrev[1] - p[1]) ** 2 + (pPrev[0] - p[0]) ** 2) ** 0.5
			pPrev = p
	
	return length


def getRasterValue(point, raster):
	"""
	Gets the elevation value from a raster at a given location. Assumes raster has only one band or that the first
	band is elevation.

	:param point: QgsPoint
	:param raster: QgsRasterLayer
	:return: float elevation value
	"""
	
	return raster.dataProvider().identify(point, QgsRaster.IdentifyFormatValue).results()[1]


def lineToPoints(feat, spacing):
	"""
	Takes a line and converts it to points with additional vertices inserted at the max spacing

	:param feat: QgsFeature - Line to be converted to points
	:param spacing: float - max spacing to use when converting line to points
	:return: List, List - QgsPoint, Chainages
	"""
	from math import sin, cos, asin
	
	geom = feat.geometry().asPolyline()
	pPrev = None
	points = []  # X, Y coordinates of point in line
	chainage = 0
	chainages = []  # list of chainages along the line that the points are located at
	for i, p in enumerate(geom):
		usedPoint = False  # point has been used and can move onto next point
		while not usedPoint:
			if i == 0:
				points.append(p)
				chainages.append(chainage)
				pPrev = p
				usedPoint = True
			else:
				length = ((p[1] - pPrev[1]) ** 2. + (p[0] - pPrev[0]) ** 2.) ** 0.5
				if length < spacing:
					points.append(p)
					chainage += length
					chainages.append(chainage)
					pPrev = p
					usedPoint = True
				else:
					angle = asin((p[1] - pPrev[1]) / length)
					x = pPrev[0] + (spacing * cos(angle)) if p[0] - pPrev[0] >= 0 else pPrev[0] - (spacing * cos(angle))
					y = pPrev[1] + (spacing * sin(angle))
					points.append(QgsPoint(x, y))
					chainage += spacing
					chainages.append(chainage)
					pPrev = QgsPoint(x, y)
	return points, chainages


def getVertices(lyrs, dem):
	"""
	Creates a dictionary from all layers. For line layers it will get both start and end, for points
	it will get centroid.

	:param lyrs: list of QgisVectorLayers
	:return: compiled dictionary of all QgsVectorLayers in format of {name: [[vertices], feature id, origin lyr, [us invert, ds invert], type, origin QgsFeature}
	:return: dict {name: {[QgsPoint], [Chainages], [Elevations]]}
	"""
	if dem is not None:
		demCellSize = max(dem.rasterUnitsPerPixelX(), dem.rasterUnitsPerPixelY())
	
	nullCounter = 1
	vectorDict = {}
	lineDrape = {}
	for line in lyrs:
		for feature in line.dataProvider().getFeatures():
			fid = feature.id()
			if line.geometryType() == 0:
				if not feature.geometry():
					continue
				geom = feature.geometry().asPoint()
				if feature.attributes()[0] == NULL:
					name = '{0} {1}'.format(feature.attributes()[1], nullCounter)
					nullCounter += 1
					vectorDict[name] = [[geom], fid, line, [feature.attributes()[6], feature.attributes()[7]],
					                    feature.attributes()[1], feature]
				else:
					vectorDict[feature.attributes()[0]] = [[geom], fid, line, [feature.attributes()[6], 
					                                      feature.attributes()[7]], feature.attributes()[1], feature]
			elif line.geometryType() == 1:
				if dem is not None:  # drape the line on the dem
					lineDrape[feature.attributes()[0]] = [[], [], []]
					points, chainages = lineToPoints(feature, demCellSize)
					lineDrape[feature.attributes()[0]][0] += points
					lineDrape[feature.attributes()[0]][1] += chainages
					for p in lineDrape[feature.attributes()[0]][0]:
						lineDrape[feature.attributes()[0]][2].append(getRasterValue(p, dem))
				if not feature.geometry():
					continue
				geom = feature.geometry().asPolyline()
				if feature.attributes()[0] == NULL:
					name = '__connector {0}'.format(nullCounter)
					nullCounter += 1
					vectorDict[name] = [[geom[0], geom[-1]], fid, line, [feature.attributes()[6], 
					                   feature.attributes()[7]], feature.attributes()[1], feature]
				else:
					vectorDict[feature.attributes()[0]] = [[geom[0], geom[-1]], fid, line, [feature.attributes()[6], 
					                                      feature.attributes()[7]], feature.attributes()[1], feature]
	return vectorDict, lineDrape


def checkSnapping(**kwargs):
	"""
	Takes vertices and checks if there are any matching and returns a list if there are no matching.
	For points, it will check points against lines.
	For lines, it will check against other lines in the same layer

	:param **kwargs: dictionary with line or point vertices {name: [vertices, origin fid, origin lyr, [us invert, ds invert]]}
	:return: list of unsnapped objects (for lines will append '==0' or first vertex, '==1' for last vertex)
	:return: list of unsnapped object names for lines without reference to first or last vertex (not returned for points)
	:return: dict of closest line vertex for unsnapped points and lines {name: [origin lyr, origin fid, closest vertex name, closest vertex coords, closest vertex dist]}
	:return: dict of downstream channels for lines if dnsConn is True {name: [[dns network channels], [us invert, ds invert], [other connecting channels]]}
	"""

	# determine which snapping check is being performed
	checkPoint = False
	checkLine = False
	dnsConn = False
	lineDict = kwargs['lines']  # will need lines no matter what
	lineDict_len = len(lineDict)
	lineLyrs = kwargs['line_layers']
	if 'dns_conn' in kwargs.keys():
		if kwargs['dns_conn']:
			dnsConn = True  # force script to loop through all pipes to get all dns connections
			checkLine = True
		if 'points' in kwargs.keys():  # if points included, check elevations in dns connections
			pointDict = kwargs['points']
			if len(pointDict) > 0:
				checkPoint = True
	if 'assessment' in kwargs.keys():
		if kwargs['assessment'] == 'lines':
			checkLine = True
		elif kwargs['assessment'] == 'points':
			if 'points' in kwargs.keys():  # assessing snapping for points
				checkPoint = True
				pointDict = kwargs['points']
	else:  # assessing for lines
		checkLine = True
	
	xIns = []  # list of X connectors that are entering a side channel - used to determine dns direction for x connectors
	xIns_index = 0
	xIns_indices = []  # list of indices incase they need to be removed later
	dsNwk = {}  # dict listing the downstream lines
	closestV = {}  # dict closest vertex results
	unsnapped = []  # list of unsnapped vertices
	unsnapped_names = []  # list of unsnapped vertices names (for lines)
	snappedUpstream = []  # list of snapped upstream vertices
	snappedDownstream = []  # list of snapped downstream vertices
	maxFeatureCount = 0
	mostFeaturedLyr = lineLyrs[0]
	# Check to see if line is snapped to another line
	if checkLine:
		for lName, lParam in lineDict.items():
			lLoc = lParam[0]  # vertices
			lUsInv = lParam[3][0] if lParam[3][0] != NULL else -99999  # upstream invert
			lDsInv = lParam[3][1] if lParam[3][1] != NULL else -99999  # downstream invert
			lFid = lParam[1]  # fid
			lLyr = lParam[2]  # QgsVectorLayer
			feature = lParam[5]  # QgsFeature
			xIn = False  # helps determine downstream direction in relation to X connectors
			vu = lLoc[0] # upstream vertex
			vd = lLoc[1]  # downstream vertex
			if lName in snappedUpstream:
				foundU = True
			else:
				foundU = False
			if lName in snappedDownstream:
				foundD = True
			else:
				foundD = False
			found_dns = False
			minDist1 = 99999
			minDist2 = 99999
			name1 = None
			name2 = None
			# Create a buffer object to loop through nearby features
			bufferDist = 25
			xmin = min((vu[0] - bufferDist), (vd[0] - bufferDist))
			xmax = max((vu[0] + bufferDist), (vd[0] + bufferDist))
			ymin = min((vu[1] - bufferDist), (vd[1] - bufferDist))
			ymax = max((vu[1] + bufferDist), (vd[1] + bufferDist))
			rectangle = QgsRectangle(xmin, ymin, xmax, ymax)
			request = QgsFeatureRequest().setFilterRect(rectangle)
			# cycle through nearby features to see if anything is snapped
			for lyr in lineLyrs:
				for i, feature2 in enumerate(lyr.getFeatures(request)):
					if feature2.attributes()[0] != NULL:
						lName2 = feature2.attributes()[0]
					else:
						for name, param in lineDict.items():
							if lyr.name() == param[2].name() and feature2.id() == param[5].id():
							#if feature2 == param[5]:
								lName2 = name
								break
					lParam2 = lineDict[lName2]
					lLoc2 = lParam2[0]
					lLyr2 = lParam2[2]
					lFid2 = lParam2[1]
					idFld2 = lLyr2.fields()[0]
					typFld2 = lLyr2.fields()[1]
					feature2 = lParam2[5]
					if foundU and foundD and not dnsConn:
						break
					vu2 = lLoc2[0]
					vd2 = lLoc2[1]
					if lName == lName2:
						continue
					if vu == vu2 or vu == vd2 or vd == vu2 or vd == vd2:
						if lName not in dsNwk.keys():
							dsNwk[lName] = [[], [], [], [], [], []]  # dsNwk name, us and ds invert, outflow angle, joining nwk dns, upstream network, upstream network to upstream network
						if 'connector' in lName:
							if vu == vu2:  # X Connector is entering side channel
								foundU = True
								snappedUpstream.append(lName)
								snappedUpstream.append(lName2)
								found_dns = True
								xIn = True
								if lName not in xIns:
									xIns.append(lName)
								if lName not in dsNwk.keys():
									dsNwk[lName] = [[lName2]]
								else:
									dsNwk[lName][0].append(lName2)
								if len(dsNwk[lName][1]) == 0:
									dsNwk[lName][1].append(lUsInv)
									dsNwk[lName][1].append(lDsInv)
								if len(dsNwk[lName]) < 3:
									dsNwk[lName].append([])
								if xIns_indices:  # remove since we now know xIn is True
									for xIns_i in xIns_indices:
										dsNwk[lName][0].pop(xIns_i)
							elif vd == vu2 and not xIn:  # X connector is leaving side channel
								foundD = True
								snappedDownstream.append(lName)
								snappedUpstream.append(lName2)
								found_dns = True
								if lName not in dsNwk.keys():
									dsNwk[lName] = [[lName2]]
								else:
									dsNwk[lName][0].append(lName2)
								if len(dsNwk[lName][1]) == 0:
									dsNwk[lName][1].append(lUsInv)
									dsNwk[lName][1].append(lDsInv)
								if len(dsNwk[lName]) < 3:
									dsNwk[lName].append([])
								xIns_indices.append(xIns_index)
								xIns_index += 1
							elif vu == vd2 and not xIn:
								foundU = True
								snappedUpstream.append(lName)
								snappedDownstream.append(lName2)
								dsNwk[lName][4].append(lName2)
								xIns_indices.append(xIns_index)
								xIns_index += 1
							elif vd == vd2 and xIn:  # upstream network
								foundD = True
								snappedDownstream.append(lName)
								snappedDownstream.append(lName2)
								dsNwk[lName][4].append(lName2)
							elif vd == vd2:
								foundD = True
								snappedDownstream.append(lName)
								snappedDownstream.append(lName2)
						elif 'connector' in lName2:  # end normal nwk connected to end X conn
							if lName2 in xIns:  # entering side channel
								if vd == vd2:
									foundD = True
									found_dns = True
									snappedDownstream.append(lName)
									snappedDownstream.append(lName2)
									if lName not in dsNwk.keys():
										dsNwk[lName] = [[lName2]]
									else:
										dsNwk[lName][0].append(lName2)
									if len(dsNwk[lName][1]) == 0:
										dsNwk[lName][1].append(lUsInv)
										dsNwk[lName][1].append(lDsInv)
									if len(dsNwk[lName]) < 3:
										dsNwk[lName].append([])
								elif vd == vu2:
									foundD = True
									snappedDownstream.append(lName)
									snappedUpstream.append(lName2)
								elif vu == vu2:  # upstream network
									foundU = True
									snappedUpstream.append(lName)
									snappedUpstream.append(lName2)
									dsNwk[lName][4].append(lName2)
								elif vu == vd2:
									foundU = True
									snappedUpstream.append(lName)
									snappedDownstream.append(lName2)
							else:  # leaving side channel
								if vd == vu2:
									foundD = True
									found_dns = True
									snappedDownstream.append(lName)
									snappedUpstream.append(lName2)
									if lName not in dsNwk.keys():
										dsNwk[lName] = [[lName2]]
									else:
										dsNwk[lName][0].append(lName2)
									if len(dsNwk[lName][1]) == 0:
										dsNwk[lName][1].append(lUsInv)
										dsNwk[lName][1].append(lDsInv)
									if len(dsNwk[lName]) < 3:
										dsNwk[lName].append([])
								elif vd == vd2:  # end vertex to end vertex
									foundD = True
									snappedDownstream.append(lName)
									snappedDownstream.append(lName2)
									dsNwk[lName][3].append(lName2)
								elif vu == vu2:
									foundU = True
									snappedUpstream.append(lName)
									snappedUpstream.append(lName2)
								elif vu == vd2:  # upstream network
									foundU = True
									snappedUpstream.append(lName)
									snappedDownstream.append(lName2)
									dsNwk[lName][4].append(lName2)
						else:  # normal connection
							if vd == vu2:  # end vertex connected to fist vertex i.e. found a dns nwk
								foundD = True
								found_dns = True
								snappedDownstream.append(lName)
								snappedUpstream.append(lName2)
								dsNwk[lName][0].append(lName2)
								if len(dsNwk[lName][1]) == 0:
									dsNwk[lName][1].append(lUsInv)
									dsNwk[lName][1].append(lDsInv)
								polyline = feature.geometry().asPolyline()
								polyline2 = feature2.geometry().asPolyline()
								point1 = [polyline[-2][0], polyline[-2][1]]
								point2 = [polyline[-1][0], polyline[-1][1]]
								point3 = [polyline2[0][0], polyline2[0][1]]
								point4 = [polyline2[1][0], polyline2[1][1]]
								geom1 = [polyline[-2], polyline[-1]]
								geom2 = [polyline2[0], polyline2[1]]
								angle = getAngle(geom1, geom2)
								dsNwk[lName][2].append(angle)
							elif vd == vd2:  # end vertex connected to an end vertex
								foundD = True
								snappedDownstream.append(lName)
								snappedDownstream.append(lName2)
								dsNwk[lName][3].append(lName2)
							elif vu == vd2:  # start vertex connected to an end vertex i.e. found an ups nwk
								foundU = True
								snappedUpstream.append(lName)
								snappedDownstream.append(lName2)
								dsNwk[lName][4].append(lName2)
							elif vu == vu2:  # start vertex connected to a start vertex
								foundU = True
								snappedUpstream.append(lName)
								snappedUpstream.append(lName2)
								dsNwk[lName][5].append(lName2)
						continue
					else:
						dist1a = ((vu2[0] - vu[0]) ** 2 + (vu2[1] - vu[1]) ** 2) ** 0.5  # distance upstream vertex
						dist1b = ((vd2[0] - vu[0]) ** 2 + (vd2[1] - vu[1]) ** 2) ** 0.5  # distance upstream vertex
						dist2a = ((vu2[0] - vd[0]) ** 2 + (vu2[1] - vd[1]) ** 2) ** 0.5  # distance downstream vertex
						dist2b = ((vd2[0] - vd[0]) ** 2 + (vd2[1] - vd[1]) ** 2) ** 0.5  # distance downstream vertex
						minDist1 = min(minDist1, dist1a, dist1b)
						minDist2 = min(minDist2, dist2a, dist2b)
						if minDist1 == dist1a or minDist1 == dist1b:
							name1 = lName2
							if minDist1 == dist1a:
								v1 = vu2
								node1 = 0
							else:
								v1 = vd2
								node1 = 1
						if minDist2 == dist2a or minDist2 == dist2b:
							name2 = lName2
							if minDist2 == dist2a:
								v2 = vu2
								node2 = 0
							else:
								v2 = vd2
								node2 = 1
			if dnsConn and not found_dns:
				if lName not in dsNwk.keys():
					dsNwk[lName] = [[], [], [], [], [], []]
				if len(dsNwk[lName][1]) == 0:
					dsNwk[lName][1].append(lUsInv)
					dsNwk[lName][1].append(lDsInv)
			if not foundU or not foundD:
				if lName not in dsNwk.keys():
					dsNwk[lName] = [[], [], [], [], [], []]
				if len(dsNwk[lName][1]) == 0:
					dsNwk[lName][1].append(lUsInv)
					dsNwk[lName][1].append(lDsInv)
				if lName not in unsnapped_names:
					unsnapped_names.append(lName)
				if not foundU:
					unsnapped.append('{0} upstream'.format(lName))
					if name1 is not None:
						closestV['{0}==0'.format(lName)] = [lLyr, lFid, '{0}=={1}'.format(name1, node1), v1, minDist1, feature]
				if not foundD:
					unsnapped.append('{0} downstream'.format(lName))
					if name2 is not None:
						closestV['{0}==1'.format(lName)] = [lLyr, lFid, '{0}=={1}'.format(name2, node2), v2, minDist2, feature]
		if not checkPoint:
			return unsnapped, unsnapped_names, closestV, dsNwk
	
	# Check to see if point is snapped to a line
	if checkPoint:
		for pName, pParam in pointDict.items():  # loop through all points
			pLoc = pParam[0]
			pFid = pParam[1]
			pLyr = pParam[2]
			feature = pParam[5]
			pUsInv = pParam[3][0]
			pDsInv = pParam[3][1]
			found = False
			minDist = 99999
			name = None
			# Create a buffer object to loop through nearby features
			bufferDist = 25
			xmin = pLoc[0][0] - bufferDist
			xmax = pLoc[0][0] + bufferDist
			ymin = pLoc[0][1] - bufferDist
			ymax = pLoc[0][1] + bufferDist
			rectangle = QgsRectangle(xmin, ymin, xmax, ymax)
			request = QgsFeatureRequest().setFilterRect(rectangle)
			# cycle through nearby features to see if anything is snapped
			for lyr in lineLyrs:
				for i, feature2 in enumerate(lyr.getFeatures(request)):
					if feature2.attributes()[0] != NULL:
						lName = feature2.attributes()[0]
					else:
						for name, param in lineDict.items():
							if lyr.name() == param[2].name() and feature2.id() == param[5].id():
								lName = name
								break
					lParam = lineDict[lName]
					lLoc = lParam[0]
					lFid = lParam[1]
					lUsInv = lParam[3][0]
					lDsInv = lParam[3][1]
					if found and not dnsConn:
						break
					vu = lLoc[0]
					vd = lLoc[1]
					if vu == pLoc[0] or vd == pLoc[0]:
						found = True
						if dnsConn:
							if vu == pLoc[0]:
								if lUsInv == -99999 or lUsInv == NULL:
									if pDsInv != -99999 and pDsInv != NULL:
										usInv = pDsInv
									else:
										usInv = -99999
								else:
									usInv = lUsInv
								dsNwk[lName][1][0] = usInv
							elif vd == pLoc[0]:
								if lDsInv == -99999 or lDsInv == NULL:
									if pDsInv != -99999 and pDsInv != NULL:
										dsInv = pDsInv
									else:
										dsInv = -99999
								else:
									dsInv = lDsInv
								dsNwk[lName][1][1] = dsInv
						continue
					else:
						dist1 = ((vu[0] - pLoc[0][0]) ** 2 + (vu[1] - pLoc[0][1]) ** 2) ** 0.5
						dist2 = ((vd[0] - pLoc[0][0]) ** 2 + (vd[1] - pLoc[0][1]) ** 2) ** 0.5
						minDist = min(minDist, dist1, dist2)
						if minDist == dist1 or minDist == dist2:
							if minDist == dist1:
								v = vu
								name = lName
								node = 0
							elif minDist == dist2:
								v = vd
								name = lName
								node = 1
			#if i + 1 == lineDict_len and not found:
			if not found:
				unsnapped.append(pName)
				if name is not None:
					closestV['{0}'.format(pName)] = [pLyr, pFid, '{0}=={1}'.format(name, node), v, minDist, feature]
		if not dnsConn:
			return unsnapped, closestV
		else:
			return unsnapped, unsnapped_names, closestV, dsNwk


def checkSnappingFlowTrace(**kwargs):
	"""
	Takes vertices and checks if there are any matching and returns a list if there are no matching.
	For points, it will check points against lines.
	For lines, it will check against other lines in the same layer

	:param **kwargs: dictionary with line or point vertices {name: [vertices, origin fid, origin lyr, [us invert,
	ds invert]]}
	:return: list of unsnapped objects (for lines will append '==0' or first vertex, '==1' for last vertex)
	:return: list of unsnapped object names for lines without reference to first or last vertex (not returned for
	points)
	:return: dict of closest line vertex for unsnapped points and lines {name: [origin lyr, origin fid, closest vertex
	name, closest vertex coords, closest vertex dist]}
	:return: dict of downstream channels for lines if dnsConn is True {name: [[dns network channels], [us invert,
	ds invert], [other connecting channels]]}
	"""
	
	# determine which snapping check is being performed
	checkPoint = False
	checkLine = False
	dnsConn = False
	lineDict = kwargs['lines']  # will need lines no matter what
	lineDict_len = len(lineDict)
	lineLyrs = kwargs['line_layers']
	if 'dns_conn' in kwargs.keys():
		if kwargs['dns_conn']:
			dnsConn = True  # force script to loop through all pipes to get all dns connections
			checkLine = True
		if 'points' in kwargs.keys():  # if points included, check elevations in dns connections
			pointDict = kwargs['points']
			pointLyrs = kwargs['point_layers']
			if len(pointDict) > 0:
				checkPoint = True
	if 'assessment' in kwargs.keys():
		if kwargs['assessment'] == 'lines':
			checkLine = True
		elif kwargs['assessment'] == 'points':
			if 'points' in kwargs.keys():  # assessing snapping for points
				checkPoint = True
				pointDict = kwargs['points']
	else:  # assessing for lines
		checkLine = True
	startLines = kwargs['start_lines']
	
	xIns = []  # list of X connectors that are entering a side channel - used to determine dns direction for x
	# connectors
	xIns_index = 0
	xIns_indices = []  # list of indices incase they need to be removed later
	dsNwk = {}  # dict listing the downstream lines
	closestV = {}  # dict closest vertex results
	unsnapped = []  # list of unsnapped vertices
	unsnapped_names = []  # list of unsnapped vertices names (for lines)
	snappedUpstream = []  # list of snapped upstream vertices
	snappedDownstream = []  # list of snapped downstream vertices
	processedFeatures = []
	maxFeatureCount = 0
	mostFeaturedLyr = lineLyrs[0]
	# Check to see if line is snapped to another line
	todos = startLines[:]
	if checkLine:
		while todos:
			lName = todos[0]
			lParam = lineDict[lName]
			lLoc = lParam[0]  # vertices
			lUsInv = lParam[3][0] if lParam[3][0] != NULL else -99999  # upstream invert
			lDsInv = lParam[3][1] if lParam[3][1] != NULL else -99999  # downstream invert
			lFid = lParam[1]  # fid
			lLyr = lParam[2]  # QgsVectorLayer
			feature = lParam[5]  # QgsFeature
			xIn = False  # helps determine downstream direction in relation to X connectors
			vu = lLoc[0]  # upstream vertex
			vd = lLoc[1]  # downstream vertex
			if lName in snappedUpstream:
				foundU = True
			else:
				foundU = False
			if lName in snappedDownstream:
				foundD = True
			else:
				foundD = False
			found_dns = False
			minDist1 = 99999
			minDist2 = 99999
			name1 = None
			name2 = None
			# Create a buffer object to loop through nearby features
			bufferDist = 25
			xmin = min((vu[0] - bufferDist), (vd[0] - bufferDist))
			xmax = max((vu[0] + bufferDist), (vd[0] + bufferDist))
			ymin = min((vu[1] - bufferDist), (vd[1] - bufferDist))
			ymax = max((vu[1] + bufferDist), (vd[1] + bufferDist))
			rectangle = QgsRectangle(xmin, ymin, xmax, ymax)
			request = QgsFeatureRequest().setFilterRect(rectangle)
			# cycle through nearby features to see if anything is snapped
			for lyr in lineLyrs:
				for i, feature2 in enumerate(lyr.getFeatures(request)):
					if feature2.attributes()[0] != NULL:
						lName2 = feature2.attributes()[0]
					else:
						for name, param in lineDict.items():
							if lyr.name() == param[2].name() and feature2.id() == param[5].id():
								lName2 = name
								break
					lParam2 = lineDict[lName2]
					lLoc2 = lParam2[0]
					lLyr2 = lParam2[2]
					lFid2 = lParam2[1]
					idFld2 = lLyr2.fields()[0]
					typFld2 = lLyr2.fields()[1]
					feature2 = lParam2[5]
					if foundU and foundD and not dnsConn:
						break
					vu2 = lLoc2[0]
					vd2 = lLoc2[1]
					if lName == lName2:
						continue
					if vu == vu2 or vu == vd2 or vd == vu2 or vd == vd2:
						if lName not in dsNwk.keys():
							dsNwk[lName] = [[], [], [], [], [],
							                []]  # dsNwk name, us and ds invert, outflow angle, joining nwk dns, upstream network, upstream network to upstream network
						if 'connector' in lName:
							if vu == vu2:  # X Connector is entering side channel
								foundU = True
								if lName2 not in todos and lName2 not in processedFeatures:
									todos.append(lName2)
								snappedUpstream.append(lName)
								snappedUpstream.append(lName2)
								found_dns = True
								xIn = True
								if lName not in xIns:
									xIns.append(lName)
								if lName not in dsNwk.keys():
									dsNwk[lName] = [[lName2]]
								else:
									dsNwk[lName][0].append(lName2)
								if len(dsNwk[lName][1]) == 0:
									dsNwk[lName][1].append(lUsInv)
									dsNwk[lName][1].append(lDsInv)
								if len(dsNwk[lName]) < 3:
									dsNwk[lName].append([])
								if xIns_indices:  # remove since we now know xIn is True
									for xIns_i in xIns_indices:
										dsNwk[lName][0].pop(xIns_i)
							elif vd == vu2 and not xIn:  # X connector is leaving side channel
								foundD = True
								if lName2 not in todos and lName2 not in processedFeatures:
									todos.append(lName2)
								snappedDownstream.append(lName)
								snappedUpstream.append(lName2)
								found_dns = True
								if lName not in dsNwk.keys():
									dsNwk[lName] = [[lName2]]
								else:
									dsNwk[lName][0].append(lName2)
								if len(dsNwk[lName][1]) == 0:
									dsNwk[lName][1].append(lUsInv)
									dsNwk[lName][1].append(lDsInv)
								if len(dsNwk[lName]) < 3:
									dsNwk[lName].append([])
								xIns_indices.append(xIns_index)
								xIns_index += 1
							elif vu == vd2 and not xIn:
								foundU = True
								snappedUpstream.append(lName)
								snappedDownstream.append(lName2)
								dsNwk[lName][4].append(lName2)
								xIns_indices.append(xIns_index)
								xIns_index += 1
							elif vd == vd2 and xIn:  # upstream network
								foundD = True
								snappedDownstream.append(lName)
								snappedDownstream.append(lName2)
								dsNwk[lName][4].append(lName2)
							elif vd == vd2:
								foundD = True
								snappedDownstream.append(lName)
								snappedDownstream.append(lName2)
						elif 'connector' in lName2:  # end normal nwk connected to end X conn
							if lName2 in xIns:  # entering side channel
								if vd == vd2:
									foundD = True
									found_dns = True
									if lName2 not in todos and lName2 not in processedFeatures:
										todos.append(lName2)
									snappedDownstream.append(lName)
									snappedDownstream.append(lName2)
									if lName not in dsNwk.keys():
										dsNwk[lName] = [[lName2]]
									else:
										dsNwk[lName][0].append(lName2)
									if len(dsNwk[lName][1]) == 0:
										dsNwk[lName][1].append(lUsInv)
										dsNwk[lName][1].append(lDsInv)
									if len(dsNwk[lName]) < 3:
										dsNwk[lName].append([])
								elif vd == vu2:
									foundD = True
									if lName2 not in todos and lName2 not in processedFeatures:
										todos.append(lName2)
									snappedDownstream.append(lName)
									snappedUpstream.append(lName2)
								elif vu == vu2:  # upstream network
									foundU = True
									if lName2 not in todos and lName2 not in processedFeatures:
										todos.append(lName2)
									snappedUpstream.append(lName)
									snappedUpstream.append(lName2)
									dsNwk[lName][4].append(lName2)
								elif vu == vd2:
									foundU = True
									if lName2 not in todos and lName2 not in processedFeatures:
										todos.append(lName2)
									snappedUpstream.append(lName)
									snappedDownstream.append(lName2)
							else:  # leaving side channel
								if vd == vu2:
									foundD = True
									found_dns = True
									if lName2 not in todos and lName2 not in processedFeatures:
										todos.append(lName2)
									snappedDownstream.append(lName)
									snappedUpstream.append(lName2)
									if lName not in dsNwk.keys():
										dsNwk[lName] = [[lName2]]
									else:
										dsNwk[lName][0].append(lName2)
									if len(dsNwk[lName][1]) == 0:
										dsNwk[lName][1].append(lUsInv)
										dsNwk[lName][1].append(lDsInv)
									if len(dsNwk[lName]) < 3:
										dsNwk[lName].append([])
								elif vd == vd2:  # end vertex to end vertex
									foundD = True
									if lName2 not in todos and lName2 not in processedFeatures:
										todos.append(lName2)
									snappedDownstream.append(lName)
									snappedDownstream.append(lName2)
									dsNwk[lName][3].append(lName2)
								elif vu == vu2:
									foundU = True
									if lName2 not in todos and lName2 not in processedFeatures:
										todos.append(lName2)
									snappedUpstream.append(lName)
									snappedUpstream.append(lName2)
								elif vu == vd2:  # upstream network
									foundU = True
									if lName2 not in todos and lName2 not in processedFeatures:
										todos.append(lName2)
									snappedUpstream.append(lName)
									snappedDownstream.append(lName2)
									dsNwk[lName][4].append(lName2)
						else:  # normal connection
							if vd == vu2:  # end vertex connected to fist vertex i.e. found a dns nwk
								foundD = True
								found_dns = True
								if lName2 not in todos and lName2 not in processedFeatures:
									todos.append(lName2)
								snappedDownstream.append(lName)
								snappedUpstream.append(lName2)
								dsNwk[lName][0].append(lName2)
								if len(dsNwk[lName][1]) == 0:
									dsNwk[lName][1].append(lUsInv)
									dsNwk[lName][1].append(lDsInv)
								polyline = feature.geometry().asPolyline()
								polyline2 = feature2.geometry().asPolyline()
								point1 = [polyline[-2][0], polyline[-2][1]]
								point2 = [polyline[-1][0], polyline[-1][1]]
								point3 = [polyline2[0][0], polyline2[0][1]]
								point4 = [polyline2[1][0], polyline2[1][1]]
								geom1 = [polyline[-2], polyline[-1]]
								geom2 = [polyline2[0], polyline2[1]]
								angle = getAngle(geom1, geom2)
								dsNwk[lName][2].append(angle)
							elif vd == vd2:  # end vertex connected to an end vertex
								foundD = True
								snappedDownstream.append(lName)
								snappedDownstream.append(lName2)
								dsNwk[lName][3].append(lName2)
							elif vu == vd2:  # start vertex connected to an end vertex i.e. found an ups nwk
								foundU = True
								snappedUpstream.append(lName)
								snappedDownstream.append(lName2)
								dsNwk[lName][4].append(lName2)
							elif vu == vu2:  # start vertex connected to a start vertex
								foundU = True
								snappedUpstream.append(lName)
								snappedUpstream.append(lName2)
								dsNwk[lName][5].append(lName2)
						continue
					else:
						dist1a = ((vu2[0] - vu[0]) ** 2 + (vu2[1] - vu[1]) ** 2) ** 0.5  # distance upstream vertex
						dist1b = ((vd2[0] - vu[0]) ** 2 + (vd2[1] - vu[1]) ** 2) ** 0.5  # distance upstream vertex
						dist2a = ((vu2[0] - vd[0]) ** 2 + (vu2[1] - vd[1]) ** 2) ** 0.5  # distance downstream vertex
						dist2b = ((vd2[0] - vd[0]) ** 2 + (vd2[1] - vd[1]) ** 2) ** 0.5  # distance downstream vertex
						minDist1 = min(minDist1, dist1a, dist1b)
						minDist2 = min(minDist2, dist2a, dist2b)
						if minDist1 == dist1a or minDist1 == dist1b:
							name1 = lName2
							if minDist1 == dist1a:
								v1 = vu2
								node1 = 0
							else:
								v1 = vd2
								node1 = 1
						if minDist2 == dist2a or minDist2 == dist2b:
							name2 = lName2
							if minDist2 == dist2a:
								v2 = vu2
								node2 = 0
							else:
								v2 = vd2
								node2 = 1
			if dnsConn and not found_dns:
				if lName not in dsNwk.keys():
					dsNwk[lName] = [[], [], [], [], [], []]
				if len(dsNwk[lName][1]) == 0:
					dsNwk[lName][1].append(lUsInv)
					dsNwk[lName][1].append(lDsInv)
			if not foundU or not foundD:
				if lName not in dsNwk.keys():
					dsNwk[lName] = [[], [], [], [], [], []]
				if len(dsNwk[lName][1]) == 0:
					dsNwk[lName][1].append(lUsInv)
					dsNwk[lName][1].append(lDsInv)
				if lName not in unsnapped_names:
					unsnapped_names.append(lName)
				if not foundU:
					unsnapped.append('{0} upstream'.format(lName))
					if name1 is not None:
						closestV['{0}==0'.format(lName)] = [lLyr, lFid, '{0}=={1}'.format(name1, node1), v1, minDist1,
						                                    feature]
				if not foundD:
					unsnapped.append('{0} downstream'.format(lName))
					if name2 is not None:
						closestV['{0}==1'.format(lName)] = [lLyr, lFid, '{0}=={1}'.format(name2, node2), v2, minDist2,
						                                    feature]
			processedFeatures.append(lName)
			todos.remove(lName)
		if not checkPoint:
			return unsnapped, unsnapped_names, closestV, dsNwk
		
		# Check to see if point is snapped to a line
		if checkPoint:
			todos = startLines[:]
			for lName in processedFeatures:
				lParam = lineDict[lName]
				lLoc = lParam[0]
				lFid = lParam[1]
				lUsInv = lParam[3][0]
				lDsInv = lParam[3][1]
				vu = lLoc[0]
				vd = lLoc[1]
				found = False
				minDist = 99999
				name = None
				# Create a buffer object to loop through nearby features
				bufferDist = 25
				xmin = min((vu[0] - bufferDist), (vd[0] - bufferDist))
				xmax = max((vu[0] + bufferDist), (vd[0] + bufferDist))
				ymin = min((vu[1] - bufferDist), (vd[1] - bufferDist))
				ymax = max((vu[1] + bufferDist), (vd[1] + bufferDist))
				rectangle = QgsRectangle(xmin, ymin, xmax, ymax)
				request = QgsFeatureRequest().setFilterRect(rectangle)
				# cycle through nearby features to see if anything is snapped
				for lyr in pointLyrs:
					for i, feature2 in enumerate(lyr.getFeatures(request)):
						if feature2.attributes()[0] != NULL:
							pName = feature2.attributes()[0]
						else:
							for name, param in pointDict.items():
								if lyr.name() == param[2].name() and feature2.id() == param[5].id():
										pName = name
										break
						pParam = pointDict[pName]
						pLoc = pParam[0]
						pFid = pParam[1]
						pLyr = pParam[2]
						feature = pParam[5]
						pUsInv = pParam[3][0]
						pDsInv = pParam[3][1]
						if found and not dnsConn:
							break
						if vu == pLoc[0] or vd == pLoc[0]:
							found = True
							if dnsConn:
								if vu == pLoc[0]:
									if lUsInv == -99999 or lUsInv == NULL:
										if pDsInv != -99999 and pDsInv != NULL:
											usInv = pDsInv
										else:
											usInv = -99999
									else:
										usInv = lUsInv
									dsNwk[lName][1][0] = usInv
								elif vd == pLoc[0]:
									if lDsInv == -99999 or lDsInv == NULL:
										if pDsInv != -99999 and pDsInv != NULL:
											dsInv = pDsInv
										else:
											dsInv = -99999
									else:
										dsInv = lDsInv
									dsNwk[lName][1][1] = dsInv
							continue
				# if i + 1 == lineDict_len and not found:
				if not found:
					unsnapped.append(pName)
			if not dnsConn:
				return unsnapped, closestV
			else:
				return unsnapped, unsnapped_names, closestV, dsNwk


def findAllRasterLyrs():
	"""
	
	:return: list of open raster layers
	"""

	rasterLyrs = []
	for name, search_layer in QgsMapLayerRegistry.instance().mapLayers().items():
		if search_layer.type() == 1:
			rasterLyrs.append(search_layer.name())
			
	return rasterLyrs


def moveVertices(lyrs, vertices_dict, dist, units):
	"""
	Edits the vertices within the layer to the snap location if within the distance
	
	:param lyr: layer being edited
	:param dist: allowed move distance
	:param vertices_dict: dictionary containing all required information 
	{name: [[dns network channels], [us invert, ds invert], [other connecting channels]]}
	:return: string of logged moves
	"""

	editedV = []  # for processing
	movedV = []  # for logging
	node = None
	log = ''
	for id, param in vertices_dict.items():
		lyr = param[0]
		lyr.startEditing()
		if id not in editedV:
			if param[4] <= dist:
				if len(id.split('==')) > 1:
					name, node = id.split('==')
				else:
					name = id
				feature = param[5]
				fid = param[1]
				id2 = param[2]
				name2, node2 = id2.split('==')
				v = param[3]
				if node is None or node == '0':
					lyr.moveVertex(v[0], v[1], fid, 0)
				else:
					#for feature in lyr.getFeatures():  # QGIS 3 has the ability to select by FID rather than loop
					#	if feature.id() == fid:
					vertices = feature.geometry().asPolyline()
					lastVertex = len(vertices) - 1
					lyr.moveVertex(v[0], v[1], fid, lastVertex)
				editedV.append(id)
				editedV.append(id2)
				movedV.append(id)
				if node is None:
					log += 'Moved {0} {5:.4f}{6} to {1} {4} ({2:.4f}, {3:.4f})\n'.format(name, name2, v[0],
																						  v[1],
																						  'upstream' if node2
																										== '0'
																						  else 'downstream',
																						  param[4], units)
				elif node == '0':
					log += 'Moved {0} upstream {5:.4f}{6} to {1} {4} ({2:.4f}, {3:.4f})\n'.format(name, name2,
																								   v[0],
																								   v[1],
																								   'upstream'
																								   if node2 == '0'
																								   else
																								   'downstream',
																								   param[4], units)
				else:
					log += 'Moved {0} downstream {5:.4f}{6} to {1} {4} ({2:.4f}, {3:.4f})\n'.format(name,
																									 name2,
																									 v[0],
																									 v[1],
																									 'upstream' if
																									 node2 ==
																									 '0' else
																									 'downstream',
																									 param[4], units)
		lyr.commitChanges()

	return movedV, log


def interpolateObvert(usInv, dsInv, size, xValues):
	"""
	Creates a list of obvert elevations for chainages along a pipe
	
	:param usInv: float - upstream invert
	:param dsInv: float - downstream invert
	:param xValues: list - chainage values to map obvert elevations to
	:param size: float - pipe height
	:return: list - obvert elevations
	"""
	
	usObv = usInv + size
	dsObv = dsInv + size
	xStart = xValues[0]
	xEnd = xValues[-1]
	obvert = []
	for i, x in enumerate(xValues):
		if i == 0:
			obvert.append(usObv)
		elif i == len(xValues) - 1:
			obvert.append(dsObv)
		else:
			interpolate = (dsObv - usObv) / (xEnd - xStart) * (x - xStart) + usObv
			obvert.append(interpolate)
	return obvert


def readInvFromCsv(source, type):
	"""
	Reads Table CSV file and returns the invert
	
	:param source: string - csv source file
	:param type: string - table type
	:return: float - invert
	"""

	header = False
	firstCol = []
	secondCol = []
	with open(source, 'r') as fo:
		for f in fo:
			line = f.split(',')
			if not header:
				try:
					float(line[0].strip('\n').strip())
					header = True
				except:
					pass
			if header:
				firstCol.append(float(line[0].strip('\n').strip()))
				secondCol.append(float(line[1].strip('\n').strip()))
	if type.lower() == 'xz' or type.lower()[0] == 'w':
		return min(secondCol)
	else:
		return min(firstCol)
	
	
def findIntersectFromVertex(vert, lyrs):
	"""
	Find an intersecting layer from a vertex
	
	:param vert: list - [float X, float Y]
	:param taLyrs: list - [QgsVectorLayer]
	:return: QgsFeature, QgsVectorLayer
	"""
	
	for lyr in lyrs:
		for f in lyr.getFeatures():
			geom = f.geometry().asPolyline()
			for v in geom:
				if v == vert:
					return f, lyr
	return None, None


def getElevFromTa(lineDict, dsLines, lineLyrs, taLyrs):
	"""
	Use 1d_ta layers to populate elevations of network
	
	:param lineDict: dict {name: [[vertices], feature id, origin lyr, [us invert, ds invert], type}
	:param dsLines: dict # dictionary {name: [[dns network channels], [us invert, ds invert], [angle], [dns-dns connected channels], [upsnetworks}, [ups-ups channels]]
	:param taLyrs: list QgsVectorLayer
	:return: updated dsLines dict with updated us and ds inverts
	"""
	
	for name, param in lineDict.items():
		type = param[4]
		usInv = dsLines[name][1][0]
		dsInv = dsLines[name][1][1]
		usVert = param[0][0]
		dsVert = param[0][1]
		lyr = param[2]
		fid = param[1]
		fld = lyr.fields()
		usFound = False
		dsFound = False
		filter = '"{0}" = \'{1}\''.format(fld[0].name(), name)
		request = QgsFeatureRequest().setFilterExpression(filter)
		for f in lyr.getFeatures(request):
			if f.id() == fid:
				feature = f
		if type.lower() != 'r' and type.lower() != 'c':
			if usInv == -99999:
				taFeat, taLyr = findIntersectFromVertex(usVert, taLyrs)
				if taFeat is not None:
					taType = taFeat.attributes()[1]
					source = taFeat.attributes()[0]
					lyrSource = taLyr.dataProvider().dataSourceUri().split('|')[0]
					lyrDirPath = os.path.dirname(lyrSource)
					taSource = os.path.join(lyrDirPath, source)
					usInv = readInvFromCsv(taSource, taType)
					usFound = True
			if dsInv == -99999:
				taFeat, taLyr = findIntersectFromVertex(dsVert, taLyrs)
				if taFeat is not None:
					taType = taFeat.attributes()[1]
					source = taFeat.attributes()[0]
					lyrSource = taLyr.dataProvider().dataSourceUri().split('|')[0]
					lyrDirPath = os.path.dirname(lyrSource)
					taSource = os.path.join(lyrDirPath, source)
					dsInv = readInvFromCsv(taSource, taType)
					dsFound = True
			if (usInv == -99999 and dsInv == -99999) or type.lower()[0] == 'w':
				geom = feature.geometry()
				for taLyr in taLyrs:
					for taFeat in taLyr.getFeatures():
						geom2 = taFeat.geometry()
						if geom.intersects(geom2):
							taType = taFeat.attributes()[1]
							source = taFeat.attributes()[0]
							lyrSource = taLyr.dataProvider().dataSourceUri().split('|')[0]
							lyrDirPath = os.path.dirname(lyrSource)
							taSource = os.path.join(lyrDirPath, source)
							usInv = dsInv = readInvFromCsv(taSource, taType)
							usFound = True
							dsFound = True
			if usFound:
				dsLines[name][1][0] = usInv
			if dsFound:
				dsLines[name][1][1] = dsInv
	return dsLines


def getNetworkMidLocation(feature):
	"""
	Returns the location of the mid point along a polyline

	:param usVertex: QgsPoint
	:param dsVetex: QgsPoint
	:return: QgsPoint
	"""

	from math import sin, cos, asin
	
	length = getLength(feature)
	desiredLength = length / 2.
	points, chainages = lineToPoints(feature, 99999)
	chPrev = 0
	for i, ch in enumerate(chainages):
		if ch > desiredLength and chPrev < desiredLength:
			break
		else:
			chPrev = ch
	usVertex = points[i-1]
	dsVertex = points[i]
	length = ((dsVertex[1] - usVertex[1]) ** 2. + (dsVertex[0] - usVertex[0]) ** 2.) ** 0.5
	newLength = desiredLength - chPrev
	angle = asin((dsVertex[1] - usVertex[1]) / length)
	x = usVertex[0] + (newLength * cos(angle)) if dsVertex[0] - usVertex[0] >= 0 else usVertex[0] - (newLength * cos(
		angle))
	y = usVertex[1] + (newLength * sin(angle))
	return QgsPoint(x, y)


def checkNetworkCover(drape, height, usInvert, dsInvert, limit):
	"""

	:param drape: list - [QgsPoint], [Chainages], [Elevations]
	:param height: float
	:param usInvert: float
	:param dsInvert: float
	:param limit: float
	:return: Bool
	:return: QgsPoint
	"""

	flag = False
	point = None
	obverts = interpolateObvert(usInvert, dsInvert, height, drape[1])
	for i, elevation in enumerate(drape[2]):
		if type(elevation) == float:
			if elevation - obverts[i] < limit:
				flag = True
				point = drape[0][i]
				break
	return flag, point, drape[1][i]


def checkNetworkContinuity(lineDict, dsLines, lineDrape, angleLimit, coverLimit, check, units):
	"""

	:param lineDict: dict - {name: [[vertices], feature id, origin lyr, [us invert, ds invert], type}
	:param dsLines: dict - # dictionary {name: [[dns network channels], [us invert, ds invert], [angle], [dns-dns connected channels], [upsnetworks}, [ups-ups channels]]
	:param lineDrape: dict - {name: {[QgsPoint], [Chainages], [Elevations]]}
	:param angleLimit: int
	:param coverLimit: float
	:param check: list - Bool checkArea, Bool checkGradient, Bool checkAngle, Bool checkCover
	:param units:
	:return log: string - logged moves
	:return location: list - list of vertices
	"""

	checkArea = check[0]
	checkGradient = check[1]
	checkAngle = check[2]
	checkCover = check[3]
	log = ''
	location = []
	warningType = []
	for name, parameter in dsLines.items():
		if '__connector' not in name:
			# define known variables
			dnsNames = parameter[0]
			usInvert = parameter[1][0]
			dsInvert = parameter[1][1]
			if len(parameter[2]) > 0:
				angle = min(parameter[2])
			else:
				angle = 0
			if name in lineDrape.keys():
				drape = lineDrape[name]
			else:
				drape = None
			usVertex = lineDict[name][0][0]
			dsVertex = lineDict[name][0][1]
			type = lineDict[name][4]
			lyr = lineDict[name][2]
			fid = lineDict[name][1]
			idFld = lyr.fields()[0]
			typFld = lyr.fields()[1]
			feature = lineDict[name][5]
			midVertex = getNetworkMidLocation(feature)
			usArea = 0
			dsArea = 0
			dnsUsInvert = 99999
			dnsDsInvert = 99999
			if type.lower() == 'c' or type.lower() == 'r':
				no = feature.attributes()[15]
				width = feature.attributes()[13]
				height = feature.attributes()[14]
				if type.lower() == 'c':
					if width != NULL:
						if no != NULL:
							usArea = no * 3.14 * (width / 2) ** 2
						else:
							usArea = 3.14 * (width / 2) ** 2
				elif type.lower() == 'r':
					if width != NULL:
						if no != NULL:
							usArea = no * width * height
						else:
							usArea = width * height
			# check for x connectors
			for dnsName in dnsNames[:]:
				if 'connector' in dnsName:
					dnsNames += dsLines[dnsName][0]
					dnsNames.remove(dnsName)
			# calculate upstream and downstream area and get downstream inverts
			for dnsName in dnsNames:
				dnsType = lineDict[dnsName][4]
				dnsLyr = lineDict[dnsName][2]
				dnsFid = lineDict[dnsName][1]
				dnsFeature = lineDict[dnsName][5]
				if dnsType.lower() == 'c' or dnsType.lower() == 'r':
					dnsNo = dnsFeature.attributes()[15]
					dnsWidth = dnsFeature.attributes()[13]
					dnsHeight = dnsFeature.attributes()[14]
					if dnsType.lower() == 'c':
						if dnsWidth != NULL:
							if dnsNo != NULL:
								dsArea += dnsNo * 3.14 * (dnsWidth / 2) ** 2
							else:
								dsArea += 3.14 * (dnsWidth / 2) ** 2
					elif dnsType.lower() == 'r':
						if dnsWidth != NULL:
							if dnsNo != NULL:
								dsArea += dnsNo * dnsWidth * dnsHeight
							else:
								dsArea += dnsWidth * dnsHeight
				if dsLines[dnsName][1][0] != -99999:
					dnsUsInvert = min(dnsUsInvert, dsLines[dnsName][1][0])
				if dsLines[dnsName][1][1] != -99999:
					dnsDsInvert = min(dnsDsInvert, dsLines[dnsName][1][1])
			# change back to null value if non-existent
			if dnsUsInvert == 99999:
				dnsUsInvert = -99999
			if dnsDsInvert == 99999:
				dnsDsInvert = -99999
			# perfrom checks
			if checkArea:
				if usArea != 0 and dsArea != 0:
					if dsArea < usArea:
						log += '{0} decreases in area downstream ({0} {1:.1f}{2}2, {3} {4:.1f}{2}2)\n' \
							   .format(name, usArea, units, (dnsNames[0] if len(dnsNames) == 1 else dnsNames), dsArea)
						warningType.append('Area Warning')
						location.append(dsVertex)
			if checkGradient:
				if usInvert != -99999 and dsInvert != -99999:
					if dsInvert > usInvert:
						log += '{0} has an adverse gradient (upstream {1:.3f}{2}RL, downstream {3:.3f}{2}RL)\n' \
							   .format(name, usInvert, units, dsInvert)
						warningType.append('Gradient Warning')
						location.append(midVertex)
				if dsInvert != -99999 and dnsUsInvert != -99999:
					if dnsUsInvert > dsInvert:
						log += '{0} outlet ({1:.3f}{2}RL) is lower than downstream {3} inlet ({4:.3f}{2}RL)\n' \
							   .format(name, dsInvert, units, (dnsNames[0] if len(dnsNames) == 1 else dnsNames), dnsUsInvert)
						warningType.append('Invert Warning')
						location.append(dsVertex)
			if checkAngle:
				if angle != 0:
					if angle < angleLimit:
						log += '{0} outlet angle ({1:.1f} deg) is less than input angle limit ({2:.1f} deg)\n' \
							   .format(name, angle, angleLimit)
						warningType.append('Angle Warning')
						location.append(dsVertex)
			if checkCover:
				if usInvert != -99999 and dsInvert != -99999:
					coverFlag = False
					if type.lower() == 'c':
						coverFlag, point, chainage = checkNetworkCover(drape, width, usInvert, dsInvert, coverLimit)
					elif type.lower() == 'r':
						coverFlag, point, chainage = checkNetworkCover(drape, height, usInvert, dsInvert, coverLimit)
					if coverFlag:
						log += '{0} cover depth is below input limit {1} at {2:.1f}{3} along network\n' \
							   .format(name, coverLimit, chainage, units)
						warningType.append('Cover Warning')
						location.append(point)
	return log, warningType, location


def correctPipeDirectionByInvert(lineLyrs, lineDict, units):
	"""
	
	:param lineDict: dict - {name: [[vertices], feature id, origin lyr, [us invert, ds invert], type}
	:param dsLines: dict - # dictionary {name: [[dns network channels], [us invert, ds invert], [angle], [dns-dns connected channels], [upsnetworks}, [ups-ups channels]]
	:param units: string - 'm' or 'ft' or ''
	:return: string, string, QgsPoint
	"""

	log = ''
	messageType = []
	messageLocation = []
	for lyr in lineLyrs:
		for feature in lyr.getFeatures():
			type = feature.attributes()[1]
			if type.lower() != 'x':
				fid = feature.id()
				name = feature.attributes()[0]
				usInvert = feature.attributes()[6]
				dsInvert = feature.attributes()[7]
				usVertex = lineDict[name][0][0]
				dsVertex = lineDict[name][0][1]
				midVertex = getNetworkMidLocation(feature)
				if usInvert != -99999 and dsInvert != -99999:
					if dsInvert > usInvert:
						geom = feature.geometry().asPolyline()
						reversedGeom = geom[::-1]
						lyr.startEditing()
						for i in range(len(geom)):
							lyr.moveVertex(reversedGeom[i][0], reversedGeom[i][1], fid, i)
						lyr.changeAttributeValue(fid, 6, dsInvert, usInvert)
						lyr.changeAttributeValue(fid, 7, usInvert, dsInvert)
						lyr.commitChanges()
						log += '{0} line direction has been reversed based on inverts ({1:.3f}{2}RL, {3:.3f}{2}RL)\n' \
							.format(name, usInvert, units, dsInvert)
						messageType.append('line direction edit')
						messageLocation.append(midVertex)
	return log, messageType, messageLocation


def correctPipeDirectionFromConnections(lineDict, dsLines):
	"""
	Reverses the pipe direction based on the upstream and downstream pipe directions
	
	:param lineDict: dict - {name: [[vertices], feature id, origin lyr, [us invert, ds invert], type}
	:param dsLines: dict - dictionary {name: [[dns network channels], [us invert, ds invert], [angle], [dns-dns connected channels], [ups networks}, [ups-ups channels]]
	:return: string, string, QgsPoint
	"""

	log = ''
	messageType = []
	messageLocation = []
	for name, parameter in dsLines.items():
		if '__connector' not in name:
			dsNwks = parameter[0]
			usNwks = parameter[4]
			dsDsNwks = parameter[3]
			usUsNwks = parameter[5]
			if len(dsDsNwks) > 0 and len(usUsNwks) > 0 and len(dsNwks) == 0 and len(usNwks) == 0:
				lyr = lineDict[name][2]
				fid = lineDict[name][1]
				feature = lineDict[name][5]
				midVertex = getNetworkMidLocation(feature)
				geom = feature.geometry().asPolyline()
				reversedGeom = geom[::-1]
				lyr.startEditing()
				for i in range(len(geom)):
					lyr.moveVertex(reversedGeom[i][0], reversedGeom[i][1], fid, i)
				lyr.commitChanges()
				log += '{0} line direction has been reversed based on upstream and downstream connected networks\n' \
					.format(name)
				messageType.append('line direction edit')
				messageLocation.append(midVertex)
	return log, messageType, messageLocation
					

def getPathFromRel(dir, relPath):
	"""
	return the full path from a relative reference
	
	:param dir: string - directory
	:param relPath: string - relative path
	:return: string - full path
	"""
	
	components = relPath.split('\\')
	path = dir
	for c in components:
		if c == '..':
			path = os.path.dirname(path)
		else:
			path = os.path.join(path, c)
	return path


def removeLayer(lyr):
	"""
	Removes the layer from the TOC once only. This is for when it the same layer features twice in the TOC.
	
	:param lyr: QgsVectorLayer
	:return: void
	"""

	if lyr is not None:
		root = QgsProject.instance().layerTreeRoot()
		for i, child in enumerate(root.children()):
			lyrName = lyr.name()
			childName = child.name()
			if child.name() == lyr.name() or child.name() == '{0} Point'.format(lyr.name()) or child.name() == '{0} LineString'.format(lyr.name()) or child.name() == '{0} Polygon'.format(lyr.name()):
				root.removeChildNode(child)


def loadGisFromControlFile(controlFile, iface, processed_paths, processed_layers, scenarios):
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
			elif 'end if' in f.lower():
				ind = f.lower().find('end if')
				if '!' not in f[:ind]:
					read = True
			elif not read:
				continue
			elif 'read' in f.lower():
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
							path = getPathFromRel(dir, relPath)
							if path in processed_paths:
								continue
							ext = os.path.splitext(path)[1]
							if ext.lower() == '.mid':
								path = '{0}.mif'.format(os.path.splitext(path)[0])
								ext = '.mif'
							if ext.lower() == '.shp':
								try:
									if os.path.exists(path):
										lyr = iface.addVectorLayer(path, os.path.basename(os.path.splitext(path)[0]), 'ogr')
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
										lyr = iface.addVectorLayer(path, os.path.basename(os.path.splitext(path)[0]), 'ogr')
										lyrName = os.path.basename(os.path.splitext(path)[0])
										for name, layer in QgsMapLayerRegistry.instance().mapLayers().items():
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
										lyr = iface.addRasterLayer(path, os.path.basename(os.path.splitext(path)[0]), 'gdal')
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
	lyrs = [c.layer() for c in group.children()]
	lyrs_sorted = sorted(lyrs, key=lambda x: x.name())
	for i, lyr in enumerate(lyrs_sorted):
		treeLyr = group.insertLayer(i, lyr)
	group.removeChildren(len(lyrs), len(lyrs))
	return error, log, processed_paths, processed_layers


def openGisFromTcf(tcf, iface, *args):
	"""
	Opens all vector layers from the tuflow model from the TCF
	
	:param tcf: string - TCF location
	:param iface: QgisInterface
	:return: void - opens all files in qgis window
	"""
	
	scenarios = []
	for arg in args:
		scenarios = arg
	
	dir = os.path.dirname(tcf)
	processed_paths = []
	processed_layers = []
	couldNotReadFile = False
	message = 'Could not open file:\n'
	error, log, pPaths, pLayers = loadGisFromControlFile(tcf, iface, processed_paths, processed_layers, scenarios)
	processed_paths += pPaths
	processed_layers += pLayers
	if error:
		couldNotReadFile = True
		message += log
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
					error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths, processed_layers, scenarios)
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
					path = getPathFromRel(dir, relPath)
					error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths, processed_layers, scenarios)
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
					path = getPathFromRel(dir, relPath)
					error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths, processed_layers, scenarios)
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
					path = getPathFromRel(dir, relPath)
					error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths, processed_layers, scenarios)
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
					path = getPathFromRel(dir, relPath)
					error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths, processed_layers, scenarios)
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
					path = getPathFromRel(dir, relPath)
					error, log, pPaths, pLayers = loadGisFromControlFile(path, iface, processed_paths, processed_layers, scenarios)
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
					scenario = scenario.split('!')[0]  # split string by ! and take first entry i.e. remove any comments after command
					scenario = scenario.strip()  # strip blank spaces and new lines \n
					scenarios = scenario.split('|')  # split scenarios by | in case there is more than one specified
					for scenario in scenarios:  # loop through scenarios and add to list if not already there
						scenario = scenario.strip()
						if scenario not in processedScenarios:
							processedScenarios.append(scenario)
	return processedScenarios


def getScenariosFromTcf(tcf, iface):
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
