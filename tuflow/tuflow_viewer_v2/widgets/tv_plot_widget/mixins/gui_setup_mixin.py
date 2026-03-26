import typing

import matplotlib.pyplot as plt
try:
    import plotly.express as px
except ImportError:
    px = None

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtGui import QColor

from ..colours import ColourAllocator
from ....tvinstance import get_viewer_instance
from ....theme import TuflowViewerTheme

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....compatibility_routines import QT_TAB_FOCUS, QT_PAINTER_ANTIALIASING, QT_STYLE_DOTTED_PEN
    from .....pyqtgraph import setConfigOption, mkPen
else:
    from tuflow.compatibility_routines import QT_TAB_FOCUS, QT_PAINTER_ANTIALIASING, QT_STYLE_DOTTED_PEN
    from tuflow.pyqtgraph import setConfigOption, mkPen

if typing.TYPE_CHECKING:
    from ..pyqtgraph_subclass.custom_view_box import CustomViewBox
    from ..pyqtgraph_subclass.custom_plot_widget import CustomPlotWidget
    from ...plot_window import PlotWindow
    from qgis.gui import QgsVertexMarker, QgsRubberBand


class SupportsQgisHooks(typing.Protocol):
    _hover_marker: 'QgsVertexMarker'
    _hover_rubber_band: 'QgsRubberBand'
    _geom_type: str


class SupportsPlotManager(typing.Protocol):
    secondary_vb: 'CustomViewBox | None' = None


class SupportUI(SupportsQgisHooks, SupportsPlotManager, typing.Protocol):
    plot_graph: 'CustomPlotWidget'
    _plot_window: 'PlotWindow | None'

    def setupUi(self, object: typing.Any) -> None:...
    def setFocusPolicy(self, policy: int) -> None:...


class GuiSetupMixin:
    """Deals with initialising and tearing down the GUI elements.

    Depends on QgisHooksMixin and PlotManagerMixin.
    """

    def _init_gui(self: SupportUI):
        self.palette = get_viewer_instance().theme.palette
        self.setupUi(self)
        self.setFocusPolicy(QT_TAB_FOCUS)
        self.plot_graph.setParent(self)
        self.plot_graph.setBackground(self.palette.base() if self.palette else QColor('#ffffff'))
        setConfigOption('foreground', self.palette.text().color() if self.palette else QColor('#000000'))
        self.plot_graph.showGrid(x=True, y=True)
        self.plot_graph.setRenderHints(QT_PAINTER_ANTIALIASING)

        for axis_name in ['left', 'bottom']:
            axis = self.plot_graph.getAxis(axis_name)
            axis.setPen(mkPen(self.palette.text().color() if self.palette else '#000000'))
            axis.setTextPen(mkPen(self.palette.text().color() if self.palette else '#000000'))

        self._plot_window  = None

        # colour cycle
        available_colours = plt.rcParams['axes.prop_cycle'].by_key()['color']
        if px is not None:
            available_colours += px.colors.qualitative.Plotly
        self._colours = ColourAllocator(available_colours)

    def _teardown_gui(self: SupportUI):
        pass

    def set_theme(self: SupportUI, theme: TuflowViewerTheme):
        self.palette = get_viewer_instance().theme.palette
        if not self.palette:
            return
        self.toolbar.set_theme(theme)
        self.plot_graph.setBackground(self.palette.base())
        setConfigOption('foreground', self.palette.text().color())
        self.plot_graph.setRenderHints(QT_PAINTER_ANTIALIASING)

        for axis_name in ['left', 'bottom', 'right', 'top']:
            axis = self.plot_graph.getAxis(axis_name)
            if not axis:
                continue
            axis.setPen(mkPen(self.palette.text().color()))
            axis.setTextPen(mkPen(self.palette.text().color()))

    def next_colour(self: SupportUI, sel_type: str) -> str:
        """Get the next available colour from the plot window's colour allocator.
        The colour is allocated based on the geometry type (marker/line).
        """
        if self._plot_window:
            return self._plot_window.next_colour(self._geom_type, sel_type)
        return ''

    def release_colour(self: SupportUI, name: str, sel_type: str):
        """Release a previously allocated colour back to the plot window's colour allocator.
        The colour is released based on the geometry type (marker/line).
        """
        self._colours.release(name)  # required to release colour shifting which is per plot basis
        if self._plot_window:
            self._plot_window.release_colour(name, self._geom_type, sel_type)

    def reset_colours(self: SupportUI):
        """Reset all colours in the plot window's colour allocator for the geometry type (marker/line)."""
        self._colours.reset_colours()  # required to release colour shifting which is per plot basis
        if self._plot_window:
            self._plot_window.reset_colours(self._geom_type)

    def on_focus_change(self: SupportUI, *args, **kwargs):
        """"Called when the focus changes in the application."""
        if self._hover_marker:
            self._hover_marker.hide()
        if self._hover_rubber_band:
            self._hover_rubber_band.hide()
        for item in self.plot_graph.items():
            if hasattr(item, 'hover_dist'):
                item.set_hover_visible(False)

    def suppress_tooltip(self: SupportUI, suppress: bool):
        """Suppress or enable tooltips on all items in the plot graph."""
        for item in self.plot_graph.scene().items():
            if hasattr(item, 'suppress_tooltip'):
                item.suppress_tooltip = suppress

    def get_top_view_box(self: SupportUI) -> 'CustomViewBox':
        """Returns the top-most visible view box, which is the secondary view box if it exists and is visible,
        otherwise the primary view box of the plot graph.
        """
        return self.secondary_vb if self.secondary_vb is not None and self.secondary_vb.isVisible() \
            and self.secondary_vb.zValue() > self.plot_graph.getViewBox().zValue() else self.plot_graph.getViewBox()
