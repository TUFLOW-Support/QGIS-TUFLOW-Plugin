from qgis.PyQt.QtWidgets import (QWidget, QCheckBox, QComboBox, QSpacerItem, QSpinBox, QLabel,
                                 QToolButton)
from qgis.PyQt.QtCore import QSettings

from .action import DepthAverageWidgetAction
from .action import DepthAverageWidget

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ....compatibility_routines import QT_SIZE_POLICY_EXPANDING, QT_SIZE_POLICY_MAXIMUM
else:
    from tuflow.compatibility_routines import QT_SIZE_POLICY_EXPANDING, QT_SIZE_POLICY_MAXIMUM


class SingleLevelWidget(DepthAverageWidget):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.cb = QCheckBox()
        self.cbo = QComboBox()
        self.label = QLabel('Layer:')
        self.sb = QSpinBox()
        self.btn = self.create_remove_button()
        spacer = QSpacerItem(50, 0, QT_SIZE_POLICY_MAXIMUM, QT_SIZE_POLICY_EXPANDING)
        self.layout.addWidget(self.cb)
        self.layout.addWidget(self.cbo)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.sb)
        self.layout.addSpacerItem(spacer)
        self.layout.addWidget(self.btn)
        self.cb.toggled.connect(self.toggled.emit)
        self.cbo.currentTextChanged.connect(self.currentTextChanged.emit)
        self.sb.valueChanged.connect(self.valueChanged.emit)
        self.btn.clicked.connect(self.removeButtonClicked.emit)


class SingleLevelWidgetAction(DepthAverageWidgetAction):

    def __init__(self, from_top: bool, parent: QWidget = None):
        super().__init__(parent)
        self.from_top = from_top
        self.widget = SingleLevelWidget(parent)
        self.connect(self.widget)
        self.setDefaultWidget(self.widget)

    def to_string(self) -> str:
        """Returns the string representation of the widget action settings in a format that pytuflow can use."""
        if not self.currentText():
            return ''
        direction = 'top' if self.from_top else 'bottom'
        return f'{self.currentText()}:{self.uuid}:singlelevel?dir={direction}&{self.value()}'

    def value(self) -> int:
        return self.widget.sb.value()

    def setValue(self, value: int):
        self.widget.sb.setValue(value)

    def setMinimum(self, value: int):
        self.widget.sb.setMinimum(value)

    def setMaximum(self, value: int):
        self.widget.sb.setMaximum(value)
