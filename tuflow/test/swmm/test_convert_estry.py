import itertools
import numpy as np
import os
import pandas as pd
from pathlib import Path
import subprocess
import unittest

has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false

from tuflow.tuflow_swmm.estry_to_swmm_gis_layers import convert_layers
from tuflow.tuflow_swmm.estry_to_swmm import array_from_csv, hw_curve_from_xz
from test.swmm.test_files import get_compare_path, get_input_full_filenames

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)


def default_convert_data():
    test_data = {
        'network_layers': [],
        'node_layers': [],
        'pit_layers': [],
        'table_link_layers': [],
        'inlet_dbase': None,
        'street_name': 'DummyStreet',
        'street_slope_pct': 4.0,
        'reference_cell_size': 5.0,
        'create_options_report_tables': True,
        'report_step': '00:05:00',
        'min_surface_area': 25.0,
        'snap_tolerance': 0.001,
        'swmm_out_filename': None,
        'ext_inlet_usage_filename': None,
        'crs': None
    }
    return test_data


def get_output_filenames(test_name):
    folder = os.path.dirname(__file__)

    output_filename = os.path.join(folder, "output", test_name)
    external_gpkg_filename = f'{output_filename}_ext'
    output_filename = output_filename + '.gpkg'
    external_gpkg_filename = external_gpkg_filename + '.gpkg'

    return output_filename, external_gpkg_filename


