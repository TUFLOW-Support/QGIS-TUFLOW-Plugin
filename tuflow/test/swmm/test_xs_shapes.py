import math
import unittest

from tuflow.tuflow_swmm.xs_shapes import get_max_width, get_max_height, get_max_area


class TestShapeMaxHeight(unittest.TestCase):
    def test_circle(self):
        self.assertAlmostEqual(1.2, get_max_height('CIRCULAR', False, 1.2))

    def test_rectangle(self):
        self.assertAlmostEqual(0.8, get_max_height('RECT_CLOSED', False, 0.8, 1.8))

    def test_arch_index(self):
        width = get_max_height('ARCH', True, 999.0, 999.0, 2.0)
        self.assertAlmostEqual(width, 13.5 / 12.0, places=2)
        width = get_max_height('ARCH', False, 999.0, 999.0, 2.0)
        self.assertAlmostEqual(width, 0.3429, places=2)


class TestShapeMaxWidth(unittest.TestCase):
    def test_circle(self):
        self.assertAlmostEqual(1.2, get_max_width('CIRCULAR', False, 1.2))

    def test_rectangle(self):
        self.assertAlmostEqual(1.8, get_max_width('RECT_CLOSED', False, 0.8, 1.8))

    def test_arch_index(self):
        width = get_max_width('ARCH', True, 999.0, 999.0, 2.0)
        self.assertAlmostEqual(width, 22.0 / 12.0, places=2)
        width = get_max_width('ARCH', False, 999.0, 999.0, 2.0)
        self.assertAlmostEqual(width, 0.5588, places=2)


class TestShapeAreas(unittest.TestCase):
    def test_circle(self):
        area = get_max_area('CIRCULAR', False, 0.5)
        self.assertAlmostEqual(area, 0.196350, 4)

    def test_rectangle(self):
        area = get_max_area('RECT_CLOSED', False, 2.0, 4.0)
        self.assertAlmostEqual(area, 8.0)

    def test_bad_shape(self):
        # We were having trouble with files from Matt and decided not to throw an exception
        self.assertAlmostEqual(0.0, get_max_area('BAD_SHAPE_TYPE', False, 3.0, 7.0))

    def test_filled_circle(self):
        area = get_max_area('FILLED_CIRCULAR', False, 2.5, 0.5)
        full_circle_area = get_max_area('CIRCULAR', False, 2.5)
        # from https://planetcalc.com/1421/
        self.assertAlmostEqual(area, full_circle_area - 0.6989, 3)

    def test_rect_triang(self):
        area = get_max_area('RECT_TRIANG', False, 4, 3, 1)
        self.assertAlmostEqual(area, 10.5, places=2)

    def test_rect_round(self):
        area = get_max_area('RECT_ROUND', False, 3.5, 3, 1.5)
        self.assertAlmostEqual(area, 9.5343, places=3)

    def test_modified_baskethandle(self):
        area = get_max_area('MOD_BASKET', False, 3.5, 3, 1.5)
        self.assertAlmostEqual(area, 9.5343, places=3)

    def test_trapezoidal(self):
        # values from hydraulic toolbox
        area = get_max_area('TRAPEZOIDAL', False, 0.533, 4.0, 1.25, 1.25)
        self.assertAlmostEqual(area, 2.485, places=2)

    def test_triangular(self):
        area = get_max_area('TRIANGULAR', False, 3.0, 4.0)
        self.assertAlmostEqual(area, 6.0, places=2)

    def test_parabolic(self):
        # Tested for reasonableness (no independent calc)
        area = get_max_area('PARABOLIC', False, 3.0, 4.0)
        self.assertAlmostEqual(area, 8.0, places=2)

    def test_powerfunc(self):
        # Tested for reasonableness (no independent calc)
        area = get_max_area('POWERFUNC', False, 3.0, 4.0, 3.0)
        self.assertAlmostEqual(area, 9.0, places=2)

    def test_horiz_ellipse_index(self):
        area = get_max_area('HORIZ_ELLIPSE', False, 999.0, 999.0, 2.0)
        self.assertAlmostEqual(area, 0.002129, places=2)

    def test_horiz_ellipse(self):
        area = get_max_area('HORIZ_ELLIPSE', False, 3.0, 4.0, 0.0)
        self.assertAlmostEqual(area, math.pi * (3.0 / 2) * (4.0 / 2), places=2)

    def test_vert_ellipse(self):
        area = get_max_area('VERT_ELLIPSE', False, 3.0, 4.0, 0.0)
        self.assertAlmostEqual(area, 9.424778, places=2)

    def test_arch_index(self):
        area = get_max_area('ARCH', False, 999.0, 999.0, 2.0)
        self.assertAlmostEqual(area, 0.001064514, places=2)

    def test_arch(self):
        # Checked for reasonableness (no separate calculation)
        area = get_max_area('ARCH', False, 3.0, 4.0, 0.0)
        self.assertAlmostEqual(area, 9.4548, places=2)
