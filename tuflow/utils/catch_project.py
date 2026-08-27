import json
import os
import re
import subprocess
from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING

from qgis.utils import plugins, iface
from qgis.core import (QgsProject, QgsUnitTypes, QgsCoordinateReferenceSystem, QgsProject, QgsVectorLayer, QgsVectorFileWriter,
                       QgsCoordinateTransformContext)

from tuflow.utils.catch_empties import TuflowCatchEmptyFiles


class ProjectConfig:

    def __init__(
            self,
            name: str,
            folder: str,
            crs: QgsCoordinateReferenceSystem,
            gis_format: int,
            hpcexe: str,
            fvexe: str,
    ):
        self.name = name
        self.folder = Path(folder)
        self.crs = crs
        if isinstance(gis_format, int):
            self.gis_format = self.gis_format_extension(gis_format)
        else:
            self.gis_format = gis_format
        if self.gis_format == 'gpkg':
            self.hpc_gis_template_type = 'db'
        else:
            self.hpc_gis_template_type = 'separate'
        self.fv_gis_template_type = 'separate'
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
        name = project.readEntry('tuflow_catch', 'project/name', '')
        folder = project.readEntry('tuflow_catch', 'project/folder', '')
        crs = project.readEntry('tuflow_catch', 'project/crs', '')
        gis_format = project.readEntry('tuflow_catch', 'project/gis_format', '')
        hpcexe = project.readEntry('tuflow_catch', 'project/hpcexe', '')
        fvexe = project.readEntry('tuflow_catch', 'project/fvexe', '')
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
        return {
            'gpkg': 'GPKG',
            'shp': 'ESRI Shapefile',
            'mif': 'MapInfo File'
        }[ext]

    def write_qgs_project(self) -> None:
        """Writes settings to QGIS Project."""
        project = QgsProject.instance()
        project.writeEntry('tuflow_catch', 'project/name', str(self.name))
        project.writeEntry('tuflow_catch', 'project/folder', str(self.folder))
        project.writeEntry('tuflow_catch', 'project/crs', self.crs.authid())
        project.writeEntry('tuflow_catch', 'project/gis_format', self.gis_format)
        project.writeEntry('tuflow_catch', 'project/hpcexe', str(self.hpcexe))
        project.writeEntry('tuflow_catch', 'project/fvexe', str(self.fvexe))
        # if not project.fileName():
        #     proj_path = self.folder / f'{self.name}_workspace.qgz'
        #     project.write(str(proj_path))
        # else:
        #     project.write(project.fileName())

    def write_json(self) -> None:
        """
        Writes settings to JSON file. Use posix for path otherwise json write out with double backslashes
        which would be annoying for users to be able to copy/paste manually from file.
        """
        if not self.folder.exists():
            raise Exception('Project folder does not exist.')
        json_path = self.folder / 'tcsettings.json'
        d = {
            'name': self.name,
            'folder': str(self.folder.as_posix()),
            'crs': self.crs.authid(),
            'gis_format': self.gis_format,
            'hpcexe': str(self.hpcexe.as_posix()),
            'fvexe': str(self.fvexe.as_posix())
        }
        json_path.open('w').write(json.dumps(d, indent=4, ensure_ascii=False))

    def save_settings(self) -> None:
        """Saves TUFLOW Catch project settings to QGS project and JSON file."""
        if not self.folder.exists():
            self.folder.mkdir(parents=True, exist_ok=True)
        self.write_qgs_project()
        # self.write_json()
        QgsProject.instance().setPresetHomePath(str(self.folder))

        custom_vars = {
            'hpc_path': str(self.hpcexe),
            'fv_path': str(self.fvexe),
            'crs': self.crs
        }
        QgsProject.instance().setCustomVariables(custom_vars)
        QgsProject.instance().write()

    def _create_folders(self, parent: Path, folders: list[str]) -> None:
        """Creates folders if they don't already exist."""
        for folder in folders:
            path = parent / folder
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)

    def create_folders(self) -> None:
        """Creates TUFLOW Catch, TUFLOW HPC, and TUFLOW FV folders."""
        catch = ['bc_dbase', 'check', 'model/gis', 'results', 'runs', 'runs/log']
        hpc = ['bc_dbase', 'check', 'model/gis', 'model/grid', 'results', 'runs/log', 'catch']
        fv = ['bc_dbase/met', 'check', 'model/gis', 'model/geo', 'model/csv', 'results', 'runs/log', 'wqm', 'stm']
        self._create_folders(self.folder / 'TUFLOWCATCH', catch)
        self._create_folders(self.folder / 'TUFLOW', hpc)
        self._create_folders(self.folder / 'TUFLOWFV', fv)

    def projection_command(self, fv: bool, write_empties: bool = False) -> str:
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
        tf = 'TUFLOWFV' if fv else 'TUFLOW'
        parent = Path('..')
        if not write_empties:
            parent = Path('..') / '..' / tf

        if (fv and self.fv_gis_template_type == 'separate') or (not fv and self.hpc_gis_template_type == 'separate'):
            p = parent / 'model' / 'gis' / f'projection.{gis}'
            return f'{d[gis]} Projection == {p}'

        if write_empties:  # if GPKG but only for write_empties.tcf
            return f'{d[gis]} Projection == ..{sep}model{sep}gis{sep}{self.name}.{gis} >> projection'

        return f'{d[gis]} Projection == projection'

    def catch_projection_command(self) -> str:
        """Returns the TUFLOW projection command for TUFLOW Catch."""
        d = {
            'shp': 'SHP',
            'gpkg': 'GPKG',
            'mif': 'MI'
        }
        # gis_format = 'shp' if self.gis_format == 'gpkg' else self.gis_format
        # allows gpkg to be global gis format
        # dbname = f'{self.name}.{self.gis_format}' if self.hpc_gis_template_type == 'db' else f'projection.{self.gis_format}'
        # p = str(Path('..') / '..' / 'TUFLOW' / 'model' / 'gis' / dbname)
        # if self.gis_format == 'gpkg':
        #     p = f'{p} >> projection'

        dbname = f'projection.shp'
        p = str(Path('..') / '..' / 'TUFLOW' / 'model' / 'gis' / dbname)
        return f'SHP Projection == {p}'

    def spatial_database_command(self, fv: bool) -> str:
        if fv:
            if self.fv_gis_template_type == 'db':
                p = Path('..') / '..' / 'TUFLOWFV' / 'model' / 'gis' / f'{self.name}.{self.gis_format}'
                return f'Spatial Database == {p}'
            else:
                return ''
        else:
            if self.hpc_gis_template_type == 'db':
                p = Path('..') / '..' / 'TUFLOW' / 'model' / 'gis' / f'{self.name}.{self.gis_format}'
                return f'Spatial Database == {p}'
            else:
                return ''

    def run_exe(self, exe: str, args: list, feedback, **kwargs) -> subprocess.CompletedProcess:
        """Runs an executable with arguments."""
        a = [exe] + args
        print(a)
        if feedback:  # assume the output should be piped to processing dialog
            with (subprocess.Popen(a, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,  # nosec B603
                                  creationflags=subprocess.CREATE_NO_WINDOW, bufsize=0, universal_newlines=True)
                  as proc):
                for line in proc.stdout:
                    feedback.pushInfo(line.strip('\n'))
        else:
            return subprocess.run(a, **kwargs)  # nosec B603

    def create_proj_gis_file(self, gis_folder: Path, fv: bool) -> None:
        """Creates the projection gis file for use in TUFLOW for creating empties."""
        if not gis_folder.exists():
            gis_folder.mkdir(parents=True, exist_ok=True)
        if fv and self.gis_format == 'gpkg':
            gis = 'shp'
        else:
            gis = self.gis_format
        if (fv and self.fv_gis_template_type == 'db') or (not fv and self.hpc_gis_template_type == 'db'):
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
        gis_folder = self.folder / 'tuflow' / 'model' / 'gis'
        self.create_proj_gis_file(gis_folder, False)
        sep = os.sep
        text = (f'{self.projection_command(False, True)}\n'
                f'GIS Format == {self.gis_format.upper()}\n'
                f'Write Empty GIS Files == ..{sep}model{sep}gis{sep}empty\n')
        tcf = self.folder / 'tuflow' / 'runs' / 'write_empties.tcf'
        tcf.open('w').write(text)
        proc = self.run_exe(str(self.hpcexe), ['-b', '-nmb', tcf.name], None,
                            cwd=str(self.folder / 'TUFLOW' / 'runs'))
        if proc.returncode != 0:
            errmsg = proc.stderr.decode('utf-8')
            raise Exception(f'Error creating TUFLOW HPC empty files. Return Code: {proc.returncode} STDERR: "{errmsg}"')

    def create_fv_empties(self) -> None:
        """Creates empty TUFLOW FV files."""
        gis_folder = self.folder / 'TUFLOWFV' / 'model' / 'gis'
        self.create_proj_gis_file(gis_folder, True)
        sep = os.sep
        text = (f'{self.projection_command(True, True)}\n'
                f'GIS Format == {"SHP" if self.gis_format == "gpkg" else self.gis_format.upper()}\n'
                f'Write Empty GIS Files == ..{sep}model{sep}gis{sep}empty\nTutorial Model == ON')
        fvc = self.folder / 'TUFLOWFV' / 'runs' / 'write_empties.fvc'
        fvc.open('w').write(text)
        proc = self.run_exe(str(self.fvexe), [fvc.name], None, cwd=str(self.folder / 'TUFLOWFV' / 'runs'))
        if proc.returncode != 0:
            raise Exception(f'Error creating TUFLOWFV empty files. Return Code: {proc.returncode}')

    def create_catch_empties(self) -> None:
        """Creates some custom TUFLOWCATCH empty files (create these manually)."""
        empties = TuflowCatchEmptyFiles(self.gis_format, self.crs.toWkt())
        gis_folder = self.folder / 'tuflow' / 'model' / 'gis'  # HPC empty folder
        empties.write(gis_folder / 'empty')

    def _replace_variables(self, input_str: str) -> str:
        """Replaces variables in a string."""
        var = {
            '${model_name}': self.name,
            '${gis_format}': self.gis_format.upper(),
            '${spatial_database_command}': self.spatial_database_command(False),
            '${gis_projection_command}': self.projection_command(False),
            '${fv_gis_format}': 'SHP' if self.gis_format == 'gpkg' else self.gis_format.upper(),
            '${fv_gis_projection_command}': self.projection_command(True),
            '${catch_gis_projection_command}': self.catch_projection_command(),
            '${hpcexe}': str(self.hpcexe),
            '${fvexe}': str(self.fvexe)
        }
        for k, v in var.items():
            input_str = input_str.replace(k, v)
        return input_str

    def setup_cf_templates(self, template_selection: list[int]) -> None:
        """Sets up TUFLOW control file templates."""
        # Map containing parameter integer and the corresponding ext or key word
        file_map = {0: ".tcc",
                    1: ".bat",
                    2: ".tgc",
                    3: ".tbc",
                    4: "bc_dbase_",
                    5: "materials",
                    6: ".trfc",
                    7: ".ecf",
                    8: ".tsoilf",
                    9: ".tef",
                    10: ".fvwq",
                    11: ".fvsed"}

        template_folder = Path(os.path.realpath(__file__)).parents[1] / 'cf_templates' / 'catch'
        selection = {file_map[i] for i in template_selection} # Selected extensions/key words

        selected_files = [] # Selected files
        for ext in selection:
            selected_files.extend(template_folder.glob(f"**/*{ext}*"))

        for in_file in selected_files:
            rel_path = os.path.relpath(in_file, template_folder)
            out_file = self.folder / self._replace_variables(str(rel_path))
            with in_file.open() as fi:
                if out_file.exists():
                    continue
                if not out_file.parent.exists():
                    out_file.parent.mkdir(parents=True, exist_ok=True)
                with out_file.open('w') as fo:
                    fo.write(self._replace_variables(fi.read()))
