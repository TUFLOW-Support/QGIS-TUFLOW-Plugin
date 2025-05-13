import re
from qgis.core import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from .Enumerators import *

from ..compatibility_routines import QT_DOUBLE, QT_STRING


class SnappingTool:
    """
    Class for generating the output for the snapping tool.

    The data collection and identifying unsnapped objects is
    done in the DataCollector.

    """

    def __init__(self, iface=None, dataCollector=None, outputLyr=None, dataCollectorLines=None, exclRadius=10,
                 dataCollectorPoints=None):
        self.iface = iface
        self.dataCollector = dataCollector
        self.dataCollectorLines = dataCollectorLines  # only used if dataCollector is points
        self.dataCollectorPoints = dataCollectorPoints
        self.outputLyr = outputLyr
        self.cutoffLimit = exclRadius  # limit to consider pipe vertex is most upstream or downstream
        self.tmpLyrs = []
        self.tmplyr2oldlyr = {}

        if outputLyr is None or not outputLyr.isValid():
            if self.iface is not None:
                crs = QgsProject.instance().crs()
                uri = "point?crs={0}".format(crs.authid().lower())
            else:
                uri = "point"
            self.outputLyr = QgsVectorLayer(uri, "output", "memory")
            self.dp = self.outputLyr.dataProvider()
            self.dp.addAttributes([QgsField('Warning', QT_STRING),
                                   QgsField("Message", QT_STRING),
                                   QgsField("Tool", QT_STRING),
                                   QgsField("Magnitude", QT_DOUBLE)])
            self.outputLyr.updateFields()
        else:
            self.dp = self.outputLyr.dataProvider()

        if dataCollector is not None:

            feats = []

            for vertex in dataCollector.unsnappedVertexes:
                if vertex.distanceToClosest < self.cutoffLimit:
                
                    id = vertex.id
                    
                    if id in dataCollector.features:
                        fData = dataCollector.features[id]

                        if vertex.vertex == VERTEX.Last:
                            loc = fData.endVertex
                        else:
                            loc = fData.startVertex

                        feat = QgsFeature()
                        feat.setGeometry(QgsGeometry.fromPointXY(loc))
                        geom = 'point' if fData.geomType == GEOM_TYPE.Point else 'line vertex'
                        feat.setAttributes(['Unsnapped {0}'.format(geom),
                                            'Unsnapped {0} at {1}, {2}'.format(geom, loc.x(), loc.y()),
                                            'Snapping: Check',
                                            vertex.distanceToClosest])
                        feats.append(feat)

            self.dp.addFeatures(feats)
            self.outputLyr.updateExtents()
            self.outputLyr.triggerRepaint()

    def autoSnap(self, radius):
        """
        Create temp layer of networks and auto snap to closest vertex if within radius
        
        :param radius: float
        :return: void
        """

        if self.dataCollector is not None:

            if self.dataCollector.unsnappedVertexes:
                # create a list of all the vertexes that we will actually move

                moveableVertexes = []
                for v in self.dataCollector.unsnappedVertexes:
                    if v.distanceToClosest < self.cutoffLimit:
                        if v.distanceToClosest < radius:
                            moveableVertexes.append(v)

                if moveableVertexes:
                    for v in moveableVertexes:
                        if not v.snapped:  # and not v.hasPoint:
                            if v.hasPoint:
                                pointVertex = self.dataCollectorPoints.vertexes[v.point]
                                pointVertex.snapped = False
                                pointVertex.closestVertex = v.closestVertex
                                pointVertex.distanceToClosest = v.distanceToClosest
                                if pointVertex not in self.dataCollectorPoints.unsnappedVertexes:
                                    self.dataCollectorPoints.unsnappedVertexes.append(pointVertex)

                            lyrnames = [x.name() for _, x in QgsProject.instance().mapLayers().items()]
                            if re.findall(r'_SN\d+$', v.layer.name()):
                                cnt = int(re.findall(r'\d+$', v.layer.name())[0])
                                name_ = re.split(r'_SN\d+', v.layer.name())[0]
                            else:
                                cnt = 1
                                name_ = v.layer.name()
                            tempLyrName = '{0}_SN{1}'.format(name_, cnt)
                            while tempLyrName in lyrnames:
                                cnt += 1
                                tempLyrName = '{0}_SN{1}'.format(name_, cnt)

                            if tempLyrName not in [x.name() for x in self.tmpLyrs]:
                                lyr = self.copyLayerToTemp(v.layer, tempLyrName)
                                self.tmpLyrs.append(lyr)
                            else:
                                i = [x.name() for x in self.tmpLyrs].index(tempLyrName)
                                lyr = self.tmpLyrs[i]

                            self.tmplyr2oldlyr[lyr.id()] = v.layer.id()
                            lyr.startEditing()
                            
                            # get position to move to
                            closestId = v.closestVertex.id
                            if self.dataCollectorLines is not None:
                                fDataMoveTo = self.dataCollectorLines.features[closestId]
                            else:
                                fDataMoveTo = self.dataCollector.features[closestId]
                            if v.closestVertex.vertex == VERTEX.First or v.closestVertex.vertex == VERTEX.Point:
                                moveTo = fDataMoveTo.startVertex
                            else:
                                moveTo = fDataMoveTo.endVertex
                            
                            # get vertex position
                            if v.vertex == VERTEX.First or v.vertex == VERTEX.Point:
                                vpos = 0
                            else:
                                if v.feature.geometry().wkbType() == QgsWkbTypes.MultiLineString:
                                    vertexes = v.feature.geometry().asMultiPolyline()[0]
                                else:
                                    vertexes = v.feature.geometry().asPolyline()
                                vpos = len(vertexes) - 1
                            
                            # move vertex
                            moved = lyr.moveVertex(moveTo.x(), moveTo.y(), v.tmpFid, vpos)
                            if moved:
                                # set vertex properties to snapped
                                v.snapped = True
                                v.closestVertex.snapped = True

                                # edit start / end point locations of moved object
                                fDataMovedObject = self.dataCollector.features[v.id]
                                if v.vertex == VERTEX.First:
                                    fDataMovedObject.startVertex = moveTo
                                elif v.vertex == VERTEX.Last:
                                    fDataMovedObject.endVertex = moveTo
                                else:  # point
                                    fDataMovedObject.startVertex = moveTo
                                    fDataMovedObject.endVertex = moveTo
                                
                                # add to the output message layer
                                feat = QgsFeature()
                                feat.setGeometry(QgsGeometry.fromPointXY(moveTo))
                                geom = 'point' if v.vertex == VERTEX.Point else 'line vertex'
                                geom2 = 'point' if v.closestVertex.vertex == VERTEX.Point else 'line vertex'
                                feat.setAttributes(['Auto Snap {0}'.format(geom),
                                                    'Moved {0} {1:.4f} to {2}'.format(geom, v.distanceToClosest, geom2),
                                                    'Snapping: Auto',
                                                    v.distanceToClosest])
                                self.dp.addFeature(feat)
                                self.outputLyr.updateExtents()
                                
                            lyr.commitChanges()
                            
                else:
                    return
                    #if self.iface is not None:
                    #    QMessageBox.information(self.iface.mainWindow(), "Integrity Tool",
                    #                            "No unsnapped networks in search radius")
                    #    return
                
            else:
                return
                #if self.iface is not None:
                #    QMessageBox.information(self.iface.mainWindow(), "Integrity Tool", "No unsnapped networks")
                #    return
                
    def copyLayerToTemp(self, copylyr, name):
        """
        
        
        :param lyr:
        :param name:
        :return:
        """

        epsg = copylyr.crs().authid().lower()
        if copylyr.geometryType() == QgsWkbTypes.LineGeometry:
            uri = 'linestring?crs={0}'.format(epsg)
        else:
            uri = 'point?crs={0}'.format(epsg)
        lyr = QgsVectorLayer(uri, name, "memory")
        dp = lyr.dataProvider()
        
        fields = copylyr.fields()
        if copylyr.storageType() == 'GPKG':  # temp layer is not a GPKG (ignore fid)
            j = fields.indexFromName('fid')
            fields.remove(j)
        dp.addAttributes(fields)
        lyr.updateFields()
        
        feats = []
        for i, f in enumerate(copylyr.getFeatures()):
            feat = QgsFeature(f)
            if copylyr.storageType() == 'GPKG':
                feat.deleteAttribute(j)
            dp.addFeature(feat)
            lyr.updateExtents()
            
            # update the vertex with a tmp fid so the vertex can be moved if necessary
            id = self.dataCollector.getIdFromFid(copylyr.name(), f.id())
            if self.dataCollector.geomType == GEOM_TYPE.Line:
                pos = [VERTEX.First, VERTEX.Last]
                for p in pos:
                    vname = '{0}{1}'.format(id, p)
                    if vname in self.dataCollector.vertexes:
                        v = self.dataCollector.vertexes[vname]
                        v.tmpFid = feat.id()
            else:
                if id in self.dataCollector.vertexes:
                    v = self.dataCollector.vertexes[id]
                    v.tmpFid = feat.id()
        
        return lyr