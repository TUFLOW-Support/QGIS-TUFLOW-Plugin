import typing
from qgis.utils import plugins
from qgis.PyQt.QtCore import QSettings

if typing.TYPE_CHECKING:
    from .tuflow_viewer import TuflowViewer


def get_viewer_instance() -> 'TuflowViewer | None':
    """Convenience method that returns the active instance of the TuflowViewer class."""
    if plugins and 'tuflow' in plugins:
        tuflow_plugin = plugins['tuflow']
        if ((not hasattr(tuflow_plugin, 'tuflow_viewer') or tuflow_plugin.tuflow_viewer is None) and
                (QSettings().value('TUFLOW/UseNewTuflowViewer', False, type=bool) or QSettings().value('TUFLOW/TestCase', False, type=bool))):
            from qgis.utils import iface
            from .tuflow_viewer import TuflowViewer
            if TuflowViewer.viewer_initialising:
                return
            tuflow_plugin.tuflow_viewer = TuflowViewer(iface)
        return tuflow_plugin.tuflow_viewer
