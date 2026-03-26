from qgis.core import QgsVectorLayer, QgsGeometry
from qgis.gui import QgsVertexMarker
from qgis.PyQt.QtGui import QColor

from tuflow.tuflow_viewer_v2.tests.stubs.qgis_stubs import QGIS
from tuflow.tuflow_viewer_v2.tests._utils import get_dataset_path, TuflowViewerTestCase
from tuflow.tuflow_viewer_v2.selection import Selection, DrawnSelection, SelectionItem
from tuflow.tuflow_viewer_v2.tvinstance import get_viewer_instance


class Output:
    LAYER_TYPE = 'Plot'



class TestSelectionContainer(TuflowViewerTestCase):

    def test_add_iter(self):
        p = get_dataset_path('LINE_FROM_ORIGIN.gpkg', 'vector layer')
        lyr = QgsVectorLayer(str(p), 'LINE_FROM_ORIGIN', 'ogr')
        feats = list(lyr.getFeatures())
        f1, f2 = feats

        sel = Selection(lyr, [f1])
        self.assertTrue(bool(sel))
        item1 = SelectionItem(
            id_=f'TUFLOW-VIEWER::::{lyr.id()}-{f1.id()}',
            geom=Selection.geom_extract(f1.geometry()),
            domain='mapoutput',
            domain_geom='line',
            chan_type='',
            is_tv_layer=False,
            sel_type='selection',
            colour=None,
            lyrid=lyr.id()
        )
        self.assertEqual(item1, [item for item in sel][0])

        sel += Selection(lyr, [f2])
        self.assertTrue(bool(sel))
        item2 = SelectionItem(
            id_=f'TUFLOW-VIEWER::::{lyr.id()}-{f2.id()}',
            geom=Selection.geom_extract(f2.geometry()),
            domain='mapoutput',
            domain_geom='line',
            chan_type='',
            is_tv_layer=False,
            sel_type='selection',
            colour=None,
            lyrid=lyr.id()
        )
        self.assertEqual([item1, item2], [item for item in sel])

    def test_clear(self):
        p = get_dataset_path('LINE_FROM_ORIGIN.gpkg', 'vector layer')
        lyr = QgsVectorLayer(str(p), 'LINE_FROM_ORIGIN', 'ogr')
        feats = list(lyr.getFeatures())
        f1, f2 = feats

        sel = Selection(lyr, [f1, f2])
        self.assertTrue(bool(sel))
        sel.clear()
        self.assertFalse(bool(sel))

    def test_pop(self):
        p = get_dataset_path('LINE_FROM_ORIGIN.gpkg', 'vector layer')
        lyr = QgsVectorLayer(str(p), 'LINE_FROM_ORIGIN', 'ogr')
        feats = list(lyr.getFeatures())
        f1, f2 = feats

        sel = Selection(lyr, [f1, f2])
        item = sel.pop()
        item2 = SelectionItem(
            id_=f'TUFLOW-VIEWER::::{lyr.id()}-{f2.id()}',
            geom=Selection.geom_extract(f2.geometry()),
            domain='mapoutput',
            domain_geom='line',
            chan_type='',
            is_tv_layer=False,
            sel_type='selection',
            colour=None,
            lyrid=lyr.id()
        )
        self.assertEqual(item2, item)

    def test_pop_by_lyrid(self):
        p = get_dataset_path('LINE_FROM_ORIGIN.gpkg', 'vector layer')
        lyr = QgsVectorLayer(str(p), 'LINE_FROM_ORIGIN', 'ogr')
        feats = list(lyr.getFeatures())
        f1, f2 = feats

        sel = Selection(lyr, [f1, f2])
        item = sel.pop(lyrid=lyr.id())
        item2 = SelectionItem(
            id_=f'TUFLOW-VIEWER::::{lyr.id()}-{f2.id()}',
            geom=Selection.geom_extract(f2.geometry()),
            domain='mapoutput',
            domain_geom='line',
            chan_type='',
            is_tv_layer=False,
            sel_type='selection',
            colour=None,
            lyrid=lyr.id()
        )
        self.assertEqual(item2, item)

    def test_pop_by_selection_type(self):
        p = get_dataset_path('LINE_FROM_ORIGIN.gpkg', 'vector layer')
        lyr = QgsVectorLayer(str(p), 'LINE_FROM_ORIGIN', 'ogr')
        feats = list(lyr.getFeatures())
        f1, f2 = feats

        sel = Selection(lyr, [f1, f2])
        item = sel.pop(sel_type='selection')
        item2 = SelectionItem(
            id_=f'TUFLOW-VIEWER::::{lyr.id()}-{f2.id()}',
            geom=Selection.geom_extract(f2.geometry()),
            domain='mapoutput',
            domain_geom='line',
            chan_type='',
            is_tv_layer=False,
            sel_type='selection',
            colour=None,
            lyrid=lyr.id()
        )
        self.assertEqual(item2, item)

    def test_pop_by_id(self):
        p = get_dataset_path('LINE_FROM_ORIGIN.gpkg', 'vector layer')
        lyr = QgsVectorLayer(str(p), 'LINE_FROM_ORIGIN', 'ogr')
        feats = list(lyr.getFeatures())
        f1, f2 = feats

        sel = Selection(lyr, [f1, f2])
        item = sel.pop(id_key=f'TUFLOW-VIEWER::::{lyr.id()}-{f1.id()}')
        item1 = SelectionItem(
            id_=f'TUFLOW-VIEWER::::{lyr.id()}-{f1.id()}',
            geom=Selection.geom_extract(f1.geometry()),
            domain='mapoutput',
            domain_geom='line',
            chan_type='',
            is_tv_layer=False,
            sel_type='selection',
            colour=None,
            lyrid=lyr.id()
        )
        self.assertEqual(item1, item)

    def test_drawn_selection_pop(self):
        p = get_dataset_path('LINE_FROM_ORIGIN.gpkg', 'vector layer')
        lyr = QgsVectorLayer(str(p), 'LINE_FROM_ORIGIN', 'ogr')
        feats = list(lyr.getFeatures())
        f1, f2 = feats

        marker = QgsVertexMarker(QGIS.iface.mapCanvas())
        marker.setColor(QColor('#000000'))
        sel = DrawnSelection(map_item=marker)
        item = list(sel)[0]
        sel += Selection(lyr, [f1, f2])

        drawn_item = sel.pop(sel_type='drawn')
        self.assertEqual(item, drawn_item)

    def test_geom_extract(self):
        point = QgsGeometry.fromWkt('POINT(1 2)')
        multi_point = QgsGeometry.fromWkt('MULTIPOINT((1 2),(3 4))')
        line = QgsGeometry.fromWkt('LINESTRING(1 2,3 4)')
        multi_line = QgsGeometry.fromWkt('MULTILINESTRING((1 2,3 4),(5 6,7 8))')
        polygon = QgsGeometry.fromWkt('POLYGON((1 2,3 4,5 6,1 2))')
        multi_polygon = QgsGeometry.fromWkt('MULTIPOLYGON(((1 2,3 4,5 6,1 2)),((7 8,9 10,11 12,7 8)))')

        self.assertEqual([1., 2.], Selection.geom_extract(point))
        self.assertEqual([1., 2.], Selection.geom_extract(multi_point))
        self.assertEqual([[1., 2.], [3., 4.]], Selection.geom_extract(line))
        self.assertEqual([[1., 2.], [3., 4.]], Selection.geom_extract(multi_line))
        self.assertEqual([[1., 2.], [3., 4.], [5., 6.], [1., 2.]], Selection.geom_extract(polygon))
        self.assertEqual([[1., 2.], [3., 4.], [5., 6.], [1., 2.]], Selection.geom_extract(multi_polygon))

    def test_plot_layer(self):
        plot_gpkg = get_dataset_path('EG15_001_PLOT.gpkg', 'result')
        plot_lyr = QgsVectorLayer(f'{plot_gpkg}|layername=EG15_001_PLOT_L', 'EG15_001_PLOT_L', 'ogr')
        plot_lyr.setCustomProperty('tuflow_viewer', '00001')
        get_viewer_instance()._outputs['00001'] = Output()
        feats = list(plot_lyr.getFeatures())

        sel = Selection(plot_lyr, feats[:2])
        item = sel.pop()

        self.assertTrue(item.is_tv_layer)
        self.assertEqual('channel', item.domain)

    def test_plot_layer_swmm(self):
        plot_gpkg = get_dataset_path('TS02_5m_001_swmm_ts.gpkg', 'result')
        plot_lyr = QgsVectorLayer(f'{plot_gpkg}|layername=TS02_5m_001_swmm_ts_L', 'TS02_5m_001_swmm_ts_L', 'ogr')
        plot_lyr.setCustomProperty('tuflow_viewer', '00001')
        get_viewer_instance()._outputs['00001'] = Output()
        feats = list(plot_lyr.getFeatures())

        sel = Selection(plot_lyr, feats[:2])
        item = sel.pop()

        self.assertTrue(item.is_tv_layer)
        self.assertEqual('channel', item.domain)

    def test_tuflow_cross_section(self):
        p = get_dataset_path('1d_xs_EG14_003_L.shp', 'result')
        lyr = QgsVectorLayer(str(p), '1d_xs_EG14_003_L', 'ogr')

        lyr.setCustomProperty('tuflow_viewer', '00001')
        output = Output()
        output.LAYER_TYPE = 'CrossSection'
        get_viewer_instance()._outputs['00001'] = output

        feat = list(lyr.getFeatures('"Column_1" = \'1d_xs_M14_ds1\''))[0]
        sel = Selection(lyr, [feat])
        item = sel.pop()
        self.assertEqual(r'..\csv\xsdb.csv:1d_xs_M14_ds1', item.id.split('::', 2)[1])

        p = get_dataset_path('1d_xs_EG14_001_L.shp', 'result')
        lyr = QgsVectorLayer(str(p), '1d_xs_EG14_001_L', 'ogr')
        lyr.setCustomProperty('tuflow_viewer', '00001')

        feat = [x for x in lyr.getFeatures() if x['Source'] == '..\\csv\\1d_xs_M14_ds1.csv'][0]
        sel = Selection(lyr, [feat])
        item = sel.pop()
        self.assertEqual(r'..\csv\1d_xs_M14_ds1.csv:1d_xs_M14_ds1', item.id.split('::', 2)[1])