class TestEstryConvert(unittest.TestCase):
    def compare_files(self, first, second):
        first, second = second, first
        print(f'Comparing: {first} {second}')
        self.assertTrue(Path(first).exists(), 'File1 does not exist')
        self.assertTrue(Path(second).exists(), 'File2 does not exist')
        with (open(first, "r", encoding='utf-8', errors='ignore') as f1,
              open(second, "r", encoding='utf-8', errors='ignore') as f2):
            text1 = f1.readlines()
            text2 = f2.readlines()
            # print(text1)
            # print(text2)
            subprocess.run(['C:\\Program Files\\git\\cmd\\git.exe',
                            'diff',
                            '--no-index',
                            '--ignore-space-at-eol',
                            first, second], shell=True)

            self.assertEqual(len(text1), len(text2))
            for line_num, (l1, l2) in enumerate(zip(text1, text2)):
                self.assertEqual(l1, l2, msg=f'Line: {line_num + 1}')

    def compare_geopackage_files(self, first, second):
        df1 = gpd.read_file(first)
        df2 = gpd.read_file(second)

        df_compare = df1.compare(df2)
        self.assertEqual(len(df_compare), 0,
                         f'GeoPackage files not identical {df_compare.to_string()}')

    def test_read_xs_file(self):
        res_array = array_from_csv(
            get_input_full_filenames(
                [
                    'bg\\TC_B_0930.csv'
                ]
            )[0],
            ['x', 'z'],
        )
        correct_array = np.array([
            [0.0, 0.88],
            [0.35, 0.72],
            [1.1, 0.0],
            [2.8, 0.0],
            [3.55, 0.71],
            [3.9, 0.88],
        ])
        np.testing.assert_array_almost_equal(correct_array, res_array)

    def test_read_xs_file_mod(self):
        res_array = array_from_csv(
            get_input_full_filenames(
                [
                    'bg\\TC_B_0930_mod.csv'
                ]
            )[0],
            ['x', 'z'],
        )
        correct_array = np.array([
            [0.0, 0.88],
            [0.35, 0.72],
            [1.1, 0.0],
            [2.8, 0.0],
            [3.55, 0.71],
            [3.9, 0.88],
        ])
        np.testing.assert_array_almost_equal(correct_array, res_array)

    def test_create_hw_curves_from_csv(self):
        minval, maxval, df = hw_curve_from_xz(
            get_input_full_filenames(
                [
                    'bg\\TC_B_0930_mod.csv'
                ]
            )[0]
        )
        print(df)
        self.assertEqual(minval, 0.0)
        self.assertAlmostEqual(maxval, 0.88)
        self.assertAlmostEqual(0.818182, df['h'][2], places=4)
        self.assertAlmostEqual(3.659759, df['w'][2], places=4)

    def test_convert_bankstown(self):
        test_data = default_convert_data()

        test_data['crs'] = 'EPSG:32760'

        nwk_layers = [
            'C13_test_003_ECF.gpkg/1d_nwk_culverts_C13_007_L',
            'C13_test_003_ECF.gpkg/1d_nwk_pipes_C13_012_L',
            'C13_test_003_ECF.gpkg/1d_nwk_junctions_C13_012_P',
            'C13_test_003_ECF.gpkg/1d_nwk_outlets_C13_012_P',
            'C13_test_003_ECF.gpkg/1d_nwk_pits_C13_012_P',
        ]
        test_data['network_layers'] = get_input_full_filenames(nwk_layers)

        test_data['table_link_layers'] = get_input_full_filenames(
            [
                'C13_test_003_ECF.gpkg/1d_xs_culvert_C13_005_L',
            ]
        )
        test_data['inlet_dbase'] = get_input_full_filenames(
            [
                'pit_dbase\BIV_pit_dbase_001B.csv'
            ]
        )[0]

        (test_data['swmm_out_filename'],
         test_data['ext_inlet_usage_filename']) = \
            get_output_filenames('test_bankstown')

        convert_layers(**test_data)

        self.compare_files(Path(test_data['swmm_out_filename']).with_suffix('.inp'),
                           get_compare_path('test_bankstown.inp'))

    def test_convert_pipes(self):
        test_data = default_convert_data()

        test_data['crs'] = 'EPSG:32760'

        nwk_layers = [
            "1d_nwk_M07_Pipes_001_L.shp",
            "1d_nwk_M07_Pits_001_P.shp",
        ]
        test_data['network_layers'] = get_input_full_filenames(nwk_layers)

        (test_data['swmm_out_filename'],
         test_data['ext_inlet_usage_filename']) = \
            get_output_filenames('test_pipes_001')

        convert_layers(**test_data)

        self.compare_files(Path(test_data['swmm_out_filename']).with_suffix('.inp'),
                           get_compare_path('test_pipes_001.inp'))

        self.compare_geopackage_files(test_data['ext_inlet_usage_filename'],
                                      get_compare_path('test_pipes_001_ext.gpkg'))

    def test_convert_pipes_broken(self):
        test_data = default_convert_data()

        test_data['crs'] = 'EPSG:32760'

        nwk_layers = [
            "1d_nwk_M07_Pipes_001_L_Broken.shp",
            "1d_nwk_M07_Pits_001_P_Broken.shp",
        ]
        test_data['network_layers'] = get_input_full_filenames(nwk_layers)

        (test_data['swmm_out_filename'],
         test_data['ext_inlet_usage_filename']) = \
            get_output_filenames('test_pipes_broken_001')

        convert_layers(**test_data)

        self.compare_files(Path(test_data['swmm_out_filename']).with_suffix('.inp'),
                           get_compare_path('test_pipes_broken_001.inp'))

        # self.compare_geopackage_files(test_data['ext_inlet_usage_filename'],
        #                   get_compare_path('test_pipes_broken_001_ext.gpkg'))

    def test_convert_onechannelbase(self):
        test_data = default_convert_data()

        test_data['crs'] = 'EPSG:32760'

        nwk_layers = [
            'onechan_inputs.gpkg/1d_nwk_estry_chan_001_L',
        ]
        test_data['network_layers'] = get_input_full_filenames(nwk_layers)

        test_data['node_layers'] = get_input_full_filenames([
            'onechan_inputs.gpkg/1d_nd_estry_001_P',
        ]
        )

        (test_data['swmm_out_filename'],
         test_data['ext_inlet_usage_filename']) = \
            get_output_filenames('test_onechannel_base')

        convert_layers(**test_data)

        self.compare_files(Path(test_data['swmm_out_filename']).with_suffix('.inp'),
                           get_compare_path('test_onechannel_base.inp'))

        # self.compare_geopackage_files(test_data['ext_inlet_usage_filename'],
        #                   get_compare_path('test_pipes_001_ext.gpkg'))

    def test_convert_onechannelpump(self):
        test_data = default_convert_data()

        test_data['crs'] = 'EPSG:32760'

        nwk_layers = [
            'onechan_inputs.gpkg/1d_nwk_estry_pump_005_L',
        ]
        test_data['network_layers'] = get_input_full_filenames(nwk_layers)

        test_data['node_layers'] = get_input_full_filenames([
            'onechan_inputs.gpkg/1d_nd_estry_001_P',
        ]
        )

        (test_data['swmm_out_filename'],
         test_data['ext_inlet_usage_filename']) = \
            get_output_filenames('test_onechannel_pump')

        convert_layers(**test_data)

        self.compare_files(Path(test_data['swmm_out_filename']).with_suffix('.inp'),
                           get_compare_path('test_onechannel_pump.inp'))

        # self.compare_geopackage_files(test_data['ext_inlet_usage_filename'],
        #                   get_compare_path('test_pipes_001_ext.gpkg'))

    def test_convert_onechannelweir(self):
        test_data = default_convert_data()

        test_data['crs'] = 'EPSG:32760'

        nwk_layers = [
            'onechan_inputs.gpkg/1d_nwk_weir01_006_L',
        ]
        test_data['network_layers'] = get_input_full_filenames(nwk_layers)

        test_data['node_layers'] = get_input_full_filenames([
            'onechan_inputs.gpkg/1d_nd_extra_weir_001_P',
        ]
        )

        (test_data['swmm_out_filename'],
         test_data['ext_inlet_usage_filename']) = \
            get_output_filenames('test_onechannel_weir')

        convert_layers(**test_data)

        self.compare_files(Path(test_data['swmm_out_filename']).with_suffix('.inp'),
                           get_compare_path('test_onechannel_weir.inp'))

        # self.compare_geopackage_files(test_data['ext_inlet_usage_filename'],
        #                   get_compare_path('test_pipes_001_ext.gpkg'))

    def test_convert_onechannelsluice(self):
        test_data = default_convert_data()

        test_data['crs'] = 'EPSG:32760'

        nwk_layers = [
            'onechan_inputs.gpkg/1d_nwk_sg01_006_L',
        ]
        test_data['network_layers'] = get_input_full_filenames(nwk_layers)

        test_data['node_layers'] = get_input_full_filenames([
            'onechan_inputs.gpkg/1d_nd_extra_weir_001_P',
        ]
        )

        (test_data['swmm_out_filename'],
         test_data['ext_inlet_usage_filename']) = \
            get_output_filenames('test_onechannel_sluice')

        convert_layers(**test_data)

        self.compare_files(Path(test_data['swmm_out_filename']).with_suffix('.inp'),
                           get_compare_path('test_onechannel_sluice.inp'))

        # self.compare_geopackage_files(test_data['ext_inlet_usage_filename'],
        #                   get_compare_path('test_pipes_001_ext.gpkg'))

    def test_convert_onechannelqchan(self):
        test_data = default_convert_data()

        test_data['crs'] = 'EPSG:32760'

        nwk_layers = [
            'onechan_inputs.gpkg/1d_nwk_qchan01_006_L',
        ]
        test_data['network_layers'] = get_input_full_filenames(nwk_layers)

        test_data['node_layers'] = get_input_full_filenames([
            'onechan_inputs.gpkg/1d_nd_extra_weir_001_P',
        ]
        )

        (test_data['swmm_out_filename'],
         test_data['ext_inlet_usage_filename']) = \
            get_output_filenames('test_onechannel_qchan')

        convert_layers(**test_data)

        self.compare_files(Path(test_data['swmm_out_filename']).with_suffix('.inp'),
                           get_compare_path('test_onechannel_qchan.inp'))

    def test_convert_throsby_bridges(self):
        test_data = default_convert_data()

        test_data['crs'] = 'ESRI:102077'

        nwk_layers = [
            'Throsby_102_ecf.gpkg/1d_nwk_TC_struct_038_L',
            'Throsby_102_ecf.gpkg/1d_nwk_TC_struct_110_P'
        ]
        test_data['network_layers'] = get_input_full_filenames(nwk_layers)

        test_data['table_link_layers'] = get_input_full_filenames([
            'Throsby_102_ecf.gpkg/1d_xs_TCC_bridges_075_L',
            'Throsby_102_ecf.gpkg/1d_xs_TCC_struct_054_L',
        ]
        )

        (test_data['swmm_out_filename'],
         test_data['ext_inlet_usage_filename']) = \
            get_output_filenames('test_throsby_bridges')

        convert_layers(**test_data)

        self.compare_files(Path(test_data['swmm_out_filename']).with_suffix('.inp'),
                           get_compare_path('test_throsby_bridges.inp'))

        # self.compare_geopackage_files(test_data['ext_inlet_usage_filename'],
        #                   get_compare_path('test_pipes_001_ext.gpkg'))

    def test_convert_throsby_all(self):
        test_data = default_convert_data()

        test_data['crs'] = 'ESRI:102077'

        nwk_layers = [
            # 'Throsby_102_ecf.gpkg/1d_nwk_stability_068_P',
            'Throsby_102_ecf.gpkg/1d_nwk_TC_pipe_ILs_064_P',
            'Throsby_102_ecf.gpkg/1d_nwk_TC_struct_110_P',
            'Throsby_102_ecf.gpkg/1d_nwk_TCC_Jun05_pipe_ILs_074_P',
            'Throsby_102_ecf.gpkg/1d_nwk_TC_struct_038_L',
            'Throsby_102_ecf.gpkg/1d_nwk_TC_pipes_056_L',
            'Throsby_102_ecf.gpkg/1d_nwk_TCC_jun05_pipes_074_L',
        ]
        test_data['network_layers'] = get_input_full_filenames(nwk_layers)

        test_data['table_link_layers'] = get_input_full_filenames([
            'Throsby_102_ecf.gpkg/1d_xs_TCC_bridges_075_L',
            'Throsby_102_ecf.gpkg/1d_xs_TCC_struct_054_L',
        ]
        )

        (test_data['swmm_out_filename'],
         test_data['ext_inlet_usage_filename']) = \
            get_output_filenames('test_throsby_all')

        convert_layers(**test_data)

        self.compare_files(Path(test_data['swmm_out_filename']).with_suffix('.inp'),
                           get_compare_path('test_throsby_all.inp'))

        # self.compare_geopackage_files(test_data['ext_inlet_usage_filename'],
        #                   get_compare_path('test_pipes_001_ext.gpkg'))

    @unittest.skip("This has not been fully implemented. Need to finish and test")
    def test_convert_bankstown_xs(self):
        test_data = default_convert_data()

        test_data['crs'] = 'EPSG:32760'

        nwk_layers = [
        ]
        test_data['network_layers'] = get_input_full_filenames(nwk_layers)

        test_data['node_layers'] = get_input_full_filenames([
        ]
        )

        test_data['table_link_layers'] = get_input_full_filenames([
            'C13_test_003_ECF.gpkg/1d_xs_culvert_C13_005_L',
        ])

        (test_data['swmm_out_filename'],
         test_data['ext_inlet_usage_filename']) = \
            get_output_filenames('test_bankstown_xs')

        convert_layers(**test_data)

        self.compare_files(Path(test_data['swmm_out_filename']).with_suffix('.inp'),
                           get_compare_path('test_bankstown_xs.inp'))

        # self.compare_geopackage_files(test_data['ext_inlet_usage_filename'],
        #                   get_compare_path('test_pipes_001_ext.gpkg'))

    def test_convert_bankstown_pits(self):
        test_data = default_convert_data()

        test_data['crs'] = 'EPSG:32760'

        nwk_layers = [
        ]
        test_data['network_layers'] = get_input_full_filenames(nwk_layers)

        test_data['node_layers'] = get_input_full_filenames([
        ]
        )

        test_data['table_link_layers'] = get_input_full_filenames([
        ])

        test_data['inlet_dbase'] = get_input_full_filenames([
            'pit_dbase\BIV_pit_dbase_001B.csv'
        ])[0]

        (test_data['swmm_out_filename'],
         test_data['ext_inlet_usage_filename']) = \
            get_output_filenames('test_bankstown_pits')

        convert_layers(**test_data)

        self.compare_files(Path(test_data['swmm_out_filename']).with_suffix('.inp'),
                           get_compare_path('test_bankstown_pits.inp'))

        # self.compare_geopackage_files(test_data['ext_inlet_usage_filename'],
        #                   get_compare_path('test_pipes_001_ext.gpkg'))
