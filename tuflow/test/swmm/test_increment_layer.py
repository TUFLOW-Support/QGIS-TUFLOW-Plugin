import pandas as pd
import subprocess
import unittest

import geopandas as gpd

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from tuflow_swmm.layer_util import increment_layer


class TestIncrementLayer(unittest.TestCase):
    def test_gpkg_layer_no_number(self):
        filename_mod, layername_mod = increment_layer('test_filename.gpkg', 'test_layer')
        self.assertEqual(filename_mod, 'test_filename.gpkg')
        self.assertEqual(layername_mod, 'test_layer_001')

    def test_gpkg_layer_versioned(self):
        filename_mod, layername_mod = increment_layer('test_filename.gpkg', 'test_layer_002')
        self.assertEqual(filename_mod, 'test_filename.gpkg')
        self.assertEqual(layername_mod, 'test_layer_003')

    def test_shapefile(self):
        # shapefiles don't have layernames
        filename_mod, layername_mod = increment_layer('test_filename.shp', None)
        self.assertEqual(filename_mod, 'test_filename_001.shp')
        self.assertEqual(layername_mod, None)

    def test_shapefile_versioned(self):
        # shapefiles don't have layernames
        filename_mod, layername_mod = increment_layer('test_filename_0522.shp', None)
        self.assertEqual(filename_mod, 'test_filename_0523.shp')
        self.assertEqual(layername_mod, None)

