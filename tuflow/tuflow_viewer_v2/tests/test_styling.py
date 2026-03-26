from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parents[3]))

from qgis.core import QgsVectorLayer

from .stubs.qgis_stubs import QGIS
from ._utils import get_dataset_path, TuflowViewerTestCase
from tuflow.gui.styling import apply_tf_style_gpkg_ts


class TestStyling(TuflowViewerTestCase):

    def test_gpkg_estry(self):
        p = get_dataset_path('EG15_001_TS_1D.gpkg', 'vector layer')
        lyr = QgsVectorLayer(f'{p}|layername=EG15_001_TS_1D_L', 'EG15_001_TS_1D_L', 'ogr')
        apply_tf_style_gpkg_ts(lyr, 'Flow', 'Flow')
        self.assertIsNotNone(lyr.renderer())
        self.assertEqual('graduatedSymbol', lyr.renderer().type())

    def test_gpkg_po(self):
        p = get_dataset_path('EG15_001_TS_2D.gpkg', 'vector layer')
        lyr = QgsVectorLayer(f'{p}|layername=EG15_001_TS_2D_L', 'EG15_001_PLOT_L', 'ogr')
        apply_tf_style_gpkg_ts(lyr, '_PLOT_Type', 'Type')
        self.assertIsNotNone(lyr.renderer())
        self.assertEqual('categorizedSymbol', lyr.renderer().type())

    def test_gpkg_rl(self):
        p = get_dataset_path('EG15_001_TS_RL.gpkg', 'vector layer')
        lyr = QgsVectorLayer(f'{p}|layername=EG15_001_TS_RL_L', 'EG15_001_PLOT_L', 'ogr')
        apply_tf_style_gpkg_ts(lyr, '_PLOT_Type', 'Type')
        self.assertIsNotNone(lyr.renderer())
        self.assertEqual('categorizedSymbol', lyr.renderer().type())
