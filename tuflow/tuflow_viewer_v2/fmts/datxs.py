import typing
from copy import deepcopy
from pathlib import Path

import numpy as np
try:
    import pandas as pd
except ImportError:
    from ...pt.pytuflow._outputs.pymesh.stubs import pandas as pd
from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry, QgsPointXY

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import DATCrossSections as DATCrossSectionsBase
    from ...gui.styling import apply_tf_style
else:
    from tuflow.pt.pytuflow import DATCrossSections as DATCrossSectionsBase
    from tuflow.gui.styling import apply_tf_style

from .tvoutput import TuflowViewerOutput

import logging
logger = logging.getLogger('tuflow_viewer')

if typing.TYPE_CHECKING:
    from ...pt.pytuflow import GXY
    from ..widgets.tv_plot_widget.plotsourceitem import PlotSourceItem


class DATCrossSections(DATCrossSectionsBase, TuflowViewerOutput):
    DRIVER_NAME = 'Flood Modeller DAT'
    LAYER_TYPE = 'CrossSection'

    def __init__(self, fpath: Path | str, driver: typing.Any = None, gxy: 'GXY' = None):
        super(DATCrossSections, self).__init__(fpath, driver)
        self.name = f'1d_xs_{self.name}'
        self._init_viewer_output_mixin(self.name)
        self._map_layers = self._create_map_layers(gxy)
        self._init_styling(self._map_layers)  # must come after temporal init

    def close(self):
        self._teardown_viewer_output_mixin()

    @staticmethod
    def format_compatible(fpath: Path | str) -> bool:
        return DATCrossSections._looks_like_this(Path(fpath))

    def section_plot(self,
                     df: pd.DataFrame,
                     data_type: str | list[str],
                     src_item: 'PlotSourceItem',
                     ) -> typing.Generator[tuple[np.ndarray, np.ndarray, dict[str, typing.Any]], None, None]:
        if df.empty:
            return
        src_item1 = deepcopy(src_item)
        src_item1.label = df.columns.levels[0][0]
        src_item1.use_label_in_tooltip = True
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [x[-1] for x in df.columns.to_flat_index()]
        df.columns = df.columns.str.split('/').str[0].str.strip()
        xdata = df.iloc[:,0].to_numpy()
        ydata = df.iloc[:,1].to_numpy()
        yield xdata, ydata, {'src_item': src_item1}

    def _create_map_layers(self, gxy: 'GXY') -> list[QgsVectorLayer]:
        lyrs = []
        crs = QgsProject.instance().crs()
        uri = (
            f'linestring?crs={crs.authid()}'
            '&field=Source:string(50)'
            '&field=Type:string(36)'
            '&field=Flags:string(8)'
            "&field=Column_1:string(8)"
            "&field=Column_2:string(8)"
            "&field=Column_3:string(8)"
            "&field=Column_4:string(8)"
            "&field=Column_5:string(8)"
            "&field=Column_6:string(8)"
            "&field=Z_Increment:double"
            "&field=Z_Maximum:double"
            "&field=Provider:string(8)"
            "&field=Comments:string(100)"
        )
        lyr = QgsVectorLayer(uri, f'1d_xs_{self.name}', 'memory')
        if not lyr.isValid():
            logger.error('Unexpected error creating DAT cross section GIS layer.')
            return []

        # create index of upstream and downstream nodes as per GXY
        dns_nodes = ups_nodes = None
        if gxy is not None:
            dns_nodes = gxy.link_df.set_index('ups_node')
            dns_nodes.index.name = 'node'
            dns_nodes = dns_nodes.merge(gxy.node_df, left_on='dns_node', right_index=True)
            ups_nodes = gxy.link_df.set_index('dns_node')
            ups_nodes.index.name = 'node'
            ups_nodes = ups_nodes.merge(gxy.node_df, left_on='ups_node', right_index=True)

        feats = []
        at_least_one_valid = False
        at_least_one_invalid = False
        for xs in self.cross_sections:
            f = QgsFeature()
            f.setFields(lyr.fields())

            # create geometry
            comment = ''
            xy = xs.df.loc[:, ['easting', 'northing']]
            linestring = xy[(xy['easting'] != 0) & (xy['northing'] != 0)]
            if gxy is None or not linestring.empty:   # use easting, northing data in DAT file - not guaranteed to exist or be meaningful
                npnts_rem = xy.shape[0] - linestring.shape[0]
                if linestring.empty:
                    at_least_one_invalid = True
                    comment = f'All easting / northing entries == (0,0), no geometry will be generated. Use GXY to load DAT.'
                elif npnts_rem:
                    comment = f'Removed {npnts_rem} due to easting / northing == (0,0) '

                if not linestring.empty:
                    at_least_one_valid = True

                linestring = linestring.to_numpy().tolist()
            else:  # create line at a right angle to channel
                nodexy = gxy.node_df.loc[xs.uid, ['x', 'y']].to_numpy()
                has_ds_links = xs.uid in dns_nodes.index
                has_us_links = xs.uid in ups_nodes.index
                if has_ds_links and has_us_links:  # take the average angle
                    v1 = ups_nodes.loc[xs.uid, ['x', 'y']].to_numpy().reshape((-1, 2))[0]
                    v2 = dns_nodes.loc[xs.uid, ['x', 'y']].to_numpy().reshape((-1, 2))[0]
                    us = nodexy
                    ds = nodexy + v2 - v1
                elif has_ds_links:
                    us = nodexy
                    ds = dns_nodes.loc[xs.uid, ['x', 'y']].to_numpy().reshape((-1, 2))[0]
                elif has_us_links:
                    us = ups_nodes.loc[xs.uid, ['x', 'y']].to_numpy().reshape((-1, 2))[0]
                    ds = nodexy
                else:
                    us = nodexy
                    ds = nodexy - np.array([-1, 0])
                length = 10.
                if np.linalg.norm(ds - us) == 0.:
                    ds = nodexy - np.array([-1, 0])
                v = (ds - us) / np.linalg.norm(ds - us)
                if v.size == 2:
                    v = np.append(v, 0.)
                v = v.astype('f8')
                p0 = np.cross([0, 0, 1], v)[:-1] * length + us
                p1 = us
                p2 = np.cross(v, [0, 0, 1])[:-1] * length + us
                linestring = [p0.astype(float).tolist(), p1.astype(float).tolist(), p2.astype(float).tolist()]
                comment = 'Linestring generated using GXY.'
                at_least_one_valid = True

            # assign geometry and attributes
            f.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(*x) for x in linestring]))
            f.setAttributes([xs.name, f'{xs.type}_{xs.sub_name}', '', '', '', '', '', '', '', 0., 0., 'FM DAT', comment])
            feats.append(f)

        if not at_least_one_valid:
            logger.error('DAT file does not contain any cross-sections with populated Easting / Northing information. '
                         'Load using a GXY file to create a valid GIS layer.')
        elif at_least_one_invalid:
            logger.warning('Unable to create a GIS feature for every cross-section due to unpopulated Easting / Northing '
                           'information (view "comment" in attribute table).'
                           'Load using a GXY file to create a valid feature for each cross-section.')

        lyr.dataProvider().truncate()
        success, _ = lyr.dataProvider().addFeatures(feats)
        if not success:
            error = lyr.dataProvider().lastError()
            logger.error(f'Error creating Flood Modeller DAT 1d_xs layer: {error}')
        else:
            lyr.updateExtents()
            if not lyr.isValid():
                logger.error('Unexpected error creating Flood Modeller DAT 1d_xs layer')
            else:
                lyrs.append(lyr)

        return lyrs

    def _init_styling(self, layers: list[QgsVectorLayer]):
        for layer in layers:
            apply_tf_style(layer=layer)
