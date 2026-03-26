from pathlib import Path

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY

from .fmts import TimeSeriesMixin

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import FVBCTide as FVBCTideBase, TuflowPath
    from ...compatibility_routines import QT_MESSAGE_BOX_YES
else:  # when running tests outside of QGIS environment
    from tuflow.pt.pytuflow import FVBCTide as FVBCTideBase, TuflowPath
    from tuflow.compatibility_routines import QT_MESSAGE_BOX_YES

try:
    from netCDF4 import Dataset
except ImportError:
    Dataset = 'Dataset'

import logging
logger = logging.getLogger('tuflow_viewer')


class FVBCTide(FVBCTideBase, TimeSeriesMixin):
    DRIVER_NAME = 'FV BC Tide'
    LAYER_TYPE = 'FVBCTide'
    AUTO_LOAD_METHOD = 'ContextMenu'

    def __init__(self,
                 nc_fpath: str | Path = '',
                 node_string_gis_fpath: str | Path = '',
                 use_local_time: bool = None,
                 layers: list[QgsVectorLayer] = (),
                 ):
        from qgis.utils import iface
        parent = iface.mainWindow() if iface else None
        self._loaded = False
        if Dataset == 'Dataset':
            logger.error('NetCDF4 Python library required to load FV BC tide data.')
            return

        node_string_gis_fpath = TuflowPath(node_string_gis_fpath)
        if not nc_fpath:
            start_dir = str(node_string_gis_fpath.parent)
            files = QFileDialog.getOpenFileName(parent, 'Open NetCDF Tide File', start_dir, 'NetCDF (*.nc)')
            nc_fpath = files[0]
            if not nc_fpath:
                return

        if not self.format_compatible(nc_fpath):
            logger.error('NetCDF file does not look like FV NetCDF BC tide data.')
            return

        nc = None
        try:
            nc = Dataset(nc_fpath, 'r')
            has_local_time = 'local_time' in nc.variables
        except Exception:
            has_local_time = False
        finally:
            if nc:
                nc.close()

        if use_local_time is None and has_local_time:
            if has_local_time:
                answer = QMessageBox.question(
                    parent, 'Use Local Time',
                    'NetCDF file contains local time information, do you want to use local time rather than UTC?',
                    defaultButton=QT_MESSAGE_BOX_YES,
                )
                use_local_time = answer == QT_MESSAGE_BOX_YES

        super(FVBCTide, self).__init__(nc_fpath, node_string_gis_fpath, use_local_time)
        self._init_viewer_output_mixin(self.name)

        node_string_layer = [x for x in layers if TuflowPath(x.dataProvider().dataSourceUri()) == node_string_gis_fpath]
        if not node_string_layer:
            logger.error('Unexpected error loading FV BC tide data - could not find node string gis layer.')
            return
        node_string_layer = node_string_layer[0]
        self._map_layers = [node_string_layer, self._create_point_layer(node_string_layer)]

        self.init_temporal_properties()
        self._init_styling(self._map_layers, {})

    def close(self):
        self._teardown_viewer_output_mixin()

    @staticmethod
    def format_compatible(fpath: Path | str) -> bool:
        return FVBCTideBase._looks_like_this(Path(fpath))

    def _create_point_layer(self, node_string: QgsVectorLayer) -> QgsVectorLayer:
        uri = f'point?crs={node_string.crs().authid()}&field=ID:string&field=Ch:real&field=Type:string&field=Source:string'
        lyr = QgsVectorLayer(uri, f'{self.name}_pts', 'memory')
        if not lyr.isValid():
            logger.error('Unexpected error creating point layer. Error: layer is invalid.')
            return lyr

        feats = []
        for label in self.provider.get_labels():
            pts = self.provider.get_ch_points(label)  # array of (ch, x, y)
            for i, pt in enumerate(pts):
                f = QgsFeature()
                f.setFields(lyr.fields())
                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(*pt[1:].tolist())))
                f.setAttributes([f'{label}_pt_{i}', pt[0], 'BC_NS', 'H_'])
                feats.append(f)

        lyr.dataProvider().truncate()
        success, _ = lyr.dataProvider().addFeatures(feats)
        if not success:
            error = lyr.dataProvider().lastError()
            logger.error(f'Error creating FV BC point layer: {error}')
        else:
            lyr.updateExtents()
            if not lyr.isValid():
                logger.error('Unexpected error adding features to point layer. Error: layer is invalid.')

        return lyr
