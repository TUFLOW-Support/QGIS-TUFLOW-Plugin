import json

from qgis.core import QgsProcessingParameterDefinition
from processing.gui.wrappers import WidgetWrapper, DIALOG_STANDARD, DIALOG_BATCH, DIALOG_MODELER

from tuflow.gui.widgets.output_format_widget import OutputFormatWidget


class OutputFormatParameter(QgsProcessingParameterDefinition):

    def __init__(self, name, description, defaultValue=None, optional=False):
        super().__init__(name, description, defaultValue, optional)
        self.setMetadata({'widget_wrapper': OutputFormatWidgetWrapper})

    def type(self):
        return self.typeName()

    @staticmethod
    def typeName():
        return 'OutputFormatParameter'

    def valueAsPythonString(self, value, context):
        return json.dumps(value)


class OutputFormatWidgetWrapper(WidgetWrapper):

    def __init__(self, *args, **kwargs):
        self.widget = None
        super().__init__(*args, **kwargs)

    def createWidget(self):
        if not self.widget:
            self.widget = OutputFormatWidget(None, self.parameterDefinition().defaultValue())
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
