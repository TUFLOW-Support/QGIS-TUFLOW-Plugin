from qgis.PyQt.QtWidgets import QWidget

from .depth import DepthWidget, DepthWidgetAction


class SigmaWidget(DepthWidget):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.label1.setText('Start fraction:')
        self.label2.setText('End fraction:')


class SigmaWidgetAction(DepthWidgetAction):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.widget = SigmaWidget(parent)
        self.connect(self.widget)
        self.setDefaultWidget(self.widget)

    def to_string(self) -> str:
        """Returns the string representation of the widget action settings in a format that pytuflow can use."""
        if not self.currentText():
            return ''
        return f'{self.currentText()}:{self.uuid}:sigma&{self.valueStart()}&{self.valueEnd()}'
