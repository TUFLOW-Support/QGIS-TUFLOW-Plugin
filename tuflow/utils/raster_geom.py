import numpy as np
from qgis.core import QgsFeature, QgsGeometry, QgsPoint, QgsPointXY, QgsWkbTypes


class RasterGeometry:
    """Class for helping to do geometry algorithms."""

    def __init__(self, raster):
        """
        :param nc_grid: NetCDFGrid
        :return: None
        """
        self.raster_info = RasterInfo(raster)

    def select_cells_from_linestring(self, linestring):
        """
        Return cell indexes from a linestring.

        :param linestring: QgsPolylineXY | QgsMultiPolylineXY
        :return: nd.array[[int, int]] - 2D array i,j cell indexes
        """
        if len(linestring) and not isinstance(linestring[0], list):
            multi_linestring = [linestring]
        else:
            multi_linestring = linestring

        selection = []
        for polyline in multi_linestring:
            for line in PolylineHelper(polyline, self.raster_info):
                sel = self._select_along_line(line.p1, line.p2, line.octant())
                if not sel:
                    continue
                if selection and sel[0] == selection[-1]:
                    sel = sel[1:]
                selection.extend(sel)

        return np.array(selection)

    def index_to_polygon(self, index, octant=None):
        """
        Returns QgsFeature with a polygon geometry of grid cell based on the coordinate index (i,j) (cell centre).
        Optional octant argument in case i,j need to be flipped.

        :param index: tuple[int,int]
        :param octant: int
        :return: QgsFeature
        """
        if octant is not None:
            index = self._octant_coords(index[0], index[1], octant)

        x, y = self.raster_info.cell_lower_left_at_index(index[0], index[1])
        x_ = [x, x, x + self.raster_info.dx, x + self.raster_info.dx, x]
        y_ = [y, y + self.raster_info.dy, y + self.raster_info.dy, y, y]
        f = QgsFeature()
        g = QgsGeometry.fromPolygonXY([[QgsPointXY(x, y) for x, y in zip(x_, y_)]])
        f.setGeometry(g)
        return f

    def intersects_along_linestring(self, linestring, indexes):
        """
        Returns locations of cells side intersects along linestring.

        :param linestring: QgsPolylineXY | QgsMultiPolylineXY
        :param indexes: list[tuple[int,int]] - list i,j grid indexes
        :return: tuple[list[QgsPointXY], list[float]] - intersect points, distance from line start
        """
        if len(linestring) and not isinstance(linestring[0], list):
            polyline = linestring[:]
        else:
            polyline = sum(linestring, [])

        intersects, chainages = [], []
        for index in indexes:
            for line in PolylineHelper(polyline, self.raster_info):
                if index[0] < 0 or index[0] > self.raster_info.ncol or index[1] < 0 or index[1] > self.raster_info.nrow:
                    continue
                intersection = self._intersection(index[0], index[1], line)
                if intersection is None:
                    continue

                if intersection.type() == QgsWkbTypes.PointGeometry:
                    points = intersection.asMultiPoint() if intersection.isMultipart() else [intersection.asPoint()]
                elif intersection.type() == QgsWkbTypes.LineGeometry:
                    points = intersection.asMultiPolyline() if intersection.isMultipart() else [intersection.asPolyline()]
                    points = sum(points, [])
                else:
                    points = []

                for point in points:
                    chainage = PolylineHelper.distance_to_point(polyline, line.index, point)
                    if chainages and np.isclose(chainage, chainages[-1]):
                        continue
                    intersects.append(point)
                    chainages.append(chainage)

        return intersects, chainages

    def points_along_linestring(self, line_geom):
        if line_geom.isMultipart():
            linestring = sum(line_geom.asMultiPolyline(), [])
        else:
            linestring = line_geom.asPolyline()
        fcs = self.select_cells_from_linestring(linestring)
        inters, chainages = self.intersects_along_linestring(linestring, fcs)

        locked_ch = []
        if line_geom.isMultipart():
            for line in line_geom.asMultiPolyline():
                if self.raster_info.contains(line[0]):
                    locked_ch.append(0.)
                if self.raster_info.contains(line[-1]):
                    locked_ch.append(QgsGeometry.fromPolyline(line).distanceToVertex(len(line)-1))
        else:
            line = line_geom.asPolyline()
            if self.raster_info.contains(line[0]):
                locked_ch.append(0.)
            if self.raster_info.contains(line[-1]):
                locked_ch.append(line_geom.length())

        out_info = []
        for i, (ch1, inter1) in enumerate(zip(chainages[1:], inters[1:])):
            ch0 = chainages[i]
            inter0 = inters[i]
            if np.isclose(ch0, locked_ch, atol=0.0001, rtol=0.).any():
                ch_ = ch0
                inter_ = inter0
            elif np.isclose(ch1, locked_ch, atol=0.0001, rtol=0.).any():
                ch_ = ch1
                inter_ = inter1
            else:
                ch_ = (ch1 - ch0) / 2 + ch0
                inter_ = line_geom.interpolate(ch_)
            if isinstance(inter_, QgsGeometry):
                inter_ = QgsPointXY(inter_.asPoint())
            out_info.append((ch_, inter_))

        return sorted(out_info, key=lambda x: x[0])

    def _select_along_line(self, p0, p1, octant):
        """
        Return selected cells along line.

        Returns all cells selected by line, regardless of cross-hair intersection. Cells are return in order of
        selection based on line direction.

        :param p0: tuple[int,int] - start point i,j
        :param p1: tuple[int,int] - end point i,j
        :octant: int - octant of line
        """
        if octant in [1, 4, 5, 8]:
            x0, x1, y0, y1 = p0.xi, p1.xi, p0.yi, p1.yi
        else:  # [2, 3, 6, 7]
            x0, x1, y0, y1 = p0.yi, p1.yi, p0.xi, p1.xi

        dx = x1 - x0
        dy = y1 - y0
        xi, yi = 1, 1
        if dx < 0:
            xi = -1
        if dy < 0:
            yi = -1
        dx, dy = abs(dx), abs(dy)
        d = 2 * dy - dx
        y = y0

        selection = []
        for x in range(x0, x1 + xi, xi):
            # check line intersects cell and also check cells on either side. - ruins elegance and speed a little :(
            if self._intersect(x, y - yi, p0, p1, octant):
                selection.append(self._octant_coords(x, y - yi, octant))
            if self._intersect(x, y, p0, p1, octant):
                selection.append(self._octant_coords(x, y, octant))
            if self._intersect(x, y + yi, p0, p1, octant):
                selection.append(self._octant_coords(x, y + yi, octant))

            if d > 0:
                y += yi
                d = d + (2 * (dy - dx))
            else:
                d += 2 * dy

        return selection

    def _octant_coords(self, x, y, octant):
        """
        Returns coordinates considering the octant - x, y could be flipped.

        :param x: int | float
        :param y: int | float
        :param octant: int
        :return: tuple[int,int] | tuple[float,float]
        """
        if octant in [1, 4, 5, 8]:
            return x, y
        else:  # [2, 3, 6, 7]
            return y, x

    def _intersect(self, i, j, p0, p1, octant):
        """
        Checks for intersection between grid cell at coordinate i,j and a line segment.

        :param i: int
        :param j: int
        :param p0: PointHelper
        :param p1: PointHelper
        :param octant: int
        :return: bool
        """
        line_geom = QgsGeometry.fromPolylineXY([QgsPointXY(p0.x, p0.y), QgsPointXY(p1.x, p1.y)])
        return self.index_to_polygon((i, j), octant).geometry().intersects(line_geom)

    def _intersection(self, i, j, line):
        """
        Returns intersection point between grid cell at coordinate i,j and a polyline.

        :param i: int
        :param j: int
        :param line: LineHelper
        :return: QgsGeometry
        """
        line_geom = QgsGeometry.fromPolylineXY([QgsPointXY(p.x, p.y) for p in line])
        return self.index_to_polygon((i, j), 1).geometry().intersection(line_geom)


