import json
from collections import OrderedDict

from PyQt5.QtCore import pyqtSignal, Qt
from qgis._gui import QgsProcessingAlgorithmDialogBase
from qgis.core import QgsApplication, QgsProcessingParameterDefinition
from qgis.gui import QgsPanelWidget, QgsGui
from processing.gui.wrappers import WidgetWrapper, DIALOG_STANDARD, DIALOG_BATCH, DIALOG_MODELER

from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QHBoxLayout, QToolButton, QCheckBox, QComboBox, QVBoxLayout, \
    QTableWidget, QTableWidgetItem, QTextBrowser

from ...compatibility_routines import Path


class ProcessingParameterConvTufModelDirSettings(QgsProcessingParameterDefinition):

    def __init__(self, name, description, default=None, optional=False):
        super().__init__(name, description, default, optional)
        self.setMetadata({'widget_wrapper': ConvTufModelDirSettingsWidgetWrapper})

    def type(self):
        return self.typeName()

    @staticmethod
    def typeName():
        return 'CustomTable'

    def valueAsPythonString(self, value, context):
        return json.dumps(value)


class ConvTufModelDirSettingsWidgetWrapper(WidgetWrapper):

    def __init__(self, *args, **kwargs):
        self.widget = None
        super().__init__(*args, **kwargs)

    def createWidget(self):
        if not self.widget:
            self.widget = ConvTufModelDirSettingsInputWidget(
                None, self.parameterDefinition(), self.parameterDefinition().defaultValue()
            )
            self.widget.valueChanged.connect(self.valueChanged)
        return self.widget

    def widgetValue(self):
        return self.value()

    def setWidgetValue(self, value, context):
        return self.setValue(value)

    def setValue(self, value):
        if self.widget:
            self.widget.value = value
        self.widgetValueHasChanged.emit(self)

    def value(self):
        if self.widget:
            return self.widget.value
        return self.parameterDefinition().defaultValue()

    def valueChanged(self):
        self.widgetValueHasChanged.emit(self)


class ConvTufModelDirSettingsInputWidget(QWidget):

    valueChanged = pyqtSignal()

    def __init__(self, parent = None, param = None, value = None):
        super().__init__(parent)
        self.param = param
        self.value = value
        hlayout = QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)

        self.line_edit = QLineEdit()
        self.line_edit.setEnabled(False)
        hlayout.addWidget(self.line_edit, 1)

        self.btn = QToolButton()
        self.btn.setText(chr(0x2026))
        self.btn.clicked.connect(self.showDialog)
        hlayout.addWidget(self.btn)

        self.setLayout(hlayout)
        self.panel_widget = None
        self.tooltip_widget = None
        self._old_tooltip = None
        self.updateValue()

    def findToolTipWidget(self):
        dlg = None
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
        self.setText(str(list(self.value.values())))
        self.valueChanged.emit()

    def revertTooltip(self):
        if self.tooltip_widget is not None and self._old_tooltip is not None:
            self.tooltip_widget.setHtml(self._old_tooltip)
        self._old_tooltip = None

    def dirSettingsTooltip(self):
        p = Path(__file__).parent.parent.parent / 'alg' / 'help' / 'html' / 'alg_convert_tuflow_model_gis_format_tuf_dir_settings.html'
        return p.open().read().replace('\n', '<p>')

    def showDialog(self):
        if self.tooltip_widget is None:
            self.tooltip_widget = self.findToolTipWidget()
        if self.tooltip_widget:
            self._old_tooltip = self.tooltip_widget.toHtml()
            self.tooltip_widget.setHtml(self.dirSettingsTooltip())

        panel = QgsPanelWidget.findParentPanel(self)
        if panel and panel.dockMode():
            self.panel_widget = ConvTufModelDirSettingsPanel(panel, self.value)
            if self.param is not None:
                self.panel_widget.setPanelTitle(self.param.description())
            self.panel_widget.panelAccepted.connect(self.revertTooltip)
            self.panel_widget.tableChanged.connect(self.updateValue)
            panel.openPanel(self.panel_widget)
        else:
            raise Exception('Table Parameter type not supported in batch mode or non-dock mode')


