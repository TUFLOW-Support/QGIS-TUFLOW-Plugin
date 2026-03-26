import typing
from collections import OrderedDict

from qgis.core import QgsApplication, QgsGeometry, QgsPoint
from qgis.gui import QgsRubberBand, QgsMapCanvas, QgsMapMouseEvent, QgsVertexMarker
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtGui import QColor, QMouseEvent

from .draw_tool import DrawTool

from ...compatibility_routines import QT_CURSOR_CROSS, QT_LEFT_BUTTON, QT_RIGHT_BUTTON, QT_KEY_MODIFIER_CONTROL

if typing.TYPE_CHECKING:
    from ..widgets.tv_plot_widget.base_plot_widget import TVPlotWidget

import logging
logger = logging.getLogger('tuflow_viewer')


class LineDraw(DrawTool):

    updated = pyqtSignal(QgsRubberBand, bool, list)

    def __init__(self, plot_widget: 'TVPlotWidget', canvas: QgsMapCanvas, colour_generator: typing.Callable):
        super().__init__(plot_widget, canvas)
        self.colour_generator = colour_generator
        self.lines = OrderedDict()
        self.previous_map_tool = None
        self.cursor_override_count = 0
        self.active_line = None
        self.active_points = []
        self.active_markers = []
        self.new = True

        self.help_text_visible = (
            'TUFLOW Viewer / Line Draw Tool<br>'
            '<ul>'
            '<li><img src=":/tuflow-plugin/icons/mouse-left-button.svg" width="32" height="32">: Add point</li>'
            '<li><img src=":/tuflow-plugin/icons/mouse-left-button.svg" width="32" height="32"> '
            '<img src=":/tuflow-plugin/icons/plus.svg" width="12" height="12"><b> Ctrl</b>: Start redraw active line</li>'
            '<li><img src=":/tuflow-plugin/icons/mouse-right-button.svg" width="32" height="32">:  Complete Line</li>'
            '<li><img src=":/tuflow-plugin/icons/draw.svg" width="32" height="32"> '
            '<img src=":/tuflow-plugin/icons/plus.svg" width="12" height="12"> '
            '<img src=":/images/themes/default/mActionToggleEditing.svg" width="32" height="32">: Select active line</li>'
            '<li><b>Esc</b>: Finish</li>'
            '</ul>'
            'Shift + F1 to hide help text'
        )
        self.help_text_hidden = \
            'TUFLOW Viewer / Line Draw Tool<br>' \
            'Shift + F1 to show help text'

    def __del__(self):
        self.remove()

    def __contains__(self, item):
        return item in self.lines

    def set_lines(self, lines: dict[QgsRubberBand, QgsVertexMarker]):
        self.lines = lines

    def start(self):
        QgsApplication.setOverrideCursor(QT_CURSOR_CROSS)
        self.cursor_override_count = 1
        super().start()

    def finish(self):
        if self.cursor_override_count > 0:
            for _ in range(self.cursor_override_count):
                QgsApplication.restoreOverrideCursor()
            self.cursor_override_count = 0
        super().finish()

    def complete_line(self):
        if self.active_line is not None:
            self.active_line.setToGeometry(QgsGeometry.fromPolylineXY(self.active_points), None)
            self.lines[self.active_line] = self.active_markers
            self.updated.emit(self.active_line, self.new, self.lines[self.active_line])
            self.active_line = None
            self.active_points.clear()
            self.active_markers.clear()

    def clear(self, idx: int = -1):
        if idx > -1:
            line = list(self.lines.keys())[idx]
            self.remove(map_item=line)
        else:
            for m in self.lines.copy().keys():
                self.remove(map_item=m)

    def remove(self, idx: int = -1, map_item: QgsRubberBand = None):
        """Remove the marker from the canvas."""
        if map_item is not None:
            markers = self.lines.pop(map_item, [])
            try:
                self.canvas.scene().removeItem(map_item)
                logger.debug(f'Line removed: {map_item.fillColor().name()}')
            except Exception:
                pass
            for m in markers:
                try:
                    self.canvas.scene().removeItem(m)
                    logger.debug(f'Line marker removed: {map_item.color().name()}')
                except Exception:
                    pass
            return
        self.clear(idx)
        if idx == -1 and map_item is None:
            self.finish()

    def create_marker(self, c: QColor) -> QgsVertexMarker:
        marker = QgsVertexMarker(self.canvas)
        marker.setColor(c)
        marker.setIconType(QgsVertexMarker.ICON_BOX)
        marker.setIconSize(10)
        logger.debug(f'Added new line marker: {c.name()}')
        return marker

    def create_line(self):
        c = QColor(self.colour_generator('drawn'))
        line = QgsRubberBand(self.canvas)
        line.setColor(c)
        line.setFillColor(c)
        line.setWidth(2)
        logger.debug(f'Added new line: {c.name()}')
        return line

    def canvasMoveEvent(self, e: QgsMapMouseEvent):
        super().canvasMoveEvent(e)
        if not self.active:
            return
        if QgsApplication.overrideCursor() != QT_CURSOR_CROSS:
            QgsApplication.setOverrideCursor(QT_CURSOR_CROSS)
            self.cursor_override_count += 1
        if self.active_line:
            point = self.canvas.getCoordinateTransform().toMapCoordinates(e.pos())
            temp_points = self.active_points + [point]
            self.active_line.setToGeometry(QgsGeometry.fromPolylineXY(temp_points), None)

    def canvasReleaseEvent(self, e: QgsMapMouseEvent):
        super().canvasReleaseEvent(e)
        if not self.active:
            return
        if e.button() == QT_LEFT_BUTTON:
            point = self.canvas.getCoordinateTransform().toMapCoordinates(e.pos())
            if e.modifiers() & QT_KEY_MODIFIER_CONTROL:
                if self.plot_widget.draw_menu_editable_action():
                    self.active_line = self.plot_widget.draw_menu_editable_action().map_item
                    self.new = False
                if self.active_line:
                    self.active_line.reset()
                    for m in self.active_markers:
                        try:
                            self.canvas.scene().removeItem(m)
                        except Exception:
                            pass
                    for m in self.lines.pop(self.active_line, []):
                        try:
                            self.canvas.scene().removeItem(m)
                        except Exception:
                            pass
                    self.active_points.clear()
                    self.active_markers.clear()
            if self.active_line is None:
                self.new = True
                self.active_line = self.create_line()
            marker = self.create_marker(self.active_line.fillColor())
            marker.setCenter(point)
            logger.debug(f'Moved line marker to: {point.asWkt()}')
            self.active_points.append(point)
            self.active_markers.append(marker)
            self.active_line.setToGeometry(QgsGeometry.fromPolylineXY(self.active_points), None)
        elif e.button() == QT_RIGHT_BUTTON:
            self.complete_line()
