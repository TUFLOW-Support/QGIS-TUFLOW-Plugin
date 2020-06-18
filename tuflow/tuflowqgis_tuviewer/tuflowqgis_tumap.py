import os, sys
import tempfile
import shutil
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtXml import QDomDocument
from qgis.core import *
from qgis.gui import *
from ui_map_dialog import Ui_MapDialog
from MapExportImportDialog import Ui_MapExportImportDialog
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuanimation import (ImagePropertiesDialog, PlotProperties,
                                                               TextPropertiesDialog, prepare_composition,
                                                               prepare_composition_from_template, createText)
from tuflow.tuflowqgis_library import (tuflowqgis_find_layer, convertTimeToFormattedTime, convertFormattedTimeToTime,
                                       browse)
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesults import TuResults
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesults2d import TuResults2D



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
			if '_ts' not in rtype and '_lp' not in rtype and '_particles' not in rtype:
				t = rtype.split('/')[0].strip()
				for key, item in ts['times'].items():
					if item[1] == 1:
						if t not in scalarTypes:
							scalarTypes.append(t)
					elif item[1] == 2:
						if t not in vectorTypes:
							vectorTypes.append(t)
					break
						
	return scalarTypes, vectorTypes


def getTimes(results, layer, stype, vtype, units='h', xAxisDates=False, tuResults=None):
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
				if TuResults.isMaximumResultType(rtype):
					t = TuResults.stripMaximumName(rtype)
					if t == typ:
						if 'Max' not in times:
							times.insert(0, 'Max')
				else:
					for key, item in ts['times'].items():
						x = item[0]
						if x == -99999:
							if 'Max' not in times:
								times.insert(0, 'Max')
						else:
							#time = '{0:02d}:{1:02.0f}:{2:05.2f}'.format(int(x), (x - int(x)) * 60, (x - int(x) - (x - int(x))) * 3600)
							if xAxisDates:
								if tuResults is not None:
									if x in tuResults.time2date:
										time = tuResults.time2date[x]
										time = tuResults._dateFormat.format(time)
							else:
								time = convertTimeToFormattedTime(x, unit=units)
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

	# get version
	qv = Qgis.QGIS_VERSION_INT
	
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
	tuResults = cfg['turesults']
	
	# store original values
	#original_rs = l.rendererSettings()
	
	# render - take settings from first render and use for subsequent renders

	rs = l.rendererSettings()
	# new api for 3.14
	setActiveScalar, setActiveVector = TuResults2D.meshRenderVersion(rs)


	asd = cfg['scalar index']
	if asd:
		#rs.setActiveScalarDataset(asd)
		#if iteration == 0 or 'scalar settings' not in cfg:
		#	cfg['scalar settings'] = rs.scalarSettings(asd.group())
		rs.setScalarSettings(asd.group(), cfg['rendering'][cfg['active scalar']])
		if qv >= 31300:
			asd = asd.group()
		setActiveScalar(asd)
	avd = cfg['vector index']
	if avd:
		# rs.setActiveVectorDataset(avd)
		if iteration == 0 or 'vector settings' not in cfg:
			cfg['vector settings'] = rs.vectorSettings(avd.group())
		rs.setVectorSettings(avd.group(), cfg['vector settings'])
		if qv >= 31300:
			avd = avd.group()
		setActiveVector(avd)
	l.setRendererSettings(rs)
	
	timetext = convertTimeToFormattedTime(time, unit=dialog.tuView.tuOptions.timeUnits)
	if dialog is not None:
		if dialog.tuView.tuOptions.xAxisDates:
			if time in dialog.tuView.tuResults.time2date:
				timetext = dialog.tuView.tuResults.time2date[time]
				timetext = dialog.tuView.tuResults._dateFormat.format(timetext)
	cfg['time text'] = timetext
	
	# Prepare layout
	layout = QgsPrintLayout(QgsProject.instance())
	layout.initializeDefaults()
	layout.setName('tuflow')

	if layoutcfg['type'] == 'file':
		prepare_composition_from_template(layout, cfg, time, dialog, os.path.dirname(imgfile), False, False, layers,
		                                  tuResults=tuResults, meshLayer=l)
	else:
		layout.renderContext().setDpi(dpi)
		layout.setUnits(QgsUnitTypes.LayoutMillimeters)
		main_page = layout.pageCollection().page(0)
		main_page.setPageSize(QgsLayoutSize(w,  h, QgsUnitTypes.LayoutMillimeters))
		prepare_composition(layout, time, cfg, layoutcfg, extent, layers, crs, os.path.dirname(imgfile), dialog,
		                    False, False, tuResults=tuResults, meshLayer=l)
		
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
	if not preview:
		if ext.lower() == '.pdf':
			res = layout_exporter.exportToPdf(imgfile, pdf_export_settings)
		elif ext.lower() == '.svg':
			res = layout_exporter.exportToSvg(imgfile, svg_export_settings)
		else:
			res = layout_exporter.exportToImage(imgfile, image_export_settings)
		
	# delete plot images
	#if 'plots' in layoutcfg:
	#	for plot in layoutcfg['plots']:
	#		source = layoutcfg['plots'][plot]['source']
	#		os.remove(source)
		
	# restore original settings
	#l.setRendererSettings(original_rs)
	
	return layout
	

