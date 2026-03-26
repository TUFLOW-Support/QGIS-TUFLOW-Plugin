import json
from pathlib import Path

import numpy as np
try:
    import pandas as pd
except ImportError:
    from ...pt.pytuflow._outputs.pymesh.stubs import pandas as pd
from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsMeshLayer, QgsProject

from .mesh_mixin import MeshMixin
from .qgis_mesh_api_mixin import QgisMeshAPIMixin
from .pydat import PyDAT

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import DAT as DATBase
    from ...pt.pytuflow._outputs.helpers.super_file import SuperFile
else:  # when running tests outside of QGIS environment
    from tuflow.pt.pytuflow import DAT as DATBase
    from tuflow.pt.pytuflow._outputs.helpers.super_file import SuperFile

import logging
logger = logging.getLogger('tuflow_viewer')


class DAT(DATBase, MeshMixin, QgisMeshAPIMixin):
    DRIVER_NAME = 'SMS DAT'
    LAYER_TYPE = 'Surface'

    def __init__(self, fpath: str | Path, twodm: str | Path = None, layer: QgsMeshLayer = None, dats: list[str | Path] = ()):
        super(DAT, self).__init__(fpath, twodm)
        if dats:
            self._dats = [Path(x) for x in dats]
        self._driver = PyDAT(self._dats, self.twodm, geom_driver='qgis', engine='qgis', mesh=layer)
        self._init_viewer_output_mixin(self.name)
        self._load()

        self._layer = self._driver.lyr
        self._map_layers.append(self._layer)

        # QGIS specific
        self.init_crs()
        self.init_temporal_properties()
        self._init_styling(self._map_layers, self._lyr2resultstyle)

    def close(self):
        self._teardown_viewer_output_mixin()

    @staticmethod
    def format_compatible(fpath: Path | str) -> bool:
        """Returns True if the file is of this format.
        This is used to determine if the handler is suitable for the file.
        """
        p = Path(fpath)
        try:
            if p.suffix.lower() == '.sup':
                sup = SuperFile(p)
                dats = sup['DATA']
                if isinstance(dats, list):
                    dats = [p.parent / d for d in dats]
                else:
                    dats = [p.parent / dats]
                return bool(dats) and DATBase._looks_like_this(dats[0])
        except Exception:
            pass
        return DATBase._looks_like_this(p)

    def to_json(self) -> str:
        d = {
            'class': self.__class__.__name__,
            'id': self.id,
            'fpath': str(self.fpath),
            'name': self.name,
            '2dm': str(self.twodm),
            'dats': [str(x) for x in self._dats],
            'lyrids': [x.id() for x in self.map_layers()],
            'duplicated': [lyr.id() for x in self.duplicated_outputs for lyr in x.map_layers()],
            'copied_files': {str(k): (str(v[0]), v[1]) for k, v in self.copied_files.items()},
        }
        return json.dumps(d)

    @staticmethod
    def from_json(string) -> 'DAT':
        d = json.loads(string)
        lyrid = d['lyrids'][0]
        lyr = QgsProject.instance().mapLayer(lyrid)
        if not lyr or not lyr.isValid():
            logger.error('Mesh layer for XMDF output not found in project: {0}'.format(d['name']))
            raise ValueError('Mesh layer not found in project')
        res = DAT(d['fpath'], d['2dm'], layer=lyr, dats=d['dats'])
        res.id = d['id']
        res.copied_files = d.get('copied_files', {})
        return res

    @staticmethod
    def find_2dm(fpath: Path | str) -> Path:
        p = Path(fpath)
        if p.suffix.lower() == '.sup':
            sup = SuperFile(p)
            return p.parent / sup['MESH2D']
        return DATBase._find_2dm(p)

    def add_dataset(self, fpath: Path | str):
        success = self._driver.dp.addDataset(str(fpath))
        if not success:
            raise RuntimeError(f'Failed to load DAT results onto 2dm: {fpath}')
        self._dats.append(fpath)
        self._driver.clear_cache()
        self._load_info()

    def _initial_load(self):
        self.name = self.twodm.stem

    def _load(self):
        super()._load()
        if self._driver.has_inherent_reference_time:
            self.reference_time = self._driver.reference_time
        self._load_info()

    def _load_info(self):
        d = {'data_type': [], 'type': [], 'is_max': [], 'is_min': [], 'static': [], '3d': [], 'start': [], 'end': [],
             'dt': []}
        for dtype in self._driver.data_groups():
            d['type'].append(dtype.type)
            d['is_min'].append('/minimums' in dtype.name.lower())
            d['is_max'].append('/maximums' in dtype.name.lower())
            d['data_type'].append(self._get_standard_data_type_name(dtype.name))
            d['start'].append(np.round(dtype.times[0], decimals=6))
            d['end'].append(np.round(dtype.times[-1], decimals=6))
            static = len(dtype.times) == 1
            d['static'].append(static)
            d['3d'].append(dtype.vert_lyr_count > 1)
            dt = 0.
            if not static:
                dt = self._calculate_time_step(np.array(dtype.times) * 3600.)
            d['dt'].append(dt)
        self._info = pd.DataFrame(d)
