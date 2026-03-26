import typing
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import numpy as np
try:
    import pandas as pd
except ImportError:
    from ...pt.pytuflow._outputs.pymesh.stubs import pandas as pd
from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry, QgsPointXY
from qgis.utils import iface

from .time_series_mixin import TimeSeriesMixin

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import FMTS as FMTSBase, FMDAT, GXY
    from ...gui.styling import apply_tf_style
else:
    from tuflow.pt.pytuflow import FMTS as FMTSBase, FMDAT, GXY
    from tuflow.gui.styling import apply_tf_style

if typing.TYPE_CHECKING:
    from ..widgets.tv_plot_widget.plotsourceitem import PlotSourceItem


import logging
logger = logging.getLogger('tuflow_viewer')


class FMTS(FMTSBase, TimeSeriesMixin):
    DRIVER_NAME = 'Flood Modeller'
    LAYER_TYPE = 'Plot'

    def __init__(self, fpath: Path | str, dat: Path | str, gxy: Path | str, bypass_dialog: bool = False):
        from ..widgets.dlg_fm_res import FMImportDialog
        self._loaded = False
        self._no_results = False
        if (not fpath or not dat) and not bypass_dialog:
            dlg = FMImportDialog(gxy, iface.mainWindow())
            if not dlg.exec():
                return
            dat = dlg.dat if dlg.dat else None
            fpath = dlg.results if dlg.results else []

        if fpath:
            super().__init__(fpath, dat, gxy)
        else:
            self._load_gxy_only(gxy)
            self._dat = None
            if dat:
                self._dat = FMDAT(dat)
        self._init_viewer_output_mixin(self.name)
        self._map_layers = self._create_map_layers()
        self.init_temporal_properties()
        self._init_vector_temporal_properties(self._map_layers, self._lyr2resultstyle)
        self._init_styling(self._map_layers, self._lyr2resultstyle)  # must come after temporal init

    @property
    def dat(self) -> FMDAT:
        return self._dat

    @property
    def gxy(self) -> GXY:
        return self._gxy

    def close(self):
        self._teardown_viewer_output_mixin()

    @staticmethod
    def format_compatible(fpath: Path | str) -> bool:
        """fpath should be the GXY file."""
        return Path(fpath).suffix.lower() == '.gxy'

    def tooltip(self, src_item: 'PlotSourceItem', location_id: str, position: tuple[float, float], *args, **kwargs) -> str:
        from ..widgets.tv_plot_widget.mixins.plot_helper_mixin import PlotHelperMixin
        try:
            int(location_id)
            us_node = self._channel_info.loc[location_id, 'us_node']
            us_node_name = self._node_info.loc[us_node, 'name']
            return PlotHelperMixin.tooltip(src_item, us_node_name, position, *args, **kwargs)
        except ValueError:
            return PlotHelperMixin.tooltip(src_item, location_id, position, *args, **kwargs)

    def times(self, *args, **kwargs) -> list[float] | list[datetime]:
        if self._no_results:
            return []
        return super().times(*args, **kwargs)

    def data_types(self, filter_by: str = None) -> list[str]:
        if self._no_results:
            return []
        return super().data_types(filter_by)

    def section(self, *args, **kwargs) -> pd.DataFrame:
        if self._no_results:
            return pd.DataFrame()
        return super().section(*args, **kwargs)

    def section_plot(self,
                     df: pd.DataFrame,
                     data_type: str | list[str],
                     src_item: 'PlotSourceItem',
                     ) -> typing.Generator[tuple[np.ndarray, np.ndarray, dict[str, typing.Any]], None, None]:
        for xdata, ydata, extra in super().section_plot(df, data_type, src_item):
            src_item1 = extra['src_item'] if 'src_item' in extra else deepcopy(src_item)
            src_item1.feedback_context = 'dynamic channel feature'
            src_item1.tooltip = self.tooltip
            extra['src_item'] = src_item1
            yield xdata, ydata, extra

    def _init_styling(self, layers: list[QgsVectorLayer], lyr2resultstyle: dict):
        for layer in layers:
            apply_tf_style(layer=layer, style='Dynamic')

    def _create_map_layers(self) -> list[QgsVectorLayer]:
        # get node and channel attributes and geometry
        node = self._plot_p_attrs()
        chan = self._plot_l_attrs(node)

        # create vector layers
        crs = QgsProject.instance().crs().authid()
        plot_p = QgsVectorLayer(
            f'point?crs={crs}&field=ID:string&field=Type:string&field=Source:string&field=Unit_Type:string(20)&field=Full_Type:string(50)',
            f'{self.name}_FM_PLOT_P',
            'memory'
        )
        plot_l = QgsVectorLayer(
            f'linestring?crs={crs}&field=ID:string&field=Type:string&field=Source:string&field=Upstrm_Type:string(20)&field=Dnstrm_Type:string(20)',
            f'{self.name}_FM_PLOT_L',
            'memory'
        )

        lyrs = []

        # create features
        feats = []
        for idx, row in node.iterrows():
            f = QgsFeature()
            f.setFields(plot_p.fields())
            f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(*row[['x', 'y']].tolist())))
            f.setAttributes(
                [row['name'].strip(' _'), 'Node', 'H_V_Q_', row['type'].strip(' _'), str(idx)]
            )
            feats.append(f)
        plot_p.dataProvider().truncate()
        success, _ = plot_p.dataProvider().addFeatures(feats)
        if not success:
            error = plot_p.dataProvider().lastError()
            logger.error(f'Error creating Flood Modeller _PLOT_P GIS layer: {error}')
        else:
            plot_p.updateExtents()
            if not plot_p.isValid():
                logger.error('Unexpected error creating Flood Modeller _PLOT_P GIS layer')
            else:
                lyrs.append(plot_p)

        feats = []
        for idx, row in chan.iterrows():
            f = QgsFeature()
            f.setFields(plot_l.fields())
            f.setGeometry(QgsGeometry.fromPolylineXY(
                [QgsPointXY(*row[['us_x', 'us_y']].tolist()), QgsPointXY(*row[['ds_x', 'ds_y']].tolist())]
            ))
            f.setAttributes(
                [str(idx).strip(' _'), 'Chan', 'H_', row['us_type'].strip(' _'), row['ds_type'].strip(' _')]
            )
            feats.append(f)
        plot_l.dataProvider().truncate()
        success, _ = plot_l.dataProvider().addFeatures(feats)
        if not success:
            error = plot_l.dataProvider().lastError()
            logger.error(f'Error creating Flood Modeller _PLOT_L GIS layer: {error}')
        else:
            plot_l.updateExtents()
            if not plot_l.isValid():
                logger.error('Unexpected error creating Flood Modeller _PLOT_P GIS layer')
            else:
                lyrs.insert(0, plot_l)  # insert channels below nodes in layer order

        return lyrs

    def _plot_p_attrs(self) -> pd.DataFrame:
        return self._node_info.loc[:,['name', 'type']].join(self._gxy.node_df)

    def _plot_l_attrs(self, node_df: pd.DataFrame) -> pd.DataFrame:
        df = self._channel_info.join(node_df, on='us_node')
        df = df.rename(columns={'x': 'us_x', 'y': 'us_y', 'name': 'us_name', 'type': 'us_type'})
        df = df.join(node_df, on='ds_node')
        df = df.rename(columns={'x': 'ds_x', 'y': 'ds_y', 'name': 'ds_name', 'type': 'ds_type'})
        return df

    def _load_gxy_only(self, gxy: Path | str):
        self.has_inherent_reference_time = False
        self.has_reference_time = False
        self.fpath = Path(gxy)
        self.name = f'{self.fpath.stem}_gxy'
        self._gxy = GXY(gxy)

        self._node_info = pd.DataFrame(index=self._gxy.node_df.index)
        self._node_info['name'] = self._node_info.index.to_series().apply(lambda x: x.split('_', 2)[-1])
        self._node_info['type'] = self._node_info.index.to_series().apply(lambda x: '_'.join(x.split('_', 2)[:-1]))

        self._channel_info = self._gxy.link_df.rename(columns={'ups_node': 'us_node', 'dns_node': 'ds_node'})

        self._no_results = True
        self._loaded = True
