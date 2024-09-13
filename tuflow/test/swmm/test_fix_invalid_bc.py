import math
import pandas as pd
import shutil
import subprocess
import unittest

import fiona
import geopandas as gpd

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from test.swmm.test_files import get_compare_path, get_output_path, get_input_full_filenames

from tuflow.tuflow_swmm.fix_invalid_bc_connections import fix_invalid_bc_connections

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)


class TestFixInvalidBC(unittest.TestCase):
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
                            '--no-index',
                            '--ignore-space-at-eol',
                            first, second], shell=True)

            self.assertEqual(len(text1), len(text2))
            for line_num, (l1, l2) in enumerate(zip(text1, text2)):
                self.assertEqual(l1, l2, msg=f'Line: {line_num + 1}')

    def compare_gis_layers(self, first, second, layername):
        first_path = Path(first)
        second_path = Path(second)

        first_json_file = first_path.with_suffix('.geojson')
        print(first_json_file)
        first_json_file.unlink(missing_ok=True)

        layernames = [layername]

        if layername is None:
            # See if the layernames match
            layers1 = sorted(fiona.listlayers(first_path))
            layers2 = sorted(fiona.listlayers(second_path))
            self.assertEqual(layers1, layers2)

            layernames = layers1

        for layername in layernames:
            gdf_first = gpd.read_file(first_path, layer=layername)
            gdf_first.to_file(first_json_file, driver='GeoJSON')

            second_json_file = Path(second_path.with_suffix('.geojson'))
            second_json_file.unlink(missing_ok=True)

            gdf_second = gpd.read_file(second_path, layer=layername)
            gdf_second.to_file(second_json_file, driver='GeoJSON')

            self.compare_files(first_json_file, second_json_file)

            # If we get here (no errors) go ahead and delete the json files
            first_json_file.unlink(missing_ok=True)
            second_json_file.unlink(missing_ok=True)

    def compare_messages_file(self, messages_filename_gpkg):
        messages_json_file = messages_filename_gpkg.with_suffix('.geojson')
        messages_json_file.unlink(missing_ok=True)

        compare_messages_json_file = Path(get_compare_path(f'{messages_filename_gpkg.stem}.geojson'))

        gdf_messages_loc = gpd.read_file(messages_filename_gpkg, layer='Messages_with_locations')
        gdf_messages_loc.to_file(str(messages_json_file))

        self.compare_files(compare_messages_json_file, messages_json_file)

    def test_fix_bc_001(self):
        swmm_gpkg_file = get_input_full_filenames(['fix_bc_conn/fixbc_swmm_001.gpkg'])[0]

        bc_connections_filenames = get_input_full_filenames(
            [
                'fix_bc_conn/fixbc_gis_layers_1d_001.gpkg',
                'fix_bc_conn/fixbc_2d_bc_001.gpkg',
            ]
        )

        bc_connections_layernames = [
            '2d_bc_swmm_connections_001',
            '2d_bc_L_001'
        ]
        gdfs_bc_connections = [
            gpd.read_file(x, layer=y) for x, y in zip(bc_connections_filenames, bc_connections_layernames)
        ]
        length_dummy_inflows = 20.0
        length_dummy_outflows = 10.0

        output_swmm_gpkg = get_output_path('fix_bc_conn/fixbc_swmm_001_out.gpkg')
        output_connection_file_and_layernames = [
            (get_output_path('fix_bc_conn/fixbc_gis_layers_1d_001_out.gpkg'), '2d_bc_swmm_connections_002'),
            (get_output_path('fix_bc_conn/fixbc_2d_bc_001_out.pkg'), '2d_bc_L_002')
        ]
        Path(output_swmm_gpkg).parent.mkdir(exist_ok=True)

        fix_invalid_bc_connections(swmm_gpkg_file,
                                   output_swmm_gpkg,
                                   length_dummy_inflows,
                                   length_dummy_outflows,
                                   gdfs_bc_connections,
                                   True,
                                   output_connection_file_and_layernames,
                                   None)

        # None compares all layers
        swmm_gpkg_compare = get_compare_path('fix_bc_conn/fixbc_swmm_001_out.gpkg')
        self.compare_gis_layers(swmm_gpkg_compare,
                                output_swmm_gpkg,
                                None)

        # only swmm connection layers get modified (writtenout)
        swmm_bc_compare = get_compare_path('fix_bc_conn/fixbc_gis_layers_1d_001_out.gpkg')
        self.compare_gis_layers(swmm_bc_compare,
                                get_output_path('fix_bc_conn/fixbc_gis_layers_1d_001_out.gpkg'),
                                '2d_bc_swmm_connections_002')

    def test_fix_bc_storage(self):
        swmm_gpkg_file = get_input_full_filenames(['fix_bc_conn/fixbc_swmm_storage.gpkg'])[0]

        bc_connections_filenames = get_input_full_filenames(
            [
                'fix_bc_conn/fixbc_gis_layers_1d_storage.gpkg',
                'fix_bc_conn/fixbc_2d_bc_storage.gpkg',
            ]
        )

        bc_connections_layernames = [
            '2d_bc_swmm_connections_001',
            '2d_bc_L_001'
        ]
        gdfs_bc_connections = [
            gpd.read_file(x, layer=y) for x, y in zip(bc_connections_filenames, bc_connections_layernames)
        ]
        length_dummy_inflows = 20.0
        length_dummy_outflows = 10.0

        output_swmm_gpkg = get_output_path('fix_bc_conn/fixbc_swmm_storage_out.gpkg')
        output_connection_file_and_layernames = [
            (get_output_path('fix_bc_conn/fixbc_gis_layers_1d_storage_out.gpkg'), '2d_bc_swmm_connections_002'),
            (get_output_path('fix_bc_conn/fixbc_2d_bc_storage_out.pkg'), '2d_bc_L_002')
        ]
        Path(output_swmm_gpkg).parent.mkdir(exist_ok=True)

        fix_invalid_bc_connections(swmm_gpkg_file,
                                   output_swmm_gpkg,
                                   length_dummy_inflows,
                                   length_dummy_outflows,
                                   gdfs_bc_connections,
                                   True,
                                   output_connection_file_and_layernames,
                                   None)

        # None compares all layers
        swmm_gpkg_compare = get_compare_path('fix_bc_conn/fixbc_swmm_storage_out.gpkg')
        self.compare_gis_layers(swmm_gpkg_compare,
                                output_swmm_gpkg,
                                None)

        # only swmm connection layers get modified (writtenout)
        swmm_bc_compare = get_compare_path('fix_bc_conn/fixbc_gis_layers_1d_storage_out.gpkg')
        self.compare_gis_layers(swmm_bc_compare,
                                get_output_path('fix_bc_conn/fixbc_gis_layers_1d_storage_out.gpkg'),
                                '2d_bc_swmm_connections_002')

    def test_sx_to_hx_01(self):
        swmm_gpkg_file = get_input_full_filenames(['fix_bc_conn/bc_sx_to_hx_convert_swmm.gpkg'])[0]

        bc_connections_filenames = get_input_full_filenames(
            [
                'fix_bc_conn/bc_sx_to_hx_convert.gpkg',
            ]
        )

        bc_connections_layernames = [
            '2d_bc_bad_sx_001'
        ]
        gdfs_bc_connections = [
            gpd.read_file(x, layer=y) for x, y in zip(bc_connections_filenames, bc_connections_layernames)
        ]

        output_swmm_gpkg = get_output_path('fix_bc_conn/bc_sx_to_hx_convert_swmm_out.gpkg')
        output_connection_file_and_layernames = [
            (get_output_path('fix_bc_conn/fixbc_gis_layers_sx_to_hx_out.gpkg'), '2d_bc_bad_sx_001'),
        ]
        Path(output_swmm_gpkg).parent.mkdir(exist_ok=True)

        length_dummy_inflows = 20.0
        length_dummy_outflows = 10.0

        fix_invalid_bc_connections(swmm_gpkg_file,
                                   output_swmm_gpkg,
                                   length_dummy_inflows,
                                   length_dummy_outflows,
                                   gdfs_bc_connections,
                                   True,
                                   output_connection_file_and_layernames,
                                   None)

        # None compares all layers
        swmm_gpkg_compare = get_compare_path('fix_bc_conn/bc_sx_to_hx_convert_swmm_out.gpkg')
        self.compare_gis_layers(swmm_gpkg_compare,
                                output_swmm_gpkg,
                                None)

        # only swmm connection layers get modified (writtenout)
        swmm_bc_compare = get_compare_path('fix_bc_conn/fixbc_gis_layers_sx_to_hx_out.gpkg')
        self.compare_gis_layers(swmm_bc_compare,
                                get_output_path('fix_bc_conn/fixbc_gis_layers_sx_to_hx_out.gpkg'),
                                '2d_bc_bad_sx_001')

    def test_sx_to_hx_inlets(self):
        swmm_gpkg_file = get_input_full_filenames(['fix_bc_conn/bc_sx_to_hx_convert_swmm.gpkg'])[0]

        bc_connections_filenames = get_input_full_filenames(
            [
                'fix_bc_conn/bc_sx_to_hx_convert.gpkg',
            ]
        )

        bc_connections_layernames = [
            '2d_bc_bad_sx_001'
        ]
        gdfs_bc_connections = [
            gpd.read_file(x, layer=y) for x, y in zip(bc_connections_filenames, bc_connections_layernames)
        ]

        inlet_usage_filelayers = [
            (get_input_full_filenames(['fix_bc_conn/bc_sx_to_hx_convert_inlets.gpkg'])[0], 'inlet_usage'),
        ]
        gdfs_inlets = [
            gpd.read_file(x[0], layer=x[1]) for x in inlet_usage_filelayers
        ]

        output_swmm_gpkg = get_output_path('fix_bc_conn/bc_sx_to_hx_convert_inlets_swmm_out.gpkg')
        output_connection_file_and_layernames = [
            (get_output_path('fix_bc_conn/fixbc_gis_layers_sx_to_hx_inlets_out.gpkg'), '2d_bc_bad_sx_001'),
        ]
        Path(output_swmm_gpkg).parent.mkdir(exist_ok=True)

        length_dummy_inflows = 20.0
        length_dummy_outflows = 10.0

        fix_invalid_bc_connections(swmm_gpkg_file,
                                   output_swmm_gpkg,
                                   length_dummy_inflows,
                                   length_dummy_outflows,
                                   gdfs_bc_connections,
                                   True,
                                   output_connection_file_and_layernames,
                                   gdfs_inlets)

        # None compares all layers
        swmm_gpkg_compare = get_compare_path('fix_bc_conn/bc_sx_to_hx_convert_inlets_swmm_out.gpkg')
        self.compare_gis_layers(swmm_gpkg_compare,
                                output_swmm_gpkg,
                                None)

        # only swmm connection layers get modified (writtenout)
        swmm_bc_compare = get_compare_path('fix_bc_conn/fixbc_gis_layers_sx_to_hx_inlets_out.gpkg')
        self.compare_gis_layers(swmm_bc_compare,
                                get_output_path('fix_bc_conn/fixbc_gis_layers_sx_to_hx_inlets_out.gpkg'),
                                '2d_bc_bad_sx_001')
