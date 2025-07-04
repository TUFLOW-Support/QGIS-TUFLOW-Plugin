from pathlib import Path
from unittest import TestCase

import pandas as pd
from tuflow.ARR2016.climate_change import ArrCCF
from tuflow.ARR2016.arr_settings import ArrSettings
from tuflow.ARR2016.BOM_WebRes import Bom
from tuflow.ARR2016.preburst import ArrPreburst


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

    def test_load_rainfall(self):
        data_file = Path(__file__).parent / 'data' / 'ARR_Web_data_test_catchment.txt'
        bom_file = Path(__file__).parent / 'data' / 'BOM_frequent_rare.html'
        settings = ArrSettings.get_instance()
        settings.arr_data_file = data_file
        settings.bom_data_file = bom_file
        ccf = ArrCCF()
        with data_file.open() as f:
            ccf.load(f)
        bom = Bom()
        bom.load(bom_file, False, False)
        rf = pd.DataFrame(bom.depths, columns=bom.aep_names, index=bom.duration)
        cc_param = {'Lon-term_SSP2-4.5': {'horizon': 'Long-term', 'ssp': 'SSP2-4.5', 'base': 0, 'temp': -1}}
        for name, param in cc_param.items():
            ccf.add_scenario(name, param)
            ccf.calc_rainfall_depths(name, rf)

    def test_load_losses(self):
        data_file = Path(__file__).parent / 'data' / 'ARR_Web_data_test_catchment.txt'
        bom_file = Path(__file__).parent / 'data' / 'BOM_frequent_rare.html'
        settings = ArrSettings.get_instance()
        settings.arr_data_file = data_file
        settings.bom_data_file = bom_file
        ccf = ArrCCF()
        with data_file.open() as f:
            ccf.load(f)
        pb = ArrPreburst()
        with data_file.open() as f:
            pb.load(f, 'median')
        bom = Bom()
        bom.load(bom_file, True, True)
        rf = pd.DataFrame(bom.depths, columns=bom.aep_names, index=bom.duration)
        cc_param = {'Lon-term_SSP2-4.5': {'horizon': 'Long-term', 'ssp': 'SSP2-4.5', 'base': 0, 'temp': -1}}
        for name, param in cc_param.items():
            ccf.add_scenario(name, param)
            ccf.calc_rainfall_depths(name, rf)

        for name in cc_param:
            ccf.calc_rainfall_losses(name, 16., 0., pb.ratios, 'East Coast North')
