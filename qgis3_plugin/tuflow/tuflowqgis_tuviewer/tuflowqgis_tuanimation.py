import platform
import os
import sys
import shutil
import tempfile
import zipfile
import subprocess
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtXml import QDomDocument
from qgis.core import *
from qgis.gui import *
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import QgsNetworkAccessManager
from ui_animation_dialog import Ui_AnimationDialog
from animation_plot_properties import Ui_PlotProperties
from tuflow.tuflowqgis_library import tuflowqgis_find_layer, applyMatplotLibArtist
import matplotlib
import numpy as np
try:
	import matplotlib.pyplot as plt
except:
	current_path = os.path.dirname(__file__)
	plugin_folder = os.path.dirname(current_path)
	sys.path.append(os.path.join(plugin_folder, '_tk\\DLLs'))
	sys.path.append(os.path.join(plugin_folder, '_tk\\libs'))
	sys.path.append(os.path.join(plugin_folder, '_tk\\Lib'))
	import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.patches import Polygon
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg


# http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(program):
	"""
	Finds exe either from filepath or in paths
	
	:param program: str
	:return: str
	"""
	
	import os
	def is_exe(fpath):
		return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

	fpath, fname = os.path.split(program)
	if fpath:
		if is_exe(program):
			return program
	else:
		for path in os.environ["PATH"].split(os.pathsep):
			path = path.strip('"')
			exe_file = os.path.join(path, program)
			if is_exe(exe_file):
				return exe_file

	return None


def findPlatformVersion():
	platformVersion = platform.system()
	if platform.architecture()[0] == '64bit':
		platformVersion += '64'
	return platformVersion


def downloadBinPackage(packageUrl, destinationFileName):
	request = QNetworkRequest(QUrl(packageUrl))
	request.setRawHeader(b'Accept-Encoding', b'gzip,deflate')

	reply = QgsNetworkAccessManager.instance().get(request)
	evloop = QEventLoop()
	reply.finished.connect(evloop.quit)
	evloop.exec_(QEventLoop.ExcludeUserInputEvents)
	content_type = reply.rawHeader(b'Content-Type')
	#if content_type == QByteArray().append('application/zip'):
	if content_type == b'application/zip':
		if os.path.isfile(destinationFileName):
			os.unlink(destinationFileName)

		destinationFile = open(destinationFileName, 'wb')
		destinationFile.write(bytearray(reply.readAll()))
		destinationFile.close()
	else:
		ret_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
		raise IOError("{} {}".format(ret_code, packageUrl))
	
	
def downloadFfmpeg(parent_widget=None):
	
	downloadBaseUrl = 'https://www.lutraconsulting.co.uk/'
	destFolder = os.path.dirname(os.path.dirname(__file__))
	ffmpegZip = 'ffmpeg-20150505-git-6ef3426-win32-static.zip'
	ffmpegZipPath = os.path.join(destFolder, ffmpegZip)
	ffmpegUrl = downloadBaseUrl+'products/crayfish/viewer/binaries/'+findPlatformVersion()+'/extra/'+ffmpegZip

	qApp.setOverrideCursor(QCursor(Qt.WaitCursor))
	try:
		downloadBinPackage(ffmpegUrl, ffmpegZipPath)
		z = zipfile.ZipFile(ffmpegZipPath)
		z.extractall(destFolder)
		z.close()
		os.unlink(ffmpegZipPath)
		qApp.restoreOverrideCursor()
		return os.path.join(destFolder, 'ffmpeg.exe')
	except IOError as err:
		qApp.restoreOverrideCursor()
		QMessageBox.critical(parent_widget,
		  'Could Not Download FFmpeg',
		  "Download of FFmpeg failed. Please try again or contact us for "
		  "further assistance.\n\n(Error: %s)" % str(err))
		

def composition_set_time(c, time):
	for i in c.items():
		if isinstance(i, QgsLayoutItemLabel) and i.id() == "time":
			#txt = time_to_string(time)
			txt = '{0:02d}:{1:02.0f}:{2:05.2f}'.format(int(time), (time - int(time)) * 60, (time - int(time) - (time - int(time))) * 3600)
			i.setText(txt)


def prepare_composition_from_template(layout, template_path, time):
	document = QDomDocument()
	with open(template_path) as f:
		document.setContent(f.read())
	context = QgsReadWriteContext()
	context.setPathResolver(QgsProject.instance().pathResolver())
	context.setProjectTranslator(QgsProject.instance())
	layout.readLayoutXml(document.documentElement(), document, context)
	composition_set_time(layout, time)

	
def _page_size(layout):
	""" returns QgsLayoutSize """
	main_page = layout.pageCollection().page(0)
	return main_page.pageSize()


def animation(cfg, progress_fn=None, dialog=None):
	dpi = 96
	cfg["dpi"] = dpi
	l = cfg['layer']
	w, h = cfg['img_size']
	imgfile = cfg['tmp_imgfile']
	layers = cfg['layers'] if 'layers' in cfg else [l.id()]
	extent = cfg['extent'] if 'extent' in cfg else l.extent()
	crs = cfg['crs'] if 'crs' in cfg else None
	dataset_group_index = cfg['scalar index']
	assert (dataset_group_index)
	count = l.dataProvider().datasetCount(dataset_group_index)
	assert (count > 2)

	time_from, time_to = cfg['time']

	# store original values
	original_rs = l.rendererSettings()

	# animate
	imgnum = 0
	for i in range(count):

		if progress_fn:
			progress_fn(i, count)

		time = l.dataProvider().datasetMetadata(QgsMeshDatasetIndex(dataset_group_index, i)).time()
		if time < time_from or time > time_to:
			continue

		# Set to render next timesteps
		rs = l.rendererSettings()
		#asd = rs.activeScalarDataset()
		#if asd.isValid():
		#	rs.setActiveScalarDataset(QgsMeshDatasetIndex(asd.group(), i))
		#avd = rs.activeVectorDataset()
		#if avd.isValid():
		#	rs.setActiveVectorDataset(QgsMeshDatasetIndex(avd.group(), i))
		asd = cfg['scalar index']
		if asd:
			rs.setActiveScalarDataset(QgsMeshDatasetIndex(asd, i))
		avd = cfg['vector index']
		if avd:
			rs.setActiveVectorDataset(QgsMeshDatasetIndex(avd, i))
		l.setRendererSettings(rs)

		# Prepare layout
		layout = QgsPrintLayout(QgsProject.instance())
		layout.initializeDefaults()
		layout.setName('tuflow')

		layoutcfg = cfg['layout']
		if layoutcfg['type'] == 'file':
			prepare_composition_from_template(layout, cfg['layout']['file'], time)
			# when using composition from template, match video's aspect ratio to paper size
			# by updating video's width (keeping the height)
			aspect = _page_size(layout).width() / _page_size(layout).height()
			w = int(round(aspect * h))
		else:  # type == 'default'
			layout.renderContext().setDpi(dpi)
			layout.setUnits(QgsUnitTypes.LayoutMillimeters)
			main_page = layout.pageCollection().page(0)
			main_page.setPageSize(QgsLayoutSize(w * 25.4 / dpi, h * 25.4 / dpi, QgsUnitTypes.LayoutMillimeters))
			prepare_composition(layout, time, cfg, layoutcfg, extent, layers, crs, os.path.dirname(imgfile), dialog)

		imgnum += 1
		fname = imgfile % imgnum
		layout_exporter = QgsLayoutExporter(layout)
		image_export_settings = QgsLayoutExporter.ImageExportSettings()
		image_export_settings.dpi = dpi
		image_export_settings.imageSize = QSize(w, h)
		res = layout_exporter.exportToImage(os.path.abspath(fname), image_export_settings)
		if res != QgsLayoutExporter.Success:
			raise RuntimeError()

	if progress_fn:
		progress_fn(count, count)

	# restore original settings
	l.setRendererSettings(original_rs)


