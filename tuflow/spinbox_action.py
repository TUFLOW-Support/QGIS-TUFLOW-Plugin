from qgis.PyQt.QtWidgets import (QWidget, QWidgetAction, QSpinBox,
                             QDoubleSpinBox, QHBoxLayout, QLabel,
                             QCheckBox, QMenu, QComboBox,
                             QDoubleSpinBox, QWidgetItem)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QPoint, QEvent
from qgis.PyQt.QtGui import QPalette, QMouseEvent




from .compatibility_routines import (is_qt6, QT_PALETTE_HIGHLIGHT, QT_LEFT_BUTTON, QT_CUSTOM_CONTEXT_MENU,
                                     QT_PALETTE_WINDOW, QT_COMBOBOX_ADJUST_TO_CONTENTS)

if is_qt6:
    from qgis.PyQt.QtGui import QAction
else:
    from qgis.PyQt.QtWidgets import QAction


class CustomMenuWidget(QWidget):
    """
    Custom widget that will highlight correctly in a QMenu.

    Primarily used for custom QWidgetAction that will be added to a QMenu.
    CustomMenuWidget will:
        - highlight item in menu correctly
        - on left click, will setChecked the first QCheckBox available in widget and emit a clicked signal
    """

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.bCheckable = False

    def setCheckable(self, b):
        self.bCheckable = b

    def set_highlighted(self, h):
        if h:
            self.setBackgroundRole(QT_PALETTE_HIGHLIGHT)
        else:
            self.setBackgroundRole(QT_PALETTE_WINDOW)
        self.setAutoFillBackground(h)

    def enterEvent(self, a0: QEvent) -> None:
        self.set_highlighted(True)

    def leaveEvent(self, a0: QEvent) -> None:
        self.set_highlighted(False)

    def mouseReleaseEvent(self, a0: QMouseEvent) -> None:
        if self.bCheckable:
            if a0.button() == QT_LEFT_BUTTON:
                layout = self.layout()
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if isinstance(item, QWidgetItem):
                        if isinstance(item.widget(), QCheckBox):
                            item.widget().setChecked(not item.widget().isChecked())
                            self.clicked.emit()
                            return


