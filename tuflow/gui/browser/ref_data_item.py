from pathlib import Path

from qgis.core import Qgis, QgsDataItem
from qgis.PyQt import QtGui

from . import ScopeDataItem, pytuflow


class ReferenceDataItem(QgsDataItem):

    def __init__(
            self,
            type_: Qgis.BrowserItemType,
            parent: QgsDataItem | None,
            name: str,
            path: str,
            provider_key: str,
            inp: pytuflow.Input
    ):
        super().__init__(type_, parent, name, path, provider_key)
        self.setCapabilitiesV2(Qgis.BrowserItemCapability.Fertile
                               | Qgis.BrowserItemCapability.RefreshChildrenWhenItemIsRefreshed
                               )
        self.inp = inp

    def createChildren(self) -> list[QgsDataItem]:
        children = []
        for scope in self.inp.scope:
            scope_item = ScopeDataItem(
                QgsDataItem.Custom,
                self,
                scope.pretty_print(neg_char='~'),
                self.path() + '/Scopes/' + str(scope), 'tuflow_plugin',
                scope
            )
            scope_item.setState(Qgis.BrowserItemState.Populated)
            children.append(scope_item)
        return children


class ReferenceListDataItem(QgsDataItem):

    def __init__(
            self,
            type_: Qgis.BrowserItemType,
            parent: QgsDataItem,
            name: str,
            path: str,
            provider_key: str,
            ref_list: dict
    ):
        super().__init__(type_, parent, name, path, provider_key)
        self.setCapabilitiesV2(Qgis.BrowserItemCapability.Fertile
                               | Qgis.BrowserItemCapability.RefreshChildrenWhenItemIsRefreshed
                               )
        self.ref_list = ref_list

    def sortKey(self):
        return -99

    def icon(self):
        if self.state() == Qgis.BrowserItemState.Populating:
            return QgsDataItem.icon(self)  # returns loading icon while populating
        try:
            path = Path(__file__).parents[2] / 'icons' / 'references.svg'
            return QtGui.QIcon(str(path))
        except Exception as _:
            return QtGui.QIcon()

    def hasChildren(self):
        return True

    def createChildren(self):
        children = []
        for inp, ref in self.ref_list.items():
            ref_item = ReferenceDataItem(
                QgsDataItem.Custom,
                None,
                ref,
                self.path() + str(inp.uuid),
                'tuflow_plugin',
                inp)
            ref_item.setToolTip(ref)
            if inp.scope:
                ref_item.setState(Qgis.BrowserItemState.NotPopulated)
            else:
                ref_item.setState(Qgis.BrowserItemState.Populated)
            children.append(ref_item)
        return children