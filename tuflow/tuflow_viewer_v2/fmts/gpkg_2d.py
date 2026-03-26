from pathlib import Path

from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsVectorLayer

from .time_series_mixin import TimeSeriesMixin
from .gpkg_mixin import GPKGMixin

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import GPKG2D as GPKG2DBase
else:
    from tuflow.pt.pytuflow import GPKG2D as GPKG2DBase


import logging
logger = logging.getLogger('tuflow_viewer')


class GPKG2D(GPKG2DBase, TimeSeriesMixin, GPKGMixin):

    DRIVER_NAME = 'GPKG Time Series'
    LAYER_TYPE = 'Plot'

    def __init__(self, fpath: Path | str, layers: list[QgsVectorLayer] = ()):
        super(GPKG2D, self).__init__(fpath)
        self._init_viewer_output_mixin(self.name)
        self._load()
        if layers:
            self._map_layers = layers
        else:
            if self.po_point_count:
                lyr = self._create_gpkg_layer(self, self.gis_layer_p_fpath, self._create_gis_layer_from_file)
                if lyr is not None:
                    self._map_layers.append(lyr)
                    self._lyr2output[lyr.id()] = self
                    self._lyr2resultstyle[lyr.id()] = '_PLOT_Type'
            if self.po_line_count:
                lyr = self._create_gpkg_layer(self, self.gis_layer_l_fpath, self._create_gis_layer_from_file)
                if lyr is not None:
                    self._map_layers.append(lyr)
                    self._lyr2output[lyr.id()] = self
                    self._lyr2resultstyle[lyr.id()] = '_PLOT_Type'
            if self.po_poly_count:
                lyr = self._create_gpkg_layer(self, self.gis_layer_r_fpath, self._create_gis_layer_from_file)
                if lyr is not None:
                    self._map_layers.append(lyr)
                    self._lyr2output[lyr.id()] = self
                    self._lyr2resultstyle[lyr.id()] = '_PLOT_Type'

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
        return GPKG2DBase._looks_like_this(Path(fpath))
