import os
import re
import shutil
import subprocess
import sys
import tempfile
import typing
from pathlib import Path

from qgis._core import QgsVectorLayer, QgsVectorFileWriter, QgsCoordinateTransformContext

from .gpkg import GPKG
from .gdal_ import get_driver_name_from_extension


def get_empty_type(name) -> str:
    if '_empty' not in name:
        return ''
    suffix = '_pts' if '_pts' in name.lower() else ''
    return name.split('_empty')[0] + suffix


def unique_empty_names(folder: Path) -> list[str]:
    empty_names = []
    for empty_file in folder.glob('*.*'):
        if empty_file.suffix.lower() not in ['.shp', '.mif', '.gpkg']:
            continue
        empty_type = get_empty_type(empty_file.stem)
        if empty_type and empty_type not in empty_names:
            empty_names.append(empty_type)
    return empty_names


def empty_types_from_project_folder(folder: typing.Union[str, Path]) -> list[str]:
    if isinstance(folder, str):
        folder = Path(folder)
    hpc = folder / 'model' / 'gis' / 'empty'
    if not hpc.exists():
        # maybe provided folder is empty folder - allow this
        return unique_empty_names(folder)
    return unique_empty_names(hpc)


class TooltipBuilder:

    def __init__(self):
        self.html = ''

    @staticmethod
    def from_file(file: Path):
        d = {}
        with file.open() as f:
            d = {x.split('==')[0].strip(): x.split('==')[1].strip() for x in f.read().split('\n') if x.strip()}
        t = TooltipBuilder()
        t.add(t.control_file(d.get('location', '')))
        t.add(t.command(d.get('command', '')))
        t.add(t.description(d.get('description', '')))
        t.add(t.links(d.get('wiki link', ''), d.get('manual link', ''), d.get('manual page', 0)))
        return t

    def add(self, text: str) -> None:
        self.html = f'{self.html}{text}<p>'

    def control_file(self, text: str) -> str:
        return f'<span style=" font-family:\'Courier New\'; font-size:10pt; color:#000000;">{text}</span><p>'

    def command(self, text: str) -> str:
        if text:
            return (f'<span style=" font-family:\'Courier New\'; font-size:8pt; color:#0000ff;">{text}'
                    f'</span><span style=" font-family:\'Courier New\'; font-size:8pt; color:#ff0000;"> ==</span><p>')
        return ''

    def description(self, text: str) -> str:
        return f'<span style=" font-family:\'MS Shell Dlg 2\'; font-size:8pt; color:#000000;">{text}</span><p>'

    def links(self, wiki_link: str, manual_link: str, manual_page: int) -> str:
        manual_link_ = f'{manual_link}#page={manual_page}' if manual_page else manual_link
        if not wiki_link and not manual_link_:
            return ''
        html = '<ul>'
        if wiki_link:
            html = f'{html}<li><a href="{wiki_link}"><span style=" font-size:8pt;">Link to TUFLOW Wiki</span></a><p>'
        if manual_link_:
            html = f'{html}<li><a href="{manual_link_}"><span style=" font-size:8pt;">Link to TUFLOW Manual</span></a><p>'
        html = f'{html}</ul>'
        return html


def empty_tooltip(empty_type: str) -> str:
    file = Path(os.path.realpath(__file__)).parent.parent / 'empty_tooltips' / f'{empty_type.lower()}.txt'
    if not file.exists():
        return ''
    tooltip = TooltipBuilder.from_file(file)
    return tooltip.html


