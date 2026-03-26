from qgis.PyQt.QtCore import pyqtSignal, QPoint, QRect, QSettings
from qgis.PyQt.QtWidgets import QToolTip, QGraphicsSceneHoverEvent

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pyqtgraph import ViewBox
    from .....compatibility_routines import QT_KEY_NO_MODIFIER, QT_KEY_MODIFIER_CONTROL
else:
    from tuflow.pyqtgraph import ViewBox
    from tuflow.compatibility_routines import QT_KEY_NO_MODIFIER, QT_KEY_MODIFIER_CONTROL


class CustomViewBox(ViewBox):

    ctxMenuAboutToHide = pyqtSignal()
    dragEventFinished = pyqtSignal()
    dragEventStarted = pyqtSignal()
    hovered = pyqtSignal(QGraphicsSceneHoverEvent)
    hoveredLeave = pyqtSignal()

    def __init__(self, parent=None, border=None, lockAspect=False, enableMouse=True, invertY=False, enableMenu=True, name=None, invertX=False, defaultPadding=0.02, axisName='primary'):
        super().__init__(parent, border, lockAspect, enableMouse, invertY, enableMenu, name, invertX, defaultPadding)
        self.axis_name = axisName
        self.setAcceptHoverEvents(True)

    def raiseContextMenu(self, ev):
        self._last_click_pos = ev.pos()
        menu = self.getMenu(ev)
        menu.aboutToHide.connect(self.ctxMenuAboutToHide.emit)
        if menu is not None:
            action = [x for x in menu.actions() if x.text() == 'View All'][0]
            action.triggered.disconnect()
            action.triggered.connect(self.autoRangeAll)
            self.scene().addParentContextMenus(self, menu, ev)
            self.get_tv_plot_widget().create_context_menu(self, menu)
            menu.popup(ev.screenPos().toPoint())

    def hoverMoveEvent(self, event):
        self.hovered.emit(event)
        event.accept()

    def hoverLeaveEvent(self, event):
        self.hoveredLeave.emit()
        super().hoverLeaveEvent(event)

    def get_tv_plot_widget(self):
        return self.getViewWidget().parent()

    def wheelEvent(self, ev, axis=None, axis_name=None):
        self.get_tv_plot_widget().reset_all_mouse_shapes()
        if self.axis_name == axis_name:
            pass
        elif ev.modifiers() == QT_KEY_MODIFIER_CONTROL and self.axis_name == 'primary':
            if self.get_tv_plot_widget().secondary_vb is not None and self.get_tv_plot_widget().secondary_vb.isVisible():
                self.get_tv_plot_widget().secondary_vb.wheelEvent(ev, axis)
                return
        elif ev.modifiers() == QT_KEY_NO_MODIFIER and self.axis_name == 'secondary':
            self.getViewWidget().getViewBox().wheelEvent(ev, axis)
            return
        super().wheelEvent(ev)

    def mouseDragEvent(self, ev, axis=None, axis_name=None):
        if self.axis_name == axis_name:
            pass
        elif ev.modifiers() == QT_KEY_MODIFIER_CONTROL and self.axis_name == 'primary':
            if self.get_tv_plot_widget().secondary_vb is not None and self.get_tv_plot_widget().secondary_vb.isVisible():
                self.get_tv_plot_widget().secondary_vb.mouseDragEvent(ev, axis)
                return
        elif ev.modifiers() == QT_KEY_NO_MODIFIER and self.axis_name == 'secondary':
            self.getViewWidget().getViewBox().mouseDragEvent(ev, axis)
            return
        super().mouseDragEvent(ev, axis)
        if ev.isStart():
            self.dragEventStarted.emit()
        if ev.isFinish():
            self.get_tv_plot_widget().reset_all_mouse_shapes()
            self.dragEventFinished.emit()

    def autoRangeAll(self, padding=None, items=None, item=None):
        super().autoRange(padding, items, item)
        for it in self.scene().items():
            if isinstance(it, CustomViewBox) and it != self:
                it.autoRange(padding, items, item)
