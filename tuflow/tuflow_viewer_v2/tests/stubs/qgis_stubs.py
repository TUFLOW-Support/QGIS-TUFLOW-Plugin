import sys
import os

try:
    from PyQt5.QtCore import QSettings, QCoreApplication
    from PyQt5.QtWidgets import QMainWindow, QApplication, QAction
except ImportError:
    from PyQt6.QtCore import QSettings, QCoreApplication
    from PyQt6.QtWidgets import QMainWindow, QApplication
    from PyQt6.QtGui import QAction

from qgis.core import (QgsApplication, QgsProject, QgsLayerTreeModel, QgsMapLayer, QgsVectorLayer, QgsFeature,
                       QgsGeometry, QgsPointXY)
from qgis.gui import QgisInterface, QgsLayerTreeView, QgsMapCanvas, QgsMessageBar
import qgis.utils


if os.name == 'nt':
    PROFILE_FOLDER = rf'C:\Users\{os.getlogin()}\AppData\Roaming\QGIS\QGIS3\profiles\default'
else:
    PROFILE_FOLDER = os.path.expanduser('~/.local/share/QGIS/QGIS3/profiles/default')
PLUGIN_FOLDER = PROFILE_FOLDER + '/python/plugins'
TUFLOW_CATCH_FOLDER = PLUGIN_FOLDER + '/tuflow'


class QGIS_:
    """Initialises QGIS for testing."""

    def __init__(self):
        """Initialises QGIS."""
        # initialise QGIS
        self.init_providers()

        # dummy QgisInterface class
        self.iface = QgisInterface_()
        qgis.utils.iface = self.iface

        # initialise tuflow plugin
        from tuflow.tuflowqgis_menu import tuflowqgis_menu
        self.tuflow = tuflowqgis_menu(self.iface)

        # add tuflow_catch plugin to qgis.utils
        qgis.utils.plugins['tuflow'] = self.tuflow
        qgis.utils.home_plugin_path = PLUGIN_FOLDER
        sys.path.append(PLUGIN_FOLDER)

    def __enter__(self):
        """Initialises QGIS."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Disconnects QGIS."""
        self.close()

    def init_providers(self):
        self.qgis = QgsApplication([bytes(x, 'utf-8') for x in sys.argv], False, PROFILE_FOLDER)
        self.qgis.initQgis()
        # setup QSettings
        QCoreApplication.setOrganizationName('QGIS')
        QCoreApplication.setOrganizationDomain('qgis.org')
        QCoreApplication.setApplicationName('QGIS3')
        QSettings().setDefaultFormat(QSettings.Format.IniFormat)
        QSettings().setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, PROFILE_FOLDER)

    def close(self):
        """Disconnects QGIS."""
        from matplotlib import pyplot as plt
        plt.close('all')
        QgsProject.instance().removeAllMapLayers()
        qgis.utils.plugins['tuflow_catch'].unload()
        del qgis.utils.plugins['tuflow_catch']
        del self.iface
        sys.path.remove(PLUGIN_FOLDER)
        # self.qgis.exitQgis()  # apparently QGIS crashes if this is called then the providers are initialised again


class QgisInterface_(QgisInterface):
    """Subclass QgisInterface class for testing."""

    def __init__(self):
        super().__init__()
        self.set_message_bar()
        self.set_layer_tree_view()
        self.set_map_canvas()
        self.main_window = QMainWindow()
        self.active_layer = None
        self._block_signals = False

    def addCustomActionForLayerType(self, *args, **kwargs):
        pass

    def addCustomActionForLayer(self, *args, **kwargs):
        pass

    def mapCanvas(self) -> 'QgsMapCanvas':
        return self.map_canvas

    def layerTreeView(self) -> 'QgsLayerTreeView':
        return self.layer_tree_view

    def messageBar(self) -> 'QgsMessageBar':
        return self.message_bar

    def activeLayer(self) -> 'QgsMapLayer':
        return self.active_layer

    def setActiveLayer(self, map_layer: 'QgsMapLayer') -> None:
        self.active_layer = map_layer
        if self._block_signals:
            return
        self._block_signals = True
        self.mapCanvas().setCurrentLayer(map_layer)
        self._block_signals = False

    def set_layer_tree_view(self):
        self.layer_tree_view = QgsLayerTreeView()
        model = QgsLayerTreeModel(QgsProject.instance().layerTreeRoot(), self)
        self.layer_tree_view.setModel(model)
        self.layer_tree_view.setMessageBar(self.message_bar)

    def set_map_canvas(self):
        self.map_canvas = QgsMapCanvas_(self)
        self.map_canvas.setObjectName('theMapCanvas')
        self.map_canvas.setProject(QgsProject.instance())

    def set_message_bar(self):
        self.message_bar = QgsMessageBar_()

    def mainWindow(self):
        return self.main_window

    def registerCustomDropHandler(self, handler):
        pass

    def actionSelect(self):
        return QAction()


class QgsMapCanvas_(QgsMapCanvas):
    """Subclass QgsMapCanvas class for testing."""
    def __init__(self, iface, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iface = iface

    def currentLayer(self):
        self.iface.activeLayer()

    def setCurrentLayer(self, layer):
        self.iface.setActiveLayer(layer)
        self.currentLayerChanged.emit(layer)


class QgsMessageBar_(QgsMessageBar):
    """Subclass QgsMessageBar class for testing."""
    pass


QGIS = QGIS_()
