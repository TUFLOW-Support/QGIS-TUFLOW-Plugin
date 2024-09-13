from pathlib import Path
from unittest import TestCase

from tuflow.ARR2016.losses import ArrLosses


class TestLosses(TestCase):

    def test_load(self):
        data_file = Path(__file__).parent / 'data' / 'ARR_Web_data_test_catchment.txt'
        losses = ArrLosses()
        with data_file.open() as f:
            losses.load(f)
        self.assertNotEqual({}, losses.data)
        self.assertEqual(21., losses.init_loss)
        self.assertEqual(1.8, losses.cont_loss)
        self.assertFalse(losses.has_neutral_losses)

    def test_load_neutral_losses(self):
        data_file = Path(__file__).parent / 'data' / 'ARR_prob_neutral_losses.txt'
        losses = ArrLosses()
        with data_file.open() as f:
            losses.load(f)
        self.assertTrue(losses.has_neutral_losses)
