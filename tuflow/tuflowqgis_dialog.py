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
import dateutil.parser
try:
	import matplotlib.pyplot as plt
except:
	current_path = os.path.dirname(__file__)
	sys.path.append(os.path.join(current_path, '_tk\\DLLs'))
	sys.path.append(os.path.join(current_path, '_tk\\libs'))
	sys.path.append(os.path.join(current_path, '_tk\\Lib'))
	import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from tuflow.tuflowqgis_library import interpolate, convertStrftimToTuviewftim, convertTuviewftimToStrftim, browse
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
		self.fname = None
		self.curr_file = None
		
		if cLayer:
			cName = cLayer.name()
			dp = cLayer.dataProvider()
			ds = dp.dataSourceUri()
			fpath = os.path.dirname(unicode(ds))
			self.fpath = fpath
			basename = os.path.basename(unicode(ds))
			ind = basename.find('|')
			if (ind>0):
				fname = basename[0:ind]
			else:
				fname = basename
			self.fname = fname
			self.curr_file = os.path.join(fpath,fname)
		else:
			QMessageBox.information( self.iface.mainWindow(),"Information", "No layer is currently selected in the layer control")

		self.browseoutfile.clicked.connect(self.browse_outfile)
		self.pbOk.clicked.connect(self.run)
		self.pbCancel.clicked.connect(self.reject)
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
		newname = QFileDialog.getSaveFileName(self, "Output Shapefile", outfolder, "*.shp *.SHP")
		if len(newname) > 0:
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
		# collect information
		layername = unicode(self.sourcelayer.currentText())
		layer = tuflowqgis_find_layer(layername)
		outname = unicode(self.outfilename.displayText()).strip()
		if not outname[-4:].upper() == '.SHP':
			outname = outname+'.shp'
			# QMessageBox.information( self.iface.mainWindow(),"Information", "Appending .shp to filename.")
		outfolder = unicode(self.outfolder.displayText()).strip()
		savename = os.path.join(outfolder, outname)
		if savename == self.curr_file:
			QMessageBox.critical( self.iface.mainWindow(),"ERROR", "Output filename is the same as the current layer.")
			return
		
		# check if file exists
		if os.path.isfile(savename):
			# ask if the user wants to override data
			override_existing = QMessageBox.question(self, "Increment Layer", 'File alreay exists. Do you want to replace the existing file?',
			                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
			if override_existing == QMessageBox.No or override_existing == QMessageBox.Cancel:
				return
		
		# duplicate layer with incremented name
		message = tuflowqgis_duplicate_file(self.iface, layer, savename, False)
		if message != None:
			QMessageBox.critical(self.iface.mainWindow(), "Duplicating File", message)
		
		# change existing layer datasource to incremented layer
		changeDataSource(self.iface, layer, savename)
		
		# check if need to move to SS folder
		if self.cbMoveToSS.isChecked():
			ssFolder = os.path.join(outfolder, 'ss')
			if not os.path.exists(ssFolder):
				os.mkdir(ssFolder)
			name = os.path.splitext(self.fname)[0]
			search = os.path.join(outfolder, name) + '.*'
			files = glob.glob(search)
			for file in files:
				os.rename(file, os.path.join(ssFolder, os.path.basename(file)))
		
		# check if need to keep layer in workspace
		if self.rbKeepSource.isChecked():  # remove layer
			if self.cbMoveToSS.isChecked():
				oldFile = os.path.join(ssFolder, self.fname)
			else:
				oldFile = os.path.join(outfolder, self.fname)
			oldLayer = self.iface.addVectorLayer(oldFile, os.path.basename(oldFile)[:-4], "ogr")
			copyLayerStyle(self.iface, layer, oldLayer)
			
		self.accept()
			

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
		showToolTip = QgsProject.instance().readBoolEntry("TUFLOW", "import_empty_tooltip", True)[0]
		self.teToolTip.setVisible(showToolTip)
		self.pbShowToolTip.setVisible(not showToolTip)
		self.pbHideToolTip.setVisible(showToolTip)
		self.teToolTip.setTabStopWidth(16)
		
		# find out which tuflow engine to use
		self.engine = 'classic'  # set a default - other option is 'flexible mesh'
		self.tfsettings = TF_Settings()
		error, message = self.tfsettings.Load()
		if self.tfsettings.project_settings.engine:
			self.engine = self.tfsettings.project_settings.engine
		
		# load stored settings
		error, message = self.tfsettings.Load()
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", "Error Loading Settings: "+message)
			
		engine = self.tfsettings.combined.engine
		self.parent_folder_name = 'TUFLOWFV' if engine == 'flexible mesh' else 'TUFLOW'
		
		self.browsedir.clicked.connect(self.browse_empty_dir)
		self.emptydir.editingFinished.connect(self.dirChanged)
		self.pbShowToolTip.clicked.connect(self.toggleToolTip)
		self.pbHideToolTip.clicked.connect(self.toggleToolTip)
		self.emptyType.itemSelectionChanged.connect(self.updateToolTip)
		self.pbOk.clicked.connect(self.run)
		self.pbCancel.clicked.connect(self.reject)

		if self.tfsettings.combined.base_dir:
			subfolders = [self.parent_folder_name.lower(), 'model', 'gis', 'empty']
			emptydir = self.tfsettings.combined.base_dir
			for i, subfolder in enumerate(subfolders):
				for p in os.walk(emptydir):
					for d in p[1]:
						if d.lower() == subfolder:
							if i == 0:
								self.parent_folder_name = d
							emptydir = os.path.join(emptydir, d)
							break
					break
			self.emptydir.setText(emptydir)
			#self.emptydir.setText(os.path.join(self.tfsettings.combined.base_dir, self.parent_folder_name, "model", "gis", "empty"))
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
			if not files:
				search_string = '{0}{1}*.SHP'.format(self.emptydir.text(), os.path.sep)
				files = glob.glob(search_string)
			empty_list = []
			for file in files:
				if len(file.split('_empty')) < 2:
					continue
				empty_type = os.path.basename(file.split('_empty')[0])
				if empty_type not in empty_list:
					empty_list.append(empty_type)
			empty_list = sorted(empty_list)
			self.emptyType.addItems(empty_list)
		
	def toggleToolTip(self):
		showToolTip = not self.teToolTip.isVisible()
		self.teToolTip.setVisible(showToolTip)
		self.pbShowToolTip.setVisible(not showToolTip)
		self.pbHideToolTip.setVisible(showToolTip)
		h = self.height()
		self.adjustSize()
		w = self.width()
		self.resize(w, h)
		
	def updateToolTip(self):
		self.teToolTip.clear()
		self.teToolTip.setFontUnderline(True)
		self.teToolTip.setTextColor(QColor(Qt.black))
		self.teToolTip.setFontFamily('MS Shell Dlg 2')
		self.teToolTip.setFontPointSize(18)
		self.teToolTip.setFontWeight(QFont.Bold)
		self.teToolTip.append('Tool Tip')
		self.teToolTip.append('\n')
		items = self.emptyType.selectedItems()
		for item in items:
			tooltip = findToolTip(item.text(), self.engine)
			if tooltip['location'] is not None:
				self.teToolTip.setFontUnderline(False)
				self.teToolTip.setTextColor(QColor(Qt.black))
				self.teToolTip.setFontFamily('Courier New')
				self.teToolTip.setFontPointSize(13)
				self.teToolTip.setFontWeight(QFont.Normal)
				self.teToolTip.append(tooltip['location'])
				self.teToolTip.append('\n')
			if tooltip['command'] is not None:
				html = "<body style=\" font-family:'Courier New'; font-size:8.25pt; font-weight:400; " \
				       "font-style:normal;\"><p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; " \
				       "margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; " \
				       "color:#0000ff;\">{0} </span><span style=\" font-size:12pt; " \
				       "color:#ff0000;\">==</span></p></body>".format(tooltip['command'])
				self.teToolTip.insertHtml(html)
				self.teToolTip.append('\n')
			if tooltip['description'] is not None:
				self.teToolTip.setFontUnderline(False)
				self.teToolTip.setTextColor(QColor(Qt.black))
				self.teToolTip.setFontFamily('MS Shell Dlg 2')
				self.teToolTip.setFontPointSize(10)
				self.teToolTip.setFontWeight(QFont.Normal)
				self.teToolTip.append(tooltip['description'])
				self.teToolTip.append('\n')
			if tooltip['wiki link'] is not None:
				self.teToolTip.setFontUnderline(False)
				self.teToolTip.setTextColor(QColor(Qt.black))
				self.teToolTip.setFontFamily('MS Shell Dlg 2')
				self.teToolTip.setFontPointSize(10)
				self.teToolTip.setFontWeight(QFont.Bold)
				self.teToolTip.append('TUFLOW Wiki')
				self.teToolTip.append('\n')
				html = "<body style=\" font-family:'MS Shell Dlg 2'; font-size:10pt; font-weight:400; " \
				       "font-style:normal;\"><p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; " \
				       "margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><a href=\"{0}\">" \
				       "<span style=\" text-decoration: underline; " \
				       "color:#0000ff;\">{0}</span></a></p></body></html>".format(tooltip['wiki link'])
				self.teToolTip.insertHtml(html)
				self.teToolTip.append('\n')
			if tooltip['manual link'] is not None:
				self.teToolTip.setFontUnderline(False)
				self.teToolTip.setTextColor(QColor(Qt.black))
				self.teToolTip.setFontFamily('MS Shell Dlg 2')
				self.teToolTip.setFontPointSize(10)
				self.teToolTip.setFontWeight(QFont.Bold)
				self.teToolTip.append('TUFLOW Manual')
				self.teToolTip.append('\n')
				page = ''
				if tooltip['manual page'] is not None:
					page = '#page={0}'.format(tooltip['manual page'])
				html = "<body style=\" font-family:'MS Shell Dlg 2'; font-size:10pt; font-weight:400; " \
				       "font-style:normal;\"><p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; " \
				       "margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><a href=\"{0}{1}\">" \
				       "<span style=\" text-decoration: underline; " \
				       "color:#0000ff;\">{0}{1}</span></a></p></body></html>".format(tooltip['manual link'], page)
				self.teToolTip.insertHtml(html)
				self.teToolTip.append('\n')
	
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
			if not files:
				search_string = '{0}{1}*.SHP'.format(self.emptydir.text(), os.path.sep)
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
		message = tuflowqgis_import_empty_tf(self.iface, basedir, runID, empty_types, points, lines, regions, self)
		#message = tuflowqgis_create_tf_dir(self.iface, crs, basedir)
		if message is not None:
			if message != 1:
				QMessageBox.critical(self.iface.mainWindow(), "Importing {0} Empty File(s)".format(self.parent_folder_name), message)
		else:
			self.accept()

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
		inFileName = QFileDialog.getOpenFileName(self, 'Select TUFLOW Control File', self.runfolder,
		                                         "All Supported Formats (*.tcf *.fvc *.TCF *.FVC);;"
		                                         "TCF (*.tcf *.TCF);;FVC (*.fvc *.FVC)")
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
		inFileName = QFileDialog.getOpenFileName(self, 'Select TUFLOW exe', self.exefolder, "TUFLOW Executable (*.exe)")
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
	def __init__(self, iface, project, parent=None):
		QDialog.__init__(self, parent)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		cLayer = self.canvas.currentLayer()
		self.tfsettings = TF_Settings()
		self.crs = None
		fname = ''

		error, message = self.tfsettings.Load()
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", message)
		
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
			
		# engine
		if self.tfsettings.project_settings.engine:
			if self.tfsettings.project_settings.engine == 'classic':
				self.rbTuflowCla.setChecked(True)
			elif self.tfsettings.project_settings.engine == 'flexible mesh':
				self.rbTuflowFM.setChecked(True)
			else:
				self.rbTuflowCla.setChecked(True)
		elif self.tfsettings.global_settings.engine:
			if self.tfsettings.global_settings.engine == 'classic':
				self.rbTuflowCla.setChecked(True)
			elif self.tfsettings.global_settings.engine == 'flexible mesh':
				self.rbTuflowFM.setChecked(True)
			else:
				self.rbTuflowCla.setChecked(True)
				
		# tutorial
		if self.tfsettings.combined.tutorial:
			if type(self.tfsettings.combined.tutorial) is str:
				self.tfsettings.combined.tutorial = True if self.tfsettings.combined.tutorial == 'True' else False
			self.cbTutorial.setChecked(self.tfsettings.combined.tutorial)
				
		self.browseoutfile.clicked.connect(self.browse_outdir)
		self.browseexe.clicked.connect(self.browse_exe)
		self.pbSelectCRS.clicked.connect(self.select_CRS)
		self.sourcelayer.currentIndexChanged[int].connect(self.layer_changed)
		self.buttonBox.accepted.connect(self.run)

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
		if sys.platform == 'win32':
			ftypes = "TUFLOW Executable (*.exe)"
		else:
			ftypes = "TUFLOW Executable (*)"
		inFileName = QFileDialog.getOpenFileName(self, 'Select TUFLOW exe', last_dir, ftypes)


		inFileName = inFileName[0]
		if len(inFileName) == 0: # If the length is 0 the user pressed cancel 
			return
		# Store the exe location and path we just looked in
		self.TUFLOW_exe.setText(inFileName)
		self.tfsettings.save_last_exe(inFileName)

	def layer_changed(self):
		layername = self.sourcelayer.currentText()
		if layername != "Use saved projection":
			layer = tuflowqgis_find_layer(layername)
			if layer != None:
				self.crs = layer.crs()
				self.form_crsID.setText(self.crs.authid())
				self.crsDesc.setText(self.crs.description())
	def run(self):
		tf_prj = self.form_crsID.displayText().strip()
		engine = 'flexible mesh' if self.rbTuflowFM.isChecked() else 'classic'
		parent_folder_name = 'TUFLOWFV' if engine == 'flexible mesh' else 'TUFLOW'
		tutorial = self.cbTutorial.isChecked()
		basedir = self.outdir.displayText().strip()
		path_split = basedir.split('/')
		for p in path_split[:]:
			path_split += p.split(os.sep)
			path_split.remove(p)
		if path_split[-1].lower() == parent_folder_name.lower():
			basedir = os.path.dirname(basedir)
		tfexe = self.TUFLOW_exe.displayText().strip()
		
		baseexe = os.path.basename(tfexe)
		if 'tuflowfv' in baseexe.lower():
			if engine == 'classic':
				fv = QMessageBox.question(self, "TUFLOW Project Settings",
				                          "Executable Appears to be TUFLOW Flexible Mesh . . . "
				                          "Would You Like to Create a TUFLOW Flexible Mesh Project "
				                          "Instead of TUFLOW Classic / HPC?",
				                          QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
				if fv == QMessageBox.Cancel:
					return
				elif fv == QMessageBox.Yes:
					engine = 'flexible mesh'
		
		#Save Project Settings
		self.tfsettings.project_settings.CRS_ID = tf_prj
		self.tfsettings.project_settings.tf_exe = tfexe
		self.tfsettings.project_settings.base_dir = basedir
		self.tfsettings.project_settings.engine = engine
		self.tfsettings.project_settings.tutorial = tutorial
		error, message = self.tfsettings.Save_Project()
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", "Error Saving Project Settings. Message: "+message)
		#else:
		#	QMessageBox.information( self.iface.mainWindow(),"Information", "Project Settings Saved")
		
		# Save Global Settings
		if self.cbGlobal.isChecked():
			self.tfsettings.global_settings.CRS_ID = tf_prj
			self.tfsettings.global_settings.tf_exe = tfexe
			self.tfsettings.global_settings.base_dir = basedir
			self.tfsettings.global_settings.engine = engine
			self.tfsettings.global_settings.tutorial = tutorial
			error, message = self.tfsettings.Save_Global()
			if error:
				QMessageBox.information( self.iface.mainWindow(),"Error", "Error Saving Global Settings. Message: "+message)
			#else:
			#	QMessageBox.information( self.iface.mainWindow(),"Information", "Global Settings Saved")
		
		if self.cbCreate.isChecked():
			crs = QgsCoordinateReferenceSystem()
			crs.createFromString(tf_prj)
	
			message = tuflowqgis_create_tf_dir(self, crs, basedir, engine, tutorial)
			if message != None:
				QMessageBox.critical(self.iface.mainWindow(), "Creating TUFLOW Directory ", message)
		
		if self.cbRun.isChecked():
			ext = '.fvc' if engine == 'flexible mesh' else '.tcf'
			runfile = os.path.join(basedir, parent_folder_name, "runs", "Create_Empties{0}".format(ext))
			#QMessageBox.information(self.iface.mainWindow(), "Running {0}".format(parent_folder_name),"Starting simulation: "+runfile+"\n Executable: "+tfexe)
			message = run_tuflow(self.iface, tfexe, runfile)
			if message != None:
				QMessageBox.critical(self.iface.mainWindow(), "Running {0} ".format(parent_folder_name), message)
			
			
		
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

		self.browsedir.clicked.connect(self.browse_empty_dir)
		self.buttonBox.accepted.connect(self.run)
		
		engine = self.tfsettings.combined.engine
		self.parent_folder_name = 'TUFLOWFV' if engine == 'flexible mesh' else 'TUFLOW'

		if self.last_chk_folder == "Undefined":
			if self.tfsettings.combined.base_dir:
				subfolders = [self.parent_folder_name.lower(), 'check']
				checkdir = self.tfsettings.combined.base_dir
				for i, subfolder in enumerate(subfolders):
					for p in os.walk(checkdir):
						for d in p[1]:
							if d.lower() == subfolder:
								if i == 0:
									self.parent_folder_name = d
								checkdir = os.path.join(checkdir, d)
								break
						break
				self.last_chk_folder = checkdir
				self.emptydir.setText(self.last_chk_folder)
		else:
			self.emptydir.setText(self.last_chk_folder)

	def browse_empty_dir(self):
		newname = QFileDialog.getExistingDirectory(None, "Output Directory", self.last_chk_folder)
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
		message = tuflowqgis_import_check_tf(self.iface, basedir, runID, showchecks)
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
		icon = QIcon(os.path.join(os.path.dirname(__file__), "icons", "arr2016.PNG"))
		self.setWindowIcon(icon)
		
		# Set up Input Catchment File ComboBox
		for name, layer in QgsProject.instance().mapLayers().items():
				if layer.type() == QgsMapLayer.VectorLayer:
					if layer.geometryType() == QgsWkbTypes.PointGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry:
						self.comboBox_inputCatchment.addItem(layer.name())
							
		layerName = self.comboBox_inputCatchment.currentText()
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
		
		# set up output format
		outputFormatIndex = int(QSettings().value("ARR2016_output_format", 0))
		self.comboBox_outputF.setCurrentIndex(outputFormatIndex)
		
		# set up output notation
		outputNotationIndex = int(QSettings().value("ARR2016_output_notation", 0))
		self.comboBox_outputN.setCurrentIndex(outputNotationIndex)
		
		# setup preburst percentile
		preBurstIndex = int(QSettings().value("ARR2016_preburst_percentile", 0))
		self.comboBox_preBurstptile.setCurrentIndex(preBurstIndex)
		
		# set up initial loss for short durations
		ilMethodIndex = int(QSettings().value("ARR2016_IL_short_durations", 0))
		self.comboBox_ilMethod.setCurrentIndex(ilMethodIndex)
		if ilMethodIndex == 2 or ilMethodIndex == 3:
			ilInputValue = QSettings().value("ARR2016_IL_input_value", "")
			if type(ilInputValue) is str:
				self.mar_staticValue.setText(ilInputValue)
				
		# Set up MAR and Static Value box
		if self.comboBox_ilMethod.currentIndex() == 2 or self.comboBox_ilMethod.currentIndex() == 3:
			self.mar_staticValue.setEnabled(True)
		else:
			self.mar_staticValue.setEnabled(False)
			
		# tuflow loss method
		tuflowLMindex = int(QSettings().value("ARR2016_TUFLOW_loss_method", 0))
		self.cboTuflowLM.setCurrentIndex(tuflowLMindex)
		
		# min arf
		minARFValue = float(QSettings().value("ARR2016_min_arf", 0))
		self.minArf.setValue(minARFValue)
		
		# setup browse boxes
		folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
		self.btnBrowsePTP.setIcon(folderIcon)
		self.btnBrowseATP.setIcon(folderIcon)
		self.btnBrowseOut.setIcon(folderIcon)
		self.btnBrowseARRFile.setIcon(folderIcon)
		self.btnBrowseBOMFile.setIcon(folderIcon)
		
		self.comboBox_inputCatchment.currentIndexChanged.connect(self.catchmentLayer_changed)
		self.checkBox_aepAll.clicked.connect(self.aep_all)
		self.checkBox_durAll.clicked.connect(self.dur_all)
		self.radioButton_ARF_auto.clicked.connect(self.toggle_comboBox_CatchArea)
		self.radioButton_ARF_manual.clicked.connect(self.toggle_comboBox_CatchArea)
		self.comboBox_ilMethod.currentIndexChanged.connect(self.ilMethod_changed)
		self.btnBrowsePTP.clicked.connect(lambda: self.browse("existing file", "ARR2016_browse_PTP",
		                                                      "ARR2016 Point Temporal Pattern",
		                                                      "CSV format (*.csv *.CSV)", self.lePTP))
		self.btnBrowseATP.clicked.connect(lambda: self.browse("existing file", "ARR2016_browse_ATP",
		                                                      "ARR2016 Areal Temporal Pattern",
		                                                      "CSV format (*.csv *.CSV)", self.leATP))
		self.btnBrowseOut.clicked.connect(lambda: self.browse("existing folder", "ARR2016_browse_out",
		                                                      "Output Folder", None, self.outfolder))
		self.btnBrowseARRFile.clicked.connect(lambda: self.browse("existing file", "ARR2016_datahub_file",
		                                                          "ARR2016 Datahub File",
		                                                          "TXT format (*.txt *.TXT)", self.leARRFile))
		self.btnBrowseBOMFile.clicked.connect(lambda: self.browse("existing file", "BOM_IFD_file",
		                                                          "BOM IFD File",
		                                                          "HTML format (*.html *.HTML)", self.leBOMFile))
		self.pbOk.clicked.connect(self.check)
		self.pbCancel.clicked.connect(self.reject)

		self.preburstTPMethodChanged()
		self.preburstUnitsChanged()
		self.cboDurTP.setCurrentIndex(1)
		self.cboDurTPChanged()
		self.cboPreburstTPMethod.currentIndexChanged.connect(self.preburstTPMethodChanged)
		self.cboPreburstDurUnits.currentIndexChanged.connect(self.preburstUnitsChanged)
		self.cboDurTP.currentIndexChanged.connect(self.cboDurTPChanged)

	def cboDurTPChanged(self, e=None):
		"""
		What happens when preburst temporal pattern duration combobox is changed.

		:param e: QEvent
		:return: None
		"""

		if self.cboDurTP.currentIndex() == 0:
			self.cboDurTP.resize(self.cboDurTP.sizeHint())
			self.wProportion.setVisible(True)
		else:
			self.cboDurTP.resize(self.cboDurTP.sizeHint())
			self.wProportion.setVisible(False)


	def preburstUnitsChanged(self, e=None):
		"""
		What happens when preburst constant rate unit combobox is changed.
		Change the suffix in spinbox.

		:param e: QEvent
		:return: None
		"""

		if self.cboPreburstDurUnits.currentIndex() == 0:
			self.cboPreburstDurUnits.resize(self.cboPreburstDurUnits.sizeHint())
			self.sbPreBurstDur.setSuffix(" min")
			self.sbPreBurstDur.setDecimals(0)
			self.sbPreBurstDur.setMinimum(1)
		elif self.cboPreburstDurUnits.currentIndex() == 1:
			self.cboPreburstDurUnits.resize(self.cboPreburstDurUnits.sizeHint())
			self.sbPreBurstDur.setSuffix(" hr")
			self.sbPreBurstDur.setDecimals(2)
			self.sbPreBurstDur.setMinimum(0.01)
		elif self.cboPreburstDurUnits.currentIndex() == 2:
			self.cboPreburstDurUnits.resize(self.cboPreburstDurUnits.sizeHint())
			self.sbPreBurstDur.setSuffix("")
			self.sbPreBurstDur.setDecimals(2)
			self.sbPreBurstDur.setMinimum(0.01)
	
	def preburstTPMethodChanged(self, e=None):
		"""
		What happens when preburst TP method is changed.
		Make the different method widgets visible / not visible

		:param e: QEvent
		:return: None
		"""

		if self.cboPreburstTPMethod.currentIndex() == 0:
			self.wPreburstConstant.setVisible(True)
			self.wPreburstTP.setVisible(False)
		elif self.cboPreburstTPMethod.currentIndex() == 1:
			self.wPreburstConstant.setVisible(False)
			self.wPreburstTP.setVisible(True)

	def catchmentLayer_changed(self):
		layerName = self.comboBox_inputCatchment.currentText()
		layer = tuflowqgis_find_layer(layerName)
		fieldname2index = {f: i for i, f in enumerate(layer.fields().names())}
		
		# Set up Catchment Field ID ComboBox
		if self.comboBox_CatchID.currentText() in fieldname2index:
			fieldIndex = fieldname2index[self.comboBox_CatchID.currentText()]
		else:
			fieldIndex = 0
		self.comboBox_CatchID.clear()
		if layer is not None:
			for f in layer.fields().names():
				self.comboBox_CatchID.addItem(f)
		self.comboBox_CatchID.setCurrentIndex(fieldIndex)
		
		# Set up Catchment Area Field ComboBox
		if self.radioButton_ARF_auto.isChecked():
			self.comboBox_CatchArea.setEnabled(False)
		else:
			if self.comboBox_CatchArea.currentText() in fieldname2index:
				fieldIndex = fieldname2index[self.comboBox_CatchArea.currentText()] + 1  # +1 because '-none-' is added as first
			else:
				fieldIndex = 0
			self.comboBox_CatchArea.setEnabled(True)
			self.comboBox_CatchArea.clear()
			self.comboBox_CatchArea.addItem('-None-')
			if layer is not None:
				for f in layer.fields().names():
					self.comboBox_CatchArea.addItem(f)
			self.comboBox_CatchArea.setCurrentIndex(fieldIndex)
	
	def browse(self, browseType, key, dialogName, fileType, lineEdit):
		"""
		Browse folder directory

		:param type: str browse type 'folder' or 'file'
		:param key: str settings key
		:param dialogName: str dialog box label
		:param fileType: str file extension e.g. "AVI files (*.avi)"
		:param lineEdit: QLineEdit to be updated by browsing
		:return: void
		"""

		settings = QSettings()
		lastFolder = settings.value(key)
		startDir = "C:\\"
		if lastFolder:  # if outFolder no longer exists, work backwards in directory until find one that does
			while lastFolder:
				if os.path.exists(lastFolder):
					startDir = lastFolder
					break
				else:
					lastFolder = os.path.dirname(lastFolder)
		if browseType == 'existing folder':
			f = QFileDialog.getExistingDirectory(self, dialogName, startDir)
		elif browseType == 'existing file':
			f = QFileDialog.getOpenFileName(self, dialogName, startDir, fileType)[0]
		else:
			return
		if f:
			lineEdit.setText(f)
			settings.setValue(key, f)
		
	def toggle_comboBox_CatchArea(self):
		layerName = self.comboBox_inputCatchment.currentText()
		layer = tuflowqgis_find_layer(layerName)
		
		if self.radioButton_ARF_auto.isChecked():
			self.comboBox_CatchArea.setEnabled(False)
		else:
			self.comboBox_CatchArea.setEnabled(True)
			self.comboBox_CatchArea.clear()
			self.comboBox_CatchArea.addItem('-None-')
			if layer is not None:
				for f in layer.fields().names():
					self.comboBox_CatchArea.addItem(f)
					
	def ilMethod_changed(self):
		ilMethod = self.comboBox_ilMethod.currentText()
		
		if ilMethod == 'Hill et al 1996: 1998' or ilMethod == 'Static Value':
			self.mar_staticValue.setEnabled(True)
		else:
			self.mar_staticValue.setEnabled(False)
			
	def AEPs(self):
		self.rare_events = 'false'
		self.frequent_events = 'false'
		self.AEP_list = ''
		if self.checkBox_1p.isChecked():
			self.AEP_list += '1AEP '
		if self.checkBox_2p.isChecked():
			self.AEP_list += '2AEP '
		if self.checkBox_5p.isChecked():
			self.AEP_list += '5AEP '
		if self.checkBox_10p.isChecked():
			self.AEP_list += '10AEP '
		if self.checkBox_20p.isChecked():
			self.AEP_list += '20AEP '
		if self.checkBox_50p.isChecked():
			self.AEP_list += '50AEP '
		if self.checkBox_63p.isChecked():
			self.AEP_list += '63.2AEP '
		if self.checkBox_200y.isChecked():
			self.AEP_list += '200ARI '
			self.rare_events = 'true'
		if self.checkBox_500y.isChecked():
			self.AEP_list += '500ARI '
			self.rare_events = 'true'
		if self.checkBox_1000y.isChecked():
			self.AEP_list += '1000ARI '
			self.rare_events = 'true'
		if self.checkBox_2000y.isChecked():
			self.AEP_list += '2000ARI '
			self.rare_events = 'true'
		if self.checkBox_12ey.isChecked():
			self.AEP_list += '12EY '
			self.frequent_events = 'true'
		if self.checkBox_6ey.isChecked():
			self.AEP_list += '6EY '
			self.frequent_events = 'true'
		if self.checkBox_4ey.isChecked():
			self.AEP_list += '4EY '
			self.frequent_events = 'true'
		if self.checkBox_3ey.isChecked():
			self.AEP_list += '3EY '
			self.frequent_events = 'true'
		if self.checkBox_2ey.isChecked():
			self.AEP_list += '2EY '
			self.frequent_events = 'true'
		if self.checkBox_05ey.isChecked():
			self.AEP_list += '0.5EY '
			self.frequent_events = 'true'
		if self.checkBox_02ey.isChecked():
			self.AEP_list += '0.2EY '
			self.frequent_events = 'true'
			
	def durations(self):
		self.dur_list = 'none'
		self.nonstnd_list = 'none'
		if self.checkBox_10m.isChecked():
			self.dur_list += '10m '
		if self.checkBox_15m.isChecked():
			self.dur_list += '15m '
		if self.checkBox_20m.isChecked():
			self.nonstnd_list += '20m '
		if self.checkBox_25m.isChecked():
			self.nonstnd_list += '25m '
		if self.checkBox_30m.isChecked():
			self.dur_list += '30m '
		if self.checkBox_45m.isChecked():
			self.nonstnd_list += '45m '
		if self.checkBox_60m.isChecked():
			self.dur_list += '60m '
		if self.checkBox_90m.isChecked():
			self.nonstnd_list += '90m '
		if self.checkBox_120m.isChecked():
			self.dur_list += '2h '
		if self.checkBox_180m.isChecked():
			self.dur_list += '3h '
		if self.checkBox_270m.isChecked():
			self.nonstnd_list += '270m '
		if self.checkBox_6h.isChecked():
			self.dur_list += '6h '
		if self.checkBox_9h.isChecked():
			self.nonstnd_list += '9h '
		if self.checkBox_12h.isChecked():
			self.dur_list += '12h '
		if self.checkBox_18h.isChecked():
			self.nonstnd_list += '18h '
		if self.checkBox_24h.isChecked():
			self.dur_list += '24h '
		if self.checkBox_30h.isChecked():
			self.nonstnd_list += '30h '
		if self.checkBox_36h.isChecked():
			self.nonstnd_list += '36h '
		if self.checkBox_48h.isChecked():
			self.dur_list += '48h '
		if self.checkBox_72h.isChecked():
			self.dur_list += '72h '
		if self.checkBox_96h.isChecked():
			self.dur_list += '96h '
		if self.checkBox_120h.isChecked():
			self.dur_list += '120h '
		if self.checkBox_144h.isChecked():
			self.dur_list += '144h '
		if self.checkBox_168h.isChecked():
			self.dur_list += '168h '
		if self.dur_list != 'none':
			self.dur_list = self.dur_list.strip('none')
		if self.nonstnd_list != 'none':
			self.nonstnd_list = self.nonstnd_list.strip('none')
			
	def climateChange(self):
		self.cc_years = 'none'
		self.cc_rcp = 'none'
		self.cc = 'false'
		if self.checkBox_2030.isChecked():
			self.cc_years += '2030 '
		if self.checkBox_2040.isChecked():
			self.cc_years += '2040 '
		if self.checkBox_2050.isChecked():
			self.cc_years += '2050 '
		if self.checkBox_2060.isChecked():
			self.cc_years += '2060 '
		if self.checkBox_2070.isChecked():
			self.cc_years += '2070 '
		if self.checkBox_2080.isChecked():
			self.cc_years += '2080 '
		if self.checkBox_2090.isChecked():
			self.cc_years += '2090 '
		if self.checkBox_45rcp.isChecked():
			self.cc_rcp += '4.5 '
		if self.checkBox_6rcp.isChecked():
			self.cc_rcp += '6 '
		if self.checkBox_85rcp.isChecked():
			self.cc_rcp += '8.5 '
		if self.cc_years != 'none':
			self.cc = 'true'
			self.cc_years = self.cc_years.strip('none')
		if self.cc_rcp != 'none':
			self.cc = 'true'
			self.cc_rcp = self.cc_rcp.strip('none')
			
	def check(self):
		"""Do some basic checks on inputs before trying to run"""
		layerName = self.comboBox_inputCatchment.currentText()
		layer = tuflowqgis_find_layer(layerName)
		if layer is None:
			QMessageBox.critical(self.iface.mainWindow(), "ERROR", "Must select a layer.")
			return
		self.AEPs()
		if not self.AEP_list:
			QMessageBox.critical(self, "ARR2016 to TUFLOW", "Must select at least one AEP")
			return
		self.durations()
		if self.dur_list == 'none' and self.nonstnd_list == 'none':
			QMessageBox.critical(self, "ARR2016 to TUFLOW", "Must select at least one duration")
			return
		self.climateChange()
		if self.cc == 'true':
			if self.cc_years == 'none':
				QMessageBox.critical(self, "ARR2016 to TUFLOW", "Must select a year when calculating climate change")
				return
			if self.cc_rcp == 'none':
				QMessageBox.critical(self, "ARR2016 to TUFLOW", "Must select a RCP when calculating climate change")
				return
		if self.lePTP.text():
			if not os.path.exists(self.lePTP.text()):
				QMessageBox.critical(self, "ARR2016 to TUFLOW", "Point Temporal Pattern CSV does not exist")
				return
		if self.leATP.text():
			if not os.path.exists(self.leATP.text()):
				QMessageBox.critical(self, "ARR2016 to TUFLOW", "Areal Temporal Pattern CSV does not exist")
				return
		if self.mar_staticValue.text():
			try:
				float(self.mar_staticValue.text())
				if float(self.mar_staticValue.text()) < 0:
					QMessageBox.critical(self, "ARR2016 to TUFLOW",
					                     "{0} cannot be less than zero".format(self.comboBox_ilMethod.currentText()))
					return
			except ValueError:
				QMessageBox.critical(self, "ARR2016 to TUFLOW",
				                     "{0} must be a number".format(self.comboBox_ilMethod.currentText()))
				return
		if self.outfolder.text() == '<outfolder>':
			QMessageBox.critical(self, "ARR2016 to TUFLOW", "Must specify an output folder")
			return
		if not self.outfolder.text():
			QMessageBox.critical(self, "ARR2016 to TUFLOW", "Must specify an output folder")
			return
		if self.gbOfflineMode.isChecked():
			if not self.leARRFile.text():
				QMessageBox.critical(self, "ARR2016 to TUFLOW", "Must specify an ARR datahub file in offline mode")
				return
			if not os.path.exists(self.leARRFile.text()):
				QMessageBox.critical(self, "ARR2016 to TUFLOW",
				                     "ARR datahub file does not exist: {0}".format(self.leARRFile.text()))
				return
			if not self.leBOMFile.text():
				QMessageBox.critical(self, "ARR2016 to TUFLOW", "Must specify an BOM IFD file in offline mode")
				return
			if not os.path.exists(self.leBOMFile.text()):
				QMessageBox.critical(self, "ARR2016 to TUFLOW",
				                     "BOM IFD file does not exist: {0}".format(self.leBOMFile.text()))
				return
		self.run()
		
	def updateProgress(self, catchment_no, total_no, start_again=False):
		if start_again:
			self.timer.stop()
		if self.progressCount == -1:
			self.pbOk.setEnabled(False)
			self.pbCancel.setEnabled(False)
			QApplication.setOverrideCursor(Qt.WaitCursor)
			self.progressBar.setRange(0, 0)
			self.progressCount = 0
			start_again = True
		if self.progressCount == 4:
			self.progressCount = 0
		else:
			self.progressCount += 1
		progressLabel = 'Processing (Catchment {0} of {1})'.format(catchment_no, total_no) + ' .' * self.progressCount
		self.progressLabel.setText(progressLabel)
		QgsApplication.processEvents()
		
		if start_again:
			self.timer = QTimer()
			self.timer.setInterval(500)
			self.timer.timeout.connect(lambda: self.updateProgress(catchment_no, total_no))
			self.timer.start()
		
	def complete(self, error, outFolder):
		self.thread.quit()
		self.timer.stop()
		self.progressBar.setMaximum(100)
		self.progressBar.setValue(100)
		QApplication.restoreOverrideCursor()
		if error:
			self.progressLabel.setText("Errors occured")
			if type(error) is bytes:
				error = error.decode('utf-8')
			QMessageBox.critical(self, "Message",
			                     'Process Complete with errors. Please see\n{0}\nfor more information on ' \
			                     'warning and error messages.\n\n{1}' \
			                     .format(os.path.join(outFolder, 'log.txt'), error))
		else:
			self.progressLabel.setText("Complete")
			QMessageBox.information(self, "Message",
			                        'Process Complete. Please see\n{0}\nfor warning and error messages.' \
			                        .format(os.path.join(outFolder, 'log.txt')))
			
		self.saveDefaults()
	
	def run(self):
		
		# get layer
		layerName = self.comboBox_inputCatchment.currentText()
		layer = tuflowqgis_find_layer(layerName)
		
		# Get format
		format = self.comboBox_outputF.currentText()
		
		# Get output notation
		output_notation = self.comboBox_outputN.currentText()
		
		# Get output folder
		outFolder = self.outfolder.displayText().strip()
		if not os.path.exists(outFolder):  # check output directory exists
			os.mkdir(outFolder)
			
		# Get preburst percentile
		preburst = self.comboBox_preBurstptile.currentText()
		if preburst == 'Median':
			preburst = '50%'
			
		# Get IL method < 60min
		mar = '0'
		staticValue = '0'
		
		ilMethod = self.comboBox_ilMethod.currentText()
		if ilMethod == 'Interpolate to zero':
			ilMethod = 'interpolate'
		elif ilMethod == 'Rahman et al 2002':
			ilMethod = 'rahman'
		elif ilMethod == 'Hill et al 1996: 1998':
			ilMethod = 'hill'
			mar = self.mar_staticValue.displayText()
			if mar == '':
				QMessageBox.critical(self.iface.mainWindow(),"ERROR", "Mean Annual Rainfall (MAR) must be specified for Hill et al loss method and must be greater than 0")
			if float(mar) <= 0:
				QMessageBox.critical(self.iface.mainWindow(),"ERROR", "Mean Annual Rainfall (MAR) must be specified for Hill et al loss method and must be greater than 0")
		elif ilMethod == 'Static Value':
			ilMethod = 'static'
			staticValue = self.mar_staticValue.displayText()
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
			
		# get file path to point and areal temporal pattern csv files
		point_tp_csv = 'none'
		if self.lePTP.text():
			point_tp_csv = self.lePTP.text()
		areal_tp_csv = 'none'
		if self.leATP.text():
			areal_tp_csv = self.leATP.text()
			
		# get tuflow loss method
		tuflowLossMethod = 'infiltration' if self.cboTuflowLM.currentIndex() == 0 else 'excess'
		
		# get user defined losses
		userInitialLoss = 'none'
		if self.cbUserIL.isChecked():
			userInitialLoss = str(self.sbUserIL.value())
		userContinuingLoss = 'none'
		if self.cbUserCL.isChecked():
			userContinuingLoss = str(self.sbUserCL.value())
		urbanInitialLoss = 'none'
		urbanContinuingLoss = 'none'
		if self.gbUrbanLosses.isChecked():
			urbanInitialLoss = '{0}'.format(self.sbUrbanIL.value())
			urbanContinuingLoss = '{0}'.format(self.sbUrbanCL.value())
		
		# Get Minimum ARF Value
		minArf = str(self.minArf.value())
		# should arf be applied to events less than 50% AEP?
		if self.cbArfFrequent.isChecked():
			arfFrequent = 'true'
		else:
			arfFrequent = 'false'
		
		# Get area and ID from input layer
		idField = self.comboBox_CatchID.currentText()
		area_list = []
		name_list = []
		for feature in layer.getFeatures():
			area_list.append(str(feature.geometry().area() / 1000000))
			name = str(feature[idField])
			if not name:
				name = 'NULL'
			name_list.append(name)
		
		areaField = self.comboBox_CatchArea.currentText()
		if not self.radioButton_ARF_auto.isChecked():
			if areaField == '-None-':
				area_list = ['0'] * len(name_list)
			else:
				area_list = []
				for feature in layer.getFeatures():
					if areaField in layer.fields().names():
						try:
							a = float(feature[areaField])
						except ValueError:
							QMessageBox.critical(self.iface.mainWindow(),"ERROR",
									 "Area Field must contain numbers only.")
							return
						area_list.append(str(a))
					else:
						try:
							a = float(areaField)
							if a < 0:
								a = 0
							area_list = ['{0}'.format(a)] * len(name_list)
						except ValueError:
							QMessageBox.critical(self.iface.mainWindow(), "ERROR",
							                     "User area must either be field containing the area or a user "
							                     "input number.")
							return

		parameters = {'INPUT': layer, 'TARGET_CRS': 'epsg:4203', 'OUTPUT': 'memory:Reprojected'}
		reproject = processing.run("qgis:reprojectlayer", parameters)
		reproject_layer = reproject['OUTPUT']

		centroid_list = []
		for feature in reproject_layer.getFeatures():
			centroid = []
			centroid.append('{0:.4f}'.format(feature.geometry().centroid().asPoint()[0]))
			centroid.append('{0:.4f}'.format(feature.geometry().centroid().asPoint()[1]))
			centroid_list.append(centroid)
		del reproject
		del reproject_layer
		
		# offline mode
		if self.gbOfflineMode.isChecked():
			offlineMode = 'true'
			arrFile = self.leARRFile.text()
			bomFile = self.leBOMFile.text()
		else:
			offlineMode = 'false'
			arrFile = 'none'
			bomFile = 'none'

		# probability neutral burst initial loss
		pnil = 'true' if self.cbPNIL.isChecked() else 'false'

		# preburst tp
		complete_storm = 'true' if self.cbCompleteStorm.isChecked() else 'false'
		preburst_proportional = 'false'
		preburst_pattern = 'none'
		preburst_pattern_dur = 'none'
		preburst_pattern_tp = 'none'
		if self.cbCompleteStorm.isChecked():
			if self.cboPreburstTPMethod.currentIndex() == 0:
				preburst_pattern = 'constant'
				if self.cboPreburstDurUnits.currentIndex() == 0:
					preburst_pattern_dur = f'{self.sbPreBurstDur.value()/60.:.4f}'
				elif self.cboPreburstDurUnits.currentIndex() == 1:
					preburst_pattern_dur = f'{self.sbPreBurstDur.value():.2f}'
				elif self.cboPreburstDurUnits.currentIndex() == 2:
					preburst_proportional = 'true'
					preburst_pattern_dur = f'{self.sbPreBurstDur.value():.2f}'
			elif self.cboPreburstTPMethod.currentIndex() == 1:
				preburst_pattern = 'tp'
				preburst_pattern_tp = self.cboTP.currentText()
				if self.cboDurTP.currentIndex() == 0:
					preburst_proportional = 'true'
					preburst_pattern_dur = f'{self.sbProportion.value():.2f}'
				else:
					preburst_pattern_dur = self.cboDurTP.currentText()

		
		# get system arguments and call ARR2016 tool
		# use QThread so that progress bar works properly
		self.thread = QThread()
		self.arr2016 = Arr2016()  # QObject so that it can be sent to QThread
		self.arr2016.load(os.path.join(outFolder, 'log.txt'))
		self.arr2016.sys_args.clear()
		script = os.path.join(currentFolder, 'ARR2016', 'ARR_to_TUFLOW.py')
		for i in range(len(name_list)):
			sys_args = ['python3', script, '-out', outFolder, '-name', name_list[i], 
						'-coords', centroid_list[i][0], centroid_list[i][1], '-mag', self.AEP_list,
						'-frequent', self.frequent_events, '-rare', self.rare_events, '-dur', self.dur_list,
						'-nonstnd', self.nonstnd_list, '-area', area_list[i], '-cc', self.cc, '-year', self.cc_years,
						'-rcp', self.cc_rcp, '-format', format, '-catchment_no', str(i),
						'-output_notation', output_notation, '-preburst', preburst, '-lossmethod', ilMethod,
						'-mar', mar, '-lossvalue', staticValue, '-minarf', minArf, '-addtp', addTp,
			            '-tuflow_loss_method', tuflowLossMethod, '-point_tp', point_tp_csv, '-areal_tp', areal_tp_csv,
			            '-offline_mode', offlineMode, '-arr_file', arrFile, '-bom_file', bomFile,
			            '-user_initial_loss', userInitialLoss, '-user_continuing_loss', userContinuingLoss,
			            '-arffreq', arfFrequent, '-urban_initial_loss', urbanInitialLoss,
			            '-urban_continuing_loss', urbanContinuingLoss,
			            '-probability_neutral_losses', pnil,
			            '-complete_storm', complete_storm, '-preburst_pattern_method', preburst_pattern,
			            '-preburst_pattern_dur', preburst_pattern_dur, '-preburst_pattern_tp', preburst_pattern_tp,
			            '-preburst_dur_proportional', preburst_proportional]
			self.arr2016.append(sys_args, name_list[i])
			
		self.arr2016.moveToThread(self.thread)
		self.arr2016.updated.connect(lambda i: self.updateProgress(i + 1, len(name_list), True))
		self.arr2016.finished.connect(lambda error: self.complete(error, outFolder))
		self.thread.started.connect(self.arr2016.run)
		self.progressCount = -1
		self.thread.start()
		self.updateProgress(1, len(name_list))  # update progress bar.. I hope it was worth the effort of using QThread!
	
	def saveDefaults(self):
		settings = QSettings()
		settings.setValue("ARR2016_preburst_percentile", self.comboBox_preBurstptile.currentIndex())
		settings.setValue("ARR2016_IL_short_durations", self.comboBox_ilMethod.currentIndex())
		if self.comboBox_ilMethod.currentIndex() == 2 or self.comboBox_ilMethod.currentIndex() == 3:
			settings.setValue("ARR2016_IL_input_value", self.mar_staticValue.text())
		settings.setValue("ARR2016_TUFLOW_loss_method", self.cboTuflowLM.currentIndex())
		settings.setValue("ARR2016_min_arf", self.minArf.value())
		settings.setValue("ARR2016_output_format", self.comboBox_outputF.currentIndex())
		settings.setValue("ARR2016_output_notation", self.comboBox_outputN.currentIndex())
		if self.lePTP.text():
			settings.setValue("ARR2016_browse_PTP", self.lePTP.text())
		if self.leATP.text():
			settings.setValue("ARR2016_browse_ATP", self.leATP.text())
		if self.gbOfflineMode.isChecked():
			if self.leARRFile.text():
				settings.setValue("ARR2016_datahub_file", self.leARRFile.text())
			if self.leBOMFile.text():
				settings.setValue("BOM_IFD_file", self.leBOMFile.text())
		settings.setValue("ARR2016_browse_out", self.outfolder.text())
		
		self.accept()

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


class Arr2016(QObject):

	finished = pyqtSignal(str)
	updated = pyqtSignal(int)
	sys_args = []
	name_list = []
	
	def load(self, logfile):
		self.logfile = logfile
		
	def append(self, sys_args, name):
		self.sys_args.append(sys_args)
		self.name_list.append(name)

	def run(self):
		try:
			errors = ''
			for i, sys_args in enumerate(self.sys_args):
				if i > 0:
					self.updated.emit(i)
				#if i == 0:
				#	logfile = open(self.logfile, 'wb')
				#else:
				#	logfile = open(self.logfile, 'ab')

				CREATE_NO_WINDOW = 0x08000000  # suppresses python console window
				error = False
				if sys.platform == 'win32':
					try:  # for some reason (in QGIS2 at least) creationsflags didn't work on all computers
						proc = subprocess.Popen(sys_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
						                        creationflags=CREATE_NO_WINDOW)
						out, err = proc.communicate()
						#logfile.write(out)
						#logfile.write(err)
						#logfile.close()
						if err:
							if type(err) is bytes:
								err = err.decode('utf-8')
							errors += '{0} - {1}'.format(self.name_list[i], err)
					except:
						try:
							proc = subprocess.Popen(sys_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
							out, err = proc.communicate()
							#logfile.write(out)
							#logfile.write(err)
							#logfile.close()
							if err:
								if type(err) is bytes:
									err = err.decode('utf-8')
								errors += '{0} - {1}'.format(self.name_list[i], err)
						except:
							error = 'Error with subprocess call'
				else:  # linux and mac
					try:
						proc = subprocess.Popen(sys_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
						out, err = proc.communicate()
						#logfile.write(out)
						#logfile.write(err)
						#logfile.close()
						if err:
							if type(err) is bytes:
								err = err.decode('utf-8')
							errors += '{0} - {1}'.format(self.name_list[i], err)
					except:
						error = 'Error with subprocess call'
		except Exception as e:
			if type(e) is bytes:
				e = err.decode('utf-8')
			errors += e
		
		self.finished.emit(errors)
		

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
		
		engine = self.tfsettings.combined.engine
		self.parent_folder_name = 'TUFLOWFV' if engine == 'flexible mesh' else 'TUFLOW'
		
		# Get empty dir
		if self.tfsettings.combined.base_dir:
			subfolders = [self.parent_folder_name.lower(), 'model', 'gis', 'empty']
			emptydir = self.tfsettings.combined.base_dir
			for i, subfolder in enumerate(subfolders):
				for p in os.walk(emptydir):
					for d in p[1]:
						if d.lower() == subfolder:
							if i == 0:
								self.parent_folder_name = d
							emptydir = os.path.join(emptydir, d)
							break
					break
			self.emptydir.setText(emptydir)
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
			if not files:
				search_string = '{0}{1}*.SHP'.format(self.emptydir.text(), os.path.sep)
				files = glob.glob(search_string)
			empty_list = []
			for file in files:
				if len(file.split('_empty')) < 2:
					continue
				empty_type = os.path.basename(file.split('_empty')[0])
				if empty_type not in empty_list:
					empty_list.append(empty_type)
			empty_list = sorted(empty_list)
			self.comboBox_tfType.addItems(empty_list)
									
		self.browsedir.clicked.connect(lambda: self.browse_empty_dir(unicode(self.emptydir.displayText()).strip()))
		self.emptydir.editingFinished.connect(self.dirChanged)
		self.pbOk.clicked.connect(self.run)
		self.pbCancel.clicked.connect(self.reject)


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
			if not files:
				search_string = '{0}{1}*.SHP'.format(self.emptydir.text(), os.path.sep)
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
		message = tuflowqgis_insert_tf_attributes(self.iface, inputLayer, basedir, runID, template, lenFields, self)
		if message is not None:
			if message != 1:
				QMessageBox.critical(self.iface.mainWindow(), "Importing TUFLOW Empty File(s)", message)
		else:
			self.accept()


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
#    tuflowqgis Output Zone selection
# ----------------------------------------------------------
from ui_tuflowqgis_outputZoneSelection import *


class tuflowqgis_outputZoneSelection_dialog(QDialog, Ui_outputZoneSelection):
	def __init__(self, iface, tcf, outputZones):
		QDialog.__init__(self)
		self.iface = iface
		self.tcf = tcf
		self.outputZones = outputZones
		self.setupUi(self)
		
		for outputZone in self.outputZones:
			self.listWidget.addItem(outputZone['name'])
		
		self.ok_button.clicked.connect(self.run)
		self.cancel_button.clicked.connect(self.cancel)
		self.selectAll_button.clicked.connect(self.selectAll)
	
	def cancel(self):
		self.reject()
	
	def selectAll(self):
		for i in range(self.listWidget.count()):
			item = self.listWidget.item(i)
			item.setSelected(True)
	
	def run(self):
		self.outputZones = []
		for i in range(self.listWidget.count()):
			item = self.listWidget.item(i)
			if item.isSelected():
				self.outputZones.append(item.text())
		self.accept()  # destroy dialog window


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
			
		# xmdf dat time units
		if self.tuOptions.timeUnits == 's':
			self.rbTimeUnitsSeconds.setChecked(True)
		else:
			self.rbTimeUnitsHours.setChecked(True)
		
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

		# vertical profile interpolation
		self.cbInterpolateVertProf.setChecked(self.tuOptions.verticalProfileInterpolated)

		# layer selection labelling
		self.sbLabelFieldIndex.setValue(self.tuOptions.iLabelField + 1)
		
		# ARR mean event selection
		if self.tuOptions.meanEventSelection == 'next higher':
			self.rbARRNextHigher.setChecked(True)
		else:
			self.rbARRClosest.setChecked(True)

		# default layout
		if self.tuOptions.defaultLayout == "plot":
			self.rbDefaultLayoutPlotView.setChecked(True)
		else:
			self.rbDeafultLayoutNarrowView.setChecked(True)

		# debug - check files
		if self.tuOptions.writeMeshIntersects:
			self.cbMeshIntCheck.setChecked(True)
		else:
			self.cbMeshIntCheck.setChecked(False)
		self.cbParticleDebug.setChecked(self.tuOptions.particlesWriteDebugInfo)

		
		# Signals
		self.leDateFormat.textChanged.connect(self.updatePreview)
		self.rbDefaultLayoutPlotView.clicked.connect(lambda: self.saveDefaultLayout("plot"))
		self.rbDeafultLayoutNarrowView.clicked.connect(lambda: self.saveDefaultLayout("narrow"))
		self.buttonBox.rejected.connect(self.cancel)
		self.buttonBox.accepted.connect(self.run)
		
	def saveDefaultLayout(self, layoutType):
		QSettings().setValue("TUFLOW/tuview_defaultlayout", layoutType)

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
			
		# xmdf dat time units
		if self.rbTimeUnitsSeconds.isChecked():
			self.tuOptions.timeUnits = 's'
		else:
			self.tuOptions.timeUnits = 'h'
		
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

		# vertical profile interpolation
		self.tuOptions.verticalProfileInterpolated = self.cbInterpolateVertProf.isChecked()

		# layer selection labelling
		self.tuOptions.iLabelField = self.sbLabelFieldIndex.value() - 1
		
		# ARR mean event selection
		if self.rbARRNextHigher.isChecked():
			self.tuOptions.meanEventSelection = 'next higher'
		else:
			self.tuOptions.meanEventSelection = 'closest'

		# default layout
		if self.rbDefaultLayoutPlotView.isChecked():
			self.tuOptions.defaultLayout = "plot"
		else:
			self.tuOptions.defaultLayout = "narrow"

		# debug - check files
		if self.cbMeshIntCheck.isChecked():
			self.tuOptions.writeMeshIntersects = True
		else:
			self.tuOptions.writeMeshIntersects = False
		self.tuOptions.particlesWriteDebugInfo = self.cbParticleDebug.isChecked()
			

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
			if layer.type() == QgsMapLayer.VectorLayer:
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
		folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
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
		self.cbGISLayer.currentIndexChanged.connect(self.populateResultTypes)
		# self.mcbResultMesh.checkedItemsChanged.connect(self.populateResultTypes)
		# self.mcbResultMesh.checkedItemsChanged.connect(self.populateTimeSteps)
		self.lwResultMesh.itemSelectionChanged.connect(self.populateResultTypes)
		self.lwResultMesh.itemSelectionChanged.connect(self.populateTimeSteps)
		#self.mcbResultMesh.currentTextChanged.connect(self.populateResultTypes)
		#self.mcbResultMesh.currentTextChanged.connect(self.populateTimeSteps)
		# self.mcbResultTypes.checkedItemsChanged.connect(self.populateTimeSteps)
		self.btnBrowse.clicked.connect(lambda: browse(self, 'existing folder', 'TUFLOW/batch_export', 'Ouput Folder',
		                                              "", self.outputFolder))
		self.buttonBox.accepted.connect(self.check)
		self.buttonBox.rejected.connect(self.reject)
		
	def populateGISLayers(self):
		for name, layer in QgsProject.instance().mapLayers().items():
			if layer.type() == QgsMapLayer.VectorLayer:
				if layer.geometryType() == QgsWkbTypes.PointGeometry or layer.geometryType() == QgsWkbTypes.LineGeometry:
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
				if '_ts' not in type and '_lp' not in type and '_particles':  # check if there is at least one 2D result type
					# self.mcbResultMesh.addItem(resultName)
					self.lwResultMesh.addItem(resultName)
					break
	
	def populateResultTypes(self):
		self.mcbResultTypes.clear()
		layer = tuflowqgis_find_layer(self.cbGISLayer.currentText())
		resultTypes = []
		# meshes = [self.mcbResultMesh.currentText()]
		# meshes = self.mcbResultMesh.checkedItems()
		meshes = [x.text() for x in self.lwResultMesh.selectedItems()]
		if layer is not None:
			for mesh in meshes:
			#for mesh in self.mcbResultMesh.checkedItems():
				r = self.tuView.tuResults.results[mesh]
				for type, t in r.items():
					if (layer.geometryType() == QgsWkbTypes.LineGeometry or ('isTemporal' in t
							and t['isTemporal'] and layer.geometryType() == QgsWkbTypes.PointGeometry)) \
							and ('isMax' in t and not t['isMax'] and 'isMin' in t and not t['isMin']):
						if type not in resultTypes:
							resultTypes.append(type)

		self.mcbResultTypes.addItems(resultTypes)
		
	def populateTimeSteps(self, *args):

		self.cbTimesteps.clear()
		self.cbTimesteps.setEnabled(False)
		timesteps = []
		timestepsFormatted = []
		maximum = False
		minimum = False
		layer = tuflowqgis_find_layer(self.cbGISLayer.currentText())
		if layer is not None:
			if layer.geometryType() == QgsWkbTypes.PointGeometry:
				self.cbTimesteps.setEnabled(False)
			elif layer.geometryType() == QgsWkbTypes.LineGeometry:
				self.cbTimesteps.setEnabled(True)
				# meshes = [self.mcbResultMesh.currentText()]
				# meshes = self.mcbResultMesh.checkedItems()
				meshes = [x.text() for x in self.lwResultMesh.selectedItems()]
				rts = [x.lower() for x in self.mcbResultTypes.checkedItems()]
				for mesh in meshes:
				# for mesh in self.mcbResultMesh.checkedItems():
					r = self.tuView.tuResults.results[mesh]
					for rtype, t in r.items():
						if type(t) is dict:  # map outputs results stored in dict, time series results stored as tuple
							if (layer.geometryType() == QgsWkbTypes.LineGeometry or ('isTemporal' in t
									and t['isTemporal'] and layer.geometryType() == QgsWkbTypes.PointGeometry)) \
									and ('isMax' in t and not t['isMax'] and 'isMin' in t and not t['isMin']):
								if 'times' in t:
									for time, items in t['times'].items():
										if time == '99999' or time == '-99999':
											continue
										elif items[0] not in timesteps:
											timesteps.append(items[0])
							elif 'isMax' in t and t['isMax']:
								maximum = True
							elif 'isMin' in t and t['isMin']:
								minimum = True

				timesteps = sorted(timesteps)
				if timesteps:
					if timesteps[-1] < 100:
						timestepsFormatted = [convertTimeToFormattedTime(x) for x in timesteps]
					else:
						timestepsFormatted = [convertTimeToFormattedTime(x, hour_padding=3) for x in timesteps]
					if maximum:
						timestepsFormatted.insert(0, 'Maximum')
					if minimum:
						timestepsFormatted.insert(0, 'Minimum')
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
		elif not self.lwResultMesh.selectedItems():
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
		# resultMesh = self.mcbResultMesh.checkedItems()  # list -> str
		resultMesh = [x.text() for x in self.lwResultMesh.selectedItems()]
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
		folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
		self.btnBrowse.setIcon(folderIcon)
		self.convertDateError = False
		self.convertDateErrorItems = ()
		self.zeroDate = None
		self.convertZeroDate()
		self.ok = False
		self.message = ''
		self._dateFormat = '{0:%d}/{0:%m}/{0:%Y} {0:%H}:{0:%M}:{0:%S}'
		self.dteZeroTime.setDisplayFormat('d/M/yyyy h:mm AP')
		
		self.btnBrowse.clicked.connect(lambda: browse(self, 'existing file', 'TUFLOW/import_user_data',
		                                              'Import Delimited File', lineEdit=self.inFile))
		self.inFile.textChanged.connect(self.populateDataColumns)
		self.inFile.textChanged.connect(self.updatePreview)
		self.rbCSV.clicked.connect(self.populateDataColumns)
		self.rbSpace.clicked.connect(self.populateDataColumns)
		self.rbTab.clicked.connect(self.populateDataColumns)
		self.rbOther.clicked.connect(self.populateDataColumns)
		self.delimiter.textChanged.connect(self.populateDataColumns)
		self.sbLines2Discard.valueChanged.connect(self.updateLabelRow)
		self.sbLines2Discard.valueChanged.connect(self.populateDataColumns)
		self.sbLines2Discard.valueChanged.connect(self.updatePreview)
		self.cbHeadersAsLabels.clicked.connect(self.populateDataColumns)
		self.sbLabelRow.valueChanged.connect(self.populateDataColumns)
		self.cbXColumn.currentIndexChanged.connect(self.updatePreview)
		self.mcbYColumn.currentTextChanged.connect(self.updatePreview)
		self.nullValue.textChanged.connect(self.updatePreview)
		self.gbUseDates.toggled.connect(self.updatePreview)
		self.cbManualZeroTime.toggled.connect(self.convertZeroDate)
		self.cbManualZeroTime.toggled.connect(self.updatePreview)
		self.dteZeroTime.dateTimeChanged.connect(self.convertZeroDate)
		self.dteZeroTime.dateTimeChanged.connect(self.updatePreview)
		self.pbOk.clicked.connect(self.check)
		self.pbCancel.clicked.connect(self.reject)
		self.cbUSDateFormat.toggled.connect(self.dateFormatChanged)

	def dateFormatChanged(self,):
		if self.cbUSDateFormat.isChecked():
			self.dteZeroTime.setDisplayFormat('M/d/yyyy h:mm AP')
		else:
			self.dteZeroTime.setDisplayFormat('d/M/yyyy h:mm AP')

		self.updatePreview()

	def addDateConversionError(self, txt='', clear=False):
		"""
		Adds an error when converting date
		
		:return: None
		"""
		
		if clear:
			if self.convertDateErrorItems:
				layout = self.convertDateErrorItems[0]
				label = self.convertDateErrorItems[1]
				layout.removeWidget(label)
				label.deleteLater()
				label.setParent(None)
				gbLayout = self.gbUseDates.layout()
				for i in range(gbLayout.count()):
					if gbLayout.itemAt(i) == layout:
						gbLayout.takeAt(i)
						layout.deleteLater()
						layout.setParent(None)
				self.convertDateErrorItems = ()
				self.convertDateError = False
			return
		
		label = QLabel()
		label.setVisible(True)
		label.setTextFormat(Qt.RichText)
		label.setText(txt)
		palette = label.palette()
		palette.setColor(QPalette.Foreground, Qt.red)
		font = label.font()
		font.setItalic(True)
		label.setPalette(palette)
		label.setFont(font)
		
		layout = QHBoxLayout()
		layout.addWidget(label)
		self.gbUseDates.layout().addLayout(layout)
		self.convertDateError = True
		self.convertDateErrorItems = (layout, label)

	def getDelim(self):
			if self.rbCSV.isChecked():
				return ','
			elif self.rbSpace.isChecked():
				return ' '
			elif self.rbTab.isChecked():
				return '\t'
			elif self.rbOther.isChecked():
				return self.delimiter.text()

	def convertZeroDate(self):

		if self.cbManualZeroTime.isChecked():
			year = self.dteZeroTime.date().year()
			month = self.dteZeroTime.date().month()
			day = self.dteZeroTime.date().day()
			hour = self.dteZeroTime.time().hour()
			minute = self.dteZeroTime.time().minute()
			second = self.dteZeroTime.time().second()
			self.zeroDate = datetime(year, month, day, hour, minute, second)
		else:
			self.zeroDate = None
		
		self.updatePreview()

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
		self.addDateConversionError(clear=True)
		if not self.cbManualZeroTime.isChecked():
			self.zeroDate = None
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
								#if not self.dateCanBeConverted:
								if self.gbUseDates.isChecked():
									self.previewTable.setColumnCount(len(yHeaders) + 2)
								else:
									self.previewTable.setColumnCount(len(yHeaders) + 1)
								if self.cbHeadersAsLabels.isChecked():
									if self.gbUseDates.isChecked():
										tableColumnNames = [xHeader, 'Time (hr)'] + yHeaders
									else:
										tableColumnNames = [xHeader] + yHeaders
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
								skip = False
								if '{0}'.format(values[xHeaderInd]).strip() == self.nullValue.text() or \
										'{0}'.format(values[xHeaderInd]).strip() == '':
									noIgnored += 1
									skip = True
								for yHeaderInd in yHeaderInds:
									if '{0}'.format(values[yHeaderInd]).strip() == self.nullValue.text() or \
										'{0}'.format(values[yHeaderInd]).strip() == '':
										noIgnored += 1
										skip = True
										break
								if skip:
									continue
								item = QTableWidgetItem(0)
								item.setText('{0}'.format(values[xHeaderInd]))
								self.previewTable.setItem((i - header_line - noIgnored), 0, item)
								k = 0
								if self.gbUseDates.isChecked():
									try:
										if self.cbUSDateFormat.isChecked():
											dateTime = dateutil.parser.parse(values[xHeaderInd])
										else:
											dateTime = dateutil.parser.parse(values[xHeaderInd], dayfirst=True)
										if self.zeroDate is None:
											self.zeroDate = dateTime
										item = QTableWidgetItem(0)
										hours = (dateTime - self.zeroDate).total_seconds() / 3600.
										item.setText('{0:.2f}'.format(hours))
										self.previewTable.setItem((i - header_line - noIgnored), 1, item)
										k = 1
									except ValueError:
										if not self.convertDateError:
											self.addDateConversionError('Line [{0}]: Error converting date "{1}"'.format(i - noIgnored + 1, values[xHeaderInd]))
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
					skip = False
					if '{0}'.format(values[xHeaderInd]).strip() == self.nullValue.text() or \
							'{0}'.format(values[xHeaderInd]).strip() == '':
						skip = True
					for yHeaderInd in yHeaderInds:
						if '{0}'.format(values[yHeaderInd]).strip() == self.nullValue.text() or \
								'{0}'.format(values[yHeaderInd]).strip() == '':
							skip = True
							break
					if skip:
						continue

					for j, yHeaderInd in enumerate(yHeaderInds):
						if self.gbUseDates.isChecked():
							try:
								if self.cbUSDateFormat.isChecked():
									dateTime = dateutil.parser.parse(values[xHeaderInd])
								else:
									dateTime = dateutil.parser.parse(values[xHeaderInd], dayfirst=True)
								if self.zeroDate is None:
									self.zeroDate = dateTime
								timeHr = (dateTime - self.zeroDate).total_seconds() / 3600.
							except ValueError:
								self.message = 'ERROR line {0}: Could not convert value to date format "{1}"'.format(i+1, values[xHeaderInd])
								QMessageBox.critical(self, 'Import Error', self.message)
								return
						else:
							timeHr = values[xHeaderInd]
						try:
							x[j].append(float(timeHr))
							if self.gbUseDates.isChecked():
								self.dates[j].append(dateTime)
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
		self.setTableProperties()
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
			item2 = QTableWidgetItem(0)
			if plotType == 'long plot':
				item2.setText('Cross Section / Long Plot')
			else:
				item2.setText('Time Series Plot')
			self.UserPlotDataTable.setItem(self.UserPlotDataTable.rowCount() - 1, 0, item)
			self.UserPlotDataTable.setItem(self.UserPlotDataTable.rowCount() - 1, 1, item2)
			self.loadedData[name] = [item2, item]
			
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
					#combobox = QComboBox()
					#combobox.setEditable(True)
					#combobox.setMaximumHeight(30)
					#combobox.setMaximumWidth(175)
					#combobox.addItem('Time Series Plot')
					#combobox.addItem('Cross Section / Long Plot')
					item2 = QTableWidgetItem(0)
					item2.setText(self.UserPlotDataTable.itemDelegateForColumn(1).default)
					self.UserPlotDataTable.setItem(self.UserPlotDataTable.rowCount() - 1, 0, item)
					self.UserPlotDataTable.setItem(self.UserPlotDataTable.rowCount() - 1, 1, item2)
					#self.UserPlotDataTable.setCellWidget(self.UserPlotDataTable.rowCount() - 1, 1, combobox)
					self.loadedData[name] = [item2, item]
					
					#combobox.currentIndexChanged.connect(lambda: self.editData(combobox=combobox))
					#self.UserPlotDataTable.itemClicked.connect(lambda item: self.editData(item=item))
					#self.UserPlotDataTable.itemChanged.connect(lambda item: self.editData(item=item))
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
			#self.UserPlotDataTable.itemClicked.disconnect()
			#self.UserPlotDataTable.itemChanged.disconnect()
		self.UserPlotDataTable.setRowCount(0)
		self.loadData()
		
	def setTableProperties(self):
		
		plotTypes = ['Time Series Plot', 'Cross Section / Long Plot']
		self.UserPlotDataTable.itemDelegateForColumn(1).setItems(items=plotTypes, default='Time Series Plot')
		
		
# ----------------------------------------------------------
#    Filter and Sort TUFLOW Layers in Map Window
# ----------------------------------------------------------
from ui_filter_sort_TUFLOW_layers import *


class FilterSortLayersDialog(QDialog, Ui_FilterAndSortLayers):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.setupUi(self)
		self.iface = iface
		self.type2rbs = {}  # e.g. { '2d_bc': ( rbOn, rbCurrent, rbOff ) }
		self.type2buttonGroup = {}
		self.bgCheck.setId(self.rbCheckOn, 0)
		self.bgCheck.setId(self.rbCheckCurrent, 1)
		self.bgCheck.setId(self.rbCheckOff, 2)
		self.bgDem.setId(self.rbDemOn, 0)
		self.bgDem.setId(self.rbDemCurrent, 1)
		self.bgDem.setId(self.rbDemOff, 2)
		self.bgMesh.setId(self.rbMeshOn, 0)
		self.bgMesh.setId(self.rbMeshCurrent, 1)
		self.bgMesh.setId(self.rbMeshOff, 2)
		self.initialiseTable()
		
		self.pbFilter.clicked.connect(self.filter)
		self.pbSort.clicked.connect(self.sort)
		self.pbFinished.clicked.connect(self.accept)
		
	def initialiseTable(self):
		"""Set up TableWidget with open tuflow layer types"""
		
		# remove row numbers
		self.tableWidget.verticalHeader().setVisible(False)
		
		# add all on / off button
		self.tableWidget.setRowCount(1)
		
		item = QTableWidgetItem(0)
		item.setText('All Layers')
		self.tableWidget.setItem(0, 0, item)
		
		# radio check boxes
		widgetOn = QWidget(self.tableWidget)
		rbOn = QRadioButton(widgetOn)
		hboxOn = QHBoxLayout()
		hboxOn.setContentsMargins(0, 0, 0, 0)
		hboxOn.addStretch()
		hboxOn.addWidget(rbOn)
		hboxOn.addStretch()
		widgetOn.setLayout(hboxOn)
		
		widgetCurrent = QWidget(self.tableWidget)
		rbCurrent = QRadioButton(widgetCurrent)
		hboxCurrent = QHBoxLayout()
		hboxCurrent.setContentsMargins(0, 0, 0, 0)
		hboxCurrent.addStretch()
		hboxCurrent.addWidget(rbCurrent)
		hboxCurrent.addStretch()
		widgetCurrent.setLayout(hboxCurrent)
		
		widgetOff = QWidget(self.tableWidget)
		rbOff = QRadioButton(widgetOff)
		hboxOff = QHBoxLayout()
		hboxOff.setContentsMargins(0, 0, 0, 0)
		hboxOff.addStretch()
		hboxOff.addWidget(rbOff)
		hboxOff.addStretch()
		widgetOff.setLayout(hboxOff)
		
		rbCurrent.setChecked(True)
		rbGroup = QButtonGroup()
		rbGroup.addButton(rbOn)
		rbGroup.setId(rbOn, 0)
		rbGroup.addButton(rbCurrent)
		rbGroup.setId(rbCurrent, 1)
		rbGroup.addButton(rbOff)
		rbGroup.setId(rbOff, 2)
		rbGroup.setExclusive(True)
		
		self.tableWidget.setCellWidget(0, 1, widgetOn)
		self.tableWidget.setCellWidget(0, 2, widgetCurrent)
		self.tableWidget.setCellWidget(0, 3, widgetOff)
		self.type2rbs['all_layers'] = (rbOn, rbCurrent, rbOff)
		self.type2buttonGroup['all_layers'] = rbGroup

		# collect open layer tuflow types
		inputLayers = getOpenTUFLOWLayers('input_types')
		self.tableWidget.setRowCount(len(inputLayers) + 1)
		for i, inputLayer in enumerate(inputLayers):
			# tuflow type label
			item = QTableWidgetItem(0)
			item.setText(inputLayer)
			self.tableWidget.setItem(i+1, 0, item)
			
			# radio check boxes
			widgetOn = QWidget(self.tableWidget)
			rbOn = QRadioButton(widgetOn)
			hboxOn = QHBoxLayout()
			hboxOn.setContentsMargins(0, 0, 0, 0)
			hboxOn.addStretch()
			hboxOn.addWidget(rbOn)
			hboxOn.addStretch()
			widgetOn.setLayout(hboxOn)
			
			widgetCurrent = QWidget(self.tableWidget)
			rbCurrent = QRadioButton(widgetCurrent)
			hboxCurrent = QHBoxLayout()
			hboxCurrent.setContentsMargins(0, 0, 0, 0)
			hboxCurrent.addStretch()
			hboxCurrent.addWidget(rbCurrent)
			hboxCurrent.addStretch()
			widgetCurrent.setLayout(hboxCurrent)
			
			widgetOff = QWidget(self.tableWidget)
			rbOff = QRadioButton(widgetOff)
			hboxOff = QHBoxLayout()
			hboxOff.setContentsMargins(0, 0, 0, 0)
			hboxOff.addStretch()
			hboxOff.addWidget(rbOff)
			hboxOff.addStretch()
			widgetOff.setLayout(hboxOff)
			
			rbCurrent.setChecked(True)
			rbGroup = QButtonGroup()
			rbGroup.addButton(rbOn)
			rbGroup.setId(rbOn, 0)
			rbGroup.addButton(rbCurrent)
			rbGroup.setId(rbCurrent, 1)
			rbGroup.addButton(rbOff)
			rbGroup.setId(rbOff, 2)
			rbGroup.setExclusive(True)
			
			self.tableWidget.setCellWidget(i+1, 1, widgetOn)
			self.tableWidget.setCellWidget(i+1, 2, widgetCurrent)
			self.tableWidget.setCellWidget(i+1, 3, widgetOff)
			self.type2rbs[inputLayer] = (rbOn, rbCurrent, rbOff)
			self.type2buttonGroup[inputLayer] = rbGroup
		
		# resize columns
		self.tableWidget.resizeColumnsToContents()
		
	def filter(self):
		filterKey = {0: 'on', 1: 'current', 2: 'off'}
		filterProp = {}  # properties / settings
		
		# input layers
		tuflowLayers = getOpenTUFLOWLayers('input_all')
		for tuflowLayer in tuflowLayers:
			if self.type2buttonGroup['all_layers'].checkedId() == 0:
				filterProp[tuflowLayer] = 'on'
			elif self.type2buttonGroup['all_layers'].checkedId() == 2:
				filterProp[tuflowLayer] = 'off'
			else:
				comp = tuflowLayer.split('_')
				ltype = '_'.join(comp[:2]).lower()
				
				# special case for 2d_sa as this could be 2d_sa_tr or 2d_sa_rf
				specialCases = ['2d_sa_rf', '2d_sa_tr']
				if len(comp) >= 3:
					for sc in specialCases:
						tempName = ltype + '_' + comp[2]
						if sc.lower() == tempName.lower():
							ltype = tempName
				
				filterProp[tuflowLayer] = filterKey[self.type2buttonGroup[ltype].checkedId()]
		
		# check layers
		if self.bgCheck.checkedId() != 1:
			checkLayers = getOpenTUFLOWLayers('check_all')
			for checkLayer in checkLayers:
				filterProp[checkLayer] = filterKey[self.bgCheck.checkedId()]
				
		# dem layers
		if self.bgDem.checkedId() != 1:
			demLayers = findAllRasterLyrs()
			for demLayer in demLayers:
				filterProp[demLayer] = filterKey[self.bgDem.checkedId()]
				
		# mesh layers
		if self.bgMesh.checkedId() != 1:
			meshLayers = findAllMeshLyrs()
			for meshLayer in meshLayers:
				filterProp[meshLayer] = filterKey[self.bgMesh.checkedId()]
				
		turnLayersOnOff(filterProp)
		
	def sort(self):
		sortLocally = True
		if self.rbSortGlobally.isChecked():
			sortLocally = False
			
		sortLayerPanel(sort_locally=sortLocally)
		
		
# ----------------------------------------------------------
#    TUFLOW Utilities
# ----------------------------------------------------------
from TUFLOW_utilities import *


class TuflowUtilitiesDialog(QDialog, Ui_utilitiesDialog):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.setupUi(self)
		self.iface = iface
		self.applyIcons()
		self.applyPrevExeLocations()
		self.commonUtilityChanged(0)
		self.populateGrids()
		self.buttonGroup = QButtonGroup()
		self.buttonGroup.addButton(self.rbCommonFunctions)
		self.buttonGroup.addButton(self.rbAdvanced)
		self.rbCommonFunctions.setVisible(False)
		self.rbAdvanced.setVisible(False)
		self.rbCommonFunctions.setChecked(True)
		self.loadProjectSettings()
		
		self.connectBrowseButtons()
		self.cboCommonUtility.currentIndexChanged.connect(self.commonUtilityChanged)
		self.btnAddGrid.clicked.connect(self.addGrid)
		self.btnRemoveGrid.clicked.connect(self.removeGrid)
		self.btnAddMesh.clicked.connect(self.addMesh)
		self.btnRemoveMesh.clicked.connect(self.removeMesh)
		self.pbDownloadExecutables.clicked.connect(self.downloadExecutables)
		self.pbOK.clicked.connect(self.check)
		self.pbCancel.clicked.connect(self.reject)
		self.tabWidget.currentChanged.connect(self.currentTabChanged)
		self.btnFindFile.clicked.connect(self.findFile)

	def findFile(self):
		files = QFileDialog.getOpenFileNames(self, "Select File(s)", self.leAdvWorkingDir.text(), "ALL (*)")[0]
		text = [self.teCommands.toPlainText()]
		# for f in files:
		# 	name = os.path.basename(f)
		# 	if not text[0]:
		# 		t = "{0}".format(name)
		# 	elif text[0][-1] == " ":
		# 		t = "{0}".format(name)
		# 	else:
		# 		t = " {0}".format(name)
		# 	text.append(t)
		relPaths = [os.path.relpath(x, self.leAdvWorkingDir.text()) for x in files]
		if text[0] and text[0][-1] == " ":
			text[0] = text[0][:-1]
		text.extend(relPaths)
		text = ' '.join(text)
		self.teCommands.setPlainText(text)

	def currentTabChanged(self):
		self.pbOK.setEnabled(True)
		if self.tabWidget.currentIndex() == 0:
			self.rbCommonFunctions.setChecked(True)
		elif self.tabWidget.currentIndex() == 1:
			self.rbAdvanced.setChecked(True)
		else:
			self.pbOK.setEnabled(False)
		
	def downloadExecutables(self):
		# check if windows
		if sys.platform == 'win32':
			self.thread = QThread()
			self.progressDialog = UtilityDownloadProgressBar(self)
			self.downloadUtilities = DownloadTuflowUtilities()
			self.downloadUtilities.moveToThread(self.thread)
			self.downloadUtilities.updated.connect(self.progressDialog.updateProgress)
			self.downloadUtilities.finished.connect(self.progressDialog.progressFinished)
			self.downloadUtilities.finished.connect(self.downloadFinished)
			self.thread.started.connect(self.downloadUtilities.download)
			self.progressDialog.show()
			self.thread.start()
		else:
			QMessageBox.critical(self, "TUFLOW Utilities", "Download feature only available on Windows")
	
	def downloadFinished(self, e):
		utilities = {'asc_to_asc': self.leAsc2Asc, 'tuflow_to_gis': self.leTUFLOW2GIS,
		             'res_to_res': self.leRes2Res, '12da_to_from_gis': self.le12da2GIS,
		             'convert_to_ts1': self.leConvert2TS1, 'tin_to_tin': self.leTin2Tin,
		             'xsGenerator': self.leXSGenerator}
		
		for key, value in e.items():
			utilities[key].setText(value)
		self.progressDialog.accept()
	
	def populateGrids(self):
		rasters = findAllRasterLyrs()
		grids = []  # only select rasters that are .asc or .flt
		for raster in rasters:
			layer = tuflowqgis_find_layer(raster)
			dataSource = layer.dataProvider().dataSourceUri()
			ext = os.path.splitext(dataSource)[1]
			if ext.upper() == '.ASC' or ext.upper() == '.FLT' or ext.upper() == '.TXT':
				grids.append(raster)
				
		self.cboDiffGrid1.addItems(grids)
		self.cboDiffGrid2.addItems(grids)
		self.cboGrid.addItems(grids)
	
	def addGrid(self):
		if self.cboGrid.currentText():
			if self.cboGrid.currentText().replace('/', os.sep).count(os.sep) > 0:
				a = self.cboGrid.currentText().split(';;')
				for i, b in enumerate(a):
					b = b.strip('"').strip("'")
					a[i] = b
				self.lwGrids.addItems(a)
			else:
				layer = tuflowqgis_find_layer(self.cboGrid.currentText().strip('"').strip("'"))
				if layer is not None:
					dataSource = layer.dataProvider().dataSourceUri()
					self.lwGrids.addItem(dataSource)
		self.cboGrid.setCurrentText('')
	
	def removeGrid(self):
		selectedItems = self.lwGrids.selectedItems()
		indexes = []
		for i in range(self.lwGrids.count()):
			item = self.lwGrids.item(i)
			if item in selectedItems:
				indexes.append(i)
		for i in reversed(indexes):
			self.lwGrids.takeItem(i)
			
	def addMesh(self):
		if self.leMeshMulti.text():
			a = self.leMeshMulti.text().split(';;')
			for i, b in enumerate(a):
				b = b.strip('"').strip("'")
				a[i] = b
			self.lwMeshes.addItems(a)
		self.leMeshMulti.setText('')
			
	def removeMesh(self):
		selectedItems = self.lwMeshes.selectedItems()
		indexes = []
		for i in range(self.lwMeshes.count()):
			item = self.lwMeshes.item(i)
			if item in selectedItems:
				indexes.append(i)
		for i in reversed(indexes):
			self.lwMeshes.takeItem(i)
	
	def commonUtilityChanged(self, i):
		if i == 0:  # asc_to_asc
			self.asc2Asc.setVisible(True)
			self.tuflow2Gis.setVisible(False)
			self.res2Res.setVisible(False)
		elif i == 1:
			self.asc2Asc.setVisible(False)
			self.tuflow2Gis.setVisible(True)
			self.res2Res.setVisible(False)
		elif i == 2:
			self.asc2Asc.setVisible(False)
			self.tuflow2Gis.setVisible(False)
			self.res2Res.setVisible(True)
		
	def browse(self, browseType, key, dialogName, fileType, lineEdit):
		"""
		Browse folder directory

		:param type: str browse type 'folder' or 'file'
		:param key: str settings key
		:param dialogName: str dialog box label
		:param fileType: str file extension e.g. "AVI files (*.avi)"
		:param lineEdit: QLineEdit to be updated by browsing
		:return: void
		"""
		
		settings = QSettings()
		lastFolder = settings.value(key)
		if type(lineEdit) is QLineEdit:
			startDir = lineEdit.text()
		elif type(lineEdit) is QComboBox:
			startDir = lineEdit.currentText()
		else:
			startDir = None
		if lastFolder:  # if outFolder no longer exists, work backwards in directory until find one that does
			while lastFolder:
				if os.path.exists(lastFolder):
					startDir = lastFolder
					break
				else:
					lastFolder = os.path.dirname(lastFolder)
		if browseType == 'existing folder':
			f = QFileDialog.getExistingDirectory(self, dialogName, startDir)
		elif browseType == 'existing file':
			f = QFileDialog.getOpenFileName(self, dialogName, startDir, fileType)[0]
		elif browseType == 'existing files':
			f = QFileDialog.getOpenFileNames(self, dialogName, startDir, fileType)[0]
		else:
			return
		if f:
			if type(f) is list:
				fs = ''
				for i, a in enumerate(f):
					if i == 0:
						value = a
						fs += a
					else:
						fs += ';;' + a
				f = fs
			else:
				value = f
			if type(lineEdit) is QLineEdit:
				lineEdit.setText(f)
			elif type(lineEdit) is QComboBox:
				lineEdit.setCurrentText(f)
			settings.setValue(key, value)
	
	def applyIcons(self):
		folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
		addIcon = QgsApplication.getThemeIcon('mActionAdd.svg')
		removeIcon = QgsApplication.getThemeIcon('symbologyRemove.svg')
		
		browseButtons = [self.btnBrowseComOutputDir, self.btnBrowseDiffGrid1, self.btnBrowseDiffGrid2,
		                 self.btnBrowseGrid, self.btnBrowseAdvWorkingDir, self.btnBrowseAsc2Asc,
		                 self.btnBrowseAsc2Asc, self.btnBrowseTUFLOW2GIS, self.btnBrowseRes2Res, self.btnBrowse12da2GIS,
		                 self.btnBrowseConvert2TS1, self.btnBrowseTin2Tin, self.btnBrowseXSGenerator,
		                 self.btnBrowseMeshToGis, self.btnBrowseMeshToRes, self.btnBrowseMeshMulti]
		addButtons = [self.btnAddGrid, self.btnAddMesh]
		removeButtons = [self.btnRemoveGrid, self.btnRemoveMesh]
		
		for button in browseButtons:
			button.setIcon(folderIcon)
		for button in addButtons:
			button.setIcon(addIcon)
		for button in removeButtons:
			button.setIcon(removeIcon)
		
	def check(self):
		if self.rbCommonFunctions.isChecked():
			if self.leOutputName.text():
				if not self.leComOutputDir.text():
					QMessageBox.critical(self, "TUFLOW Utilities", "Must specify output location if specifying output name")
					return
				elif not os.path.exists(self.leComOutputDir.text().strip('"').strip("'")):
					QMessageBox.critical(self, "TUFLOW Utilities", "Output location does not exist")
					return
			if self.cboCommonUtility.currentIndex() == 0:  # asc_to_asc
				if not self.leAsc2Asc.text():
					QMessageBox.critical(self, "TUFLOW Utilities", "Must specify asc_to_asc.exe location")
					return
				else:
					if not os.path.exists(self.leAsc2Asc.text().strip('"').strip("'")):
						QMessageBox.critical(self, "TUFLOW Utilities", "asc_to_asc.exe location does not exist")
						return
				if self.rbAscDiff.isChecked():
					if not self.cboDiffGrid1.currentText() or not self.cboDiffGrid2.currentText():
						QMessageBox.critical(self, "TUFLOW Utilities", "Must specify grid 1 and grid 2")
						return
					if self.cboDiffGrid1.currentText().replace('/', os.sep).count(os.sep) == 0:
						layer = tuflowqgis_find_layer(self.cboDiffGrid1.currentText().strip('"').strip("'"))
						if layer is None:
							QMessageBox.critical(self, "TUFLOW Utilities", "Could not find grid 1 in workspace")
							return
					if self.cboDiffGrid2.currentText().replace('/', os.sep).count(os.sep) == 0:
						layer = tuflowqgis_find_layer(self.cboDiffGrid2.currentText().strip('"').strip("'"))
						if layer is None:
							QMessageBox.critical(self, "TUFLOW Utilities", "Could not find grid 2 in workspace")
							return
					if self.cboDiffGrid1.currentText().strip('"').strip("'") == \
							self.cboDiffGrid2.currentText().strip('"').strip("'"):
						reply = QMessageBox.warning(self, "TUFLOW Utilities",
						                            "Input grid 1 and grid 2 are the same. Do you wish to continue?",
						                            QMessageBox.Yes | QMessageBox.No)
						if reply == QMessageBox.No:
							return
				elif self.rbAscConv.isChecked():
					if not self.lwGrids.count():
						QMessageBox.critical(self, "TUFLOW Utilities", "Must specify at least one grid")
						return
				else:
					if self.lwGrids.count() < 2:
						QMessageBox.critical(self, "TUFLOW Utilities", "Must specify 2 or more grids")
						return
					grids = []
					for i in range(self.lwGrids.count()):
						item = self.lwGrids.item(i)
						grid = item.text()
						if grid in grids:
							j = grids.index(grid)
							reply = QMessageBox.warning(self, "TUFLOW Utilities",
							                            "Input grid {0} and grid {1} are the same. "
							                            "Do you wish to continue?".format(j+1, i+1),
							                            QMessageBox.Yes | QMessageBox.No)
							if reply == QMessageBox.No:
								return
						else:
							grids.append(grid)
			elif self.cboCommonUtility.currentIndex() == 1:  # tuflow_to_gis
				if not self.leTUFLOW2GIS.text():
					QMessageBox.critical(self, "TUFLOW Utilities", "Must specify tuflow_to_gis.exe location")
					return
				else:
					if not os.path.exists(self.leTUFLOW2GIS.text().strip('"').strip("'")):
						QMessageBox.critical(self, "TUFLOW Utilities", "tuflow_to_gis.exe location does not exist")
						return
				if not self.leMeshToGis.text():
					QMessageBox.critical(self, "TUFLOW Utilities", "Must specify and input mesh (XMDF or DAT)")
					return
				elif not os.path.exists(self.leMeshToGis.text().strip('"').strip("'")):
					QMessageBox.critical(self, "TUFLOW Utilities", "Input mesh layer does not exist")
					return
				elif os.path.splitext(self.leMeshToGis.text())[1].upper() == '.XMDF':
					if not self.cboToGisMeshDataset.currentText():
						QMessageBox.critical(self, "TUFLOW Utilities", "Must specify an input data type for XMDF")
						return
				if not self.cboTimestep.currentText():
					QMessageBox.critical(self, "TUFLOW Utilities", "Must specify a timestep")
					return
				if self.cboTimestep.currentText().lower() != 'max' and self.cboTimestep.currentText().lower() != 'maximum':
					try:
						float(self.cboTimestep.currentText())
					except ValueError:
						QMessageBox.critical(self, "TUFLOW Utilities", "Timestep must be a number or max")
						return
			elif self.cboCommonUtility.currentIndex() == 2:  # res_to_res
				if not self.leRes2Res.text():
					QMessageBox.critical(self, "TUFLOW Utilities", "Must specify res_to_res.exe location")
					return
				else:
					if not os.path.exists(self.leRes2Res.text().strip('"').strip("'")):
						QMessageBox.critical(self, "TUFLOW Utilities", "res_to_res.exe location does not exist")
						return
				if self.rbMeshInfo.isChecked() or self.rbMeshConvert.isChecked():
					if not self.leMeshToRes.text():
						QMessageBox.critical(self, "TUFLOW Utilities", "Must an input mesh file")
						return
					elif not os.path.exists(self.leMeshToRes.text().strip('"').strip("'")):
						QMessageBox.critical(self, "TUFLOW Utilities", "Input mesh file does not exist")
						return
					ext = os.path.splitext(self.leMeshToRes.text())[1].upper()
				else:
					if self.lwMeshes.count() == 0:
						QMessageBox.critical(self, "TUFLOW Utilities", "Must specify at least one mesh file")
						return
					meshes = []
					for i in range(self.lwMeshes.count()):
						if not os.path.exists(self.lwMeshes.item(i).text().strip('"').strip("'")):
							QMessageBox.critical(self, "TUFLOW Utilities",
							                     "Input mesh {0} location does not exist".format(i))
							return
						if self.lwMeshes.item(i).text() in meshes:
							j = meshes.index(self.lwMeshes.item(i).text())
							reply = QMessageBox.warning(self, "TUFLOW Utilities",
							                            "Input mesh {0} and mesh {1} are the same. "
							                            "Do you wish to continue?".format(j + 1, i + 1),
							                            QMessageBox.Yes | QMessageBox.No)
							if reply == QMessageBox.No:
								return
						else:
							meshes.append(self.lwMeshes.item(i).text())
						if i == 0:
							ext = os.path.splitext(self.lwMeshes.item(i).text())[1].upper()
						else:
							if ext != os.path.splitext(self.lwMeshes.item(i).text())[1].upper():
								QMessageBox.critical(self, "TUFLOW Utilities",
								                     "Input meshes must all be of the same type (XMDF or DAT)")
								return
				if ext == '.XMDF':
					if not self.rbMeshInfo.isChecked():
						if not self.cboToResMeshDataset.currentText():
							QMessageBox.critical(self, "TUFLOW Utilities", "Must specify datatype for XMDF inputs")
							return
				
		else:
			if not self.leAdvWorkingDir.text():
				QMessageBox.critical(self, "TUFLOW Utilities", "Must specify a working directory")
				return
			if not os.path.exists(self.leAdvWorkingDir.text().strip('"').strip("'")):
				QMessageBox.critical(self, "TUFLOW Utilities", "Working directory does not exist")
				return
			if not self.teCommands.toPlainText():
				QMessageBox.critical(self, "TUFLOW Utilities", "Must specify some flags")
				return
		
		self.run()
		
	def run(self):
		self.pbOK.setEnabled(False)
		self.pbCancel.setEnabled(False)
		QgsApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
		error = False
		
		# precoded functions
		if self.rbCommonFunctions.isChecked():
			workdir = self.leComOutputDir.text().strip('"').strip("'")
			
			# asc_to_asc
			if self.cboCommonUtility.currentIndex() == 0:
				# difference
				if self.rbAscDiff.isChecked():
					function = 'diff'
					grids = [self.cboDiffGrid1.currentText().strip('"').strip("'"),
					         self.cboDiffGrid2.currentText().strip('"').strip("'")]
				else:
					grids = []
					for i in range(self.lwGrids.count()):
						grids.append(self.lwGrids.item(i).text())
					# Max
					if self.rbAscMax.isChecked():
						function = 'max'
					# stat
					if self.rbAscStat.isChecked():
						function = 'stat'
					# convert
					if self.rbAscConv.isChecked():
						function = 'conv'
				error, message = ascToAsc(self.leAsc2Asc.text().strip('"').strip("'"), function, workdir, grids,
				                          out=self.leOutputName.text(), saveFile=self.cbSaveBatComm.isChecked())
				
			# tuflow_to_gis
			elif self.cboCommonUtility.currentIndex() == 1:
				if self.rbMeshToGrid.isChecked():
					function = 'grid'
				elif self.rbMeshToPoints.isChecked():
					function = 'points'
				else:
					function = 'vectors'
				error, message = tuflowToGis(self.leTUFLOW2GIS.text().strip('"').strip("'"), function, workdir, self.leMeshToGis.text(),
				                             self.cboToGisMeshDataset.currentText(), self.cboTimestep.currentText(), saveFile=self.cbSaveBatComm.isChecked())
				
			# res_to_res
			elif self.cboCommonUtility.currentIndex() == 2:
				if self.rbMeshInfo.isChecked():
					function = 'info'
					meshes = [self.leMeshToRes.text().strip('"').strip("'")]
				elif self.rbMeshConvert.isChecked():
					function = 'conv'
					meshes = [self.leMeshToRes.text().strip('"').strip("'")]
				else:
					meshes = []
					for i in range(self.lwMeshes.count()):
						meshes.append(self.lwMeshes.item(i).text())
					if self.rbMeshMaximum.isChecked():
						function = 'max'
					else:
						function = 'conc'
				error, message = resToRes(self.leRes2Res.text().strip('"').strip("'"), function, workdir, meshes,
				                          self.cboToResMeshDataset.currentText(), out=self.leOutputName.text())
				
				
		# user input arguments (advanced mode)
		else:
			cbo2utility = {0: self.leAsc2Asc.text().strip('"').strip("'"), 1: self.leTUFLOW2GIS.text().strip('"').strip("'"), 2: self.leRes2Res.text().strip('"').strip("'"),
			               3: self.le12da2GIS.text().strip('"').strip("'"), 4: self.leConvert2TS1.text().strip('"').strip("'"), 5: self.leTin2Tin.text().strip('"').strip("'"),
			               6: self.leXSGenerator.text().strip('"').strip("'")}
			error, message = tuflowUtility(cbo2utility[self.cboAdvancedUtility.currentIndex()],
			                               self.leAdvWorkingDir.text().strip('"').strip("'"),
			                               self.teCommands.toPlainText(), self.cbSaveBatAdv.isChecked())
		
		self.setDefaults()
		self.saveProjectSettings()
		QgsApplication.restoreOverrideCursor()
		self.pbOK.setEnabled(True)
		self.pbCancel.setEnabled(True)
		if error:
			if message.count('\n') > 50:
				QMessageBox.critical(self, "TUFLOW Utilities", "Error Occured")
				self.errorDialog = UtilityErrorDialog(message)
				self.errorDialog.exec_()
			else:
				QMessageBox.critical(self, "TUFLOW Utilities", "Error Occured: {0}".format(message))
			self.pbOK.setEnabled(True)
			self.pbCancel.setEnabled(True)
		else:
			if self.rbCommonFunctions.isChecked() and \
					self.cboCommonUtility.currentIndex() == 2 and self.rbMeshInfo.isChecked():
				self.xmdfInfoDialog = XmdfInfoDialog(message)
				self.xmdfInfoDialog.exec_()
			else:
				#QMessageBox.information(self, "TUFLOW Utilities", "Utility Finished")
				self.accept()
		
	def saveProjectSettings(self):
		project = QgsProject.instance()
		project.writeEntry("TUFLOW", "utilities_current_tab", self.tabWidget.currentIndex())
		project.writeEntry("TUFLOW", "utilities_common_functions_cb", self.rbCommonFunctions.isChecked())
		project.writeEntry("TUFLOW", "utilities_advanced_cb", self.rbAdvanced.isChecked())
		if self.rbCommonFunctions.isChecked():
			project.writeEntry("TUFLOW", "utilities_common_functions", self.cboCommonUtility.currentIndex())
			project.writeEntry("TUFLOW", "utilities_output_directory", self.leComOutputDir.text())
			if self.leOutputName.text():
				project.writeEntry("TUFLOW", "utilities_output_name", self.leOutputName.text())
			if self.cboCommonUtility.currentIndex() == 0:
				project.writeEntry("TUFLOW", "utilities_asc_diff", self.rbAscDiff.isChecked())
				project.writeEntry("TUFLOW", "utilities_asc_max", self.rbAscMax.isChecked())
				project.writeEntry("TUFLOW", "utilities_asc_stat", self.rbAscStat.isChecked())
				project.writeEntry("TUFLOW", "utilities_asc_conv", self.rbAscConv.isChecked())
				if self.rbAscDiff.isChecked():
					project.writeEntry("TUFLOW", "utilities_asc_diff_grid1", self.cboDiffGrid1.currentText())
					project.writeEntry("TUFLOW", "utilities_asc_diff_grid2", self.cboDiffGrid2.currentText())
				else:
					grids = []
					for i in range(self.lwGrids.count()):
						grids.append(self.lwGrids.item(i).text())
					project.writeEntry("TUFLOW", "utilities_asc_diff_grids", grids)
			elif self.cboCommonUtility.currentIndex() == 1:
				project.writeEntry("TUFLOW", "utilities_tuflow_to_gis_mesh", self.leMeshToGis.text())
				project.writeEntry("TUFLOW", "utilities_tuflow_to_gis_datatype", self.cboToGisMeshDataset.currentText())
				project.writeEntry("TUFLOW", "utilities_tuflow_to_gis_togrid", self.rbMeshToGrid.isChecked())
				project.writeEntry("TUFLOW", "utilities_tuflow_to_gis_topoints", self.rbMeshToPoints.isChecked())
				project.writeEntry("TUFLOW", "utilities_tuflow_to_gis_tovectors", self.rbMeshToVectors.isChecked())
				project.writeEntry("TUFLOW", "utilities_tuflow_to_gis_timestep", self.cboTimestep.currentText())
			elif self.cboCommonUtility.currentIndex() == 2:
				project.writeEntry("TUFLOW", "utilities_res_to_res_datatype", self.cboToResMeshDataset.currentText())
				project.writeEntry("TUFLOW", "utilities_res_to_res_mesh", self.leMeshToRes.text())
				project.writeEntry("TUFLOW", "utilities_res_to_res_info", self.rbMeshInfo.isChecked())
				project.writeEntry("TUFLOW", "utilities_res_to_res_max", self.rbMeshMaximum.isChecked())
				project.writeEntry("TUFLOW", "utilities_res_to_res_conv", self.rbMeshConvert.isChecked())
				project.writeEntry("TUFLOW", "utilities_res_to_res_conc", self.rbMeshConcatenate.isChecked())
				meshes = []
				for i in range(self.lwMeshes.count()):
					meshes.append(self.lwMeshes.item(i).text())
				project.writeEntry("TUFLOW", "utilities_res_to_res_meshes", meshes)
		else:
			project.writeEntry("TUFLOW", "utilities_advanced", self.cboAdvancedUtility.currentIndex())
			project.writeEntry("TUFLOW", "utilities_working_directory", self.leAdvWorkingDir.text())
			project.writeEntry("TUFLOW", "utilities_flags", self.teCommands.toPlainText())
			
	def loadProjectSettings(self):
		project = QgsProject.instance()
		self.tabWidget.setCurrentIndex(project.readNumEntry("TUFLOW", "utilities_current_tab")[0])
		self.rbCommonFunctions.setChecked(project.readBoolEntry("TUFLOW", "utilities_common_functions_cb")[0])
		self.rbAdvanced.setChecked(project.readBoolEntry("TUFLOW", "utilities_advanced_cb")[0])
		self.cboCommonUtility.setCurrentIndex(project.readNumEntry("TUFLOW", "utilities_common_functions")[0])
		self.commonUtilityChanged(self.cboCommonUtility.currentIndex())
		self.leComOutputDir.setText(project.readEntry("TUFLOW", "utilities_output_directory")[0])
		self.leOutputName.setText(project.readEntry("TUFLOW", "utilities_output_name")[0])
		self.rbAscDiff.setChecked(project.readBoolEntry("TUFLOW", "utilities_asc_diff")[0])
		self.rbAscMax.setChecked(project.readBoolEntry("TUFLOW", "utilities_asc_max")[0])
		self.rbAscStat.setChecked(project.readBoolEntry("TUFLOW", "utilities_asc_stat")[0])
		self.rbAscConv.setChecked(project.readBoolEntry("TUFLOW", "utilities_asc_conv")[0])
		self.cboDiffGrid1.setCurrentText(project.readEntry("TUFLOW", "utilities_asc_diff_grid1")[0])
		self.cboDiffGrid2.setCurrentText(project.readEntry("TUFLOW", "utilities_asc_diff_grid2")[0])
		self.lwGrids.addItems(project.readListEntry("TUFLOW", "utilities_asc_diff_grids")[0])
		self.leMeshToGis.setText(project.readEntry("TUFLOW", "utilities_tuflow_to_gis_mesh")[0])
		self.cboToGisMeshDataset.setCurrentText(project.readEntry("TUFLOW", "utilities_tuflow_to_gis_datatype")[0])
		self.rbMeshToGrid.setChecked(project.readBoolEntry("TUFLOW", "utilities_tuflow_to_gis_togrid")[0])
		self.rbMeshToPoints.setChecked(project.readBoolEntry("TUFLOW", "utilities_tuflow_to_gis_topoints")[0])
		self.rbMeshToVectors.setChecked(project.readBoolEntry("TUFLOW", "utilities_tuflow_to_gis_tovectors")[0])
		self.cboTimestep.setCurrentText(project.readEntry("TUFLOW", "utilities_tuflow_to_gis_timestep", 'Max')[0])
		self.cboToResMeshDataset.setCurrentText(project.readEntry("TUFLOW", "utilities_res_to_res_datatype")[0])
		self.leMeshToRes.setText(project.readEntry("TUFLOW", "utilities_res_to_res_mesh")[0])
		self.rbMeshInfo.setChecked(project.readBoolEntry("TUFLOW", "utilities_res_to_res_info")[0])
		self.rbMeshMaximum.setChecked(project.readBoolEntry("TUFLOW", "utilities_res_to_res_max")[0])
		self.rbMeshConvert.setChecked(project.readBoolEntry("TUFLOW", "utilities_res_to_res_conv")[0])
		self.rbMeshConcatenate.setChecked(project.readBoolEntry("TUFLOW", "utilities_res_to_res_conc")[0])
		self.lwMeshes.addItems(project.readListEntry("TUFLOW", "utilities_res_to_res_meshes")[0])
		self.cboAdvancedUtility.setCurrentIndex(project.readNumEntry("TUFLOW", "utilities_advanced")[0])
		self.leAdvWorkingDir.setText(project.readEntry("TUFLOW", "utilities_working_directory")[0])
		self.teCommands.setPlainText(project.readEntry("TUFLOW", "utilities_flags")[0])
	
	def setDefaults(self, executables_only=False):
		if not executables_only:
			if self.leComOutputDir.text():
				QSettings().setValue('TUFLOW_Utilities/output_directory', self.leComOutputDir.text())
			if self.cboDiffGrid1.currentText():
				if self.cboDiffGrid1.currentText().count(os.sep) > 0:
					QSettings().setValue('TUFLOW_Utilities/ASC_to_ASC_difference_grid1', self.cboDiffGrid1.currentText())
			if self.cboDiffGrid2.currentText():
				if self.cboDiffGrid2.currentText().count(os.sep) > 0:
					QSettings().setValue('TUFLOW_Utilities/ASC_to_ASC_difference_grid2', self.cboDiffGrid2.currentText())
			if self.leAdvWorkingDir.text():
				QSettings().setValue("TUFLOW_Utilities/advanced_working_directory", self.leAdvWorkingDir.text())
			if self.leMeshToGis.text():
				QSettings().setValue("TUFLOW_Utilities/TUFLOW_to_GIS_mesh", self.leMeshToGis.text())
			if self.leMeshToRes.text():
				QSettings().setValue("'TUFLOW_Utilities/Res_to_Res_mesh'", self.leMeshToRes.text())
		if self.leAsc2Asc.text():
			QSettings().setValue("TUFLOW_Utilities/ASC_to_ASC_exe", self.leAsc2Asc.text())
		if self.leTUFLOW2GIS.text():
			QSettings().setValue("TUFLOW_Utilities/TUFLOW_to_GIS_exe", self.leTUFLOW2GIS.text())
		if self.leRes2Res.text():
			QSettings().setValue("TUFLOW_Utilities/Res_to_Res_exe", self.leRes2Res.text())
		if self.le12da2GIS.text():
			QSettings().setValue("TUFLOW_Utilities/12da_to_from_GIS_exe", self.le12da2GIS.text())
		if self.leConvert2TS1.text():
			QSettings().setValue("TUFLOW_Utilities/Convert_to_TS1_exe", self.leConvert2TS1.text())
		if self.leTin2Tin.text():
			QSettings().setValue("Tin_to_Tin executable location", self.leTin2Tin.text())
		if self.leXSGenerator.text():
			QSettings().setValue("TUFLOW_Utilities/xsGenerator_exe", self.leXSGenerator.text())
	
	def applyPrevExeLocations(self):
		self.leAsc2Asc.setText(QSettings().value("TUFLOW_Utilities/ASC_to_ASC_exe"))
		self.leTUFLOW2GIS.setText(QSettings().value("TUFLOW_Utilities/TUFLOW_to_GIS_exe"))
		self.leRes2Res.setText(QSettings().value("TUFLOW_Utilities/Res_to_Res_exe"))
		self.le12da2GIS.setText(QSettings().value("TUFLOW_Utilities/12da_to_from_GIS_exe"))
		self.leConvert2TS1.setText(QSettings().value("TUFLOW_Utilities/Convert_to_TS1_exe"))
		self.leTin2Tin.setText(QSettings().value("Tin_to_Tin executable location"))
		self.leXSGenerator.setText(QSettings().value("TUFLOW_Utilities/xsGenerator_exe"))
		
	def connectBrowseButtons(self):
		self.btnBrowseComOutputDir.clicked.connect(lambda: self.browse('existing folder',
		                                                               'TUFLOW_Utilities/output_directory',
		                                                               'Output Directory', None, self.leComOutputDir))
		self.btnBrowseDiffGrid1.clicked.connect(lambda: self.browse('existing file',
		                                                            'TUFLOW_Utilities/ASC_to_ASC_difference_grid1',
		                                                            'ASC_to_ASC Difference Grid 1',
		                                                            "All grid formats (*.asc *.ASC *.flt *.FLT *.txt *.TXT);;"
		                                                            "ASC format(*.asc *.ASC);;"
		                                                            "FLT format (*.flt *.FLT);;"
		                                                            "TXT format (*.txt *.TXT", self.cboDiffGrid1))
		self.btnBrowseDiffGrid2.clicked.connect(lambda: self.browse('existing file',
		                                                            'TUFLOW_Utilities/ASC_to_ASC_difference_grid2',
		                                                            'ASC_to_ASC Difference Grid 2',
		                                                            "All grid formats (*.asc *.ASC *.flt *.FLT *.txt *.TXT);;"
		                                                            "ASC format(*.asc *.ASC);;"
		                                                            "FLT format (*.flt *.FLT);;"
		                                                            "TXT format (*.txt *.TXT", self.cboDiffGrid2))
		self.btnBrowseGrid.clicked.connect(lambda: self.browse('existing files',
		                                                       'TUFLOW_Utilities/ASC_to_ASC_grid',
		                                                       'ASC_to_ASC Input Grid',
		                                                       "All grid formats (*.asc *.ASC *.flt *.FLT *.txt *.TXT);;"
		                                                       "ASC format(*.asc *.ASC);;"
		                                                       "FLT format (*.flt *.FLT);;"
		                                                       "TXT format (*.txt *.TXT", self.cboGrid))
		self.btnBrowseAdvWorkingDir.clicked.connect(lambda: self.browse('existing folder',
		                                                                "TUFLOW_Utilities/advanced_working_directory",
		                                                                "Working Directory", None,
		                                                                self.leAdvWorkingDir))
		self.btnBrowseAsc2Asc.clicked.connect(lambda: self.browse('existing file', "TUFLOW_Utilities/ASC_to_ASC_exe",
		                                                          "ASC_to_ASC executable location", "EXE (*.exe *.EXE)",
		                                                          self.leAsc2Asc))
		self.btnBrowseTUFLOW2GIS.clicked.connect(lambda: self.browse('existing file',
		                                                             "TUFLOW_Utilities/TUFLOW_to_GIS_exe",
		                                                             "TUFLOW_to_GIS executable location",
		                                                             "EXE (*.exe *.EXE)", self.leTUFLOW2GIS))
		self.btnBrowseRes2Res.clicked.connect(lambda: self.browse('existing file',
		                                                          "TUFLOW_Utilities/Res_to_Res_exe",
		                                                          "Res_to_Res executable location",
		                                                          "EXE (*.exe *.EXE)", self.leRes2Res))
		self.btnBrowse12da2GIS.clicked.connect(lambda: self.browse('existing file',
		                                                           "TUFLOW_Utilities/12da_to_from_GIS_exe",
		                                                           "12da_to_from_GIS executable location",
		                                                           "EXE (*.exe *.EXE)", self.le12da2GIS))
		self.btnBrowseConvert2TS1.clicked.connect(lambda: self.browse('existing file',
		                                                              "TUFLOW_Utilities/Convert_to_TS1_exe",
		                                                              "Convert_to_TS1 executable location",
		                                                              "EXE (*.exe *.EXE)", self.leConvert2TS1))
		self.btnBrowseTin2Tin.clicked.connect(lambda: self.browse('existing file',
		                                                          "TUFLOW_Utilities/Tin_to_Tin_exe",
		                                                          "Tin_to_Tin executable location",
		                                                          "EXE (*.exe *.EXE)", self.leTin2Tin))
		self.btnBrowseXSGenerator.clicked.connect(lambda: self.browse('existing file',
		                                                              "TUFLOW_Utilities/xsGenerator_exe",
		                                                              "xsGenerator executable location",
		                                                              "EXE (*.exe *.EXE)", self.leXSGenerator))
		self.btnBrowseMeshToGis.clicked.connect(lambda: self.browse('existing file',
		                                                            'TUFLOW_Utilities/TUFLOW_to_GIS_mesh',
		                                                            'XMDF or DAT location',
		                                                            "All mesh formats (*.xmdf *.XMDF *.dat *.DAT);;"
		                                                            "XMDF format(*.xmdf *.XMDF);;"
		                                                            "DAT format (*.dat *.DAT)", self.leMeshToGis))
		self.btnBrowseMeshToRes.clicked.connect(lambda: self.browse('existing file',
		                                                            'TUFLOW_Utilities/Res_to_Res_mesh',
		                                                            'XMDF or DAT location',
		                                                            "All mesh formats (*.xmdf *.XMDF *.dat *.DAT);;"
		                                                            "XMDF format(*.xmdf *.XMDF);;"
		                                                            "DAT format (*.dat *.DAT)", self.leMeshToRes))
		self.btnBrowseMeshMulti.clicked.connect(lambda: self.browse('existing files',
		                                                            'TUFLOW_Utilities/TUFLOW_to_GIS_meshes',
		                                                            'XMDF or DAT location',
		                                                            "All mesh formats (*.xmdf *.XMDF *.dat *.DAT);;"
		                                                            "XMDF format(*.xmdf *.XMDF);;"
		                                                            "DAT format (*.dat *.DAT)", self.leMeshMulti))
		

#-----------------------------------------------------------
#    XMDF info
# ----------------------------------------------------------
from XMDF_info import *


class XmdfInfoDialog(QDialog, Ui_XmdfInfoDialog):
	def __init__(self, text):
		QDialog.__init__(self)
		self.setupUi(self)
		self.teXmdfInfo.setPlainText(text)


# ----------------------------------------------------------
#    Stack Trace
# ----------------------------------------------------------
from StackTrace import *


class StackTraceDialog(QDialog, Ui_StackTraceDialog):
	def __init__(self, text):
		QDialog.__init__(self)
		self.setupUi(self)
		self.teStackTrace.setPlainText(text)
		
		
# ----------------------------------------------------------
#    Tuflow utility error
# ----------------------------------------------------------
from Tuflow_utility_error import *


class UtilityErrorDialog(QDialog, Ui_utilityErrorDialog):
	def __init__(self, text):
		QDialog.__init__(self)
		self.setupUi(self)
		self.teError.setPlainText(text)
		
		
# ----------------------------------------------------------
#    Tuflow utility download progress bar
# ----------------------------------------------------------
from download_utility_progress import *


class UtilityDownloadProgressBar(QDialog, Ui_downloadUtilityProgressDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent=parent)
		self.setupUi(self)
		self.progressBar.setRange(0, 0)
		self.progressCount = 0
		self.start = True
		
	def updateProgress(self, e, start_again=True):
		self.label.setText('Downloading {0}'.format(e) + ' .' * self.progressCount)
		self.progressCount += 1
		if self.progressCount > 4:
			self.progressCount = 0
		QgsApplication.processEvents()
		
		if start_again:
			if not self.start:
				self.timer.stop()
			else:
				self.start = False
			self.timer = QTimer()
			self.timer.setInterval(500)
			self.timer.timeout.connect(lambda: self.updateProgress(e, start_again=False))
			self.timer.start()
		
	def progressFinished(self, e):
		self.timer.stop()
		self.progressBar.setRange(100, 100)
		self.label.setText('Complete')


class DownloadTuflowUtilities(QObject):
	finished = pyqtSignal(dict)
	updated = pyqtSignal(str)
	
	utilities = ['asc_to_asc', 'tuflow_to_gis', 'res_to_res', '12da_to_from_gis', 'convert_to_ts1', 'tin_to_tin',
	             'xsGenerator']
	paths = {}
	
	def download(self):
		for utility in self.utilities:
			self.updated.emit(utility)
			path = downloadUtility(utility)
			self.paths[utility] = path
		
		self.finished.emit(self.paths)


# ----------------------------------------------------------
#    tuflowqgis broken links
# ----------------------------------------------------------
from ui_tuflowqgis_brokenLinks import *


class tuflowqgis_brokenLinks_dialog(QDialog, Ui_scenarioSelection):
	def __init__(self, iface, brokenLinks):
		QDialog.__init__(self)
		self.iface = iface
		self.brokenLinks = brokenLinks
		self.setupUi(self)
		
		for brokenLink in self.brokenLinks:
			self.brokenLinks_lw.addItem(brokenLink)
		
		self.ok_button.clicked.connect(self.accept)
