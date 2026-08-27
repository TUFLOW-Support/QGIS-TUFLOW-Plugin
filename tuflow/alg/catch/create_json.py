import typing
from collections import OrderedDict
from pathlib import Path
from dataclasses import dataclass, field
import numpy as np
import numpy.typing as npt
from netCDF4 import Dataset
import re
import subprocess
import tempfile
import shutil
import json
import os
import errno
import stat
from datetime import datetime, timedelta

from qgis.PyQt.QtCore import QCoreApplication, QSettings
from qgis.core import (QgsProcessingAlgorithm, QgsProcessingParameterFile, QgsProcessingParameterFileDestination,
                       QgsProcessingContext, QgsProcessingFeedback, QgsProcessingParameterMultipleLayers,
                       QgsProcessing, QgsProcessingMultiStepFeedback)
from qgis.utils import plugin_paths


from tuflow.gui.alg.custom_multi_file_select import CustomMultiFileSelectParameter
from tuflow.gui.alg.custom_output_file_dest import CustomOutputFileDestination


class CreateJson(QgsProcessingAlgorithm):
    """Processing algorithm to convert XMDF and NC results from TUFLOW and TUFLOW FV into a TUFLOW Catch JSON file."""

    # uncomment to remote debug
    # def flags(self):
    #     return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def initAlgorithm(self, configuration: typing.Dict[str, typing.Any] = ...) -> None:
        """Initialise the algorithm dialog's inputs/outputs."""
        # input results
        self.addParameter(
            CustomMultiFileSelectParameter('INPUTS', 'Results', dirSettingsKey='/tuflow_catch/create_json_input_folder')
        )

        # output location
        # param = QgsProcessingParameterFileDestination('OUTPUT', 'Output File', 'JSON (*.json)')
        param = CustomOutputFileDestination('OUTPUT', 'Output File', fileFilter='JSON (*.json)')
        self.addParameter(param)

        # res_to_res.exe
        res_to_res_exe = plugin_paths[0] + '/tuflow/_utilities/res_to_res/res_to_res_w64.exe'
        if not os.path.exists(res_to_res_exe):
            res_to_res_exe = None
        self.addParameter(
            QgsProcessingParameterFile('res_to_res_exe', 'res_to_res.exe', defaultValue=res_to_res_exe)
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        """Algorithm execution."""
        feedback = QgsProcessingMultiStepFeedback(0, model_feedback)
        # check inputs
        feedback.setCurrentStep(0)
        feedback.pushInfo('Checking inputs...')
        if not parameters['INPUTS']:
            feedback.reportError('No input file(s) specified.')
            return {}
        nc_mesh_info = None
        for fpath in parameters['INPUTS']:
            if Path(fpath).suffix.upper() == '.NC':
                nc_mesh_info = NetCDFMeshInfo(fpath, 0)
        use_index = len(parameters['INPUTS']) > 1 and nc_mesh_info

        # output location
        feedback.pushInfo('\nCollecting output information...')
        out_json_fpath = parameters['OUTPUT']
        p = Path(out_json_fpath)
        if os.path.splitext(p.stem)[1].lower() != '.tuflow':
            out_json_fpath = p.parent / f'{p.stem}.tuflow{p.suffix}'
        outputs = []
        if use_index:
            if '.tuflow.json' in p.name:
                index_nc_fpath = str(Path(out_json_fpath).parent / f'{Path(p.stem).stem}_index.nc')
            else:
                index_nc_fpath = str(Path(out_json_fpath).parent / f'{p.stem}_index.nc')
            feedback.pushInfo(f'Using {Path(index_nc_fpath).name} file...')
            outputs.append(index_nc_fpath)
            index = Path(index_nc_fpath).stem
        else:
            index = Path(parameters['INPUTS'][0]).stem
        out_name = Path(Path(out_json_fpath).stem).stem

        # load result info classes
        result_classes = []
        for fpath in parameters['INPUTS']:
            res_info = ResultInfo(fpath, parameters['res_to_res_exe'])
            res_info.load(feedback)
            if not res_info.driver:
                feedback.reportError(f'Failed to load result: {fpath}')
                return {}
            outputs.append(fpath)
            result_classes.append(res_info)

        # output result types
        sed_types = OrderedDict({})
        if use_index:
            feedback.pushInfo('\nAligning sediment types between results...')
            for res_info in result_classes:
                if res_info.type == 'netcdf mesh':
                    for sed_name in res_info.sediment_output_names():
                        if sed_name not in sed_types:
                            sed_types[sed_name] = None
                else:
                    for i, sed_name in enumerate(res_info.sediment_output_names()):
                        if len(list(sed_types.keys())) > i:
                            sed_types[list(sed_types.keys())[i]] = sed_name
            for old_name, new_name in sed_types.copy().items():
                if new_name is None:
                    del sed_types[old_name]
                    continue
                feedback.pushInfo(f'\t{old_name} -> {new_name}')
        gw_ad_types = OrderedDict({})
        if [res_info for res_info in result_classes if res_info.type == 'xmdf']:
            feedback.pushInfo('\nAssigning ground water concentration names')
            gw_names, conc_names = [], []
            for res_info in result_classes:
                if res_info.type == 'xmdf':
                    gw_names.extend(list(res_info.ground_water_output_names()))
                    conc_names.extend(list(res_info.ad_names()))
            # conc_names = [x for x in conc_names if not [y.lower() for y in tcc.infil_off if y.lower() in x.lower()]]
            for i, gw_name in enumerate(gw_names):
                if len(conc_names) > i:
                    ilyr = re.findall(r'Layer\s+\d+', gw_name)
                    if not ilyr:
                        continue
                    ilyr = int(re.findall(r'\d+', ilyr[0])[0])
                    gw_ad_types[gw_name] = f'GW {conc_names[i]} Layer {ilyr}'
            for old_name, new_name in gw_ad_types.items():
                feedback.pushInfo(f'\t{old_name} -> {new_name}')
            feedback.pushInfo('\nRemoving GW pollutant outputs [temporary solution]...')
            for gw_i, gw_name in gw_ad_types.copy().items():
                feedback.pushInfo(f'\t{gw_name} -> "none"')
                gw_ad_types[gw_i] = 'none'

        dynamic_types = sed_types.copy()
        dynamic_types.update(gw_ad_types)
        out_result_types = []
        for res_info in result_classes:
            if use_index:
                out_result_types = result_type_keys(out_result_types, res_info.driver, dynamic_types)
            else:
                out_result_types = list(res_info.result_types())

        feedback.pushInfo('\nOutput Results')
        for res_type in out_result_types:
            feedback.pushInfo(f'\t{res_type}')

        start_time_str = 'hours since 1990-01-01 00:00'
        start_time = datetime(1990, 1, 1)
        for res_info in result_classes:
            if res_info.has_reference_time():
                start_time_str = res_info.start_time_str()
                _, _, start_time = parse_reference_time(start_time_str)
                break

        # loop through and check for xmdf files and correct reference time
        for res_info in result_classes:
            if res_info.type == 'xmdf':
                if res_info.times(None):
                    t = res_info.times(None)[0]  # first time
                    start_time -= timedelta(hours=t)
                    start_time_str = start_time_string(start_time, 'h')

        times = []
        for res_info in result_classes:
            for time in res_info.times(start_time):
                if time not in times:
                    times.append(time)
        times = sorted(times)
        feedback.pushInfo(f'\nOutput Times: [reference time: {start_time_str}]')
        for time in times:
            feedback.pushInfo(f'\t{time}')

        index_info = None
        if use_index:
            index_info = ResultInfo(index_nc_fpath, None)
            index_info.load_index(out_result_types, start_time_str)
            result_classes.insert(0, index_info)

        timestep = None
        for res_info in result_classes:
            ts = res_info.timestep()
            if ts is not None:
                if timestep is None:
                    timestep = ts
                else:
                    timestep = min(timestep, ts)

        # create json
        feedback.pushInfo('Creating JSON file...')
        feedback.pushInfo(f'JSON file: {out_json_fpath}')
        out_data = {
            'version': 0.1,
            'name': out_name,
            'units': 'metric',
            'outputs': [Path(x).stem for x in outputs],
            'index': index,
            'result types': out_result_types,
            'time units': start_time_str,
            'timestep': timestep,
            'output data': {
                x.name(): x.output_data(use_index, index_info, out_json_fpath, dynamic_types) for x in result_classes
            }
        }
        out_json = json.dumps(out_data, indent=2)
        with open(out_json_fpath, 'w') as f:
            f.write(out_json)

        if use_index:
            feedback.pushInfo(f'Creating {Path(index_nc_fpath).name} file...')
            feedback.pushInfo(f'{Path(index_nc_fpath).name}: {index_nc_fpath}')
            with Dataset(index_nc_fpath, 'w') as nc:
                # global attributes
                nc.setncatts({'Origin': 'Created by TUFLOW Catch', 'Type': 'Index NetCDF Mesh'})

                # dimensions
                nc.createDimension('NumCells2D', 1)
                nc.createDimension('NumCells3D', 1)
                nc.createDimension('NumVert2D', nc_mesh_info.cell_nvert)
                nc.createDimension('NumVert3D', nc_mesh_info.cell_nvert)
                nc.createDimension('MaxNumCellVert', nc_mesh_info.cell_nvert)
                nc.createDimension('NumLayerFaces3D', 0)
                nc.createDimension('NumSedFrac', 1)
                nc.createDimension('Time', None)

                # variables
                var = nc.createVariable('ResTime', 'f8', ('Time'), compression='zlib')
                time_units = start_time_str
                var.setncatts({'long_name': 'output time', 'units': time_units})
                var[:] = np.array(times, dtype='f8')

                var = nc.createVariable('cell_Nvert', 'i4', ('NumCells2D'), compression='zlib')
                var.setncatts({'long_name': 'Cell number of vertices'})
                var[:] = nc_mesh_info.cell_nvert

                var = nc.createVariable('cell_node', 'i4', ('NumCells2D', 'MaxNumCellVert'), compression='zlib')
                var.setncatts({'long_name': 'Cell node connectivity'})
                var[:] = nc_mesh_info.cell_node

                var = nc.createVariable('NL', 'i4', ('NumCells2D'), compression='zlib')
                var.setncatts({'long_name': 'Number of layers in profile'})
                var[:] = 1

                var = nc.createVariable('idx2', 'i4', ('NumCells3D'), compression='zlib')
                var.setncatts({'long_name': 'Index from 3D to 2D arrays'})
                var[:] = 0

                var = nc.createVariable('idx3', 'i4', ('NumCells2D'), compression='zlib')
                var.setncatts({'long_name': 'Index from 2D to 3D arrays'})
                var[:] = 0

                var = nc.createVariable('cell_X', 'f8', ('NumCells2D'), compression='zlib')
                var.setncatts({'long_name': 'Cell Centroid X-Coordinate', 'units': 'm'})
                var[:] = nc_mesh_info.cell_x

                var = nc.createVariable('cell_Y', 'f8', ('NumCells2D'), compression='zlib')
                var.setncatts({'long_name': 'Cell Centroid Y-Coordinate', 'units': 'm'})
                var[:] = nc_mesh_info.cell_y

                var = nc.createVariable('cell_Zb', 'f4', ('NumCells2D'), compression='zlib')
                var.setncatts({'long_name': 'Cell Bed Elevation', 'units': 'm'})
                var[:] = nc_mesh_info.cell_zb

                var = nc.createVariable('cell_A', 'f4', ('NumCells2D'), compression='zlib')
                var.setncatts({'long_name': 'Cell Area', 'units': 'm'})
                var[:] = nc_mesh_info.cell_a

                var = nc.createVariable('node_X', 'f4', ('NumVert2D'), compression='zlib')
                var.setncatts({'long_name': 'Node X-Coordinate', 'units': 'm'})
                var[:] = nc_mesh_info.node_x

                var = nc.createVariable('node_Y', 'f4', ('NumVert2D'), compression='zlib')
                var.setncatts({'long_name': 'Node Y-Coordinate', 'units': 'm'})
                var[:] = nc_mesh_info.node_y

                var = nc.createVariable('node_Zb', 'f4', ('NumVert2D'), compression='zlib')
                var.setncatts({'long_name': 'Node Bed Elevation', 'units': 'm'})
                var[:] = nc_mesh_info.node_zb

                var = nc.createVariable('layerface_Z', 'f4', ('Time', 'NumLayerFaces3D'), compression='zlib')
                var.setncatts({'long_name': 'Layer Face Z-Coordinates', 'units': 'm'})
                var[:] = 0

                var = nc.createVariable('stat', 'i4', ('Time', 'NumCells2D'), compression='zlib')
                var.setncatts({'long_name': 'Cell wet/dry status', 'units': 'boolean'})
                var[:] = 0

                for res_type in out_result_types:
                    if res_type.lower() == 'bed elevation':
                        continue
                    static = False
                    dims = ('NumCells2D') if static else ('Time', 'NumCells2D')
                    if 'velocity' in res_type.lower():
                        if static:
                            continue
                        res_type = 'V Maximum' if static else 'V'
                        var = nc.createVariable(f'{res_type}_x', 'f4', dims, compression='zlib')
                        var.setncatts({'long_name': 'x_velocity'})
                        var[:] = 0
                        var = nc.createVariable(f'{res_type}_y', 'f4', dims, compression='zlib')
                        var.setncatts({'long_name': 'y_velocity'})
                        var[:] = 0
                    else:
                        var = nc.createVariable(res_type, 'f4', dims, compression='zlib')
                        var.setncatts({'long_name': res_type})
                        var[:] = 0

        return {'OUTPUT': str(out_json_fpath)}

    def name(self):
        return 'Create TUFLOW CATCH JSON'

    def displayName(self):
        return self.tr(self.name())

    def createInstance(self):
        return CreateJson()

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def checkParameterValues(self, parameters, p_str=None, Any=None, *args, **kwargs):
        return True, ''


class TuflowCatchControl:

    def __init__(self, fpath: str):
        self.fpath = Path(fpath)
        self.infil_off = []
        self.load(self.fpath)

    def load(self, fpath: Path):
        regex_in = re.compile(r'catchment\s+pollutant\s+export\s+model\s+==', re.IGNORECASE)
        regex_out = re.compile(r'end\s+catchment\s+pollutant\s+export\s+model', re.IGNORECASE)
        regex_infil = re.compile(r'infiltration.*==\s+off', re.IGNORECASE)
        regex_extract = re.compile(r'(?<=infiltration).*(?===\s+off)', re.IGNORECASE)
        with fpath.open() as fo:
            in_pollutant_block = False
            for line in fo:
                cmd = re.split(r'[!#]', line, maxsplit=1)
                if len(cmd) == 2 and not cmd[0].strip():
                    continue
                cmd = cmd[0].strip()
                if not in_pollutant_block and regex_in.findall(cmd):
                    in_pollutant_block = True
                    continue
                elif in_pollutant_block and regex_out.findall(cmd):
                    in_pollutant_block = False
                    break
                if not in_pollutant_block:
                    continue
                if regex_infil.findall(cmd):
                    name = regex_extract.findall(cmd)[0].strip()
                    if name not in self.infil_off:
                        self.infil_off.append(name)



class ResultInfo:

    def __init__(self, fpath: str, res_to_res_exe: str):
        self.fpath = fpath
        self.path = Path(fpath)
        self.res_to_res_exe = res_to_res_exe
        self.driver = None
        self.type = None
        if self.fpath.endswith('_index.nc'):
            self.type = 'index'
        elif self.path.suffix.upper() == '.XMDF':
            self.type = 'xmdf'
        elif self.path.suffix.upper() == '.NC':
            self.type = 'netcdf mesh'

    def load(self, feedback):
        if self.type == 'xmdf':
            feedback.pushInfo(f'Reading XMDF file: {self.fpath}')
            if not os.path.exists(self.res_to_res_exe):
                raise AssertionError('res_to_res.exe does not exist, please use the TUFLOW plugin to download it.')
            out_txt = res_to_res_runner(self.res_to_res_exe, self.fpath)
            self.driver = XMDF_Header_Info(out_txt)
        elif self.type == 'netcdf mesh':
            feedback.pushInfo(f'Reading NetCDF file: {self.fpath}')
            self.driver = NetCDFMeshInfo(self.fpath, 0)

    def name(self):
        if self.driver:
            return self.path.stem
        return ''

    def load_index(self, result_types, reference_time):
        self.driver = IndexResult(result_types, reference_time)

    def result_types(self):
        if self.driver:
            return self.driver.result_types()
        return []

    def ad_names(self):
        if self.driver:
            for ad_name in self.driver.ad_names():
                yield ad_name

    def sediment_output_names(self):
        if self.driver:
            for sed_name in self.driver.sediment_output_names():
                yield sed_name

    def ground_water_output_names(self):
        if self.driver:
            for gw_name in self.driver.ground_water_output_names():
                yield gw_name

    def ground_water_ad_output_names(self):
        for gw_name in self.ground_water_output_names():
            if re.findall(r'AD\d{2}', gw_name):
                yield gw_name

    def has_reference_time(self):
        if self.driver:
            return self.driver.has_reference_time
        return False

    def start_time_str(self):
        if self.driver and hasattr(self.driver, 'start_time_str'):
            return self.driver.start_time_str
        return 'hours'

    def timestep(self):
        if self.driver:
            return self.driver.timestep

    def times(self, reference_time):
        if self.type == 'index':
            return []
        if self.driver:
            if self.driver.has_reference_time:
                if self.driver.units == 'h':
                    return [(self.driver.reference_time + timedelta(hours=t) - reference_time).total_seconds() / 3600 for t in self.driver.times()]
                elif self.driver.units == 's':
                    return [(self.driver.reference_time + timedelta(seconds=t) - reference_time).total_seconds() for t in self.driver.times()]
            else:
                return self.driver.times()
        return []

    def output_data(self, use_index, index, json_fpath, dynamic_types):
        if self.type == 'xmdf':
            _2dm = os.path.relpath(self.path.with_suffix('.2dm'), Path(json_fpath).parent)
        else:
            _2dm = None
        if self.type == 'index':
            relpath = os.path.relpath(self.fpath, Path(json_fpath).parent)
            result_type_map = {x: x for x in self.result_types()}
        elif self.type == 'netcdf mesh':
            relpath = os.path.relpath(self.fpath, Path(json_fpath).parent)
            nc_result_types = self.result_types()
            if use_index:
                result_type_map = {restype2restype(x, dynamic_types): x for x in self.result_types() if restype2restype(x, dynamic_types) in index.result_types() and restype2restype(x, dynamic_types) != 'none'}
            else:
                result_type_map = {x: x for x in self.result_types()}
        else:
            relpath = os.path.relpath(self.fpath, Path(json_fpath).parent)
            if use_index:
                result_type_map = {restype2restype(x, dynamic_types): x for x in self.result_types() if
                                   restype2restype(x, dynamic_types) in index.result_types() and x != 'Velocity' and x != 'Velocity/Maximums' and restype2restype(x, dynamic_types) != 'none'}
            else:
                result_type_map = {x: x for x in self.result_types()}

        if use_index:
            for res_type in index.result_types():
                if res_type not in result_type_map:
                    result_type_map[res_type] = 'none'

        output_data = {
            'format': 'netcdf mesh' if self.type == 'index' else self.type,
            'path': relpath,
            'result type map': result_type_map
        }
        if _2dm:
            output_data['2dm'] = _2dm
        return output_data


def start_time_string(start_time: datetime, units: str) -> str:
    if units[0].lower() == 'h':
        rt_string = start_time.strftime('%Y-%m-%d %H:%M:%S')
        start_time_str = f'hours since {rt_string}'
    elif units[0].lower() == 's':
        rt_string = start_time.strftime('%Y-%m-%d %H:%M:%S')
        start_time_str = f'seconds since {rt_string}'
    else:
        start_time_str = 'hours'
    return start_time_str


class IndexResult:

    def __init__(self, result_types, reference_time):
        self._result_types = result_types
        self._reference_time = reference_time
        self.has_reference_time = True
        self.timestep = None

    def result_types(self):
        return self._result_types


@dataclass
class NetCDFMeshInfo:
    """
    Class for storing some TUFLOW FV mesh data and results.
    Mesh element at index is recorded and result types.
    """
    filepath: str
    index: int
    cell_x: float = field(init=False)
    cell_y: float = field(init=False)
    cell_nvert: int = field(init=False)
    cell_node: npt.NDArray[int] = field(init=False)
    cell_zb: float = field(init=False)
    cell_a: float = field(init=False)
    node_x: npt.NDArray[float] = field(init=False)
    node_y: npt.NDArray[float] = field(init=False)
    node_zb: npt.NDArray[float] = field(init=False)
    _times: list[float] = field(init=False)
    reference_time: datetime = field(init=False)
    has_reference_time: bool = field(init=False)
    units: str = field(init=False)
    start_time: datetime = field(init=False)
    start_time_str: str = field(init=False)
    _result_types: list = field(init=False, default=())
    timestep: float = field(init=False, default=None)

    def __post_init__(self):
        with Dataset(self.filepath) as nc:
            self.cell_x = float(nc['cell_X'][self.index])
            self.cell_y = float(nc['cell_Y'][self.index])
            self.cell_nvert = int(nc['cell_Nvert'][self.index])
            self.cell_node = nc['cell_node'][self.index, 0:self.cell_nvert]
            self.cell_zb = float(nc['cell_Zb'][self.index])
            self.cell_a = float(nc['cell_A'][self.index])
            self.node_x = nc['node_X'][self.cell_node - 1]
            self.node_y = nc['node_Y'][self.cell_node - 1]
            self.node_zb = nc['node_Zb'][self.cell_node - 1]
            self._times = nc['ResTime'][:].tolist()
            rt_str = nc['ResTime'].units
            self.has_reference_time, self.units, self.reference_time = parse_reference_time(rt_str)
            if self.units == 'h':
                self.start_time = self.reference_time + timedelta(hours=self._times[0])
                rt_string = self.start_time.strftime('%Y-%m-%d %H:%M:%S')
                self.start_time_str = f'hours since {rt_string}'
            elif self.units == 's':
                self.start_time = self.reference_time + timedelta(seconds=self._times[0])
                rt_string = self.start_time.strftime('%Y-%m-%d %H:%M:%S')
                self.start_time_str = f'seconds since {rt_string}'
            else:
                self.start_time = self.reference_time
                self.start_time_str = 'hours'

            if len(self._times) > 1:
                self.timestep = self._times[-1] - self._times[-2]
                self._times.append(self._times[-1] + self.timestep)
            self._result_types = []
            for var_name, var in nc.variables.items():
                if var_name in ['ResTime', 'cell_Nvert', 'cell_node', 'NL', 'idx2', 'idx3', 'cell_X',
                                'cell_Y', 'cell_Zb', 'cell_A', 'node_X', 'node_Y', 'node_Zb', 'layerface_Z',
                                'stat']:
                    continue
                if hasattr(var, 'long_name'):
                    self._result_types.append(var.long_name)

    def times(self):
        return self._times

    def result_types(self):
        result_types = ['Bed Elevation']
        result_types.extend(self._result_types)
        if 'x_velocity' in result_types and 'y_velocity' in result_types:
            i = result_types.index('x_velocity')
            result_types.remove('x_velocity')
            result_types.remove('y_velocity')
            result_types.insert(i, 'Velocity')
        return result_types

    def ad_names(self):
        for res_type in self.result_types():
            if re.findall('^WQ_', res_type):
                yield res_type

    def sediment_output_names(self):
        for res_type in self.result_types():
            if 'sediment fraction' in res_type.lower():
                yield res_type

    def ground_water_output_names(self):
        pass


class XMDF_Res_Type:

    def __init__(self, folder, name, is_vector, scalar_count, vector_count):
        self._is_vector = is_vector
        self._key = 'v{0}'.format(vector_count) if is_vector else 's{0}'.format(scalar_count)
        self._folder = folder
        self._name = name
        self._times = []

    def __str__(self):
        return self._name

    @property
    def timestep(self):
        if len(self._times) > 1:
            return self._times[-1] - self._times[-2]

    def add_times(self, times):
        for time in times:
            if time not in self._times:
                self._times.append(time)
        self._times = sorted(self._times)

    def times(self):
        return self._times[:]

    def name(self):
        return self._name

    def folder(self):
        return self._folder

    def key(self):
        return self._key


class XMDF_Header_Info:

    def __init__(self, header_text_dump):
        self._header_text_dump = header_text_dump
        self._vector_dataset_count = 0
        self._scalar_dataset_count = 0
        self._res_types = []
        self._loaded = False
        self.has_reference_time = False

        si, vi = 0, 0
        scalar, vector = False, False
        res_type = None
        line_count = 0
        line_index = 0
        times = []
        for line in header_text_dump.split('\n'):
            if vector and self._vector_dataset_count > 0 and vi == self._vector_dataset_count:
                vector = False
            if scalar and self._scalar_dataset_count > 0 and si == self._scalar_dataset_count:
                scalar = False

            if 'Vector Datasets' in line:
                vector = True
                scalar = False
            elif 'Scalar Datasets' in line:
                scalar = True
                vector = False

            elif 'Number Datasets:' in line:
                n = re.findall(r'\d+', line)
                if n:
                    if vector:
                        self._vector_dataset_count = int(n[0])
                    elif scalar:
                        self._scalar_dataset_count = int(n[0])
            elif re.findall(r'\w+/\w+/\w+(\s\w+)?', line):
                if scalar:
                    si += 1
                elif vector:
                    vi += 1
                else:
                    continue
                folder, name = line.split('/')[-2:]
                # if 'Vector' in name:
                #     name = re.sub(r'\s*vector\s+', '', name, flags=re.IGNORECASE)
                res_type = XMDF_Res_Type(folder, name, vector, si, vi)
                self._res_types.append(res_type)

            elif 'Num Times' in line:
                line_count = int(re.findall(r'\d+', line)[0])

            elif line_count != 0 and res_type is not None and line_index != line_count:
                line_index += 1
                try:
                    time = float(line)
                except ValueError:
                    return
                times.append(time)
                if line_index == line_count:
                    res_type.add_times(times)
                    res_type = None
                    line_count = 0
                    line_index = 0
                    times = []

        self._loaded = (bool(self._vector_dataset_count) or bool(self._scalar_dataset_count)) and bool(self._res_types)

    def __contains__(self, item):
        if isinstance(item, str):
            return item.lower() in [x.name().lower() for x in self._res_types]
        elif isinstance(item, XMDF_Res_Type):
            return item.name().lower() in [x.name().lower() for x in self._res_types]
        else:
            return False

    def __getitem__(self, item):
        if isinstance(item, tuple) and len(item) == 2:
            item1, item2 = item
            if isinstance(item1, str) and isinstance(item2, str):
                if item2 == 'Max':
                    a = [x for x in self._res_types if
                         x.name() == item1 and x.folder() in ['Maximums', 'Final', 'Times']]
                    if a:
                        return a[0].key(), str(a[0].times()[0])
                elif item2 == 'Min':
                    a = [x for x in self._res_types if x.name() == item1 and x.folder() == 'Minimums']
                    if a:
                        return a[0].key(), str(a[0].times()[0])
                else:
                    a = [x for x in self._res_types if x.name() == item1]
                    if a:
                        for t in a[0].times():
                            if abs(t - float(item2)) < 0.001:
                                return a[0].key(), t
                            else:
                                return a[0].key(), None
        else:
            return [x for x in self._res_types if x.name() == item][0]

    def result_types(self):
        yield 'Bed Elevation'
        for x in self._res_types:
            if self.has_additional_static(x):
                yield f'{x}/{x.folder()}'
        for x in self._res_types:
            if not self.has_additional_static(x):
                yield x.name()

    def ad_names(self):
        for res_type in self.result_types():
            if re.findall(r'^Conc (WQ|SED)', res_type):
                yield res_type

    def sediment_output_names(self):
        for res_type in self.result_types():
            if 'conc sed_' in res_type.lower():
                yield res_type

    def ground_water_output_names(self):
        for res_type in self.result_types():
            if re.findall(r'^GW\s', res_type):
                yield res_type

    def loaded(self):
        return self._loaded

    @property
    def timestep(self):
        if len(self.times()) > 1:
            return self.times()[-1] - self.times()[-2]

    def times(self, res_type=None):
        if not res_type:
            return sorted(list(set(sum([x.times() for x in self._res_types], []))))
        else:
            return sorted(list(set(sum([x.times() for x in self._res_types if x.name() == res_type], []))))

    def has_additional_static(self, res_type):
        return res_type.folder() == 'Maximums' or res_type.folder() == 'Final' or res_type.folder() == 'Minimums'


def handleRemoveReadonly(func, path, exc):
    excvalue = exc[1]
    if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise


def res_to_res_runner(res_to_res_fpath: str, xmdf_fpath: str) -> str:
    tmploc = tempfile.mkdtemp(prefix='res_to_res_runner')
    xnfo_fpath = os.path.join(tmploc, 'info.txt')
    args = [res_to_res_fpath, '-xnfo', xmdf_fpath, '-out', xnfo_fpath]
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,  # nosec B603
                              input='\n', encoding='utf-8', timeout=10,
                              creationflags=subprocess.CREATE_NO_WINDOW)
        with open(xnfo_fpath, 'r') as f:
            txt = f.read()
    except Exception as e:
        txt = e.decode('utf-8')
    finally:
        shutil.rmtree(tmploc, ignore_errors=False, onerror=handleRemoveReadonly)
    return txt


