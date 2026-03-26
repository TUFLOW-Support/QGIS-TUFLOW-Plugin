import json
import typing
import logging
from datetime import datetime, timezone

from qgis.core import QgsMapLayer, QgsPointXY, QgsGeometry, QgsFeature, QgsVectorLayer
from qgis.gui import QgsVertexMarker, QgsRubberBand
from qgis.utils import iface
from qgis.PyQt.QtCore import pyqtSignal, QPointF, QSettings
from qgis.PyQt.QtGui import QColor

from ..cursor_tracker import CursorTrackerManager
from ....tvinstance import get_viewer_instance

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....compatibility_routines import QT_DASH_LINE
    from .....toc.toc import node_to_layer
    from .....pt.pytuflow.util import misc
    from .....pt.pytuflow import INFO, TuflowPath
else:
    from tuflow.compatibility_routines import QT_DASH_LINE
    from tuflow.toc.toc import node_to_layer
    from tuflow.pt.pytuflow.util import misc
    from tuflow.pt.pytuflow import INFO, TuflowPath

if typing.TYPE_CHECKING:
    from ....fmts.tvoutput import TuflowViewerOutput


logger = logging.getLogger('tuflow_viewer')


class QgisHooksMixin:
    """Handles QGIS integration:
      - responds to temporal range updates
      - responds to layer/feature selection changes
      - manages marker and rubberbands in the map window that represent hover positions and active geometries

    Independent of the other plot mixins.
    """
    selection_changed = pyqtSignal(list, list, bool)

    def _init_qgis_hooks(self):
        self._time_updated = False
        self._clyr = None
        self._hover_marker = self._init_hover_marker()  # basic hover over point marker - only one will be active at once
        self._hover_rubber_band = self._init_hover_rubber_band()  # basic hover over geometry rubber band - only one will be active at once
        self._cursor_tracker = CursorTrackerManager(iface.mapCanvas())  # manages multiple trackers - for showing on the map canvas where the cursor is on the plot
        self.qgis_current_layer_changed(iface.activeLayer())
        iface.mapCanvas().currentLayerChanged.connect(self.qgis_current_layer_changed)
        iface.mapCanvas().temporalRangeChanged.connect(self.qgis_time_changed)

    def _teardown_qgis_hooks(self):
        try:
            iface.mapCanvas().currentLayerChanged.disconnect(self.qgis_current_layer_changed)
        except Exception:
            pass
        try:
            iface.mapCanvas().temporalRangeChanged.disconnect(self.qgis_time_changed)
        except Exception:
            pass
        if self._clyr is not None:
            try:
                try:
                    self._clyr.selectionChanged.disconnect(self.selected_features_changed)
                except Exception:
                    pass
            except RuntimeError:  # sometimes clyr is deleted before disconnecting
                pass
            self._clyr = None
        self._hover_marker = None
        self._hover_rubber_band = None
        self._cursor_tracker.clear()

    def update_qgis_static_feedback(self, geom: list[float] | list[list[float]] | None):
        """Show/hide the hover marker/rubber band in the QGIS map window."""
        if geom is None:
            self.update_hover_marker_geometry(None)
            self.update_hover_rubber_band_geometry(None)
            return
        is_point = misc.list_depth(geom) < 2
        if is_point:
            self.update_hover_marker_geometry(geom)
            self.update_hover_rubber_band_geometry(None)
        else:
            self.update_hover_marker_geometry(None)
            self.update_hover_rubber_band_geometry(geom)

    def update_qgis_cursor_tracking(self, pos: QPointF):
        self._cursor_tracker.update(pos)

    def update_hover_marker_geometry(self, geom: list[float] | QgsGeometry | None):
        """Updates the marker geometry in the QGIS map window that shows the current hover position.
        If geom is None, the marker is hidden.
        """
        if geom is None:
            self._hover_marker.hide()
        else:
            if isinstance(geom, QgsGeometry):
                p = QgsPointXY(geom.asPoint())
            else:
                p = QgsPointXY(geom[0], geom[1])
            self._hover_marker.setCenter(p)
            self._hover_marker.show()

    def update_hover_rubber_band_geometry(self, geom: list[list[float]] | QgsGeometry | None):
        """Updates the rubber band geometry in the QGIS map window that shows the active geometry.
        If geom is None, the rubber band is hidden.
        """
        if geom is None:
            self._hover_rubber_band.hide()
        else:
            if isinstance(geom, QgsGeometry):
                g = geom
            else:
                g = QgsGeometry.fromPolylineXY([QgsPointXY(x[0], x[1]) for x in geom])
            self._hover_rubber_band.setToGeometry(g, None)
            self._hover_rubber_band.show()

    def _init_hover_marker(self) -> QgsVertexMarker:
        """Initialises a QgsVertexMarker for displaying hover positions in the QGIS map canvas."""
        marker = QgsVertexMarker(iface.mapCanvas())
        marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
        marker.setIconSize(17)
        marker.setColor(QColor('#ff00ff'))
        marker.setPenWidth(2)
        marker.setIconSize(17)
        marker.setVisible(False)
        return marker

    def _init_hover_rubber_band(self) -> QgsRubberBand:
        """Initialises a QgsRubberBand for displaying active geometries in the QGIS map canvas."""
        band = QgsRubberBand(iface.mapCanvas())
        band.setColor(QColor('#ff00ff'))
        band.setLineStyle(QT_DASH_LINE)
        band.setWidth(3)
        band.setVisible(False)
        return band

    def qgis_selected_layers(self) -> list[QgsMapLayer]:
        """Returns a list of currently selected layers in the QGIS layer tree view."""
        tree_view = iface.layerTreeView()
        lyrs = [node_to_layer(tree_view.index2node(idx)) for idx in tree_view.selectionModel().selectedIndexes()]
        return [x for x in lyrs if x is not None and x.isValid() and x.customProperty('tuflow_viewer') is not None]

    def qgis_selected_outputs(self) -> list['TuflowViewerOutput']:
        """Returns a list of TuflowViewerOutput instances selected in the QGIS layer tree view."""
        def get_output(layer: QgsMapLayer):
            try:
                d = json.loads(layer.customProperty('tuflow_viewer'))
                return get_viewer_instance().output(d['id'])
            except json.JSONDecodeError:
                return get_viewer_instance().output(layer.customProperty('tuflow_viewer'))
        lyrs = self.qgis_selected_layers()
        return [get_output(x) for x in lyrs if x.customProperty('tuflow_viewer') is not None]

    def qgis_current_layer_changed(self, layer: QgsMapLayer):
        """Handles changes to the current layer in the QGIS map canvas."""
        if self._clyr is not None:
            try:
                self._clyr.selectionChanged.disconnect(self.selected_features_changed)
            except Exception:
                pass
        if layer is None or layer.type() != QgsMapLayer.VectorLayer:
            self._clyr = None
            return
        self._clyr = layer
        self._clyr.selectionChanged.connect(self.selected_features_changed)

    def selected_features_changed(self, selected_ids: list[int], deselected_ids: list[int], clear_and_select: bool):
        self.selection_changed.emit(selected_ids, deselected_ids, clear_and_select)

    def qgis_layers_removed(self, layers: list[str]):
        """Handles the removal of layers in the QGIS map canvas."""
        for lyrid in layers:
            if self._clyr is not None and lyrid == self._clyr.id():
                self._clyr = None

    def qgis_current_time(self) -> datetime | None:
        """Returns the current time from the QGIS map canvas temporal range."""
        if not iface:
            return datetime(1990, 1, 1, tzinfo=timezone.utc)
        date_range = iface.mapCanvas().temporalRange()
        if date_range.begin().isValid():
            dt = date_range.begin().toPyDateTime()
            if dt.tzinfo is None:
                tz = timezone.utc
                dt = dt.replace(tzinfo=tz)
        else:
            return datetime(1990, 1, 1, tzinfo=timezone.utc)
        return dt

    def qgis_time_range_end(self) -> datetime | None:
        if not iface:
            return datetime(1990, 1, 1, tzinfo=timezone.utc)
        date_range = iface.mapCanvas().temporalRange()
        if not date_range.end().isValid():
            return datetime(1990, 1, 1, tzinfo=timezone.utc)
        dt = date_range.end().toPyDateTime()
        if dt.tzinfo is None:
            tz = timezone.utc
            dt = dt.replace(tzinfo=tz)
        return dt

    def qgis_time_changed(self):
        """Handles changes to the temporal range in the QGIS map canvas.
        Override depending on the plot type."""
        self._time_updated = True

    def get_plot_layer(self, output_id: str, geom: str) -> QgsMapLayer | None:
        output = self.tv.output(output_id)
        if not isinstance(output, INFO):
            return None
        lyr = None
        for map_layer in output.map_layers():
            name = map_layer.name() if map_layer.storageType() == 'Memory storage' else TuflowPath(map_layer.dataProvider().dataSourceUri()).lyrname
            if name.lower().endswith(f'_{geom.lower()[0]}'):
                lyr = map_layer
                break
        return lyr

    def get_feature(self, lyr: QgsVectorLayer, feature_id: str, type_: str) -> QgsFeature | None:
        expr = f'"ID" = \'{feature_id}\' AND "Type" NOT LIKE \'2D\' AND "Type" NOT LIKE \'RL\''
        feats = [f for f in lyr.getFeatures(expr)]
        if not feats:
            return None
        return feats[0]

    def get_channel_feature(self, output_id: str, channel_id: str) -> QgsFeature | None:
        lyr = self.get_plot_layer(output_id, 'Line')
        if not lyr:
            return None
        return self.get_feature(lyr, channel_id, 'Chan')

    def get_node_feature(self, output_id: str, node_id: str) -> 'QgsFeature | None':
        lyr = self.get_plot_layer(output_id, 'Point')
        if not lyr:
            return None
        return self.get_feature(lyr, node_id, 'Node')
