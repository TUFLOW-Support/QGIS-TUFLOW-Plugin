import typing

import numpy as np

from qgis.core import (
    QgsProcessingParameterDefinition,
    QgsProcessingContext,
)
from qgis.gui import (
    QgsAbstractProcessingParameterWidgetWrapper,
    QgsProcessingParameterWidgetFactoryInterface,
    QgsGui,
)
from qgis.PyQt.QtWidgets import QPushButton, QWidget, QHBoxLayout, QVBoxLayout


class QgsProcessingParameterButtonGroup(QgsProcessingParameterDefinition):
    """A processing parameter made up of buttons."""
    TYPE = 'QgsProcessingParameterButtonGroup'

    def __init__(
            self, name: str, 
            description: str = '', 
            buttons: list[QPushButton] | list[list[QPushButton]] = (),
            defaultValue: typing.Any = None,
            optional: bool = False
            ):
        if defaultValue is None:
            defaultValue = []
        super().__init__(name, description, defaultValue, optional)
        self.buttons = buttons

    def clone(self) -> "QgsProcessingParameterButtonGroup":
        copy = QgsProcessingParameterButtonGroup(self.name(), self.description(), self.buttons)
        copy.setFlags(self.flags())
        return copy

    def type(self) -> str:
        return self.TYPE

    def valueAsPythonString(self, value, context: QgsProcessingContext) -> str:  # noqa: N802
        return repr(str(value))
    
    def asPythonString(self) -> str:  # noqa: N802
        return f"QgsProcessingParameterButtonGroup('{self.name()}', '{self.description()}')"

    @classmethod
    def registerWidget(cls) -> None:
        """Register the widget factory. Call once at plugin load time."""
        QgsGui.processingGuiRegistry().addParameterWidgetFactory(
            _ButtonGroupWidgetFactory()
        )


class _ButtonGroupWidgetWrapper(QgsAbstractProcessingParameterWidgetWrapper):

    def __init__(self, parameter, dialog_type, parent=None):
        super().__init__(parameter, dialog_type, parent)
        self.last_button_clicked = ''

    def createWidget(self) -> QWidget:  # noqa: N802
        buttons = [x for y in self.parameterDefinition().buttons for x in y]
        for btn in buttons:
            btn.clicked.connect(self.btn_clicked)
        self._widget = _ButtonGroupWidget(buttons=self.parameterDefinition().buttons)
        return self._widget

    def setWidgetValue(self, value, context: QgsProcessingContext) -> None:  # noqa: N802
        if value is not None:
            self._widget.setValue(value)

    def widgetValue(self) -> list[QPushButton]:  # noqa: N802
        return self._widget.value()

    def parameterLabelString(self) -> str:  # noqa: N802
        return self.parameterDefinition().description()

    def btn_clicked(self, checked: bool):
        sender = self._widget.sender()
        self.last_button_clicked = sender.text()
        self.widgetValueHasChanged.emit(None)


class _ButtonGroupWidgetFactory(QgsProcessingParameterWidgetFactoryInterface):

    def parameterType(self) -> str:  # noqa: N802
        return QgsProcessingParameterButtonGroup.TYPE

    def createWidgetWrapper(self, parameter, type_, parent=None):  # noqa: N802
        return _ButtonGroupWidgetWrapper(parameter, type_, parent)

    def compatibleParameterTypes(self) -> list[str]:  # noqa: N802
        return [QgsProcessingParameterButtonGroup.TYPE]

    def compatibleOutputTypes(self) -> list[str]:  # noqa: N802
        return []


class _ButtonGroupWidget(QWidget):

    def __init__(self, parent=None, buttons=()):
        super().__init__(parent)
        depth = 1
        if buttons and isinstance(buttons[0], list):
            depth = 2
        height = 35
        height = height if depth == 1 else height * len(buttons)
        self.layout = QVBoxLayout(self)
        for i in range(depth):
            if len(buttons) <= i or not buttons[i]:
                continue

            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)

            for btn in buttons[i]:
                btn.setParent(self)
                layout.addWidget(btn)
            layout.addStretch(1)

            self.layout.addLayout(layout)

            
        self.setLayout(self.layout)
        self.setFixedHeight(height)

    def value(self) -> list[QPushButton]:
        return [self.layout.itemAt(i).widget() for i in range(self.layout.count())]

    def setValue(self, value: list[QPushButton]):
        pass
