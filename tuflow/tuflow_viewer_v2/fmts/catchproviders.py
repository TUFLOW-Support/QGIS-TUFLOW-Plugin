import typing
from datetime import datetime, timezone
from pathlib import Path

from qgis.PyQt.QtCore import QSettings, QDateTime, QDate, QTime, QTimeZone
from qgis.core import QgsMeshLayer, QgsMeshDatasetIndex, QgsStyle, QgsColorRampShader
from qgis.utils import iface

from .xmdf import XMDF
from .ncmesh import NCMesh

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow._outputs.helpers.catch_providers import CATCHProvider as CATCHProviderBase
    from ...pt.pytuflow.misc import CaseInsDict
else:  # when running tests outside of QGIS environment
    from tuflow.pt.pytuflow._outputs.helpers.catch_providers import CATCHProvider as CATCHProviderBase
    from tuflow.pt.pytuflow.misc import CaseInsDict


class CATCHProvider(CATCHProviderBase):

    def __init__(self, *args,
                 data: dict = None,
                 parent_reference_time: datetime = datetime(1990, 1, 1),
                 default_reference_time: datetime = datetime(1990, 1, 1),
                 **kwargs):
        super().__init__(*args, **kwargs)
        if not self.has_inherent_reference_time:
            self.reference_time = default_reference_time
            self.set_provider_reference_time(self.reference_time)
        self._glob2loc = CaseInsDict(data['result type map'])
        self._loc2glob = CaseInsDict({val: key for key, val in self._glob2loc.items()})
        self.time_offset = (self.reference_time - parent_reference_time).total_seconds()

    @property
    def layer(self) -> QgsMeshLayer:
        return self._map_layers[0]

    def global_name(self, local_name: str):
        return self._loc2glob[local_name]

    def local_name(self, global_name: str):
        return self._glob2loc[global_name]

    def provider_data_types(self, scope: str = 'global') -> typing.Generator[str, None, None]:
        if scope == 'global':
            yield from self._glob2loc.keys()
        else:
            yield from self._loc2glob.keys()

    def provider_reference_time(self) -> datetime:
        pass

    def set_provider_reference_time(self, ref_time: datetime):
        pass

    def active_scalar_data_type(self, group_index: int = -1, scope: str = 'global'):
        pass

    def set_active_scalar_data_type(self, name: str, scope: str = 'global'):
        pass

    def active_vector_data_type(self, group_index: int = -1, scope: str = 'global'):
        pass

    def set_active_vector_data_type(self, name: str, scope: str = 'global'):
        pass


class CATCHProviderMesh(CATCHProvider):

    def provider_reference_time(self) -> datetime:
        ref_time = self.layer.temporalProperties().referenceTime()
        if ref_time.isValid():
            return datetime(ref_time.date().year(), ref_time.date().month(), ref_time.date().day(),
                            ref_time.time().hour(), ref_time.time().minute(), ref_time.time().second(),
                            tzinfo=timezone.utc)
        return datetime(1990, 1, 1, tzinfo=timezone.utc)

    def set_provider_reference_time(self, ref_time: datetime):
        qdt = QDateTime(QDate(ref_time.year, ref_time.month, ref_time.day),
                        QTime(ref_time.hour, ref_time.minute, ref_time.second),
                        QTimeZone(0))
        self.layer.setReferenceTime(qdt)

    def dataset_group_index(self, data_type: str, scope: str = 'global') -> int:
        if scope == 'global':
            data_type = self.local_name(data_type)
        group_index = -1
        for i in range(self.layer.datasetGroupCount()):
            if self.layer.datasetGroupMetadata(QgsMeshDatasetIndex(i)).name().lower() == data_type.lower():
                group_index = i
                break
        return group_index

    def provider_min(self, data_type: str, scope: str = 'global'):
        group_index = self.dataset_group_index(data_type, scope)
        if group_index == -1:
            return 9e29
        return self.layer.datasetGroupMetadata(QgsMeshDatasetIndex(group_index)).minimum()

    def provider_max(self, data_type: str, scope: str = 'global'):
        group_index = self.dataset_group_index(data_type, scope)
        if group_index == -1:
            return -9e29
        return self.layer.datasetGroupMetadata(QgsMeshDatasetIndex(group_index)).maximum()

    def init_style(self, data_type: str, minmax: tuple[float, float], scope: str = 'global'):
        group_index = self.dataset_group_index(data_type, scope)
        layer_tree = iface.layerTreeView()
        if not layer_tree:
            return

        # get renderer settings
        rs = self.layer.rendererSettings()
        settings = rs.scalarSettings(group_index)
        settings.setClassificationMinimumMaximum(*minmax)

        # create a new color ramp shader
        shader = settings.colorRampShader()
        colour_ramp_gradient = QgsStyle().defaultStyle().colorRamp('Plasma')
        colour_ramp_gradient.invert()
        new_shader = QgsColorRampShader(minmax[0], minmax[1], colour_ramp_gradient, shader.colorRampType())
        new_shader.classifyColorRamp(10, -1)
        settings.setColorRampShader(new_shader)

        # apply changes
        rs.setScalarSettings(group_index, settings)
        self.layer.setCustomProperty('block-signal', True)
        self.layer.setRendererSettings(rs)
        self.layer.removeCustomProperty('block-signal')

    def active_scalar_data_type(self, group_index: int = -1, scope: str = 'global'):
        if group_index == -1:
            group_index = self.layer.rendererSettings().activeScalarDatasetGroup()
        loc_name = self.layer.datasetGroupMetadata(QgsMeshDatasetIndex(group_index)).name()
        if scope == 'global' and loc_name:
            return self.global_name(loc_name)
        return loc_name

    def set_active_scalar_data_type(self, name: str, scope: str = 'global'):
        group_index = self.dataset_group_index(name, scope) if name else -1
        rs = self.layer.rendererSettings()
        rs.setActiveScalarDatasetGroup(group_index)
        self.layer.setRendererSettings(rs)

    def active_vector_data_type(self, group_index: int = -1, scope: str = 'global'):
        if group_index == -1:
            group_index = self.layer.rendererSettings().activeVectorDatasetGroup()
        loc_name = self.layer.datasetGroupMetadata(QgsMeshDatasetIndex(group_index)).name()
        if scope == 'global' and loc_name:
            return self.global_name(loc_name)
        return loc_name

    def set_active_vector_data_type(self, name: str, scope: str = 'global'):
        group_index = self.dataset_group_index(name, scope) if name else -1
        rs = self.layer.rendererSettings()
        rs.setActiveVectorDatasetGroup(group_index)
        self.layer.setRendererSettings(rs)


class CATCHProviderXMDF(CATCHProviderMesh, XMDF):
    # no-auto-import
    pass


class CATCHProviderNCMesh(CATCHProviderMesh, NCMesh):
    # no-auto-import
    pass
