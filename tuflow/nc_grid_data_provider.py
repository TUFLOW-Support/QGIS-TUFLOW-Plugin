import re
from datetime import datetime, timedelta

import numpy as np
from qgis._core import QgsGeometry, QgsFeature, QgsPointXY, QgsWkbTypes, QgsMapLayer
from qgis.core import QgsRasterLayer, QgsSingleBandPseudoColorRenderer, QgsColorRampShader, QgsStyle
from PyQt5.QtCore import pyqtSignal

try:
    from netCDF4 import Dataset
    netcdf_loaded = True
except ImportError:
    netcdf_loaded = False


class LoadError(Exception):
    pass


class NetCDFGrid(QgsRasterLayer):

    nameChanged = pyqtSignal()

    def __init__(self, uri='', base_name='', provider_type='gdal', layer_options=QgsRasterLayer.LayerOptions(),
                 existing_layer=None, **kwargs):
        if not netcdf_loaded:
            raise LoadError('NetCDF4 Python library not installed. Please see the following wiki page for more information:<p>'
                            '<a href="https://wiki.tuflow.com/index.php?title=TUFLOW_Viewer_-_Load_Results_-_NetCDF_Grid"'
                            '<span style=" text-decoration: underline; color:#0000ff;">wiki.tuflow.com/index.php?title=TUFLOW_Viewer_-_Load_Results_-_NetCDF_Grid'
                            '</span></a>')

        self.fid = None
        self.canvas = None
        self._nc_file = ':'.join(uri.split(':')[1:-1])
        self._lyr_name = uri.split(':')[-1]
        self._existing_layer = bool(existing_layer)

        if not self.is_nc_grid(self._nc_file):
            raise LoadError('Format is not recognised as a NetCDF raster.')

        # load as raster layer
        if existing_layer is None:
            QgsRasterLayer.__init__(self, uri, base_name, provider_type, layer_options)
            if not self.isValid():
                raise LoadError('Failed to initialise QgsRasterLayer for {0} - Check if there is data'.format(uri))
            self._lyr = self
        else:
            QgsRasterLayer.__init__(self)
            self._lyr = existing_layer
        self._lyr.nameChanged.connect(self._name_changed)

        self._dp = self._lyr.dataProvider()

        # load grid properties
        self.dx = self._lyr.rasterUnitsPerPixelX()
        self.dy = self._lyr.rasterUnitsPerPixelY()
        self.ox = self._lyr.extent().xMinimum()
        self.oy = self._lyr.extent().yMinimum()

        # get time data
        self.units = 'h'
        with Dataset(self._nc_file) as nc:
            self.reference_time = self._reference_time(nc, **kwargs)
            self.static = self._is_static(nc)
            self.times = self._times(nc)

        # get min/max data for rendering - this is what can slow down loading
        self._min, self._max = 9e29, -9e29
        with Dataset(self._nc_file, 'r') as nc:
            max_dataset = 'maximum_{0}'.format(self._lyr_name)  # try and be clever and find maximum dataset
            dataset = max_dataset if max_dataset in nc.variables else self._lyr_name
            ds = nc.variables[dataset][:]
            if np.ma.is_masked(np.nanmin(ds)) and np.nanmin(ds).mask.all():
                ds = nc.variables[self._lyr_name][:]
            self._min = min(self._min, np.nanmin(ds))
            self._max = max(self._max, np.nanmax(ds))

        # apply a default renderer - could replace later with result type specific defaults
        self._renderer = None
        self._curr_band = 0
        self._set_raster_renderer_to_band(1)

    def id(self):
       return QgsRasterLayer.id(self._lyr)

    def triggerRepaint(self):
        return QgsRasterLayer.triggerRepaint(self._lyr)

    def name(self):
        return QgsRasterLayer.name(self._lyr)

    def setDataSource(self, dataSource, baseName, provider, *__args):
        uri = 'NETCDF:{0}:{1}'.format(dataSource, self._lyr_name)
        self._nc_file = dataSource
        super().setDataSource(uri, baseName, provider, *__args)
        with Dataset(self._nc_file) as nc:
            self.times = self._times(nc)

    def update_band(self, band_number):
        if band_number is None:
            return

        self._set_raster_renderer_to_band(band_number)

    def connect_temporal_controller(self, qgs_canvas):
        self.canvas = qgs_canvas
        qgs_canvas.temporalRangeChanged.connect(self.update_band_from_time)

    def update_band_from_time(self, temporal_range=None):
        if temporal_range is None and (not self.canvas or not self.canvas.temporalRange().begin().isValid()):
            return
        if temporal_range is None:
            temporal_range = self.canvas.temporalRange()
        dt = temporal_range.begin()
        dt = datetime(dt.date().year(), dt.date().month(), dt.date().day(), dt.time().hour(), dt.time().minute(), dt.time().second())
        time = (dt - self.reference_time).total_seconds() / 3600.
        band = self.get_band_from_time(time)
        self.update_band(band)
        self.triggerRepaint()

    def _name_changed(self):
        self.nameChanged.emit()

    def timesteps(self, time_type='relative'):
        for time in self.times:
            if time_type == 'relative':
                yield time
            else:
                if self.units == 'h':
                    yield self.reference_time + timedelta(hours=time)
                elif self.units == 's':
                    yield self.reference_time + timedelta(seconds=time)
                else:
                    raise NotImplementedError('Temporal unit not supported: {0}'.format(self.units))

    def get_band_from_time(self, time):
        if self.static:
            return 1

        i = 1
        for i, time_ in enumerate(self.times):
            if abs(time_ - time) < 0.001:
                return i + 1
            elif time_ > time:
                if abs(time_ - time) * 3600. > 0.001:
                    return i
                return i + 1

        return i

    def open(self):
        if self.fid is None:
            self.fid = Dataset(self._nc_file, 'r')

    def close(self):
        if self.fid is not None:
            self.fid.close()
            self.fid = None

    def set_reference_time(self, datetime):
        self.reference_time = datetime

    def _set_raster_renderer_to_band(self, band_number):
        if self.static:
            band_number = 1
        if self._curr_band == band_number:
            return
        self._curr_band = band_number
        if self._renderer is None:
            colour_ramp_gradient = QgsStyle().defaultStyle().colorRamp('Spectral')
            colour_ramp_gradient.invert()
            self._renderer = QgsSingleBandPseudoColorRenderer(self._dp, band_number)
            self._renderer.setClassificationMin(self._min)
            self._renderer.setClassificationMax(self._max)
            self._renderer.createShader(colour_ramp_gradient, QgsColorRampShader.Interpolated,
                                        QgsColorRampShader.Continuous, 5)
            self._lyr.setRenderer(self._renderer)
        else:
            self._renderer = self._lyr.renderer()
            if isinstance(self._renderer, QgsSingleBandPseudoColorRenderer):
                self._renderer.setBand(band_number)

    def _is_static(self, nc):
        shape = nc.variables[self._lyr_name].shape
        if len(shape) == 3:
            return shape[0] == 1

        return True

    def _times(self, nc):
        if self.reference_time is None:
            return []

        if self.static:  # self.static may not be populated at this stage
            return []

        return nc.variables['time'][:].tolist()

    def _reference_time(self, nc, default_reference_time=None, **kwargs):
        if 'time' not in nc.variables:
            return

        units = nc.variables['time'].units
        if 'hour' in units:
            self.units = 'h'
        elif 'second' in units:
            self.units = 's'
        else:
            self.units = units.split(' ')[0]

        if not re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', units):
            if default_reference_time:
                return default_reference_time
            return datetime(2000, 1, 1)  # a default value

        return datetime.strptime(re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', units)[0], '%Y-%m-%d %H:%M')

    @staticmethod
    def is_nc_grid(nc_file_path):
        if not netcdf_loaded:
            return False

        for _ in NetCDFGrid.nc_grid_layers(nc_file_path):
            return True

    @staticmethod
    def nc_grid_layers(nc_file_path):
        if not netcdf_loaded:
            return []

        try:
            with Dataset(nc_file_path, 'r') as nc:
                x_dims = [name for name, dim in nc.dimensions.items() if name in nc.variables and hasattr(nc.variables[name], 'axis') and nc.variables[name].axis == 'X']
                y_dims = [name for name, dim in nc.dimensions.items() if name in nc.variables and hasattr(nc.variables[name], 'axis') and nc.variables[name].axis == 'Y']
                for name, var in nc.variables.items():
                    if len(var.shape) == 3:
                        i, j = 1, 2
                    elif len(var.shape) == 2:
                        i, j = 0, 1
                    else:
                        continue
                    if var.dimensions[i] in y_dims and var.dimensions[j] in x_dims:
                        yield name
        except Exception:
            return

    @staticmethod
    def capable():
        return netcdf_loaded


class NetCDFGridGeometry:
    """Class for helping to do geometry algorithms."""

    def __init__(self, nc_grid):
        """
        :param nc_grid: NetCDFGrid
        :return: None
        """
        self._nc_grid = nc_grid

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
            for line in PolylineHelper(polyline, self._nc_grid):
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

        x = self._nc_grid.fid.variables['x'][index[0]] - self._nc_grid.dx / 2.
        y = self._nc_grid.fid.variables['y'][index[1]] - self._nc_grid.dy / 2.
        x_ = [x, x, x + self._nc_grid.dx, x + self._nc_grid.dx, x]
        y_ = [y, y + self._nc_grid.dy, y + self._nc_grid.dy, y, y]
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
            for line in PolylineHelper(polyline, self._nc_grid):
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


class PointHelper:
    """Helper to hold point data and convert to integer values."""

    def __init__(self, p, nc_grid):
        self.x = p.x()
        self.y = p.y()
        self.xi, self.yi = self.coord_to_int(nc_grid)

    def coord_to_int(self, nc_grid):
        """
        Return point x, y coords as integer values i,j.

        :param p: QgsPointXY
        :return: tuple[int,int]
        """
        i = int((self.x - nc_grid.ox) / nc_grid.dx)
        j = int((self.y - nc_grid.oy) / nc_grid.dy)

        if i < 0 or i >= nc_grid.width():
            raise Exception('i coordinate outside raster limit')
        if j < 0 or j >= nc_grid.height():
            raise Exception('j coordinate outside raster limit')

        return i, j


class LineHelper:
    """Helper to hold data in a custom class."""

    def __init__(self, p1, p2, nc_grid, index):
        self.p1 = PointHelper(p1, nc_grid)
        self.p2 = PointHelper(p2, nc_grid)
        self.index = index
        self._nc_grid = nc_grid

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

    def __init__(self, line, nc_grid):
        self.line = line
        self._nc_grid = nc_grid

    def __iter__(self):
        for i in range(1, len(self.line)):
            yield LineHelper(self.line[i-1], self.line[i], self._nc_grid, i)

    @staticmethod
    def distance_to_point(polyline, index, point):
        polyline_ = polyline[:]
        polyline_.insert(index, point)
        return QgsGeometry.fromPolylineXY(polyline_).distanceToVertex(index)