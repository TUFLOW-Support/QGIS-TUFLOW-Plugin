import typing
from logging import getLogger

from qgis.core import QgsFields, QgsFeature, QgsField, QgsVectorLayer, QgsProject, QgsGeometry, Qgis
from qgis.utils import iface
from qgis.gui import QgsVectorLayerSaveAsDialog
from qgis.PyQt.QtCore import QSettings, QMetaType
from qgis.PyQt.QtGui import QAction

from ...drawn_item_action import DrawnItemAction
from ....map_tools.point_draw import PointDraw, DrawTool
from ....map_tools.line_draw import LineDraw

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pt.pytuflow import TuflowPath
else:
    from tuflow.pt.pytuflow import TuflowPath

if typing.TYPE_CHECKING:
    from qgis.gui import QgsMapCanvasItem, QgsVertexMarker
    from qgis.PyQt.QtCore import pyqtBoundSignal
    from qgis.core import QgsGeometry
    from ..pyqtgraph_subclass.custom_view_box import CustomViewBox
    from ..pyqtgraph_subclass.custom_plot_widget import CustomPlotWidget
    from ...tv_plot_toolbar import TVPlotToolBar
    from ...plot_window import PlotWindow
    from ....selection import SelectionItem
    from qgis.PyQt.QtCore import pyqtBoundSignal


logger = getLogger('tuflow_viewer')


class SupportsQgisHooks(typing.Protocol):
    _geom_type: str

    def update_hover_marker_geometry(self, geom: 'list[float] | QgsGeometry | None') -> None: ...
    def update_hover_rubber_band_geometry(self, geom: 'list[list[float]] | QgsGeometry | None') -> None: ...


class SupportsPlotManager(typing.Protocol):
    secondary_vb: 'CustomViewBox | None' = None

    def clear_drawn_selection(self) -> None: ...
    def clear_feature_selection(self) -> None: ...
    def add_drawn_item_to_selection(self, map_item: 'QgsMapCanvasItem') -> None: ...
    def remove_drawn_item_from_selection(self, map_item: 'QgsMapCanvasItem') -> 'SelectionItem | None': ...


class SupportsGui(typing.Protocol):

    def next_colour(self, sel_type: str) -> str: ...
    def release_colour(self, name: str, sel_type: str): ...


class SupportsMenuToolbar(typing.Protocol):
    draw_tool_toggled: 'pyqtBoundSignal'
    clear_drawn_selection_requested: 'pyqtBoundSignal'
    draw_item_hovered: 'pyqtBoundSignal'
    draw_item_toggled: 'pyqtBoundSignal'
    draw_item_removed: 'pyqtBoundSignal'

    def update_draw_menu(self, drawn_items: list['QgsMapCanvasItem'], new_drawn_item: 'QgsMapCanvasItem | None'): ...


class SupportsInteraction(typing.Protocol):
    drawn_item_geom_changed: 'pyqtBoundSignal'

    def update_plot(self) -> None: ...


class SupportUI(SupportsQgisHooks, SupportsPlotManager, SupportsGui, SupportsMenuToolbar, SupportsInteraction, typing.Protocol):
    plot_graph: 'CustomPlotWidget'
    toolbar: 'TVPlotToolBar'
    _plot_window: 'PlotWindow | None'


