from pathlib import Path
from unittest import TestCase

from tuflow.ARR2016.preburst import ArrPreburst


class TestPreburst(TestCase):

    def test_load(self):
        data_file = Path(__file__).parent / 'data' / 'ARR_Web_data_test_catchment.txt'
        pb = ArrPreburst()
        with data_file.open() as f:
            pb.load(f, 'median')
        self.assertNotEqual({}, pb.data)
        self.assertTrue(not pb.depths.empty)
