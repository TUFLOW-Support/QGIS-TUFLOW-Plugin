from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QWidget, QCheckBox, QLabel, QDoubleSpinBox, QComboBox, QSpacerItem

from .action import DepthAverageWidget, DepthAverageWidgetAction

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ....compatibility_routines import QT_SIZE_POLICY_EXPANDING, QT_SIZE_POLICY_MAXIMUM
else:
    from tuflow.compatibility_routines import QT_SIZE_POLICY_EXPANDING, QT_SIZE_POLICY_MAXIMUM


class DepthWidget(DepthAverageWidget):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.cb = QCheckBox()
        self.cbo = QComboBox()
        self.label1 = QLabel('Start depth:')
        self.sb_start = QDoubleSpinBox()
        self.label2 = QLabel('End depth:')
        self.sb_end = QDoubleSpinBox()
        self.btn = self.create_remove_button()
        spacer = QSpacerItem(50, 0, QT_SIZE_POLICY_MAXIMUM, QT_SIZE_POLICY_EXPANDING)
        self.layout.addWidget(self.cb)
        self.layout.addWidget(self.cbo)
        self.layout.addWidget(self.label1)
        self.layout.addWidget(self.sb_start)
        self.layout.addWidget(self.label2)
        self.layout.addWidget(self.sb_end)
        self.layout.addSpacerItem(spacer)
        self.layout.addWidget(self.btn)
        self.cb.toggled.connect(self.toggled.emit)
        self.cbo.currentTextChanged.connect(self.currentTextChanged.emit)
        self.sb_start.valueChanged.connect(self.valueChanged.emit)
        self.sb_end.valueChanged.connect(self.valueChanged.emit)
        self.btn.clicked.connect(self.removeButtonClicked.emit)


class DepthWidgetAction(DepthAverageWidgetAction):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.widget = DepthWidget(parent)
        self.connect(self.widget)
        self.setDefaultWidget(self.widget)

    def to_string(self) -> str:
        """Returns the string representation of the widget action settings in a format that pytuflow can use."""
        if not self.currentText():
            return ''
        return f'{self.currentText()}:{self.uuid}:depth?dir=top&{self.valueStart()}&{self.valueEnd()}'

    def valueStart(self) -> float:
        return self.widget.sb_start.value()

    def valueEnd(self) -> float:
        return self.widget.sb_end.value()

    def setValue(self, value_start: float, value_end: int):
        self.setValueStart(value_start)
        self.setValueEnd(value_end)

    def setValueStart(self, value: float):
        self.widget.sb_start.setValue(value)

    def setValueEnd(self, value: float):
        self.widget.sb_end.setValue(value)

    def setMinimum(self, value: float):
        self.widget.sb_start.setMinimum(value)
        self.widget.sb_end.setMinimum(value)

    def setMaximum(self, value: float):
        self.widget.sb_start.setMaximum(value)
        self.widget.sb_end.setMaximum(value)

    def setDecimals(self, value: int):
        self.widget.sb_start.setDecimals(value)
        self.widget.sb_end.setDecimals(value)

    def setSingleStep(self, value: float):
        self.widget.sb_start.setSingleStep(value)
        self.widget.sb_end.setSingleStep(value)
