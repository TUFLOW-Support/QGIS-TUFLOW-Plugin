import re
import typing
from datetime import datetime, timedelta
from math import cos, sin, asin, sqrt, radians

from tuflow.compatibility_routines import Path
import numpy as np

try:
    from netCDF4 import Dataset
except ImportError:
    from tuflow.netCDF4_ import Dataset_ as Dataset

try:
    from tuflow.gui.logging import Logging
    has_logging = True
except ImportError:
    has_logging = False

from osgeo import ogr
if not ogr.GetUseExceptions():
    try:
        ogr.UseExceptions()
    except RuntimeError:
        pass

try:
    import shapely
    has_shapely = True
except ImportError:
    has_shapely = False

from .utils import file_from_data_source, layer_name_from_data_source, get_driver_name_from_extension


PathLike = typing.Union[str, bytes, Path]
TimeLike = typing.Union[float, datetime]


def calc_distance(lat1, lon1, lat2, lon2):
    """    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km * 1000


def calc_length(points):
    """Calculate the length of a line defined by a series of points."""
    length = 0
    for i in range(1, len(points)):
        length += calc_distance(points[i - 1][1], points[i - 1][0], points[i][1], points[i][0])
    return length


class FVBCTideProvider:
    """Class for providing FV BC tide data to the TUFLOW Viewer class."""

    def __init__(self, nc_path: PathLike, gis_path: PathLike, use_local_time: bool = True) -> None:
        """
        Parameters
        ----------
        nc_path : PathLike
            Path to the netCDF file.
        gis_path : PathLike
            Path to the node string GIS file.
        label: str
            The boundary label / name within the netCDF file.
        """
        if not has_shapely:
            raise ImportError('Shapely is required for FVBCTideProvider')
        self.display_name = ''
        self.reference_time = None
        self.nc = FVBCTideNCProvider(nc_path, use_local_time)
        self.gis = FVBCTideGISProvider(gis_path)
        self.load()

    def __repr__(self) -> str:
        return f'FVBCTideProvider({self.nc.path.name}, {self.gis.path.name})'

    def load(self) -> None:
        """Loads the data from the netCDF and GIS files."""
        self.nc.open()
        self.gis.open()
        self.display_name = f'{Path(self.nc.path).stem}(TZ:{self.nc.tz})'
        self.reference_time = self.nc.reference_time
        self.gis_name = self.gis.name

    def close(self) -> None:
        """Closes the netCDF and GIS files."""
        self.nc.close()
        self.gis.close()

    def is_empty(self) -> bool:
        """Returns True if the netCDF or GIS files are empty.

        Returns
        -------
        bool
        """
        return self.nc.is_empty() or self.gis.is_empty()

    def is_fv_tide_bc(self) -> bool:
        """Returns True if the inputs look like FV tide boundary conditions.

        Returns
        -------
        bool
        """
        return self.nc.is_fv_tide_bc() and self.gis.is_fv_tide_bc()

    def get_crs(self) -> str:
        """Returns the CRS of the GIS file in the form of AUTHORITY:CODE.

        Returns
        -------
        str
        """
        return self.gis.get_crs()

    def get_ch_points(self, label: str) -> np.ndarray:
        """Returns the chainage as points along the node string GIS file from the
        FV Tide boundary based on the chainage values in the netCDF file.

        Returns a 2D array of shape (n, 2) where n is the number of points.

        Returns
        -------
        np.ndarray
        """
        return self.gis.get_ch_points(label, self.nc.get_chainages(label))

    def get_timesteps(self, fmt: str = 'relative') -> np.ndarray:
        """Returns the timesteps from the netCDF file. Returns from 'local_time' if available, otherwise
        returns from 'time'. The time format can be 'relative' (default) or 'datetime'/'absolute'.

        Returns a 1D array of shape (n,) where n is the number of timesteps.

        Parameters
        ----------
        fmt : str, optional
            The format of the timesteps. Default is 'relative'.

        Returns
        -------
        np.ndarray
        """
        return self.nc.get_timesteps(fmt)

    def get_section(self, label: str, time: TimeLike, data_at_ends: bool = False) -> np.ndarray:
        """Returns section data (i.e. long profile data) for a given time. Time can be passed in as
        either a float (relative time) or a datetime object.

        Returns a 2D array of shape (n, 2) where n is the number of points.

        Parameters
        ----------
        label : str
            The boundary name / label to get data for.
        time : float or datetime
            The time of the section data.
        data_at_ends : bool, optional
            If True, will ensure there are data points at the start and end of the line (will be set to nan
            if it is added).

        Returns
        -------
        np.ndarray
        """
        section = self.nc.get_section(label, time)
        if data_at_ends:
            if not np.isclose(section[0, 0], 0, rtol=0.):
                section = np.insert(section, 0, [[0, np.nan]], axis=0)
            length = self.gis.get_length(label)
            if not np.isclose(section[-1, 0], length, rtol=0.001):
                section = np.append(section, [[length, np.nan]], axis=0)
        return section

    def get_time_series(self, label: str, point_ind: int, time_fmt: str = 'relative') -> np.ndarray:
        """Returns time series data at a given point index. The time format can be 'relative' (default) or 'datetime'.

        Returns a 2D array of shape (n, 2) where n is the number of timesteps.

        Parameters
        ----------
        point_ind : int
            The index of the point.
        time_fmt : str, optional
            The format of the timesteps. Default is 'relative'.

        Returns
        -------
        np.ndarray
        """
        return self.nc.get_time_series(label, point_ind, time_fmt)

    def get_geometry(self, label: str) -> bytes:
        """Returns the geometry of the GIS line in a WKB format.

        Returns
        -------
        bytes
        """
        return self.gis.get_geometry(label)

    def get_labels(self) -> list[str]:
        """Returns the boundary labels in the netCDF file.

        Returns
        -------
        list[str]
        """
        return self.nc.labels


class FVBCTideGISProvider:

    def __init__(self, path: PathLike) -> None:
        self.path = path
        self._ds = None
        self._lyr = None
        self._points = {}
        self.name = None

    def __repr__(self) -> str:
        return f'FVBCTideGISProvider({self.path.name})'

    def open(self) -> None:
        dbpath = Path(file_from_data_source(str(self.path)))
        self.name = layer_name_from_data_source(str(self.path))
        driver_name = get_driver_name_from_extension('vector', dbpath.suffix)
        self._ds = ogr.GetDriverByName(driver_name).Open(str(dbpath))
        self._lyr = self._ds.GetLayer(self.name)

    def close(self) -> None:
        self._ds, self._lyr = None, None

    def is_empty(self) -> bool:
        return self._lyr.GetFeatureCount() == 0

    def is_fv_tide_bc(self) -> bool:
        return self._geometry_type() in [ogr.wkbLineString, ogr.wkbMultiLineString]

    def get_crs(self) -> str:
        sr = self._lyr.GetSpatialRef()
        return f'{sr.GetAuthorityName(None)}:{sr.GetAuthorityCode(None)}'

    def get_ch_points(self, label: str, chainages: np.ndarray) -> np.ndarray:
        if self.is_empty():
            return np.array([])
        if self._points.get(label.lower()) is None:
            feat = None
            for f in self._lyr:
                if f.GetField('ID').lower() == label.lower():
                    feat = f
                    break
            if feat is None:
                return np.array([])
            geom = feat.GetGeometryRef()
            linestring = shapely.from_wkb(bytes(geom.ExportToWkb()))
            if not self._lyr.GetSpatialRef().IsProjected():
                length = self.get_length(label)
                chainages = chainages / length
                points = np.array([linestring.interpolate(x, normalized=True).xy for x in chainages])
            else:
                points = np.array([linestring.interpolate(x).xy for x in chainages])
            if len(points.shape) == 3:
                points = points.reshape((points.shape[0], points.shape[1]))
            chs = np.reshape(chainages, (chainages.size, 1))
            points = np.append(chs, points, axis=1)
            self._points[label.lower()] = points
        return self._points.get(label.lower())

    def get_geometry(self, label: str) -> bytes:
        if self.is_empty():
            return b''
        feat = None
        for f in self._lyr:
            if f.GetField('ID').lower() == label.lower():
                feat = f
                break
        if feat is None:
            return b''
        geom = feat.GetGeometryRef()
        return bytes(geom.ExportToWkb())

    def get_length(self, label: str) -> float:
        if self.is_empty():
            return 0.
        feat = None
        for f in self._lyr:
            if f.GetField('ID').lower() == label.lower():
                feat = f
                break
        if feat is None:
            return 0.
        geom = feat.GetGeometryRef()
        linestring = shapely.from_wkb(bytes(geom.ExportToWkb()))
        if not self._lyr.GetSpatialRef().IsProjected():
            x, y = linestring.xy
            points = list(zip(x.tolist(), y.tolist()))
            return calc_length(points)
        return linestring.length

    def _geometry_type(self) -> int:
        geom_type = self._lyr.GetGeomType()
        while geom_type > 1000:
            geom_type -= 1000
        return geom_type


class FVBCTideNCProvider:

    def __init__(self, path: PathLike, use_local_time: bool) -> None:
        self.path = path
        self.labels = []
        self.use_local_time = use_local_time
        self.reference_time = datetime(1990, 1, 1)
        self.units = 'd'
        self.tz = 'UTC'
        self._timevar = 'time'
        self._nc = None
        self._units = ''  # full units string from nc file
        self._timesteps = None  # cache this data so we don't have to read it every time it's requested

    def __repr__(self):
        return f'FVBCTideNCProvider({self.path.name})'

    def open(self) -> None:
        self._nc = Dataset(self.path)
        self.load()

    def close(self) -> None:
        if self._nc:
            self._nc.close()
            self._nc = None

    def load(self) -> None:
        if self.use_local_time and 'local_time' not in self._nc.variables and has_logging:
            Logging.warning('Local time not available in netCDF file. Using UTC time instead.')
        self.use_local_time = 'local_time' in self._nc.variables and self.use_local_time
        self._timevar = 'local_time' if self.use_local_time else 'time'
        self._get_units()
        self.labels = [self._strip_label(k) for k, v in self._nc.variables.items() if v.ndim == 2 and v.dimensions[0] == 'time']

    def is_empty(self) -> bool:
        return False

    def is_fv_tide_bc(self) -> bool:
        return 'time' in self._nc.dimensions and len(self._nc.dimensions) > 1

    def get_timesteps(self, fmt: str) -> np.ndarray:
        if fmt == 'relative':
            return self._get_relative_timesteps()
        else:  # absolute or datetime
            return self._get_absolute_timesteps()

    def get_chainages(self, label: str) -> np.ndarray:
        chlabel = self._chainage_label(label)
        chainages = self._nc.variables[chlabel][:]
        return self._convert_from_masked_array(chainages)

    def get_section(self, label: str, time: TimeLike) -> np.ndarray:
        sect_label = self._section_label(label)
        time_ind = self._get_closest_timestep_index(time)
        y = self._nc.variables[sect_label][time_ind, :]
        x = np.ma.masked_where(y.mask, self.get_chainages(label))
        x = x.reshape((x.shape[0], 1))
        y = y.reshape((y.shape[0], 1))
        return np.ma.append(x, y, axis=1)

    def get_time_series(self, label: str, point_ind: int, time_fmt: str) -> np.ndarray:
        sect_label = self._section_label(label)
        if time_fmt == 'relative':
            timesteps = self._get_relative_timesteps()
        else:
            timesteps = self._get_absolute_timesteps()
        y = self._nc.variables[sect_label][:, point_ind]
        x = timesteps.reshape((timesteps.shape[0], 1))
        y = y.reshape((y.shape[0], 1))
        return np.ma.append(x, y, axis=1)

    def _strip_label(self, label: str) -> str:
        x = re.sub(r'^ns', '', label)
        x = re.sub(r'_wl$', '', x)
        return x

    def _section_label(self, label: str) -> str:
        return f'ns{label}_wl'

    def _chainage_label(self, label: str) -> str:
        return f'ns{label}_chainage'

    def _get_closest_timestep_index(self, time: TimeLike, tol: float = 0.01) -> int:
        if isinstance(time, datetime):
            time = (time - self.reference_time).total_seconds() / 3600
        timesteps = self._get_relative_timesteps()
        a = np.isclose(time, timesteps, atol=tol, rtol=0.)
        if a[a].any():
            return np.where(a)[0][0]
        else:
            if time < timesteps.min():
                return 0
            elif time > timesteps.max():
                return timesteps.size - 1
            i = np.argmin(np.absolute(timesteps - time))
            if timesteps[i] < time:
                return i
            return max(i - 1, 0)

    def _get_relative_timesteps(self) -> np.ndarray:
        # return in hours
        if self.units == 'd':
            return self._get_timesteps() * 24
        elif self.units == 's':
            return self._get_timesteps() / 3600
        return self._get_timesteps()

    def _get_absolute_timesteps(self) -> np.ndarray:
        return np.array([self.reference_time + timedelta(hours=float(ts)) for ts in self._get_relative_timesteps()])

    def _get_timesteps(self) -> np.ndarray:
        if self._timesteps is None:
            self._timesteps = self._nc.variables[self._timevar][:]
            self._timesteps = self._convert_from_masked_array(self._timesteps)
        return self._timesteps

    def _get_units(self) -> None:
        self._units = self._nc.variables[self._timevar].units
        rt = re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', self._units)
        if rt:
            self.reference_time = datetime.strptime(rt[0], '%Y-%m-%d %H:%M:%S')  # keep timezone naive for now (TUFLOW Viewer assumes UTC)
        if 'day' in self._units:
            self.units = 'd'
        elif 'hour' in self._units:
            self.units = 'h'
        elif 'sec' in self._units:
            self.units = 's'
        self.tz = self._nc.variables[self._timevar].timezone

    def _convert_from_masked_array(self, a: np.ma.MaskedArray) -> np.ndarray:
        if not isinstance(a, np.ma.MaskedArray):
            return a
        if not a.mask.any():
            return a.filled(0)
        if len(a.shape) == 1 or a.shape[1] == 1:
            return self._convert_from_masked_array_1d(a)
        return a

    def _convert_from_masked_array_1d(self, a: np.ma.MaskedArray) -> np.ndarray:
        x = np.arange(0, a.shape[0])
        xp = x[~a.mask]
        fp = a[~a.mask].filled(0)
        return np.interp(x, xp, fp)
