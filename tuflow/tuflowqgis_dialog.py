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

from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
import logging

from tuflow.toc.toc import findAllRasterLyrs, findAllMeshLyrs, findAllVectorLyrs, tuflowqgis_find_layer

# import processing
from .tuflowqgis_library import *
from qgis.PyQt.QtWidgets import *
from qgis.utils import active_plugins, plugins
from datetime import datetime
import sys
import subprocess
import dateutil.parser
import json
try:
	from pathlib import Path
except ImportError:
	from pathlib_ import Path_ as Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from .tuflowqgis_library import interpolate, convertStrftimToTuviewftim, convertTuviewftimToStrftim, browse

from .compatibility_routines import is_qt6, QT_FONT_BOLD, QT_MESSAGE_BOX_YES, QT_INT, QT_ITEM_FLAG_ITEM_IS_SELECTABLE, QT_ALIGN_TOP, QT_MESSAGE_BOX_NO, QT_CUSTOM_CONTEXT_MENU, QT_ITEM_FLAG_ITEM_IS_EDITABLE, QT_UNCHECKED, QT_FONT_NORMAL, QT_RED, QT_CHECKED, QT_ABSTRACT_ITEM_VIEW_EXTENDED_SELECTION, QT_CURSOR_WAIT, QT_ITEM_FLAG_ITEM_IS_USER_CHECKABLE, QT_STRING, QT_BLACK, QT_ITEM_FLAG_ITEM_IS_ENABLED, QT_MESSAGE_BOX_CANCEL, QT_DOUBLE, QT_RICH_TEXT, QT_TIMESPEC_UTC

currentFolder = os.path.dirname(os.path.abspath(__file__))
spatial_database_option = True

if Qgis.QGIS_VERSION_INT < 31030:
	spatial_database_option = False


# ----------------------------------------------------------
#    tuflowqgis increment selected layer
# ----------------------------------------------------------

class OverWrite_or_IncrementName_Dialog(QDialog):

	def __init__(self, parent, db, layername):
		try:
			from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.gis import GPKG
		except ImportError:
			from .compatibility_routines import GPKG

		super().__init__(parent)
		self.db = db
		self.layername = layername
		self.parent = Path(db).parent
		self.setWindowTitle('File Exists')

		self.layout = QVBoxLayout()
		self.text = QLabel()
		self.text.setText('Superseded file already exists. Do you want to overwrite or increment name?')
		self.layout.addWidget(self.text)
		self.rb_overwrite = QRadioButton()
		self.rb_overwrite.setText('Overwrite file')
		self.rb_increment = QRadioButton()
		self.rb_increment.setText('Increment file name')
		self.button_group = QButtonGroup()
		self.button_group.addButton(self.rb_overwrite)
		self.button_group.addButton(self.rb_increment)
		self.layout.addWidget(self.rb_overwrite)
		self.layout.addWidget(self.rb_increment)
		self.rb_overwrite.setChecked(True)
		self.text_2 = QLabel()
		self.text_2.setText('Incremented layer name')
		self.layout.addWidget(self.text_2)
		self.error_text = QLabel()
		self.error_text.setTextFormat(QT_RICH_TEXT)
		self.error_text.setVisible(False)
		self.error_text.setText('File already exists')
		palette = self.error_text.palette()
		palette.setColor(QPalette.Foreground, QT_RED)
		font = self.error_text.font()
		font.setItalic(True)
		self.error_text.setPalette(palette)
		self.error_text.setFont(font)
		self.layout.addWidget(self.error_text)
		self.line_edit = QLineEdit()
		self.line_edit.setText(Path(db).name)
		self.line_edit.setEnabled(False)
		self.layout.addWidget(self.line_edit)
		self.button_layout = QHBoxLayout()
		self.pbOk = QPushButton()
		self.pbOk.setText('OK')
		self.pbCancel = QPushButton()
		self.pbCancel.setText('Cancel')
		self.button_layout.addWidget(self.pbOk)
		self.button_layout.addWidget(self.pbCancel)
		self.button_layout.insertStretch(0)
		self.layout.addLayout(self.button_layout)
		self.setLayout(self.layout)

		self.incremented_layer_name_changed(self.line_edit.text())

		self.pbOk.clicked.connect(self.accept)
		self.pbCancel.clicked.connect(self.reject)
		self.rb_overwrite.toggled.connect(self.rb_overwrite_toggled)
		self.line_edit.textChanged.connect(self.incremented_layer_name_changed)

	def rb_overwrite_toggled(self, checked):
		if checked:
			self.line_edit.setEnabled(False)
		else:
			self.line_edit.setEnabled(True)

	def incremented_layer_name_changed(self, text):
		name_ = self.parent / text.strip()
		if name_.suffix.lower() != '.gpkg':
			name_ = name_.with_suffix('.gpkg')
		if name_.exists():
			self.error_text.setVisible(True)
		else:
			self.error_text.setVisible(False)


class SuperSededRun:

	def __init__(self, in_db, in_lyrname, out_db, out_lyrname):
		self.in_db = in_db
		self.in_lyrname = in_lyrname
		self.out_db = out_db
		self.out_lyrname = out_lyrname
		self.errmsg = ''

	def run(self):
		try:
			from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.gis import ogr_copy
		except ImportError:
			from .compatibility_routines import ogr_copy

		result = True
		try:
			src = '{0} >> {1}'.format(self.in_db, self.in_lyrname)
			dst = '{0} >> {1}'.format(self.out_db, self.out_lyrname)
			ogr_copy(src, dst, explode_multipart=False, copy_associated_files=False)
		except Exception as e:
			result = False
			self.errmsg = str(e)

		return result

	def rename_layer(self, file_management_plugin, layer, target_name):
		result = False
		if file_management_plugin is None:
			self.errmsg = 'Issue retrieving file management plugin'
			return result

		try:
			file_management_plugin.rename_layer(layer, target_name)
			result = True
		except Exception as e:
			self.errmsg = str(e)

		return result


from .forms.ui_tuflowqgis_increment import *

class tuflowqgis_increment_dialog(QDialog, Ui_tuflowqgis_increment):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.layout().setAlignment(QT_ALIGN_TOP)
		self.setMinimumWidth(450)
		self.canvas = self.iface.mapCanvas()
		cLayer = self.canvas.currentLayer()
		fname = ''
		fpath = None
		self.fname = None
		self.curr_file = None
		self.isgpkg = False
		self.has_file_management_plugin = 'file_management' in active_plugins
		if not self.has_file_management_plugin:
			self.cbRenameLayer.setVisible(False)
			self.leRenameLayer.setVisible(False)

		self.twTables.setHorizontalHeaderLabels(["Layer", "Incremented Layer"])

		table_width = 414

		self.twTables.setColumnWidth(0, int(table_width / 2))
		self.twTables.setColumnWidth(1, int(table_width / 2))

		self.browseoutfile.clicked.connect(self.browse_outfile)
		self.btnBrowseDatabase.clicked.connect(lambda: browse(self, 'output database', "TUFLOW/increment_database",
												              "Spatial Database", "GPKG (*.gpkg *.GPKG)",
												              self.outfolder))
		self.pbDiscardDb_browse.clicked.connect(lambda: browse(self, 'output database', "TUFLOW/increment_discard_db",
			                                                   "Spatial Database", "GPKG (*.gpkg *.GPKG)",
			                                                   self.leDiscardedDb))

		self.sourcelayer.addItems([x.name() for x in QgsProject.instance().mapLayers().values()])
		if self.iface.activeLayer() is not None:
			self.sourcelayer.setCurrentText(self.iface.activeLayer().name())
		else:
			layer_tree = self.iface.layerTreeView()
			idxs = layer_tree.selectionModel().selectedIndexes()
			if idxs:
				idx = idxs[0]
				nd = layer_tree.index2node(idx)
				if nd.findLayers():
					self.sourcelayer.setCurrentText(nd.findLayers()[0].name())

		if self.sourcelayer.currentIndex() == -1:
			self.outfolder.setText('No layer currently selected!')
			self.outfilename.setText('No layer currently selected!')
			self.leDiscardedDb.setText('No layer currently selected!')
			self.leDiscardedLayer.setText('No layer currently selected!')
		else:
			last_database = QSettings().value('TUFLOW/increment_discard_db')
			if last_database:
				self.leDiscardedDb.setText(last_database)
			else:
				self.leDiscardedDb.setText('<new or existing database>')
			self.leDiscardedLayer.setText(self.sourcelayer.currentText())
			if self.has_file_management_plugin:
				self.leRenameLayer.setText(tuflowqgis_increment_fname(self.sourcelayer.currentText()))

		increment_db_method = QSettings().value('TUFLOW/increment_db_method')
		if increment_db_method is None:
			self.rbDatabaseLayer.setChecked(True)
		elif increment_db_method.lower() == 'increment layer only':
			self.rbDatabaseLayer.setChecked(True)
		elif increment_db_method.lower() == 'increment layer and preserve database':
			self.rbDatabaseDbLayer.setChecked(True)
		elif increment_db_method.lower() == 'save layer out into superseded folder':
			self.rbSaveLayerOut.setChecked(True)
		else:
			self.rbDatabaseLayer.setChecked(True)

		self.cbRenameLayer.setChecked(QSettings().value('TUFLOW/increment_rename_layer_cb') == 'True')
		self.cb_rename_layer_toggled(self.cbRenameLayer.isChecked())

		if cLayer:
			cName = cLayer.name()
		else:
			QMessageBox.information(self.iface.mainWindow(), "Information",
			                        "No layer is currently selected in the layer control")

		self.source_layer_changed()
		self.config_gui()
		self.config_ss_layer_gui()

		# ok / cancel buttons
		self.pbOk.clicked.connect(self.run)
		self.pbCancel.clicked.connect(self.reject)

		# signal so settings can be saved/remembered
		if self.has_file_management_plugin:
			self.cbRenameLayer.toggled.connect(self.cb_rename_layer_toggled)
		self.buttonGroup_2.buttonToggled.connect(self.rbSSLayerToggled)
		self.leDiscardedDb.textChanged.connect(self.discharded_db_changed)

		# source layer changed signal
		self.sourcelayer.currentIndexChanged.connect(self.source_layer_changed)

		# gui needs to be changed signals
		self.buttonGroup_2.buttonToggled.connect(self.config_gui)
		self.buttonGroup_3.buttonToggled.connect(self.config_ss_layer_gui)

		self._d = {}

	def gpkg_or_not_gui_config(self):
		if self.isgpkg:
			self.label_2.setText('Output Database')
			self.label.setText('Output Layer Name')
			self.label_5.setVisible(True)
			self.gbSpatialDatabaseOptions.setVisible(True)
			self.btnBrowseDatabase.setVisible(True)
			self.browseoutfile.setVisible(False)
		else:
			self.label_2.setText('Output Folder')
			self.label.setText('Output File Name')
			self.label_5.setVisible(False)
			self.gbSpatialDatabaseOptions.setVisible(False)
			self.btnBrowseDatabase.setVisible(False)
			self.browseoutfile.setVisible(True)

	def increment_layer_only_set_visible(self, visible):
		if not self.isgpkg:
			return
		visible = not self.rbDatabaseDbLayer.isChecked()
		self.label.setVisible(visible)
		self.outfilename.setVisible(visible)

	def preserve_db_set_visible(self, visible):
		self.twTables.setVisible(visible)

	def ss_layer_set_visible(self, visible):
		self.gbSSSettings.setVisible(visible)
		self.cbMoveToSS.setVisible(not visible)
		self.rbRemoveSource.setVisible(not visible)
		self.rbKeepSource.setVisible(not visible)
		self.outfolder.setVisible(not visible)
		if visible:
			self.label_2.setVisible(not visible)
			self.label.setVisible(not visible)
			self.outfilename.setVisible(not visible)
			self.browseoutfile.setVisible(not visible)
			self.btnBrowseDatabase.setVisible(not visible)

		self.gbSSSettings.setMinimumWidth(self.gbSSSettings.width())
		self.gbSSSettings.adjustSize()

		self.gbSpatialDatabaseOptions.setMinimumWidth(self.gbSpatialDatabaseOptions.width())
		self.gbSpatialDatabaseOptions.adjustSize()

	def config_gui(self):
		self.gpkg_or_not_gui_config()
		self.increment_layer_only_set_visible(self.isgpkg and self.rbDatabaseLayer.isChecked())
		self.preserve_db_set_visible(self.isgpkg and self.rbDatabaseDbLayer.isChecked())
		self.ss_layer_set_visible(self.isgpkg and self.rbSaveLayerOut.isChecked())

		self.adjustSize()

	def config_ss_layer_gui(self):
		if self.rbAutoSSLayer.isChecked():
			self.leDiscardedDb.setEnabled(False)
			self.pbDiscardDb_browse.setEnabled(False)
			self.leDiscardedLayer.setEnabled(False)
			# self.cbRenameLayer.setEnabled(True)
			# self.leRenameLayer.setEnabled(self.cbRenameLayer.isChecked())
		else:
			self.leDiscardedDb.setEnabled(True)
			self.pbDiscardDb_browse.setEnabled(True)
			self.leDiscardedLayer.setEnabled(True)
			# self.cbRenameLayer.setEnabled(False)
			# self.leRenameLayer.setEnabled(False)

	def set_outputs(self, layer):
		if layer is None:
			return

		if self.isgpkg:
			pattern = r'\d{2,3}[A-z]?(?=(?:_[PLR]$|$))'
			db, lyrname = re.split(r'\|layername=', layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE)
			new_lyrname = tuflowqgis_increment_fname(lyrname)
			new_lyrname = new_lyrname.split('|')[0]
			# if re.findall(pattern, new_lyrname, flags=re.IGNORECASE):
			# 	vers_num = re.findall(pattern, new_lyrname, flags=re.IGNORECASE)[0]
			# 	if re.findall(pattern, Path(db).stem, flags=re.IGNORECASE):
			# 		new_db = re.sub(pattern, vers_num, Path(db).stem, flags=re.IGNORECASE)
			# 	else:
			# 		new_db = tuflowqgis_increment_fname(Path(db).stem)
			# else:
			# 	new_db = new_lyrname
			# db = str(Path(db).parent / '{0}{1}'.format(new_db, Path(db).suffix))
		else:
			# name_ = re.split(r'\|layername=', layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE)[0]
			ds = Path(layer.dataProvider().dataSourceUri().split('|')[0])
			db = str(ds.parent)
			lyrname = ds.name

		self.outfolder.setText(db)
		self.outfilename.setText(tuflowqgis_increment_fname(lyrname))
		self.leRenameLayer.setText(tuflowqgis_increment_fname(lyrname))
		self.leDiscardedLayer.setText(lyrname)

	def source_layer_changed(self):
		layer = tuflowqgis_find_layer(self.sourcelayer.currentText())
		self.check_if_layer_is_db(layer)
		self.set_outputs(layer)
		if self.isgpkg:
			self.populateTableNames(layer)
		self.config_gui()

	def cb_rename_layer_toggled(self, checked):
		QSettings().setValue('TUFLOW/increment_rename_layer_cb', str(checked))

		if checked:
			self.leRenameLayer.setEnabled(True)
		else:
			self.leRenameLayer.setEnabled(False)

	def rbSSLayerToggled(self):
		QSettings().setValue('TUFLOW/increment_db_method', self.buttonGroup_2.checkedButton().text())

	def discharded_db_changed(self):
		QSettings().setValue('TUFLOW/increment_discard_db', self.leDiscardedDb.text())

	def check_if_layer_is_db(self, layer):
		self.isgpkg = False
		if layer is not None:
			dp = layer.dataProvider()
			ds = dp.dataSourceUri()
			self.isgpkg = bool(re.findall(re.escape(r'.gpkg|layername='), ds, flags=re.IGNORECASE))

	def populateTableNames(self, layer=None):
		try:
			from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.gis import GPKG  # req. python 3.9+
		except ImportError:
			from .compatibility_routines import GPKG

		self.twTables.setRowCount(0)

		if not self.isgpkg:
			return

		if layer is None:
			return

		db, lyrname = re.split(r'\|layername=', layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE)
		lyrname = lyrname.split('|')[0]
		tablenames = GPKG(db).layers()

		self.twTables.setRowCount(len(tablenames))
		for i, table in enumerate(tablenames):
			item = QTableWidgetItem()
			item.setCheckState(QT_CHECKED)
			item.setText(table)
			self.twTables.setItem(i, 0, item)

			if table == lyrname:
				item = QTableWidgetItem()
				item.setText(tuflowqgis_increment_fname(table))
				self.twTables.setItem(i, 1, item)

	def browse_outfile(self):
		outfolder = unicode(self.outfolder.displayText()).strip()
		newname = QFileDialog.getSaveFileName(self, "Output Shapefile", outfolder, "*.shp *.SHP")
		if len(newname) > 0:
			fpath, fname = os.path.split(newname[0])
			self.outfolder.setText(self.translate(fpath))
			outfname = tuflowqgis_increment_fname(fname)
			self.outfilename.setText(self.translate(outfname))

	def translate(self, string):
		return re.sub(r'[\\/]', re.escape(os.sep), string)

	def incrementedDatabaseTableNames(self):

		incrementedNames = {}
		for i in range(self.twTables.rowCount()):
			item1 = self.twTables.item(i, 0)
			item2 = self.twTables.item(i, 1)
			if item1.checkState() == QT_CHECKED:
				if item2 and item2.text().strip():
					incrementedNames[item1.text()] = item2.text().strip()
				else:
					incrementedNames[item1.text()] = item1.text()

		return incrementedNames

	def setup_ss_run(self):
		try:
			from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.gis import GPKG
		except ImportError:
			from .compatibility_routines import GPKG

		# find input layer
		layer = tuflowqgis_find_layer(self.sourcelayer.currentText())
		if layer is None:
			QMessageBox.critical(self, 'Increment Layer', 'Source layer no longer exists in workspace')
			return
		db, lyrname = re.split(re.escape(r"|layername="), layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE)
		lyrname = lyrname.split('|')[0]

		# if auto supersede - output will be to ss folder in same folder as input. Output gpkg will be the same as layer name.
		if self.rbAutoSSLayer.isChecked():
			out_db = (Path(db).parent / 'ss' / lyrname).with_suffix('.gpkg')
			out_lyrname = lyrname

			# check if exists - if so, give user opportunity to give a unique name
			if Path(out_db).exists() and out_lyrname.lower() in [x.lower() for x in GPKG(out_db).layers()]:
				dialog = OverWrite_or_IncrementName_Dialog(self, out_db, out_lyrname)  # custom dialog for this
				dialog.exec()
				if not dialog.result():  # cancelled
					return
				if dialog.rb_increment.isChecked():  # user has changed name
					out_db = out_db.with_name(dialog.line_edit.text().strip())
					out_lyrname = out_db.stem
		else:  # user defined location and layer name
			out_db = self.leDiscardedDb.text()
			out_lyrname = self.leDiscardedLayer.text()
			if Path(out_db).suffix.lower() != '.gpkg':
				QMessageBox.critical(self, 'Incement Layer', 'Output database must be .gpkg')
				return

			# check if exists
			if Path(out_db).exists() and out_lyrname.lower() in [x.lower() for x in GPKG(out_db).layers()]:
				res = QMessageBox.warning(self, 'Layer already exists',
				                          'Layer already exists. Do you want to overwrite the existing layer?',
				                          QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO | QT_MESSAGE_BOX_CANCEL)
				if res != QT_MESSAGE_BOX_YES:
					return

		return SuperSededRun(str(db), lyrname, str(out_db), out_lyrname)

	def run(self):
		try:
			from .convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.gis import GPKG
		except ImportError:
			from .compatibility_routines import GPKG
		# ss layer
		if self.isgpkg and self.rbSaveLayerOut.isChecked():
			ss_run = self.setup_ss_run()
			if not ss_run:
				return

			res = ss_run.run()
			if not res:
				QMessageBox.critical(self, 'Increment Layer', ss_run.errmsg)
				return

			if self.has_file_management_plugin and self.cbRenameLayer.isChecked():
				res = ss_run.rename_layer(plugins.get('file_management'),
				                          tuflowqgis_find_layer(self.sourcelayer.currentText()),
				                          self.leRenameLayer.text().strip())
				if not res:
					QMessageBox.critical(self, 'Increment Layer', ss_run.errmsg)
					return

			self.accept()
			return

		# collect information
		layername = unicode(self.sourcelayer.currentText())
		if layername == self.iface.activeLayer().name():
			layer = self.iface.activeLayer()
		else:
			layer = tuflowqgis_find_layer(layername)
		dp = layer.dataProvider()
		ds = dp.dataSourceUri()
		outname = unicode(self.outfilename.displayText()).strip()
		if self.isgpkg:
			filename_old, layer_old = re.split(re.escape(r"|layername="), ds, flags=re.IGNORECASE)
		else:
			filename_old = os.path.basename(ds.split('|')[0])
			layer_old = None
		if outname[-4:].upper() != '.SHP' and not self.isgpkg:
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
			override_existing = QMessageBox.question(self, "Increment Layer", 'File already exists. Do you want to replace the existing file?',
			                                         QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO | QT_MESSAGE_BOX_CANCEL)
			if override_existing == QT_MESSAGE_BOX_NO or override_existing == QT_MESSAGE_BOX_CANCEL:
				return

		try:
			if self.isgpkg and outname in GPKG(outfolder).layers():
				override_existing = QMessageBox.question(self, "Increment Layer", '{0} already exists within output GPKG database. Do you want to replace the existing layer?'.format(outname),
				                                         QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO | QT_MESSAGE_BOX_CANCEL)
				if override_existing != QT_MESSAGE_BOX_YES:
					return
		except Exception as e:
			print('Error determining if layer exists in GPKG database.')
			print(e)
		
		# duplicate layer with incremented name
		incrementDatabase = False
		incrementDatabaseLayers = []
		if self.isgpkg:
			incrementDatabase = True if self.rbDatabaseDbLayer.isChecked() else False
			incrementDatabaseLayers = self.incrementedDatabaseTableNames()
			message = duplicate_database(self.iface, layer, outfolder, outname, incrementDatabase, incrementDatabaseLayers)
			savename = '{0}|layername={1}'.format(outfolder, outname)
		else:
			message = tuflowqgis_duplicate_file(self.iface, layer, savename, False)
		if message != None:
			QMessageBox.critical(self.iface.mainWindow(), "Duplicating File", message)
			return

		# change existing layer datasource to incremented layer
		if self.isgpkg and incrementDatabase:
			for lyrname, lyr in QgsProject.instance().mapLayers().items():
				if re.findall(re.escape(r".gpkg|layername="), lyr.dataProvider().dataSourceUri(), re.IGNORECASE):
					tablename = re.split(re.escape(r".gpkg|layername="), lyr.dataProvider().dataSourceUri(), flags=re.IGNORECASE)[1]
					if tablename in incrementDatabaseLayers:
						newtablesource = '{0}|layername={1}'.format(outfolder, incrementDatabaseLayers[tablename])
						changeDataSource(self.iface, lyr, newtablesource, True)
		else:
			changeDataSource(self.iface, layer, savename, self.isgpkg)
			QgsProject.instance().reloadAllLayers()

		self._d.clear()
		self._d['incrementDatabase'] = incrementDatabase
		self._d['incrementDatabaseLayers'] = incrementDatabaseLayers
		self._d['filename_old'] = filename_old
		self._d['layer_old'] = layer_old
		self._d['outfolder'] = outfolder
		self._d['layer'] = layer

		self.timer = QTimer()
		self.timer.setSingleShot(True)
		self.timer.setInterval(300)
		self.timer.timeout.connect(self.move_to_ss_folder)
		self.timer.start()
		self.accept()

	def move_to_ss_folder(self):
		incrementDatabase = self._d['incrementDatabase']
		incrementDatabaseLayers = self._d['incrementDatabaseLayers']
		filename_old = self._d['filename_old']
		layer_old = self._d['layer_old']
		outfolder = self._d['outfolder']
		layer = self._d['layer']

		# check if need to move to SS folder
		layers_not_copied = []
		layers_copied_orig = []
		layers_copied_new = []
		if self.cbMoveToSS.isChecked():
			if self.isgpkg and not incrementDatabase and len(incrementDatabaseLayers) > 1:
				pass
			else:
				if self.isgpkg:
					ssFolder = os.path.join(os.path.dirname(outfolder), 'ss')
				else:
					ssFolder = os.path.join(outfolder, 'ss')
				if not os.path.exists(ssFolder):
					os.mkdir(ssFolder)
				dp = layer.dataProvider()
				ds = dp.dataSourceUri()
				if self.isgpkg:
					files = [filename_old]
				else:
					name = os.path.splitext(filename_old)[0]
					search = os.path.join(outfolder, name) + '.*'
					files = glob.glob(search)
				messages = []

				for file in files:
					try:
						os.rename(file, os.path.join(ssFolder, os.path.basename(file)))
						layers_copied_orig.append(file)
						layers_copied_new.append(os.path.join(ssFolder, os.path.basename(file)))
					except Exception as e:
						layers_not_copied.append(file)
						messages.append(e)
				if layers_not_copied:
					for i, file in enumerate(layers_copied_new):  # copy back since some have failed
						os.rename(file, layers_copied_orig[i])
					QMessageBox.warning(self, "Copy Failed", "Warning could not copy the following layers to superseded folder:\n"
															 "{0}\n\n"
															 "{1}".format('\n'.join(layers_not_copied), messages[0]))
		
		# check if need to keep layer in workspace
		if self.rbKeepSource.isChecked():  # remove layer
			# work out where the old layer is
			if self.cbMoveToSS.isChecked():
				if self.isgpkg:
					name = layer_old
					if incrementDatabase and not layers_not_copied:
						oldFile = '{0}|layername={1}'.format(os.path.join(ssFolder, os.path.basename(filename_old)), layer_old)
					else:
						oldFile = '{0}|layername={1}'.format(filename_old, layer_old)
				else:
					name = os.path.splitext(filename_old)[0]
					if not layers_not_copied:
						oldFile = os.path.join(ssFolder, filename_old)
					else:
						oldFile = os.path.join(outfolder, filename_old)
			else:
				if self.isgpkg:
					oldFile = '{0}|layername={1}'.format(filename_old, layer_old)
					name = layer_old
				else:
					name = os.path.splitext(filename_old)[0]
					oldFile = os.path.join(outfolder, filename_old)
			# add and style old layer
			oldLayer = self.iface.addVectorLayer(oldFile, name, "ogr")
			copyLayerStyle(self.iface, layer, oldLayer)

		self._d.clear()


