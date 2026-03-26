import typing
from typing import Callable

from qgis.core import QgsApplication
from qgis.gui import QgsMapCanvas, QgsVertexMarker, QgsMapMouseEvent

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtGui import QColor, QMouseEvent

from .draw_tool import DrawTool

from ...compatibility_routines import QT_CURSOR_CROSS, QT_LEFT_BUTTON, QT_RIGHT_BUTTON, QT_KEY_MODIFIER_CONTROL

if typing.TYPE_CHECKING:
    from ..widgets.tv_plot_widget.base_plot_widget import TVPlotWidget

import logging
logger = logging.getLogger('tuflow_viewer')


class PointDraw(DrawTool):

    def __init__(self, plot_widget: 'TVPlotWidget', canvas: QgsMapCanvas, colour_generator: Callable):
        super().__init__(plot_widget, canvas)
        self.colour_generator = colour_generator
        self.markers = []
        self.previous_map_tool = None
        self.cursor_override_count = 0

        self.help_text_visible = (
            'TUFLOW Viewer / Point Draw Tool<br>' 
            '<ul>' 
            '<li><img src=":/tuflow-plugin/icons/mouse-left-button.svg" width="32" height="32">: Add point</li>'
            '<li><img src=":/tuflow-plugin/icons/mouse-left-button.svg" width="32" height="32"> '
            '<img src=":/tuflow-plugin/icons/plus.svg" width="12" height="12"><b> Ctrl</b>: Re-position active point</li>'
            '<li><img src=":/tuflow-plugin/icons/mouse-right-button.svg" width="32" height="32"> <b>/ Esc</b>:  Finish</li>'
            '<li><img src=":/tuflow-plugin/icons/draw.svg" width="32" height="32"> '
            '<img src=":/tuflow-plugin/icons/plus.svg" width="12" height="12"> '
            '<img src=":/images/themes/default/mActionToggleEditing.svg" width="32" height="32">: Select active point'
            '</ul>'
            'Shift + F1 to hide help text'
        )
        self.help_text_hidden = \
            'TUFLOW Viewer / Point Draw Tool<br>' \
            'Shift + F1 to show help text'

    def __contains__(self, item):
        return item in self.markers

    def set_markers(self, markers: list[QgsVertexMarker]):
        self.markers = markers

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

    def clear(self, idx: int = -1):
        if idx > -1:
            self.canvas.scene().removeItem(self.markers[idx])
            self.markers.pop(idx)
        else:
            for m in self.markers:
                try:
                    self.canvas.scene().removeItem(m)
                except Exception:
                    pass
            self.markers.clear()

    def remove(self, idx: int = -1, map_item: QgsVertexMarker = None):
        """Remove the marker from the canvas."""
        if map_item is not None:
            self.markers.remove(map_item)
            try:
                self.canvas.scene().removeItem(map_item)
                logger.debug(f'Marker removed: {map_item.color().name()}')
            except Exception:
                pass
            return
        self.clear(idx)
        if idx == -1 and map_item is None:
            self.finish()

    def create_marker(self):
        c = QColor(self.colour_generator('drawn'))
        marker = QgsVertexMarker(self.canvas)
        marker.setColor(c)
        marker.setFillColor(c)
        marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
        marker.setIconSize(10)
        logger.debug(f'Added new marker: {c.name()}')
        return marker

    def canvasMoveEvent(self, e: QgsMapMouseEvent):
        super().canvasMoveEvent(e)
        if not self.active:
            return
        if QgsApplication.overrideCursor() != QT_CURSOR_CROSS:
            QgsApplication.setOverrideCursor(QT_CURSOR_CROSS)
            self.cursor_override_count += 1

    def canvasReleaseEvent(self, e: QgsMapMouseEvent):
        super().canvasReleaseEvent(e)
        if not self.active:
            return
        if e.button() == QT_LEFT_BUTTON:
            point = self.canvas.getCoordinateTransform().toMapCoordinates(e.pos())
            marker = None
            if e.modifiers() & QT_KEY_MODIFIER_CONTROL:
                if self.plot_widget.draw_menu_editable_action():
                    marker = self.plot_widget.draw_menu_editable_action().map_item
                    new = False
            else:
                new = True
                marker = self.create_marker()
            if marker:
                marker.setCenter(point)
                logger.debug(f'Moved marker to {point.asWkt()}')
                self.updated.emit(marker, new)
        elif e.button() == QT_RIGHT_BUTTON:
            self.finish()
            self.finished.emit()