def set_composer_item_label(item, itemcfg):
	item.setBackgroundEnabled(itemcfg['background'])
	item.setBackgroundColor(itemcfg['background color'])
	item.setFont(itemcfg['font'])
	item.setFontColor(itemcfg['font colour'])


class CFItemPosition:
	TOP_LEFT = 0
	TOP_RIGHT = 1
	BOTTOM_LEFT = 2
	BOTTOM_RIGHT = 3
	TOP_CENTER = 4
	BOTTOM_CENTER = 5

def set_item_pos(item, posindex, layout):
	page_size = _page_size(layout)
	r = item.sizeWithUnits()
	assert (r.units() == QgsUnitTypes.LayoutMillimeters)
	assert (page_size.units() == QgsUnitTypes.LayoutMillimeters)

	if posindex == CFItemPosition.TOP_CENTER: # top-center
		item.attemptMove(QgsLayoutPoint((page_size.width() - r.width()) / 2, r.height(), QgsUnitTypes.LayoutMillimeters))
	elif posindex == CFItemPosition.BOTTOM_CENTER:
		item.attemptMove(QgsLayoutPoint((page_size.width() - r.width()) / 2, 0, QgsUnitTypes.LayoutMillimeters))
	elif posindex == CFItemPosition.TOP_LEFT:  # top-left
		item.attemptMove(QgsLayoutPoint(0, 0))
	elif posindex == CFItemPosition.TOP_RIGHT:  # top-right
		item.attemptMove(QgsLayoutPoint(page_size.width() - r.width(), 0, QgsUnitTypes.LayoutMillimeters))
	elif posindex == CFItemPosition.BOTTOM_LEFT:  # bottom-left
		item.attemptMove(QgsLayoutPoint(0, page_size.height() - r.height(), QgsUnitTypes.LayoutMillimeters))
	else: # bottom-right
		item.attemptMove(QgsLayoutPoint(page_size.width() - r.width(), page_size.height() - r.height(), QgsUnitTypes.LayoutMillimeters))
		
def fix_legend_box_size(cfg, legend):
	# adjustBoxSize() does not work without
	# call of the paint() function
	w, h = cfg['img_size']
	dpi = cfg['dpi']
	image = QImage(w, h, QImage.Format_ARGB32 )
	image.setDevicePixelRatio(dpi)
	p = QPainter(image)
	s = QStyleOptionGraphicsItem()
	legend.paint(p, s, None)
	p.end()
	# Now we can adjust box size
	legend.adjustBoxSize()
	
def setPlotProperties(fig, ax, prop, ax2):
	fig.set_size_inches(prop.sbFigSizeX.value() / 25.4, prop.sbFigSizeY.value() / 25.4)
	fig.suptitle(prop.leTitle.text())
	ax.set_xlabel(prop.leXLabel.text())
	ax.set_ylabel(prop.leYLabel.text())
	if ax2:
		ax2.set_ylabel(prop.leY2Label.text())
		ax2.set_ylim((prop.sbY2Min.value(), prop.sbY2Max.value()))
	ax.set_xlim((prop.sbXmin.value(), prop.sbXMax.value()))
	ax.set_ylim((prop.sbYMin.value(), prop.sbYMax.value()))
	if prop.cbGridY.isChecked() and prop.cbGridX.isChecked():
		ax.grid()
		ax.tick_params(axis="both", which="major", direction="out", length=10, width=1, bottom=True, top=False,
		                 left=True, right=False)
	elif prop.cbGridY.isChecked():
		ax.grid()
		ax.tick_params(axis="y", which="major", direction="out", length=10, width=1, bottom=True, top=False,
		            left=True, right=False)
	elif prop.cbGridX.isChecked():
		ax.grid()
		ax.tick_params(axis="x", which="major", direction="out", length=10, width=1, bottom=True, top=False,
		                 left=True, right=False)
	
	
def addLineToPlot(fig, ax, line, label):
	if label == 'Current Time':
		ylim = ax.get_ylim()
		line.set_ydata(ylim)
		ax.set_ylim(ylim)
	if type(line) is matplotlib.lines.Line2D:
		a, = ax.plot(line.get_data()[0], line.get_data()[1], label=label)
		applyMatplotLibArtist(a, line)
	elif type(line) is matplotlib.patches.Polygon:
		xy = line.get_xy()
		poly = Polygon(xy, facecolor='0.9', edgecolor='0.5', label=label)
		ax.add_patch(poly)
	
	
def isSecondaryNeeded(neededLabels, allLabels, allAxis):
	if 'axis 1' in allAxis and 'axis 2' in allAxis:
		axis1 = None
		axis2 = None
		for i, label in enumerate(allLabels):
			axis = allAxis[i]
			if axis == 'axis 1':
				axis1 = True
				if axis2:
					return True
			elif axis == 'axis 2':
				axis2 = True
				if axis1:
					return True
				
	return False
	

