from pathlib import Path

from qgis.core import QgsApplication, Qgis, QgsDataItem
from qgis.PyQt import QtGui, QtWidgets, QtCore

from . import pytuflow, TuflowDataItemBaseMixin, TuflowDatabaseItemMixin


class TuflowTableItem(QgsDataItem, TuflowDataItemBaseMixin, TuflowDatabaseItemMixin):
    """QgsDataItem representing a TUFLOW database file, but not CSV files. E.g. .tmf

    CSV files are already provided for by QGIS in the QgsLayerItem class, so are handled by
    a subclass of that (TuflowLayerItem).
    """

    def __init__(
            self,
            type_: Qgis.BrowserItemType,
            parent: QgsDataItem,
            name: str,
            path: str,
            provider_key: str,
            inp: pytuflow.Input
    ):
        super().__init__(type_, parent, name, path, provider_key)
        self.setCapabilitiesV2(Qgis.BrowserItemCapability.Fertile
                               | Qgis.BrowserItemCapability.RefreshChildrenWhenItemIsRefreshed
                               | Qgis.BrowserItemCapability.ItemRepresentsFile
                               )
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
        icon = QgsApplication.instance().getThemeIcon('/mIconTableLayer.svg')
        return self.apply_icon_overlays(icon)

    def createChildren(self) -> list[QgsDataItem]:
        try:
            children = self._create_children(self)
        except Exception:
            return []
        return children

    def actions(self, parent) -> list[QtWidgets.QAction]:
        actions = []
        actions.extend(self.tuflow_base_actions(parent))
        actions.extend(self.database_actions(parent))
        return actions
