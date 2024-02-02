import numpy as np
import unittest

from tuflow_swmm.xs_processing import get_normalized_hw


class TestXsProcessing(unittest.TestCase):
    def test_throsby_tcb_1140(self):
        coords = np.array(
            [
                [0.0, 1.76],
                [0.1, 0.96],
                [0.6, 0.96],
                [1.8, 0.0],
                [4.25, 0.04],
                [5.45, 1.01],
                [5.89, 1.01],
                [5.9, 1.76],
            ]
        )
        hw_out = np.array(
            [
                [0.0, 0.0],
                [0.02272727, 1.36363636],
                [0.54545455, 3.00462746],
                [0.57386364, 3.28622159],
                [1.00000000, 3.35227273]
            ]
        )
        min_elev, max_elev, hw_points = get_normalized_hw(coords)
        self.assertAlmostEqual(0.0, min_elev)
        self.assertAlmostEqual(1.76, max_elev)
        np.testing.assert_array_almost_equal(hw_points, hw_out)

    def test_throsby_tcb_1390(self):
        coords = np.array(
            [
                [0.0, 2.25],
                [0.01, 1.6],
                [2.23, 0.32],
                [2.63, 0.32],
                [3.03, 0.3],
                [3.95, 0.26],
                [3.96, 0],
                [5.16, 0],
                [5.17, 0.23],
                [6.14, 0.3],
                [6.54, 0.32],
                [6.94, 0.32],
                [9.16, 1.6],
                [9.17, 2.25],
            ]
        )
        hw_out = np.array(
            [
                [0., 0.53333333],
                [0.10222222, 0.53384615],
                [0.11555556, 0.72698413],
                [0.13333333, 1.38222222],
                [0.14222222, 2.09333333],
                [0.71111111, 4.06666667],
                [1., 4.07555556],
            ]
        )
        min_elev, max_elev, hw_points = get_normalized_hw(coords)
        self.assertAlmostEqual(0.0, min_elev)
        self.assertAlmostEqual(2.25, max_elev)
        np.testing.assert_array_almost_equal(hw_points, hw_out)

    def test_channels_with_same_peak(self):
        coords = np.array(
            [
                [0.0, 2.1],
                [0.5, 0.1],
                [1.5, 0.1],
                [2.0, 1.3],
                [2.5, 0.1],
                [3.0, 0.1],
                [3.5, 1.3],
                [4.0, 0.1],
                [5.0, 2.1],
            ]
        )
        hw_out = np.array(
            [
                [0.0, 0.75],
                [0.6, 1.9],
                [1.0, 2.5]
            ]
        )
        min_elev, max_elev, hw_points = get_normalized_hw(coords)
        self.assertAlmostEqual(0.1, min_elev)
        self.assertAlmostEqual(2.1, max_elev)
        np.testing.assert_array_almost_equal(hw_points, hw_out)