# ----------------------------------------------------------
#    tuflowqgis import empty tuflow files
# ----------------------------------------------------------
from .forms.ui_tuflowqgis_import_empties import *


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
		if is_qt6:
			self.teToolTip.setTabStopDistance(16.)
		else:
			self.teToolTip.setTabStopWidth(16)

		self.sizes = self.splitter.sizes()
		if not showToolTip:
			self.sizes[1] = 20

		# find out which tuflow engine to use
		self.engine = 'classic'  # set a default - other option is 'flexible mesh'
		self.tfsettings = TF_Settings()
		error, message = self.tfsettings.Load()
		if self.tfsettings.project_settings.engine:
			self.engine = self.tfsettings.project_settings.engine
			
		engine = self.tfsettings.combined.engine
		self.parent_folder_name = 'TUFLOWFV' if engine == 'flexible mesh' else 'TUFLOW'

		self.browsedir.clicked.connect(lambda: browse(self, 'existing folder', 'TUFLOW/empty_directory',
		                                              'Empty Directory', lineEdit=self.emptydir, action=self.dirChanged))
		self.emptydir.editingFinished.connect(self.dirChanged)
		self.pbShowToolTip.clicked.connect(self.toggleToolTip)
		self.pbHideToolTip.clicked.connect(self.toggleToolTip)
		self.emptyType.itemSelectionChanged.connect(self.updateToolTip)
		self.pbOk.clicked.connect(self.run)
		self.pbCancel.clicked.connect(self.reject)
		self.btnDatabaseBrowse.clicked.connect(lambda: browse(self, 'output database', "TUFLOW/import_empty_database",
													          "Spatial Database", "gpkg (*.gpkg *.GPKG)",
													          self.leDatabaseBrowse))
		self.pbSaveToProject.clicked.connect(lambda: self.saveDir('project'))
		self.pbSaveToGlobal.clicked.connect(lambda: self.saveDir('global'))

		self.cbConvertToDb.clicked.connect(self.save_settings_convert_to_database)
		self.rbDatabaseSeparate.clicked.connect(self.save_settings_to_separate)
		self.rbDatabaseGrouped.clicked.connect(self.save_settings_group_geometries)
		self.rbDatabaseOne.clicked.connect(self.save_settings_group_together)
		self.leDatabaseBrowse.textChanged.connect(self.save_settings_database)

		if self.tfsettings.combined.empty_dir:
			self.emptydir.setText(self.tfsettings.combined.empty_dir.replace('/', os.sep).replace('\\', os.sep))
		elif self.tfsettings.combined.base_dir:
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
			self.emptydir.setText(emptydir.replace('/', os.sep).replace('\\', os.sep))
			#self.emptydir.setText(os.path.join(self.tfsettings.combined.base_dir, self.parent_folder_name, "model", "gis", "empty"))
		else:
			self.emptydir.setText("ERROR - Project not loaded")
			
		# load empty types
		self.dirChanged()

		kart_version = get_kart_version()
		if kart_version > -1:
			self.cb_import_into_kart.setEnabled(True)
			self.le_kart_repo.setEnabled(True)
			self.cb_import_into_kart.setChecked(QSettings().value('TUFLOW/import_empty/kart_cb', 'False') == 'True')
			kart_repo = QSettings().value('TUFLOW/import_empty/kart_repo', '')
			if not kart_repo:
				kart_repo = kart_repo_from_empty_folder(self.emptydir.text())
			self.le_kart_repo.setText(kart_repo)
			self.cb_import_into_kart.toggled.connect(lambda state: QSettings().setValue('TUFLOW/import_empty/kart_cb', str(state)))
			self.le_kart_repo.textEdited.connect(lambda text: QSettings().setValue('TUFLOW/import_empty/kart_repo', text))
		else:
			self.cb_import_into_kart.setEnabled(False)
			self.cb_import_into_kart.setChecked(False)
			self.le_kart_repo.setEnabled(False)
			self.le_kart_repo.setText('')

		self.gbSpatialDatabaseOptions.setVisible(spatial_database_option)
		w = self.width()
		h = self.height() - self.gbSpatialDatabaseOptions.sizeHint().height()
		self.resize(w, h)

		b = True if QSettings().value('TUFLOW/import_empty/convert_to_dbase', False) in ['true', 'True', True] else False
		self.cbConvertToDb.setChecked(b)

		db_setting = QSettings().value('TUFLOW/import_empty/db_output_option', 'separate')
		if db_setting == 'geometries':
			self.rbDatabaseGrouped.setChecked(True)
		elif db_setting == 'grouped':
			self.rbDatabaseOne.setChecked(True)
		else:
			self.rbDatabaseSeparate.setChecked(True)
		db_path = QSettings().value('TUFLOW/import_empty/db_path', '<Existing or New Database>')
		self.leDatabaseBrowse.setText(db_path)

	def save_settings_convert_to_database(self):
		QSettings().setValue('TUFLOW/import_empty/convert_to_dbase', self.cbConvertToDb.isChecked())

	def save_settings_to_separate(self):
		if self.rbDatabaseSeparate.isChecked():
			QSettings().setValue('TUFLOW/import_empty/db_output_option', 'separate')

	def save_settings_group_geometries(self):
		if self.rbDatabaseGrouped.isChecked():
			QSettings().setValue('TUFLOW/import_empty/db_output_option', 'geometries')

	def save_settings_group_together(self):
		if self.rbDatabaseOne.isChecked():
			QSettings().setValue('TUFLOW/import_empty/db_output_option', 'grouped')

	def save_settings_database(self):
		QSettings().setValue('TUFLOW/import_empty/db_path', self.leDatabaseBrowse.text())
		
	def saveDir(self, type_):
		if type_ == 'project':
			self.tfsettings.project_settings.empty_dir = self.emptydir.text()
			self.tfsettings.Combine()
			self.tfsettings.Save_Project()
		elif type_ == 'global':
			self.tfsettings.global_settings.empty_dir = self.emptydir.text()
			self.tfsettings.Save_Global()

	def toggleToolTip(self):

		showToolTip = not self.teToolTip.isVisible()
		self.teToolTip.setVisible(showToolTip)
		self.pbShowToolTip.setVisible(not showToolTip)
		self.pbHideToolTip.setVisible(showToolTip)
		dif = self.width() - sum(self.splitter.sizes())
		if not showToolTip:
			self.sizes = self.splitter.sizes()
			self.splitter.setSizes([self.sizes[0], 0])
			w = self.sizes[0] + dif
		else:
			self.splitter.setSizes(self.sizes)
			w = sum(self.sizes) + dif
		self.splitter.refresh()
		h = self.height()
		self.adjustSize()
		# w = self.width()
		self.resize(w, h)
		
	def updateToolTip(self):
		self.teToolTip.clear()
		self.teToolTip.setFontUnderline(True)
		self.teToolTip.setTextColor(QColor(QT_BLACK))
		self.teToolTip.setFontFamily('MS Shell Dlg 2')
		self.teToolTip.setFontPointSize(18)
		self.teToolTip.setFontWeight(QT_FONT_BOLD)
		self.teToolTip.append('Tool Tip')
		self.teToolTip.append('\n')
		items = self.emptyType.selectedItems()
		for item in items:
			tooltip = findToolTip(item.text(), self.engine)
			if tooltip['location'] is not None:
				self.teToolTip.setFontUnderline(False)
				self.teToolTip.setTextColor(QColor(QT_BLACK))
				self.teToolTip.setFontFamily('Courier New')
				self.teToolTip.setFontPointSize(13)
				self.teToolTip.setFontWeight(QT_FONT_NORMAL)
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
				self.teToolTip.setTextColor(QColor(QT_BLACK))
				self.teToolTip.setFontFamily('MS Shell Dlg 2')
				self.teToolTip.setFontPointSize(10)
				self.teToolTip.setFontWeight(QT_FONT_NORMAL)
				self.teToolTip.append(tooltip['description'])
				self.teToolTip.append('\n')
			if tooltip['wiki link'] is not None:
				self.teToolTip.setFontUnderline(False)
				self.teToolTip.setTextColor(QColor(QT_BLACK))
				self.teToolTip.setFontFamily('MS Shell Dlg 2')
				self.teToolTip.setFontPointSize(10)
				self.teToolTip.setFontWeight(QT_FONT_BOLD)
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
				self.teToolTip.setTextColor(QColor(QT_BLACK))
				self.teToolTip.setFontFamily('MS Shell Dlg 2')
				self.teToolTip.setFontPointSize(10)
				self.teToolTip.setFontWeight(QT_FONT_BOLD)
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
			self.emptydir.setText(newname.replace('/', os.sep).replace('\\', os.sep))
			
			# load empty types
			self.emptyType.clear()
			if self.emptydir.text() == "ERROR - Project not loaded":
				self.emptyType.addItem('No empty directory')
			elif not os.path.exists(self.emptydir.text()):
				self.emptyType.addItem('Empty directory not valid')
			else:
				exts = ['shp', 'gpkg']
				files = []
				for ext in exts:
					search_string = '{0}{1}*.{2}'.format(self.emptydir.text(), os.path.sep, ext)
					f = glob.glob(search_string)
					if not f:
						search_string = '{0}{1}*.{2}'.format(self.emptydir.text(), os.path.sep, ext.upper())
						f = glob.glob(search_string)
					files += f
				empty_list = []
				for file in files:
					if len(file.split('_empty')) < 2:
						continue
					empty_type = os.path.basename(file.split('_empty')[0])
					if empty_type not in empty_list:
						empty_list.append(empty_type)
						self.emptyType.addItem(empty_type)

	def dirChanged(self):
		self.emptyType.clear()
		if self.emptydir.text() == "ERROR - Project not loaded":
			self.emptyType.addItem('No empty directory')
		elif not os.path.exists(self.emptydir.text()):
			self.emptyType.addItem('Empty directory not valid')
		else:
			exts = ['shp', 'gpkg']
			files = []
			for ext in exts:
				p = Path(self.emptydir.text())
				if not p.exists():
					continue
				f = list(p.glob('*.{0}'.format(ext)))
				f.extend(list(p.glob('*.{0}'.format(ext.upper()))))
				files.extend(f)
			empty_list = []
			for file in files:
				file = str(file)
				if len(file.split('_empty')) < 2:
					continue
				empty_type = Path(file).stem.split('_empty')[0]
				if '_pts' in os.path.basename(file):
					empty_type = '{0}_pts'.format(empty_type)
				if empty_type not in empty_list:
					empty_list.append(empty_type)
					self.emptyType.addItem(empty_type)
			if not empty_list:
				self.emptyType.addItem('No empty files in directory')
	
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

		# spatial database
		databaseOption = 'separate'
		databaseLoc = ''
		if self.rbDatabaseGrouped.isChecked():
			databaseOption = 'grouped'
		elif self.rbDatabaseOne.isChecked():
			databaseOption = 'one'
			databaseLoc = self.leDatabaseBrowse.text() if os.path.splitext(self.leDatabaseBrowse.text().lower())[1] == '.gpkg' else ''
		convert = True if self.cbConvertToDb.isChecked() else False

		# run create dir script
		if self.cb_import_into_kart.isChecked():
			import_empty = ImportEmpty(self.emptydir.text(), self.txtRunID.text(), databaseOption, databaseLoc, convert)
			for empty_type in empty_types:
				if points:
					import_empty.add(empty_type, '_P')
				if lines:
					import_empty.add(empty_type, '_L')
				if regions:
					import_empty.add(empty_type, '_R')

			invalid_layers = import_empty.validate_kart_layers(self.le_kart_repo.text())
			if invalid_layers and isinstance(invalid_layers, str):
				QMessageBox.warning(self.iface.mainWindow(), 'Import Empty', invalid_layers)
				return
			if invalid_layers:
				# question = QMessageBox.question(self.iface.mainWindow(), 'Import Empty',
				#                                 'The following layers already exist in the Kart repository.\n{0}\n\n'
				#                                 'Do you want to override existing layers?'.format('\n'.join(invalid_layers)),
				#                                 QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_CANCEL)
				# if question == QT_MESSAGE_BOX_CANCEL:
				# 	return
				QMessageBox.warning(self.iface.mainWindow(), 'Import Empty', 'The following layers already exist in the Kart repository.\n{0}\n\n'.format('\n'.join(invalid_layers)))
				return
			message = import_empty.import_to_kart(kart_executable(), self.le_kart_repo.text())
			if message:
				QMessageBox.warning(self.iface.mainWindow(), 'Import Empty', message)
				return
			for empty_file in import_empty.empty_files:
				uri = '{0}|layername={1}'.format(kart_gpkg(self.le_kart_repo.text()), empty_file.out_name)
				layer = QgsVectorLayer(uri, empty_file.out_name, 'ogr')
				if layer.isValid():
					QgsProject.instance().addMapLayer(layer)
		else:
			message = tuflowqgis_import_empty_tf(self.iface, basedir, runID, empty_types, points, lines, regions, self, databaseOption, databaseLoc, convert)
		#message = tuflowqgis_create_tf_dir(self.iface, crs, basedir)
		if message == 'pass':
			pass
		elif message is not None:
			if message != 1:
				QMessageBox.critical(self.iface.mainWindow(), "Importing {0} Empty File(s)".format(self.parent_folder_name), message)
		else:
			self.accept()

