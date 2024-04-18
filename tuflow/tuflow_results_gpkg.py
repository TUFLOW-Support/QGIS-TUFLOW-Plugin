import re
import typing
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from sqlite3 import DatabaseError

import numpy as np

from .TUFLOW_results import ResData, ChanInfo, NodeInfo
from .compatibility_routines import Path
from .gui.logging import Logging


GisLayerType = typing.Union['QgsVectorLayer', 'ogr.Layer']
GisFeatureType = typing.Union['QgsFeature', 'ogr.Feature']


@dataclass
class Pos:
    x: float = field(default=None)
    y: float = field(default=None)
    valid: bool = field(default=False, init=False)

    def __post_init__(self):
        if self.x is None or self.y is None:
            return
        self.valid = True

    def __eq__(self, other):
        if not isinstance(other, Pos):
            return False
        return np.allclose([self.x, self.y], [other.x, other.y], rtol=0., atol=1e-6)


@dataclass
class Rect:
    x_min: float = field(default=None)
    y_min: float = field(default=None)
    x_max: float = field(default=None)
    y_max: float = field(default=None)
    width: float = field(default=None)
    height: float = field(default=None)
    valid: bool = field(default=False, init=False)

    def __post_init__(self):
        if self.x_min is None or self.y_min is None:
            return
        if self.x_max is None and self.width is None:
            return
        if self.y_max is None and self.height is None:
            return
        if self.x_max is not None and self.y_max is not None:
            self.valid = True
            return
        if self.x_max is None:
            self.x_max = self.x_min + self.width / 2.
            self.x_min = self.x_min - self.width / 2.
        if self.y_max is None:
            self.y_max = self.y_min + self.height / 2.
            self.y_min = self.y_min - self.height / 2.
        self.valid = True


class Feature:
    """Abstract feature so it can use libraries outside of QGIS."""

    def __init__(self, feat: GisFeatureType):
        self.feat = feat

    def __getitem__(self, item):
        pass

    def vertices(self) -> list[Pos]:
        pass

    def length(self) -> float:
        pass


class QgisFeature(Feature):

    def __getitem__(self, item):
        return self.feat[item]

    def vertices(self) -> list[Pos]:
        return [Pos(x.x(), x.y()) for x in self.feat.geometry().vertices()]

    def length(self) -> float:
        return self.feat.geometry().length()


class GdalFeature(Feature):
    pass



class GISDriver:
    """Abstract GIS driver so it can use libraries outside of QGIS."""

    def __new__(cls, layer: GisLayerType) -> 'GISDriver':
        try:
            from qgis.core import QgsVectorLayer
            has_qgis_lib = True
        except ImportError:
            has_qgis_lib = False
        try:
            from osgeo import gdal, ogr
            has_gdal_lib = True
        except ImportError:
            has_gdal_lib = False
        if has_qgis_lib and isinstance(layer, QgsVectorLayer):
            cls = QgisDriver
        elif has_gdal_lib and isinstance(layer, ogr.Layer):
            cls = GdalDriver
        elif not has_gdal_lib and not has_qgis_lib:
            raise ModuleNotFoundError('No GIS drivers available')
        else:
            raise NotImplementedError('GIS Driver not recognised: {0}'.format(type(layer)))
        self = object.__new__(cls)
        self._init(layer)
        return self

    def _init(self, layer: GisLayerType) -> None:
        self.layer = layer

    def still_alive(self) -> bool:
        return True

    def get_feature_by_field_value(self, field: str, value: str) -> GisFeatureType:
        pass

    def start_vertex_from_field_value(self, field: str, id_: str) -> Pos:
        pass

    def end_vertex_from_field_value(self, field: str, id_: str) -> Pos:
        pass

    def feat_is_ds_dir(self, pos: Pos, feat: GisFeatureType) -> bool:
        verts = feat.vertices()
        snapped = bool(verts) and pos == verts[0]
        return snapped

    def get_features_by_region(self, rect: Rect, timestep: float) -> typing.Generator[GisFeatureType, None, None]:
        pass

    def get_snapped_features_in_ds_dir(self, rect: Rect, pos: Pos, timestep: float) -> typing.Generator[GisFeatureType, None, None]:
        not_snapped = []
        for feat in self.get_features_by_region(rect, timestep):
            if feat['ID'] not in not_snapped and self.feat_is_ds_dir(pos, feat):
                yield feat
            else:
                not_snapped.append(feat['ID'])


