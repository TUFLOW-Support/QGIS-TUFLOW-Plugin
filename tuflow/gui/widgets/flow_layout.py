"""A layout that arranges its child widgets left to right and wraps them onto
 a new row whenever the current row runs out of horizontal space.

Used Qt's official "Flow Layout" C++ example as guide
(https://doc.qt.io/qt-6/qtwidgets-layouts-flowlayout-example.html)
"""

from qgis.PyQt.QtCore import QPoint, QRect, QSize, Qt
from qgis.PyQt.QtWidgets import QLayout

# qt5, qt6 compatibility
try:
    _QT_ORIENTATION_NONE = Qt.Orientation(0)
except Exception:
    _QT_ORIENTATION_NONE = 0

_DEFAULT_SPACING = 6


class FlowLayout(QLayout):
    """A :class:`QLayout` that lays out child widgets in a row and wrapping onto new
    rows as needed to fit in the available width (rather then scrolling)."""

    def __init__(self, parent=None, margin: int = -1, h_spacing: int = -1, v_spacing: int = -1):
        super().__init__(parent)
        self._item_list = []
        self._h_space = h_spacing
        self._v_space = v_spacing
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        while self.count():
            self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def horizontalSpacing(self) -> int:
        if self._h_space >= 0:
            return self._h_space
        return _DEFAULT_SPACING

    def verticalSpacing(self) -> int:
        if self._v_space >= 0:
            return self._v_space
        return _DEFAULT_SPACING

    def count(self) -> int:
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return _QT_ORIENTATION_NONE

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        h_space = self.horizontalSpacing()
        v_space = self.verticalSpacing()

        for item in self._item_list:
            next_x = x + item.sizeHint().width() + h_space
            if next_x - h_space > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + v_space
                next_x = x + item.sizeHint().width() + h_space
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + bottom




