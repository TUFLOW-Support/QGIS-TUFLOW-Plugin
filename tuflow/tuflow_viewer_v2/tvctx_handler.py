from qgis.PyQt.QtWidgets import QMenu
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtXml import QDomDocument

from qgis.core import QgsMapLayer, Qgis, QgsProject, QgsMeshDatasetIndex

from .fmts.map_output_mixin import MapOutputMixin
from .fmts.tvoutput import TuflowViewerOutput

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ..pt.pytuflow import TuflowPath, Output
    from ..tuflow_plugin_cache import save_cached_content, get_cached_content
else:
    from tuflow.pt.pytuflow import TuflowPath, Output
    from tuflow.tuflow_plugin_cache import save_cached_content, get_cached_content

from .fmts import FVBCTide
from .tvinstance import get_viewer_instance

import logging
logger = logging.getLogger('tuflow_viewer')


def is_fv_bc_tide_nc(layer: QgsMapLayer) -> bool:
    if layer is None or layer.type() != QgsMapLayer.VectorLayer:
        return False
    tv = get_viewer_instance()
    if not tv:  # not initialised completely yet
        return False
    if not tv.settings.enabled_fmts.get(FVBCTide.DRIVER_NAME, False):
        return False
    if layer.type() == QgsMapLayer.VectorLayer:
        p = TuflowPath(layer.dataProvider().dataSourceUri())
        if Qgis.QGIS_VERSION_INT >= 33000:
            isline = layer.geometryType() == Qgis.GeometryType.Line
        else:
            isline = layer.geometryType() == Qgis.QgsWkbTypes.LineGeometry
        lyrname = layer.name() if p.name.startswith('memory?') else p.lyrname
        return lyrname and lyrname.lower().startswith('2d_ns') and isline
    return False


