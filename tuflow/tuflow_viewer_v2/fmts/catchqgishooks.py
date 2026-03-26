from datetime import timedelta
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtWidgets import QDockWidget, QComboBox
from qgis.PyQt.QtXml import QDomDocument
from qgis.core import QgsMapLayer, QgsProject, QgsReadWriteContext, QgsLayerTreeNode, QgsRectangle, Qgis

from .catchproviders import CATCHProvider
from ..tvinstance import get_viewer_instance


def layer_styling_dock():
    from qgis.utils import iface
    if iface.mainWindow() is None:
        return
    styling_docks = [x for x in iface.mainWindow().findChildren(QDockWidget) if x.windowTitle() == 'Layer Styling']
    if styling_docks:
        return styling_docks[0]


def layer_styling_cbo() -> QComboBox:
    styling_dock = layer_styling_dock()
    if styling_dock:
        cbo = [x for x in styling_dock.findChildren(QComboBox)][0]
        return cbo


class CATCHQgisHooks:

    def _init_catch_qgis_hooks(self, alias: str, data: dict, providers: dict[str, CATCHProvider]):
        self._node_order_being_changed = False
        self._providers = providers
        self._data = data

        # set index provider
        self.index = providers[data['index']]
        self.index.layer.setName(alias)

        # hide all layers except the index layer
        self._ancil_layers = []
        for provider in providers.values():
            if provider == self.index:
                continue
            provider.layer.setFlags(QgsMapLayer.Private)
            self._ancil_layers.append(provider.layer.id())

        # calculate min/max across all providers
        self.mm = {}
        for provider in providers.values():
            for dtype in provider.provider_data_types():
                if dtype not in self.mm:
                    self.mm[dtype] = (9e29, -9e29)
                mm = self.mm[dtype]
                min_ = min(provider.provider_min(dtype), mm[0])
                max_ = max(provider.provider_max(dtype), mm[1])
                if min_ == max_:
                    max_ += 0.1
                self.mm[dtype] = (min_, max_)

        # init consistent styles using the min/max
        for provider in providers.values():
            for dtype in provider.provider_data_types():
                provider.init_style(dtype, self.mm[dtype])

        # name changed
        self.index.layer.nameChanged.connect(self._name_changed)

        # node order changed - keep layers together and in the correct order
        QgsProject.instance().layerTreeRoot().addedChildren.connect(self._node_order_changed)

        # active scalar/vector dataset changed
        self.index.layer.activeScalarDatasetGroupChanged.connect(self._scalar_group_changed)
        self.index.layer.activeVectorDatasetGroupChanged.connect(self._vector_group_changed)

        # styling changed
        self.index.layer.rendererChanged.connect(self._renderer_changed)

        # metadata changed - e.g. reference time
        self.index.layer.metadataChanged.connect(self._metadata_changed)

        # crs changed
        self.index.layer.crsChanged.connect(self._crs_changed)

    def _teardown_catch_qgis_hooks(self):
        try:
            self.index.layer.nameChanged.disconnect(self._name_changed)
        except Exception:
            pass
        try:
            QgsProject.instance().layerTreeRoot().addedChildren.disconnect(self._node_order_changed)
        except Exception:
            pass
        try:
            self.index.layer.activeScalarDatasetGroupChanged.disconnect(self._scalar_group_changed)
        except Exception:
            pass
        try:
            self.index.layer.activeVectorDatasetGroupChanged.disconnect(self._vector_group_changed)
        except Exception:
            pass
        try:
            self.index.layer.rendererChanged.disconnect(self._renderer_changed)
        except Exception:
            pass
        try:
            self.index.layer.metadataChanged.disconnect(self._metadata_changed)
        except Exception:
            pass
        try:
            self.index.layer.crsChanged.disconnect(self._crs_changed)
        except Exception:
            pass

    def zoom_to_layer(self):
        from qgis.utils import iface
        if iface is None:
            return
        map_canvas = iface.mapCanvas()

        rect = QgsRectangle()
        if Qgis.QGIS_VERSION_INT >= 33400:
            rect.setNull()
        else:
            rect.setMinimal()

        for provider in self._providers.values():
            extent = provider.layer.extent()
            if extent.isEmpty():
                provider.layer.updateExtents()
                extent = provider.layer.extent()
            if extent.isNull():
                continue
            extent = map_canvas.mapSettings().layerExtentToOutputExtent(provider.layer, extent)
            rect.combineExtentWith(extent)

        if rect.isNull():
            return

        rect.scale(1.05)
        map_canvas.setExtent(rect, True)
        map_canvas.refresh()

    def _name_changed(self):
        self.alias = self.index.layer.name()
        QgsProject.instance().writeEntry('tuflow_viewer', f'output/{self.id}', self.to_json())

    def _layers_will_be_removed(self, lyrids: list[str]):
        if self.index.layer.id() in lyrids:
            for lyrid in self._ancil_layers:
                lyr = QgsProject.instance().mapLayer(lyrid)
                lyr.removeCustomProperty('tuflow_viewer')  # stops tuflow_viewer from triggering on layer removal
                self._map_layers.remove(lyr)
            QgsProject.instance().removeMapLayers(self._ancil_layers)
            return
        for name, provider in self._providers.copy().items():
            if provider.layer.id() in lyrids:
                self._providers.pop(name)
                self._ancil_layers.remove(provider.layer.id())

    def _node_order_changed(self, node: QgsLayerTreeNode, ind_from: int, ind_to: int):
        if self.index is None:
            return
        if self._node_order_being_changed:
            return

        self._node_order_being_changed = True
        for res in get_viewer_instance().outputs():
            if res.DRIVER_NAME == 'TUFLOW CATCH Json':
                res._node_order_being_changed = True

        layers = [QgsProject.instance().mapLayer(x) for x in self._ancil_layers]

        # check if a hidden layer is being moved - don't let it go above index or below other unassociated layers
        moved_nd = 'unknown'
        if ind_to < len(node.layerOrder()) and node.layerOrder()[ind_to] in layers:
            moved_nd = 'hidden node'
            i = node.layerOrder().index(self.index.layer)
            if ind_to <= i:
                for nd in node.children():
                    if nd.layer() == self.index.layer:
                        node.insertChildNode(ind_to, nd.clone())
                        node.removeChildNode(nd)
            elif ind_to > i + len(layers):
                nd = node.children()[ind_to]
                node.insertChildNode(i + len(layers), nd.clone())
                node.removeChildNode(nd)

        # find index layer - if it is being moved, it will appear twice
        if moved_nd != 'hidden node' and node.layerOrder().count(self.index.layer) == 2:
            i = ind_to
            moved_nd = 'index node'
        else:
            i = node.layerOrder().index(self.index.layer)
            moved_nd = 'other node' if moved_nd == 'unknown' else moved_nd
        i += 1

        # move hidden layers just below index layer - retain original order
        if moved_nd != 'hidden node':
            nd4rem = []
            for k, layer in enumerate(reversed(layers)):
                for nd in node.children():
                    if nd.layer() == layer:
                        node.insertChildNode(i, nd.clone())
                        nd4rem.append(nd)
                        # node.removeChildNode(nd)
                        break
            _ = [node.removeChildNode(x) for x in nd4rem]

        for res in get_viewer_instance().outputs():
            if res.DRIVER_NAME == 'TUFLOW CATCH Json':
                res._node_order_being_changed = False

    def _scalar_group_changed(self, index: int = -1):
        data_type = self.index.active_scalar_data_type(index)
        for provider in self._providers.values():
            if provider != self.index:
                provider.set_active_scalar_data_type(data_type)

    def _vector_group_changed(self, index: int = -1):
        data_type = self.index.active_vector_data_type(index)
        for provider in self._providers.values():
            if provider != self.index:
                provider.set_active_vector_data_type(data_type)

    def _renderer_changed(self):
        if self.index.layer.customProperty('block-signal', False):
            return
        rs_ref = self.index.layer.rendererSettings()
        scalar_settings = rs_ref.scalarSettings(rs_ref.activeScalarDatasetGroup())
        vector_settings = rs_ref.vectorSettings(rs_ref.activeVectorDatasetGroup())

        for provider in self._providers.values():
            rs = provider.layer.rendererSettings()

            # scalar/vector rendering
            rs.setScalarSettings(rs.activeScalarDatasetGroup(), scalar_settings)
            rs.setVectorSettings(rs.activeVectorDatasetGroup(), vector_settings)

            # mesh
            rs.setEdgeMeshSettings(rs_ref.edgeMeshSettings())
            rs.setNativeMeshSettings(rs_ref.nativeMeshSettings())
            rs.setTriangularMeshSettings(rs_ref.triangularMeshSettings())

            # averaging method
            rs.setAveragingMethod(rs_ref.averagingMethod())

            # set the new renderer
            provider.layer.setRendererSettings(rs)

    def _metadata_changed(self):
        # temporal properties
        doc = QDomDocument('TUFLOW Catch')
        element = doc.createElement('temporal-properties')
        self.index.layer.temporalProperties().writeXml(element, doc, QgsReadWriteContext())
        for provider in self._providers.values():
            provider.layer.temporalProperties().readXml(element, QgsReadWriteContext())
            if provider.time_offset != 0:
                rt = provider.provider_reference_time() + timedelta(seconds=provider.time_offset)
                provider.set_provider_reference_time(rt)

    def _crs_changed(self):
        crs = self.index.layer.crs()
        for provider in self._providers.values():
            provider.layer.setCrs(crs)