# ----------------------------------------------------------
#    tuflowqgis Run TUFLOW (Simple)
# ----------------------------------------------------------
from .forms.ui_tuflowqgis_run_tf_simple import *


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

		self.exefolder = QDir().homePath()
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
		# self.buttonBox.accepted.connect(self.run)
		self.pbCancel.clicked.connect(self.reject)
		self.pbOk.clicked.connect(self.run)
		self.pbKillRun.clicked.connect(self.kill_run)

		files = glob.glob(unicode(self.runfolder)+os.path.sep+"*.tcf")
		self.tcfin=''
		if (len(files) > 0):
			files.sort(key=os.path.getmtime, reverse=True)
			self.tcfin = files[0]
		if (len(self.tcfin)>3):
			self.tcf.setText(self.tcfin)

		self.prog_inc = 0
		self.progressText.hide()
		self.pbKillRun.hide()
		self._kill_run = False
		self._running = False

	def accept(self):
		if self._running:
			self.run_tuflow.terminate()
			self._running = False
		super().accept()

	def reject(self):
		if self._running:
			self.run_tuflow.terminate()
			self._running = False
		super().reject()

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
		inFileName = inFileName[0]
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

	def on_error(self, err):
		self._running = False
		QMessageBox.critical(self, 'Run TUFLOW', err)

	def on_finish(self, text):
		self._running = False
		dlg = QDialog(parent=self)
		dlg.setWindowTitle('TUFLOW')
		layout = QHBoxLayout()
		html_edit = QTextBrowser()
		html_edit.setHtml(self.text2html(text))
		layout.addWidget(html_edit)
		dlg.setLayout(layout)
		dlg.resize(800, 600)
		dlg.exec()

	def update(self, finished):
		if not finished:
			self.prog_inc += 1
			if self.prog_inc > 5:
				self.prog_inc = 1
			text = 'TUFLOW Running' + ' .' * self.prog_inc
			self.progressText.setText(text)
		else:
			self.progressText.hide()
			self.pbKillRun.hide()
			self.pbOk.setEnabled(True)
		return self._kill_run

	def text2html(self, text):
		text_ = text.replace('\r\n', '<p>')
		text_ = text_.replace(' ', '&nbsp;')
		text_ = '<tt>{0}</tt>'.format(text_)
		return text_

	def kill_run(self):
		self._kill_run = True

	def run(self):
		tcf = unicode(self.tcf.displayText()).strip()
		tfexe = unicode(self.TUFLOW_exe.displayText()).strip()
		capture_output = self.cbCaptureOutput.isChecked()
		if capture_output:
			self.progressText.setText('TUFLOW Running')
			self.progressText.show()
			self.pbKillRun.show()
		self.prog_inc = 0
		self._kill_run = False
		self.run_tuflow = RunTuflow(tfexe, tcf, capture_output, self.update)
		self.run_tuflow.finished.connect(self.on_finish)
		self.run_tuflow.error.connect(self.on_error)
		self.run_tuflow.run()
		if capture_output:
			self.pbOk.setEnabled(False)
			self._running = True

# ----------------------------------------------------------
#    tuflowqgis points to lines
# ----------------------------------------------------------
from .forms.ui_tuflowqgis_line_from_points import *

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
		fields = {0 : QgsField("z", QT_DOUBLE), 1 : QgsField("dz", QT_DOUBLE),
				  2 : QgsField("width", QT_DOUBLE), 3 : QgsField("Options", QT_STRING) }
	
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
from .forms.ui_tuflowqgis_configure_tuflow_project import *


class tuflowqgis_configure_tf_dialog(QDialog, Ui_tuflowqgis_configure_tf):
	def __init__(self, iface, project, parent=None):
		QDialog.__init__(self, parent)
		self.iface = iface
		self.setupUi(self)
		self.canvas = self.iface.mapCanvas()
		self.setWindowTitle('Configure / Create TUFLOW Project')
		cLayer = self.canvas.currentLayer()
		self.tfsettings = TF_Settings()
		self.crs = None
		fname = ''

		error, message = self.tfsettings.Load()
		if error:
			QMessageBox.information( self.iface.mainWindow(),"Error", message)
		
		#set fields
		if self.tfsettings.project_settings.base_dir:
			self.outdir.setText(self.translate(self.tfsettings.project_settings.base_dir))
		elif self.tfsettings.global_settings.base_dir:
			self.outdir.setText(self.translate(self.tfsettings.global_settings.base_dir))
		else:
			self.outdir.setText("Not Yet Set")
			self.outdir.setText("Not Yet Set")
		
		if self.tfsettings.project_settings.tf_exe:
			self.TUFLOW_exe.setText(self.translate(self.tfsettings.project_settings.tf_exe))
		elif self.tfsettings.global_settings.tf_exe:
			self.TUFLOW_exe.setText(self.translate(self.tfsettings.global_settings.tf_exe))
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
		# self.buttonBox.accepted.connect(self.run)
		self.pbCancel.clicked.connect(self.reject)
		self.pbOk.clicked.connect(self.run)

		self.gbGisFormat.setVisible(spatial_database_option)

	def translate(self, string):
		return re.sub(r'[\\/]', re.escape(os.sep), string)

	def browse_outdir(self):
		#newname = QFileDialog.getExistingDirectory(None, QString.fromLocal8Bit("Output Directory"))
		newname = QFileDialog.getExistingDirectory(None, "Output Directory")
		if newname != None:
			#self.outdir.setText(QString(newname))
			self.outdir.setText(self.translate(newname))
	
	def select_CRS(self):
		# projSelector = QgsProjectionSelectionWidget(self)
		# projSelector.selectCrs()
		dlg = QgsProjectionSelectionDialog(self)
		dlg.setWindowTitle('Select CRS')
		crs = None
		if self.form_crsID.text() and re.findall(r'\d+', self.form_crsID.text()):
			try:
				crs = QgsCoordinateReferenceSystem.fromEpsgId(int(re.findall(r'\d+', self.form_crsID.text())[0]))
				if not crs.isValid():
					crs = None
			except ValueError:
				pass
		if crs is None:
			crs = QgsProject.instance().crs()
		self.crs = crs
		dlg.setCrs(crs)
		if dlg.exec():
			self.crs = dlg.crs()
			self.crsDesc.setText(self.crs.description())
			self.form_crsID.setText(self.crs.authid())
		else:
			return
		# try:
		# 	authid = projSelector.crs().authid()
		# 	description = projSelector.crs().description()
		# 	self.crs = projSelector.crs()
		# 	success = projSelector.crs()
		# 	if not success:
		# 		self.crs = None
		# 	else:
		# 		self.crsDesc.setText(description)
		# 		self.form_crsID.setText(authid)
		# except:
		# 	self.crs = None
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
		self.TUFLOW_exe.setText(self.translate(inFileName))
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
		basedir = self.outdir.displayText().strip().strip('\\/')
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
				                          QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO | QT_MESSAGE_BOX_CANCEL)
				if fv == QT_MESSAGE_BOX_CANCEL:
					return
				elif fv == QT_MESSAGE_BOX_YES:
					engine = 'flexible mesh'
		
		#Save Project Settings
		self.tfsettings.project_settings.CRS_ID = tf_prj
		self.tfsettings.project_settings.tf_exe = tfexe
		self.tfsettings.project_settings.base_dir = basedir
		self.tfsettings.project_settings.engine = engine
		self.tfsettings.project_settings.tutorial = tutorial
		tf_folder = 'TUFLOW' if engine == 'classic' else 'TUFLOWFV'
		if re.findall(r'TUFLOW\\?$', basedir, flags=re.IGNORECASE):
			empty_dir = os.path.join(basedir, 'model', 'gis', 'empty')
		else:
			empty_dir = os.path.join(basedir, tf_folder, 'model', 'gis', 'empty')

		self.tfsettings.project_settings.empty_dir = empty_dir
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
			self.tfsettings.global_settings.empty_dir = empty_dir
			error, message = self.tfsettings.Save_Global()
			if error:
				QMessageBox.information( self.iface.mainWindow(),"Error", "Error Saving Global Settings. Message: "+message)
			#else:
			#	QMessageBox.information( self.iface.mainWindow(),"Information", "Global Settings Saved")
		crs = QgsCoordinateReferenceSystem()
		crs.createFromString(tf_prj)
		if self.cbCreate.isChecked():
			gisFormat = 'GPKG' if self.rbGPKG.isChecked() else 'SHP'
			message = tuflowqgis_create_tf_dir(self, crs, basedir, engine, tutorial, gisFormat)
			if message == 'user cancelled':
				return
			if message != None:
				QMessageBox.critical(self.iface.mainWindow(), "Creating TUFLOW Directory ", message)
				return
		
		if self.cbRun.isChecked():
			ext = '.fvc' if engine == 'flexible mesh' else '.tcf'
			runfile = os.path.join(basedir, parent_folder_name, "runs", "Create_Empties{0}".format(ext))
			if not os.path.exists(runfile):
				gisFormat = 'GPKG' if self.rbGPKG.isChecked() else 'SHP'
				create_empty_tcf(runfile, gisFormat, tutorial, engine, crs)
			#QMessageBox.information(self.iface.mainWindow(), "Running {0}".format(parent_folder_name),"Starting simulation: "+runfile+"\n Executable: "+tfexe)
			message = run_tuflow(self.iface, tfexe, runfile)
			if message != None:
				QMessageBox.critical(self.iface.mainWindow(), "Running {0} ".format(parent_folder_name), message)
				return

		self.accept()
		
# ----------------------------------------------------------
#    tuflowqgis flow trace
# ----------------------------------------------------------

