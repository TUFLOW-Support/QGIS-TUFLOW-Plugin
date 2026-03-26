import typing

from qgis.utils import iface

if typing.TYPE_CHECKING:
    from qgis.PyQt.QtCore import pyqtBoundSignal
    from qgis.PyQt.QtWidgets import QAction
    from qgis.core import QgsVectorLayer
    from qgis.gui import QgsMapTool, QgsMapCanvas
    from ..pyqtgraph_subclass.custom_plot_widget import CustomPlotWidget
    from ...plot_window import PlotWindow
    from ...tv_plot_toolbar import TVPlotToolBar


class SupportsQgisHooks(typing.Protocol):
    _geom_type: str
    _clyr: 'QgsVectorLayer | None'
    selection_changed: 'pyqtBoundSignal'


class SupportsPlotManager(typing.Protocol):
    def clear_feature_selection(self): ...
    def update_feature_selection(self, lyr: 'QgsVectorLayer | None', selected_fids: list[int]): ...


class SupportsMenuToolbar(typing.Protocol):
    clear_feature_selection_requested: 'pyqtBoundSignal'
    selection_tool_toggled: 'pyqtBoundSignal'


class SupportsInteraction(typing.Protocol):
    def update_plot(self) -> None: ...


class SupportUI(SupportsQgisHooks, SupportsPlotManager, SupportsMenuToolbar, SupportsInteraction, typing.Protocol):
    plot_graph: 'CustomPlotWidget'
    toolbar: 'TVPlotToolBar'
    _plot_window: 'PlotWindow | None'


class SelectionToolMixin:
    """Handles updating the plot based on feature selection in the map canvas.

    Depends on QgisHooksMixin, PlotManagerMixin, MenuToolbarMixin, and InteractionMixin.
    """

    @property
    def selection_tool_action(self) -> 'QAction':
        return iface.actionSelect()

    def _init_selection_tool(self: SupportUI):
        self.selection_changed.connect(self.update_layer_selection)
        self.clear_feature_selection_requested.connect(self._clear_feature_selection)
        self.selection_map_tool = self.tv.selection_map_tool
        self._active = False
        self.selection_tool_toggled.connect(self._selection_tool_toggled)
        self.tv.selection_map_tool.finished.connect(self._selection_map_tool_finished)

    def _teardown_selection_tool(self: SupportUI):
        try:
            self.selection_changed.disconnect(self.update_layer_selection)
        except Exception:
            pass
        try:
            self.clear_feature_selection_requested.disconnect(self._clear_feature_selection)
        except Exception:
            pass
        try:
            self.selection_tool_toggled.disconnect(self._selection_tool_toggled)
        except Exception:
            pass
        if self._active:
            self.toggle_selection_tool(False)

    def _selection_tool_toggled(self, active: bool):
        self._active = active
        if active:
            self.selection_map_tool.start()
        else:
            self.selection_map_tool.finish()

    def is_selection_tool_active(self) -> bool:
        return self._active

    def toggle_selection_tool(self: SupportUI, active: bool):
        self.toolbar.selection_action.setChecked(active)
        if not active and self.selection_map_tool.active:
            self.selection_map_tool.finish()

    def _selection_map_tool_finished(self):
        self.toggle_selection_tool(False)

    def update_layer_selection(self: SupportUI, selected_ids: list[int], *args, **kwargs):
        if not self.toolbar.selection_active():
            return
        self.update_feature_selection(self._clyr, selected_ids)
        self.update_plot()

    def _clear_feature_selection(self: SupportUI):
        self.clear_feature_selection()
        self.update_plot()
