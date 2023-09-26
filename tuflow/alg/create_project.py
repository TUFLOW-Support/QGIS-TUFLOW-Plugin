import os
from pathlib import Path

from PyQt5.QtGui import QIcon

# processing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterCrs
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterString
from processing.gui.AlgorithmDialog import AlgorithmDialog

from ..utils import ProjectConfig, tuflow_plugin


class CreateTuflowCatchProject_CustomDialog(AlgorithmDialog):
    """
    Custom dialog. Updates parameters dynamically if a new project folder is selected and it contains an
    existing tcsettings.json file.
    """

    def __init__(self, *args):
        self.project_folder = ''
        super().__init__(*args)

    def changeEvent(self,  *args, **kwargs):
        super().changeEvent(*args, **kwargs)
        self.event_handler()

    def keyReleaseEvent(self, *args, **kwargs):
        super().keyReleaseEvent(*args, **kwargs)
        self.event_handler()

    def event_handler(self):
        if self.mainWidget() is None:
            return
        if not hasattr(self.mainWidget(), 'wrappers'):
            return
        if 'project_folder' not in self.mainWidget().wrappers or not self.mainWidget().wrappers['project_folder'].widgetValue():
            return
        folder = self.mainWidget().wrappers['project_folder'].widgetValue()
        if folder == self.project_folder:
            return
        self.project_folder = folder
        folder = Path(folder)
        settings = folder / 'tfsettings.json'
        if not settings.exists():
            return
        try:
            with settings.open() as f:
                project = ProjectConfig.from_json(f)
        except Exception:
            return
        if 'tuflow_executable' in self.mainWidget().wrappers:
            widget = self.mainWidget().wrappers['tuflow_executable'].wrappedWidget()
            widget.setFilePath(str(project.hpcexe))
        if 'tuflow_fv_executable' in self.mainWidget().wrappers:
            widget = self.mainWidget().wrappers['tuflow_fv_executable'].wrappedWidget()
            widget.setFilePath(str(project.fvexe))
        if 'project_crs' in self.mainWidget().wrappers:
            wrapper = self.mainWidget().wrappers['project_crs']
            wrapper.setParameterValue(project.crs, self.processingContext())
        if 'default_gis_format' in self.mainWidget().wrappers:
            cbo = self.mainWidget().wrappers['default_gis_format'].wrappedWidget()
            cbo.setCurrentIndex(project.gis_extension_to_enum(project.gis_format))


# QGIS_VERSION>=32800
class CreateTuflowProject(QgsProcessingAlgorithm):
    """Setup and create a TUFLOW Catch project with the option to create empty files and folder structure."""

    def initAlgorithm(self, config=None):
        """Adds inputs and outputs which define what is displayed in the dialog."""
        # Project Name input
        self.addParameter(
            QgsProcessingParameterString(
                'project_name',
                'Project Name',
                defaultValue=None
            )
        )
        # Project Folder input
        self.addParameter(
            QgsProcessingParameterFile(
                'project_folder',
                'Project Folder',
                behavior=QgsProcessingParameterFile.Folder,
                fileFilter='All files (*.*)',
                defaultValue=None
            )
        )
        # Project CRS input
        self.addParameter(
            QgsProcessingParameterCrs('project_crs', 'Project CRS', defaultValue=None)
        )
        # HPC Executable input
        self.addParameter(
            QgsProcessingParameterFile(
                'tuflow_executable',
                'TUFLOW Executable',
                behavior=QgsProcessingParameterFile.File,
                fileFilter='EXE (*.exe *.EXE)',
                defaultValue=None
            )
        )
        # GIS Format combobox
        self.addParameter(
            QgsProcessingParameterEnum(
                'default_gis_format',
                'Default GIS Format',
                options=['GPKG', 'SHP', 'MIF'],
                allowMultiple=False,
                usesStaticStrings=False,
                defaultValue=[0]
            )
        )
        # checkbox to create empty files
        self.addParameter(
            QgsProcessingParameterBoolean('create_empty_files', 'Create Empty Files', optional=True, defaultValue=False)
        )
        # checkbox to create folder structure
        self.addParameter(
            QgsProcessingParameterBoolean(
                'create_folder_structure',
                'Create Folder Structure',
                optional=True,
                defaultValue=False
            )
        )
        # checkbox to setup tuflow control file templates
        self.addParameter(
            QgsProcessingParameterBoolean(
                'setup_cf_templates',
                'Setup Control File Templates',
                optional=True,
                defaultValue=False
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)
        results = {}
        feedback.setCurrentStep(0)

        project = ProjectConfig(
            self.parameterAsString(parameters, 'project_name', context),
            self.parameterAsFile(parameters, 'project_folder', context),
            self.parameterAsCrs(parameters, 'project_crs', context),
            self.parameterAsInt(parameters, 'default_gis_format', context),
            self.parameterAsFile(parameters, 'tuflow_executable', context),
        )
        # save settings
        feedback.pushInfo('Saving settings...')
        project.save_settings()
        feedback.setCurrentStep(1)
        # folder structure
        if self.parameterAsBool(parameters, 'create_folder_structure', context):
            feedback.pushInfo('Creating folder structure...')
            project.create_folders()
        feedback.setCurrentStep(2)
        # empty files
        if self.parameterAsBool(parameters, 'create_empty_files', context):
            project.create_proj_gis_file(project.folder /  'model' / 'gis', False)
            feedback.pushInfo('Creating HPC empty files...')
            project.create_hpc_empties()
            feedback.setCurrentStep(3)
        feedback.setCurrentStep(4)
        # setup template control files
        if self.parameterAsBool(parameters, 'setup_cf_templates', context):
            feedback.pushInfo('Setting up control file templates...')
            project.setup_cf_templates()
        feedback.setCurrentStep(5)

        return results

    def createCustomParametersWidget(self, parent=None):
        """Custom parameters widget so events can dynamically update gui."""
        return CreateTuflowCatchProject_CustomDialog(self, False, parent)

    def shortHelpString(self) -> str:
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help' / 'html' / 'create_project.html'
        return help_filename.open().read()

    def name(self):
        return 'create_tuflow_project'

    def displayName(self):
        return 'Create TUFLOW Project (beta)'

    def icon(self) -> QIcon:
        if tuflow_plugin():
            return tuflow_plugin().icon('config_proj')
        return QIcon()

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return CreateTuflowProject()
