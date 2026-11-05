"""A replacement for :class:`QTabWidget` where the 'tab bar' will wrap onto mutltiple
rows, rather then scrolling horizontally when there isn't enough width to see all in one row.

:class:`QTabBar` has no native support for wrapping tabs onto multiple rows. This will work around
 that issue by building a row of checkable, mutually exclusive toolbutton tabs that are arranged with
 `FlowLayout` (qt native functionality) that wraps and sits over a stacked widget that holds the tab
 pages.

This was built for the ARR2026 tool.
"""

from typing import Optional

from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtWidgets import QButtonGroup, QStackedWidget, QToolButton, QVBoxLayout, QWidget

from .flow_layout import FlowLayout

# Thickness (px) of the line running under the tab row
_UNDERLINE_WIDTH = 2

_BUTTON_ROW_STYLESHEET = f"""
QWidget#wrapping_tab_button_row {{
    background: palette(window);
    border-bottom: {_UNDERLINE_WIDTH}px solid palette(mid);
}}
QToolButton {{
    background-color: palette(button);
    border: 1px solid palette(mid);
    border-bottom: {_UNDERLINE_WIDTH}px solid palette(mid);
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 4px 10px;
    color: palette(text);
}}
QToolButton:checked {{
    background-color: white;
    border-bottom: {_UNDERLINE_WIDTH}px solid white;
    font-weight: bold;
}}
QToolButton:hover:!checked {{
    background-color: palette(light);
}}
"""

_STACK_STYLESHEET = """
QStackedWidget#wrapping_tab_stack {
    background-color: white;
    border: 1px solid palette(mid);
    border-top: none;
}
"""


class WrappingTabWidget(QWidget):
    """See module docstring."""

    currentChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._buttons = []

        self._button_row = QWidget(self)
        self._button_row.setObjectName("wrapping_tab_button_row")
        self._button_row.setStyleSheet(_BUTTON_ROW_STYLESHEET)
        # Tabs touch each other
        self._button_flow_layout = FlowLayout(self._button_row, margin=0, h_spacing=0, v_spacing=0)
        self._button_row.setLayout(self._button_flow_layout)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._button_group.idClicked.connect(self._on_button_clicked)

        self._stack = QStackedWidget(self)
        self._stack.setObjectName("wrapping_tab_stack")
        self._stack.setStyleSheet(_STACK_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._button_row)
        layout.addWidget(self._stack)

    # ------------------------------------------------------------------
    # QTabWidget-like API
    # ------------------------------------------------------------------

    def addTab(self, widget: QWidget, icon_or_label, label: Optional[str] = None) -> int:
        """Mirrors :meth:`QTabWidget.addTab`'s two overloads: ``addTab(widget, label)``
        and ``addTab(widget, icon, label)``."""

        if label is None:
            icon = None
            text = icon_or_label
        else:
            icon = icon_or_label
            text = label

        index = self._stack.addWidget(widget)

        button = QToolButton(self._button_row)
        button.setCheckable(True)
        button.setAutoRaise(True)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        if icon is not None and not icon.isNull():
            button.setIcon(icon)
        button.setText(text)
        self._button_flow_layout.addWidget(button)
        self._button_group.addButton(button, index)
        self._buttons.append(button)

        if index == 0:
            button.setChecked(True)

        return index

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)
            self._on_button_clicked(index)

    def currentIndex(self) -> int:
        return self._stack.currentIndex()

    def count(self) -> int:
        return self._stack.count()

    def widget(self, index: int):
        return self._stack.widget(index)

    def indexOf(self, widget: QWidget) -> int:
        return self._stack.indexOf(widget)

    def setTabText(self, index: int, text: str) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setText(text)

    def setTabIcon(self, index: int, icon) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setIcon(icon)

    def setTabToolTip(self, index: int, tip: str) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setToolTip(tip)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_button_clicked(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self.currentChanged.emit(index)