class RasterInfo:

    def __init__(self, qgsraster):
        self.qgsraster = qgsraster
        self.dx = qgsraster.rasterUnitsPerPixelX()
        self.dy = qgsraster.rasterUnitsPerPixelY()
        self.ox = qgsraster.extent().xMinimum()
        self.oy = qgsraster.extent().yMinimum()
        self.ncol = qgsraster.width()
        self.nrow = qgsraster.height()

    def cell_lower_left_at_index(self, i, j):
        return self.ox + i * self.dx, self.oy + j * self.dy

    def contains(self, point):
        return self.qgsraster.extent().contains(point)



class PointHelper:
    """Helper to hold point data and convert to integer values."""

    def __init__(self, p, nc_grid):
        self.x = p.x()
        self.y = p.y()
        self.xi, self.yi = self.coord_to_int(nc_grid)
        self.outside_raster = False

    def coord_to_int(self, raster_info):
        """
        Return point x, y coords as integer values i,j.

        :param p: QgsPointXY
        :return: tuple[int,int]
        """
        i = int((self.x - raster_info.ox) / raster_info.dx)
        j = int((self.y - raster_info.oy) / raster_info.dy)

        if i < 0 or i >= raster_info.ncol:
            self.outside_raster = True
        if j < 0 or j >= raster_info.nrow:
            self.outside_raster = True

        return i, j


