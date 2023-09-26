import os

from PyQt5.QtWidgets import QAction, QMenu
from qgis.gui import QgisInterface
from qgis.core import QgsMapLayer

from .utils import create_tuflow_command_path, create_tuflow_command_name
from .gui import apply_tf_style_message_ids
from .utils import tuflow_plugin, increment_file, increment_db_and_lyr, increment_lyr


class TuflowContextMenuProvider(QMenu):

    def __init__(self, iface: QgisInterface):
        super().__init__('&TUFLOW')
        self.iface = iface
        self.action_filter_msgs = None
        self.action_create_tf_command_shp = None
        self.action_create_tf_command_gpkg = None
        self.action_increment_file = None
        self.action_increment_db_and_lyr = None
        self.action_increment_lyr = None

    def init_menu(self) -> None:
        self.action_filter_msgs = QAction('Filter Messages By Code', self.iface.mainWindow())
        self.action_filter_msgs.triggered.connect(apply_tf_style_message_ids)
        self.action_create_tf_command_shp = QAction('Copy TUFLOW Command', self.iface.mainWindow())
        self.action_create_tf_command_shp.triggered.connect(create_tuflow_command_path)
        self.action_create_tf_command_gpkg = QAction('Copy TUFLOW Command (name only)', self.iface.mainWindow())
        self.action_create_tf_command_gpkg.triggered.connect(create_tuflow_command_name)
        self.action_increment_file = QAction(
            tuflow_plugin().icon('increment_layer'),
            'Increment File (beta)',
            self.iface.mainWindow()
        )
        self.action_increment_file.triggered.connect(increment_file)
        self.action_increment_db_and_lyr = QAction(
            tuflow_plugin().icon('increment_layer'),
            'Increment Layer and Database (beta)',
            self.iface.mainWindow()
        )
        self.action_increment_db_and_lyr.triggered.connect(increment_db_and_lyr)
        self.action_increment_lyr = QAction(
            tuflow_plugin().icon('increment_layer'),
            'Increment Layer (beta)',
            self.iface.mainWindow()
        )
        self.action_increment_lyr.triggered.connect(increment_lyr)
        self.iface.currentLayerChanged.connect(self.create_menu)

    def register_menu(self) -> None:
        self.iface.addCustomActionForLayerType(
            self.menuAction(),
            '',
            QgsMapLayer.VectorLayer,
            False
        )
        self.iface.addCustomActionForLayerType(
            self.menuAction(),
            '',
            QgsMapLayer.RasterLayer,
            False
        )

    def unregister_menu(self) -> None:
        self.iface.removeCustomActionForLayerType(self.menuAction())
        self.iface.currentLayerChanged.disconnect(self.create_menu)

    def register_layer(self, layer: QgsMapLayer):
        if layer.type() == QgsMapLayer.VectorLayer:
            if layer.storageType() in ['GPKG', 'ESRI Shapefile', 'Mapinfo File']:
                self.iface.addCustomActionForLayer(self.menuAction(), layer)

    def register_layers(self, layers: list[QgsMapLayer]):
        for layer in layers:
            self.register_layer(layer)

    def create_menu(self, layer: QgsMapLayer):
        self.clear()
        if layer and layer.type() == QgsMapLayer.VectorLayer:
            if 'messages' in layer.name().lower():
                self.addAction(self.action_filter_msgs)
                self.addSeparator()
            if layer.storageType() in ['ESRI Shapefile', 'Mapinfo File']:
                self.addActions(self.shp_menu_actions())
            elif layer.storageType() == 'GPKG':
                self.addActions(self.gpkg_menu_actions())

    def shp_menu_actions(self) -> list[QAction]:
        separator = QAction(parent=self)
        separator.setSeparator(True)
        return [
            self.action_create_tf_command_shp,
            separator,
            self.action_increment_file
        ]

    def gpkg_menu_actions(self) -> list[QAction]:
        separator = QAction(parent=self)
        separator.setSeparator(True)
        return [
            self.action_create_tf_command_shp,
            self.action_create_tf_command_gpkg,
            separator,
            self.action_increment_db_and_lyr,
            self.action_increment_lyr
        ]
