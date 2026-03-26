import typing

from qgis.PyQt.QtCore import pyqtSignal, QTimer, Qt
from qgis.PyQt.QtGui import QKeyEvent
from qgis.PyQt.QtWidgets import QApplication

from qgis.gui import QgsMapCanvasItem, QgsMapTool, QgsMapCanvas
from qgis.utils import iface

from ..tvinstance import get_viewer_instance

from ...compatibility_routines import QT_KEY_ESCAPE, QT_KEY_F1, QT_KEY_MODIFIER_SHIFT

if typing.TYPE_CHECKING:
    from ..widgets.tv_plot_widget.base_plot_widget import TVPlotWidget


class DrawTool(QgsMapTool):

    finished = pyqtSignal()
    updated = pyqtSignal(QgsMapCanvasItem, bool)

    def __init__(self, plot_widget: 'TVPlotWidget', canvas: QgsMapCanvas, *args, **kwargs):
        super().__init__(canvas)
        self.plot_widget = plot_widget
        self.canvas = canvas
        self.help_text_visible = 'TUFLOW Viewer'
        self.help_text_hidden = 'TUFLOW Viewer'
        self.is_help_text_visible = True
        self.previous_map_tool = None
        self.active = False

    def __del__(self):
        self.remove()

    def clear(self):
        pass

    def remove(self):
        pass

    def start(self):
        self.active = True
        help_text = get_viewer_instance().help_text
        help_text.owner = self
        if self.is_help_text_visible:
            help_text.setText(self.help_text_visible)
        else:
            help_text.setText(self.help_text_hidden)
        help_text.show()
        self.previous_map_tool = self.canvas.mapTool()
        self.canvas.setMapTool(self)
        QTimer.singleShot(100, self.shift_focus)

    def shift_focus(self):
        QApplication.setActiveWindow(iface.mainWindow())  # main window gets active
        self.canvas.setFocus()

    def finish(self):
        self.active = False
        if get_viewer_instance().help_text.owner == self:
            get_viewer_instance().help_text.hide()
            get_viewer_instance().help_text.owner = None
        if self.previous_map_tool is not None and self.canvas.mapTool() == self:
            self.canvas.setMapTool(self.previous_map_tool)

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() == QT_KEY_ESCAPE:
            self.finish()
            self.finished.emit()
            return
        help_text = get_viewer_instance().help_text
        if e.key() == QT_KEY_F1 and e.modifiers() & QT_KEY_MODIFIER_SHIFT:
            if self.is_help_text_visible:
                help_text.setText(self.help_text_hidden)
                self.is_help_text_visible = False
            else:
                help_text.setText(self.help_text_visible)
                self.is_help_text_visible = True
            return
        super().keyReleaseEvent(e)