def prepare_composition(layout, time, cfg, layoutcfg, extent, layers, crs, dir, dialog):
	layout_map = QgsLayoutItemMap(layout)
	layout_map.attemptResize(_page_size(layout))
	set_item_pos(layout_map, CFItemPosition.TOP_LEFT, layout)
	layout_map.setLayers(layers)
	if crs is not None:
		layout_map.setCrs(crs)
	layout_map.setExtent(extent)
	layout_map.refresh()
	layout.setReferenceMap(layout_map)
	layout.addLayoutItem(layout_map)

	if 'title' in layoutcfg:
		cTitle = QgsLayoutItemLabel(layout)
		cTitle.setId('title')
		layout.addLayoutItem(cTitle)

		set_composer_item_label(cTitle, layoutcfg['title'])
		cTitle.setText(layoutcfg['title']['label'])
		cTitle.setHAlign(Qt.AlignCenter)
		cTitle.setVAlign(Qt.AlignCenter)
		cTitle.adjustSizeToText()
		set_item_pos(cTitle, layoutcfg['title']['position'], layout)

	if 'time' in layoutcfg:
		cTime = QgsLayoutItemLabel(layout)
		cTime.setId('time')
		layout.addLayoutItem(cTime)

		set_composer_item_label(cTime, layoutcfg['time'])
		composition_set_time(layout, time)
		cTime.adjustSizeToText()
		set_item_pos(cTime, layoutcfg['time']['position'], layout)

	if 'legend' in layoutcfg:
		cLegend = QgsLayoutItemLegend(layout)
		cLegend.setId('legend')
		cLegend.setLinkedMap(layout_map)
		layout.addLayoutItem(cLegend)

		itemcfg = layoutcfg['legend']
		cLegend.setBackgroundEnabled(itemcfg['background'])
		cLegend.setBackgroundColor(itemcfg['background color'])
		cLegend.setTitle(itemcfg['label'])
		for s in [QgsLegendStyle.Title,
				  QgsLegendStyle.Group,
				  QgsLegendStyle.Subgroup,
				  QgsLegendStyle.SymbolLabel]:
			cLegend.setStyleFont(s, itemcfg['font'])
		cLegend.setFontColor(itemcfg['font colour'])

		#cLegend.adjustBoxSize()
		fix_legend_box_size(cfg, cLegend)
		set_item_pos(cLegend, itemcfg['position'], layout)
		
	if 'plots' in layoutcfg:
		# update tuplot with new time and if time series, show current time - but don't draw
		dialog.tuView.tuPlot.updateCurrentPlot(0, retain_flow=True, draw=False, time=time, show_current_time=True)
		dialog.tuView.tuPlot.updateCurrentPlot(1, draw=False, time=time)
		
		# split out lines into specified plots
		for plot in sorted(layoutcfg['plots']):
			type = layoutcfg['plots'][plot]['type']
			position = layoutcfg['plots'][plot]['position']
			labels = layoutcfg['plots'][plot]['labels']
			properties = layoutcfg['plots'][plot]['properties']
			
			fig, ax = plt.subplots()
			ax2 = None
			lines, labs, axis = dialog.plotItems(type, include_duplicates=True)
			y2 = isSecondaryNeeded(labels, labs, axis)
			if y2:
				ax2 = ax.twinx()
			setPlotProperties(fig, ax, properties, ax2)
			for i, line in enumerate(lines):
				if labs[i] in labels or labs[i] == 'Current Time':
					addLineToPlot(fig, ax, line, labs[i])
			fig.tight_layout()
			fname = '{0}\\{1}-{2}.svg'.format(dir, plot, time)
			fig.savefig(fname)
			layoutcfg['plots'][plot]['source'] = fname
			
			cPlot = QgsLayoutItemPicture(layout)
			cPlot.setId('plot_{0}'.format(plot))
			cPlot.setPicturePath(fname)
			cPlot.attemptResize(QgsLayoutSize(properties.sbFigSizeX.value(), properties.sbFigSizeY.value()))
			layout.addItem(cPlot)
			set_item_pos(cPlot, position, layout)


def images_to_video(tmp_img_dir="/tmp/vid/%03d.png", output_file="/tmp/vid/test.avi", fps=10, qual=1,
					ffmpeg_bin="ffmpeg"):
	if qual == 0:  # lossless
		opts = ["-vcodec", "ffv1"]
	else:
		bitrate = 10000 if qual == 1 else 2000
		opts = ["-vcodec", "mpeg4", "-b", str(bitrate) + "K"]

	# if images do not start with 1: -start_number 14
	cmd = [ffmpeg_bin, "-f", "image2", "-framerate", str(fps), "-i", tmp_img_dir]
	cmd += opts
	cmd += ["-r", str(fps), "-f", "avi", "-y", output_file]

	f = tempfile.NamedTemporaryFile(prefix="tuflow", suffix=".txt")
	f.write(str.encode(" ".join(cmd) + "\n\n"))

	# stdin redirection is necessary in some cases on Windows
	res = subprocess.call(cmd, stdin=subprocess.PIPE, stdout=f, stderr=f)
	if res != 0:
		f.delete = False  # keep the file on error

	return res == 0, f.name


