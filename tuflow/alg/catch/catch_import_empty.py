import io
import os
import sys
import typing
from pathlib import Path

from qgis.PyQt.QtCore import QCoreApplication, QDir
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QToolButton, QLineEdit, QFileDialog

from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterDefinition
from qgis.core import QgsProcessingParameterFileDestination
from qgis.core import QgsProcessingParameterBoolean
import processing
from qgis.core import Qgis
if Qgis.QGIS_VERSION_INT >= 40200:
    from processing.gui.algorithm_widget import AlgorithmWidget as AlgorithmDialog
else:
    from processing.gui.AlgorithmDialog import AlgorithmDialog

from tuflow.utils import unique_empty_names, EmptyCreator
from tuflow.utils.catch_project import ProjectConfig
from tuflow.gui.alg.empty_selector_parameter import EmptySelectorParameter, EmptySelectorPanel
from tuflow.compatibility_routines import QT_FILE_DIALOG_DONT_CONFIRM_OVERWRITE

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def empty_types_from_project_folder(folder: typing.Union[str, Path]) -> list[str]:
    """
    Return available empty types from a CATCH Modelling folder.

    Checks both ``TUFLOW/model/gis/empty`` and ``TUFLOWFV/model/gis/empty``
    under *folder*.  Types that exist in both solvers are labelled with a
    ``(HPC)`` / ``(FV)`` suffix to distinguish between them.
    """
    if isinstance(folder, str):
        folder = Path(folder)
    hpc_dir = folder / 'TUFLOW' / 'model' / 'gis' / 'empty'
    fv_dir = folder / 'TUFLOWFV' / 'model' / 'gis' / 'empty'
    hpc_empties = unique_empty_names(hpc_dir) if hpc_dir.exists() else []
    fv_empties = unique_empty_names(fv_dir) if fv_dir.exists() else []
    for empty in fv_empties:
        if empty in hpc_empties:
            ind = hpc_empties.index(empty)
            hpc_empties[ind] = empty + ' (HPC)'
            hpc_empties.append(empty + ' (FV)')
        else:
            hpc_empties.append(empty)
    return hpc_empties

def _strip_solver_suffix(empty_type: str) -> str:
    """
    Remove the ``' (HPC)'`` / ``' (FV)'`` suffix from an empty type name.
    """
    ind = empty_type.find(' ')
    return empty_type[:ind] if ind != -1 else empty_type

# ---------------------------------------------------------------------------
# Empty file creator
# ---------------------------------------------------------------------------

class CatchEmptyCreator(EmptyCreator):
    """
    EmptyCreator subclass for CATCH projects.

    Overrides only the directory setup and solver-string resolution so that
    templates are read from ``TUFLOW/model/gis/empty`` (HPC) and
    ``TUFLOWFV/model/gis/empty`` (FV) beneath *project_folder*, and output
    is written to ``TUFLOW/model/gis`` or ``TUFLOWFV/model/gis``.

    All file writing logic (GIS type detection, driver selection,
    action on existing, ``create_empty``) is inherited unchanged from
    :class:`~tuflow.utils.tf_empty.EmptyCreator`.
    """

    def __init__(self, project_folder: str, gpkg_export_type: str, gpkg_folder: str,
                 overwrite: bool, feedback=None):
        # kart repo is not used for CATCH projects
        super().__init__(project_folder, gpkg_export_type, gpkg_folder, '', overwrite, feedback)

    def _setup_dirs(self) -> None:
        """
        Configure the separate TUFLOW (HPC) and TUFLOWFV directories.
        """
        # TUFLOW HPC
        self.hpc_empty_dir = self.proj_folder / 'TUFLOW' / 'model' / 'gis' / 'empty'
        self.hpc_gis_dir = self.hpc_empty_dir.parent
        self.hpc_gis_type = self.gis_type(self.hpc_empty_dir, 'gpkg')
        self.hpc_empty_types = unique_empty_names(self.hpc_empty_dir) if self.hpc_empty_dir.exists() else []

        # TUFLOW FV
        self.fv_empty_dir = self.proj_folder / 'TUFLOWFV' / 'model' / 'gis' / 'empty'
        self.fv_gis_dir = self.fv_empty_dir.parent
        self.fv_gis_type = self.gis_type(self.fv_empty_dir, 'shp')
        self.fv_empty_types = unique_empty_names(self.fv_empty_dir) if self.fv_empty_dir.exists() else []

    def solver(self, empty_type: str) -> str:
        """
        Return ``'hpc'`` or ``'fv'``, using the ``(HPC)``/``(FV)`` suffix
        when present, otherwise falling back to the type-list lookup.
        Final fallback/default is hpc
        """
        if ' (HPC)' in empty_type:
            return 'hpc'
        if ' (FV)' in empty_type:
            return 'fv'
        clean = _strip_solver_suffix(empty_type)
        if clean in self.hpc_empty_types:
            return 'hpc'
        if clean in self.fv_empty_types:
            return 'fv'
        return 'hpc'  # default

    def _strip_solver_info(self, empty_type: str) -> str:
        """
        Remove ``' (HPC)'`` / ``' (FV)'`` suffix before file I/O.
        """
        return _strip_solver_suffix(empty_type)

