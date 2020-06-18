import os
import numpy as np
import io
import datetime
import re
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets import *
from qgis.PyQt.QtXml import QDomDocument
from matplotlib.patches import Polygon
from matplotlib.quiver import Quiver
from matplotlib.collections import PolyCollection
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap
from tuflow.tuflowqgis_library import loadLastFolder, getResultPathsFromTCF, getScenariosFromTcf, getEventsFromTCF, \
	tuflowqgis_find_layer, getUnit, getCellSizeFromTCF, getOutputZonesFromTCF, getPathFromRel, convertTimeToFormattedTime, \
	convertFormattedTimeToTime, getResultPathsFromTLF, browse, qgsxml_as_mpl_cdict
from tuflow.tuflowqgis_dialog import tuflowqgis_scenarioSelection_dialog, tuflowqgis_eventSelection_dialog, \
	TuOptionsDialog, TuSelectedElementsDialog, tuflowqgis_meshSelection_dialog, TuBatchPlotExportDialog, \
	TuUserPlotDataManagerDialog, tuflowqgis_outputZoneSelection_dialog, tuflowqgis_brokenLinks_dialog
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuanimation import TuAnimationDialog
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tumap import TuMapDialog
from tuflow.tuflowqgis_tuviewer.tuflowqgis_turesults import TuResults


