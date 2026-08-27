from pathlib import Path

from qgis._core import QgsProcessingParameterFile
from qgis.core import QgsSettings, Qgis
from processing.gui.wrappers import WidgetWrapper

from qgis.PyQt.QtCore import QDir, pyqtSignal
from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QToolButton, QFileDialog

if Qgis.QGIS_VERSION_INT >= 33600:
    FileBehaviour = Qgis.ProcessingFileParameterBehavior
else:
    FileBehaviour = QgsProcessingParameterFile


class CustomOutputFileDestination(QgsProcessingParameterFile):

    def __init__(self, name, description='', behavior=FileBehaviour.File,
                 defaultValue=None, optional=False, fileFilter=''):
        super().__init__(name, description, behavior, '', defaultValue, optional, fileFilter)
        self.setMetadata({'widget_wrapper': CustomFileDestinationWidgetWrapper})

    def type(self):
        return 'CustomOutputFileDestination'

    def typeName(self):
        return 'CustomOutputFileDestination'


class CustomFileDestinationWidgetWrapper(WidgetWrapper):

    def __init__(self, param=None, dialog=None, row=0, col=0, **kwargs):
        self.widget = None
        super().__init__(param, dialog, row, col, **kwargs)

    def createWidget(self, **kwargs):
        self.widget = CustomFileDestinationWidget(param=self.param)
        return self.widget

    def setValue(self, value):
        if self.widget:
            self.widget.value = value

    def value(self):
        if self.widget:
            return self.widget.value
        return ''


class CustomFileDestinationWidget(QWidget):

    value_changed = pyqtSignal()

    def __init__(self, parent=None, param=None):
        super().__init__(parent)
        self.param = param
        self.line_edit = QLineEdit()
        self.btn = QToolButton()
        self.btn.setText(chr(0x2026))
        self.btn.clicked.connect(self.showFileDialog)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.btn)
        self.setLayout(layout)

    @property
    def value(self):
        return self.line_edit.text()

    @value.setter
    def value(self, value):
        self.line_edit.setText(value)
        self.value_changed.emit()

    def showFileDialog(self):
        settings = QgsSettings()
        path = settings.value('/Processing/LastOutputPath', QDir.homePath())
        fpath = QFileDialog.getSaveFileName(self, 'Select output file', path, 'All files (*.*)')
        if fpath[0]:
            p = Path(fpath[0])
            if Path(p.stem).suffix.lower() != '.tuflow':
                p = p.with_suffix('.tuflow.json')
            settings.setValue('/Processing/LastOutputPath', str(p))
            self.value = str(p)
