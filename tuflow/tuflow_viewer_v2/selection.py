import json
import typing
from uuid import uuid4

from qgis.core import QgsFeature, QgsGeometry, Qgis, QgsVectorLayer
from qgis.gui import QgsVertexMarker, QgsMapCanvasItem
from qgis.PyQt.QtCore import QSettings

from .tvinstance import get_viewer_instance

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ..pt.pytuflow import TuflowPath
else:
    from tuflow.pt.pytuflow import TuflowPath

import logging
logger = logging.getLogger('tuflow_viewer')

if typing.TYPE_CHECKING:
    from .fmts.tvoutput import TuflowViewerOutput


class SelectionItem:

    def __init__(self, id_: str, geom: list | tuple, domain: str, domain_geom: str, chan_type: str,
                 is_tv_layer: bool, sel_type: str, colour: str | None, lyrid: str):
        self.id = id_
        self.geom = geom
        self.domain = domain
        self.domain_geom = domain_geom
        self.chan_type = chan_type
        self.is_tv_layer = is_tv_layer
        self.sel_type = sel_type
        self.colour = colour
        self.lyrid = lyrid

    def __eq__(self, other):
        if not isinstance(other, SelectionItem):
            return False
        return (self.id == other.id and
                self.geom == other.geom and
                self.domain == other.domain and
                self.domain_geom == other.domain_geom and
                self.chan_type == other.chan_type and
                self.is_tv_layer == other.is_tv_layer and
                self.sel_type == other.sel_type and
                self.colour == other.colour and
                self.lyrid == other.lyrid)


