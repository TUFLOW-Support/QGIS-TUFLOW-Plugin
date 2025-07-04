from pathlib import Path
from unittest import TestCase

from tuflow.ARR2016.preburst import ArrPreburst
from tuflow.ARR2016.arr_settings import ArrSettings


class TestPreburst(TestCase):

    def test_load(self):
        data_file = Path(__file__).parent / 'data' / 'ARR_Web_data_test_catchment.txt'
        pb = ArrPreburst()
        with data_file.open() as f:
            pb.load(f, 'median')
        self.assertNotEqual({}, pb.data)
        self.assertTrue(not pb.depths.empty)
        self.assertTrue(not pb.ratios.empty)

    def test_load_pb_trans(self):
        settings = ArrSettings.get_instance()
        settings.bom_data_file = Path(__file__).parent / 'data' / 'BOM_frequent_rare.html'
        settings.frequent_events = True
        settings.rare_events = True
        settings.use_nsw_prob_neutral_losses = True
        data_file = Path(__file__).parent / 'data' / 'ARR_prob_neutral_losses_trans.txt'
        pb = ArrPreburst()
        with data_file.open() as f:
            pb.load(f, 'median')
        self.assertTrue(not pb.depths.empty)
        self.assertTrue(not pb.ratios.empty)

    def test_load_pb_trans_and_limb(self):
        settings = ArrSettings.get_instance()
        settings.bom_data_file = Path(__file__).parent / 'data' / 'BOM_frequent_rare.html'
        settings.frequent_events = True
        settings.rare_events = True
        settings.use_nsw_prob_neutral_losses = True
        settings.limb_option = 'enveloped'
        data_file = Path(__file__).parent / 'data' / 'ARR_prob_neutral_losses_and_limb.txt'
        pb = ArrPreburst()
        with data_file.open() as f:
            pb.load(f, 'median')
        self.assertTrue(not pb.depths.empty)
        self.assertTrue(not pb.ratios.empty)

    def test_load_pb_limb(self):
        settings = ArrSettings.get_instance()
        settings.bom_data_file = Path(__file__).parent / 'data' / 'BOM_frequent_rare.html'
        settings.frequent_events = True
        settings.rare_events = True
        settings.limb_option = 'enveloped'
        data_file = Path(__file__).parent / 'data' / 'ARR_limb_data.txt'
        pb = ArrPreburst()
        with data_file.open() as f:
            pb.load(f, 'median')
        self.assertTrue(not pb.depths.empty)
        self.assertTrue(not pb.ratios.empty)
