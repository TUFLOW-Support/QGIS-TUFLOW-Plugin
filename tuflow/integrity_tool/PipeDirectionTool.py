from qgis.core import *
from PyQt5.QtCore import *
from .FeatureData import FeatureData
from .Enumerators import *
from tuflow.tuflowqgis_library import is1dNetwork, getNetworkMidLocation


class PipeDirectionTool():
    
    def __init__(self, iface=None, outputLyr=None):
        self.iface = iface
        self.outputLyr = outputLyr
        self.tmpLyrs = []
        
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
                uri = "point?crs{0}".format(crs.authid())
            else:
                uri = "point"
            self.outputLyr = QgsVectorLayer(uri, "output", "memory")
            self.dp = self.outputLyr.dataProvider()
            self.dp.addAttributes([QgsField('Warning', QVariant.String),
                                   QgsField("Message", QVariant.String),
                                   QgsField("Tool", QVariant.String)])
            self.outputLyr.updateFields()
            
    def byGradient(self, inputs=()):
        """
        
        :param inputs:
        :return:
        """
        
        if not self.tmpLyrs:
            for layer in inputs:
                if is1dNetwork(layer):
                    lyr = self.copyLayerToTemp(layer, 'temp_{0}'.format(layer.name()))
                    self.tmpLyrs.append(lyr)
            
        
        for layer in self.tmpLyrs:
            for f in layer.getFeatures():
                fData = FeatureData(layer, f)
                if fData.type.lower() != 'x':
                    if fData.invertUs != -99999 and fData.invertDs != -99999:
                        if fData.invertUs < fData.invertDs:
                            # flip line direction
                            geom = f.geometry().asMultiPolyline()
                            layer.startEditing()
                            for g in geom:
                                reversedGeom = g[::-1]
                                for i in range(len(g)):
                                    layer.moveVertexV2(QgsPoint(reversedGeom[i]), f.id(), i)
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
                                'Pipe Direction: Gradient'])
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
                if is1dNetwork(layer):
                    lyr = self.copyLayerToTemp(layer, 'temp_{0}'.format(layer.name()), dataCollector)
                    self.tmpLyrs.append(lyr)
                    
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
                        geom = f.geometry().asMultiPolyline()
                        layer.startEditing()
                        for g in geom:
                            reversedGeom = g[::-1]
                            for i in range(len(g)):
                                layer.moveVertexV2(QgsPoint(reversedGeom[i]), f.id(), i)
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
                                'Pipe Direction: Continuity'])
            feats.append(feat)
        self.dp.addFeatures(feats)
        self.outputLyr.updateExtents()

    def copyLayerToTemp(self, copylyr, name, dataCollector=None):
        """


        :param lyr:
        :param name:
        :return:
        """
    
        if copylyr.geometryType() == QgsWkbTypes.LineGeometry:
            uri = 'linestring'
        else:
            uri = 'point'
        lyr = QgsVectorLayer(uri, name, "memory")
        dp = lyr.dataProvider()
    
        fields = copylyr.fields()
        dp.addAttributes(fields)
        lyr.updateFields()
        
        for i, f in enumerate(copylyr.getFeatures()):
            feat = QgsFeature(f)
            dp.addFeature(feat)
            lyr.updateExtents()
            
            if dataCollector is not None:
                # update fData with a tmp feature and layer the vertex can be moved if necessary
                id = dataCollector.getIdFromFid(copylyr.name(), f.id())
                dataCollector.features[id].tmpLayer = lyr
                dataCollector.features[id].tmpFeature = feat
    
        return lyr