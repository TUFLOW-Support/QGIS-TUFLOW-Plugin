import re
import typing
from copy import deepcopy
from pathlib import Path

import numpy as np
try:
    import pandas as pd
except ImportError:
    from ...pt.pytuflow._outputs.pymesh.stubs import pandas as pd
from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsVectorLayer

from .time_series_mixin import TimeSeriesMixin

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import BCTablesCheck as BCTablesCheckBase, TuflowPath
else:
    from tuflow.pt.pytuflow import BCTablesCheck as BCTablesCheckBase, TuflowPath

if typing.TYPE_CHECKING:
    from ..widgets.tv_plot_widget.plotsourceitem import PlotSourceItem

import logging
logger = logging.getLogger('tuflow_viewer')


BC_2D_REGEX = re.compile(r'(_bcc_check(?:_R)?|_sac_check(?:_R)?)')
BC_1D_REGEX = re.compile(r'(_1d_bc_check(?:_P)?)')


class BCTablesCheck(BCTablesCheckBase, TimeSeriesMixin):
    DRIVER_NAME = 'BC Tables Check'
    LAYER_TYPE = 'BCTable'
    AUTO_LOAD_METHOD = 'OnOpened'

    def __init__(self, fpath: str, layers: list[QgsVectorLayer] = ()):
        fpath = TuflowPath(fpath)  # origin fpath
        self.fpath = self.bc_tables_csv_from_gis_file(fpath)
        if self.fpath is None:
            self.fpath = fpath
        self.domain = ''

        super().__init__(self.fpath)
        self._init_viewer_output_mixin(self.name)
        self._map_layers = list(layers)
        self.init_temporal_properties()
        self._init_styling(self._map_layers, self._lyr2resultstyle)

        self._data_types = []
        self._loaded = False
        self._soft_load()

    def close(self):
        self._teardown_viewer_output_mixin()

    @staticmethod
    def format_compatible(fpath: Path | str) -> bool:
        fpath = TuflowPath(fpath)
        try:
            csv = BCTablesCheck.bc_tables_csv_from_gis_file(fpath)
            if csv is not None:
                if not csv.exists():
                    logger.info(f'BC Tables Check CSV file does not exist, skipping load: {csv}')
                    return False
                return True
        except Exception:
            return False
        return False

    @staticmethod
    def bc_tables_csv_from_gis_file(fpath: TuflowPath) -> Path:
        check_base_fpath = None
        fpath_out = None
        lyrname = fpath.stem if fpath.lyrname is None else fpath.lyrname
        is_single_gpkg = fpath.stem != lyrname  # it is in a central check file gpkg e.g. "<name>_Check.gpkg"
        if is_single_gpkg:
            check_base_fpath = fpath.parent / re.sub(r'_Check(?:_[12]D)?', '', fpath.stem)
        if BC_2D_REGEX.findall(lyrname):
            if not check_base_fpath:
                check_base_fpath = fpath.parent / BC_2D_REGEX.sub('', fpath.stem)
            fpath_out = Path(f'{check_base_fpath}_2d_bc_tables_check.csv')
        elif BC_1D_REGEX.findall(lyrname):
            if not check_base_fpath:
                check_base_fpath = fpath.parent / BC_1D_REGEX.sub('', fpath.stem)
            fpath_out = Path(f'{check_base_fpath}_1d_bc_tables_check.csv')

        return fpath_out

    def _load(self):
        self.domain = '2d' if str(self.fpath.stem).endswith('_2d_bc_tables_check') else '1d'
        self.name = re.sub(r'_[12]d_bc_tables_check', '', self.fpath.stem)
        self.name = f'{self.name}_{self.domain}_bc_tables_check'

    def _soft_load(self):
        regex = re.compile(r'BC\d{6}:')
        with self.fpath.open() as f:
            for line in f:
                if not regex.findall(line):
                    continue
                dtype = line.split(':', 1)[1].strip().split(' ')[0].upper()
                if dtype == 'ST' and 'based on SA region' in line:
                    dtype = 'SA'
                if dtype not in self._data_types:
                    self._data_types.append(dtype)

    def _complete_load(self):
        if self._loaded:
            return
        self.provider.load()
        self.tcf = self.provider.tcf
        self._load_objs()
        self._loaded = True

    def data_types(self, filter_by: str = None, bndry_type: bool = True) -> list[str]:
        if not self._loaded:
            if filter_by not in ['timeseries', 'line', 'point', 'polygon', 'timeseries/line', 'timeseries/point', 'timeseries/polygon', None]:
                return []
            return self._data_types
        return super().data_types(filter_by, bndry_type)

    def time_series(self, *args, **kwargs) -> pd.DataFrame:
        if not self._loaded:
            self._complete_load()
        return super().time_series(*args, **kwargs)

    def time_series_plot(self,
                     df: pd.DataFrame,
                     data_type: str | list[str],
                     src_item: 'PlotSourceItem',
                     ) -> typing.Generator[tuple[np.ndarray, np.ndarray, dict[str, typing.Any]], None, None]:
        if df.empty:
            return
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [x[-1] for x in df.columns.to_flat_index()]
        src_item1 = deepcopy(src_item)
        src_item1.label = df.columns[1].split('/')[1]
        if data_type == 'HQ':
            src_item1.xaxis_name = 'flow'
            src_item1.yaxis_name = 'elevation'
        df.columns = df.columns.str.split('/').str[0].str.strip()
        xdata = df.iloc[:,0].to_numpy()
        ydata = df.loc[:, data_type].to_numpy()
        yield xdata, ydata, {'src_item': src_item1}
