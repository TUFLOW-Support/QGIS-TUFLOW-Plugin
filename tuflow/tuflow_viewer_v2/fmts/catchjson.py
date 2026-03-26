import json
from pathlib import Path

from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsMeshLayer, QgsProject

from .map_output_mixin import MapOutputMixin
from .catchqgishooks import CATCHQgisHooks
from . import catchproviders

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import CATCHJson as CATCHJsonBase
    from ...pt.pytuflow import misc
else:  # when running tests outside of QGIS environment
    from tuflow.pt.pytuflow import CATCHJson as CATCHJsonBase
    from tuflow.pt.pytuflow import misc

import logging
logger = logging.getLogger('tuflow_viewer')


class CATCHJson(CATCHJsonBase, MapOutputMixin, CATCHQgisHooks):
    DRIVER_NAME = 'TUFLOW CATCH Json'
    LAYER_TYPE = 'Surface'

    def __init__(self, fpath: str | Path, layers: list[QgsMeshLayer] = (), alias: str = ''):
        super(CATCHJson, self).__init__(fpath)
        self._init_viewer_output_mixin(self.name)
        self.alias = alias if alias else self.name  # the alias is needed when loading from a project if the user changed the index layer name

        # overwrite providers with providers from the TuflowViewer fmts
        self._load_viewer_providers(layers)

        i = 0
        # when loaded initially, the layer will be called by the index name, when loaded
        # from a project, it will have been renamed to the result name
        sort_key = {self._data['index']: 0, self.name: 0, self.alias: 0}
        for name in reversed(self._data['outputs']):
            if name != self._data['index']:
                i += 1
                sort_key[name] = i
        self._map_layers = sorted(misc.flatten([provider.map_layers() for provider in self._providers.values()]), key=lambda x: sort_key[x.name()])
        self.init_temporal_properties()

        self._init_catch_qgis_hooks(self.alias, self._data, self._providers)

    def close(self):
        self._teardown_viewer_output_mixin()

    def pre_close(self, layerids: list[str]):
        self._teardown_catch_qgis_hooks()
        for lyr in self._map_layers.copy():
            if lyr != self.index.layer and lyr.id() not in layerids:
                try:
                    self._map_layers.remove(lyr)
                    QgsProject.instance().removeMapLayer(lyr.id())
                except Exception:
                    logger.debug('ERROR: CATCHJson.pre_close() - could not remove layer {0}'.format(lyr.name()))

    @staticmethod
    def format_compatible(fpath: Path | str) -> bool:
        return CATCHJson._looks_like_this(fpath)

    def to_json(self) -> str:
        """Serialize the object to a JSON string.
        Used for saving/loading sessions.
        """
        d = {
            'class': self.__class__.__name__,
            'id': self.id,
            'fpath': str(self.fpath),
            'name': self.name,
            'alias': self.alias,
            'lyrids': [x.id() for x in self.map_layers()],
            'duplicated': [lyr.id() for x in self.duplicated_outputs for lyr in x.map_layers()],
            'copied_files': {str(k): (str(v[0]), v[1]) for k, v in self.copied_files.items()},
        }
        return json.dumps(d)

    @staticmethod
    def from_json(string) -> 'TuflowViewerOutput':
        """Deserialize the object from a JSON string.
        Used for saving/loading sessions.
        """
        d = json.loads(string)
        lyrids = d['lyrids']
        lyrs = [QgsProject.instance().mapLayer(x) for x in lyrids]
        if not lyrs:
            logger.error('No vector layers loaded for TPC: {0}'.format(d['name']))
            raise ValueError('No vector layers loaded for TPC: {0}'.format(d['name']))
        for lyr in lyrs:
            if not lyr.isValid():
                logger.error('Vector layer for TPC output not found in project: {0}'.format(d['name']))
                raise ValueError('Vector layer for TPC output not found in project: {0}'.format(d['name']))
        res = CATCHJson(d['fpath'], layers=lyrs, alias=d['alias'])
        res.id = d['id']
        res.copied_files = d.get('copied_files', {})
        return res

    def _load_viewer_providers(self, layers: list[QgsMeshLayer]):
        def get_layer(output_name: str, avail_layers: list[QgsMeshLayer]) -> QgsMeshLayer:
            for lyr in avail_layers:
                try:
                    lyrname = Path(lyr.dataProvider().dataSourceUri()).stem
                    if output_name.lower() == lyrname.lower():
                        return lyr
                except Exception:
                    pass

        default_ref_time = self.times(fmt='absolute')[0]

        for name, provider in self._providers.copy().items():
            p = self.fpath.parent / self._data['output data'][name]['path']
            lyr = get_layer(name, layers)
            format_ = self._data['output data'][name]['format']
            if format_ == 'netcdf mesh':
                tv_provider = catchproviders.CATCHProviderNCMesh(
                    p,
                    layers=[lyr],
                    data=self._data['output data'][name],
                    parent_reference_time=self.reference_time,
                    default_reference_time=default_ref_time,
                )
            elif format_ == 'xmdf':
                twodm = self.fpath.parent / self._data['output data'][name]['2dm']
                tv_provider = catchproviders.CATCHProviderXMDF(
                    p,
                    twodm=twodm,
                    layer=lyr,
                    data=self._data['output data'][name],
                    parent_reference_time=self.reference_time,
                    default_reference_time=default_ref_time,
                )
            else:
                tv_provider = None
                logger.error(f'Result type in TUFLOW CATCH .json file is not currently supported in TUFLOW Viewer: {format_}')
            if tv_provider is not None:
                self._providers[name] = tv_provider
                if provider == self._idx_provider:
                    self._idx_provider = tv_provider
