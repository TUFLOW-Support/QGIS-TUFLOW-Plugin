import os
import typing
from pathlib import Path

from qgis.PyQt.QtCore import QEvent, QTimer, QDir, QCoreApplication, QSettings
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QListView, QLabel, QTextBrowser, QToolButton, QLineEdit, QFileDialog

from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterDefinition
from qgis.core import QgsProcessingParameterFileDestination
from qgis.core import QgsProcessingParameterFolderDestination
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProject
import processing
from processing.gui.AlgorithmDialog import AlgorithmDialog

from ..utils import tuflow_plugin, ProjectConfig, empty_types_from_project_folder, empty_tooltip, EmptyCreator



from ..compatibility_routines import QT_EVENT_MOUSE_BUTTON_RELEASE, QT_FILE_DIALOG_DONT_CONFIRM_OVERWRITE


class ImportEmpty_CustomDialog(AlgorithmDialog):
    """
    Custom dialog. Updates tooltip if empty type is selected. Updates available
    empty types if the project folder is changed.
    """

    def __init__(self, *args):
        self.timer = None
        self.timer_conn = None
        self.list_view = None
        self.text_browser = None
        self.original_text = ''
        super().__init__(*args)
        self.override_output_btn()
        self._project_folder = self.project_folder
        self.empty_type_btn = self.mainWidget().wrappers['empty_type'].wrappedWidget().findChild(QToolButton)
        self.empty_type_btn.installEventFilter(self)
        self.mainWidget().wrappers['gpkg_options'].wrappedWidget().currentIndexChanged.connect(self.gpkg_option_changed)

    def eventFilter(self, obj, event):
        if event.type() == QT_EVENT_MOUSE_BUTTON_RELEASE:
            self.timer = QTimer()
            self.timer.setSingleShot(True)
            self.timer_conn = self.timer.timeout.connect(lambda: self.event_handler(entering_empty_types_view=True))
            self.timer.start(200)
        return False

    def override_output_btn(self):
        self.gpkg_input = self.mainWidget().wrappers['export_to_gpkg_all_to_one']
        self.btn = self.gpkg_input.wrappedWidget().findChild(QToolButton)
        self.le = self.gpkg_input.wrappedWidget().findChild(QLineEdit)
        self.le.setPlaceholderText('[GPKG Database]')
        self.btn.setMenu(None)
        self.btn.clicked.connect(self.browse)

        self.kart_repo_input = self.mainWidget().wrappers['kart_repo']
        self.kart_btn = self.kart_repo_input.wrappedWidget().findChild(QToolButton)
        self.kart_le = self.kart_repo_input.wrappedWidget().findChild(QLineEdit)
        self.kart_le.setPlaceholderText('[Kart Repository]')
        self.kart_btn.setMenu(None)
        self.kart_btn.clicked.connect(self.browse_folder)

    def browse(self):
        param = self.gpkg_input.parameterDefinition()
        if self.le.text():
            start_dir = self.le.text()
        elif self.project_folder:
            start_dir = self.project_folder
        else:
            start_dir = QDir.homePath()
        file = QFileDialog.getSaveFileName(self, param.description(), start_dir, param.fileFilter(),
                                           options=QT_FILE_DIALOG_DONT_CONFIRM_OVERWRITE)
        file = file[0]
        if not file:
            return
        self.le.setText(file)
        self.gpkg_input.setParameterValue(file, self.processingContext())

    def browse_folder(self):
        param = self.kart_repo_input.parameterDefinition()
        if self.kart_le.text():
            start_dir = self.kart_le.text()
        elif QgsProject.instance().readEntry('tuflow', 'import_empty/import_gpkg_kart_repo', None)[0]:
            start_dir = QgsProject.instance().readEntry('tuflow', 'import_empty/import_gpkg_kart_repo', None)[0]
        elif self.project_folder:
            start_dir = self.project_folder
        else:
            start_dir = QDir.homePath()
        folder = QFileDialog.getExistingDirectory(self, param.description(), start_dir)
        if not folder:
            return
        folder = str(folder)
        self.kart_le.setText(folder)
        self.kart_repo_input.setParameterValue(folder, self.processingContext())

    def changeEvent(self,  *args, **kwargs):
        super().changeEvent(*args, **kwargs)
        self.event_handler()

    def keyReleaseEvent(self, *args, **kwargs):
        super().keyReleaseEvent(*args, **kwargs)
        self.event_handler()

    def actionEvent(self, *args, **kwargs):
        super().actionEvent(*args, **kwargs)
        self.event_handler()

    def event_handler(self, newSelection = (), oldSelection = (), entering_empty_types_view: bool = False):
        if self.timer_conn and self.timer:
            self.timer.timeout.disconnect(self.timer_conn)
            self.timer = None
            self.timer_conn = None
        if not self.is_valid():
            return
        tooltip_widget = self.get_tooltip_widget()
        empty_types_widget = self.get_empty_types_widget()
        in_empty_types_view = empty_types_widget is not None
        if in_empty_types_view:
            if entering_empty_types_view:
                self.original_text = tooltip_widget.toHtml()
            self.update_tooltip_widget(tooltip_widget, empty_types_widget)
        elif self.project_folder != self._project_folder:
            self.empty_types = empty_types_from_project_folder(self.project_folder)
            self._project_folder = self.project_folder

        self.mainWidget().wrappers['export_to_gpkg_all_to_one'].wrappedWidget().setEnabled(self.gpkg_export_option == 'All to one')
        self.mainWidget().wrappers['kart_repo'].wrappedWidget().setEnabled(self.gpkg_export_option == 'Kart Repo')

    def gpkg_option_changed(self, index: int):
        self.mainWidget().wrappers['export_to_gpkg_all_to_one'].wrappedWidget().setEnabled(self.gpkg_export_option == 'All to one')
        self.mainWidget().wrappers['kart_repo'].wrappedWidget().setEnabled(self.gpkg_export_option == 'Kart Repo')

    def update_tooltip_widget(self, text_browser: QTextBrowser, list_view: QListView):
        model = list_view.model()
        idxs = list_view.selectionModel().selectedIndexes()
        if not idxs:
            return
        html = ''
        for idx in idxs:
            html = f'{html}{empty_tooltip(model.data(idx))}'
        text_browser.setHtml(html)

    def is_valid(self) -> bool:
        return self.mainWidget() is not None and hasattr(self.mainWidget(), 'wrappers')

    @property
    def project_folder(self) -> str:
        return self.mainWidget().wrappers['project_directory'].wrappedWidget().filePath()

    @project_folder.setter
    def project_folder(self, value: str):
        self.mainWidget().wrappers['project_directory'].wrappedWidget().setFilePath(value)

    @property
    def empty_types(self) -> list[str]:
        return self.mainWidget().wrappers['empty_type'].parameterDefinition().options()

    @empty_types.setter
    def empty_types(self, value: list[str]):
        self.mainWidget().wrappers['empty_type'].parameterDefinition().setOptions(value)

    @property
    def gpkg_export_option(self) -> str:
        param = self.mainWidget().wrappers['gpkg_options'].parameterDefinition()
        idx = self.mainWidget().wrappers['gpkg_options'].wrappedWidget().currentIndex()
        return param.options()[idx]

    @gpkg_export_option.setter
    def gpkg_export_option(self, value: str):
        param = self.mainWidget().wrappers['gpkg_options'].parameterDefinition()
        if value in param.options():
            idx = param.options().index(value)
            self.mainWidget().wrappers['gpkg_options'].wrappedWidget().setCurrentIndex(idx)

    def get_tooltip_widget(self) -> QTextBrowser:
        if self.text_browser:
            return self.text_browser
        text_browsers = self.findChildren(QTextBrowser)
        if text_browsers:
            self.text_browser = text_browsers[0]
            return self.text_browser

    def get_empty_types_widget(self) -> QListView:
        if self.list_view:
            return self.list_view
        list_views = self.findChildren(QListView)
        if len(list_views) == 2:
            labels = [x for x in self.findChildren(QLabel) if x.isVisible()]
            if labels and labels[0].text() == ' Empty Type ':
                self.list_view = list_views[1]
                self.list_view.selectionModel().selectionChanged.connect(self.event_handler)
                self.list_view.destroyed.connect(self.list_view_destroyed)
                return self.list_view

    def list_view_destroyed(self, obj):
        self.list_view = None
        text_browser = self.get_tooltip_widget()
        text_browser.setHtml(self.original_text)


