import typing
from collections import OrderedDict

try:
    import plotly.express as px
except ImportError:
    px = None
import matplotlib.pyplot as plt
from qgis.PyQt.QtCore import pyqtSignal, QObject, QEvent, Qt, QPoint, QRect, QSettings, QCoreApplication, QTimer
from qgis.PyQt.QtWidgets import QDialog, QTabBar, QLabel, QWidget, QStyleFactory, QApplication, QDockWidget, QApplication
from qgis.PyQt.QtGui import QColor, QCloseEvent, QResizeEvent, QMoveEvent

from qgis.gui import QgsVertexMarker, QgsMapCanvasItem, QgsRubberBand, QgsMapTool, QgsDockWidget

# from .ui_plot_window import Ui_PlotWindow
from .ui_plot_window_dock import Ui_PlotWindow
from ..tvinstance import get_viewer_instance
from .tv_plot_widget.base_plot_widget import TVPlotWidget
from .tv_plot_widget.colours import ColourAllocator
from ..theme import TuflowViewerTheme

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...compatibility_routines import (QT_KEY_ESCAPE, QT_DOCK_WIDGET_AREA_ALL, QT_DOCK_WIDGET_AREA_NONE,
                                           QT_WINDOW_TYPE, QT_EVENT_KEY_PRESS)
else:
    from tuflow.compatibility_routines import (QT_KEY_ESCAPE, QT_DOCK_WIDGET_AREA_ALL, QT_DOCK_WIDGET_AREA_NONE,
                                               QT_WINDOW_TYPE, QT_EVENT_KEY_PRESS)

if typing.TYPE_CHECKING:
    from ..tuflow_viewer import TuflowViewer