from .forms.ui_tuflowqgis_flowtrace import *

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
from .forms.ui_tuflowqgis_import_check import *


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
from .forms.ui_tuflowqgis_arr2016 import *
from tuflow.ARR2016.arr_cc_dlg import ARRCCDialog
from tuflow.ARR2016.ARR_to_TUFLOW import ARR_to_TUFLOW


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
		default = None
		if layer is not None:
			for f in layer.fields():
				#QMessageBox.information(self.iface.mainWindow(), "Debug", '{0}'.format(f.name()))
				self.comboBox_CatchID.addItem(f.name())
				if f.name().lower() in ['name', 'id']:
					default = f.name()
		if default is not None:
			self.comboBox_CatchID.setCurrentText(default)
				
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

		self.cc_scen = {}
		
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
		self.cbPNIL.clicked.connect(self.probabilityNeutralLosses)
		self.cbCompleteStorm.clicked.connect(self.toggleCompleteStorm)

		self.pbCCEdit.clicked.connect(self.editCC)

		self.sizeDialog()

	def editCC(self):
		dlg = ARRCCDialog(self, self.cc_scen)
		if dlg.exec():
			self.cc_scen = dlg.value
			self.lwCCScen.clear()
			for key, val in self.cc_scen.items():
				self.lwCCScen.addItem(key)

	def sizeDialog(self):
		"""Resize dialog to fit contents"""
		self.gbTemporalPatterns.setCollapsed(True)
		w = max(self.groupBox_SAEP.sizeHint().width(), self.groupBox_RAEP.sizeHint().width(), self.groupBox_FAEP.sizeHint().width()) \
		    + self.groupBox_Durations.sizeHint().width() \
		    + max(self.groupBox_CC.sizeHint().width(), self.groupBox_output.sizeHint().width(), self.groupBox_ARF.sizeHint().width()) \
		    + max(self.gbTemporalPatterns.sizeHint().width(), self.groupBox_5.sizeHint().width(),  + self.groupBox_IL.sizeHint().width()) \
		    + (6*9 + 8*6 + 15)
		w = max(w, self.width())
		h = self.height()
		self.resize(w, h)

	def probabilityNeutralLosses(self):
		if self.cbPNIL.isChecked():
			self.cbCompleteStorm.setChecked(False)

	def toggleCompleteStorm(self):
		if self.cbCompleteStorm.isChecked():
			self.cbPNIL.setChecked(False)

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
			if Path(Path(lastFolder).drive).exists():
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
		self.cc = 'true' if self.lwCCScen.count() > 0 else 'false'
		self.cc_param = json.dumps(self.cc_scen)
			
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
			QApplication.setOverrideCursor(QT_CURSOR_WAIT)
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
		import processing
		
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
		elif ilMethod == 'Log-Interpolate to zero':
			ilMethod = 'interpolate_log'
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
		elif ilMethod == 'Interpolate pre-burst':
			ilMethod = 'interpolate_linear_preburst'
		elif ilMethod == 'Log-Interpolate pre-burst':
			ilMethod = 'interpolate_log_preburst'

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

		# global continuing loss
		globalCL = 'false'
		if self.cbGlobalCL.isChecked():
			globalCL = 'true'
		
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

		parameters = {'INPUT': layer, 'TARGET_CRS': 'epsg:4326', 'OUTPUT': 'memory:Reprojected'}
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
		# if self.cbCompleteStorm.isChecked():
		if complete_storm:
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
				if preburst_pattern_tp == 'design burst':
					preburst_pattern_tp = 'design_burst'
				if self.cboDurTP.currentIndex() == 0:
					preburst_proportional = 'true'
					preburst_pattern_dur = f'{self.sbProportion.value():.2f}'
				else:
					preburst_pattern_dur = self.cboDurTP.currentText()

		# LIMB data
		limb = 'none'
		if self.cbLIMB.isChecked():
			limb = self.cboLIMB.currentText()

		# additional temporal patterns (from the same region)
		all_point_tp = str(self.cbUseAllPointTP.isChecked())
		add_areal_tp = str(self.sbNoAdditionalTP.value()) if self.cbAddArealTP.isChecked() else '0'
		
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
						'-nonstnd', self.nonstnd_list, '-area', area_list[i], '-format', format, '-catchment_no', str(i),
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
			            '-preburst_dur_proportional', preburst_proportional,
			            '-global_continuing_loss', globalCL,
			            '-limb', limb,
						'-all_point_tp', all_point_tp, '-add_areal_tp', add_areal_tp,
						'-cc', self.cc, '-cc_param', self.cc_param,
						'-cc_use_old_il', str(self.cb_cc_il_old_method.isChecked())]
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
		# try:
		errors = ''
		for i, sys_args in enumerate(self.sys_args):
			if i > 0:
				self.updated.emit(i)
			#if i == 0:
			#	logfile = open(self.logfile, 'wb')
			#else:
			#	logfile = open(self.logfile, 'ab')

			try:
				ARR_to_TUFLOW(sys_args)
			except Exception as e:
				errors += '{0} - {1}'.format(self.name_list[i], e)

				# CREATE_NO_WINDOW = 0x08000000  # suppresses python console window
				# error = False
				# if sys.platform == 'win32':
				# 	try:  # for some reason (in QGIS2 at least) creationsflags didn't work on all computers
				#
				# 		proc = subprocess.Popen(sys_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
				# 		                        creationflags=CREATE_NO_WINDOW)
				# 		out, err = proc.communicate()
				# 		#logfile.write(out)
				# 		#logfile.write(err)
				# 		#logfile.close()
				# 		if err:
				# 			if type(err) is bytes:
				# 				err = err.decode('utf-8')
				# 			errors += '{0} - {1}'.format(self.name_list[i], err)
				# 	except Exception as e:
				# 		try:
				# 			proc = subprocess.Popen(sys_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				# 			out, err = proc.communicate()
				# 			# #logfile.write(out)
				# 			# #logfile.write(err)
				# 			# #logfile.close()
				# 			if err:
				# 				if type(err) is bytes:
				# 					err = err.decode('utf-8')
				# 				errors += '{0} - {1}'.format(self.name_list[i], err)
				# 		except Exception as e:
				# 			error = 'Error with subprocess call'
				# else:  # linux and mac
				# 	try:
				# 		proc = subprocess.Popen(sys_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				# 		out, err = proc.communicate()
				# 		#logfile.write(out)
				# 		#logfile.write(err)
				# 		#logfile.close()
				# 		if err:
				# 			if type(err) is bytes:
				# 				err = err.decode('utf-8')
				# 			errors += '{0} - {1}'.format(self.name_list[i], err)
				# 	except:
				# 		error = 'Error with subprocess call'
		# except Exception as e:
		# 	if type(e) is bytes:
		# 		e = err.decode('utf-8')
		# 	errors += e
		
		self.finished.emit(errors)
		

# ----------------------------------------------------------
#    tuflowqgis insert tuflow attributes
# ----------------------------------------------------------
from .forms.ui_tuflowqgis_insert_tuflow_attributes import *
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
		if self.tfsettings.combined.empty_dir:
			self.emptydir.setText(self.tfsettings.combined.empty_dir.replace('/', os.sep).replace('\\', os.sep))
		elif self.tfsettings.combined.base_dir:
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
			self.emptydir.setText(emptydir.replace('/', os.sep).replace('\\', os.sep))
		else:
			self.emptydir.setText("ERROR - Project not loaded")
			
		# load empty types
		self.dirChanged()
		# self.emptyType.clear()
		# if self.emptydir.text() == "ERROR - Project not loaded":
		# 	self.emptyType.addItem('No empty directory')
		# elif not os.path.exists(self.emptydir.text()):
		# 	self.emptyType.addItem('Empty directory not valid')
		# else:
		# 	search_string = '{0}{1}*.shp'.format(self.emptydir.text(), os.path.sep)
		# 	files = glob.glob(search_string)
		# 	if not files:
		# 		search_string = '{0}{1}*.SHP'.format(self.emptydir.text(), os.path.sep)
		# 		files = glob.glob(search_string)
		# 	empty_list = []
		# 	for file in files:
		# 		if len(file.split('_empty')) < 2:
		# 			continue
		# 		empty_type = os.path.basename(file.split('_empty')[0])
		# 		if empty_type not in empty_list:
		# 			empty_list.append(empty_type)
		# 	empty_list = sorted(empty_list)
		# 	self.emptyType.addItems(empty_list)
									
		# self.browsedir.clicked.connect(lambda: self.browse_empty_dir(unicode(self.emptydir.displayText()).strip()))
		self.browsedir.clicked.connect(lambda: browse(self, 'existing folder', 'TUFLOW/empty_directory',
		                                              'Empty Directory', lineEdit=self.emptydir, action=self.dirChanged))
		self.emptydir.editingFinished.connect(self.dirChanged)
		self.pbOk.clicked.connect(self.run)
		self.pbCancel.clicked.connect(self.reject)
		self.browseDatabase.clicked.connect(lambda: browse(self, 'output database', "TUFLOW/import_empty_database",
													      "Spatial Database", "gpkg (*.gpkg *.GPKG)",
													      self.leDatabase))
		self.pbSaveToProject.clicked.connect(lambda: self.saveDir('project'))
		self.pbSaveToGlobal.clicked.connect(lambda: self.saveDir('global'))

		self.label.setVisible(spatial_database_option)
		self.leDatabase.setVisible(spatial_database_option)
		self.browseDatabase.setVisible(spatial_database_option)
		w = self.width()
		h = self.height() - self.label.sizeHint().height() - self.leDatabase.sizeHint().height() - \
		    self.browseDatabase.sizeHint().height()
		self.resize(w, h)

	def saveDir(self, type_):
		if type_ == 'project':
			self.tfsettings.project_settings.empty_dir = self.emptydir.text()
			self.tfsettings.Combine()
			self.tfsettings.Save_Project()
		elif type_ == 'global':
			self.tfsettings.global_settings.empty_dir = self.emptydir.text()
			self.tfsettings.Save_Global()

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
		self.emptyType.clear()
		if self.emptydir.text() == "ERROR - Project not loaded":
			self.emptyType.addItem('No empty directory')
		elif not os.path.exists(self.emptydir.text()):
			self.emptyType.addItem('Empty directory not valid')
		else:
			exts = ['shp', 'gpkg']
			files = []
			for ext in exts:
				p = Path(self.emptydir.text())
				if not p.exists():
					continue
				f = list(p.glob('*.{0}'.format(ext)))
				f.extend(list(p.glob('*.{0}'.format(ext.upper()))))
				files.extend(f)
			empty_list = []
			for file in files:
				file = str(file)
				if len(file.split('_empty')) < 2:
					continue
				empty_type = os.path.basename(file.split('_empty')[0])
				if '_pts' in os.path.basename(file):
					empty_type = '{0}_pts'.format(empty_type)
				if empty_type not in empty_list:
					empty_list.append(empty_type)
					self.emptyType.addItem(empty_type)
			if not empty_list:
				self.emptyType.addItem('No empty files in directory')
	
	def run(self):
		runID = unicode(self.txtRunID.displayText()).strip()
		basedir = unicode(self.emptydir.displayText()).strip()
		template = unicode(self.emptyType.currentText())
		
		inputFile = unicode(self.comboBox_inputLayer.currentText())
		inputLayer = tuflowqgis_find_layer(inputFile)
		lenFields = len(inputLayer.fields())

		output_dbase = self.leDatabase.text() if not re.findall(r'^<.*>$', self.leDatabase.text()) and self.leDatabase.text() else None
		
		# run insert tuflow attributes script
		message = tuflowqgis_insert_tf_attributes(self.iface, inputLayer, basedir, runID, template, lenFields, self,
		                                          output_dbase)
		if message is not None:
			if message != 1:
				QMessageBox.critical(self.iface.mainWindow(), "Importing TUFLOW Empty File(s)", message)
		elif message == 'pass':
			pass
		else:
			self.accept()


# ----------------------------------------------------------
#    tuflowqgis tuplot axis editor
# ----------------------------------------------------------
from .forms.ui_tuflowqgis_tuplotAxisEditor import *


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
from .forms.ui_tuflowqgis_tuplotAxisLabels import *


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
from .forms.ui_tuflowqgis_scenarioSelection import *


class tuflowqgis_scenarioSelection_dialog(QDialog, Ui_scenarioSelection):
	def __init__(self, iface, tcf, scenarios, events=()):
		QDialog.__init__(self)
		self.setupUi(self)
		self.scenario_lw.setStyleSheet("QListWidget:!active { selection-color: white; selection-background-color: #1383DC }")
		self.event_lw.setStyleSheet("QListWidget:!active { selection-color: white; selection-background-color: #1383DC }")
		self.iface = iface
		self.tcf = tcf
		self.scenarios = scenarios
		self.events = events
		self.status = 0

		if not scenarios:
			self.scenario_lw_label.hide()
			self.scenario_lw.hide()
			self.selectAll_button_scenarios.hide()
		else:
			for scenario in self.scenarios:
				self.scenario_lw.addItem(scenario)
		if not events:
			self.event_lw_label.hide()
			self.event_lw.hide()
			self.selectAll_button_events.hide()
		else:
			for event in self.events:
				self.event_lw.addItem(event)
		
		self.ok_button.clicked.connect(self.run)
		self.cancel_button.clicked.connect(self.cancel)
		self.selectAll_button_scenarios.clicked.connect(self.selectAll_scenarios)
		self.selectAll_button_events.clicked.connect(self.selectAll_events)

		self.options = LoadTcfOptions()
		self.init_cond()
		self.setOptionsVisible(False)
		self.rbGrouped.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup1(self.buttonGroup))
		self.rbUngrouped.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup1(self.buttonGroup))
		self.rbRasterLoad.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup2(self.buttonGroup_2))
		self.rbRasterNoLoad.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup2(self.buttonGroup_2))
		self.rbRasterLoadInvisible.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup2(self.buttonGroup_2))
		self.rbOrderAlpha.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup3(self.buttonGroup_3))
		self.rbOrderCF.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup3(self.buttonGroup_3))
		self.rbOrderCFRev.clicked.connect(lambda: loadTCFOptionsMessageBox_signal_rbgroup3(self.buttonGroup_3))

	def init_cond(self):
		self.rbGrouped.setChecked(True) if self.options.grouped else self.rbUngrouped.setChecked(True)
		if self.options.load_raster_method == 'yes':
			self.rbRasterLoad.setChecked(True)
		elif self.options.load_raster_method == 'no':
			self.rbRasterNoLoad.setChecked(True)
		elif self.options.load_raster_method == 'invisible':
			self.rbRasterLoadInvisible.setChecked(True)
		else:
			self.rbRasterLoadInvisible.setChecked(True)

		if self.options.order_method == 'control_file':
			self.rbOrderCF.setChecked(True)
		elif self.options.order_method == 'control_file_group_rasters':
			self.rbOrderCFRev.setChecked(True)
		else:
			self.rbOrderAlpha.setChecked(True)

	def setOptionsVisible(self, b):
		widget = [self.label, self.rbGrouped, self.rbUngrouped, self.label_2, self.rbRasterLoad, self.rbRasterNoLoad,
				  self.rbRasterLoadInvisible, self.label_3, self.rbOrderAlpha, self.rbOrderCF, self.rbOrderCFRev]
		for w in widget:
			w.setVisible(b)

	def cancel(self):
		self.status = 0
		self.reject()
	
	def selectAll_scenarios(self):
		for i in range(self.scenario_lw.count()):
			item = self.scenario_lw.item(i)
			item.setSelected(True)

	def selectAll_events(self):
		for i in range(self.event_lw.count()):
			item = self.event_lw.item(i)
			item.setSelected(True)
	
	def run(self):
		self.scenarios = []
		self.events = []
		for i in range(self.scenario_lw.count()):
			item = self.scenario_lw.item(i)
			if item.isSelected():
				self.scenarios.append(item.text())
		for i in range(self.event_lw.count()):
			item = self.event_lw.item(i)
			if item.isSelected():
				self.events.append(item.text())
		self.status = 1
		self.accept()  # destroy dialog window


# ----------------------------------------------------------
#    tuflowqgis event selection
# ----------------------------------------------------------
from .forms.ui_tuflowqgis_eventSelection import *


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
from .forms.ui_tuflowqgis_meshSelection import *


class tuflowqgis_meshSelection_dialog(QDialog, Ui_meshSelection):
	def __init__(self, iface, meshes, dialog_text=None):
		QDialog.__init__(self)
		self.setupUi(self)
		self.iface = iface
		self.meshes = meshes
		self.selectedMesh = None
		if dialog_text is not None:
			self.setWindowTitle(dialog_text)
		
		for mesh in self.meshes:
			self.mesh_lw.addItem(mesh.name())
		
		self.ok_button.clicked.connect(self.run)
		self.cancel_button.clicked.connect(self.cancel)
	
	def cancel(self):
		self.reject()

	def run(self):
		selection = self.mesh_lw.selectedItems()
		if selection:
			if self.mesh_lw.selectionMode() == QT_ABSTRACT_ITEM_VIEW_EXTENDED_SELECTION:
				self.selectedMesh = [x.text() for x in selection]
			else:
				self.selectedMesh = selection[0].text()
			self.accept()  # destroy dialog window
		else:
			QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'Please select a result layer to save style.')


# ----------------------------------------------------------
#    tuflowqgis Output Zone selection
# ----------------------------------------------------------
from .forms.ui_tuflowqgis_outputZoneSelection import *


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
#    tuflowqgis Output Zone selection
# ----------------------------------------------------------
from .forms.ui_tuflowqgis_outputZoneSelection import *


class tuflowqgis_outputSelection_dialog(QDialog, Ui_outputZoneSelection):
	def __init__(self, iface, outputs):
		QDialog.__init__(self)
		self.iface = iface
		self.setupUi(self)
		self.setWindowTitle('Select Result(s) to Add')
		self.outputs = []

		self.listWidget.addItems(outputs)

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
				self.outputs.append(item.text())
		self.accept()  # destroy dialog window


# ----------------------------------------------------------
#    tuView Options Dialog
# ----------------------------------------------------------
from .forms.ui_tuflowqgis_TuOptionsDialog import *


