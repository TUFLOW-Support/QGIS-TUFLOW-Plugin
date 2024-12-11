import numpy as np
import pandas as pd
import subprocess
import unittest

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from tuflow.utils.create_grid_commands import compute_shifted_origin

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)


class TestGridComputations(unittest.TestCase):
    def test_grid_origin1(self):
        # if grid angle is 0.0, x_min = 12.3, y_min = 33.6
        # shifted origin (nearest 10.0) should be 10.0, 30.0
        angle = 0.0
        origin = np.array([12.3, 33.6])

        shifted = compute_shifted_origin(angle, origin)
        self.assertAlmostEqual(shifted[0], 10.0, 4)
        self.assertAlmostEqual(shifted[1], 30.0, 4)

    def test_grid_origin_rotated(self):
        angle = 10.0
        origin = np.array([12.3, 33.6])

        shifted = compute_shifted_origin(angle, origin)
        self.assertAlmostEqual(shifted[0], 10.0, 4)
        self.assertAlmostEqual(shifted[1], 30.0, 4)

    def test_grid_origin_90(self):
        # At 90 shift x value needs to be larger for it to smaller in rotated space
        angle = 90.0
        origin = np.array([12.3, 33.6])

        shifted = compute_shifted_origin(angle, origin)
        self.assertAlmostEqual(shifted[0], 20.0, 4)
        self.assertAlmostEqual(shifted[1], 30.0, 4)

    def test_grid_origin_180(self):
        # At 180 shift x and y value needs to be larger for it to smaller in rotated space
        angle = 180.0
        origin = np.array([12.3, 33.6])

        shifted = compute_shifted_origin(angle, origin)
        self.assertAlmostEqual(shifted[0], 20.0, 4)
        self.assertAlmostEqual(shifted[1], 40.0, 4)

    def test_grid_origin_neg90(self):
        # At -90 shift y value needs to be larger for it to smaller in rotated space
        angle = -90.0
        origin = np.array([12.3, 33.6])

        shifted = compute_shifted_origin(angle, origin)
        self.assertAlmostEqual(shifted[0], 10.0, 4)
        self.assertAlmostEqual(shifted[1], 40.0, 4)

    def test_grid_rotate_45(self):
        # A 45 degree shift is tricky because if x goes bigger or smaller it theoretically could go outside the grid
        angle = 45
        origin = np.array([19.4, 30.45])

        shifted = compute_shifted_origin(angle, origin)
        self.assertAlmostEqual(shifted[0], 20.0, 4)
        self.assertAlmostEqual(shifted[1], 20.0, 4)