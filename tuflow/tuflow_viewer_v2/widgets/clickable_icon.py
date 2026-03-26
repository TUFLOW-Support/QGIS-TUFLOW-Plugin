from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.QtGui import QPixmap, QPainter, QMouseEvent, QPaintEvent
from qgis.PyQt.QtCore import pyqtSignal, QSettings

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...compatibility_routines import QT_LEFT_BUTTON
else:
    from tuflow.compatibility_routines import QT_LEFT_BUTTON


class ClickableIcon(QWidget):

    clicked = pyqtSignal(bool)

    def __init__(self, active_pixmap: QPixmap = None, inactive_pixmap: QPixmap = None, parent=None):
        super().__init__(parent)
        self.active_pixmap = None
        self.inactive_pixmap = None
        if isinstance(active_pixmap, QPixmap):
            self.active_pixmap = active_pixmap
        if isinstance(inactive_pixmap, QPixmap):
            self.inactive_pixmap = inactive_pixmap
        self.active = False
        self.cursor_in_widget = False
        if self.active_pixmap:
            self.setFixedSize(self.active_pixmap.size())

    def setPixmaps(self, active_pixmap: QPixmap, inactive_pixmap: QPixmap):
        """Set the pixmaps for the active and inactive states."""
        self.active_pixmap = active_pixmap
        self.inactive_pixmap = inactive_pixmap
        self.setFixedSize(self.active_pixmap.size())

    def enterEvent(self, event: QMouseEvent):
        self.cursor_in_widget = True
        super().enterEvent(event)

    def leaveEvent(self, event: QMouseEvent):
        self.cursor_in_widget = False
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == QT_LEFT_BUTTON:
            self.active = not self.active
            self.clicked.emit(self.active)
            self.update()  # Redraw

    def paintEvent(self, event: QPaintEvent):
        if self.active_pixmap is None or self.inactive_pixmap is None:
            return
        painter = QPainter(self)
        if self.active:
            painter.drawPixmap(0, 0, self.active_pixmap)
        else:
            painter.drawPixmap(0, 0, self.inactive_pixmap)

    def setActive(self, active: bool):
        """Set the edit active state."""
        if self.active != active:
            self.active = active
            self.update()

    def isActive(self) -> bool:
        return self.active
