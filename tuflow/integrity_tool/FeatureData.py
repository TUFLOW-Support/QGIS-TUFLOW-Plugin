from qgis.core import *
from .Enumerators import *


class FeatureData():
    """
    Class for storing useful feature data from a 1d_nwk.


    """

    def __init__(self, layer=None, feature=None, nullCounter=0):
        self.id = None
        self.geomType = None
        self.feature = None
        self.layer = None
        self.fid = None
        self.startVertex = None
        self.endVertex = None
        self.type = None
        self.invertUs = None
        self.invertDs = None
        self.width = None
        self.height = None
        self.numberOf = None
        self.nullCounter = nullCounter

        if feature is not None:
            if feature.geometry():
                # User ID (not the same as fid)
                id = feature.attribute(0)
                if id == NULL:
                    if feature.attribute(1).lower() == 'x':
                        id = '__connector__{0}'.format(nullCounter)
                    else:
                        id = '{0}_{1}'.format(feature.attribute(1), nullCounter)
                    self.nullCounter += 1
                self.id = id

                # QgsFeature
                self.feature = feature

                # QgsVectorLayer
                self.layer = layer

                # QgsFeatureId
                self.fid = feature.id()

                # type i.e. C, R, S etc
                self.type = feature.attribute(1)

                # inverts
                self.invertUs = feature.attribute(6)
                self.invertDs = feature.attribute(7)
                if self.type:
                    if self.type.lower()[0] == 'b':
                        self.invertDs = self.invertUs
                if self.invertUs == NULL:
                    self.invertUs = -99999
                if self.invertDs == NULL:
                    self.invertDs = -99999

                # size
                self.width = feature.attribute(13)
                if self.width == NULL:
                    self.width = 0
                self.height = feature.attribute(14)
                if self.height == NULL:
                    self.height = 0
                self.numberOf = feature.attribute(15)
                if self.numberOf == 0 or self.numberOf == NULL:
                    self.numberOf = 1

                # start and end vertex QgsPointXY
                if layer.geometryType() == QgsWkbTypes.PointGeometry:
                    self.geomType = GEOM_TYPE.Point
                    point = feature.geometry().asPoint()
                    self.startVertex = point
                    self.endVertex = point
                elif layer.geometryType() == QgsWkbTypes.LineGeometry:
                    self.geomType = GEOM_TYPE.Line
                    if feature.geometry().isMultipart():
                        line = feature.geometry().asMultiPolyline()
                        self.startVertex = line[0][0]
                        self.endVertex = line[-1][-1]
                    else:
                        line = feature.geometry().asPolyline()
                        self.startVertex = line[0]
                        self.endVertex = line[-1]

    def getNullCounter(self):
        """
        Return null counter so it can be updated in DataCollector

        :return: int
        """

        return self.nullCounter