class QgisDriver(GISDriver):

    def _init(self, layer: GisLayerType) -> None:
        super()._init(layer)
        self.si = None

    def still_alive(self) -> bool:
        try:
            self.layer.name()
            return True
        except RuntimeError:
            return False

    def get_feature_by_field_value(self, field: str, value: str) -> 'QgisFeature':
        from qgis.core import QgsFeatureRequest
        exp = '"{0}" = \'{1}\''.format(field, value)
        # use expression to get feature - use subset of attributes to speed up query - need geometry, so don't turn off
        req = QgsFeatureRequest().setFilterExpression(exp).setSubsetOfAttributes([field, 'Time_relative'], self.layer.fields())
        for feat in self.layer.getFeatures(req):
            return QgisFeature(feat)

    def start_vertex_from_field_value(self, field: str, id_: str) -> Pos:
        feat = self.get_feature_by_field_value(field, id_)
        if feat is None:
            return Pos()
        verts = feat.vertices()
        if verts:
            return verts[-1]
        return Pos()

    def end_vertex_from_field_value(self, field: str, id_: str) -> Pos:
        feat = self.get_featuret_by_field_value(field, id_)
        if feat is None:
            return Pos()
        verts = feat.vertices()
        if verts:
            return verts[-1]
        return Pos()

    def get_features_by_region(self, rect: Rect, timestep: float) -> typing.Generator[GisFeatureType, None, None]:
        from qgis.core import QgsFeatureRequest, QgsSpatialIndex, QgsRectangle
        if self.si is None:
            exp = '"Time_hours" = {0}'.format(timestep)
            req = QgsFeatureRequest().setFilterExpression(exp)
            self.si = QgsSpatialIndex(self.layer.getFeatures(exp))
        qgsrect = QgsRectangle(rect.x_min, rect.y_min, rect.x_max, rect.y_max)
        for fid in self.si.intersects(qgsrect):
            yield QgisFeature(self.layer.getFeature(fid))


class GdalDriver(GISDriver):
    # TODO: implement
    pass


