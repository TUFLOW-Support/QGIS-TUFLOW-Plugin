import json
import os
import subprocess
import typing
from pathlib import Path

from qgis._core import QgsCoordinateReferenceSystem, QgsProject, QgsVectorLayer, QgsVectorFileWriter, \
    QgsCoordinateTransformContext

from .gdal_ import get_driver_name_from_extension


class ProjectConfig:
    """Class for setting up and reading TUFLOW settings from a project (.QGZ or .JSON)."""

    def __init__(
            self,
            name: str,
            folder: str,
            crs: QgsCoordinateReferenceSystem,
            gis_format: typing.Union[int, str],
            hpcexe: str = '',
            fvexe: str = ''
    ):
        self.name = name
        self.folder = Path(folder)
        self.hpc_folder = self.folder
        self.fv_folder = self.folder
        self.crs = crs
        if isinstance(gis_format, int):
            self.gis_format = self.gis_format_extension(gis_format)
        else:
            self.gis_format = gis_format
        if self.gis_format == 'gpkg':
            self.gis_template_type = 'db'
        else:
            self.gis_template_type = 'sep'
        self.run_hpc = False
        if hpcexe:
            self.run_hpc = True
        self.run_fv = False
        if fvexe:
            self.run_fv = True
        self.hpcexe = Path(hpcexe)
        self.fvexe = Path(fvexe)
        self.valid = bool(self.name)

    @staticmethod
    def from_json(json_file) -> 'ProjectConfig':
        """Creates a Project object from a JSON file."""
        d = json.load(json_file)
        return ProjectConfig(
            d['name'],
            d['folder'],
            QgsCoordinateReferenceSystem(d['crs']),
            d['gis_format'],
            d['hpcexe'],
            d['fvexe']
        )

    @staticmethod
    def from_qgs_project() -> 'ProjectConfig':
        project = QgsProject.instance()
        name = project.readEntry('tuflow', 'project/name', '')
        folder = project.readEntry('tuflow', 'project/folder', '')
        crs = project.readEntry('tuflow', 'project/crs', '')
        gis_format = project.readEntry('tuflow', 'project/gis_format', '')
        hpcexe = project.readEntry('tuflow', 'project/hpcexe', '')
        fvexe = project.readEntry('tuflow', 'project/fvexe', '')
        return ProjectConfig(
            name[0],
            folder[0],
            QgsCoordinateReferenceSystem(crs[0]),
            gis_format[0],
            hpcexe[0],
            fvexe[0]
        )

    def gis_format_extension(self, enum: int) -> str:
        """Returns the file extension for the GIS format."""
        return {
            0: 'gpkg',
            1: 'shp',
            2: 'mif'
        }[enum]

    def gis_extension_to_enum(self, gis_format) -> int:
        """Returns the enum for the GIS format."""
        return {
            'gpkg': 0,
            'shp': 1,
            'mif': 2
        }[gis_format]

    def driver_name(self, ext: str):
        """Returns the driver name for the GIS format."""
        return get_driver_name_from_extension('vector', ext)

    def write_qgs_project(self, param: str = None) -> None:
        """Writes settings to QGIS Project."""
        project = QgsProject.instance()
        if param:
            project.writeEntry('tuflow', f'project/{param}', str(getattr(self, param)))
            return

        project.writeEntry('tuflow', 'project/name', str(self.name))
        project.writeEntry('tuflow', 'project/folder', str(self.folder))
        project.writeEntry('tuflow', 'project/crs', self.crs.authid())
        project.writeEntry('tuflow', 'project/gis_format', self.gis_format)
        project.writeEntry('tuflow', 'project/hpcexe', str(self.hpcexe) if self.run_hpc else '')
        project.writeEntry('tuflow', 'project/fvexe', str(self.fvexe) if self.run_fv else '')
        if not project.fileName():
            proj_path = self.folder / f'{self.name}_workspace.qgz'
            project.write(str(proj_path))

    def write_json(self) -> None:
        """
        Writes settings to JSON file. Use posix for path otherwise json write out with double backslashes
        which would be annoying for users to be able to copy/paste manually from file.
        """
        if not self.folder.exists():
            raise Exception('Project folder does not exist.')
        json_path = self.folder / 'tfsettings.json'
        d = {
            'name': self.name,
            'folder': str(self.folder.as_posix()),
            'crs': self.crs.authid(),
            'gis_format': self.gis_format,
            'hpcexe': str(self.hpcexe.as_posix()) if self.run_hpc else '',
            'fvexe': str(self.fvexe.as_posix()) if self.run_fv else ''
        }
        json_path.open('w').write(json.dumps(d, indent=4, ensure_ascii=False))

    def save_settings(self) -> None:
        """Saves TUFLOW project settings to QGS project and JSON file."""
        if not self.folder.exists():
            self.folder.mkdir(parents=True, exist_ok=True)
        self.write_qgs_project()
        self.write_json()
        QgsProject.instance().setPresetHomePath(str(self.folder))

    def _create_folders(self, parent: Path, folders: list[str]) -> None:
        """Creates folders if they don't already exist."""
        for folder in folders:
            path = parent / folder
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)

    def create_folders(self) -> None:
        """Creates TUFLOW and TUFLOW FV folders."""
        hpc = ['bc_dbase', 'check', 'model/gis', 'model/grid', 'results', 'runs/log']
        fv = ['bc_dbase/met', 'check', 'model/gis', 'model/geo', 'model/csv', 'results', 'runs/log', 'wqm', 'stm']
        if self.run_hpc:
            self._create_folders(self.hpc_folder, hpc)
        if self.run_fv:
            self._create_folders(self.fv_folder, fv)

    def projection_command(self, fv: bool) -> str:
        """Returns the TUFLOW projection command."""
        d = {
            'shp': 'SHP',
            'gpkg': 'GPKG',
            'mif': 'MI'
        }
        gis = self.gis_format
        if fv and self.gis_format == 'gpkg':
            gis = 'shp'
        sep = os.sep
        if self.gis_template_type == 'db':
            return f'{d[gis]} Projection == ..{sep}model{sep}gis{sep}{self.name}.{gis} >> projection'
        else:
            return f'{d[gis]} Projection == ..{sep}model{sep}gis{sep}projection.{gis}'

    def run_exe(self, exe: str, args: list, feedback, **kwargs) -> None:
        """Runs an executable with arguments."""
        a = [exe] + args
        print(a)
        if feedback:  # assume the output should be piped to processing dialog
            with (subprocess.Popen(a, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                                  creationflags=subprocess.CREATE_NO_WINDOW, bufsize=0, universal_newlines=True)
                  as proc):
                for line in proc.stdout:
                    feedback.pushInfo(line.strip('\n'))
        else:
            subprocess.run(a, **kwargs)

    def create_proj_gis_file(self, gis_folder: Path, fv: bool) -> None:
        """Creates the projection gis file for use in TUFLOW for creating empties."""
        if not gis_folder.exists():
            gis_folder.mkdir(parents=True, exist_ok=True)
        if fv and self.gis_format == 'gpkg':
            gis = 'shp'
        else:
            gis = self.gis_format
        if self.gis_template_type == 'db':
            proj_file = gis_folder / f'{self.name}.{gis}'
        else:
            proj_file = gis_folder / f'projection.{gis}'
        lyr = QgsVectorLayer(f'Point?crs={self.crs.authid()}', 'projection', 'memory')
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = self.driver_name(gis)
        options.layerName = 'projection'
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        ret = QgsVectorFileWriter.writeAsVectorFormatV3(lyr, str(proj_file),  QgsCoordinateTransformContext(), options)
        if ret[0] != QgsVectorFileWriter.NoError:
            raise Exception(ret[1])

    def create_hpc_empties(self) -> None:
        """Creates empty TUFLOW HPC files."""
        gis_folder = self.hpc_folder / 'model' / 'gis'
        self.create_proj_gis_file(gis_folder, False)
        sep = os.sep
        text = (f'{self.projection_command(False)}\n'
                f'GIS Format == {self.gis_format.upper()}\n'
                f'Write Empty GIS Files == ..{sep}model{sep}gis{sep}empty\n')
        tcf = self.hpc_folder / 'runs' / 'write_empties.tcf'
        tcf.open('w').write(text)
        self.run_exe(str(self.hpcexe), ['-b', '-nmb', str(tcf)], None)

    def create_fv_empties(self) -> None:
        """Creates empty TUFLOW FV files."""
        gis_folder = self.fv_folder / 'model' / 'gis'
        self.create_proj_gis_file(gis_folder, True)
        sep = os.sep
        text = (f'{self.projection_command(True)}\n'
                f'GIS Format == {"SHP" if self.gis_format == "gpkg" else self.gis_format.upper()}\n'
                f'Write Empty GIS Files == ..{sep}model{sep}gis{sep}empty\nTutorial Model == ON')
        fvc = self.fv_folder / 'runs' / 'write_empties.fvc'
        fvc.open('w').write(text)
        self.run_exe(str(self.fvexe), [str(fvc)], None, cwd=str(self.folder / 'fv' / 'runs'))

    def _replace_variables(self, input_str: str) -> str:
        """Replaces variables in a string."""
        var = {
            '${model_name}': self.name,
            '${gis_format}': self.gis_format.upper(),
            '${gis_ext}': self.gis_format,
            '${gis_projection_command}': self.projection_command(False),
            '${fv_gis_format}': 'SHP' if self.gis_format == 'gpkg' else self.gis_format.upper(),
            '${fv_gis_projection_command}': self.projection_command(True),
            '${hpcexe}': str(self.hpcexe),
            '${fvexe}': str(self.fvexe)
        }
        for k, v in var.items():
            input_str = input_str.replace(k, v)
        return input_str

    def _setup_cf_templates(self, template_folder: Path) -> None:
        """Sets up TUFLOW control file templates."""
        for in_file in template_folder.glob('**/*.*'):
            rel_path = os.path.relpath(in_file, template_folder)
            out_file = self.folder / self._replace_variables(str(rel_path))
            with in_file.open() as fi:
                if out_file.exists():
                    continue
                if not out_file.parent.exists():
                    out_file.parent.mkdir(parents=True, exist_ok=True)
                with out_file.open('w') as fo:
                    fo.write(self._replace_variables(fi.read()))

    def _setup_hpc_templates(self, parent_folder: Path) -> None:
        """Sets up TUFLOW HPC control file templates."""
        hpc_template_folder = parent_folder / 'hpc' / self.gis_template_type
        self._setup_cf_templates(hpc_template_folder)

    def _setup_fv_templates(self, parent_folder: Path) -> None:
        """Sets up TUFLOW FV control file templates."""
        fv_template_folder = parent_folder / 'fv'
        self._setup_cf_templates(fv_template_folder)

    def setup_cf_templates(self) -> None:
        """Sets up TUFLOW control file templates."""
        template_folder = Path(os.path.realpath(__file__)).parent.parent / 'cf_templates'
        if self.run_hpc:
            self._setup_hpc_templates(template_folder)
        if self.run_fv:
            self._setup_fv_templates(template_folder)
