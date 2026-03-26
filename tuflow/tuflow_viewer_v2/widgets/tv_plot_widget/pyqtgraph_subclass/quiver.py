import typing

import numpy as np
from qgis.PyQt.QtCore import QSettings, pyqtSignal, QPointF, QRectF, QMarginsF
from qgis.PyQt.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QWidget
from qgis.PyQt.QtGui import QBrush, QPainter, QPainterPath, QPen, QPolygonF, QTransform

from .tuflow_viewer_curve import TuflowViewerCurve
from .polycollection import ColourCurve

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pyqtgraph import GraphicsObject, mkPen, mkBrush
    from .....pyqtgraph.GraphicsScene.mouseEvents import HoverEvent
    from .....compatibility_routines import QT_STYLE_NO_BRUSH
else:
    from tuflow.pyqtgraph import GraphicsObject, mkPen, mkBrush
    from tuflow.pyqtgraph.GraphicsScene.mouseEvents import HoverEvent

if typing.TYPE_CHECKING:
    from ..plotsourceitem import PlotSourceItem


class ArrowPainter:
    METHOD = ''

    def __init__(self, minval: float, maxval: float):
        self.min = minval
        self.max = maxval
        self.colmin = 0.
        self.colmax = 1.
        self.colour_method = 'single'
        self.single_colour = '#000000'
        self.color_curve = ColourCurve()
        self.line_width = 0.26
        self.head_width = 0.15
        self.head_length = 0.4

    def pen(self, value: np.ndarray) -> QPen:
        if self.colour_method =='single':
            return mkPen(color=self.single_colour, width=self.line_width)
        else:  # curve
            mag = float(np.linalg.norm(value))
            norm = (np.clip(mag, self.colmin, self.colmax) - self.colmin) / (self.colmax - self.colmin)
            return mkPen(color=self.color_curve.color(norm), width=self.line_width)

    def brush(self, value: np.ndarray) -> QBrush:
        return QT_STYLE_NO_BRUSH

    def arrow_pixel_length(self, value: float, tr: QTransform) -> float:
        raise NotImplemented

    def arrow_head(self,
                   p1_px: np.ndarray,
                   length_px: float,
                   dir_: np.ndarray,
                   perp: np.ndarray,
                   inv: QTransform,
                   ) -> QPolygonF:
        # size in pixels
        head_len_px = np.clip(length_px * self.head_length, 2, None)
        head_width_px = np.clip(length_px * self.head_width, 2, None)

        # coordinates in pixels
        p_base_px = p1_px - dir_ * head_len_px
        p_left_px = p_base_px + perp * (head_width_px / 2)
        p_right_px = p_base_px - perp * (head_width_px / 2)

        # coordinates in data coords
        p1 = inv.map(QPointF(*p1_px))
        p_base = inv.map(QPointF(*p_base_px))
        p_left = inv.map(QPointF(*p_left_px))
        p_right = inv.map(QPointF(*p_right_px))

        return QPolygonF([p_base, p_left, p1, p_right, p_base])

    def shape(self, p0: np.ndarray, value: np.ndarray, tr: QTransform, inv: QTransform, dpi: int) -> QPainterPath:
        path = QPainterPath()

        length = float(np.linalg.norm(value))
        if length < 0.0001:
            return path

        dir_ = value / length
        perp = np.array([-dir_[1], dir_[0]])
        length_px = self.arrow_pixel_length(length, tr) * dpi / 25.4

        # p0 = start of arrow (base of shaft)
        p0_px = tr.map(QPointF(*p0))
        p0_px = np.array([p0_px.x(), p0_px.y()])

        # p1 = end of arrow (tip)
        p1_px = p0_px + dir_ * length_px

        # arrow head
        path.addPolygon(self.arrow_head(p1_px, length_px, dir_, perp, inv))

        # arrow shaft
        path.moveTo(inv.map(QPointF(*p1_px)))
        path.lineTo(QPointF(*p0))

        path.closeSubpath()
        return path


class ArrowPainterScaledByMagnitude(ArrowPainter):
    METHOD = 'scaled_by_magnitude'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scale_factor = 10.

    def arrow_pixel_length(self, length: float, tr: QTransform) -> float:
        return length * self.scale_factor


class ArrowPainterDefinedByMinMax(ArrowPainter):
    METHOD = 'defined_by_min_max'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_length = 0.8
        self.max_length = 10.

    def arrow_pixel_length(self, length: float, tr: QTransform) -> float:
        if self.max == self.min:
            return (self.min_length + self.max_length) / 2
        length = (np.clip(length, self.min, self.max) - self.min) / (self.max - self.min)
        return length * (self.max_length - self.min_length) + self.min_length


class ArrowPainterFixed(ArrowPainter):
    METHOD = 'fixed_size'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixed_length = 20.

    def arrow_pixel_length(self, length: float, tr: QTransform) -> float:
        return self.fixed_length