class TuMapDialog(QDialog, Ui_MapDialog):
	"""
	Class for producing flood maps.
	
	"""
	
	INSERT_BEFORE = 0
	INSERT_AFTER = 1
	
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
		self.mapTableRows = []
		self.mapTableRowItems = []
		self.plotTableRows = []
		self.plotTableRowItems = []
		self.imageTableRows = []
		
		self.populateLayoutTab()
		self.populateExportMapsTab()

		self.tableMaps.horizontalHeader().setStretchLastSection(True)
		self.tablePlots.horizontalHeader().setStretchLastSection(True)
		self.tableGraphics.horizontalHeader().setStretchLastSection(True)
		self.tableImages.horizontalHeader().setStretchLastSection(True)
		self.tableMaps.horizontalHeader().setCascadingSectionResizes(True)
		self.tablePlots.horizontalHeader().setCascadingSectionResizes(True)
		self.tableGraphics.horizontalHeader().setCascadingSectionResizes(True)
		self.tableImages.horizontalHeader().setCascadingSectionResizes(True)
		self.tableImages.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
		self.tablePlots.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
		
		total_width = self.tablePlots.verticalHeader().width() + self.tablePlots.horizontalHeader().length() + self.tablePlots.frameWidth() * 2
		primarywidth = 175.
		subwidth = (total_width - primarywidth) / (self.tablePlots.columnCount() - 1)
		self.tablePlots.setColumnWidth(0, subwidth)
		self.tablePlots.setColumnWidth(1, primarywidth)
		self.tablePlots.setColumnWidth(2, subwidth)
		self.tablePlots.setColumnWidth(3, subwidth)
		
		total_width = self.tableGraphics.verticalHeader().width() + self.tableGraphics.horizontalHeader().length() + self.tableGraphics.frameWidth() * 2
		primarywidth = 175.
		subwidth = (total_width - primarywidth) / (self.tableGraphics.columnCount() - 1)
		self.tableGraphics.setColumnWidth(0, subwidth)
		self.tableGraphics.setColumnWidth(1, primarywidth)
		self.tableGraphics.setColumnWidth(2, subwidth)
		self.tableGraphics.setColumnWidth(3, subwidth)
		
		total_width = self.tableImages.verticalHeader().width() + self.tableImages.horizontalHeader().length() + self.tableImages.frameWidth() * 2
		primarywidth = 250.
		subwidth = (total_width - primarywidth) / (self.tableImages.columnCount() - 1)
		self.tableImages.setColumnWidth(0, primarywidth)
		self.tableImages.setColumnWidth(1, subwidth)
		self.tableImages.setColumnWidth(2, subwidth)

		self.setPlotTableProperties()
		self.setImageTableProperties()
		self.setMapTableSignalProperties()
		self.tableMaps.itemChanged.connect(self.updateMapRow)
		self.tablePlots.itemChanged.connect(self.plotTypeChanged)
		self.contextMenuMapTable()
		self.contextMenuPlotTable()
		self.contextMenuImageTable()
		
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
		self.btnRemovePlot.clicked.connect(self.removePlots)
		self.btnPlotUp.clicked.connect(lambda event: self.movePlot(event, 'up'))
		self.btnPlotDown.clicked.connect(lambda event: self.movePlot(event, 'down'))
		self.btnAddImage.clicked.connect(self.addImage)
		self.btnRemoveImage.clicked.connect(self.removeImages)
		self.btnImageUp.clicked.connect(lambda event: self.moveImage(event, 'up'))
		self.btnImageDown.clicked.connect(lambda event: self.moveImage(event, 'down'))
		self.btnBrowseTemplate.clicked.connect(lambda: browse(self, 'existing file', "TUFLOW/animation_template", "QGIS Print Template", "QGIS Print Layout (*.qpt)", self.editTemplate))
		self.btnAddMap.clicked.connect(self.addMap)
		self.btnRemoveMap.clicked.connect(self.removeMaps)
		self.btnMapUp.clicked.connect(lambda event: self.moveMap(event, 'up'))
		self.btnMapDown.clicked.connect(lambda event: self.moveMap(event, 'down'))
		self.buttonBox.accepted.connect(self.check)
		self.buttonBox.rejected.connect(self.reject)
		self.pbPreview.clicked.connect(lambda: self.check(preview=True))
		
		self.importMapTable = MapExportImportDialog(self.iface)
		self.pbImport.clicked.connect(self.importMapTableData)

	def importMapTableData(self):
		"""imports data from external file and populates map table"""
		
		self.importMapTable.exec_()
		
		if self.importMapTable.imported:
			for i in range(len(self.importMapTable.col1)):
				j = self.tableMaps.rowCount()
				self.tableMaps.setRowCount(j + 1)
				
				item1 = QTableWidgetItem(0)
				item1.setText(self.importMapTable.col1[i])
				self.tableMaps.setItem(j, 0, item1)
				
				item2 = QTableWidgetItem(0)
				item2.setText(self.importMapTable.col2[i])
				self.tableMaps.setItem(j, 1, item2)
				
				item3 = QTableWidgetItem(0)
				item3.setText(self.importMapTable.col3[i])
				self.tableMaps.setItem(j, 2, item3)
				
				item4 = QTableWidgetItem(0)
				item4.setText(self.importMapTable.col4[i])
				self.tableMaps.setItem(j, 3, item4)
				
				item5 = QTableWidgetItem(0)
				item5.setText(self.importMapTable.col5[i])
				self.tableMaps.setItem(j, 4, item5)
				
				mapTableRow = [item1, item2, item3, item4, item5]
				mapTableRowItems = [[], [], [], [], []]
				self.mapTableRows.append(mapTableRow)
				self.mapTableRowItems.append(mapTableRowItems)
				
				if j == 0:
					self.tableMaps.setColumnWidth(3, self.tableMaps.columnWidth(3)
					                              - self.tableMaps.verticalHeader().sizeHint().width())
	
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

	def populateGraphics(self):
		"""
		Populates the graphics table with available TS Point, CS Line, or Flow Line objects that can be included in the
		animation map.

		:param checked: bool -> True means groupbox is checked on
		:return: void
		"""
		
		lines = self.tuView.tuPlot.tuCrossSection.rubberBands
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
		
		points = self.tuView.tuPlot.tuTSPoint.points
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
		
		item1 = QTableWidgetItem(0)
		item1.setText(label)
		item1.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
		if status:
			item1.setCheckState(Qt.Checked)
		else:
			item1.setCheckState(Qt.Unchecked)
		self.tableGraphics.setItem(rowNo, 0, item1)
		
		item2 = QTableWidgetItem(0)
		item2.setText(userLabel) if userLabel is not None else item2.setText(label)
		self.tableGraphics.setItem(rowNo, 1, item2)
		
		item3 = QTableWidgetItem(0)
		item3.setText('Left')
		self.tableGraphics.setItem(rowNo, 2, item3)
		items = ['Left', 'Right']
		if 'TS' in label:
			items += ['Above', 'Below', 'Above-Left', 'Below-Left', 'Above-Right', 'Below-Right']
		self.tableGraphics.itemDelegateForColumn(2).itemsInRows[rowNo] = items
		
		pb = QPushButton()
		pb.setText('Text Properties')
		dialog = TextPropertiesDialog()
		self.rowNo2fntDialog[rowNo] = dialog
		pb.clicked.connect(lambda: dialog.exec_())
		self.tableGraphics.setCellWidget(rowNo, 3, pb)
		
		if rowNo == 0:
			self.tableGraphics.setColumnWidth(2, self.tableGraphics.columnWidth(2) - self.tableGraphics.verticalHeader().sizeHint().width())

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
			return [], [], []
		
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
	
	def addPlot(self, e=False, item1=None, item2=None, item3=None, dialog=None):
		"""
		Add plot to QTableWidget

		:return: void
		"""

		## add to table
		n = self.tablePlots.rowCount()
		self.tablePlots.setRowCount(n + 1)
		if item1 is None:
			item1 = QTableWidgetItem(0)
			item1.setText(self.tablePlots.itemDelegateForColumn(0).default)
		if item2 is None:
			item2 = QTableWidgetItem(0)
		else:
			self.tablePlots.itemDelegateForColumn(1).currentCheckedItems[n] = self.plotTableRowItems[n][1]
		if item3 is None:
			item3 = QTableWidgetItem(0)
			item3.setText(self.tablePlots.itemDelegateForColumn(2).default)
		
		self.tablePlots.setItem(n, 0, item1)
		self.tablePlots.setItem(n, 1, item2)
		self.tablePlots.setItem(n, 2, item3)

		pb = QPushButton(self.tablePlots)
		pb.setText('Properties')
		if dialog is None:
			dialog = PlotProperties(self, item1, item2, self.tuView.tuOptions.xAxisDates)
		self.pbDialogs[pb] = dialog
		self.dialog2Plot[dialog] = [item1, item2, item3]
		pb.clicked.connect(lambda: dialog.setDefaults(self, item1, item2, static=True))
		pb.clicked.connect(lambda: dialog.exec_())
		self.tablePlots.setCellWidget(n, 3, pb)
		if n == 0:
			self.tablePlots.setColumnWidth(2, self.tablePlots.columnWidth(2) - self.tablePlots.verticalHeader().sizeHint().width())

		plotTableRow = [item1, item2, item3, dialog]
		plotTableRowItems = [[], [], [], [], []]
		self.plotTableRows.append(plotTableRow)
		self.plotTableRowItems.append(plotTableRowItems)
	
	def insertPlotRow(self, index=None, loc=INSERT_BEFORE):
		"""
		Insert a row into the map table.
		Can be inserted before or after clicked row.

		:param index: int
		:param loc: Table
		:return: void
		"""

		if index is not None:
			for i, plotTableRow in enumerate(self.plotTableRows):
				item1 = QTableWidgetItem(0)
				item1.setText(plotTableRow[0].text())
				item1Items = []
				item2 = QTableWidgetItem(0)
				item2.setText(plotTableRow[1].text())
				if i in self.tablePlots.itemDelegateForColumn(1).currentCheckedItems:
					item2Items = self.tablePlots.itemDelegateForColumn(1).currentCheckedItems[i]
					del self.tablePlots.itemDelegateForColumn(1).currentCheckedItems[i]
				else:
					item2Items = []
				item3 = QTableWidgetItem(0)
				item3.setText(plotTableRow[2].text())
				item3Items = []
				pb = self.tablePlots.cellWidget(i, 3)
				pb.clicked.disconnect()
				item4 = self.pbDialogs[pb]
				del pb
				item4Items = []
				plotTableRow = [item1, item2, item3, item4]
				plotTableRowItems = [item1Items, item2Items, item3Items, item4Items]
				self.plotTableRows[i] = plotTableRow
				self.plotTableRowItems[i] = plotTableRowItems
			
			self.pbDialogs.clear()
			
			if loc == TuMapDialog.INSERT_BEFORE:
				j = index
			else:
				j = index + 1
			
			## add to table
			item1 = QTableWidgetItem(0)
			item1.setText(self.tablePlots.itemDelegateForColumn(0).default)
			item2 = QTableWidgetItem(0)
			item3 = QTableWidgetItem(0)
			item3.setText(self.tablePlots.itemDelegateForColumn(2).default)
			item4 = PlotProperties(self, item1, item2, self.tuView.tuOptions.xAxisDates)
			
			plotTableRow = [item1, item2, item3, item4]
			plotTableRowItems = [[], [], [], []]
			self.plotTableRows.insert(j, plotTableRow)
			self.plotTableRowItems.insert(j, plotTableRowItems)
			
			self.reAddPlots()
	
	def removePlots(self, index=None):
		"""Remove plot from table."""

		selectionRange = self.tablePlots.selectedRanges()
		selectionRange = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRange]
		selectionRange = sum(selectionRange, [])
		if index:
			if index not in selectionRange:
				selectionRange = [index]
		
		if selectionRange:
			for i, plotTableRow in enumerate(self.plotTableRows):
				item1 = QTableWidgetItem(0)
				item1.setText(plotTableRow[0].text())
				item1Items = []
				item2 = QTableWidgetItem(0)
				item2.setText(plotTableRow[1].text())
				if i in self.tablePlots.itemDelegateForColumn(1).currentCheckedItems:
					item2Items = self.tablePlots.itemDelegateForColumn(1).currentCheckedItems[i]
					del self.tablePlots.itemDelegateForColumn(1).currentCheckedItems[i]
				else:
					item2Items = []
				item3 = QTableWidgetItem(0)
				item3.setText(plotTableRow[2].text())
				item3Items = []
				pb = self.tablePlots.cellWidget(i, 3)
				pb.clicked.disconnect()
				item4 = self.pbDialogs[pb]
				del pb
				item4Items = []
				plotTableRow = [item1, item2, item3, item4]
				plotTableRowItems = [item1Items, item2Items, item3Items, item4Items]
				self.plotTableRows[i] = plotTableRow
				self.plotTableRowItems[i] = plotTableRowItems
			for i in reversed(selectionRange):
				self.plotTableRows.pop(i)
				self.plotTableRowItems.pop(i)
			self.pbDialogs.clear()
			self.reAddPlots()
		else:
			if self.tablePlots.rowCount():
				if self.tablePlots.rowCount() == 1:
					self.tablePlots.setColumnWidth(2, self.tablePlots.columnWidth(2) +
					                               self.tablePlots.verticalHeader().sizeHint().width())
				pb = self.tablePlots.cellWidget(self.tablePlots.rowCount() - 1, 3)
				del self.pbDialogs[pb]
				self.tablePlots.setRowCount(self.tablePlots.rowCount() - 1)
				self.plotTableRows.pop()
				self.plotTableRowItems.pop()
				if self.tablePlots.rowCount() in self.tablePlots.itemDelegateForColumn(1).currentCheckedItems:
					del self.tablePlots.itemDelegateForColumn(1).currentCheckedItems[self.tablePlots.rowCount()]
	
	def reAddPlots(self):
		
		self.tablePlots.setColumnWidth(2, self.tablePlots.columnWidth(2) +
		                               self.tablePlots.verticalHeader().sizeHint().width())
		self.tablePlots.setRowCount(0)
		
		plotTableRows = self.plotTableRows[:]
		self.plotTableRows.clear()

		for i, plotTableRow in enumerate(plotTableRows):
			item1 = plotTableRow[0]
			item2 = plotTableRow[1]
			item3 = plotTableRow[2]
			item4 = plotTableRow[3]
			self.addPlot(item1=item1, item2=item2, item3=item3, dialog=item4)
	
	def movePlot(self, event=None, action='up'):
		"""Move position of selected map in table. Options 'up' or 'down'."""
		
		selectionRanges = self.tablePlots.selectedRanges()
		selectionRangeIndexes = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRanges]
		selectionRangeIndexes = sum(selectionRangeIndexes, [])
		
		if selectionRangeIndexes:
			for i, plotTableRow in enumerate(self.plotTableRows):
				item1 = QTableWidgetItem(0)
				item1.setText(plotTableRow[0].text())
				item1Items = []
				item2 = QTableWidgetItem(0)
				item2.setText(plotTableRow[1].text())
				if i in self.tablePlots.itemDelegateForColumn(1).currentCheckedItems:
					item2Items = self.tablePlots.itemDelegateForColumn(1).currentCheckedItems[i]
					del self.tablePlots.itemDelegateForColumn(1).currentCheckedItems[i]
				else:
					item2Items = []
				item3 = QTableWidgetItem(0)
				item3.setText(plotTableRow[2].text())
				item3Items = []
				pb = self.tablePlots.cellWidget(i, 3)
				pb.clicked.disconnect()
				item4 = self.pbDialogs[pb]
				del pb
				item4Items = []
				plotTableRow = [item1, item2, item3, item4]
				plotTableRowItems = [item1Items, item2Items, item3Items, item4Items]
				self.plotTableRows[i] = plotTableRow
				self.plotTableRowItems[i] = plotTableRowItems
			if action == 'up':
				for i in selectionRangeIndexes:
					if i > 0:
						row = self.plotTableRows.pop(i)
						self.plotTableRows.insert(i - 1, row)
						row = self.plotTableRowItems.pop(i)
						self.plotTableRowItems.insert(i - 1, row)
			else:
				for i in reversed(selectionRangeIndexes):
					if i < self.tablePlots.rowCount() - 1:
						row = self.plotTableRows.pop(i)
						self.plotTableRows.insert(i + 1, row)
						row = self.plotTableRowItems.pop(i)
						self.plotTableRowItems.insert(i + 1, row)
			self.reAddPlots()
			
			for sr in selectionRanges:
				if action == 'up':
					top = sr.topRow() - 1 if sr.topRow() > 0 else sr.topRow()
					bottom = sr.bottomRow() - 1 if sr.bottomRow() > sr.rowCount() - 1 else sr.bottomRow()
					left = sr.leftColumn()
					right = sr.rightColumn()
					newSelectionRange = QTableWidgetSelectionRange(top, left, bottom, right)
				else:
					top = sr.topRow() + 1 if sr.topRow() < self.tablePlots.rowCount() - sr.rowCount() else sr.topRow()
					bottom = sr.bottomRow() + 1 if sr.bottomRow() < self.tablePlots.rowCount() - 1 else sr.bottomRow()
					left = sr.leftColumn()
					right = sr.rightColumn()
					newSelectionRange = QTableWidgetSelectionRange(top, left, bottom, right)
				self.tablePlots.setRangeSelected(newSelectionRange, True)
	
	def plotTypeChanged(self, item=None):
		"""Updates row in map table if one of the combo boxes is changed."""
		
		if item is not None:
			if item.column() == 0:
				lines, labs, axis = self.plotItems(self.tablePlots.item(item.row(), item.column()).text())
				if labs:
					availablePlots = ['Active Dataset', 'Active Dataset [Water Level for Depth]'] + labs
					self.tablePlots.itemDelegateForColumn(1).setItems(item.row(), availablePlots)

	def addImage(self, e=False, item1=None, item2=None, dialog=None):
		"""
		Add plot to QTableWidget

		:return: void
		"""
		
		## add to table
		n = self.tableImages.rowCount()
		self.tableImages.setRowCount(n + 1)
		if item1 is None:
			item1 = QTableWidgetItem(0)
		if item2 is None:
			item2 = QTableWidgetItem(0)
			item2.setText(self.tableImages.itemDelegateForColumn(1).default)
		
		self.tableImages.setItem(n, 0, item1)
		self.tableImages.setItem(n, 1, item2)
		
		pb = QPushButton()
		pb.setText('Properties')
		if dialog is None:
			dialog = ImagePropertiesDialog()
		self.pbDialogsImage[pb] = dialog
		pb.clicked.connect(lambda: dialog.exec_())
		self.tableImages.setCellWidget(n, 2, pb)
		if n == 0:
			self.tableImages.setColumnWidth(1, self.tableImages.columnWidth(
				1) - self.tableImages.verticalHeader().sizeHint().width())
		
		imageTableRow = [item1, item2, dialog]
		self.imageTableRows.append(imageTableRow)
	
	def insertImageRow(self, index=None, loc=INSERT_BEFORE):
		"""
		Insert a row into the map table.
		Can be inserted before or after clicked row.

		:param index: int
		:param loc: Table
		:return: void
		"""
		
		if index is not None:
			for i, imageTableRow in enumerate(self.imageTableRows):
				item1 = QTableWidgetItem(0)
				item1.setText(imageTableRow[0].text())
				item2 = QTableWidgetItem(0)
				item2.setText(imageTableRow[1].text())
				pb = self.tableImages.cellWidget(i, 2)
				pb.clicked.disconnect()
				item3 = self.pbDialogsImage[pb]
				del pb
				imageTableRow = [item1, item2, item3]
				self.imageTableRows[i] = imageTableRow
			
			self.pbDialogsImage.clear()
			
			if loc == TuMapDialog.INSERT_BEFORE:
				j = index
			else:
				j = index + 1
			
			## add to table
			item1 = QTableWidgetItem(0)
			item2 = QTableWidgetItem(0)
			item2.setText(self.tableImages.itemDelegateForColumn(1).default)
			item3 = ImagePropertiesDialog()
			
			imageTableRow = [item1, item2, item3]
			self.imageTableRows.insert(j, imageTableRow)
			
			self.reAddImages()
	
	def removeImages(self, index=None):
		"""Remove plot from table."""
		
		selectionRange = self.tableImages.selectedRanges()
		selectionRange = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRange]
		selectionRange = sum(selectionRange, [])
		if index:
			if index not in selectionRange:
				selectionRange = [index]
		
		if selectionRange:
			for i, imageTableRow in enumerate(self.imageTableRows):
				item1 = QTableWidgetItem(0)
				item1.setText(imageTableRow[0].text())
				item2 = QTableWidgetItem(0)
				item2.setText(imageTableRow[1].text())
				pb = self.tableImages.cellWidget(i, 2)
				pb.clicked.disconnect()
				item3 = self.pbDialogsImage[pb]
				del pb
				imageTableRow = [item1, item2, item3]
				self.imageTableRows[i] = imageTableRow
			for i in reversed(selectionRange):
				self.imageTableRows.pop(i)
			self.pbDialogsImage.clear()
			self.reAddImages()
		else:
			if self.tableImages.rowCount():
				if self.tableImages.rowCount() == 1:
					self.tableImages.setColumnWidth(1, self.tableImages.columnWidth(1) +
					                                self.tableImages.verticalHeader().sizeHint().width())
				pb = self.tableImages.cellWidget(self.tableImages.rowCount() - 1, 2)
				del self.pbDialogsImage[pb]
				self.tableImages.setRowCount(self.tableImages.rowCount() - 1)
				self.imageTableRows.pop()
	
	def reAddImages(self):
		
		self.tableImages.setColumnWidth(1, self.tableImages.columnWidth(1) +
		                                self.tableImages.verticalHeader().sizeHint().width())
		self.tableImages.setRowCount(0)
		
		imageTableRows = self.imageTableRows[:]
		self.imageTableRows.clear()
		
		for i, imageTableRow in enumerate(imageTableRows):
			item1 = imageTableRow[0]
			item2 = imageTableRow[1]
			item3 = imageTableRow[2]
			self.addImage(item1=item1, item2=item2, dialog=item3)
	
	def moveImage(self, event=None, action='up'):
		"""Move position of selected map in table. Options 'up' or 'down'."""
		
		selectionRanges = self.tableImages.selectedRanges()
		selectionRangeIndexes = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRanges]
		selectionRangeIndexes = sum(selectionRangeIndexes, [])
		
		if selectionRangeIndexes:
			for i, imageTableRow in enumerate(self.imageTableRows):
				item1 = QTableWidgetItem(0)
				item1.setText(imageTableRow[0].text())
				item2 = QTableWidgetItem(0)
				item2.setText(imageTableRow[1].text())
				pb = self.tableImages.cellWidget(i, 2)
				pb.clicked.disconnect()
				item3 = self.pbDialogsImage[pb]
				del pb
				imageTableRow = [item1, item2, item3]
				self.imageTableRows[i] = imageTableRow
			if action == 'up':
				for i in selectionRangeIndexes:
					if i > 0:
						row = self.imageTableRows.pop(i)
						self.imageTableRows.insert(i - 1, row)
			else:
				for i in reversed(selectionRangeIndexes):
					if i < self.tableImages.rowCount() - 1:
						row = self.imageTableRows.pop(i)
						self.imageTableRows.insert(i + 1, row)
			self.reAddImages()
			
			for sr in selectionRanges:
				if action == 'up':
					top = sr.topRow() - 1 if sr.topRow() > 0 else sr.topRow()
					bottom = sr.bottomRow() - 1 if sr.bottomRow() > sr.rowCount() - 1 else sr.bottomRow()
					left = sr.leftColumn()
					right = sr.rightColumn()
					newSelectionRange = QTableWidgetSelectionRange(top, left, bottom, right)
				else:
					top = sr.topRow() + 1 if sr.topRow() < self.tableImages.rowCount() - sr.rowCount() else sr.topRow()
					bottom = sr.bottomRow() + 1 if sr.bottomRow() < self.tableImages.rowCount() - 1 else sr.bottomRow()
					left = sr.leftColumn()
					right = sr.rightColumn()
					newSelectionRange = QTableWidgetSelectionRange(top, left, bottom, right)
				self.tableImages.setRangeSelected(newSelectionRange, True)

	def setPlotTableProperties(self):
		
		plotTypes = ['Time Series', 'CS / LP']
		positions = ['Top-Left', 'Top-Right', 'Bottom-Left', 'Bottom-Right']
		
		self.tablePlots.itemDelegateForColumn(0).setItems(items=plotTypes, default='Time Series')
		self.tablePlots.itemDelegateForColumn(2).setItems(items=positions, default='Top-Left')
	
	def setImageTableProperties(self):
		
		imageTypes = "All Files(*)"
		positions = ['Top-Left', 'Top-Right', 'Bottom-Left', 'Bottom-Right']
		btnSignal = {'parent': self, 'browse type': 'existing file', 'key': 'TUFLOW/map_image',
		            'title': "Image", 'file types': imageTypes}
		
		self.tableImages.itemDelegateForColumn(0).setSignalProperties(btnSignal)
		self.tableImages.itemDelegateForColumn(1).setItems(items=positions, default='Top-Left')
	
	def setMapTableSignalProperties(self):
		"""Sets up the signal settings for the QStyledItemDelegate"""
		
		resultTypes = 'Mesh Layer (*.xmdf *.dat *.sup *.2dm)'
		exportTypes = "PDF (*.pdf *.PDF);;BMP format (*.bmp *.BMP);;CUR format (*.cur *.CUR);;ICNS format (*.icns *.ICNS);;" \
		              "ICO format (*.ico *.ICO);;JPEG format (*.jpeg *.JPEG);;JPG format (*.jpg *.JPG);;PBM format (*.pbm *,PBM);;" \
		              "PGM format (*.pgm *.PGM);;PNG format (*.png *.PNG);;PPM format (*.ppm *.PPM);;SVG format (*.svg *.SVG);;" \
		              "TIF format (*.tif *.TIF);;TIFF format (*.tiff *.TIFF);;WBMP format (*.wbmp *.WBMP);;WEBP (*.webp *.WEBP);;" \
		              "XBM format (*.xbm *.XBM);;XPM format (*.xpm *.XPM)"
		
		btnSignalResult = {'parent': self, 'browse type': 'existing file', 'key': 'TUFLOW/map_input',
		                   'title': "Result Layer", 'file types': resultTypes}
		btnSignalOutput = {'parent': self, 'browse type': 'output file', 'key': 'TUFLOW/map_output',
		                   'title': "Output Map", 'file types': exportTypes}
		

		items = []
		for i in range(self.tuView.OpenResults.count()):
			item = self.tuView.OpenResults.item(i).text()
			items.append(item)
		self.tableMaps.itemDelegateForColumn(0).setItems(items)
		self.tableMaps.itemDelegateForColumn(0).setSignalProperties(btnSignalResult)
		self.tableMaps.itemDelegateForColumn(4).setSignalProperties(btnSignalOutput)
	
	def updateMapRow(self, item=None):
		"""Updates row in map table if one of the combo boxes is changed."""
		
		if item is not None:
			if item.column() == 0:
				self.updateMapResultTypes(item.text(), item.row())
				self.updateMapTimes(item.text(), item.row())
			elif item.column() == 1 or item.column() == 2:
				self.updateMapTimes(self.tableMaps.item(item.row(), 0).text(), item.row())
	
	def updateMapResultTypes(self, result, row):
		"""Update scalar and vector result types in table"""
		
		prevScalar = None
		prevVector = None
		if self.tableMaps.item(row, 1) is not None:
			prevScalar = self.tableMaps.item(row, 1).text()
		if self.tableMaps.item(row, 2) is not None:
			prevVector = self.tableMaps.item(row, 2).text()
		scalarTypes, vectorTypes = getResultTypes(self.tuView.tuResults.results, result)
		scalars = ['-None-'] + scalarTypes
		vectors = ['-None-'] + vectorTypes
		self.tableMaps.itemDelegateForColumn(1).setItems(row, scalars)
		self.tableMaps.itemDelegateForColumn(2).setItems(row, vectors)
		if prevScalar in scalars:
			self.tableMaps.item(row, 1).setText(prevScalar)
		if prevVector in vectors:
			self.tableMaps.item(row, 2).setText(prevVector)
	
	def updateMapTimes(self, result, row):
		"""Update available times in table"""
		prevTime = None
		if self.tableMaps.item(row, 3) is not None:
			prevTime = self.tableMaps.item(row, 3).text()
		scalar = None
		vector = None
		if self.tableMaps.item(row, 1) is not None:
			scalar = self.tableMaps.item(row, 1).text()
		if self.tableMaps.item(row, 2) is not None:
			vector = self.tableMaps.item(row, 2).text()
		times = getTimes(self.tuView.tuResults.results, result, scalar,
		                 vector, self.tuView.tuOptions.timeUnits, self.tuView.tuOptions.xAxisDates,
		                 self.tuView.tuResults)
		self.tableMaps.itemDelegateForColumn(3).setItems(row, times)
		if prevTime in times:
			self.tableMaps.item(row, 3).setText(prevTime)
	
	def addMap(self):
		"""Add map to export list"""

		## add to table
		n = self.tableMaps.rowCount()
		self.tableMaps.setRowCount(n + 1)
		item1 = QTableWidgetItem(0)
		item2 = QTableWidgetItem(0)
		item3 = QTableWidgetItem(0)
		item4 = QTableWidgetItem(0)
		item5 = QTableWidgetItem(0)

		self.tableMaps.setItem(n, 0, item1)
		self.tableMaps.setItem(n, 1, item2)
		self.tableMaps.setItem(n, 2, item3)
		self.tableMaps.setItem(n, 3, item4)
		self.tableMaps.setItem(n, 4, item5)
		
		mapTableRow = [item1, item2, item3, item4, item5]
		mapTableRowItems = [[], [], [], [], []]
		self.mapTableRows.append(mapTableRow)
		self.mapTableRowItems.append(mapTableRowItems)
		
		if n == 0:
			self.tableMaps.setColumnWidth(3, self.tableMaps.columnWidth(3)
			                              - self.tableMaps.verticalHeader().sizeHint().width())
	
	def insertMapRow(self, index=None, loc=INSERT_BEFORE):
		"""
		Insert a row into the map table.
		Can be inserted before or after clicked row.

		:param index: int
		:param loc: Table
		:return: void
		"""
		
		if index is not None:
			for i, mapTableRow in enumerate(self.mapTableRows):
				item1 = QTableWidgetItem(0)
				item1.setText(mapTableRow[0].text())
				item1Items = []
				item2 = QTableWidgetItem(0)
				item2.setText(mapTableRow[1].text())
				if i in self.tableMaps.itemDelegateForColumn(1).itemsInRows:
					item2Items = self.tableMaps.itemDelegateForColumn(1).itemsInRows[i]
					del self.tableMaps.itemDelegateForColumn(1).itemsInRows[i]
				else:
					item2Items = []
				item3 = QTableWidgetItem(0)
				item3.setText(mapTableRow[2].text())
				if i in self.tableMaps.itemDelegateForColumn(2).itemsInRows:
					item3Items = self.tableMaps.itemDelegateForColumn(2).itemsInRows[i]
					del self.tableMaps.itemDelegateForColumn(2).itemsInRows[i]
				else:
					item3Items = []
				item4 = QTableWidgetItem(0)
				item4.setText(mapTableRow[3].text())
				if i in self.tableMaps.itemDelegateForColumn(3).itemsInRows:
					item4Items = self.tableMaps.itemDelegateForColumn(3).itemsInRows[i]
					del self.tableMaps.itemDelegateForColumn(3).itemsInRows[i]
				else:
					item4Items = []
				item5 = QTableWidgetItem(0)
				item5.setText(mapTableRow[4].text())
				item5Items = []
				mapTableRow = [item1, item2, item3, item4, item5]
				mapTableRowItems = [item1Items, item2Items, item3Items, item4Items, item5Items]
				self.mapTableRows[i] = mapTableRow
				self.mapTableRowItems[i] = mapTableRowItems
			
			if loc == TuMapDialog.INSERT_BEFORE:
				j = index
			else:
				j = index + 1
				
			# Available results e.g. Mo4_5m_001
			items = []
			for i in range(self.tuView.OpenResults.count()):
				item = self.tuView.OpenResults.item(i).text()
				items.append(item)
			
			## add to table
			item1 = QTableWidgetItem(0)
			item2 = QTableWidgetItem(0)
			item3 = QTableWidgetItem(0)
			item4 = QTableWidgetItem(0)
			item5 = QTableWidgetItem(0)

			mapTableRow = [item1, item2, item3, item4, item5]
			mapTableRowItems = [[], [], [], [], []]
			self.mapTableRows.insert(j, mapTableRow)
			self.mapTableRowItems.insert(j, mapTableRowItems)
			
			self.reAddMaps()

	def removeMaps(self, index=None):
		"""Remove map from table."""

		selectionRange = self.tableMaps.selectedRanges()
		selectionRange = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRange]
		selectionRange = sum(selectionRange, [])
		if index:
			if index not in selectionRange:
				selectionRange = [index]
		
		if selectionRange:
			for i, mapTableRow in enumerate(self.mapTableRows):
				item1 = QTableWidgetItem(0)
				item1.setText(mapTableRow[0].text())
				item1Items = []
				item2 = QTableWidgetItem(0)
				item2.setText(mapTableRow[1].text())
				if i in self.tableMaps.itemDelegateForColumn(1).itemsInRows:
					item2Items = self.tableMaps.itemDelegateForColumn(1).itemsInRows[i]
					del self.tableMaps.itemDelegateForColumn(1).itemsInRows[i]
				else:
					item2Items = []
				item3 = QTableWidgetItem(0)
				item3.setText(mapTableRow[2].text())
				if i in self.tableMaps.itemDelegateForColumn(2).itemsInRows:
					item3Items = self.tableMaps.itemDelegateForColumn(2).itemsInRows[i]
					del self.tableMaps.itemDelegateForColumn(2).itemsInRows[i]
				else:
					item3Items = []
				item4 = QTableWidgetItem(0)
				item4.setText(mapTableRow[3].text())
				if i in self.tableMaps.itemDelegateForColumn(3).itemsInRows:
					item4Items = self.tableMaps.itemDelegateForColumn(3).itemsInRows[i]
					del self.tableMaps.itemDelegateForColumn(3).itemsInRows[i]
				else:
					item4Items = []
				item5 = QTableWidgetItem(0)
				item5.setText(mapTableRow[4].text())
				item5Items = []
				mapTableRow = [item1, item2, item3, item4, item5]
				mapTableRowItems = [item1Items, item2Items, item3Items, item4Items, item5Items]
				self.mapTableRows[i] = mapTableRow
				self.mapTableRowItems[i] = mapTableRowItems
			for i in reversed(selectionRange):
				self.mapTableRows.pop(i)
				self.mapTableRowItems.pop(i)
			self.reAddMaps()
		else:
			if self.tableMaps.rowCount():
				if self.tableMaps.rowCount() == 1:
					self.tableMaps.setColumnWidth(3, self.tableMaps.columnWidth(3)
					                              + self.tableMaps.verticalHeader().sizeHint().width())
				self.tableMaps.setRowCount(self.tableMaps.rowCount() - 1)
				self.mapTableRows.pop()
				self.mapTableRowItems.pop()
		
			
	def moveMap(self, event=None, action='up'):
		"""Move position of selected map in table. Options 'up' or 'down'."""
		
		selectionRanges = self.tableMaps.selectedRanges()
		selectionRangeIndexes = [[y for y in range(x.topRow(), x.bottomRow() + 1)] for x in selectionRanges]
		selectionRangeIndexes = sum(selectionRangeIndexes, [])
		
		if selectionRangeIndexes:
			for i, mapTableRow in enumerate(self.mapTableRows):
				item1 = QTableWidgetItem(0)
				item1.setText(mapTableRow[0].text())
				item1Items = []
				item2 = QTableWidgetItem(0)
				item2.setText(mapTableRow[1].text())
				if i in self.tableMaps.itemDelegateForColumn(1).itemsInRows:
					item2Items = self.tableMaps.itemDelegateForColumn(1).itemsInRows[i]
					del self.tableMaps.itemDelegateForColumn(1).itemsInRows[i]
				else:
					item2Items = []
				item3 = QTableWidgetItem(0)
				item3.setText(mapTableRow[2].text())
				if i in self.tableMaps.itemDelegateForColumn(2).itemsInRows:
					item3Items = self.tableMaps.itemDelegateForColumn(2).itemsInRows[i]
					del self.tableMaps.itemDelegateForColumn(2).itemsInRows[i]
				else:
					item3Items = []
				item4 = QTableWidgetItem(0)
				item4.setText(mapTableRow[3].text())
				if i in self.tableMaps.itemDelegateForColumn(3).itemsInRows:
					item4Items = self.tableMaps.itemDelegateForColumn(3).itemsInRows[i]
					del self.tableMaps.itemDelegateForColumn(3).itemsInRows[i]
				else:
					item4Items = []
				item5 = QTableWidgetItem(0)
				item5.setText(mapTableRow[4].text())
				item5Items = []
				mapTableRow = [item1, item2, item3, item4, item5]
				mapTableRowItems = [item1Items, item2Items, item3Items, item4Items, item5Items]
				self.mapTableRows[i] = mapTableRow
				self.mapTableRowItems[i] = mapTableRowItems
			if action == 'up':
				for i in selectionRangeIndexes:
					if i > 0:
						row = self.mapTableRows.pop(i)
						self.mapTableRows.insert(i-1, row)
						row = self.mapTableRowItems.pop(i)
						self.mapTableRowItems.insert(i - 1, row)
			else:
				for i in reversed(selectionRangeIndexes):
					if i < self.tableMaps.rowCount() - 1:
						row = self.mapTableRows.pop(i)
						self.mapTableRows.insert(i+1, row)
						row = self.mapTableRowItems.pop(i)
						self.mapTableRowItems.insert(i + 1, row)
			self.reAddMaps()
			
			for sr in selectionRanges:
				if action == 'up':
					top = sr.topRow() - 1 if sr.topRow() > 0 else sr.topRow()
					bottom = sr.bottomRow() - 1 if sr.bottomRow() > sr.rowCount() - 1 else sr.bottomRow()
					left = sr.leftColumn()
					right = sr.rightColumn()
					newSelectionRange = QTableWidgetSelectionRange(top, left, bottom, right)
				else:
					top = sr.topRow() + 1 if sr.topRow() < self.tableMaps.rowCount() - sr.rowCount() else sr.topRow()
					bottom = sr.bottomRow() + 1 if sr.bottomRow() < self.tableMaps.rowCount() - 1 else sr.bottomRow()
					left = sr.leftColumn()
					right = sr.rightColumn()
					newSelectionRange = QTableWidgetSelectionRange(top, left, bottom, right)
				self.tableMaps.setRangeSelected(newSelectionRange, True)

			
	def reAddMaps(self):
		
		self.tableMaps.setColumnWidth(3, self.tableMaps.columnWidth(3)
		                              + self.tableMaps.verticalHeader().sizeHint().width())
		self.tableMaps.setRowCount(0)
		
		for i, mapTableRow in enumerate(self.mapTableRows):
			rowNo = i
			rowCount = i + 1
			
			self.tableMaps.setRowCount(rowCount)
			
			self.tableMaps.setItem(rowNo, 0, mapTableRow[0])
			self.tableMaps.setItem(rowNo, 1, mapTableRow[1])
			self.tableMaps.setItem(rowNo, 2, mapTableRow[2])
			self.tableMaps.setItem(rowNo, 3, mapTableRow[3])
			self.tableMaps.setItem(rowNo, 4, mapTableRow[4])
			
			self.tableMaps.itemDelegateForColumn(1).itemsInRows[i] = self.mapTableRowItems[i][1]
			self.tableMaps.itemDelegateForColumn(2).itemsInRows[i] = self.mapTableRowItems[i][2]
			self.tableMaps.itemDelegateForColumn(3).itemsInRows[i] = self.mapTableRowItems[i][3]
			
	def updateProgress(self, i, cnt):
		""" callback from routine """
		self.progress.setMaximum(cnt)
		self.progress.setValue(i)
		qApp.processEvents()
	
	def contextMenuMapTable(self):
		"""
		Context menu for map table - right click on row number
		gives option to delete, insert before, insert after.

		:return: None
		"""
		
		self.tableMaps.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
		self.tableMaps.verticalHeader().customContextMenuRequested.connect(self.mapTableMenu)
	
	def mapTableMenu(self, pos):
		"""
		Prepare the context menu for the map table.

		:param pos: QPoint
		:return: None
		"""
		
		self.mapTableMenu = QMenu()
		self.mapTableInsertRowBefore = QAction("Insert Above", self.mapTableMenu)
		self.mapTableInsertRowAfter = QAction("Insert Below", self.mapTableMenu)
		self.mapTableDeleteRow = QAction("Delete", self.mapTableMenu)
		
		index = self.tableMaps.rowAt(pos.y())
		self.mapTableInsertRowBefore.triggered.connect(lambda: self.insertMapRow(index, TuMapDialog.INSERT_BEFORE))
		self.mapTableInsertRowAfter.triggered.connect(lambda: self.insertMapRow(index, TuMapDialog.INSERT_AFTER))
		self.mapTableDeleteRow.triggered.connect(lambda: self.removeMaps(index))
		
		self.mapTableMenu.addAction(self.mapTableInsertRowBefore)
		self.mapTableMenu.addAction(self.mapTableInsertRowAfter)
		self.mapTableMenu.addSeparator()
		self.mapTableMenu.addAction(self.mapTableDeleteRow)
		
		posH = self.tableMaps.mapToGlobal(pos).x()
		posV = self.tableMaps.mapToGlobal(pos).y() + \
		       self.mapTableMenu.actionGeometry(self.mapTableInsertRowBefore).height()
		newPos = QPoint(posH, int(posV))
		self.mapTableMenu.popup(newPos, self.mapTableInsertRowBefore)
	
	def contextMenuPlotTable(self):
		"""
		Context menu for map table - right click on row number
		gives option to delete, insert before, insert after.

		:return: None
		"""
		
		self.tablePlots.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
		self.tablePlots.verticalHeader().customContextMenuRequested.connect(self.plotTableMenu)
	
	def plotTableMenu(self, pos):
		"""
		Prepare the context menu for the map table.

		:param pos: QPoint
		:return: None
		"""
		
		self.plotTableMenu = QMenu()
		self.plotTableInsertRowBefore = QAction("Insert Above", self.plotTableMenu)
		self.plotTableInsertRowAfter = QAction("Insert Below", self.plotTableMenu)
		self.plotTableDeleteRow = QAction("Delete", self.plotTableMenu)
		
		index = self.tablePlots.rowAt(pos.y())
		self.plotTableInsertRowBefore.triggered.connect(lambda: self.insertPlotRow(index, TuMapDialog.INSERT_BEFORE))
		self.plotTableInsertRowAfter.triggered.connect(lambda: self.insertPlotRow(index, TuMapDialog.INSERT_AFTER))
		self.plotTableDeleteRow.triggered.connect(lambda: self.removePlots(index))
		
		self.plotTableMenu.addAction(self.plotTableInsertRowBefore)
		self.plotTableMenu.addAction(self.plotTableInsertRowAfter)
		self.plotTableMenu.addSeparator()
		self.plotTableMenu.addAction(self.plotTableDeleteRow)
		
		posH = self.tablePlots.mapToGlobal(pos).x()
		posV = self.tablePlots.mapToGlobal(pos).y() + \
		       self.plotTableMenu.actionGeometry(self.plotTableInsertRowBefore).height()
		newPos = QPoint(posH, int(posV))
		self.plotTableMenu.popup(newPos, self.plotTableInsertRowBefore)
	
	def contextMenuImageTable(self):
		"""
		Context menu for map table - right click on row number
		gives option to delete, insert before, insert after.

		:return: None
		"""
		
		self.tableImages.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
		self.tableImages.verticalHeader().customContextMenuRequested.connect(self.imageTableMenu)
	
	def imageTableMenu(self, pos):
		"""
		Prepare the context menu for the map table.

		:param pos: QPoint
		:return: None
		"""
		
		self.imageTableMenu = QMenu()
		self.imageTableInsertRowBefore = QAction("Insert Above", self.imageTableMenu)
		self.imageTableInsertRowAfter = QAction("Insert Below", self.imageTableMenu)
		self.imageTableDeleteRow = QAction("Delete", self.imageTableMenu)
		
		index = self.tableImages.rowAt(pos.y())
		self.imageTableInsertRowBefore.triggered.connect(lambda: self.insertImageRow(index, TuMapDialog.INSERT_BEFORE))
		self.imageTableInsertRowAfter.triggered.connect(lambda: self.insertImageRow(index, TuMapDialog.INSERT_AFTER))
		self.imageTableDeleteRow.triggered.connect(lambda: self.removeImages(index))
		
		self.imageTableMenu.addAction(self.imageTableInsertRowBefore)
		self.imageTableMenu.addAction(self.imageTableInsertRowAfter)
		self.imageTableMenu.addSeparator()
		self.imageTableMenu.addAction(self.imageTableDeleteRow)
		
		posH = self.tableImages.mapToGlobal(pos).x()
		posV = self.tableImages.mapToGlobal(pos).y() + \
		       self.imageTableMenu.actionGeometry(self.imageTableInsertRowBefore).height()
		newPos = QPoint(posH, int(posV))
		self.imageTableMenu.popup(newPos, self.imageTableInsertRowBefore)
	
	def check(self, preview=False):
		"""Pre run checks."""
		
		# check image locations exist
		for i in range(self.tableImages.rowCount()):
			#path = self.tableImages.cellWidget(i, 0).layout().itemAt(1).widget().text()
			path = self.tableImages.item(i, 0).text()
			if not os.path.exists(path):
				QMessageBox.information(self, 'Input Error', 'Cannot find file: {0}'.format(path))
				return
				
		# check all the result and type selections make sense
		if not self.tableMaps.rowCount():
			QMessageBox.information(self, 'Input Error', 'No Maps Added')
			return
		for i in range(self.tableMaps.rowCount()):
			result = self.tableMaps.item(i, 0).text()
			if not result:
				QMessageBox.information(self, 'Input Error', 'Row {0} - Must specify input result'.format(i + 1))
				return
			if result not in self.tuView.tuResults.results:
				if not os.path.exists(result):
					QMessageBox.information(self, 'Input Error',
					                        'Row {0} - cannot find result: {1}'.format(i + 1, result))
					return
			scalar = self.tableMaps.item(i, 1).text()
			vector = self.tableMaps.item(i, 2).text()
			if (scalar == '-None-' or scalar == '') and (vector == '-None-' or vector == ''):
				QMessageBox.information(self, 'Input Error',
				                        'Row {0} - must choose at least one scalar or vector result'.format(i + 1))
				return
			time = self.tableMaps.item(i, 3).text()
			if not time:
				QMessageBox.information(self, 'Input Error', 'Row {0} - must specify a timestep'.format(i + 1))
				return
			output = self.tableMaps.item(i, 4).text()
			if not output:
				QMessageBox.information(self, 'Input Error', 'Row {0} - Must specify an output path'.format(i + 1))
				return
		
		self.run(preview)
		
	def run(self, preview):
		"""run tool"""

		self.tuView.qgisDisconnect()
		
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
				plotDict['type'] = self.tablePlots.item(i, 0).text()
				plotDict['labels'] = self.tablePlots.item(i, 1).text().split(';;')
				plotDict['position'] = self.tablePlots.item(i, 2).text()
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
					userLabel = self.tableGraphics.item(i, 1).text()
					position = self.tableGraphics.item(i, 2).text()
					font = self.rowNo2fntDialog[i]
					graphicDict['id'] = label.text()
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
					'source': self.tableImages.item(i, 0).text(),
					'position': self.tableImages.item(i, 1).text(),
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
		     'page margin': pageMargin,
		     'datetime': self.tuView.tuOptions.xAxisDates,
		     'dateformat': self.tuView.tuOptions.dateFormat,
		     'dynamic axis update': self.cbDynamicAxisLimits.isChecked(),
		     'turesults': self.tuView.tuResults,
		     }
		tmpdir = tempfile.mkdtemp(suffix='tflw_maps')
		d['tmpdir'] = tmpdir
		
		count = self.tableMaps.rowCount()
		
		# loop once through types to get rendering settings
		rendering = {}
		for i in range(count):
			scalar = self.tableMaps.item(i, 1).text()
			if scalar not in rendering:
				time = self.tableMaps.item(i, 3).text()
				# result layer
				layer = self.tableMaps.item(i, 0).text()
				d['rendered'] = False
				if layer not in self.tuView.tuResults.results and \
						os.path.splitext(os.path.basename(layer))[0] not in self.tuView.tuResults.results:
					imported = self.tuView.tuMenuBar.tuMenuFunctions.load2dResults(result_2D=[[layer]])
					if not imported:
						continue
					layer = tuflowqgis_find_layer(self.tuView.OpenResults.item(self.tuView.OpenResults.count() - 1).text())
				else:
					if layer in self.tuView.tuResults.results:
						layer = tuflowqgis_find_layer(layer)
					else:
						layer = tuflowqgis_find_layer(os.path.splitext(os.path.basename(layer))[0])
				# active scalar and vector index
				if time.lower() != 'max':
					if self.tuView.tuOptions.xAxisDates:
						time = self.tuView.tuPlot.convertDateToTime(time, unit=self.tuView.tuOptions.timeUnits)
					else:
						time = convertFormattedTimeToTime(time, unit=self.tuView.tuOptions.timeUnits)
					d['time'] = time
				else:
					d['time'] = -99999
					scalar += '/Maximums'
					time = 0.0
				scalarInd = -1
				for j in range(layer.dataProvider().datasetGroupCount()):
					if str(layer.dataProvider().datasetGroupMetadata(j).name()).lower() == scalar.lower():
						scalarInd = j
				rs = layer.rendererSettings()
				rendering[self.tableMaps.item(i, 1).text()] = rs.scalarSettings(scalarInd)
				
		d['rendering'] = rendering
		
		# main loop
		for i in range(count):
			d['map number'] = i
			prog(i, count)
			
			# outfile
			path = self.tableMaps.item(i, 4).text()
			d['imgfile'] = path
			
			# result layer
			layer = self.tableMaps.item(i, 0).text()
			d['rendered'] = False
			if layer not in self.tuView.tuResults.results and \
					os.path.splitext(os.path.basename(layer))[0] not in self.tuView.tuResults.results:
				imported = self.tuView.tuMenuBar.tuMenuFunctions.load2dResults(result_2D=[[layer]])
				if not imported:
					continue
				layer = tuflowqgis_find_layer(self.tuView.OpenResults.item(self.tuView.OpenResults.count() - 1).text())
			else:
				if layer in self.tuView.tuResults.results:
					layer = tuflowqgis_find_layer(layer)
				else:
					layer = tuflowqgis_find_layer(os.path.splitext(os.path.basename(layer))[0])

			self.tuView.tuResults.tuResults2D.activeMeshLayers = []
			self.tuView.tuResults.tuResults2D.activeMeshLayers.append(layer)
			d['layer'] = layer
			
			# iterate through layers and turn off any mesh layers not needed
			layersToTurnOff = []
			for mapLayer in self.canvas.layers():
				if isinstance(mapLayer, QgsMeshLayer):
					if mapLayer != layer:
						layersToTurnOff.append(mapLayer)
			layers = [layer]
			legint = self.tuView.project.layerTreeRoot()
			nodes = legint.findLayers()
			for node in nodes:
				mapLayer = node.layer()
				if isinstance(mapLayer, QgsMeshLayer):
					if mapLayer == layer:
						node.setItemVisibilityChecked(True)
					else:
						node.setItemVisibilityChecked(False)
			mapLayers = self.canvas.layers()
			for mapLayer in mapLayers[:]:
				if isinstance(mapLayer, QgsMeshLayer):
					if mapLayer != layer:
						if mapLayer in layers:
							layers.remove(mapLayer)
					else:
						if mapLayer not in layers:
							layers.append(mapLayer)
				else:
					if mapLayer not in layers:
						layers.append(mapLayer)
			d['layers'] = layers
			
			# label text
			text = self.labelInput.toPlainText()
			result = layer.name()
			scalar = self.tableMaps.item(i, 1).text()
			vector = self.tableMaps.item(i, 2).text()
			time = self.tableMaps.item(i, 3).text()
			label = createText(text, result, scalar, vector, time, path, self.project, i + 1)
			if self.groupLabel.isChecked():
				d['layout']['title']['label'] = label
			d['active scalar'] = scalar

			# active scalar and vector index
			if time.lower() != 'max':
				if self.tuView.tuOptions.xAxisDates:
					time = self.tuView.tuPlot.convertDateToTime(time, unit=self.tuView.tuOptions.timeUnits)
				else:
					time = convertFormattedTimeToTime(time, unit=self.tuView.tuOptions.timeUnits)
				d['time'] = time
			else:
				d['time'] = -99999
				scalar += '/Maximums'
				vector += '/Maximums'
				time = 0.0
			scalarInd = -1
			vectorInd = -1
			for j in range(layer.dataProvider().datasetGroupCount()):
				if str(layer.dataProvider().datasetGroupMetadata(j).name()).lower() == scalar.lower():
					scalarInd = j
				if str(layer.dataProvider().datasetGroupMetadata(j).name()).lower() == vector.lower():
					vectorInd = j
			asd = QgsMeshDatasetIndex(-1, 0)
			for j in range(layer.dataProvider().datasetCount(scalarInd)):
				ind = QgsMeshDatasetIndex(scalarInd, j)
				if '{0:.2f}'.format(layer.dataProvider().datasetMetadata(ind).time()) == '{0:.2f}'.format(time):
					asd = ind
			avd = QgsMeshDatasetIndex(-1, 0)
			for j in range(layer.dataProvider().datasetCount(vectorInd)):
				ind = QgsMeshDatasetIndex(vectorInd, j)
				if '{0:.2f}'.format(layer.dataProvider().datasetMetadata(ind).time()) == '{0:.2f}'.format(time):
					avd = ind
			d['scalar index'] = asd
			d['vector index'] = avd
			
			for pb, dialog in self.pbDialogs.items():
				if self.cbDynamicAxisLimits.isChecked():
					dialog.yUseMatplotLibDefault = True
					dialog.dynamicYAxis = True
					
				dialog.setDefaults(self, self.dialog2Plot[dialog][0].text(),
				                   self.dialog2Plot[dialog][1].text().split(';;'), static=True,
				                   activeScalar=d['active scalar'], xAxisDates=self.tuView.tuOptions.xAxisDates)

			self.layout = makeMap(d, self.iface, prog, self, preview, i)
			# self.tuView.renderMap()
			
			if preview:
				self.iface.openLayoutDesigner(layout=self.layout)
				self.tuView.qgisConnect()
				return

		self.tuView.qgisConnect()
		QApplication.restoreOverrideCursor()
		self.updateProgress(0, 1)
		self.buttonBox.setEnabled(True)
		shutil.rmtree(tmpdir)
		QMessageBox.information(self, "Export", "Map export was successfully!")
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


