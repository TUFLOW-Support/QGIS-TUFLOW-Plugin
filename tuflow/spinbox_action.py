from PyQt5.QtWidgets import (QWidget, QWidgetAction, QSpinBox,
                             QDoubleSpinBox, QHBoxLayout, QLabel,
                             QCheckBox, QMenu, QAction)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint



class SingleSpinBoxAction(QWidgetAction):
    """
    Custom class for widget that can be added to a QMenu.

    Integer QSpinbox with label and optional check box. Passing in
    more than one label (in args) will insert additional spinboxes.
    """

    removeActionRequested = pyqtSignal(QPoint)

    def __init__(self, parent, bCheckBox, *args, **kwargs):
        QWidgetAction.__init__(self, parent)
        self.bCheckBox = bCheckBox
        self.nsb = len(args)  # number of spinboxes

        self.widget = QWidget()
        self.layout = QHBoxLayout()
        if bCheckBox:
            cb = QCheckBox()
            cb.setChecked(True)
            cb.setContextMenuPolicy(Qt.CustomContextMenu)
            cb.customContextMenuRequested.connect(self.contextMenu)
            self.layout.addWidget(cb)
        for a in args:
            label = QLabel(a)
            label.setContextMenuPolicy(Qt.CustomContextMenu)
            label.customContextMenuRequested.connect(self.contextMenu)

            spinbox = QSpinBox()
            if 'range' in kwargs:
                spinbox.setRange(kwargs['range'][0], kwargs['range'][1])
            else:
                spinbox.setRange(-99999, 99999)

            self.layout.addWidget(label)
            self.layout.addWidget(spinbox)
            self.widget.setLayout(self.layout)

        self.setDefaultWidget(self.widget)

    def value(self, i: int) -> int:
        """
        Return spinbox number i value
        """

        # check index is within range
        if self.nsb + 1 < i < 0: return -1

        # get index of spinbox in widget
        if self.bCheckBox:
            j = 1
        else:
            j = 0
        j += (i * 2) + 1

        # get spinbox and return value
        sb = self.layout.itemAt(j).widget()
        return sb.value()

    def values(self) -> tuple:
        """
        Return spinbox number i value
        """

        # get index of spinbox in widget
        if self.bCheckBox:
            j = 1
        else:
            j = 0

        values = []
        for i in range(j + 1, self.nsb * 2 + j, 2):
            sb = self.layout.itemAt(i).widget()
            values.append(sb.value())

        return values

    def insertCheckbox(self):
        """
        Insert a checkbox in widget
        """

        cb = QCheckBox()
        cb.setChecked(True)
        cb.setContextMenuPolicy(Qt.CustomContextMenu)
        cb.customContextMenuRequested.connect(self.contextMenu)
        self.layout.insertWidget(0, cb)
        self.bCheckBox = True

    def removeCheckbox(self):
        """
        Remove checkbox from widget
        """

        widget = self.layout.itemAt(0).widget()
        self.layout.removeWidget(widget)
        widget.deleteLater()
        widget.setParent(None)
        self.bCheckBox = False

    def contextMenu(self, pos):
        self.menu = QMenu()
        action = QAction("Remove Method", self.menu)
        action.triggered.connect(lambda e: self.remove(self.parent().mapTo(self.parent(), pos)))
        self.menu.addAction(action)
        self.menu.popup(self.parent().mapToGlobal(pos))

    def remove(self, p):
        self.removeActionRequested.emit(p)

    def isChecked(self):
        if self.bCheckBox:
            return self.layout.itemAt(0).widget().isChecked()
        else:
            return True