class Selection:

    def __init__(self, lyr: QgsVectorLayer | None, feats: list[QgsFeature]):
        self.feats = feats
        self._vector_lyr = lyr
        self._lyrid = lyr.id() if lyr and lyr.isValid() else ''
        self.lyr = {}
        # noinspection PyUnreachableCode,PyUnresolvedReferences
        is_tv_layer = lyr.customProperty('tuflow_viewer') is not None if lyr else False
        output = None
        if is_tv_layer:
            try:
                d = json.JSONDecoder().decode(lyr.customProperty('tuflow_viewer'))
                output = get_viewer_instance().output(d['id'])
            except json.JSONDecodeError:
                output = get_viewer_instance().output(lyr.customProperty('tuflow_viewer'))
                is_tv_layer = output is not None
        self.ids = []
        self.geom = {}
        self.domain = {}
        self.domain_geom = {}
        self.chan_type = {}
        self.extract(output)
        self.colour = {x: None for x in self.ids}
        self.sel_type = {x: 'selection' for x in self.ids}
        # noinspection PyUnreachableCode,PyUnresolvedReferences
        self.lyr = {x: lyr.id() if lyr else None for x in self.ids}
        self.is_tv_layer = {x: is_tv_layer for x in self.ids}

    def __iter__(self):
        for id_ in self.ids:
            yield SelectionItem(id_, self.geom[id_], self.domain[id_], self.domain_geom[id_], self.chan_type[id_],
                                self.is_tv_layer[id_], self.sel_type[id_], self.colour[id_], self.lyr[id_])

    def __bool__(self):
        return len(self.ids) > 0

    def __add__(self, other):
        sel = Selection(self._vector_lyr, [])
        if isinstance(other, Selection):
            sel.ids = self.ids + other.ids
            sel.geom = {**self.geom, **other.geom}
            sel.domain = {**self.domain, **other.domain}
            sel.domain_geom = {**self.domain_geom, **other.domain_geom}
            sel.chan_type = {**self.chan_type, **other.chan_type}
            sel.sel_type = {**self.sel_type, **other.sel_type}
            sel.colour = {**self.colour, **other.colour}
            sel.is_tv_layer = {**self.is_tv_layer, **other.is_tv_layer}
            sel.lyr = {**self.lyr, **other.lyr}
        elif isinstance(other, SelectionItem):
            sel.ids.append(other.id)
            sel.geom[other.id] = other.geom
            sel.domain[other.id] = other.domain
            sel.domain_geom[other.id] = other.domain_geom
            sel.chan_type[other.id] = other.chan_type
            sel.sel_type[other.id] = other.sel_type
            sel.colour[other.id] = other.colour
            sel.is_tv_layer[other.id] = other.is_tv_layer
            sel.lyr[other.id] = other.lyrid
        else:
            raise TypeError(f'Cannot add {type(other)} to Selection')
        return sel

    def clear(self):
        self.ids.clear()
        self.geom.clear()
        self.domain.clear()
        self.domain_geom.clear()
        self.chan_type.clear()
        self.sel_type.clear()
        self.colour.clear()
        self.lyr.clear()

    def get(self, sel_type: str = None, colour: str = None, lyrid: str = None, id_key: str = None) -> str | None:
        for id_ in reversed(self.ids[:]):
            if id_key and id_key != id_:
                continue
            if sel_type and sel_type != self.sel_type[id_]:
                continue
            if colour and colour != self.colour[id_]:
                continue
            if lyrid and lyrid != self.lyr[id_]:
                continue
            return id_
        return None

    def pop(self, sel_type: str = None, colour: str = None, lyrid: str = None, id_key: str = None) -> SelectionItem | None:
        id_ = self.get(sel_type, colour, lyrid, id_key)
        if not id_:
            return None
        sel = SelectionItem(id_, self.geom[id_], self.domain[id_], self.domain_geom[id_], self.chan_type[id_],
                            self.is_tv_layer[id_], self.sel_type[id_], self.colour[id_], self.lyr[id_])
        while id_ in self.ids:
            self.ids.remove(id_)
        del self.geom[id_]
        del self.domain[id_]
        del self.domain_geom[id_]
        del self.chan_type[id_]
        del self.sel_type[id_]
        del self.colour[id_]
        return sel

    def extract(self, output: 'TuflowViewerOutput'):
        d = {
            Qgis.GeometryType.Line: 'line',
            Qgis.GeometryType.Point: 'point',
            Qgis.GeometryType.Polygon: 'polygon'
        }
        for f in self.feats:
            id_suffix = f'{self._lyrid}-{f.id()}'
            chan_type = ''
            if output is None:
                id_ = ''
                domain = 'mapoutput'
            elif output.LAYER_TYPE == 'Plot':
                id_ = f['ID']
                if f['Type'].startswith('Chan') or f['Type'].startswith('CONDUIT'):
                    domain = 'channel'
                    chan_type = f['Type']
                    chan_type = chan_type.split('[', 1)[1].strip(' ]') if '[' in chan_type else chan_type
                elif f['Type'].startswith('Node'):
                    domain = 'node'
                elif f['Type'].startswith('PO') or f['Type'].startswith('2D'):
                    domain = '2d'
                else:
                    domain = 'rl'
            elif output.LAYER_TYPE == 'CrossSection':
                source = f['Source']
                col1 = f['Column_1']
                if f.fieldNameIndex('Provider') > -1 and f['Provider'] == 'FM DAT':
                    id_ = source
                elif col1 and isinstance(col1, str):
                    id_ = f'{source}:{col1}'
                else:
                    id_ = f'{source}:{TuflowPath(source).stem}'
                domain = 'crosssection'
            elif output.LAYER_TYPE == 'BCTable':
                if f.fieldNameIndex('Source') > -1:
                    id_ = f['Source'].split(':', 1)[0].strip() if isinstance(f['Source'], str) else ''
                elif f.fieldNameIndex('BC_Name') > -1:
                    id_ = f['BC_Name'] if isinstance(f['BC_Name'], str) else ''
                else:
                    id_ = f['Name'] if isinstance(f['Name'], str) else ''
                if not id_:
                    logger.error(f'Unable to get boundary name from feature ({f.id()}) in layer {self._vector_lyr.name()}')
                domain = 'bctable'
            elif output.LAYER_TYPE == 'HydTable':
                id_ = f['ID'] if isinstance(f['ID'], str) else ''
                domain = 'hydraulictable'
            elif output.LAYER_TYPE == 'FVBCTide':
                id_ = f['ID'] if isinstance(f['ID'], str) else ''
                domain = 'fvbctide'
            else:
                id_ = f'{self._lyrid}-{f.id()}'
                domain = 'mapoutput'
            id_ = f'TUFLOW-VIEWER::{id_}::{id_suffix}'  # ensure uniqueness across different result that may use the same feature IDs
            self.geom[id_] = self.geom_extract(f.geometry())
            self.ids.append(id_)
            self.domain[id_] = domain
            self.domain_geom[id_] = d[self._vector_lyr.geometryType()]
            self.chan_type[id_] = chan_type

    @staticmethod
    def geom_extract(geom: QgsGeometry) -> list:
        if geom.type() == Qgis.GeometryType.Point:
            p = geom.asMultiPoint()[0] if geom.isMultipart() else geom.asPoint()
            return [p.x(), p.y()]
        elif geom.type() == Qgis.GeometryType.Line:
            return [[p.x(), p.y()] for p in geom.asMultiPolyline()[0]] if geom.isMultipart() else [[p.x(), p.y()] for p in geom.asPolyline()]
        elif geom.type() == Qgis.GeometryType.Polygon:
            return [[p.x(), p.y()] for x in geom.asMultiPolygon()[0] for p in x] if geom.isMultipart() else [[p.x(), p.y()] for x in geom.asPolygon() for p in x]
        return []


class DrawnSelection(Selection):

    def __init__(self, map_item: QgsMapCanvasItem, *args, **kwargs):
        super().__init__(None, [])
        self.map_item = map_item
        if isinstance(self.map_item, QgsVertexMarker):
            color = map_item.color()
        else:
            color = map_item.fillColor()
        self._id = f'{uuid4()}-{color.name()}'
        self.ids = [self._id]

        if isinstance(self.map_item, QgsVertexMarker):
            self.geom = {self._id: self.geom_extract(QgsGeometry.fromPointXY(map_item.center()))}
        else:
            self.geom = {self._id: self.geom_extract(map_item.asGeometry())}

        self.sel_type = {self._id: 'drawn'}
        self.colour = {self._id: color.name()}
        self.lyr = {self._id: None}
        self.domain = {self._id: '2d'}
        self.chan_type = {self._id: ''}
        if isinstance(self.map_item, QgsVertexMarker):
            self.domain_geom = {self._id: 'point'}
        else:
            self.domain_geom = {self._id: 'line'}

        self.is_tv_layer = {self._id: False}
