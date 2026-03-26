import typing

import numpy as np

from qgis.PyQt.QtCore import Qt, QPointF, QSettings

from .hoverable_base_class import HoverableBaseClass

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pyqtgraph import ScatterPlotItem
else:
    from tuflow.pyqtgraph import ScatterPlotItem

if typing.TYPE_CHECKING:
    from ...tv_plot_widget.plotsourceitem import PlotSourceItem


class NodeCurve:

    def __init__(self, node_id: str):
        self.channel_id = node_id

    def set_visible(self, vis: bool):
        pass


class HoverableScatterPlot(HoverableBaseClass, ScatterPlotItem):

    def __init__(self, src_item: 'PlotSourceItem', *args, **kwargs):
        self.xData = kwargs.get('x', np.array([]))
        self.yData = kwargs.get('y', np.array([]))
        super(HoverableScatterPlot, self).__init__(*args, **kwargs)
        self.src_item = src_item
        self.data_type = 'pits'
        self.data_type_pretty = 'pits'
        self.units = 'm'
        self.is_datetime = False

    def setData(self, *args, **kwargs):
        self.is_datetime = kwargs.pop('is_datetime', False)
        super().setData(*args, **kwargs)
        xdata = ydata = None
        if args:
            self.xData = np.array(args[0])
        if len(args) > 1:
            self.yData = np.array(args[1])
        if xdata is None:
            self.xData = np.array(kwargs['x']) if 'x' in kwargs else self.xData
        if ydata is None:
            self.yData = np.array(kwargs['y']) if 'y' in kwargs else self.yData
        self.hoverItem.setData(*args, **kwargs)
        self.range = (self.xData.min(), self.xData.max())

    def is_mouse_over_curve(self, ev) -> bool:
        a = self._maskAt(ev.pos())
        for pnt in self.points()[a]:
            p_ = QPointF(pnt._data['x'], pnt._data['y'])
            dist = ((p_.x() - ev.pos().x()) ** 2 + (p_.y() - ev.pos().y()) ** 2) ** 0.5
            if dist < self.hover_dist:
                return True
        return False

    def hoverEvent(self, ev, *args, **kwargs):
        if self.suppress_tooltip:
            self.setToolTip('')
            return

        super().hoverEvent(ev)
        if ev.isExit():
            return

        if self._p:
            self.active_channel_curve = NodeCurve(self._node_id)
            self.hover_text = self.src_item.tooltip(self.src_item, self._node_id, (self._p.x(), self._p.y()), is_datetime=self.is_datetime)
        else:
            self.setToolTip('')
            self.hover_local_pos = None

        self.sigHoverEvent.emit(self.getViewBox().mapFromView(ev.pos()), self.feedback_context)