class ResData_GPKG(ResData):

    def __init__(self):
        super().__init__()
        self.default_reference_time = datetime(1999, 12, 31, 14, 0, 0)
        self.has_reference_time = False
        self._display_name = ''
        self._fname = ''
        self._db = None
        self._cur = None
        self._keep_open = 0
        self._reference_time = None
        self._timesteps = None
        self._point_ts_types = None
        self._line_ts_types = None
        self._region_ts_types = None
        self._gis_point_layer_name = None
        self._gis_line_layer_name = None
        self._gis_region_layer_name = None
        self._gis_point_layer = None
        self._gis_line_layer = None
        self._gis_region_layer = None
        self._gis_point_feat_count = None
        self._gis_line_feat_count = None
        self._gis_region_feat_count = None
        self._saved_results = {}
        self.LP.id1 = None
        self.LP.id2 = None
        self.LP.loaded = False
        self.Channels = ChanInfo_GPKG(None)
        self.nodes = NodeInfo_GPKG(None)

    def __del__(self):
        self.close()

    @property
    def displayname(self) -> str:
        """Name displayed in TUFLOW Viewer."""
        if hasattr(self, '_display_name'):
            return self._display_name
        return ''

    @displayname.setter
    def displayname(self, name: str) -> None:
        """Set display name."""
        if hasattr(self, '_display_name'):
            self._display_name = name

    @property
    def reference_time(self) -> datetime:
        if self._reference_time is None:
            self._reference_time = self.get_reference_time()
        return self._reference_time

    @reference_time.setter
    def reference_time(self, rt: datetime) -> None:
        if hasattr(self, '_reference_time'):
            self._reference_time = rt

    @property
    def gis_point_layer_name(self) -> str:
        if self._gis_point_layer_name is None:
            try:
                self.open_db()
                self._cur.execute(
                    'SELECT'
                    ' DISTINCT Timeseries_info.Table_name '
                    'FROM'
                    ' Timeseries_info '
                    'INNER JOIN gpkg_geometry_columns'
                    ' ON Timeseries_info.Table_name = gpkg_geometry_columns.table_name '
                    'WHERE'
                    ' gpkg_geometry_columns.geometry_type_name = "POINT" LIMIT 1;'
                )
                ret = self._cur.fetchone()
                if ret:
                    self._gis_point_layer_name = ret[0]
            except Exception as e:
                Logging.warning(e)
            finally:
                self.close_db()

            if self._gis_point_layer_name is None and self.displayname:
                self._gis_point_layer_name = '{0}_P'.format(self.displayname)
        return self._gis_point_layer_name

    @gis_point_layer_name.setter
    def gis_point_layer_name(self, name: str) -> None:
        raise NotImplementedError('Cannot set GIS point layer name')

    @property
    def gis_line_layer_name(self) -> str:
        if self._gis_line_layer_name is None:
            try:
                self.open_db()
                self._cur.execute(
                    'SELECT'
                    ' DISTINCT Timeseries_info.Table_name '
                    'FROM'
                    ' Timeseries_info '
                    'INNER JOIN gpkg_geometry_columns'
                    ' ON Timeseries_info.Table_name = gpkg_geometry_columns.table_name '
                    'WHERE'
                    ' gpkg_geometry_columns.geometry_type_name = "LINESTRING" LIMIT 1;'
                )
                ret = self._cur.fetchone()
                if ret:
                    self._gis_line_layer_name = ret[0]
            except Exception as e:
                Logging.warning(e)
            finally:
                self.close_db()
            if self._gis_line_layer_name is None and self.displayname:
                self._gis_line_layer_name = '{0}_L'.format(self.displayname)
        return self._gis_line_layer_name

    @gis_line_layer_name.setter
    def gis_line_layer_name(self, name: str) -> None:
        raise NotImplementedError('Cannot set GIS line layer name')

    @property
    def gis_region_layer_name(self) -> str:
        if self._gis_region_layer_name is None:
            try:
                self.open_db()
                self._cur.execute(
                    'SELECT'
                    ' DISTINCT Timeseries_info.Table_name '
                    'FROM'
                    ' Timeseries_info '
                    'INNER JOIN gpkg_geometry_columns'
                    ' ON Timeseries_info.Table_name = gpkg_geometry_columns.table_name '
                    'WHERE'
                    ' gpkg_geometry_columns.geometry_type_name = "POLYGON" LIMIT 1;'
                )
                ret = self._cur.fetchone()
                if ret:
                    self._gis_region_layer_name = ret[0]
            except Exception as e:
                Logging.warning(e)
            finally:
                self.close_db()
            if self._gis_region_layer_name is None and self.displayname:
                self._gis_region_layer_name = '{0}_R'.format(self.displayname)
        return self._gis_region_layer_name

    @gis_region_layer_name.setter
    def gis_region_layer_name(self, name: str) -> None:
        raise NotImplementedError('Cannot set GIS region layer name')

    @property
    def gis_point_layer(self) -> GisLayerType:
        if self._gis_point_layer is not None and self._gis_point_layer.still_alive():
            return self._gis_point_layer.layer
        else:
            self._gis_point_layer = None

    @gis_point_layer.setter
    def gis_point_layer(self, layer: GisLayerType) -> None:
        try:
            self._gis_point_layer = GISDriver(layer)
        except (ModuleNotFoundError, NotImplementedError):
            pass

    @property
    def gis_line_layer(self) -> GisLayerType:
        if self._gis_line_layer is not None and self._gis_line_layer.still_alive():
            return self._gis_line_layer.layer
        else:
            self._gis_line_layer = None

    @gis_line_layer.setter
    def gis_line_layer(self, layer: GisLayerType) -> None:
        try:
            self._gis_line_layer = GISDriver(layer)
        except (ModuleNotFoundError, NotImplementedError):
            pass

    @property
    def gis_region_layer(self) -> GisLayerType:
        if self._gis_region_layer is not None and self._gis_region_layer.still_alive():
            return self._gis_region_layer.layer
        else:
            self._gis_region_layer = None

    @gis_region_layer.setter
    def gis_region_layer(self, layer: GisLayerType) -> None:
        try:
            self._gis_region_layer = GISDriver(layer)
        except (ModuleNotFoundError, NotImplementedError):
            pass

    @property
    def times(self) -> typing.List[float]:
        return self.timeSteps()

    @property
    def gis_point_feature_count(self) -> int:
        if self._gis_point_feat_count is None:
            try:
                self.open_db()
                self._cur.execute(
                    'SELECT'
                    ' Count '
                    'FROM'
                    ' Timeseries_info '
                    'WHERE'
                    ' Table_name = "{0}" LIMIT 1;'.format(self.gis_point_layer_name)
                )
                ret = self._cur.fetchone()
                if ret:
                    try:
                        self._gis_point_feat_count = int(ret[0])
                    except ValueError:
                        self._gis_point_feat_count = 0
                else:
                    self._gis_point_feat_count = 0
            except Exception as e:
                Logging.warning(e)
            finally:
                self.close_db()

        return self._gis_point_feat_count

    @gis_point_feature_count.setter
    def gis_point_feature_count(self, count: int) -> None:
        raise NotImplementedError('Cannot set GIS point feature count')

    @property
    def gis_line_feature_count(self) -> int:
        if self._gis_line_feat_count is None:
            try:
                self.open_db()
                self._cur.execute(
                    'SELECT'
                    ' Count '
                    'FROM'
                    ' Timeseries_info '
                    'WHERE'
                    ' Table_name = "{0}" LIMIT 1;'.format(self.gis_line_layer_name)
                )
                ret = self._cur.fetchone()
                if ret:
                    try:
                        self._gis_line_feat_count = int(ret[0])
                    except ValueError:
                        self._gis_line_feat_count = 0
                else:
                    self._gis_line_feat_count = 0
            except Exception as e:
                Logging.warning(e)
            finally:
                self.close_db()
        return self._gis_line_feat_count

    @gis_line_feature_count.setter
    def gis_line_feature_count(self, count: int) -> None:
        raise NotImplementedError('Cannot set GIS line feature count')

    @property
    def gis_region_feature_count(self) -> int:
        if self._gis_region_feat_count is None:
            try:
                self.open_db()
                self._cur.execute(
                    'SELECT'
                    ' Count '
                    'FROM'
                    ' Timeseries_info '
                    'WHERE'
                    ' Table_name = "{0}" LIMIT 1;'.format(self.gis_region_layer_name)
                )
                ret = self._cur.fetchone()
                if ret:
                    try:
                        self._gis_region_feat_count = int(ret[0])
                    except ValueError:
                        self._gis_region_feat_count = 0
                else:
                    self._gis_region_feat_count = 0
            except Exception as e:
                Logging.warning(e)
            finally:
                self.close_db()
        return self._gis_region_feat_count

    @gis_region_feature_count.setter
    def gis_region_feature_count(self, count: int) -> None:
        raise NotImplementedError('Cannot set GIS region feature count')

    @staticmethod
    def is_gpkg_ts_res(fname: Path) -> bool:
        """Routine determining if file is valid / compatible."""
        try:
            conn = sqlite3.connect(fname)
        except Exception as e:
            return False
        try:
            cur = conn.cursor()
            cur.execute('SELECT Version FROM TUFLOW_timeseries_version;')
            version = cur.fetchone()[0]
            valid = True
        except Exception as e:
            # No need to log. If the table doesn't exist, we just want to return valid as False
            # Logging.error(e, Logging.get_stack_trace())
            valid = False
        finally:
            conn.close()
        return valid

    def close(self) -> None:
        self.close_db()

    def open_db(self) -> None:
        if self._db is None:
            try:
                self._db = sqlite3.connect(self._fname)
                self._cur = self._db.cursor()
                self.Channels.cur = self._cur
                self.nodes.cur = self._cur
            except Exception as e:
                Logging.warning(e)
                raise e
        else:
            self._keep_open += 1

    def close_db(self) -> None:
        if self._db is not None:
            if not self._keep_open:
                try:
                    self._cur = None
                    self._db.close()
                    self._db = None
                    self.Channels.cur = None
                    self.nodes.cur = None
                except Exception as e:
                    Logging.warning(e)
                    raise e
            else:
                self._keep_open -= 1

    def Load(self, fname: str) -> typing.Tuple[bool, str]:
        """Load file. This routine just checks compatibility etc. Load data on the fly as needed."""
        err, msg = False, ''
        self.formatVersion = 2
        self._fname = Path(fname)
        self._display_name = re.sub(r'_swmm_ts', '', self._fname.stem)
        self.fpath = str(self._fname.parent)
        self.filename = self._fname.name
        self.Channels.parent = self
        self.nodes.parent = self
        if not self._fname.exists():
            err, msg = True, 'File {0} does not exist\n'.format(fname)
            return err, msg
        if not self.is_gpkg_ts_res(self._fname):
            err, msg = True, 'File {0} is not recognised as a compatible time series result'.format(self._fname)
            return err, msg

        try:
            self.open_db()
        except DatabaseError as e:
            err, msg = True, 'Error opening SQLite database: {0}'.format(e)
        finally:
            self.close_db()

        # gis layers
        self.GIS.P = r'{0}|layername={1}'.format(self._fname, self.gis_point_layer_name)
        self.GIS.L = r'{0}|layername={1}'.format(self._fname, self.gis_line_layer_name)
        self.GIS.R = None

        return err, msg

    def timestep_interval(self, layer_name: str, result_type: str) -> float:
        try:
            self.open_db()
            sql = 'SELECT dt FROM Timeseries_info WHERE Table_name = "{0}" and "Column_name" = "{1}";'.format(layer_name, result_type)
            self._cur.execute(sql)
            try:
                step = float(self._cur.fetchone()[0])
            except (TypeError, IndexError):
                step = 0.
        except Exception as e:
            Logging.error(e, Logging.get_stack_trace())
            step = 0.
        finally:
            self.close_db()
            return step

    def timeSteps(self, zero_time=None):
        if self._timesteps is not None:
            return self._timesteps
        timesteps = []
        try:
            self.open_db()
            for row in self._cur.execute('SELECT Time_relative FROM DatasetTimes;'):
                try:
                    timesteps.append(float(row[0]))
                except (ValueError, IndexError):
                    continue
        except Exception as e:
            Logging.warning(e)
        finally:
            self.close_db()
            self._timesteps = timesteps
            return self._timesteps

    def lineResultTypesLP(self) -> typing.List[str]:
        types = []
        types.append('Bed Level')
        if 'Water Level' in self.pointResultTypesTS():
            types.append('Water Level')
            types.append('Max Water Level')
        types.append('Culverts and Pipes')
        types.append('Pit Ground Levels (if any)')
        return types

    def pointResultTypesTS(self) -> typing.List[str]:
        if self._point_ts_types is None:
            self._point_ts_types = self.result_types_from_table(self.gis_point_layer_name)
        return self._point_ts_types

    def lineResultTypesTS(self) -> typing.List[str]:
        if self._line_ts_types is None:
            self._line_ts_types = self.result_types_from_table(self.gis_line_layer_name)
        return self._line_ts_types

    def regionResultTypesTS(self) -> typing.List[str]:
        if self._region_ts_types is None:
            self._region_ts_types = self.result_types_from_table(self.gis_region_layer_name)
        return self._region_ts_types

    def getTSData(self, id_: str, dom: str, res: str, geom: str) -> typing.Tuple[bool, list[float], str]:
        key = self.create_key(id_, res)
        if key in self._saved_results:
            return True, self._saved_results[key], ''

        if res in self.pointResultTypesTS():
            tbl = self.gis_point_layer_name
        elif res in self.lineResultTypesTS():
            tbl = self.gis_line_layer_name
        elif res in self.regionResultTypesTS():
            tbl = self.gis_region_layer_name
        else:
            return False, [0.], 'No data'

        y = []
        try:
            self.open_db()
            for row in self._cur.execute('SELECT "{0}" FROM "{1}" WHERE ID = "{2}";'.format(res, tbl, id_)):
                try:
                    y.append(float(row[0]))
                except (ValueError, IndexError):
                    continue
            err, data, msg = True, y, ''
        except Exception as e:
            Logging.error(e, Logging.get_stack_trace())
            err, data, msg = False, [0.], 'No data'
        finally:
            self.close_db()

        self._saved_results[key] = y

        return err, data, msg

    def result_types_from_table(self, table: str) -> typing.List[str]:
        types = []
        try:
            self.open_db()
            start = False
            for row in self._cur.execute('PRAGMA "main".TABLE_INFO("{0}");'.format(table)):
                if row[1] == 'Datetime':
                    start = True
                    continue
                if start:
                    types.append(row[1])
        except Exception as e:
            Logging.warning(e)
        finally:
            self.close_db()
            return types

    def parse_reference_time(self, string: str) -> datetime:
        if 'hour' in string:
            self.units = 'h'
        elif 'second' in string:
            self.units = 's'
        else:
            self.units = string.split(' ')[0]

        if not re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', string):
            return datetime(2000, 1, 1)  # a default value

        return datetime.strptime(re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', string)[0], '%Y-%m-%d %H:%M:%S')

    def get_reference_time(self) -> datetime:
        reference_time = self.default_reference_time
        try:
            self.open_db()
            self._cur.execute('SELECT Reference_time FROM Timeseries_info LIMIT 1;')
            row = self._cur.fetchone()[0]
            reference_time = self.parse_reference_time(row)
            self.has_reference_time = True
        except Exception as e:
            pass
        finally:
            self.close_db()
            return reference_time

    def create_key(self, id_: str, res: str):
        return '{0}_{1}'.format(id_, res)

    def LP_getConnectivity(self, id1: str, id2: str, *args, **kwargs) -> typing.Tuple[bool, str]:
        self.LP.connected = id1 == self.LP.id1 and id2 == self.LP.id2
        if self.LP.connected:
            return False, ''
        print('get connectivitiy')
        self.LP.loaded = False
        if id1 not in self.Channels.chan_name:
            return True, 'ID2 not found'
        if id2 is not None and id2 not in self.Channels.chan_name:
            id2 = None
        found = self.LP_force_connection(id1, id2)
        if found:
            self.LP.id1 = id1
            self.LP.id2 = id2
            return False, ''
        found = self.LP_force_connection(id2, id1)
        if found:
            self.LP.id1 = id2
            self.LP.id2 = id1
            return False, ''
        return True, 'No connection found'

    def LP_getStaticData(self) -> typing.Tuple[bool, str]:
        if self.LP.loaded:
            return False, ''
        print('get static data')
        self.LP.dist_chan_inverts = []
        self.LP.culv_verts = []
        self.LP.chan_inv = []
        self.LP.node_bed = []
        self.LP.node_top = []
        self.LP.dist_nodes = [0.0]
        self.LP.H_nd_index = []
        self.LP.node_index = []
        self.LP.Hmax = []
        self.LP.Emax = []
        self.LP.tHmax = []
        self.LP.adverseH.nLocs = 0
        self.LP.adverseH.chainage = []
        self.LP.adverseH.node = []
        self.LP.adverseH.elevation = []
        self.LP.adverseE.nLocs = 0
        self.LP.adverseE.chainage = []
        self.LP.adverseE.node = []
        self.LP.adverseE.elevation = []
        self.LP.npits = 0
        self.LP.pit_dist = []
        self.LP.pit_z = []
        try:
            time = self.timeSteps()[0]
        except IndexError:
            return True, 'Cannot load bed level without temporal data'

        total_len = 0
        for i, idx in enumerate(self.LP.chan_index):
            # bed level
            self.LP.dist_chan_inverts.append(total_len)
            total_len += self.Channels.chan_Length[i]
            self.LP.dist_nodes.append(total_len)
            self.LP.dist_chan_inverts.append(total_len)
            self.LP.chan_inv.append(self.Channels.chan_US_Inv[idx])
            self.LP.chan_inv.append(self.Channels.chan_DS_Inv[idx])

            # culverts/pipes
            hgt_us , hgt_ds = -1, -1
            if not np.isnan(self.Channels.chan_US_Obv[idx]):
                hgt_us = self.Channels.chan_US_Obv[idx] - self.Channels.chan_US_Inv[idx]
            if not np.isnan(self.Channels.chan_DS_Obv[idx]):
                hgt_ds = self.Channels.chan_DS_Obv[idx] - self.Channels.chan_DS_Inv[idx]
            if hgt_us > 0 or hgt_ds > 0:
                x = [
                    self.LP.dist_chan_inverts[-2], self.LP.dist_chan_inverts[-1],
                    self.LP.dist_chan_inverts[-1], self.LP.dist_chan_inverts[-2]
                ]
                y = [
                    self.Channels.chan_US_Inv[idx], self.Channels.chan_DS_Inv[idx],
                    self.Channels.chan_DS_Obv[idx], self.Channels.chan_US_Obv[idx]
                ]
                verts = list(zip(x, y))
                self.LP.culv_verts.append(verts)
            else:
                self.LP.culv_verts.append(None)

        # max water level
        if self.LP.node_list:
            node_list = [f'ID = "{id_}"' for id_ in self.LP.node_list]
            node_list = ' OR '.join(node_list)
            order_case = [f' WHEN "{id_}" THEN {i}' for i, id_ in enumerate(self.LP.node_list)]
            order_case = ''.join(order_case)
            sql = 'SELECT MAX("Water Level") FROM "{0}" WHERE {1} GROUP BY ID ORDER BY CASE ID{2} END;'.format(self.gis_point_layer_name, node_list, order_case)
            try:
                self.open_db()
                self._cur.execute(sql)
                for row in self._cur.fetchall():
                    try:
                        self.LP.Hmax.append(float(row[0]))
                    except (ValueError, IndexError):
                        continue
            except Exception as e:
                Logging.warning(e)
            finally:
                self.close_db()
            tmp = []
            for i, mx in enumerate(self.LP.Hmax):
                tmp.append(mx)
                if 0 < i < len(self.LP.Hmax) - 1:
                    tmp.append(mx)
            self.LP.Hmax = tmp

        # pit elevations
        if self.LP.node_list:
            should_not_bere_here = []
            node_list = [f'ID = "{id_}"' for id_ in self.LP.node_list]
            node_list = ' OR '.join(node_list)
            sql = f'SELECT ID, "Inlet_elevation" FROM "{self.gis_point_layer_name}" WHERE ({node_list}) AND "Inlet_elevation" IS NOT NULL;'
            try:
                self.open_db()
                self._cur.execute(sql)
                for row in self._cur.fetchall():
                    if row[1] == 'Inlet_elevation':
                        raise Exception('Missing inlet elevation data')
                    self.LP.npits += 1
                    self.LP.pit_z.append(float(row[1]))
                    if row[0] in self.LP.node_list:
                        self.LP.pit_dist.append(self.LP.dist_nodes[self.LP.node_list.index(row[0])])
                    else:
                        should_not_bere_here.append(f'Node ID not found: {row[0]}')
                if should_not_bere_here:
                    Logging.warning('::'.join(should_not_bere_here))
            except Exception as e:
                Logging.warning(e)
            finally:
                self.close_db()

        self.LP.loaded = True
        return False, ''

    def LP_getData(self, dat_type: str, time: float, dt_tol: float) -> typing.Tuple[bool, str]:
        values = []
        for i, node in enumerate(self.LP.node_list):
            found, data, msg = self.getTSData(node, '1D', dat_type, 'P')
            if not found:
                return True, 'Error loading {0}'.format(dat_type)
            j = self.timeSteps().index(time)
            v = data[j]
            values.append(v)
            if 0 < i < len(self.LP.node_list) - 1:
                values.append(v)

        if dat_type == 'Water Level':
            self.LP.Hdata = values
        return False, ''


class ChanInfo_GPKG(ChanInfo):
    """ChanInfo class for GPKG - lazy load all properties"""

    def __init__(self, fullpath: str):
        self.cur = None
        self.parent = None
        self._nChan = -1
        self._chan_num = []
        self._chan_name = []
        self._chan_US_Node = []
        self._chan_DS_Node = []
        self._chan_US_Chan = []
        self._chan_DS_Chan = []
        self._chan_Flags = []
        self._chan_Length = []
        self._chan_FormLoss = []
        self._chan_n = []
        self._chan_slope = []
        self._chan_US_Inv = []
        self._chan_DS_Inv = []
        self._chan_US_Obv = []
        self._chan_DS_Obv = []
        self._chan_LBUS_Obv = []
        self._chan_RBUS_Obv = []
        self._chan_LBDS_Obv = []
        self._chan_RBDS_Obv = []
        self._chan_Blockage = []
        self._inv_warning_shown = False
        ChanInfo.__init__(self, None)  # don't want base class to ever try and read a GPKG file

    @property
    def nChan(self) -> int:
        if self._nChan == -1:
            self._nChan = self.parent.gis_line_feature_count
        return self._nChan

    @nChan.setter
    def nChan(self, value: int) -> None:...

    @property
    def chan_num(self) -> list[int]:
        if self._nChan == -1:
            self._chan_num = [x + 1 for x in range(self.nChan)]
        return self._chan_num

    @chan_num.setter
    def chan_num(self, value: list[int]) -> None:...

    @property
    def chan_name(self) -> list[str]:
        if self._nChan == -1:
            try:
                self.parent.open_db()
                self.cur.execute(
                    'SELECT'
                    ' ID '
                    'FROM'
                    ' "{0}" '
                    'LIMIT {1};'.format(self.parent.gis_line_layer_name, self.nChan)
                )
                ret = self.cur.fetchall()
                if ret:
                    try:
                        self._chan_name = [x[0] for x in ret]
                    except ValueError:
                        pass
            except Exception as e:
                Logging.warning(e)
            finally:
                self.parent.close_db()
        return self._chan_name

    @chan_name.setter
    def chan_name(self, value: list[str]) -> None:
        pass

    @property
    def chan_US_Node(self) -> list[str]:
        if self.parent:
            try:
                if not self._chan_US_Node:
                    self.parent.open_db()
                    self.cur.execute(
                        'SELECT p.ID FROM "{0}" AS p, "{1}" as l WHERE p.fid = l.US_Node AND l.TimeId = 1;'.
                        format(self.parent.gis_point_layer_name, self.parent.gis_line_layer_name)
                    )
                    ret = self.cur.fetchall()
                    if ret:
                        self._chan_US_Node = [x[0] for x in ret]
            except Exception as e:
                Logging.warning(e)
            finally:
                self.parent.close_db()
        return self._chan_US_Node

    @chan_US_Node.setter
    def chan_US_Node(self, valud: list[str]) -> None:
        pass

    @property
    def chan_DS_Node(self) -> list[str]:
        if self.parent:
            try:
                if not self._chan_DS_Node:
                    self.parent.open_db()
                    self.cur.execute(
                        'SELECT p.ID FROM "{0}" AS p, "{1}" as l WHERE p.fid = l.DS_Node AND l.TimeId = 1;'.
                        format(self.parent.gis_point_layer_name, self.parent.gis_line_layer_name)
                    )
                    ret = self.cur.fetchall()
                    if ret:
                        self._chan_DS_Node = [x[0] for x in ret]
            except Exception as e:
                Logging.warning(e)
            finally:
                self.parent.close_db()
        return self._chan_DS_Node

    @chan_DS_Node.setter
    def chan_DS_Node(self, valud: list[str]) -> None:
        pass

    @property
    def chan_US_Chan(self) -> list[list[str]]:
        if self.parent:
            if not self._chan_US_Chan:
                for node in self.chan_US_Node:
                    chans = []
                    for i, nd in enumerate(self.chan_DS_Node):
                        if nd == node:
                            chans.append(self.chan_name[i])
                    self._chan_US_Chan.append(chans)
        return self._chan_US_Chan

    @chan_US_Chan.setter
    def chan_US_Chan(self, valud: list[list[str]]) -> None:
        pass

    @property
    def chan_DS_Chan(self) -> list[list[str]]:
        if self.parent:
            if not self._chan_DS_Chan:
                for node in self.chan_DS_Node:
                    chans = []
                    for i, nd in enumerate(self.chan_US_Node):
                        if nd == node:
                            chans.append(self.chan_name[i])
                    self._chan_DS_Chan.append(chans)
        return self._chan_DS_Chan

    @chan_DS_Chan.setter
    def chan_DS_Chan(self, valud: list[list[str]]) -> None:
        pass

    @property
    def chan_Flags(self) -> list[str]:
        raise NotImplementedError('GPKG time series format does not support chan_Flags property')

    @chan_Flags.setter
    def chan_Flags(self, valud: list[str]) -> str:
        pass

    @property
    def chan_Length(self) -> list[float]:
        if self.parent:
            if not self._chan_Length:
                try:
                    self.parent.open_db()
                    self.cur.execute(
                        'SELECT Length FROM "{0}" WHERE TimeId = 1;'.format(self.parent.gis_line_layer_name)
                    )
                    ret = self.cur.fetchall()
                    if ret:
                        self._chan_Length = [float(x[0]) for x in ret]
                except Exception as e:
                    Logging.warning(e)
                finally:
                    self.parent.close_db()
        return self._chan_Length

    @chan_Length.setter
    def chan_Length(self, valud: list[float]) -> None:
        pass

    @property
    def chan_FormLoss(self) -> list[float]:
        raise NotImplementedError('GPKG time series format does not support chan_FormLoss property')

    @chan_FormLoss.setter
    def chan_FormLoss(self, valud: list[float]) -> None:
        pass

    @property
    def chan_n(self) -> list[float]:
        raise NotImplementedError('GPKG time series format does not support chan_n property')

    @chan_n.setter
    def chan_n(self, valud: list[float]) -> None:
        pass

    @property
    def chan_slope(self) -> list[float]:
        if self.parent:
            if not self._chan_slope:
                if self.chan_US_Inv and self.chan_DS_Inv and self.chan_Length:
                    self._chan_slope = [(us - ds) / l for us, ds, l in zip(self.chan_US_Inv, self.chan_DS_Inv, self.chan_Length)]
        return self._chan_slope

    @chan_slope.setter
    def chan_slope(self, valud: list[float]) -> None:
        pass

    @property
    def chan_US_Inv(self) -> list[float]:
        if self.parent:
            if not self._chan_US_Inv:
                try:
                    self.parent.open_db()
                    self.cur.execute(
                        'SELECT US_Invert FROM "{0}" WHERE TimeId = 1;'.format(self.parent.gis_line_layer_name)
                    )
                    ret = self.cur.fetchall()
                    if ret:
                        self._chan_US_Inv = [float(x[0]) for x in ret]
                except Exception as e:
                    Logging.warning(e)
                finally:
                    self.parent.close_db()
        return self._chan_US_Inv

    @chan_US_Inv.setter
    def chan_US_Inv(self, valud: list[float]) -> None:
        pass

    @property
    def chan_DS_Inv(self) -> list[float]:
        if not self._chan_DS_Inv:
            try:
                self.parent.open_db()
                self.cur.execute(
                    'SELECT DS_Invert FROM "{0}" WHERE TimeId = 1;'.format(self.parent.gis_line_layer_name)
                )
                ret = self.cur.fetchall()
                if ret:
                    self._chan_DS_Inv = [float(x[0]) for x in ret]
            except Exception as e:
                Logging.warning(e)
            finally:
                self.parent.close_db()
        return self._chan_DS_Inv

    @chan_DS_Inv.setter
    def chan_DS_Inv(self, valud: list[float]) -> None:
        pass

    @property
    def chan_US_Obv(self) -> list[float]:
        if self.parent:
            if not self._chan_US_Obv:
                try:
                    self.parent.open_db()
                    self.cur.execute(
                        'SELECT US_Obvert FROM "{0}" WHERE TimeId = 1;'.format(self.parent.gis_line_layer_name)
                    )
                    ret = self.cur.fetchall()
                    if ret:
                        for row in ret:
                            try:
                                self._chan_US_Obv.append(float(row[0]))
                            except (TypeError, ValueError):
                                self._chan_US_Obv.append(np.nan)
                except Exception as e:
                    Logging.warning(e)
                finally:
                    self.parent.close_db()
        return self._chan_US_Obv

    @chan_US_Obv.setter
    def chan_US_Obv(self, valud: list[float]) -> None:
        pass

    @property
    def chan_DS_Obv(self) -> list[float]:
        if not self._chan_DS_Obv:
            try:
                self.parent.open_db()
                self.cur.execute(
                    'SELECT DS_Obvert FROM "{0}" WHERE TimeId = 1;'.format(self.parent.gis_line_layer_name)
                )
                ret = self.cur.fetchall()
                if ret:
                    for row in ret:
                        try:
                            self._chan_DS_Obv.append(float(row[0]))
                        except (TypeError, ValueError):
                            self._chan_DS_Obv.append(np.nan)
            except Exception as e:
                Logging.warning(e)
            finally:
                self.parent.close_db()
        return self._chan_DS_Obv

    @chan_DS_Obv.setter
    def chan_DS_Obv(self, valud: list[float]) -> None:
        pass

    @property
    def chan_LBUS_Obv(self) -> list[float]:
        raise NotImplementedError('GPKG time series format does not support chan_LBUS_Obv property')

    @chan_LBUS_Obv.setter
    def chan_LBUS_Obv(self, valud: list[float]) -> None:
        pass

    @property
    def chan_LBDS_Obv(self) -> list[float]:
        raise NotImplementedError('GPKG time series format does not support chan_LBDS_Obv property')


    @chan_LBDS_Obv.setter
    def chan_LBDS_Obv(self, valud: list[float]) -> None:
        pass

    @property
    def chan_Blockage(self) -> list[float]:
        raise NotImplementedError('GPKG time series format does not support chan_Blockage property')
    @chan_Blockage.setter
    def chan_Blockage(self, valud: list[float]) -> None:
        pass


class NodeInfo_GPKG(NodeInfo):
    """NodeInfo class for GPKG - lazy load all properties"""

    def __init__(self, fullpath: str):
        self.cur = None
        self.parent = None
        self._nNode = -1
        self._node_num = []
        self._node_name = []
        self._node_bed = []
        self._node_top = []
        self._node_nChan = []
        self._node_channels = []
        NodeInfo.__init__(self, None)

    @property
    def nNode(self) -> int:
        if self._nNode == -1:
            if self.parent is not None:
                self._nNode = self.parent.gis_point_feature_count
        return self._nNode

    @nNode.setter
    def nNode(self, value: int) -> None:...

    @property
    def node_num(self) -> list[int]:
        if self._nNode == -1:
            self._node_num = [x + 1 for x in range(self.nNode)]
        return self._node_num

    @node_num.setter
    def node_num(self, value: list[int]) -> None:...

    @property
    def node_name(self) -> list[str]:
        if self.parent:
            if not self._node_name:
                try:
                    self.parent.open_db()
                    self.cur.execute(
                        'SELECT'
                        ' ID '
                        'FROM'
                        ' "{0}" '
                        'LIMIT {1};'.format(self.parent.gis_point_layer_name, self.nNode)
                    )
                    ret = self.cur.fetchall()
                    if ret:
                        try:
                            self._node_name = [x[0] for x in ret]
                        except ValueError:
                            pass
                except Exception as e:
                    Logging.warning(e)
                finally:
                    self.parent.close_db()
        return self._node_name

    @node_name.setter
    def node_name(self, value: list[str]) -> None:...

    @property
    def node_bed(self) -> list[float]:
        if self.parent:
            if not self._node_bed:
                for node in self.node_name:
                    z = 9e29
                    for i, nd in enumerate(self.parent.Channels.chan_US_Node):
                        if nd == node:
                            z = min(z, self.parent.Channels.chan_US_Inv[i])
                    for i, nd in enumerate(self.parent.Channels.chan_DS_Node):
                        if nd == node:
                            z = min(z, self.parent.Channels.chan_DS_Inv[i])
                    self._node_bed.append(z)
        return self._node_bed

    @node_bed.setter
    def node_bed(self, value: list[float]) -> None:...

    @property
    def node_top(self) -> list[float]:
        raise NotImplementedError('GPKG time series format does not support node_top property')

    @node_top.setter
    def node_top(self, value: list[float]) -> None:...

    @property
    def node_nChan(self) -> list[int]:
        if self.parent:
            if not self._node_nChan:
                self._node_nChan = len(self.node_channels)
        return self._node_nChan

    @node_nChan.setter
    def node_nChan(self, value: list[int]) -> None:...

    @property
    def node_channels(self) -> list[list[str]]:
        if self.parent:
            if not self._node_channels:
                for node in self.node_name:
                    chans = []
                    for i, nd in enumerate(self.parent.Channels.chan_US_Node):
                        if nd == node:
                            chans.append(self.parent.Channels.chan_name[i])
                    for i, nd in enumerate(self.parent.Channels.chan_DS_Node):
                        if nd == node:
                            chans.append(self.parent.Channels.chan_name[i])
                    self._node_channels.append(chans)
        return self._node_channels

    @node_channels.setter
    def node_channels(self, value: list[list[str]]) -> None:...
