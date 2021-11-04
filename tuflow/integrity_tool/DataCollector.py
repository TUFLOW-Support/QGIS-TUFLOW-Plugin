import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.gui import *
from PyQt5.QtWidgets import *
from .Enumerators import *
from .FeatureData import FeatureData
from .DrapeData import DrapeData
from .ConnectionData import ConnectionData
from .NetworkVertex import NetworkVertex
from tuflow.tuflowqgis_library import tuflowqgis_find_layer, is1dNetwork, lineToPoints, getRasterValue, readInvFromCsv
from datetime import datetime, timedelta


import sys
sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2020.3.1\debug-eggs')
sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2020.3.1\plugins\python\helpers\pydev')


class DataCollector(QObject):
    """
    Class for collecting 1D network input data.
    Input Data includes all useful attribute information,
    draped data from DEM, and connectivity.

    Inherits from QObject so it can make use of signals
    and QThread which means that a parent dialog can
    use a progress bar.

    """

    # add some custom signals for progress bar
    updated = pyqtSignal()
    finished = pyqtSignal(QObject)

    def __init__(self, iface=None):
        # initialise inherited classes
        QObject.__init__(self, parent=None)

        # custom initialisations
        # start with QgsInterface
        self.iface = iface
        self.errMessage = None

        # list of all input files
        self.geomType = GEOM_TYPE.Null
        self.inputs = []  # str file names
        self.lines = []

        # some metadata on the input files
        self.inputFilePaths = {}  # key str input layer nam: value str full file path
        self.fileSaveDates = {}  # key str input layer nam: value file save date
        self.inputLinesFilePaths = {}
        self.lineSaveDates = {}
        self.demFilePaths = {}  # key str dem name: dem file path
        self.demSaveDates = {}  # key str dem name: dem save date

        # feature data
        self.nullCounter = 1  # used when feature ID is NULL e.g. x connectors or NODES
        self.ids = []  # str ID, if no ID (e.g. x connector) use a null counter to give a unique ID
        self.features = {}  # key str ID: value QgsFeature
        self.drapes = {}
        self.connections = {}
        self.feature2id = {}  # key QgsFeature: value str ID
        self.vertexes = {}
        self.unsnappedVertexes = []
        self.allFeatures = {}
        self.spatialIndexes = {}
        
        # tables
        self.allTableFeatures = {}
        self.indexedTables = {}
        
        # some stuff for flow trace
        self.featuresToAssess = []
        self.featuresAssessed = []
        self.layersToAssess = []

    def collectData(self, inputs=(), dem=None, lines=(), lineDataCollector=None, exclRadius=15, tables=(),
                    startLocs=(), flowTrace=False):
        """
        Primary function.

        Collect data from the input layers to use in the integrity tool. Using dictionaries
        and an object orientated approach hopefully speeds things up when retrieving data later
        and makes the code more readable.

        :param inputs: list -> str layer name
        :param dem: QgsRaterLayer
        :param lines: list -> QgsVectorLayer line inputs
        :param lineDataCollector: DataCollector
        :param exclRadius: float
        :param tables: list -> QgsVectorLayer
        :param startLocs: list -> list -> (layer name, fid)
        :param flowTrace: bool
        :return: void
        """
        
        # if inputs have been run through data collector already
        # and nothing has changed then we don't need to run it again
        #if not self.hasAlreadyRun(inputs, dem, lines):
        # clear inputs and metadata so we don't get a build up of old inputs
        self.inputs.clear()
        self.inputFilePaths.clear()
        self.fileSaveDates.clear()
        self.demFilePaths.clear()
        self.demSaveDates.clear()
        self.nullCounter = 1  # used when feature ID is NULL e.g. x connectors or NODES
        self.ids.clear()  # str ID, if no ID (e.g. x connector) use a null counter to give a unique ID
        self.features.clear()  # key str ID: value QgsFeature
        self.drapes.clear()
        self.connections.clear()
        self.feature2id.clear()  # key QgsFeature: value str ID
        self.vertexes.clear()
        self.unsnappedVertexes.clear()
        self.allFeatures.clear()
        self.hasStarted = False

        # loop through all inputs and start collecting
        #for layer in inputs:
            #if layer is not None:
        if inputs:
            if inputs[0].geometryType() == QgsWkbTypes.LineGeometry:
                self.geomType = GEOM_TYPE.Line
            else:
                self.geomType = GEOM_TYPE.Point

        # check if layer is a 1d_nwk
        for layer in inputs:
            if is1dNetwork(layer):
                # start by indexing all fid and features
                if layer.name() in self.spatialIndexes:
                    spatialIndex = self.spatialIndexes[layer.name()]
                else:
                    spatialIndex = QgsSpatialIndex(layer)
                    self.spatialIndexes[layer.name()] = spatialIndex
                    # create dict of fid to QgsFeature
                    allFeatures = {f.id(): f for f in layer.getFeatures()}
                    self.allFeatures[layer.name()] = allFeatures
            
        # iterate through all features in layer
        # connectivity tool only works if X connectors are assessed first
        err = self.getFeaturesToAssess(inputs, startLocs, flowTrace, lines, lineDataCollector)
        if err:
            self.errMessage = err
            self.finished.emit(self)

        #key = lambda x: 0 if x.attribute(1).lower() == 'x' else 1
        #for f in sorted(layer.getFeatures(), key=key):
        for i, f in enumerate(self.featuresToAssess):
            layer = self.layersToAssess[i]
            # if flow trace, collect X connectors first but don't start tracing upstream
            # check if current feature is the start location - if yes start tracing upstream
            if not self.hasStarted:
                loc = (layer.name(), f.id())
                if loc in startLocs:
                    self.hasStarted = True
            
            # populate current feature information if haven't already
            id = self.getIdFromFid(layer.name(), f.id())
            if id is None:
                featureData = self.populateFeatureData(layer, f, dem)
                if self.errMessage is not None:
                    return
                id = featureData.id
            else:
                featureData = self.features[id]
                
            # collect data from tables i.e. 1d_xs
            for table in tables:
                self.collectTableData(table, featureData)
            # initialise some classes monitoring closest vertexes
            if self.geomType == GEOM_TYPE.Line:
                vname = '{0}{1}'.format(id, VERTEX.First)
                if vname in self.vertexes:
                    closestVertexToUs = self.vertexes[vname]
                else:
                    closestVertexToUs = NetworkVertex(id, VERTEX.First, layer, f)
                    self.vertexes[vname] = closestVertexToUs
                vname = '{0}{1}'.format(id, VERTEX.Last)
                if vname in self.vertexes:
                    closestVertexToDs = self.vertexes[vname]
                else:
                    closestVertexToDs = NetworkVertex(id, VERTEX.Last, layer, f)
                    self.vertexes[vname] = closestVertexToDs
            else:
                if id in self.vertexes:
                    closestVertexToUs = self.vertexes[id]
                else:
                    closestVertexToUs = NetworkVertex(id, VERTEX.Point, layer, f)
                    self.vertexes[id] = closestVertexToUs
                closestVertexToDs = None
            
            # create buffer object then find features in buffered region
            request = self.createRequest(featureData, exclRadius)
            if lines and self.geomType == GEOM_TYPE.Point:
                # if lines have been input separately
                # inputs must be points - so check
                # snapping against lines not itself
                reqInputs = lines
            else:
                reqInputs = inputs

            snappedFeatures = []
            snappedLayers = []
            for reqLayer in reqInputs:
                if not lines:
                    if reqLayer.name() in self.spatialIndexes:
                        spatialIndex = self.spatialIndexes[reqLayer.name()]
                    else:
                        spatialIndex = QgsSpatialIndex(reqLayer)
                        self.spatialIndexes[reqLayer.name()] = spatialIndex
                else:
                    spatialIndex = lineDataCollector.spatialIndexes[reqLayer.name()]

                for fid in spatialIndex.intersects(request):
                    # create feature data object if not already done so
                    if lines and self.geomType == GEOM_TYPE.Point:
                        reqFeat = lineDataCollector.allFeatures[reqLayer.name()][fid]
                        # if checking against lines, need to get
                        # data from the line data collector
                        id = lineDataCollector.getIdFromFid(reqLayer.name(), reqFeat.id())
                        if flowTrace and id not in lineDataCollector.features:
                            continue
                        reqFeatData = lineDataCollector.features[id]
                        vertexes = lineDataCollector.vertexes
                    else:
                        if reqLayer.name() in self.allFeatures:
                            reqFeat = self.allFeatures[reqLayer.name()][fid]
                        else:
                            reqAllFeatures = {f.id(): f for f in reqLayer.getFeatures()}
                            self.allFeatures[reqLayer.name()] = reqAllFeatures
                            reqFeat = self.allFeatures[reqLayer.name()][fid]
                            
                        vertexes = None
                        id = self.getIdFromFid(reqLayer.name(), reqFeat.id())
                        if id is None:
                            reqFeatData = self.populateFeatureData(reqLayer, reqFeat, dem)
                            id = reqFeatData.id
                        else:
                            reqFeatData = self.features[id]

                    # check if the requested feature snaps to our current feature
                    if featureData.id != reqFeatData.id:
                        if self.isSnapped(featureData, reqFeatData):
                            # is snapped so need to work out if upstream or downstream
                            isUpstream = self.populateConnectionData(featureData, reqFeatData, lineDataCollector,
                                                                     closestVertexToUs, closestVertexToDs)
                            if self.hasStarted:
                                if isUpstream and not lines:
                                    snappedFeatures.append(reqFeat)
                                    snappedLayers.append(reqLayer)

                        # check how far away and update closest vertex info
                        self.updateVertexes(featureData, reqFeatData,
                                            closestVertexToUs, closestVertexToDs, vertexes)
            
            # call correction of some X connector information
            # that has to be called post everything else
            # being done - messy but it works
            if featureData.feature not in self.featuresAssessed:
                if featureData.id in self.connections:
                    connectionData = self.connections[featureData.id]
                    connectionData.correctConnectorUpstream()

            # check if there are any unsnapped vertexes in feature
            if not closestVertexToUs.snapped:
                self.unsnappedVertexes.append(closestVertexToUs)
                
                if self.geomType == GEOM_TYPE.Line:
                    # if unsnapped, do not consider closest vertexes that are snapped
                    # to the downstream end of the same pipe
                    if featureData.id in self.connections:
                        collectorData = self.connections[featureData.id]

                        if (closestVertexToUs.closestVertex is not None and
                                closestVertexToUs.closestVertex.id in collectorData.linesDs) or \
                                (closestVertexToUs.closestVertex is not None and
                                 closestVertexToUs.closestVertex.id in collectorData.linesDsDs):
                            closestVertexToUs.closestVertex = None
                            closestVertexToUs.distanceToClosest = 99999

            if self.geomType == GEOM_TYPE.Line:
                if not closestVertexToDs.snapped:
                    self.unsnappedVertexes.append(closestVertexToDs)
                    
                    # if unsnapped, do not consider closest vertexes that are snapped
                    # to the upstream end of the same pipe
                    if featureData.id in self.connections:
                        collectorData = self.connections[featureData.id]
                        if (closestVertexToDs.closestVertex is not None and
                                closestVertexToDs.closestVertex.id in collectorData.linesUs) or \
                                (closestVertexToDs.closestVertex is not None and
                                 closestVertexToDs.closestVertex.id in collectorData.linesUsUs):
                            closestVertexToDs.closestVertex = None
                            closestVertexToDs.distanceToClosest = 99999


            # make sure feature has a ConnectionData object
            if featureData.id not in self.connections:
                connectionData = ConnectionData(featureData.id)
                self.connections[featureData.id] = connectionData
            
            # do something since we've finished assessing feature
            self.finishedFeature(f, layer, snappedFeatures, snappedLayers)
            
            # let progress bar know we've finished one feature
            self.updated.emit()

        # save meta data for inputs so we can skip it
        # if it is called again and nothing has changed
        #self.saveMetadata(inputs, dem, lines)

        # emit finished signal for progress bar
        self.finished.emit(self)

    def populateFeatureData(self, layer, feature, dem):
        """
        Creates and populates FeatureData and DrapeData objects.
        Returns FeatureData object

        :param layer: QgsVectorLayer
        :param feature: QgsFeature
        :param dem: QgsRasterLayer
        :return: FeatureData
        """

        # create feature data object
        featureData = FeatureData(layer, feature, self.nullCounter)

        # store feature data in dictionary for easy lookup later
        id = featureData.id
        self.ids.append(id)
        self.features[id] = featureData

        # create an easy reference to go from layer and fid to user id
        if layer.name() not in self.feature2id:
            self.feature2id[layer.name()] = {}
        self.feature2id[layer.name()][feature.id()] = id

        # update null counter
        self.nullCounter = featureData.getNullCounter()

        # create drape data object and store in dict
        drapeData = DrapeData(self.iface, id, layer, feature, dem)
        if drapeData.error:
            self.errMessage = drapeData.message
            return
        self.drapes[id] = drapeData

        return featureData

    def populateConnectionData(self, featData1, featData2, lineDataCollector, vDataUs, vDataDs):
        """


        :param featData1:
        :param featData2:
        :return:
        """

        # create connection data object if not already done so
        id = featData1.id
        if id in self.connections:
            connectionData = self.connections[id]
        else:
            # Create our ConnectionData object if needed
            connectionData = ConnectionData(id)

        # if one of our features is an X connector
        # it's a special case and we need to work
        # out which direction is upstream
        if featData1.feature not in self.featuresAssessed:
            if '__connector__' in featData1.id:
                connectionData.getConnectorData(featData1, featData2, X_OBJECT.IsFirst, vDataUs=vDataUs, vDataDs=vDataDs)
            elif '__connector__' in featData2.id:
                if featData1.geomType == GEOM_TYPE.Point and featData2.geomType == GEOM_TYPE.Line:
                    connData2 = lineDataCollector.connections[featData2.id]
                else:
                    connData2 = self.connections[featData2.id]
                xIn = connData2.xIn
                connectionData.getConnectorData(featData1, featData2, X_OBJECT.IsSecond, xIn, self, vDataUs, vDataDs)
            else:
                # else it's just a normal connection
                # between 1d_nwk
                if featData1.geomType == GEOM_TYPE.Point and featData2.geomType == GEOM_TYPE.Line:
                    if featData2.id not in lineDataCollector.connections:
                        # this can happen when line is not connected to another line
                        # but is connected to a point - there will be no existing connection data
                        lineConnectionData = ConnectionData(featData2.id)
                        lineDataCollector.connections[featData2.id] = lineConnectionData
                    else:
                        lineConnectionData = lineDataCollector.connections[featData2.id]
                    connectionData.getData(featData1, featData2, lineConnectionData, vDataUs,
                                           dataCollectorLine=lineDataCollector)
                else:
                    connectionData.getData(featData1, featData2, vDataUs=vDataUs, vDataDs=vDataDs)

            # store connection data in a dictionary for easy reference later
            self.connections[featData1.id] = connectionData
        
        if featData2.id in connectionData.linesUs:
            return True
        else:
            return False

    def createRequest(self, featureData, buffer):
        """
        Create feature request for a buffer region around input feature

        :param featureData: FeatureData
        :param buffer: float
        :return: QgsFeatureRequest
        """

        xmin = min(featureData.startVertex.x(), featureData.endVertex.x()) - buffer
        xmax = max(featureData.startVertex.x(), featureData.endVertex.x()) + buffer
        ymin = min(featureData.startVertex.y(), featureData.endVertex.y()) - buffer
        ymax = max(featureData.startVertex.y(), featureData.endVertex.y()) + buffer

        rect = QgsRectangle(xmin, ymin, xmax, ymax)
        return rect
        #return QgsFeatureRequest().setFilterRect(rect)

    def isSnapped(self, featureData1, featureData2):
        """
        Checks if 2 input features are snapped.
        Returns:
        True if snapped
        False if not snapped

        :param featureData1: FeatureData
        :param featureData2: FeatureData
        :return: bool
        """

        if featureData1.geomType == GEOM_TYPE.Line:  # line-to-line snapping check
            feature1StartVertex = featureData1.startVertex
            feature1EndVertex = featureData1.endVertex
            feature2StartVertex = featureData2.startVertex
            feature2EndVertex = featureData2.endVertex

            if feature1StartVertex == feature2StartVertex or feature1StartVertex == feature2EndVertex or \
                    feature1EndVertex == feature2StartVertex or feature1EndVertex == feature2EndVertex:
                return True
            else:
                return False

        elif featureData1.geomType == GEOM_TYPE.Point:  # point-to-line snapping check
            feature1Vertex = featureData1.startVertex
            feature2StartVertex = featureData2.startVertex
            feature2EndVertex = featureData2.endVertex

            if feature1Vertex == feature2StartVertex or feature1Vertex == feature2EndVertex:
                return True
            else:
                return False

        return False

    def updateVertexes(self, featureData1, featureData2, vertDataUs, vertDataDs, vertexes):
        """


        :param featureData1:
        :param featureData2:
        :param vertDataUs:
        :param vertDataDs:
        :return:
        """

        if featureData1.geomType == GEOM_TYPE.Line:
            feature1StartVertex = featureData1.startVertex
            feature1EndVertex = featureData1.endVertex
            feature2StartVertex = featureData2.startVertex
            feature2EndVertex = featureData2.endVertex

            # check the closest vertex to the upstream
            if not vertDataUs.snapped:
                # upstream-upstream
                self.getDistanceAndUpdate(feature1StartVertex, feature2StartVertex, vertDataUs, vertexes,
                                          VERTEX.First, featureData2)

                # upstream-downstream
                self.getDistanceAndUpdate(feature1StartVertex, feature2EndVertex, vertDataUs, vertexes,
                                          VERTEX.Last, featureData2)

            # check the closest vertex to the downstream
            if not vertDataDs.snapped:
                # upstream-upstream
                self.getDistanceAndUpdate(feature1EndVertex, feature2StartVertex, vertDataDs, vertexes,
                                          VERTEX.First, featureData2)

                # upstream-downstream
                self.getDistanceAndUpdate(feature1EndVertex, feature2EndVertex, vertDataDs, vertexes,
                                          VERTEX.Last, featureData2)

        else:
            feature1Vertex = featureData1.startVertex
            feature2StartVertex = featureData2.startVertex
            feature2EndVertex = featureData2.endVertex

            if not vertDataUs.snapped:
                # upstream-upstream
                self.getDistanceAndUpdate(feature1Vertex, feature2StartVertex, vertDataUs, vertexes,
                                          VERTEX.First, featureData2)

                # upstream-downstream
                self.getDistanceAndUpdate(feature1Vertex, feature2EndVertex, vertDataUs, vertexes,
                                          VERTEX.Last, featureData2)

    def getDistanceAndUpdate(self, v1, v2, vData, vertexes, vertPos, fData):
        """


        :param v1:
        :param v2:
        :param vData1:
        :param vData2:
        :return:
        """

        dx = v1.x() - v2.x()
        dy = v1.y() - v2.y()
        dist = (dx ** 2 + dy ** 2) ** 0.5

        if dist < vData.distanceToClosest:
            if vertexes is None:
                vertexes = self.vertexes
            vname = '{0}{1}'.format(fData.id, vertPos)
            if vname in vertexes:
                vertex = vertexes[vname]
            else:
                vertex = NetworkVertex(fData.id, vertPos,
                                       fData.layer, fData.feature)
                vertexes[vname] = vertex
            vData.distanceToClosest = dist
            vData.closestVertex = vertex

    def hasAlreadyRun(self, inputs, dem, lines):
        """
        Checks if input data set has already been run -
        and that no changes have occured to the input
        datasets.

        Returns:
        True if has already run
        False not already run / needs to be run again

        :param inputs: list -> QgsVectorLayer
        :param dem: QgsRasterLayer
        :return: bool
        """

        func = lambda x: x.name() if x is not None else None
        if sorted([func(x) for x in inputs]) != sorted(self.inputs):
            return False
        if sorted([func(x) for x in lines]) != sorted(self.lines):
            return False
        if self.checkDemMetadata(dem):
            return False
        for layer in inputs:
            if self.checkFileMetadata(layer, "input"):
                return False
        for layer in lines:
            if self.checkFileMetadata(layer, "line"):
                return False

        return True

    def checkFileMetadata(self, layer, inputType):
        """
        Collects file metadata and return True if input is new, or False
        if input has already been run through the data collector.

        Don't save any metadata yet in case something errors in the data collection.
        If the data collections completes successfully, can we can then save.

        :param layer: QgsMapLayer
        :return: bool
        """

        source = layer.source()
        saveDate = None
        if os.path.exists(source):
            saveDate = os.path.getmtime(source)

        # check if save date is newer or file path has changed
        if inputType == 'input':
            if source != self.inputFilePaths[layer.name()]:
                return True
            if saveDate != self.fileSaveDates[layer.name()]:
                return True
        elif inputType == 'line':
            if source != self.inputLinesFilePaths[layer.name()]:
                return True
            if saveDate != self.lineSaveDates[layer.name()]:
                return True

        return False

    def checkDemMetadata(self, dem):
        """
        Checks the dem metadata against what has previously been used for the layer.
        Return True if dem is different or newer, False if nothing has changed.

        :param dem: QgsRaterLayer
        :return: bool
        """

        if dem is not None:
            source = dem.dataProvider().dataSourceUri()
            saveDate = None
            if os.path.exists(source):
                saveDate = os.path.getmtime(source)

            if dem.name() not in self.demFilePaths:
                return True
            if source != self.demFilePaths[dem.name()]:
                return True
            if dem.name() not in self.demSaveDates:
                return True
            if saveDate != self.demSaveDates[dem.name()]:
                return True
        else:
            if self.demFilePaths:
                return True

        return False

    def saveMetadata(self, inputs, dem, lines):
        """
        Saves the metadata so it can be checked next time and
        this step skipped if nothing is new.

        :param inputs: list -> QgsMapLayer
        :param dem: QgsRasterLayer
        :return: void
        """

        for layer in inputs:
            if layer is not None:
                source = layer.source()
                saveDate = None
                if os.path.exists(source):
                    saveDate = os.path.getmtime(source)

                self.inputs.append(layer.name())
                self.inputFilePaths[layer.name()] = source
                self.fileSaveDates[layer.name()] = saveDate

        for layer in lines:
            if layer is not None:
                source = layer.source()
                saveDate = None
                if os.path.exists(source):
                    saveDate = os.path.getmtime(source)

                self.lines.append(layer.name())
                self.inputLinesFilePaths[layer.name()] = source
                self.lineSaveDates[layer.name()] = saveDate

        self.saveDemMetadata(dem)

    def saveDemMetadata(self, dem):
        """
        Save dem metadata to layer so it can be checked next time
        and this step can be skipped if nothing is new.

        :param dem: QgsRasterLayer
        :return: void
        """

        if dem is not None:
            source = dem.dataProvider().dataSourceUri()
            saveDate = None
            if os.path.exists(source):
                saveDate = os.path.getmtime(source)

            self.demFilePaths[dem.name()] = source
            self.demSaveDates[dem.name()] = saveDate


    def getIdFromFid(self, layerName, fid):
        """
        Returns the ID from a given QgsFeature

        :param layerName: str
        :param fid: QgsFeatureId
        :return: str ID
        """

        if layerName in self.feature2id:
            if fid in self.feature2id[layerName]:
                return self.feature2id[layerName][fid]

        return None
    
    def collectTableData(self, layer, featureData):
        """
        Place holder function to be overwritten later in subobjects
        
        :param featureData: FeatureData
        :return: void
        """
        
        endXsUs = False
        endXsDs = False
        
        if layer.name() in self.allTableFeatures:
            allTableFeatures = self.allTableFeatures[layer.name()]
            index = self.indexedTables[layer.name()]
        else:
            allTableFeatures = {f.id(): f for f in layer.getFeatures()}
            self.allTableFeatures[layer.name()] = allTableFeatures
            index = QgsSpatialIndex(layer)
            self.indexedTables[layer.name()] = index
            
        # check if any table features snapped to the
        # upstream or downstream end of network
        if featureData.type:
            if featureData.type.lower()[0] != 'w':
                rect = QgsRectangle(featureData.startVertex.x()-1, featureData.startVertex.y()-1,
                                    featureData.startVertex.x()+1, featureData.startVertex.y()+1)
                for fid in index.intersects(rect):
                    feature = allTableFeatures[fid]
                    if feature.geometry().intersects(QgsGeometry.fromPointXY(featureData.startVertex)):
                        source = os.path.join(os.path.dirname(layer.source()), feature.attribute(0))
                        typ = feature.attribute(1)
                        
                        if os.path.isfile(source):
                            inv = readInvFromCsv(source, typ)
                        else:
                            inv = None
                        
                        if inv is not None:
                            if featureData.invertUs == -99999:
                                featureData.invertUs = inv
                            endXsUs = True
                
                # downstream
                rect = QgsRectangle(featureData.endVertex.x() - 1, featureData.endVertex.y() - 1,
                                    featureData.endVertex.x() + 1, featureData.endVertex.y() + 1)
                for fid in index.intersects(rect):
                    feature = allTableFeatures[fid]
                    if feature.geometry().intersects(QgsGeometry.fromPointXY(featureData.endVertex)):
                        source = os.path.join(os.path.dirname(layer.source()), feature.attribute(0))
                        typ = feature.attribute(1)
                
                        if os.path.exists(source):
                            inv = readInvFromCsv(source, typ)
                        else:
                            inv = None
                
                        if inv is not None:
                            if featureData.invertDs == -99999:
                                featureData.invertDs = inv
                            endXsDs = True
                    
        # mid cross section
        if not endXsUs or not endXsDs:
            rect = self.createRequest(featureData, 1)
            for fid in index.intersects(rect):
                feature = allTableFeatures[fid]
                if feature.geometry().intersects(featureData.feature.geometry()):
                    source = os.path.join(os.path.dirname(layer.source()), feature.attribute(0))
                    typ = feature.attribute(1)
    
                    if os.path.exists(source):
                        inv = readInvFromCsv(source, typ)
                    else:
                        inv = None
    
                    if inv is not None:
                        if typ.upper() == 'XZ' or typ.upper() == 'CS':
                            if featureData.invertUs == -99999 or featureData.invertDs == -99999:
                                featureData.invertUs = inv
                                featureData.invertDs = inv
                        if featureData.type:
                            if featureData.type.lower()[0] == 'w':
                                featureData.invertUs = inv
                                featureData.invertDs = inv
                            if featureData.type.lower()[0] == 'b':
                                if featureData.invertUs == -99999:
                                    featureData.invertUs = inv
                                    featureData.invertDs = inv
                
    def getFeaturesToAssess(self, inputs, startLocs, flowTrace, lines=(), dataCollectorLines=None):
        """
        
        :param inputs: list -> QgsVectorLayer
        :param startLocs: list -> id
        :param flowTrace: bool
        :return:
        """
        
        self.featuresToAssess = []
        self.featuresAssessed = []
        self.layersToAssess = []
        self.hasStarted = False
        idmapping = {}
        
        # get x connectors first
        key = lambda x: 0 if x.attribute(1).lower() == 'x' else 1
        for layer in inputs:
            if is1dNetwork(layer):
                try:
                    for f in sorted(layer.getFeatures(), key=key):
                        if f.attribute(1).lower() == 'x':
                            self.featuresToAssess.append(f)
                            self.layersToAssess.append(layer)
                        else:
                            break  # stop after all x connectors
                except AttributeError:
                    return "ERROR: Check all 1d_nwk features have 'Type' specified"
                    
        # if flowTrace is true then add start locations
        # else if not flowTrace then assess whole network
        if flowTrace:
            for loc in startLocs:
                layername = loc[0]
                fid = loc[1]
                if layername in self.allFeatures:
                    f = self.allFeatures[layername][fid]
                    self.featuresToAssess.append(f)
                    for layer in inputs:
                        if layername == layer.name():
                            self.layersToAssess.append(layer)
        else:
            for layer in inputs:
                if is1dNetwork(layer):
                    features = [f for f in sorted(layer.getFeatures(), key=key)]
                    layers = [layer for x in range(layer.featureCount())]
                    i = 0
                    for i, f in enumerate(features):
                        if f.attribute(1).lower() == 'x':
                            continue
                        else:
                            break
                    self.featuresToAssess += features[i:]
                    self.layersToAssess += layers[i:]
            
    def finishedFeature(self, feature, layer, snappedFeatures, snappedLayers):
        """
        Place holder for flow trace object to override.
        
        :param feature: QgsFeature
        :param snappedFeatures: list -> QgsFeature
        :param snappedLayers: list -> QgsVectorLayer
        :return: void
        """
        
        self.featuresAssessed.append(feature)