class TuMenuFunctions():
	"""
	Generic class for handling menu functions.
	
	"""
	
	def __init__(self, TuView):
		self.tuView = TuView
		self.iface = TuView.iface
	
	def load2dResults(self, **kwargs):
		"""
		Loads 2D results into map window and plotting ui

		:return: bool -> True for successful, False for unsuccessful
		"""

		result2D = kwargs['result_2D'] if 'result_2D' in kwargs.keys() else None  # list of xmdfs or dats
		
		if not result2D:
			# Get last loaded settings
			# fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_2DResults/lastFolder")
			fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_Results/lastFolder")

			# User get 2D result file
			inFileNames = QFileDialog.getOpenFileNames(self.iface.mainWindow(), 'Open TUFLOW 2D results file',
			                                           fpath,
			                                           "TUFLOW 2D Results (*.dat *.xmdf *.sup *.2dm *.nc)")
			if not inFileNames[0]:  # empty list
				return False
			
		else:
			inFileNames = result2D
			if not inFileNames[0]:  # empty list
				return False
		
		# if .sup file - read and extract mesh and result datasets
		for file in inFileNames[0]:
			filename, ext = os.path.splitext(file)
			filename = os.path.basename(filename)
			res = {'path': file}
			self.tuView.tuResults.tuResults2D.results2d[filename] = res
		if ext.upper() == '.SUP':
			sups, engine, build = self.resultsFromSuperFiles(inFileNames[0])
			if engine == 'FV':
				self.tuView.tuOptions.timeUnits = 's'
			else:
				self.tuView.tuOptions.timeUnits = 'h'
		
		# import into qgis
		if ext.upper() == '.SUP':
			loaded = self.tuView.tuResults.importResults('mesh', sups)
		else:
			loaded = self.tuView.tuResults.importResults('mesh', inFileNames[0])
		
		# finally save the last folder location
		fpath = os.path.dirname(inFileNames[0][0])
		settings = QSettings()
		settings.setValue("TUFLOW_Results/lastFolder", fpath)
		
		if not loaded:
			return False
		
		return True
	
	def load1dResults(self, **kwargs):
		"""
		Loads 1D results into ui and prompts user to load GIS files.

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		result1D = kwargs['result_1D'] if 'result_1D' in kwargs.keys() else None
		unlock = kwargs['unlock'] if 'unlock' in kwargs else True
		askGis = kwargs['ask_gis'] if 'ask_gis' in kwargs else True
		
		if not result1D:
			# Get last loaded settings
			# fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_1DResults/lastFolder")
			fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_Results/lastFolder")

			# User get 1D result file
			inFileNames = QFileDialog.getOpenFileNames(self.iface.mainWindow(), 'Open TUFLOW 1D results file',
			                                           fpath,
			                                           "TUFLOW 1D Results (*.tpc *.info)")
			if not inFileNames[0]:  # empty list
				return False
			
		else:
			# check if the result paths exist
			# for loading in project - check if links are not broken
			inFileNames = []
			brokenLinks = []
			for inFileName in result1D[0]:
				if os.path.exists(inFileName):
					inFileNames.append(inFileName)
				else:
					brokenLinks.append(inFileName)
			if brokenLinks:
				brokenLinksDialog = tuflowqgis_brokenLinks_dialog(self.iface, brokenLinks)
				brokenLinksDialog.exec_()
			inFileNames = [inFileNames]
			
		if not inFileNames[0]:
			return False
		
		# Prompt user if they want to load in GIS files
		for inFileName in inFileNames[0]:
			alsoOpenGis = QMessageBox.No
			if os.path.splitext(inFileName)[1].lower() == '.tpc':
				if askGis:
					alsoOpenGis = QMessageBox.question(self.iface.mainWindow(),
					                                   "TUFLOW Viewer", 'Do you also want to open result GIS layer?',
					                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
			break  # only need to ask once
		if alsoOpenGis == QMessageBox.Yes:
			self.tuView.tuResults.tuResults1D.openGis(inFileNames[0][0])
		elif alsoOpenGis == QMessageBox.Cancel:
			return False
		
		# import results
		self.tuView.tuResults.importResults('timeseries', inFileNames[0])
		
		# unlock map output timesteps only
		if unlock:
			if self.tuView.lock2DTimesteps:
				self.tuView.timestepLockChanged()
		
		# finally save the last folder location
		fpath = os.path.dirname(inFileNames[0][0])
		settings = QSettings()
		settings.setValue("TUFLOW_Results/lastFolder", fpath)
		
		return True

	def loadParticlesResults(self, **kwargs):
		"""
		Loads Particles results into ui and prompts user to load GIS files.

		:return: bool -> True for successful, False for unsuccessful
		"""

		resultParticles = kwargs['result_particles'] if 'result_particles' in kwargs.keys() else None
		unlock = kwargs['unlock'] if 'unlock' in kwargs else True
		askGis = kwargs['ask_gis'] if 'ask_gis' in kwargs else True

		if not resultParticles:
			# Get last loaded settings
			fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_ParticlesResults/lastFolder")

			# User get 1D result file
			inFileNames = QFileDialog.getOpenFileNames(self.iface.mainWindow(), 'Open TUFLOW Particles results file',
													   fpath,
													   "TUFLOW Particles Results (*.nc)")
			if not inFileNames[0]:  # empty list
				return False

		else:
			# check if the result paths exist
			# for loading in project - check if links are not broken
			inFileNames = []
			brokenLinks = []
			for inFileName in resultParticles[0]:
				if os.path.exists(inFileName):
					inFileNames.append(inFileName)
				else:
					brokenLinks.append(inFileName)
			if brokenLinks:
				brokenLinksDialog = tuflowqgis_brokenLinks_dialog(self.iface, brokenLinks)
				brokenLinksDialog.exec_()
			inFileNames = [inFileNames]

		if not inFileNames[0]:
			return False

		# Prompt user if they want to load in GIS files
		for inFileName in inFileNames[0]:
			alsoOpenGis = QMessageBox.No
			if os.path.splitext(inFileName)[1].lower() == '.tpc':
				if askGis:
					alsoOpenGis = QMessageBox.question(self.iface.mainWindow(),
													   "TUFLOW Viewer", 'Do you also want to open result GIS layer?',
													   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
			break  # only need to ask once
		if alsoOpenGis == QMessageBox.Yes:
			self.tuView.tuResults.tuResults1D.openGis(inFileNames[0][0])
		elif alsoOpenGis == QMessageBox.Cancel:
			return False

		# import results
		self.tuView.tuResults.importResults('particles', inFileNames[0])

		# unlock map output timesteps only
		if unlock:
			if self.tuView.lock2DTimesteps:
				self.tuView.timestepLockChanged()

		# finally save the last folder location
		fpath = os.path.dirname(inFileNames[0][0])
		settings = QSettings()
		settings.setValue("TUFLOW_ParticlesResults/lastFolder", fpath)

		return True

	def load1d2dResults(self):
		"""
		Loads 1D and 2D reuslts from TCF file.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		# Get last loaded settings
		fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_Results/lastFolder")
		
		# User get TCF file
		inFileNames = QFileDialog.getOpenFileNames(self.iface.mainWindow(), 'Open TUFLOW results file',
		                                           fpath,
		                                           "All Available (*.tcf *.tlf *.TCF *.TLF);;TUFLOW Control File (*.tcf *.TCF);;TUFLOW Log File (*.tlf *.TLF)")
		
		if not inFileNames[0]:  # empty list
			return False
		
		# get 1D and 2D results from TCF or TLF
		results1D, results2D, messages = [], [], []
		for file in inFileNames[0]:
			ext = os.path.splitext(file)[1].lower()
			
			if ext == '.tcf':
				# get scenarios from TCF and prompt user to select desired scenarios
				error, message, scenarios = getScenariosFromTcf(file)
				if error:
					if message:
						QMessageBox.critical(self.tuView, "Load From TCF", message)
				if scenarios:
					self.scenarioDialog = tuflowqgis_scenarioSelection_dialog(self.iface, file, scenarios)
					self.scenarioDialog.exec_()
					if self.scenarioDialog.scenarios is None:
						scenarios = []
					else:
						scenarios = self.scenarioDialog.scenarios
						
				# get events from TCF and prompt user to select desired events
				events = getEventsFromTCF(file)
				if events:
					self.eventDialog = tuflowqgis_eventSelection_dialog(self.iface, file, events)
					self.eventDialog.exec_()
					if self.eventDialog.events is None:
						events = []
					else:
						events = self.eventDialog.events
						
				# get output zones from TCF and prompt user to select desired output zones
				outputZones = getOutputZonesFromTCF(file)
				selectedOutputZones = []
				if outputZones:
					self.outputZoneDialog = tuflowqgis_outputZoneSelection_dialog(self.iface, file, outputZones)
					self.outputZoneDialog.exec_()
					for opz in outputZones:
						if opz['name'] in self.outputZoneDialog.outputZones:
							selectedOutputZones.append(opz)

				res1D, res2D, mess = getResultPathsFromTCF(file, scenarios=scenarios, events=events, output_zones=selectedOutputZones)
			else:
				res1D, res2D, mess = getResultPathsFromTLF(file)
			
			if res1D:
				if results1D:
					results1D[0] += res1D
				else:
					results1D.append(res1D)
			if res2D:
				if results2D:
					results2D[0] += res2D
				else:
					results2D.append(res2D)
			if mess:
				messages += mess

		# load 2D results
		if results2D:
			self.load2dResults(result_2D=results2D)
		
		# load 1D results
		if results1D:
			self.load1dResults(result_1D=results1D, unlock=False)
			
		# if no results found
		if not results2D and not results1D:
			mes = ''
			for i, m in enumerate(messages):
				if i == 0:
					mes += m
				else:
					mes += '\n\n{0}'.format(m)
			QMessageBox.information(self.iface.mainWindow(), "TUFLOW Viewer", "Failed to load results from {1}\n\n{0}".format(mes, ext.upper()[1:]))
			
		# finally save the last folder location
		fpath = os.path.dirname(inFileNames[0][0])
		settings = QSettings()
		settings.setValue("TUFLOW_Results/lastFolder", fpath)
		
		return True
	
	def remove1d2dResults(self):
		"""
		Removes the selected results from the ui.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		results = []
		for item in self.tuView.OpenResults.selectedItems():
			if self.tuView.hydTables.getData(item.text()) is None:
				results.append(item.text())

		self.tuView.tuResults.removeResults(results)
		for result in results:
			layer = tuflowqgis_find_layer(result)
			self.tuView.project.removeMapLayer(layer)
		
		self.tuView.canvas.refresh()
		self.tuView.resultsChanged()
		
		return True
	
	def remove2dResults(self):
		"""
		Removes the selected results from the ui - 2D results only
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		results = []
		for item in self.tuView.OpenResults.selectedItems():
			if self.tuView.hydTables.getData(item.text()) is None:
				layer = tuflowqgis_find_layer(item.text())
				self.tuView.project.removeMapLayer(layer)
			
		self.tuView.canvas.refresh()
		self.tuView.resultsChanged()
		
		return True
	
	def remove1dResults(self):
		"""
		Removes the selected results from the ui - 1D results only
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		results = []
		for item in self.tuView.OpenResults.selectedItems():
			if self.tuView.hydTables.getData(item.text()) is None:
				results.append(item.text())
		
		self.tuView.tuResults.tuResults1D.removeResults(results)
		
		self.tuView.resultsChanged()
		
		return True

	def removeParticlesResults(self):
		"""
		Removes the selected results from the ui - 1D results only

		:return: bool -> True for successful, False for unsuccessful
		"""

		results = []
		for item in self.tuView.OpenResults.selectedItems():
			if self.tuView.hydTables.getData(item.text()) is None:
				results.append(item.text())

		self.tuView.tuResults.tuResultsParticles.removeResults(results)

		self.tuView.resultsChanged()

		return True

	def updateMapPlotWindows(self):
		"""
		Update map window and all plot windows

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuView.renderMap()
		
		self.tuView.tuPlot.updateCurrentPlot(self.tuView.tabWidget.currentIndex())
		
		return True
	
	def options(self):
		"""
		Open options dialog
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		xAxisDatesPrev = self.tuView.tuOptions.xAxisDates
		showGridPrev = self.tuView.tuOptions.showGrid
		showTrianglesPrev = self.tuView.tuOptions.showTriangles
		timeUnitsPrev = self.tuView.tuOptions.timeUnits
		zeroDatePrev = self.tuView.tuOptions.zeroTime
		self.tuOptionsDialog = TuOptionsDialog(self.tuView.tuOptions)
		self.tuOptionsDialog.exec_()

		if self.tuView.tuMenuBar.showMedianEvent_action.isChecked() or self.tuView.tuMenuBar.showMeanEvent_action.isChecked():
			self.tuView.renderMap()
		if self.tuView.tuOptions.showGrid != showGridPrev or self.tuView.tuOptions.showTriangles != showTrianglesPrev:
			self.tuView.renderMap()
		if self.tuView.tuOptions.xAxisDates != xAxisDatesPrev:
			#self.tuView.tuResults.updateResultTypes()
			self.tuView.tuResults.updateTimeUnits()
		if self.tuView.tuOptions.timeUnits != timeUnitsPrev:
			self.tuView.tuResults.updateTimeUnits()
		if self.tuView.tuOptions.xAxisDates:
			if self.tuView.tuOptions.zeroTime != zeroDatePrev:
				self.tuView.tuResults.updateDateTimes()

		self.tuView.tuPlot.updateCurrentPlot(self.tuView.tabWidget.currentIndex(), update='1d and 2d only')
		self.tuView.tuPlot.tuPlotToolbar.cursorTrackingButton.setChecked(self.tuView.tuOptions.liveMapTracking)
		
		return True
	
	def exportCSV(self):
		"""
		Export the data as a CSV.

		:return: bool -> True for successful, False for unsuccessful
		"""

		plotNo = self.tuView.tabWidget.currentIndex()
		
		dataHeader, data = self.getPlotData(plotNo)
		
		if dataHeader is None or data is None:
			QMessageBox.critical(self.iface.mainWindow(), 'TUFLOW Viewer', 'Error exporting file')
			return False
		
		fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_Results/export_csv")
		
		saveFile = QFileDialog.getSaveFileName(self.iface.mainWindow(), 'Save File', fpath)[0]
		if len(saveFile) < 2:
			return
		else:
			if saveFile != os.sep and saveFile.lower() != 'c:\\' and saveFile != '':
				QSettings().setValue("TUFLOW_Results/export_csv", saveFile)
			if not os.path.splitext(saveFile)[-1]:  # no extension specified - default to csv
				saveFile = '{0}.csv'.format(saveFile)

		
		if saveFile is not None:
			retry = True
			while retry:
				try:
					file = open(saveFile, 'w')
					file.write('{0}\n'.format(dataHeader))
					for i, row in enumerate(data):
						line = ''
						for j, value in enumerate(row):
							if type(data[i][j]) is datetime.datetime:
								# line += '{0}\t'.format(data[i][j])
								line += '{0},'.format(data[i][j])
							elif not np.isnan(data[i][j]):
								line += '{0},'.format(data[i][j])
							else:
								line += '{0},'.format('')
						line += '\n'
						file.write(line)
					file.close()
					QMessageBox.information(self.iface.mainWindow(), 'TUFLOW Viewer', 'Successfully exported data.')
					retry = False
				except IOError:
					questionRetry = QMessageBox.question(self.iface.mainWindow(),
						                                 "TUFLOW Viewer", 'Could not access {0}. Check file is not open.'.format(saveFile),
						                                 QMessageBox.Retry | QMessageBox.Cancel)
					if questionRetry == QMessageBox.Cancel:
						retry = False
						return False
						
				except:
					QMessageBox.critical(self.iface.mainWindow(), 'TUFLOW Viewer', 'Error exporting file')
					retry = False
					return False
		
		return True
	
	def exportDataToClipboard(self):
		"""
		Export plot data to clipboard
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		plotNo = self.tuView.tabWidget.currentIndex()
		
		dataHeader, data = self.getPlotData(plotNo)
		
		if dataHeader is None or data is None:
			QMessageBox.critical(self.iface.mainWindow(), 'TUFLOW Viewer', 'Error exporting data')
			return False
		
		copyData = '{0}\n'.format(dataHeader.replace(',', '\t'))
		for i, row in enumerate(data):
			line = ''
			for j, value in enumerate(row):
				if type(data[i][j]) is datetime.datetime:
					line += '{0}\t'.format(data[i][j])
				elif not np.isnan(data[i][j]):
					line += '{0}\t'.format(data[i][j])
				else:
					line += '{0}\t'.format('')
			line += '\n'
			copyData += line
		
		clipboard = QApplication.clipboard()
		clipboard.setText(copyData)
		
		return True
	
	def exportImageToClipboard(self):
		"""
		Export plot image to clipboard
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		plotNo = self.tuView.tabWidget.currentIndex()
		
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, \
		yAxisLabel, xAxisLabel, xAxisLimits, yAxisLimits = self.tuView.tuPlot.plotEnumerator(plotNo)
		
		# thanks to EelkeSpaak for saving figure to clipboard
		# https://stackoverflow.com/questions/31607458/how-to-add-clipboard-support-to-matplotlib-figures
		buf = io.BytesIO()
		figure.savefig(buf)
		
		clipboard = QApplication.clipboard()
		clipboard.setImage(QImage.fromData(buf.getvalue()))
		buf.close()
		
		return True
		
	def getPlotData(self, plotNo):
		"""
		Collects all the plot data into one numpy array.
		
		:return: str Headers, numpy array data
		"""

		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.tuView.tuPlot.plotEnumerator(plotNo)
		
		# get lines and labels for both axis 1 and axis 2
		lines, labels = subplot.get_legend_handles_labels()
		lines2, labels2 = [], []
		if isSecondaryAxis[0]:
			subplot2 = self.tuView.tuPlot.getSecondaryAxis(plotNo)
			lines2, labels2 = subplot2.get_legend_handles_labels()
		
		# get maximum data length so we can adjust all lengths to be the same (easier to export that way)
		maxLen = 0
		for line in lines:
			if type(line) == Polygon:
				maxLen = max(maxLen, len(line.get_xy()))
			elif type(line) is Quiver:
				continue
			elif type(line) is PolyCollection:
				continue
			else:
				maxLen = max(maxLen, len(line.get_data()[0]))
		for line in lines2:
			if type(line) == Polygon:
				maxLen = max(maxLen, len(line.get_xy()))
			else:
				maxLen = max(maxLen, len(line.get_data()[0]))
			
		# put all data into one big numpy array and adjust data accordingly to max length - axis 1
		data = None
		for i, line in enumerate(lines):
			if i == 0:
				data = np.zeros((maxLen, 1))  # set up data array.. start with zeros and delete first column once populated
			if type(line) is Polygon:
				xy = line.get_xy()
				x = xy[:,0]
				y = xy[:,1]
			elif type(line) is Quiver:
				continue
			elif type(line) is PolyCollection:
				continue
			else:
				x, y = line.get_data()
			if type(x) is list:  # if not a numpy array, convert it to one
				x = np.array(x)
			if type(y) is list:  # if not a numpy array, convert it to one
				y = np.array(y)
			dataX = np.reshape(x, (len(x), 1))  # change the shape so it has 2 axis
			dataY = np.reshape(y, (len(y), 1))  # change the shape so it has 2 axis
			if len(dataX) < maxLen:
				diff = maxLen - len(dataX)
				fill = np.zeros([diff, 1]) * np.nan
				dataX = np.append(dataX, fill, axis=0)
			if len(dataY) < maxLen:
				diff = maxLen - len(dataY)
				fill = np.zeros([diff, 1]) * np.nan
				dataY = np.append(dataY, fill, axis=0)
			data = np.append(data, dataX, axis=1)
			data = np.append(data, dataY, axis=1)
			if i == 0:
				data = np.delete(data, 0, 1)  # delete initialised row of zeros
				
		# put all data into one big numpy array and adjust data accordingly to max length - axis 2
		needToDeleteFirstColumn = False
		for i, line in enumerate(lines2):
			if i == 0:
				if data is None:
					data = np.zeros((maxLen, 1))  # set up data array
					needToDeleteFirstColumn = True
			if type(line) is Polygon:
				xy = line.get_xy()
				x = xy[:,0]
				y = xy[:,1]
			elif type(line) is Quiver:
				continue
			elif type(line) is PolyCollection:
				continue
			else:
				x, y = line.get_data()
			if type(x) is list:  # if not a numpy array, convert it to one
				x = np.array(x)
			if type(y) is list:  # if not a numpy array, convert it to one
				y = np.array(y)
			dataX = np.reshape(x, (len(x), 1))  # change the shape so it has 2 axis
			dataY = np.reshape(y, (len(y), 1))  # change the shape so it has 2 axis
			if len(dataX) < maxLen:
				diff = maxLen - len(dataX)
				fill = np.zeros([diff, 1]) * np.nan
				dataX = np.append(dataX, fill, axis=0)
			if len(dataY) < maxLen:
				diff = maxLen - len(dataY)
				fill = np.zeros([diff, 1]) * np.nan
				dataY = np.append(dataY, fill, axis=0)
			data = np.append(data, dataX, axis=1)
			data = np.append(data, dataY, axis=1)
			if i == 0:
				if needToDeleteFirstColumn:
					data = np.delete(data, 0, 1)  # delete initialised row of zeros

		if plotNo == 0:
			dataHeader = self.getTimeSeriesPlotHeaders(labels, labels2)
		elif plotNo == 1:
			dataHeader = self.getLongPlotHeaders(labels, labels2)
		else:
			dataHeader = ''

		# delete duplicate Time arrays
		timeColumns = []
		for i in range(1, data.shape[1]):
			if i % 2 == 0:
				if np.allclose(data[:, i - 2], data[:, i], equal_nan=True):		# avoid nan == nan not being True
					timeColumns.append(i)
		data = np.delete(data, timeColumns, axis=1)
		# keep data headers only for remaining arrays
		dataHeader = dataHeader.split(',')
		remainingHeader = []
		for i in range(len(dataHeader)):
			if i not in timeColumns:
				remainingHeader.append(dataHeader[i])
		dataHeader = ','.join(remainingHeader)

		return dataHeader, data

	def getTimeSeriesPlotHeaders(self, labels, labels2):
		"""
		Returns column headings in comma delimiter format for time series export to csv.
		
		:param labels: list -> str label axis 1
		:param labels2: list -> str label axis 2
		:return: str column headers
		"""
		
		# get labels into one big comma delimiter string
		dataHeader = None
		for i, label in enumerate(labels):
			labelUnit = getUnit(label, self.tuView.canvas)
			if i == 0:
				dataHeader = 'Time (hr)'
				dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
			else:
				dataHeader = '{0},Time (hr)'.format(dataHeader)
				dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
		for i, label in enumerate(labels2):
			labelUnit = getUnit(label, self.tuView.canvas)
			if i == 0:
				if not labels:
					dataHeader = 'Time (hr)'
					dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
				else:
					dataHeader = '{0},Time (hr)'.format(dataHeader)
					dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
			else:
				dataHeader = '{0},Time (hr)'.format(dataHeader)
				dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
				
		return dataHeader
	
	def getLongPlotHeaders(self, labels, labels2):
		"""
		Return column headings in comma delimiter format for long plot export to csv.
		
		:param labels: list -> str label axis 1
		:param labels2: list -> str label axis 2
		:return: str column headers
		"""
		
		# get labels into one big comma delimiter string
		dataHeader = None
		xAxisUnit = getUnit(None, self.tuView.canvas, return_map_units=True)
		for i, label in enumerate(labels):
			labelUnit = getUnit(label, self.tuView.canvas)
			if i == 0:
				dataHeader = 'Offset ({0})'.format(xAxisUnit)
				dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
			else:
				dataHeader = '{0},Offset ({1})'.format(dataHeader, xAxisUnit)
				dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
		for i, label in enumerate(labels2):
			labelUnit = getUnit(label, self.tuView.canvas)
			if i == 0:
				if not labels:
					dataHeader = 'Offset ({0})'.format(xAxisUnit)
					dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
				else:
					dataHeader = '{0},Offset ({1})'.format(dataHeader, xAxisUnit)
					dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
			else:
				dataHeader = '{0},Offset ({1})'.format(dataHeader, xAxisUnit)
				dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
		
		return dataHeader
	
	def freezeAxisLimits(self, enum):
		"""
		Toggles Freeze Axis Y and X limits for both the menu bar and context menu.
		
		:param enum: int -> 0: menu bar
							1: context menu
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if enum == 0:
			if self.tuView.tuMenuBar.freezeAxisLimits_action.isChecked():
				# menu bar
				self.tuView.tuMenuBar.freezeAxisXLimits_action.setChecked(True)
				self.tuView.tuMenuBar.freezeAxisYLimits_action.setChecked(True)
				# context menu
				self.tuView.tuContextMenu.freezeAxisLimits_action.setChecked(True)
				self.tuView.tuContextMenu.freezeAxisXLimits_action.setChecked(True)
				self.tuView.tuContextMenu.freezeAxisYLimits_action.setChecked(True)
			else:
				# menu bar
				self.tuView.tuMenuBar.freezeAxisXLimits_action.setChecked(False)
				self.tuView.tuMenuBar.freezeAxisYLimits_action.setChecked(False)
				# context menu
				self.tuView.tuContextMenu.freezeAxisLimits_action.setChecked(False)
				self.tuView.tuContextMenu.freezeAxisXLimits_action.setChecked(False)
				self.tuView.tuContextMenu.freezeAxisYLimits_action.setChecked(False)
		elif enum == 1:
			if self.tuView.tuContextMenu.freezeAxisLimits_action.isChecked():
				# menu bar
				self.tuView.tuMenuBar.freezeAxisLimits_action.setChecked(True)
				self.tuView.tuMenuBar.freezeAxisXLimits_action.setChecked(True)
				self.tuView.tuMenuBar.freezeAxisYLimits_action.setChecked(True)
				# context menu
				self.tuView.tuContextMenu.freezeAxisXLimits_action.setChecked(True)
				self.tuView.tuContextMenu.freezeAxisYLimits_action.setChecked(True)
			else:
				# menu bar
				self.tuView.tuMenuBar.freezeAxisLimits_action.setChecked(False)
				self.tuView.tuMenuBar.freezeAxisXLimits_action.setChecked(False)
				self.tuView.tuMenuBar.freezeAxisYLimits_action.setChecked(False)
				# context menu
				self.tuView.tuContextMenu.freezeAxisXLimits_action.setChecked(False)
				self.tuView.tuContextMenu.freezeAxisYLimits_action.setChecked(False)
		else:
			return False
			
		return True
	
	def freezeAxisXLimits(self, enum):
		"""
		Toggles Freeze X axis limits for menu bar and context menu.
		
		:param enum: int -> 0: menu bar
							1: context menu
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if enum == 0:
			if self.tuView.tuMenuBar.freezeAxisXLimits_action.isChecked():
				self.tuView.tuContextMenu.freezeAxisXLimits_action.setChecked(True)
				self.tuView.tuPlot.tuPlotToolbar.freezeXAxisButton.setChecked(True)
			else:
				self.tuView.tuContextMenu.freezeAxisXLimits_action.setChecked(False)
				self.tuView.tuPlot.tuPlotToolbar.freezeXAxisButton.setChecked(False)
		elif enum == 1:
			if self.tuView.tuContextMenu.freezeAxisXLimits_action.isChecked():
				self.tuView.tuMenuBar.freezeAxisXLimits_action.setChecked(True)
			else:
				self.tuView.tuMenuBar.freezeAxisXLimits_action.setChecked(False)
		else:
			return False
		
		return True
	
	def freezeAxisYLimits(self, enum):
		"""
		Toggles Freeze Y axis limits for menu bar and context menu.

		:param enum: int -> 0: menu bar
							1: context menu
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if enum == 0:
			if self.tuView.tuMenuBar.freezeAxisYLimits_action.isChecked():
				self.tuView.tuContextMenu.freezeAxisYLimits_action.setChecked(True)
			else:
				self.tuView.tuContextMenu.freezeAxisYLimits_action.setChecked(False)
		elif enum == 1:
			if self.tuView.tuContextMenu.freezeAxisYLimits_action.isChecked():
				self.tuView.tuMenuBar.freezeAxisYLimits_action.setChecked(True)
			else:
				self.tuView.tuMenuBar.freezeAxisYLimits_action.setChecked(False)
		else:
			return False
		
		return True
	
	def freezeAxisLabels(self, enum):
		"""
		Toggles Freeze Axis Labels for menu bar and context menu
		
		:param enum: int -> 0: menu bar
							1: context menu
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if enum == 0:
			if self.tuView.tuMenuBar.freezeAxisLabels_action.isChecked():
				self.tuView.tuContextMenu.freezeAxisLabels_action.setChecked(True)
			else:
				self.tuView.tuContextMenu.freezeAxisLabels_action.setChecked(False)
		elif enum == 1:
			if self.tuView.tuContextMenu.freezeAxisLabels_action.isChecked():
				self.tuView.tuMenuBar.freezeAxisLabels_action.setChecked(True)
			else:
				self.tuView.tuMenuBar.freezeAxisLabels_action.setChecked(False)
		else:
			return False
		
		return True
	
	def freezeLegendLabels(self, enum):
		"""
		Toggles Freeze Legend Labels for menu bar and context menu.
		
		:param enum: int -> 0: menu bar
							1: context menu
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if enum == 0:
			if self.tuView.tuMenuBar.freezeLegendLabels_action.isChecked():
				self.tuView.tuContextMenu.freezeLegendLabels_action.setChecked(True)
			else:
				self.tuView.tuContextMenu.freezeLegendLabels_action.setChecked(False)
		elif enum == 1:
			if self.tuView.tuContextMenu.freezeLegendLabels_action.isChecked():
				self.tuView.tuMenuBar.freezeLegendLabels_action.setChecked(True)
			else:
				self.tuView.tuMenuBar.freezeLegendLabels_action.setChecked(False)
		else:
			return False
		
		self.tuView.tuPlot.setNewPlotProperties(enum)
		
		return True
		
	def exportTempLines(self):
		"""
		Export rubberband lines as shape file
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# User defined save path
		fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_Results/export_shp")
		saveFile = QFileDialog.getSaveFileName(self.iface.mainWindow(), 'Save Shape File', fpath)[0]
		if len(saveFile) < 2:
			return
		else:
			if saveFile != os.sep and saveFile.lower() != 'c:\\' and saveFile != '':
				QSettings().setValue("TUFLOW_Results/export_shp", saveFile)
			if not os.path.splitext(saveFile)[-1] or os.path.splitext(saveFile)[-1].lower() != '.shp':
				saveFile = '{0}.shp'.format(saveFile)

		# create shape file
		crs = self.tuView.project.crs()
		crsId = crs.authid()
		uri = 'linestring?crs={0}'.format(crsId)
		shpLayer = QgsVectorLayer(uri, os.path.splitext(os.path.basename(saveFile))[0], 'memory')
		dp = shpLayer.dataProvider()
		dp.addAttributes([
			QgsField('Name', QVariant.String, len=10),
			QgsField('Type', QVariant.String, len=50)
		])
		shpLayer.updateFields()
		feats = []  # list of QgsFeature objects
		#for i, rubberBand in enumerate(self.tuView.tuPlot.tuCrossSection.rubberBands):
		i = 0
		for line, type_ in self.tuView.tuPlot.lines.items():
			for rubberBand in line.rubberBands:
				i += 1
				geom = rubberBand.asGeometry().asPolyline()
				feat = QgsFeature()
				try:
					feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in geom]))
				except:
					feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x.x(), x.y()) for x in geom]))
				feat.setAttributes([
					'Line {0}'.format(i),
					type_
				])
				feats.append(feat)
		# for i, line in enumerate(self.tuView.tuPlot.tuFlowLine.rubberBands):
		# 	geom = line.asGeometry().asPolyline()
		# 	feat = QgsFeature()
		# 	try:
		# 		feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in geom]))
		# 	except:
		# 		feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x.x(), x.y()) for x in geom]))
		# 	feat.setAttributes(['Flow Location {0}'.format(i + 1)])
		# 	feats.append(feat)
		error = dp.addFeatures(feats)
		shpLayer.updateExtents()
		QgsVectorFileWriter.writeAsVectorFormat(shpLayer, saveFile, 'CP1250', crs, 'ESRI Shapefile')
		
		# ask user if import or not
		importLayer = QMessageBox.question(self.iface.mainWindow(),
		                                   "TUFLOW Viewer", 'Successfully saved {0}. Open in workspace?'.format(os.path.basename(saveFile)),
		                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
		if importLayer == QMessageBox.Yes:
			self.iface.addVectorLayer(saveFile, os.path.splitext(os.path.basename(saveFile))[0], 'ogr')
			
		return True
	
	def exportTempPoints(self):
		"""
		Export marker points as shape file
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# User defined save path
		fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_Results/export_shp")
		saveFile = QFileDialog.getSaveFileName(self.iface.mainWindow(), 'Save Shape File', fpath)[0]
		if len(saveFile) < 2:
			return
		else:
			if saveFile != os.sep and saveFile.lower() != 'c:\\' and saveFile != '':
				QSettings().setValue("TUFLOW_Results/export_shp", saveFile)
			if not os.path.splitext(saveFile)[-1] or os.path.splitext(saveFile)[-1].lower() != '.shp':
				saveFile = '{0}.shp'.format(saveFile)
		
		# create shape file
		crs = self.tuView.project.crs()
		crsId = crs.authid()
		uri = 'point?crs={0}'.format(crsId)
		shpLayer = QgsVectorLayer(uri, os.path.splitext(os.path.basename(saveFile))[0], 'memory')
		dp = shpLayer.dataProvider()
		dp.addAttributes([
			QgsField('Name', QVariant.String, len=10),
			QgsField('Type', QVariant.String, len=50)
		])
		shpLayer.updateFields()
		feats = []  # list of QgsFeature objects
		#for i, point in enumerate(self.tuView.tuPlot.tuTSPoint.points):
		i = 0
		for marker, type_ in self.tuView.tuPlot.markers.items():
			for point in marker.points:
				i += 1
				feat = QgsFeature()
				feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
				feat.setAttributes([
					'Point {0}'.format(i),
					type_
				])
				feats.append(feat)
		error = dp.addFeatures(feats)
		shpLayer.updateExtents()
		QgsVectorFileWriter.writeAsVectorFormat(shpLayer, saveFile, 'CP1250', crs, 'ESRI Shapefile')
		
		# ask user if import or not
		importLayer = QMessageBox.question(self.iface.mainWindow(),
		                                   "TUFLOW Viewer", 'Successfully saved {0}. Open in workspace?'.format(
				os.path.basename(saveFile)),
		                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
		if importLayer == QMessageBox.Yes:
			self.iface.addVectorLayer(saveFile, os.path.splitext(os.path.basename(saveFile))[0], 'ogr')
		
		return True
	
	def updateLegend(self):
		"""
		Updates the legend on the figure.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		self.tuView.tuPlot.updateLegend(self.tuView.tabWidget.currentIndex())
		self.tuView.tuPlot.setNewPlotProperties(self.tuView.tabWidget.currentIndex())
		
		return True
	
	def showMeanEvent(self):
		"""
		Shows the mean event from all displayed lines. The mean event is either chosen from the closest or next above.

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuView.tuPlot.showStatResult(self.tuView.tabWidget.currentIndex(), 'Mean')
		
		return True
	
	def showMedianEvent(self):
		"""
		Shows the median event from all displayed lines. If even number, will show the n + 1 event

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuView.tuPlot.showStatResult(self.tuView.tabWidget.currentIndex(), 'Median')
		
		return True
	
	def showSelectedElements(self):
		"""
		Displays a dialog of all the selected elements in the results.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		elements = self.tuView.tuResults.tuResults1D.ids
		
		self.selectedElementsDialog = TuSelectedElementsDialog(self.iface, elements)
		self.selectedElementsDialog.show()
		
		return True
	
	def toggleResultTypeToMax(self):
		"""
		Toggles the result type to max or temporal through context menu.

		:return: bool -> True for successful, False for unsuccessful
		"""

		self.tuView.tuContextMenu.resultTypeContextItem.toggleMaxActive()
		if self.tuView.tuContextMenu.resultTypeContextItem.isMin:
			self.tuView.tuContextMenu.resultTypeContextItem.toggleMinActive()

		self.tuView.maxResultTypesChanged(None)

		return True

	def toggleResultTypeToMin(self):
		"""
		Toggles the result type to min or temporal through context menu.

		:return: bool -> True for successful, False for unsuccessful
		"""

		self.tuView.tuContextMenu.resultTypeContextItem.toggleMinActive()
		if self.tuView.tuContextMenu.resultTypeContextItem.isMax:
			self.tuView.tuContextMenu.resultTypeContextItem.toggleMaxActive()

		self.tuView.minResultTypesChanged(None)

		return True
	
	def toggleResultTypeToSecondaryAxis(self):
		"""
		Toggles the result type to primary or secondary axis through context menu.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuView.tuContextMenu.resultTypeContextItem.toggleSecondaryActive()
		
		self.tuView.secondaryAxisResultTypesChanged(None)
		
		return True
		
	def saveDefaultStyleScalar(self, renderType, **kwargs):
		"""
		Saves the current active result type style as default for future similar result types.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		useClicked = kwargs['use_clicked'] if 'use_clicked' in kwargs.keys() else False
		saveType = kwargs['save_type'] if 'save_type' in kwargs else 'xml'
		meshIndex = kwargs['mesh_index'] if 'mesh_index' in kwargs else None
		result = kwargs['result'] if 'result' in kwargs else None
		
		# what happens if there are no mesh layer or more than one active mesh layer
		if meshIndex is not None and result is not None:
			meshLayer = tuflowqgis_find_layer(result)
		elif not self.tuView.tuResults.tuResults2D.activeMeshLayers:
				QMessageBox.information(self.iface.mainWindow(), 'TUFLOW Viewer', 'No Active Result Datasets')
				return False
		elif len(self.tuView.tuResults.tuResults2D.activeMeshLayers) > 1:
			self.meshDialog = tuflowqgis_meshSelection_dialog(self.iface, self.tuView.tuResults.tuResults2D.activeMeshLayers)
			self.meshDialog.exec_()
			if self.meshDialog.selectedMesh is None:
				return False
			else:
				meshLayer = tuflowqgis_find_layer(self.meshDialog.selectedMesh)
		else:
			meshLayer = self.tuView.tuResults.tuResults2D.activeMeshLayers[0]

		# get data provider and renderer settings
		dp = meshLayer.dataProvider()
		rs = meshLayer.rendererSettings()
		
		# get scalar renderer settings
		if useClicked:
			resultType = self.tuView.tuContextMenu.resultTypeContextItem.ds_name
			for i in range(dp.datasetGroupCount()):
				# is the datasetGroup a maximum?
				isDatasetMax = TuResults.isMaximumResultType(dp.datasetGroupMetadata(i).name(),
				                                             dp=dp, groupIndex=i)
				if self.tuView.tuContextMenu.resultTypeContextItem.isMax and isDatasetMax:
					if TuResults.stripMaximumName(dp.datasetGroupMetadata(i).name()) == resultType:
						activeScalarGroupIndex = i
						break
				else:
					if dp.datasetGroupMetadata(i).name() == resultType and not isDatasetMax:
						activeScalarGroupIndex = i
						break
		elif meshIndex is not None:
			activeScalarGroupIndex = meshIndex.group()
		else:
			activeScalar = rs.activeScalarDataset()
			activeScalarGroupIndex = activeScalar.group()
			if activeScalarGroupIndex == -1:
				QMessageBox.information(self.iface.mainWindow(), 'TUFLOW Viewer', 'No Active Scalar Dataset')
				return False

		activeScalarType = dp.datasetGroupMetadata(activeScalarGroupIndex).name()
		activeScalarType = TuResults.stripMaximumName(activeScalarType)
		rsScalar = rs.scalarSettings(activeScalarGroupIndex)
		
		# save color ramp if option chosen
		if renderType == 'color ramp':
			## get color ramp properties
			shader = rsScalar.colorRampShader()
			file = os.path.join(os.path.dirname(__file__), '_saved_styles', '{0}.xml'.format(activeScalarType))
			doc = QDomDocument(activeScalarType.replace(' ', '_'))
			element = shader.writeXml(doc)
			doc.appendChild(element)
			fo = open(file, 'w')
			fo.write('<?xml version="1.0" encoding="UTF-8"?>\n')
			fo.write(doc.toString())
			fo.close()
			
			# save as default for that result type
			key = "TUFLOW_scalarRenderer/{0}_ramp".format(activeScalarType)
			settings = QSettings()
			settings.setValue(key, file)
			
			# remove color map key
			key = "TUFLOW_scalarRenderer/{0}_map".format(activeScalarType)
			settings = QSettings()
			settings.remove(key)
		
		# save color map if option chosen
		elif renderType == 'color map':
			file = os.path.join(os.path.dirname(__file__), '_saved_styles', '{0}.xml'.format(activeScalarType))
			doc = QDomDocument(activeScalarType.replace(' ', '_'))
			element = rsScalar.writeXml(doc)
			doc.appendChild(element)
			if saveType == 'xml':
				fo = open(file, 'w')
				fo.write('<?xml version="1.0" encoding="UTF-8"?>\n')
				fo.write(doc.toString())
				fo.close()
				
				# save setting so tuview knows to load it in
				key = "TUFLOW_scalarRenderer/{0}_map".format(activeScalarType)
				settings = QSettings()
				settings.setValue(key, file)
				
				# remove color ramp key
				key = "TUFLOW_scalarRenderer/{0}_ramp".format(activeScalarType)
				settings = QSettings()
				settings.remove(key)
			else:  # save to project
				style = '<?xml version="1.0" encoding="UTF-8"?>\n' + doc.toString()
				return style
		
		QMessageBox.information(self.iface.mainWindow(), 'TUFLOW Viewer', 'Saved default style for {0}'.format(activeScalarType))
		
		return True
			
	def saveDefaultStyleVector(self, **kwargs):
		"""
		Save the current active vector renderer settings as default for future vector types.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		useClicked = kwargs['use_clicked'] if 'use_clicked' in kwargs.keys() else False
		saveType = kwargs['save_type'] if 'save_type' in kwargs else 'default'
		meshIndex = kwargs['mesh_index'] if 'mesh_index' in kwargs else None
		result = kwargs['result'] if 'result' in kwargs else None
		
		# what happens if there are no mesh layer or more than one active mesh layer
		if meshIndex is not None and result is not None:
			meshLayer = tuflowqgis_find_layer(result)
		elif not self.tuView.tuResults.tuResults2D.activeMeshLayers:
			if meshIndex is None:
				QMessageBox.information(self.iface.mainWindow(), 'TUFLOW Viewer', 'No Active Result Datasets')
				return False
		elif len(self.tuView.tuResults.tuResults2D.activeMeshLayers) > 1:
			self.meshDialog = tuflowqgis_meshSelection_dialog(self.iface, self.tuView.tuResults.tuResults2D.activeMeshLayers)
			self.meshDialog.exec_()
			if self.meshDialog.selectedMesh is None:
				return False
			else:
				meshLayer = tuflowqgis_find_layer(self.meshDialog.selectedMesh)
		else:
			meshLayer = self.tuView.tuResults.tuResults2D.activeMeshLayers[0]
			
		# get data provider and renderer settings
		dp = meshLayer.dataProvider()
		rs = meshLayer.rendererSettings()
		
		# get the active scalar dataset
		if useClicked:
			resultType = self.tuView.tuContextMenu.resultTypeContextItem.ds_name
			for i in range(dp.datasetGroupCount()):
				if self.tuView.tuContextMenu.resultTypeContextItem.isMax and \
						TuResults.isMaximumResultType(dp.datasetGroupMetadata(i).name()):
					if TuResults.stripMaximumName(dp.datasetGroupMetadata(i).name()) == resultType:
						activeVectorGroupIndex = i
						break
				else:
					if dp.datasetGroupMetadata(i).name() == resultType:
						activeVectorGroupIndex = i
						break
		elif meshIndex is not None:
			activeVectorGroupIndex = meshIndex.group()
		else:
			activeVector = rs.activeVectorDataset()
			activeVectorGroupIndex = activeVector.group()
			if activeVectorGroupIndex == -1:
				if saveType == 'default':
					QMessageBox.information(self.iface.mainWindow(), 'TUFLOW Viewer', 'No Active Vector Dataset')
					return False
				else:
					return ''
		activeVectorType = dp.datasetGroupMetadata(activeVectorGroupIndex).name()
		activeVectorType = TuResults.stripMaximumName(activeVectorType)

		qv = Qgis.QGIS_VERSION_INT
		rsVector = rs.vectorSettings(activeVectorGroupIndex)
		if qv >= 31100:
			rsVectorArrow = rsVector.arrowSettings()
		
		# get vector properties
		if qv < 31100:
			properties = {
				'arrow head length ratio': rsVector.arrowHeadLengthRatio(),
				'arrow head width ratio': rsVector.arrowHeadWidthRatio(),
				'color': rsVector.color(),
				'filter max': rsVector.filterMax(),
				'filter min': rsVector.filterMin(),
				'fixed shaft length': rsVector.fixedShaftLength(),
				'line width': rsVector.lineWidth(),
				'max shaft length': rsVector.maxShaftLength(),
				'min shaft length': rsVector.minShaftLength(),
				'scale factor': rsVector.scaleFactor(),
				'shaft length method': rsVector.shaftLengthMethod()
			}
		else:
			properties = {
				'arrow head length ratio': rsVectorArrow.arrowHeadLengthRatio(),
				'arrow head width ratio': rsVectorArrow.arrowHeadWidthRatio(),
				'color': rsVector.color(),
				'filter max': rsVector.filterMax(),
				'filter min': rsVector.filterMin(),
				'fixed shaft length': rsVectorArrow.fixedShaftLength(),
				'line width': rsVector.lineWidth(),
				'max shaft length': rsVectorArrow.maxShaftLength(),
				'min shaft length': rsVectorArrow.minShaftLength(),
				'scale factor': rsVectorArrow.scaleFactor(),
				'shaft length method': rsVectorArrow.shaftLengthMethod()
			}
		
		if saveType == 'default':
			# save as default for that result type
			key = "TUFLOW_vectorRenderer/vector"
			settings = QSettings()
			settings.setValue(key, properties)
		else:  # save to project
			return properties
		
		QMessageBox.information(self.iface.mainWindow(), 'TUFLOW Viewer', 'Saved default style for vectors')
		
		return True
	
	def loadDefaultStyleScalar(self, **kwargs):
		"""
		Loads the default scalar style for result type.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		useClicked = kwargs['use_clicked'] if 'use_clicked' in kwargs.keys() else False
		
		# what happens if there are no active mesh layers
		if not self.tuView.tuResults.tuResults2D.activeMeshLayers:
			QMessageBox.information(self.iface.mainWindow(), 'TUFLOW Viewer', 'No Active Result Datasets')
			return False
		
		for layer in self.tuView.tuResults.tuResults2D.activeMeshLayers:
			# get renderers and data provider
			dp = layer.dataProvider()
			rs = layer.rendererSettings()
			
			# get active dataset and check if it is scalar
			if useClicked:
				resultType = self.tuView.tuContextMenu.resultTypeContextItem.ds_name
				for i in range(dp.datasetGroupCount()):
					# is the datasetGroup a maximum?
					isDatasetMax = TuResults.isMaximumResultType(dp.datasetGroupMetadata(i).name(),
					                                             dp=dp, groupIndex=i)
					if self.tuView.tuContextMenu.resultTypeContextItem.isMax and isDatasetMax:
						if TuResults.stripMaximumName(dp.datasetGroupMetadata(i).name()) == resultType:
							activeScalarGroupIndex = i
							break
					else:
						if dp.datasetGroupMetadata(i).name() == resultType and not isDatasetMax:
							activeScalarGroupIndex = i
							break
						
			else:
				activeScalar = rs.activeScalarDataset()
				activeScalarGroupIndex = activeScalar.group()
				if not activeScalar.isValid():
					QMessageBox.information(self.iface.mainWindow(), 'TUFLOW Viewer', 'No Active Scalar Dataset')
					return False

			# get the name and try and apply default styling
			mdGroup = dp.datasetGroupMetadata(activeScalarGroupIndex)
			if mdGroup.isScalar():  # should be scalar considering we used activeScalarDataset
				resultType = TuResults.stripMaximumName(mdGroup.name())
				# try finding if style has been saved as a ramp first
				key = 'TUFLOW_scalarRenderer/{0}_ramp'.format(resultType)
				file = QSettings().value(key)
				if file:
					self.tuView.tuResults.tuResults2D.applyScalarRenderSettings(layer, activeScalarGroupIndex, file, type='ramp')
				# else try map
				key = 'TUFLOW_scalarRenderer/{0}_map'.format(resultType)
				file = QSettings().value(key)
				if file:
					self.tuView.tuResults.tuResults2D.applyScalarRenderSettings(layer, activeScalarGroupIndex, file, type='map')
					
		return True
	
	def loadDefaultStyleVector(self, **kwargs):
		"""
		Loads the default vector style for result type.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		useClicked = kwargs['use_clicked'] if 'use_clicked' in kwargs.keys() else False
		
		# what happens if there are no active mesh layers
		if not self.tuView.tuResults.tuResults2D.activeMeshLayers:
			QMessageBox.information(self.iface.mainWindow(), 'TUFLOW Viewer', 'No Active Result Datasets')
			return False
		
		for layer in self.tuView.tuResults.tuResults2D.activeMeshLayers:
			# get renderers and data provider
			dp = layer.dataProvider()
			rs = layer.rendererSettings()
			
			# get active dataset and check if it is vector
			if useClicked:
				resultType = self.tuView.tuContextMenu.resultTypeContextItem.ds_name
				for i in range(dp.datasetGroupCount()):
					if self.tuView.tuContextMenu.resultTypeContextItem.isMax and \
							TuResults.isMaximumResultType(dp.datasetGroupMetadata(i).name()):
						if TuResults.stripMaximumName(dp.datasetGroupMetadata(i).name()) == resultType:
							activeVectorGroupIndex = i
							break
					else:
						if dp.datasetGroupMetadata(i).name() == resultType:
							activeVectorGroupIndex = i
							break
			else:
				activeVector = rs.activeVectorDataset()
				activeVectorGroupIndex = activeVector.group()
				if not activeVector.isValid():
					QMessageBox.information(self.iface.mainWindow(), 'TUFLOW Viewer', 'No Active Scalar Dataset')
					return False
				
			# get the name and try and apply default styling
			mdGroup = dp.datasetGroupMetadata(activeVectorGroupIndex)
			if mdGroup.isVector():  # should be vector considering we used activeScalarDataset
				resultType = mdGroup.name()
				resultType = TuResults.stripMaximumName(resultType)
				mdGroup = dp.datasetGroupMetadata(activeVectorGroupIndex)
				rsVector = rs.vectorSettings(activeVectorGroupIndex)
				vectorProperties = QSettings().value('TUFLOW_vectorRenderer/vector')
				if vectorProperties:
					self.tuView.tuResults.tuResults2D.applyVectorRenderSettings(layer, activeVectorGroupIndex, vectorProperties)
					
		return True
	
	def resetDefaultStyles(self):
		"""
		Resets all the default styles back to original i.e. none
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		settings = QSettings()
		for key in settings.allKeys():
			if 'TUFLOW_scalarRenderer' in key:
				settings.remove(key)
			elif 'TUFLOW_vectorRenderer' in key:
				settings.remove(key)
		
		QMessageBox.information(self.iface.mainWindow(), 'TUFLOW Viewer', 'Reset Default Styles')
				
		return True

	def batchPlotExportInitialise(self):
		"""
		Initiates the dialog - automatically loops through all features in shape file (or selection of features in
		shape file) and exports set results to CSV or Image.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.batchPlotExportDialog = TuBatchPlotExportDialog(self.tuView)
		self.batchPlotExportDialog.exec_()
		
	def batchPlotExport(self, gisLayer, resultMesh, resultTypes, timestep, features, format, outputFolder, nameField, imageFormat):
		"""
		Automatically loops through all features in shape file (or selection of features in
		shape file) and exports set results to CSV or Image.
		
		:param gisLayer: str layer name
		:param resultMesh: list -> str mesh name e.g. 'M01_5m_001'
		:param resultTypes: list -> str result type e.g. 'depth'
		:param timestep: str time step e.g. '01:00:00'
		:param features: str 'all' or 'selection'
		:param format: str 'csv' or 'image'
		:param outputFolder: str output folder
		:param nameField: str attribute field used for naming files
		:param imageFormat: str extension e.g. '.png'
		:return: bool -> True for successful, False for unsuccessful
		"""

		# get features to iterate through
		vLayer = tuflowqgis_find_layer(gisLayer)
		if features == 'all':
			featIterator = vLayer.getFeatures()
			featureCount = vLayer.featureCount()
		elif features == 'selection':
			featIterator = vLayer.getSelectedFeatures()
			featureCount = vLayer.selectedFeatureCount()
		else:
			return False
			
		# get mesh layers (QgsMeshLayer)
		mLayers = []
		for mesh in resultMesh:
			mLayers.append(tuflowqgis_find_layer(mesh))
			
		# get attribute field index for name
		if nameField is not None and nameField != '-None-':
			nameIndex = vLayer.fields().names().index(nameField)
		else:
			nameIndex = None
			
		# convert formatted time back to what can be used to get results
		if timestep:
			if timestep == 'Maximum':
				timestepKey = timestep
			else:
				timestepKey = '{0:.6f}'.format(convertFormattedTimeToTime(timestep))
			
		# setup progress bar
		if featureCount:
			complete = 0
			self.iface.messageBar().clearWidgets()
			progressWidget = self.iface.messageBar().createMessage("TUFLOW Viewer",
			                                                       " Exporting {0}s . . .".format(format))
			messageBar = self.iface.messageBar()
			progress = QProgressBar()
			progress.setMaximum(100)
			progressWidget.layout().addWidget(progress)
			messageBar.pushWidget(progressWidget, duration=1)
			self.iface.mainWindow().repaint()
			pComplete = 0
			complete = 0
		# loop through features and output
		for f in featIterator:
			if vLayer.geometryType() == QgsWkbTypes.PointGeometry:
				if nameIndex is not None:
					name = '{0}'.format(f.attributes()[nameIndex])
				else:
					name = 'Time_Series_{0}'.format(f.id())
				self.tuView.tuPlot.tuPlot2D.plotTimeSeriesFromMap(
					vLayer, f, bypass=True, mesh=mLayers, types=resultTypes, export=format,
					export_location=outputFolder, name=name, export_format=imageFormat)
			elif vLayer.geometryType() == QgsWkbTypes.LineGeometry:
				if nameIndex is not None:
					name = '{0}'.format(f.attributes()[nameIndex])
				else:
					name = 'Cross_Section_{0}'.format(f.id())
				self.tuView.tuPlot.tuPlot2D.plotCrossSectionFromMap(
					vLayer, f, bypass=True, mesh=mLayers, types=resultTypes, export=format,
					export_location=outputFolder, name=name, time=timestepKey, time_formatted=timestep, export_format=imageFormat)
			else:
				return False
			complete += 1
			pComplete = complete / featureCount * 100
			progress.setValue(pComplete)

		return True
	
	def openUserPlotDataManager(self):
		"""
		Opens the user plot data manage dialog
		
		:return:
		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot
		
		self.userPlotDataDialog = TuUserPlotDataManagerDialog(self.iface, self.tuView.tuPlot.userPlotData)
		self.userPlotDataDialog.exec_()
		# self.tuView.tuPlot.clearPlot(self.tuView.tabWidget.currentIndex(), retain_1d=True, retain_2d=True, retain_flow=True)
		self.tuView.tuPlot.clearPlot2(self.tuView.tabWidget.currentIndex(), TuPlot.DataUserData)

		return True

	def toggleMeshRender(self):
		"""
		Toggles mesh on and off
		
		:return:
		"""
		
		if self.tuView.tuPlot.tuPlotToolbar.meshGridAction.isChecked():
			self.tuView.tuOptions.showGrid = True
		else:
			self.tuView.tuOptions.showGrid = False
			
		self.tuView.renderMap()
		
	def exportAnimation(self):
		"""
		Export animation dialog
		
		:return:
		"""
		
		self.animationDialog = TuAnimationDialog(self.tuView)
		self.animationDialog.show()
		
	def exportMaps(self):
		"""
		Export maps dialog
		
		:return:
		"""
		
		self.mapDialog = TuMapDialog(self.tuView)
		self.mapDialog.show()
		
	def resultsFromSuperFiles(self, files):
		"""
		Extract mesh files and result datasets from .sup files
		
		:param files: list -> str full path to .sup file
		:return: dict -> 'name': dict -> 'mesh': path to mesh, 'datasets': list -> paths to datasets
		"""

		results = {}
		engine = None
		build = None
		
		for file in files:
			
			result = {}
			basename, ext = file, 1
			while ext:
				basename, ext = os.path.splitext(basename)
			name = os.path.basename(basename)
			dir = os.path.dirname(file)
			
			with open(file, 'r') as fo:
				for line in fo:
					if 'mesh2d' in line.lower():
						components = line.split('mesh2d')
						if len(components) < 2:
							components = line.split('MESH2D')
						if len(components) < 2:
							continue
						mesh = components[1].strip().strip('"').strip("'")
						mesh = getPathFromRel(dir, mesh)
						result['mesh'] = mesh
					elif 'data' in line.lower():
						components = line.split('data')
						if len(components) < 2:
							components = line.split('DATA')
						if len(components) < 2:
							continue
						dataset = components[1].strip().strip('"').strip("'")
						dataset = getPathFromRel(dir, dataset)
						if 'datasets' not in result:
							result['datasets'] = []
						result['datasets'].append(dataset)
					elif 'tuflow' in line.lower() and 'build' in line.lower():
						if 'fv' in line.lower():
							engine = 'FV'
						else:
							engine = 'CLA'
						build = line.split(':')[1].strip()
			
			results[name] = result
			
		return results, engine, build

	def flowRegimeToggled(self):

		self.tuView.tuContextMenu.resultTypeContextItem.toggleFlowRegime()

		# redraw plot
		self.tuView.tuPlot.updateCurrentPlot(0, update='1d only')

	def loadHydraulicTables(self):
		"""

		"""

		inFileNames = browse(self.tuView, 'existing files', 'TUFLOW_Results/lastFolder', 'Load 1D Hydraulic Tables',
		                     'CSV (*.csv *.CSV)')
		for f in inFileNames:
			ta, err = self.tuView.hydTables.loadData(f)
			if err:
				QMessageBox.critical(self.tuView, "Load 1D Hydraulic Tables", err)
			else:
				# dn = re.sub(r"(_1d_ta_tables_check.csv)$", "", os.path.basename(f), flags=re.IGNORECASE)  # displayname
				# dn = '{0}_1d_ta'.format(dn)
				self.tuView.tuResults.add1dHydTableToResults(ta.displayName, ta)


	def removeHydraulicTables(self):
		"""

		"""

		results = []
		for item in self.tuView.OpenResults.selectedItems():
			ta = self.tuView.hydTables.getData(item.text())
			if ta is not None:
				self.tuView.tuResults.remove1dHydTable(ta.displayName)
				self.tuView.hydTables.closeData(ta.displayName)

	def addColourRampFromXML(self):
		"""

		"""

		xmlfile = browse(self.tuView, 'existing file', "TUFLOW/plot_colour_ramp", "Load Style XML", "XML (*.xml *.XML)")
		if xmlfile:
			cdicts = qgsxml_as_mpl_cdict(xmlfile)

			if not cdicts:
				QMessageBox.warning(self.tuView, "Add Colour Ramp to Plot", "Error importing colour ramp styles")

			for name, cdict in cdicts.items():
				lcm = LinearSegmentedColormap(name, cdict)
				cm.register_cmap(name=name, cmap=lcm)

			QMessageBox.information(self.tuView, "Add Colour Ramp to Plot", "Successfully imported colour ramp(s)")