class TuflowViewerContextMenuProvider(QMenu):

    def __init__(self):
        from qgis.utils import iface
        super().__init__('TUFLOW &Viewer')
        # styling
        self.save_colour_ramp_action = QAction('Save colour &ramp as default')
        self.save_colour_ramp_action.triggered.connect(self.save_colour_ramp)
        self.save_colour_map_action = QAction('Save colour &map as default')
        self.save_colour_map_action.triggered.connect(self.save_colour_map)
        self.save_vector_style_action = QAction('Save &vector settings as default')
        self.save_vector_style_action.triggered.connect(self.save_vector_style)
        self.load_colour_action = QAction('Load default colour style')
        self.load_colour_action.triggered.connect(self.load_colour_style)
        self.load_vector_settings_action = QAction('Load default vector settings')
        self.load_vector_settings_action.triggered.connect(self.load_vector_settings)

        self.styling_sep = QAction()
        self.styling_sep.setSeparator(True)
        styling_actions = [self.save_colour_ramp_action, self.save_colour_map_action, self.save_vector_style_action,
                           self.styling_sep, self.load_colour_action, self.load_vector_settings_action]

        self.load_fv_bc_nc_action = QAction('Load BC tide &NetCDF data')
        self.load_fv_bc_nc_action.triggered.connect(self.load_fv_bc_nc_data)

        self.providers = [
            (is_fv_bc_tide_nc, [self.load_fv_bc_nc_action]),
            (lambda x: x is not None and x.type() == QgsMapLayer.MeshLayer, styling_actions)
        ]

        if iface is not None:
            iface.currentLayerChanged.connect(self.create_menu)

        QgsProject.instance().layersAdded.connect(self.on_layers_added)

    def load_fv_bc_nc_data(self, *args, **kwargs):
        from qgis.utils import iface
        if iface is None:
            return
        output = FVBCTide(
            node_string_gis_fpath=TuflowPath(iface.activeLayer().dataProvider().dataSourceUri()),
            layers=[iface.activeLayer()]
        )
        if output._loaded:
            get_viewer_instance().load_output(output)

    def get_output(self) -> TuflowViewerOutput | None:
        from qgis.utils import iface
        if iface is None or not iface.activeLayer():
            logger.warning('Qgis interface not found or no active layer')
            return None
        output = get_viewer_instance().map_layer_to_output(iface.activeLayer())
        if not output:
            logger.warning('Active layer is not associated with any output')
            return None
        if not isinstance(output, MapOutputMixin):
            logger.warning('Output must be a map output type')
            return None
        return output

    def styling_xml(self, type_: str) -> str:
        output = self.get_output()
        if not output:
            return
        xml = output.styling_xml(type_)
        if not xml:
            logger.warning(f'No active {type_} style.')
            return ''
        return xml

    @staticmethod
    def merge_existing_xml( doc: QDomDocument, path: str, tag: str) -> str:
        """This is so vector and scalar settings can be stored in the same xml, so don't want to necessarily
         throw out any existing settings."""
        existing = get_cached_content(path, str)
        if existing:
            doc1 = QDomDocument()
            doc1.setContent(existing)
            existing_elem = doc1.documentElement().elementsByTagName(tag)
            if existing_elem.count():
                doc1.documentElement().replaceChild(doc.documentElement().elementsByTagName(tag).item(0), existing_elem.item(0))
            else:
                doc1.documentElement().appendChild(doc.documentElement().elementsByTagName(tag).item(0))
            return doc1.toString()
        return doc.toString()

    def save_colour_ramp(self, *args, **kwargs):
        xml = self.styling_xml('scalar')
        if not xml:
            return
        try:
            doc = QDomDocument()
            doc.setContent(xml)
            elem = doc.documentElement()
            name = elem.attribute('data-type')
            if not name:
                logger.warning('Error writing XML')
                return
            name = Output._get_standard_data_type_name(name)  # removes things like 'Maximums/' from the name
            elem.setAttribute('mapping-type', 'ramp')
            p = f'tuflow_viewer/mesh_styles/{name}.xml'
            xml = self.merge_existing_xml(doc, p, 'scalar-settings')
            save_cached_content(p, xml)
            logger.info(f'Colour ramp saved for {name}', extra={'messagebar': True})
        except Exception as e:
            logger.warning(f'Failed to save style: {e}')

    def save_colour_map(self, *args, **kwargs):
        try:
            xml = self.styling_xml('scalar')
            if not xml:
                return
            doc = QDomDocument()
            doc.setContent(xml)
            name = doc.documentElement().attribute('data-type')
            if not name:
                logger.warning('Error writing XML')
                return
            name = Output._get_standard_data_type_name(name)  # removes things like 'Maximums/' from the name
            p = f'tuflow_viewer/mesh_styles/{name}.xml'
            xml = self.merge_existing_xml(doc, p, 'scalar-settings')
            save_cached_content(p, xml)
            logger.info(f'Colour map saved for {name}', extra={'messagebar': True})
        except Exception as e:
            logger.warning(f'Failed to save style: {e}')

    def save_vector_style(self, *args, **kwargs):
        try:
            xml = self.styling_xml('vector')
            if not xml:
                return
            doc = QDomDocument()
            doc.setContent(xml)
            name = doc.documentElement().attribute('data-type')
            if not name:
                logger.warning('Error writing XML')
                return
            name = Output._get_standard_data_type_name(name)  # removes things like 'Maximums/' from the name
            p = f'tuflow_viewer/mesh_styles/{name}.xml'
            xml = self.merge_existing_xml(doc, p, 'vector-settings')
            save_cached_content(p, xml)
            logger.info(f'Vector settings saved for {name}', extra={'messagebar': True})
        except Exception as e:
            logger.warning(f'Failed to save style: {e}')

    def load_colour_style(self, *args, **kwargs):
        output = self.get_output()
        if not output:
            return
        lyr = output.map_layers()[0]
        i = lyr.rendererSettings().activeScalarDatasetGroup()
        if i < 0:
            logger.warning('No active scalar dataset')
            return
        name = lyr.datasetGroupMetadata(QgsMeshDatasetIndex(i)).name()
        name = Output._get_standard_data_type_name(name)  # removes things like 'Maximums/' from the name
        xml = get_cached_content(f'tuflow_viewer/mesh_styles/{name}.xml', str)
        output.load_styling_xml(xml, 'scalar')
        logger.info(f'Loaded scalar colour styling for {name}.')

    def load_vector_settings(self, *args, **kwargs):
        output = self.get_output()
        if not output:
            return
        lyr = output.map_layers()[0]
        i = lyr.rendererSettings().activeVectorDatasetGroup()
        if i < 0:
            logger.warning('No active vector dataset')
            return
        name = lyr.datasetGroupMetadata(QgsMeshDatasetIndex(i)).name()
        name = Output._get_standard_data_type_name(name)  # removes things like 'Maximums/' from the name
        xml = get_cached_content(f'tuflow_viewer/mesh_styles/{name}.xml', str)
        output.load_styling_xml(xml, 'vector')
        logger.info(f'Loaded vector styling for {name}.')

    def register_menu(self):
        from qgis.utils import iface
        if iface is not None:
            iface.addCustomActionForLayerType(
                self.menuAction(),
                '',
                QgsMapLayer.VectorLayer,
                False
            )
            iface.addCustomActionForLayerType(
                self.menuAction(),
                '',
                QgsMapLayer.MeshLayer,
                False
            )
            iface.addCustomActionForLayerType(
                self.menuAction(),
                '',
                QgsMapLayer.RasterLayer,
                False
            )

    def unregister_menu(self):
        from qgis.utils import iface
        try:
            QgsProject.instance().layersAdded.disconnect(self.on_layers_added)
        except Exception:
            pass
        if iface is not None:
            try:
                self.load_fv_bc_nc_action.triggered.disconnect(self.load_fv_bc_nc_data)
            except Exception:
                pass
            try:
                iface.removeCustomActionForLayerType(self.menuAction())
            except Exception:
                pass
            try:
                iface.currentLayerChanged.disconnect(self.create_menu)
            except Exception:
                pass

    def register_layer(self, layer: QgsMapLayer):
        from qgis.utils import iface
        if iface is None:
            return
        for is_recognised, _ in self.providers:
            if is_recognised(layer):
                iface.addCustomActionForLayer(self.menuAction(), layer)

    def register_layers(self, layers: list[QgsMapLayer]):
        for layer in layers:
            self.register_layer(layer)

    def on_layers_added(self, layers: list[QgsMapLayer]):
        self.register_layers(layers)

    def create_menu(self, layer: QgsMapLayer):
        self.clear()
        for is_recognised, actions in self.providers:
            if is_recognised(layer):
                self.addActions(actions)
                break
