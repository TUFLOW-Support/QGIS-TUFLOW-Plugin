from qgis.PyQt.QtWidgets import QLabel
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtGui import QMouseEvent


class ClickableLabel(QLabel):
    """Subclasses QLabel to emit a signal when label is clicked."""

    clicked = pyqtSignal()

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        """Override mouseReleaseEvent to emit clicked signal."""
        self.clicked.emit()
