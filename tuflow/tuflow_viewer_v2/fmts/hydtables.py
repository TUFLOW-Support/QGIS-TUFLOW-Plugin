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
    from ...pt.pytuflow import HydTablesCheck as HydTablesCheckBase, TuflowPath
else:
    from tuflow.pt.pytuflow import HydTablesCheck as HydTablesCheckBase, TuflowPath

if typing.TYPE_CHECKING:
    from ..widgets.tv_plot_widget.plotsourceitem import PlotSourceItem

import logging
logger = logging.getLogger('tuflow_viewer')


HYD_PROP_REGEX = re.compile(r'_hydprop_check(?:_L)?')


class HydTablesCheck(HydTablesCheckBase, TimeSeriesMixin):
    DRIVER_NAME = 'Hydraulic Tables Check'
    LAYER_TYPE = 'HydTable'
    AUTO_LOAD_METHOD = 'OnOpened'

    def __init__(self, fpath: str, layers: list[QgsVectorLayer]):
        fpath = TuflowPath(fpath)  # origin fpath
        self.fpath = self.hyd_tables_csv_from_gis_file(fpath)
        if self.fpath is None:
            self.fpath = fpath
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
            csv = HydTablesCheck.hyd_tables_csv_from_gis_file(fpath)
            if csv is not None:
                if not csv.exists():
                    logger.info(f'Hydraulic Tables Check CSV file does not exist, skipping load: {csv}')
                    return False
                return True
        except Exception:
            return False
        return False

    @staticmethod
    def hyd_tables_csv_from_gis_file(fpath: TuflowPath) -> Path:
        check_base_fpath = None
        fpath_out = None
        lyrname = fpath.stem if fpath.lyrname is None else fpath.lyrname
        is_single_gpkg = fpath.stem != lyrname  # it is in a central check file gpkg e.g. "<name>_Check.gpkg"
        if is_single_gpkg:
            check_base_fpath = fpath.parent / re.sub(r'_Check(?:_[12]D)?', '', fpath.stem)
        elif HYD_PROP_REGEX.findall(lyrname):
            if not check_base_fpath:
                check_base_fpath = fpath.parent / HYD_PROP_REGEX.sub('', fpath.stem)
        if check_base_fpath:
            fpath_out = Path(f'{check_base_fpath}_1d_ta_tables_check.csv')
        return fpath_out

    def _load(self, complete_load: bool = False):
        if complete_load:
            super()._load()
        self.name = re.sub(r'_1d_ta_tables_check', '', self.fpath.stem)
        self.name = f'{self.name}_1d_ta_tables_check'

    def _soft_load(self):
        with self.fpath.open() as f:
            for line in f:
                if line.startswith('Channel'):
                    for line1 in f:
                        if line1.startswith('"Elevation"') or line1.startswith('Elevation'):
                            self._data_types = [
                                'depth',
                                'storage width',
                                'flow width',
                                'area',
                                'wetted perimeter',
                                'radius',
                                'vertex resistance factor',
                                'k '
                            ]
                            return

    def _complete_load(self):
        if self._loaded:
            return
        self._load(complete_load=True)
        self._loaded = True

    def data_types(self, filter_by: str = None) -> list[str]:
        if not self._loaded:
            if filter_by in ['section', 'line', 'section/line']:
                return self._data_types
            return []
        if filter_by is None:
            filter_by = 'channel'
        else:
            if 'channel' not in filter_by:
                filter_by = f'channel/{filter_by}'
        return super().data_types(filter_by)

    def section(self, *args, **kwargs) -> pd.DataFrame:
        if not self._loaded:
            self._complete_load()
        return super().section(*args, **kwargs)

    def section_plot(self,
                     df: pd.DataFrame,
                     data_type: str | list[str],
                     src_item: 'PlotSourceItem',
                     ) -> typing.Generator[tuple[np.ndarray, np.ndarray, dict[str, typing.Any]], None, None]:
        if df.empty:
            return
        src_item1 = deepcopy(src_item)
        if isinstance(df.columns, pd.MultiIndex):
            src_item1.label = df.columns.get_level_values(0)[0].split('/')[0]
            src_item1.use_label_in_tooltip = True
            df.columns = [x[-1] for x in df.columns.to_flat_index()]
        df.columns = df.columns.str.split('/').str[0].str.strip()
        xdata = df.loc[:, data_type].to_numpy()
        ydata = df.loc[:, 'elevation'].to_numpy()
        src_item1.feedback_context = 'static'
        src_item1.xaxis_name = data_type
        src_item1.yaxis_name = 'elevation'
        yield xdata, ydata, {'src_item': src_item1}
