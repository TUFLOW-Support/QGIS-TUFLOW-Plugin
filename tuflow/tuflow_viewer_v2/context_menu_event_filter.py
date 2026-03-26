import json

from qgis.PyQt.QtCore import QObject, QEvent, QSettings

from .tvinstance import get_viewer_instance

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ..compatibility_routines import QT_EVENT_CONTEXT_MENU
else:
    from tuflow.compatibility_routines import QT_EVENT_CONTEXT_MENU


class ContextMenuEventFilter(QObject):
    """Class for filtering QGIS Layers Panel context menu events.

    This is used to override certain action in the context menu such as 'Zoom to Layer'.
    """

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Event filter that catches the context menu event and overrides certain actions."""
        from qgis.utils import iface
        if iface is None:
            return False

        if event.type() == QT_EVENT_CONTEXT_MENU:
            idx = iface.layerTreeView().indexAt(event.pos())
            if not idx.isValid():
                return False

            lyr = iface.activeLayer()
            try:
                d = json.loads(lyr.customProperty('tuflow_viewer'))
                output = get_viewer_instance().output(d['id'])
            except (TypeError, json.JSONDecodeError):
                output = get_viewer_instance().output(lyr.customProperty('tuflow_viewer'))
            if not output or output.DRIVER_NAME != 'TUFLOW CATCH Json' or lyr != output.index.layer:
                return False

            menu = iface.layerTreeView().menuProvider().createContextMenu()
            for a in menu.actions():
                if a.text() == '&Zoom to Layer(s)':
                    a.triggered.disconnect()
                    a.triggered.connect(output.zoom_to_layer)
                elif a.text() == '&Duplicate Layer':
                    a.setEnabled(False)
                    # a.triggered.disconnect()
                    # a.triggered.connect(output.duplicate)
                elif a.text() == 'Copy Layer':
                    a.setEnabled(False)
                elif a.text() == 'C&hange Data Source…':
                    a.setEnabled(False)

            menu.exec(iface.layerTreeView().mapToGlobal(event.pos()))
            return True

        return False