# ---------------------------------------------------------------------------
# Custom processing dialog
# ---------------------------------------------------------------------------

class CatchImportEmpty_CustomDialog(AlgorithmDialog):
    """
    Custom dialog for :class:`CatchImportEmpty`.

    * Refreshes the :class:`EmptySelectorParameter` options whenever the
      project folder changes.
    * Enables / disables the GPKG database field depending on the chosen
      GPKG export option.

    Tooltip support is provided automatically by :class:`EmptySelectorPanel`
    (the panel that opens when the user clicks the *Empty Type* ``…`` button).
    """

    def __init__(self, *args):
        super().__init__(*args)
        self._project_folder = self.project_folder
        self._override_gpkg_btn()
        self.mainWidget().wrappers['gpkg_options'].wrappedWidget().currentIndexChanged.connect(
            self._on_gpkg_option_changed)
        self._on_gpkg_option_changed()
        # sys.stderr = io.StringIO()
        # import pydevd_pycharm
        # pydevd_pycharm.settrace('localhost', port=50000, stdout_to_server=True, stderr_to_server=True)


    # ------------------------------------------------------------------
    # GPKG button override
    # ------------------------------------------------------------------

    def _override_gpkg_btn(self):
        self._gpkg_input = self.mainWidget().wrappers['export_to_gpkg_all_to_one']
        btn = self._gpkg_input.wrappedWidget().findChild(QToolButton)
        le = self._gpkg_input.wrappedWidget().findChild(QLineEdit)
        le.setPlaceholderText('[GPKG Database]')
        btn.setMenu(None)
        btn.clicked.connect(self._browse_gpkg)

    def _browse_gpkg(self):
        param = self._gpkg_input.parameterDefinition()
        le = self._gpkg_input.wrappedWidget().findChild(QLineEdit)
        start = le.text() or self.project_folder or QDir.homePath()
        path, _ = QFileDialog.getSaveFileName(
            self, param.description(), start, param.fileFilter(),
            options=QT_FILE_DIALOG_DONT_CONFIRM_OVERWRITE)
        if path:
            le.setText(path)
            self._gpkg_input.setParameterValue(path, self.processingContext())

    def _on_gpkg_option_changed(self, index: int = -1):
        self.mainWidget().wrappers['export_to_gpkg_all_to_one'].wrappedWidget().setEnabled(
            self.gpkg_export_option == 'All to one')

    # ------------------------------------------------------------------
    # Qt event hooks – used to detect project folder changes
    # ------------------------------------------------------------------

    def changeEvent(self, *args, **kwargs):
        super().changeEvent(*args, **kwargs)
        self._refresh_empty_types()

    def keyReleaseEvent(self, *args, **kwargs):
        super().keyReleaseEvent(*args, **kwargs)
        self._refresh_empty_types()

    def actionEvent(self, *args, **kwargs):
        super().actionEvent(*args, **kwargs)
        self._refresh_empty_types()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_empty_types(self):
        if not self._is_valid():
            return
        folder = self.project_folder
        if folder != self._project_folder:
            self.empty_types = empty_types_from_project_folder(folder)
            self._project_folder = folder

    def _is_valid(self) -> bool:
        return self.mainWidget() is not None and hasattr(self.mainWidget(), 'wrappers')

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def project_folder(self) -> str:
        try:
            return self.mainWidget().wrappers['project_directory'].wrappedWidget().filePath()
        except Exception:
            return ''

    @property
    def empty_types(self) -> list:
        return self.mainWidget().wrappers['empty_type'].parameterDefinition().options()

    @empty_types.setter
    def empty_types(self, value: list):
        self.mainWidget().wrappers['empty_type'].parameterDefinition().setOptions(value)

    @property
    def gpkg_export_option(self) -> str:
        param = self.mainWidget().wrappers['gpkg_options'].parameterDefinition()
        idx = self.mainWidget().wrappers['gpkg_options'].wrappedWidget().currentIndex()
        opts = param.options()
        return opts[idx] if 0 <= idx < len(opts) else ''

