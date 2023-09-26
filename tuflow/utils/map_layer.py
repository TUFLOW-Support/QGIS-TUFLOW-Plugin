from PyQt5.QtXml import QDomDocument
from qgis._core import QgsReadWriteContext

from ..compatibility_routines import Path


def clean_data_source(data_source: str) -> str:
    if '|layername=' in data_source:
        return '|'.join(data_source.split('|')[:2])
    else:
        return '|'.join(data_source.split('|')[:1])


def file_from_data_source(data_source: str) -> Path:
    return Path(data_source.split('|')[0])


def layer_name_from_data_source(data_source: str) -> str:
    if '|layername=' in data_source:
        return data_source.split('|')[1].split('=')[1]
    else:
        return Path(clean_data_source(data_source)).stem


def copy_layer_style(iface, src_lyr, dest_lyr):
    """Copies styling from one layer to another."""

    if src_lyr is None or dest_lyr is None:
        return

    # create dom document to store layer style
    doc = QDomDocument("styles")
    element = doc.createElement("maplayer")
    errorCopy = ''
    errorRead = ''
    src_lyr.writeStyle(element, doc, errorCopy, QgsReadWriteContext())

    # set style to new layer
    dest_lyr.readStyle(element, errorRead, QgsReadWriteContext())

    # refresh map and legend
    dest_lyr.triggerRepaint()
    iface.layerTreeView().refreshLayerSymbology(dest_lyr.id())
