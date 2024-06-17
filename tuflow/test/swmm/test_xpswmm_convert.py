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

from tuflow.tuflow_swmm.xpswmm_xpx_convert import convert_xpswmm
from tuflow.tuflow_swmm.xpswmm_gis_cleanup import bc_layer_processing

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)


class TestXpswmmConvert(unittest.TestCase):
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

    def compare_gpkg_file(self, filename_gpkg, layername):
        json_file = filename_gpkg.with_suffix('.geojson')
        json_file.unlink(missing_ok=True)

        output_root = Path(get_output_path(''))
        relative_path = json_file.relative_to(output_root)
        print(relative_path)

        compare_json_file = Path(get_compare_path(relative_path))

        loc = gpd.read_file(filename_gpkg, layer=layername)
        loc.to_file(str(json_file))

        self.compare_files(compare_json_file, json_file)

    def test_all_in_one(self):
        # copy the files into a new folder
        test_folder = 'xpswmm_convert\\all_in_one_gpkg\\'
        output_folder = Path(get_output_path(test_folder))

        skip_delete = False
        if not skip_delete:
            # Delete and copy starting files
            shutil.rmtree(output_folder, ignore_errors=True)
            shutil.copytree(str(get_input_full_filenames([test_folder])[0]),
                            str(output_folder))

        base_output_folder = Path(get_output_path(''))
        xpx_filename = output_folder / '1D2D_Urban_001.xpx'
        tcf_filename = output_folder / 'TUFLOW\\runs\\1D2D_Urban_001.tcf'
        swmm_prefix = 'urban'
        crs = 'EPSG:32760'

        convert_xpswmm(
            xpx_filename,
            tcf_filename,
            swmm_prefix,
            'HPC',
            'GPU',
            crs,
        )

        # do comparisons
        tcf_compare = Path(get_compare_path(tcf_filename.relative_to(base_output_folder)))
        self.compare_files(tcf_filename, tcf_compare)

        tbc_relative = 'TUFLOW\\model\\1D2D_Urban_001.tbc'
        tbc_compare = Path(get_compare_path(test_folder + tbc_relative))
        tbc_output = Path(get_output_path(test_folder + tbc_relative))
        self.compare_files(tbc_output, tbc_compare)

    def test_multiple_gpkg(self):
        # copy the files into a new folder
        test_folder = 'xpswmm_convert\\multiple_gpkg\\'
        output_folder = Path(get_output_path(test_folder))

        skip_delete = False
        if not skip_delete:
            # Delete and copy starting files
            shutil.rmtree(output_folder, ignore_errors=True)
            shutil.copytree(str(get_input_full_filenames([test_folder])[0]),
                            str(output_folder))

        base_output_folder = Path(get_output_path(''))
        xpx_filename = output_folder / '1D2D_Urban_001.xpx'
        tcf_filename = output_folder / 'TUFLOW\\runs\\1D2D_Urban_001.tcf'
        swmm_prefix = 'urban'
        crs = 'EPSG:32760'

        convert_xpswmm(
            xpx_filename,
            tcf_filename,
            swmm_prefix,
            'HPC',
            'GPU',
            crs
        )

        # do comparisons
        tcf_compare = Path(get_compare_path(tcf_filename.relative_to(base_output_folder)))
        self.compare_files(tcf_filename, tcf_compare)

        tbc_relative = 'TUFLOW\\model\\1D2D_Urban_001.tbc'
        tbc_compare = Path(get_compare_path(test_folder + tbc_relative))
        tbc_output = Path(get_output_path(test_folder + tbc_relative))
        self.compare_files(tbc_output, tbc_compare)

    def test_shp(self):
        # copy the files into a new folder
        test_folder = 'xpswmm_convert\\shp\\'
        output_folder = Path(get_output_path(test_folder))

        skip_delete = False
        if not skip_delete:
            # Delete and copy starting files
            shutil.rmtree(output_folder, ignore_errors=True)
            shutil.copytree(str(get_input_full_filenames([test_folder])[0]),
                            str(output_folder))

        base_output_folder = Path(get_output_path(''))
        xpx_filename = output_folder / '1D2D_Urban_001.xpx'
        tcf_filename = output_folder / 'TUFLOW\\runs\\1D2D_Urban_001.tcf'
        swmm_prefix = 'urban'
        crs = 'EPSG:32760'

        convert_xpswmm(
            xpx_filename,
            tcf_filename,
            swmm_prefix,
            'HPC',
            'GPU',
            crs
        )

        # do comparisons
        tcf_compare = Path(get_compare_path(tcf_filename.relative_to(base_output_folder)))
        self.compare_files(tcf_filename, tcf_compare)

        tbc_relative = 'TUFLOW\\model\\1D2D_Urban_001.tbc'
        tbc_compare = Path(get_compare_path(test_folder + tbc_relative))
        tbc_output = Path(get_output_path(test_folder + tbc_relative))
        self.compare_files(tbc_output, tbc_compare)


    def test_gis_processing_remove_sx_layer(self):
        test_folder = 'xpswmm_convert\\gis_processing\\'
        output_folder = Path(get_output_path(test_folder))

        bc_in_filename = get_input_full_filenames([f'{test_folder}bc_processing_test.gpkg'])[0]
        bc_in_layername = '1D2D_Urban_001_2d_bc_P'

        bc_out_filename = output_folder / 'bc_processing_blank_sx.gpkg'
        bc_out_layername = 'shouldnt be written'

        swmm_filename = get_input_full_filenames([f'{test_folder}urban_001.gpkg'])[0]

        self.assertEqual(False,
                         bc_layer_processing(bc_in_filename,
                                             bc_in_layername,
                                             swmm_filename,
                                             bc_out_filename,
                                             bc_out_layername))

    def test_gis_processing_keep_non_sx(self):
        test_folder = 'xpswmm_convert\\gis_processing\\'
        output_folder = Path(get_output_path(test_folder))

        bc_in_filename = get_input_full_filenames([f'{test_folder}bc_processing_test.gpkg'])[0]
        bc_in_layername = '1D2D_Urban_nonsx_001_2d_bc_P'

        bc_out_filename = output_folder / 'bc_processing_non_sx.gpkg'
        bc_out_layername = '2d_bc_P'

        swmm_filename = get_input_full_filenames([f'{test_folder}urban_001.gpkg'])[0]

        self.assertEqual(True,
                         bc_layer_processing(bc_in_filename,
                                             bc_in_layername,
                                             swmm_filename,
                                             bc_out_filename,
                                             bc_out_layername))

        self.compare_gpkg_file(bc_out_filename, bc_out_layername)

    def test_gis_processing_snap_L(self):
        test_folder = 'xpswmm_convert\\gis_processing\\'
        output_folder = Path(get_output_path(test_folder))

        bc_in_filename = get_input_full_filenames([f'{test_folder}bc_processing_test.gpkg'])[0]
        bc_in_layername = '1D2D_Urban_001_2d_bc_L'

        bc_out_filename = output_folder / 'bc_processing_snap_L.gpkg'
        bc_out_layername = '1D2D_Urban_001_2d_bc_L'

        swmm_filename = get_input_full_filenames([f'{test_folder}urban_001.gpkg'])[0]

        self.assertEqual(True,
                         bc_layer_processing(bc_in_filename,
                                             bc_in_layername,
                                             swmm_filename,
                                             bc_out_filename,
                                             bc_out_layername))

        self.compare_gpkg_file(bc_out_filename, bc_out_layername)
