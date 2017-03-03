# -*- coding: utf-8 -*-
"""
/***************************************************************************
 tuflowqgis_menu
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
build_vers = '2017-03-AA (QGIS 2.x)'
build_type = 'developmental' #release / developmental

# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import os

# Import the code for the dialog
from tuflowqgis_dialog import *

# Import the code for the 1D results viewer
from tuflowqgis_TuPlot import *

#par
from tuflowqgis_library import tuflowqgis_apply_check_tf

class tuflowqgis_menu:

	def __init__(self, iface):
		self.iface = iface
		self.dockOpened = False

	def initGui(self):
		# About Submenu
		self.about_menu = QMenu(QCoreApplication.translate("TUFLOW", "&About"))
		self.iface.addPluginToMenu("&TUFLOW", self.about_menu.menuAction())

		icon = QIcon(os.path.dirname(__file__) + "/icons/info.png")
		self.about_action = QAction(icon, "About", self.iface.mainWindow())
		QObject.connect(self.about_action, SIGNAL("triggered()"), self.about_tuflowqgis)
		self.about_menu.addAction(self.about_action)
		
		icon = QIcon(os.path.dirname(__file__) + "/icons/check_dependancy.png")
		self.check_dependancy_action = QAction(icon, "Check Python Dependencies Installed", self.iface.mainWindow())
		QObject.connect(self.check_dependancy_action, SIGNAL("triggered()"), self.check_dependencies)
		self.about_menu.addAction(self.check_dependancy_action)
		
		# Editing Submenu
		self.editing_menu = QMenu(QCoreApplication.translate("TUFLOW", "&Editing"))
		self.iface.addPluginToMenu("&TUFLOW", self.editing_menu.menuAction())
		
		#icon = QIcon(os.path.dirname(__file__) + "/icons/tuflow_increment_24px.png")
		icon = QIcon(os.path.dirname(__file__) + "/icons/tuflow.png")
		self.configure_tf_action = QAction(icon, "Configure / Create TUFLOW Project", self.iface.mainWindow())
		QObject.connect(self.configure_tf_action, SIGNAL("triggered()"), self.configure_tf)
		self.editing_menu.addAction(self.configure_tf_action)
		
		#icon = QIcon(os.path.dirname(__file__) + "/icons/tuflow.png")
		#self.create_tf_dir_action = QAction(icon, "Create TUFLOW Directory", self.iface.mainWindow())
		#QObject.connect(self.create_tf_dir_action, SIGNAL("triggered()"), self.create_tf_dir)
		#self.editing_menu.addAction(self.create_tf_dir_action)

		icon = QIcon(os.path.dirname(__file__) + "/icons/tuflow_import.png")
		self.import_empty_tf_action = QAction(icon, "Import Empty File", self.iface.mainWindow())
		QObject.connect(self.import_empty_tf_action, SIGNAL("triggered()"), self.import_empty_tf)
		self.editing_menu.addAction(self.import_empty_tf_action)

		icon = QIcon(os.path.dirname(__file__) + "/icons/tuflow_increment_24px.png")
		self.increment_action = QAction(icon, "Increment Selected Layer", self.iface.mainWindow())
		QObject.connect(self.increment_action, SIGNAL("triggered()"), self.increment_layer)
		self.editing_menu.addAction(self.increment_action)
		
		icon = QIcon(os.path.dirname(__file__) + "/icons/mif_2_shp.png")
		self.splitMI_action = QAction(icon, "Convert MapInfo file to Shapefile (beta)", self.iface.mainWindow())
		QObject.connect(self.splitMI_action, SIGNAL("triggered()"), self.split_MI)
		self.editing_menu.addAction(self.splitMI_action)

		icon = QIcon(os.path.dirname(__file__) + "/icons/mif_2_shp.png")
		self.splitMI_folder_action = QAction(icon, "Convert MapInfo files in folder Shapefile (beta)", self.iface.mainWindow())
		QObject.connect(self.splitMI_folder_action, SIGNAL("triggered()"), self.split_MI_folder)
		self.editing_menu.addAction(self.splitMI_folder_action)
		
		#Not tested enough to include
		#icon = QIcon(os.path.dirname(__file__) + "/icons/icon.png")
		#self.points_to_lines_action = QAction(icon, "Convert Points to Lines (survey to breaklines) ALPHA", self.iface.mainWindow())
		#QObject.connect(self.points_to_lines_action, SIGNAL("triggered()"), self.points_to_lines)
		#self.editing_menu.addAction(self.points_to_lines_action)
		
		

		# RUN Submenu
		self.run_menu = QMenu(QCoreApplication.translate("TUFLOW", "&Run"))
		self.iface.addPluginToMenu("&TUFLOW", self.run_menu.menuAction())
		
		icon = QIcon(os.path.dirname(__file__) + "/icons/Run_TUFLOW.png")
		self.run_tuflow_action = QAction(icon, "Run TUFLOW Simulation", self.iface.mainWindow())
		QObject.connect(self.run_tuflow_action, SIGNAL("triggered()"), self.run_tuflow)
		self.run_menu.addAction(self.run_tuflow_action)
		
		#top level in menu
		# TuPlot
		icon = QIcon(os.path.dirname(__file__) + "/icons/results.png")
		self.view_1d_results_action = QAction(icon, "TuPlot", self.iface.mainWindow())
		QObject.connect(self.view_1d_results_action, SIGNAL("triggered()"), self.results_1d)
		self.iface.addToolBarIcon(self.view_1d_results_action)
		self.iface.addPluginToMenu("&TUFLOW", self.view_1d_results_action)
  
		# Added MJS 11/02   
		icon = QIcon(os.path.dirname(__file__) + "/icons/check_files_folder.png")
		self.import_chk_action = QAction(icon, "Import Check Files from Folder", self.iface.mainWindow())
		QObject.connect(self.import_chk_action, SIGNAL("triggered()"), self.import_check)
		self.iface.addToolBarIcon(self.import_chk_action)
		self.iface.addPluginToMenu("&TUFLOW", self.import_chk_action)
	
		#PAR 2016/02/12
		icon = QIcon(os.path.dirname(__file__) + "/icons/check_files_open.png")
		self.apply_chk_action = QAction(icon, "Apply TUFLOW Styles to Open Layers", self.iface.mainWindow())
		QObject.connect(self.apply_chk_action, SIGNAL("triggered()"), self.apply_check)
		self.iface.addToolBarIcon(self.apply_chk_action)
		self.iface.addPluginToMenu("&TUFLOW", self.apply_chk_action)
		
		#PAR 2016/02/15
		icon = QIcon(os.path.dirname(__file__) + "/icons/check_files_currentlayer.png")
		self.apply_chk_cLayer_action = QAction(icon, "Apply TUFLOW Styles to Current Layer", self.iface.mainWindow())
		QObject.connect(self.apply_chk_cLayer_action, SIGNAL("triggered()"), self.apply_check_cLayer)
		self.iface.addToolBarIcon(self.apply_chk_cLayer_action)
		self.iface.addPluginToMenu("&TUFLOW", self.apply_chk_cLayer_action)
		
		#Init classes variables
		self.dockOpened = False		#remember for not reopening dock if there's already one opened
		self.resdockOpened = False
		self.selectionmethod = 0						#The selection method defined in option
		self.saveTool = self.iface.mapCanvas().mapTool()			#Save the standard mapttool for restoring it at the end
		self.layerindex = None							#for selection mode
		self.previousLayer = None						#for selection mode
		self.plotlibrary = None							#The plotting library to use
		self.textquit0 = "Click for polyline and double click to end (right click to cancel then quit)"
		self.textquit1 = "Select the polyline in a vector layer (Right click to quit)"

	def unload(self):
		self.iface.removePluginMenu("&TUFLOW", self.about_menu.menuAction())
		self.iface.removePluginMenu("&TUFLOW", self.editing_menu.menuAction())
		self.iface.removePluginMenu("&TUFLOW", self.run_menu.menuAction())
		del self.import_chk_action

	def configure_tf(self):
		project = QgsProject.instance()
		dialog = tuflowqgis_configure_tf_dialog(self.iface,project)
		dialog.exec_()

	def create_tf_dir(self):
		project = QgsProject.instance()
		dialog = tuflowqgis_create_tf_dir_dialog(self.iface, project)
		dialog.exec_()
		
	def import_empty_tf(self):
		project = QgsProject.instance()
		dialog = tuflowqgis_import_empty_tf_dialog(self.iface, project)
		dialog.exec_()

	def increment_layer(self):
		dialog = tuflowqgis_increment_dialog(self.iface)
		dialog.exec_()
	
	def flow_trace(self):
		dialog = tuflowqgis_flowtrace_dialog(self.iface)
		dialog.exec_()
		
	def points_to_lines(self):
		#QMessageBox.information(self.iface.mainWindow(), "debug", "points to lines")
		dialog = tuflowqgis_line_from_points(self.iface)
		dialog.exec_()

	def split_MI(self):
		#QMessageBox.information(self.iface.mainWindow(), "debug", "points to lines")
		dialog = tuflowqgis_splitMI_dialog(self.iface)
		dialog.exec_()

	def split_MI_folder(self):
		#QMessageBox.information(self.iface.mainWindow(), "debug", "points to lines")
		QMessageBox.information( self.iface.mainWindow(),"debug", "starting" )
		dialog = tuflowqgis_splitMI_folder_dialog(self.iface)
		dialog.exec_()
		
#### external viewer interface
#	def results_1d_ext(self):
#		if self.dockOpened == False:
#			self.dock = TUFLOWifaceDock(self.iface)
#			self.iface.addDockWidget( Qt.RightDockWidgetArea, self.dock )
#			self.dockOpened = True
		
	def results_1d(self):
		#if self.resdockOpened == False:
		if self.dockOpened:
			#QMessageBox.information(self.iface.mainWindow(), "debug", "Show it")
			self.resdock.qgis_connect()
			self.resdock.show()
			self.resdock.layerChanged()
			
		else:
			self.dockOpened = True
			self.resdock = TuPlot(self.iface)
			self.iface.addDockWidget( Qt.RightDockWidgetArea, self.resdock)
		#else:
		#	if self.resdock.dockOpened:
		#		#QMessageBox.information(self.iface.mainWindow(), "debug", "Dock already open")
		#		#QMessageBox.information(self.iface.mainWindow(), "debug", "Show it")
		#		self.resdock.show()
		#	else:
		#		QMessageBox.information(self.iface.mainWindow(), "debug", "Dock not open??")

	def cleaning_res(res):
		QMessageBox.information(self.iface.mainWindow(), "debug", "Dock Closed")
		self.dockOpened = False
		
	def run_tuflow(self):
		project = QgsProject.instance()
		dialog = tuflowqgis_run_tf_simple_dialog(self.iface, project)
		dialog.exec_()
	
	def check_dependencies(self):
		#QMessageBox.critical(self.iface.mainWindow(), "Info", "Not yet implemented!")
		from tuflowqgis_library import check_python_lib
		error = check_python_lib(self.iface)
		if error <> None:
			QMessageBox.critical(self.iface.mainWindow(), "Error", "Not all dependencies installed.")
		else:
			QMessageBox.information(self.iface.mainWindow(), "Information", "All dependencies installed :)")

	def about_tuflowqgis(self):
		#QMessageBox.information(self.iface.mainWindow(), "About TUFLOW QGIS", 'This is a developmental version of the TUFLOW QGIS utitlity, build: '+build_vers)
		QMessageBox.information(self.iface.mainWindow(), "About TUFLOW QGIS", "This is a {0} version of the TUFLOW QGIS utitlity\nBuild: {1}".format(build_type,build_vers))

      # Added MJS 11/02  
	def import_check(self):
		project = QgsProject.instance()
		dialog = tuflowqgis_import_check_dialog(self.iface, project)
		dialog.exec_()
		
	def apply_check(self):
		error, message = tuflowqgis_apply_check_tf(self.iface)
		if error:
			QMessageBox.critical(self.iface.mainWindow(), "Error", message)
	
	def apply_check_cLayer(self):
		error, message = tuflowqgis_apply_check_tf_clayer(self.iface)
		if error:
			QMessageBox.critical(self.iface.mainWindow(), "Error", message)