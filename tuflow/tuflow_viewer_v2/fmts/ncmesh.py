from pathlib import Path
import shutil
import os

from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsMeshLayer

from .mesh_mixin import MeshMixin
from .qgis_mesh_api_mixin import QgisMeshAPIMixin
from .pyncmesh import PyNCMesh

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import NCMesh as NCMeshBase
else:
    from tuflow.pt.pytuflow import NCMesh as NCMeshBase


import logging
logger = logging.getLogger('tuflow_viewer')


class NCMesh(NCMeshBase, MeshMixin, QgisMeshAPIMixin):

    DRIVER_NAME = 'NetCDF Mesh'
    LAYER_TYPE = 'Surface'

    def __init__(self, fpath: str, layers: QgsMeshLayer = ()):
        super(NCMesh, self).__init__(fpath)
        layer = layers[0] if layers else None
        self._driver = PyNCMesh(self.fpath, geom_driver='qgis', engine='qgis', mesh=layer)
        self._driver.extractor.open_reader()
        self._soft_load_driver = self._driver
        self._init_viewer_output_mixin(self.name)
        self.copied_files = self._driver.copied_files
        self._load()  # load layer beyond just the light-weight initial load the pytuflow.XMDF class does

        self._layer = self._driver.lyr
        self._map_layers.append(self._layer)

        # QGIS specific
        self.init_temporal_properties()
        self._init_styling(self._map_layers, self._lyr2resultstyle)

    def __del__(self):
        self.close()

    def close(self):
        self._driver.extractor.close_reader()
        self._teardown_viewer_output_mixin()

    @staticmethod
    def format_compatible(fpath: Path | str) -> bool:
        """Returns True if the file is of this format.
        This is used to determine if the handler is suitable for the file.
        """
        return NCMeshBase._looks_like_this(Path(fpath))

    def _init_styling(self, map_layers: list[QgsMeshLayer], lyr2resultstyle: dict):
        """Initialise styling for the layer."""
        pass

    def reload_layer(self, layer: QgsMeshLayer, copied_files_mapping: dict):
        self._driver.reload_layer(layer, copied_files_mapping)

    def set_data_source(self, new_fpath: Path):
        from ..tvinstance import get_viewer_instance

        self._layer.setDataSource(str(new_fpath), self._layer.name(), 'mdal')
        self._layer.reload()

        v1_1_driver = self._driver.DRIVER_SOURCE == 'python'
        if v1_1_driver:
            self._driver.set_data_source(new_fpath)
        else:
            self._driver.mesh = new_fpath

        self._initial_load()

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

        logger.info('Successfully sync\'d and reloaded NetCDF mesh results.', extra={'messagebar': True})
