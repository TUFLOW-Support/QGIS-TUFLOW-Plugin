import typing
from datetime import datetime

from qgis.core import (QgsMapLayer, QgsMeshDatasetIndex, Qgis, QgsMeshLayer, QgsCoordinateReferenceSystem,
                       QgsMeshDataProviderTemporalCapabilities, QgsRectangle)
from qgis.PyQt.QtCore import QSettings, QDateTime, QDate, QTime, QTimeZone
from qgis.PyQt.QtXml import QDomDocument

from .map_output_mixin import MapOutputMixin

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import Output
    from ...tuflow_plugin_cache import get_cached_content
else:
    from tuflow.pt.pytuflow import Output
    from tuflow.tuflow_plugin_cache import get_cached_content

import logging
logger = logging.getLogger('tuflow_viewer')


class MeshMixin(MapOutputMixin):

    def _init_styling(self, map_layers: list[QgsMapLayer], lyr2resultstyle: dict):
        """Initialise styling for the layer."""
        super()._init_styling(map_layers, lyr2resultstyle)
        layer = map_layers[0]
        for i in range(layer.datasetGroupCount()):
            name = layer.datasetGroupMetadata(QgsMeshDatasetIndex(i)).name()
            name = Output._get_standard_data_type_name(name)
            xml = get_cached_content(f'tuflow_viewer/mesh_styles/{name}.xml', str)
            if xml:
                self.load_styling_xml(xml, 'scalar', i)
                if layer.datasetGroupMetadata(QgsMeshDatasetIndex(i)).isVector():
                    self.load_styling_xml(xml, 'vector', i)
        self.qgis_styling_hook(map_layers)

    def qgis_styling_hook(self, layers: list[QgsMapLayer]):
        for layer in layers:
            sig = layer.rendererChanged.connect(self.mesh_layer_style_changed)
            self._style_changed_signals[layer] = sig

    def styling_xml(self, type_: str, group_index: int | str = 'active') -> str:
        layer = self._map_layers[0]
        rs = layer.rendererSettings()
        if group_index == 'active':
            group_index = rs.activeScalarDatasetGroup() if type_ == 'scalar' else rs.activeVectorDatasetGroup()
        if group_index < 0:
            return ''
        name = layer.datasetGroupMetadata(QgsMeshDatasetIndex(group_index)).name()
        doc = QDomDocument('QGIS-TUFLOW-Viewer-Saved-Styling')
        root = doc.createElement('render-settings')
        doc.appendChild(root)
        root.setAttribute('data-type', name)
        root.setAttribute('mapping-type', 'map')
        if type_ == 'scalar':
            root.appendChild(rs.scalarSettings(group_index).writeXml(doc))
        else:
            root.appendChild(rs.vectorSettings(group_index).writeXml(doc))
        return doc.toString()

    def load_styling_xml(self, xml: str, type_: str, group_index: int | str = 'active'):
        layer = self._map_layers[0]
        rs = layer.rendererSettings()
        if group_index == 'active':
            group_index = rs.activeScalarDatasetGroup() if type_ == 'scalar' else rs.activeVectorDatasetGroup()
        if group_index < 0:
            return
        doc = QDomDocument()
        ret = doc.setContent(xml)
        if not ret[0]:
            logger.warning(f'{ret[1]}, line: {ret[2]}, col: {ret[3]}')
            return
        root = doc.documentElement()
        maptype = root.attribute('mapping-type')
        render_settings = root.elementsByTagName('scalar-settings') if type_ == 'scalar' else root.elementsByTagName(
            'vector-settings')
        if not render_settings.count():
            return
        render_settings = render_settings.item(0).toElement()
        if type_ == 'vector':
            settings = rs.vectorSettings(group_index)
            settings.readXml(render_settings)
            rs.setVectorSettings(group_index, settings)
        else:
            settings = rs.scalarSettings(group_index)
            if maptype == 'map':
                settings.readXml(render_settings)
            else:  # ramp
                shader = settings.colorRampShader()
                min_ = shader.colorRampItemList()[0].value
                max_ = shader.colorRampItemList()[-1].value
                shader_settings = render_settings.elementsByTagName('colorrampshader').item(0).toElement()
                shader.readXml(shader_settings)
                shader.setMinimumValue(min_)
                shader.setMaximumValue(max_)
                if Qgis.QGIS_VERSION_INT >= 33800:
                    shader.setColorRampType(Qgis.ShaderInterpolationMethod.Linear)
                else:
                    shader.setColorRampType(0)
                shader.classifyColorRamp(5, -1, QgsRectangle(), None)
                settings.setColorRampShader(shader)
            rs.setScalarSettings(group_index, settings)

        layer.setRendererSettings(rs)

    def mesh_layer_style_changed(self):
        if self._block_style_changed_signal:
            return

        from qgis.utils import iface
        if iface is None:
            return

        self._block_style_changed_signal = True
        layer = self._map_layers[0]
        rs = layer.rendererSettings()

        scalar = rs.activeScalarDatasetGroup()
        vector = rs.activeVectorDatasetGroup()
        scalar_name = layer.datasetGroupMetadata(QgsMeshDatasetIndex(scalar)).name() if scalar != -1 else ''
        vector_name = layer.datasetGroupMetadata(QgsMeshDatasetIndex(vector)).name() if vector != -1 else ''

        def same_name_iter(layer: QgsMeshLayer, name: str) -> typing.Generator[int, None, None]:
            """Iterate through all dataset groups in the mesh layer and return if they are
            the same i.e. Depth/Maximums is the same as Depth.
            """
            stnd = Output._get_standard_data_type_name(name)
            for i in range(layer.datasetGroupCount()):
                name1 = layer.datasetGroupMetadata(QgsMeshDatasetIndex(i)).name()
                if name1 == name:
                    continue
                stnd1 = Output._get_standard_data_type_name(name1)
                if stnd == stnd1:
                    yield i

        if scalar_name:
            doc = self.styling_xml('scalar', scalar)
            for idx in same_name_iter(layer, scalar_name):
                doc1 = self.styling_xml('scalar', idx)
                if doc1 == doc:
                    continue
                self.load_styling_xml(doc, 'scalar', idx)

        if vector_name:
            doc = self.styling_xml('vector', scalar)
            for idx in same_name_iter(layer, scalar_name):
                doc1 = self.styling_xml('vector', idx)
                if doc1 == doc:
                    continue
                self.load_styling_xml(doc, 'vector', idx)

        self._block_style_changed_signal = False

    def init_crs(self):
        prj = self.fpath.with_suffix('.prj')
        if not prj.exists() and hasattr(self, 'twodm'):
            prj_2dm = self.twodm.with_suffix('.prj')
            if prj_2dm.exists():
                prj = prj_2dm
        if not prj.exists():
            return
        try:
            with open(prj) as f:
                wkt = f.read()
            self._layer.setCrs(QgsCoordinateReferenceSystem(wkt))
        except Exception as e:
            logger.warning(f'Failed to set CRS from .prj file: {prj} - {e}')

    def set_reference_time(self, reference_time: datetime):
        ref_time = QDateTime(QDate(reference_time.year, reference_time.month, reference_time.day),
                             QTime(reference_time.hour, reference_time.minute, reference_time.second,
                                   reference_time.microsecond // 1000),
                             QTimeZone(0))
        self._layer.setReferenceTime(ref_time)

    def init_temporal_properties(self):
        """Initialise temporal properties for the layer."""
        super().init_temporal_properties()
        self._layer.setTemporalMatchingMethod(QgsMeshDataProviderTemporalCapabilities.FindClosestDatasetFromStartRangeTime)
        if self.has_reference_time:
            return  # layer already has temporal properties setup
        self.set_reference_time(self.reference_time)