class ConvTufModelDirSettingsPanel(QgsPanelWidget):

    acceptClicked = pyqtSignal()
    tableChanged = pyqtSignal()

    def __init__(self, parent = None, value = None):
        super().__init__(parent=parent)
        QgsGui.instance().enableAutoGeometryRestore(self)
        vlayout = QVBoxLayout()

        # directory structure table
        self.pathTableLabel = QLabel('Folder Structure')
        vlayout.addWidget(self.pathTableLabel)
        hlayout = QHBoxLayout()
        self.addPathButton = QToolButton()
        self.addPathButton.setIcon(QgsApplication.getThemeIcon('/mActionAdd.svg'))
        self.addPathButton.setToolTip('Add Row to Table')
        self.addPathButton.clicked.connect(self.addPathRow)
        hlayout.addWidget(self.addPathButton)
        self.remPathButton = QToolButton()
        self.remPathButton.setIcon(QgsApplication.getThemeIcon('/mActionRemove.svg'))
        self.remPathButton.setToolTip('Remove Row from Table')
        self.remPathButton.clicked.connect(self.removePathRow)
        hlayout.addWidget(self.remPathButton)
        hlayout.addStretch(0)
        vlayout.addLayout(hlayout)
        self.pathTable = QTableWidget()
        self.pathTable.setColumnCount(2)
        self.pathTable.setRowCount(3)
        self.pathTable.setHorizontalHeaderLabels(['Key', 'Path'])
        self.pathTable.horizontalHeader().setStretchLastSection(True)
        self.pathTable.setItem(0, 0, QTableWidgetItem('Test'))
        vlayout.addWidget(self.pathTable, 1)

        # mappings table
        self.mappingTableLabel = QLabel('Extension Mappings')
        vlayout.addWidget(self.mappingTableLabel)
        hlayout = QHBoxLayout()
        self.addMappingButton = QToolButton()
        self.addMappingButton.setIcon(QgsApplication.getThemeIcon('/mActionAdd.svg'))
        self.addMappingButton.setToolTip('Add Row to Table')
        self.addMappingButton.clicked.connect(self.addMappingRow)
        hlayout.addWidget(self.addMappingButton)
        self.remMappingButton = QToolButton()
        self.remMappingButton.setIcon(QgsApplication.getThemeIcon('/mActionRemove.svg'))
        self.remMappingButton.setToolTip('Remove Row from Table')
        self.remMappingButton.clicked.connect(self.removeMappingRow)
        hlayout.addWidget(self.remMappingButton)
        hlayout.addStretch(0)
        vlayout.addLayout(hlayout)
        self.mappingTable = QTableWidget()
        self.mappingTable.setColumnCount(2)
        self.mappingTable.setRowCount(3)
        self.mappingTable.setHorizontalHeaderLabels(['Ext', 'Key'])
        self.mappingTable.horizontalHeader().setStretchLastSection(True)
        self.mappingTable.setItem(0, 0, QTableWidgetItem('Test'))
        vlayout.addWidget(self.mappingTable, 1)

        self.setLayout(vlayout)

        if value:
            self.value = value
        self.pathTable.itemChanged.connect(self.itemChanged)
        self.mappingTable.itemChanged.connect(self.itemChanged)

    def addPathRow(self):
        self.pathTable.setRowCount(self.pathTable.rowCount() + 1)
        item = QTableWidgetItem('')
        item.setCheckState(Qt.Unchecked)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        self.pathTable.setItem(self.pathTable.rowCount() - 1, 0, item)
        self.pathTable.setItem(self.pathTable.rowCount() - 1, 1, QTableWidgetItem(''))
        self.pathTable.scrollToBottom()
        self.pathTable.setCurrentItem(self.pathTable.item(self.pathTable.rowCount() - 1, 0))
        self.pathTable.editItem(self.pathTable.item(self.pathTable.rowCount() - 1, 0))
        self.tableChanged.emit()

    def removePathRow(self):
        if self.pathTable.selectedItems():
            ind = sorted(set([x.row() for x in self.pathTable.selectedItems()]), reverse=True)
            for i in ind:
                self.pathTable.removeRow(i)
        else:
            self.pathTable.removeRow(self.pathTable.rowCount() - 1)
        self.tableChanged.emit()

    def addMappingRow(self):
        self.mappingTable.setRowCount(self.mappingTable.rowCount() + 1)
        self.mappingTable.setItem(self.mappingTable.rowCount() - 1, 0, QTableWidgetItem(''))
        self.mappingTable.setItem(self.mappingTable.rowCount() - 1, 1, QTableWidgetItem(''))
        self.mappingTable.scrollToBottom()
        self.mappingTable.setCurrentItem(self.mappingTable.item(self.mappingTable.rowCount() - 1, 0))
        self.mappingTable.editItem(self.mappingTable.item(self.mappingTable.rowCount() - 1, 0))
        self.tableChanged.emit()

    def removeMappingRow(self):
        if self.mappingTable.selectedItems():
            ind = sorted(set([x.row() for x in self.mappingTable.selectedItems()]), reverse=True)
            for i in ind:
                self.mappingTable.removeRow(i)
        else:
            self.mappingTable.removeRow(self.mappingTable.rowCount() - 1)
        self.tableChanged.emit()

    def itemChanged(self, item):
        self.tableChanged.emit()

    @property
    def value(self) -> dict:
        d1 = OrderedDict({})
        lst = []
        for i in range(self.pathTable.rowCount()):
            try:
                if self.pathTable.item(i, 0).text().strip() != '':
                    d1[self.pathTable.item(i, 0).text()] = self.pathTable.item(i, 1).text()
                    if self.pathTable.item(i, 0).checkState() == Qt.Checked:
                        lst.append(self.pathTable.item(i, 1).text())
            except Exception as e:
                pass
        d2 = OrderedDict({})
        for i in range(self.mappingTable.rowCount()):
            try:
                if self.mappingTable.item(i, 0).text().strip() != '':
                    d2[self.mappingTable.item(i, 0).text()] = self.mappingTable.item(i, 1).text()
            except Exception as e:
                pass
        return {'folder_structure': d1, 'mappings': d2, 'always_create': lst}

    @value.setter
    def value(self, d: dict) -> None:
        self.pathTable.blockSignals(True)
        try:
            folder_structure = d.get('folder_structure', {})
            always_create = d.get('always_create', [])
            self.pathTable.setRowCount(len(folder_structure))
            for i, (k, v) in enumerate(folder_structure.items()):
                try:
                    item = QTableWidgetItem(k)
                    item.setCheckState(Qt.Unchecked)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    if v in always_create:
                        item.setCheckState(Qt.Checked)
                    self.pathTable.setItem(i, 0, item)
                    self.pathTable.setItem(i, 1, QTableWidgetItem(v))
                except Exception as e:
                    pass
            mappings = d.get('mappings', {})
            self.mappingTable.setRowCount(len(mappings))
            for i, (k, v) in enumerate(mappings.items()):
                try:
                    self.mappingTable.setItem(i, 0, QTableWidgetItem(k))
                    self.mappingTable.setItem(i, 1, QTableWidgetItem(v))
                except Exception as e:
                    pass
        except Exception as e:
            pass
        finally:
            self.pathTable.blockSignals(False)

