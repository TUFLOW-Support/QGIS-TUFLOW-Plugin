import json
from pathlib import Path

from qgis.PyQt import QtWidgets, QtCore
from qgis.core import QgsProcessingParameterDefinition, QgsProject
from processing.gui.wrappers import WidgetWrapper

from tuflow.tuflowqgis_settings import TF_Settings


class ProjectDirectoryParameter(QgsProcessingParameterDefinition):

    def __init__(self, name, description, defaultValue=None, optional=False):
        if defaultValue is None:
            defaultValue = ''
        super().__init__(name, description, defaultValue, optional)
        self.setMetadata({'widget_wrapper': ProjectDirectoryWidgetWrapper})

    def type(self):
        return self.typeName()

    @staticmethod
    def typeName():
        return 'EmptySelectorParameter'

    def valueAsPythonString(self, value, context):
        return json.dumps(value)


class ProjectDirectoryWidgetWrapper(WidgetWrapper):

    def __init__(self, *args, **kwargs):
        self.widget = None
        super().__init__(*args, **kwargs)

    def createWidget(self):
        if not self.widget:
            self.widget = ProjectDirectoryWidget(None, self.parameterDefinition(), self.parameterDefinition().defaultValue())
            self.widget.valueChanged.connect(lambda: self.widgetValueHasChanged.emit(self))
        return self.widget

    def widgetValue(self):
        return self.value()

    def setWidgetValue(self, value, context):
        self.setValue(value)

    def value(self):
        if self.widget:
            return self.widget.value
        return self.parameterDefinition().defaultValue()

    def setValue(self, value):
        if self.widget:
            self.widget.value = value
            self.widget.updateValue()


class ProjectDirectoryWidget(QtWidgets.QWidget):

    valueChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None, param_defn=None, value=None):
        super().__init__(parent)
        self.param_defn = param_defn
        self.value = value
        self.vlayout = QtWidgets.QVBoxLayout()
        self.vlayout.setContentsMargins(0, 0, 0, 0)

        self.browse_layout = QtWidgets.QHBoxLayout()
        self.browse_layout.setContentsMargins(0, 0, 0, 0)
        self.vlayout.addLayout(self.browse_layout)

        self.line_edit = QtWidgets.QLineEdit()
        self.browse_layout.addWidget(self.line_edit, 1)
        self.btn = QtWidgets.QToolButton()
        self.btn.setText(chr(0x2026))
        self.btn.clicked.connect(self.browse)
        self.browse_layout.addWidget(self.btn)

        self.save_layout = QtWidgets.QHBoxLayout()
        self.save_layout.setContentsMargins(0, 0, 0, 0)
        self.pb_save_to_project = QtWidgets.QPushButton('Save directory to project')
        self.pb_save_to_project.clicked.connect(self.save_to_project)
        self.save_layout.addWidget(self.pb_save_to_project)
        self.pb_save_global = QtWidgets.QPushButton('Save directory globally')
        self.pb_save_global.clicked.connect(self.save_global)
        self.save_layout.addWidget(self.pb_save_global)
        self.vlayout.addLayout(self.save_layout)

        self.setLayout(self.vlayout)
        self.updateValue()

    def setText(self, text):
        if text:
            text = str(Path(text))
        self.line_edit.setText(text)

    def updateValue(self):
        if self.value:
            self.setText(self.value)
        self.valueChanged.emit()

    def browse(self):
        text = self.line_edit.text()
        if not text or text == '.':
            last_dir = QtCore.QSettings().value('tuflow_plugin/import_empty/project_directory', QtCore.QDir.homePath())
        else:
            last_dir = text
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select project/empty directory', last_dir)
        if dir_path:
            self.value = dir_path
            self.updateValue()
            QtCore.QSettings().setValue('tuflow_plugin/import_empty/project_directory', dir_path)

    def save_to_project(self):
        if self.line_edit.text() and self.line_edit.text() != '.':
            QgsProject.instance().writeEntry('tuflow', 'project/folder', self.line_edit.text())

    def save_global(self):
        if self.line_edit.text() and self.line_edit.text() != '.':
            tf_settings = TF_Settings()
            tf_settings.Load()
            tf_settings.global_settings.base_dir = self.line_edit.text()
            tf_settings.Save()
