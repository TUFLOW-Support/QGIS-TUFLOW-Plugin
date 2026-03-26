from qgis.PyQt.QtCore import QPointF, pyqtSignal, QSettings
from qgis.PyQt.QtWidgets import QGraphicsSceneHoverEvent
from qgis.PyQt.QtGui import QColor

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pyqtgraph import PlotCurveItem, mkPen
    from .....pyqtgraph.GraphicsScene.mouseEvents import HoverEvent
else:
    from tuflow.pyqtgraph import PlotCurveItem, mkPen
    from tuflow.pyqtgraph.GraphicsScene.mouseEvents import HoverEvent


class ChannelCurve(PlotCurveItem):

    channelHover = pyqtSignal(HoverEvent, PlotCurveItem)

    def __init__(self, channel_id: str, hoverable: bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel_id = channel_id
        self.is_hovered = False
        self.hoverable = hoverable
        self.setAcceptHoverEvents(True)

    def set_visible(self, visible: bool):
        pen = mkPen(color=(0, 255, 255, 255), width=2) if visible else mkPen(color=(0, 255, 255, 0), width=2)
        self.setPen(pen)

    def hoverEvent(self, ev):
        if not self.hoverable:
            return
        self.channelHover.emit(ev, self)
