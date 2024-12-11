import json
from collections import OrderedDict

from qgis.core import QgsApplication

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QTableWidget, QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QAbstractItemView, QMenu,
                             QAction)

from tuflow.compatibility_routines import Path
from tuflow.bridge_editor.BridgeEditorTable import HeaderChannelTable
from tuflow.gui.widgets.custom_delegates import ComboBoxDelegate, DoubleSpinBoxDelegate, MultiComboBoxDelegate


with (Path(__file__).parents[2] / 'alg' / 'data' / 'output_formats.json').open() as f:
    OUT_FMT = json.load(f)


class OutputFormatWidget(QWidget):

    valueChanged = pyqtSignal()

    def __init__(self, parent=None, initial_values: dict = None):
        super().__init__(parent)
        self.vlayout = QVBoxLayout()
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.toolbar = OutputFormatToolbar(self)
        self.toolbar.addClicked.connect(self.add_new_output_format)
        self.toolbar.remClicked.connect(self.rem_sel_output_format)
        self.vlayout.addWidget(self.toolbar)
        self.table = OutputFormatTable(self, initial_values)
        self.vlayout.addWidget(self.table)
        self.vlayout.addStretch()
        self.setLayout(self.vlayout)
        self.table.itemChanged.connect(self.valueChanged.emit)

    @property
    def value(self) -> str:
        d = OrderedDict()
        for i in range(self.table.rowCount()):
            fmt = self.table.model().index(i, 0).data(Qt.EditRole)
            result_types = [x.strip() for x in self.table.model().index(i, 1).data(Qt.EditRole).split(',')]
            interval = self.table.model().index(i, 2).data(Qt.EditRole)
            d[fmt] = {'result_types': result_types, 'interval': interval}
        return json.dumps(d)

    @value.setter
    def value(self, value: str):
        if isinstance(value, str):
            d = json.loads(value, object_pairs_hook=OrderedDict)
        else:
            d = value
        self.table.setRowCount(len(d))
        for i, (fmt, settings) in enumerate(d.items()):
            self.table.model().setData(self.table.model().index(i, 0), fmt, Qt.EditRole)
            self.table.model().setData(self.table.model().index(i, 1), ', '.join(settings['result_types']), Qt.EditRole)
            self.table.model().setData(self.table.model().index(i, 2), settings['interval'], Qt.EditRole)

    def add_new_output_format(self, action: QAction):
        self.table.add_row(action.text())

    def rem_sel_output_format(self):
        if not self.table.rowCount():
            return
        rows = sorted(list(set([x.row() for x in self.table.selectedIndexes()])))
        if not rows:
            rows = [self.table.rowCount() - 1]
        for i in reversed(rows):
            self.table.removeRow(i)


class OutputFormatTable(QTableWidget):

    def __init__(self, parent=None, initial_values: dict = None):
        super().__init__(parent)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setColumnCount(3)
        self.setItemDelegateForColumn(0, ComboBoxDelegate(self, items=self.result_formats(), col_idx=0))
        self.setItemDelegateForColumn(1, MultiComboBoxDelegate(self, items=self.result_types(), col_idx=1))
        self.setItemDelegateForColumn(2, DoubleSpinBoxDelegate(self, 0., 9999999., 1., 1.))
        self.horizontalHeader().setStretchLastSection(True)
        self.setHorizontalHeaderLabels(['Format', 'Result Types', 'Interval (s)'])
        self.setColumnWidth(0, 250)
        self.setColumnWidth(1, 250)
        if initial_values:
            self.setRowCount(len(initial_values))
            for i, (fmt, settings) in enumerate(initial_values.items()):
                self.model().setData(self.model().index(i, 0), fmt, Qt.EditRole)
                self.model().setData(self.model().index(i, 1), settings['result_types'], Qt.EditRole)
                self.model().setData(self.model().index(i, 2), settings['interval'], Qt.EditRole)
        total_height = sum(self.rowHeight(i) for i in range(self.rowCount()))
        total_height = max(total_height, 150)
        self.setFixedHeight(total_height + self.horizontalHeader().height() + 2)

    def result_formats(self):
        return OUT_FMT.get('formats')

    def result_types(self):
        return OUT_FMT.get('types')

    def add_row(self, fmt: str):
        self.setRowCount(self.rowCount() + 1)
        i = self.rowCount() - 1
        if i > 0:
            values = [fmt, self.model().index(i - 1, 1).data(Qt.EditRole), self.model().index(i - 1, 2).data(Qt.EditRole)]
        else:
            values = [fmt, 'Water Level, Depth, Velocity', 3600.]
        for j, value in enumerate(values):
            self.model().setData(self.model().index(i, j), value, Qt.EditRole)


class OutputFormatToolbar(QWidget):

    addClicked = pyqtSignal(QAction)
    remClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hlayout = QHBoxLayout()
        self.hlayout.setContentsMargins(0, 0, 0, 0)
        self.btn_add = QToolButton()
        self.btn_add.setIcon(QgsApplication.getThemeIcon('/symbologyAdd.svg'))
        self.btn_add.setToolTip('Add new output format')
        self.menu_add = QMenu()
        for fmt in OUT_FMT.get('formats', []):
            self.menu_add.addAction(fmt)
        self.btn_add.setMenu(self.menu_add)
        self.btn_add.setPopupMode(QToolButton.InstantPopup)
        self.menu_add.triggered.connect(self.addClicked.emit)
        self.hlayout.addWidget(self.btn_add)
        self.btn_rem = QToolButton()
        self.btn_rem.setIcon(QgsApplication.getThemeIcon('/symbologyRemove.svg'))
        self.btn_rem.setToolTip('Remove selected output format')
        self.btn_rem.clicked.connect(self.remClicked.emit)
        self.hlayout.addWidget(self.btn_rem)
        self.hlayout.addStretch()
        self.setLayout(self.hlayout)