class SingleSpinBoxAction(QWidgetAction):
    """
    Custom class for widget that can be added to a QMenu.

    Integer QSpinbox with label and optional check box. Passing in
    more than one label (in args) will insert additional spinboxes.
    """

    removeActionRequested = pyqtSignal(QPoint)
    sbValueChanged = pyqtSignal(int)

    def __init__(self, parent, bCheckBox, *args, **kwargs):
        QWidgetAction.__init__(self, parent)
        self.bCheckBox = bCheckBox
        self.nsb = len(args)  # number of spinboxes
        self.labels = args

        # self.widget = QWidget()
        self.widget = CustomMenuWidget()
        self.layout = QHBoxLayout()

        enable_menuHighlighting = True
        if 'enable_menu_highlighting' in kwargs:
            enable_menuHighlighting = kwargs['enable_menu_highlighting']
        if enable_menuHighlighting:
            self.widget.setMouseTracking(True)
            self.widget.setCheckable(True)
            self.widget.clicked.connect(self.emitTriggered)

        if bCheckBox:
            cb = QCheckBox()
            if 'cb_setChecked' in kwargs:
                cb.setChecked(kwargs['cb_setChecked'])
            else:
                cb.setChecked(True)
            cb.setContextMenuPolicy(QT_CUSTOM_CONTEXT_MENU)
            cb.customContextMenuRequested.connect(self.contextMenu)
            self.layout.addWidget(cb)
        for i, a in enumerate(args):
            label = QLabel(a)
            label.setContextMenuPolicy(QT_CUSTOM_CONTEXT_MENU)
            label.customContextMenuRequested.connect(self.contextMenu)

            spinbox = QSpinBox()
            if 'range' in kwargs:
                if type(kwargs['range'][0]) is tuple or type(kwargs['range'][0]) is list:
                    spinbox.setRange(kwargs['range'][i][0], kwargs['range'][i][1])
                else:
                    spinbox.setRange(kwargs['range'][0], kwargs['range'][1])
            else:
                spinbox.setRange(-99999, 99999)
            if 'value' in kwargs:
                if type(kwargs['value']) is tuple or type(kwargs['value']) is list:
                    spinbox.setValue(kwargs['value'][i])
                else:
                    spinbox.setValue(kwargs['value'])
            if 'single_step' in kwargs:
                if type(kwargs['single_step']) is tuple or type(kwargs['single_step']) is list:
                    spinbox.setSingleStep(kwargs['single_step'][i])
                else:
                    spinbox.setSingleStep(kwargs['single_step'])

            spinbox.valueChanged.connect(lambda e: self.sbValueChanged.emit(e))

            self.layout.addWidget(label)
            self.layout.addWidget(spinbox)
            self.layout.setContentsMargins(8, 1, 1, 1)

        self.cbo = QComboBox()
        self.cbo.setSizeAdjustPolicy(QT_COMBOBOX_ADJUST_TO_CONTENTS)
        self.layout.addWidget(self.cbo)
        self.layout.addStretch(1)
        if 'set_cbo_items' in kwargs:
            self.cboSetItems(kwargs['set_cbo_items'])
        if 'set_cbo_current_item' in kwargs:
            if kwargs['set_cbo_current_item']:
                self.cboSetValue(kwargs['set_cbo_current_item'])
        if 'set_cbo_visible' in kwargs:
            self.cboSetVisibility(kwargs['set_cbo_visible'])

        self.widget.setLayout(self.layout)
        self.setDefaultWidget(self.widget)

    def paramToText(self):
        s = []
        for i in range(self.nsb):
            # s.append('{0} - {1}'.format(self.labels[i], self.value(i)))
            s.append('{0}'.format(self.value(i)))

        if is_qt6:
            return '{0}: {1}: '.format(self.cbo.currentText(), self.parent().parent().title()) + ' - '.join(s)
        else:
            return '{0}: {1}: '.format(self.cbo.currentText(), self.parentWidget().title()) + ' - '.join(s)

    def defaultItem(self):
        if self.isChecked():
            pass
        else:
            menu = None
            if is_qt6:
                pw = self.parent()
            else:
                pw = self.parentWidget()
            if pw is not None:
                if isinstance(pw, (QAction, QWidgetAction)) and is_qt6:
                    menu = pw.parent()
                else:
                    menu = pw.parentWidget()

            if menu is not None:
                return menu.defaultItem
            else:
                return None

    def cboSetValue(self, itemText):
        """
        Set combobox text but only if text is an option in combobox
        """

        allItemText = [self.cbo.itemText(x) for x in range(self.cbo.count())]

        if itemText in allItemText:
            self.cbo.setCurrentText(itemText)

    def cboSetItems(self, items, **kwargs):
        """
        Sets items to combobox
        """

        self.cbo.clear()
        self.cbo.addItems(items)
        if 'set_cbo_current_item' in kwargs:
            if kwargs['set_cbo_current_item']:
                self.cboSetValue(kwargs['set_cbo_current_item'])

    def cboItems(self):
        """
        Get all cbo items
        """

        return [self.cbo.itemText(x) for x in range(self.cbo.count())]

    def cboCurrentItem(self):
        """

        """

        return self.cbo.currentText()

    def cboAddItem(self, item):
        """
        Add item to combobox
        """

        self.cbo.addItem(item)

    def cboClear(self):

        self.cbo.clear()

    def cboSetVisibility(self, bVisible):
        """
        Set cbo visible / not visible
        """

        self.cbo.setVisible(bVisible)

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

    def values(self) -> list:
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

    def setValues(self, values):
        """

        """

        if self.bCheckBox:
            j = 1
        else:
            j = 0

        isbs = [i for i in range(j + 1, self.nsb * 2 + j, 2)]
        for i in range(len(values)):
            if self.nsb >= i + 1:
                sb = self.layout.itemAt(isbs[i]).widget()
                sb.setValue(values[i])

    def insertCheckbox(self):
        """
        Insert a checkbox in widget
        """

        cb = QCheckBox()
        cb.setChecked(True)
        cb.setContextMenuPolicy(QT_CUSTOM_CONTEXT_MENU)
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

    def setChecked(self, a0: bool) -> None:
        for i in range(self.layout.count()):
            item = self.layout.itemAt(i)
            if isinstance(item, QWidgetItem):
                if isinstance(item.widget(), QCheckBox):
                    item.widget().setChecked(a0)
                    return

    def emitTriggered(self):
        self.trigger()