def restype2restype(res_type: str, dynamic_types: dict) -> str:
    mapper = {
        'water surface elevation': 'Water Level',
        'water depth': 'Depth',
        'Vector Velocity': 'Velocity',
        'Vector Velocity/Maximums': 'Velocity/Maximums'
    }
    if dynamic_types:
        mapper.update(dynamic_types)
    if res_type in mapper:
        return_res_type = mapper[res_type]
    elif re.findall(r'^WQ_', res_type):
        return_res_type = f'Conc {res_type}'
    else:
        return_res_type = res_type
    if '/' in return_res_type:
        return_res_type = '{0} {1}'.format(*return_res_type.split('/', 1))
    return return_res_type


def result_type_keys(result_types: list[str], input: typing.Union[NetCDFMeshInfo, XMDF_Header_Info], dynamic_types: dict) -> list[str]:
    result_types_ = []
    result_types_l = [x.lower() for x in result_types]
    if isinstance(input, NetCDFMeshInfo):
        result_types_ = [restype2restype(x, dynamic_types) for x in input.result_types() if restype2restype(x, dynamic_types) != 'none']
    elif isinstance(input, XMDF_Header_Info):
        result_types_ = [restype2restype(x, dynamic_types) for x in input.result_types() if
                     x != 'Velocity/Maximums' and x != 'Vector Velocity/Maximums' and restype2restype(x, dynamic_types) != 'none']
    for res_type in result_types_:
        if res_type.lower() not in result_types_l:
            result_types.append(res_type)
            result_types_l.append(res_type.lower())
    return result_types


