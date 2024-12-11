from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView

from tuflow.bridge_editor.BridgeEditorTable import HeaderChannelTable
from tuflow.gui.widgets.custom_delegates import (ComboBoxDelegate, RichTextDelegate, SpinBoxDelegate,
                                                 DoubleSpinBoxDelegate, CRSDelegate)


class SettingsTable(QTableWidget):
    """Widget class for displaying TUFLOW settings in a table."""

    def __init__(self, parent=None, row_params: dict = None) -> None:
        super().__init__(parent)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.setVerticalHeader(HeaderChannelTable())
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setAlternatingRowColors(True)
        self.row_params = row_params
        self.row_widgets = [SettingsRow(parent, key, settings) for key, settings in row_params.items()]
        self.row_widgets = [x for x in self.row_widgets if not type(x) == SettingsRow]
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(['Setting', 'Value', 'Comment'])
        self.setColumnWidth(0, 150)
        self.setColumnWidth(1, 300)
        self.horizontalHeader().setStretchLastSection(True)
        self.setRowCount(len(self.row_widgets))
        for i, row_widget in enumerate(self.row_widgets):
            self.setItemDelegateForRow(i, row_widget.delegate())
            text = self.rich_text(f'<b>{row_widget.key}</b>')
            item = QTableWidgetItem(text)
            item.setFlags(Qt.ItemIsEnabled)
            self.setItem(i, 0, item)
            self.model().setData(self.model().index(i, 1), row_widget.default_value())
            comment = row_widget.settings.get('comment', '')
            item = QTableWidgetItem(comment)
            item.setFlags(Qt.ItemIsEnabled)
            self.setItem(i, 2, item)

        total_height = sum(self.rowHeight(i) for i in range(self.rowCount()))
        self.setFixedHeight(total_height + self.horizontalHeader().height() + 2)

    def rich_text(self, text: str) -> str:
        html = ('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">'
                '<html><head><meta name="qrichtext" content="1" /><style type="text/css">'
                'p, li { white-space: pre-wrap; }'
                '</style></head><body style=" font-family:\'MS Shell Dlg 2\'; font-size:8pt; font-weight:400; font-style:normal;">')
        html += text
        return html


class SettingsRow:
    """Class for a single row in the settings table."""

    def __new__(cls, parent, key, settings):
        if settings.get('type', '').lower() == 'combobox':
            cls = SettingsComboBox
        elif settings.get('type', '').lower() == 'spinbox':
            cls = SettingsSpinBox
        elif settings.get('type', '').lower() == 'doublespinbox':
            cls = SettingsDoubleSpinBox
        elif settings.get('type', '').lower() == 'crswidget':
            cls = SettingsCRSWidget
        return object.__new__(cls)

    def __init__(self, parent, key: str, settings: dict) -> None:
        self.parent = parent
        self.key = key
        self.settings = settings
        self.default = ''
        self._delegate = RichTextDelegate(parent)

    def delegate(self):
        return self._delegate

    def default_value(self):
        return self.default


class SettingsComboBox(SettingsRow):

    def __init__(self, parent, key: str, settings: dict) -> None:
        super().__init__(parent, key, settings)
        self.options = settings.get('options', [])
        self.default = settings.get('default', '')
        self._delegate = ComboBoxDelegate(parent, items=self.options, col_idx=1)

    def delegate(self):
        return self._delegate


class SettingsSpinBox(SettingsRow):

    def __init__(self, parent, key: str, settings: dict) -> None:
        super().__init__(parent, key, settings)
        self.range = settings.get('range', (0, 100))
        self.default = settings.get('default', 0)
        self.step = settings.get('step', 1)
        self._delegate = SpinBoxDelegate(parent, minimum=self.range[0], maximum=self.range[1], step=self.step, col_idx=1)

    def default_value(self):
        return int(self.default)


class SettingsDoubleSpinBox(SettingsSpinBox):

    def __init__(self, parent, key: str, settings: dict) -> None:
        super().__init__(parent, key, settings)
        self.decimals = settings.get('decimals', 1)
        self._delegate = DoubleSpinBoxDelegate(parent, minimum=self.range[0], maximum=self.range[1], step=self.step,
                                               decimals=self.decimals, col_idx=1)

    def default_value(self):
        return '{0:.{1}f}'.format(self.default, self.decimals)


class SettingsCRSWidget(SettingsRow):

    def __init__(self, parent, key: str, settings: dict) -> None:
        super().__init__(parent, key, settings)
        self._delegate = CRSDelegate(parent, col_idx=1)
        self.default = settings.get('default', '')