class TuOptionsDialog(QDialog, Ui_TuViewOptions):
	def __init__(self, TuOptions):
		qv = Qgis.QGIS_VERSION_INT

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
		#d = QDate(self.tuOptions.zeroTime.year, self.tuOptions.zeroTime.month, self.tuOptions.zeroTime.day)
		#t = QTime(self.tuOptions.zeroTime.hour, self.tuOptions.zeroTime.minute, self.tuOptions.zeroTime.second)
		#dt = QDateTime(d, t)
		dt = dt2qdt(self.tuOptions.zeroTime, QT_TIMESPEC_UTC)
		if qv >= 31300:
			dt.setTimeSpec(self.tuOptions.timeSpec)
			dt = dt.toTimeSpec(QT_TIMESPEC_UTC)

		if qv >= 31600:
			self.tpLabel.setVisible(True)
			self.dteZeroDate.setDateTime(dt)
			# self.dteZeroDate.setVisible(False)
			# self.zeroDateLabel.setVisible(False)
		else:
			# self.dteZerodate.setVisible(True)
			# self.zeroDateLabel.setVisible(True)
			self.dteZeroDate.setDateTime(dt)
			self.tpLabel.setVisible(False)
		
		# date format
		self.leDateFormat.setText(convertStrftimToTuviewftim(self.tuOptions.dateFormat))
		
		# date format preview
		self.date = datetime.now()
		self.datePreview.setText(self.tuOptions._dateFormat.format(self.date))
		
		# x axis label rotation
		self.sbXAxisLabelRotation.setValue(int(self.tuOptions.xAxisLabelRotation))
			
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
		elif self.tuOptions.defaultLayout == "narrow":
			self.rbDefaultLayoutNarrowView.setChecked(True)
		else:
			self.rbDeafultLayoutPreviousState.setChecked(True)

		self.colourButtonPlotBackground.setAllowOpacity(True)
		if self.tuOptions.plotBackgroundColour == '#e5e5e5':
			self.cbPlotBackgroudGrey.setChecked(True)
		elif self.tuOptions.plotBackgroundColour == '#ffffff':
			self.cbPlotBackgroudWhite.setChecked(True)
		else:
			self.cbPlotBackgroudCustom.setChecked(True)
			color = QColor(mplcolor_to_qcolor(self.tuOptions.plotBackgroundColour))
			self.colourButtonPlotBackground.setColor(color)

		# default font size
		self.sbDefaultFontSize.setValue(self.tuOptions.defaultFontSize)

		# icon size
		self.cboIconSize.setCurrentText(str(self.tuOptions.iconSize))

		# debug - check files
		if self.tuOptions.writeMeshIntersects:
			self.cbMeshIntCheck.setChecked(True)
		else:
			self.cbMeshIntCheck.setChecked(False)
		self.cbParticleDebug.setChecked(self.tuOptions.particlesWriteDebugInfo)

		if self.tuOptions.tcfLoadMethod == 'scenario_selection':
			self.rbByScenSelection.setChecked(True)
		elif self.tuOptions.tcfLoadMethod == 'result_selection':
			self.rbByResSelection.setChecked(True)
		else:
			self.rbByResSelection.setChecked(True)

		self.cbPlotInactiveAreas.setChecked(self.tuOptions.plotInactiveAreas)

		# curtain vector
		self.sbScale.setValue(self.tuOptions.curtain_vector_scale)
		if self.tuOptions.curtain_vector_scale_units is None:
			self.cboScaleUnits.setCurrentText('default')
		else:
			self.cboScaleUnits.setCurrentText(self.tuOptions.curtain_vector_scale_units)
		if self.tuOptions.curtain_vector_units is None:
			self.cboUnits.setCurrentText('default')
		else:
			self.cboUnits.setCurrentText(self.tuOptions.curtain_vector_units)
		self.sbWidth.setValue(self.tuOptions.curtain_vector_width)
		self.sbHeadWidth.setValue(self.tuOptions.curtain_vector_head_width)
		self.sbHeadLength.setValue(self.tuOptions.curtain_vector_head_length)
		self.sbHorizontalFactor.setValue(self.tuOptions.curtain_vector_horizontal_factor)
		self.sbVertVelFactor.setValue(self.tuOptions.curtain_vector_vertical_factor)


		# Signals
		self.leDateFormat.textChanged.connect(self.updatePreview)
		self.rbDefaultLayoutPlotView.clicked.connect(lambda: self.saveDefaultLayout("plot"))
		self.rbDefaultLayoutNarrowView.clicked.connect(lambda: self.saveDefaultLayout("narrow"))
		self.rbDeafultLayoutPreviousState.clicked.connect(lambda: self.saveDefaultLayout("previous_state"))
		self.sbDefaultFontSize.valueChanged.connect(self.saveDefaultFontSize)
		self.buttonBox.rejected.connect(self.cancel)
		self.buttonBox.accepted.connect(self.run)
		self.colourButtonPlotBackground.colorChanged.connect(lambda e: self.cbPlotBackgroudCustom.setChecked(True))
		self.rbByScenSelection.clicked.connect(lambda e: self.tcfLoadMethodChanged('scenario_selection'))
		self.rbByResSelection.clicked.connect(lambda e: self.tcfLoadMethodChanged('result_selection'))
		self.cbPlotInactiveAreas.clicked.connect(self.cbPlotInactiveAreasToggled)
		# curtain vector
		self.pbVectorTVDefaults.clicked.connect(self.curtain_vector_set_tuflow_viewer_defaults)
		self.pbVectorMPLDefaults.clicked.connect(self.curtain_vector_set_mpl_defaults)
		self.sbScale.valueChanged.connect(self.curtain_vector_scale_changed)
		self.cboScaleUnits.currentTextChanged.connect(self.curtain_vector_scale_units_changed)
		self.cboUnits.currentTextChanged.connect(self.curtain_vector_units_changed)
		self.sbWidth.valueChanged.connect(self.curtain_vector_width_changed)
		self.sbHeadWidth.valueChanged.connect(self.curtain_vector_head_width_changed)
		self.sbHeadLength.valueChanged.connect(self.curtain_vector_head_length_changed)
		self.sbHorizontalFactor.valueChanged.connect(self.curtain_vector_horizontal_factor_changed)
		self.sbVertVelFactor.valueChanged.connect(self.vertical_velocity_factor_changed)
		# copy mesh
		self.cb_copy_mesh.setChecked(self.tuOptions.copy_mesh)
		self.cb_show_mesh_copy_dlg.setChecked(self.tuOptions.show_copy_mesh_dlg)
		self.cb_del_copied_mesh.setChecked(self.tuOptions.del_copied_res)
		self.cb_copy_mesh.toggled.connect(self.cb_copy_mesh_toggled)
		self.cb_show_mesh_copy_dlg.toggled.connect(self.cb_show_mesh_copy_dlg_toggled)
		self.cb_del_copied_mesh.toggled.connect(self.cb_del_copied_mesh_toggled)
		self.btn_del_all_cache_res.clicked.connect(self.del_all_cache_res)

	def cb_copy_mesh_toggled(self, e):
		self.tuOptions.copy_mesh = e
		QSettings().setValue('TUFLOW/tuview_copy_mesh', self.tuOptions.copy_mesh)

	def cb_show_mesh_copy_dlg_toggled(self, e):
		self.tuOptions.show_copy_mesh_dlg = e
		QSettings().setValue('TUFLOW/tuview_show_copy_mesh_dlg', self.tuOptions.show_copy_mesh_dlg)

	def cb_del_copied_mesh_toggled(self, e):
		self.tuOptions.del_copied_res = e
		QSettings().setValue('TUFLOW/tuview_del_copied_res', self.tuOptions.del_copied_res)

	def del_all_cache_res(self):
		from .tuflowqgis_tuviewer.tmp_result import TmpResult
		from .gui import Logging
		folders = TmpResult.clear_cache()
		if folders:
			folders = '\n'.join([str(x) for x in folders])
			Logging.error('Errors occurred deleting some copied results', 'The following folders could not be deleted:\n{0}'.format(folders))
		else:
			Logging.info('Successfully Deleted Copied Results')

	def curtain_vector_set_tuflow_viewer_defaults(self):
		self.sbScale.setValue(0.005)
		self.cboScaleUnits.setCurrentText('dots')
		self.cboUnits.setCurrentText('dots')
		self.sbWidth.setValue(0.5)
		self.sbHeadWidth.setValue(10.)
		self.sbHeadLength.setValue(10.)
		self.sbHorizontalFactor.setValue(1.)
		self.sbVertVelFactor.setValue(1.)

	def curtain_vector_set_mpl_defaults(self):
		self.sbScale.setValue(-1.)
		self.cboScaleUnits.setCurrentText('default')
		self.cboUnits.setCurrentText('default')
		self.sbWidth.setValue(-1.)
		self.sbHeadWidth.setValue(-1.)
		self.sbHeadLength.setValue(-1.)
		self.sbHorizontalFactor.setValue(1.)
		self.sbVertVelFactor.setValue(1.)

	def curtain_vector_scale_changed(self, e):
		self.tuOptions.curtain_vector_scale = self.sbScale.value()
		QSettings().setValue("TUFLOW/tuview_curtain_vector_scale", self.sbScale.value())

	def curtain_vector_scale_units_changed(self, e):
		if self.cboScaleUnits.currentText() == 'default':
			self.tuOptions.curtain_vector_scale_units = None
		else:
			self.tuOptions.curtain_vector_scale_units = self.cboScaleUnits.currentText()
		QSettings().setValue("TUFLOW/tuview_curtain_vector_scale_units", self.cboScaleUnits.currentText())

	def curtain_vector_units_changed(self, e):
		if self.cboUnits.currentText() == 'default':
			self.tuOptions.curtain_vector_units = None
		else:
			self.tuOptions.curtain_vector_units = self.cboUnits.currentText()
		QSettings().setValue("TUFLOW/tuview_curtain_vector_units", self.cboUnits.currentText())

	def curtain_vector_width_changed(self, e):
		self.tuOptions.curtain_vector_width = self.sbWidth.value()
		QSettings().setValue("TUFLOW/tuview_curtain_vector_width", self.sbWidth.value())

	def curtain_vector_head_width_changed(self, e):
		self.tuOptions.curtain_vector_head_width = self.sbHeadWidth.value()
		QSettings().setValue("TUFLOW/tuview_curtain_vector_head_width", self.sbHeadWidth.value())

	def curtain_vector_head_length_changed(self, e):
		self.tuOptions.curtain_vector_head_length = self.sbHeadLength.value()
		QSettings().setValue("TUFLOW/tuview_curtain_vector_head_length", self.sbHeadLength.value())

	def curtain_vector_horizontal_factor_changed(self, e):
		self.tuOptions.curtain_vector_horizontal_factor = self.sbHorizontalFactor.value()
		QSettings().setValue("TUFLOW/tuview_curtain_vector_horizontal_factor", self.sbHorizontalFactor.value())

	def vertical_velocity_factor_changed(self, e):
		self.tuOptions.curtain_vector_vertical_factor = self.sbVertVelFactor.value()
		QSettings().setValue("TUFLOW/tuview_curtain_vector_vertical_factor", self.sbVertVelFactor.value())

	def cbPlotInactiveAreasToggled(self, e):
		self.tuOptions.plotInactiveAreas = bool(self.cbPlotInactiveAreas.isChecked())
		QSettings().setValue("TUFLOW/tuview_plot_inactive_areas", self.tuOptions.plotInactiveAreas)

	def tcfLoadMethodChanged(self, tcf_load_method):
		self.tuOptions.tcfLoadMethod = tcf_load_method
		QSettings().setValue("TUFLOW/tuview_tcf_load_method", tcf_load_method)

	def saveDefaultLayout(self, layoutType):
		QSettings().setValue("TUFLOW/tuview_defaultlayout", layoutType)

	def saveDefaultFontSize(self, value):
		size = self.sbDefaultFontSize.value()
		QSettings().setValue("TUFLOW/tuview_defaultfontsize", size)

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
		qv = Qgis.QGIS_VERSION_INT
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
		#d = [self.dteZeroDate.date().year(), self.dteZeroDate.date().month(), self.dteZeroDate.date().day()]
		#t = [self.dteZeroDate.time().hour(), self.dteZeroDate.time().minute(), self.dteZeroDate.time().second()]
		#self.tuOptions.zeroTime = datetime(d[0], d[1], d[2], t[0], t[1], t[2])
		self.tuOptions.zeroTime = qdt2dt(self.dteZeroDate)
		if 31300 <= qv < 31600:
			self.tuOptions.zeroTime = datetime2timespec(self.tuOptions.zeroTime, QT_TIMESPEC_UTC, self.tuOptions.timeSpec)
		else:
			self.tuOptions.zeroTime = datetime2timespec(self.tuOptions.zeroTime, QT_TIMESPEC_UTC, QT_TIMESPEC_UTC)
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
		elif self.rbDefaultLayoutNarrowView.isChecked():
			self.tuOptions.defaultLayout = "narrow"
		else:
			self.tuOptions.defaultLayout = "previous_state"

		if self.cbPlotBackgroudGrey.isChecked():
			self.tuOptions.plotBackgroundColour = '#e5e5e5'
		elif self.cbPlotBackgroudWhite.isChecked():
			self.tuOptions.plotBackgroundColour = '#ffffff'
		else:
			color = self.colourButtonPlotBackground.color()
			self.tuOptions.plotBackgroundColour = qcolor_to_mplcolor(color.name(QColor.HexArgb))
		settings.setValue("TUFLOW/tuview_plotbackgroundcolour", self.tuOptions.plotBackgroundColour)

		# debug - check files
		if self.cbMeshIntCheck.isChecked():
			self.tuOptions.writeMeshIntersects = True
		else:
			self.tuOptions.writeMeshIntersects = False
		self.tuOptions.particlesWriteDebugInfo = self.cbParticleDebug.isChecked()

		# icon size
		self.tuOptions.iconSize = int(self.cboIconSize.currentText())
		settings.setValue("TUFLOW/tuview_iconsize", self.tuOptions.iconSize)

		# font size
		self.tuOptions.defaultFontSize = int(self.sbDefaultFontSize.value())


# ----------------------------------------------------------
#    tuView Selected Elements Dialog
# ----------------------------------------------------------
from .forms.ui_tuflowqgis_selectedElements import *


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
		self.elementList.setContextMenuPolicy(QT_CUSTOM_CONTEXT_MENU)
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
					pattern = re.escape(r'.gpkg|layername=')
					i = 0
					if layer.dataProvider().name() != 'memory':
						if re.findall(pattern, layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE):
							i = 0
					for feature in layer.getFeatures():
						if feature.attributes()[i].strip() in selIds:
							layer.select(feature.id())
		
		return True
	

# ----------------------------------------------------------
#    Auto Plot and Export Dialog
# ----------------------------------------------------------
from .forms.ui_BatchExportPlotDialog import *


