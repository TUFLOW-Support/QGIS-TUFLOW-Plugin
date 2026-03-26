from qgis.PyQt.QtWidgets import QToolButton, QMenu
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QTimer, pyqtSignal, QSettings

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...compatibility_routines import is_qt6
else:
    from tuflow.compatibility_routines import is_qt6

if is_qt6:
    from qgis.PyQt.QtGui import QAction
else:
    from qgis.PyQt.QtWidgets import QAction

import logging
logger = logging.getLogger('tuflow_viewer')


class PersistentMenu(QMenu):
    """Menu that stays open after an action is selected so multiple can be selected at once."""

    def mouseReleaseEvent(self, e):
        action = self.activeAction()
        if action is not None:
            if action.isEnabled():
                action.setEnabled(False)
                QMenu.mouseReleaseEvent(self, e)
                action.setEnabled(True)
                action.trigger()
            else:
                super().mouseReleaseEvent(e)
        else:
            super().mouseReleaseEvent(e)

class MenuButton(QToolButton):

    triggered = pyqtSignal(QAction)

    def __init__(self, icon: QIcon, text: str, parent=None, persistent_menu: bool = False):
        super().__init__(parent)
        self.setIcon(icon)
        self.setText(text)
        self.setToolTip(text)
        self.setCheckable(True)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.block_menu = False
        if persistent_menu:
            self.menu = PersistentMenu(self)
        else:
            self.menu = QMenu(self)
        self.menu.triggered.connect(self.triggered.emit)
        self.clicked.connect(self.show_menu)
        self.menu.aboutToHide.connect(self.about_to_hide_menu)

    def show_menu(self):
        if self.block_menu:
            self.setChecked(False)
            return
        self.menu.popup(self.mapToGlobal(self.rect().bottomLeft()))

    def about_to_hide_menu(self):
        self.setChecked(False)
        # block menu from opening again for a very short time -
        # stops menu from opening again if the user clicked the button again to close the menu
        self.block_menu = True
        self.timer.timeout.connect(lambda: setattr(self, 'block_menu', False))
        self.timer.start(100)

    def addActions(self, actions: list[QAction]):
        self.menu.addActions(actions)

    def addMenu(self, menu: QMenu):
        self.menu.addMenu(menu)

    def addSeparator(self):
        self.menu.addSeparator()

    def actions(self) -> list[QAction]:
        return self.menu.actions()

    def clear(self):
        self.menu.clear()
