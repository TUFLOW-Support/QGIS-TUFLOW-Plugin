from pathlib import Path

from qgis.PyQt import QtCore, QtWidgets
from qgis.utils import iface

from ..fmts.xmdf import XMDF
from ..tvinstance import get_viewer_instance
from ...pt.pytuflow.results import ResultTypeError

import logging
logger = logging.getLogger('tuflow_viewer')


class BrowserEventFilter(QtCore.QObject):

    def browser_tree(self):
        if iface is not None:
            browser_docks = [x for x in iface.mainWindow().findChildren(QtWidgets.QDockWidget) if x.objectName() == 'Browser']
            if browser_docks:
                browser_dock = browser_docks[0]
                browser_tree = browser_dock.findChild(QtWidgets.QTreeView)
                return browser_tree

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.MouseButtonDblClick:
            logger.debug('Detected double-click event in browser tree view.')
            try:
                tree = obj.parent()
                index = tree.currentIndex()

                model = self.browser_tree().model()
                data = model.itemData(index)
                logger.debug(f'Item data from double-clicked index: {data}')
                if Path(data.get(0)).suffix.lower() in ['.xmdf', '.2dm']:
                    if not get_viewer_instance().settings.enabled_fmts.get('XMDF', False):
                        logger.debug('XMDF support is disabled in settings, ignoring double-click on XMDF file.')
                        return super().eventFilter(obj, event)
                    logger.debug(f'Double-clicked on XMDF file in browser: {data.get(0)}')
                    p = Path(data.get(3))
                    try:
                        xmdf = XMDF(p)
                        QtCore.QTimer.singleShot(100, lambda: get_viewer_instance().load_output(xmdf))
                    except FileNotFoundError:
                        logger.error(f'File not found: {self.path()}')  # should not get here since the file was drag/dropped
                    except EOFError:
                        logger.error(f'File appears empty or incomplete: {self.path()}')
                    except ResultTypeError:
                        logger.error(f'Failed to load file using XMDF driver: {self.path()}')
                    except Exception as e:
                        logger.error(f'Unexpected error: {e}')
                    return True
            except Exception:
                pass
        return super().eventFilter(obj, event)