class LineHelper:
    """Helper to hold data in a custom class."""

    def __init__(self, p1, p2, raster_info, index):
        self.p1 = PointHelper(p1, raster_info)
        self.p2 = PointHelper(p2, raster_info)
        self.index = index
        self.raster_info = raster_info

    def __iter__(self):
        yield self.p1
        yield self.p2

    def __getitem__(self, item):
        if isinstance(item, int):
            if item == 0:
                return self.p1
            elif item == 1:
                return self.p2
            else:
                raise IndexError('Index out of range - allowed values are 0 or 1')
        else:
            raise TypeError('Index must be an integer value - allowed values are 0 or 1')

    def octant(self):
        """
        Return the octant of the line segment.

        Convention:
            1 = +dx, +dy, dx larger
            2 = +dx, +dy, dy larger
            3 = -dx, +dy, dy larger
            4 = -dx, +dy, dx larger
            5 = -dx, -dy, dx larger
            6 = -dx, -dy, dy larger
            7 = +dx, -dy, dy larger
            8 = +dx, -dy, dx larger

        :return: int
        """

        dx = self.p2.xi - self.p1.xi
        dy = self.p2.yi - self.p1.yi
        dx_larger = abs(dx) >= abs(dy)

        if dx > 0 and dy > 0 and dx_larger:
            return 1
        elif dx > 0 and dy > 0:
            return 2
        elif dx < 0 and dy > 0 and not dx_larger:
            return 3
        elif dx < 0 and dy > 0:
            return 4
        elif dx < 0 and dx_larger:
            return 5
        elif dx < 0:
            return 6
        elif not dx_larger:
            return 7
        else:
            return 8


class PolylineHelper:
    """Helper to make looping through segments more Pythonic."""

    def __init__(self, line, raster_info):
        self.line = line
        self.raster_info = raster_info

    def __iter__(self):
        for i in range(1, len(self.line)):
            yield LineHelper(self.line[i-1], self.line[i], self.raster_info, i)

    @staticmethod
    def distance_to_point(polyline, index, point):
        polyline_ = polyline[:]
        polyline_.insert(index, point)
        return QgsGeometry.fromPolylineXY(polyline_).distanceToVertex(index)