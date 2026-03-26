import typing

from qgis.core import QgsMeshDatasetIndex


class QgisMeshAPIMixin:

    def data_groups(self, source: str = 'layer') -> typing.Generator[int, None, None]:
        if not self._driver.lyr:
            raise RuntimeError('Layer not loaded.')

        source = self._driver.lyr if source == 'layer' else self._driver.lyr.dataProvider()
        dataset_group_count = source.datasetGroupCount()
        i = -1
        while dataset_group_count:
            i += 1
            ind = QgsMeshDatasetIndex(i, 0)
            grp = source.datasetGroupMetadata(ind)
            name = grp.name()
            if not name:
                continue
            dataset_group_count -= 1
            yield i

    def group_index_from_name(self, data_type: str, source: str = 'layer', type_: str = '') -> int:
        from ...pt.pytuflow import MapOutput
        source = self._driver.lyr if source == 'layer' else self._driver.lyr.dataProvider()
        data_type = MapOutput._get_standard_data_type_name(data_type)
        for i in self.data_groups(source):
            ind = QgsMeshDatasetIndex(i)
            grp_metadata = source.datasetGroupMetadata(ind)
            name = MapOutput._get_standard_data_type_name(grp_metadata.name())
            result_type = 'vector' if grp_metadata.isVector() else 'scalar'
            if name == data_type:
                if not type_ or type_ == result_type:
                    return i
                if type_ == 'vector' and data_type in ['velocity', 'max velocity']:
                    if data_type == 'velocity':
                        data_type_ = 'vector velocity'
                    else:
                        data_type_ = 'max vector velocity'
                    return self.group_index_from_name(data_type_, source, type_)
        return -1
