from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QMenu
from qgis.PyQt.QtCore import pyqtSignal, QSettings

from qgis.gui import QgsMapCanvasItem

from .drawn_item_action import DrawnItemAction

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...compatibility_routines import is_qt6
else:
    from tuflow.compatibility_routines import is_qt6

if is_qt6:
    from qgis.PyQt.QtGui import QAction
else:
    from qgis.PyQt.QtWidgets import QAction


class DrawnItemMenu(QMenu):

    cleared = pyqtSignal()
    action_removed = pyqtSignal(DrawnItemAction)
    action_toggled = pyqtSignal(DrawnItemAction, bool)
    editable_item_changed = pyqtSignal(DrawnItemAction)
    action_hover_changed = pyqtSignal([], [QgsMapCanvasItem])

    def __init__(self, parent = None):
        super().__init__(parent)
        self.clear_action = QAction('Clear')
        self.clear_action.triggered.connect(self.clear_items)
        self.addAction(self.clear_action)
        self.editable_item_changed.connect(self.on_edit_item_changed)

    def clear_items(self):
        for action in self.actions():
            if isinstance(action, DrawnItemAction) or action.isSeparator():
                self.removeAction(action)
        self.cleared.emit()

    def drawn_item_actions(self) -> list[DrawnItemAction]:
        actions = []
        for action in self.actions():
            if not isinstance(action, DrawnItemAction):
                continue
            actions.append(action)
        return actions

    def count(self) -> int:
        return max(len(self.actions()) - 2, 0)

    def editable_action(self) -> DrawnItemAction | None:
        for action in self.drawn_item_actions():
            if action.isEditActive():
                return action
        return None

    def add_action(self, text: str, item: QgsMapCanvasItem, checked: bool):
        action = DrawnItemAction(text, item, self)
        action.setCheckable(True)
        action.setChecked(checked)
        action.toggled.connect(self.on_item_toggled)
        action.removeButtonClicked.connect(self.on_item_removed)
        action.cursorEntered.connect(self.on_cursor_entered)
        action.cursorLeft.connect(self.on_cursor_left)
        action.editClicked.connect(self.on_edit_item_changed)
        if not self.count() and not self.actions()[-1].isSeparator():
            self.addSeparator()
        self.addAction(action)
        action.setEditActive(True)
        self.on_edit_item_changed(action)

    def remove_action(self, action: DrawnItemAction):
        if not isinstance(action, DrawnItemAction):
            return
        self.removeAction(action)
        if action.isEditActive():
            action.setEditActive(False)
            self.editable_item_changed.emit(action)
        self.action_removed.emit(action)

    def on_edit_item_changed(self, action: DrawnItemAction):
        if action.isEditActive():
            for action0 in self.drawn_item_actions():
                if action0 != action:
                    action0.setEditActive(False)
        elif action in self.drawn_item_actions():
            action.setEditActive(True)
        elif self.count():
            self.drawn_item_actions()[-1].setEditActive(True)

    def on_item_toggled(self, checked: bool):
        self.action_toggled.emit(self.sender(), checked)

    def on_item_removed(self):
        action = self.sender()
        self.remove_action(action)
        if action.isEditActive():
            action.setEditActive(False)
            self.editable_item_changed.emit(action)
        self.action_removed.emit(action)

    def on_cursor_entered(self, drawn_item: QgsMapCanvasItem):
        self.action_hover_changed[QgsMapCanvasItem].emit(drawn_item)

    def on_cursor_left(self):
        self.action_hover_changed.emit()
