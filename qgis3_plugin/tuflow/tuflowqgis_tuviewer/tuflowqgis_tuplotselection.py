


class TuPlotSelection():
	"""
	Class for handling plotting selected vector layers.
	
	"""
	
	def __init__(self, TuPlot):
		self.tuPlot = TuPlot
		self.iface = TuPlot.iface
	
	def plotTimeSeries(self, layer):
		"""
		Plot time series from selected points

		:param layer: QgsVectorLayer
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuPlot.tuPlot2D.plotSelectionPointFeat = []  # clear selected feature for plotting list
		
		sel = layer.selectedFeatures()
		multi = False
		if len(sel) > 1:
			multi = True
		for i, f in enumerate(sel):
			if i == 0:
				self.tuPlot.clearPlot(0, retain_1d=True, retain_flow=True)  # clear plot
				self.tuPlot.tuPlot2D.resetMultiPointCount()
				self.tuPlot.tuPlot2D.plotTimeSeriesFromMap(layer, f.geometry().asPoint(), bypass=multi)
			else:
				self.tuPlot.tuPlot2D.plotTimeSeriesFromMap(layer, f.geometry().asPoint(), bypass=multi)
			self.tuPlot.tuPlot2D.plotSelectionPointFeat.append(f)
		
		self.tuPlot.tuPlot2D.reduceMultiPointCount(1)  # have to minus 1 off to make it count properly
		self.tuPlot.holdTimeSeriesPlot = True
		self.tuPlot.timeSeriesPlotFirst = False
		
		# unpress button
		self.tuPlot.tuPlotToolbar.plotTSMenu.menuAction().setChecked(False)
		
		return True
	
	def plotCrossSection(self, layer):
		"""
		Plot cross section or long profile from selected polyline

		:param layer: QgsVectorLayer
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuPlot.tuPlot2D.plotSelectionLineFeat = []  # clear selected feature for plotting list
		
		sel = layer.selectedFeatures()
		multi = False
		if len(sel) > 1:
			multi = True
		for i, f in enumerate(sel):
			if i == 0:
				self.tuPlot.clearPlot(1, retain_1d=True, retain_flow=True)  # clear plot
				self.tuPlot.tuPlot2D.resetMultiLineCount()
				self.tuPlot.tuPlot2D.plotCrossSectionFromMap(layer, f, bypass=multi)
			else:
				self.tuPlot.tuPlot2D.plotCrossSectionFromMap(layer, f, bypass=multi)
			self.tuPlot.tuPlot2D.plotSelectionLineFeat.append(f)
		
		self.tuPlot.tuPlot2D.reduceMultiLineCount(1)  # have to minus 1 off to make it count properly
		self.tuPlot.profilePlotFirst = False
		
		# unpress button
		self.tuPlot.tuPlotToolbar.plotLPMenu.menuAction().setChecked(False)
		
		return True
	
	def plotFlow(self, layer):
		"""
		Plot flow from selected line.
		
		:param layer: QgsVectorLayer
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuPlot.tuPlot2D.plotSelectionFlowFeat = []
		
		sel = layer.selectedFeatures()
		multi = False
		if len(sel) > 1:
			multi = True
		for i, f in enumerate(sel):
			if i == 0:
				self.tuPlot.clearPlot(1, retain_1d=True, retain_2d=True)  # clear plot
				self.tuPlot.tuPlot2D.resetMultiFlowLineCount()
				self.tuPlot.tuPlot2D.plotFlowFromMap(layer, f, bypass=multi)
			else:
				self.tuPlot.tuPlot2D.plotFlowFromMap(layer, f, bypass=multi)
			self.tuPlot.tuPlot2D.plotSelectionFlowFeat.append(f)
		
		self.tuPlot.tuPlot2D.reduceMultiFlowLineCount(1)  # have to minus 1 off to make it count properly
		self.tuPlot.profilePlotFirst = False
		
		# unpress button
		self.tuPlot.tuPlotToolbar.plotFluxButton.setChecked(False)
		
		return True
	
	def useSelection(self, plotNo, **kwargs):
		"""
		Use selected features for plotting.
		
		:param kwargs: -> dict key word arguments
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		plotType = kwargs['type'] if 'type' in kwargs.keys() else 'standard'
		
		plot = False
		layer = self.iface.activeLayer()
		
		# check that there is an active layer
		if layer is not None:
			
			# check that layer is vector type
			if layer.type() == 0:
				
				# check geometry type i.e. point, line
				if plotNo == 0:
					if layer.geometryType() == 0:
						plot = self.plotTimeSeries(layer)
					elif layer.geometryType() == 1:
						if plotType == 'flow':
							plot = self.plotFlow(layer)
				elif plotNo == 1:
					if layer.geometryType() == 1:
						plot = self.plotCrossSection(layer)
		
		self.tuPlot.plotSelectionPoint = True
		
		return plot