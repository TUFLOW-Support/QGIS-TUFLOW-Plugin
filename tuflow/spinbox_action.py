from PyQt5.QtWidgets import (QWidget, QWidgetAction, QSpinBox,
                             QDoubleSpinBox, QHBoxLayout, QLabel,
                             QCheckBox, QMenu, QAction, QComboBox,
                             QDoubleSpinBox)
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
        self.labels = args

        self.widget = QWidget()
        self.layout = QHBoxLayout()
        if bCheckBox:
            cb = QCheckBox()
            cb.setChecked(True)
            cb.setContextMenuPolicy(Qt.CustomContextMenu)
            cb.customContextMenuRequested.connect(self.contextMenu)
            self.layout.addWidget(cb)
        for i, a in enumerate(args):
            label = QLabel(a)
            label.setContextMenuPolicy(Qt.CustomContextMenu)
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

            self.layout.addWidget(label)
            self.layout.addWidget(spinbox)

        self.cbo = QComboBox()
        self.cbo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.layout.addWidget(self.cbo)
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

        return '{0}: {1}: '.format(self.cbo.currentText(), self.parentWidget().title()) + ' - '.join(s)

    def defaultItem(self):
        if self.isChecked():
            pass
        else:
            menu = None
            pw = self.parentWidget()
            if pw is not None:
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


class DoubleSpinBoxAction(SingleSpinBoxAction):
    """
    Custom class for widget that can be added to a QMenu.

    Integer QSpinbox with label and optional check box. Passing in
    more than one label (in args) will insert additional spinboxes.
    """

    def __init__(self, parent, bCheckBox, *args, **kwargs):
        QWidgetAction.__init__(self, parent)
        self.bCheckBox = bCheckBox
        self.nsb = len(args)  # number of spinboxes
        self.labels = args

        self.widget = QWidget()
        self.layout = QHBoxLayout()
        if bCheckBox:
            cb = QCheckBox()
            cb.setChecked(True)
            cb.setContextMenuPolicy(Qt.CustomContextMenu)
            cb.customContextMenuRequested.connect(self.contextMenu)
            self.layout.addWidget(cb)
        for i, a in enumerate(args):
            label = QLabel(a)
            label.setContextMenuPolicy(Qt.CustomContextMenu)
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

            self.layout.addWidget(label)
            self.layout.addWidget(spinbox)

        self.cbo = QComboBox()
        self.cbo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.layout.addWidget(self.cbo)
        if 'set_cbo_items' in kwargs:
            self.cboSetItems(kwargs['set_cbo_items'])
        if 'set_cbo_current_item' in kwargs:
            if kwargs['set_cbo_current_item']:
                self.cboSetValue(kwargs['set_cbo_current_item'])
        if 'set_cbo_visible' in kwargs:
            self.cboSetVisibility(kwargs['set_cbo_visible'])

        self.widget.setLayout(self.layout)
        self.setDefaultWidget(self.widget)
