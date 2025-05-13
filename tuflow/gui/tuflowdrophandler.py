from osgeo import ogr
from qgis import processing
from qgis.gui import QgsCustomDropHandler
from qgis.PyQt.QtWidgets import QMessageBox

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path


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
        return False
