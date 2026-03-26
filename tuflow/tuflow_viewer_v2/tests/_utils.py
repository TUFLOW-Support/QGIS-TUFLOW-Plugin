from pathlib import Path
import contextlib
from unittest import TestCase


class TuflowViewerTestCase(TestCase):

    def setUp(self):
        try:
            from PyQt5.QtCore import QSettings
        except ImportError:
            from PyQt6.QtCore import QSettings
        QSettings().setValue('TUFLOW/TestCase', True)
        from ..tvinstance import get_viewer_instance
        self.old_copy_on_load_setting = get_viewer_instance().settings.copy_results_on_load
        get_viewer_instance().settings.copy_results_on_load = False

    def tearDown(self):
        try:
            from PyQt5.QtCore import QSettings
        except ImportError:
            from PyQt6.QtCore import QSettings
        QSettings().setValue('TUFLOW/TestCase', False)
        from ..tvinstance import get_viewer_instance
        get_viewer_instance().settings.copy_results_on_load = self.old_copy_on_load_setting


def get_dataset_path(name: str, dataset_type: str) -> Path | None:
    dir_ = Path(__file__).parent / 'data'
    if dataset_type == 'vector layer':
        return dir_ / 'vector_layers' / name
    if dataset_type == 'result':
        return (dir_ / 'results').glob(f'**/{name}').__next__()


@contextlib.contextmanager
def add_layer_to_qgis(layer):
    """Context manager to ensure that any layer added to QGIS is removed after use as to
    not interfere with other tests.
    """
    from qgis.core import QgsProject
    project = QgsProject.instance()
    project.addMapLayer(layer)
    try:
        yield layer
    finally:
        project.removeMapLayer(layer.id())


@contextlib.contextmanager
def add_layers_to_qgis(layers):
    """Context manager to ensure that any layer added to QGIS is removed after use as to
    not interfere with other tests.
    """
    from qgis.core import QgsProject
    project = QgsProject.instance()
    project.addMapLayers(layers)
    try:
        yield layers
    finally:
        project.removeMapLayers([x.id() for x in layers])


@contextlib.contextmanager
def add_result_to_viewer(result):
    from qgis.core import QgsProject
    from ..tvinstance import get_viewer_instance
    layers = [x.id() for x in result.map_layers()]
    try:
        get_viewer_instance().load_output(result)
        yield result
    finally:
        from .stubs.qgis_stubs import QGIS
        QGIS.iface.setActiveLayer(None)
        QgsProject.instance().removeMapLayers(layers)


@contextlib.contextmanager
def add_results_to_viewer(results):
    from qgis.core import QgsProject
    from ..tvinstance import get_viewer_instance
    layers = [x.id() for result in results for x in result.map_layers()]
    try:
        for result in results:
            get_viewer_instance().load_output(result)
        yield results
    finally:
        from .stubs.qgis_stubs import QGIS
        QGIS.iface.setActiveLayer(None)
        QgsProject.instance().removeMapLayers(layers)
