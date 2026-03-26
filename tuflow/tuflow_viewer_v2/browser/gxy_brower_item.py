from pathlib import Path

from qgis.core import QgsDataItem, Qgis, QgsMimeDataUtils
from qgis.PyQt import QtGui

from ..tvinstance import get_viewer_instance
from ..fmts.fmts import FMTS
from ...pt.pytuflow.results import ResultTypeError

import logging
logger = logging.getLogger('tuflow_viewer')


class GXYBrowserItem(QgsDataItem):

    def __init__(self, path, parent=None):
        super().__init__(QgsDataItem.Custom, parent, Path(path).name, path, 'tuflow_viewer')
        self.setToolTip(path)

        self.setCapabilitiesV2(Qgis.BrowserItemCapability.Fast)
        self.populate()

    def hasChildren(self):
        return False

    def createChildren(self):
        return []

    def handleDoubleClick(self):
        # Optional: define what happens when user double-clicks
        try:
            output = FMTS(fpath='', dat='', gxy=self.path())
            get_viewer_instance().load_output(output)
        except FileNotFoundError:
            logger.error(f'File not found: {self.path()}')  # should not get here since the file was drag/dropped
        except EOFError:
            logger.error(f'File appears empty or incomplete: {self.path()}')
        except ResultTypeError:
            logger.error(f'Failed to load file using TPC driver: {self.path()}')
        except Exception as e:
            logger.error(f'Unexpected error: {e}')
        return True

    def hasDragEnabled(self):
        return True

    def mimeUris(self):
        u = QgsMimeDataUtils.Uri()
        u.layerType = 'custom'
        u.providerKey = 'tuflow_viewer'
        u.name = self.name()
        u.uri = self.path()
        return [u]

    def icon(self):
        try:
            return get_viewer_instance().icon('gxy_stream.svg', use_qgis_theme=True)
        except Exception:
            return QtGui.QIcon()
