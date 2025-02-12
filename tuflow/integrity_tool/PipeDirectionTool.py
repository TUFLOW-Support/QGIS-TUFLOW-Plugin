from qgis.core import *
from PyQt5.QtCore import *
from .FeatureData import FeatureData
from .Enumerators import *
from tuflow.tuflowqgis_library import is1dNetwork, getNetworkMidLocation
from .helpers import EstryHelper, SwmmHelper

from tuflow.tuflow_swmm.swmm_gis_info import is_swmm_network_layer

class PipeDirectionTool():

    def __init__(self, iface=None, outputLyr=None):
        self.iface = iface
        self.outputLyr = outputLyr
        self.tmpLyrs = []
        self.tmplyr2oldlyr = {}

        self.flagGradientPoint = []
        self.flagGradientMessage = []

        self.flagContinuityPoint = []
        self.flagContinuityMessage = []

        # prepare the outputlyr
        if outputLyr is not None:
            self.outputLyr = outputLyr
            self.dp = outputLyr.dataProvider()
        else:
            if self.iface is not None:
                crs = QgsProject.instance().crs()
                uri = "point?crs={0}".format(crs.authid().lower())
            else:
                uri = "point"
            self.outputLyr = QgsVectorLayer(uri, "output", "memory")
            self.dp = self.outputLyr.dataProvider()
            if Qgis.QGIS_VERSION_INT < 33800:
                self.dp.addAttributes([QgsField('Warning', QVariant.String),
                                       QgsField("Message", QVariant.String),
                                       QgsField("Tool", QVariant.String),
                                       QgsField("Magnitude", QVariant.Double)])
            else:
                self.dp.addAttributes([QgsField('Warning', QMetaType.QString),
                                       QgsField("Message", QMetaType.QString),
                                       QgsField("Tool", QMetaType.QString),
                                       QgsField("Magnitude", QMetaType.Double)])
            self.outputLyr.updateFields()

        self.helper = EstryHelper()

    def byGradient(self, inputs=()):
        """
        
        :param inputs:
        :return:
        """
        # import pydevd_pycharm
        # pydevd_pycharm.settrace('localhost', port=53110, stdoutToServer=True, stderrToServer=True)

        if not self.tmpLyrs and len(inputs) > 0:
            if is_swmm_network_layer(inputs[0]):
                self.helper = SwmmHelper()

        if not self.tmpLyrs:
            for layer in inputs:
                if is_swmm_network_layer(layer) or is1dNetwork(layer):
                    lyr = self.copyLayerToTemp(layer, '{0}_tmp'.format(layer.name()))
                    self.tmpLyrs.append(lyr)
                    self.helper.register_temp_layer(lyr, layer)

        for layer in self.tmpLyrs:
            for f in layer.getFeatures():
                fData = FeatureData(self.helper, layer, f)
                if fData.type.lower() != 'x':
                    if fData.invertUs != -99999 and fData.invertDs != -99999:
                        if fData.invertUs < fData.invertDs:
                            # flip line direction
                            geomMulti = f.geometry()
                            geomMulti.convertToMultiType()
                            geom = geomMulti.asMultiPolyline()
                            layer.startEditing()
                            for g in geom:
                                reversedGeom = g[::-1]
                                for i in range(len(g)):
                                    layer.moveVertex(reversedGeom[i].x(), reversedGeom[i].y(), f.id(), i)
                                # TODO - Needs to be handled differently for SWMM
                                layer.changeAttributeValue(f.id(), 6, fData.invertDs, fData.invertUs)
                                layer.changeAttributeValue(f.id(), 7, fData.invertUs, fData.invertDs)
                            layer.commitChanges()

                            # log change
                            midPoint = getNetworkMidLocation(f)
                            self.flagGradientPoint.append(midPoint)
                            message = '{0} has been reversed based on inverts ' \
                                      '({1:.3f}RL, {2:.3f}RL)'.format(fData.id, fData.invertUs, fData.invertDs)
                            self.flagGradientMessage.append(message)

        # add features to outputlyr
        feats = []
        for i, point in enumerate(self.flagGradientPoint):
            message = self.flagGradientMessage[i]
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
            feat.setAttributes(['Pipe Direction Changed',
                                message,
                                'Pipe Direction: Gradient',
                                1.])
            feats.append(feat)
        self.dp.addFeatures(feats)
        self.outputLyr.updateExtents()

    def byContinuity(self, inputs=(), dataCollector=None):
        """
        
        
        :param dataCollector:
        :return:
        """

        if not self.tmpLyrs:
            for layer in inputs:
                if is_swmm_network_layer(layer) or is1dNetwork(layer):
                    lyrnames = [x.name() for _, x in QgsProject.instance().mapLayers().items()]
                    cnt = 1
                    tmplyrname = '{0}_PD{1}'.format(layer.name(), cnt)
                    while tmplyrname in lyrnames:
                        cnt += 1
                        tmplyrname = '{0}_PD{1}'.format(layer.name(), cnt)

                    lyr = self.copyLayerToTemp(layer, tmplyrname, dataCollector)
                    self.tmpLyrs.append(lyr)
                    self.tmplyr2oldlyr[lyr.id()] = layer.id()

        for id in dataCollector.ids:
            if '__connector__' not in id:
                if id in dataCollector.connections:
                    linesDs = dataCollector.connections[id].linesDs
                    linesUs = dataCollector.connections[id].linesUs
                    linesDsDs = dataCollector.connections[id].linesDsDs
                    linesUsUs = dataCollector.connections[id].linesUsUs

                    if linesDsDs and linesUsUs and not linesDs and not linesUs:
                        # reverse direction
                        layer = dataCollector.features[id].tmpLayer
                        f = dataCollector.features[id].tmpFeature
                        geomMulti = f.geometry()
                        geomMulti.convertToMultiType()
                        geom = geomMulti.asMultiPolyline()
                        layer.startEditing()
                        for g in geom:
                            reversedGeom = g[::-1]
                            for i in range(len(g)):
                                layer.moveVertex(reversedGeom[i].x(), reversedGeom[i].y(), f.id(), i)
                        layer.commitChanges()

                        # log change
                        midPoint = getNetworkMidLocation(f)
                        self.flagContinuityPoint.append(midPoint)
                        message = '{0} has been reversed based on continuity'.format(id)
                        self.flagContinuityMessage.append(message)

        # add features to outputlyr
        feats = []
        for i, point in enumerate(self.flagContinuityPoint):
            message = self.flagContinuityMessage[i]
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
            feat.setAttributes(['Pipe Direction Changed',
                                message,
                                'Pipe Direction: Continuity',
                                1.])
            feats.append(feat)
        self.dp.addFeatures(feats)
        self.outputLyr.updateExtents()

    def copyLayerToTemp(self, copylyr, name, dataCollector=None):
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

        for i, f in enumerate(copylyr.getFeatures()):
            feat = QgsFeature(f)
            if copylyr.storageType() == 'GPKG':
                feat.deleteAttribute(j)
            dp.addFeature(feat)
            lyr.updateExtents()

            if dataCollector is not None:
                # update fData with a tmp feature and layer the vertex can be moved if necessary
                id = dataCollector.getIdFromFid(copylyr.name(), f.id())
                dataCollector.features[id].tmpLayer = lyr
                dataCollector.features[id].tmpFeature = feat

        return lyr
