import os
from PyQt5.QtGui import QColor
from PyQt5.QtCore import *
from qgis.core import QgsPoint, QgsPointXY, QgsGeometry, Qgis
from qgis.gui import QgsVertexMarker, QgsRubberBand
from tuflow.tuflowqgis_library import tuflowqgis_find_layer


class TuProject():
	"""
	Class for saving and loading dock settings to / from project
	"""
	
	def __init__(self, TuView):
		self.tuView = TuView
		self.project = TuView.project
		
	def save(self):
		"""Saves settings to project"""

		# save if dock is opened or not
		if self.tuView.isVisible():
			self.project.writeEntry("TUVIEW", "dock_opened", "Open")
		else:
			self.project.writeEntry("TUVIEW", "dock_opened", "Close")
		
		# 2D results
		self.processResults2d('save')
		
		# 1D results
		self.processResults1d('save')
		
		# active results
		self.processActiveResults('save')
		
		# active result types
		self.processActiveResultTypes('save')
		
		# active time
		self.processActiveTime('save')
		
		# max and secondary types
		self.processMaxSecondaryTypes('save')
		
		# styles
		self.processMeshStyles('save')
		
		# options
		self.processOptions('save')
		
		# current plot tab
		self.processPlotTab('save')
		
		# map output plotting
		self.processMapPlotting('save')
		
		# general plotting options
		self.processPlotToolbarOptions('save')
		
		# plot configuration
		self.processPlotConfiguration('save')
		
		# graphic objects
		self.processGraphics('save')
		
		# user plot data
		self.processUserPlotData('save')
		
		# show active time
		self.processShowActiveTime('save')
		
	def load(self):
		"""Loads settings for project"""
		
		if Qgis.QGIS_VERSION_INT >= 30400:

			# should dock be visible?
			visible = True if self.project.readEntry("TUVIEW", "dock_opened")[0] == 'Open' else False
			self.tuView.setVisible(visible)
		
			# 2D results
			#self.processResults2d('load')
		
			# 1D results
			self.processResults1d('load')
			
			# active results
			self.processActiveResults('load')
			self.tuView.tuResults.updateResultTypes()
			
			# active result types
			#self.processActiveResultTypes('load')
			
			# active time
			self.processActiveTime('load')
			
			# max and secondary types
			self.processMaxSecondaryTypes('load')
			
			# styles
			self.processMeshStyles('load')
			
			# options
			self.processOptions('load')
			
			# current plot tab
			self.processPlotTab('load')
			
			# map output plotting
			self.processMapPlotting('load')
			
			# general plotting options
			self.processPlotToolbarOptions('load')
			
			# plot configuration
			self.processPlotConfiguration('load')
			
			# graphic objects
			self.processGraphics('load')
			
			# user plot data
			self.processUserPlotData('load')
			
			# show active time
			self.processShowActiveTime('load')
			
			# after all said and done.. render
			#self.tuView.tuResults.tuResults2D.renderMap()
		
	def processResults2d(self, call_type):
		"""Project settings for 2d results"""
		
		if call_type == 'save':
			results2d = self.tuView.tuResults.tuResults2D.results2d
			results = ''
			for i, result in enumerate(results2d):
				if i == 0:
					results += results2d[result]['path']
				else:
					results += '~~{0}'.format(results2d[result]['path'])
			self.project.writeEntry("TUVIEW", "results2d", results)
		else:  # load
			results = self.project.readEntry("TUVIEW", "results2d")[0]
			if results:
				results = results.split('~~')
				try:
					self.tuView.tuMenuBar.tuMenuFunctions.load2dResults(result_2D=[results])
				except:
					pass
			
	def processResults1d(self, call_type):
		"""Project settings for 1d results"""
		
		if call_type == 'save':
			results1d = self.tuView.tuResults.tuResults1D.results1d
			results = ''
			for i, result in enumerate(results1d):
				if i == 0:
					results += os.path.join(results1d[result].fpath, results1d[result].filename)
				else:
					results += '~~{0}'.format(os.path.join(results1d[result].fpath, results1d[result].filename))
			self.project.writeEntry("TUVIEW", "results1d", results)
		else:  # load
			results = self.project.readEntry("TUVIEW", "results1d")[0]
			if results:
				results = results.split('~~')
				try:
					self.tuView.tuMenuBar.tuMenuFunctions.load1dResults(result_1D=[results], ask_gis=False)
				except:
					pass
	
	def processActiveResults(self, call_type):
		"""Saves active mesh layers to project"""
		
		openResults = self.tuView.OpenResults
		
		if call_type == 'save':
			selectedResults = []
			results = []
			for i in range(openResults.count()):
				item = openResults.item(i)
				results.append(item.text())
				if item.isSelected():
					selectedResults.append(item.text())
			# get the result order
			allResults = ''
			for i, result in enumerate(results):
				if i == 0:
					allResults += result
				else:
					allResults += '~~{0}'.format(result)
			self.project.writeEntry("TUVIEW", "allresults", allResults)
			# get the selected results
			activeResults = ''
			for i, result in enumerate(selectedResults):
				if i == 0:
					activeResults += result
				else:
					activeResults += '~~{0}'.format(result)
			self.project.writeEntry("TUVIEW", "activeresults", activeResults)
		else:  # load
			try:
				allResults = self.project.readEntry("TUVIEW", 'allresults')[0]
				if allResults:
					allResults = allResults.split('~~')
				activeResults = self.project.readEntry("TUVIEW", "activeresults")[0]
				if activeResults:
					activeResults = activeResults.split('~~')
				# first fix the order
				if allResults:
					openResults.clear()
					for res in allResults:
						if res in self.tuView.tuResults.results:
							openResults.addItem(res)
				# then enforce selection
				for i in range(openResults.count()):
					item = openResults.item(i)
					if item.text() in activeResults:
						item.setSelected(True)
					else:
						item.setSelected(False)
				self.tuView.tuResults.tuResults2D.activeMeshLayers.clear()
				if activeResults:
					for result in activeResults:
						layer = tuflowqgis_find_layer(result)
						if layer is not None:
							self.tuView.tuResults.tuResults2D.activeMeshLayers.append(layer)
			except:
				pass
			
	def processActiveResultTypes(self, call_type):
		"""Project settings for active result types"""
		
		openResultTypes = self.tuView.OpenResultTypes
		
		if call_type == 'save':
			selectedIndexes = openResultTypes.selectedIndexes()
			selectedTypes = []
			for index in selectedIndexes:
				item = index.internalPointer()
				selectedTypes.append(item.ds_name)
			activeResultTypes = ''
			for i, result in enumerate(selectedTypes):
				if i == 0:
					activeResultTypes += result
				else:
					activeResultTypes += '~~{0}'.format(result)
			self.project.writeEntry("TUVIEW", "activeresulttypes", activeResultTypes)
		else:  # load
			try:
				activeResultTypes = self.project.readEntry("TUVIEW", "activeresulttypes")[0]
				if activeResultTypes:
					activeResultTypes = activeResultTypes.split('~~')
					self.tuView.tuResults.activeResultsIndexes.clear()
					self.tuView.tuResults.activeResultsTypes.clear()
					self.tuView.tuResults.activeResultsItems.clear()
					self.tuView.tuResults.activeResults.clear()
					self.tuView.tuResults.tuResults1D.items1d.clear()
					self.tuView.tuResults.tuResults1D.typesTS.clear()
					self.tuView.tuResults.tuResults1D.typesLP.clear()
					self.tuView.tuResults.tuResults1D.pointTS.clear()
					self.tuView.tuResults.tuResults1D.lineTS.clear()
					self.tuView.tuResults.tuResults1D.regionTS.clear()
					for i in range(openResultTypes.model().mapOutputsItem.childCount()):
						item = openResultTypes.model().dsindex2item[i]
						name = item.ds_name
						if name in activeResultTypes:
							self.tuView.tuResults.activeResults.append(name)
							self.tuView.tuResults.activeResultsItems.append(item)
							self.tuView.tuResults.activeResultsIndexes.append(openResultTypes.model().item2index(item))
							self.tuView.tuResults.activeResultsTypes.append(item.ds_type)
							if item.ds_type == 1:
								self.tuView.tuResults.tuResults2D.activeScalar = name
							elif item.ds_type == 2:
								self.tuView.tuResults.tuResults2D.activeVector = name
					for item in openResultTypes.model().timeSeriesItem.children():
						name = item.ds_name
						if name in activeResultTypes:
							self.tuView.tuResults.activeResultsItems.append(item)
							self.tuView.tuResults.activeResultsIndexes.append(openResultTypes.model().item2index(item))
							self.tuView.tuResults.activeResultsTypes.append(item.ds_type)
							nameAppend = ''
							if item.ds_type == 4 or item.ds_type == 5 or item.ds_type == 6 or item.ds_type == 7:
								self.tuView.tuResults.tuResults1D.items1d.append(name)
								if item.ds_type == 4 or item.ds_type == 5 or item.ds_type == 6:
									nameAppend = '_TS'
									self.tuView.tuResults.tuResults1D.typesTS.append(name)
								elif item.ds_type == 7:
									nameAppend = '_LP'
									self.tuView.tuResults.tuResults1D.typesLP.append(name)
								elif item.ds_type == 8:
									nameAppend = '_CS'
								if item.ds_type == 4:
									self.tuView.tuResults.tuResults1D.pointTS.append(name)
								elif item.ds_type == 5:
									self.tuView.tuResults.tuResults1D.lineTS.append(name)
								elif item.ds_type == 6:
									self.tuView.tuResults.tuResults1D.regionTS.append(name)
								name += nameAppend
								self.tuView.tuResults.activeResults.append(name)
			except:
				pass
							
	def processActiveTime(self, call_type):
		"""Project settings for current timestep"""
		
		cboTime = self.tuView.cboTime
		sliderTime = self.tuView.sliderTime
		btn2dLock = self.tuView.btn2dLock
		
		if call_type == 'save':
			cbo = '{0}'.format(cboTime.currentIndex())
			self.project.writeEntry("TUVIEW", "cbotime", cbo)
			slider = '{0}'.format(sliderTime.sliderPosition())
			self.project.writeEntry("TUVIEW", "slidertime", slider)
			lock = '{0}'.format(self.tuView.lock2DTimesteps)
			self.project.writeEntry("TUVIEW", "locktime", lock)
		else:  # load
			lock = self.project.readEntry("TUVIEW", "locktime")[0]
			lock = True if lock == 'True' else False
			self.tuView.lock2DTimesteps = lock
			btn2dLock.setChecked(lock)
			self.tuView.timestepLockChanged(switch=False)
			cbo = self.project.readEntry("TUVIEW", "cbotime")[0]
			cboTime.setCurrentIndex(int(cbo))
			slider = self.project.readEntry("TUVIEW", "slidertime")[0]
			sliderTime.setSliderPosition(int(slider))
	
	def processMaxSecondaryTypes(self, call_type):
		"""Project settings for result types set to Max and Secondary Axis"""
		
		secondaryResultTypes = self.tuView.tuResults.secondaryAxisTypes
		maxResultTypes = self.tuView.tuResults.maxResultTypes
		openResultTypes = self.tuView.OpenResultTypes
		
		if call_type == 'save':
			stypes = ''
			for i, rtype in enumerate(secondaryResultTypes):
				if i == 0:
					stypes += rtype
				else:
					stypes += '~~{0}'.format(rtype)
			self.project.writeEntry("TUVIEW", "secondarytypes", stypes)
			mtypes = ''
			for i, rtype in enumerate(maxResultTypes):
				if i == 0:
					mtypes += rtype
				else:
					mtypes += '~~{0}'.format(rtype)
			self.project.writeEntry("TUVIEW", "maxtypes", mtypes)
		else:  # load
			try:
				stypes = self.project.readEntry("TUVIEW", "secondarytypes")[0]
				secondaryResultTypes.clear()
				secondaryResultTypes += stypes.split('~~')
				mtypes = self.project.readEntry("TUVIEW", "maxtypes")[0]
				maxResultTypes.clear()
				maxResultTypes += mtypes.split('~~')
				for item in openResultTypes.model().mapOutputsItem.children():
					if item.ds_name in secondaryResultTypes:
						item.toggleSecondaryActive()
					if item.ds_name in maxResultTypes:
						item.toggleMaxActive()
				for item in openResultTypes.model().timeSeriesItem.children():
					if '{0}_1d'.format(item.ds_name) in secondaryResultTypes:
						item.toggleSecondaryActive()
					if '{0}_1d'.format(item.ds_name) in maxResultTypes:
						item.toggleMaxActive()
				if '2D Flow' in secondaryResultTypes:
					self.tuView.tuPlot.tuPlotToolbar.fluxSecAxisButton.setChecked(True)
			except:
				pass

	def processMeshStyles(self, call_type):
		"""Project settings for scalar and vector mesh styles."""
		
		results = self.tuView.tuResults.results
		menuFunctions = self.tuView.tuMenuBar.tuMenuFunctions
		results2D = self.tuView.tuResults.tuResults2D
		
		if call_type == 'save':
			for result, rtypeDict in results.items():
				# result -> 'M03_5m_001'
				# rtype -> 'Depth' or 'point_ts'
				for rtype, timeDict in rtypeDict.items():
					if '_ts' not in rtype and '_lp' not in rtype:
						if type(timeDict) is dict:  # make sure we're looking at 2d results
							for time, items in timeDict.items():  # just do first timestep
								# time -> '0.0000'
								# items -> ( timestep, type, QgsMeshDatasetIndex )
								dtype = items[1]  # data type e.g. scalar or vector
								mindex = items[2]  # QgsMeshDatasetIndex
								style = None
								if dtype == 1:  # scalar
									style = menuFunctions.saveDefaultStyleScalar('color map', mesh_index=mindex,
									                                             result=result, save_type='project')
									if style is not None:
										rtypeFormatted = rtype.replace('/', '_')
										rtypeFormatted = rtypeFormatted.replace(' ', '_')
										self.project.writeEntry("TUVIEW",
										                        "scalarstyle_{0}_{1}".format(result, rtypeFormatted),
										                        style)
								elif dtype == 2:  # vector
									style = menuFunctions.saveDefaultStyleVector(mesh_index=mindex, save_type='project',
									                                             result=result)
									for key, item in style.items():
										if key == 'color':
											item = item.name()
										rtypeFormatted = rtype.replace('/', '_')
										rtypeFormatted = rtypeFormatted.replace(' ', '_')
										keyFormatted = key.replace(' ', '_')
										self.project.writeEntry("TUVIEW",
										                        "vectorstyle_{0}_{1}_{2}".format(
											                        result, rtypeFormatted, keyFormatted),
										                        "{0}".format(item))
								
								break  # only do first timestep
		else:  # load
			for result, rtypeDict in results.items():
				# result -> 'M03_5m_001'
				# rtype -> 'Depth' or 'point_ts'
				layer = tuflowqgis_find_layer(result)
				for rtype, timeDict in rtypeDict.items():
					if '_ts' not in rtype and '_lp' not in rtype:
						if type(timeDict) is dict:  # make sure we're looking at 2d results
							for time, items in timeDict.items():  # just do first timestep
								# time -> '0.0000'
								# items -> ( timestep, type, QgsMeshDatasetIndex )
								rtypeFormatted = rtype.replace('/', '_')
								rtypeFormatted = rtypeFormatted.replace(' ', '_')
								style = self.project.readEntry("TUVIEW",
								                               "scalarstyle_{0}_{1}".format(result, rtypeFormatted))[0]
								try:
									dtype = items[1]  # data type e.g. scalar or vector
									mindex = items[2]  # QgsMeshDatasetIndex
									gindex = mindex.group()  # int group index
									if dtype == 1:
										results2D.applyScalarRenderSettings(layer, gindex, style, 'map',
										                                    save_type='project')
									elif dtype == 2:
										propertyDict = {}
										propertyList = [
											'arrow head length ratio',
											'arrow head width ratio',
											'color',
											'filter max',
											'filter min',
											'fixed shaft length',
											'line width',
											'max shaft length',
											'min shaft length',
											'scale factor',
											'shaft length method'
										]
										for property in propertyList:
											propertyFormatted = property.replace(' ', '_')
											value = self.project.readEntry("TUVIEW",
											                               "vectorstyle_{0}_{1}_{2}".format(
												                               result, rtypeFormatted, propertyFormatted))[0]
											if value == '':
												continue
											if property == 'color':
												item = QColor(value)
											elif property == 'shaft length method':
												item = int(value)
											else:
												item = float(value)
											propertyDict[property] = item
										results2D.applyVectorRenderSettings(layer, gindex, propertyDict)
								except:
									pass
								break
								
	def processOptions(self, call_type):
		"""Project settings for tuview options."""
		
		if call_type == 'save':
			self.tuView.tuOptions.saveProject(self.project)
		else:
			try:
				self.tuView.tuOptions.readProject(self.project)
				self.tuView.tuPlot.tuPlotToolbar.cursorTrackingButton.setChecked(self.tuView.tuOptions.liveMapTracking)
			except:
				pass
			
	def processPlotTab(self, call_type):
		"""Project settings for which plotting tab is active."""
		
		if call_type == 'save':
			currentTab = self.tuView.tabWidget.currentIndex()
			self.project.writeEntry("TUVIEW", "currentplottab", str(currentTab))
		else:  # load
			try:
				currentTab = int(self.project.readEntry("TUVIEW", "currentplottab")[0])
			except:
				currentTab = 0
			self.tuView.tabWidget.setCurrentIndex(currentTab)
	
	def processMapPlotting(self, call_type):
		"""Project settings for 2D mapoutput plotting."""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot
		
		cbo = self.tuView.cboSelectType
		toolbar = self.tuView.tuPlot.tuPlotToolbar
		
		if call_type == 'save':
			self.project.writeEntry("TUVIEW", "selecttype", str(cbo.currentIndex()))
			
			checkedTS = toolbar.getCheckedItemsFromPlotOptions(TuPlot.DataTimeSeries2D)
			tstypes = ''
			for i, rtype in enumerate(checkedTS):
				if i == 0:
					tstypes += rtype
				else:
					tstypes += '~~{0}'.format(rtype)
			self.project.writeEntry("TUVIEW", "tstypes", tstypes)
			
			checkedCS = toolbar.getCheckedItemsFromPlotOptions(TuPlot.DataCrossSection2D)
			cstypes = ''
			for i, rtype in enumerate(checkedCS):
				if i == 0:
					cstypes += rtype
				else:
					cstypes += '~~{0}'.format(rtype)
			self.project.writeEntry("TUVIEW", "cstypes", cstypes)
		else:  # load
			try:
				selectType = self.project.readEntry("TUVIEW", "selecttype")[0]
				cbo.setCurrentIndex(int(selectType))
			except:
				pass

			try:
				tstypes = self.project.readEntry("TUVIEW", "tstypes")[0]
				tstypes = tstypes.split('~~')
				toolbar.setCheckedItemsPlotOptions(tstypes, 0)
			except:
				pass

			try:
				cstypes = self.project.readEntry("TUVIEW", "cstypes")[0]
				cstypes = cstypes.split('~~')
				toolbar.setCheckedItemsPlotOptions(cstypes, 1)
			except:
				pass
			
	def processPlotToolbarOptions(self, call_type):
		"""Project settings for general plotting options."""
		
		viewToolbarTS = self.tuView.tuPlot.tuPlotToolbar.viewToolbarTimeSeries
		viewToolbarLP = self.tuView.tuPlot.tuPlotToolbar.viewToolbarLongPlot
		viewToolbarCS = self.tuView.tuPlot.tuPlotToolbar.viewToolbarCrossSection
		viewToolbarVP = self.tuView.tuPlot.tuPlotToolbar.viewToolbarVerticalProfile
		subplotTS = self.tuView.tuPlot.subplotTimeSeries
		subplotLP = self.tuView.tuPlot.subplotLongPlot
		subplotCS = self.tuView.tuPlot.subplotCrossSection
		subplotVP = self.tuView.tuPlot.subplotVerticalProfile
		isSecondaryTS = self.tuView.tuPlot.isTimeSeriesSecondaryAxis
		isSecondaryLP = self.tuView.tuPlot.isLongPlotSecondaryAxis
		isSecondaryCS = self.tuView.tuPlot.isCrossSectionSecondaryAxis
		isSecondaryVP = self.tuView.tuPlot.isVerticalProfileSecondaryAxis

		if call_type == 'save':
			self.saveViewToolbar(viewToolbarTS, subplotTS, isSecondaryTS, 0, 'ts')
			self.saveViewToolbar(viewToolbarLP, subplotLP, isSecondaryLP, 1, 'lp')
			self.saveViewToolbar(viewToolbarCS, subplotCS, isSecondaryCS, 2, 'cs')
			self.saveViewToolbar(viewToolbarVP, subplotCS, isSecondaryCS, 3, 'vp')
		else:  # load
			try:
				self.loadViewToolbar(viewToolbarTS, subplotTS, 0, 'ts')
				self.loadViewToolbar(viewToolbarLP, subplotLP, 1, 'lp')
				self.loadViewToolbar(viewToolbarCS, subplotCS, 2, 'cs')
				self.loadViewToolbar(viewToolbarVP, subplotCS, 3, 'vp')
			except:
				pass

	def saveViewToolbar(self, viewToolbar, subplot, isSecondary, plotNo, suffix):
			freezeAxis = viewToolbar.freezeXYAxisAction.isChecked()
			self.project.writeEntry("TUVIEW", "freezeaxis{0}".format(suffix), str(freezeAxis))
			freezeXAxis = viewToolbar.freezeXAxisAction.isChecked()
			self.project.writeEntry("TUVIEW", "freezexaxis{0}".format(suffix), str(freezeXAxis))
			freezeYAxis = viewToolbar.freezeYAxisAction.isChecked()
			self.project.writeEntry("TUVIEW", "freezeyaxis{0}".format(suffix), str(freezeYAxis))
			legend = viewToolbar.legendMenu.menuAction().isChecked()
			self.project.writeEntry("TUVIEW", "legend{0}".format(suffix), str(legend))
			legendPos = viewToolbar.legendCurrentIndex()
			self.project.writeEntry("TUVIEW", "legendpos{0}".format(suffix), str(legendPos))
	
			xmin, xmax = subplot.get_xlim()
			ymin, ymax = subplot.get_ylim()
			self.project.writeEntry("TUVIEW", 'xmin{0}'.format(suffix), xmin)
			self.project.writeEntry("TUVIEW", 'xmax{0}'.format(suffix), xmax)
			self.project.writeEntry("TUVIEW", 'ymin{0}'.format(suffix), ymin)
			self.project.writeEntry("TUVIEW", 'ymax{0}'.format(suffix), ymax)
			if isSecondary[0]:
				subplot2 = self.tuView.tuPlot.getSecondaryAxis(plotNo)
				ymin2, ymax2 = subplot2.get_ylim()
				self.project.writeEntry("TUVIEW", "issecondary{0}".format(suffix), "True")
				self.project.writeEntry("TUVIEW", 'ymin2{0}'.format(suffix), ymin2)
				self.project.writeEntry("TUVIEW", 'ymax2{0}'.format(suffix), ymax2)
	
	def loadViewToolbar(self, viewToolbar, subplot, plotNo, suffix):
			freezeAxis = True if self.project.readEntry("TUVIEW", "freezeaxis{0}".format(suffix))[0] == 'True' else False
			viewToolbar.freezeXYAxisAction.setChecked(freezeAxis)
			freezeXAxis = True if self.project.readEntry("TUVIEW", "freezexaxis{0}".format(suffix))[0] == 'True' else False
			viewToolbar.freezeXAxisAction.setChecked(freezeXAxis)
			freezeYAxis = True if self.project.readEntry("TUVIEW", "freezeyaxis{0}".format(suffix))[0] == 'True' else False
			viewToolbar.freezeYAxisAction.setChecked(freezeYAxis)
			legend = True if self.project.readEntry("TUVIEW", "legend{0}".format(suffix))[0] == 'True' else False
			viewToolbar.legendMenu.menuAction().setChecked(legend)
			legendPos = int(self.project.readEntry("TUVIEW", "legendpos{0}".format(suffix))[0])
			viewToolbar.legendPosChanged(None, index=legendPos)
		
			xmin = float(self.project.readEntry("TUVIEW", 'xmin{0}'.format(suffix))[0])
			xmax = float(self.project.readEntry("TUVIEW", 'xmax{0}'.format(suffix))[0])
			xlim = (xmin, xmax)
			ymin = float(self.project.readEntry("TUVIEW", 'ymin{0}'.format(suffix))[0])
			ymax = float(self.project.readEntry("TUVIEW", 'ymax{0}'.format(suffix))[0])
			ylim = (ymin, ymax)
			isSecondary = True if self.project.readEntry("TUVIEW", "issecondary{0}".format(suffix))[0] == "True" else False
			if isSecondary:
				subplot2 = self.tuView.tuPlot.getSecondaryAxis(plotNo)
				ymin2 = float(self.project.readEntry("TUVIEW", 'ymin2{0}'.format(suffix))[0])
				ymax2 = float(self.project.readEntry("TUVIEW", 'ymax2{0}'.format(suffix))[0])
				ylim2 = (ymin2, ymax2)
			
			if freezeAxis:
				subplot.set_xlim(xlim)
				subplot.set_ylim(ylim)
				if isSecondary:
					subplot2.set_ylim(ylim2)
			elif freezeXAxis:
				subplot.set_xlim(xlim)
			elif freezeYAxis:
				subplot.set_ylim(ylim)
				if isSecondary:
					subplot2.set_ylim(ylim2)
			
	def processPlotConfiguration(self, call_type):
		"""Project settings for plot configurations"""
		
		frozenTSProperties = self.tuView.tuPlot.frozenTSProperties
		frozenLPProperties = self.tuView.tuPlot.frozenLPProperties
		frozenCSProperties = self.tuView.tuPlot.frozenCSProperties
		frozenVPProperties = self.tuView.tuPlot.frozenVPProperties
		frozenTSAxisLabels = self.tuView.tuPlot.frozenTSAxisLabels
		frozenLPAxisLabels = self.tuView.tuPlot.frozenLPAxisLabels
		frozenCSAxisLabels = self.tuView.tuPlot.frozenCSAxisLabels
		frozenVPAxisLabels = self.tuView.tuPlot.frozenVPAxisLabels

		if call_type == 'save':
			self.savePlot(frozenTSProperties, frozenTSAxisLabels, 'ts')
			self.savePlot(frozenLPProperties, frozenLPAxisLabels, 'lp')
			self.savePlot(frozenCSProperties, frozenCSAxisLabels, 'cs')
			self.savePlot(frozenVPProperties, frozenVPAxisLabels, 'vp')
		else:  # load
			try:
				self.loadPlot(frozenTSProperties, frozenTSAxisLabels, 'ts')
			except:
				pass
			try:
				self.loadPlot(frozenLPProperties, frozenLPAxisLabels, 'lp')
			except:
				pass
			try:
				self.loadPlot(frozenCSProperties, frozenCSAxisLabels, 'cs')
			except:
				pass
			try:
				self.loadPlot(frozenVPProperties, frozenVPAxisLabels, 'vp')
			except:
				pass
		
	def savePlot(self, properties, labels, suffix):
		autoLabels = ''
		userLabels = ''
		userColorTypes = ''
		userColors = ''
		userLineWidths = ''
		userLineStyles = ''
		userDrawStyles = ''
		userMarkers = ''
		userMarkerSizes = ''
		userMarkerEdgeColorTypes = ''
		userMarkerEdgeColors = ''
		userMarkerFaceColorTypes = ''
		userMarkerFaceColors = ''
		for i, (autoLabel, property) in enumerate(properties.items()):
			if i == 0:
				autoLabels += '{0}'.format(autoLabel)
				userLabels += '{0}'.format(property[0])
				if type(property[1]) is dict:
					color = property[1]['color']
					if type(color) is str:
						userColorTypes += 'string'  # either name or hex
					else:
						userColorTypes += 'tuple'  # rgba
					userColors += '{0}'.format(color)
					userLineWidths += '{0}'.format(property[1]['linewidth'])
					userLineStyles += '{0}'.format(property[1]['linestyle'])
					userDrawStyles += '{0}'.format(property[1]['drawstyle'])
					userMarkers += '{0}'.format(property[1]['marker'])
					userMarkerSizes += '{0}'.format(property[1]['markersize'])
					edgeColor = property[1]['markeredgecolor']
					if type(edgeColor) is str:
						userMarkerEdgeColorTypes += 'string'  # either name or hex
					else:
						userMarkerEdgeColorTypes += 'tuple'  # rgba
					userMarkerEdgeColors += '{0}'.format(edgeColor)
					faceColor = property[1]['markerfacecolor']
					if type(faceColor) is str:
						userMarkerFaceColorTypes += 'string'  # either name or hex
					else:
						userMarkerFaceColorTypes += 'tuple'  # rgba
					userMarkerFaceColors += '{0}'.format(faceColor)
				else:
					color = property[1].get_color()
					if type(color) is str:
						userColorTypes += 'string'  # either name or hex
					else:
						userColorTypes += 'tuple'  # rgba
					userColors += '{0}'.format(color)
					userLineWidths += '{0}'.format(property[1].get_linewidth())
					userLineStyles += '{0}'.format(property[1].get_linestyle())
					userDrawStyles += '{0}'.format(property[1].get_drawstyle())
					userMarkers += '{0}'.format(property[1].get_marker())
					userMarkerSizes += '{0}'.format(property[1].get_markersize())
					edgeColor = property[1].get_markeredgecolor()
					if type(edgeColor) is str:
						userMarkerEdgeColorTypes += 'string'  # either name or hex
					else:
						userMarkerEdgeColorTypes += 'tuple'  # rgba
					userMarkerEdgeColors += '{0}'.format(edgeColor)
					faceColor = property[1].get_markerfacecolor()
					if type(faceColor) is str:
						userMarkerFaceColorTypes += 'string'  # either name or hex
					else:
						userMarkerFaceColorTypes += 'tuple'  # rgba
					userMarkerFaceColors += '{0}'.format(faceColor)
			else:
				autoLabels += '~~{0}'.format(autoLabel)
				userLabels += '~~{0}'.format(property[0])
				if type(property[1]) is dict:
					color = property[1]['color']
					if type(color) is str:
						userColorTypes += '~~string'  # either name or hex
					else:
						userColorTypes += '~~tuple'  # rgba
					userColors += '~~{0}'.format(color)
					userLineWidths += '~~{0}'.format(property[1]['linewidth'])
					userLineStyles += '~~{0}'.format(property[1]['linestyle'])
					userDrawStyles += '~~{0}'.format(property[1]['drawstyle'])
					userMarkers += '~~{0}'.format(property[1]['marker'])
					userMarkerSizes += '~~{0}'.format(property[1]['markersize'])
					edgeColor = property[1]['markeredgecolor']
					if type(edgeColor) is str:
						userMarkerEdgeColorTypes += '~~string'  # either name or hex
					else:
						userMarkerEdgeColorTypes += '~~tuple'  # rgba
					userMarkerEdgeColors += '~~{0}'.format(edgeColor)
					faceColor = property[1]['markerfacecolor']
					if type(faceColor) is str:
						userMarkerFaceColorTypes += '~~string'  # either name or hex
					else:
						userMarkerFaceColorTypes += '~~tuple'  # rgba
					userMarkerFaceColors += '~~{0}'.format(faceColor)
				else:
					color = property[1].get_color()
					if type(color) is str:
						userColorTypes += '~~string'  # either name or hex
					else:
						userColorTypes += '~~tuple'  # rgba
					userColors += '~~{0}'.format(color)
					userLineWidths += '~~{0}'.format(property[1].get_linewidth())
					userLineStyles += '~~{0}'.format(property[1].get_linestyle())
					userDrawStyles += '~~{0}'.format(property[1].get_drawstyle())
					userMarkers += '~~{0}'.format(property[1].get_marker())
					userMarkerSizes += '~~{0}'.format(property[1].get_markersize())
					edgeColor = property[1].get_markeredgecolor()
					if type(edgeColor) is str:
						userMarkerEdgeColorTypes += '~~string'  # either name or hex
					else:
						userMarkerEdgeColorTypes += '~~tuple'  # rgba
					userMarkerEdgeColors += '~~{0}'.format(edgeColor)
					faceColor = property[1].get_markerfacecolor()
					if type(faceColor) is str:
						userMarkerFaceColorTypes += '~~string'  # either name or hex
					else:
						userMarkerFaceColorTypes += '~~tuple'  # rgba
					userMarkerFaceColors += '~~{0}'.format(faceColor)
		self.project.writeEntry("TUVIEW", "autolabels{0}".format(suffix), autoLabels)
		self.project.writeEntry("TUVIEW", "userlabels{0}".format(suffix), userLabels)
		self.project.writeEntry("TUVIEW", "usercolortypes{0}".format(suffix), userColorTypes)
		self.project.writeEntry("TUVIEW", "usercolors{0}".format(suffix), userColors)
		self.project.writeEntry("TUVIEW", "userlinewidths{0}".format(suffix), userLineWidths)
		self.project.writeEntry("TUVIEW", "userlinestyles{0}".format(suffix), userLineStyles)
		self.project.writeEntry("TUVIEW", "userdrawstyles{0}".format(suffix), userDrawStyles)
		self.project.writeEntry("TUVIEW", "usermarkers{0}".format(suffix), userMarkers)
		self.project.writeEntry("TUVIEW", "usermarkersizes{0}".format(suffix), userMarkerSizes)
		self.project.writeEntry("TUVIEW", "usermarkeredgecolortypes{0}".format(suffix), userMarkerEdgeColorTypes)
		self.project.writeEntry("TUVIEW", "usermarkeredgecolors{0}".format(suffix), userMarkerEdgeColors)
		self.project.writeEntry("TUVIEW", "usermarkerfacecolortypes{0}".format(suffix), userMarkerFaceColorTypes)
		self.project.writeEntry("TUVIEW", "usermarkerfacecolors{0}".format(suffix), userMarkerFaceColors)
		
		autoAxisLabels = ''
		userAxisLabels = ''
		for i, (autoAxisLabel, userAxisLabel) in enumerate(labels.items()):
			if i == 0:
				autoAxisLabels += autoAxisLabel
				userAxisLabels += userAxisLabel
			else:
				autoAxisLabels += '~~{0}'.format(autoAxisLabel)
				userAxisLabels += '~~{0}'.format(userAxisLabel)
		self.project.writeEntry("TUVIEW", "autoaxislabels{0}".format(suffix), autoAxisLabels)
		self.project.writeEntry("TUVIEW", "useraxislabels{0}".format(suffix), userAxisLabels)
	
	def loadPlot(self, properties, labels, suffix):
		try:
			autoLabels = self.project.readEntry("TUVIEW", "autolabels{0}".format(suffix))[0]
			autoLabels = autoLabels.split('~~')
			if autoLabels:
				if autoLabels[0] == '':
					autoLabels.clear()

			userLabels = self.project.readEntry("TUVIEW", "userlabels{0}".format(suffix))[0]
			userLabels = userLabels.split('~~')

			colorTypes = self.project.readEntry("TUVIEW", "usercolortypes{0}".format(suffix))[0]
			colorTypes = colorTypes.split('~~')
			colors = self.project.readEntry("TUVIEW", "usercolors{0}".format(suffix))[0]
			colors = colors.split('~~')
			userColors = []
			for i, c in enumerate(colors):
				if colorTypes[i] == 'tuple':
					d = c.strip('(').strip(')')
					d = d.strip("'")
					d = d.strip('"')
					d = d.split(',')
					e = []
					for f in d:
						f = f.strip()
						e.append(float(f))
					g = tuple(e)
					userColors.append(g)
				else:
					userColors.append(c)

			lw = self.project.readEntry("TUVIEW", "userlinewidths{0}".format(suffix))[0]
			lw = lw.split('~~')
			userLineWidths = []
			for a in lw:
				if a != '':
					userLineWidths.append(float(a))

			userLineStyles = self.project.readEntry("TUVIEW", "userlinestyles{0}".format(suffix))[0]
			userLineStyles = userLineStyles.split('~~')

			userDrawStyles = self.project.readEntry("TUVIEW", "userdrawstyles{0}".format(suffix))[0]
			userDrawStyles = userDrawStyles.split('~~')

			userMarkers = self.project.readEntry("TUVIEW", "usermarkers{0}".format(suffix))[0]
			userMarkers = userMarkers.split('~~')

			ms = self.project.readEntry("TUVIEW", "usermarkersizes{0}".format(suffix))[0]
			ms = ms.split('~~')
			userMarkerSizes = []
			for a in ms:
				if a != '':
					userMarkerSizes.append(float(a))

			edgeColorTypes = self.project.readEntry("TUVIEW", "usermarkeredgecolortypes{0}".format(suffix))[0]
			edgeColorTypes = edgeColorTypes.split('~~')
			edgeColor = self.project.readEntry("TUVIEW", "usermarkeredgecolors{0}".format(suffix))[0]
			edgeColor = edgeColor.split('~~')
			userMarkerEdgeColors = []
			for i, c in enumerate(edgeColor):
				if edgeColorTypes[i] == 'tuple':
					d = c.strip('(').strip(')')
					d = d.strip("'")
					d = d.strip('"')
					d = d.split(',')
					e = []
					for f in d:
						f = f.strip()
						e.append(float(f))
					g = tuple(e)
					userMarkerEdgeColors.append(g)
				else:
					userMarkerEdgeColors.append(c)

			faceColorTypes = self.project.readEntry("TUVIEW", "usermarkerfacecolortypes{0}".format(suffix))[0]
			faceColorTypes = faceColorTypes.split('~~')
			faceColor = self.project.readEntry("TUVIEW", "usermarkerfacecolors{0}".format(suffix))[0]
			faceColor = faceColor.split('~~')
			userMarkerFaceColors = []
			for i, c in enumerate(faceColor):
				if faceColorTypes[i] == 'tuple':
					d = c.strip('(').strip(')')
					d = d.strip("'")
					d = d.strip('"')
					d = d.split(',')
					e = []
					for f in d:
						f = f.strip()
						e.append(float(f))
					g = tuple(e)
					userMarkerFaceColors.append(g)
				else:
					userMarkerFaceColors.append(c)

			for i, autoLabel in enumerate(autoLabels):
				style = {
					'color': userColors[i],
					'linewidth': userLineWidths[i],
					'linestyle': userLineStyles[i],
					'drawstyle': userDrawStyles[i],
					'marker': userMarkers[i],
					'markersize': userMarkerSizes[i],
					'markeredgecolor': userMarkerEdgeColors[i],
					'markerfacecolor': userMarkerFaceColors[i]
				}
				property = [userLabels[i], style]
				properties[autoLabel] = property

			autoAxisLabels = self.project.readEntry("TUVIEW", "autoaxislabels{0}".format(suffix))[0]
			autoAxisLabels = autoAxisLabels.split('~~')
			userAxisLabels = self.project.readEntry("TUVIEW", "useraxislabels{0}".format(suffix))[0]
			userAxisLabels = userAxisLabels.split('~~')

			for i, autoAxisLabel in enumerate(autoAxisLabels):
				labels[autoAxisLabel] = userAxisLabels[i]
		except:
			pass
			
	def processGraphics(self, call_type):
		"""Graphic objects in the project."""

		points = self.tuView.tuPlot.tuTSPoint.points
		markers = self.tuView.tuPlot.tuTSPoint.markers
		
		linesCS = self.tuView.tuPlot.tuCrossSection.rubberBands
		lineMarkersCS = self.tuView.tuPlot.tuCrossSection.linePoints
		linePointsCS = self.tuView.tuPlot.tuCrossSection.points
		
		linesQ = self.tuView.tuPlot.tuFlowLine.rubberBands
		lineMarkersQ = self.tuView.tuPlot.tuFlowLine.linePoints
		linePointsQ = self.tuView.tuPlot.tuFlowLine.points
		
		if call_type == 'save':
			self.savePoints(points)
			self.saveLines(linesCS, 'cs')
			self.saveLines(linesQ, 'q')
		else:  # load
			self.loadPoints(points, markers)
			self.loadLines(linesCS, linePointsCS, lineMarkersCS, 'cs')
			self.loadLines(linesQ, linePointsQ, lineMarkersQ, 'q')
		
	def savePoints(self, points):
		x = ''
		y = ''
		for i, point in enumerate(points):
			if i == 0:
				x += '{0}'.format(point.x())
				y += '{0}'.format(point.y())
			else:
				x += '~~{0}'.format(point.x())
				y += '~~{0}'.format(point.y())
		self.project.writeEntry("TUVIEW", "pointsx", x)
		self.project.writeEntry("TUVIEW", "pointsy", y)
		
	def loadPoints(self, points, markers):

		try:
			a = self.project.readEntry("TUVIEW", "pointsx")[0]
			if a:
				a = a.split('~~')
				b = self.project.readEntry("TUVIEW", "pointsy")[0]
				b = b.split('~~')
				for i in range(len(a)):
					x = float(a[i])
					y = float(b[i])
					point = QgsPointXY(x, y)
					points.append(point)
					marker = QgsVertexMarker(self.tuView.canvas)
					marker.setColor(Qt.red)
					marker.setFillColor(Qt.red)
					marker.setIconSize(10)
					marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
					marker.setCenter(QgsPointXY(point))
					markers.append(marker)
		except:
			pass
			
	def saveLines(self, lines, suffix):
		i = -1
		for i, line in enumerate(lines):
			x = ''
			y = ''
			geom = line.asGeometry().asPolyline()
			for j, p in enumerate(geom):
				if j == 0:
					x += '{0}'.format(p.x())
					y += '{0}'.format(p.y())
				else:
					x += '~~{0}'.format(p.x())
					y += '~~{0}'.format(p.y())
			self.project.writeEntry("TUVIEW", 'lines{0}x{1}'.format(suffix, i), x)
			self.project.writeEntry("TUVIEW", 'lines{0}y{1}'.format(suffix, i), y)
		self.project.writeEntry("TUVIEW", "lines{0}no".format(suffix), i + 1)
		
	def loadLines(self, lines, points, markers, suffix):
		try:
			no = self.project.readEntry("TUVIEW", "lines{0}no".format(suffix))[0]
			if no:
				no = int(no)
				for i in range(no):
					a = self.project.readEntry("TUVIEW", 'lines{0}x{1}'.format(suffix, i))[0]
					a = a.split('~~')
					b = self.project.readEntry("TUVIEW", 'lines{0}y{1}'.format(suffix, i))[0]
					b = b.split('~~')
					points.clear()
					for j in range(len(a)):
						x = float(a[j])
						y = float(b[j])
						point = QgsPoint(x, y)
						points.append(point)
						if i + 1 == no:
							marker = QgsVertexMarker(self.tuView.canvas)
							if suffix == 'cs':
								marker.setColor(Qt.red)
								marker.setIconSize(10)
								marker.setIconType(QgsVertexMarker.ICON_BOX)
							else:  # 'q'
								marker.setColor(Qt.blue)
								marker.setIconSize(12)
								marker.setIconType(QgsVertexMarker.ICON_DOUBLE_TRIANGLE)
							marker.setCenter(QgsPointXY(point))
							markers.append(marker)
					line = QgsRubberBand(self.tuView.canvas, False)
					line.setWidth(2)
					if suffix == 'cs':
						line.setColor(QColor(Qt.red))
					else:  # 'q'
						line.setColor(QColor(Qt.blue))
					line.setToGeometry(QgsGeometry.fromPolyline(points), None)
					lines.append(line)
		except:
			pass
	
	def processUserPlotData(self, call_type):
		"""Save user plot data to Project."""
		
		data = self.tuView.tuPlot.userPlotData
		
		if call_type == 'save':
			data.saveProject(self.project)
		else:
			try:
				data.loadProject(self.project)
			except:
				pass
			
	def processShowActiveTime(self, call_type):
		"""Save check box for show active time to Project"""
		
		cb = self.tuView.cbShowCurrentTime
		
		if call_type == 'save':
			self.project.writeEntry("TUVIEW", "showcurrenttime", str(cb.isChecked()))
		else:
			checked = True if self.project.readEntry("TUVIEW", "showcurrenttime")[0] == 'True' else False
			cb.setChecked(checked)
			