# QGIS_VERSION>=32800
class ImportEmpty(QgsProcessingAlgorithm):

    def initAlgorithm(self, config: typing.Dict[str, typing.Any] = ...) -> None:
        project = ProjectConfig.from_qgs_project()

        # empty directory
        self.addParameter(
            QgsProcessingParameterFile(
                'project_directory', 'Project Directory / Empty Directory',
                behavior=QgsProcessingParameterFile.Folder,
                fileFilter='All files (*.*)',
                defaultValue=str(project.folder) if str(project.folder) else None
            )
        )
        options = []
        if str(project.folder):
            options = empty_types_from_project_folder(project.folder)
        # empty type selection
        self.addParameter(
            QgsProcessingParameterEnum(
                'empty_type',
                'Empty Type',
                options=options,
                allowMultiple=True,
                usesStaticStrings=False,
                defaultValue=[]
            )
        )
        # geometry type
        self.addParameter(
            QgsProcessingParameterEnum(
                'geometry_type',
                'Geometry Type',
                options=['Point', 'Line', 'Region'],
                allowMultiple=True,
                usesStaticStrings=False,
                defaultValue=[]
            )
        )
        # run id
        self.addParameter(QgsProcessingParameterString('run_id', 'Run ID', multiLine=False, defaultValue=''))
        # overwrite file if existing
        self.addParameter(
            QgsProcessingParameterBoolean(
                'overwrite',
                'Overwrite Output if Exist',
                optional=False,
                defaultValue=False
            )
        )
        # gpkg export options
        prev_export_option = QgsProject.instance().readNumEntry('tuflow', 'import_empty/import_gpkg_option', 0)[0]
        param = QgsProcessingParameterEnum('gpkg_options',
                                           'GPKG Options',
                                           optional=False,
                                           options=['Separate', 'Group Geometry Types', 'All to one', 'Kart Repo'],
                                           allowMultiple=False,
                                           usesStaticStrings=False,
                                           defaultValue=prev_export_option)
        self.addParameter(param)

        # gpkg to export to if 'all to one' is selected
        prev_gpkg_db = QgsProject.instance().readEntry('tuflow', 'import_empty/import_gpkg_db', None)[0]
        param = QgsProcessingParameterFileDestination('export_to_gpkg_all_to_one',
                                                      'Export to GPKG (All to One)',
                                                      optional=True,
                                                      fileFilter='GPKG (*.gpkg *.GPKG)',
                                                      defaultValue=prev_gpkg_db)
        self.addParameter(param)

        prev_kart = QgsProject.instance().readEntry('tuflow', 'import_empty/import_gpkg_kart_repo', None)[0]
        param = QgsProcessingParameterFolderDestination('kart_repo',
                                                      'Kart Repository',
                                                      optional=True,
                                                      defaultValue=prev_kart)
        self.addParameter(param)

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        project = ProjectConfig.from_qgs_project()
        results = {'OUTPUT': []}  # init results

        # get parameters
        project_folder = self.parameterAsString(parameters, 'project_directory', context)
        empty_types = parameters['empty_type']  # doesn't work with 'parameterAsEnums' because the list is dynamic i think
        geometry_types = self.parameterAsEnums(parameters, 'geometry_type', context)
        run_id = self.parameterAsString(parameters, 'run_id', context)
        overwrite = self.parameterAsBool(parameters, 'overwrite', context)
        gpkg_export_option = self.parameterAsEnum(parameters, 'gpkg_options', context)
        gpkg_folder = self.parameterAsString(parameters, 'export_to_gpkg_all_to_one', context)
        kart_repo = self.parameterAsString(parameters, 'kart_repo', context)

        # save settings
        QgsProject.instance().writeEntry('tuflow', 'import_empty/import_gpkg_option', gpkg_export_option)
        QgsProject.instance().writeEntry('tuflow', 'import_empty/import_gpkg_db', gpkg_folder)
        QgsProject.instance().writeEntry('tuflow', 'import_empty/import_gpkg_kart_repo', kart_repo)

        project_folder_path = Path(project_folder)
        if project_folder_path != project.folder and project_folder_path.exists():
            project.folder = project_folder_path
            project.write_qgs_project(param='folder')

        # convert paramters to something meaningful
        empty_options = empty_types_from_project_folder(project_folder)
        empty_types = [empty_options[x] for x in empty_types]

        geometry_options = ['Point', 'Line', 'Region']
        geometry_types = [geometry_options[x] for x in geometry_types]

        gpkg_export_options = ['Separate', 'Group Geometry Types', 'All to one', 'Kart Repo']
        gpkg_export_option = gpkg_export_options[gpkg_export_option]

        total_steps = len(empty_types) * len(geometry_types)
        feedback = QgsProcessingMultiStepFeedback(total_steps, model_feedback)

        creator = EmptyCreator(project_folder, gpkg_export_option, gpkg_folder, kart_repo, overwrite, feedback)
        for empty_type in empty_types:
            for geometry_type in geometry_types:
                feedback.pushInfo(f'Creating {empty_type} {geometry_type} empty...')
                uri, name = creator.create_empty(empty_type, geometry_type, run_id)
                if not uri:
                    feedback.pushWarning('Empty file already exists. Skipping...')
                    continue
                # results['OUTPUT'].append(name)
                # open output file
                alg_params = {
                    'INPUT': uri,
                    'NAME': name
                }
                processing.run('native:loadlayer', alg_params, context=context, feedback=feedback,
                               is_child_algorithm=True)
                feedback.setProgress(feedback.progress() + 1)

        return results

    def createCustomParametersWidget(self, parent=None):
        """Custom parameters widget so events can dynamically update gui."""
        return ImportEmpty_CustomDialog(self, False, parent)

    def name(self):
        return 'import_empty'

    def displayName(self):
        return 'Import Empty'

    def icon(self) -> QIcon:
        if tuflow_plugin():
            return tuflow_plugin().icon('import_empty')
        return QIcon()

    def shortHelpString(self) -> str:
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help' / 'html' / 'import_empty.html'
        return self.tr(help_filename.open().read().replace('\n', '<p>'))

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return ImportEmpty()

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
