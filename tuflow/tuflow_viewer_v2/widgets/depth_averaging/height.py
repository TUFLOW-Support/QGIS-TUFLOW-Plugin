from qgis.PyQt.QtWidgets import QWidget

from .depth import DepthWidget, DepthWidgetAction


class HeightWidget(DepthWidget):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.label1.setText('Start height:')
        self.label2.setText('End height:')


class HeightWidgetAction(DepthWidgetAction):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.widget = HeightWidget(parent)
        self.connect(self.widget)
        self.setDefaultWidget(self.widget)

    def to_string(self) -> str:
        """Returns the string representation of the widget action settings in a format that pytuflow can use."""
        if not self.currentText():
            return ''
        return f'{self.currentText()}:{self.uuid}:height?dir=bottom&{self.valueStart()}&{self.valueEnd()}'
