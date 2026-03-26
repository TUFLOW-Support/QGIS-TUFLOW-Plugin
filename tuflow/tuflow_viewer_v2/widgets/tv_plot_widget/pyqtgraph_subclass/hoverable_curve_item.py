import typing

import numpy as np

from qgis.PyQt.QtCore import QPointF, QRectF, QPoint, QRect, pyqtSignal, QTimer, QSettings
from qgis.PyQt.QtWidgets import QToolTip
from qgis.PyQt.QtGui import QColor

from .hoverable_base_class import HoverableBaseClass

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pyqtgraph import PlotCurveItem, mkPen
else:
    from tuflow.pyqtgraph import PlotCurveItem, mkPen

from .channel_curve import ChannelCurve

if typing.TYPE_CHECKING:
    from ..plotsourceitem import PlotSourceItem


class HoverableCurveItem(HoverableBaseClass, PlotCurveItem):

    def __init__(self, src_item: 'PlotSourceItem', is_datetime: bool = False, *args, **kwargs):
        super(HoverableCurveItem, self).__init__(*args, **kwargs)
        self._pen = self.opts.get('pen')
        self.plot_type = 'curve'
        self.is_datetime = is_datetime
        self.src_item = src_item
        self.hoverable = True
        self.suppress_tooltip = False
        self.selected = False
        self.active_channel_curve = None
        self.channel_curves = []
        self.create_channel_curves()

    def create_channel_curves(self):
        i = -2
        for ch in self.channel_ids[::2]:
            i += 2
            x = self.xData[i:i+2]
            y = self.yData[i:i+2]
            curve = ChannelCurve(channel_id=ch, x=x, y=y, hoverable=True, pen=mkPen(color=(0, 255, 255, 0), width=2))
            curve.setParentItem(self)
            curve.channelHover.connect(self.hoverEvent)
            self.channel_curves.append(curve)

    def update_channel_curve_data(self):
        i, j = 0, -2
        for i, ch in enumerate(self.channel_ids[::2]):
            if i >= len(self.channel_curves):
                break
            j += 2
            curve = self.channel_curves[i]
            curve.setData(x=self.xData[j:j+2], y=self.yData[j:j+2])
            curve.channel_id = ch

        if i + 1 == len(self.channel_ids) // 2:  # exactly the right number of curves
            return

        if i + 1 < len(self.channel_ids) // 2:  # too few curves
            for ch in self.channel_ids[(i + 1) * 2::2]:
                j += 2
                curve = ChannelCurve(channel_id=ch, x=self.xData[j:j+2], y=self.yData[j:j+2], hoverable=True, pen=mkPen(color=(0, 255, 255, 0), width=2))
                curve.setParentItem(self)
                curve.channelHover.connect(self.hoverEvent)
                self.channel_curves.append(curve)
        else:  # too many curves
            for curve in self.channel_curves[i + 1:]:
                self.getViewBox().removeItem(curve)
            self.channel_curves = self.channel_curves[:i + 1]

    def setData(self, is_datetime: bool = None, *args, **kwargs):
        super().setData(*args, **kwargs)
        self.range = (self.xData.min(), self.xData.max())
        if hasattr(self, 'hoverItem'):  # is called during super().__init__() before hoverItem is created
            self.hoverItem.setData(*args, **kwargs)
            self.hoverItem_mask = np.zeros(len(self.xData), dtype=bool)
            if is_datetime is not None:
                self.is_datetime = is_datetime

        self._mouse_shape = None  # forces this to be recalculated

    def is_mouse_over_curve(self, event) -> bool:
        return self.mouseShape().contains(event.pos()) or self.hover_dist < 100

    def hoverEvent(self, ev, channel_curve: ChannelCurve = None):
        self.hover_text = ''
        if self.suppress_tooltip:
            self.setToolTip('')
            return

        super().hoverEvent(ev, channel_curve)
        if ev.isExit():
            return

        if self._p:
            self.hover_text = self.src_item.tooltip(self.src_item, self._node_id, (self._p.x(), self._p.y()), is_datetime=self.is_datetime)
        elif channel_curve:
            self.hover_pos = ev.screenPos().toPoint()
            vis = channel_curve.mouseShape().contains(ev.pos())
            if self.active_channel_curve:
                self.active_channel_curve.set_visible(False)
            channel_curve.set_visible(vis)
            self.active_channel_curve = channel_curve if vis else None
            self.hover_text = self.src_item.tooltip(self.src_item, channel_curve.channel_id, None) if vis else ''
        else:
            self.setToolTip('')
            self.hover_local_pos = None

        self.is_cursor_over_curve = self.mouseShape().contains(ev.pos())
        self.sigHoverEvent.emit(self.getViewBox().mapFromView(ev.pos()), self.feedback_context)
