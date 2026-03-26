from qgis.core import Qgis, QgsDataItem, QgsApplication
from qgis.PyQt import QtCore, QtWidgets

from . import Logging


class BrowserHelper(QtCore.QObject):
    """Helper class that runs in the main GUI thread that can be used to help do things in a thread safe way.
    It should be initialised with QgsApplication.instance() as its parent.
    """

    def children(self, data_item: QgsDataItem) -> list[QgsDataItem]:
        """Populates children via the browser model. I found that calling QgsDataItem.children() is not
        always safe and can crash QGIS (esp on WSL). Maybe pointers are stale or something but
        this seems to be a more reliable way to get children without crashing.
        """
        from qgis.utils import iface
        children = []
        browser_model = iface.browserModel()
        index = browser_model.findItem(data_item)
        if not index.isValid():
            Logging.warning(f'Something has gone wrong, index is not valid in BrowserHelper.children(): {data_item.name()}')

        for row in range(browser_model.rowCount(index)):
            child_index = browser_model.index(row, 0, index)
            child_item = browser_model.dataItem(child_index)
            if child_item is not None:
                children.append(child_item)
        return children

    def populate_children(self, data_item: QgsDataItem):
        """Recursively populate children."""
        gui_thread = QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        if not gui_thread:
            Logging.warning('Something has gone wrong, BrowserHelper.populate_children() is not on GUI thread')
            return

        if data_item.state() == Qgis.BrowserItemState.NotPopulated:

            def on_data_changed():
                data_item.dataChanged.disconnect(on_data_changed)
                QtCore.QTimer.singleShot(100, lambda: self.populate_children(data_item))

            data_item.dataChanged.connect(on_data_changed)
            data_item.populate(False)
            return

        if data_item.state() == Qgis.BrowserItemState.Populating:
            return

        for child in self.children(data_item):
            self.populate_children(child)

    def filter_changed(self, data_item: QgsDataItem):
        from qgis.utils import iface
        from . import ControlFileItem
        # path = data_item.path()
        parent = data_item.parent()
        while isinstance(parent, ControlFileItem):
            parent = parent.parent()
        browser_widgets = [x for x in iface.mainWindow().findChildren(QtWidgets.QWidget) if x.objectName() == 'QgsBrowserWidgetBase']
        for browser in browser_widgets:
            browser.refresh()


browser_helper = None  # initialise it later when QgsApplication.instance() is guaranteed to exist
def init_browser_helper():
    global browser_helper
    if browser_helper is None:
        browser_helper = BrowserHelper(QgsApplication.instance())


def get_browser_helper() -> BrowserHelper | None:
    global browser_helper
    if browser_helper is None:
        Logging.warning('BrowserHelper has not been initialised yet, something has gone wrong')
    return browser_helper
