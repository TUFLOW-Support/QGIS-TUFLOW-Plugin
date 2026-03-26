import json
from collections import OrderedDict

from qgis.PyQt import QtWidgets, QtCore
from qgis.core import QgsProcessingParameterDefinition
from qgis.gui import QgsGui, QgsPanelWidget, QgsProcessingAlgorithmDialogBase
from processing.gui.wrappers import WidgetWrapper, DIALOG_STANDARD, DIALOG_BATCH, DIALOG_MODELER

from ...utils import empty_tooltip


class EmptySelectorParameter(QgsProcessingParameterDefinition):

    def __init__(self, name, description, options, defaultValue=None, optional=False):
        if defaultValue is None:
            defaultValue = ''
        super().__init__(name, description, defaultValue, optional)
        self._options = options
        self.setMetadata({'widget_wrapper': EmptySelectorWidgetWrapper})

    def type(self):
        return self.typeName()

    @staticmethod
    def typeName():
        return 'EmptySelectorParameter'

    def valueAsPythonString(self, value, context):
        return json.dumps(value)

    def options(self):
        return self._options

    def setOptions(self, options):
        self._options = options


class EmptySelectorWidgetWrapper(WidgetWrapper):

    def __init__(self, *args, **kwargs):
        self.widget = None
        super().__init__(*args, **kwargs)

    def createWidget(self):
        if not self.widget:
            self.widget = EmptySelectorWidget(None, self.parameterDefinition(), self.parameterDefinition().defaultValue())
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


class EmptySelectorWidget(QtWidgets.QWidget):

    valueChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None, param_defn=None, value=None):
        super().__init__(parent)
        self.param_defn = param_defn
        self.value = value
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.line_edit = QtWidgets.QLineEdit()
        self.line_edit.setEnabled(False)
        self.layout.addWidget(self.line_edit, 1)

        self.btn = QtWidgets.QToolButton()
        self.btn.setText(chr(0x2026))
        self.btn.clicked.connect(self.showDialog)
        self.layout.addWidget(self.btn)

        self.setLayout(self.layout)
        self.panel_widget = None
        self.tooltip_widget = None
        self._old_tooltip = None
        self.updateValue()

    def setText(self, text):
        self.line_edit.setText(text)

    def updateValue(self):
        if self.panel_widget:
            self.value = self.panel_widget.value
        if self.value:
            self.setText(self.value)
        self.valueChanged.emit()

    def showDialog(self):
        if self.tooltip_widget is None:
            self.tooltip_widget = self.findToolTipWidget()
        if self.tooltip_widget:
            self._old_tooltip = self.tooltip_widget.toHtml()

        panel = QgsPanelWidget.findParentPanel(self)
        if panel and panel.dockMode():
            self.panel_widget = EmptySelectorPanel(panel, self.value, self.param_defn.options(), self.tooltip_widget)
            if self.param_defn is not None:
                self.panel_widget.setPanelTitle(self.param_defn.description())
            self.panel_widget.panelAccepted.connect(self.revertTooltip)
            self.panel_widget.valuesChanged.connect(self.updateValue)
            panel.openPanel(self.panel_widget)
        else:
            raise Exception('Empty selection type not supported in batch mode or non-dock mode')

    def findToolTipWidget(self):
        wdg = self
        while wdg is not None and not isinstance(wdg, QgsProcessingAlgorithmDialogBase):
            wdg = wdg.parent()
        if wdg is None:
            return
        text_browsers = wdg.findChildren(QtWidgets.QTextBrowser)
        if text_browsers:
            return text_browsers[0]

    def revertTooltip(self):
        if self.tooltip_widget is not None and self._old_tooltip is not None:
            self.tooltip_widget.setHtml(self._old_tooltip)
        self._old_tooltip = None


class EmptySelectorPanel(QgsPanelWidget):

    valuesChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None, value=None, options=(), tooltip_widget=None):
        super().__init__(parent)
        QgsGui.instance().enableAutoGeometryRestore(self)
        self.tooltip_widget = tooltip_widget
        self.layout = QtWidgets.QVBoxLayout()
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Type', 'P', 'L', 'R'])
        header_item = self.table.horizontalHeaderItem(0)
        header_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        options = {v: {'P': False, 'L': False, 'R': False} for v in options}
        value = self.set_checked_options(options, value)
        self.value = value or {}
        self.table.itemChanged.connect(self.valuesChanged.emit)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)

    def update_tooltip_widget(self, items: list[str], text_browser: QtWidgets.QTextBrowser):
        html = ''
        for item in items:
            html = f'{html}{empty_tooltip(item)}'
        text_browser.setHtml(html)

    def selection_changed(self):
        items = [x.text() for x in self.table.selectedItems() if x.column() == 0]
        if self.tooltip_widget and items:
            self.update_tooltip_widget(items, self.tooltip_widget)

    @staticmethod
    def parse_empty_type_string(value: str):
        if not value:
            return {}
        d = {}
        s = value.split(';;')
        for item in s:
            empty_type, geom = [x.strip() for x in item.split(':', 1)]
            d_ = {'P': False, 'L': False, 'R': False}
            for g in geom.split(','):
                g = g.strip()
                if g in d_:
                    d_[g] = True
            d[empty_type] = d_
        return d

    @staticmethod
    def set_checked_options(options: dict, value: str):
        if not value:
            return options
        d = EmptySelectorPanel.parse_empty_type_string(value)
        for k, v in options.items():
            if k in d:
                options[k] = d[k]
        return options

    @property
    def value(self):
        s = []
        for i in range(self.table.rowCount()):
            empty_type = self.table.item(i, 0).text()
            d_ = {
                'P': self.table.item(i, 1).checkState() == QtCore.Qt.CheckState.Checked,
                'L': self.table.item(i, 2).checkState() == QtCore.Qt.CheckState.Checked,
                'R': self.table.item(i, 3).checkState() == QtCore.Qt.CheckState.Checked,
            }
            if any(d_.values()):
                geom = ','.join([k for k, v in d_.items() if v])
                s.append(f'{empty_type}: {geom}')
        return ';;'.join(s)

    @value.setter
    def value(self, value):
        self.table.blockSignals(True)
        d = {1: 'P', 2: 'L', 3: 'R'}
        if isinstance(value, str):
            try:
                value = json.loads(value, object_pairs_hook=OrderedDict)
            except json.JSONDecodeError:
                value = {}
        self.table.setRowCount(len(value))
        for row, (key, val) in enumerate(value.items()):
            type_item = QtWidgets.QTableWidgetItem(key)
            type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, type_item)

            for col in range(1, 4):
                checkbox_item = QtWidgets.QTableWidgetItem()
                checkbox_item.setFlags(
                    QtCore.Qt.ItemFlag.ItemIsUserCheckable |
                    QtCore.Qt.ItemFlag.ItemIsEnabled
                )
                if val.get(d[col], False):
                    checkbox_item.setCheckState(QtCore.Qt.CheckState.Checked)
                else:
                    checkbox_item.setCheckState(QtCore.Qt.CheckState.Unchecked)
                checkbox_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, checkbox_item)

            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()
        self.table.blockSignals(False)
