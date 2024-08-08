import os
import pandas as pd
from pathlib import Path
import unittest

from tuflow.tuflow_swmm.fix_multi_link_oulets import extend_multi_link_outfalls
from tuflow.tuflow_swmm.gis_to_swmm import gis_to_swmm

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)

def get_input_full_filenames(filenames):
    dir = os.path.dirname(__file__)

    return [os.path.join(dir, "input", x) for x in filenames]

def get_output_full_filenames(filenames):
    dir = os.path.dirname(__file__)

    return [os.path.join(dir, "output", x) for x in filenames]

def get_compare_path(filename):
    dir = os.path.dirname(__file__)
    return os.path.join(dir, "compare", filename)

class TestFixOutletsMultiLinks(unittest.TestCase):
    def compare_files(self, first, second):
        print(f'Comparing: {first} {second}')
        with (open(first, "r", encoding='utf-8', errors='ignore') as f1,
              open(second, "r", encoding='utf-8', errors='ignore') as f2):
            text1 = f1.readlines()
            text2 = f2.readlines()
            # print(text1)
            # print(text2)
            self.assertEqual(len(text1), len(text2))
            for line_num, (l1, l2) in enumerate(zip(text1, text2)):
                self.assertEqual(l1, l2, msg=f'Line: {line_num + 1}')

    def test_A(self):
        input_filename = get_input_full_filenames(['throsby_bridges_bad_outlets.gpkg'])[0]
        print(f'Fix outlets multi-links input filename: {input_filename}')

        channel_ext_length = 10.0
        channel_ext_width = 20.0
        channel_ext_maxdepth = 30.0
        channel_ext_zoffset = -0.1
        channel_ext_roughness = 0.015

        output_gpkg = get_output_full_filenames(['throsby_bridges_ext_outlets.gpkg'])[0]

        extend_multi_link_outfalls(input_filename,
                                   output_gpkg,
                                   channel_ext_length)

        output_inp = Path(output_gpkg).with_suffix('.inp')
        gis_to_swmm(output_gpkg, output_inp)

        self.compare_files(output_inp, get_compare_path('throsby_bridges_ext_outlets.inp'))