class TuAnimationDialog(QDialog, Ui_AnimationDialog):
	def __init__(self, TuView):
		QDialog.__init__(self)
		self.setupUi(self)
		self.tuView = TuView
		self.iface = TuView.iface
		self.project = TuView.project
		self.canvas = TuView.canvas
		self.pbDialogs = {}
		self.dialog2Plot = {}
		
		self.populateGeneralTab()
		self.populateLayoutTab()
		self.populateVideoTab()
		
		self.cboResult.currentIndexChanged.connect(lambda: self.populateGeneralTab(ignore='results'))
		self.btnBrowseOutput.clicked.connect(lambda: self.browse('save', 'TUFLOW/animation_outfolder', "AVI files (*.avi)", self.editOutput))
		self.btnBrowseTemplate.clicked.connect(lambda: self.browse('load', "TUFLOW/animation_ffmpeg", "QGIS Print Layout (*.qpt)", self.editTemplate))
		self.btnBrowseFfmpegPath.clicked.connect(lambda: self.browse('ffmpeg', 'TUFLOW/animation_ffmep', "FFmpeg (ffmpeg ffmpeg.exe avconv avconv.exe)", self.editTemplate))
		self.btnAddPlot.clicked.connect(self.addPlot)
		self.btnRemovePlot.clicked.connect(self.removePlot)
		self.btnAddImage.clicked.connect(self.addImage)
		self.btnRemoveImage.clicked.connect(self.removeImage)
		self.buttonBox.accepted.connect(self.check)

	def populateGeneralTab(self, ignore=None):
		"""
		Populates widgets in general tab.
		
		:return: void
		"""
		
		if ignore != 'results':
			self.populateResults()
		if ignore != 'times':
			self.populateTimes()
		if ignore != 'types':
			self.populateResultTypes()
		
		folderIcon = QgsApplication.getThemeIcon('\mActionFileOpen.svg')
		self.btnBrowseOutput.setIcon(folderIcon)
		
	def populateLayoutTab(self):
		"""
		Populates widgets in Layout Tab
		
		:return: void
		"""
		
		addIcon = QgsApplication.getThemeIcon('\symbologyAdd.svg')
		removeIcon = QgsApplication.getThemeIcon('\symbologyRemove.svg')
		upIcon = QgsApplication.getThemeIcon('\mActionArrowUp.svg')
		downIcon = QgsApplication.getThemeIcon('\mActionArrowDown.svg')
		folderIcon = QgsApplication.getThemeIcon('\mActionFileOpen.svg')
		
		self.btnAddPlot.setIcon(addIcon)
		self.btnRemovePlot.setIcon(removeIcon)
		self.btnPlotUp.setIcon(upIcon)
		self.btnPlotDown.setIcon(downIcon)
		
		self.btnAddImage.setIcon(addIcon)
		self.btnRemoveImage.setIcon(removeIcon)
		self.btnImageUp.setIcon(upIcon)
		self.btnImageDown.setIcon(downIcon)
		
		self.btnBrowseTemplate.setIcon(folderIcon)
		
	def populateVideoTab(self):
		"""
		Populates widgets in Video Tab
		
		:return: void
		"""
		
		folderIcon = QgsApplication.getThemeIcon('\mActionFileOpen.svg')
		self.btnBrowseFfmpegPath.setIcon(folderIcon)
		
		settings = QSettings()
		ffmpeg = settings.value("TUFLOW/animation_ffmpeg_switch")
		ffmpegLoc = settings.value("TUFLOW/animation_ffmpeg")
		switch = True if ffmpeg == 'custom' else False
		self.radFfmpegCustom.setChecked(switch)
		self.editFfmpegPath.setText(ffmpegLoc)
		
	def browse(self, type, key, fileType, lineEdit):
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
		if type == 'save':
			f = QFileDialog.getSaveFileName(self, 'Ouput', startDir, fileType)[0]
		elif type == 'load':
			f = QFileDialog.getOpenFileName(self, 'Import Template', startDir, fileType)[0]
		elif type == 'image':
			f = QFileDialog.getOpenFileName(self, 'Image File', startDir, fileType)[0]
		elif type == 'ffmpeg':
			f = QFileDialog.getOpenFileName(self, 'FFmpeg Location', startDir, fileType)[0]
		else:
			return
		if f:
			lineEdit.setText(f)
			settings.setValue(key, f)
	
	def populateResults(self):
		"""
		Populates open results combobox
		
		:return: void
		"""
		
		selected = None
		for i in range(self.tuView.OpenResults.count()):
			item = self.tuView.OpenResults.item(i)
			self.cboResult.addItem(item.text())
			if selected is None and item in self.tuView.OpenResults.selectedItems():
				selected = i
		if selected is not None:
			self.cboResult.setCurrentIndex(selected)
			
	def populateTimes(self):
		"""
		Populates start and end time combobox
		
		:return: void
		"""
		
		self.cboStart.clear()
		self.cboEnd.clear()
		for i in range(self.tuView.cboTime.count()):
			item = self.tuView.cboTime.itemText(i)
			self.cboStart.addItem(item)
			self.cboEnd.addItem(item)
		
		self.cboStart.setCurrentIndex(self.tuView.cboTime.currentIndex())
		self.cboEnd.setCurrentIndex(self.tuView.cboTime.count() - 1)
		
	def populateResultTypes(self):
		"""
		Populate scalar and vector result type options.
		
		:return: void
		"""
		
		self.cboScalar.clear()
		self.cboVector.clear()
		
		resultName = self.cboResult.currentText()
		scalarResults, vectorResults = ['-None-'], ['-None-']
		activeScalar, activeVector = 0, 0
		scalarCount, vectorCount = 0, 0
		
		if resultName:
			result = self.tuView.tuResults.results[resultName]  # dict -> e.g. { 'Depth': { '0.000': ( timestep, scalar / vector type, QgsMeshDatasetIndex ) } }
			for  rtype, ts in result.items():
				if rtype == 'Bed Elevation':
					continue
				if '_ts' not in rtype and '_lp' not in rtype and '/Maximums' not in rtype:  # temporal map output result type
					for key, item in ts.items():
						if item[1] == 1:
							scalarResults.append(rtype)
							scalarCount += 1
							if rtype in self.tuView.tuResults.activeResults:
								activeScalar = scalarCount
						elif item[1] == 2:
							vectorResults.append(rtype)
							vectorCount += 1
							if rtype in self.tuView.tuResults.activeResults:
								activeVector = vectorCount
						break  # only need to check one entry
		
		self.cboScalar.addItems(scalarResults)
		self.cboVector.addItems(vectorResults)
		self.cboScalar.setCurrentIndex(activeScalar)
		self.cboVector.setCurrentIndex(activeVector)
		
	def plotItems(self, type, **kwargs):
		"""
		Returns a list of plot item labels and artists
		
		:param plotNo:
		:return:
		"""
		
		# deal with kwargs
		includeDuplicates = kwargs['include_duplicates'] if 'include_duplicates' in kwargs.keys() else False
		
		if type == 'Time Series':
			plotNo = 0
		elif type == 'CS / LP':
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
	
	def addPlot(self, event=None, plotTypeTemplate=None, mcboPlotItemTemplate=None, cboPosTemplate=None, pbTemplate=None):
		"""
		Add plot to QTableWidget
		
		:return: void
		"""
		
		self.tablePlots.horizontalHeader().setVisible(True)
		self.tablePlots.setRowCount(self.tablePlots.rowCount() + 1)
		
		cboPlotType = QComboBox()
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
		pb.clicked.connect(lambda: dialog.setDefaults(self, cboPlotType.currentText(), mcboPlotItems.checkedItems()))
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
				if i not in selectionRange:
					col1.append(self.tablePlots.cellWidget(i, 0))
					col2.append(self.tablePlots.cellWidget(i, 1))
					col3.append(self.tablePlots.cellWidget(i, 2))
					pb = self.pbDialogs[self.tablePlots.cellWidget(i, 3)]
					col4.append(pb)
			self.tablePlots.setRowCount(0)
			for i in range(len(col1)):  # adding widgets directly back from the list caused QGIS to crash :(
				self.addPlot(plotTypeTemplate=col1[i], mcboPlotItemTemplate=col2[i], cboPosTemplate=col3[i], pbTemplate=col4[i])
		else:
			self.tablePlots.setRowCount(self.tablePlots.rowCount() - 1)
		
	def plotTypeChanged(self, text, mcbo):
		"""
		Action when plot type is changed between Time Series and CS/ LP
		
		:return: void
		"""
		
		mcbo.clear()
		lines, labs, axis = self.plotItems(text)
		mcbo.addItems(labs)
		
	def addImage(self, event=None, widgetImageTemplate=None, cboPosTemplate=None, xSizeTemplate=None, ySizeTemplate=None):
		"""
		Add image to image table.
		
		:return: void
		"""
		
		self.tableImages.setRowCount(self.tableImages.rowCount() + 1)
		
		folderIcon = QgsApplication.getThemeIcon('\mActionFileOpen.svg')
		btnBrowse = QToolButton()
		btnBrowse.setIcon(folderIcon)
		btnBrowse.setToolTip('Image Location')
		#btnBrowse.setMaximumHeight(21)
		
		leImage = QLineEdit()
		leImage.setMaximumHeight(20)
		if widgetImageTemplate is not None:
			leImage.setText(widgetImageTemplate.layout().itemAt(1).widget().text())
		
		widget = QWidget()
		hbox = QHBoxLayout()
		hbox.addWidget(btnBrowse)
		hbox.addWidget(leImage)
		hbox.setContentsMargins(0, 0, 0, 0)
		widget.setLayout(hbox)
		widget.setMaximumHeight(20)
		
		cboPos = QComboBox()
		cboPos.setEditable(True)
		cboPos.setMaximumHeight(20)
		cboPos.setMaximumWidth(190)
		cboPos.addItem('Top-Left')
		cboPos.addItem('Top-Right')
		cboPos.addItem('Bottom-Left')
		cboPos.addItem('Bottom-Right')
		if cboPosTemplate is not None:
			cboPos.setCurrentIndex(cboPosTemplate.currentIndex())
		
		xitem = QTableWidgetItem(0)
		if xSizeTemplate is not None:
			xitem.setText(xSizeTemplate)
		else:
			xitem.setText('100')
		yitem = QTableWidgetItem(0)
		if ySizeTemplate is not None:
			yitem.setText(ySizeTemplate)
		else:
			yitem.setText('100')
		
		self.tableImages.setCellWidget(self.tableImages.rowCount() - 1, 0, widget)
		self.tableImages.setCellWidget(self.tableImages.rowCount() - 1, 1, cboPos)
		self.tableImages.setItem(self.tableImages.rowCount() - 1, 2, xitem)
		self.tableImages.setItem(self.tableImages.rowCount() - 1, 3, yitem)
		
		btnBrowse.clicked.connect(lambda: self.browse('image', 'TUFLOW/animation_image', "All Files(*)", leImage))
		
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
		col4 = []
		if selectionRange:
			for i in range(self.tableImages.rowCount()):
				self.tableImages.cellWidget(i, 0).layout().itemAt(0).widget().clicked.disconnect()
				if i not in selectionRange:
					col1.append(self.tableImages.cellWidget(i, 0))
					col2.append(self.tableImages.cellWidget(i, 1))
					col3.append(self.tableImages.item(i, 2).text())
					col4.append(self.tableImages.item(i, 3).text())
			self.tableImages.setRowCount(0)
			for i in range(len(col1)):  # adding widgets directly back from the list caused QGIS to crash :(
				self.addImage(widgetImageTemplate=col1[i], cboPosTemplate=col2[i], xSizeTemplate=col3[i], ySizeTemplate=col4[i])
		else:
			self.tableImages.setRowCount(self.tableImages.rowCount() - 1)
			
	def check(self):
		"""
		Checks input parameters before trying to run the tool and destroying the dialog.
		
		:return: void
		"""

		# General Tab
		if not self.cboResult.currentText():
			QMessageBox.information(self, 'Input Error', 'No Result File Selected')
			return
		if self.cboScalar.currentText() == '-None-' and self.cboVector.currentText() == '-None-':
			QMessageBox.information(self, 'Input Error', 'Must Choose at Least One Scalar or Vector Result Type')
			return
		startTimeConverted = self.cboStart.currentText().split(':')
		startTimeConverted = float(startTimeConverted[0]) + float(startTimeConverted[1]) / 60 + float(startTimeConverted[2]) / 3600
		endTimeConverted = self.cboEnd.currentText().split(':')
		endTimeConverted = float(endTimeConverted[0]) + float(endTimeConverted[1]) / 60 + float(endTimeConverted[2]) / 3600
		if startTimeConverted >= endTimeConverted:
			QMessageBox.information(self, 'Input Error', 'End Time Must Be Later Than Start Time')
			return
		if not self.editOutput.text():
			QMessageBox.information(self, 'Input Error', 'Must Specify Output Folder')
			return
		self.layer = tuflowqgis_find_layer(self.cboResult.currentText())
		if self.layer is None:
			QMessageBox.information(self, 'Input Error',
									'Cannot Find Result File in QGIS: {0}'.format(self.cboResult.currentText()))
		if self.layer.type() != 3:
			QMessageBox.information(self, 'Input Error',
									'Error finding Result Mesh Layer: {0}'.format(self.cboResult.currentText()))
		if not os.path.exists(os.path.dirname(self.editOutput.text())):
			QMessageBox.information(self, 'Input Error', 'Could Not Find Output Folder:\n{0}'.format(self.editOutput.text()))
			return
			
		# Layout Tab
		for i in range(self.tableImages.rowCount()):
			if not os.path.exists(self.tableImages.cellWidget(i, 0).layout().itemAt(1).widget().text()):
				QMessageBox.information(
					self, 'Input Error', 'Cannot Find Image:\n{0}'.format(
						self.tableImages.cellWidget(i, 0).layout().itemAt(1).widget().text()))
				return
		if self.radLayoutCustom.isChecked():
			if not os.path.exists(self.editTemplate.text()):
				QMessageBox.information(
					self, 'Input Error', 'Cannot Find Custom Layout Template:\n{0}'.format(self.editTemplate.text()))
				return
				
		# Video Tab
		if self.radFfmpegSystem.isChecked():
			self.ffmpeg_bin = "ffmpeg"
			# debian systems use avconv (fork of ffmpeg)
			if which(self.ffmpeg_bin) is None:
				self.ffmpeg_bin = "avconv"
		else:
			self.ffmpeg_bin = self.editFfmpegPath.text()  # custom path
			if not self.ffmpeg_bin:
				QMessageBox.information(self, 'Input Error', 'Missing FFmpeg exe Location')
				return
			elif not os.path.exists(self.ffmpeg_bin):
				QMessageBox.information(self, 'Input Error',
										'Could Not Find FFmpeg exe:\n{0}'.format(self.ffmpeg_bin))
				return
		
		if which(self.ffmpeg_bin) is None:
			QMessageBox.warning(self, "FFmpeg missing",
								"The tool for video creation (<a href=\"http://en.wikipedia.org/wiki/FFmpeg\">FFmpeg</a>) "
								"is missing. Please check your FFmpeg configuration in <i>Video</i> tab.<p>"
								"<b>Windows users:</b> Let the TUFLOW plugin download FFmpeg automatically (by clicking OK) or "
								"<a href=\"http://ffmpeg.zeranoe.com/builds/\">download</a> FFmpeg manually "
								"and configure path in <i>Video</i> tab to point to ffmpeg.exe.<p>"
								"<b>Linux users:</b> Make sure FFmpeg is installed in your system - usually a package named "
								"<tt>ffmpeg</tt>. On Debian/Ubuntu systems FFmpeg was replaced by Libav (fork of FFmpeg) "
								"- use <tt>libav-tools</tt> package.<p>"
								"<b>MacOS users:</b> Make sure FFmpeg is installed in your system <tt>brew install ffmpeg</tt>")
			
			if platform.system() != 'Windows':
				return
			
			# special treatment for Windows users!
			# offer automatic download and installation from Lutra web.
			# Official distribution is not used because:
			# 1. packages use 7zip compression (need extra software)
			# 2. packages contain extra binaries we do not need
			
			reply = QMessageBox.question(self,
										 'Download FFmpeg',
										 "Would you like to download and auto-configure FFmpeg?\n\n"
										 "The download may take some time (~13 MB).\n"
										 "FFmpeg will be downloaded to Crayfish plugin's directory.",
										 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
			if reply != QMessageBox.Yes:
				return
			
			self.ffmpeg_bin = downloadFfmpeg(self)
			if not self.ffmpeg_bin:
				return
			
			# configure the path automatically
			self.radFfmpegCustom.setChecked(True)
			self.editFfmpegPath.setText(self.ffmpeg_bin)
			s = QSettings()
			s.setValue("TUFLOW/animation_ffmpeg_switch", "custom")
			s.setValue("TUFLOW/animation_ffmpeg", self.ffmpeg_bin)
			
		self.run()
	
	def updateProgress(self, i, cnt):
		""" callback from animation routine """
		self.progress.setMaximum(cnt)
		self.progress.setValue(i)
		qApp.processEvents()
	
	def quality(self):
		if self.radQualBest.isChecked():
			return 0
		elif self.radQualLow.isChecked():
			return 2
		else:  # high
			return 1
		
	def viewToolbar(self, plotType):
		if plotType == 'Time Series':
			return self.tuPlot.tuPlotToolbar.viewToolbarTimeSeries
		elif plotType == 'CS / LP':
			return self.tuPlot.tuPlotToolbar.viewToolbarLongPlot
		elif plotType == 'Cross Section':
			return self.tuPlot.tuPlotToolbar.viewToolbarCrossSection
		else:
			return None
		
	def plotAxisLimits(self, plotType, axis):
		if type == 'Time Series':
			plotNo = 0
		elif type == 'CS / LP':
			plotNo = 1
		else:
			return [], []
		
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.tuView.tuPlot.plotEnumerator(plotNo)
		
		if axis == 'x':
			return subplot.get_xlim()
		elif axis == 'y1':
			return subplot.get_ylim()
		elif axis == 'y2':
			subplot2 = self.tuView.tuPlot.getSecondaryAxis()
			return subplot2.get_ylim()
		
	def getResultType(self, plotType, label):
		rt = label
		if plotType == 'Time Series':
			for resultType, userLabel in self.tuView.tuPlot.frozenTSProperties.items():
				if userLabel[0] == label:
					rt = resultType
					break
		elif plotType == 'CS / LP':
			for resultType, userLabel in self.tuView.tuPlot.frozenLPProperties.items():
				if userLabel[0] == label:
					rt = resultType
					break
		
		if plotType == 'Time Series':
			plotNo = 0
		elif plotType == 'CS / LP':
			plotNo = 1
		
		for t in self.tuView.tuPlot.tuPlotToolbar.getItemsFromPlotOptions(0):
			if t in rt:
				return t  # e.g. 'Water Level point 1' returns 'Water Level'
		
		
	def run(self):
		"""
		Run tool to create animation
		
		:return: void
		"""

		self.buttonBox.setEnabled(False)  # disable button box so users know something is happening
		QApplication.setOverrideCursor(Qt.WaitCursor)
		
		# save plot settings so line colours won't vary over time
		self.tuView.tuPlot.setNewPlotProperties(0)
		self.tuView.tuPlot.setNewPlotProperties(1)
		
		# get results
		asd = self.cboScalar.currentText()
		avd = self.cboVector.currentText()
		if asd == '-None-':
			asd = None
		if avd == '-None-':
			avd = None
		for i in range(self.layer.dataProvider().datasetGroupCount()):
			if self.layer.dataProvider().datasetGroupMetadata(i).name() == asd:
				asd = i
			if self.layer.dataProvider().datasetGroupMetadata(i).name() == avd:
				avd = i
		
		# Get start and end time
		tStart = self.cboStart.currentText().split(':')
		tStart = float(tStart[0]) + float(tStart[1]) / 60 + float(tStart[2]) / 3600
		tStartKey = '{0:.4f}'.format(tStart)
		tEnd = self.cboEnd.currentText().split(':')
		tEnd = float(tEnd[0]) + float(tEnd[1]) / 60 + float(tEnd[2]) / 3600
		tEndKey = '{0:.4f}'.format(tEnd)
		
		# Get video settings
		w = self.spinWidth.value()  # width
		h = self.spinHeight.value()  # height
		fps = self.spinSpeed.value()  # frames per second
		
		# Get output directory for images
		tmpdir = tempfile.mkdtemp(prefix='tuflow')
		img_output_tpl = os.path.join(tmpdir, "%03d.png")
		tmpl = None  # path to template file to be used
		
		# get output for animation
		output_file = self.editOutput.text()
		QSettings().setValue('TUFLOW/animation_outfolder', output_file)
		
		# Get Map Layout properties
		titleProp = {}
		if self.groupTitle.isChecked():
			titleProp['label'] = self.labelTitle.text()
			titleProp['font'] = self.fbtnTitle.currentFont()
			titleProp['font colour'] = self.colorTitleText.color()
			titleProp['background'] = self.cbTitleBackground.isChecked()
			titleProp['background color'] = self.colorTitleBackground.color()
			titleProp['position'] = self.cboPosTitle.currentIndex()
		timeProp = {}
		if self.groupTime.isChecked():
			timeProp['label'] = self.labelTime.text()
			timeProp['font'] = self.fbtnTime.currentFont()
			timeProp['font colour'] = self.colorTimeText.color()
			timeProp['background'] = self.cbTimeBackground.isChecked()
			timeProp['background color'] = self.colorTimeBackground.color()
			timeProp['position'] = self.cboPosTime.currentIndex()
		legendProp = {}
		if self.groupLegend.isChecked():
			legendProp['label'] = self.labelLegend.text()
			legendProp['font'] = self.fbtnLegend.currentFont()
			legendProp['font colour'] = self.colorLegendText.color()
			legendProp['background'] = self.cbLegendBackground.isChecked()
			legendProp['background color'] = self.colorLegendBackground.color()
			legendProp['position'] = self.cboPosLegend.currentIndex()
		layout = {}
		if self.radLayoutDefault.isChecked():
			layout['type'] = 'default'
			layout['file'] = None
			if self.groupTitle.isChecked():
				layout['title'] = titleProp
			if self.groupTime.isChecked():
				layout['time'] = timeProp
			if self.groupLegend.isChecked():
				layout['legend'] = legendProp
		else:
			layout['type'] = 'file'
			layout['file'] = self.editTemplate.text()
			
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
			layout['plots'] = plot
			
		# Get Image Data
		if self.groupImages.isChecked():
			image = {}
			imageCount = 0
			for i in range(self.tableImages.rowCount()):
				imageDict = {
					'source': self.tableImages.cellWidget(i, 0).layout().itemAt(1).widget().text(),
					'location': self.tableImages.cellWidget(i, 1).currentText()
				}
				image[imageCount] = imageDict
				imageCount += 1
			layout['images'] = image
		
		prog = lambda i, count: self.updateProgress(i, count)  # progress bar
		
		# put collected data into dictionary for easy access later
		d = {'layer': self.layer,
			 'time': (tStart, tEnd),
			 'img_size': (w, h),
			 'tmp_imgfile': img_output_tpl,
			 'layers': self.canvas.layers(),
			 'extent': self.canvas.extent(),
			 'crs': self.canvas.mapSettings().destinationCrs(),
			 'layout': layout,
		     'scalar index': asd,
		     'vector index': avd
			 }
		
		for pb, dialog in self.pbDialogs.items():
			dialog.setDefaults(self, self.dialog2Plot[dialog][0].currentText(), self.dialog2Plot[dialog][1].checkedItems())
		animation(d, prog, self)
		self.tuView.tuPlot.updateCurrentPlot(0, retain_flow=True)
		self.tuView.tuPlot.updateCurrentPlot(1)
		
		ffmpeg_res, logfile = images_to_video(img_output_tpl, output_file, fps, self.quality(), self.ffmpeg_bin)
		
		if ffmpeg_res:
			shutil.rmtree(tmpdir)
		
		QApplication.restoreOverrideCursor()
		
		self.updateProgress(0, 1)
		
		self.buttonBox.setEnabled(True)
		
		if ffmpeg_res:
			QMessageBox.information(self, "Export", "The export of animation was successful!")
		else:
			QMessageBox.warning(self, "Export",
			                    "An error occurred when converting images to video. "
			                    "The images are still available in " + tmpdir + "\n\n"
			                                                                    "This should not happen. Please file a ticket in "
			                                                                    "Crayfish issue tracker with the contents from the log file:\n" + logfile)
		
		#self.storeDefaults()
		
		self.accept()
		
	
class PlotProperties(QDialog, Ui_PlotProperties):
	
	def __init__(self, animationDialog, cboPlotType, mcboPlotItems):
		QDialog.__init__(self)
		self.setupUi(self)
		self.userSet = False  # once user has entered properties and left once, don't update anymore
		self.animationDialog = animationDialog
		self.cboPlotType = cboPlotType
		self.mcboPlotItems = mcboPlotItems
		
		self.pbAutoCalcXLim.clicked.connect(lambda event: self.setDefaults(self.animationDialog, self.cboPlotType, self.mcboPlotItems, 'x limits'))
		self.pbAutoCalcYLim.clicked.connect(lambda event: self.setDefaults(self.animationDialog, self.cboPlotType, self.mcboPlotItems, 'y limits'))
		self.pbAutoCalcY2Lim.clicked.connect(lambda event: self.setDefaults(self.animationDialog, self.cboPlotType, self.mcboPlotItems, 'y2 limits'))
		self.buttonBox.accepted.connect(self.userSetTrue)
		
	def userSetTrue(self): self.userSet = True
		
	def applyPrevious(self, prop=None):
		
		if prop is not None:
			self.leTitle.setText(prop.leTitle.text())
			self.leXLabel.setText(prop.leXLabel.text())
			self.leYLabel.setText(prop.leYLabel.text())
			self.leY2Label.setText(prop.leY2Label.text())
			self.sbXmin.setValue(prop.sbXmin.value())
			self.sbXMax.setValue(prop.sbXMax.value())
			self.sbYMin.setValue(prop.sbYMin.value())
			self.sbYMax.setValue(prop.sbYMax.value())
			self.sbY2Min.setValue(prop.sbY2Min.value())
			self.sbY2Max.setValue(prop.sbY2Max.value())
			self.cbLegend.setChecked(prop.cbLegend.isChecked())
			self.cboLegendPos.setCurrentIndex(prop.cboLegendPos.currentIndex())
			self.cbGridY.setChecked(prop.cbGridY.isChecked())
			self.cbGridX.setChecked(prop.cbGridX.isChecked())
			self.sbFigSizeX.setValue(prop.sbFigSizeX.value())
			self.sbFigSizeY.setValue(prop.sbFigSizeY.value())
	
	def setDefaults(self, animation, plotType, items, recalculate=''):
		if type(plotType) is not str:
			plotType = plotType.currentText()
		if type(items) is not list:
			items = items.checkedItems()
		
		li, la, ax = animation.plotItems(plotType)
		lines, labels, axis = [], [], []
		for item in items:
			i = la.index(item) if la.count(item) else -1
			if i > -1:
				lines.append(li[i])
				labels.append(la[i])
				axis.append(ax[i])
		
		# X Axis Label
		if plotType == 'Time Series':
			if self.leXLabel.text() == 'Chainage' or not self.userSet:  # sitting on default or user hasn't made changes
				self.leXLabel.setText('Time')
		elif plotType == 'CS / LP':
			if self.leXLabel.text() == 'Time' or not self.userSet:  # sitting on default or user hasn't made changes
				self.leXLabel.setText('Chainage')
				
		# X Axis Limits
		if not self.userSet or recalculate == 'x limits':
			for item in items:
				if item != 'Current Time' and item != 'Culverts and Pipes':
					i = labels.index(item) if labels.count(item) else -1
					if i > -1:
						x = lines[i].get_xdata()
						margin = (max(x) - min(x)) * 0.05
						self.sbXmin.setValue(np.nanmin(x) - margin)
						self.sbXMax.setValue(np.nanmax(x) + margin)
						break
					self.sbXmin.setValue(0)
					self.sbXMax.setValue(1)
				
		# Y Axis Label
		if not self.userSet:
			if items:
				if 'axis 1' in axis and 'axis 2' in axis:
					for item in items:
						i = labels.index(item) if labels.count(item) else -1
						if i > -1:
							if axis[i] == 'axis 1':
								self.leYLabel.setText(item)
								break
				else:
					self.leYLabel.setText(items[0])
				
		# Y2 Axis Label
		userSetY2 = True
		if 'axis 1' in axis and 'axis 2' in axis:
			if self.sbY2Min.value() == 0 and self.sbY2Max.value() == 0:
				userSetY2 = False
		if not self.userSet or not userSetY2:
			if items:
				if 'axis 1' in axis and 'axis 2' in axis:
					for item in items:
						i = labels.index(item) if labels.count(item) else -1
						if i > -1:
							if axis[i] == 'axis 2':
								self.leY2Label.setText(item)
								break
					
		# Y and Y2 Axis limits
		if (not self.userSet or not userSetY2) or recalculate == 'y limits' or recalculate == 'y2 limits':
			# set up progress bar since extracting from long sections can take some time
			maxProgress = 0
			maxProgress = animation.tuView.cboTime.count() * len(items)
			if maxProgress:
				animation.iface.messageBar().clearWidgets()
				progressWidget = animation.iface.messageBar().createMessage("Tuview",
				                                                            " Calculating Plot Minimums and Maximums . . .")
				messageBar = animation.iface.messageBar()
				progress = QProgressBar()
				progress.setMaximum(100)
				progressWidget.layout().addWidget(progress)
				messageBar.pushWidget(progressWidget, duration=1)
				animation.iface.mainWindow().repaint()
				pComplete = 0
				complete = 0
			if plotType == 'Time Series':
				if items:
					ymin = 99999
					ymax = -99999
					if 'axis 1' in axis and 'axis 2' in axis:
						ymin2 = 99999
						ymax2 = -99999
						for item in items:
							if item != 'Current Time':
								i = labels.index(item) if labels.count(item) else -1
								if i > -1:
									if axis[i] == 'axis 1':
										y = lines[i].get_ydata()
										ymin = min(ymin, np.nanmin(y))
										ymax = max(ymax, np.nanmax(y))
									elif axis[i] == 'axis 2':
										y = lines[i].get_ydata()
										ymin2 = min(ymin2, np.nanmin(y))
										ymax2 = max(ymax2, np.nanmax(y))
							complete += 1 * animation.tuView.cboTime.count()
							pComplete = complete / maxProgress * 100
							progress.setValue(pComplete)
						margin = (ymax - ymin) * 0.05
						margin2 = (ymax2 - ymin2) * 0.05
						if not self.userSet or recalculate == 'y limits':
							self.sbYMin.setValue(ymin - margin)
							self.sbYMax.setValue(ymax + margin)
						if recalculate != 'y limits':
							self.sbY2Min.setValue(ymin2 - margin2)
							self.sbY2Max.setValue(ymax2 + margin2)
					elif not self.userSet or recalculate == 'y limits':
						for item in items:
							if item != 'Current Time':
								i = labels.index(item) if labels.count(item) else -1
								if i > -1:
									y = lines[i].get_ydata()
									ymin = min(ymin, np.nanmin(y))
									ymax = max(ymax, np.nanmax(y))
							complete += 1 * animation.tuView.cboTime.count()
							pComplete = complete / maxProgress * 100
							progress.setValue(pComplete)
						margin = (ymax - ymin) * 0.05
						self.sbYMin.setValue(ymin - margin)
						self.sbYMax.setValue(ymax + margin)
				else:
					self.sbYMin.setValue(0)
					self.sbYMax.setValue(1)
			else:  # long plot / cross section - so need to loop through all timesteps to get max
				if items:
					ymin = 99999
					ymax = -99999
					ymin2 = 99999
					ymax2 = -99999
					for i in range(animation.tuView.cboTime.count()):
						timeFormatted = animation.tuView.cboTime.itemText(i)
						time = timeFormatted.split(':')
						time = float(time[0]) + float(time[1]) / 60 + float(time[2]) / 3600
						timeKey = '{0:.4f}'.format(time)
						animation.tuView.tuPlot.updateCurrentPlot(1, draw=False, time=time)
						lines, labels, axis = animation.plotItems(plotType)
						if 'axis 1' in axis and 'axis 2' in axis:
							for item in items:
								i = labels.index(item) if labels.count(item) else -1
								if i > -1:
									if axis[i] == 'axis 1':
										if type(lines[i]) is matplotlib.lines.Line2D:
											y = lines[i].get_ydata()
										elif type(lines[i]) is matplotlib.patches.Polygon:
											xy = lines[i].line.get_xy()
											y = xy[:, 1]
										ymin = min(ymin, np.nanmin(y))
										ymax = max(ymax, np.nanmax(y))
									elif axis[i] == 'axis 2':
										y = lines[i].get_ydata()
										ymin2 = min(ymin2, np.nanmin(y))
										ymax2 = max(ymax2, np.nanmax(y))
								complete += 1
								pComplete = complete / maxProgress * 100
								progress.setValue(pComplete)
						elif not self.userSet or recalculate == 'y limits':
							for item in items:
								if item != 'Current Time':
									i = labels.index(item) if labels.count(item) else -1
									if i > -1:
										if type(lines[i]) is matplotlib.lines.Line2D:
											y = lines[i].get_ydata()
										elif type(lines[i]) is matplotlib.patches.Polygon:
											xy = lines[i].get_xy()
											y = xy[:, 1]
										ymin = min(ymin, np.nanmin(y))
										ymax = max(ymax, np.nanmax(y))
								complete += 1
								pComplete = complete / maxProgress * 100
								progress.setValue(pComplete)
					margin = (ymax - ymin) * 0.05
					if not self.userSet or recalculate == 'y limits':
						self.sbYMin.setValue(ymin - margin)
						self.sbYMax.setValue(ymax + margin)
					if ymin2 != 99999 and ymax2 != -99999:
						if not self.userSet or recalculate == 'y2 limits':
							margin2 = (ymax2 - ymin2) * 0.05
							self.sbY2Min.setValue(ymin2 - margin2)
							self.sbY2Max.setValue(ymax2 + margin2)
				else:
					self.sbYMin.setValue(0)
					self.sbYMax.setValue(1)
				
					