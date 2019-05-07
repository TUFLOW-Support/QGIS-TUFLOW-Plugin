# TuPLOT External python File. Writes interface file and calls tkinter program.
# Build: 2017-11-AA Development
# Author: ES

# ArcGIS version

import os
import sys
import csv
from subprocess import Popen
import subprocess
from PyQt4.QtCore import * # QGIS only
from PyQt4.QtGui import * # QGIS only
from qgis.core import * # QGIS only

from numpy import genfromtxt
import tuflowqgis_styles

current_path = os.path.dirname(__file__)

class TuPLOT(object):
	"""Activated when TuPLOT external button is pressed.
	Button will write an interface file if any features are selected
	and initiate TuPLOT if not already initiated.
	
	ArcGIS and QGIS versions are very similar however there are some code
	block differences, as well as some minor differences. These differences
	are highlighted as best as possible."""
	
	def __init__(self, iface):
		self.iface = iface # QGIS only
		self.tpcFile = ''
		self.intFile = ''
		self.defaultPath = 'C:\\'
		self.tpOpen = None
		self.intFile = ''
		
		
		# check dependencies. Only relevant in QGIS.
		try:
			import Tkinter
		except:
			sys.path.append(os.path.join(current_path, 'tkinter\\DLLs'))
			sys.path.append(os.path.join(current_path, 'tkinter\\libs'))
			sys.path.append(os.path.join(current_path, 'tkinter\\Lib'))
			sys.path.append(os.path.join(current_path, 'tkinter\\Lib\\lib-tk'))
			try:
				import Tkinter
			except:
				QMessageBox.information(self.iface.mainWindow(), "TuPLOT: Error", "Unable to find or install Tkinter")
	
		
	def open(self, tpOpen, intFile, defaultPath):
		self.tpOpen = tpOpen
		self.intFile = intFile
		self.defaultPath = defaultPath
		
		
		# check if TuPLOT is already running, otherwise open dialog and let user select tpc
		try:
			poll = self.tpOpen.poll()
			if poll == None:
				next
			else:
				break_statement # break the try statement. 'break' command doesn't seem to work!
		except: # TuPLOT is not running. Open dialog so user can choose .tpc
			self.tpcFile = QFileDialog.getOpenFileNames(self.iface.mainWindow(), 'Select TUFLOW Plot Control (.tpc)', self.defaultPath, "TUFLOW Plot Results (*.tpc)")
			if len(self.tpcFile) < 1:
				return 'not open', '', self.defaultPath
			self.tpcFile = self.tpcFile[0]
			fpath = os.path.dirname(self.tpcFile)
			self.defaultPath = fpath # next time it will open to this location
			
			
			
			
			# Ask user if they want to import gis layers as well
			alsoOpenGIS = QMessageBox.question(self.iface.mainWindow(), "TuPLOT", 'Do you also want to open result GIS layer?', QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
			
			# Add gis layers
			if alsoOpenGIS == QMessageBox.Yes:
				error, message, gisLayers, nPoints, nLines, nRegions = open_gis(self.tpcFile)
				if error: # something has gone wrong
					QMessageBox.information(self.iface.mainWindow(), "TuPLOT: Error", message)
				else: # all good and now reading in the gis layers to arcmap
					for layer in gisLayers:
						if (os.path.basename(layer)[-6:-4] == '_P' and nPoints > 0) or (os.path.basename(layer)[-6:-4] == '_L' and nLines > 0) or (os.path.basename(layer)[-6:-4] == '_R' and nRegions > 0):
							addLayer = self.iface.addVectorLayer(layer, os.path.basename(layer)[:-4], "ogr")
						
						# apply tuflow style to imported gis layer
						try:
							tf_styles = tuflowqgis_styles.TF_Styles()
							error, message = tf_styles.Load()
							error, message, slyr = tf_styles.Find(os.path.basename(addLayer.source())[:-4], addLayer) #use tuflow styles to find longest matching 
							if error:
								return error, message
							if slyr: #style layer found:
								addLayer.loadNamedStyle(slyr)
								addLayer.triggerRepaint()
						except:
							next

			# specify .int file
			self.intFile = os.path.splitext(self.tpcFile)[0] + '.int'
			iterator = 1
			while os.path.isfile(self.intFile):
				self.intFile = os.path.splitext(self.tpcFile)[0] + '[' + str(iterator) +']' + '.int'
				iterator += 1

		# write .int file for selected features (if any)
		try:
			cLayer = self.iface.mapCanvas().currentLayer()
			cSelection = cLayer.selectedFeatures()
			
			# get geometry type for .int file
			if cLayer and (cLayer.type() == QgsMapLayer.VectorLayer):
				geom_type = cLayer.geometryType()
				if geom_type == 0:
					geom_type = 'Point'
					valid = True
				elif geom_type == 1:
					geom_type = 'Line'
					valid = True
				elif geom_type == 2:
					geom_type = 'Region'
				else:
					message = "Unexpected input geometry."
			else:
				message = "Invalid layer or no layer selected"
			
			# get attributes for .int file
			attributes = []
			try:
				for feature in cSelection:
					try:
						attribute = []
						featureID = feature['ID'].strip()
						attribute.append(feature['ID'].strip())
						attribute.append(feature['Type'].strip())
						attribute.append(feature['Source'].strip())
						attributes.append(attribute)
					except:
						warning = True #suppress the warning below, most likely due to a "X" type channel or blank name
			except:
				message = 'Not a valid TUFLOW result file layer.'
			create_int(self.intFile, geom_type, attributes)
		except: # no features selected
			create_int(self.intFile, "", [])
		
		# open tkinter program
		try:
			# check to see if TuPlot is already running
			poll = self.tpOpen.poll()
			if poll == None: # TuPLOT is already running
				return self.tpOpen, self.intFile, self.defaultPath
			else:
				break_statement # break the try statement. 'break' command doesn't seem to work!
		except: # Tuplot is not running: open tuplot
			pid = str(os.getpid()) + ".pid"
			try: # tpLocation not defined, but left in to be consistent with ArcGIS version
				tpArgs = ['python', tpLocation, self.intFile, self.tpcFile, pid]
			except:
				tpArgs = ['python', os.path.join(current_path, 'tkinter_tuplot.py'), self.intFile, self.tpcFile, pid]
			CREATE_NO_WINDOW = 0x08000000 # suppresses python console window
			#logfile = open(r'C:\TUFLOW\TUPLOT\example_results\plot\log.txt', 'w')
			#self.tpOpen = subprocess.Popen(tpArgs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
			#                               creationflags=CREATE_NO_WINDOW)
			#try:
			#	for line in self.tpOpen.stdout:
			#		#sys.stdout.write(line)
			#		logfile.write(line)
			#		self.tpOpen.wait()
			#	logfile.close()
			#except:
			#	logfile.close()
			self.tpOpen = Popen(tpArgs, creationflags=CREATE_NO_WINDOW)
			return self.tpOpen, self.intFile, self.defaultPath
			
class MyValidatorTpc(object): # relevant in ArcGIS only
	"""TPC file type validator for use in with the openDialog command. This will stop any file
	that isn't .tpc from being opened from Arc to TuPLOT."""
	
	def __str__(self):
		return "TPC(*.tpc)"
	def __call__(self, filename):
		if os.path.isfile(filename) and filename.lower().endswith(".tpc"):
			return True
		return False
		
def plot_objects(filepath):
	"""
	Hold the plot objects data
	"""
	with open(filepath, 'rb') as csvfile:
		reader = csv.reader(csvfile, delimiter=',', quotechar='"')
		ID = []
		domain = []
		dat_type = []
		geom = []
		for row in reader:
			ID.append(row[0].strip())
			domain.append(row[1])
			dat_type.append(row[2])
			geom.append(row[3])

		csvfile.close()
		nPoints = geom.count('P') #2017-08-AA
		nLines = geom.count('L') #2017-08-AA
		nRegions = geom.count('R') #2017-08-AA
	return nPoints, nLines, nRegions

def create_int(int, geom_type, attributes):
	"""Creates an interface file (.int) that is used by TuPLOT to know which result features are selected."""

	if len(geom_type) > 0:
		geom_type = geom_type + "\n"
	
	# write geometry header
	geometry_header = "!set the geometry of the slected plot layer (point, line, region, multiple)\n[GEOMETRY]\n" \
	+ geom_type + "[/GEOMETRY]\n\n"

	# write selection data
	selection = ""
	if len(attributes) > 0:
		for item in attributes:
			selection += "\n" + item[0] + "," + item[1] + "," + item[2]
		selection_data = "!the GIS attribute data for the selection, the same as it appears in the _PLOT_ layer" \
		"(ID,Type,Source)\n[SELECTION]" + selection + "\n[/SELECTION]"
	else:
		selection_data = "!the GIS attribute data for the selection, the same as it appears in the _PLOT_ layer" \
		"(ID,Type,Source)\n[SELECTION]\n[/SELECTION]"
	
	# write header and data out to .int file
	final_txt = geometry_header + selection_data
	f = open(int, "w")
	f.write(final_txt)
	f.close()
	


def open_gis(tpc):
	"""Open result GIS layers using the input tpc file. Extract from TUFLOW_result2016.py."""
	
	error = False
	message = None
	gisLayers = []
	fpath = os.path.dirname(tpc)
	try:
		data = genfromtxt(tpc, dtype=str, delimiter="==")
	except:
		error = True
		message = 'ERROR - Unable to load data, check file exists.'
		return error, message, gisLayers

	for i in range (0,len(data)):
		tmp = data[i,0]
		dat_type = tmp.strip()
		tmp = data[i,1]
		rdata = tmp.strip()
		if (dat_type == 'GIS Plot Layer Points'):
			gisLayers.append(os.path.join(fpath, rdata[2:]))
		elif (dat_type == 'GIS Plot Layer Lines'):
			gisLayers.append(os.path.join(fpath, rdata[2:]))
		elif (dat_type == 'GIS Plot Layer Regions'):
			gisLayers.append(os.path.join(fpath, rdata[2:]))
		elif (dat_type=='GIS Plot Objects'):
			fullpath = os.path.join(fpath, rdata[2:])
			nPoints, nLines, nRegions = plot_objects(fullpath)
	return error, message, gisLayers, nPoints, nLines, nRegions
	