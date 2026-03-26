from qgis.core import QgsMimeDataUtils
from qgis.gui import QgsCustomDropHandler
from qgis.PyQt.QtCore import QTimer

from ..pt.pytuflow.results import ResultTypeError
from .tvinstance import get_viewer_instance
from .fmts import DAT, DATCrossSections

import logging
logger = logging.getLogger('tuflow_viewer')


QGIS_BROWSER_MIME_TYPE = 'application/x-vnd.qgis.qgis.uri'


class TuflowViewerDropHandler(QgsCustomDropHandler):

    def handleFileDrop(self, file: str) -> bool:
        tv = get_viewer_instance()
        driver = tv.get_driver_from_file(file, auto_load_method='DragDrop')
        if driver:
            try:
                if driver.DRIVER_NAME == 'SMS DAT':  # special treatment for dat files since they can combine
                    twodm = DAT.find_2dm(file)
                    name = twodm.stem
                    for output in tv.outputs(name):
                        if hasattr(output, 'twodm') and output.twodm == twodm and hasattr(output, '_dats') and file not in output._dats:
                            output.add_dataset(file)
                            tv.outputs_changed.emit(output)
                            return True
                elif driver.DRIVER_NAME == 'Flood Modeller':  # some more special treatment
                    output = driver(fpath='', dat='', gxy=file)  # result and dat file locations are prompted in a dialog in the driver init method
                    if not output._loaded:  # dialog cancelled
                        return True
                    tv.load_output(output)
                    if output.dat is not None:  # load cross-sections if user has provided a dat file
                        output_dat = DATCrossSections(output.dat.fpath, output.dat, output.gxy)
                        tv.load_output(output_dat)
                    return True
                output = driver(file)
                logger.debug('Successfully loaded output.')
                tv.load_output(output)
            except FileNotFoundError:
                logger.error(f'File not found: {file}')  # should not get here since the file was drag/dropped
            except EOFError:
                logger.error(f'File appears empty or incomplete: {file}')
            except ResultTypeError:
                logger.error(f'Failed to load file using {driver.__name__}: {file}')
            except Exception as e:
                logger.error(f'Unexpected error: {e}')
            return True
        return False

    def handleFileDrops(self, files: list[str]):
        for file in files:
            _ = self.handleFileDrop(file)

    def handleMimeDataV2(self, data) -> bool:
        files = []
        if data.hasFormat(QGIS_BROWSER_MIME_TYPE):
            uris = QgsMimeDataUtils.decodeUriList(data)
            for uri in uris:
                logger.debug(f'Checking if mime data is a file that can be loaded: {uri.uri}')
                tv = get_viewer_instance()
                driver = tv.get_driver_from_file(uri.uri, auto_load_method='DragDrop')
                if driver:
                    files.append(uri.uri)
                    logger.debug(f'Mime data is a file that can be loaded')

        if files:
            QTimer.singleShot(100, lambda: self.handleFileDrops(files))
            return True

        return False
