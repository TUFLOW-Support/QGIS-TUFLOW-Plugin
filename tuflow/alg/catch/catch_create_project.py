import os
import sys
from pathlib import Path

from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingParameterDefinition

# processing
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterCrs
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterString
from qgis.core import Qgis
if Qgis.QGIS_VERSION_INT >= 40200:
    from processing.gui.algorithm_widget import AlgorithmWidget as AlgorithmDialog
else:
    from processing.gui.AlgorithmDialog import AlgorithmDialog

from tuflow.utils.catch_project import ProjectConfig


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
        settings = folder / 'tcsettings.json'
        if not settings.exists():
            return
        try:
            with settings.open() as f:
                project = ProjectConfig.from_json(f)
        except Exception:
            return
        if 'tuflow_hpc_executable' in self.mainWidget().wrappers:
            widget = self.mainWidget().wrappers['tuflow_hpc_executable'].wrappedWidget()
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


class CreateTuflowCatchProject(QgsProcessingAlgorithm):
    """Setup and create a TUFLOW Catch project with the option to create empty files and folder structure."""

    def initAlgorithm(self, config=None):
        """Adds inputs and outputs which define what is displayed in the dialog."""
        project = ProjectConfig.from_qgs_project()

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
                defaultValue=str(project.folder) if project.valid else None
            )
        )
        # Project CRS input
        self.addParameter(
            QgsProcessingParameterCrs('project_crs', 'Project CRS', defaultValue=project.crs if project.valid else 'EPSG:28356')
        )
        # HPC Executable input
        self.addParameter(
            QgsProcessingParameterFile(
                'tuflow_hpc_executable',
                'TUFLOW HPC Executable',
                behavior=QgsProcessingParameterFile.File,
                fileFilter='EXE (*.exe *.EXE)',
                defaultValue=str(project.hpcexe) if project.valid else None
            )
        )
        # FV Executable input
        self.addParameter(
            QgsProcessingParameterFile(
                'tuflow_fv_executable',
                'TUFLOW FV Executable',
                behavior=QgsProcessingParameterFile.File,
                fileFilter='EXE (*.exe *.EXE)',
                defaultValue=str(project.fvexe) if project.valid else None
            )
        )
        # GIS Format combobox
        self.addParameter(
            QgsProcessingParameterEnum(
                'default_gis_format',
                'GIS Format for Catchment Hydraulic Model',
                options=['GPKG', 'SHP'],
                # options=['GPKG', 'SHP', 'MIF'],
                allowMultiple=False,
                usesStaticStrings=False,
                defaultValue=[1]
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
        # checkbox to setup TUFLOW control file templates
        self.addParameter(
            QgsProcessingParameterBoolean(
                'setup_cf_templates',
                'Setup Control File Templates',
                optional=True,
                defaultValue=False
            )
        )

        template_files = ["TUFLOW CATCH Control file (.tcc)",
                          "Batch file (.bat)",
                          "TUFLOW Geometry Control file (.tgc)",
                          "TUFLOW BC Control file (.tbc)",
                          "BC Database",
                          "Materials file",
                          "Rainfall Control file (.trfc)",
                          "ESTRY Control file (.ecf)",
                          "Soils file (.tsoilf)",
                          "Event file (.tef)",
                          "Water Quality Control file (.fvwq)",
                          "Sediment Control file (.fvsed)"]

        param = QgsProcessingParameterEnum(
                'cf_selection',
                'Control File Templates',
                options=template_files,
                defaultValue=list(range(len(template_files))),
                allowMultiple=True,
                usesStaticStrings=False
            )

        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

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
            self.parameterAsFile(parameters, 'tuflow_hpc_executable', context),
            self.parameterAsFile(parameters, 'tuflow_fv_executable', context)
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
            project.create_proj_gis_file(project.folder / 'TUFLOWCATCH' / 'model' / 'gis', True)
            feedback.pushInfo('Creating HPC empty files...')
            try:
                project.create_hpc_empties()
            except Exception as e:
                feedback.reportError(str(e))
            feedback.setCurrentStep(3)
            feedback.pushInfo('Creating FV empty files...')
            try:
                project.create_fv_empties()
            except Exception as e:
                feedback.reportError(str(e))
            feedback.pushInfo('Creating TUFLOW CATCH empty files...')
            try:
                project.create_catch_empties()
            except Exception as e:
                feedback.reportError(str(e))
        feedback.setCurrentStep(4)
        # setup template control files
        if self.parameterAsBool(parameters, 'setup_cf_templates', context):
            feedback.pushInfo('Setting up control file templates...')
            template_selection = self.parameterAsEnums(parameters, 'cf_selection', context)
            project.setup_cf_templates(template_selection)
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
        return 'create_tuflow_catch_project'

    def displayName(self):
        return 'Create TUFLOW CATCH Project'

    def icon(self) -> QIcon:
        return QIcon(str(Path(__file__).parents[2] / 'icons' / 'catch_create_project.svg'))

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return CreateTuflowCatchProject()