class DoubleSpinBoxAction(SingleSpinBoxAction):
    """
    Custom class for widget that can be added to a QMenu.

    Integer QSpinbox with label and optional check box. Passing in
    more than one label (in args) will insert additional spinboxes.
    """

    sbValueChanged = pyqtSignal(float)

    def __init__(self, parent, bCheckBox, *args, **kwargs):
        QWidgetAction.__init__(self, parent)
        self.bCheckBox = bCheckBox
        self.nsb = len(args)  # number of spinboxes
        self.labels = args

        # self.widget = QWidget()
        self.widget = CustomMenuWidget()
        self.layout = QHBoxLayout()

        enable_menuHighlighting = True
        if 'enable_menu_highlighting' in kwargs:
            enable_menuHighlighting = kwargs['enable_menu_highlighting']
        if enable_menuHighlighting:
            self.widget.setMouseTracking(True)
            self.widget.setCheckable(True)
            self.widget.clicked.connect(self.emitTriggered)

        if bCheckBox:
            cb = QCheckBox()
            if 'cb_setChecked' in kwargs:
                cb.setChecked(kwargs['cb_setChecked'])
            else:
                cb.setChecked(True)
            cb.setContextMenuPolicy(QT_CUSTOM_CONTEXT_MENU)
            cb.customContextMenuRequested.connect(self.contextMenu)
            self.layout.addWidget(cb)
        for i, a in enumerate(args):
            label = QLabel(a)
            label.setContextMenuPolicy(QT_CUSTOM_CONTEXT_MENU)
            label.customContextMenuRequested.connect(self.contextMenu)

            spinbox = QDoubleSpinBox()
            if 'range' in kwargs:
                if type(kwargs['range'][0]) is tuple or type(kwargs['range'][0]) is list:
                    spinbox.setRange(kwargs['range'][i][0], kwargs['range'][i][1])
                else:
                    spinbox.setRange(kwargs['range'][0], kwargs['range'][1])
            else:
                spinbox.setRange(-99999, 99999)
            if 'value' in kwargs:
                if type(kwargs['value']) is tuple or type(kwargs['value']) is list:
                    spinbox.setValue(kwargs['value'][i])
                else:
                    spinbox.setValue(kwargs['value'])
            if 'decimals' in kwargs:
                if type(kwargs['decimals']) is tuple or type(kwargs['decimals']) is list:
                    spinbox.setDecimals(kwargs['decimals'][i])
                else:
                    spinbox.setDecimals(kwargs['decimals'])
            else:
                spinbox.setDecimals(2)
            if 'single_step' in kwargs:
                if type(kwargs['single_step']) is tuple or type(kwargs['single_step']) is list:
                    spinbox.setSingleStep(kwargs['single_step'][i])
                else:
                    spinbox.setSingleStep(kwargs['single_step'])

            spinbox.valueChanged.connect(lambda e: self.sbValueChanged.emit(e))

            self.layout.addWidget(label)
            self.layout.addWidget(spinbox)
            margin = self.layout.contentsMargins()
            self.layout.setContentsMargins(8, 1, 1, 1)

        self.cbo = QComboBox()
        self.cbo.setSizeAdjustPolicy(QT_COMBOBOX_ADJUST_TO_CONTENTS)
        self.layout.addWidget(self.cbo)
        self.layout.addStretch(1)
        if 'set_cbo_items' in kwargs:
            self.cboSetItems(kwargs['set_cbo_items'])
        if 'set_cbo_current_item' in kwargs:
            if kwargs['set_cbo_current_item']:
                self.cboSetValue(kwargs['set_cbo_current_item'])
        if 'set_cbo_visible' in kwargs:
            self.cboSetVisibility(kwargs['set_cbo_visible'])

        self.widget.setLayout(self.layout)
        self.setDefaultWidget(self.widget)
