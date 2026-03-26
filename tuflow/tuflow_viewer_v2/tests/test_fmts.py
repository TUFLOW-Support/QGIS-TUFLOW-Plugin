import json

from .stubs.qgis_stubs import QGIS

from qgis.core import QgsVectorLayer

from tuflow.tuflow_viewer_v2.fmts import (XMDF, TPC, GPKG1D, GPKG2D, GPKGRL, NCMesh, NCGrid, TuflowCrossSections,
                                          BCTablesCheck, HydTablesCheck, DAT, FMTS, DATCrossSections,
                                          CATCHJson, FVBCTide)
from ._utils import get_dataset_path, add_layer_to_qgis, add_layers_to_qgis, TuflowViewerTestCase


class TestFmts(TuflowViewerTestCase):

    def test_xmdf(self):
        p = get_dataset_path('run.xmdf', 'result')
        dat_sup = get_dataset_path('small_model_001.ALL.sup', 'result')

        self.assertTrue(XMDF.format_compatible(p))
        self.assertFalse(XMDF.format_compatible(dat_sup))

        res = XMDF(p)

        self.assertTrue(res._loaded)
        self.assertTrue(res.map_layers()[0].isValid())

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'XMDF',
                'id': res.id,
                'fpath': str(p),
                'name': 'run',
                '2dm': str(p.with_suffix('.2dm')),
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layer_to_qgis(res.map_layers()[0]):  # loading from json requires the layer to be in the project
            res2 = XMDF.from_json(json_str)
            self.assertTrue(res2._loaded)
            self.assertTrue(res2.map_layers()[0].isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_2dm(self):
        p = get_dataset_path('run.2dm', 'result')
        self.assertTrue(XMDF.format_compatible(p))

        res = XMDF(p)

        self.assertTrue(res._loaded)
        self.assertTrue(res.map_layers()[0].isValid())

        self.assertTrue(res._loaded)
        self.assertTrue(res.map_layers()[0].isValid())

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'XMDF',
                'id': res.id,
                'fpath': str(p),
                'name': 'run',
                '2dm': str(p.with_suffix('.2dm')),
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layer_to_qgis(res.map_layers()[0]):  # loading from json requires the layer to be in the project
            res2 = XMDF.from_json(json_str)
            self.assertTrue(res2._loaded)
            self.assertTrue(res2.map_layers()[0].isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_nc_mesh(self):
        p = get_dataset_path('fv_res.nc', 'result')
        xmdf = get_dataset_path('run.xmdf', 'result')
        ncgrid = get_dataset_path('small_model_001.nc', 'result')

        self.assertTrue(NCMesh.format_compatible(p))
        self.assertFalse(NCMesh.format_compatible(xmdf))
        self.assertFalse(NCMesh.format_compatible(ncgrid))

        res = NCMesh(p)

        self.assertTrue(res._loaded)
        self.assertTrue(res.map_layers()[0].isValid())

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'NCMesh',
                'id': res.id,
                'fpath': str(p),
                'name': 'fv_res',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layer_to_qgis(res.map_layers()[0]):  # loading from json requires the layer to be in the project
            res2 = NCMesh.from_json(json_str)
            self.assertTrue(res2._loaded)
            self.assertTrue(res2.map_layers()[0].isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_nc_grid(self):
        p = get_dataset_path('small_model_001.nc', 'result')

        self.assertTrue(NCGrid.format_compatible(p))

        res = NCGrid(p, layer_names=['water_level'])
        self.assertTrue(res._loaded)
        self.assertTrue(res.map_layers()[0].isValid())

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'NCGrid',
                'id': res.id,
                'fpath': str(p),
                'name': 'small_model_001_nc',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layer_to_qgis(res.map_layers()[0]):  # loading from json requires the layer to be in the project
            res2 = NCGrid.from_json(json_str)
            self.assertTrue(res2._loaded)
            self.assertTrue(res2.map_layers()[0].isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_tpc(self):
        p = get_dataset_path('EG15_001.tpc', 'result')

        self.assertTrue(TPC.format_compatible(p))

        res = TPC(p)

        self.assertTrue(res._loaded)
        self.assertEqual(2, len(res.map_layers()))
        for lyr in res.map_layers():
            self.assertTrue(lyr.isValid())

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'TPC',
                'id': res.id,
                'fpath': str(p),
                'name': 'EG15_001',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layers_to_qgis(res.map_layers()):  # loading from json requires the layer to be in the project
            res2 = TPC.from_json(json_str)
            self.assertTrue(res2._loaded)
            self.assertTrue(res._loaded)
            self.assertEqual(2, len(res.map_layers()))
            for lyr in res.map_layers():
                self.assertTrue(lyr.isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_gpkg_swmm(self):
        p = get_dataset_path('TS02_5m_001_swmm_ts.gpkg', 'result')

        self.assertTrue(GPKG1D.format_compatible(p))

        res = GPKG1D(p)

        self.assertTrue(res._loaded)
        self.assertEqual(2, len(res.map_layers()))
        for lyr in res.map_layers():
            self.assertTrue(lyr.isValid())

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'GPKG1D',
                'id': res.id,
                'fpath': str(p),
                'name': 'TS02_5m_001',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layers_to_qgis(res.map_layers()):  # loading from json requires the layer to be in the project
            res2 = GPKG1D.from_json(json_str)
            self.assertTrue(res2._loaded)
            self.assertTrue(res._loaded)
            self.assertEqual(2, len(res.map_layers()))
            for lyr in res.map_layers():
                self.assertTrue(lyr.isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_gpkg_1d(self):
        p = get_dataset_path('EG15_001_TS_1D.gpkg', 'result')

        self.assertTrue(GPKG1D.format_compatible(p))

        res = GPKG1D(p)

        self.assertTrue(res._loaded)
        self.assertEqual(2, len(res.map_layers()))
        for lyr in res.map_layers():
            self.assertTrue(lyr.isValid())

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'GPKG1D',
                'id': res.id,
                'fpath': str(p),
                'name': 'EG15_001',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layers_to_qgis(res.map_layers()):  # loading from json requires the layer to be in the project
            res2 = GPKG1D.from_json(json_str)
            self.assertTrue(res2._loaded)
            self.assertTrue(res._loaded)
            self.assertEqual(2, len(res.map_layers()))
            for lyr in res.map_layers():
                self.assertTrue(lyr.isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_gpkg_2d(self):
        p = get_dataset_path('EG15_001_TS_2D.gpkg', 'result')

        self.assertTrue(GPKG2D.format_compatible(p))

        res = GPKG2D(p)

        self.assertTrue(res._loaded)
        self.assertEqual(3, len(res.map_layers()))
        for lyr in res.map_layers():
            self.assertTrue(lyr.isValid())

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'GPKG2D',
                'id': res.id,
                'fpath': str(p),
                'name': 'EG15_001',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layers_to_qgis(res.map_layers()):  # loading from json requires the layer to be in the project
            res2 = GPKG2D.from_json(json_str)
            self.assertTrue(res2._loaded)
            self.assertTrue(res._loaded)
            self.assertEqual(3, len(res.map_layers()))
            for lyr in res.map_layers():
                self.assertTrue(lyr.isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_gpkg_rl(self):
        p = get_dataset_path('EG15_001_TS_RL.gpkg', 'result')

        self.assertTrue(GPKGRL.format_compatible(p))

        res = GPKGRL(p)

        self.assertTrue(res._loaded)
        self.assertEqual(3, len(res.map_layers()))
        for lyr in res.map_layers():
            self.assertTrue(lyr.isValid())

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'GPKGRL',
                'id': res.id,
                'fpath': str(p),
                'name': 'EG15_001',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layers_to_qgis(res.map_layers()):  # loading from json requires the layer to be in the project
            res2 = GPKGRL.from_json(json_str)
            self.assertTrue(res2._loaded)
            self.assertTrue(res._loaded)
            self.assertEqual(3, len(res.map_layers()))
            for lyr in res.map_layers():
                self.assertTrue(lyr.isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_tuflow_cross_sections(self):
        p = get_dataset_path('1d_xs_EG14_003_L.shp', 'result')

        self.assertTrue(TuflowCrossSections.format_compatible(p))

        lyr = QgsVectorLayer(str(p), '1d_xs_EG14_003_L', 'ogr')
        res = TuflowCrossSections(p, [lyr])
        self.assertEqual('1d_xs_EG14_003_L', res.name)
        self.assertFalse(res._loaded)  # result is lazy loaded, so this should be False at this stage

        res._complete_load()  # loads everything
        self.assertTrue(res._loaded)

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'TuflowCrossSections',
                'id': res.id,
                'fpath': str(p),
                'name': '1d_xs_EG14_003_L',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layers_to_qgis(res.map_layers()):  # loading from json requires the layer to be in the project
            res2 = TuflowCrossSections.from_json(json_str)
            self.assertFalse(res2._loaded)
            self.assertEqual(1, len(res.map_layers()))
            for lyr in res.map_layers():
                self.assertTrue(lyr.isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_2d_bc_tables_check(self):
        p = get_dataset_path('EG15_001_bcc_check_R.shp', 'result')
        p1 = get_dataset_path('EG15_001_2d_bc_tables_check.csv', 'result')

        self.assertTrue(BCTablesCheck.format_compatible(p))

        layer = QgsVectorLayer(str(p), 'EG15_001_bcc_check_R', 'ogr')
        res = BCTablesCheck(p, [layer])
        self.assertEqual('EG15_001_2d_bc_tables_check', res.name)
        self.assertFalse(res._loaded)

        res._complete_load()
        self.assertTrue(res._loaded)

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'BCTablesCheck',
                'id': res.id,
                'fpath': str(p1),
                'name': 'EG15_001_2d_bc_tables_check',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layers_to_qgis(res.map_layers()):  # loading from json requires the layer to be in the project
            res2 = BCTablesCheck.from_json(json_str)
            self.assertFalse(res2._loaded)
            self.assertEqual(1, len(res.map_layers()))
            for lyr in res.map_layers():
                self.assertTrue(lyr.isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_2d_bc_tables_check_sa(self):
        p = get_dataset_path('EG15_001_sac_check_R.shp', 'result')
        p1 = get_dataset_path('EG15_001_2d_bc_tables_check.csv', 'result')

        self.assertTrue(BCTablesCheck.format_compatible(p))

        layer = QgsVectorLayer(str(p), 'EG15_001_sac_check_R', 'ogr')
        res = BCTablesCheck(p, [layer])
        self.assertEqual('EG15_001_2d_bc_tables_check', res.name)
        self.assertFalse(res._loaded)

        res._complete_load()
        self.assertTrue(res._loaded)

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'BCTablesCheck',
                'id': res.id,
                'fpath': str(p1),
                'name': 'EG15_001_2d_bc_tables_check',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layers_to_qgis(res.map_layers()):  # loading from json requires the layer to be in the project
            res2 = BCTablesCheck.from_json(json_str)
            self.assertFalse(res2._loaded)
            self.assertEqual(1, len(res.map_layers()))
            for lyr in res.map_layers():
                self.assertTrue(lyr.isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_1d_bc_tables_check(self):
        p = get_dataset_path('EG14_001_1d_bc_check_P.shp', 'result')
        p1 = get_dataset_path('EG14_001_1d_bc_tables_check.csv', 'result')

        self.assertTrue(BCTablesCheck.format_compatible(p))
        self.assertFalse(HydTablesCheck.format_compatible(p))

        layer = QgsVectorLayer(str(p), 'EG14_001_1d_bc_check_P', 'ogr')
        res = BCTablesCheck(p, [layer])
        self.assertEqual('EG14_001_1d_bc_tables_check', res.name)
        self.assertFalse(res._loaded)

        res._complete_load()
        self.assertTrue(res._loaded)

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'BCTablesCheck',
                'id': res.id,
                'fpath': str(p1),
                'name': 'EG14_001_1d_bc_tables_check',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layers_to_qgis(res.map_layers()):  # loading from json requires the layer to be in the project
            res2 = BCTablesCheck.from_json(json_str)
            self.assertFalse(res2._loaded)
            self.assertEqual(1, len(res.map_layers()))
            for lyr in res.map_layers():
                self.assertTrue(lyr.isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_hyd_tables_check(self):
        p = get_dataset_path('EG14_001_hydprop_check_L.shp', 'result')
        p1 = get_dataset_path('EG14_001_1d_ta_tables_check.csv', 'result')

        self.assertTrue(HydTablesCheck.format_compatible(p))
        self.assertFalse(BCTablesCheck.format_compatible(p))

        layer = QgsVectorLayer(str(p), 'EG14_001_hydprop_check_L', 'ogr')
        res = HydTablesCheck(p, [layer])
        self.assertEqual('EG14_001_1d_ta_tables_check', res.name)
        self.assertFalse(res._loaded)

        res._complete_load()
        self.assertTrue(res._loaded)

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'HydTablesCheck',
                'id': res.id,
                'fpath': str(p1),
                'name': 'EG14_001_1d_ta_tables_check',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layers_to_qgis(res.map_layers()):  # loading from json requires the layer to be in the project
            res2 = HydTablesCheck.from_json(json_str)
            self.assertFalse(res2._loaded)
            self.assertEqual(1, len(res.map_layers()))
            for lyr in res.map_layers():
                self.assertTrue(lyr.isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_dat(self):
        p = get_dataset_path('small_model_001_h.dat', 'result')
        sup = get_dataset_path('small_model_001.ALL.sup', 'result')

        self.assertTrue(DAT.format_compatible(p))
        self.assertTrue(DAT.format_compatible(sup))

        res = DAT(p)
        res_sup = DAT(sup)

        self.assertTrue(res._loaded)
        self.assertTrue(res.map_layers()[0].isValid())

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'DAT',
                'id': res.id,
                'fpath': str(p),
                'name': 'small_model_001',
                '2dm': str(res.twodm),
                'dats': [str(p)],
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layer_to_qgis(res.map_layers()[0]):  # loading from json requires the layer to be in the project
            res2 = DAT.from_json(json_str)
            self.assertTrue(res2._loaded)
            self.assertTrue(res2.map_layers()[0].isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    def test_fm_ts(self):
        pgxy = get_dataset_path('FMT_M01_001.gxy','result')
        pdat = get_dataset_path('FMT_M01_001.dat', 'result')
        pzzn = get_dataset_path('FMT_M01_001.zzn', 'result')

        self.assertTrue(FMTS.format_compatible(pgxy))

        res = FMTS(pzzn, pdat, pgxy)
        self.assertTrue(res._loaded)

    def test_fm_ts_only_gxy(self):
        pgxy = get_dataset_path('FMT_M01_001.gxy', 'result')

        res = FMTS('', dat='', gxy=pgxy, bypass_dialog=True)
        self.assertTrue(res._loaded)

    def test_dat_cross_sections(self):
        p = get_dataset_path('River_Sections_w_Junctions.dat', 'result')

        self.assertTrue(DATCrossSections.format_compatible(p))
        self.assertFalse(DAT.format_compatible(p))

        res = DATCrossSections(p)
        self.assertTrue(res._loaded)
        self.assertEqual(9, len(res.cross_sections))
        self.assertTrue(res.map_layers()[0].isValid())

    def test_dat_cross_sections_via_fm_ts(self):
        pgxy = get_dataset_path('FMT_M01_001.gxy', 'result')
        pdat = get_dataset_path('FMT_M01_001.dat', 'result')
        pzzn = get_dataset_path('FMT_M01_001.zzn', 'result')

        res = FMTS(pzzn, pdat, pgxy)

        xs = DATCrossSections(res.dat.fpath, res.dat, res.gxy)
        self.assertTrue(xs._loaded)
        self.assertEqual(51, len(xs.cross_sections))

        self.assertTrue(xs.map_layers()[0].isValid())

        # all cross-section geometry should be valid
        for f in xs.map_layers()[0].getFeatures():
            self.assertFalse(f.geometry().isEmpty())

    def test_catch_json(self):
        p = get_dataset_path('res.tuflow.json', 'result')

        self.assertTrue(CATCHJson.format_compatible(p))

        res = CATCHJson(p)
        self.assertEqual(3, len(res.map_layers()))
        for lyr in res.map_layers():
            self.assertTrue(lyr.isValid())

        json_str = res.to_json()
        json_exp = json.dumps(
            {
                'class': 'CATCHJson',
                'id': res.id,
                'fpath': str(p),
                'name': 'res',
                'alias': 'res',
                'lyrids': [x.id() for x in res.map_layers()],
                'duplicated': [],
                'copied_files': {},
            }
        )
        self.assertEqual(json_exp, json_str)

        with add_layers_to_qgis(res.map_layers()):  # loading from json requires the layer to be in the project
            res2 = CATCHJson.from_json(json_str)
            for lyr in res2.map_layers():
                self.assertTrue(lyr.isValid())
            self.assertTrue(res.id, res2.id)
            self.assertEqual(res.map_layers(), res2.map_layers())

    # def test_catch_json_tmp(self):
    #     # doesn't matter if failed during regular tests. Testing with large dataset
    #     p = r"C:\TUFLOW\working\Cudgen_Creek_002\Cudgen_Creek.tuflow.json"
    #     res = CATCHJson(p)
    #     xmdf_ref_time = res.times(fmt='absolute')[0]
    #     for provider in res._providers.values():
    #         if provider.DRIVER_NAME == 'XMDF':
    #             self.assertEqual(xmdf_ref_time, provider.provider_reference_time())
    #             break

    def test_fv_bc_tide(self):
        from tuflow.tuflow_viewer_v2.tvctx_handler import is_fv_bc_tide_nc

        ncp = get_dataset_path('Cudgen_Tide.nc', 'result')
        gisp = get_dataset_path('2d_ns_Cudgen_004_OceanBoundary_L.shp', 'result')

        ns_lyr = QgsVectorLayer(str(gisp), '2d_ns_Cudgen_004_OceanBoundary_L', 'ogr')
        self.assertTrue(ns_lyr.isValid())

        self.assertTrue(is_fv_bc_tide_nc(ns_lyr))
        self.assertTrue(FVBCTide.format_compatible(ncp))

        res = FVBCTide(ncp, gisp, use_local_time=False, layers=[ns_lyr])
        self.assertTrue(res._loaded)
        for lyr in res.map_layers():
            self.assertTrue(lyr.isValid())
            if lyr.name().endswith('_pts'):
                self.assertTrue(lyr.featureCount() > 0)