class EmptyCreator:

    def __init__(self, project_folder: str, gpkg_export_type: str, gpkg_folder: str, kart_repo: str, overwrite: bool, feedback=None):
        self.proj_folder = Path(project_folder)
        self.overwrite = overwrite
        self.feedback = feedback
        self.using_empty_folder = False  # user has specified empty folder and not project folder

        self.hpc_empty_dir = self.proj_folder / 'model' / 'gis' / 'empty'
        self.fv_empty_dir = self.proj_folder / 'model' / 'gis' / 'empty'
        self._solver = ''

        if not self.hpc_empty_dir.exists() and not self.fv_empty_dir.exists() and unique_empty_names(self.proj_folder):
            self.using_empty_folder = True
            self.hpc_empty_dir = self.proj_folder
            self.fv_empty_dir = self.proj_folder
            empty_types = unique_empty_names(self.proj_folder)
            if len(empty_types) > 10:
                self._solver = 'hpc'
            else:
                self._solver = 'fv'

        # hpc
        self.hpc_gis_dir = self.hpc_empty_dir.parent
        self.hpc_gis_type = self.gis_type(self.hpc_empty_dir, 'gpkg')
        self.hpc_empty_types = unique_empty_names(self.hpc_empty_dir)

        # fv
        self.fv_gis_dir = self.fv_empty_dir.parent
        self.fv_gis_type = 'shp'
        self.fv_empty_types = unique_empty_names(self.hpc_empty_dir)

        # gpkg settings
        self.gpkg_export_type = gpkg_export_type
        self.gpkg_folder = Path(gpkg_folder)
        self.kart_repo = Path(kart_repo)

    def gis_type(self, folder: Path, default: str) -> str:
        if not folder.exists():
            return default
        gis_type = [x for x in folder.glob('*.*') if x.suffix.lower() in ['.shp', '.mif', '.gpkg']]
        if gis_type:
            return gis_type[0].suffix.lower()[1:]
        return default

    def solver(self, empty_type: str):
        if self._solver:
            return self._solver
        if empty_type in self.hpc_empty_types:
            return 'hpc'
        elif empty_type in self.fv_empty_types:
            return 'fv'
        return ''

    def geom_suffix(self, geom: str) -> str:
        if geom.lower() == 'point':
            return 'P'
        elif geom.lower() == 'line':
            return 'L'
        elif geom.lower() == 'region':
            return 'R'
        return ''

    def geom_to_uri(self, geom: str) -> str:
        d = {
            'Point': 'point',
            'Line': 'linestring',
            'Region': 'polygon'
        }
        return d.get(geom, '')

    def gis_ext(self, gis_type: str) -> str:
        return f'.{gis_type}'

    def gis_to_driver(self, gis_type: str) -> str:
        return get_driver_name_from_extension('vector', gis_type)

    def gis_driver(self, solver: str) -> str:
        if solver == 'hpc':
            return self.gis_to_driver(self.hpc_gis_type)
        elif solver == 'fv':
            return self.gis_to_driver(self.fv_gis_type)

    def action_on_existing(self, solver: str, out_db: str, out_name: str):
        if solver == 'hpc' and self.hpc_gis_type == 'gpkg':
            if Path(out_db).exists():
                if out_name.lower() in [x.lower() for x in GPKG(out_db).layers()] and not self.overwrite:
                    return
                else:
                    return QgsVectorFileWriter.CreateOrOverwriteLayer
        elif Path(out_db).exists() and not self.overwrite:
            return
        return QgsVectorFileWriter.CreateOrOverwriteFile

    def out_database_name(self, name: str, solver: str) -> str:
        if solver == 'fv':
            return str(self.fv_gis_dir / f'{name}{self.gis_ext(self.fv_gis_type)}')
        if self.hpc_gis_type == 'gpkg':
            if self.gpkg_export_type == 'Group Geometry Types':
                return str(self.hpc_gis_dir / f'{name[:-2]}{self.gis_ext(self.hpc_gis_type)}')
            elif self.gpkg_export_type == 'All to one':
                return str(self.gpkg_folder)
            elif self.gpkg_export_type == 'Kart Repo':
                temp_dir = tempfile.mkdtemp(prefix='import_empty')
                return str(Path(temp_dir) / 'temp.gpkg')
        return str(self.hpc_gis_dir / f'{name}{self.gis_ext(self.hpc_gis_type)}')

    def in_database_name(self, solver, empty_type, suffix):
        p = self.hpc_empty_dir if solver == 'hpc' else self.fv_empty_dir
        gis_type = self.hpc_gis_type if solver == 'hpc' else self.fv_gis_type
        if gis_type == 'gpkg':
            files = [x for x in p.glob(f'{empty_type}_empty{suffix}{self.gis_ext(gis_type)}')]
            if files:
                lyrs = [x for x in GPKG(files[0]).glob(f'{empty_type}_empty{suffix}_*')]
                if lyrs:
                    return f'{files[0]}|layername={lyrs[0]}'
        else:
            files = [x for x in p.glob(f'{empty_type}_empty{suffix}_*{self.gis_ext(gis_type)}')]
            if files:
                return str(files[0])
        return ''

    def actual_kart_folder(self):
        git = self.kart_repo / '.git'
        if git.exists():
            try:
                kart_dir = None
                with git.open() as f:
                    for line in f:
                        if 'gitdir' in line:
                            kart_dir = git.parent / line.split(':')[1].strip()
                if kart_dir and kart_dir.exists():
                    config = kart_dir / 'config'
                    with config.open() as f:
                        contents = f.read()
                    if re.findall(r'\[kart', contents):
                        return str(kart_dir)
            except Exception as e:
                return ''
        else:
            return ''

    @staticmethod
    def kart_executable():
        if os.name == "nt":
            defaultFolder = os.path.join(os.environ["PROGRAMFILES"], "Kart")
        elif sys.platform == "darwin":
            defaultFolder = "/Applications/Kart.app/Contents/MacOS/"
        else:
            defaultFolder = "/opt/kart"
        folder = defaultFolder
        for exe_name in ("kart.exe", "kart_cli_helper", "kart_cli", "kart"):
            path = os.path.join(folder, exe_name)
            if os.path.isfile(path):
                return path
        return path

    def kart_gpkg(self):
        kart_folder = self.actual_kart_folder()
        if not kart_folder:
            return
        config = Path(kart_folder) / 'config'
        if not config.exists():
            return
        with config.open() as f:
            contents = f.read()
        if '[kart "workingcopy"]' not in contents:
            return
        try:
            working_copy = re.split(r'\[kart "workingcopy"\]', contents)[1].split('[')[0]
            working_copy_settings = zip(working_copy.split('=')[::2], working_copy.split('=')[1::2])
            for param, value in working_copy_settings:
                if param.strip() == 'location':
                    gpkg = self.kart_repo / value.strip()
                    return str(os.path.abspath(gpkg))
        except Exception as e:
            return

    def create_empty(self, empty_type: str, geom: str, run_id: str) -> tuple[str | None, str | None]:
        solver = self.solver(empty_type)
        if self.feedback:
            self.feedback.pushInfo(f'Solver: {solver}')
        suffix = '_pts' if '_pts' in empty_type else ''
        empty_type = empty_type.split('_pts')[0]

        # input stuff
        in_db = self.in_database_name(solver, empty_type, suffix)
        if self.feedback:
            self.feedback.pushInfo(f'Template file: {in_db}')
        in_name = 'empty_input'
        in_lyr = QgsVectorLayer(in_db, in_name, 'ogr')
        if not in_lyr.isValid():
            raise Exception(f'Could not import empty file. Could not load layer for {empty_type}')
        if self.feedback:
            self.feedback.pushInfo('Successfully Loaded layer')

        # output stuff
        out_name = f'{empty_type}_{run_id}{suffix}_{self.geom_suffix(geom)}'
        out_db = self.out_database_name(out_name, solver)
        if self.feedback:
            self.feedback.pushInfo(f'Output file: {out_db}')
            self.feedback.pushInfo(f'Output layer: {out_name}')
        out_lyr = QgsVectorLayer(f'{self.geom_to_uri(geom)}?crs={in_lyr.crs().authid()}', out_name, 'memory')
        if not out_lyr.isValid():
            raise Exception('Could not initialise output layer')
        out_lyr.setProviderEncoding('UTF-8')
        for field in in_lyr.fields():
            self.feedback.pushInfo(f'Adding field: {field.name()}')
        out_lyr.dataProvider().addAttributes(in_lyr.fields())
        out_lyr.updateFields()
        self.feedback.pushInfo('\nOutput layer fields:')
        for field in out_lyr.fields():
            self.feedback.pushInfo(f'Field:  {field.name()}')

        # write to disk
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = self.gis_driver(solver)
        options.layerName = out_name
        options.fileEncoding = 'UTF-8'
        action_on_existing_ = self.action_on_existing(solver, out_db, out_name)
        if action_on_existing_ is None:  # exists and not overwrite
            return None, None
        options.actionOnExistingFile = action_on_existing_

        self.feedback.pushInfo(f'Using encoding: {options.fileEncoding}')
        ret = QgsVectorFileWriter.writeAsVectorFormatV3(out_lyr, out_db, QgsCoordinateTransformContext(), options)
        if ret[0] != QgsVectorFileWriter.NoError:
            raise Exception(ret[1])

        if self.gpkg_export_type == 'Kart Repo':
            kart_exe = self.kart_executable()
            wkdir = self.actual_kart_folder()
            proc = subprocess.run([kart_exe, 'import', '{0}'.format(out_db), out_name], cwd=wkdir,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(out_db).unlink()
            shutil.rmtree(Path(out_db).parent, ignore_errors=True)
            if proc.returncode != 0:
                raise Exception(proc.stderr.decode('utf-8', errors='ignore'))

            uri = '{0}|layername={1}'.format(self.kart_gpkg(), out_name)
            return uri, out_name

        if options.driverName == 'GPKG':
            uri = f'{out_db}|layername={out_name}'
        else:
            uri = out_db

        return uri, out_name