class MapExportImportDialog(QDialog, Ui_MapExportImportDialog):
	
	def __init__(self, iface):
		QDialog.__init__(self)
		self.setupUi(self)
		self.iface = iface
		folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
		self.btnBrowse.setIcon(folderIcon)
		
		# import data to these members
		# data type depends on importType (i.e. channel, arch bridge etc)
		self.col1 = []
		self.col2 = []
		self.col3 = []
		self.col4 = []
		self.col5 = []
		self.imported = False
		self.message = []
		self.error = False
		
		self.btnBrowse.clicked.connect(lambda: browse(self, 'existing file', 'TUFLOW/map_export_import_data',
		                                              'Import: Map Export Data', "ALL (*)", self.inFile))
		self.inFile.textChanged.connect(self.populateDataColumns)
		self.inFile.textChanged.connect(self.updatePreview)
		self.sbLines2Discard.valueChanged.connect(self.populateDataColumns)
		self.sbLines2Discard.valueChanged.connect(self.updatePreview)
		self.cboCol1.currentIndexChanged.connect(self.updatePreview)
		self.cboCol2.currentIndexChanged.connect(self.updatePreview)
		self.cboCol3.currentIndexChanged.connect(self.updatePreview)
		self.cboCol4.currentIndexChanged.connect(self.updatePreview)
		self.cboCol5.currentIndexChanged.connect(self.updatePreview)
		self.rbCSV.clicked.connect(self.populateDataColumns)
		self.rbSpace.clicked.connect(self.populateDataColumns)
		self.rbTab.clicked.connect(self.populateDataColumns)
		self.rbOther.clicked.connect(self.populateDataColumns)
		self.delimiter.textChanged.connect(self.populateDataColumns)
		self.pbOk.clicked.connect(self.check)
		self.pbCancel.clicked.connect(self.reject)
	
	def getDelim(self):
		if self.rbCSV.isChecked():
			return ','
		elif self.rbSpace.isChecked():
			return ' '
		elif self.rbTab.isChecked():
			return '\t'
		elif self.rbOther.isChecked():
			return self.delimiter.text()
	
	def checkConsecutive(self, letter):
		f = self.dateFormat.text()
		for i in range(f.count(letter)):
			if i == 0:
				indPrev = f.find(letter)
			else:
				ind = f[indPrev + 1:].find(letter)
				if ind != 0:
					return False
				indPrev += 1
		
		return True
	
	def populateDataColumns(self):
		self.cboCol1.clear()
		self.cboCol2.clear()
		self.cboCol3.clear()
		self.cboCol4.clear()
		self.cboCol5.clear()
		headers = []
		if self.inFile.text():
			if os.path.exists(self.inFile.text()):
				header_line = self.sbLines2Discard.value() - 1
				if header_line >= 0:
					with open(self.inFile.text(), 'r') as fo:
						for i, line in enumerate(fo):
							if i == header_line:
								delim = self.getDelim()
								if delim != '':
									headers = line.split(delim)
									headers[-1] = headers[-1].strip('\n')
									for j, header in enumerate(headers):
										headers[j] = header.strip('"').strip("'")
							elif i > header_line:
								break
				else:
					with open(self.inFile.text(), 'r') as fo:
						for i, line in enumerate(fo):
							if i == 0:
								delim = self.getDelim()
								if delim != '':
									n = len(line.split(delim))
									headers = ['Column {0}'.format(x + 1) for x in range(n)]
							else:
								break
				self.cboCol1.addItems(headers)
				self.cboCol2.addItems(headers)
				self.cboCol3.addItems(headers)
				self.cboCol4.addItems(headers)
				self.cboCol5.addItems(headers)
		
		self.cboCol1.addItem('-None-')
		self.cboCol2.addItem('-None-')
		self.cboCol3.addItem('-None-')
		self.cboCol4.addItem('-None-')
		self.cboCol5.addItem('-None-')
		self.cboCol1.setCurrentIndex(-1)
		self.cboCol2.setCurrentIndex(-1)
		self.cboCol3.setCurrentIndex(-1)
		self.cboCol4.setCurrentIndex(-1)
		self.cboCol5.setCurrentIndex(-1)
		# try and autopopulate comboboxes if possible
		for i, h in enumerate(headers):
			if h.lower() == 'result':
				self.cboCol1.setCurrentIndex(i)
			if 'scalar' in h.lower():
				self.cboCol2.setCurrentIndex(i)
			if 'vector' in h.lower():
				self.cboCol3.setCurrentIndex(i)
			if h.lower() == 'time':
				self.cboCol4.setCurrentIndex(i)
			if h.lower() == 'output':
				self.cboCol5.setCurrentIndex(i)
	
	def updatePreview(self):
		columnNames = ['Result', 'Scalar Type', "Vector Type", 'Time', 'Output']
		iCol1 = -1
		iCol2 = -1
		iCol3 = -1
		iCol4 = -1
		iCol5 = -1
		
		self.previewTable.clear()
		self.previewTable.setRowCount(0)
		self.previewTable.setColumnCount(0)
		if self.inFile.text():
			if os.path.exists(self.inFile.text()):
				# sort out number of columns and column names
				self.previewTable.setColumnCount(len(columnNames))
				self.previewTable.setHorizontalHeaderLabels(columnNames)
				if self.cboCol1.currentIndex() > -1 and self.cboCol1.currentText() != '-None-':
					iCol1 = self.cboCol1.currentIndex()
				if self.cboCol2.currentIndex() > -1 and self.cboCol2.currentText() != '-None-':
					iCol2 = self.cboCol2.currentIndex()
				if self.cboCol3.currentIndex() > -1 and self.cboCol3.currentText() != '-None-':
					iCol3 = self.cboCol3.currentIndex()
				if self.cboCol4.currentIndex() > -1 and self.cboCol4.currentText() != '-None-':
					iCol4 = self.cboCol4.currentIndex()
				if self.cboCol5.currentIndex() > -1 and self.cboCol5.currentText() != '-None-':
					iCol5 = self.cboCol5.currentIndex()
				
				if self.previewTable.columnCount():
					# read in first 10 rows of data for preview
					with open(self.inFile.text(), 'r') as fo:
						header_line = self.sbLines2Discard.value() - 1
						data_entries = 0
						for i, line in enumerate(fo):
							if i > header_line:
								if data_entries > 9:
									break
								delim = self.getDelim()
								values = line.split(delim)
								
								self.previewTable.setRowCount(self.previewTable.rowCount() + 1)
								
								# first column
								value = ''
								if iCol1 > -1:
									if len(values) > iCol1:
										value = values[iCol1].strip()
								item = QTableWidgetItem(0)
								item.setText(value)
								self.previewTable.setItem(data_entries, 0, item)
								
								# second column
								value = ''
								if iCol2 > -1:
									if len(values) > iCol2:
										value = values[iCol2].strip()
								item = QTableWidgetItem(0)
								item.setText(value)
								self.previewTable.setItem(data_entries, 1, item)
								
								# third column
								value = ''
								if iCol3 > -1:
									if len(values) > iCol3:
										value = values[iCol3].strip()
								item = QTableWidgetItem(0)
								item.setText(value)
								self.previewTable.setItem(data_entries, 2, item)
								
								# forth column
								value = ''
								if iCol4 > -1:
									if len(values) > iCol4:
										value = values[iCol4].strip()
								item = QTableWidgetItem(0)
								item.setText(value)
								self.previewTable.setItem(data_entries, 3, item)
								
								# fifth column
								value = ''
								if iCol5 > -1:
									if len(values) > iCol5:
										value = values[iCol5].strip()
								item = QTableWidgetItem(0)
								item.setText(value)
								self.previewTable.setItem(data_entries, 4, item)
								
								data_entries += 1

	def check(self):
		if not self.inFile.text():
			QMessageBox.critical(self, 'Import Data', 'No Input File Specified')
			return
		if not os.path.exists(self.inFile.text()):
			QMessageBox.critical(self, 'Import Data', 'Invalid Input File')
			return

		# prelim checks out :)
		self.run()
	
	def run(self):
		# make sure entries are reset and blank
		self.col1 = []
		self.col2 = []
		self.col3 = []
		self.col4 = []
		self.col5 = []
		self.imported = False
		self.message = []
		self.error = False
		
		# columns to import
		iCol1 = -1
		iCol2 = -1
		iCol3 = -1
		iCol4 = -1
		iCol5 = -1
		if self.cboCol1.currentIndex() > -1 and self.cboCol1.currentText() != '-None-':
			iCol1 = self.cboCol1.currentIndex()
		if self.cboCol2.currentIndex() > -1 and self.cboCol2.currentText() != '-None-':
			iCol2 = self.cboCol2.currentIndex()
		if self.cboCol3.currentIndex() > -1 and self.cboCol3.currentText() != '-None-':
			iCol3 = self.cboCol3.currentIndex()
		if self.cboCol4.currentIndex() > -1 and self.cboCol4.currentText() != '-None-':
			iCol4 = self.cboCol4.currentIndex()
		if self.cboCol5.currentIndex() > -1 and self.cboCol5.currentText() != '-None-':
			iCol5 = self.cboCol5.currentIndex()
		
		with open(self.inFile.text(), 'r') as fo:
			header_line = self.sbLines2Discard.value() - 1
			for i, line in enumerate(fo):
				if i > header_line:
					delim = self.getDelim()
					values = line.split(delim)

					# first column
					value = ''
					if iCol1 > -1:
						if len(values) > iCol1:
							value = values[iCol1].strip()
					self.col1.append(value)
					
					# second column
					value = ''
					if iCol2 > -1:
						if len(values) > iCol2:
							value = values[iCol2].strip()
					self.col2.append(value)

					# third column
					value = ''
					if iCol3 > -1:
						if len(values) > iCol3:
							value = values[iCol3].strip()
					self.col3.append(value)
					
					# fourth column
					value = ''
					if iCol4 > -1:
						if len(values) > iCol4:
							value = values[iCol4].strip()
					self.col4.append(value)
					
					# fifth column
					value = ''
					if iCol5 > -1:
						if len(values) > iCol5:
							value = values[iCol5].strip()
					self.col5.append(value)
		
		if self.col1 or self.col2 or self.col3 or self.col4 or self.col5:
			if len(self.col1) == len(self.col2) == len(self.col3) == len(self.col4) == len(self.col5):
				pass
			else:
				QMessageBox.critical(self, "Import Data", "Error Importing Data: Data Set Lengths Do Not Match")
				return
		else:
			QMessageBox.critical(self, "Import Data", "Empty Data Set. Check Input File Contains Useable Data")
			return
		
		# finally destroy dialog box
		self.imported = True
		QMessageBox.information(self, "Import Data", "Import Successful")
		self.accept()