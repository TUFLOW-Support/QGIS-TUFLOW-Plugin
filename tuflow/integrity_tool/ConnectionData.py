from .Enumerators import *

class ConnectionData():
    """
    Class for handling upstream and downstream connection data

    """

    def __init__(self, id):
        self.id = id

        # standard connections i.e. upstream or downstream flow
        self.linesUs = []
        self.linesDs = []
        self.pointUs = None
        self.pointDs = None

        # non-standard i.e. us to us or ds to ds
        self.linesUsUs = []
        self.linesDsDs = []

        # some data useful for determining X connector upstream and downstream direction
        self.xIn = False
        self.xInIndexDownstream = 0
        self.xInIndexesDownstream = []
        self.xInIndexUpstream = 0
        self.xInIndexesUpstream = []

    def getData(self, fData1, fData2, cData2=None, vDataUs=None, vDataDs=None, dataCollectorLine=None):
        """
        Get normal connection data

        :param fData1: FeatureData
        :param fData2: FeatureData
        :return: void
        """

        feature1StartVertex = fData1.startVertex
        feature1EndVertex = fData1.endVertex
        feature2StartVertex = fData2.startVertex
        feature2EndVertex = fData2.endVertex

        if feature1StartVertex == feature2EndVertex:
            vDataUs.snapped = True
            self.linesUs.append(fData2.id)
       
            # if point make sure to update line layer if the point information
            if fData1.geomType == GEOM_TYPE.Point and fData2.geomType == GEOM_TYPE.Line and cData2 is not None:
                cData2.pointDs = fData1.id
                if fData2.invertDs == -99999:
                    fData2.invertDs = fData1.invertDs + fData2.invertOffsetDs
                vname = '{0}{1}'.format(cData2.id, VERTEX.Last)
                if vname in dataCollectorLine.vertexes:
                    v = dataCollectorLine.vertexes[vname]
                    v.hasPoint = True
                    v.point = fData1.id
                
        elif feature1EndVertex == feature2StartVertex:
            self.linesDs.append(fData2.id)

            # if point make sure to update line layer if the point information
            if fData1.geomType == GEOM_TYPE.Point and fData2.geomType == GEOM_TYPE.Line and cData2 is not None:
                vDataUs.snapped = True
                cData2.pointUs = fData1.id
                if fData2.invertUs == -99999:
                    fData2.invertUs = fData1.invertDs + fData2.invertOffsetUs
                vname = '{0}{1}'.format(cData2.id, VERTEX.First)
                if vname in dataCollectorLine.vertexes:
                    v = dataCollectorLine.vertexes[vname]
                    v.hasPoint = True
                    v.point = fData1.id
            else:
                vDataDs.snapped = True
        else:
            if feature1StartVertex == feature2StartVertex:
                vDataUs.snapped = True
                self.linesUsUs.append(fData2.id)
            if feature1EndVertex == feature2EndVertex:
                vDataDs.snapped = True
                self.linesDsDs.append(fData2.id)

    def getConnectorData(self, fData1, fData2, connector, xIn=None, dataCollector=None, vDataUs=None, vDataDs=None):
        """
        Need to determine which way is upstream and which way is downstream for X connectors.
        This is annoyingly difficult.

        And populate relevant properties.

        :param fData1: FeatureData
        :param fData2: FeatureData
        :param connector: X_OBJECT
        :param xIn: bool
        :param dataCollector: DataCollector
        :return: void
        """

        feature1StartVertex = fData1.startVertex
        feature1EndVertex = fData1.endVertex
        feature2StartVertex = fData2.startVertex
        feature2EndVertex = fData2.endVertex

        if connector == X_OBJECT.IsFirst:
            if feature1StartVertex == feature2StartVertex:  # x connector is entering side channel
                vDataUs.snapped = True
                
                self.xIn = True

                self.xInIndexDownstream += 1
                self.linesDs.append(fData2.id)

                # remove previously thought downstream networks
                # - this can potentiall happen before we new this was an xIn
                for i in reversed(self.xInIndexesDownstream):
                    if len(self.linesDs) >= i:
                        self.linesDs.pop(i)

            elif feature1EndVertex == feature2StartVertex and not self.xIn:  # x connector leaving side channel
                if vDataDs is not None:
                    vDataDs.snapped = True
                
                self.xInIndexesDownstream.append(self.xInIndexDownstream)
                self.xInIndexDownstream += 1
                self.linesDs.append(fData2.id)
            elif feature1StartVertex == feature2EndVertex and not self.xIn:
                vDataUs.snapped = True
                
                self.xInIndexUpstream += 1
                self.linesUs.append(fData2.id)
            elif feature1EndVertex == feature2EndVertex and self.xIn:
                if vDataDs is not None:
                    vDataDs.snapped = True
                
                self.xInIndexUpstream += 1
                self.linesUs.append(fData2.id)
            elif feature1EndVertex == feature2EndVertex:
                if vDataDs is not None:
                    vDataDs.snapped = True
                
                self.xInIndexesUpstream.append(self.xInIndexUpstream)
                self.xInIndexUpstream += 1
                self.linesUs.append(fData2.id)
        elif connector == X_OBJECT.IsSecond:
            if xIn is not None:
                if xIn:
                    if feature1EndVertex == feature2EndVertex:
                        self.linesDs.append(fData2.id)
                        if vDataDs is not None:
                            vDataDs.snapped = True
                    elif feature1StartVertex == feature2StartVertex:
                        self.linesUs.append(fData2.id)
                        vDataUs.snapped = True
                    elif feature1StartVertex == feature2EndVertex:
                        self.linesUsUs.append(fData2.id)
                        vDataUs.snapped = True
                        # also add it to the connector data
                        connectorConnData = dataCollector.connections[fData2.id]
                        connectorConnData.linesUsUs.append(fData1.id)
                else:
                    if feature1EndVertex == feature2StartVertex:
                        self.linesDs.append(fData2.id)
                        if vDataDs is not None:
                            vDataDs.snapped = True
                    elif feature1StartVertex == feature2EndVertex:
                        self.linesUs.append(fData2.id)
                        vDataUs.snapped = True
                    elif feature1EndVertex == feature2EndVertex:
                        self.linesDsDs.append(fData2.id)
                        if vDataDs is not None:
                            vDataDs.snapped = True
                        # also add it to the connector data
                        connectorConnData = dataCollector.connections[fData2.id]
                        connectorConnData.linesDsDs.append(fData1.id)

    def correctConnectorUpstream(self):
        """
        Corrects some of the x connector information since now we have a better
        picture i.e. we know for sure whether this x connector is incoming
        or outgoing from the side channel.

        :param id: str
        :return: void
        """

        if not self.xIn:
            for i in reversed(self.xInIndexesUpstream):
                if len(self.linesUs) > i:
                    self.linesUs.pop(i)

