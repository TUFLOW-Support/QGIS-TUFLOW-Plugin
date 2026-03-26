from uuid import uuid4

from qgis.PyQt.QtWidgets import QWidgetAction, QToolButton, QLabel
from qgis.PyQt.QtCore import pyqtSignal

from ..menu_action_widget import MenuActionWidget
from ...tvinstance import get_viewer_instance


class DepthAverageWidget(MenuActionWidget):
    toggled = pyqtSignal(bool)
    currentTextChanged = pyqtSignal(str)
    valueChanged = pyqtSignal(int)
    removeButtonClicked = pyqtSignal()

    def set_highlighted(self, h: bool) -> None:
        """Sets whether the background is highlighted."""
        for label in self.findChildren(QLabel):
            if h:
                label.setStyleSheet("color: white;")
            else:
                label.setStyleSheet("color: black;")
        super().set_highlighted(h)

    @staticmethod
    def create_remove_button():
        btn = QToolButton()
        btn.setIcon(get_viewer_instance().icon('close-ring'))
        btn.setText('Remove')
        btn.setToolTip('Remove')
        btn.setAutoRaise(True)
        btn.setFixedSize(20, 20)  # square dimensions
        btn.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 10px;  /* half of width/height = perfect circle */
                background-color: transparent;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 50%);
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 70%);
            }
        """)
        return btn


class DepthAverageWidgetAction(QWidgetAction):
    """Base class so isinstance() can be used for all depth averageing widget actions."""
    toggled = pyqtSignal(bool)
    currentTextChanged = pyqtSignal(str)
    valueChanged = pyqtSignal(int)
    removeButtonClicked = pyqtSignal(QWidgetAction)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uuid = uuid4()

    # must override this method!
    def to_string(self) -> str:
        return ''

    def connect(self, widget: DepthAverageWidget):
        widget.toggled.connect(self.toggled.emit)
        widget.currentTextChanged.connect(self.currentTextChanged.emit)
        widget.valueChanged.connect(self.valueChanged.emit)
        widget.removeButtonClicked.connect(self.remove_btn_clicked)

    def remove_btn_clicked(self):
        """Slot to handle the remove button click."""
        self.removeButtonClicked.emit(self)

    def isChecked(self) -> bool:
        return self.widget.cb.isChecked()

    def setChecked(self, checked: bool) -> None:
        self.widget.cb.setChecked(checked)

    def currentText(self) -> str:
        return self.widget.cbo.currentText()

    def setCurrentText(self, text: str) -> None:
        self.widget.cbo.setCurrentText(text)

    def currentIndex(self) -> int:
        return self.widget.cbo.currentIndex()

    def setCurrentIndex(self, index: int) -> None:
        self.widget.cbo.setCurrentIndex(index)

    def items(self) -> list[str]:
        return [self.widget.cbo.itemText(i) for i in range(self.widget.cbo.count())]

    def addItems(self, items: list[str]):
        self.widget.cbo.addItems(items)

    def clear(self):
        self.widget.cbo.clear()