class DrawToolMixin:
    """Handles the draw tool for adding markers or lines to the plot.

    Depends on QgisHooksMixin, PlotManagerMixin, GuiSetupMixin, MenuToolbarMixin, and InteractionMixin.
    """

    def _init_draw_tool(self: SupportUI):
        if self._geom_type == 'marker':
            pass
        else:
            self.help_text_visible = \
                'TUFLOW Viewer / Line Draw Tool<br>' \
                '- Left Click to add vertex<br>' \
                '- Ctrl + Left Click to reposition vertex<br>' \
                '- Right Click to finish line<br>' \
                '<br>' \
                'Shift + F1 to toggle this help text'

        self.draw_tool = None
        self.set_draw_tool(self.create_draw_tool())
        self._new_drawn_item = None
        self._block_signal = False

        self.draw_tool_toggled.connect(self.toggle_draw_tool)
        self.clear_drawn_selection_requested.connect(self.clear_drawn_items)
        self.draw_item_hovered.connect(self.draw_item_action_hovered)
        self.draw_item_toggled.connect(self.drawn_item_action_toggled)
        self.draw_item_removed.connect(self.drawn_item_action_removed)

        # add copy/drawn items to context menu
        # copy drawn items... this exports them to a memory layer
        self.copy_drawn_items_action = QAction('Copy drawn items into memory layer...', self)
        self.copy_drawn_items_action.triggered.connect(self.copy_drawn_items_to_memory_layer)
        self._copy_menu.addAction(self.copy_drawn_items_action)
        # export drawn items... this exports to a vector file format
        self.export_drawn_items_action = QAction('Export drawn items...', self)
        self.export_drawn_items_action.triggered.connect(self.export_drawn_items)
        self._export_menu.addAction(self.export_drawn_items_action)

    def _teardown_draw_tool(self: SupportUI):
        if self.draw_tool.isActive():
            self.draw_tool.finish()
        try:
            self.draw_tool_toggled.disconnect(self.toggle_draw_tool)
        except Exception:
            pass
        try:
            self.clear_drawn_selection_requested.disconnect(self.clear_drawn_items)
        except Exception:
            pass
        try:
            self.draw_item_hovered.disconnect(self.draw_item_action_hovered)
        except Exception:
            pass
        try:
            self.draw_item_toggled.disconnect(self.drawn_item_action_toggled)
        except Exception:
            pass
        try:
            self.draw_item_removed.disconnect(self.drawn_item_action_removed)
        except Exception:
            pass
        plots = [x for x in self._plot_window.find_plot_widget_from_geom_type(self._geom_type) if x != self]
        if not plots:
            self.draw_tool.clear()

    def connect_to_plot_window_drawn_item_signals(self: SupportUI, plot_window: 'PlotWindow'):
        if self._geom_type == 'marker':
            if self._plot_window is not None:  # disconnect current plot window
                self._plot_window.markersChanged.disconnect(self.draw_menu_updated)
            if plot_window:
                plot_window.markersChanged.connect(self.draw_menu_updated)
        else:
            if self._plot_window is not None:
                self._plot_window.linesChanged.disconnect(self.draw_menu_updated)
            if plot_window:
                plot_window.linesChanged.connect(self.draw_menu_updated)

    def is_draw_tool_active(self) -> bool:
        return self.draw_tool.active if self.draw_tool else False

    def create_draw_tool(self: SupportUI):
        if self._geom_type == 'marker':
            return PointDraw(self, iface.mapCanvas(), self.next_colour)
        else:
            return LineDraw(self, iface.mapCanvas(), self.next_colour)

    def set_draw_tool(self, draw_tool: DrawTool):
        if self.draw_tool:
            self.draw_tool.updated.disconnect(self.draw_tool_updated)
            self.draw_tool.finished.disconnect(self.draw_tool_finished)
        self.draw_tool = draw_tool
        if draw_tool:
            self.draw_tool.updated.connect(self.draw_tool_updated)
            self.draw_tool.finished.connect(self.draw_tool_finished)

    def toggle_draw_tool(self: SupportUI, enabled: bool):
        if enabled:
            if self._geom_type == 'marker':
                self.draw_tool.set_markers(self.plot_window.markers())
            else:
                self.draw_tool.set_lines(self.plot_window.lines())
            self.draw_tool.start()
        else:
            self.draw_tool.finish()
            self.toolbar.draw_action.setChecked(False)

    def drawn_items(self: SupportUI) -> list['QgsMapCanvasItem']:
        if not self._plot_window:
            return []
        return self._plot_window.markers() if self._geom_type == 'marker' else list(self._plot_window.lines().keys())

    def clear_drawn_items(self: SupportUI):
        for map_item in self.drawn_items():
            c = map_item.color() if self._geom_type == 'marker' else map_item.fillColor()
            self.release_colour(c.name(), 'drawn')
        self.clear_drawn_selection()
        self.draw_tool.clear()
        self._plot_window.clear_markers() if self._geom_type == 'marker' else self._plot_window.clear_lines()
        self.update_draw_menu([], None)
        self.update_plot()

    def draw_tool_finished(self: SupportUI):
        self.toolbar.draw_action.setChecked(False)

    def draw_item_action_hovered(self: SupportUI, map_item: 'QgsMapCanvasItem' = None):
        if map_item is None:
            self.update_hover_marker_geometry(None)
            self.update_hover_rubber_band_geometry(None)
            return
        geom = QgsGeometry.fromPointXY(map_item.center()) if self._geom_type == 'marker' else map_item.asGeometry()
        if self._geom_type == 'marker':
            self.update_hover_marker_geometry(geom)
            self.update_hover_rubber_band_geometry(None)
        else:
            self.update_hover_marker_geometry(None)
            self.update_hover_rubber_band_geometry(geom)

    def drawn_item_action_toggled(self: SupportUI, action: DrawnItemAction, checked: bool):
        if checked:
            logger.info('Setting drawn item selected')
            self.add_drawn_item_to_selection(action.map_item)
        else:
            logger.info('Setting drawn item not selected')
            self.remove_drawn_item_from_selection(action.map_item)
        self.update_plot()

    def drawn_item_action_removed(self: SupportUI, action: DrawnItemAction):
        if self._block_signal:
            return
        sel = self.remove_drawn_item_from_selection(action.map_item)
        if action.map_item in self.draw_tool:
            self.draw_tool.remove(map_item=action.map_item)
            self._block_signal = True
            self._plot_window.remove_drawn_item(action.map_item)
            self._block_signal = False
        if sel:
            self.update_plot()
        c = action.map_item.color() if self._geom_type == 'marker' else action.map_item.fillColor()
        self.release_colour(c.name(), 'drawn')

    def draw_tool_updated(self: SupportUI, map_item: 'QgsMapCanvasItem', new: bool, markers: list['QgsVertexMarker'] = ()):
        if self._block_signal or self._plot_window is None:
            return
        if new:
            self._new_drawn_item = map_item
            self._plot_window.add_drawn_item(map_item, markers)  # this will trigger the draw menu update
        else:
            self._plot_window.update_line(map_item, markers) if self._geom_type != 'marker' else None
            self.remove_drawn_item_from_selection(map_item)
            self._block_signal = True
            self.drawn_item_geom_changed.emit(map_item)  # let plot_window know about the change so it can update other plots
            self._block_signal = False

        self.add_drawn_item_to_selection(map_item)
        self.update_plot()

    def draw_menu_updated(self: SupportUI):
        self.update_draw_menu(self.drawn_items(), self._new_drawn_item)

    def copy_drawn_items_to_memory_layer(self):
        lyr = self._convert_drawn_items_to_vector_layer()
        if not lyr:
            return
        if not lyr.isValid():
            logger.error('Failed to create memory layer for drawn items')
            return
        QgsProject.instance().addMapLayer(lyr)
        logger.info('Successfully copied drawn items to memory layer', extra={'messagebar': True})

    def export_drawn_items(self):
        from ..export_to_vector_layer import save_as_vector_file_general
        if Qgis.QGIS_VERSION_INT < 33200:
            logger.error('Exporting drawn items requires QGIS 3.32 or later')
            return
        lyr = self._convert_drawn_items_to_vector_layer()
        if not lyr:
            return
        if not lyr.isValid():
            logger.error('Failed to create memory layer for drawn items')
            return

        def on_success(new_file_name: str, add_to_canvas: bool, layer_name: str, encoding: str, vector_file_name: str):
            if add_to_canvas:
                p = TuflowPath(f'{new_file_name}|layername={layer_name}' if layer_name else new_file_name)
                uri = str(p.dbpath) if p.dbpath.stem.lower() == p.lyrname.lower() else str(p)
                exported_lyr = QgsVectorLayer(uri, p.lyrname, 'ogr')
                if exported_lyr.isValid():
                    QgsProject.instance().addMapLayer(exported_lyr)
                else:
                    logger.error(f'Failed to load exported drawn items layer from {new_file_name}')
                    return
            logger.info(f'Successfully exported drawn items to {new_file_name}', extra={'messagebar': True})

        def on_failure(error_code: int, error_message: str):
            logger.error(f'Failed to export drawn items: {error_message}')

        save_as_vector_file_general(
            lyr,
            False,
            False,
            True,
            on_success,
            on_failure,
            QgsVectorLayerSaveAsDialog.Options(),
            'Save Drawn Items as Vector Layer'
        )

    def _convert_drawn_items_to_vector_layer(self) -> QgsVectorLayer | None:
        feats = self._convert_drawn_items_to_features()
        if not feats:
            return
        if self._geom_type == 'marker':
            uri = 'point'
        else:
            uri = 'linestring'
        crs = QgsProject.instance().crs()
        uri = f'{uri}?crs={crs.authid()}&field=Colour:string(8)'
        lyr = QgsVectorLayer(uri, f'{self.PLOT_TYPE}_drawn_items', 'memory')
        lyr.dataProvider().truncate()
        lyr.dataProvider().addFeatures(feats)
        lyr.updateExtents()
        return lyr

    def _convert_drawn_items_to_features(self) -> list[QgsFeature]:
        if not self.drawn_items():
            logger.warning('No drawn items to export')
            return []
        features = []
        for map_item in self.drawn_items():
            feature = QgsFeature()
            feature.setFields(QgsFields([QgsField('Colour', QMetaType.Type.QString, len=8)]))
            if self._geom_type == 'marker':
                feature.setGeometry(QgsGeometry.fromPointXY(map_item.center()))
                feature.setAttribute('Colour', map_item.color().name())
            else:
                feature.setGeometry(map_item.asGeometry())
                feature.setAttribute('Colour', map_item.fillColor().name())
            features.append(feature)
        return features
