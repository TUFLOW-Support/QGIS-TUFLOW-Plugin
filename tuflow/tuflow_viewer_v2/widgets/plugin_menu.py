from qgis.PyQt.QtWidgets import QMenu


class TuflowViewerPluginMenu(QMenu):
    """Menu class for the QGIS TUFLOW plugin menu."""

    def mouseReleaseEvent(self, e):
        action = self.activeAction()
        if action is not None and action.isCheckable():
            if action.isEnabled():
                action.setEnabled(False)
                QMenu.mouseReleaseEvent(self, e)
                action.setEnabled(True)
                action.trigger()
            else:
                QMenu.mouseReleaseEvent(self, e)
        elif action is None and self.parent() and self.parent().activeAction() == self.menuAction():
            self.menuAction().trigger()
        else:
            QMenu.mouseReleaseEvent(self, e)
