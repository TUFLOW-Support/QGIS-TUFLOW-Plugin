import json

from qgis.core import QgsProcessingParameterDefinition, QgsCoordinateReferenceSystem
from qgis.gui import QgsGui, QgsPanelWidget, QgsProcessingAlgorithmDialogBase
from processing.gui.wrappers import WidgetWrapper, DIALOG_STANDARD, DIALOG_BATCH, DIALOG_MODELER

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QHBoxLayout, QLineEdit, QToolButton, QTextBrowser, QVBoxLayout, QLabel,
                             QSpacerItem, QSizePolicy, QFrame)

from tuflow.compatibility_routines import Path, QT_FRAME_HLINE, QT_FRAME_SUNKEN
from tuflow.gui.widgets.settings_table import SettingsTable


class SettingsTableParameter(QgsProcessingParameterDefinition):
    """Parameter definition for a table of settings."""

    def __init__(self, name, description, defaultValue=None, optional=False, table_params=None):
        super().__init__(name, description, defaultValue, optional)
        self.table_params = table_params
        self.setMetadata({'widget_wrapper': SettingsTableWidgetWrapper})

    def type(self):
        return self.typeName()

    @staticmethod
    def typeName():
        return 'SettingsTableParameter'

    def valueAsPythonString(self, value, context):
        return json.dumps(value)

    def tableParams(self):
        return self.table_params

    def checkValueIsAcceptable(self, input, context = ...):
        if input is None:
            return False
        if not isinstance(input, str):
            return False
        try:
            d = json.loads(input)
        except json.JSONDecodeError:
            return False
        crs_str = d.get('Projection')
        if not crs_str:
            return False
        if ' - ' not in crs_str:
            return False
        crs = QgsCoordinateReferenceSystem(crs_str.split(' - ')[0])
        return crs.isValid()


class SettingsTableWidgetWrapper(WidgetWrapper):

    def __init__(self, *args, **kwargs):
        self.widget = None
        super().__init__(*args, **kwargs)

    def createWidget(self):
        if not self.widget:
            self.widget = SettingsTableWidget(None, self.parameterDefinition(), self.parameterDefinition().defaultValue())
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


class SettingsTableWidget(QWidget):

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
        if self.tooltip_widget is None:
            self.tooltip_widget = self.findToolTipWidget()
        if self.tooltip_widget:
            self._old_tooltip = self.tooltip_widget.toHtml()
            p = Path(__file__).parents[2] / 'alg' / 'help' / 'html' / 'tuflow_settings_table.html'
            with p.open() as f:
                self.tooltip_widget.setHtml(f.read())

        panel = QgsPanelWidget.findParentPanel(self)
        if panel and panel.dockMode():
            self.panel_widget = SettingsTablePanel(panel, self.value, self.param_defn.tableParams())
            if self.param_defn is not None:
                self.panel_widget.setPanelTitle(self.param_defn.description())
            self.panel_widget.panelAccepted.connect(self.revertTooltip)
            self.panel_widget.valuesChanged.connect(self.updateValue)
            panel.openPanel(self.panel_widget)
        else:
            raise Exception('Settings Table Parameter type not supported in batch mode or non-dock mode')


class SettingsTablePanel(QgsPanelWidget):

    valuesChanged = pyqtSignal()

    def __init__(self, parent=None, value=None, table_params=None):
        super().__init__(parent)
        QgsGui.instance().enableAutoGeometryRestore(self)
        self.layout = QVBoxLayout()
        self.tables = []
        for i, (table_name, row_params) in enumerate(table_params.items()):
            if i > 0:
                line = self.line()
                self.layout.addWidget(line)
                self.layout.addSpacing(10)
            label = QLabel(f'<p style="font-size:10pt;"><b>{table_name}</b></p>')
            self.layout.addWidget(label)
            table = SettingsTable(self, row_params)
            table.itemChanged.connect(lambda: self.valuesChanged.emit())
            self.layout.addWidget(table)
            self.tables.append(table)
        self.layout.addStretch(1)
        self.setLayout(self.layout)
        self.value = value

    @property
    def value(self):
        d = {}
        for table in self.tables:
            for i in range(table.rowCount()):
                browser = QTextBrowser()
                browser.setHtml(table.item(i, 0).text())
                key = browser.toPlainText()
                val = table.item(i, 1).text()
                d[key] = val
        return json.dumps(d)

    @value.setter
    def value(self, value):
        if not value:
            return
        try:
            d = json.loads(value)
        except json.JSONDecodeError:
            return
        for table in self.tables:
            for i in range(table.rowCount()):
                browser = QTextBrowser()
                browser.setHtml(table.item(i, 0).text())
                key = browser.toPlainText()
                if key in d:
                    table.item(i, 1).setText(str(d[key]))

    def line(self):
        line = QFrame()
        line.setFrameShape(QT_FRAME_HLINE)
        line.setFrameShadow(QT_FRAME_SUNKEN)
        line.setLineWidth(2)
        return line