class TuBatchPlotExportDialog(QDialog, Ui_BatchPlotExport):
	def __init__(self, TuView, **kwargs):
		QDialog.__init__(self)
		self.setupUi(self)
		self.tuView = TuView
		self.iface = TuView.iface
		self.project = TuView.project
		self.canvas = TuView.canvas
		folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
		addIcon = QgsApplication.getThemeIcon('mActionAdd.svg')
		# removeIcon = QgsApplication.getThemeIcon('symbologyRemove.svg')
		self.btnBrowse.setIcon(folderIcon)
		self.btnAddRes.setIcon(addIcon)
		# self.btnRemRes.setIcon(removeIcon)
		self.populateGISLayers()
		self.populateNameAttributes()
		self.populateResultMesh()
		self.populateResultTypes()
		self.populateTimeSteps()
		self.populateImageFormats()
		self.selectionEnabled()

		if self.canvas is not None:
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
		self.btnAddRes.clicked.connect(lambda: browse(self, 'existing files', 'TUFLOW/batch_export_res', 'TUFLOW Results',
		                                              "XMDF (*.xmdf *.XMDF)", self.lwResultMesh))
		self.buttonBox.accepted.connect(self.check)
		self.buttonBox.rejected.connect(self.reject)

		self.pythonPopulateGui(**kwargs)
		self.kwargs = kwargs

	def pythonPopulateGui(self, **kwargs):
		if 'gis_layer' in kwargs:
			self.cbGISLayer.setCurrentText(kwargs['gis_layer'])
		if 'name_attribute_field' in kwargs:
			self.cbNameAttribute.setCurrentText(kwargs['name_attribute_field'])
		if 'result_meshes' in kwargs:
			if type(kwargs['result_meshes']) is  List:
				self.lwResultMesh.addItems(kwargs['result_meshes'])
			else:
				self.lwResultMesh.addItem(kwargs['result_meshes'])
			for i in range(self.lwResultMesh.count()):
				item = self.lwResultMesh.item(i)
				item.setSelected(True)
		if 'result_types' in kwargs:
			if type(kwargs['result_types']) is list:
				rts = ';;'.join(kwargs['result_types'])
			else:
				rts = kwargs['result_types']
			self.mcbResultTypes.setCurrentText(rts)
		if 'timestep' in kwargs:
			self.cbTimesteps.setCurrentText(kwargs['timestep'])
		if 'export' in kwargs:
			if kwargs['export'] == 'selected':
				self.rbSelectedFeatures.setChecked(True)
			else:
				self.rbAllFeatures.setChecked(True)
		if 'format' in kwargs:
			if kwargs['format'] == 'csv':
				self.rbCSV.setChecked(True)
			else:
				self.rbImage.setChecked(True)
				self.cbImageFormat.setCurrentText('.{0}'.format(kwargs['format']))
		if 'output_folder' in kwargs:
			self.outputFolder.setText(kwargs['output_folder'])
		
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
		from .tuflowqgis_tuviewer.tuflowqgis_turesults import TuResults

		onlyTemporal = False
		gisLayer = tuflowqgis_find_layer(self.cbGISLayer.currentText())
		if gisLayer is not None:
			if gisLayer.geometryType() == QgsWkbTypes.PointGeometry:
				onlyTemporal = True

		firstFound = True
		for res in self.lwResultMesh.selectedItems():
			layer = tuflowqgis_find_layer(res.text())
			if layer is not None:
				if firstFound:
					self.mcbResultTypes.clear()
					firstFound = False
				resultTypes = []
				# meshes = [self.mcbResultMesh.currentText()]
				# meshes = self.mcbResultMesh.checkedItems()
				# meshes = [x.text() for x in self.lwResultMesh.selectedItems()]
				# if layer is not None:
					#for mesh in meshes:
					#for mesh in self.mcbResultMesh.checkedItems():
				if layer.name() in self.tuView.tuResults.results:
					r = self.tuView.tuResults.results[layer.name()]
					for type, t in r.items():
						# if (layer.geometryType() == QgsWkbTypes.LineGeometry or ('isTemporal' in t
						# 		and t['isTemporal'] and layer.geometryType() == QgsWkbTypes.PointGeometry)) \
						# 		and ('isMax' in t and not t['isMax'] and 'isMin' in t and not t['isMin']):
						if not onlyTemporal or 'isTemporal' not in t or t['isTemporal']:
							type = TuResults.stripMaximumName(type)
							if type not in resultTypes:
								resultTypes.append(type)

				self.mcbResultTypes.addItems(resultTypes)
		
	def populateTimeSteps(self, *args):
		enableTimesteps = False
		gisLayer = tuflowqgis_find_layer(self.cbGISLayer.currentText())
		if gisLayer is not None:
			enableTimesteps = True

		timestepsFormatted = []
		firstFound = True
		for res in self.lwResultMesh.selectedItems():
			layer = tuflowqgis_find_layer(res.text())
			if layer is not None:
				if firstFound:
					self.cbTimesteps.clear()
					self.cbTimesteps.setEnabled(False)
					timesteps = []
					timestepsFormatted = []
					maximum = False
					minimum = False
					firstFound = False
				if not enableTimesteps:
					self.cbTimesteps.setEnabled(False)
				else:
					self.cbTimesteps.setEnabled(True)
					# meshes = [self.mcbResultMesh.currentText()]
					# meshes = self.mcbResultMesh.checkedItems()
					# meshes = [x.text() for x in self.lwResultMesh.selectedItems()]
					# rts = [x.lower() for x in self.mcbResultTypes.checkedItems()]
					# for mesh in meshes:
					# for mesh in self.mcbResultMesh.checkedItems():
					if layer.name() in self.tuView.tuResults.results:
						r = self.tuView.tuResults.results[layer.name()]
						for rtype, t in r.items():
							if type(t) is dict:  # map outputs results stored in dict, time series results stored as tuple
								if (gisLayer.geometryType() == QgsWkbTypes.LineGeometry or ('isTemporal' in t
										and t['isTemporal'] and gisLayer.geometryType() == QgsWkbTypes.PointGeometry)) \
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
						# if timesteps[-1] < 100:
						# 	timestepsFormatted = [convertTimeToFormattedTime(x) for x in timesteps]
						# else:
						# 	timestepsFormatted = [convertTimeToFormattedTime(x, hour_padding=3) for x in timesteps]
						if not self.tuView.tuOptions.xAxisDates:  # use Time (hrs)
							unit = self.tuView.tuOptions.timeUnits
							if (unit == 'h' and timesteps[-1] < 100) or (unit == 's' and timesteps[-1] / 3600 < 100):
								pad = 2
							else:
								pad = 3
							timestepsFormatted = [convertTimeToFormattedTime(x, unit=unit, hour_padding=pad) for x in timesteps]
						else:  # use datetime format
							timestepsFormatted = [self.tuView.tuResults._dateFormat.format(self.tuView.tuResults.time2date_tspec[x]) for x in timesteps]
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
		self.run()
		# if not self.cbGISLayer.currentText():
		# 	QMessageBox.information(self, 'Missing Data', 'Missing GIS Layer')
		# elif not self.lwResultMesh.selectedItems():
		# 	QMessageBox.information(self, 'Missing Data', 'Missing Result Mesh')
		# elif not self.mcbResultTypes.checkedItems():
		# 	QMessageBox.information(self, 'Missing Data', 'Missing Result Types')
		# elif self.cbTimesteps.isEnabled() and not self.cbTimesteps.currentText():
		# 	QMessageBox.information(self, 'Missing Data', 'Missing Time Step')
		# elif not self.outputFolder.text():
		# 	QMessageBox.information(self, 'Missing Data', 'Missing Output Folder')
		# elif not os.path.exists(self.outputFolder.text()):
		# 	QMessageBox.information(self, 'Missing Data', 'Output Folder Does Not Exist')
		# else:  # made it through the checks :)
		# 	self.run()
		
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
		if not resultTypes:
			resultTypes = self.mcbResultTypes.currentText().split(';;')
		timestep = self.cbTimesteps.currentText()  # str
		features = 'all' if self.rbAllFeatures.isChecked() else 'selection'  # str
		format = 'csv' if self.rbCSV.isChecked() else 'image'  # str
		imageFormat = self.cbImageFormat.currentText()
		outputFolder = self.outputFolder.text()  # str

		if 'timestep' in self.kwargs:
			del self.kwargs['timestep']
		if 'format' in self.kwargs:
			del self.kwargs['format']

		# setup logger
		logger = logging.getLogger('BatchExport')
		logger.setLevel(logging.INFO)
		fh = logging.FileHandler('{0}'.format(os.path.join(outputFolder, 'batch_export.log')), mode='w')
		fh.setLevel(logging.INFO)
		ch = logging.StreamHandler()
		ch.setLevel(logging.ERROR)
		fmt = logging.Formatter('%(message)s')
		fh.setFormatter(fmt)
		ch.setFormatter(fmt)
		logger.addHandler(fh)
		logger.addHandler(ch)

		# run process
		errorsOccured = False
		for r in resultMesh:
			neededLoading = False
			if r not in self.tuView.tuResults.results and \
					os.path.splitext(os.path.basename(r))[0] not in self.tuView.tuResults.results:
				imported = self.tuView.tuMenuBar.tuMenuFunctions.load2dResults(result_2D=[[r]])
				if not imported:
					logger.info('Error loading result: {0}'.format(r))
					errorsOccured = True
					continue
				neededLoading = True

			if neededLoading:
				r2 = os.path.basename(os.path.splitext(r)[0])
			else:
				r2 = r

			successful = self.tuView.tuMenuBar.tuMenuFunctions.batchPlotExport(gisLayer, [r2], resultTypes, timestep,
			                                                                   features, format, outputFolder,
			                                                                   nameField, imageFormat, **self.kwargs)
			if not successful:
				logger.info('Error creating plots for result: {0}'.format(r))
				errorsOccured = True

			if neededLoading:
				layer = tuflowqgis_find_layer(r2)
				if layer is not None:
					self.tuView.layersRemoved([layer.id()])
					self.tuView.project.removeMapLayer(layer.id())
		
		if not errorsOccured:
			msg = 'Successfully Exported Data'
			if self.iface is not None:
				QMessageBox.information(self, 'Batch Export', msg)
			else:
				print(msg)
			logger.info('Successfully exported plots')
		else:
			msg = 'Export process finished. Errors occured:\n{0}'.format('{0}'.format(os.path.join(outputFolder, 'batch_export.log')))
			if self.iface is not None:
				QMessageBox.information(self, 'Batch Export', msg)
			else:
				print(msg)

		# close logger
		logger.info('Finished')
		logging.shutdown()

		# finally destroy dialog
		self.accept()


# ----------------------------------------------------------
#    User Plot Data Plot View
# ----------------------------------------------------------
from .forms.ui_UserPlotDataPlotView import *


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
from .forms.ui_UserPlotDataTableView import *
from .tuflowqgis_tuviewer.tuflowqgis_tuuserplotdata import TuUserPlotDataSet


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
		self.tableDialog.exec()
		
		
# ----------------------------------------------------------
#    User Plot Data Import Dialog
# ----------------------------------------------------------
from .forms.ui_UserPlotDataImportDialog import *


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
		# self.dteZeroTime.setDisplayFormat('d/M/yyyy h:mm AP')
		
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
		label.setTextFormat(QT_RICH_TEXT)
		label.setText(txt)
		palette = label.palette()
		palette.setColor(QPalette.Foreground, QT_RED)
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
		dateTime = None
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
		if self.gbUseDates.isChecked():
			# self.referenceTime = dateTime
			self.referenceTime = self.zeroDate
		else:
			self.referenceTime = None
		
		# finally destroy dialog box
		self.ok = True
		self.accept()
		
		
	
# ----------------------------------------------------------
#    User Plot Data Manager
# ----------------------------------------------------------
from .forms.ui_UserPlotDataManagerDialog import *


class TuUserPlotDataManagerDialog(QDialog, Ui_UserPlotDataManagerDialog):
	
	def __init__(self, iface, TuUserPlotDataManager, **kwargs):
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

		if 'add_data' in kwargs:
			self.addData(**kwargs)
		if 'remove_data' in kwargs:
			if type(kwargs['remove_data']) is list:
				for item in kwargs['remove_data']:
					self.removeData(kwargs['remove_data'])
			else:
				self.removeData(kwargs['remove_data'])
		
	def loadData(self):
		# load data in correct order.. for dict means a little bit of manipulation

		for i, userData in enumerate([k for k, v in sorted(self.tuUserPlotDataManager.datasets.items(), key=lambda x: x[-1].number)]):
			name = self.tuUserPlotDataManager.datasets[userData].name
			plotType = self.tuUserPlotDataManager.datasets[userData].plotType
			status = QT_CHECKED if self.tuUserPlotDataManager.datasets[userData].status else QT_UNCHECKED
			self.UserPlotDataTable.setRowCount(self.UserPlotDataTable.rowCount() + 1)
			item = QTableWidgetItem(0)
			item.setText(name)
			item.setFlags(QT_ITEM_FLAG_ITEM_IS_USER_CHECKABLE | QT_ITEM_FLAG_ITEM_IS_EDITABLE | QT_ITEM_FLAG_ITEM_IS_SELECTABLE | QT_ITEM_FLAG_ITEM_IS_ENABLED)
			item.setCheckState(status)
			item2 = QTableWidgetItem(0)
			if plotType == 'Cross Section / Long Plot':
				item2.setText('Cross Section / Long Plot')
			else:
				item2.setText('Time Series Plot')
			self.UserPlotDataTable.setItem(self.UserPlotDataTable.rowCount() - 1, 0, item)
			self.UserPlotDataTable.setItem(self.UserPlotDataTable.rowCount() - 1, 1, item2)
			self.loadedData[name] = [item2, item]
			
			self.UserPlotDataTable.itemClicked.connect(lambda: self.editData(item=item))
			self.UserPlotDataTable.itemChanged.connect(lambda item: self.editData(item=item))
		
	def addData(self, **kwargs):
		self.addDataDialog = TuUserPlotDataImportDialog(self.iface)
		if 'add_data' in kwargs:
			self.pythonPopulateGui(**kwargs)
		else:
			self.addDataDialog.exec()
		if self.addDataDialog.ok:
			for i, name in enumerate(self.addDataDialog.names):
				# add data to class
				counter = 1
				while name in self.tuUserPlotDataManager.datasets.keys():
					name = '{0}_{1}'.format(name, counter)
					counter += 1
				# self.tuUserPlotDataManager.addDataSet(name, self.addDataDialog.data[i], 'time series', self.addDataDialog.dates[i], self.addDataDialog.referenceTime)
				self.tuUserPlotDataManager.addDataSet(name, self.addDataDialog.data[i], 'time series plot', self.addDataDialog.dates[i], self.addDataDialog.referenceTime)
				if not self.tuUserPlotDataManager.datasets[name].error:
					# add data to dialog
					self.UserPlotDataTable.setRowCount(self.UserPlotDataTable.rowCount() + 1)
					item = QTableWidgetItem(0)
					item.setText(name)
					item.setFlags(QT_ITEM_FLAG_ITEM_IS_USER_CHECKABLE | QT_ITEM_FLAG_ITEM_IS_EDITABLE | QT_ITEM_FLAG_ITEM_IS_SELECTABLE | QT_ITEM_FLAG_ITEM_IS_ENABLED)
					item.setCheckState(QT_CHECKED)
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
					self.UserPlotDataTable.itemClicked.connect(lambda item: self.editData(item=item))
					self.UserPlotDataTable.itemChanged.connect(lambda item: self.editData(item=item))
				else:
					QMessageBox.information(self.iface.mainWindow(), 'Import User Plot Data', self.tuUserPlotDataManager.datasets[name].error)

	def pythonPopulateGui(self, **kwargs):
		if 'add_data' in kwargs:
			self.addDataDialog.inFile.setText(str(kwargs['add_data']))
			self.addDataDialog.populateDataColumns()
		if 'delim' in kwargs:
			if kwargs['delim'] == 'csv' or kwargs['delim'] == ',':
				self.addDataDialog.rbCSV.setChecked(True)
			elif kwargs['delim'] == 'space' or kwargs['delim'] == ' ':
				self.addDataDialog.rbSpace.setChecked(True)
			elif kwargs['delim'] == 'tab' or kwargs['delim'] == '\t':
				self.addDataDialog.rbTab.setChecked(True)
			else:
				self.addDataDialog.rbOther.setChecked(True)
				self.addDataDialog.delimiter.setText(str(kwargs['delim']))
		if 'header_rows' in kwargs:
			self.addDataDialog.sbLines2Discard.setValue(int(kwargs['header_rows']))
		if 'user_header_rows_as_labels' in kwargs:
			self.addDataDialog.cbHeadersAsLabels.setChecked(bool(kwargs['user_header_rows_as_labels']))
		if 'header_row_index' in kwargs:
			self.addDataDialog.sbLabelRow.setValue(int(kwargs['header_row_index']))
		if 'x_column' in kwargs:
			self.addDataDialog.cbXColumn.setCurrentText(str(kwargs['x_column']))
		if 'y_columns' in kwargs:
			if type(kwargs['y_columns']) is str:
				kwargs['y_columns'] = [kwargs['y_columns']]
			self.addDataDialog.mcbYColumn.setCheckedItems(kwargs['y_columns'])
		if 'null_value' in kwargs:
			self.addDataDialog.nullValue.setText(str(kwargs['null_value']))
		if 'dates' in kwargs:
			self.addDataDialog.gbUseDates.setChecked(kwargs['dates'])
		if 'date_format' in kwargs:
			self.addDataDialog.cbUSDateFormat.setChecked(True) if kwargs['date_format'].lower() == 'us' else self.addDataDialog.cbUSDateFormat.setChecked(False)
		if 'reference_time' in kwargs:
			if self.addDataDialog.gbUseDates.isChecked():
				self.addDataDialog.dteZeroTime.setDateTime(kwargs['reference_time'])
				self.addDataDialog.cbManualZeroTime.setChecked(True)

		self.addDataDialog.run()

	def editData(self, **kwargs):
		combobox = kwargs['combobox'] if 'combobox' in kwargs.keys() else None
		item = kwargs['item'] if 'item' in kwargs.keys() else None
		
		if combobox is not None:
			for name, widgets in self.loadedData.items():
				if widgets[0] == combobox:
					# plotType = 'time series plot' if combobox.currentText() == 'Time Series Plot' else 'cross section / long plot'
					plotType = combobox.currentText()
					self.tuUserPlotDataManager.editDataSet(name, plotType=plotType)
	
		elif item is not None:
			for name, widgets in self.loadedData.items():
				if widgets[-1] == item:
					status = True if item.checkState() == QT_CHECKED else False
					self.tuUserPlotDataManager.editDataSet(name, newname=item.text(), status=status)
	
	def showDataTable(self):
		selectedItems = self.UserPlotDataTable.selectedItems()
		for item in selectedItems:
			row = self.UserPlotDataTable.row(item)
			item = self.UserPlotDataTable.item(row, 0)
			data = self.tuUserPlotDataManager.datasets[item.text()]
			self.tableDialog = TuUserPlotDataTableView(self.iface, data)
			self.tableDialog.exec()
			break  # just do first selection only
			
	def showDataPlot(self):
		selectedItems = self.UserPlotDataTable.selectedItems()
		for item in selectedItems:
			row = self.UserPlotDataTable.row(item)
			item = self.UserPlotDataTable.item(row, 0)
			data = self.tuUserPlotDataManager.datasets[item.text()]
			self.tableDialog = TuUserPlotDataPlotView(self.iface, data)
			self.tableDialog.exec()
			break  # just do first selection only
			
	def removeData(self, e=None, item_name=None):
		if item_name is None:
			selectedItems = self.UserPlotDataTable.selectedItems()
			for item in selectedItems:
				name = item.text()
				self.tuUserPlotDataManager.removeDataSet(name)
				#self.UserPlotDataTable.itemClicked.disconnect()
				#self.UserPlotDataTable.itemChanged.disconnect()
		else:
			self.tuUserPlotDataManager.removeDataSet(item_name)
		self.UserPlotDataTable.setRowCount(0)
		self.loadData()
		
	def setTableProperties(self):
		
		plotTypes = ['Time Series Plot', 'Cross Section / Long Plot']
		self.UserPlotDataTable.itemDelegateForColumn(1).setItems(items=plotTypes, default='Time Series Plot')
		
		
