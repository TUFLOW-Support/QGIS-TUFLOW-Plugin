import json

from qgis.PyQt import QtWidgets
from qgis.core import QgsProcessingParameterDefinition, NULL

from processing.gui.wrappers import WidgetWrapper, DIALOG_STANDARD, DIALOG_BATCH, DIALOG_MODELER

from tuflow.tfversion_manager import tuflow_binaries, TuflowVersionDialog
from tuflow.compatibility_routines import QT_DIALOG_ACCEPTED


class TuflowVersionParameter(QgsProcessingParameterDefinition):

    def __init__(self, name, description, defaultValue=None, optional=False):
        if defaultValue is None:
            values = sorted(tuflow_binaries.version2bin.keys(), reverse=True)
            defaultValue = values[0] if values else ''
        super().__init__(name, description, defaultValue, optional)
        self.setMetadata({'widget_wrapper': TuflowVersionWidgetWrapper})

    def type(self):
        return self.typeName()

    @staticmethod
    def typeName():
        return 'TuflowVersionParameter'

    def valueAsPythonString(self, value, context):
        return json.dumps(value)


class TuflowVersionWidgetWrapper(WidgetWrapper):

    def __init__(self, *args, **kwargs):
        self.widget = None
        super().__init__(*args, **kwargs)

    def createWidget(self):
        if not self.widget:
            self.widget = TuflowVersionWidget(None, self.parameterDefinition(), self.parameterDefinition().defaultValue())
        return self.widget

    def widgetValue(self):
        return self.value()

    def setWidgetValue(self, value, context):
        self.setValue(value)

    def value(self):
        if self.widget:
            return self.widget.value
        return self.parameterDefinition().defaultValue() if self.parameterDefinition() is not None else ''

    def setValue(self, value):
        if self.widget and value is not NULL:
            self.widget.value = value


class TuflowVersionWidget(QtWidgets.QWidget):

    def __init__(self, parent=None, param_defn=None, value=None):
        super().__init__(parent)
        self.param_defn = param_defn
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.combo_box = QtWidgets.QComboBox()
        self.layout.addWidget(self.combo_box, 1)

        self.btn = QtWidgets.QPushButton('Manage versions')
        self.btn.clicked.connect(self.open_version_manager)
        self.layout.addWidget(self.btn)

        self.setLayout(self.layout)

        self.refresh_versions()

        self.value = value

    @property
    def value(self):
        return self.combo_box.currentText()

    @value.setter
    def value(self, val):
        if val:
            idx = self.combo_box.findText(val)
            if idx > -1:
                self.combo_box.setCurrentIndex(idx)
                return
        self.combo_box.setCurrentIndex(-1)

    def refresh_versions(self):
        self.combo_box.clear()
        versions = sorted(tuflow_binaries.version2bin.keys(), reverse=True)
        self.combo_box.addItems(versions)

    def open_version_manager(self):
        TuflowVersionDialog(self).exec()
        self.refresh_versions()