class Arrow(QGraphicsObject):
    sigHoverEvent = pyqtSignal(HoverEvent, QGraphicsObject)

    def __init__(self, pos: np.ndarray, value: np.ndarray, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pos = pos
        self.value = value
        self.ratio = 1.
        self.arrow_head_width = 0.15
        self.arrow_head_length = 0.4
        self.arrow_shaft_width = 0.01
        self.line_width = 0.26
        self._shape = None
        self._bounding_rect = QRectF(self.pos[0], self.pos[1], self.value[0] + 1000, self.value[1] + 100)
        self._dpi = 96
        self.painter = ArrowPainterScaledByMagnitude(0, 0)

    def setData(self, pos: np.ndarray, value: np.ndarray):
        self.pos = pos
        self.value = value
        self._shape = None

    def update(self, *args, **kwargs):
        self._shape = None
        super().update(*args, **kwargs)

    def set_visible(self, vis: bool):
        if not vis:
            self._brush = self._brush_normal
        else:
            self._brush = self._brush_darker
        self.update()

    def hoverEvent(self, ev):
        if ev.isExit():
            self._brush = self._brush_normal
            self.update()
        else:
            self._brush = self._brush_darker
            self.update()
        self.sigHoverEvent.emit(ev, self)

    def shape(self, dpi: int = -1) -> QPainterPath:
        if self._shape:
            return self._shape

        if not self.parentItem() or not self.parentItem().getViewBox():
            return QPainterPath()

        if dpi >= 0:
            self._dpi = dpi

        vb = self.parentItem().getViewBox()
        tr = vb.childGroup.transform()
        inv = tr.inverted()[0]

        self._shape = self.painter.shape(self.pos, self.value, tr, inv, self._dpi)
        self._bounding_rect = self._shape.boundingRect().marginsAdded(QMarginsF(10, 10, 10, 10))
        self.prepareGeometryChange()

        return self._shape

    def boundingRect(self) -> QRectF:
        return self._bounding_rect

    def contains(self, point: QPointF) -> bool:
        return self.shape().contains(point)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(self.painter.pen(self.value))
        painter.setBrush(self.painter.brush(self.value))
        painter.drawPath(self.shape(painter.device().logicalDpiX()))


class Quiver(TuflowViewerCurve, GraphicsObject):

    def __init__(self, pos: np.ndarray, values: np.ndarray, src_item: 'PlotSourceItem', *args, **kwargs):
        self.xData = pos[:,0]
        self.yData = pos[:,1]
        pen = kwargs.pop('pen', None)
        brush = kwargs.pop('brush', None)
        super(Quiver, self).__init__(*args, **kwargs)
        self.opts = {
            'pen': mkPen(color='#000000', width=1),
            'brush': mkBrush(color=(255, 255, 255)),
        }
        if pen:
            self.opts['pen'] = pen
        if brush:
            self.opts['brush'] = brush
        self.plot_type = 'quiver'
        self.hover_colour = '#000000'
        self.src_item = src_item
        self.suppress_tooltip = False
        self.arrows = []
        self._bounding_rect = QRectF()
        self.hoverable = False
        self.values = np.array([])

        self._painter = None
        self.setData(pos, values, src_item)

    def export_data(self) -> np.ndarray:
        return np.column_stack((self.xData, self.yData, self.values))

    def setData(self, pos: np.ndarray, values: np.ndarray, src_item: 'PlotSourceItem'):
        self.xData = pos[:,0]
        self.yData = pos[:,1]
        self.values = values
        xmin = np.nanmin(self.xData)
        xmax = np.nanmax(self.yData)
        ymin = np.nanmin(self.yData)
        ymax = np.nanmax(self.yData)
        self._bounding_rect = QRectF(QPointF(xmin, ymax), QPointF(xmax, ymin))
        ratio = (ymax - ymin) / (xmax - xmin) / 50 if (xmax - xmin) != 0 else 1.0
        arrows = self.arrows.copy()
        i = -1
        for i in range(len(arrows) - 1, -1, -1):
            arrow = arrows.pop(i)
            if i >= pos.shape[0]:
                self.getViewBox().removeItem(arrow)
                self.arrows.pop(i)
                continue
            arrow.setData(pos[i], values[i])

        if i < pos.shape[0] - 1:
            for j in range(i + 1, pos.shape[0]):
                arrow = Arrow(pos[j], values[j])
                if self._painter is not None:
                    arrow.painter = self._painter
                self.arrows.append(arrow)
                arrow.setParentItem(self)

        self.prepareGeometryChange()
        self.src_item = src_item
        self.update()

    @property
    def painter(self) -> ArrowPainter:
        return self._painter

    @painter.setter
    def painter(self, painter: ArrowPainter):
        self._painter = painter
        for arrow in self.arrows:
            arrow.painter = painter
        self.update()

    def boundingRect(self):
        return self._bounding_rect

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        for arrow in self.arrows:
            arrow.paint(painter, option, widget)

    def update(self, *args, **kwargs):
        for arrow in self.arrows:
            arrow.update(*args, **kwargs)
        super().update(*args, **kwargs)

    def reset_hover(self):
        pass

    def set_hover_visible(self, b: bool):
        pass
