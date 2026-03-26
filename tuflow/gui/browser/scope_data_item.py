from pathlib import Path

from qgis.core import Qgis, QgsDataItem
from qgis.PyQt import QtGui


class ScopeDataItem(QgsDataItem):

    def __init__(self, type_, parent, name, path, provider_key, scope):
        super().__init__(type_, parent, name, path, provider_key)
        self.scope = scope

    def icon(self):
        if self.state() == Qgis.BrowserItemState.Populating:
            return QgsDataItem.icon(self)  # returns loading icon while populating
        try:
            path = Path(__file__).parents[2] / 'icons' / 'scope.svg'
            return QtGui.QIcon(str(path))
        except Exception:
            return QtGui.QIcon()
