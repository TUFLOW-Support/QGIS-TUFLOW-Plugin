import os, sys
import tempfile
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtXml import QDomDocument

from qgis.core import *
from qgis.gui import *
from ui_map_dialog import Ui_MapDialog
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuanimation import ImagePropertiesDialog, PlotProperties, TextPropertiesDialog
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuanimation import prepare_composition, prepare_composition_from_template, createText
from tuflow.tuflowqgis_library import tuflowqgis_find_layer


def getResultTypes(results, layer):
	"""
	get available scalar types
	
	:param results: dict -> e.g. { M01_5m_001: { depth: { '0.0000': ( timestep, type, QgsMeshDatasetIndex )}, point_ts: ( types, timesteps ) } }
	:param layer: str mesh layer result name
	:return: list -> str scalar type
	"""
	
	scalarTypes, vectorTypes = [], []
	if layer in results:
		result = results[layer]
		for rtype, ts in result.items():
			if '_ts' not in rtype and '_lp' not in rtype:
				t = rtype.split('/')[0].strip()
				for key, item in ts.items():
					if item[1] == 1:
						if t not in scalarTypes:
							scalarTypes.append(t)
					elif item[1] == 2:
						if t not in vectorTypes:
							vectorTypes.append(t)
					break
						
	return scalarTypes, vectorTypes


def getTimes(results, layer, stype, vtype):
	"""
	get available times
	
	:param results: dict -> e.g. { M01_5m_001: { depth: { '0.0000': ( timestep, type, QgsMeshDatasetIndex )}, point_ts: ( types, timesteps ) } }
	:param layer: str mesh layer result name
	:param stype: str scalar result type
	:param vtype: str vector result type
	:return: list -> str formatted time
	"""
	
	typ = vtype if stype == 'None' else stype
	
	times = []
	if layer in results:
		result = results[layer]
		for rtype, ts in result.items():
			if '_ts' not in rtype and '_lp' not in rtype:
				t = rtype.split('/')[0].strip()
				if t == typ:
					if '/Maximums' in ts:
						if 'Max' not in times:
							times.insert(0, 'Max')
					else:
						for key, item in ts.items():
							x = item[0]
							if x == -99999:
								if 'Max' not in times:
									times.insert(0, 'Max')
							else:
								time = '{0:02d}:{1:02.0f}:{2:05.2f}'.format(int(x), (x - int(x)) * 60, (x - int(x) - (x - int(x))) * 3600)
								if time not in times:
									times.append(time)
							
	return times


def makeMap(cfg, iface, progress_fn=None, dialog=None, preview=False, iteration=0):
	"""
	
	
	:param cfg: dict
	:param iface: QgsInterface
	:param progress_fn: lambda function
	:param dialog: TuMapDialog
	:param preview: bool
	:return: QgsLayout
	"""
	
	# get configuration properties
	l = cfg['layer']
	time = cfg['time']
	w, h = cfg['img_size']
	dpi = cfg['dpi']
	imgfile = cfg['imgfile']
	layers = cfg['layers'] if 'layers' in cfg else [l.id()]
	extent = cfg['extent'] if 'extent' in cfg else l.extent()
	crs = cfg['crs'] if 'crs' in cfg else None
	layoutcfg = cfg['layout']
	
	# store original values
	#original_rs = l.rendererSettings()
	
	# render - take settings from first render and use for subsequent renders
	rs = l.rendererSettings()
	asd = cfg['scalar index']
	if asd:
		rs.setActiveScalarDataset(asd)
		if iteration == 0 or 'scalar settings' not in cfg:
			cfg['scalar settings'] = rs.scalarSettings(asd.group())
		rs.setScalarSettings(asd.group(), cfg['scalar settings'])
	avd = cfg['vector index']
	if avd:
		rs.setActiveVectorDataset(avd)
		if iteration == 0 or 'vector settings' not in cfg:
			cfg['vector settings'] = rs.vectorSettings(avd.group())
		rs.setVectorSettings(avd.group(), cfg['vector settings'])
	l.setRendererSettings(rs)
	
	# Prepare layout
	layout = QgsPrintLayout(QgsProject.instance())
	layout.initializeDefaults()
	layout.setName('tuflow')
	
	if layoutcfg['type'] == 'file':
		prepare_composition_from_template(layout, cfg, time, dialog, os.path.dirname(imgfile), False, False, layers)
	else:
		layout.renderContext().setDpi(dpi)
		layout.setUnits(QgsUnitTypes.LayoutMillimeters)
		main_page = layout.pageCollection().page(0)
		main_page.setPageSize(QgsLayoutSize(w,  h, QgsUnitTypes.LayoutMillimeters))
		prepare_composition(layout, time, cfg, layoutcfg, extent, layers, crs, os.path.dirname(imgfile), dialog, False, False)
		
	# export layout
	layout_exporter = QgsLayoutExporter(layout)
	image_export_settings = QgsLayoutExporter.ImageExportSettings()
	image_export_settings.dpi = dpi
	image_export_settings.imageSize = QSize(w, h)
	pdf_export_settings = QgsLayoutExporter.PdfExportSettings()
	pdf_export_settings.dpi = dpi
	pdf_export_settings.imageSize = QSize(w, h)
	svg_export_settings = QgsLayoutExporter.SvgExportSettings()
	svg_export_settings.dpi = dpi
	svg_export_settings.imageSize = QSize(w, h)
	ext = os.path.splitext(imgfile)[1]
	if ext.lower() == '.pdf':
		res = layout_exporter.exportToPdf(imgfile, pdf_export_settings)
	elif ext.lower() == '.svg':
		res = layout_exporter.exportToSvg(imgfile, svg_export_settings)
	else:
		res = layout_exporter.exportToImage(imgfile, image_export_settings)
		
	# delete plot images
	if 'plots' in layoutcfg:
		for plot in layoutcfg['plots']:
			source = layoutcfg['plots'][plot]['source']
			os.remove(source)
		
	# restore original settings
	#l.setRendererSettings(original_rs)
	
	return layout
	

