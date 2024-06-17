import math
import pandas as pd
import shutil
import subprocess
import unittest

import geopandas as gpd

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from test.swmm.test_files import get_compare_path, get_output_path, get_input_full_filenames

from tuflow.tuflow_swmm.convert_nonoutfall_sx_to_hx import convert_nonoutfall_sx_to_hx

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)


class TestXpxToSwmmConvert(unittest.TestCase):
    def compare_files(self, first, second):
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
                            '--no-index', first, second], shell=True)

            self.assertEqual(len(text1), len(text2))
            for line_num, (l1, l2) in enumerate(zip(text1, text2)):
                self.assertEqual(l1, l2, msg=f'Line: {line_num + 1}')

    def compare_gis_layers(self, first, second, layername):
        first_path = Path(first)
        second_path = Path(second)

        first_json_file = first_path.with_suffix('.geojson')
        first_json_file.unlink(missing_ok=True)

        gdf_first = gpd.read_file(first_path, layer=layername)
        gdf_first.to_file(first_json_file, driver='GeoJSON')

        second_json_file = Path(get_compare_path(f'{second_path.stem}.geojson'))
        gdf_second = gpd.read_file(second_path, layer=layername)
        gdf_second.to_file(second_json_file, driver='GeoJSON')

        self.compare_files(first_json_file, second_json_file)

    def compare_messages_file(self, messages_filename_gpkg):
        messages_json_file = messages_filename_gpkg.with_suffix('.geojson')
        messages_json_file.unlink(missing_ok=True)

        compare_messages_json_file = Path(get_compare_path(f'{messages_filename_gpkg.stem}.geojson'))

        gdf_messages_loc = gpd.read_file(messages_filename_gpkg, layer='Messages_with_locations')
        gdf_messages_loc.to_file(str(messages_json_file))

        self.compare_files(compare_messages_json_file, messages_json_file)

    def test_sx_to_hx_01(self):
        swmm_gpkg_file = get_input_full_filenames(['bc_sx_to_hx_convert_swmm.gpkg'])[0]

        bc_gpkg_input_filename = get_input_full_filenames(['bc_sx_to_hx_convert.gpkg'])[0]
        bc_gpkg_input_layername = '2d_bc_bad_sx_001'

        bc_gpkg_output_filename = get_output_path('bc_sx_to_hx_convert_out.gpkg')
        bc_gpkg_output_layername = '2d_bc_bad_sx_001'

        convert_nonoutfall_sx_to_hx(
            swmm_gpkg_file,
            bc_gpkg_input_filename,
            bc_gpkg_input_layername,
            [],
            bc_gpkg_output_filename,
            bc_gpkg_output_layername,
        )

        bc_gpkg_compare_filename = get_compare_path('bc_sx_to_hx_convert_out.gpkg')
        self.compare_gis_layers(bc_gpkg_compare_filename,
                                bc_gpkg_output_filename,
                                bc_gpkg_output_layername)

    def test_sx_to_hx_shapefile(self):
        swmm_gpkg_file = get_input_full_filenames(['bc_sx_to_hx_convert_swmm.gpkg'])[0]

        bc_gpkg_input_filename = get_input_full_filenames(['bc_sx_to_hx_convert_shp.shp'])[0]
        bc_gpkg_input_layername = None

        bc_gpkg_output_filename = get_output_path('bc_sx_to_hx_convert_shp_out.shp')
        bc_gpkg_output_layername = None

        convert_nonoutfall_sx_to_hx(
            swmm_gpkg_file,
            bc_gpkg_input_filename,
            bc_gpkg_input_layername,
            [],
            bc_gpkg_output_filename,
            bc_gpkg_output_layername,
        )

        bc_gpkg_compare_filename = get_compare_path('bc_sx_to_hx_convert_shp_out.shp')
        self.compare_gis_layers(bc_gpkg_compare_filename,
                                bc_gpkg_output_filename,
                                bc_gpkg_output_layername)

    def test_sx_to_hx_bad_colnames(self):
        swmm_gpkg_file = get_input_full_filenames(['bc_sx_to_hx_convert_swmm.gpkg'])[0]

        bc_gpkg_input_filename = get_input_full_filenames(['bc_sx_to_hx_convert_bad_colnames.gpkg'])[0]
        bc_gpkg_input_layername = '2d_bc_bad_sx_001'

        bc_gpkg_output_filename = get_output_path('bc_sx_to_hx_convert_bad_colnames_out.gpkg')
        bc_gpkg_output_layername = '2d_bc_bad_sx_001'

        convert_nonoutfall_sx_to_hx(
            swmm_gpkg_file,
            bc_gpkg_input_filename,
            bc_gpkg_input_layername,
            [],
            bc_gpkg_output_filename,
            bc_gpkg_output_layername,
        )

        bc_gpkg_compare_filename = get_compare_path('bc_sx_to_hx_convert_bad_colnames_out.gpkg')
        self.compare_gis_layers(bc_gpkg_compare_filename,
                                bc_gpkg_output_filename,
                                bc_gpkg_output_layername)

    def test_sx_to_hx_too_few_cols(self):
        swmm_gpkg_file = get_input_full_filenames(['bc_sx_to_hx_convert_swmm.gpkg'])[0]

        bc_gpkg_input_filename = get_input_full_filenames(['bc_sx_to_hx_convert_too_few_cols.gpkg'])[0]
        bc_gpkg_input_layername = '2d_bc_bad_sx_001'

        bc_gpkg_output_filename = get_output_path('bc_sx_to_hx_convert_too_few_cols_out.gpkg')
        bc_gpkg_output_layername = '2d_bc_bad_sx_001'
        Path(bc_gpkg_output_filename).unlink(missing_ok=True)

        self.assertRaises(ValueError,
                          convert_nonoutfall_sx_to_hx,
                          swmm_gpkg_file,
                          bc_gpkg_input_filename,
                          bc_gpkg_input_layername,
                          [],
                          bc_gpkg_output_filename,
                          bc_gpkg_output_layername,
                          )

    def test_sx_to_hx_inlets(self):
        swmm_gpkg_file = get_input_full_filenames(['bc_sx_to_hx_convert_swmm.gpkg'])[0]

        bc_gpkg_input_filename = get_input_full_filenames(['bc_sx_to_hx_convert.gpkg'])[0]
        bc_gpkg_input_layername = '2d_bc_bad_sx_001'

        bc_gpkg_output_filename = get_output_path('bc_sx_to_hx_convert_inlets_out.gpkg')
        bc_gpkg_output_layername = '2d_bc_bad_sx_001'
        Path(bc_gpkg_output_filename).unlink(missing_ok=True)

        inlet_usage_filelayers = [
            (get_input_full_filenames(['bc_sx_to_hx_convert_inlets.gpkg'])[0], 'inlet_usage'),
        ]

        convert_nonoutfall_sx_to_hx(
            swmm_gpkg_file,
            bc_gpkg_input_filename,
            bc_gpkg_input_layername,
            inlet_usage_filelayers,
            bc_gpkg_output_filename,
            bc_gpkg_output_layername,
        )

        bc_gpkg_compare_filename = get_compare_path('bc_sx_to_hx_convert_inlets_out.gpkg')
        self.compare_gis_layers(bc_gpkg_compare_filename,
                                bc_gpkg_output_filename,
                                bc_gpkg_output_layername)
