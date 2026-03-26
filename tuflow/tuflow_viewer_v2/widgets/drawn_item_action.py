from qgis.PyQt.QtWidgets import QWidget, QLabel, QToolButton, QHBoxLayout, QCheckBox, QSpacerItem, QWidgetAction
from qgis.PyQt.QtCore import pyqtSignal, QTimer, QEvent, QSettings
from qgis.PyQt.QtGui import QMouseEvent, QPixmap, QIcon

from qgis.core import QgsApplication
from qgis.gui import QgsMapCanvasItem, QgsVertexMarker

from .menu_action_widget import MenuActionWidget
from .clickable_label import ClickableLabel
from .clickable_icon import ClickableIcon
from ..tvinstance import get_viewer_instance

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...compatibility_routines import is_qt6, QT_RICH_TEXT, QT_ICON_DISABLED, QT_SIZE_POLICY_MAXIMUM, QT_SIZE_POLICY_EXPANDING
else:
    from tuflow.compatibility_routines import is_qt6, QT_RICH_TEXT, QT_ICON_DISABLED, QT_SIZE_POLICY_MAXIMUM, QT_SIZE_POLICY_EXPANDING


class MarkerLabelWidget(MenuActionWidget):

    toggled = pyqtSignal(bool)
    removeButtonClicked = pyqtSignal()
    cursorEntered = pyqtSignal()
    cursorLeft = pyqtSignal()
    editClicked = pyqtSignal(bool)

    def __init__(self, label: str, colour, parent: QWidget = None):
        super().__init__(parent)
        self.background_highlight_colour = '#fffdca'
        self._text = label
        self._font_size = 11
        self._colour = colour
        self.cb = QCheckBox()
        self.cb.toggled.connect(self.toggled.emit)
        self.cb.setVisible(False)
        self.layout.addWidget(self.cb)
        self.label = ClickableLabel()
        self.label.clicked.connect(self.toggle)
        self.label.setTextFormat(QT_RICH_TEXT)
        self.label.setText(self.create_html_text(label, self._font_size, colour))
        self.layout.addWidget(self.label)
        self.edit_pix = QgsApplication.getThemeIcon('/mActionToggleEditing.svg').pixmap(16, 16)
        self.edit_pix0 = QIcon(self.edit_pix).pixmap(self.edit_pix.width(),self.edit_pix.height(), QT_ICON_DISABLED)
        self.edit_icon = ClickableIcon(self.edit_pix, self.edit_pix0)
        self.edit_icon.setToolTip('Active edit')
        self.edit_icon.clicked.connect(self.editClicked.emit)
        self.layout.addWidget(self.edit_icon)
        spacer = QSpacerItem(50, 0, QT_SIZE_POLICY_MAXIMUM, QT_SIZE_POLICY_EXPANDING)
        self.layout.addSpacerItem(spacer)
        self.btn_remove = QToolButton()
        self.btn_remove.clicked.connect(self.removeButtonClicked.emit)
        self.btn_remove.setIcon(get_viewer_instance().icon('close-ring'))
        self.btn_remove.setText('Remove')
        self.btn_remove.setToolTip('Remove')
        self.btn_remove.setAutoRaise(True)
        self.btn_remove.setFixedSize(20, 20)  # square dimensions
        self.btn_remove.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 10px;  /* half of width/height = perfect circle */
                background-color: transparent;
            }
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 20%);
            }
            QToolButton:pressed {
                background-color: rgba(0, 0, 0, 35%);
            }
        """)
        self.layout.addWidget(self.btn_remove)

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, text: str):
        self._text = text
        self.label.setText(self.create_html_text(text, self._font_size, self._colour))

    @property
    def font_size(self) -> int:
        return self._font_size

    @font_size.setter
    def font_size(self, font_size: int):
        self._font_size = font_size
        self.label.setText(self.create_html_text(self._text, font_size, self._colour))

    @property
    def colour(self) -> str:
        return self._colour

    @colour.setter
    def colour(self, colour: str):
        self._colour = colour
        self.label.setText(self.create_html_text(self._text, self._font_size, colour))

    def enterEvent(self, a0: QEvent) -> None:
        super().enterEvent(a0)
        self.cursorEntered.emit()

    def leaveEvent(self, a0: QEvent) -> None:
        super().leaveEvent(a0)
        self.cursorLeft.emit()

    def create_html_text(self, text: str, font_size: int, colour: str) -> str:
        return f'<span style="font-size: {font_size}px; color: {colour};">{text}</span>'

    def toggle(self) -> None:
        """Override the toggle method to animate the click."""
        if is_qt6:
            self.cb.animateClick()
        else:
            self.cb.animateClick(100)

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        """Override mouseReleaseEvent to emit clicked signal."""
        if self.edit_icon.cursor_in_widget:
            return
        self.cb.setDown(False)
        self.toggle()

    def mousePressEvent(self, ev: QMouseEvent):
        if self.edit_icon.cursor_in_widget:
            return
        self.cb.setDown(True)


class DrawnItemAction(QWidgetAction):
    """A QWidgetAction that contains a label and a checkbox."""

    toggled = pyqtSignal(bool)
    removeButtonClicked = pyqtSignal(QWidgetAction)
    cursorEntered = pyqtSignal(QgsMapCanvasItem)
    cursorLeft = pyqtSignal()
    editClicked = pyqtSignal(QWidgetAction, bool)

    def __init__(self, text: str, map_item: QgsMapCanvasItem, parent=None):
        super().__init__(parent)
        self.map_item = map_item
        c = map_item.color() if isinstance(map_item, QgsVertexMarker) else map_item.fillColor()
        if QgsApplication.instance().themeName() == 'Blend of Gray':
            c = c.lighter(150)
        self._widget = MarkerLabelWidget(text, c.name(), parent)
        self._widget.toggled.connect(self.toggled.emit)
        self._widget.removeButtonClicked.connect(self.onRemoveButtonClicked)
        self._widget.cursorEntered.connect(self.onCursorEntered)
        self._widget.cursorLeft.connect(self.cursorLeft.emit)
        self._widget.editClicked.connect(self.onEditClicked)
        self.setDefaultWidget(self._widget)

    def text(self) -> str:
        return self._widget.text

    def setText(self, text: str):
        self._widget.text = text

    def setCheckable(self, checkable: bool):
        self._widget.cb.setVisible(checkable)

    def setChecked(self, checked: bool):
        self._widget.cb.setChecked(checked)

    def isChecked(self) -> bool:
        return self._widget.cb.isChecked()

    def onRemoveButtonClicked(self):
        self.removeButtonClicked.emit(self)

    def onCursorEntered(self):
        self.cursorEntered.emit(self.map_item)

    def onEditClicked(self, checked: bool):
        self.editClicked.emit(self, checked)

    def isEditActive(self) -> bool:
        return self._widget.edit_icon.isActive()

    def setEditActive(self, active: bool):
        self._widget.edit_icon.setActive(active)
