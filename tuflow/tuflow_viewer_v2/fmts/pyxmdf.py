import os
import typing
from pathlib import Path

from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsMeshLayer

from .copy_on_load_mixin import CopyOnLoadMixin
from ..tvinstance import get_viewer_instance

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow._outputs.pymesh import PyXMDF as PyXMDFBase, QgisDataExtractor, PyXMDFDataExtractor
else:  # when running tests outside of QGIS environment
    from tuflow.pt.pytuflow._outputs.pymesh import PyXMDF as PyXMDFBase, QgisDataExtractor, PyXMDFDataExtractor


class PyXMDF(PyXMDFBase, CopyOnLoadMixin):

    def __init__(self, fpath: Path | str, twodm: Path | str = None, geom_driver: str = None, engine: str = None, mesh: typing.Any = None):
        self.copied_files = {}
        if mesh is None and get_viewer_instance().settings.copy_results_on_load:
            orig = fpath
            fpath = self.copy(Path(fpath))
            self.copied_files[str(fpath)] = (str(orig), os.path.getmtime(orig))
        super().__init__(fpath, twodm, geom_driver, engine, mesh)

    @property
    def lyr(self) -> QgsMeshLayer:
        return self.geom.lyr

    def set_data_source(self, fpath: Path | str):
        """Not for setting 2dm path."""
        self.extractor.close_reader()
        if self.extractor.NAME == 'QgisDataExtractor':
            self.extractor = QgisDataExtractor(self.extractor.mesh, [Path(fpath)], layer=self.extractor.lyr)
        else:
            self.extractor = PyXMDFDataExtractor(Path(fpath))
        self.extractor.open_reader()
        self.clear_cache()
