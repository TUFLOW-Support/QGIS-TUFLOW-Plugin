from qgis.PyQt.QtCore import QSettings

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pyqtgraph import AxisItem
else:
    from tuflow.pyqtgraph import AxisItem


class SecondaryAxisItem(AxisItem):

    def __init__(self, orientation, *args, **kwargs):
        self.axis_name = kwargs.pop('axis_name', 'primary')
        super().__init__(orientation, *args, **kwargs)

    def wheelEvent(self, event):
        lv = self.linkedView()
        if lv is None:
            return
        # Did the event occur inside the linked ViewBox (and not over the axis iteself)?
        if lv.sceneBoundingRect().contains(event.scenePos()):
            event.ignore()
            return
        else:
            # pass event to linked viewbox with appropriate single axis zoom parameter
            if self.orientation in ['left', 'right']:
                lv.wheelEvent(event, axis=1, axis_name=self.axis_name)
            else:
                lv.wheelEvent(event, axis=0)
        event.accept()

    def mouseDragEvent(self, event):
        lv = self.linkedView()
        if lv is None:
            return
        # Did the mouse down event occur inside the linked ViewBox (and not the axis)?
        if lv.sceneBoundingRect().contains(event.buttonDownScenePos()):
            event.ignore()
            return
        # otherwise pass event to linked viewbox with appropriate single axis parameter
        if self.orientation in ['left', 'right']:
            return lv.mouseDragEvent(event, axis=1, axis_name=self.axis_name)
        else:
            return lv.mouseDragEvent(event, axis=0, axis_name=self.axis_name)
