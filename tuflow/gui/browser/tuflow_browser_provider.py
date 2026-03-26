from pathlib import Path

from qgis.core import QgsDataItemProvider, Qgis

from . import ControlFileItem
from ..logging import Logging


class TuflowBrowserProvider(QgsDataItemProvider):

    def name(self):
        return "TUFLOW Plugin Browser Provider"

    def capabilities(self):
        return  Qgis.DataItemProviderCapability.Files

    def createDataItem(self, path, parentItem):
        if Path(path).suffix.lower() in ['.tcf', '.tgc', '.tbc', '.ecf', '.qcf', '.tef', 'tesf', 'trfcf', '.adcf', 'tscf']:
            try:
                return ControlFileItem(path, parentItem)
            except Exception as e:
                Logging.warning('Failed to create ControlFileDataItem in QGIS Browser: {}'.format(e), silent=True)
        return None
