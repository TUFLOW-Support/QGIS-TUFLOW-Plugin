from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QWidget, QCheckBox, QLabel, QSpinBox, QComboBox, QSpacerItem

from .action import DepthAverageWidget, DepthAverageWidgetAction

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ....compatibility_routines import QT_SIZE_POLICY_EXPANDING, QT_SIZE_POLICY_MAXIMUM
else:
    from tuflow.compatibility_routines import QT_SIZE_POLICY_EXPANDING, QT_SIZE_POLICY_MAXIMUM


class MultiLevelWidget(DepthAverageWidget):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.cb = QCheckBox()
        self.cbo = QComboBox()
        self.label1 = QLabel('Start layer:')
        self.sb_start = QSpinBox()
        self.label2 = QLabel('End layer:')
        self.sb_end = QSpinBox()
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


class MultiLevelWidgetAction(DepthAverageWidgetAction):

    def __init__(self, from_top: bool, parent: QWidget = None):
        super().__init__(parent)
        self.from_top = from_top
        self.widget = MultiLevelWidget(parent)
        self.connect(self.widget)
        self.setDefaultWidget(self.widget)

    def to_string(self) -> str:
        """Returns the string representation of the widget action settings in a format that pytuflow can use."""
        if not self.currentText():
            return ''
        direction = 'top' if self.from_top else 'bottom'
        return f'{self.currentText()}:{self.uuid}:multilevel?dir={direction}&{self.valueStart()}&{self.valueEnd()}'

    def valueStart(self) -> int:
        return self.widget.sb_start.value()

    def valueEnd(self) -> int:
        return self.widget.sb_end.value()

    def setValue(self, value_start: int, value_end: int):
        self.setValueStart(value_start)
        self.setValueEnd(value_end)

    def setValueStart(self, value: int):
        self.widget.sb_start.setValue(value)

    def setValueEnd(self, value: int):
        self.widget.sb_end.setValue(value)

    def setMinimum(self, value: int):
        self.widget.sb_start.setMinimum(value)
        self.widget.sb_end.setMinimum(value)

    def setMaximum(self, value: int):
        self.widget.sb_start.setMaximum(value)
        self.widget.sb_end.setMaximum(value)
