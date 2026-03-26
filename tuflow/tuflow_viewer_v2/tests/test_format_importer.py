from pathlib import Path
from unittest import TestCase
from ..fmt_importer import get_available_classes
from .stubs.qgis_stubs import QGIS


class TestFormatImporter(TestCase):

    def test_format_importer(self):
        output_handlers = {}
        dir_ = Path(__file__).parents[1] / 'fmts'
        import_loc = 'tuflow.tuflow_viewer_v2.fmts'
        base_class = 'TuflowViewerOutput'
        for handler in get_available_classes(dir_, base_class, import_loc):
            if handler not in output_handlers:
                output_handlers[handler.__name__] = handler
        expected_output_handlers = ['XMDF', 'TPC', 'GPKG1D', 'GPKG2D', 'GPKGRL', 'NCMesh', 'NCGrid',
                                    'TuflowCrossSections', 'BCTablesCheck', 'HydTablesCheck', 'DAT',
                                    'FMTS', 'DATCrossSections', 'CATCHJson', 'FVBCTide']
        self.assertEqual(sorted(expected_output_handlers), sorted(output_handlers.keys()))
