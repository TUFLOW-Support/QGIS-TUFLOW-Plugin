from qgis.PyQt.QtWidgets import QWidgetAction, QRadioButton, QWidget, QHBoxLayout, QSpacerItem, QLabel
from qgis.PyQt.QtGui import QPalette, QIcon, QMouseEvent
from qgis.PyQt.QtCore import QEvent, pyqtSignal, QTimer, QSettings
from qgis.core import QgsApplication

from .clickable_label import ClickableLabel
from .menu_action_widget import MenuActionWidget
from ..tvinstance import get_viewer_instance

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...compatibility_routines import is_qt6, QT_SIZE_POLICY_MAXIMUM, QT_SIZE_POLICY_EXPANDING
else:
    from tuflow.compatibility_routines import is_qt6, QT_SIZE_POLICY_MAXIMUM, QT_SIZE_POLICY_EXPANDING


class RadioButtonWidget(MenuActionWidget):

    toggled = pyqtSignal(bool)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.rb = QRadioButton()
        self.rb.toggled.connect(self.toggled)
        self.label = ClickableLabel(text)
        self.label.clicked.connect(self.toggle)
        spacer = QSpacerItem(50, 0, QT_SIZE_POLICY_MAXIMUM, QT_SIZE_POLICY_EXPANDING)
        self.layout.addWidget(self.rb)
        self.layout.addWidget(self.label)
        self.layout.addItem(spacer)

    def toggle(self) -> None:
        """Override the toggle method to animate the click."""
        if is_qt6:
            self.rb.animateClick()
        else:
            self.rb.animateClick(100)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.rb.toggle)
        self.timer.start(300)

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        """Override mouseReleaseEvent to emit clicked signal."""
        self.toggle()

    def set_highlighted(self, h: bool) -> None:
        """Sets whether the background is highlighted."""
        if h:
            self.label.setStyleSheet(f"color: {get_viewer_instance().theme.palette.highlightedText().color().name()};")
        else:
            self.label.setStyleSheet(f"color: {get_viewer_instance().theme.palette.text().color().name()};")
        super().set_highlighted(h)


class RadioButtonAction(QWidgetAction):

    toggled = pyqtSignal(bool)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._widget = RadioButtonWidget(text)
        self._widget.rb.toggled.connect(self.toggled)
        self.setDefaultWidget(self._widget)

    def setIcon(self, icon: QIcon):
        self._widget.rb.setIcon(icon)

    def setChecked(self, checked: bool):
        self._widget.rb.setChecked(checked)

    def isChecked(self) -> bool:
        return self._widget.rb.isChecked()

    def button(self) -> QRadioButton:
        return self._widget.rb
