from qgis.core import Qgis, QgsDataItem, QgsLayerItem, QgsFieldsItem
from qgis.PyQt import QtGui, QtWidgets

from . import pytuflow, TuflowDataItemBaseMixin, TuflowDatabaseItemMixin


class TuflowLayerItem(QgsLayerItem, TuflowDataItemBaseMixin, TuflowDatabaseItemMixin):
    """Subclasses QgsLayerItem and adds TUFLOW-specific functionality."""

    def __init__(
            self,
            parent: QgsDataItem | None,
            name: str,
            path: str,
            provider_key: str,
            inp: pytuflow.Input,
            layer_type: Qgis.BrowserLayerType
    ):
        super().__init__(parent, name, path, path, layer_type, provider_key)
        self._init_tuflow_data_item_base_mixin(self.path(), inp)
        self._init_tuflow_database_mixin(inp)
        self._init_filter_state()
        if self._is_db:
            self._init_database(inp)
        self.set_tooltip()

    def sortKey(self):
        return self.sort_key()

    def hasChildren(self):
        return True

    def icon(self) -> QtGui.QIcon:
        if self.state() == Qgis.BrowserItemState.Populating:
            return QgsDataItem.icon(self)  # returns loading icon while populating
        return self.apply_icon_overlays(super().icon())

    def createChildren(self) -> list[QgsDataItem]:
        children = self._create_children(self)
        if self.providerKey() == 'ogr':
            fields_item = QgsFieldsItem(self, self.path() + '/Fields/', self.uri(), 'ogr', '', self.name())
            children.append(fields_item)
        return children

    def actions(self, parent) -> list[QtWidgets.QAction]:
        actions = []
        actions.extend(self.tuflow_base_actions(parent))
        actions.extend(self.database_actions(parent))
        return actions
