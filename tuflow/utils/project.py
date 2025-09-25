import json
import os
import re
import subprocess
import typing
from pathlib import Path

import numpy as np
from qgis._core import QgsCoordinateReferenceSystem, QgsProject, QgsVectorLayer, QgsVectorFileWriter, \
    QgsCoordinateTransformContext

from tuflow.tuflowqgis_library import get_driver_by_extension
from .gdal_ import get_driver_name_from_extension
from osgeo import gdal, osr, ogr
from tuflow.tuflowqgis_settings import TF_Settings


class ProjectConfig:
    """Class for setting up and reading TUFLOW settings from a project (.QGZ or .JSON)."""

    def __init__(
            self,
            name: str,
            folder: str,
            crs: QgsCoordinateReferenceSystem,
            gis_format: typing.Union[int, str],
            hpcexe: str = '',
            fvexe: str = '',
            domain: str = '',
            settings: dict = None,
            output_formats: dict = None,
            save_settings_globally: bool = False
    ):
        self.name = name
        self.folder = Path(folder)
        self.hpc_folder = self.folder
        self.fv_folder = self.folder
        self.crs = crs
        self.save_settings_globally = save_settings_globally
        if isinstance(gis_format, int):
            self.gis_format = self.gis_format_extension(gis_format)
        else:
            self.gis_format = gis_format
        if self.gis_format.lower() == 'gpkg':
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
        self.fvexe = Path(fvexe) if fvexe is not None else Path('')
        self.domain = domain
        self.command_validation = self._get_command_validation()
        self.section_validation = self._get_section_validation()
        self.settings = settings
        if self.settings:
            self.settings.update(self._get_hidden_inputs())
            self.update_timestep_settings()
        self.output_formats = output_formats
        self.valid = bool(self.name)
        self._proj_file_created = False

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
        """Returns a Project object from the current QGS project."""
        project = QgsProject.instance()
        name, _ = project.readEntry('tuflow', 'project/name', '')
        folder, _ = project.readEntry('tuflow', 'project/folder', '')
        crs, _ = project.readEntry('tuflow', 'project/crs', '')
        gis_format, _ = project.readEntry('tuflow', 'project/gis_format', '')
        hpcexe, _ = project.readEntry('tuflow', 'project/hpcexe', '')
        fvexe, _ = project.readEntry('tuflow', 'project/fvexe', '')
        return ProjectConfig(
            name,
            folder,
            QgsCoordinateReferenceSystem(crs),
            gis_format,
            hpcexe,
            fvexe
        )

    @staticmethod
    def from_global_settings() -> 'ProjectConfig':
        """Returns a project object from the old TUFLOW settings."""
        tf_settings = TF_Settings()
        tf_settings.Load()
        name = ''
        folder = tf_settings.combined.base_dir if tf_settings.combined.base_dir is not None else ''
        crs = tf_settings.combined.CRS_ID
        gis_format = tf_settings.combined.gis_format if tf_settings.combined.gis_format else 'GPKG'
        hpcexe = tf_settings.combined.tf_exe if tf_settings.combined.tf_exe is not None else ''
        fvexe = ''
        return ProjectConfig(
            name,
            folder,
            QgsCoordinateReferenceSystem(crs),
            gis_format,
            hpcexe,
            fvexe
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

        self.write_old_project_settings()  # set deprecated settings so some of the deprecated tools still get the settings updated

        if not project.fileName():
            proj_path = self.folder / f'{self.name}_workspace.qgz'
            project.write(str(proj_path))

    def write_old_project_settings(self) -> None:
        """Writes project settings to the old TUFLOW settings class which is still used by some of the older tools."""
        tfsettings = TF_Settings()
        tfsettings.Load()
        tfsettings.project_settings.CRS_ID = self.crs.authid()
        tfsettings.project_settings.tf_exe = str(self.hpcexe) if self.run_hpc else ''
        tfsettings.project_settings.base_dir = str(self.folder)
        tfsettings.project_settings.engine = 'classic'
        tfsettings.project_settings.tutorial = False
        tfsettings.project_settings.gis_format = self.gis_format
        err, msg = tfsettings.Save_Project()
        if err:
            print(msg)
        if self.save_settings_globally:
            tfsettings.global_settings = tfsettings.project_settings
            err, msg = tfsettings.Save_Global()
            if err:
                print(msg)

    def write_json(self) -> None:
        """Writes settings to JSON file. Use posix for path otherwise json write out with double backslashes
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
        with json_path.open('w') as f:
            f.write(json.dumps(d, indent=4, ensure_ascii=False))

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
        if fv and self.gis_format.lower() == 'gpkg':
            gis = 'shp'
        sep = os.sep
        if self.gis_template_type == 'db':
            return f'{d[gis.lower()]} Projection == ..{sep}model{sep}gis{sep}{self.name}_001.{gis.lower()} >> projection'
        else:
            return f'{d[gis.lower()]} Projection == ..{sep}model{sep}gis{sep}projection.{gis.lower()}'

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
        if self._proj_file_created:
            return
        if not gis_folder.exists():
            gis_folder.mkdir(parents=True, exist_ok=True)
        if fv and self.gis_format.lower() == 'gpkg':
            gis = 'shp'
        else:
            gis = self.gis_format.lower()
        if self.gis_template_type == 'db':
            proj_file = gis_folder / f'{self.name}_001.{gis.lower()}'
        else:
            proj_file = gis_folder / f'projection.{gis.lower()}'
        lyr = QgsVectorLayer(f'Point?crs={self.crs.authid()}&field=id:string', 'projection', 'memory')
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = self.driver_name(gis.lower())
        options.layerName = 'projection'
        if Path(proj_file).exists() and self.gis_format.lower() == 'gpkg':
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        else:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        ret = QgsVectorFileWriter.writeAsVectorFormatV3(lyr, str(proj_file),  QgsCoordinateTransformContext(), options)
        if ret[0] != QgsVectorFileWriter.NoError:
            raise Exception(ret[1])
        self._proj_file_created = True

    def create_tif_projection(self, grid_folder: Path) -> None:
        """Creates a template TIF projection file that TUFLOW can use as a reference."""
        if not grid_folder.exists():
            grid_folder.mkdir(parents=True, exist_ok=True)
        sr = osr.SpatialReference(self.crs.toWkt())
        tif = gdal.GetDriverByName('GTiff').Create(str(grid_folder / 'projection.tif'), 1, 1, 1, gdal.GDT_Float32)
        tif.SetGeoTransform([0, 1, 0, 0, 0, -1])
        tif.SetSpatialRef(sr)
        data = np.zeros((1, 1)).astype(np.float32)
        band = tif.GetRasterBand(1)
        band.WriteArray(data)
        band.SetNoDataValue(-999)
        tif = None

    def create_hpc_empties(self) -> None:
        """Creates empty TUFLOW HPC files."""
        gis_folder = self.hpc_folder / 'model' / 'gis'
        self.create_proj_gis_file(gis_folder, False)
        if self.settings.get('GRID Format') == 'TIF':
            self.create_tif_projection(self.hpc_folder / 'model' / 'grid')
        sep = os.sep
        text = (f'{self.projection_command(False)}\n'
                f'GIS Format == {self.gis_format.upper()}\n'
                f'Write Empty GIS Files == ..{sep}model{sep}gis{sep}empty\n')
        tcf = self.hpc_folder / 'runs' / 'write_empties.tcf'
        with tcf.open('w') as f:
            f.write(text)
        self.run_exe(str(self.hpcexe), ['-b', '-nmb', str(tcf)], None)

    def create_fv_empties(self) -> None:
        """Creates empty TUFLOW FV files."""
        gis_folder = self.fv_folder / 'model' / 'gis'
        self.create_proj_gis_file(gis_folder, True)
        sep = os.sep
        text = (f'{self.projection_command(True)}\n'
                f'GIS Format == {"SHP" if self.gis_format.lower() == "gpkg" else self.gis_format.upper()}\n'
                f'Write Empty GIS Files == ..{sep}model{sep}gis{sep}empty\nTutorial Model == ON')
        fvc = self.fv_folder / 'runs' / 'write_empties.fvc'
        fvc.open('w').write(text)
        self.run_exe(str(self.fvexe), [str(fvc)], None, cwd=str(self.folder / 'fv' / 'runs'))

    def _get_hidden_inputs(self) -> dict:
        """Hidden inputs are those that are not shown in the GUI but are used in the TUFLOW control files.
        These inputs can contain validation steps that determine whether they should be kept/removed from
        the template control files.
        """
        f = Path(__file__).parents[1] / 'alg' / 'data' / 'create_tuflow_settings.json'
        with f.open() as fi:
            d = json.load(fi)
        d = d.get('command settings', {})
        d = {k2: None for k, v in d.items() for k2, v2 in v.items() if v2['type'].lower() == 'none'}
        return d

    def update_timestep_settings(self) -> None:
        """Switches the "Timestep == " command to be "Timestep Initial == " if the solution scheme is set to HPC.
        Also sets validation steps so that the command that isn't used is removed from the template control files.
        """
        ss = self.settings.get('Solution Scheme', '')
        if ss == 'Classic':
            self.command_validation['Timestep Initial'] = 'Solution Scheme == HPC'
        elif ss == 'HPC':
            self.command_validation['Timestep'] = 'Solution Scheme == Classic'
            self.settings['Timestep Initial'] = self.settings['Timestep']

    def _get_command_validation(self) -> dict:
        """Returns the validation requirements for some of the commands in the TUFLOW control files."""
        f = Path(__file__).parents[1] / 'alg' / 'data' / 'create_tuflow_settings.json'
        with f.open() as fi:
            d = json.load(fi)
        d = d.get('command settings', {})
        d = {k2: v2.get('validation', None) for k, v in d.items() for k2, v2 in v.items()}
        return d

    def _get_section_validation(self) -> dict:
        """Returns the validation requirements for some of the sections in the TUFLOW control files."""
        f = Path(__file__).parents[1] / 'alg' / 'data' / 'create_tuflow_settings.json'
        with f.open() as fi:
            d = json.load(fi)
        d = d.get('section settings', {})
        d = {k: v.get('validation', None) for k, v in d.items()}
        return d

    def _validate_command(self, lhs, validation) -> bool:
        """Returns if the command/section is valid based on the validation requirements."""
        if lhs not in validation:
            return True
        if not validation[lhs]:
            return True
        validation_reqs = validation[lhs]
        if not isinstance(validation_reqs, list):
            validation_reqs = [validation_reqs]
        for req in validation_reqs:
            lhs1, rhs1 = req.split(' == ')
            if lhs1 not in self.settings:
                return True
            rhs2 = self.settings[lhs1]
            if rhs1.lower() != rhs2.lower():
                return False
        return True

    def _domain_commands(self, domain_str: str) -> str:
        """Returns the domain commands for the TUFLOW control files."""
        origin, angle, size = domain_str.split('--')
        origin_x, origin_y = origin.split(':')
        width, height = size.split(':')
        return (f'Origin == {origin_x} {origin_y}\n'
                f'Orientation Angle == {angle}\n'
                f'Grid Size (X,Y) == {width}, {height}')

    def _output_format_commands(self, fmts: dict):
        from tuflow.gui.widgets.output_format_widget import OUT_FMT
        def data_types(result_types: list) -> str:
            return ' '.join([OUT_FMT['types'][x] for x in result_types])

        def output_data_types(fmt: str, result_types: list) -> str:
            lhs = f'{fmt} Map Output Data Types' if fmt else 'Map Output Data Types'
            return '{0} == {1}'.format(lhs, data_types(result_types))

        def output_interval(fmt:str, interval: list) -> str:
            lhs = f'{fmt} Map Output Interval' if fmt else 'Map Output Interval'
            return f'{lhs} == {interval}'

        string = 'Map Output Format == {0}'.format(' '.join(list(fmts.keys())))
        for i, (fmt, settings) in enumerate(fmts.items()):
            if i == 0:
                string = '{0}\n{1}\n{2}'.format(string, output_data_types(None, settings['result_types']), output_interval(None, settings["interval"]))
            string = '{0}\n{1}\n{2}'.format(string, output_data_types(fmt, settings['result_types']), output_interval(fmt, settings["interval"]))
        return string

    def _replace_variables(self, input_str: str) -> str:
        """Replaces variables in a string."""
        var = {
            '${model_name}': self.name,
            '${gis_format}': self.gis_format.upper(),
            '${gis_ext}': self.gis_format.lower(),
            '${gis_projection_command}': self.projection_command(False),
            '${fv_gis_format}': 'SHP' if self.gis_format.lower() == 'gpkg' else self.gis_format.upper(),
            '${fv_gis_projection_command}': self.projection_command(True),
            '${hpcexe}': str(self.hpcexe),
            '${fvexe}': str(self.fvexe)
        }
        for k, v in var.items():
            if k == '${gis_projection_command}' and self.settings['GRID Format'] == 'TIF':
                if self.gis_template_type == 'db':
                    k = 'GPKG Projection == projection'
                    v = k
                v = f'{v}\nTIF Projection == ..{os.sep}model{os.sep}grid{os.sep}projection.tif'
            input_str = input_str.replace(k, v)
        return input_str

    def _find_block(self, input_str: str, keyword: str) -> str:
        """Finds a block of text starting with the keyword and ending with a blank line."""
        if keyword not in input_str:
            return ''
        i = input_str.find(keyword)
        if '\n\n' not in input_str[i:]:
            return input_str[i:]
        j = input_str[i:].find('\n\n') + i
        return input_str[i:j]

    def _clean_empty_blocks(self, input_str: str):
        """Cleans/removes empty blocks from the template control files. Empty blocks can be left over
        after some commands/sections are removed after the validation step.
        """
        empty_block = '\n!_______________________________________________________\n\n'
        return input_str.replace(empty_block, '')

    def _replace_block(self, input_str: str) -> str:
        """Replaces a block of text with a new block with actual values.
        e.g. a block headed with "! 2D DOMAIN SETUP" could be replaced with actual domain values.
        """
        var = {}
        if self.domain:
            var['! 2D DOMAIN SETUP'] = self._domain_commands(self.domain)
        if self.output_formats:
            var['! MAP OUTPUT FORMATS'] = self._output_format_commands(self.output_formats)
        for k, v in self.section_validation.items():
            if not self._validate_command(k, self.section_validation):
                var[k] = ''
        for k, v in var.items():
            block = self._find_block(input_str, k)
            if block:
                if not v:
                    input_str = input_str.replace(block, '')
                else:
                    input_str = input_str.replace(block, f'{k}\n{v}')
        return self._clean_empty_blocks(input_str)

    def _replace_commands(self, input_str: str) -> str:
        """Replaces a given command in the template control file with the actual value.
        This includes finding commands that are commented out in the template control file.
        """
        lines = input_str.split('\n')
        for lhs, rhs in self.settings.items():
            for i, line in enumerate(lines):
                if line is None:
                    continue
                if re.findall(fr'^\s*!?\s*{lhs}\s+==.*', line, flags=re.IGNORECASE):
                    if self._validate_command(lhs, self.command_validation):
                        if rhs is not None:
                            lines[i] = f'{lhs} == {rhs}'
                    else:
                        lines[i] = None
                    break
        return '\n'.join([x for x in lines if x is not None])

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
                    content = self._replace_variables(fi.read())
                    content = self._replace_block(content)
                    content = self._replace_commands(content)
                    fo.write(content)

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

    def create_domain_check_file(self, domain: str, crs_wkt: str) -> str:
        """Creates a domain check file."""
        checkfile = self.hpc_folder / 'check'/ f'create_project_2d_dom_check.{self.gis_format.lower()}'
        if not checkfile.parent.exists():
            checkfile.parent.mkdir(parents=True, exist_ok=True)

        driver_name = get_driver_by_extension('vector', self.gis_format)
        driver = ogr.GetDriverByName(driver_name)

        e = ''
        try:
            if checkfile.exists():
                ds = ogr.GetDriverByName(driver_name).Open(str(checkfile), 1)
            else:
                ds = ogr.GetDriverByName(driver_name).CreateDataSource(str(checkfile))
        except (RuntimeError, UnboundLocalError) as e:
            ds = None

        if ds is None:
            return f'ERROR: Unable to open/create domain check datasource: {e}'

        sr = osr.SpatialReference(crs_wkt)

        lyr = ds.GetLayer(checkfile.stem)
        exists = lyr is not None
        lyr = None
        if exists:
            ds.DeleteLayer(checkfile.stem)

        lyr = ds.CreateLayer(checkfile.stem, sr, ogr.wkbPolygon)

        if lyr is None:  # do it like this because old gdal versions returned None, newer versions raise exception
            return f'ERROR: Unable to create domain check layer'

        flds = [ogr.FieldDefn('Domain_Ind', ogr.OFTInteger), ogr.FieldDefn('Domain_Name', ogr.OFTString)]
        for fld in flds:
            lyr.CreateField(fld)

        origin, angle, size = domain.split('--')
        angle = float(angle)
        origin_x, origin_y = [float(x) for x in origin.split(':')]
        width, height = [float(x) for x in size.split(':')]

        # create a rotated rectangle
        a = np.array([[0., 0.], [width, 0.], [width, height], [0., height], [0., 0.]])
        rot = np.array([[np.cos(np.radians(-angle)), -np.sin(np.radians(-angle))], [np.sin(np.radians(-angle)), np.cos(np.radians(-angle))]])
        a = np.dot(a, rot) + np.array([origin_x, origin_y])

        # create geometry from rotated rectangle
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(a[0, 0], a[0, 1])
        ring.AddPoint(a[1, 0], a[1, 1])
        ring.AddPoint(a[2, 0], a[2, 1])
        ring.AddPoint(a[3, 0], a[3, 1])
        ring.AddPoint(a[0, 0], a[0, 1])
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)

        # create feature
        feat = ogr.Feature(lyr.GetLayerDefn())
        feat.SetField(0, 1)
        feat.SetField(1, 'Domain_001')
        feat.SetGeometry(poly)
        lyr.CreateFeature(feat)

        ds, lyr = None, None

        return str(checkfile) if self.gis_format != 'GPKG' else f'{checkfile}|layername={checkfile.stem}'
