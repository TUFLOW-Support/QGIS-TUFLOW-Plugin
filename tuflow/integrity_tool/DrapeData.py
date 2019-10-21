from qgis.core import *
from .Enumerators import *
from tuflow.tuflowqgis_library import lineToPoints, getRasterValue


class DrapeData():
    """
    Class for storing draped and elevation data
    relating to the DEM (not 1D inverts)

    """

    def __init__(self, iface, id=None, layer=None, feature=None, dem=None):
        self.id = id
        self.points = []
        self.chainages = []
        self.directions = []
        self.elevations = []

        if layer is not None:
            if layer.geometryType() == QgsWkbTypes.PointGeometry:
                point = feature.geometry().asPoint()
                chainage = 0
                elevations = getRasterValue(point, dem) if dem is not None else None
                self.points = [point]
                self.chainages = [chainage]
                self.elevations = [elevations]
                self.directions = None
            elif layer.geometryType() == QgsWkbTypes.LineGeometry:
                if dem is not None:
                    demCellSize = max(dem.rasterUnitsPerPixelX(), dem.rasterUnitsPerPixelY())
                else:
                    demCellSize = 99999  # only get vertexes if no dem drape is needed
                if iface is not None:
                    units = iface.mapCanvas().mapUnits()
                else:
                    units = QgsUnitTypes.DistanceMeters
                points, chainages, directions = lineToPoints(feature, demCellSize, units)
                elevations = []
                for point in points:
                    elevation = getRasterValue(point, dem) if dem is not None else None
                    elevations.append(elevation)
                self.points = points
                self.chainages = chainages
                self.elevations = elevations
                self.directions = directions