# def output_data(fpath, result_types, nc_mesh_info, xmdf_header, json_fpath, use_index):
#     format = 'netcdf mesh' if Path(fpath).suffix.lower() == '.nc' else 'xmdf'
#     path = os.path.relpath(fpath, Path(json_fpath).parent)
#     if format == 'xmdf':
#         _2dm = Path(fpath).with_suffix('.2dm').name
#     else:
#         _2dm = None
#     if Path(fpath).name == 'index.nc':
#         result_type_map = {x: x for x in result_types}
#     elif format == 'netcdf mesh':
#         nc_result_types = nc_mesh_info.result_types
#         if use_index:
#             result_type_map = {restype2restype(x): x for x in nc_result_types if restype2restype(x) in result_types}
#         else:
#             result_type_map = {x: x for x in nc_result_types}
#     else:
#         if use_index:
#             result_type_map = {restype2restype(x): x for x in xmdf_header.result_types() if
#                                restype2restype(x) in result_types and x != 'Velocity' and x != 'Velocity/Maximums'}
#             # if 'Velocity' not in result_type_map and 'Vector Velocity' in list(xmdf_header.result_types()):
#             #     xmdf_header['Velocity'] = 'Vector Velocity'
#         else:
#             result_type_map = {x: x for x in xmdf_header.result_types()}
#     for res_type in result_types:
#         if res_type not in result_type_map:
#             result_type_map[res_type] = 'none'
#     output_data = {
#         'format': format,
#         'path': path,
#         'result type map': result_type_map
#     }
#     if _2dm:
#         output_data['2dm'] = _2dm
#     return output_data

def parse_reference_time(string):
    if 'hour' in string:
        units = 'h'
    elif 'second' in string:
        units = 's'
    else:
        units = string.split(' ')[0]

    if re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', string):
        return True, units, datetime.strptime(re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', string)[0], '%Y-%m-%d %H:%M:%S')
    elif re.findall(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', string):
        return True, units, datetime.strptime(re.findall(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', string)[0], '%Y-%m-%dT%H:%M:%S')

    return False, units, datetime(1990, 1, 1)  # a default value
