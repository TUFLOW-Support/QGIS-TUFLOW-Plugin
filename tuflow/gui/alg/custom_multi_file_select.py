import os

from qgis.core import QgsProcessingParameterMultipleLayers, QgsProcessing, QgsSettings
from qgis.gui import QgsPanelWidget
from processing.gui.wrappers import MultipleLayerWidgetWrapper, DIALOG_STANDARD
from processing.gui.MultipleInputPanel import MultipleInputPanel
from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QToolButton, QFileDialog, QPushButton
from qgis.PyQt.QtCore import QSettings, QDir, Qt

from qgis.gui import QgsProcessingMultipleInputPanelWidget


class CustomMultiFileSelectParameter(QgsProcessingParameterMultipleLayers):
    """Custom parameter class for multiple file selection that allows for a settings key to be passed in that will
    be used in place of "/Processing/LastInputPath".

    Only available for file types (QgsProcessing.TypeFile).
    """

    def __init__(self, name, description='', default=None, optional=False, dirSettingsKey=None):
        super().__init__(name, description, QgsProcessing.TypeFile, default, optional)
        self.dir_settings_key = dirSettingsKey
        self.setMetadata({'widget_wrapper': CustomMultiFileWidgetWrapper})

    def type(self):
        return 'CustomMultiFileSelectParameter'

    def typeName(self):
        return 'CustomMultiFileSelectParameter'


class CustomMultiFileWidgetWrapper(MultipleLayerWidgetWrapper):

    def __init__(self, param, dialog, row=0, col=0, **kwargs):
        super().__init__(param, dialog, row, col, **kwargs)

    def createWidget(self):
        if self.dialogType == DIALOG_STANDARD:
            if self.parameterDefinition().layerType() == QgsProcessing.SourceType.TypeFile:
                return CustomMultiFilePanel(self.param, self.dialog, datatype=QgsProcessing.SourceType.TypeFile)
        super().createWidget()

    def value(self):
        if self.widget is None:
            return []
        return self.widget.widgetValue()

    def setValue(self, value, context=None):
        if value is None:
            value = []
        if not isinstance(value, list):
            value = [value]
        if self.widget is not None:
            self.widget.setWidgetValue(value)


class CustomMultiFilePanel(MultipleInputPanel):

    def __init__(self, param, dialog, options=None, datatype=None, parent=None, value=()):
        super().__init__(options, datatype)
        self.param = param
        self.dialog = dialog
        self.model = None
        self.value = []

    def showSelectionDialog(self):
        panel = QgsPanelWidget.findParentPanel(self)
        if panel and panel.dockMode():
            self.panel_widget = CustomMultiFinalPanelWidget(self.param, self.value, [], self.model, self)
            if self.param is not None:
                self.panel_widget.setPanelTitle(self.param.description())
            self.panel_widget.selectionChanged.connect(lambda: self.setWidgetValue(self.panel_widget.selectedOptions()))
            panel.openPanel(self.panel_widget)
        else:
            super().showSelectionDialog()

    def widgetValue(self):
        return self.selectedoptions

    def setWidgetValue(self, value):
        self.value = value
        self.setSelectedItems(value)


class CustomMultiFinalPanelWidget(QgsProcessingMultipleInputPanelWidget):

    def __init__(self, parameter, selectedOptions, modelSources, model, parent):
        super().__init__(parameter, selectedOptions, modelSources, model, parent)
        self.param = parameter
        add_files_btn = [x for x in self.findChildren(QPushButton) if x.text() == 'Add File(s)…'][0]
        add_files_btn.disconnect()
        add_files_btn.clicked.connect(self.addFiles)

    def addFiles(self):
        settings = QgsSettings()
        key = self.param.dir_settings_key if self.param.dir_settings_key else '/Processing/LastInputPath'
        path = str(settings.value(key, QDir.homePath()))

        ret, selected_filter = QFileDialog.getOpenFileNames(self, self.tr('Select File(s)'),
                                                            path, 'All files (*.*)')
        if ret:
            files = list(ret)
            settings.setValue(key, os.path.dirname(str(files[0])))
            for filename in files:
                self.addOption(filename, filename, True)
            self.selectionChanged.emit()
