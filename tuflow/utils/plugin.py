from qgis.utils import plugins


def tuflow_plugin():
    """Returns the TUFLOW Plugin instance."""
    return plugins.get('tuflow')
