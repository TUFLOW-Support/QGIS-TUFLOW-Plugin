from .stubs.qgis_stubs import QGIS

from ._utils import TuflowViewerTestCase
from ..tvdeveloper_tools import Profiler


class TestProfiler(TuflowViewerTestCase):

    def test_singleton(self):
        profiler1 = Profiler()
        profiler2 = Profiler()

        self.assertIs(profiler1, profiler2)