class TuMapDialog(QDialog, Ui_MapDialog):
	"""
	Class for producing flood maps.
	
	"""
	
	def __init__(self, TuView):
		QDialog.__init__(self)
		self.setupUi(self)
		self.tuView = TuView
		self.iface = TuView.iface
		self.project = TuView.project
		self.canvas = TuView.canvas
		self.pbDialogs = {}
		self.dialog2Plot = {}
		self.pbDialogsImage = {}
		self.rowNo2fntDialog = {}
		self.label2graphic = {}
		
		self.populateLayoutTab()
		self.populateExportMapsTab()
		
		self.cboPageSize.currentIndexChanged.connect(self.setPageSize)
		self.cboUnits.currentIndexChanged.connect(self.setPageSize)
		self.cboOrientation.currentIndexChanged.connect(self.setPageSize)
		self.sbWidth.editingFinished.connect(lambda: self.cboPageSize.setCurrentIndex(29))
		self.sbHeight.editingFinished.connect(lambda: self.cboPageSize.setCurrentIndex(29))
		self.pbResultName.clicked.connect(lambda: self.insertAutoText(auto_text='result name'))
		self.pbResultType.clicked.connect(lambda: self.insertAutoText(auto_text='result type'))
		self.pbWorkspaceLoc.clicked.connect(lambda: self.insertAutoText(auto_text='workspace'))
		self.pbMapNo.clicked.connect(lambda: self.insertAutoText(auto_text='map number'))
		self.pbDate.clicked.connect(lambda: self.insertAutoText(auto_text='date'))
		self.btnAddPlot.clicked.connect(self.addPlot)
		self.btnRemovePlot.clicked.connect(self.removePlot)
		self.btnPlotUp.clicked.connect(lambda event: self.movePlot(event, 'up'))
		self.btnPlotDown.clicked.connect(lambda event: self.movePlot(event, 'down'))
		self.btnAddImage.clicked.connect(self.addImage)
		self.btnRemoveImage.clicked.connect(self.removeImage)
		self.btnImageUp.clicked.connect(lambda event: self.moveImage(event, 'up'))
		self.btnImageDown.clicked.connect(lambda event: self.moveImage(event, 'down'))
		self.btnBrowseTemplate.clicked.connect(lambda: self.browse('load', "TUFLOW/animation_template", "QGIS Print Layout (*.qpt)", self.editTemplate))
		self.btnBrowseTemplateOut.clicked.connect(lambda: self.browse('location', 'TUFLOW/map_template_export', "", self.leTemplateOut))
		self.btnAddMap.clicked.connect(self.addMap)
		self.btnRemoveMap.clicked.connect(self.removeMaps)
		self.btnMapUp.clicked.connect(lambda event: self.moveMap(event, 'up'))
		self.btnMapDown.clicked.connect(lambda event: self.moveMap(event, 'down'))
		self.buttonBox.accepted.connect(self.check)
		self.pbPreview.clicked.connect(lambda: self.check(preview=True))
		
	def populateLayoutTab(self):
		"""Sets up Layout tab"""
		
		addIcon = QgsApplication.getThemeIcon('/symbologyAdd.svg')
		removeIcon = QgsApplication.getThemeIcon('/symbologyRemove.svg')
		upIcon = QgsApplication.getThemeIcon('/mActionArrowUp.svg')
		downIcon = QgsApplication.getThemeIcon('/mActionArrowDown.svg')
		folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
		
		self.setPageSize()
		
		self.btnAddPlot.setIcon(addIcon)
		self.btnRemovePlot.setIcon(removeIcon)
		self.btnPlotUp.setIcon(upIcon)
		self.btnPlotDown.setIcon(downIcon)
		self.tablePlots.horizontalHeader().setVisible(True)
		self.tableGraphics.horizontalHeader().setVisible(True)
		self.populateGraphics()
		
		self.btnAddImage.setIcon(addIcon)
		self.btnRemoveImage.setIcon(removeIcon)
		self.btnImageUp.setIcon(upIcon)
		self.btnImageDown.setIcon(downIcon)
		
		self.btnBrowseTemplate.setIcon(folderIcon)
		
	def populateExportMapsTab(self):
		"""Sets up Export Maps tab"""
		
		addIcon = QgsApplication.getThemeIcon('/symbologyAdd.svg')
		removeIcon = QgsApplication.getThemeIcon('/symbologyRemove.svg')
		upIcon = QgsApplication.getThemeIcon('/mActionArrowUp.svg')
		downIcon = QgsApplication.getThemeIcon('/mActionArrowDown.svg')
		folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
		
		self.btnAddMap.setIcon(addIcon)
		self.btnRemoveMap.setIcon(removeIcon)
		self.btnMapUp.setIcon(upIcon)
		self.btnMapDown.setIcon(downIcon)
		self.btnBrowseTemplateOut.setIcon(folderIcon)
	
	def browse(self, dialogType, key, fileType, lineEdit):
		"""
		Browse folder directory

		:param type: str browse type 'folder' or 'file'
		:param key: str settings key
		:param fileType: str file extension e.g. "AVI files (*.avi)"
		:param lineEdit: QLineEdit to be updated by browsing
		:return: void
		"""
		
		settings = QSettings()
		lastFolder = settings.value(key)
		startDir = None
		if lastFolder:  # if outFolder no longer exists, work backwards in directory until find one that does
			while lastFolder:
				if os.path.exists(lastFolder):
					startDir = lastFolder
					break
				else:
					lastFolder = os.path.dirname(lastFolder)
		if dialogType == 'save':
			f = QFileDialog.getSaveFileName(self, 'Ouput', startDir, fileType)[0]
		elif dialogType == 'load':
			f = QFileDialog.getOpenFileName(self, 'Import Template', startDir, fileType)[0]
		elif dialogType == 'image':
			f = QFileDialog.getOpenFileName(self, 'Image File', startDir, fileType)[0]
		elif dialogType == 'ffmpeg':
			f = QFileDialog.getOpenFileName(self, 'FFmpeg Location', startDir, fileType)[0]
		elif dialogType == 'location':
			f = QFileDialog.getExistingDirectory(self, 'Template Folder', startDir)
		elif dialogType == 'mesh':
			f = QFileDialog.getOpenFileName(self, 'Input File', startDir, fileType)[0]
		else:
			return
		if f:
			if type(lineEdit) is QLineEdit:
				lineEdit.setText(f)
			elif type(lineEdit) is QComboBox:
				lineEdit.addItem(f)
				lineEdit.setCurrentIndex(lineEdit.findText(f, Qt.MatchExactly))
			settings.setValue(key, f)
	
	def populateGraphics(self):
		"""
		Populates the graphics table with available TS Point, CS Line, or Flow Line objects that can be included in the
		animation map.

		:param checked: bool -> True means groupbox is checked on
		:return: void
		"""
		
		lines = self.tuView.tuPlot.tuRubberBand.rubberBands
		for i, line in enumerate(lines):
			rowNo = self.tableGraphics.rowCount()
			self.tableGraphics.setRowCount(rowNo + 1)
			self.addGraphicRowToTable('CS / LP Line {0}'.format(i + 1), rowNo)
			self.label2graphic['CS / LP Line {0}'.format(i + 1)] = line
		
		lines = self.tuView.tuPlot.tuFlowLine.rubberBands
		for i, line in enumerate(lines):
			rowNo = self.tableGraphics.rowCount()
			self.tableGraphics.setRowCount(rowNo + 1)
			self.addGraphicRowToTable('Flow Line {0}'.format(i + 1), rowNo)
			self.label2graphic['Flow Line {0}'.format(i + 1)] = line
		
		points = self.tuView.tuPlot.tuRubberBand.markerPoints
		for i, point in enumerate(points):
			rowNo = self.tableGraphics.rowCount()
			self.tableGraphics.setRowCount(rowNo + 1)
			self.addGraphicRowToTable('TS Point {0}'.format(i + 1), rowNo)
			self.label2graphic['TS Point {0}'.format(i + 1)] = point
	
	def addGraphicRowToTable(self, label, rowNo, status=True, userLabel=None):
		"""
		Create widget for graphic to insert into graphic table.

		:param label: str e.g. 'TS Point 1' or 'CS Line 1'
		:param rowNo: int row number in graphic options table of graphic being added
		:param checked: bool include graphic in animation
		:param userLabel: str defaults to label if None
		:return: void
		"""
		
		item = QTableWidgetItem(0)
		item.setText(label)
		item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
		if status:
			item.setCheckState(Qt.Checked)
		else:
			item.setCheckState(Qt.Unchecked)
		
		lineEdit = QLineEdit()
		lineEdit.setText(userLabel) if userLabel is not None else lineEdit.setText(label)
		lineEdit.setMaximumHeight(20)
		
		cbo = QComboBox()
		cbo.setMaximumHeight(20)
		cbo.setEditable(True)
		cbo.addItem('Left')
		cbo.addItem('Right')
		if 'TS' in label:
			cbo.addItem('Above')
			cbo.addItem('Below')
			cbo.addItem('Above-Left')
			cbo.addItem('Below-Left')
			cbo.addItem('Above-Right')
			cbo.addItem('Below-Right')
		
		pb = QPushButton()
		pb.setText('Text Properties')
		dialog = TextPropertiesDialog()
		self.rowNo2fntDialog[rowNo] = dialog
		pb.clicked.connect(lambda: dialog.exec_())
		
		self.tableGraphics.setItem(rowNo, 0, item)
		self.tableGraphics.setCellWidget(rowNo, 1, lineEdit)
		self.tableGraphics.setCellWidget(rowNo, 2, cbo)
		self.tableGraphics.setCellWidget(rowNo, 3, pb)
			
	def insertAutoText(self, event=None, auto_text=None):
		"""inserts text for auto text"""
		
		if auto_text == 'result name':
			self.labelInput.append('<<result_name>>')
		elif auto_text == 'result type':
			self.labelInput.append('<<result_type>> - <<result_time>>')
		elif auto_text == 'workspace':
			self.labelInput.append('<<workspace>>')
		elif auto_text == 'map number':
			self.labelInput.append('<<X>>')
		elif auto_text == 'date':
			self.labelInput.append('<<date>>')
	
	def plotItems(self, ptype, **kwargs):
		"""
		Returns a list of plot item labels and artists

		:param plotNo:
		:return:
		"""
		
		# deal with kwargs
		includeDuplicates = kwargs['include_duplicates'] if 'include_duplicates' in kwargs.keys() else False
		
		if ptype == 'Time Series':
			plotNo = 0
		elif ptype == 'CS / LP':
			plotNo = 1
		else:
			return [], []
		
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.tuView.tuPlot.plotEnumerator(plotNo)
		
		lines, labs = subplot.get_legend_handles_labels()
		axis = ['axis 1' for x in range(len(lines))]
		if isSecondaryAxis[0]:
			subplot2 = self.tuView.tuPlot.getSecondaryAxis(plotNo)
			lines2, labs2 = subplot2.get_legend_handles_labels()
			axis2 = ['axis 2' for x in range(len(lines2))]
		else:
			lines2, labs2, axis2 = [], [], []
		
		lines += lines2
		labs += labs2
		axis += axis2
		
		uniqLines, uniqLabs, uniqAxis = [], [], []
		for i, lab in enumerate(labs):
			if lab not in uniqLabs:
				uniqLabs.append(lab)
				uniqLines.append(lines[i])
				uniqAxis.append(axis[i])
		
		if includeDuplicates:
			return lines, labs, axis
		else:
			return uniqLines, uniqLabs, uniqAxis
	
	def addPlot(self, event=None, plotTypeTemplate=None, mcboPlotItemTemplate=None, cboPosTemplate=None,
	            pbTemplate=None):
		"""
		Add plot to QTableWidget

		:return: void
		"""
		
		self.tablePlots.setRowCount(self.tablePlots.rowCount() + 1)
		
		cboPlotType = QComboBox(self.tablePlots)
		cboPlotType.setEditable(True)
		cboPlotType.setMaximumHeight(20)
		cboPlotType.setMaximumWidth(175)
		cboPlotType.addItem('Time Series')
		cboPlotType.addItem('CS / LP')
		if plotTypeTemplate is None:
			cboPlotType.setCurrentIndex(self.tuView.tabWidget.currentIndex())
		else:
			cboPlotType.setCurrentIndex(plotTypeTemplate.currentIndex())
		
		mcboPlotItems = QgsCheckableComboBox(self.tablePlots)
		mcboPlotItems.setMaximumHeight(20)
		mcboPlotItems.setMaximumWidth(175)
		lines, labs, axis = self.plotItems(cboPlotType.currentText())
		mcboPlotItems.addItems(labs)
		if mcboPlotItemTemplate is not None:
			mcboPlotItems.setCheckedItems(mcboPlotItemTemplate.checkedItems())
		
		cboPos = QComboBox(self.tablePlots)
		cboPos.setEditable(True)
		cboPos.setMaximumHeight(20)
		cboPos.setMaximumWidth(175)
		cboPos.addItem('Top-Left')
		cboPos.addItem('Top-Right')
		cboPos.addItem('Bottom-Left')
		cboPos.addItem('Bottom-Right')
		if cboPosTemplate is not None:
			cboPos.setCurrentIndex(cboPosTemplate.currentIndex())
		
		pb = QPushButton(self.tablePlots)
		pb.setText('Properties')
		dialog = PlotProperties(self, cboPlotType, mcboPlotItems)
		if pbTemplate is not None:
			dialog.applyPrevious(pbTemplate)
		self.pbDialogs[pb] = dialog
		self.dialog2Plot[dialog] = [cboPlotType, mcboPlotItems, cboPos]
		pb.clicked.connect(lambda: dialog.setDefaults(self, cboPlotType.currentText(), mcboPlotItems.checkedItems(), static=True))
		pb.clicked.connect(lambda: dialog.exec_())
		
		self.tablePlots.setCellWidget(self.tablePlots.rowCount() - 1, 0, cboPlotType)
		self.tablePlots.setCellWidget(self.tablePlots.rowCount() - 1, 1, mcboPlotItems)
		self.tablePlots.setCellWidget(self.tablePlots.rowCount() - 1, 2, cboPos)
		self.tablePlots.setCellWidget(self.tablePlots.rowCount() - 1, 3, pb)
		
		cboPlotType.currentTextChanged.connect(lambda text: self.plotTypeChanged(text, mcboPlotItems))
	
	def removePlot(self):
		"""
		Remove plot item from QTableWidget

		:return: void
		"""
		
		selectionRange = self.tablePlots.selectedRanges()
		selectionRange = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRange]
		selectionRange = sum(selectionRange, [])
		col1 = []
		col2 = []
		col3 = []
		col4 = []
		if selectionRange:
			for i in range(self.tablePlots.rowCount()):
				self.tablePlots.cellWidget(i, 0).currentTextChanged.disconnect()
				self.tablePlots.cellWidget(i, 3).clicked.disconnect()
				pb = self.tablePlots.cellWidget(i, 3)
				if i not in selectionRange:
					col1.append(self.tablePlots.cellWidget(i, 0))
					col2.append(self.tablePlots.cellWidget(i, 1))
					col3.append(self.tablePlots.cellWidget(i, 2))
					dialog = self.pbDialogs[pb]
					col4.append(dialog)
				del self.pbDialogs[pb]
			self.tablePlots.setRowCount(0)
			for i in range(len(col1)):  # adding widgets directly back from the list caused QGIS to crash :(
				self.addPlot(plotTypeTemplate=col1[i], mcboPlotItemTemplate=col2[i], cboPosTemplate=col3[i],
				             pbTemplate=col4[i])
		else:
			pb = self.tablePlots.cellWidget(self.tablePlots.rowCount() - 1, 3)
			del self.pbDialogs[pb]
			self.tablePlots.setRowCount(self.tablePlots.rowCount() - 1)
	
	def movePlot(self, event=None, action='up'):
		""" Move plot item up or down in table. If multiple selected, only move first selection."""
		
		selectionRange = self.tablePlots.selectedRanges()
		selectionRange = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRange]
		selectionRange = sum(selectionRange, [])
		selection = selectionRange[0] if selectionRange else None
		col1 = []
		col2 = []
		col3 = []
		col4 = []
		if selection is not None:
			if selection == 0 and action == 'up':  # first entry so can't move up
				return
			elif selection == self.tablePlots.rowCount() - 1 and action == 'down':  # last entry so can't move down
				return
			elif action == 'down':
				newPos = selection + 1
			else:
				newPos = selection - 1
			for i in range(self.tablePlots.rowCount()):
				self.tablePlots.cellWidget(i, 0).currentTextChanged.disconnect()
				self.tablePlots.cellWidget(i, 3).clicked.disconnect()
				pb = self.tablePlots.cellWidget(i, 3)
				col1.append(self.tablePlots.cellWidget(i, 0))
				col2.append(self.tablePlots.cellWidget(i, 1))
				col3.append(self.tablePlots.cellWidget(i, 2))
				dialog = self.pbDialogs[pb]
				col4.append(dialog)
				del self.pbDialogs[pb]
			c1 = col1.pop(selection)
			c2 = col2.pop(selection)
			c3 = col3.pop(selection)
			c4 = col4.pop(selection)
			col1.insert(newPos, c1)
			col2.insert(newPos, c2)
			col3.insert(newPos, c3)
			col4.insert(newPos, c4)
			self.tablePlots.setRowCount(0)
			for i in range(len(col1)):
				self.addPlot(plotTypeTemplate=col1[i], mcboPlotItemTemplate=col2[i], cboPosTemplate=col3[i],
				             pbTemplate=col4[i])
			self.tablePlots.setCurrentCell(newPos, 0, QItemSelectionModel.Select)
			self.tablePlots.setCurrentCell(newPos, 1, QItemSelectionModel.Select)
			self.tablePlots.setCurrentCell(newPos, 2, QItemSelectionModel.Select)
			self.tablePlots.setCurrentCell(newPos, 3, QItemSelectionModel.Select)
	
	def plotTypeChanged(self, text, mcbo):
		"""
		Action when plot type is changed between Time Series and CS/ LP

		:return: void
		"""
		
		mcbo.clear()
		lines, labs, axis = self.plotItems(text)
		mcbo.addItems(labs)
	
	def addImage(self, event=None, widgetImageTemplate=None, cboPosTemplate=None, pbTemplate=None):
		"""
		Add image to image table.

		:return: void
		"""

		self.tableImages.setRowCount(self.tableImages.rowCount() + 1)
		
		folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
		btnBrowse = QToolButton(self.tableImages)
		btnBrowse.setIcon(folderIcon)
		btnBrowse.setToolTip('Image Location')
		
		leImage = QLineEdit(self.tableImages)
		leImage.setMaximumHeight(20)
		if widgetImageTemplate is not None:
			leImage.setText(widgetImageTemplate.layout().itemAt(1).widget().text())
		
		widget = QWidget(self.tableImages)
		hbox = QHBoxLayout()
		hbox.addWidget(btnBrowse)
		hbox.addWidget(leImage)
		hbox.setContentsMargins(0, 0, 0, 0)
		widget.setLayout(hbox)
		widget.setMaximumHeight(20)
		
		cboPos = QComboBox(self.tableImages)
		cboPos.setEditable(True)
		cboPos.setMaximumHeight(20)
		cboPos.setMaximumWidth(190)
		cboPos.addItem('Top-Left')
		cboPos.addItem('Top-Right')
		cboPos.addItem('Bottom-Left')
		cboPos.addItem('Bottom-Right')
		if cboPosTemplate is not None:
			cboPos.setCurrentIndex(cboPosTemplate.currentIndex())
		
		pb = QPushButton(self.tableImages)
		pb.setText('Properties')
		dialog = ImagePropertiesDialog()
		if pbTemplate is not None:
			dialog.applyPrevious(pbTemplate)
		self.pbDialogsImage[pb] = dialog
		pb.clicked.connect(lambda: dialog.exec_())
		
		self.tableImages.setCellWidget(self.tableImages.rowCount() - 1, 0, widget)
		self.tableImages.setCellWidget(self.tableImages.rowCount() - 1, 1, cboPos)
		self.tableImages.setCellWidget(self.tableImages.rowCount() - 1, 2, pb)
		
		btnBrowse.clicked.connect(lambda: self.browse('image', 'TUFLOW/map_image', "All Files(*)", leImage))
	
	def removeImage(self):
		"""
		Remove image from image table.

		:return: void
		"""
		
		selectionRange = self.tableImages.selectedRanges()
		selectionRange = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRange]
		selectionRange = sum(selectionRange, [])
		col1 = []
		col2 = []
		col3 = []
		if selectionRange:
			for i in range(self.tableImages.rowCount()):
				self.tableImages.cellWidget(i, 0).layout().itemAt(0).widget().clicked.disconnect()
				pb = self.tableImages.cellWidget(i, 2)
				if i not in selectionRange:
					col1.append(self.tableImages.cellWidget(i, 0))
					col2.append(self.tableImages.cellWidget(i, 1))
					dialog = self.pbDialogsImage[pb]
					col3.append(dialog)
				del self.pbDialogsImage[pb]
			self.tableImages.setRowCount(0)
			for i in range(len(col1)):  # adding widgets directly back from the list caused QGIS to crash :(
				self.addImage(widgetImageTemplate=col1[i], cboPosTemplate=col2[i], pbTemplate=col3[i])
		else:
			pb = self.tableImages.cellWidget(self.tableImages.rowCount() - 1, 2)
			del self.pbDialogsImage[pb]
			self.tableImages.setRowCount(self.tableImages.rowCount() - 1)
	
	def moveImage(self, event=None, action='up'):
		"""Move Image up or down in table."""
		
		selectionRange = self.tableImages.selectedRanges()
		selectionRange = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRange]
		selectionRange = sum(selectionRange, [])
		selection = selectionRange[0] if selectionRange else None
		col1 = []
		col2 = []
		col3 = []
		col4 = []
		if selection is not None:
			if selection == 0 and action == 'up':  # first entry so can't move up
				return
			elif selection == self.tableImages.rowCount() - 1 and action == 'down':  # last entry so can't move down
				return
			elif action == 'down':
				newPos = selection + 1
			else:
				newPos = selection - 1
			for i in range(self.tableImages.rowCount()):
				self.tableImages.cellWidget(i, 0).layout().itemAt(0).widget().clicked.disconnect()
				pb = self.tableImages.cellWidget(i, 2)
				col1.append(self.tableImages.cellWidget(i, 0))
				col2.append(self.tableImages.cellWidget(i, 1))
				dialog = self.pbDialogsImage[pb]
				col3.append(dialog)
				del self.pbDialogsImage[pb]
			c1 = col1.pop(selection)
			c2 = col2.pop(selection)
			c3 = col3.pop(selection)
			col1.insert(newPos, c1)
			col2.insert(newPos, c2)
			col3.insert(newPos, c3)
			self.tableImages.setRowCount(0)
			for i in range(len(col1)):
				self.addImage(widgetImageTemplate=col1[i], cboPosTemplate=col2[i], pbTemplate=col3[i])
			self.tableImages.setCurrentCell(newPos, 0, QItemSelectionModel.Select)
			self.tableImages.setCurrentCell(newPos, 1, QItemSelectionModel.Select)
			self.tableImages.setCurrentCell(newPos, 2, QItemSelectionModel.Select)
			
	def addMap(self, event=None, inputResultTemplate=None, cboScalarTemplate=None, cboVectorTemplate=None,
	           cboTimeTemplate=None, outputWidgetTemplate=None):
		"""Add map to export list"""
		
		folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
		
		# Available Results - user can choose a location through file explorer
		btnBrowseInput = QToolButton(self.tableMaps)
		btnBrowseInput.setIcon(folderIcon)
		btnBrowseInput.setToolTip('Input Result File')
		cboResult = QComboBox(self.tableMaps)
		cboResult.setEditable(True)
		for i in range(self.tuView.OpenResults.count()):
			item = self.tuView.OpenResults.item(i)
			cboResult.addItem(item.text())
		if inputResultTemplate is not None:
			cboResult.setCurrentText(inputResultTemplate.layout().itemAt(1).widget().currentText())
		inputWidget = QWidget(self.tableMaps)
		hbox = QHBoxLayout()
		hbox.addWidget(btnBrowseInput)
		hbox.addWidget(cboResult)
		hbox.setContentsMargins(0, 0, 0, 0)
		inputWidget.setLayout(hbox)
		inputWidget.setMaximumHeight(20)
		btnBrowseInput.clicked.connect(lambda: self.browse('mesh', 'TUFLOW/map_input', 'Mesh Layer (*.xmdf *.dat *.sup *.2dm)', cboResult))
		
		# Available result types
		scalarTypes, vectorTypes = getResultTypes(self.tuView.tuResults.results, cboResult.currentText())
		cboScalar = QComboBox(self.tableMaps)
		cboScalar.setEditable(True)
		cboScalar.addItem('-None-')
		cboScalar.addItems(scalarTypes)
		if cboScalarTemplate is not None:
			cboScalar.setCurrentText(cboScalarTemplate.currentText())
		cboVector = QComboBox(self.tableMaps)
		cboVector.setEditable(True)
		cboVector.addItem('-None-')
		cboVector.addItems(vectorTypes)
		if cboVectorTemplate is not None:
			cboVector.setCurrentText(cboVectorTemplate.currentText())
		
		# Available times (including max)
		times = getTimes(self.tuView.tuResults.results, cboResult.currentText(), cboScalar.currentText(), cboVector.currentText())
		cboTime = QComboBox(self.tableMaps)
		cboTime.setEditable(True)
		cboTime.addItems(times)
		if cboTimeTemplate is not None:
			cboTime.setCurrentText(cboTimeTemplate.currentText())
		
		cboResult.currentIndexChanged.connect(lambda: self.updateMapRow(cboResult, cboScalar, cboVector, cboTime, cboResult))
		cboScalar.currentIndexChanged.connect(lambda: self.updateMapRow(cboResult, cboScalar, cboVector, cboTime, cboScalar))
		cboVector.currentIndexChanged.connect(lambda: self.updateMapRow(cboResult, cboScalar, cboVector, cboTime, cboVector))
		
		# output
		btnBrowseOutput = QToolButton(self.tableMaps)
		btnBrowseOutput.setIcon(folderIcon)
		btnBrowseOutput.setToolTip('Output Map')
		leOutput = QLineEdit(self.tableMaps)
		leOutput.setMaximumHeight(20)
		if outputWidgetTemplate is not None:
			leOutput.setText(outputWidgetTemplate.layout().itemAt(1).widget().text())
		outputWidget = QWidget(self.tableMaps)
		hbox = QHBoxLayout()
		hbox.addWidget(btnBrowseOutput)
		hbox.addWidget(leOutput)
		hbox.setContentsMargins(0, 0, 0, 0)
		outputWidget.setLayout(hbox)
		outputWidget.setMaximumHeight(20)
		exportTypes = "PDF (*.pdf *.PDF);;BMP format (*.bmp *.BMP);;CUR format (*.cur *.CUR);;ICNS format (*.icns *.ICNS);;" \
		              "ICO format (*.ico *.ICO);;JPEG format (*.jpeg *.JPEG);;JPG format (*.jpg *.JPG);;PBM format (*.pbm *,PBM);;" \
		              "PGM format (*.pgm *.PGM);;PNG format (*.png *.PNG);;PPM format (*.ppm *.PPM);;SVG format (*.svg *.SVG);;" \
		              "TIF format (*.tif *.TIF);;TIFF format (*.tiff *.TIFF);;WBMP format (*.wbmp *.WBMP);;WEBP (*.webp *.WEBP);;" \
		              "XBM format (*.xbm *.XBM);;XPM format (*.xpm *.XPM)"
		btnBrowseOutput.clicked.connect(lambda: self.browse('save', 'TUFLOW/map_output', exportTypes, leOutput))
		
		# add to table
		n = self.tableMaps.rowCount()
		self.tableMaps.setRowCount(n + 1)
		self.tableMaps.setCellWidget(n, 0, inputWidget)
		self.tableMaps.setCellWidget(n, 1, cboScalar)
		self.tableMaps.setCellWidget(n, 2, cboVector)
		self.tableMaps.setCellWidget(n, 3, cboTime)
		self.tableMaps.setCellWidget(n, 4, outputWidget)
		
	def updateMapRow(self, cboResult, cboScalar, cboVector, cboTime, changed):
		"""Updates row in map table if one of the combo boxes is changed."""
		
		if changed == cboResult:
			prevScalar = cboScalar.currentText()
			prevVector = cboVector.currentText()
			scalarTypes, vectorTypes = getResultTypes(self.tuView.tuResults.results, cboResult.currentText())
			cboScalar.clear()
			cboVector.clear()
			cboScalar.addItem('-None-')
			cboVector.addItem('-None-')
			cboScalar.addItems(scalarTypes)
			cboVector.addItems(vectorTypes)
			for i in range(cboScalar.count()):
				if cboScalar.itemText(i) == prevScalar:
					cboScalar.setCurrentIndex(i)
			for i in range(cboVector.count()):
				if cboVector.itemText(i) == prevVector:
					cboVector.setCurrentIndex(i)
			
		if changed == cboResult or changed == cboScalar or changed == cboVector:
			prevTime = cboTime.currentText()
			times = getTimes(self.tuView.tuResults.results, cboResult.currentText(), cboScalar.currentText(), cboVector.currentText())
			cboTime.clear()
			cboTime.addItems(times)
			for i in range(cboTime.count()):
				if cboTime.itemText(i) == prevTime:
					cboTime.setCurrentIndex(i)
					
	def removeMaps(self):
		"""Remove map from table."""

		selectionRange = self.tableMaps.selectedRanges()
		selectionRange = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRange]
		selectionRange = sum(selectionRange, [])
		col1 = []
		col2 = []
		col3 = []
		col4 = []
		col5 = []
		if selectionRange:
			for i in range(self.tableMaps.rowCount()):
				self.tableMaps.cellWidget(i, 0).layout().itemAt(0).widget().clicked.disconnect()
				self.tableMaps.cellWidget(i, 0).layout().itemAt(1).widget().currentIndexChanged.disconnect()
				self.tableMaps.cellWidget(i, 1).currentIndexChanged.disconnect()
				self.tableMaps.cellWidget(i, 2).currentIndexChanged.disconnect()
				self.tableMaps.cellWidget(i, 4).layout().itemAt(0).widget().clicked.disconnect()
				if i not in selectionRange:
					col1.append(self.tableMaps.cellWidget(i, 0))
					col2.append(self.tableMaps.cellWidget(i, 1))
					col3.append(self.tableMaps.cellWidget(i, 2))
					col4.append(self.tableMaps.cellWidget(i, 3))
					col5.append(self.tableMaps.cellWidget(i, 4))
			self.tableMaps.setRowCount(0)
			for i in range(len(col1)):  # adding widgets directly back from the list caused QGIS to crash :(
				self.addMap(inputResultTemplate=col1[i], cboScalarTemplate=col2[i], cboVectorTemplate=col3[i], cboTimeTemplate=col4[i], outputWidgetTemplate=col5[i])
		else:
			self.tableMaps.setRowCount(self.tableMaps.rowCount() - 1)
			
	def moveMap(self, event=None, action='up'):
		"""Move position of selected map in table. Options 'up' or 'down'."""
		
		selectionRange = self.tableMaps.selectedRanges()
		selectionRange = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRange]
		selectionRange = sum(selectionRange, [])
		selection = selectionRange[0] if selectionRange else None
		col1 = []
		col2 = []
		col3 = []
		col4 = []
		col5 = []
		if selectionRange:
			if selection == 0 and action == 'up':  # first entry so can't move up
				return
			elif selection == self.tableMaps.rowCount() - 1 and action == 'down':  # last entry so can't move down
				return
			elif action == 'down':
				newPos = selection + 1
			else:
				newPos = selection - 1
			for i in range(self.tableMaps.rowCount()):
				self.tableMaps.cellWidget(i, 0).layout().itemAt(0).widget().clicked.disconnect()
				self.tableMaps.cellWidget(i, 0).layout().itemAt(1).widget().currentIndexChanged.disconnect()
				self.tableMaps.cellWidget(i, 1).currentIndexChanged.disconnect()
				self.tableMaps.cellWidget(i, 2).currentIndexChanged.disconnect()
				self.tableMaps.cellWidget(i, 4).layout().itemAt(0).widget().clicked.disconnect()
				col1.append(self.tableMaps.cellWidget(i, 0))
				col2.append(self.tableMaps.cellWidget(i, 1))
				col3.append(self.tableMaps.cellWidget(i, 2))
				col4.append(self.tableMaps.cellWidget(i, 3))
				col5.append(self.tableMaps.cellWidget(i, 4))
			c1 = col1.pop(selection)
			c2 = col2.pop(selection)
			c3 = col3.pop(selection)
			c4 = col4.pop(selection)
			c5 = col5.pop(selection)
			col1.insert(newPos, c1)
			col2.insert(newPos, c2)
			col3.insert(newPos, c3)
			col4.insert(newPos, c4)
			col5.insert(newPos, c5)
			self.tableMaps.setRowCount(0)
			for i in range(len(col1)):
				self.addMap(inputResultTemplate=col1[i], cboScalarTemplate=col2[i], cboVectorTemplate=col3[i],
				            cboTimeTemplate=col4[i], outputWidgetTemplate=col5[i])
			self.tableMaps.setCurrentCell(newPos, 0, QItemSelectionModel.Select)
			self.tableMaps.setCurrentCell(newPos, 1, QItemSelectionModel.Select)
			self.tableMaps.setCurrentCell(newPos, 2, QItemSelectionModel.Select)
			self.tableMaps.setCurrentCell(newPos, 4, QItemSelectionModel.Select)
			self.tableMaps.setCurrentCell(newPos, 4, QItemSelectionModel.Select)
			
	def updateProgress(self, i, cnt):
		""" callback from routine """
		self.progress.setMaximum(cnt)
		self.progress.setValue(i)
		qApp.processEvents()
	
	def check(self, preview=False):
		"""Pre run checks."""
		
		# check image locations exist
		for i in range(self.tableImages.rowCount()):
			path = self.tableImages.cellWidget(i, 0).layout().itemAt(1).widget().text()
			if not os.path.exists(path):
				QMessageBox.information(self, 'Input Error', 'Cannot find file: {0}'.format(path))
				return
				
		# check if save templates is ticked, file location has been specified
		if self.cbSaveTemplates.isChecked():
			if not self.leTemplateOut.text():
				QMessageBox.information(self, 'Input Error', 'Must specify template outfolder if saving templates')
				return
				
		# check all the result and type selections make sense
		if not self.tableMaps.rowCount():
			QMessageBox.information(self, 'Input Error', 'No Maps Added')
			return
		for i in range(self.tableMaps.rowCount()):
			result = self.tableMaps.cellWidget(i, 0).layout().itemAt(1).widget().currentText()
			if not result:
				QMessageBox.information(self, 'Input Error', 'Row {0} - Must specify input result'.format(i + 1))
				return
			if result not in self.tuView.tuResults.results:
				if not os.path.exists(result):
					QMessageBox.information(self, 'Input Error',
					                        'Row {0} - cannot find result: {1}'.format(i + 1, result))
					return
			scalar = self.tableMaps.cellWidget(i, 1).currentText()
			vector = self.tableMaps.cellWidget(i, 2).currentText()
			if scalar == '-None-' and vector == '-None-':
				QMessageBox.information(self, 'Input Error',
				                        'Row {0} - must choose at least one scalar or vector result'.format(i + 1))
				return
			time = self.tableMaps.cellWidget(i, 3).currentText()
			if not time:
				QMessageBox.information(self, 'Input Error', 'Row {0} - must specify a timestep'.format(i + 1))
				return
			output = self.tableMaps.cellWidget(i, 4).layout().itemAt(1).widget().text()
			if not output:
				QMessageBox.information(self, 'Input Error', 'Row {0} - Must specify an output path'.format(i + 1))
				return
		
		self.run(preview)
		
	def run(self, preview):
		"""run tool"""
		
		if not preview:
			self.buttonBox.setEnabled(False)  # disable button box so users know something is happening
			QApplication.setOverrideCursor(Qt.WaitCursor)
			
		# save plot settings so line colours won't vary over time
		self.tuView.tuPlot.setNewPlotProperties(0)
		self.tuView.tuPlot.setNewPlotProperties(1)
		
		# get page properties
		conv = 1 if self.cboUnits.currentText() == 'mm' else 25.4
		w = self.sbWidth.value() * conv
		h = self.sbHeight.value() * conv
		
		# set all results inactive
		for i in range(self.tuView.OpenResults.count()):
			item = self.tuView.OpenResults.item(i)
			item.setSelected(False)
		self.tuView.tuResults.tuResults2D.activeMeshLayers = []
		
		# Get Map Layout properties
		legendProp = {}
		if self.groupLegend.isChecked():
			legendProp['label'] = self.labelLegend.text()
			legendProp['font'] = self.fbtnLegend.currentFont()
			legendProp['font colour'] = self.colorLegendText.color()
			legendProp['background'] = self.cbLegendBackground.isChecked()
			legendProp['background color'] = self.colorLegendBackground.color()
			legendProp['frame'] = self.cbLegendFrame.isChecked()
			legendProp['frame color'] = self.colorLegendFrame.color()
			legendProp['position'] = self.cboPosLegend.currentIndex()
		scaleBarProp = {}
		if self.groupScaleBar.isChecked():
			scaleBarProp['font'] = self.fbtnScaleBar.currentFont()
			scaleBarProp['font color'] = self.colorScaleBarText.color()
			scaleBarProp['background'] = self.cbScaleBarBackground.isChecked()
			scaleBarProp['background color'] = self.colorScaleBarBackground.color()
			scaleBarProp['frame'] = self.cbScaleBarFrame.isChecked()
			scaleBarProp['frame color'] = self.colorScaleBarFrame.color()
			scaleBarProp['position'] = self.cboPosScaleBar.currentIndex()
		northArrowProp = {}
		if self.groupNorthArrow.isChecked():
			northArrowProp['background'] = self.cbNorthArrowBackground.isChecked()
			northArrowProp['background color'] = self.colorNorthArrowBackground.color()
			northArrowProp['frame'] = self.cbNorthArrowFrame.isChecked()
			northArrowProp['frame color'] = self.colorNorthArrowFrame.color()
			northArrowProp['position'] = self.cboPosNorthArrow.currentIndex()
		labelProp = {}
		if self.groupLabel.isChecked():
			#labelProp['label'] = self.labelInput.toPlainText()
			labelProp['font'] = self.fbtnLabel.currentFont()
			labelProp['font colour'] = self.colorLabelText.color()
			labelProp['background'] = self.cbLabelBackground.isChecked()
			labelProp['background color'] = self.colorLabelBackground.color()
			labelProp['frame'] = self.cbLabelFrame.isChecked()
			labelProp['frame color'] = self.colorLabelFrame.color()
			labelProp['position'] = self.cboPosLabel.currentIndex()
		layout = {}
		if self.radLayoutDefault.isChecked():
			layout['type'] = 'default'
			layout['file'] = None
			if self.groupLegend.isChecked():
				layout['legend'] = legendProp
			if self.groupScaleBar.isChecked():
				layout['scale bar'] = scaleBarProp
			if self.groupNorthArrow.isChecked():
				layout['north arrow'] = northArrowProp
		else:
			layout['type'] = 'file'
			layout['file'] = self.editTemplate.text()
		if self.groupLabel.isChecked():
			layout['title'] = labelProp
			
		# Get Plot Data
		if self.groupPlot.isChecked():
			plot = {}
			plotCount = 0
			for i in range(self.tablePlots.rowCount()):
				plotDict = {}
				plotDict['labels'] = self.tablePlots.cellWidget(i, 1).checkedItems()
				plotDict['type'] = self.tablePlots.cellWidget(i, 0).currentText()
				plotDict['position'] = self.tablePlots.cellWidget(i, 2).currentIndex()
				plotDict['properties'] = self.pbDialogs[self.tablePlots.cellWidget(i, 3)]
				plot[plotCount] = plotDict
				plotCount += 1
			if plot:
				layout['plots'] = plot
			graphics = {}
			for i in range(self.tableGraphics.rowCount()):
				cb = self.tableGraphics.item(i, 0)
				if cb.checkState() == Qt.Checked:
					graphicDict = {}
					label = self.tableGraphics.item(i, 0)
					graphic = self.label2graphic[label.text()]
					userLabel = self.tableGraphics.cellWidget(i, 1).text()
					position = self.tableGraphics.cellWidget(i, 2).currentText()
					font = self.rowNo2fntDialog[i]
					graphicDict['user label'] = userLabel
					graphicDict['position'] = position
					graphicDict['font'] = font.fntButton.currentFont()
					graphicDict['font colour'] = font.fntColor.color()
					graphicDict['background'] = font.cbBackground.isChecked()
					graphicDict['background color'] = font.backgroundColor.color()
					graphicDict['frame'] = font.cbFrame.isChecked()
					graphicDict['frame color'] = font.frameColor.color()
					if 'TS' in label.text():
						graphicDict['type'] = 'marker'
					elif 'CS' in label.text():
						graphicDict['type'] = 'rubberband profile'
					else:
						graphicDict['type'] = 'rubberband flow'
					graphics[graphic] = graphicDict
			if graphics:
				layout['graphics'] = graphics
		
		# Get Image Data
		if self.groupImages.isChecked():
			image = {}
			imageCount = 0
			for i in range(self.tableImages.rowCount()):
				imageDict = {
					'source': self.tableImages.cellWidget(i, 0).layout().itemAt(1).widget().text(),
					'position': self.tableImages.cellWidget(i, 1).currentIndex(),
					'properties': self.pbDialogsImage[self.tableImages.cellWidget(i, 2)]
				}
				image[imageCount] = imageDict
				imageCount += 1
			layout['images'] = image
			
		prog = lambda i, count: self.updateProgress(i, count)  # progress bar
		
		pageMargin = (self.sbPageMarginLeft.value(), self.sbPageMarginRight.value(),
		              self.sbPageMarginTop.value(), self.sbPageMarginBottom.value())
		# put collected data into dictionary for easy access later
		d = {'img_size': (w, h),
		     'extent': self.canvas.extent(),
		     'crs': self.canvas.mapSettings().destinationCrs(),
		     'layout': layout,
		     'dpi': self.sbDpi.value(),
		     'frame': self.cbPageFrame.isChecked(),
		     'frame color': self.colorPageFrame.color(),
		     'frame thickness': self.sbPageFrameThickness.value(),
		     'page margin': pageMargin
		     }
		
		count = self.tableMaps.rowCount()
		for i in range(count):
			d['map number'] = i
			prog(i, count)
			
			# outfile
			path = self.tableMaps.cellWidget(i, 4).layout().itemAt(1).widget().text()
			d['imgfile'] = path
			
			# result layer
			layer = self.tableMaps.cellWidget(i, 0).layout().itemAt(1).widget().currentText()
			if layer not in self.tuView.tuResults.results:
				imported = self.tuView.tuMenuBar.tuMenuFunctions.load2dResults(result_2D=[[layer]])
				if not imported:
					continue
				layer = tuflowqgis_find_layer(self.tuView.OpenResults.item(self.tuView.OpenResults.count() - 1).text())
				d['rendered'] = False
			else:
				layer = tuflowqgis_find_layer(layer)
				d['rendered'] = True
			self.tuView.tuResults.tuResults2D.activeMeshLayers = []
			self.tuView.tuResults.tuResults2D.activeMeshLayers.append(layer)
			d['layer'] = layer
				
			# get maplayers - only include the one mesh layer
			layerOrder = self.canvas.layers()
			layers = []
			for name, mapLayer in QgsProject.instance().mapLayers().items():
				if mapLayer.type() == 3:
					if mapLayer == layer:
						layers.append(mapLayer)
				else:
					layers.append(mapLayer)
			layersOrdered = []
			for l in layerOrder:
				if l in layers:
					layersOrdered.append(l)
			for l in layers:
				if l not in layersOrdered:
					layersOrdered.insert(0, l)
			d['layers'] = layersOrdered
			
			# uncheck unwanted mesh layers in layers panel
			legint = self.tuView.project.layerTreeRoot()
			# grab all nodes that are QgsMapLayers - get to node bed rock i.e. not a group
			nodes = []
			for item in legint.children():
				items = [item]
				while items:
					it = items[0]
					if it.children():
						items += it.children()
					else:
						nodes.append(it)
					items = items[1:]
			# now turn off all nodes that are mesh layers that are not the one we are interested in
			for node in nodes:
				# turn on node visibility for all items
				# so we can get the corresponding map layer
				# but record visibility status and turn off
				# again if it's not the mesh layer we're interested it
				if node.checkedLayers():
					visible = True
				else:
					visible = False
					node.setItemVisibilityChecked(True)
				ml = node.checkedLayers()[0] if node.checkedLayers() else False
				if ml:
					if ml.type() == 3:  # is a mesh layer
						if ml == layer:  # is the layer we're interested in
							node.setItemVisibilityChecked(True)
						else:  # is NOT the mesh layer we're interested in
							node.setItemVisibilityChecked(False)
					else:
						node.setItemVisibilityChecked(visible)
			
			# label text
			text = self.labelInput.toPlainText()
			result = layer.name()
			scalar = self.tableMaps.cellWidget(i, 1).currentText()
			vector = self.tableMaps.cellWidget(i, 2).currentText()
			time = self.tableMaps.cellWidget(i, 3).currentText()
			template = ''
			if self.cbSaveTemplates.isChecked():
				template = self.leTemplateOut.text()
			label = createText(text, result, scalar, vector, time, path, template, self.project, i + 1)
			if self.groupLabel.isChecked():
				d['layout']['title']['label'] = label
				
			# active scalar and vector index
			if time.lower() != 'max':
				time = time.split(':')
				time = float(time[0]) + float(time[1]) / 60 + float(time[2]) / 3600
				d['time'] = time
			else:
				d['time'] = -99999
				scalar += '/Maximums'
				vector += '/Maximums'
				time = 0.0
			scalarInd = -1
			vectorInd = -1
			for i in range(layer.dataProvider().datasetGroupCount()):
				if str(layer.dataProvider().datasetGroupMetadata(i).name()).lower() == scalar.lower():
					scalarInd = i
				if str(layer.dataProvider().datasetGroupMetadata(i).name()).lower() == vector.lower():
					vectorInd = i
			asd = QgsMeshDatasetIndex(-1, 0)
			for i in range(layer.dataProvider().datasetCount(scalarInd)):
				ind = QgsMeshDatasetIndex(scalarInd, i)
				if layer.dataProvider().datasetMetadata(ind).time() == time:
					asd = ind
			avd = QgsMeshDatasetIndex(-1, 0)
			for i in range(layer.dataProvider().datasetCount(vectorInd)):
				ind = QgsMeshDatasetIndex(vectorInd, i)
				if layer.dataProvider().datasetMetadata(ind).time() == time:
					avd = ind
			d['scalar index'] = asd
			d['vector index'] = avd
			
			for pb, dialog in self.pbDialogs.items():
				dialog.setDefaults(self, self.dialog2Plot[dialog][0].currentText(),
				                   self.dialog2Plot[dialog][1].checkedItems(), static=True)
			
			self.layout = makeMap(d, self.iface, prog, self, preview, i)
			
			if preview:
				self.iface.openLayoutDesigner(layout=self.layout)
				return
			
			if self.cbSaveTemplates.isChecked():
				folder = self.leTemplateOut.text()
				name = os.path.splitext(os.path.basename(path))[0] + '.qpt'
				templateFile = os.path.join(folder, name)
				
			
		
		QApplication.restoreOverrideCursor()
		self.updateProgress(0, 1)
		self.buttonBox.setEnabled(True)
		self.accept()
	
	def setPageSize(self):
		"""populate page dimensions based on size"""
		
		pageDict = {
			'A0': (1189.0, 841.0),
			'A1': (841.0, 594.0),
			'A2': (594.0, 420.0),
			'A3': (420.0, 297.0),
			'A4': (297.0, 210.0),
			'A5': (210.0, 148.0),
			'A6': (148.0, 105.0),
			'B0': (1414.0, 1000.0),
			'B1': (1000.0, 707.0),
			'B2': (707.0, 500.0),
			'B3': (500.0, 353.0),
			'B4': (353.0, 250.0),
			'B5': (250.0, 176.0),
			'B6': (176.0, 125.0),
			'Legal': (355.6, 215.9),
			'Letter': (279.4, 215.9),
			'ANSI A': (279.4, 215.9),
			'ANSI B': (431.8, 279.4),
			'ANSI C': (558.8, 431.8),
			'ANSI D': (863.6, 558.8),
			'ANSI E': (1117.6, 863.6),
			'Arch A': (304.8, 228.6),
			'Arch B': (457.2, 304.8),
			'Arch C': (609.6, 457.2),
			'Arch D': (914.4, 609.6),
			'Arch E': (1219.2, 914.4),
			'Arch E1': (1066.8, 762.0),
			'Arch E2': (965.0, 660.0),
			'Arch E3': (991.0, 686.0),
			'Custom': (1, 1)
		}
		
		conv = 1 if self.cboUnits.currentText() == 'mm' else 25.4
		
		page = self.cboPageSize.currentText()
		if page != 'Custom':
			if self.cboOrientation.currentText() == 'Portrait':
				x = pageDict[page][1] if page in pageDict else 1
				y = pageDict[page][0] if page in pageDict else 1
			else:
				x = pageDict[page][0] if page in pageDict else 1
				y = pageDict[page][1] if page in pageDict else 1
		
			self.sbWidth.setValue(x / conv)
			self.sbHeight.setValue(y / conv)