from qgis.PyQt import QtCore, QtWidgets, QtGui

from ..logging import Logging


class ToolButtonDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate that draws a tool-button-like control in a table cell and handles clicks."""

    triggered = QtCore.pyqtSignal(QtCore.QModelIndex)  # signal emitted when the button is clicked

    def __init__(self, icon: QtGui.QIcon, should_show_callback, parent=None):
        super().__init__(parent)
        self._icon = icon
        self._should_show = should_show_callback

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        try:
            if not self._should_show(index):
                return super().paint(painter, option, index)

            # Draw a push-button style control with the icon centered
            btn_opt = QtWidgets.QStyleOptionButton()
            # slightly inset the button
            btn_opt.rect = option.rect.adjusted(4, 2, -4, -2)
            # Qt6 enum namespace: use StateFlag
            try:
                btn_opt.state = QtWidgets.QStyle.StateFlag.State_Enabled
            except Exception:
                # fallback for PyQt5 or older bindings
                btn_opt.state = QtWidgets.QStyle.State_Enabled
            # draw the button frame
            QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.ControlElement.CE_PushButton, btn_opt, painter)

            # draw the icon centered inside the rect
            icon_size = min(btn_opt.rect.height() - 4, btn_opt.rect.width() - 4)
            if icon_size < 1:
                return
            pixmap = self._icon.pixmap(icon_size, icon_size)
            x = btn_opt.rect.x() + (btn_opt.rect.width() - pixmap.width()) // 2
            y = btn_opt.rect.y() + (btn_opt.rect.height() - pixmap.height()) // 2
            painter.drawPixmap(x, y, pixmap)
        except Exception:
            # fallback to default painting
            super().paint(painter, option, index)

    def editorEvent(self, event: QtCore.QEvent, model: QtCore.QAbstractItemModel, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> bool:
        # handle mouse press/release as a click
        try:
            # Use Qt6 enum names for QEvent types and MouseButton (with fallbacks)
            try:
                mouse_press = QtCore.QEvent.Type.MouseButtonPress
                mouse_release = QtCore.QEvent.Type.MouseButtonRelease
            except Exception:
                mouse_press = QtCore.QEvent.MouseButtonPress
                mouse_release = QtCore.QEvent.MouseButtonRelease
            try:
                left_button = QtCore.Qt.MouseButton.LeftButton
            except Exception:
                left_button = QtCore.Qt.LeftButton

            if event.type() in (mouse_press, mouse_release) and event.button() == left_button:
                if self._should_show(index):
                    # visible trigger for testing
                    # log on release for clarity
                    if event.type() == mouse_release:
                        self.triggered.emit(index)
                    # consume the event
                    return True
        except Exception:
            # swallow errors to avoid breaking the view
            pass
        return False