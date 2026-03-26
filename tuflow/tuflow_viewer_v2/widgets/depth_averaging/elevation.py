from qgis.PyQt.QtWidgets import QWidget

from .depth import DepthWidget, DepthWidgetAction


class ElevationWidget(DepthWidget):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.label1.setText('Start elevation:')
        self.label2.setText('End elevation:')


class ElevationWidgetAction(DepthWidgetAction):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.widget = ElevationWidget(parent)
        self.connect(self.widget)
        self.setDefaultWidget(self.widget)

    def to_string(self) -> str:
        """Returns the string representation of the widget action settings in a format that pytuflow can use."""
        if not self.currentText():
            return ''
        return f'{self.currentText()}:{self.uuid}:elevation&{self.valueStart()}&{self.valueEnd()}'
