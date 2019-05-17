import platform
import os
import sys
import shutil
import tempfile
import zipfile
import subprocess
from datetime import datetime
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
from label_properties import Ui_textPropertiesDialog
from image_properties import Ui_ImageProperties
from tuflow.tuflowqgis_library import tuflowqgis_find_layer, applyMatplotLibArtist, convertTimeToFormattedTime, convertFormattedTimeToTime
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


def findLayoutItem(layout, id):
	for i in layout.items():
		if isinstance(i, QgsLayoutItemPicture) and i.id() == id:
			return i
		
	return None


def composition_set_time(c, time):
	for i in c.items():
		if isinstance(i, QgsLayoutItemLabel) and i.id() == "time":
			#txt = time_to_string(time)
			if time < 100:
				txt = convertTimeToFormattedTime(time)
			else:
				txt = convertTimeToFormattedTime(time, hour_padding=3)
			i.setText(txt)
			
			
def composition_set_title(c, label):
	for i in c.items():
		if isinstance(i, QgsLayoutItemLabel) and i.id() == "title":
			#txt = time_to_string(time)
			i.setText(label)


def setPlotProperties(fig, ax, prop, ax2, layout_type, layout_item):
	if layout_type == 'default':
		fig.set_size_inches(prop.sbFigSizeX.value() / 25.4, prop.sbFigSizeY.value() / 25.4)
	elif layout_type == 'template':
		if layout_item is None:
			return
		r = layout_item.sizeWithUnits()
		fig.set_size_inches(r.width() / 25.4, r.height() / 25.4)
	else:
		return
	fig.suptitle(prop.leTitle.text())
	ax.set_xlabel(prop.leXLabel.text())
	ax.set_ylabel(prop.leYLabel.text())
	if ax2:
		ax2.set_ylabel(prop.leY2Label.text())
		ax2.set_ylim((prop.sbY2Min.value(), prop.sbY2Max.value()))
	if not prop.xUseMatplotLibDefault:
		ax.set_xlim((prop.sbXmin.value(), prop.sbXMax.value()))
	if not prop.yUseMatplotLibDefault:
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
			if label in neededLabels:
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


def createText(text, result, scalar, vector, time, outfile, template, project, number):
	"""
	Update dynamic text to actual text

	:param text: str text to be updated
	:param result: str result name
	:param scalar: str scalar name
	:param vector: str vector name
	:param time: str timestep
	:param outfile: str output file
	:param template: str full path to template folder
	:param project: QgsProject
	:param number: int
	:return: str new text after update
	"""
	
	newText = text
	
	# numbering
	newText = newText.replace('<<X>>', str(number))
	# result name
	newText = newText.replace('<<result_name>>', result)
	# result type
	result_type = scalar if scalar != '-None-' else ''
	result_type = '{0}, {1}'.format(result_type, vector) if vector != '-None-' else result_type
	newText = newText.replace('<<result_type>>', result_type)
	# time
	newText = newText.replace('<<result_time>>', time)
	# date
	date = '{0:%d}/{0:%m}/{0:%Y}'.format(datetime.now())
	newText = newText.replace('<<date>>', date)
	# workspace location
	if template:
		name = os.path.splitext(os.path.basename(outfile))[0] + '.qpt'
		loc = os.path.join(template, name)
	else:
		loc = project.absoluteFilePath()
	newText = newText.replace('<<workspace>>', loc)
	
	return newText


def transformMapCoordToLayout(layout, extent, point, margin):
	# if extent.contains(point):
	# layoutWidth = layout.layoutBounds().width()
	# layoutHeight = layout.layoutBounds().height()
	if margin is None:
		margin = (0, 0, 0, 0)
	layoutWidth = layout.width()
	layoutHeight = layout.height()
	extentWidth = extent.width()
	extentHeight = extent.height()
	xRatio = layoutWidth / extentWidth
	yRatio = layoutHeight / extentHeight
	
	upperLeftExtentX = extent.xMinimum()
	upperLeftExtentY = extent.yMaximum()
	
	distanceX = point.x() - upperLeftExtentX
	distanceY = upperLeftExtentY - point.y()
	
	# layout_map = layout.referenceMap()
	# pos = layout_map.pagePositionWithUnits()
	# xpos = pos.x()
	# ypos = pos.y()
	
	layoutX = distanceX * xRatio
	layoutY = distanceY * yRatio
	
	return QPointF(layoutX + margin[0], layoutY + margin[2])
	
			
def composition_set_plots(dialog, cfg, time, layout, dir, layout_type, showCurrentTime, retainFlow):
	layoutcfg = cfg['layout']
	l = cfg['layer']
	margin = cfg['page margin'] if 'page margin' in cfg else None
	
	# update tuplot with new time and if time series, show current time - but don't draw
	rendered = cfg['rendered'] if 'rendered' in cfg else True
	dialog.tuView.tuPlot.updateCurrentPlot(0, retain_flow=retainFlow, draw=False, time=time,
	                                       show_current_time=showCurrentTime, mesh_rendered=rendered)
	dialog.tuView.tuPlot.updateCurrentPlot(1, draw=False, time=time, mesh_rendered=rendered)
	
	# split out lines into specified plots
	for plot in sorted(layoutcfg['plots']):
		ptype = layoutcfg['plots'][plot]['type']
		position = layoutcfg['plots'][plot]['position']
		labels = layoutcfg['plots'][plot]['labels']
		properties = layoutcfg['plots'][plot]['properties']
		
		if layout_type == 'default':
			cPlot = QgsLayoutItemPicture(layout)
			cPlot.setId('plot_{0}'.format(plot))
			layout.addItem(cPlot)
			cPlot.attemptResize(QgsLayoutSize(properties.sbFigSizeX.value(), properties.sbFigSizeY.value()))
		elif layout_type == 'template':
			cPlot = findLayoutItem(layout, 'plot_{0}'.format(plot))
		else:
			return
		
		fig, ax = plt.subplots()
		ax2 = None
		lines, labs, axis = dialog.plotItems(ptype, include_duplicates=True)
		y2 = isSecondaryNeeded(labels, labs, axis)
		if y2:
			ax2 = ax.twinx()
		setPlotProperties(fig, ax, properties, ax2, layout_type, cPlot)
		for i, line in enumerate(lines):
			if labs[i] in labels or labs[i] == 'Current Time':
				if y2 and axis[i] == 'axis 2':
					addLineToPlot(fig, ax2, line, labs[i])
				else:
					addLineToPlot(fig, ax, line, labs[i])
		if properties.cbLegend.isChecked():
			legend(ax, properties.cboLegendPos.currentIndex())
		fig.tight_layout()
		fname = os.path.join('{0}'.format(dir), '{0}-{1}-{2}.svg'.format(l.name(), plot, time))
		fig.savefig(fname)
		layoutcfg['plots'][plot]['source'] = fname
		
		if cPlot:
			cPlot.setPicturePath(fname)
			if layout_type == 'default':
				set_item_pos(cPlot, position, layout, margin)


def prepare_composition_from_template(layout, cfg, time, dialog, dir, showCurrentTime, retainFlow, layers=None):
	layoutcfg = cfg['layout']
	template_path = layoutcfg['file']
	document = QDomDocument()
	with open(template_path) as f:
		document.setContent(f.read())
	context = QgsReadWriteContext()
	context.setPathResolver(QgsProject.instance().pathResolver())
	context.setProjectTranslator(QgsProject.instance())
	layout.readLayoutXml(document.documentElement(), document, context)
	if layers is not None:
		layout_map = layout.referenceMap()
		layout_map.setLayers(layers)
	composition_set_time(layout, time)
	composition_set_plots(dialog, cfg, time, layout, dir, 'template', showCurrentTime, retainFlow)
	composition_set_dynamic_text(dialog, cfg, layout)
	
	
