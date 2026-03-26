from pathlib import Path

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
