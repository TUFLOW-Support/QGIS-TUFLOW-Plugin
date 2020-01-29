from PyQt5.QtCore import *
from qgis.core import *
from math import pi
from .Enumerators import *
from tuflow.tuflowqgis_library import getNetworkMidLocation, interpolateObvert


class ContinuityTool(QObject):

    # some custom signals to let the gui know what's going on
    updated = pyqtSignal()
    finished = pyqtSignal()
    
    def __init__(self, iface=None, dataCollector=None, outputLyr=None, limitAngle=0, limitCover=99999, limitArea=100,
                 checkArea=False, checkAngle=False, checkInvert=False, checkCover=False):
        # initialise inherited QObject
        QObject.__init__(self, parent=None)
        
        # some custom properties
        self.iface = iface
        self.dataCollector = dataCollector
        self.limitAngle = limitAngle
        self.limitCover = limitCover
        self.limitArea = limitArea
        
        self.flaggedAreaUniqueIds = []
        self.flaggedAreaIds = []
        self.flaggedAreas = []
        self.flaggedAreaMessages = []
        
        self.flaggedInvertUniqueIds = []
        self.flaggedInvertIds = []
        self.flaggedInverts = []
        self.flaggedInvertMessages = []
        
        self.flaggedGradientUniqueIds = []
        self.flaggedGradientIds = []
        self.flaggedGradients = []
        self.flaggedGradientMessages = []
        
        self.flaggedAngleUniqueIds = []
        self.flaggedAngleIds = []
        self.flaggedAngles = []
        self.flaggedAngleMessages = []
        
        self.flaggedCoverUniqueIds = []
        self.flaggedCoverIds = []
        self.flaggedCover = []
        self.flaggedCoverMessages = []
        
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
            self.dp.addAttributes([QgsField('Warning', QVariant.String),
                                   QgsField("Message", QVariant.String),
                                   QgsField("Tool", QVariant.String)])
            self.outputLyr.updateFields()
            
        # loop through features and check continuity
        for id in dataCollector.ids:
            fData = dataCollector.features[id]
            cData = dataCollector.connections[id]
            
            # Check Downstream Area
            if checkArea:
                self.checkArea(fData, cData)
            
            # Check Downstream Inverts
            if checkInvert:
                self.checkInverts(fData, cData)
            
                # Check Gradient
                self.checkGradient(fData)
            
            # Check outflow angle
            if checkAngle:
                self.checkAngles(fData, cData)
            
            # Check pipe cover
            if checkCover:
                self.checkCover(fData)
            
        # write out outputlyr shape file
        feats = []
        # area
        for i, point in enumerate(self.flaggedAreas):
            id = self.flaggedAreaIds[i]
            message = self.flaggedAreaMessages[i]
            
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
            feat.setAttributes(['Flow area decreases downstream of {0}'.format(id),
                                '{0}'.format(message),
                                'Continuity: Flow Area Check'])
            feats.append(feat)
        # inverts
        for i, point in enumerate(self.flaggedInverts):
            id = self.flaggedInvertIds[i]
            message = self.flaggedInvertMessages[i]
    
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
            feat.setAttributes(['Invert increases downstream of {0}'.format(id),
                                '{0}'.format(message),
                                'Continuity: Invert Check'])
            feats.append(feat)
        # gradients
        for i, point in enumerate(self.flaggedGradients):
            id = self.flaggedGradientIds[i]
            message = self.flaggedGradientMessages[i]
    
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
            feat.setAttributes(['Adverse gradient at {0}'.format(id),
                                '{0}'.format(message),
                                'Continuity: Gradient Check'])
            feats.append(feat)
        # angle
        for i, point in enumerate(self.flaggedAngles):
            id = self.flaggedAngleIds[i]
            message = self.flaggedAngleMessages[i]
    
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
            feat.setAttributes(['Accute outflow angle at {0}'.format(id),
                                '{0}'.format(message),
                                'Continuity: Outflow Angle Check'])
            feats.append(feat)
        # cover
        for i, point in enumerate(self.flaggedCover):
            id = self.flaggedCoverIds[i]
            message = self.flaggedCoverMessages[i]
    
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
            feat.setAttributes(['Insufficient cover at {0}'.format(id),
                                '{0}'.format(message),
                                'Continuity: Cover Check'])
            feats.append(feat)

        self.dp.addFeatures(feats)
        self.outputLyr.updateExtents()
        self.outputLyr.triggerRepaint()

    def checkArea(self, fData, cData):
        """
        Compares area for the input pipe against the downstream area.
        Will consider the total area of all downstream connections
        Will consider the total area of all cojoining pipes connecting to
        downstream node.

        :param fData: FeatureData current pipe
        :param cData: ConnectionData current pipe
        :return: void
        """

        # Downstream area check
        area = self.getTotalArea([fData.id] + cData.linesDsDs, NETWORK.Upstream)
        if area is None:
            return
        areaDs = self.getTotalArea(cData.linesDs, NETWORK.Downstream)
        if areaDs is not None:
            doesAreaDecrease = False
            
            # if only one upstream pipe connecting to downstream pipe
            # just consider if area decreases
            # else if more than one, consider percent decrease as user has defined
            if not cData.linesDsDs:  # just the one pipe entering the downstream pipe
                if areaDs < area:
                    doesAreaDecrease = True
            else:  # more than one pipe
                if 1 - areaDs / area > self.limitArea / 100:
                    doesAreaDecrease = True
            if doesAreaDecrease:
                self.flaggedAreaIds.append(fData.id)
                uniqueId = (fData.endVertex.x(), fData.endVertex.y())
                if uniqueId not in self.flaggedAreaUniqueIds:
                    self.flaggedAreaUniqueIds.append(uniqueId)
                    #self.flaggedAreaIds.append(fData.id)
                    self.flaggedAreas.append(fData.endVertex)
                    self.flaggedAreaMessages.append('Area changes from {0:.02f} to {1:.02f}'.format(area, areaDs))
    
    def checkInverts(self, fData, cData):
        """
        Compares downstream invert of pipe to the upstream invert of the downstream pipe.
        If multiple pipes downstream, will use the minimum inert.
        
        :param fData: FeatureData current pipe
        :param cData: ConnectionData current pipe
        :return: void
        """
        
        # downstream invert check
        if '__connector__' not in fData.id:
            invert = fData.invertDs
            if invert != -99999:
                invertDs = self.getInvert(cData.linesDs, NETWORK.Downstream)
                
                if invertDs is not None:
                    if invert < invertDs:
                        uniqueId = (fData.endVertex.x(), fData.endVertex.y())
                        if uniqueId not in self.flaggedInvertUniqueIds:
                            self.flaggedInvertUniqueIds.append(uniqueId)
                            self.flaggedInvertIds.append(fData.id)
                            self.flaggedInverts.append(fData.endVertex)
                            self.flaggedInvertMessages.append(
                                'Invert goes from {0:.02f} to {1:.02f}'.format(invert, invertDs))
                        
    def checkGradient(self, fData):
        """
        Checks the gradient of the pipe - flags if adverse
        
        :param fData: FeatureData current pipe
        :return: void
        """
        
        if fData.invertUs != -99999 and fData.invertDs != -99999:
            if fData.invertUs < fData.invertDs:
                point = getNetworkMidLocation(fData.feature)
                uniqueId = (point.x(), point.y())
                if uniqueId not in self.flaggedGradientUniqueIds:
                    self.flaggedGradientUniqueIds.append(uniqueId)
                    self.flaggedGradientIds.append(fData.id)
                    self.flaggedGradients.append(point)
                    self.flaggedGradientMessages.append(
                        'Adverse Gradient: Upstream invert: {0:.02f} Downstream invert {1:.02f}'.
                            format(fData.invertUs, fData.invertDs))
                    
    def checkAngles(self, fData, cData):
        """
        Checks the outflow angle. Will ignore x connectors.
        If multiple outflow pipe exist, will adopt the value
        from the pipe with the larges (straightest) angle.
        
        :param dData: DrapeData current network
        :param cData: ConnectionData current network
        :return: void
        """
        
        angle = self.getAngle([cData.id] + cData.linesDsDs, NETWORK.Downstream)
        if angle is not None:
            angleDs = self.getAngle(cData.linesDs, NETWORK.Upstream)
            if angleDs is not None:
                outFlowAngle = 0
                for a in angle:
                    for a2 in angleDs:
                        if a is not None and a2 is not None:
                            if a > 180 and a2 < 180:
                                a2 += 360
                            outa = 180.0 - abs(a - a2)
                            outFlowAngle = max(outFlowAngle, outa)
                if outFlowAngle != 0:
                    if outFlowAngle < self.limitAngle:
                        uniqueId = (fData.endVertex.x(), fData.endVertex.y())
                        if uniqueId not in self.flaggedAngleUniqueIds:
                            self.flaggedAngleUniqueIds.append(uniqueId)
                            self.flaggedAngleIds.append(fData.id)
                            self.flaggedAngles.append(fData.endVertex)
                            self.flaggedAngleMessages.append('Outflow angle is {0:.2f}'.format(outFlowAngle))
                            
    def checkCover(self, fData):
        """
        Checks the ground cover against the pipe obvert.
        
        :param fData: FeatureData
        :return: void
        """
        
        # get pipe obvert
        if fData.type.upper() == 'C' or fData.type.upper() == 'R':
            if fData.invertUs != -99999 and fData.invertDs != -99999:
                dData = self.dataCollector.drapes[fData.id]
                chainages = dData.chainages
                if fData.type.upper() == 'C':
                    height = fData.width
                else:
                    height = fData.height
                obverts = interpolateObvert(fData.invertUs, fData.invertDs, height, chainages)
                for i, obvert in enumerate(obverts):
                    ground = dData.elevations[i]
                    point = dData.points[i]
                    if ground is not None:
                        cover = ground - obvert
                        if cover < self.limitCover:
                            uniqueId = (point.x(), point.y())
                            if uniqueId not in self.flaggedCoverUniqueIds:
                                self.flaggedCoverUniqueIds.append(uniqueId)
                                self.flaggedCoverIds.append(uniqueId)
                                self.flaggedCover.append(point)
                                self.flaggedCoverMessages.append("Pipe cover drops below limit")
                            break
            
    def getAngle(self, ids, whichEnd):
        """
        
        :param ids:
        :return:
        """

        # if no downstream network return None
        if not ids:
            return None
        # if current ids area all x connectors the return none
        func = lambda x: 1 if '__connector__' in x else 0
        if len(ids) == sum([func(x) for x in ids]):
            return None
        
        angle = []
        for id in ids:
            if '__connector__' in id:
                continue
            
            if id not in self.dataCollector.drapes:
                continue
            dData = self.dataCollector.drapes[id]
            if len(dData.directions) > 1:
                if whichEnd == NETWORK.Downstream:
                    angle.append(dData.directions[-1])
                elif whichEnd == NETWORK.Upstream:
                    angle.append(dData.directions[1])
        
        if not angle:
            return None
        else:
            return angle
    
    def getInvert(self, ids, whichDirection):
        """
        
        :param ids:
        :param whichDirection:
        :return:
        """

        # if no downstream network return None
        if not ids:
            return None
        # check there is something downstream - there can
        # be an x-connector that has nothing downstream
        if [self.checkConnectionExists(x, whichDirection) for x in ids].count(True) == 0:
            return None
        # if current ids area all x connectors the return none
        func = lambda x: 1 if '__connector__' in x else 0
        if len(ids) == sum([func(x) for x in ids]):
            return None
        
        invert = 99999
        for id in ids:
            if '__connector__' in id:
                ids += self.correctForConnectors(id, whichDirection)
                continue
            
            if id not in self.dataCollector.features:
                continue
            fData = self.dataCollector.features[id]
            if fData.invertUs != -99999:
                invert = min(invert, fData.invertUs)
        
        if invert == 99999:
            return None
            
        return invert
    
    def getTotalArea(self, ids, whichEnd):
        """
        Calculates the total area from the list of pipe ids.
        Will consider X connectors and get next downstream connection.
        
        :param ids: list -> str ids (not pipe id)
        :return: float
        """
        
        # if no downstream network return None
        if not ids:
            return None
        # check there is something downstream - there can
        # be an x-connector that has nothing downstream
        if [self.checkConnectionExists(x, whichEnd) for x in ids].count(True) == 0:
            return None
        # if current ids area all x connectors the return none
        func = lambda x: 1 if '__connector__' in x else 0
        if len(ids) == sum([func(x) for x in ids]):
            return None
        
        totalArea = 0.0
        for id in ids:
            if '__connector__' in id:
                ids += self.correctForConnectors(id, whichEnd)
                continue
            
            if id not in self.dataCollector.features:
                continue
            fData = self.dataCollector.features[id]
            if fData.type.upper() == 'R':
                totalArea += fData.numberOf * fData.width * fData.height
            elif fData.type.upper() == 'C':
                totalArea += fData.numberOf * pi * (fData.width / 2.0) ** 2
        
        if totalArea == 0:
            return None
        else:
            return totalArea
    
    def checkConnectionExists(self, id, whichDirection):
        """
        
        :param id: str
        :param whichDirection: NETWORK
        :return: bool
        """
        
        if '__connector__' in id:
            if self.correctForConnectors(id, whichDirection):
                return True
            else:
                return False
            
        return True
        
    def correctForConnectors(self, id, whichDirection):
        """
        Returns the next upstream or downstream pipe from an x-connector
        
        :param id: str
        :param whichEnd: NETWORK which way to go from x-connector
        :return: list -> str id
        """
        
        if whichDirection == NETWORK.Upstream:
            return self.dataCollector.connections[id].linesUs
        elif whichDirection == NETWORK.Downstream:
            return self.dataCollector.connections[id].linesDs
        elif whichDirection == NETWORK.UpstreamUpstream:
            return self.dataCollector.connections[id].linesUsUs
