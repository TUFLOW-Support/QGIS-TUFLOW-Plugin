import math
import pandas as pd
import subprocess
import unittest

import geopandas as gpd

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from test.swmm.test_files import get_compare_path, get_output_path, get_input_full_filenames

from tuflow_swmm.xpswmm_xpx_to_gpkg import xpx_to_gpkg

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
            subprocess.run(['git', 'diff', '--no-index', first, second])

            self.assertEqual(len(text1), len(text2))
            for line_num, (l1, l2) in enumerate(zip(text1, text2)):
                self.assertEqual(l1, l2, msg=f'Line: {line_num + 1}')

    def compare_messages_file(self, messages_filename_gpkg):
        messages_json_file = messages_filename_gpkg.with_suffix('.geojson')
        messages_json_file.unlink(missing_ok=True)

        compare_messages_json_file = Path(get_compare_path(f'{messages_filename_gpkg.stem}.geojson'))

        gdf_messages_loc = gpd.read_file(messages_filename_gpkg, layer='Messages_with_locations')
        gdf_messages_loc.to_file(str(messages_json_file))

        self.compare_files(compare_messages_json_file, messages_json_file)

    def test_urban1(self):
        urban_input_file = get_input_full_filenames(
            [
                'xpx_urban_001.xpx',
            ]
        )[0]
        intermediate_file = get_output_path('xpx_urban_001_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)
        compare_file = get_compare_path('xpx_urban_001_out.inp')

        iu_output_file = Path(get_output_path('xpx_urban_iu_001_out.gpkg'))
        iu_output_file.unlink(missing_ok=True)
        # iu_compare_file = get_compare_path('xpx_urban_iu_001_out.inp')

        messages_file = Path(get_output_path('xpx_urban_001_out_messages.gpkg'))

        crs = 'EPSG:32760'
        xpx_to_gpkg(urban_input_file, intermediate_file, iu_output_file, messages_file, crs)

        # Happens in xpx_to_gpkg now
        # print('\n\nConverting to inp')
        # gis_to_swmm(lid_intermediate_file, lid_output_file)

        self.compare_files(compare_file, output_file)

        self.compare_messages_file(messages_file)

    def test_shapes1(self):
        input_file = get_input_full_filenames(
            [
                'xpx_shapes_001.xpx',
            ]
        )[0]
        intermediate_file = get_output_path('xpx_shapes_001_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)
        compare_file = get_compare_path('xpx_shapes_001_out.inp')

        iu_output_file = Path(get_output_path('xpx_shapes_iu_001_out.gpkg'))
        iu_output_file.unlink(missing_ok=True)

        messages_file = Path(get_output_path('xpx_shapes_001_messages.gpkg'))
        messages_file.unlink(missing_ok=True)

        crs = 'EPSG:32760'
        xpx_to_gpkg(input_file, intermediate_file, iu_output_file, messages_file, crs)

        self.compare_files(compare_file, output_file)

        self.compare_messages_file(messages_file)

    def test_natural_channel1(self):
        input_file = get_input_full_filenames(
            [
                'xpx_natural_channel_01.xpx',
            ]
        )[0]
        intermediate_file = get_output_path('xpx_natural_channel_01_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)
        compare_file = get_compare_path('xpx_natural_channel_01_out.inp')

        iu_output_file = Path(get_output_path('xpx_natural_channel_iu_001_out.gpkg'))
        iu_output_file.unlink(missing_ok=True)

        messages_file = Path(get_output_path('xpx_natural_channel_01_messages.gpkg'))
        messages_file.unlink(missing_ok=True)

        crs = 'EPSG:32760'
        xpx_to_gpkg(input_file, intermediate_file, iu_output_file, messages_file, crs)

        self.compare_files(compare_file, output_file)

        self.compare_messages_file(messages_file)

    def test_noninlet_1d2d_connections(self):
        # XPSWMM models can define a connection to the invert or spill crest without an inlet.
        # For TUFLOW-SWMM, connections to inverts are usually included in 2d_bc as HX or SX polylines outside of the xpx
        #   connections to the spill crest are only analogous to inlets so they should probably be added.
        # For now, connections will be exported into a messages GeoPackage file to deal with separately
        input_file = get_input_full_filenames(
            [
                'xpx_connections_1d2d.xpx',
            ]
        )[0]
        intermediate_file = get_output_path('xpx_connections_1d2d_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)
        compare_file = get_compare_path('xpx_connections_1d2d_out.inp')

        iu_output_file = Path(get_output_path('xpx_connections_1d2d_iu_001_out.gpkg'))
        iu_output_file.unlink(missing_ok=True)

        output_messages_file = Path(get_output_path('xpx_connections_1d2d_messages.gpkg'))
        output_messages_file.unlink(missing_ok=True)

        crs = 'EPSG:32760'
        xpx_to_gpkg(input_file, intermediate_file, iu_output_file, output_messages_file, crs)
        self.compare_files(compare_file, output_file)

        self.compare_messages_file(output_messages_file)

    def test_bc_inflows(self):
        input_file = get_input_full_filenames(
            [
                'xpx_inflows_001.xpx',
            ]
        )[0]
        intermediate_file = get_output_path('xpx_inflows_001_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)
        compare_file = get_compare_path('xpx_inflows_001_out.inp')

        iu_output_file = Path(get_output_path('xpx_inflows_iu_001_out.gpkg'))
        iu_output_file.unlink(missing_ok=True)

        messages_file = Path(get_output_path('xpx_inflows_001_messages.gpkg'))
        messages_file.unlink(missing_ok=True)

        crs = 'EPSG:32760'
        xpx_to_gpkg(input_file, intermediate_file, iu_output_file, messages_file, crs)

        self.compare_files(compare_file, output_file)

        self.compare_messages_file(messages_file)

    def test_inactive(self):
        input_file = get_input_full_filenames(
            [
                'xpx_inactive_001.xpx',
            ]
        )[0]
        intermediate_file = get_output_path('xpx_inactive_001_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)
        compare_file = get_compare_path('xpx_inactive_001_out.inp')

        iu_output_file = Path(get_output_path('xpx_inactive_iu_001_out.gpkg'))
        iu_output_file.unlink(missing_ok=True)

        messages_file = Path(get_output_path('xpx_inactive_001_messages.gpkg'))
        messages_file.unlink(missing_ok=True)

        crs = 'EPSG:32760'
        xpx_to_gpkg(input_file, intermediate_file, iu_output_file, messages_file, crs)

        self.compare_files(compare_file, output_file)

        self.compare_messages_file(messages_file)
