from qgis.core import *
from .Enumerators import *


class FeatureData():
    """
    Class for storing useful feature data from a 1d_nwk.


    """

    def __init__(self, helper, layer=None, feature=None, nullCounter=0):
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
        self.invertOffsetUs = 0.0  # SWMM stores offsets to node elevations to have pipes not at manhole elev
        self.invertOffsetDs = 0.0
        self.width = None
        self.height = None
        self.numberOf = None
        self.length = None
        self.height_ = None
        self.nullCounter = nullCounter
        self.area = 0.0

        if feature is not None:
            if feature.geometry():
                # User ID (not the same as fid)
                id = helper.get_feature_id(layer, feature)
                if id == NULL:
                    if helper.get_nwk_type(feature).lower() == 'x':
                        id = '__connector__{0}'.format(nullCounter)
                    else:
                        id = '{0}_{1}'.format(helper.get_nwk_type(feature), nullCounter)
                    self.nullCounter += 1
                self.id = id

                # QgsFeature
                self.feature = feature

                # QgsVectorLayer
                self.layer = layer

                # QgsFeatureId
                self.fid = feature.id()

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

                # Attributes must come through helper
                atts = helper.get_feature_attributes(layer, feature)
                self.type = atts['type']
                self.invertUs = atts['invertUs']
                self.invertDs = atts['invertDs']
                self.width = atts['width']
                self.height = atts['height']
                self.numberOf = atts['numberOf']
                self.height_ = atts['height_']
                self.length = atts['length']
                self.area = atts['area']
                self.invertOffsetUs = 0.0
                self.invertOffsetDs = 0.0

                if 'invertOffsetUs' in atts:
                    self.invertOffsetUs = atts['invertOffsetUs']
                if 'invertOffsetDs' in atts:
                    self.invertOffsetDs = atts['invertOffsetDs']

                # # type i.e. C, R, S etc
                # self.type = feature.attribute(1)
                #
                # # inverts
                # self.invertUs = feature.attribute(6)
                # self.invertDs = feature.attribute(7)
                # if self.type:
                #     if self.type.lower()[0] == 'b':
                #         self.invertDs = self.invertUs
                # if self.invertUs == NULL:
                #     self.invertUs = -99999
                # if self.invertDs == NULL:
                #     self.invertDs = -99999
                #
                # # size
                # self.width = feature.attribute(13)
                # if self.width == NULL:
                #     self.width = 0
                # self.height = feature.attribute(14)
                # if self.height == NULL:
                #     self.height = 0
                # self.numberOf = feature.attribute(15)
                # if self.numberOf == 0 or self.numberOf == NULL:
                #     self.numberOf = 1
                # self.height_ = self.width if self.type.lower()[0] == 'c' else self.height
                # self.length = feature.attribute(4) if feature.attribute(4) != NULL and feature.attribute(4) > 0. else feature.geometry().length()

    def getNullCounter(self):
        """
        Return null counter so it can be updated in DataCollector

        :return: int
        """

        return self.nullCounter
