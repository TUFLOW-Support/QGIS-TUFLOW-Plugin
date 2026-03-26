from osgeo import ogr
from qgis import processing
from qgis.gui import QgsCustomDropHandler
from qgis.PyQt.QtWidgets import QMessageBox

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from .logging import Logging


class TuflowDropHandler(QgsCustomDropHandler):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface

    def handleFileDrop(self, file: str) -> bool:
        filepath = Path(file)
        if filepath.suffix == '.inp':
            gpkg_filename = filepath.with_suffix('.gpkg')
            result = processing.execAlgorithmDialog("TUFLOW:TUFLOWConvertSWMMinpToGpkg",
                                                    {'INPUT': file,
                                                     'INPUT_crs': '',
                                                     'INPUT_tags_to_filter': '',
                                                     'INPUT_gpkg_output_filename': str(gpkg_filename),
                                                     }
                                                    )
            if 'OUTPUT' in result:
                gpkg_filename = Path(result['OUTPUT'])
            conn = ogr.Open(str(gpkg_filename))
            self.iface.addVectorLayer(str(gpkg_filename), gpkg_filename.stem, 'ogr')
            return True
        elif filepath.suffix.lower() in ['.tcf', '.tgc', '.tbc', '.ecf', '.qcf', '.tef', 'tesf', 'trfcf', '.adcf', 'tscf']:
            return self.handle_cf_drop(str(filepath))
        return False

    def handle_cf_drop(self, path: str):
        from qgis.utils import plugins
        tuflow_plugin = plugins.get('tuflow')
        if not tuflow_plugin:
            Logging.error('TUFLOW plugin not found')
            return False
        try:
            tuflow_plugin.loadTuflowLayersFromTCF(path)
            return True
        except Exception:
            pass
        return False

    def customUriProviderKey(self):
        return 'tuflow_plugin'

    def handleCustomUriDrop(self, uri):
        self.handle_cf_drop(uri.uri)
