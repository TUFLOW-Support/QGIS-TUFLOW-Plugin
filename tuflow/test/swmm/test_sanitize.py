import pandas as pd
import subprocess
import unittest

import geopandas as gpd

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from tuflow_swmm.swmm_sanitize import sanitize_name

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)


class TestSanitize(unittest.TestCase):
    def test_name1(self):
        self.assertEqual(sanitize_name('"RemoveQuotes"'), 'RemoveQuotes')

    def test_remove_spaces(self):
        self.assertEqual(sanitize_name('Remove spa ce s'), 'Remove_spa_ce_s')

    def test_remove_invalid(self):
        self.assertEqual(sanitize_name('SwmmSaysTheseAreValid;:!@#$%^&*|\\,/?Invalid'),
                                       'SwmmSaysTheseAreValid;:!@#$%^&*|\\,/?Invalid')

    def test_valid_symbols(self):
        self.assertEqual(sanitize_name('Valid-.symbols'), 'Valid-.symbols')
