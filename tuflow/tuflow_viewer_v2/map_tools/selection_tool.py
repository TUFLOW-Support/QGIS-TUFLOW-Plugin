import typing

from qgis.PyQt.QtCore import QTimer

from .draw_tool import DrawTool
from ..tvinstance import get_viewer_instance

from ...compatibility_routines import QT_KEY_ESCAPE, QT_KEY_F1, QT_KEY_MODIFIER_SHIFT, QT_EVENT_KEY_PRESS

if typing.TYPE_CHECKING:
    from ..widgets.tv_plot_widget.base_plot_widget import TVPlotWidget
    from qgis.gui import QgsMapCanvas


class SelectionMapTool(DrawTool):
    """A map tool that just adds help text. Map tool does actually activate since
    the QGIS select map tool needs to stay active, instead this installs an event filter.
    """

    def __init__(self, plot_widget: 'TVPlotWidget', canvas: 'QgsMapCanvas'):
        super().__init__(plot_widget, canvas)
        self.stack = 0

        self.help_text_visible = (
            'TUFLOW Viewer / Selection Tool<br>'
            '<ul>'
            '<li><img src=":/tuflow-plugin/icons/mouse-left-button.svg" width="32" height="32">: Select features</li>'
            '<li><b>Esc</b>: Finish</li>'
            '</ul>'
            'Shift + F1 to hide help text'
        )
        self.help_text_hidden = (
            'TUFLOW Viewer / Selection Tool<br>'
            'Shift + F1 to show help text'
        )

    def start(self):
        # override so that map tool is not actually activated
        self.stack += 1
        if self.stack > 1:
            return
        self.active = True
        help_text = get_viewer_instance().help_text
        help_text.owner = 'selection_map_tool'  # use text because owner is shared by all plots
        if self.is_help_text_visible:
            help_text.setText(self.help_text_visible)
        else:
            help_text.setText(self.help_text_hidden)
        help_text.show()
        QTimer.singleShot(100, self.shift_focus)
        self.canvas.installEventFilter(self)

    def finish(self):
        self.stack -= 1
        if self.stack:
            return
        self.active = False
        if get_viewer_instance().help_text.owner == 'selection_map_tool':
            get_viewer_instance().help_text.hide()
        self.canvas.removeEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QT_EVENT_KEY_PRESS:
            if event.key() == QT_KEY_ESCAPE:
                self.finish()
                self.finished.emit()
                return True
            elif event.key() == QT_KEY_F1 and event.modifiers() & QT_KEY_MODIFIER_SHIFT:
                help_text = get_viewer_instance().help_text
                if self.is_help_text_visible:
                    help_text.setText(self.help_text_hidden)
                    self.is_help_text_visible = False
                else:
                    help_text.setText(self.help_text_visible)
                    self.is_help_text_visible = True
                return True
        return False
