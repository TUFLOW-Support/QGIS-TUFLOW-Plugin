import numpy as np

from qgis.PyQt.QtCore import QPointF, pyqtSignal, Qt, QSettings

from .tuflow_viewer_curve import TuflowViewerCurve

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pyqtgraph import ScatterPlotItem, mkPen, mkBrush
else:
    from tuflow.pyqtgraph import ScatterPlotItem, mkPen, mkBrush


class HoverableBaseClass(TuflowViewerCurve):
    sigHoverEvent = pyqtSignal(QPointF, str)

    def __init__(self, *args, **kwargs):
        marker_size = kwargs.get('size', 5)
        self.hoverItem = ScatterPlotItem(pen=mkPen(color=(0, 255, 255), width=2), brush=mkBrush(color=(0, 255, 255)),
                                         symbol='o', size=marker_size, hoverable=False)
        super().__init__(*args, **kwargs)
        self.hoverItem.setParentItem(self)
        self.hoverItem.setData(self.xData, self.yData)
        self.hoverItem.setVisible(False)
        self.hoverItem.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.hover_dist = 9e29
        self.hover_text = ''
        self.hover_colour = self.opts['pen'].color().name() if 'pen' in self.opts else '#000000'
        self.hover_pos = None  # global position
        self.hover_local_pos = None  # local position in the viewBox (not the data coordinates)
        self.hoverItem_mask = np.zeros(len(self.xData), dtype=bool)
        self.is_cursor_over_curve = False
        self.hoverable = True
        self.node_ids = np.array([], dtype=object)
        self.active_channel_curve = None
        self._node_id = None
        self._p = None
        self.feedback_context = ''

    def reset_hover(self):
        self.hoverItem_mask[:] = False
        self.hover_dist = 9e29
        self.hover_pos = None
        self.hover_local_pos = None
        self.hover_text = ''
        self.is_cursor_over_curve = False
        if self.active_channel_curve:
            self.active_channel_curve.set_visible(False)
        self.active_channel_curve = None

    def set_hover_visible(self, vis: bool):
        if not self.hover_local_pos or not vis:
            self.hoverItem.setVisible(False)
        if vis and self.hover_pos:
            self.showTooltip()
            if self.hover_local_pos:
                self.hoverItem.setPointsVisible(self.hoverItem_mask)
                self.hoverItem.setVisible(True)
        elif not vis and self.active_channel_curve:
            self.active_channel_curve.set_visible(False)
            self.hover_text = ''
            self.active_channel_curve = None
            self.is_cursor_over_curve = None

    def hoverEvent(self, ev, channel_curve = None):
        self.hover_dist = 9e29
        self.hoverItem_mask[:] = False
        self.hover_local_pos = None
        self._p = None

        if ev.isExit():
            if self.active_channel_curve:
                self.active_channel_curve.set_visible(False)
                self.active_channel_curve = None
            return

        if self.hoverable:
            self.hoverItem.data['visible'] = True
            a = self.hoverItem._maskAt(ev.pos())
            node_ids = self.node_ids[a] if self.node_ids.size else None
            pnts = [(i, QPointF(x._data['x'], x._data['y'])) for i, x in enumerate(self.hoverItem.points()[a])]

            min_idx = None
            self._node_id = None
            b = np.where(a)[0]
            for idx, p_ in pnts:
                dist = ((p_.x() - ev.pos().x()) ** 2 + (p_.y() - ev.pos().y()) ** 2) ** 0.5
                if dist < self.hover_dist:
                    self.hover_dist = dist
                    self._p = p_
                    min_idx = b[idx]
                    self._node_id = node_ids[idx] if node_ids is not None else None
            if min_idx is not None:
                self.hoverItem_mask[min_idx] = True

            if self._p:
                if self.active_channel_curve:
                    self.active_channel_curve.set_visible(False)
                    self.active_channel_curve = None
                self.hover_pos = self.getViewWidget().mapToGlobal(self.mapToDevice(self._p).toPoint())
                self.hover_local_pos = self.getViewBox().mapFromView(self._p)
