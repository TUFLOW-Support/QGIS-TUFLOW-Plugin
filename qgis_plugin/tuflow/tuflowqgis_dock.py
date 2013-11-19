
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms")

from ui_tuflowqgis_1d_iface import Ui_tuflowqgis_1d_iface

class TUFLOWifaceDock(QDockWidget, Ui_tuflowqgis_1d_iface):
    
	def __init__(self, iface):
        
		QDockWidget.__init__(self)
		Ui_tuflowqgis_1d_iface.__init__(self)
		self.setupUi(self)
		self.iface = iface
		self.canvas = self.iface.mapCanvas()
		self.handler = None
		self.idx = -1
		self.selected_layer = None
             
		# Connect signals and slots
		QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.closeup)
		QObject.connect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.connect(self.locationDrop, SIGNAL("currentIndexChanged(int)"), self.loc_changed)       
        #self.ResTypeList.currentItemChanged.connect(self.res_type_changed)
		QObject.connect(self.ResTypeList, SIGNAL("currentRowChanged(int)"), self.res_type_changed) 

		self.refresh()
		
	def __del__(self):
		# Disconnect signals and slots
		QObject.disconnect(self.buttonBox, SIGNAL("accepted()"), self.closeup)
		QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerChanged)
		QObject.disconnect(self.locationDrop,SIGNAL("currentIndexChanged(int)"), self.loc_changed)
		QObject.disconnect(self.ResTypeList, SIGNAL("currentRowChanged(int)"), self.res_type_changed) 
		try:
			QObject.disconnect(layer,SIGNAL("selectionChanged()"),self.select_changed)
		except:
			QMessageBox.information(self.iface.mainWindow(), "DEBUG", "error disconnecting()")
	def refresh(self):
		"""
			Refresh is usually called when the selected layer changes in the legend
			Refresh clears and repopulates the dock widgets, restoring them to their correct values
		"""
		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "refresh()")
		self.cLayer = self.canvas.currentLayer()
		self.layerChanged(self.cLayer)
		self.select_changed()

	def closeup(self):
		"""
			Close up and remove the dock
		"""
		QMessageBox.information(self.iface.mainWindow(), "DEBUG", "closeup()")

	def layerChanged(self, layer):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "layerChanged()")
		self.cLayer = self.canvas.currentLayer()
		self.sourcelayer.clear()
		self.locationDrop.clear()
		self.IDList.clear()
		if self.cLayer and (self.cLayer.type() == QgsMapLayer.VectorLayer):
			#QMessageBox.information(self.iface.mainWindow(), "DEBUG", self.cLayer.name())
			self.sourcelayer.addItem(self.cLayer.name())
			self.sourcelayer.setCurrentIndex(0)
			GType = self.cLayer.dataProvider().geometryType()
			if (GType == QGis.WKBPoint):
				self.locationDrop.addItem("Node") #this triggers loc_changed which populates data fields
			elif (GType == QGis.WKBLineString):
				self.locationDrop.addItem("Channel")
				self.locationDrop.addItem("Long Profile")
				self.locationDrop.setCurrentIndex(0)
			elif (GType == QGis.WKBPolygon):
				QMessageBox.information(self.iface.mainWindow(), "Information", "Expecting point or line geometry type, not polygon.")
			else:
				QMessageBox.information(self.iface.mainWindow(), "Information", "Expecting point or line geometry type.")
			#index to ID
			self.idx = self.cLayer.fieldNameIndex('ID')
			if (self.idx < 0):
				QMessageBox.information(self.iface.mainWindow(), "Information", "Layer has no field named ID, please choose another layer.")
		else:
			self.sourcelayer.addItem("Invalid layer or no layer selected")
			self.sourcelayer.setCurrentIndex(0)

		if self.handler:
			QObject.disconnect(self.selected_layer, SIGNAL("selectionChanged()"),self.select_changed)
			self.handler = False
			self.selected_layer = None
		if layer is not None:
			if layer.isValid():
				QObject.connect(layer,SIGNAL("selectionChanged()"),self.select_changed)
				self.selected_layer = layer

	def select_changed(self):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "select_changed()")
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", self.cLayer.name())
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", QString(self.idx))
		# whatever
		self.IDs = []
		self.IDList.clear()
		if self.idx >= 0:
			for feature in self.cLayer.selectedFeatures():
				self.IDs.append(feature.attributeMap()[self.idx].toString())
				#QMessageBox.information(self.iface.mainWindow(), "DEBUG", feature.attributeMap()[self.idx].toString())
				self.IDList.addItem(feature.attributeMap()[self.idx].toString())
		
		# call file writer
		self.write_iface_file()

	def res_type_changed(self):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "Results type changed")
		# call file writer
		self.write_iface_file()
		
	def loc_changed(self):
		loc = self.locationDrop.currentText()
		if (loc == "Node"):
			self.ResTypeList.clear()
			self.ResTypeList.addItem("Level")
		elif (loc == "Channel"):
			self.ResTypeList.clear()
			self.ResTypeList.addItem("Flow")
			self.ResTypeList.addItem("Velocity")
			self.ResTypeList.addItem("US Levels")
			self.ResTypeList.addItem("DS Levels")
		elif (loc == "Long Profile"):
			self.ResTypeList.clear()
			self.ResTypeList.addItem("Level")
		else:
			self.ResTypeList.clear()

	def write_iface_file(self):
		#QMessageBox.information(self.iface.mainWindow(), "DEBUG", "write_iface_file()")
		loc = self.locationDrop.currentText()
		type = []
		
		# Compile of output types
		for x in range(0, self.ResTypeList.count()):
			list_item = self.ResTypeList.item(x)
			if list_item.isSelected():
				type.append(list_item.text())
				#QMessageBox.information(self.iface.mainWindow(), "DEBUG", list_item.text())
		
		# Write .txt file
		skip = False
		if len(type) == 0:
			QMessageBox.information(self.iface.mainWindow(), "Information", "No results type selected.")
			skip = True
		if len (self.IDs) == 0:
			QMessageBox.information(self.iface.mainWindow(), "Information", "No elements selected.")
			skip = True
		
		if skip:
			pass
		else:
			iface = r'C:\TUFLOW\dev\Python\gis_iface\gis_iface.txt'
			f = file(iface, 'w')
			line = "Location Type == "+loc
			f.write(line+"\n")
			line = "Parameter == "
			for x in type:
				line = line+x+","
			if (line[len(line)-1] == ","):
				line = line[0:len(line)-1]
			f.write(line+"\n")
			line = "ID == "
			for x in self.IDs:
				line = line+x+","
			if (line[len(line)-1] == ","):
				line = line[0:len(line)-1]
			f.write(line+"\n")
			f.flush()
			f.close()