# ----------------------------------------------------------
#    Filter and Sort TUFLOW Layers in Map Window
# ----------------------------------------------------------
from .forms.ui_filter_sort_TUFLOW_layers import *


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
from .forms.TUFLOW_utilities import *


class TuflowUtilitiesDialog(QDialog, Ui_utilitiesDialog):
	def __init__(self, iface):
		QDialog.__init__(self)
		self.setupUi(self)
		self.iface = iface
		self.applyIcons()
		self.applyPrevExeLocations()
		self.browse_signals = {}
		self.label_40.setText('Unknown - click \'ASC_to_ASC Version\' to find')
		self.get_asc_to_asc_version(button_pushed=False)
		self.commonUtilityChanged(0)
		self.downloadUtilities = None
		self.populateGrids()
		self.populateGis()
		self.buttonGroup = QButtonGroup()
		self.buttonGroup.addButton(self.rbCommonFunctions)
		self.buttonGroup.addButton(self.rbAdvanced)
		self.rbCommonFunctions.setVisible(False)
		self.rbAdvanced.setVisible(False)
		self.rbCommonFunctions.setChecked(True)
		self.loadProjectSettings()
		self.cbo_output_format.setCurrentText(QSettings().value('TUFLOW/asc_to_asc_output_format', 'TIF'))

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
		self.pbLoadFromXmdfHeader.clicked.connect(self.populateXmdfInfo)
		self.pbAscToAsc_version.clicked.connect(self.get_asc_to_asc_version)
		self.cbo_output_format.currentIndexChanged.connect(self.toggle_output_format)

		self.xmdf_header = None
		self.cboToGisMeshDataset.currentIndexChanged.connect(self.tuflow_to_gis_result_type_changed)

		self.leAsc2Asc.textChanged.connect(lambda x: QSettings().setValue("TUFLOW_Utilities/ASC_to_ASC_exe", x))
		self.leTUFLOW2GIS.textChanged.connect(lambda x: QSettings().setValue("TUFLOW_Utilities/TUFLOW_to_GIS_exe", x))
		self.leRes2Res.textChanged.connect(lambda x: QSettings().setValue("TUFLOW_Utilities/Res_to_Res_exe", x))
		self.le12da2GIS.textChanged.connect(lambda x: QSettings().setValue("TUFLOW_Utilities/12da_to_from_GIS_exe", x))
		self.leConvert2TS1.textChanged.connect(lambda x: QSettings().setValue("TUFLOW_Utilities/Convert_to_TS1_exe", x))
		self.leTin2Tin.textChanged.connect(lambda x: QSettings().setValue("Tin_to_Tin executable location", x))
		self.leXSGenerator.textChanged.connect(lambda x: QSettings().setValue("TUFLOW_Utilities/xsGenerator_exe", x))

		self.connectBrowseButtons()

	def toggle_output_format(self):
		QSettings().setValue('TUFLOW/asc_to_asc_output_format', self.cbo_output_format.currentText())

	def toggle_new_asc_format(self):
		if self.asc_to_asc_version >= 20230100:
			self.label_41.show()
			self.cbo_output_format.show()
		else:
			self.label_41.hide()
			self.cbo_output_format.hide()

	def letter_to_patch_version(self, letters):
		A_ord = ord('A')
		return ''.join([str(ord(letter) - A_ord) for letter in letters])

	def build_to_version_int(self, build):
		comp = build.split('-')
		version_int = '{0}{1}{2}'.format(comp[0], comp[1], self.letter_to_patch_version(comp[2]))
		return int(version_int)

	def get_asc_to_asc_version(self, button_pushed=True):
		self.asc_to_asc_version = 0
		path = self.leAsc2Asc.text()
		if not path or not os.path.exists(path):
			if button_pushed:
				QMessageBox.warning(self, "TUFLOW Utilities", "Warning: ASC to ASC executable is not valid")
			return

		try:
			self.proc = subprocess.run([path], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
			                           input='\n', encoding='utf-8', timeout=10,
			                           creationflags=subprocess.CREATE_NO_WINDOW)
		except Exception as e:
			self.label_40.setText('Failed to get version')
			return

		out_text = self.proc.stdout.split('\n')
		for line in out_text:
			if re.findall(r'Build \d{4}-\d{2}-[A-Z]{2}', line):
				build = re.findall(r'\d{4}-\d{2}-[A-Z]{2}', line)[0]
				self.label_40.setText(build)
				self.asc_to_asc_version = self.build_to_version_int(build)
				break

		self.toggle_new_asc_format()

	def findFile(self):
		if not self.leAdvWorkingDir.text():
			QMessageBox.warning(self, "TUFLOW Utilities",
			                    "Warning: specify a working directory before selecting a file")
			return
		if not os.path.exists(self.leAdvWorkingDir.text()):
			QMessageBox.warning(self, "TUFLOW Utilities",
			                    "Warning: working directory is not valid")
			return

		files = QFileDialog.getOpenFileNames(self, "Select File(s)", self.leAdvWorkingDir.text(), "ALL (*)")[0]
		text = [self.teCommands.toPlainText()]

		try:
			relPaths = [os.path.relpath(x, self.leAdvWorkingDir.text()) for x in files]
		except Exception as e:
			QMessageBox.warning(self, "TUFLOW Utilities", "Warning: file is on a different drive than working directory")
			relPaths = files
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
			self.progressDialog.rejected.connect(self.stopDownload)
			self.downloadUtilities = DownloadTuflowUtilities()
			self.downloadUtilities.moveToThread(self.thread)
			self.downloadUtilities.updated.connect(self.progressDialog.updateProgress)
			self.downloadUtilities.finished.connect(self.progressDialog.progressFinished)
			self.downloadUtilities.finished.connect(self.downloadFinished)
			self.downloadUtilities.finished.connect(self.thread.terminate)
			self.thread.started.connect(self.downloadUtilities.download)
			self.progressDialog.show()
			self.thread.start()
		else:
			QMessageBox.critical(self, "TUFLOW Utilities", "Download feature only available on Windows")

	def stopDownload(self):
		if self.downloadUtilities:
			self.downloadUtilities.cancelled = True
			from tuflow.gui.logging import Logging
			Logging.info('Downloads will be cancelled after current utility [{}] is downloaded.'.format(self.downloadUtilities.cur_util))
	
	def downloadFinished(self, e):
		utilities = {'asc_to_asc': self.leAsc2Asc, 'tuflow_to_gis': self.leTUFLOW2GIS,
		             'res_to_res': self.leRes2Res, '12da_to_from_gis': self.le12da2GIS,
		             'convert_to_ts1': self.leConvert2TS1, 'tin_to_tin': self.leTin2Tin,
		             'xsGenerator': self.leXSGenerator}
		if self.downloadUtilities.error:
			QMessageBox.critical(self, "TUFLOW Utilities", self.downloadUtilities.errmsg)
			self.progressDialog.accept()
			return
		for key, value in e.items():
			utilities[key].setText(value)

		if self.downloadUtilities.cancelled:
			from tuflow.gui.logging import Logging
			Logging.warning('Download cancelled by user.')

		self.progressDialog.accept()

		self.get_asc_to_asc_version(button_pushed=False)
	
	def populateGrids(self):
		rasters = findAllRasterLyrs()
		grids = []  # only select rasters that are .asc or .flt
		for raster in rasters:
			layer = tuflowqgis_find_layer(raster)
			layer_helper = LayerHelper(layer)
			if layer_helper.is_tuflow_type(self.asc_to_asc_version):
				grids.append(raster)
				
		self.cboDiffGrid1.addItems(grids)
		self.cboDiffGrid2.addItems(grids)
		self.cboGrid.addItems(grids)
		self.cboBrkline_raster.addItems(grids)

	def populateGis(self):
		layers = findAllVectorLyrs()
		gis = []
		for layer in layers:
			layer = tuflowqgis_find_layer(layer)
			layer_helper = LayerHelper(layer)
			if layer_helper.is_tuflow_type(self.asc_to_asc_version):
				gis.append(layer.name())

		self.cboBrkline_vector.addItems(gis)
	
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
					layer_helper = LayerHelper(layer)
					dataSource = layer_helper.tuflow_path
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
		                 self.btnBrowseMeshToGis, self.btnBrowseMeshToRes, self.btnBrowseMeshMulti,
		                 self.btnBrowseBrkline_vector, self.btnBrowseBrkline_raster]
		addButtons = [self.btnAddGrid, self.btnAddMesh]
		removeButtons = [self.btnRemoveGrid, self.btnRemoveMesh]
		
		for button in browseButtons:
			button.setIcon(folderIcon)
		for button in addButtons:
			button.setIcon(addIcon)
		for button in removeButtons:
			button.setIcon(removeIcon)

	def populateXmdfInfo(self):
		if not self.leMeshToGis.text():
			QMessageBox.critical(self, "TUFLOW Utilities", "Please specify an XMDF first.")
			return

		if os.path.splitext(self.leMeshToGis.text())[1].lower() != '.xmdf':
			QMessageBox.critical(self, "TUFLOW Utilities", "Please file must be an XMDF to load information.")
			return

		if not self.leRes2Res.text():
			QMessageBox.critical(self, "TUFLOW Utilities", "Must specify res_to_res.exe location before populating XMDF information.")
			return

		QApplication.setOverrideCursor(QT_CURSOR_WAIT)

		error, message = resToRes(self.leRes2Res.text().strip('"').strip("'"), 'info', '',
								  [self.leMeshToGis.text().strip('"\'')],
								  '', hide_window=True)

		QApplication.restoreOverrideCursor()

		if error:
			QMessageBox.critical(self, "TUFLOW Utilities", "Error occurred reading XMDF header information.\nPlease see output log information for more information.")
			output_dialog = StackTraceDialog(message)
			output_dialog.setWindowTitle('Res_to_Res Output Log')
			output_dialog.exec()
			return

		self.xmdf_header = XMDF_Header_Info(message)

		if not self.xmdf_header.loaded:
			QMessageBox.critical(self, "TUFLOW Utilities", "Error occurred reading XMDF header information. Please contact support@tuflow.com if problem persists.")
			return

		self.cboToGisMeshDataset.clear()
		self.cboToGisMeshDataset.addItems(self.xmdf_header.result_types())

		self.cboTimestep.clear()
		times = []
		if self.xmdf_header.has_max():
			times.append('Max')
		if self.xmdf_header.has_min():
			times.append('Min')
		times.extend(['{0:.03f}'.format(x) for x in self.xmdf_header.times()])
		self.cboTimestep.addItems(times)
		self.tuflow_to_gis_result_type_changed(None)

	def tuflow_to_gis_result_type_changed(self, e):
		if self.xmdf_header is None or not self.xmdf_header.loaded:
			return

		result_type = self.cboToGisMeshDataset.currentText()
		self.cboTimestep.clear()
		times = []
		if self.xmdf_header.has_max(result_type):
			times.append('Max')
		if self.xmdf_header.has_min(result_type):
			times.append('Min')
		times.extend(['{0:.03f}'.format(x) for x in self.xmdf_header.times(result_type)])
		self.cboTimestep.addItems(times)

	def check(self):
		if self.rbCommonFunctions.isChecked():
			# if self.leOutputName.text():
				# if not self.leComOutputDir.text():
				# 	QMessageBox.critical(self, "TUFLOW Utilities", "Must specify output location if specifying output name")
				# 	return
				# if not os.path.exists(self.leComOutputDir.text().strip('"').strip("'")):
				# 	QMessageBox.critical(self, "TUFLOW Utilities", "Output location does not exist")
				# 	return
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
						                            QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO)
						if reply == QT_MESSAGE_BOX_NO:
							return
				elif self.rbAscConv.isChecked():
					if not self.lwGrids.count():
						QMessageBox.critical(self, "TUFLOW Utilities", "Must specify at least one grid")
						return
				elif self.rbBrklineFunc.isChecked():
					if not self.cboBrkline_vector.currentText() and not self.cboBrkline_raster.currentText():
						QMessageBox.critical(self, "TUFLOW Utilities", "Must specify a vector and raster for breakline function")
						return
					if not tuflowqgis_find_layer(self.cboBrkline_vector.currentText()) and not os.path.exists(self.cboBrkline_vector.currentText()):
						QMessageBox.critical(self, "TUFLOW Utilities", "Breakline function - Could not find vector layer")
						return
					if not tuflowqgis_find_layer(self.cboBrkline_raster.currentText()) and not os.path.exists(self.cboBrkline_raster.currentText()):
						QMessageBox.critical(self, "TUFLOW Utilities", "Breakline function - Could not find raster layer")
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
							                            QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO)
							if reply == QT_MESSAGE_BOX_NO:
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
							                            QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO)
							if reply == QT_MESSAGE_BOX_NO:
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
			utilities = ['Asc2Asc', 'TUFLOW2GIS', 'Res2Res', '12da2GIS', 'Convert2TS1','Tin2Tin', 'XSGenerator']
			i = self.cboAdvancedUtility.currentIndex()
			leutil = eval("self.le{0}".format(utilities[i]))
			if not leutil.text():
				QMessageBox.critical(self, "TUFLOW Utilities", "{0} path is not specified in the Executables tab".format(self.cboAdvancedUtility.currentText()))
				return
			if not os.path.exists(leutil.text()):
				QMessageBox.critical(self, "TUFLOW Utilities",
				                     "{0} path in the Executables tab is not valid:\n{1}".format(
					                     self.cboAdvancedUtility.currentText(), leutil.text()))
				return
		
		self.run()
		
	def run(self):
		self.pbOK.setEnabled(False)
		self.pbCancel.setEnabled(False)
		QgsApplication.setOverrideCursor(QCursor(QT_CURSOR_WAIT))
		error = False
		
		# precoded functions
		util = ''
		if self.rbCommonFunctions.isChecked():
			workdir = self.leComOutputDir.text().strip('"').strip("'")
			
			# asc_to_asc
			if self.cboCommonUtility.currentIndex() == 0:
				util = 'asc_to_asc'
				gis = []
				format = self.cbo_output_format.currentText()

				# difference
				if self.rbAscDiff.isChecked():
					if not workdir:
						workdir = os.path.dirname(self.cboDiffGrid1.currentText().strip('"').strip("'"))
					function = 'diff'
					inps = [self.cboDiffGrid1.currentText().strip('"').strip("'"),
					         self.cboDiffGrid2.currentText().strip('"').strip("'")]
					grids = []
					for inp in inps:
						if tuflowqgis_find_layer(inp):
							layer_helper = LayerHelper(tuflowqgis_find_layer(inp))
							ds = layer_helper.tuflow_path
						else:
							ds = inp
						grids.append(ds)
				elif self.rbBrklineFunc.isChecked():
					if not workdir:
						if tuflowqgis_find_layer(self.cboBrkline_vector.currentText()):
							layer_helper = LayerHelper(tuflowqgis_find_layer(self.cboBrkline_vector.currentText()))
							ds = Path(layer_helper.datasource).parent
						else:
							ds = self.cboBrkline_vector.currentText().strip('"').strip("'")
						workdir = Path(ds).parent
					function = 'brkline'

					# get raster
					if tuflowqgis_find_layer(self.cboBrkline_raster.currentText()):
						layer_helper = LayerHelper(tuflowqgis_find_layer(self.cboBrkline_raster.currentText()))
						ds = layer_helper.tuflow_path
					else:
						ds = self.cboBrkline_raster.currentText()
					grids = [ds]

					# get vector layer
					if tuflowqgis_find_layer(self.cboBrkline_vector.currentText()):
						layer_helper = LayerHelper(tuflowqgis_find_layer(self.cboBrkline_vector.currentText()))
						ds = layer_helper.tuflow_path
					else:
						ds = self.cboBrkline_vector.currentText()
					gis = [ds]
				else:
					if not workdir:
						workdir = os.path.dirname(self.lwGrids.item(0).text())
					grids = []
					for i in range(self.lwGrids.count()):
						inp = self.lwGrids.item(i).text()
						if tuflowqgis_find_layer(inp):
							layer_helper = LayerHelper(tuflowqgis_find_layer(inp))
							ds = layer_helper.tuflow_path
						else:
							ds = inp
						grids.append(ds)
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
				                          out=self.leOutputName.text(), saveFile=self.cbSaveBatComm.isChecked(),
				                          format=format, version=self.asc_to_asc_version, gis=gis)
				
			# tuflow_to_gis
			elif self.cboCommonUtility.currentIndex() == 1:
				util = 'tuflow_to_gis'
				if not workdir:
					workdir = os.path.dirname(self.leTUFLOW2GIS.text().strip('"').strip("'"))
				if self.rbMeshToGrid.isChecked():
					function = 'grid'
				elif self.rbMeshToPoints.isChecked():
					function = 'points'
				else:
					function = 'vectors'
				dataset = self.cboToGisMeshDataset.currentText()
				time = self.cboTimestep.currentText()
				if self.xmdf_header is not None and self.xmdf_header.loaded():
					dataset, time = self.xmdf_header[dataset,time]
				if self.xmdf_header is None or not self.xmdf_header.loaded() or dataset is None or time is None:
					dataset = self.cboToGisMeshDataset.currentText()
					time = self.cboTimestep.currentText()
				error, message = tuflowToGis(self.leTUFLOW2GIS.text().strip('"').strip("'"), function, workdir, self.leMeshToGis.text(),
				                             dataset, time, saveFile=self.cbSaveBatComm.isChecked(), out=self.leOutputName.text())
				
			# res_to_res
			elif self.cboCommonUtility.currentIndex() == 2:
				util = 'res_to_res'
				if self.rbMeshInfo.isChecked():
					function = 'info'
					meshes = [self.leMeshToRes.text().strip('"').strip("'")]
				elif self.rbMeshConvert.isChecked():
					if not workdir:
						workdir = os.path.dirname(self.leMeshToRes.text().strip('"').strip("'"))
					function = 'conv'
					meshes = [self.leMeshToRes.text().strip('"').strip("'")]
				else:
					if not workdir:
						workdir = os.path.dirname(self.lwMeshes.item(0).text())
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
			util_name = {0: 'asc_to_asc', 1: 'tuflow_to_gis', 2: 'res_to_res', 3: '12da_to_gis', 4: 'convert_to_ts1', 5: 'tin_to_tin', 6: 'xsGenerator'}
			util = util_name[self.cboAdvancedUtility.currentIndex()]
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
				self.errorDialog.exec()
			else:
				QMessageBox.critical(self, "TUFLOW Utilities", "Error Occured: {0}".format(message))
			self.pbOK.setEnabled(True)
			self.pbCancel.setEnabled(True)
		else:
			if self.rbCommonFunctions.isChecked() and \
					self.cboCommonUtility.currentIndex() == 2 and self.rbMeshInfo.isChecked():
				self.xmdfInfoDialog = XmdfInfoDialog(message)
				self.xmdfInfoDialog.exec()
			else:
				#QMessageBox.information(self, "TUFLOW Utilities", "Utility Finished")
				# self.accept()
				from tuflow.gui.logging import Logging
				if util:
					util = '[{}]'.format(util)
				Logging.info('Utility {} finished successfully'.format(util))
		
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
		if self.browse_signals:
			self.disconnectBrowseSignals()

		if self.asc_to_asc_version >= 20230100:
			grid_filters = 'All raster formats (*.asc *.ASC *.txt *.TXT *.dem *.DEM *.flt *.FLT *.tif *.TIF *.gtiff *.GTIFF *.gtif *.GTIF *.tif8 *.TIF8 *.btif *.BTIF *.gpkg *.GPKG *.nc *.NC);; \
			                ASC format (*.asc *.ASC *.txt *.TXT *.dem *.DEM);;' \
			               'FLT format (*.flt *.FLT);;' \
			               'TIF format (*.tif *.TIF *.gtiff *.GTIFF *.gtif *.GTIF *.tif8 *.TIF8 *.btif *.BTIF);; \
			                GeoPackage (*.gpkg *.GPKG);;NetCDF (*.nc *.NC)'
			gis_filters = 'All vector formats (*.shp *.SHP *.gpkg *.GPKG *.mif *.MIF);; \
		                   Shapefile (*.shp *.SHP);;GeoPackage (*.gpkg *.GPKG);;MapInfo (*.mif *.MIF)'
		else:
			grid_filters = 'All raster formats (*.asc *.ASC *.flt *.FLT *.tif);; \
						    ASC format (*.asc *.ASC);;FLT format (*.flt *.FLT)'
			gis_filters = 'All vector formats (*.shp *.SHP *.mif *.MIF);;Shapefile (*.shp *.SHP);;MapInfo (*.mif *.MIF)'

		signal = self.btnBrowseComOutputDir.clicked.connect(lambda: browse(self, 'existing folder',
		                                                                   'TUFLOW_Utilities/output_directory',
		                                                                   'Output Directory', None, self.leComOutputDir))
		self.browse_signals[self.btnBrowseComOutputDir] = signal

		signal = self.btnBrowseDiffGrid1.clicked.connect(lambda: browse(self, 'existing file',
		                                                                'TUFLOW_Utilities/ASC_to_ASC_difference_grid1',
		                                                                'ASC_to_ASC Difference Grid 1',
		                                                                grid_filters, self.cboDiffGrid1))
		self.browse_signals[self.btnBrowseDiffGrid1] = signal

		signal = self.btnBrowseDiffGrid2.clicked.connect(lambda: browse(self, 'existing file',
		                                                            'TUFLOW_Utilities/ASC_to_ASC_difference_grid2',
		                                                            'ASC_to_ASC Difference Grid 2',
		                                                            grid_filters, self.cboDiffGrid2))
		self.browse_signals[self.btnBrowseDiffGrid2] = signal

		signal = self.btnBrowseGrid.clicked.connect(lambda: browse(self, 'existing files',
		                                                       'TUFLOW_Utilities/ASC_to_ASC_grid',
		                                                       'ASC_to_ASC Input Grid',
		                                                       grid_filters, self.cboGrid))
		self.browse_signals[self.btnBrowseGrid] = signal

		signal = self.btnBrowseAdvWorkingDir.clicked.connect(lambda: browse(self, 'existing folder',
		                                                                "TUFLOW_Utilities/advanced_working_directory",
		                                                                "Working Directory", None,
		                                                                self.leAdvWorkingDir))
		self.browse_signals[self.btnBrowseAdvWorkingDir] = signal

		signal = self.btnBrowseAsc2Asc.clicked.connect(lambda: browse(self, 'existing file', "TUFLOW_Utilities/ASC_to_ASC_exe",
		                                                          "ASC_to_ASC executable location", "EXE (*.exe *.EXE)",
		                                                          self.leAsc2Asc))
		self.browse_signals[self.btnBrowseAsc2Asc] = signal

		signal = self.btnBrowseTUFLOW2GIS.clicked.connect(lambda: browse(self, 'existing file',
		                                                             "TUFLOW_Utilities/TUFLOW_to_GIS_exe",
		                                                             "TUFLOW_to_GIS executable location",
		                                                             "EXE (*.exe *.EXE)", self.leTUFLOW2GIS))
		self.browse_signals[self.btnBrowseTUFLOW2GIS] = signal

		signal = self.btnBrowseRes2Res.clicked.connect(lambda: browse(self, 'existing file',
		                                                          "TUFLOW_Utilities/Res_to_Res_exe",
		                                                          "Res_to_Res executable location",
		                                                          "EXE (*.exe *.EXE)", self.leRes2Res))
		self.browse_signals[self.btnBrowseRes2Res] = signal

		signal = self.btnBrowse12da2GIS.clicked.connect(lambda: browse(self, 'existing file',
		                                                           "TUFLOW_Utilities/12da_to_from_GIS_exe",
		                                                           "12da_to_from_GIS executable location",
		                                                           "EXE (*.exe *.EXE)", self.le12da2GIS))
		self.browse_signals[self.btnBrowse12da2GIS] = signal

		signal = self.btnBrowseConvert2TS1.clicked.connect(lambda: browse(self, 'existing file',
		                                                              "TUFLOW_Utilities/Convert_to_TS1_exe",
		                                                              "Convert_to_TS1 executable location",
		                                                              "EXE (*.exe *.EXE)", self.leConvert2TS1))
		self.browse_signals[self.btnBrowseConvert2TS1] = signal

		signal = self.btnBrowseTin2Tin.clicked.connect(lambda: browse(self, 'existing file',
		                                                          "TUFLOW_Utilities/Tin_to_Tin_exe",
		                                                          "Tin_to_Tin executable location",
		                                                          "EXE (*.exe *.EXE)", self.leTin2Tin))
		self.browse_signals[self.btnBrowseTin2Tin] = signal

		signal = self.btnBrowseXSGenerator.clicked.connect(lambda: browse(self, 'existing file',
		                                                              "TUFLOW_Utilities/xsGenerator_exe",
		                                                              "xsGenerator executable location",
		                                                              "EXE (*.exe *.EXE)", self.leXSGenerator))
		self.browse_signals[self.btnBrowseXSGenerator] = signal

		signal = self.btnBrowseMeshToGis.clicked.connect(lambda: browse(self, 'existing file',
		                                                            'TUFLOW_Utilities/TUFLOW_to_GIS_mesh',
		                                                            'XMDF or DAT location',
		                                                            "All mesh formats (*.xmdf *.XMDF *.dat *.DAT);;"
		                                                            "XMDF format(*.xmdf *.XMDF);;"
		                                                            "DAT format (*.dat *.DAT)", self.leMeshToGis))
		self.browse_signals[self.btnBrowseMeshToGis] = signal

		signal = self.btnBrowseMeshToRes.clicked.connect(lambda: browse(self, 'existing file',
		                                                            'TUFLOW_Utilities/Res_to_Res_mesh',
		                                                            'XMDF or DAT location',
		                                                            "All mesh formats (*.xmdf *.XMDF *.dat *.DAT);;"
		                                                            "XMDF format(*.xmdf *.XMDF);;"
		                                                            "DAT format (*.dat *.DAT)", self.leMeshToRes))
		self.browse_signals[self.btnBrowseMeshToRes] = signal

		signal = self.btnBrowseMeshMulti.clicked.connect(lambda: browse(self, 'existing files',
		                                                            'TUFLOW_Utilities/TUFLOW_to_GIS_meshes',
		                                                            'XMDF or DAT location',
		                                                            "All mesh formats (*.xmdf *.XMDF *.dat *.DAT);;"
		                                                            "XMDF format(*.xmdf *.XMDF);;"
		                                                            "DAT format (*.dat *.DAT)", self.leMeshMulti))
		self.browse_signals[self.btnBrowseMeshMulti] = signal

		signal = self.btnBrowseBrkline_vector.clicked.connect(lambda: browse(self, 'existing file', "TUFLOW_Utilities/brkline_input",
		                                                            'Vector input',
		                                                            gis_filters, self.cboBrkline_vector))
		self.browse_signals[self.btnBrowseBrkline_vector] = signal

		signal = self.btnBrowseBrkline_raster.clicked.connect(lambda: browse(self, 'existing file', "TUFLOW_Utilities/brkline_input",
		                                                            'Raster input',
		                                                            grid_filters, self.cboBrkline_raster))
		self.browse_signals[self.btnBrowseBrkline_raster] = signal

	def disconnectBrowseSignals(self):
		for btn, signal in self.browse_signals.items():
			btn.disconnect(signal)

		self.browse_signals.clear()


		

