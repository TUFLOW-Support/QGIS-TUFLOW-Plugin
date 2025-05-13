import os

from qgis.core import QgsProcessingParameterFile, Qgis, QgsProcessing, QgsSettings
from qgis.gui import QgsProcessingGui
from processing.gui.wrappers import FileWidgetWrapper, FileSelectionPanel

from qgis.PyQt.QtWidgets import QFileDialog


if Qgis.QGIS_VERSION_INT >= 33600:
    FILE_BEHAVIOUR = Qgis.ProcessingFileParameterBehavior.File
else:
    FILE_BEHAVIOUR = QgsProcessingParameterFile.File

DIALOG_STANDARD = QgsProcessingGui.WidgetType.Standard
DIALOG_BATCH = QgsProcessingGui.WidgetType.Batch
DIALOG_MODELER = QgsProcessingGui.WidgetType.Modeler


class CustomFileSelectParameter(QgsProcessingParameterFile):
    """Custom parameter class for file selection that allows for a settings key to be passed in that will
    be used in place of "/Processing/LastInputPath".

    Parts of this will be removed in QGIS 4.0 and will require some attention or perhaps a completely different
    approach.
    """

    def __init__(self, name, description='', defaultValue=None, behavior=FILE_BEHAVIOUR, extension='',
                 optional=False, fileFilter = "", dirSettingsKey=None):
        super().__init__(name, description, behavior, extension, defaultValue, optional, fileFilter)
        self.dir_settings_key = dirSettingsKey
        self.setMetadata({'widget_wrapper': CustomFileWidgetWrapper})

    def typeName(self):
        return 'CustomFileSelectParameter'


class CustomFileWidgetWrapper(FileWidgetWrapper):

    def __init__(self, *args, **kwargs):
        import warnings
        with warnings.catch_warnings():  # base class is being removed in QGIS 4.0
            warnings.simplefilter("ignore")
            super().__init__(*args, **kwargs)

    def createWidget(self):
        if self.dialogType in (DIALOG_STANDARD, DIALOG_BATCH):
            return CustomFileSelectionPanel(
                self.parameterDefinition().behavior() == QgsProcessingParameterFile.Behavior.Folder,
                self.parameterDefinition().extension(),
                self.parameterDefinition().dir_settings_key
            )
        else:
            return super().createWidget()

    def selectFile(self):
        settings = QgsSettings()
        if os.path.isdir(os.path.dirname(self.combo.currentText())):
            path = os.path.dirname(self.combo.currentText())
        if settings.contains(self.parameterDefinition().dir_settings_key):
            path = settings.value(self.parameterDefinition().dir_settings_key)
        else:
            path = ''

        if self.parameterDefinition().extension():
            filter = self.tr('{} files').format(
                self.parameterDefinition().extension().upper()) + ' (*.' + self.parameterDefinition().extension() + self.tr(
                ');;All files (*.*)')
        else:
            filter = self.tr('All files (*.*)')

        filename, selected_filter = QFileDialog.getOpenFileName(self.widget,
                                                                self.tr('Select File'), path,
                                                                filter)
        if filename:
            self.combo.setEditText(filename)
            settings.setValue(self.parameterDefinition().dir_settings_key, filename)


class CustomFileSelectionPanel(FileSelectionPanel):

    def __init__(self, isFolder, ext=None, key=None):
        super().__init__(isFolder, ext)
        self.key = key

    def showSelectionDialog(self):
        # Find the file dialog's working directory
        settings = QgsSettings()
        text = self.leText.text()
        if os.path.isdir(text):
            path = text
        elif os.path.isdir(os.path.dirname(text)):
            path = os.path.dirname(text)
        elif settings.contains(self.key):
            path = settings.value(self.key)
        else:
            path = ''

        if self.isFolder:
            folder = QFileDialog.getExistingDirectory(self,
                                                      self.tr('Select Folder'), path)
            if folder:
                self.leText.setText(folder)
                settings.setValue(self.key, folder)
        else:
            filenames, selected_filter = QFileDialog.getOpenFileNames(self,
                                                                      self.tr('Select File'), path,
                                                                      self.tr('{} files').format(
                                                                          self.ext.upper()) + ' (*.' + self.ext + self.tr(
                                                                          ');;All files (*.*)'))
            if filenames:
                self.leText.setText(';'.join(filenames))
                settings.setValue(self.key, filenames[0])