def composition_set_dynamic_text(dialog, cfg, layout):
	layoutcfg = cfg['layout']
	layer = cfg['layer']
	if 'title' in layoutcfg:
		if 'map number' in cfg:
			i = cfg['map number']
			path = cfg['imgfile']
			text = dialog.labelInput.toPlainText()
			result = layer.name()
			scalar = dialog.tableMaps.cellWidget(i, 1).currentText()
			vector = dialog.tableMaps.cellWidget(i, 2).currentText()
			time = dialog.tableMaps.cellWidget(i, 3).currentText()
			template = ''
			if dialog.cbSaveTemplates.isChecked():
				template = dialog.leTemplateOut.text()
			label = createText(text, result, scalar, vector, time, path, template, dialog.project, i + 1)
			composition_set_title(layout, label)

	
def _page_size(layout, margin):
	""" returns QgsLayoutSize """
	main_page = layout.pageCollection().page(0)
	if margin is None:
		margin = (0, 0, 0, 0)
	width = main_page.pageSize().width() - margin[0] - margin[1]
	height = main_page.pageSize().height() - margin[2] - margin[3]
	return QgsLayoutSize(width, height)


def animation(cfg, iface, progress_fn=None, dialog=None, preview=False):
	margin = cfg['page margin'] if 'page margin' in cfg else (0, 0, 0, 0)
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
		asd = cfg['scalar index']
		rs.setActiveScalarDataset(QgsMeshDatasetIndex(asd, i))
		avd = cfg['vector index']
		rs.setActiveVectorDataset(QgsMeshDatasetIndex(avd, i))
		l.setRendererSettings(rs)

		# Prepare layout
		layout = QgsPrintLayout(QgsProject.instance())
		layout.initializeDefaults()
		layout.setName('tuflow')

		layoutcfg = cfg['layout']
		if layoutcfg['type'] == 'file':
			prepare_composition_from_template(layout, cfg, time, dialog, os.path.dirname(imgfile), True, True)
			# when using composition from template, match video's aspect ratio to paper size
			# by updating video's width (keeping the height)
			aspect = _page_size(layout, margin).width() / _page_size(layout, margin).height()
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
		
		if preview:
			return layout

	if progress_fn:
		progress_fn(count, count)

	# restore original settings
	l.setRendererSettings(original_rs)


def set_composer_item_label(item, itemcfg):
	item.setBackgroundEnabled(itemcfg['background'])
	item.setBackgroundColor(itemcfg['background color'])
	item.setFont(itemcfg['font'])
	item.setFontColor(itemcfg['font colour'])
	item.setFrameEnabled(itemcfg['frame'])
	item.setFrameStrokeColor(itemcfg['frame color'])


class CFItemPosition:
	TOP_LEFT = 0
	TOP_RIGHT = 1
	BOTTOM_LEFT = 2
	BOTTOM_RIGHT = 3
	TOP_CENTER = 4
	BOTTOM_CENTER = 5

def set_item_pos(item, posindex, layout, margin, buffer=0):
	if margin is None:
		margin = (0, 0, 0, 0)
	page_size = _page_size(layout, margin)
	r = item.sizeWithUnits()
	assert (r.units() == QgsUnitTypes.LayoutMillimeters)
	assert (page_size.units() == QgsUnitTypes.LayoutMillimeters)

	if posindex == CFItemPosition.TOP_CENTER: # top-center
		item.attemptMove(QgsLayoutPoint((page_size.width() - r.width()) / 2 + margin[0], margin[2] + buffer, QgsUnitTypes.LayoutMillimeters))
	elif posindex == CFItemPosition.BOTTOM_CENTER:
		item.attemptMove(QgsLayoutPoint((page_size.width() - r.width()) / 2 + margin[0], page_size.height() - r.height() + margin[3] - buffer, QgsUnitTypes.LayoutMillimeters))
	elif posindex == CFItemPosition.TOP_LEFT:  # top-left
		item.attemptMove(QgsLayoutPoint(margin[0] + buffer, margin[2] + buffer))
	elif posindex == CFItemPosition.TOP_RIGHT:  # top-right
		item.attemptMove(QgsLayoutPoint(page_size.width() - r.width() + margin[0] - buffer, margin[2] + buffer, QgsUnitTypes.LayoutMillimeters))
	elif posindex == CFItemPosition.BOTTOM_LEFT:  # bottom-left
		item.attemptMove(QgsLayoutPoint(margin[0] + buffer, page_size.height() - r.height() + margin[2] - buffer, QgsUnitTypes.LayoutMillimeters))
	else: # bottom-right
		item.attemptMove(QgsLayoutPoint(page_size.width() - r.width() + margin[0] - buffer, page_size.height() - r.height() + margin[2] - buffer, QgsUnitTypes.LayoutMillimeters))
		
def fix_legend_box_size(cfg, legend):
	# adjustBoxSize() does not work without
	# call of the paint() function
	w, h = cfg['img_size']
	dpi = cfg['dpi']
	image = QImage(w, h, QImage.Format_ARGB32)
	image.setDevicePixelRatio(dpi)
	p = QPainter(image)
	s = QStyleOptionGraphicsItem()
	legend.paint(p, s, None)
	p.end()
	# Now we can adjust box size
	legend.adjustBoxSize()
	
	
def fix_label_box_size(layout, cTitle, layoutcfg):
	# adjustSizeToText does not work with
	# return characters as it treats the
	# text as one long string
	text = cTitle.text()
	s = text.split('\n')
	w, h = 0, 0
	for i in s:
		if i:
			label = QgsLayoutItemLabel(layout)
			label.setText(i)
			set_composer_item_label(label, layoutcfg['title'])
			size = label.sizeForText()
			w = max(w, size.width())
			h += size.height()
	cTitle.attemptResize(QgsLayoutSize(w, h))
		
	
def legend(ax, position):
	# get legend labels and artists
	uniqueNames, uniqueNames2, uniqueLines, uniqueLines2 = [], [], [], []
	line, lab = ax.get_legend_handles_labels()
	# remove duplicates i.e. culvert and pipes only need to appear in legend once
	uniqueNames = []
	uniqueLines = []
	for i, l in enumerate(lab):
		if l not in uniqueNames:
			uniqueNames.append(l)
			uniqueLines.append(line[i])
		if len(ax.get_shared_x_axes().get_siblings(ax)) < 2:
			ax2 = ax.get_shared_x_axes().get_siblings(ax)[0]
		line2, lab2 = ax2.get_legend_handles_labels()
		# remove duplicates i.e. culvert and pipes only need to appear in legend once
		uniqueNames2 = []
		uniqueLines2 = []
		for i, l in enumerate(lab2):
			if l not in uniqueNames:
				uniqueNames2.append(l)
				uniqueLines2.append(line2[i])
	lines = uniqueLines + uniqueLines2
	lab = uniqueNames + uniqueNames2
	ax.legend(lines, lab, loc=position)


def createDefaultSymbol(gtype):
	if gtype == 'rubberband profile':
		color = '255, 0, 0'
		symbol = QgsSymbol.defaultSymbol(1)
	elif gtype == 'rubberband flow':
		color = '0, 0, 255'
		symbol = QgsSymbol.defaultSymbol(1)
	elif gtype == 'marker':
		color = '255, 0, 0'
		symbol = QgsSymbol.defaultSymbol(1)
	layer_style = {}
	layer_style['color'] = color
	layer_style['outline'] = '#000000'
	symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
	symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
	symbol_layer.setWidth(1)
	symbol_layer2 = QgsMarkerLineSymbolLayer.create({'placement': 'vertex'})
	layer_style['color_border'] = color
	markerSymbol = QgsSimpleMarkerSymbolLayer.create(layer_style)
	if gtype == 'rubberband profile' or gtype == 'rubberband flow':
		markerSymbol.setShape(QgsSimpleMarkerSymbolLayerBase.Square)
		markerSymbol.setFillColor(QColor(0, 0, 0, 0))
	else:
		markerSymbol.setShape(QgsSimpleMarkerSymbolLayerBase.Circle)
	markerSymbol.setSize(3)
	marker = QgsMarkerSymbol()
	marker.changeSymbolLayer(0, markerSymbol)
	symbol_layer2.setSubSymbol(marker)
	if symbol_layer is not None:
		symbol.changeSymbolLayer(0, symbol_layer)
		if symbol_layer2 is not None:
			symbol.appendSymbolLayer(symbol_layer2)
			
	return symbol
	

