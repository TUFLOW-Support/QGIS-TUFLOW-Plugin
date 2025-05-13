import json
import math

from qgis.core import QgsProcessingParameterDefinition, NULL
from qgis.gui import QgsGui, QgsProcessingAlgorithmDialogBase, QgsPanelWidget
from qgis.utils import iface, pluginDirectory
from processing.gui.wrappers import WidgetWrapper, DIALOG_STANDARD, DIALOG_BATCH, DIALOG_MODELER

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QToolButton, QTextBrowser

from tuflow.gui.widgets.interactive_domain_widget import InteractiveDomainWidget
from tuflow.compatibility_routines import Path


class DomainSetupParameter(QgsProcessingParameterDefinition):
    """Parameter definition for an interactive domain setup."""

    def __init__(self, name, description, defaultValue=None, optional=False):
        if defaultValue is None:
            defaultValue = ''
        super().__init__(name, description, defaultValue, optional)
        self.setMetadata({'widget_wrapper': DomainSetupWidgetWrapper})

    def type(self):
        return self.typeName()

    @staticmethod
    def typeName():
        return 'DomainSetupParameter'

    def valueAsPythonString(self, value, context):
        return json.dumps(value)


class DomainSetupWidgetWrapper(WidgetWrapper):

    def __init__(self, *args, **kwargs):
        self.widget = None
        super().__init__(*args, **kwargs)

    def createWidget(self):
        if not self.widget:
            self.widget = DomainSetupWidget(None, self.parameterDefinition(), self.parameterDefinition().defaultValue())
            self.widget.valueChanged.connect(lambda: self.widgetValueHasChanged.emit(self))
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
            self.widget.updateValue()


class DomainSetupWidget(QWidget):

    valueChanged = pyqtSignal()

    def __init__(self, parent=None, param_defn=None, value=None):
        super().__init__(parent)
        self.param_defn = param_defn
        self.value = value
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.line_edit = QLineEdit()
        self.line_edit.setEnabled(False)
        self.layout.addWidget(self.line_edit, 1)

        self.btn = QToolButton()
        self.btn.setText(chr(0x2026))
        self.btn.clicked.connect(self.showDialog)
        self.layout.addWidget(self.btn)

        self.setLayout(self.layout)
        self.panel_widget = None
        self.tooltip_widget = None
        self._old_tooltip = None
        self.updateValue()

    def findToolTipWidget(self):
        wdg = self
        while wdg is not None and not isinstance(wdg, QgsProcessingAlgorithmDialogBase):
            wdg = wdg.parent()
        if wdg is None:
            return
        text_browsers = wdg.findChildren(QTextBrowser)
        if text_browsers:
            return text_browsers[0]

    def setText(self, text):
        self.line_edit.setText(text)

    def updateValue(self):
        if self.panel_widget:
            self.value = self.panel_widget.value
        if self.value:
            self.setText(self.value)
        self.valueChanged.emit()

    def revertTooltip(self):
        if self.tooltip_widget is not None and self._old_tooltip is not None:
            self.tooltip_widget.setHtml(self._old_tooltip)
        self._old_tooltip = None

    def showDialog(self):
        if not iface:
            raise Exception('Interactive domain setup cannot be used without an interface')

        if self.tooltip_widget is None:
            self.tooltip_widget = self.findToolTipWidget()
        if self.tooltip_widget:
            self._old_tooltip = self.tooltip_widget.toHtml()
            p = Path(__file__).parents[2] / 'alg' / 'help' / 'html' / 'domain_setup.html'
            with p.open() as f:
                self.tooltip_widget.setHtml(f.read().replace('${plugin_folder}', pluginDirectory('tuflow')))

        panel = QgsPanelWidget.findParentPanel(self)
        if panel and panel.dockMode():
            self.panel_widget = DomainSetupPanel(panel, self.value)
            if self.param_defn is not None:
                self.panel_widget.setPanelTitle(self.param_defn.description())
            self.panel_widget.panelAccepted.connect(self.revertTooltip)
            self.panel_widget.domainChanged.connect(self.updateValue)
            panel.openPanel(self.panel_widget)
        else:
            raise Exception('Domain Setup Parameter type not supported in batch mode or non-dock mode')


class DomainSetupPanel(QgsPanelWidget):

    domainChanged = pyqtSignal()

    def __init__(self, parent=None, value=None):
        super().__init__(parent)
        QgsGui.instance().enableAutoGeometryRestore(self)
        self.layout = QVBoxLayout()
        self.domain_widget = InteractiveDomainWidget(iface.mapCanvas())
        if value:
            self.domain_from_string(value)
        self.value = value
        self.layout.addWidget(self.domain_widget)
        self.setLayout(self.layout)
        self.domain_widget.domainChanged.connect(self.updateValue)

    def updateValue(self):
        self.value = self.domain_to_string()
        self.domainChanged.emit()

    def domain_to_string(self):
        return (f'{self.domain_widget.origin_x:.2f}:{self.domain_widget.origin_y:.2f}--'
                f'{math.degrees(self.domain_widget.angle)}--'
                f'{self.domain_widget.x_size:.2f}:{self.domain_widget.y_size:.2f}')

    def domain_from_string(self, domain_str):
        origin, angle, size = domain_str.split('--')
        origin_x, origin_y = origin.split(':')
        width, height = size.split(':')
        self.domain_widget.set_domain(float(origin_x), float(origin_y), float(width), float(height), math.radians(float(angle)))
        self.domain_widget.zoom_full_extent()