#-----------------------------------------------------------
#    XMDF info
# ----------------------------------------------------------
from .forms.XMDF_info import *


class XmdfInfoDialog(QDialog, Ui_XmdfInfoDialog):
	def __init__(self, text):
		QDialog.__init__(self)
		self.setupUi(self)
		self.teXmdfInfo.setPlainText(text)


# ----------------------------------------------------------
#    Stack Trace
# ----------------------------------------------------------
from .forms.StackTrace import *


class StackTraceDialog(QDialog, Ui_StackTraceDialog):
	def __init__(self, text):
		QDialog.__init__(self)
		self.setupUi(self)
		self.teStackTrace.setPlainText(text)
		
		
# ----------------------------------------------------------
#    Tuflow utility error
# ----------------------------------------------------------
from .forms.Tuflow_utility_error import *


class UtilityErrorDialog(QDialog, Ui_utilityErrorDialog):
	def __init__(self, text):
		QDialog.__init__(self)
		self.setupUi(self)
		self.teError.setPlainText(text)
		
		
# ----------------------------------------------------------
#    Tuflow utility download progress bar
# ----------------------------------------------------------
from .forms.download_utility_progress import *


class UtilityDownloadProgressBar(QDialog, Ui_downloadUtilityProgressDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent=parent)
		self.setupUi(self)
		self.progressBar.setRange(0, 0)
		self.progressCount = 0
		self.start = True
		self.timer = None
		
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
		if self.timer:
			self.timer.stop()
			self.progressBar.setRange(100, 100)
			self.label.setText('Complete')


class DownloadTuflowUtilities(QObject):
	finished = pyqtSignal(dict)
	updated = pyqtSignal(str)
	
	utilities = ['asc_to_asc', 'tuflow_to_gis', 'res_to_res', '12da_to_from_gis', 'convert_to_ts1', 'tin_to_tin',
	             'xsGenerator']
	paths = {}

	def __init__(self):
		super().__init__()
		self.error = False
		self.errmsg = ''
		self.cancelled = False
		self.cur_util = None
	
	def download(self):
		for utility in self.utilities:
			if self.cancelled:
				break
			self.cur_util = utility
			self.updated.emit(utility)
			try:
				path = downloadUtility(utility)
			except Exception as e:
				self.error = True
				self.errmsg = str(e)
				self.finished.emit(self.paths)
				return
			self.paths[utility] = path
		
		self.finished.emit(self.paths)


# ----------------------------------------------------------
#    tuflowqgis broken links
# ----------------------------------------------------------
from .forms.ui_tuflowqgis_brokenLinks import *


class tuflowqgis_brokenLinks_dialog(QDialog, Ui_scenarioSelection):
	def __init__(self, iface, brokenLinks):
		QDialog.__init__(self)
		self.iface = iface
		self.brokenLinks = brokenLinks
		self.setupUi(self)
		
		for brokenLink in self.brokenLinks:
			self.brokenLinks_lw.addItem(brokenLink)
		
		self.ok_button.clicked.connect(self.accept)


# ----------------------------------------------------------
#    Import Flood Modeller results into tuflow viewer
# ----------------------------------------------------------
from .forms.FMResImport_Dialog import *


class FloodModellerResultImportDialog(QDialog, Ui_FMResDialog):
	def __init__(self):
		QDialog.__init__(self)
		self.setupUi(self)
		self.setupButtons()
		self.gxy = None
		self.dat = None
		self.results = []

		# browse to files
		self.btnBrowseGXY.clicked.connect(lambda: browse(self, 'existing file', 'TUFLOW/import_FM_Dialog',
		                                                 'Flood Modeller GXY File', 'GXY (*.gxy *.GXY)', self.leGXY))
		self.btnBrowseSectionData.clicked.connect(lambda: browse(self, 'existing file', 'TUFLOW/import_FM_Dialog',
		                                                         'Flood Modeller Cross-Section DAT File', 'DAT (*.dat *.DAT)', self.leSectionData))
		self.btnBrowseCSV.clicked.connect(lambda: browse(self, 'existing files', 'TUFLOW/import_FM_Dialog',
		                                                 'Flood Modeller Result CSV Files', 'CSV ZZN (*.csv *.CSV *.zzn *.ZZN)',
		                                                 self.lwCSVFiles, allowDuplicates=False))

		# other signals
		self.btnRemCSV.clicked.connect(self.removeCSV)
		self.pbOK.clicked.connect(self.run)
		self.pbCancel.clicked.connect(self.reject)

	def setupButtons(self):
		folIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
		remIcon = QgsApplication.getThemeIcon('/symbologyRemove.svg')

		# browse icon
		self.btnBrowseGXY.setIcon(folIcon)
		self.btnBrowseSectionData.setIcon(folIcon)
		self.btnBrowseCSV.setIcon(folIcon)

		# add / remove icons
		self.btnRemCSV.setIcon(remIcon)

		# tooltips
		self.btnBrowseGXY.setToolTip("Browse to GXY file location")
		self.btnBrowseSectionData.setToolTip("Browse to section (.DAT) file location")
		self.btnBrowseCSV.setToolTip("Browse to CSV file location")
		self.btnRemCSV.setToolTip("Remove selected CSV from list")

	def removeCSV(self):
		selectedItems = self.lwCSVFiles.selectedItems()
		selectedIndexes = [x for x in range(self.lwCSVFiles.count()) if self.lwCSVFiles.item(x) in selectedItems]
		for i in reversed(selectedIndexes):
			self.lwCSVFiles.takeItem(i)

	def errorMessage_(self, message):
		QMessageBox.critical(self, "Import FM Results", message)

	def run(self):
		if not self.leGXY.text():
			self.errorMessage_("GXY file path not specified")
			return
		if not os.path.exists(self.leGXY.text()):
			self.errorMessage_("GXY file does not exist:\n{0}".format(self.leGXY.text()))
			return
		self.gxy = self.leGXY.text()

		if self.leSectionData.text():
			if not os.path.exists(self.leSectionData.text()):
				self.errorMessage_("Cross-section dat file does not exist:\n{0}".format(self.leSectionData.text()))
				return
			self.dat = self.leSectionData.text()

		self.results = [self.lwCSVFiles.item(x).text() for x in range(self.lwCSVFiles.count())]
		if not self.results:
			self.errorMessage_("No result CSV files specified")
			return
		for res in self.results:
			invalidFilePaths = [x for x in self.results if not os.path.exists(x)]
			if invalidFilePaths:
				invalidFilePaths = '\n'.join(invalidFilePaths)
				self.errorMessage_(invalidFilePaths)
				return

		self.accept()

















































