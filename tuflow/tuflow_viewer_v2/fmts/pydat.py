from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsMeshLayer, QgsMeshDataProvider

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow._outputs.pymesh import PyDAT as PyDATBase
else:  # when running tests outside of QGIS environment
    from tuflow.pt.pytuflow._outputs.pymesh import PyDAT as PyDATBase


class PyDAT(PyDATBase):

    @property
    def lyr(self) -> QgsMeshLayer:
        return self.geom.lyr

    @property
    def dp(self) -> QgsMeshDataProvider:
        return self.geom.lyr.dataProvider()
