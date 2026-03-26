import typing

import numpy as np
from qgis.PyQt.QtWidgets import (QGraphicsPolygonItem, QStyleOptionGraphicsItem, QWidget, QGraphicsSceneHoverEvent,
                                 QGraphicsItem, QGraphicsObject)
from qgis.PyQt.QtGui import QPolygonF, QPainter, QBrush, QPainterPath, QMouseEvent, QPen, QColor, QPainterPathStroker
from qgis.PyQt.QtCore import QRectF, QPointF, pyqtSignal, QEvent, Qt, QObject, QSettings

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....compatibility_routines import QT_SOLID_LINE
    from ....tvinstance import get_viewer_instance
    from .....pyqtgraph import GraphicsObject, mkPen, mkBrush
    from .....pyqtgraph.GraphicsScene.mouseEvents import HoverEvent
else:
    from tuflow.compatibility_routines import QT_SOLID_LINE
    from tuflow.tuflow_viewer_v2.tvinstance import get_viewer_instance
    from tuflow.pyqtgraph import GraphicsObject, mkPen, mkBrush
    from tuflow.pyqtgraph.GraphicsScene.mouseEvents import HoverEvent

from .hoverable_base_class import HoverableBaseClass

if typing.TYPE_CHECKING:
    from ..plotsourceitem import PlotSourceItem


class Polygon(QGraphicsObject):
    sigHoverEvent = pyqtSignal(HoverEvent, QGraphicsObject)

    def __init__(self, polygon: QPolygonF, channel_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._polygon = polygon
        self.channel_id = channel_id
        self._brush = QBrush()
        self._brush_normal = QBrush()
        self._brush_darker = QBrush()
        self._pen = QPen()
        self._bounding_rect = None

    def polygon(self) -> QPolygonF:
        return self._polygon

    def set_polygon(self, poly: QPolygonF):
        self._polygon = poly
        self.prepareGeometryChange()
        self.update()

    def setPolygon(self, polygon: QPolygonF):
        self._polygon = polygon
        self.update()

    def set_visible(self, vis: bool):
        if not vis:
            self._brush = self._brush_normal
        else:
            self._brush = self._brush_darker
        self.update()

    def brush(self) -> QBrush:
        return self._brush

    def setBrush(self, brush: QBrush):
        self._brush = brush
        self._brush_normal = QBrush(brush)
        self._brush_darker = QBrush(brush)
        self._brush_darker.setColor(self._brush_darker.color().darker(125))
        self.update()

    def pen(self) -> QPen:
        return self._pen

    def setPen(self, pen: QPen):
        self._pen = pen
        self.update()

    def hoverEvent(self, ev):
        if ev.isExit():
            self._brush = self._brush_normal
            self.update()
        else:
            self._brush = self._brush_darker
            self.update()
        self.sigHoverEvent.emit(ev, self)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addPolygon(self.polygon())
        path.closeSubpath()
        return path

    def boundingRect(self) -> QRectF:
        return self.polygon().boundingRect()

    def contains(self, point: QPointF) -> bool:
        return self.shape().contains(point)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawPolygon(self.polygon())


class Polygons(HoverableBaseClass, GraphicsObject):

    def __init__(self, polygons: list[QPolygonF], channel_ids: list[str], node_ids: list[str], src_item: 'PlotSourceItem', *args, **kwargs):
        self.xData = np.array([[y.x() for y in x] for x in polygons]).flatten()
        self.yData = np.array([[y.y() for y in x] for x in polygons]).flatten()
        self.range = (self.xData.min(), self.xData.max())
        pen = kwargs.pop('pen', None)
        super(Polygons, self).__init__(*args, **kwargs)
        self.opts = {
            'pen': mkPen(color='#000000', width=1),
            'brush': mkBrush(color=(200, 200, 200, 128)),
            'tip': '{2}\noffset: {0:.3g} m\n{3}: {1:.3g} {4}'.format
        }
        if pen:
            self.opts['pen'] = pen
        self.hover_colour = '#969696'
        self.src_item = src_item
        self.plot_type = 'polygons'
        self.data_type = 'pipes'
        self.units = ''
        self.suppress_tooltip = False
        self.selected = False

        self.node_ids = np.array([[node_ids[i], node_ids[i+1], node_ids[i+1], node_ids[i]] for i in range(0, len(node_ids)-1, 2)]).flatten()

        self._polygons = []
        for poly, chan_id in zip(polygons, channel_ids):
            item = Polygon(poly, chan_id, parent=self)
            item.setPen(self.opts['pen'])
            item.setBrush(self.opts['brush'])
            item.sigHoverEvent.connect(self.hoverEvent)
            self._polygons.append(item)

    def getData(self):
        return self.xData, self.yData

    def getDataClean(self):
        idx = np.array([[i + 3, i + 2] for i in range(0, self.xData.size, 4)]).flatten()
        return self.xData[idx], self.yData[idx]

    def boundingRect(self):
        rect = QRectF()
        for poly in self._polygons:
            rect = rect.united(poly.boundingRect())
        return rect

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        pass

    def setPen(self, pen: QPen):
        for poly in self._polygons:
            poly.setPen(pen)

    def is_mouse_over_curve(self, event) -> bool:
        return self.hover_dist < 100 or self.is_cursor_over_curve or [x.contains(event.pos()) for x in self._polygons].count(True) > 0

    def reset_hover(self):
        pass

    def hoverEvent(self, ev: HoverEvent, polygon: Polygon = None):
        if self.suppress_tooltip:
            self.setToolTip('')
            return

        super().hoverEvent(ev, polygon)

        if ev.isExit():
            return

        if self._p:
            self.hover_text = self.src_item.tooltip(self.src_item, self._node_id, (self._p.x(), self._p.y()))
        elif polygon:
            self.is_cursor_over_curve = True
            self.hover_colour = polygon.brush().color().name()
            self.hover_text = self.src_item.tooltip(self.src_item, polygon.channel_id, None)
            self.active_channel_curve = polygon
            self.hover_pos = ev.screenPos().toPoint()
        else:
            self.is_cursor_over_curve = False
            self.setToolTip('')
            self.hover_local_pos = None

        self.sigHoverEvent.emit(self.getViewBox().mapFromView(ev.pos()), self.feedback_context)