# ---------------------------------------------------------------------------
# Processing algorithm
# ---------------------------------------------------------------------------

class CatchImportEmpty(QgsProcessingAlgorithm):
    """
    Import empty files into a CATCH project.

    The *Project Directory* parameter should point to the **Modelling**
    folder of the CATCH project.  Empty template files are read from
    ``TUFLOW/model/gis/empty`` (HPC) and/or ``TUFLOWFV/model/gis/empty``
    (FV) beneath that folder, and output layers are written to
    ``TUFLOW/model/gis`` or ``TUFLOWFV/model/gis`` accordingly.
    """

    def initAlgorithm(self, config=...):
        project = ProjectConfig.from_qgs_project()
        folder = str(project.folder) if project.valid else None

        self.addParameter(
            QgsProcessingParameterFile(
                'project_directory', 'Project Directory (Modelling Folder)',
                behavior=QgsProcessingParameterFile.Folder,
                fileFilter='All files (*.*)',
                defaultValue=folder
            )
        )

        options = empty_types_from_project_folder(folder) if folder else []
        self.addParameter(
            EmptySelectorParameter(
                'empty_type',
                'Empty Type',
                options=options,
                defaultValue=()
            )
        )

        # run id
        self.addParameter(
            QgsProcessingParameterString(
                'run_id',
                'Run ID',
                multiLine=False,
                defaultValue=''
            )
        )
        # overwrite file if it already exists
        self.addParameter(
            QgsProcessingParameterBoolean(
                'overwrite',
                'Overwrite Output if Exist',
                optional=False,
                defaultValue=False
            )
        )

        param = QgsProcessingParameterEnum(
            'gpkg_options',
            'GPKG Options',
            optional=False,
            options=['Separate', 'Group Geometry Types', 'All to one'],
            allowMultiple=False,
            usesStaticStrings=False,
            defaultValue=0
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

        param = QgsProcessingParameterFileDestination(
            'export_to_gpkg_all_to_one',
            'Export to GPKG (All to One)',
            optional=True,
            fileFilter='GPKG (*.gpkg *.GPKG)',
            defaultValue=None
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

    def processAlgorithm(self, parameters, context, model_feedback):
        results = {'OUTPUT': []}

        project_folder = self.parameterAsString(
            parameters,
            'project_directory',
            context
        )
        empty_types_str = parameters.get('empty_type', '')
        empty_types_parsed = EmptySelectorPanel.parse_empty_type_string(empty_types_str)
        empty_types = [
            (t, g)
            for t, geoms in empty_types_parsed.items()
            for g, checked in geoms.items()
            if checked
        ]
        run_id = self.parameterAsString(parameters, 'run_id', context)
        overwrite = self.parameterAsBool(parameters, 'overwrite', context)
        gpkg_option_idx = self.parameterAsEnum(parameters, 'gpkg_options', context)
        gpkg_folder = self.parameterAsString(parameters, 'export_to_gpkg_all_to_one', context)

        gpkg_export_option = ['Separate', 'Group Geometry Types', 'All to one'][gpkg_option_idx]

        total = len(empty_types) or 1
        feedback = QgsProcessingMultiStepFeedback(total, model_feedback)
        creator = CatchEmptyCreator(project_folder, gpkg_export_option, gpkg_folder, overwrite, feedback)

        for empty_type, geom in empty_types:
            feedback.pushInfo(f'Creating {empty_type} [{geom}]...')
            uri, name = creator.create_empty(empty_type, geom, run_id)
            if not uri:
                feedback.pushWarning(f'{empty_type} [{geom}] already exists. Skipping.')
            else:
                processing.run(
                    'native:loadlayer', {'INPUT': uri, 'NAME': name},
                    context=context, feedback=feedback, is_child_algorithm=True)
            feedback.setProgress(feedback.progress() + 1)

        return results

    def createCustomParametersWidget(self, parent=None):
        """Return the custom dialog with tooltip support and dynamic empty-type refresh."""
        return CatchImportEmpty_CustomDialog(self, False, parent)

    def name(self):
        return 'catch_import_empty'

    def displayName(self):
        return 'Import Empty'

    def icon(self) -> QIcon:
        return QIcon(str(Path(__file__).parents[2] / 'icons' / 'catch_import_empty.svg'))

    def shortHelpString(self) -> str:
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help' / 'html' / 'import_empty.html'
        with help_filename.open() as fo:
            return self.tr(fo.read().replace('\n', '<p>'))

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return CatchImportEmpty()

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
