from qgis.core import QgsWkbTypes, QgsVectorLayer


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

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot
		
		self.tuPlot.tuPlot2D.plotSelectionPointFeat = []  # clear selected feature for plotting list
		
		sel = layer.selectedFeatures()
		multi = False
		if len(sel) > 1:
			multi = True
		for i, f in enumerate(sel):
			# get feature name from attribute
			iFeatName = int(self.tuPlot.tuView.tuOptions.iLabelField)
			if len(f.attributes()) > iFeatName:
				featName = f.attributes()[iFeatName]
			else:
				featName = None

			if i == 0:
				# self.tuPlot.clearPlot(0, retain_1d=True, retain_flow=True)  # clear plot
				self.tuPlot.clearPlot2(TuPlot.TimeSeries, TuPlot.DataTimeSeries2D)  # clear plot
				self.tuPlot.tuPlot2D.resetMultiPointCount()
				self.tuPlot.tuPlot2D.plotTimeSeriesFromMap(layer, f.geometry().asPoint(), bypass=multi,
				                                           featName=featName, markerNo=i+1)
			else:
				self.tuPlot.tuPlot2D.plotTimeSeriesFromMap(layer, f.geometry().asPoint(), bypass=multi,
				                                           featName=featName, markerNo=i+1)
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

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot
		
		self.tuPlot.tuPlot2D.plotSelectionLineFeat = []  # clear selected feature for plotting list
		
		sel = layer.selectedFeatures()
		multi = False
		if len(sel) > 1:
			multi = True
		for i, f in enumerate(sel):
			# get feature name from attribute
			iFeatName = self.tuPlot.tuView.tuOptions.iLabelField
			if len(f.attributes()) > iFeatName:
				featName = f.attributes()[iFeatName]
			else:
				featName = None

			if i == 0:
				# self.tuPlot.clearPlot(1, retain_1d=True, retain_flow=True)  # clear plot
				self.tuPlot.clearPlot2(TuPlot.CrossSection, TuPlot.DataCrossSection2D)  # clear plot
				self.tuPlot.tuPlot2D.resetMultiLineCount()
				self.tuPlot.tuPlot2D.plotCrossSectionFromMap(layer, f, bypass=multi, featName=featName, lineNo=i+1)
			else:
				self.tuPlot.tuPlot2D.plotCrossSectionFromMap(layer, f, bypass=multi, featName=featName, lineNo=i+1)
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

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		self.tuPlot.tuPlot2D.plotSelectionFlowFeat = []
		
		sel = layer.selectedFeatures()
		multi = False
		if len(sel) > 1:
			multi = True
		for i, f in enumerate(sel):
			# get feature name from attribute
			iFeatName = self.tuPlot.tuView.tuOptions.iLabelField
			if len(f.attributes()) > iFeatName:
				featName = f.attributes()[iFeatName]
			else:
				featName = None

			if i == 0:
				if self.tuPlot.timeSeriesPlotFirst:  # first plot so need to remove test line
					self.tuPlot.clearPlot2(TuPlot.TimeSeries, TuPlot.DataFlow2D)
					self.tuPlot.timeSeriesPlotFirst = False
				else:
					# self.tuPlot.clearPlot(0, retain_1d=True, retain_2d=True)  # clear plot
					self.tuPlot.clearPlot2(TuPlot.TimeSeries, TuPlot.DataFlow2D)
				self.tuPlot.tuPlot2D.resetMultiFlowLineCount()
				self.tuPlot.tuPlot2D.plotFlowFromMap(layer, f, bypass=multi, featName=featName)
			else:
				self.tuPlot.tuPlot2D.plotFlowFromMap(layer, f, bypass=multi, featName=featName)
			self.tuPlot.tuPlot2D.plotSelectionFlowFeat.append(f)
		
		self.tuPlot.tuPlot2D.reduceMultiFlowLineCount(1)  # have to minus 1 off to make it count properly
		self.tuPlot.profilePlotFirst = False
		
		# unpress button
		self.tuPlot.tuPlotToolbar.plotFluxButton.setChecked(False)
		
		return True

	def plotCurtain(self, layer):
		"""
		Plot flow from selected line.

		:param layer: QgsVectorLayer
		:return: bool -> True for successful, False for unsuccessful
		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		self.tuPlot.tuPlot3D.plotSelectionCurtainFeat = []

		sel = layer.selectedFeatures()
		multi = False
		if len(sel) > 1:
			multi = True
		for i, f in enumerate(sel):
			# get feature name from attribute
			iFeatName = self.tuPlot.tuView.tuOptions.iLabelField
			if len(f.attributes()) > iFeatName:
				featName = f.attributes()[iFeatName]
			else:
				featName = None

			if i == 0:
				self.tuPlot.clearPlot2(TuPlot.TimeSeries, TuPlot.DataFlow2D)

			self.tuPlot.tuPlot3D.plotCurtainFromMap(layer, f, bypass=multi, featName=featName)
			self.tuPlot.tuPlot3D.plotSelectionCurtainFeat.append(f)

		self.tuPlot.profilePlotFirst = False

		# unpress button
		self.tuPlot.tuPlotToolbar.curtainPlotMenu.menuAction().setChecked(False)

		return True
	
	def useSelection(self, dataType, **kwargs):
		"""
		Use selected features for plotting.
		
		:param kwargs: -> dict key word arguments
		:return: bool -> True for successful, False for unsuccessful
		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot
		
		plotType = kwargs['type'] if 'type' in kwargs.keys() else 'standard'
		
		plot = False
		layer = self.iface.activeLayer()
		
		# check that there is an active layer
		if layer is not None:
			
			# check that layer is vector type
			if isinstance(layer, QgsVectorLayer):
				
				# check geometry type i.e. point, line
				if dataType == TuPlot.DataTimeSeries2D:
					if layer.geometryType() == QgsWkbTypes.PointGeometry:
						plot = self.plotTimeSeries(layer)
				elif dataType == TuPlot.DataCrossSection2D:
					if layer.geometryType() == QgsWkbTypes.LineGeometry:
						plot = self.plotCrossSection(layer)
				elif dataType == TuPlot.DataFlow2D:
					if layer.geometryType() == QgsWkbTypes.LineGeometry:
						plot = self.plotFlow(layer)
				elif dataType == TuPlot.DataCurtainPlot:
					if layer.geometryType() == QgsWkbTypes.LineGeometry:
						plot = self.plotCurtain(layer)
		
		self.tuPlot.plotSelectionPoint = True
		
		return plot

	def clearSelection(self, dataType):
		"""

		"""

		from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuplot import TuPlot

		if dataType == TuPlot.DataTimeSeries2D:
			self.tuPlot.tuPlot2D.plotSelectionPointFeat.clear()
		elif dataType == TuPlot.DataCrossSection2D:
			self.tuPlot.tuPlot2D.plotSelectionLineFeat.clear()
		elif dataType == TuPlot.DataFlow2D:
			self.tuPlot.tuPlot2D.plotSelectionFlowFeat.clear()
		elif dataType == TuPlot.DataCurtainPlot:
			self.tuPlot.tuPlot3D.plotSelectionCurtainFeat.clear()