import os

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from typing import Union

from PyQt5.QtWidgets import QAction, QMenu
from qgis.gui import QgisInterface
from qgis.core import QgsMapLayer, QgsWkbTypes, QgsProcessingFeedback
from qgis import processing

from .utils import create_tuflow_command_path, create_tuflow_command_name
from .gui import apply_tf_style_message_ids, apply_tf_style_temporal, apply_tf_style_static
from .utils import (tuflow_plugin, increment_file, increment_db_and_lyr, increment_lyr, file_from_data_source,
                    layer_name_from_data_source)
from .tuflow_results_gpkg import ResData_GPKG

from .tuflow_swmm.swmm_io import is_tuflow_swmm_file
from .tuflow_swmm.gis_to_swmm import gis_to_swmm
from .tuflow_swmm.qgis.dialogs.increment_gpkg import run_increment_dlg


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
        self.action_gpkg_ts_static_style_shape = None
        self.action_gpkg_ts_static_style_type = None

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
        self.action_gpkg_ts_static_style_type = QAction('Static style Type', self.iface.mainWindow())
        self.action_gpkg_ts_static_style_shape = QAction('Static style Shape', self.iface.mainWindow())
        self.action_gpkg_ts_static_style_type.triggered.connect(lambda e: apply_tf_style_static('Type'))
        self.action_gpkg_ts_static_style_shape.triggered.connect(lambda e: apply_tf_style_static('Shape'))

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
                db = file_from_data_source(layer.dataProvider().dataSourceUri())

                try:
                    if is_tuflow_swmm_file(db):
                        self.addActions(self.add_gpkg_swmm_actions(db, layer))
                        return
                except Exception as e:
                    pass  # Nothing to do action won't get added

                res = ResData_GPKG()
                err, msg = res.Load(db)
                if not err:
                    geom = layer.geometryType()
                    self.addActions(self.add_gpkg_ts_actions(res, geom))
                    self.addSeparator()
                    if layer.geometryType() == QgsWkbTypes.PointGeometry:
                        self.addAction(self.action_gpkg_ts_static_style_type)
                    else:
                        self.addAction(self.action_gpkg_ts_static_style_shape)
                        self.addAction(self.action_gpkg_ts_static_style_type)
                    self.addSeparator()
                    res.close()
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

    def add_gpkg_swmm_actions(self, gpkg_filename, layer) -> list:
        export_inp_action = QAction('SWMM - Export inp file', self.iface.mainWindow())
        export_inp_action.setStatusTip('Export EPA SWMM inp file with same name as the GeoPackage file')
        export_inp_action.triggered.connect(
            lambda b,
                   l=str(gpkg_filename),
                   f=str(Path(gpkg_filename).with_suffix('.inp')):
            processing.execAlgorithmDialog(
                "TUFLOW:ConvertGpkgToSWMMInp",
                {
                    'INPUT': l,
                    'INPUT_inp_output_filename': f,
                }
            )
        )

        increment_gpkg_action = QAction('SWMM - Increment GeoPackage', self.iface.mainWindow())
        increment_gpkg_action.setStatusTip('Increment the SWMM GeoPackage file')
        increment_gpkg_action.triggered.connect(
            lambda b,
                   l=str(gpkg_filename),
                   lay=layer:
            run_increment_dlg(l, lay)
        )

        # processing.run("TUFLOW:ConvertGpkgToSWMMInp", {
        #    'INPUT': 'D:\\models\\TUFLOW\\test_models\\SWMM\\ExampleModels\\urban\\TUFLOW\\model\\swmm\\EG15_004_swmm_w_ext_inlets_004.gpkg',
        #    'INPUT_inp_output_filename': 'D:\\models\\TUFLOW\\test_models\\SWMM\\ExampleModels\\urban\\TUFLOW\\model\\swmm\\EG15_004_swmm_w_ext_inlets_004.inp'})

        # feedback = QgsProcessingFeedback()
        # export_inp_action.triggered.connect(
        #    lambda b,
        #           l=gpkg_filename,
        #           f=Path(gpkg_filename).with_suffix('.inp'):
        #    gis_to_swmm(l, f, feedback)
        # )
        return [export_inp_action, increment_gpkg_action]

    def add_gpkg_ts_actions(self, res: ResData_GPKG, geom: int) -> Union[None, list]:
        if geom == QgsWkbTypes.PointGeometry:
            types = res.pointResultTypesTS()
        elif geom == QgsWkbTypes.LineGeometry:
            types = res.lineResultTypesTS()
        elif geom == QgsWkbTypes.PolygonGeometry:
            types = res.regionResultTypesTS()
        else:
            return []
        actions = []
        for type_ in types:
            if not hasattr(self, 'action_{0}'.format(type_)):
                setattr(self, 'action_{0}'.format(type_),
                        QAction('Temporal style {0}..'.format(type_), self.iface.mainWindow()))
                getattr(self, 'action_{0}'.format(type_)).triggered.connect(
                    lambda b, t=type_: apply_tf_style_temporal(t))
            actions.append(getattr(self, 'action_{0}'.format(type_)))
        return actions
