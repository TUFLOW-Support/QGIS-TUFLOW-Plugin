from pathlib import Path

from qgis.core import QgsMapLayer, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings

from .time_series_mixin import TimeSeriesMixin
from .gpkg_mixin import GPKGMixin

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import TPC as TPCBase
    from ...pt.pytuflow._pytuflow_types import TuflowPath
else:  # when running tests outside of QGIS environment
    from tuflow.pt.pytuflow import TPC as TPCBase
    from tuflow.pt.pytuflow._pytuflow_types import TuflowPath

import logging
logger = logging.getLogger('tuflow_viewer')


class TPC(TPCBase, TimeSeriesMixin, GPKGMixin):
    DRIVER_NAME = 'TPC'
    LAYER_TYPE = 'Plot'

    def __init__(self, fpath: Path | str, layers: list[QgsVectorLayer] = ()):
        super(TPC, self).__init__(fpath)
        self._init_viewer_output_mixin(self.name)
        self._load()
        self.format = self.format.upper()  # ensure upper case, makes it easier to compare
        if layers:
            self._map_layers = layers
        else:
            if self.format == 'GPKG':
                self._map_layers = self._create_map_layers_from_gpkg()
            else:
                self._map_layers = self._create_map_layers_from_tpc()

        # QGIS specific
        self.init_temporal_properties()
        self._init_vector_temporal_properties(self._map_layers, self._lyr2resultstyle)
        self._init_styling(self._map_layers, self._lyr2resultstyle)  # must come after temporal init

    def close(self):
        self._teardown_viewer_output_mixin()

    @staticmethod
    def format_compatible(fpath: Path | str) -> bool:
        """Returns True if the file is of this format.
        This is used to determine if the handler is suitable for the file.
        """
        return TPCBase._looks_like_this(Path(fpath))

    def _create_map_layers_from_tpc(self) -> list[QgsMapLayer]:
        logger.debug('Creating map layers from TPC...')
        map_layers = []
        for prop, val in self._tpc_reader.iter_properties('GIS Plot Layer'):
            logger.debug(f'GIS Plot Layer in TPC: {val}')
            if 'point' in prop.lower() and not self.data_types('point'):
                logger.info(f'Skipping {val} as the result does not contain any point data.')
                continue
            if 'line' in prop.lower() and not self.data_types('line'):
                logger.info(f'Skipping {val} as the result does not contain any line data.')
                continue
            if 'region' in prop.lower() and not self.data_types('region'):
                logger.info(f'Skipping {val} as the result does not contain any region data.')
                continue

            fpath = TuflowPath(self.fpath).parent / val
            if not fpath.exists():
                logger.debug(f'File not found: {fpath}')
                continue
            lyr = self._create_gis_layer_from_file(fpath)
            if lyr is None:
                continue
            map_layers.append(lyr)
            self._lyr2output[lyr.id()] = self

        map_layers = sorted(map_layers, key=lambda x: {'_R': 0, '_L': 1, '_P': 2}.get(x.name()[-2:], 99))
        if self._gpkgswmm:
            map_layers.extend(self._create_map_layers_from_gpkg())

        return map_layers

    def _create_map_layers_from_gpkg(self) -> list[QgsMapLayer]:
        map_layers = []
        for gpkg1d in [self._gpkg1d, self._gpkgswmm]:
            if not gpkg1d:
                continue
            if gpkg1d.channel_count:
                lyr = self._create_gpkg_layer(gpkg1d, gpkg1d.gis_layer_l_fpath, self._create_gis_layer_from_file)
                if lyr is not None:
                    map_layers.append(lyr)
                    self._lyr2output[lyr.id()] = gpkg1d
                    self._lyr2resultstyle[lyr.id()] = 'Flow'
            if gpkg1d.node_count:
                lyr = self._create_gpkg_layer(gpkg1d, gpkg1d.gis_layer_p_fpath, self._create_gis_layer_from_file)
                if lyr is not None:
                    map_layers.append(lyr)
                    self._lyr2output[lyr.id()] = gpkg1d
                    self._lyr2resultstyle[lyr.id()] = 'Water Level'

        for gpkg in [self._gpkg2d, self._gpkgrl]:
            if not gpkg:
                continue
            if gpkg.po_point_count:
                lyr = self._create_gpkg_layer(gpkg, gpkg.gis_layer_p_fpath, self._create_gis_layer_from_file)
                if lyr is not None:
                    map_layers.append(lyr)
                    self._lyr2output[lyr.id()] = gpkg
                    self._lyr2resultstyle[lyr.id()] = '_PLOT_Type'
            if gpkg.po_line_count:
                lyr = self._create_gpkg_layer(gpkg, gpkg.gis_layer_l_fpath, self._create_gis_layer_from_file)
                if lyr is not None:
                    map_layers.append(lyr)
                    self._lyr2output[lyr.id()] = gpkg
                    self._lyr2resultstyle[lyr.id()] = '_PLOT_Type'
            if gpkg.po_poly_count:
                lyr = self._create_gpkg_layer(gpkg, gpkg.gis_layer_r_fpath, self._create_gis_layer_from_file)
                if lyr is not None:
                    map_layers.append(lyr)
                    self._lyr2output[lyr.id()] = gpkg
                    self._lyr2resultstyle[lyr.id()] = '_PLOT_Type'

        return map_layers


