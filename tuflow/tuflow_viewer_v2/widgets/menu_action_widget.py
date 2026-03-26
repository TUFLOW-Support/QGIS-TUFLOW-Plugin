from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QSpacerItem, QMenu
from qgis.PyQt.QtGui import QIcon, QMouseEvent
from qgis.PyQt.QtCore import QEvent, pyqtSignal, QTimer, Qt, QSettings
from qgis.core import QgsApplication

from ..tvinstance import get_viewer_instance

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...compatibility_routines import QT_WA_STYLED_BACKGROUND
else:
    from tuflow.compatibility_routines import QT_WA_STYLED_BACKGROUND


class MenuActionWidget(QWidget):
    """A QWidget that can be used as base for widgets in a QWidgetAction that will
    handle basic cursor highlighting events.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName('menu_action_widget')
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(6, 1, 6, 1)
        self.setLayout(self.layout)
        self.cursor_in_widget = False
        self.setAttribute(QT_WA_STYLED_BACKGROUND, True)
        # self.background_highlight_colour = '#3498db'
        if get_viewer_instance().theme.theme_name == 'Night Mapping':
            self.background_highlight_colour = '#008000'  # Qt.darkGreen
        else:
            self.background_highlight_colour = get_viewer_instance().theme.palette.highlight().color().name()
        parent_menu = self.parent()
        if isinstance(parent_menu, QMenu):
            self.parent().aboutToHide.connect(self.reset_highlight)

    def enterEvent(self, a0: QEvent) -> None:
        """Overrides the enterEvent method to trigger highlighting."""
        # Deactivate any QAction the QMenu thinks is active
        parent_menu = self.parent()
        if isinstance(parent_menu, QMenu):
            parent_menu.setActiveAction(None)
        self.cursor_in_widget = True
        self.set_highlighted(True)

    def leaveEvent(self, a0: QEvent) -> None:
        """Overrides the leaveEvent method to turn of highlighting."""
        self.cursor_in_widget = False
        self.set_highlighted(False)

    def set_highlighted(self, h: bool) -> None:
        """Sets whether the background is highlighted."""
        if h:
            self.setStyleSheet("#menu_action_widget { background-color: " + self.background_highlight_colour + "; }")
        else:
            self.setStyleSheet("#menu_action_widget { background-color: transparent; }")

    def reset_highlight(self):
        self.cursor_in_widget = False
        self.set_highlighted(False)
