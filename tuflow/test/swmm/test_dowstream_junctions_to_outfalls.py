import math
import pandas as pd
import unittest

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from test_files import get_compare_path, get_output_path, get_input_full_filenames

from tuflow_swmm.junctions_downstream_to_outfalls import downstream_junctions_to_outfalls_from_files
from tuflow_swmm.gis_to_swmm import gis_to_swmm

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
            self.assertEqual(len(text1), len(text2))
            for line_num, (l1, l2) in enumerate(zip(text1, text2)):
                self.assertEqual(l1, l2, msg=f'Line: {line_num + 1}')

    def test_brs(self):
        input_filename = get_input_full_filenames(['bsr_hydraulics_001.gpkg'])[0]
        print(f'Converting downstream junctions to outfalls from: {input_filename}')

        output_filename = get_output_path('bsr_junctions_to_outfalls_001.gpkg')

        downstream_junctions_to_outfalls_from_files(
            input_filename,
            'Nodes--Junctions',
            input_filename,
            'Links--Conduits',
            output_filename,
            'Nodes--Junctions',
            output_filename,
            'Nodes--Outfalls'
        )

        inp_filename = Path(output_filename).with_suffix('.inp')
        gis_to_swmm(
            output_filename,
            inp_filename
        )

        self.compare_files(inp_filename,
                           get_compare_path('bsr_junctions_to_outfalls_001.inp'))