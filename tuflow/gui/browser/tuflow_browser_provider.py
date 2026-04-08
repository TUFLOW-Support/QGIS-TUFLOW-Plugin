from pathlib import Path

from qgis.core import QgsDataItemProvider, Qgis, QgsDataProvider

from . import ControlFileItem
from ..logging import Logging


class TuflowBrowserProvider(QgsDataItemProvider):

    def name(self):
        return "TUFLOW Plugin Browser Provider"

    def capabilities(self):
        if Qgis.QGIS_VERSION_INT >= 33600:
            return Qgis.DataItemProviderCapability.Files
        return QgsDataProvider.DataCapability.File

    def createDataItem(self, path, parentItem):
        if Path(path).suffix.lower() in ['.tcf', '.tgc', '.tbc', '.ecf', '.qcf', '.tef', 'tesf', 'trfcf', '.adcf', 'tscf']:
            try:
                return ControlFileItem(path, parentItem)
            except Exception as e:
                if Qgis.QGIS_VERSION_INT < 33800:
                    Logging.warning('Failed to create ControlFileDataItem in QGIS Browser: Requires QGIS 3.38 or later')
                else:
                    Logging.warning('Failed to create ControlFileDataItem in QGIS Browser: {}'.format(e), silent=True)
        return None
