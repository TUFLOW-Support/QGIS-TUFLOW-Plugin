from .Enumerators import *

class NetworkVertex():
    """
    Class for storing data for a 1d_nwk vertex. Used so upstream and downstream line vertexes can
    be differentiated.

    """

    def __init__(self, id=None, vertex=VERTEX.Null, layer=None, feature=None,
                 closestVertex=None, distanceToClosest=99999, snapped=False):
        self.id = id
        self.layer = layer
        self.feature = feature
        if feature is not None:
            self.fid = feature.id()
        else:
            self.fid = None
        self.vertex = vertex
        self.snapped = snapped
        self.closestVertex = closestVertex
        self.distanceToClosest = distanceToClosest
        self.tmpFid = None
        self.hasPoint = False
        self.point = None