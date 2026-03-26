import typing

from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsVectorLayer

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import TPC as TPCBase, Output
else:  # when running tests outside of QGIS environment
    from tuflow.pt.pytuflow import TPC as TPCBase, Output


import logging
logger = logging.getLogger('tuflow_viewer')


class GPKGMixin:

    def _create_gpkg_layer(self, output: Output, uri: str, create_layer: typing.Callable[[str], QgsVectorLayer]) -> QgsVectorLayer | None:
        def tuflowuri2qgisuri(tuflow_uri: str) -> str:
            return '{0}|layername={1}'.format(*tuflow_uri.split(' >> ', 1))

        uri = tuflowuri2qgisuri(uri)
        return create_layer(uri)
