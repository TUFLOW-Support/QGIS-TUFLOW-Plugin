import math
import pandas as pd
import unittest

import geopandas as gpd

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from test.swmm.test_files import get_compare_path, get_output_path, get_input_full_filenames

from tuflow_swmm.gis_to_swmm import gis_to_swmm
from tuflow_swmm.swmm_to_gis import swmm_to_gpkg

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)


class TestSWMMShapeConvert(unittest.TestCase):
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
            self.assertEqual(len(text1), len(text2))
            for line_num, (l1, l2) in enumerate(zip(text1, text2)):
                self.assertEqual(l1, l2, msg=f'Line: {line_num + 1}')

    def test_LIDExample(self):
        lid_input_file = get_input_full_filenames(
            [
                'LID_Model_ex.inp',
            ]
        )[0]
        lid_intermediate_file = get_output_path('LID_Model_ex_out.gpkg')
        lid_output_file = Path(lid_intermediate_file).with_suffix('.inp')
        Path(lid_intermediate_file).unlink(missing_ok=True)
        lid_output_file.unlink(missing_ok=True)

        lid_compare_file = get_compare_path('LID_Model_ex_compare.inp')

        crs = 'EPSG:32760'
        swmm_to_gpkg(lid_input_file, lid_intermediate_file, crs)

        print('\n\nConverting to inp')
        gis_to_swmm(lid_intermediate_file, lid_output_file)

        self.compare_files(lid_compare_file, lid_output_file)

    def test_ExternalFiles(self):
        base_filename = 'swmm_demo_w_files'
        input_file = get_input_full_filenames(
            [
               f'{base_filename}.inp',
            ]
        )[0]
        intermediate_file = get_output_path(f'{base_filename}_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)

        compare_file = get_compare_path(f'{base_filename}_compare.inp')

        crs = 'EPSG:32760'
        swmm_to_gpkg(input_file, intermediate_file, crs)

        print('\n\nConverting to inp')
        gis_to_swmm(intermediate_file, output_file)

        self.compare_files(compare_file, output_file)

    def test_Transects(self):
        base_filename = 'test_openchannel'
        input_file = get_input_full_filenames(
            [
               f'{base_filename}.inp',
            ]
        )[0]
        intermediate_file = get_output_path(f'{base_filename}_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)

        compare_file = get_compare_path(f'{base_filename}_compare.inp')

        crs = 'EPSG:32760'
        swmm_to_gpkg(input_file, intermediate_file, crs)

        print('\n\nConverting to inp')
        gis_to_swmm(intermediate_file, output_file)

        self.compare_files(compare_file, output_file)

    def test_Temperature(self):
        base_filename = 'HargreavesETexample_temperature'
        input_file = get_input_full_filenames(
            [
               f'{base_filename}.inp',
            ]
        )[0]
        intermediate_file = get_output_path(f'{base_filename}_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)

        compare_file = get_compare_path(f'{base_filename}_compare.inp')

        crs = 'EPSG:32760'
        swmm_to_gpkg(input_file, intermediate_file, crs)

        print('\n\nConverting to inp')
        gis_to_swmm(intermediate_file, output_file)

        self.compare_files(compare_file, output_file)

    def test_brsSubcatchments(self):
        base_filename = 'bsr_subcatchments_001'
        input_file = get_input_full_filenames(
            [
                f'{base_filename}.inp',
            ]
        )[0]
        intermediate_file = get_output_path(f'{base_filename}_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)

        compare_file = get_compare_path(f'{base_filename}_compare.inp')

        crs = 'EPSG:32760'
        swmm_to_gpkg(input_file, intermediate_file, crs)

        print('\n\nConverting to inp')
        self.assertRaises(ValueError, gis_to_swmm, intermediate_file, output_file)
        #self.compare_files(compare_file, output_file)

    def test_tags_descriptions(self):
        base_filename = 'test_tags_descriptions'
        input_file = get_input_full_filenames(
            [
                f'{base_filename}.inp',
            ]
        )[0]
        intermediate_file = get_output_path(f'{base_filename}_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)

        compare_file = get_compare_path(f'{base_filename}_compare.inp')

        crs = 'EPSG:32760'
        swmm_to_gpkg(input_file, intermediate_file, crs)

        print('\n\nConverting to inp')
        gis_to_swmm(intermediate_file, output_file)
        self.compare_files(compare_file, output_file)

    def test_tags2(self):
        base_filename = 'test_tags_swmm_tutorial'
        input_file = get_input_full_filenames(
            [
                f'{base_filename}.inp',
            ]
        )[0]
        intermediate_file = get_output_path(f'{base_filename}_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)

        compare_file = get_compare_path(f'{base_filename}_compare.inp')

        crs = 'EPSG:32760'
        swmm_to_gpkg(input_file, intermediate_file, crs)

        print('\n\nConverting to inp')
        gis_to_swmm(intermediate_file, output_file)
        self.compare_files(compare_file, output_file)

    def test_date_convert(self):
        base_filename = 'HargreavesETexample_temperature_for_time'
        input_file = get_input_full_filenames(
            [
                f'{base_filename}.inp',
            ]
        )[0]
        intermediate_file = get_output_path(f'{base_filename}_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)

        compare_file = get_compare_path(f'{base_filename}_compare.inp')

        crs = 'EPSG:32760'
        swmm_to_gpkg(input_file, intermediate_file, crs)

        # Make sure it converted to yyyy-mm-dd format in GeoPackage file
        gdf_options = gpd.read_file(intermediate_file, layer='Project--Options')

        # START_DATE 10/01/2009 -> 2009-10-01
        #print(gdf_options.loc[gdf_options['Option'] == 'START_DATE', 'Value'].iloc[0])
        self.assertEqual('2009-10-01', gdf_options.loc[gdf_options['Option'] == 'START_DATE', 'Value'].iloc[0])

        # REPORT_START_DATE 01/01/1920
        self.assertEqual('1920-01-01', gdf_options.loc[
            gdf_options['Option'] == 'REPORT_START_DATE', 'Value'].iloc[0])

        # END_DATE 09/30/2010
        self.assertEqual('2010-09-30', gdf_options.loc[
            gdf_options['Option'] == 'END_DATE', 'Value'].iloc[0])

        print('\n\nConverting to inp')
        gis_to_swmm(intermediate_file, output_file)
        self.compare_files(compare_file, output_file)

    # Created when we had an issue with infiltration coming through
    def test_infiltration(self):
        base_filename = 'EG15_005_subcatchments_test_convert'
        input_file = get_input_full_filenames(
            [
                f'{base_filename}.inp',
            ]
        )[0]
        intermediate_file = get_output_path(f'{base_filename}_out.gpkg')
        output_file = Path(intermediate_file).with_suffix('.inp')
        Path(intermediate_file).unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)

        compare_file = get_compare_path(f'{base_filename}_compare.inp')

        crs = 'EPSG:32760'
        swmm_to_gpkg(input_file, intermediate_file, crs)

        print('\n\nConverting to inp')
        gis_to_swmm(intermediate_file, output_file)
        self.compare_files(compare_file, output_file)


    # This test was to provide an error message if the number of values written to an inp file
    # was less than required by the format. This functionality has been delayed to look at higher value efforts
    # Uncomment and finish when time permits
    # def test_onechannel_incomplete(self):
    #     # This one starts with GeoPackage so different approach
    #     base_filename = 'test_onechannel_base_incomplete'
    #     input_file = get_input_full_filenames(
    #         [
    #             f'{base_filename}.gpkg',
    #         ]
    #     )[0]
    #     #intermediate_file = get_output_path(f'{base_filename}_out.gpkg')
    #     #output_file = Path(intermediate_file).with_suffix('.inp')
    #     output_file = Path(get_output_path(f'{base_filename}_out.inp'))
    #     #Path(intermediate_file).unlink(missing_ok=True)
    #     output_file.unlink(missing_ok=True)
    #
    #     compare_file = get_compare_path(f'{base_filename}_compare.inp')
    #
    #     crs = 'EPSG:32760'
    #     #swmm_to_gpkg(input_file, intermediate_file, crs)
    #
    #     print('\n\nConverting to inp')
    #     gis_to_swmm(input_file, output_file)
    #     self.compare_files(compare_file, output_file)
