from qgis.gui import QgsCheckableComboBox

from qgis.PyQt.QtCore import Qt, QEvent
from qgis.PyQt.QtWidgets import QLineEdit, QMenu, QApplication



from ...compatibility_routines import QT_KEY_V, QT_KEY_MODIFIER_CONTROL, QT_KEY_C, QT_EVENT_KEY_RELEASE


class CheckableComboBox(QgsCheckableComboBox):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_edit = self.findChild(QLineEdit)
        self.line_edit.customContextMenuRequested.disconnect()

        self.context_menu = QMenu(self)
        self.select_all_action = self.context_menu.addAction('Select All')
        self.deselect_all_action = self.context_menu.addAction('Deselect All')
        self.copy_action = self.context_menu.addAction('Copy')
        self.paste_action = self.context_menu.addAction('Paste')

        self.select_all_action.triggered.connect(self.selectAllOptions)
        self.deselect_all_action.triggered.connect(self.deselectAllOptions)
        self.copy_action.triggered.connect(self.copySelected)
        self.paste_action.triggered.connect(self.pasteSelected)

        self.line_edit.customContextMenuRequested.connect(self.showContextMenu)
        self.installEventFilter(self)

    def eventFilter(self, object, event):
        if event.type() == QT_EVENT_KEY_RELEASE:
            if event.key() == QT_KEY_C and event.modifiers() == QT_KEY_MODIFIER_CONTROL:
                self.copySelected()
        # capture ctrl+v paste event
        if event.type() == QT_EVENT_KEY_RELEASE:
            if event.key() == QT_KEY_V and event.modifiers() == QT_KEY_MODIFIER_CONTROL:
                self.pasteSelected()
        return super().eventFilter(object, event)

    def showContextMenu(self, pos):
        self.context_menu.exec(self.line_edit.mapToGlobal(pos))

    def copySelected(self):
        QApplication.clipboard().setText(self.line_edit.text())

    def pasteSelected(self):
        checked_items = [x.strip() for x in QApplication.clipboard().text().split(',')]
        self.deselectAllOptions()
        self.setCheckedItems(checked_items)
