class TOOL_TYPE:
    Snapping = 0
    PipeDirection = 1
    Continuity = 2
    FlowTrace = 3
    UniqueIds = 4
    NullGeometry = 5


class X_OBJECT:
    IsFirst = 0
    IsSecond = 1


class GEOM_TYPE:
    Point = 0
    Line = 1
    Null = -1


class VERTEX:
    First = 0
    Last = 1
    Point = 2
    Null = -1
    
    
class NETWORK:
    Upstream = 0
    Downstream = 1
    UpstreamUpstream = 2


class LongPlotMessages:
    CollectingBranches = 0
    Populating = 1