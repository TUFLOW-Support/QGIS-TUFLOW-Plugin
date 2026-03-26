import typing
from copy import deepcopy
from pathlib import Path

import numpy as np
try:
    import pandas as pd
except ImportError:
    from ...pt.pytuflow._outputs.pymesh.stubs import pandas as pd
from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsVectorLayer, Qgis, QgsUnitTypes

from .tvoutput import TuflowViewerOutput

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow._pytuflow_types import TuflowPath
    from ...gui.styling import apply_tf_style, apply_tf_style_gpkg_ts
else:  # when running tests outside of QGIS environment
    from tuflow.gui.styling import apply_tf_style, apply_tf_style_gpkg_ts
    from tuflow.pt.pytuflow._pytuflow_types import TuflowPath


if typing.TYPE_CHECKING:
    from ..widgets.tv_plot_widget.plotsourceitem import PlotSourceItem


import logging
logger = logging.getLogger('tuflow_viewer')


class TimeSeriesMixin(TuflowViewerOutput):

    def time_series_plot(self,
                         df: pd.DataFrame,
                         data_type: str | list[str],
                         src_item: 'PlotSourceItem',
                         ) -> typing.Generator[tuple[np.ndarray, np.ndarray, dict[str, typing.Any]], None, None]:
        columns = [x[-1] for x in df.columns.to_flat_index()] if isinstance(df.columns, pd.MultiIndex) else df.columns
        for xdata, ydata, extra in super().time_series_plot(df, data_type, src_item):
            src_item1 = extra['src_item'] if 'src_item' in extra else deepcopy(src_item)
            src_item1.label = columns.str.split('/').str[-1].str.strip()[0]
            src_item1.use_label_in_tooltip = True
            extra['src_item'] = src_item1
            yield xdata, ydata, extra

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
        if 'branch_id' not in df.columns:
            df['branch_id'] = 0
        for branch_id in range(df['branch_id'].max() + 1):
            extra = {}
            df_branch = df[df['branch_id'] == branch_id]
            if df_branch.empty:
                continue
            xdata = df_branch.loc[:, 'offset'].to_numpy()
            ydata = df_branch.loc[:, data_type].to_numpy()
            extra['channel_ids'] = df_branch.loc[:, 'channel'].tolist() if 'channel' in df_branch.columns else []
            extra['node_ids'] = df_branch.loc[:, 'node'].tolist() if 'node' in df_branch.columns else []
            yield xdata, ydata, extra

    def _create_gis_layer_from_file(self, fpath: TuflowPath | str) -> QgsVectorLayer:
        if isinstance(fpath, TuflowPath):
            name = fpath.lyrname
        else:
            name = fpath.split('|layername=')[-1] if '|layername=' in fpath else Path(fpath).stem
        lyr = QgsVectorLayer(str(fpath), name, 'ogr')
        if not lyr.isValid():
            logger.debug(f'Failed to load GIS Plot Layer: {fpath}')
            lyr = None
        return lyr

    def _init_vector_temporal_properties(self, layers: list[QgsVectorLayer], lyr2resultstyle: dict):
        # setup QGIS dynamic temporal properties for each layer
        for lyr in layers:
            result_type = lyr2resultstyle.get(lyr.id(), None)
            if result_type:
                self.set_vector_temporal_properties(lyr, enabled=True)

    def _init_styling(self, map_layers: list[QgsVectorLayer], lyr2resultstyle: dict):
        super()._init_styling(map_layers, lyr2resultstyle)
        for layer in map_layers:
            result_type = lyr2resultstyle.get(layer.id())
            if result_type:
                apply_tf_style_gpkg_ts(layer, result_type, result_type)
            else:
                apply_tf_style(layer=layer)

    @staticmethod
    def set_vector_temporal_properties(lyr: QgsVectorLayer, enabled: bool):
        lyr.temporalProperties().setIsActive(enabled)
        if not enabled:
            return
        lyr.temporalProperties().setMode(Qgis.VectorTemporalMode.FeatureDateTimeInstantFromField)
        lyr.temporalProperties().setLimitMode(Qgis.VectorTemporalLimitMode.IncludeBeginIncludeEnd)
        lyr.temporalProperties().setStartField('Datetime')
        lyr.temporalProperties().setEndField('Datetime')
        lyr.temporalProperties().setFixedDuration(0.0)
        lyr.temporalProperties().setDurationUnits(QgsUnitTypes.TemporalUnit.TemporalSeconds)