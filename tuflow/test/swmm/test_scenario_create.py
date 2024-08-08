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

from tuflow.tuflow_swmm.swmm_extract_scenarios import extract_scenarios

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)


class TestSwmmCreateScenarios(unittest.TestCase):
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

    def compare_messages_file(self, messages_filename_gpkg):
        messages_json_file = messages_filename_gpkg.with_suffix('.geojson')
        messages_json_file.unlink(missing_ok=True)

        compare_messages_json_file = Path(get_compare_path(f'{messages_filename_gpkg.stem}.geojson'))

        gdf_messages_loc = gpd.read_file(messages_filename_gpkg, layer='Messages_with_locations')
        gdf_messages_loc.to_file(str(messages_json_file))

        self.compare_files(compare_messages_json_file, messages_json_file)

    def test_base_remove_pipes(self):
        model_prefix = 'scenarios'
        gpkg_filenames = get_input_full_filenames(
            [
                'scenarios\\scenarios_base_001.gpkg',
                'scenarios\\scenarios_remove-pipes_001.gpkg',
            ]
        )
        scenario_names = [
            'base',
            'remove_pipes',
        ]
        output_prefix = 'base_remove_pipes'
        output_folder = get_output_path(f'scenarios\\{output_prefix}\\')
        #output_file = get_output_path(f'scenarios\\{output_prefix}\\{output_prefix}.inp')
        #Path(output_file).unlink(missing_ok=True)

        output_control_file_lines = Path(output_folder) / f'control_file_lines.txt'

        extract_scenarios(gpkg_filenames, scenario_names, output_folder, model_prefix, output_control_file_lines)

        compare_files = [Path(get_compare_path(f'scenarios\\{output_prefix}\\{model_prefix}_{s}.inp'))
                         for s in scenario_names] + [Path(
            get_compare_path(f'scenarios\\{output_prefix}\\{model_prefix}_Common.inp'))]
        compare_files = [x for x in compare_files if x.exists()]

        output_files = [Path(get_output_path(f'scenarios\\{output_prefix}\\{model_prefix}_{s}.inp'))
                         for s in scenario_names] + [Path(
            get_output_path(f'scenarios\\{output_prefix}\\{model_prefix}_Common.inp'))]
        output_files = [x for x in output_files if x.exists()]

        self.assertEqual(len(compare_files), len(output_files),
                         msg=f'The number of output and compare files do not match.\n'
                         f'\tOutput files: {", ".join([x.stem for x in output_files])}\n'
                         f'\tCompare files: {", ".join([x.stem for x in compare_files])}\n')

        for compare_file, output_file in zip(compare_files, output_files):
            self.compare_files(compare_file, output_file)

    def test_base_culvert_size(self):
        model_prefix = 'scenarios'
        gpkg_filenames = get_input_full_filenames(
            [
                'scenarios\\scenarios_base_001.gpkg',
                'scenarios\\scenarios_culvert-size_001.gpkg',
            ]
        )
        scenario_names = [
            'base',
            'culvert_size',
        ]
        output_prefix = 'base_culvert_size'
        output_folder = get_output_path(f'scenarios\\{output_prefix}\\')
        #output_file = get_output_path(f'scenarios\\{output_prefix}\\{model_prefix}.inp')
        #Path(output_file).unlink(missing_ok=True)

        output_control_file_lines = Path(output_folder) / f'control_file_lines.txt'

        extract_scenarios(gpkg_filenames, scenario_names, output_folder, model_prefix, output_control_file_lines)

        compare_files = [Path(get_compare_path(f'scenarios\\{output_prefix}\\{model_prefix}_{s}.inp'))
                         for s in scenario_names] + [Path(
            get_compare_path(f'scenarios\\{output_prefix}\\{model_prefix}_Common.inp'))]
        compare_files = [x for x in compare_files if x.exists()]

        output_files = [Path(get_output_path(f'scenarios\\{output_prefix}\\{model_prefix}_{s}.inp'))
                         for s in scenario_names] + [Path(
            get_output_path(f'scenarios\\{output_prefix}\\{model_prefix}_Common.inp'))]
        output_files = [x for x in output_files if x.exists()]

        self.assertEqual(len(compare_files), len(output_files),
                         msg=f'The number of output and compare files do not match.\n'
                         f'\tOutput files: {", ".join([x.stem for x in output_files])}\n'
                         f'\tCompare files: {", ".join([x.stem for x in compare_files])}\n')

        for compare_file, output_file in zip(compare_files, output_files):
            self.compare_files(compare_file, output_file)

    def test_base_change_node_values(self):
        model_prefix = 'scenarios'
        gpkg_filenames = get_input_full_filenames(
            [
                'scenarios\\scenarios_base_001.gpkg',
                'scenarios\\scenarios_change-node-values_001.gpkg',
            ]
        )
        scenario_names = [
            'base',
            'change_node_values',
        ]
        output_prefix = 'base_change_node_values'
        output_folder = get_output_path(f'scenarios\\{output_prefix}\\')

        output_control_file_lines = Path(output_folder) / f'control_file_lines.txt'
        #output_file = get_output_path(f'scenarios\\{output_prefix}\\{model_prefix}.inp')
        #Path(output_file).unlink(missing_ok=True)

        extract_scenarios(gpkg_filenames, scenario_names, output_folder, model_prefix,
                          output_control_file_lines)

        compare_files = [Path(get_compare_path(f'scenarios\\{output_prefix}\\{model_prefix}_{s}.inp'))
                         for s in scenario_names] + [Path(
            get_compare_path(f'scenarios\\{output_prefix}\\{model_prefix}_Common.inp'))]
        compare_files = [x for x in compare_files if x.exists()]

        output_files = [Path(get_output_path(f'scenarios\\{output_prefix}\\{model_prefix}_{s}.inp'))
                         for s in scenario_names] + [Path(
            get_output_path(f'scenarios\\{output_prefix}\\{model_prefix}_Common.inp'))]
        output_files = [x for x in output_files if x.exists()]

        self.assertEqual(len(compare_files), len(output_files),
                         msg=f'The number of output and compare files do not match.\n'
                         f'\tOutput files: {", ".join([x.stem for x in output_files])}\n'
                         f'\tCompare files: {", ".join([x.stem for x in compare_files])}\n')

        for compare_file, output_file in zip(compare_files, output_files):
            self.compare_files(compare_file, output_file)

    def test_scenarios_all(self):
        model_prefix = 'scenarios'
        gpkg_filenames = get_input_full_filenames(
            [
                'scenarios\\scenarios_base_001.gpkg',
                'scenarios\\scenarios_remove-pipes_001.gpkg',
                'scenarios\\scenarios_culvert-size_001.gpkg',
                'scenarios\\scenarios_change-node-values_001.gpkg',
            ]
        )
        scenario_names = [
            'base',
            'remove_pipes',
            'culvert_size',
            'change_node_values',
        ]
        output_prefix = 'all'
        output_folder = get_output_path(f'scenarios\\{output_prefix}\\')
        #output_file = get_output_path(f'scenarios\\{output_prefix}\\{model_prefix}.inp')
        #Path(output_file).unlink(missing_ok=True)

        output_control_file_lines = Path(output_folder) / f'control_file_lines.txt'

        extract_scenarios(gpkg_filenames, scenario_names, output_folder, model_prefix, output_control_file_lines)

        compare_files = [Path(get_compare_path(f'scenarios\\{output_prefix}\\{model_prefix}_{s}.inp'))
                         for s in scenario_names] + [Path(
            get_compare_path(f'scenarios\\{output_prefix}\\{model_prefix}_Common.inp'))]
        compare_files = [x for x in compare_files if x.exists()]

        output_files = [Path(get_output_path(f'scenarios\\{output_prefix}\\{model_prefix}_{s}.inp'))
                         for s in scenario_names] + [Path(
            get_output_path(f'scenarios\\{output_prefix}\\{model_prefix}_Common.inp'))]
        output_files = [x for x in output_files if x.exists()]

        self.assertEqual(len(compare_files), len(output_files),
                         msg=f'The number of output and compare files do not match.\n'
                         f'\tOutput files: {", ".join([x.stem for x in output_files])}\n'
                         f'\tCompare files: {", ".join([x.stem for x in compare_files])}\n')

        for compare_file, output_file in zip(compare_files, output_files):
            self.compare_files(compare_file, output_file)