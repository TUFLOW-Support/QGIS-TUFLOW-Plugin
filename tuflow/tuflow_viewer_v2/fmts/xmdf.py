import json
import os
import shutil
from pathlib import Path

from qgis.core import (QgsMeshLayer, QgsProject, Qgis, QgsMeshDatasetIndex)
from qgis.PyQt.QtCore import QSettings, QDateTime, QDate, QTime, QTimeZone, QTimer

from .mesh_mixin import MeshMixin
from .qgis_mesh_api_mixin import QgisMeshAPIMixin
from .pyxmdf import PyXMDF

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import XMDF as XMDFBase, Output, Mesh
    from ...pt.pytuflow._outputs.helpers.super_file import SuperFile
else:  # when running tests outside of QGIS environment
    from tuflow.pt.pytuflow import XMDF as XMDFBase, Output, Mesh
    from tuflow.pt.pytuflow._outputs.helpers.super_file import SuperFile

import logging
logger = logging.getLogger('tuflow_viewer')


class SoftLoadDriverDummy: valid = False


class XMDF(XMDFBase, MeshMixin, QgisMeshAPIMixin):

    DRIVER_NAME = 'XMDF'
    LAYER_TYPE = 'Surface'

    def __init__(self, fpath: Path | str, twodm: Path | str = None, layer: QgsMeshLayer = None):
        if Path(fpath).suffix.lower() == '.sup':
            sup = SuperFile(fpath)
            fpath = Path(fpath).parent / sup['DATA']
            self.twodm = Path(fpath).parent / Path(sup['MESH2D'])
        else:
            self.twodm = Path(twodm) if twodm else self._find_2dm(fpath)

        if not self.twodm.exists():
            raise FileNotFoundError(f'2dm file does not exist: {self.twodm}')

        Mesh.__init__(self, self.twodm)
        self.fpath = Path(fpath)
        self._driver = PyXMDF(self.fpath, self.twodm, geom_driver='qgis', mesh=layer)
        self._driver.extractor.open_reader()
        self._soft_load_driver = self._driver
        self._initial_load()
        self._load()

        if self._driver.extractor.NAME == 'PyDataExtractor' and layer is None:
            if self._driver.fpath.suffix.lower() == '.xmdf':
                success = self._driver.lyr.dataProvider().addDataset(str(self._driver.fpath))
                if not success:
                    raise RuntimeError(f'Failed to load xmdf results onto 2dm: {self._driver.fpath}')

        self._init_viewer_output_mixin(self.name)
        self.copied_files = self._driver.copied_files

        self._layer = self._driver.lyr
        self._map_layers.append(self._layer)

        # QGIS specific
        self.init_crs()
        self.init_temporal_properties()
        self._init_styling(self._map_layers, self._lyr2resultstyle)

    def __del__(self):
        self.close()

    def close(self):
        self._driver.extractor.close_reader()
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
                xmdfs = sup['DATA']
                if isinstance(xmdfs, list):
                    xmdfs = [p.parent / d for d in xmdfs]
                else:
                    xmdfs = [p.parent / xmdfs]
                return bool(xmdfs) and XMDF._looks_like_this(xmdfs[0])
        except Exception:
            pass
        return XMDFBase._looks_like_this(p)

    @staticmethod
    def from_json(string) -> 'XMDF':
        d = json.loads(string)
        lyrid = d['lyrids'][0]
        lyr = QgsProject.instance().mapLayer(lyrid)
        if not lyr or not lyr.isValid():
            logger.error('Mesh layer for XMDF output not found in project: {0}'.format(d['name']))
            raise ValueError('Mesh layer not found in project')
        xmdf = XMDF(d['fpath'], d['2dm'], layer=lyr)
        xmdf.id = d['id']
        xmdf.duplicated_outputs = [QgsProject.instance().mapLayer(x) for x in d['duplicated'] if QgsProject.instance().mapLayer(x)]
        xmdf.copied_files = d.get('copied_files', {})
        return xmdf

    def to_json(self) -> str:
        d = {
            'class': 'XMDF',
            'id': self.id,
            'fpath': str(self.fpath),
            'name': self.name,
            '2dm': str(self.twodm),
            'lyrids': [x.id() for x in self.map_layers()],
            'duplicated': [lyr.id() for x in self.duplicated_outputs for lyr in x.map_layers()],
            'copied_files': {str(k): (str(v[0]), v[1]) for k, v in self.copied_files.items()},
        }
        return json.dumps(d)

    def maximum(self, data_type: str) -> float:
        return self._driver.maximum(data_type)

    def minimum(self, data_type: str) -> float:
        return self._driver.minimum(data_type)

    def reload_layer(self, layer: QgsMeshLayer, copied_files_mapping: dict):
        if copied_files_mapping and Qgis.QGIS_VERSION_INT < 34200:
            logger.warning('Reloading copied XMDF files requires QGIS 3.42 or later')
            return
        self._driver.reload_layer(layer, copied_files_mapping)

    def set_data_source(self, new_fpath: Path):
        one_failed = False
        # remove XMDF datasets so it can be re-added.
        # Dataset indexing will remain the same, but datasets can be added/removed,
        # so a dataset at index 10 will remain at index 10 even if datasets 0-9 are removed.
        dataset_count = self._layer.datasetGroupCount() - 1
        mat_id = self.group_index_from_name('material id')
        min_datasets = 1 if mat_id == -1 else 2

        i = 0
        max_iter = 1_000
        while self._layer.dataProvider().datasetGroupCount() > min_datasets and i < max_iter:
            ind = QgsMeshDatasetIndex(i, 0)
            grp_metadata = self._layer.dataProvider().datasetGroupMetadata(ind)
            name = grp_metadata.name()
            if not name:
                i += 1
                continue
            if name.lower() in ['bed elevation', 'material id']:
                i += 1
                continue
            _ = self._layer.dataProvider().removeDatasetGroup(i)
            self._layer.reload()
            i += 1
        QTimer.singleShot(300, lambda: self._set_data_source_delayed(new_fpath))

    def _set_data_source_delayed(self, new_fpath: str):
        from ..tvinstance import get_viewer_instance

        logger.info('Loading copied XMDF results')
        v1_1_driver = self._driver.DRIVER_SOURCE == 'python'

        if v1_1_driver:
            self._driver.set_data_source(new_fpath)
        else:
            self._driver.xmdf = Path(new_fpath)
        old_src = list(self.copied_files.keys())[0]
        orig = self.copied_files[old_src]
        self.copied_files.clear()
        self.copied_files[str(new_fpath)] = (str(orig[0]), os.path.getmtime(orig[0]))
        success = self._layer.dataProvider().addDataset(str(new_fpath))
        if not success:
            raise RuntimeError(f'Failed to load xmdf results onto 2dm: {self._driver.xmdf}')
        self._layer.reload()
        self._initial_load()

        try:
            with open(old_src, 'rb+'):
                pass
            Path(old_src).unlink()
            shutil.rmtree(Path(old_src).parent, ignore_errors=True)
            logger.info('Deleted previously copied file: {}'.format(old_src))
        except Exception:
            logger.info('Original copied file is locked, cannot remove: {}'.format(old_src))

        for extra in self._layer.dataProvider().extraDatasets():
            if extra == str(new_fpath):
                logger.info('Successfully sync\'d and reloaded XMDF results.', extra={'messagebar': True})
                break

        self.init_temporal_properties()
        self._init_styling(self._map_layers, self._lyr2resultstyle)
        get_viewer_instance().configure_temporal_controller()
