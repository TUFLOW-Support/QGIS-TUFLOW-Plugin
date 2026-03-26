import os
import shutil
from pathlib import Path

import numpy as np
from qgis.PyQt.QtCore import QSettings, QTimer
from qgis.core import QgsRasterLayer, QgsStyle, QgsSingleBandPseudoColorRenderer, QgsColorRampShader
from qgis.utils import iface

try:
    from netCDF4 import Dataset
    has_nc = True
except ImportError:
    Dataset = 'Dataset'
    has_nc = False

from .map_output_mixin import MapOutputMixin
from .nc_grid_layer import NetCDFGridLayer
from ..tvinstance import get_viewer_instance
from ..temporal_controller_widget import temporal_controller
from .copy_on_load_mixin import CopyOnLoadMixin

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import NCGrid as NCGridBase
    from ...tuflowqgis_dialog import tuflowqgis_scenarioSelection_dialog
else:
    from tuflow.pt.pytuflow import NCGrid as NCGridBase
    from tuflow.tuflowqgis_dialog import tuflowqgis_scenarioSelection_dialog


import logging
logger = logging.getLogger('tuflow_viewer')


class NCGrid(NCGridBase, MapOutputMixin, CopyOnLoadMixin):

    DRIVER_NAME = 'NetCDF Grid'
    LAYER_TYPE = 'Surface'

    def __init__(self, fpath: str, layers: QgsRasterLayer = (), layer_names: list[str] = ()):
        self._map_layers = layers
        self._copied_files = {}
        super(NCGrid, self).__init__(fpath)
        self._init_viewer_output_mixin(self.name)
        self.copied_files = self._copied_files
        self.lyr2layer_name = {}
        if not layers:
            layers = self._user_layer_selection() if not layer_names else layer_names
            if not layers:
                return
            self._map_layers = self._load_ncgrid_layers(layers)
        else:
            self._map_layers = layers
            self._lyr2output = {}
            self._lyr2resultstyle = {}

        self.init_temporal_properties()
        self._init_styling(self._map_layers, self._lyr2resultstyle)
        iface.mapCanvas().temporalRangeChanged.connect(self._update_band_from_time)
        self._loaded = True

    def close(self):
        self._teardown_viewer_output_mixin()
        try:
            iface.mapCanvas().temporalRangeChanged.disconnect(self._update_band_from_time)
        except Exception:
            pass

    @staticmethod
    def format_compatible(fpath: Path | str) -> bool:
        """Returns True if the file is of this format.
        This is used to determine if the handler is suitable for the file.
        """
        return NCGridBase._looks_like_this(fpath) and  NCGridBase.is_tuflow_output(fpath)

    def set_data_source(self, new_fpath: Path):
        self.fpath = Path(new_fpath)
        for lyr in self._map_layers:
            lyrname = self.lyr2layer_name[lyr.id()]
            uri = f'NETCDF:"{new_fpath}":{lyrname}'
            lyr.setDataSource(uri, lyr.name(), 'gdal')
        QTimer.singleShot(300, lambda: self._set_data_source_delayed(new_fpath))

    def _set_data_source_delayed(self, new_fpath: Path):
        from ..tvinstance import get_viewer_instance

        for lyr in self._map_layers:
            lyr.reload()
        self._initial_load()

        for lyr in self._map_layers:
            name = lyr.dataProvider().dataSourceUri().split(':')[-1].strip()
            times = self.times(name, fmt='absolute')
            lyr.times = times

        old_src = list(self.copied_files.keys())[0]
        orig = self.copied_files[old_src]
        self.copied_files.clear()
        self.copied_files[str(new_fpath)] = (str(orig[0]), os.path.getmtime(orig[0]))

        try:
            with open(old_src, 'rb+'):
                pass
            Path(old_src).unlink()
            shutil.rmtree(Path(old_src).parent, ignore_errors=True)
            logger.info('Deleted previously copied file: {}'.format(old_src))
        except Exception:
            logger.info('Original copied file is locked, cannot remove: {}'.format(old_src))

        self.init_temporal_properties()
        self._init_styling(self._map_layers, self._lyr2resultstyle)
        get_viewer_instance().configure_temporal_controller()

        logger.info('Successfully sync\'d and reloaded NetCDF grid results.', extra={'messagebar': True})

    def _initial_load(self):
        from ..tvinstance import get_viewer_instance
        if not self._map_layers:
            if get_viewer_instance().settings.copy_results_on_load:
                orig = self.fpath
                self.fpath = self.copy(Path(self.fpath))
                self._copied_files[str(self.fpath)] = (orig, os.path.getmtime(orig))
            super()._initial_load()
        else:
            super()._initial_load()
        self.name = f'{self.fpath.stem}_nc'

    def _user_layer_selection(self) -> list[str]:
        dlg = tuflowqgis_scenarioSelection_dialog(iface, str(self.fpath), self._available_layers())
        dlg.setWindowTitle('NetCDF Grid Layer Selection')
        if dlg.exec():
            return dlg.scenarios
        return []

    def _load_ncgrid_layers(self, layer_names: list[str]) -> list[QgsRasterLayer]:
        def create_uri(fpath: Path | str, layer_name: str) -> str:
            return f'NETCDF:"{fpath}":{layer_name}'

        layers = []
        for layer_name in layer_names:
            uri = create_uri(self.fpath, layer_name)
            lyr = NetCDFGridLayer(uri, f'{self.name} - {layer_name}', 'gdal', self.times(layer_name, fmt='absolute'), self.reference_time)
            if lyr.isValid():
                self.lyr2layer_name[lyr.id()] = layer_name
                layers.append(lyr)
                self._lyr2output[lyr.id()] = self
                if get_viewer_instance().temporal_settings_initialised and not lyr.static:
                    cur_time = temporal_controller.currentTime() if temporal_controller.currentTime() is not None else self.reference_time
                    band = lyr.get_band_from_time(cur_time)
                else:
                    band = 1
                    temporal_controller.setCurrentTime(self.reference_time)
                lyr._curr_band = band
                min_, max_ = self._get_min_max(layer_name)
                renderer = self._create_renderer(lyr, band, min_, max_)
                lyr.setRenderer(renderer)
            else:
                logger.debug(f'Failed to load GIS Plot Layer: {uri}')

        return layers

    def _create_renderer(self, layer: QgsRasterLayer, band: int, min_: float, max_: float) -> QgsSingleBandPseudoColorRenderer:
        colour_ramp_gradient = QgsStyle().defaultStyle().colorRamp('Spectral')
        colour_ramp_gradient.invert()
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), band)
        renderer.setClassificationMin(min_)
        renderer.setClassificationMax(max_)
        renderer.createShader(colour_ramp_gradient, QgsColorRampShader.Interpolated,
                              QgsColorRampShader.Continuous, 5)
        return renderer

    def _get_min_max(self, layer_name: str) -> tuple[float, float]:
        min_, max_ = 9e29, -9e29
        with Dataset(self.fpath, 'r') as nc:
            max_dataset = 'maximum_{0}'.format(layer_name)  # try and be clever and find maximum dataset
            dataset = max_dataset if max_dataset in nc.variables else layer_name
            ds = nc.variables[dataset][:]
            if np.ma.is_masked(np.nanmin(ds)) and np.nanmin(ds).mask.all():
                ds = nc.variables[layer_name][:]
            min_ = min(min_, np.nanmin(ds))
            max_ = max(max_, np.nanmax(ds))
        if np.isclose(min_, max_, atol=0.001) or min_ > max_:
            max_ += 0.01 * abs(max_) if max_ != 0 else 0.1
        return min_, max_

    def _update_band_from_time(self, *args):
        cur_time = temporal_controller.currentTime()
        if cur_time is None:
            return
        for lyr in self._map_layers:
            if isinstance(lyr, NetCDFGridLayer):
                lyr.update_band_from_time(cur_time)

    def _available_layers(self) -> list[str]:
        layers = []
        try:
            with Dataset(self.fpath, 'r') as nc:
                x_dims = [name for name, dim in nc.dimensions.items() if
                          name in nc.variables and hasattr(nc.variables[name], 'axis') and nc.variables[
                              name].axis == 'X']
                y_dims = [name for name, dim in nc.dimensions.items() if
                          name in nc.variables and hasattr(nc.variables[name], 'axis') and nc.variables[
                              name].axis == 'Y']
                for name, var in nc.variables.items():
                    if len(var.shape) == 3:
                        i, j = 1, 2
                    elif len(var.shape) == 2:
                        i, j = 0, 1
                    else:
                        continue
                    if var.dimensions[i] in y_dims and var.dimensions[j] in x_dims:
                        layers.append(name)
        except Exception:
            pass
        finally:
            pass
        return layers

    def _init_styling(self, map_layers: list[QgsRasterLayer], lyr2resultstyle: dict):
        """Initialise styling for the layer."""
        pass
