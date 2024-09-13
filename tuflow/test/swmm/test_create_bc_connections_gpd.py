import math
import geopandas as gpd
import pandas as pd
import subprocess
import unittest

from tuflow_swmm.gis_messages import GisMessages

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from test.swmm.test_files import get_compare_path, get_output_path, get_input_full_filenames

from tuflow.tuflow_swmm.create_bc_connections_gpd import create_bc_connections_gpd
from tuflow.tuflow_swmm.gis_to_swmm import gis_to_swmm
from tuflow.tuflow_swmm.gis_messages import GisMessages

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)


class TestSWMMDownstreamJunctionsToOutfalls(unittest.TestCase):
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



    def test_outfall_connections(self):
        input_filename = get_input_full_filenames(['xpx_create_bc_connections.gpkg'])[0]
        print(f'Creating outfall connections from: {input_filename}')

        output_filename = get_output_path('xpx_create_bc_connections_outfalls_out.geojson')
        compare_filename = get_compare_path('xpx_create_bc_connections_outfalls_out.geojson')

        gdf_all_links = gpd.read_file(input_filename, layer='All Links')

        gdf_outfalls = gpd.read_file(input_filename, layer='Outfalls')

        gis_messages = GisMessages()

        gdf_bc_connections = create_bc_connections_gpd(
            gdf_all_links,
            gdf_outfalls,
            True,
            2.0,
            15.0,
            True,
            gis_messages,
        )

        gdf_bc_connections.to_file(output_filename, driver='GeoJSON')

        self.compare_files(output_filename, compare_filename)

    def test_junction_connections(self):
        input_filename = get_input_full_filenames(['xpx_create_bc_connections.gpkg'])[0]
        print(f'Creating junction connections from: {input_filename}')

        output_filename = get_output_path('xpx_create_bc_connections_junctions_out.geojson')
        compare_filename = get_compare_path('xpx_create_bc_connections_junctions_out.geojson')

        gdf_all_links = gpd.read_file(input_filename, layer='All Links')

        gdf_junctions = gpd.read_file(input_filename, layer='Junctions')

        gis_messages = GisMessages()

        gdf_bc_connections = create_bc_connections_gpd(
            gdf_all_links,
            gdf_junctions,
            False,
            2.0,
            15.0,
            True,
            gis_messages,
        )

        gdf_bc_connections.to_file(output_filename, driver='GeoJSON')

        self.compare_files(output_filename, compare_filename)