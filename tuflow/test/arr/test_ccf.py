from pathlib import Path
from unittest import TestCase

from tuflow.ARR2016.climate_change import ArrCCF


class TestCCF(TestCase):

    def test_load(self):
        data_file = Path(__file__).parent / 'data' / 'ARR_Web_data_test_catchment.txt'
        ccf = ArrCCF()
        with data_file.open() as f:
            ccf.load(f)
        self.assertNotEqual({}, ccf.data)
        self.assertIsNotNone(ccf.data.get('SSP1-2.6'))
        self.assertIsNotNone(ccf.data.get('SSP2-4.5'))
        self.assertIsNotNone(ccf.data.get('SSP3-7.0'))
        self.assertIsNotNone(ccf.data.get('SSP5-8.5'))
        self.assertIsNotNone(ccf.data.get('Climate_Change_INITIAL_LOSS'))
        self.assertIsNotNone(ccf.data.get('Climate_Change_CONTINUING_LOSS'))
        self.assertIsNotNone(ccf.data.get('TEMPERATURE_CHANGES'))
