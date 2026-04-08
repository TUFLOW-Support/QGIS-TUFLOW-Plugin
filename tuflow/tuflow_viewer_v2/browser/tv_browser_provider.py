from pathlib import Path

from qgis.core import QgsDataItemProvider, Qgis, QgsDataProvider
from . import TPCBrowserItem


class TVBrowserProvider(QgsDataItemProvider):

    def name(self):
        return "TUFLOW Viewer Browser Provider"

    def capabilities(self):
        if Qgis.QGIS_VERSION_INT >= 33600:
            return  Qgis.DataItemProviderCapability.Files
        return QgsDataProvider.DataCapability.File

    def createDataItem(self, path, parentItem):
        if Path(path).suffix.lower() == '.tpc':
            return TPCBrowserItem(path, parentItem)
        elif Path(path).suffix.lower() == '.sup':
            from .sup_browser_item import SUPBrowserItem
            return SUPBrowserItem(path, parentItem)
        elif Path(path).suffix.lower() == '.gxy':
            from .gxy_brower_item import GXYBrowserItem
            return GXYBrowserItem(path, parentItem)
        return None