class PlotWindow(QgsDockWidget, Ui_PlotWindow):

    markersChanged = pyqtSignal()
    linesChanged = pyqtSignal()
    closed = pyqtSignal(QWidget)

    def __init__(self, tuflow_viewer: 'TuflowViewer', id_: int = -1):
        super().__init__(tuflow_viewer.iface.mainWindow())
        self._window_id = id_
        self._markers = []
        self._lines = OrderedDict()

        self.setStyleSheet(tuflow_viewer.theme.style_sheet)
        self.setPalette(tuflow_viewer.theme.palette)
        self.setupUi(self)
        self.setWindowTitle(f'TUFLOW Viewer ({id_})')
        self.setObjectName('TuflowViewerPlotWindow')
        # self.setWindowIcon(get_viewer_instance().icon('tuview'))
        self.dockable_window_flags = (Qt.WindowType.X11BypassWindowManagerHint |
                                      Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint |
                                      Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowCloseButtonHint |
                                      Qt.WindowType.Dialog | Qt.WindowType.Popup | Qt.WindowType.Tool)
        self.setWindowFlags(self.dockable_window_flags)
        self.child = None
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        self.btn_is_dockable.setIcon(get_viewer_instance().icon('not_dockable'))
        self.btn_is_dockable.setCheckable(True)
        self.btn_is_dockable.toggled.connect(self.set_dockable)

        # primary tab widget view
        self.tabWidget_view1.plot_window = self
        self.tabWidget_view1.move_add_btn()
        self.tabWidget_view1.widget(0).close()
        self.tabWidget_view1.clear()
        self.tabWidget_view1.add_time_series_tab()
        self.set_origin_plot(self.tabWidget_view1.widget(0))
        self.tabWidget_view1.plot_linking_changed.connect(self.plot_linking_changed)

        # second tab widget view
        self.tabWidget_view2.name = 'view2'
        self.tabWidget_view2.plot_window = self
        self.tabWidget_view2.clear()
        self.tabWidget_view2.hide()
        self.tabWidget_view2.plot_linking_changed.connect(self.plot_linking_changed)

        colours = plt.rcParams['axes.prop_cycle'].by_key()['color']
        if px is not None:
            colours += px.colors.qualitative.Plotly
        self._marker_colours = ColourAllocator(colours)
        self._line_colours = ColourAllocator(colours)

        self.view2_first_show = True  # to track if view2 is shown for the first time

        self.installEventFilter(self)

        # get the dialog state
        dlg_state = QSettings().value('tuflow_viewer/plot_window/state', None)
        if dlg_state is not None:
            self.restoreGeometry(dlg_state)

    def eventFilter(self, a0: 'QObject', a1: QEvent) -> bool:
        if a1.type() == QT_EVENT_KEY_PRESS:
            if a1.key() == QT_KEY_ESCAPE:
                return True
        return False

    def closeEvent(self, event: QCloseEvent):
        QSettings().setValue('tuflow_viewer/plot_window/state', self.saveGeometry())
        self.reject()
        for tab_widget in [self.tabWidget_view1, self.tabWidget_view2]:
            count = tab_widget.count()
            for i in range(tab_widget.count()):
                j = count - i - 1
                plot_widget = tab_widget.widget(j)
                plot_widget.close()
                tab_widget.remove_tab(j)
        super().closeEvent(event)

    def changeEvent(self, event):
        if event.type() in [QEvent.Type.ParentChange]:
            parent = self.parent()
            if parent.objectName() != 'QgisApp':
                children = parent.children()
                for child in children:
                    if child != self and isinstance(child, PlotWindow):
                        if not child.btn_is_dockable.isChecked():
                            self.child = child
                            QTimer.singleShot(300, self.set_child_dockable)
        super().changeEvent(event)

    def set_child_dockable(self):
        if self.child:
            self.child.set_dockable(True)
            self.child = None

    def reject(self):
        _ = [self.tabWidget_view1.widget(i).close() for i in range(self.tabWidget_view1.count())]
        _ = [self.tabWidget_view2.widget(i).close() for i in range(self.tabWidget_view2.count())]
        self.closed.emit(self)
        super().close()
        self.deleteLater()

    def set_theme(self, theme: TuflowViewerTheme):
        if not theme.valid:
            return
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setStyleSheet(theme.style_sheet)
        self.setPalette(theme.palette)
        for tab_widget in [self.tabWidget_view1, self.tabWidget_view2]:
            tab_widget.set_theme(theme)
        _translate = QCoreApplication.translate
        self.help_text_label.setText(_translate("PlotWindow", f"<html><head/><body><p><a href=\"https://docs.tuflow.com/qgis-tuflow-plugin/latest/tuflow-viewer/plot-window/\"><span style=\" text-decoration: underline; color:{get_viewer_instance().theme.palette.link().color().name()};\">Documentation</span></a></p></body></html>"))

    def set_dockable(self, checked: bool):
        icon = get_viewer_instance().icon('is_dockable') if checked else get_viewer_instance().icon('not_dockable')
        self.btn_is_dockable.setIcon(icon)
        if self.btn_is_dockable.isChecked() != checked:
            self.btn_is_dockable.setChecked(checked)
        if checked:
            QTimer.singleShot(100, self.set_dock_areas_all)
        else:
            if not self.isFloating():
                QTimer.singleShot(100, self.pop_from_dock)
            else:
                QTimer.singleShot(100, self.set_dock_areas_none)

    def set_dock_areas_all(self):
        self.setAllowedAreas(QT_DOCK_WIDGET_AREA_ALL)
        QTimer.singleShot(100, self.set_features_dockable)

    def set_features_dockable(self):
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        QTimer.singleShot(100, self.show)

    def pop_from_dock(self):
        pos = self.mapToGlobal(QPoint(0, 0))
        size = self.size()
        self.setFloating(True)
        self.setGeometry(QRect(pos, size))
        # QTimer.singleShot(100, self.set_dock_areas_none)

    def set_dock_areas_none(self):
        self.setAllowedAreas(QT_DOCK_WIDGET_AREA_NONE)
        QTimer.singleShot(100, self.set_features_non_dockable)

    def set_features_non_dockable(self):
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        QTimer.singleShot(100, self.show)

    def split_view_equally(self):
        # set the splitter to be equally split
        self.splitter.setSizes([self.splitter.width() // 2, self.splitter.width() // 2])

    def switch_tab_view_order(self):
        self.splitter.insertWidget(0, self.tabWidget_view2)
        self.tabWidget_view1, self.tabWidget_view2 = self.tabWidget_view2, self.tabWidget_view1
        self.tabWidget_view1.name = 'view1'
        self.tabWidget_view2.name = 'view2'

    def map_tool_changed(self, tool: QgsMapTool):
        for tab_widget in [self.tabWidget_view1, self.tabWidget_view2]:
            for i in range(tab_widget.count()):
                plot_widget = tab_widget.widget(i)
                if plot_widget.is_draw_tool_active() and tool != plot_widget.draw_tool:
                    plot_widget.toggle_draw_tool(False)
                if plot_widget.is_selection_tool_active() and tool.action() != plot_widget.selection_tool_action:
                    plot_widget.toggle_selection_tool(False)

    def next_colour(self, geom: str, sel_type: str) -> str:
        colours = self._marker_colours if geom == 'marker' else self._line_colours
        return colours.next_colour(unique=sel_type == 'drawn')  # drawn items should use unique colours as it is used as an identifier

    def release_colour(self, name: str, geom: str, sel_type: str):
        colours = self._marker_colours if geom == 'marker' else self._line_colours
        colours.release(name)

    def reset_colours(self, geom: str):
        colours = self._marker_colours if geom == 'marker' else self._line_colours
        colours.reset()

    def add_drawn_item(self, item: QgsMapCanvasItem, markers: list[QgsVertexMarker]):
        if isinstance(item, QgsVertexMarker):
            self.add_marker(item)
        else:
            self.add_line(item, markers)

    def remove_drawn_item(self, item: QgsMapCanvasItem):
        if isinstance(item, QgsVertexMarker):
            self.remove_marker(item)
        else:
            self.remove_line(item)

    def add_marker(self, marker: QgsVertexMarker):
        self._markers.append(marker)
        self.markersChanged.emit()

    def remove_marker(self, marker: QgsVertexMarker):
        if marker in self._markers:
            self._markers.remove(marker)
            self.markersChanged.emit()

    def remove_line(self, line: QgsRubberBand):
        if line in self._lines:
            self._lines.pop(line)
            self.linesChanged.emit()

    def markers(self) -> list[QgsVertexMarker]:
        return self._markers

    def clear_markers(self):
        self._markers.clear()
        self.markersChanged.emit()

    def add_line(self, line: QgsRubberBand, markers: list[QgsVertexMarker]):
        self._lines[line] = markers
        self.linesChanged.emit()

    def update_line(self, line: QgsRubberBand, markers: list[QgsVertexMarker]):
        self._lines[line] = markers

    def lines(self) -> dict:
        return self._lines

    def clear_lines(self):
        self._lines.clear()
        self.linesChanged.emit()

    def connect(self, w: TVPlotWidget):
        w.drawn_item_geom_changed.connect(self.on_drawn_item_geom_changed)

    def on_drawn_item_geom_changed(self, item: QgsMapCanvasItem):
        for tab_widget in [self.tabWidget_view1, self.tabWidget_view2]:
            for i in range(tab_widget.count()):
                w = tab_widget.widget(i)
                if isinstance(item, QgsVertexMarker) and tab_widget.tabText(i) in ['Time Series', 'Profile']:
                    w.draw_tool_updated(item, False)
                elif isinstance(item, QgsRubberBand) and tab_widget.tabText(i) in ['Section', 'Curtain']:
                    w.draw_tool_updated(item, False, self._lines[item])

    def plot_linking_changed(self, plot_widget: TVPlotWidget, linked: bool):
        if not linked and plot_widget.is_origin_plot:
            plot_widget.is_origin_plot = False
            new_origin = None
            for w in self.find_plot_widgets(plot_widget):
                if w == plot_widget:
                    continue
                if w.plot_linker.active:
                    new_origin = w
                    new_origin.set_linked_plot(new_origin)
                    break
            if new_origin:
                self.set_origin_plot(new_origin)

    def origin_plot(self, plot_type: TVPlotWidget) -> TVPlotWidget:
        for w in self.find_plot_widgets(plot_type):
            if w.is_origin_plot:
                return w
        return plot_type

    def set_origin_plot(self, plot_widget: TVPlotWidget):
        for w in self.find_plot_widgets(plot_widget):
            w.set_linked_plot(plot_widget)

    def find_new_origin_plot(self, plot_widget: TVPlotWidget) -> TVPlotWidget | None:
        for w in self.find_plot_widgets(plot_widget):
            if w == plot_widget or not w.plot_linker.active:
                continue
            w.is_origin_plot = True
            w.plot_graph.getViewBox().setXLink(None)
            return w
        return None

    def find_plot_widgets(self, plot_type: TVPlotWidget) -> typing.Generator[TVPlotWidget, None, None]:
        for tab_widget in [self.tabWidget_view1, self.tabWidget_view2]:
            for i in range(tab_widget.count()):
                w = tab_widget.widget(i)
                if isinstance(w, type(plot_type)):
                    yield w

    def find_plot_widget_from_geom_type(self, geom_type: str) -> typing.Generator[TVPlotWidget, None, None]:
        for tab_widget in [self.tabWidget_view1, self.tabWidget_view2]:
            for i in range(tab_widget.count()):
                w = tab_widget.widget(i)
                if w._geom_type == geom_type:
                    yield w
