import os
import typing
from pathlib import Path

from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsMeshLayer

from .copy_on_load_mixin import CopyOnLoadMixin
from ..tvinstance import get_viewer_instance

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow._outputs.pymesh import PyNCMesh as PyNCMeshBase, QgisDataExtractor, PyNCMeshDataExtractor
else:
    from tuflow.pt.pytuflow._outputs.pymesh import PyNCMesh as PyNCMeshBase, QgisDataExtractor, PyNCMeshDataExtractor


class PyNCMesh(PyNCMeshBase, CopyOnLoadMixin):

    def __init__(self, fpath: Path | str, geom_driver: str = None, engine: str = None, mesh: typing.Any = None):
        self.copied_files = {}
        if mesh is None and get_viewer_instance().settings.copy_results_on_load:
            orig = fpath
            fpath = self.copy(Path(fpath))
            self.copied_files[str(fpath)] = (str(orig), os.path.getmtime(orig))
        super().__init__(fpath, geom_driver, engine, mesh)

    @property
    def lyr(self) -> QgsMeshLayer:
        return self.geom.lyr

    def set_data_source(self, fpath: Path | str):
        """Not for setting 2dm path."""
        self.extractor.close_reader()
        if self.extractor.NAME == 'QgisDataExtractor':
            self.extractor = QgisDataExtractor(fpath, extra_datasets=[], layer=self.extractor.lyr)
        else:
            self.extractor = PyNCMeshDataExtractor(Path(fpath))
        self.extractor.open_reader()
        self.clear_cache()
