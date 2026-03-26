import os
from datetime import datetime
import typing
from pathlib import Path
import logging

import numpy as np
try:
    import pandas as pd
except ImportError:
    from ...pt.pytuflow._outputs.pymesh.stubs import pandas as pd
from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsVectorLayer

from .tvoutput import TuflowViewerOutput

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import CrossSections, TuflowPath
else:
    from tuflow.pt.pytuflow import CrossSections, TuflowPath

if typing.TYPE_CHECKING:
    from ..widgets.tv_plot_widget.plotsourceitem import PlotSourceItem


logger = logging.getLogger('tuflow_viewer')


TUFLOW_CROSS_SECTION_ATTR_NAMES = [
    'source',
    'type',
    'flags',
    'column_1',
    'column_2',
]


class TuflowCrossSections(CrossSections, TuflowViewerOutput):
    DRIVER_NAME = 'TUFLOW Cross Sections'
    LAYER_TYPE = 'CrossSection'
    AUTO_LOAD_METHOD = 'OnOpened'

    def __init__(self, fpath: str, layers: list[QgsVectorLayer] = ()):
        super(TuflowCrossSections, self).__init__(fpath)
        self._init_viewer_output_mixin(self.name)
        self._map_layers = layers.copy()
        self._loaded = False
        self._data_types = []
        self._soft_load()

    def close(self):
        self._teardown_viewer_output_mixin()

    @staticmethod
    def format_compatible(fpath: Path | str) -> bool:
        try:
            with TuflowPath(fpath).open_gis() as fo:
                for f in fo:
                    return len(f.attrs) >= 9 and [x.lower() for x in f.attrs.keys()][:5] == TUFLOW_CROSS_SECTION_ATTR_NAMES
        except Exception:
            return False
        return False

    def _load(self):
        # override _load() and only do a full load when needed
        # users may never want to plot from the cross-section layer, so don't annoy them by slowing down
        # the process of opening the vector layer in QGIS by loading this class
        self.name = self.fpath.stem

    def _soft_load(self):
        for layer in self._map_layers:
            self._data_types = [x.lower() for x in layer.uniqueValues(layer.fields().indexFromName('Type'))]

    def _complete_load(self):
        if self._loaded:
            return
        CrossSections._load(self)
        self._loaded = True

    def data_types(self, filter_by: str = None) -> list[str]:
        if not self._loaded:
            if filter_by.lower() not in ['section', 'na', 'line', 'section/line', 'section/point', 'static']:
                return []
            return self._data_types
        return super().data_types(filter_by)

    def section(self, locations: str | list[str], data_types: str | list[str] = None,
                time: float | datetime = -1, *args, **kwargs) -> pd.DataFrame:
        if not self._loaded:
            self._complete_load()

        def loc(x: str) -> str:
            if os.name != 'nt' and '\\' in str(x):
                x = x.replace('\\', '/')
            elif os.name == 'nt' and '/' in str(x):
                x = x.replace('/', '\\')
            if '.csv:' in x.lower():
                df_ = self.objs[self.objs['uid'].str.lower() == x.lower()][['id']]
                if not df_.empty:
                    return df_.iloc[0,0]
            elif '.csv' in x.lower():
                df_ = self.objs[self.objs['source'].str.lower() == Path(x).name.lower()][['id']]
                if not df_.empty:
                    return df_.iloc[0,0]
            else:
                df_ = self.objs[self.objs['id'].str.lower() == x.lower()][['id']]
                if not df_.empty:
                    return df_.iloc[0,0]
            return Path(x).stem

        if locations is not None:
            if not isinstance(locations, (list, tuple)):
                locations = [locations]
            locations = [loc(x) for x in locations]

        for loc in locations.copy():
            if loc not in self.ids():
                locations.remove(loc)

        if not locations:
            return pd.DataFrame()

        return super().section(locations, data_types)

    def section_plot(self,
                     df: pd.DataFrame,
                     data_type: str | list[str],
                     src_item: 'PlotSourceItem',
                     ) -> typing.Generator[tuple[np.ndarray, np.ndarray, dict[str, typing.Any]], None, None]:
        if df.empty:
            return
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [x[-1] for x in df.columns.to_flat_index()]
        df.columns = df.columns.str.split('/').str[0].str.strip()
        i, j = (1, 0) if data_type in ['na', 'bg', 'lc'] else (0, 1)
        xdata = df.iloc[:,i].to_numpy()
        ydata = df.iloc[:,j].to_numpy()
        yield xdata, ydata, {}
