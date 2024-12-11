import math
import pandas as pd
try:
    from shapely.geometry.linestring import LineString
    has_shapely = True
except ImportError:
    has_shapely = False
    LineString = 'LineString'
import subprocess
import unittest

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from test.swmm.test_files import get_compare_path, get_output_path, get_input_full_filenames

import tuflow.tuflow_swmm.geom_util as geom_util

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)


class TestGeomUtils(unittest.TestCase):
    def test_perp_offset_01(self):
        linestring = LineString([(0.0, 2.0), (3.0, 2.0)])

        out_line = geom_util.get_perp_offset_line_points(linestring,
                                              4.0,
                                              6.0,
                                              False)

        print(out_line)
        self.assertEqual(len(out_line.coords), 2)
        self.assertEqual(out_line.coords[0][0], 7.0)
        self.assertEqual(out_line.coords[0][1], 5.0)
        self.assertEqual(out_line.coords[1][0], 7.0)
        self.assertEqual(out_line.coords[1][1], -1.0)

    def test_perp_offset_02(self):
        linestring = LineString([(0.0, 2.0), (3.0, 2.0)])

        out_line = geom_util.get_perp_offset_line_points(linestring,
                                                         4.0,
                                                         6.0,
                                                         True)

        print(out_line)
        self.assertEqual(len(out_line.coords), 2)
        self.assertEqual(out_line.coords[0][0], -4.0)
        self.assertEqual(out_line.coords[0][1], -1.0)
        self.assertEqual(out_line.coords[1][0], -4.0)
        self.assertEqual(out_line.coords[1][1], 5.0)