import json
import os
from datetime import datetime
from pathlib import Path

from qgis.core import QgsMapLayer
from qgis.PyQt.QtCore import QSettings

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import TuflowPath
else:
    from tuflow.pt.pytuflow import TuflowPath

import logging
logger = logging.getLogger('tuflow_viewer')


class CopyOnLoadMixin:
    """Mixin to add copy on load functionality to mesh drivers."""

    def mapped_paths(self):
        from ...tuflow_plugin_cache import get_cached_content
        mapped_paths = get_cached_content('tuflow_viewer/copied_results/mapped_paths.json', str)
        return json.loads(mapped_paths) if mapped_paths else {}

    def save_mapped_paths(self, mapped_paths: dict):
        from ...tuflow_plugin_cache import save_cached_content
        save_cached_content('tuflow_viewer/copied_results/mapped_paths.json', json.dumps(mapped_paths, indent=2))

    def new_path(self, fpath: Path | str) -> Path:
        from ...tuflow_plugin_cache import cache_dir
        fpath = Path(fpath)
        name = f'{fpath.stem}_{fpath.suffix[1:]}_{hex(int(datetime.now().timestamp()))[2:]}_{hex(int(os.path.getmtime(fpath)))[2:]}'
        return Path(cache_dir('tuflow_viewer/copied_results')) / name / fpath.name

    def copy(self, fpath: Path) -> Path:
        from ...utils.copy_file import copy_file_with_progbar
        from qgis.utils import iface

        logger.info('Copying file before loading into QGIS')
        mapped_paths = self.mapped_paths()
        dst, mtime = mapped_paths[str(fpath)] if str(fpath) in mapped_paths else [self.new_path(fpath), -1]
        dst = Path(dst)
        if dst.exists() and mtime == os.path.getmtime(fpath):
            logger.info('Copied file already exists and is up to date, using existing copy: {}'.format(dst))
            return dst

        if dst.exists() and mtime < os.path.getmtime(fpath):
            logger.info('Copied file exists but is outdated, creating new copy')
            try:
                with open(dst, 'rb+'):
                    pass
                # old file is not locked, safe to copy over
            except Exception:
                dst = self.new_path(fpath)
                logger.info('Original copied file is locked, copying to a new location')

        parent = iface.mainWindow() if iface is not None else None
        if not dst.parent.exists():
            dst.parent.mkdir(parents=True)
        copy_file_with_progbar(fpath, dst, parent=parent)
        logger.info(f'Copied file to: {dst}')
        mapped_paths[str(fpath)] = [str(dst), os.path.getmtime(fpath)]
        self.save_mapped_paths(mapped_paths)
        return dst

    def reload_layer(self, layer: QgsMapLayer, copied_map: dict):
        from ...utils.copy_file import copy_file_with_progbar
        from ..tvinstance import get_viewer_instance
        from qgis.utils import iface

        copied_map = {Path(p): v for p, v in copied_map.items()}
        dst = Path(TuflowPath(layer.dataProvider().dataSourceUri()).dbpath)
        if dst.suffix.lower() == '.2dm':
            for extra in layer.dataProvider().extraDatasets():
                if Path(extra) in copied_map:
                    dst = Path(extra)
        if not copied_map or dst not in copied_map:
            logger.info('No copied data mapping found for layer, reloading normally')
            layer.reload()
            return
        logger.info('Synchronizing copied data with source layer')

        src, mtime = copied_map[dst]
        if os.path.getmtime(src) == mtime:
            logger.info('Copied file is up to date, no need to reload layer')
            return

        new_dst = self.new_path(src)
        logger.info('Copying updated file into: {}'.format(new_dst))
        parent = iface.mainWindow() if iface is not None else None
        if not new_dst.parent.exists():
            new_dst.parent.mkdir(parents=True)
        output = get_viewer_instance().map_layer_to_output(layer)
        mapped_paths = self.mapped_paths()
        mapped_paths[str(src)] = [str(new_dst), os.path.getmtime(src)]
        self.save_mapped_paths(mapped_paths)
        copy_file_with_progbar(src, new_dst, parent, lambda x: output.set_data_source(new_dst))
