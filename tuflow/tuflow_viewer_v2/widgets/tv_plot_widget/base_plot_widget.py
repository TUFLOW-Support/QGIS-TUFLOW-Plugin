import typing

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QWidget

from .ui_plot_widget import Ui_TVPlotWidget
from .mixins.gui_setup_mixin import GuiSetupMixin
from .mixins.interaction_mixin import InteractionMixin
from .mixins.plot_manager_mixin import PlotManagerMixin
from .mixins.qgis_hooks_mixin import QgisHooksMixin
from .mixins.menu_toolbar_mixin import MenuToolbarMixin
from .mixins.plot_linker_mixin import PlotLinkerMixin
from .mixins.draw_tool_mixin import DrawToolMixin
from .mixins.selection_tool_mixin import SelectionToolMixin
from .pyqtgraph_subclass.tuflow_viewer_curve import TuflowViewerCurve

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...tvinstance import get_viewer_instance
else:
    from tuflow.tuflow_viewer_v2.tvinstance import get_viewer_instance

if typing.TYPE_CHECKING:
    # noinspection PyUnusedImports
    from ...tvinstance import TuflowViewer
    from qgis.PyQt.QtCore import QEvent


class TVPlotWidget(QWidget, Ui_TVPlotWidget,
                   InteractionMixin,
                   SelectionToolMixin,
                   DrawToolMixin,
                   PlotLinkerMixin,
                   MenuToolbarMixin,
                   GuiSetupMixin,
                   PlotManagerMixin,
                   QgisHooksMixin):
    """Composite widget that unifies eight mixins with a common lifecycle.

    Expected mixin lifecycle API:
      - GuiSetupMixin: _init_gui(), _teardown_gui()
      - InteractionMixin: _init_interaction(), _teardown_interaction(), connect_to_plot_window_signals(plot_window)
      - PlotManagerMixin: _init_plot_manager(), _teardown_plot_manager()
      - QgisHooksMixin: _init_qgis_hooks(), _teardown_qgis_hooks()

    Notes:
      - plot_window property setter must call connect_to_plot_window_signals before assigning.
      - leaveEvent delegates to on_focus_change to allow mixins to reset hover state.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tv: 'TuflowViewer' = get_viewer_instance()

        # init from mixins
        self._init_qgis_hooks()
        self._init_plot_manager()
        self._init_gui()
        self._init_menus_and_toolbar()
        self._init_plot_linker()
        self._init_interaction()
        self._init_draw_tool()
        self._init_selection_tool()

    def __repr__(self):
        return f"<TVPlotWidget {self.__class__.__name__}>"

    @property
    def plot_window(self):
        return self._plot_window

    @plot_window.setter
    def plot_window(self, pw):
        self.connect_to_plot_window_drawn_item_signals(pw)
        self._plot_window = pw
        if self._geom_type == 'marker':
            self.draw_tool.set_markers(self._plot_window.markers())
        else:
            self.draw_tool.set_lines(self._plot_window.lines())

    def plot_items(self) -> list[TuflowViewerCurve]:
        items = []
        for item in self.plot_graph.items():
            if isinstance(item, TuflowViewerCurve):
                items.append(item)
        return items

    def leaveEvent(self, event: 'QEvent'):
        # override method - this is why camelCase is used here
        self.on_focus_change(None, None)
        super().leaveEvent(event)

    def close(self):
        """Tear down cleanly via mixins"""
        self._teardown_menus_and_toolbar()
        self._teardown_selection_tool()
        self._teardown_draw_tool()
        self._teardown_interaction()
        self._teardown_plot_linker()

        self._teardown_gui()
        self._teardown_plot_manager()
        self._teardown_qgis_hooks()
        super().close()