def prepare_composition(layout, time, cfg, layoutcfg, extent, layers, crs, dir, dialog, show_current_time=True,
                        retainFlow=True):
	margin = cfg['page margin'] if 'page margin' in cfg else None
	layout_map = QgsLayoutItemMap(layout)
	layout_map.attemptResize(_page_size(layout, margin))
	set_item_pos(layout_map, CFItemPosition.TOP_LEFT, layout, margin)
	layout_map.setLayers(layers)
	if crs is not None:
		layout_map.setCrs(crs)
	layout_map.setExtent(extent)
	debug = layout_map.extent()
	layout_map.refresh()
	layout.setReferenceMap(layout_map)
	layout.addLayoutItem(layout_map)
	layout_map.attemptResize(_page_size(layout, margin))
	if 'frame' in cfg:
		layout_map.setFrameEnabled(cfg['frame'])
		layout_map.setFrameStrokeColor(cfg['frame color'])
		layout_map.setFrameStrokeWidth(QgsLayoutMeasurement(cfg['frame thickness']))
	#actualExtent = calculateLayoutExtent(layout, layout_map.extent())
	actualExtent = debug

	if 'title' in layoutcfg:
		cTitle = QgsLayoutItemLabel(layout)
		cTitle.setId('title')
		layout.addLayoutItem(cTitle)

		set_composer_item_label(cTitle, layoutcfg['title'])
		cTitle.setText(layoutcfg['title']['label'])
		cTitle.setHAlign(Qt.AlignLeft)
		cTitle.setVAlign(Qt.AlignTop)
		fix_label_box_size(layout, cTitle, layoutcfg)
		set_item_pos(cTitle, layoutcfg['title']['position'], layout, margin)

	if 'time' in layoutcfg:
		cTime = QgsLayoutItemLabel(layout)
		cTime.setId('time')
		layout.addLayoutItem(cTime)

		set_composer_item_label(cTime, layoutcfg['time'])
		composition_set_time(layout, time)
		cTime.adjustSizeToText()
		set_item_pos(cTime, layoutcfg['time']['position'], layout, margin)

	if 'legend' in layoutcfg:
		cLegend = QgsLayoutItemLegend(layout)
		cLegend.setId('legend')
		cLegend.setLinkedMap(layout_map)
		cLegend.setLegendFilterByMapEnabled(True)
		layout.addLayoutItem(cLegend)

		itemcfg = layoutcfg['legend']
		cLegend.setBackgroundEnabled(itemcfg['background'])
		cLegend.setBackgroundColor(itemcfg['background color'])
		cLegend.setFrameEnabled(itemcfg['frame'])
		cLegend.setFrameStrokeColor(itemcfg['frame color'])
		cLegend.setTitle(itemcfg['label'])
		for s in [QgsLegendStyle.Title,
				  QgsLegendStyle.Group,
				  QgsLegendStyle.Subgroup,
				  QgsLegendStyle.SymbolLabel]:
			cLegend.setStyleFont(s, itemcfg['font'])
		cLegend.setFontColor(itemcfg['font colour'])

		fix_legend_box_size(cfg, cLegend)
		#cLegend.adjustBoxSize()
		set_item_pos(cLegend, itemcfg['position'], layout, margin)
		
	if 'plots' in layoutcfg:
		composition_set_plots(dialog, cfg, time, layout, dir, 'default', show_current_time, retainFlow)
			
	if 'graphics' in layoutcfg:
		for graphic in layoutcfg['graphics']:
			label = layoutcfg['graphics'][graphic]['user label']
			position = layoutcfg['graphics'][graphic]['position']
			gtype = layoutcfg['graphics'][graphic]['type']
			
			# graphic
			if gtype == 'rubberband profile' or gtype == 'rubberband flow':
				geom = graphic.asGeometry().asPolyline()
				layoutGeom = [transformMapCoordToLayout(layout_map.rectWithFrame(), layout_map.extent(), x, margin) for x in geom]
			else:
				layoutGeom = [transformMapCoordToLayout(layout_map.rectWithFrame(), layout_map.extent(), QgsPointXY(graphic), margin)] * 2
			qpolygonf = QPolygonF(layoutGeom)
			polylineGraphic = QgsLayoutItemPolyline(qpolygonf, layout)
			symbol = createDefaultSymbol(gtype)
			polylineGraphic.setSymbol(symbol)
			layout.addItem(polylineGraphic)
			
			# label
			if label:
				if position.lower() == 'right':
					layoutPosX = max([x.x() for x in layoutGeom])
					ind = [x.x() for x in layoutGeom].index(layoutPosX)
					layoutPosY = layoutGeom[ind].y()
					offset = 3
					pos = (layoutPosX + offset, layoutPosY)
					anchor = QgsLayoutItem.MiddleLeft
				elif position.lower() == 'left':
					layoutPosX = min([x.x() for x in layoutGeom])
					ind = [x.x() for x in layoutGeom].index(layoutPosX)
					layoutPosY = layoutGeom[ind].y()
					offset = 3
					pos = (layoutPosX - offset, layoutPosY)
					anchor = QgsLayoutItem.MiddleRight
				elif position.lower() == 'above':  # only available for points at the moment
					layoutPosX = layoutGeom[0].x()
					layoutPosY = layoutGeom[0].y()
					offset = 3
					pos = (layoutPosX, layoutPosY - offset)
					anchor = QgsLayoutItem.LowerMiddle
				elif position.lower() == 'below':  # only available for points at the moment
					layoutPosX = layoutGeom[0].x()
					layoutPosY = layoutGeom[0].y()
					offset = 3
					pos = (layoutPosX, layoutPosY + offset)
					anchor = QgsLayoutItem.UpperMiddle
				elif position.lower() == 'above-left':  # only available for points at the moment
					layoutPosX = layoutGeom[0].x()
					layoutPosY = layoutGeom[0].y()
					offset = 1.5
					pos = (layoutPosX - offset, layoutPosY - offset)
					anchor = QgsLayoutItem.LowerRight
				elif position.lower() == 'above-right':  # only available for points at the moment
					layoutPosX = layoutGeom[0].x()
					layoutPosY = layoutGeom[0].y()
					offset = 1.5
					pos = (layoutPosX + offset, layoutPosY - offset)
					anchor = QgsLayoutItem.LowerLeft
				elif position.lower() == 'below-left':  # only available for points at the moment
					layoutPosX = layoutGeom[0].x()
					layoutPosY = layoutGeom[0].y()
					offset = 1.5
					pos = (layoutPosX - offset, layoutPosY + offset)
					anchor = QgsLayoutItem.UpperRight
				elif position.lower() == 'below-right':  # only available for points at the moment
					layoutPosX = layoutGeom[0].x()
					layoutPosY = layoutGeom[0].y()
					offset = 1.5
					pos = (layoutPosX + offset, layoutPosY + offset)
					anchor = QgsLayoutItem.UpperLeft
				else:
					return
				
				graphicLabel = QgsLayoutItemLabel(layout)
				graphicLabel.setId(label)
				layout.addLayoutItem(graphicLabel)
				
				graphicLabel.setText(label)
				graphicLabel.setHAlign(Qt.AlignCenter)
				graphicLabel.setVAlign(Qt.AlignCenter)
				set_composer_item_label(graphicLabel, layoutcfg['graphics'][graphic])
				graphicLabel.adjustSizeToText()
				graphicLabel.setReferencePoint(anchor)
				graphicLabel.attemptMove(QgsLayoutPoint(pos[0], pos[1]))
				
	if 'images' in layoutcfg:
		for i, image in enumerate(layoutcfg['images']):
			source = layoutcfg['images'][image]['source']
			position = layoutcfg['images'][image]['position']
			properties = layoutcfg['images'][image]['properties']
			
			cImage = QgsLayoutItemPicture(layout)
			if properties.rbUseOriginalSize.isChecked():
				cImage.setResizeMode(QgsLayoutItemPicture.FrameToImageSize)
			else:
				if properties.cbKeepAspectRatio.isChecked():
					cImage.setResizeMode(QgsLayoutItemPicture.ZoomResizeFrame)
				else:
					cImage.setResizeMode(QgsLayoutItemPicture.Stretch)
			cImage.setId('image_{0}'.format(i))
			layout.addItem(cImage)
			cImage.attemptResize(QgsLayoutSize(properties.sbSizeX.value(), properties.sbSizeY.value()))
			cImage.setPicturePath(source)
			set_item_pos(cImage, position, layout, margin)
			
	if 'scale bar' in layoutcfg:
		itemcfg = layoutcfg['scale bar']
		cScaleBar = QgsLayoutItemScaleBar(layout)
		cScaleBar.setLinkedMap(layout_map)
		cScaleBar.applyDefaultSize()
		cScaleBar.setStyle('Double Box')
		cScaleBar.setNumberOfSegments(3)
		cScaleBar.setNumberOfSegmentsLeft(0)
		cScaleBar.setFont(itemcfg['font'])
		cScaleBar.setFontColor(itemcfg['font color'])
		cScaleBar.setBackgroundEnabled(itemcfg['background'])
		cScaleBar.setBackgroundColor(itemcfg['background color'])
		cScaleBar.setFrameEnabled(itemcfg['frame'])
		cScaleBar.setFrameStrokeColor(itemcfg['frame color'])
		cScaleBar.setId('scale bar')
		layout.addItem(cScaleBar)
		set_item_pos(cScaleBar, itemcfg['position'], layout, margin)
		
	if 'north arrow' in layoutcfg:
		itemcfg = layoutcfg['north arrow']
		path = QgsApplication.defaultThemesFolder()
		path = path[:-19]
		path = os.path.join(path, 'svg', 'arrows', 'NorthArrow_02.svg')
		cNorthArrow = QgsLayoutItemPicture(layout)
		cNorthArrow.setId('north arrow')
		cNorthArrow.setSvgFillColor(QColor(Qt.black))
		cNorthArrow.setLinkedMap(layout_map)
		cNorthArrow.setBackgroundEnabled(itemcfg['background'])
		cNorthArrow.setBackgroundColor(itemcfg['background color'])
		cNorthArrow.setFrameEnabled(itemcfg['frame'])
		cNorthArrow.setFrameStrokeColor(itemcfg['frame color'])
		layout.addItem(cNorthArrow)
		cNorthArrow.setPicturePath(path)
		cNorthArrow.setResizeMode(QgsLayoutItemPicture.Stretch)
		cNorthArrow.attemptResize(QgsLayoutSize(7.5, 15))
		set_item_pos(cNorthArrow, itemcfg['position'], layout, margin, buffer=2)
		

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
		self.pbDialogsImage = {}
		self.dialog2Plot = {}
		self.rowNo2fntDialog = {}
		self.label2graphic = {}
		
		self.populateGeneralTab()
		self.populateLayoutTab()
		self.populateVideoTab()
		
		self.cboResult.currentIndexChanged.connect(lambda: self.populateGeneralTab(ignore='results'))
		self.btnBrowseOutput.clicked.connect(lambda: self.browse('save', 'TUFLOW/animation_outfolder', "AVI files (*.avi)", self.editOutput))
		self.btnBrowseTemplate.clicked.connect(lambda: self.browse('load', "TUFLOW/animation_template", "QGIS Print Layout (*.qpt)", self.editTemplate))
		self.btnBrowseFfmpegPath.clicked.connect(lambda: self.browse('ffmpeg', 'TUFLOW/animation_ffmpeg', "FFmpeg (ffmpeg ffmpeg.exe avconv avconv.exe)", self.editFfmpegPath))
		self.btnAddPlot.clicked.connect(self.addPlot)
		self.btnRemovePlot.clicked.connect(self.removePlot)
		self.btnPlotUp.clicked.connect(lambda event: self.movePlot(event, 'up'))
		self.btnPlotDown.clicked.connect(lambda event: self.movePlot(event, 'down'))
		self.btnAddImage.clicked.connect(self.addImage)
		self.btnRemoveImage.clicked.connect(self.removeImage)
		self.btnImageUp.clicked.connect(lambda event: self.moveImage(event, 'up'))
		self.btnImageDown.clicked.connect(lambda event: self.moveImage(event, 'down'))
		self.pbPreview.clicked.connect(lambda: self.check(preview=True))
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
		# apply project settings
		if self.project.readEntry("TUFLOW", 'start_time')[0]:
			for i in range(self.cboStart.count()):
				if self.cboStart.itemText(i) == self.project.readEntry("TUFLOW", 'start_time')[0]:
					self.cboStart.setCurrentIndex(i)
					break
		if self.project.readEntry("TUFLOW", 'end_time')[0]:
			for i in range(self.cboEnd.count()):
				if self.cboEnd.itemText(i) == self.project.readEntry("TUFLOW", 'end_time')[0]:
					self.cboEnd.setCurrentIndex(i)
					break
		if self.project.readEntry("TUFLOW", 'result_name')[0]:
			for i in range(self.cboResult.count()):
				if self.cboResult.itemText(i) == self.project.readEntry("TUFLOW", 'result_name')[0]:
					self.cboResult.setCurrentIndex(i)
					break
		if self.project.readEntry("TUFLOW", 'result_scalar')[0]:
			for i in range(self.cboScalar.count()):
				if self.cboScalar.itemText(i) == self.project.readEntry("TUFLOW", 'result_scalar')[0]:
					self.cboScalar.setCurrentIndex(i)
					break
		if self.project.readEntry("TUFLOW", 'result_vector')[0]:
			for i in range(self.cboVector.count()):
				if self.cboVector.itemText(i) == self.project.readEntry("TUFLOW", 'result_vector')[0]:
					self.cboVector.setCurrentIndex(i)
					break
		if self.project.readEntry("TUFLOW", 'video_width')[0]:
			self.spinWidth.setValue(self.project.readNumEntry("TUFLOW", 'video_width')[0])
		if self.project.readEntry("TUFLOW", 'video_height')[0]:
			self.spinHeight.setValue(self.project.readNumEntry("TUFLOW", 'video_height')[0])
		if self.project.readEntry("TUFLOW", 'video_fps')[0]:
			self.spinSpeed.setValue(self.project.readNumEntry("TUFLOW", 'video_fps')[0])
		if self.project.readEntry("TUFLOW", 'output_file')[0]:
			self.editOutput.setText(self.project.readEntry("TUFLOW", 'output_file')[0])
		
	def populateLayoutTab(self):
		"""
		Populates widgets in Layout Tab
		
		:return: void
		"""
		
		addIcon = QgsApplication.getThemeIcon('/symbologyAdd.svg')
		removeIcon = QgsApplication.getThemeIcon('/symbologyRemove.svg')
		upIcon = QgsApplication.getThemeIcon('/mActionArrowUp.svg')
		downIcon = QgsApplication.getThemeIcon('/mActionArrowDown.svg')
		folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
		
		self.btnAddPlot.setIcon(addIcon)
		self.btnRemovePlot.setIcon(removeIcon)
		self.btnPlotUp.setIcon(upIcon)
		self.btnPlotDown.setIcon(downIcon)
		
		self.btnAddImage.setIcon(addIcon)
		self.btnRemoveImage.setIcon(removeIcon)
		self.btnImageUp.setIcon(upIcon)
		self.btnImageDown.setIcon(downIcon)
		
		self.btnBrowseTemplate.setIcon(folderIcon)
		
		self.tablePlots.horizontalHeader().setVisible(True)
		self.tableGraphics.horizontalHeader().setVisible(True)
		self.populateGraphics()
		
		# load project settings
		# Title
		self.groupTitle.setChecked(self.project.readBoolEntry("TUFLOW", 'title_cb')[0])
		self.labelTitle.setText(self.project.readEntry("TUFLOW", 'title_label')[0])
		font = QFont()
		font.setFamily(self.project.readEntry("TUFLOW", 'title_font_name', 'MS Shell Dlg 2')[0])
		font.setPointSize(self.project.readNumEntry("TUFLOW", 'title_font_size', 9)[0])
		font.setBold(self.project.readBoolEntry("TUFLOW", 'title_font_bold')[0])
		font.setStyle(self.project.readNumEntry("TUFLOW", 'title_font_italic')[0])
		font.setStrikeOut(self.project.readBoolEntry("TUFLOW", 'title_font_strikeout')[0])
		font.setUnderline(self.project.readBoolEntry("TUFLOW", 'title_font_underline')[0])
		self.fbtnTitle.setCurrentFont(font)
		color = QColor()
		color.setNamedColor(self.project.readEntry("TUFLOW", 'title_font_color', '#000000')[0])
		self.colorTitleText.setColor(color)
		self.cbTitleBackground.setChecked(self.project.readBoolEntry("TUFLOW", 'title_background_cb')[0])
		color = QColor()
		color.setNamedColor(self.project.readEntry("TUFLOW", 'title_background_color', '#ffffff')[0])
		self.colorTitleBackground.setColor(color)
		self.cboPosTitle.setCurrentIndex(self.project.readNumEntry("TUFLOW", 'title_background_position', 0)[0])
		
		# Time
		self.groupTime.setChecked(self.project.readBoolEntry("TUFLOW", 'time_cb')[0])
		self.labelTime.setText(self.project.readEntry("TUFLOW", 'time_label')[0])
		font = QFont()
		font.setFamily(self.project.readEntry("TUFLOW", 'time_font_name', 'MS Shell Dlg 2')[0])
		font.setPointSize(self.project.readNumEntry("TUFLOW", 'time_font_size', 9)[0])
		font.setBold(self.project.readBoolEntry("TUFLOW", 'time_font_bold')[0])
		font.setStyle(self.project.readNumEntry("TUFLOW", 'time_font_italic')[0])
		font.setStrikeOut(self.project.readBoolEntry("TUFLOW", 'time_font_strikeout')[0])
		font.setUnderline(self.project.readBoolEntry("TUFLOW", 'time_font_underline')[0])
		self.fbtnTime.setCurrentFont(font)
		color = QColor()
		color.setNamedColor(self.project.readEntry("TUFLOW", 'time_font_color', '#000000')[0])
		self.colorTimeText.setColor(color)
		self.cbTimeBackground.setChecked(self.project.readBoolEntry("TUFLOW", 'time_background_cb')[0])
		color = QColor()
		color.setNamedColor(self.project.readEntry("TUFLOW", 'time_background_color', '#ffffff')[0])
		self.colorTimeBackground.setColor(color)
		self.cboPosTime.setCurrentIndex(self.project.readNumEntry("TUFLOW", 'time_background_position', 0)[0])
		
		# Legend
		self.groupLegend.setChecked(self.project.readBoolEntry("TUFLOW", 'legend_cb')[0])
		self.labelLegend.setText(self.project.readEntry("TUFLOW", 'legend_label')[0])
		font = QFont()
		font.setFamily(self.project.readEntry("TUFLOW", 'legend_font_name', 'MS Shell Dlg 2')[0])
		font.setPointSize(self.project.readNumEntry("TUFLOW", 'legend_font_size', 9)[0])
		font.setBold(self.project.readBoolEntry("TUFLOW", 'legend_font_bold')[0])
		font.setStyle(self.project.readNumEntry("TUFLOW", 'legend_font_italic')[0])
		font.setStrikeOut(self.project.readBoolEntry("TUFLOW", 'legend_font_strikeout')[0])
		font.setUnderline(self.project.readBoolEntry("TUFLOW", 'legend_font_underline')[0])
		self.fbtnLegend.setCurrentFont(font)
		color = QColor()
		color.setNamedColor(self.project.readEntry("TUFLOW", 'legend_font_color', '#000000')[0])
		self.colorLegendText.setColor(color)
		self.cbLegendBackground.setChecked(self.project.readBoolEntry("TUFLOW", 'legend_background_cb')[0])
		color = QColor()
		color.setNamedColor(self.project.readEntry("TUFLOW", 'legend_background_color', '#ffffff')[0])
		self.colorLegendBackground.setColor(color)
		self.cboPosLegend.setCurrentIndex(self.project.readNumEntry("TUFLOW", 'legend_background_position', 0)[0])
		
		# layout type
		layout_type = self.project.readEntry("TUFLOW", 'layout_type', 'default')[0]
		if layout_type == 'default':
			self.radLayoutDefault.setChecked(True)
		else:
			self.radLayoutCustom.setChecked(True)
		self.editTemplate.setText(self.project.readEntry("TUFLOW", 'custom_template_path')[0])
		
		# plots
		self.groupPlot.setChecked(self.project.readBoolEntry("TUFLOW", 'plots_cb')[0])
		nPlots = self.project.readNumEntry("TUFLOW", 'number_of_plots')[0]
		for i in range(nPlots):
			self.addPlot()
			self.tablePlots.cellWidget(i, 0).setCurrentIndex(self.project.readNumEntry("TUFLOW", 'plot_{0}_type'.format(i))[0])
			items = self.project.readListEntry("TUFLOW", 'plot_{0}_items'.format(i))[0]
			for j in range(self.tablePlots.cellWidget(i, 1).count()):
				if self.tablePlots.cellWidget(i, 1).itemText(j) in items:
					self.tablePlots.cellWidget(i, 1).setItemCheckState(j, Qt.Checked)
			self.tablePlots.cellWidget(i, 2).setCurrentIndex(self.project.readNumEntry("TUFLOW", 'plot_{0}_position'.format(i))[0])
			p = self.pbDialogs[self.tablePlots.cellWidget(i, 3)]
			p.leTitle.setText(self.project.readEntry("TUFLOW", 'plot_{0}_title'.format(i))[0])
			p.leXLabel.setText(self.project.readEntry("TUFLOW", 'plot_{0}_xlabel'.format(i))[0])
			p.leYLabel.setText(self.project.readEntry("TUFLOW", 'plot_{0}_ylabel'.format(i))[0])
			p.leY2Label.setText(self.project.readEntry("TUFLOW", 'plot_{0}_y2label'.format(i))[0])
			p.sbXmin.setValue(self.project.readDoubleEntry("TUFLOW", 'plot_{0}_xmin'.format(i))[0])
			p.sbXMax.setValue(self.project.readDoubleEntry("TUFLOW", 'plot_{0}_xmax'.format(i))[0])
			p.sbYMin.setValue(self.project.readDoubleEntry("TUFLOW", 'plot_{0}_ymin'.format(i))[0])
			p.sbYMax.setValue(self.project.readDoubleEntry("TUFLOW", 'plot_{0}_ymax'.format(i))[0])
			p.sbY2Min.setValue(self.project.readDoubleEntry("TUFLOW", 'plot_{0}_y2min'.format(i))[0])
			p.sbY2Max.setValue(self.project.readDoubleEntry("TUFLOW", 'plot_{0}_y2max'.format(i))[0])
			p.cbLegend.setChecked(self.project.readBoolEntry("TUFLOW", 'plot_{0}_legend_cb'.format(i))[0])
			p.cboLegendPos.setCurrentIndex(self.project.readNumEntry("TUFLOW", 'plot_{0}_legend_pos'.format(i))[0])
			p.cbGridY.setChecked(self.project.readBoolEntry("TUFLOW", 'plot_{0}_ygrid'.format(i))[0])
			p.cbGridX.setChecked(self.project.readBoolEntry("TUFLOW", 'plot_{0}_xgrid'.format(i))[0])
			p.sbFigSizeX.setValue(self.project.readDoubleEntry("TUFLOW", 'plot_{0}_xsize'.format(i))[0])
			p.sbFigSizeY.setValue(self.project.readDoubleEntry("TUFLOW", 'plot_{0}_ysize'.format(i))[0])
			
		# graphics
		for i in range(self.tableGraphics.rowCount()):
			self.tableGraphics.item(i, 0).setCheckState(self.project.readNumEntry("TUFLOW", "graphic_{0}_cb".format(i), 2)[0])
			userLabel = self.project.readEntry("TUFLOW", "graphic_{0}_user_label".format(i))[0]
			if userLabel:
				self.tableGraphics.cellWidget(i, 1).setText(userLabel)
			self.tableGraphics.cellWidget(i, 2).setCurrentIndex(self.project.readNumEntry("TUFLOW", "graphic_{0}_position".format(i))[0])
			p = self.rowNo2fntDialog[i]
			font = QFont()
			font.setFamily(self.project.readEntry("TUFLOW", 'graphic_{0}_font_name'.format(i), 'MS Shell Dlg 2')[0])
			font.setPointSize(self.project.readNumEntry("TUFLOW", 'graphic_{0}_font_size'.format(i), 9)[0])
			font.setBold(self.project.readBoolEntry("TUFLOW", 'graphic_{0}_font_bold'.format(i))[0])
			font.setStyle(self.project.readNumEntry("TUFLOW", 'graphic_{0}_font_italic'.format(i))[0])
			font.setStrikeOut(self.project.readBoolEntry("TUFLOW", 'graphic_{0}_font_strikeout'.format(i))[0])
			font.setUnderline(self.project.readBoolEntry("TUFLOW", 'graphic_{0}_font_underline'.format(i))[0])
			p.fntButton.setCurrentFont(font)
			color = QColor()
			color.setNamedColor(self.project.readEntry("TUFLOW", 'graphic_{0}_font_color'.format(i), '#000000')[0])
			p.fntColor.setColor(color)
			p.cbBackground.setChecked(self.project.readBoolEntry("TUFLOW", 'graphic_{0}_background_cb'.format(i))[0])
			color = QColor()
			color.setNamedColor(self.project.readEntry("TUFLOW", 'graphic_{0}_background_color'.format(i), '#ffffff')[0])
			
		# Images
		self.groupImages.setChecked(self.project.readBoolEntry("TUFLOW", 'images_cb')[0])
		nImages = self.project.readNumEntry("TUFLOW", 'number_of_images')[0]
		for i in range(nImages):
			self.addImage()
			self.tableImages.cellWidget(i, 0).layout().itemAt(1).widget().setText(self.project.readEntry("TUFLOW", 'image_{0}_source'.format(i))[0])
			self.tableImages.cellWidget(i, 1).setCurrentIndex(self.project.readNumEntry("TUFLOW", 'image_{0}_position'.format(i))[0])
			p = self.pbDialogsImage[self.tableImages.cellWidget(i, 2)]
			p.rbUseOriginalSize.setChecked(self.project.readBoolEntry("TUFLOW", 'image_{0}_use_original_size'.format(i), True)[0])
			p.rbResizeImage.setChecked(self.project.readBoolEntry("TUFLOW", 'image_{0}_resize_image'.format(i))[0])
			p.sbSizeX.setValue(self.project.readDoubleEntry("TUFLOW", 'image_{0}_xsize'.format(i))[0])
			p.sbSizeY.setValue(self.project.readDoubleEntry("TUFLOW", 'image_{0}_ysize'.format(i))[0])
			p.cbKeepAspectRatio.setChecked(self.project.readBoolEntry("TUFLOW", 'image_{0}_maintain_aspect_ratio'.format(i))[0])
		
	def populateVideoTab(self):
		"""
		Populates widgets in Video Tab
		
		:return: void
		"""
		
		folderIcon = QgsApplication.getThemeIcon('/mActionFileOpen.svg')
		self.btnBrowseFfmpegPath.setIcon(folderIcon)
		
		settings = QSettings()
		ffmpeg = settings.value("TUFLOW/animation_ffmpeg_switch")
		ffmpegLoc = settings.value("TUFLOW/animation_ffmpeg")
		switch = True if ffmpeg == 'custom' else False
		self.radFfmpegCustom.setChecked(switch)
		self.editFfmpegPath.setText(ffmpegLoc)
		
		quality = self.project.readEntry("TUFLOW", 'video_quality', 'high')
		if quality == 'best':
			self.radQualBest.setChecked(True)
		elif quality == 'high':
			self.radQualHigh.setChecked(True)
		else:
			self.radQualLow.setChecked(True)
		
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
	
	def addPlot(self, event=None, plotTypeTemplate=None, mcboPlotItemTemplate=None, cboPosTemplate=None, pbTemplate=None):
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
				self.addPlot(plotTypeTemplate=col1[i], mcboPlotItemTemplate=col2[i], cboPosTemplate=col3[i], pbTemplate=col4[i])
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
				self.addPlot(plotTypeTemplate=col1[i], mcboPlotItemTemplate=col2[i], cboPosTemplate=col3[i], pbTemplate=col4[i])
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
		#btnBrowse.setMaximumHeight(21)
		
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
			point = QgsPointXY(point)
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
		
	def check(self, event=None, preview=False):
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
		if not self.editOutput.text() and not preview:
			QMessageBox.information(self, 'Input Error', 'Must Specify Output File')
			return
		self.layer = tuflowqgis_find_layer(self.cboResult.currentText())
		if self.layer is None:
			QMessageBox.information(self, 'Input Error',
									'Cannot Find Result File in QGIS: {0}'.format(self.cboResult.currentText()))
		if self.layer.type() != 3:
			QMessageBox.information(self, 'Input Error',
									'Error finding Result Mesh Layer: {0}'.format(self.cboResult.currentText()))
		if not os.path.exists(os.path.dirname(self.editOutput.text())) and not preview:
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
		if not preview:
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
											 "FFmpeg will be downloaded to the TUFLOW plugin's directory.",
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
			
		self.run(preview)
	
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
		
		
	def run(self, preview=False):
		"""
		Run tool to create animation
		
		:return: void
		"""

		if not preview:
			self.buttonBox.setEnabled(False)  # disable button box so users know something is happening
			QApplication.setOverrideCursor(Qt.WaitCursor)
		
		# save plot settings so line colours won't vary over time
		self.tuView.tuPlot.setNewPlotProperties(0)
		self.tuView.tuPlot.setNewPlotProperties(1)
		
		# get results
		asd = self.cboScalar.currentText()
		avd = self.cboVector.currentText()
		if asd == '-None-':
			asd = -1
		if avd == '-None-':
			avd = -1
		#for i in range(self.layer.dataProvider().datasetGroupCount()):
		#	if self.layer.dataProvider().datasetGroupMetadata(i).name() == asd:
		#		asd = i
		#	if self.layer.dataProvider().datasetGroupMetadata(i).name() == avd:
		#		avd = i
		for resultType in self.tuView.tuResults.results[self.layer.name()]:
			if resultType == asd:
				for time in self.tuView.tuResults.results[self.layer.name()][resultType]:
					asd = self.tuView.tuResults.results[self.layer.name()][resultType][time][-1].group()
			if resultType == avd:
				for time in self.tuView.tuResults.results[self.layer.name()][resultType]:
					avd = self.tuView.tuResults.results[self.layer.name()][resultType][time][-1].group()
		
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
			titleProp['frame'] = self.cbTitleFrame.isChecked()
			titleProp['frame color'] = self.colorTitleFrame.color()
			titleProp['position'] = self.cboPosTitle.currentIndex()
		timeProp = {}
		if self.groupTime.isChecked():
			timeProp['label'] = self.labelTime.text()
			timeProp['font'] = self.fbtnTime.currentFont()
			timeProp['font colour'] = self.colorTimeText.color()
			timeProp['background'] = self.cbTimeBackground.isChecked()
			timeProp['background color'] = self.colorTimeBackground.color()
			timeProp['frame'] = self.cbTimeFrame.isChecked()
			timeProp['frame color'] = self.colorTimeFrame.color()
			timeProp['position'] = self.cboPosTime.currentIndex()
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
		self.layout = animation(d, self.iface, prog, self, preview)
		self.tuView.tuPlot.updateCurrentPlot(0, retain_flow=True)
		self.tuView.tuPlot.updateCurrentPlot(1)
		
		if preview:
			self.iface.openLayoutDesigner(layout=self.layout)
		else:
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
				                                                                    "This should not happen. Please email support@tuflow.com "
				                                                                    "with the contents from the log file:\n" + logfile)
			
			self.storeDefaults()
			
			self.accept()
			
	def storeDefaults(self):
		"""
		Store inputs in project.
		
		:return: void
		"""
		
		# General Tab
		self.project.writeEntry("TUFLOW", 'start_time', self.cboStart.currentText())
		self.project.writeEntry("TUFLOW", 'end_time', self.cboEnd.currentText())
		self.project.writeEntry("TUFLOW", 'result_name', self.cboResult.currentText())
		self.project.writeEntry("TUFLOW", 'result_scalar', self.cboScalar.currentText())
		self.project.writeEntry("TUFLOW", 'result_vector', self.cboVector.currentText())
		self.project.writeEntry("TUFLOW", 'video_width', self.spinWidth.value())
		self.project.writeEntry("TUFLOW", 'video_height', self.spinHeight.value())
		self.project.writeEntry("TUFLOW", 'video_fps', self.spinSpeed.value())
		self.project.writeEntry("TUFLOW", 'output_file', self.editOutput.text())
		
		# Layout
		layout_type = 'default' if self.radLayoutDefault.isChecked() else 'custom'
		self.project.writeEntry("TUFLOW", 'layout_type', layout_type)
		self.project.writeEntry("TUFLOW", 'custom_template_path', self.editTemplate.text())
		# title
		self.project.writeEntry("TUFLOW", 'title_cb', self.groupTitle.isChecked())
		self.project.writeEntry("TUFLOW", 'title_label', self.labelTitle.text())
		self.project.writeEntry("TUFLOW", 'title_font_name', self.fbtnTitle.currentFont().family())
		self.project.writeEntry("TUFLOW", 'title_font_size', self.fbtnTitle.currentFont().pointSize())
		self.project.writeEntry("TUFLOW", 'title_font_bold', self.fbtnTitle.currentFont().bold())
		self.project.writeEntry("TUFLOW", 'title_font_italic', self.fbtnTitle.currentFont().style())
		self.project.writeEntry("TUFLOW", 'title_font_strikeout', self.fbtnTitle.currentFont().strikeOut())
		self.project.writeEntry("TUFLOW", 'title_font_underline', self.fbtnTitle.currentFont().underline())
		self.project.writeEntry("TUFLOW", 'title_font_color', self.colorTitleText.color().name())
		self.project.writeEntry("TUFLOW", 'title_background_cb', self.cbTitleBackground.isChecked())
		self.project.writeEntry("TUFLOW", 'title_background_color', self.colorTitleBackground.color().name())
		self.project.writeEntry("TUFLOW", 'title_background_position', self.cboPosTitle.currentIndex())
		
		# time
		self.project.writeEntry("TUFLOW", 'time_cb', self.groupTime.isChecked())
		self.project.writeEntry("TUFLOW", 'time_label', self.labelTime.text())
		self.project.writeEntry("TUFLOW", 'time_font_name', self.fbtnTime.currentFont().family())
		self.project.writeEntry("TUFLOW", 'time_font_size', self.fbtnTime.currentFont().pointSize())
		self.project.writeEntry("TUFLOW", 'time_font_bold', self.fbtnTime.currentFont().bold())
		self.project.writeEntry("TUFLOW", 'time_font_italic', self.fbtnTime.currentFont().style())
		self.project.writeEntry("TUFLOW", 'time_font_strikeout', self.fbtnTime.currentFont().strikeOut())
		self.project.writeEntry("TUFLOW", 'time_font_underline', self.fbtnTime.currentFont().underline())
		self.project.writeEntry("TUFLOW", 'time_font_color', self.colorTimeText.color().name())
		self.project.writeEntry("TUFLOW", 'time_background_cb', self.cbTimeBackground.isChecked())
		self.project.writeEntry("TUFLOW", 'time_background_color', self.colorTimeBackground.color().name())
		self.project.writeEntry("TUFLOW", 'time_background_position', self.cboPosTime.currentIndex())
		
		# legend
		self.project.writeEntry("TUFLOW", 'legend_cb', self.groupLegend.isChecked())
		self.project.writeEntry("TUFLOW", 'legend_label', self.labelLegend.text())
		self.project.writeEntry("TUFLOW", 'legend_font_name', self.fbtnLegend.currentFont().family())
		self.project.writeEntry("TUFLOW", 'legend_font_size', self.fbtnLegend.currentFont().pointSize())
		self.project.writeEntry("TUFLOW", 'legend_font_bold', self.fbtnLegend.currentFont().bold())
		self.project.writeEntry("TUFLOW", 'legend_font_italic', self.fbtnLegend.currentFont().style())
		self.project.writeEntry("TUFLOW", 'legend_font_strikeout', self.fbtnLegend.currentFont().strikeOut())
		self.project.writeEntry("TUFLOW", 'legend_font_underline', self.fbtnLegend.currentFont().underline())
		self.project.writeEntry("TUFLOW", 'legend_font_color', self.colorLegendText.color().name())
		self.project.writeEntry("TUFLOW", 'legend_background_cb', self.cbLegendBackground.isChecked())
		self.project.writeEntry("TUFLOW", 'legend_background_color', self.colorLegendBackground.color().name())
		self.project.writeEntry("TUFLOW", 'legend_background_position', self.cboPosLegend.currentIndex())
		
		# Plots
		self.project.writeEntry("TUFLOW", 'plots_cb', self.groupPlot.isChecked())
		self.project.writeEntry("TUFLOW", 'number_of_plots', self.tablePlots.rowCount())
		for i in range(self.tablePlots.rowCount()):
			self.project.writeEntry("TUFLOW", 'plot_{0}_type'.format(i), self.tablePlots.cellWidget(i, 0).currentIndex())
			self.project.writeEntry("TUFLOW", 'plot_{0}_items'.format(i), self.tablePlots.cellWidget(i, 1).checkedItems())
			self.project.writeEntry("TUFLOW", 'plot_{0}_position'.format(i), self.tablePlots.cellWidget(i, 2).currentIndex())
			p = self.pbDialogs[self.tablePlots.cellWidget(i, 3)]
			self.project.writeEntry("TUFLOW", 'plot_{0}_title'.format(i), p.leTitle.text())
			self.project.writeEntry("TUFLOW", 'plot_{0}_xlabel'.format(i), p.leXLabel.text())
			self.project.writeEntry("TUFLOW", 'plot_{0}_ylabel'.format(i), p.leYLabel.text())
			self.project.writeEntry("TUFLOW", 'plot_{0}_y2label'.format(i), p.leY2Label.text())
			self.project.writeEntry("TUFLOW", 'plot_{0}_xmin'.format(i), p.sbXmin.value())
			self.project.writeEntry("TUFLOW", 'plot_{0}_xmax'.format(i), p.sbXMax.value())
			self.project.writeEntry("TUFLOW", 'plot_{0}_ymin'.format(i), p.sbYMin.value())
			self.project.writeEntry("TUFLOW", 'plot_{0}_ymax'.format(i), p.sbYMax.value())
			self.project.writeEntry("TUFLOW", 'plot_{0}_y2min'.format(i), p.sbY2Min.value())
			self.project.writeEntry("TUFLOW", 'plot_{0}_y2max'.format(i), p.sbY2Max.value())
			self.project.writeEntry("TUFLOW", 'plot_{0}_legend_cb'.format(i), p.cbLegend.isChecked())
			self.project.writeEntry("TUFLOW", 'plot_{0}_legend_pos'.format(i), p.cboLegendPos.currentIndex())
			self.project.writeEntry("TUFLOW", 'plot_{0}_ygrid'.format(i), p.cbGridY.isChecked())
			self.project.writeEntry("TUFLOW", 'plot_{0}_xgrid'.format(i), p.cbGridX.isChecked())
			self.project.writeEntry("TUFLOW", 'plot_{0}_xsize'.format(i), p.sbFigSizeX.value())
			self.project.writeEntry("TUFLOW", 'plot_{0}_ysize'.format(i), p.sbFigSizeY.value())
			
		# Graphics
		for i in range(self.tableGraphics.rowCount()):
			self.project.writeEntry("TUFLOW", "graphic_{0}_cb".format(i), self.tableGraphics.item(i, 0).checkState())
			self.project.writeEntry("TUFLOW", "graphic_{0}_user_label".format(i), self.tableGraphics.cellWidget(i, 1).text())
			self.project.writeEntry("TUFLOW", "graphic_{0}_position".format(i), self.tableGraphics.cellWidget(i, 2).currentIndex())
			p = self.rowNo2fntDialog[i]
			self.project.writeEntry("TUFLOW", 'graphic_{0}_font_name'.format(i), p.fntButton.currentFont().family())
			self.project.writeEntry("TUFLOW", 'graphic_{0}_font_size'.format(i), p.fntButton.currentFont().pointSize())
			self.project.writeEntry("TUFLOW", 'graphic_{0}_font_bold'.format(i), p.fntButton.currentFont().bold())
			self.project.writeEntry("TUFLOW", 'graphic_{0}_font_italic'.format(i), p.fntButton.currentFont().style())
			self.project.writeEntry("TUFLOW", 'graphic_{0}_font_strikeout'.format(i), p.fntButton.currentFont().strikeOut())
			self.project.writeEntry("TUFLOW", 'graphic_{0}_font_underline'.format(i), p.fntButton.currentFont().underline())
			self.project.writeEntry("TUFLOW", 'graphic_{0}_font_color'.format(i), p.fntColor.color().name())
			self.project.writeEntry("TUFLOW", 'graphic_{0}_background_cb'.format(i), p.cbBackground.isChecked())
			self.project.writeEntry("TUFLOW", 'graphic_{0}_background_color'.format(i), p.backgroundColor.color().name())
			
		# Images
		self.project.writeEntry("TUFLOW", 'images_cb', self.groupImages.isChecked())
		self.project.writeEntry("TUFLOW", 'number_of_images', self.tableImages.rowCount())
		for i in range(self.tableImages.rowCount()):
			self.project.writeEntry("TUFLOW", 'image_{0}_source'.format(i), self.tableImages.cellWidget(i, 0).layout().itemAt(1).widget().text())
			self.project.writeEntry("TUFLOW", 'image_{0}_position'.format(i), self.tableImages.cellWidget(i, 1).currentIndex())
			p = self.pbDialogsImage[self.tableImages.cellWidget(i, 2)]
			self.project.writeEntry("TUFLOW", 'image_{0}_use_original_size'.format(i), p.rbUseOriginalSize.isChecked())
			self.project.writeEntry("TUFLOW", 'image_{0}_resize_image'.format(i), p.rbResizeImage.isChecked())
			self.project.writeEntry("TUFLOW", 'image_{0}_xsize'.format(i), p.sbSizeX.value())
			self.project.writeEntry("TUFLOW", 'image_{0}_ysize'.format(i), p.sbSizeY.value())
			self.project.writeEntry("TUFLOW", 'image_{0}_maintain_aspect_ratio'.format(i), p.cbKeepAspectRatio.isChecked())
		
		# Video Tab
		if self.radQualBest.isChecked():
			quality = 'best'
		elif self.radQualHigh.isChecked():
			quality = 'high'
		else:
			quality = 'low'
		self.project.writeEntry("TUFLOW", 'video_quality', quality)
		ffmpeg_path = 'default' if self.radFfmpegSystem.isChecked() else 'custom'
		QSettings().setValue("TUFLOW/animation_ffmpeg_switch", ffmpeg_path)
		QSettings().setValue("TUFLOW/animation_ffmpeg", self.ffmpeg_bin)
	
