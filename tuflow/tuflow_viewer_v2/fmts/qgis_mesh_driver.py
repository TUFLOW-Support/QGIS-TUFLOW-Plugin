import os
from pathlib import Path

from qgis.PyQt.QtCore import QSettings

from .copy_on_load_mixin import CopyOnLoadMixin

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow._outputs.helpers.mesh_driver_qgis import QgisMeshDriver
    from ...pt.pytuflow._outputs.helpers.mesh_driver_qgis_xmdf import QgisXmdfMeshDriver
    from ...pt.pytuflow._outputs.helpers.mesh_driver_qgis_dat import QgisDATMeshDriver
    from ...pt.pytuflow._outputs.helpers.mesh_driver_qgis_nc import QgisNcMeshDriver
else:  # when running tests outside of QGIS environment
    from tuflow.pt.pytuflow._outputs.helpers.mesh_driver_qgis import QgisMeshDriver
    from tuflow.pt.pytuflow._outputs.helpers.mesh_driver_qgis_xmdf import QgisXmdfMeshDriver
    from tuflow.pt.pytuflow._outputs.helpers.mesh_driver_qgis_dat import QgisDATMeshDriver
    from tuflow.pt.pytuflow._outputs.helpers.mesh_driver_qgis_nc import QgisNcMeshDriver


class TVQgisXmdfMeshDriver(QgisXmdfMeshDriver, CopyOnLoadMixin):
    """Override QgisXmdfMeshDriver class from pytuflow for situations where the QgsMeshLayer is already loaded and
    we don't want to load it again.
    """

    def __init__(self, mesh: Path, xmdf: Path):
        self.copied_files = {}
        super().__init__(mesh, xmdf)

    def load(self):
        from ..tvinstance import get_viewer_instance
        if not self.lyr:
            if get_viewer_instance().settings.copy_results_on_load:
                orig = self.xmdf
                self.xmdf = self.copy(Path(self.xmdf))
                self.copied_files[str(self.xmdf)] = (orig, os.path.getmtime(orig))
            super().load()
        elif not self.lyr.dataProvider().extraDatasets():
            success = self.lyr.dataProvider().addDataset(str(self.xmdf))
            if not success:
                raise RuntimeError(f'Failed to load xmdf results onto 2dm: {self.xmdf}')
            QgisMeshDriver.load(self)
        else:
            QgisMeshDriver.load(self)


class TVQgisNcMeshDriver(QgisNcMeshDriver, CopyOnLoadMixin):
    """Override QgisNcMeshDriver class from pytuflow for situations where the QgsMeshLayer is already loaded and
    we don't want to load it again.
    """

    def __init__(self, mesh: Path):
        self.copied_files = {}
        super().__init__(mesh)

    def load(self):
        from ..tvinstance import get_viewer_instance
        if not self.lyr:
            if get_viewer_instance().settings.copy_results_on_load:
                orig = self.mesh
                self.mesh = self.copy(Path(self.mesh))
                self.copied_files[str(self.mesh)] = (orig, os.path.getmtime(orig))
            super().load()
        else:
            QgisMeshDriver.load(self)


class TVQGisDATMeshDriver(QgisDATMeshDriver):
    """Override QgisDATMeshDriver class from pytuflow for situations where the QgsMeshLayer is already loaded and
    we don't want to load it again.
    """

    def load(self):
        if not self.lyr:
            super().load()
        elif not self.lyr.dataProvider().extraDatasets():
            for dat in self.dats:
                success = self.lyr.dataProvider().addDataset(str(dat))
                if not success:
                    raise RuntimeError(f'Failed to load DAT result onto 2dm: {dat}')
            QgisMeshDriver.load(self)
        else:
            QgisMeshDriver.load(self)