class PlotProperties(QDialog, Ui_PlotProperties):
	
	def __init__(self, animationDialog, cboPlotType, mcboPlotItems):
		QDialog.__init__(self)
		self.setupUi(self)
		self.userSet = False  # once user has entered properties and left once, don't update anymore
		self.xUseMatplotLibDefault = False
		self.yUseMatplotLibDefault = False
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
	
	def setDefaults(self, animation, plotType, items, recalculate='', static=False):
		
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
			xmin = 99999
			xmax = -99999
			for item in items:
				if item != 'Current Time' and item != 'Culverts and Pipes':
					i = labels.index(item) if labels.count(item) else -1
					if i > -1:
						x = lines[i].get_xdata()
						margin = (max(x) - min(x)) * 0.05
						xmin = np.nanmin(x) - margin
						xmax = np.nanmax(x) + margin
						self.sbXmin.setValue(xmin)
						self.sbXMax.setValue(xmax)
						break
					self.sbXmin.setValue(0)
					self.sbXMax.setValue(1)
			if xmin == 99999 or xmax == -99999:
				self.xUseMatplotLibDefault = True
				
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
		#if 'axis 1' in axis and 'axis 2' in axis:
		#	if self.sbY2Min.value() == 0 and self.sbY2Max.value() == 0:
		#		userSetY2 = False
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
			# static option is for maps so don't need to loop
			# through all iterations in cross section / long plots
			# to get max and min
			if plotType == 'Time Series' or static == True:
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
					if ymin == 99999 or ymax == -99999:
						self.yUseMatplotLibDefault = True
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
						unit = self.animationDialog.tuView.tuOptions.timeUnits
						time = convertFormattedTimeToTime(timeFormatted, unit=unit)
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
					if ymin == 99999 or ymax == -99999:
						self.yUseMatplotLibDefault = True
				else:
					self.sbYMin.setValue(0)
					self.sbYMax.setValue(1)
		self.userSet = True


class TextPropertiesDialog(QDialog, Ui_textPropertiesDialog):
	
	def __init__(self):
		QDialog.__init__(self)
		self.setupUi(self)
		
		self.buttonBox.accepted.connect(self.accept)
		
		
class ImagePropertiesDialog(QDialog, Ui_ImageProperties):
	
	def __init__(self):
		QDialog.__init__(self)
		self.setupUi(self)
		
		self.buttonBox.accepted.connect(self.accept)
		
	def applyPrevious(self, prop=None):
		if prop is not None:
			self.rbUseOriginalSize.setChecked(prop.rbUseOriginalSize.isChecked())
			self.rbResizeImage.setChecked(prop.rbResizeImage.isChecked())
			self.sbSizeX.setValue(prop.sbSizeX.value())
			self.sbSizeY.setValue(prop.sbSizeY.value())
			self.cbKeepAspectRatio.setChecked(prop.cbKeepAspectRatio.isChecked())