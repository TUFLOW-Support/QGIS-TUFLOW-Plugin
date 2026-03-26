from qgis.PyQt.QtWidgets import (QWidget, QBoxLayout, QComboBox, QLabel, QVBoxLayout, QHBoxLayout, QTableWidget,
                                 QTableWidgetItem)
from qgis.PyQt.QtCore import QSettings
from qgis.gui import QgsCollapsibleGroupBox

from ...tvinstance import get_viewer_instance
from ...fmt_importer import get_available_classes

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ....compatibility_routines import (QT_ITEM_FLAG_ITEM_IS_USER_CHECKABLE, QT_ITEM_FLAG_ITEM_IS_ENABLED,
                                            QT_CHECKED, QT_UNCHECKED)
else:
    from tuflow.compatibility_routines import (QT_ITEM_FLAG_ITEM_IS_USER_CHECKABLE, QT_ITEM_FLAG_ITEM_IS_ENABLED,
                                               QT_CHECKED, QT_UNCHECKED)


class Formats:

    def _init_formats(self, layout: QBoxLayout) -> QWidget:
        self.formats_widget = QWidget()
        self.formats_layout = QVBoxLayout()
        self.formats_widget.setLayout(self.formats_layout)

        # formats / linked result formats
        self.linked_formats_groupbox = QgsCollapsibleGroupBox()
        self.linked_formats_groupbox.setTitle('Linked Result Formats')
        self.linked_formats_groupbox.setToolTip('Select which result formats should be managed by TUFLOW Viewer.\n\n'
                                                'Example, disabling "XMDF" will disable the drag/drop handler and '
                                                'XMDF results will no longer appear in the plot window')
        self.formats_layout.addWidget(self.linked_formats_groupbox)
        self.linked_formats_layout = QVBoxLayout()
        self.linked_formats_groupbox.setLayout(self.linked_formats_layout)
        self.linked_formats_table = QTableWidget()
        self.linked_formats_table.setColumnCount(2)
        self.linked_formats_table.setHorizontalHeaderLabels(['Format', 'Load Method'])
        self.linked_formats_table.verticalHeader().setVisible(False)
        self.linked_formats_table.horizontalHeader().setStretchLastSection(True)
        widths = QSettings().value('tuflow_viewer/options_dialog/formats/linked_formats_table/column_widths', None, type=list)
        if widths is not None and len(widths) == 2:
            self.linked_formats_table.setColumnWidth(0, int(widths[0]))
        else:
            self.linked_formats_table.setColumnWidth(0, 200)
        self.linked_formats_table.horizontalHeader().geometriesChanged.connect(self.linked_formats_table_header_changed)
        formats = []
        for name in sorted(get_viewer_instance().output_handlers):
            hnd = get_viewer_instance().output_handlers[name]
            if hnd.DRIVER_NAME in formats:
                continue
            formats.append(hnd.DRIVER_NAME)
            if hnd.DRIVER_NAME not in get_viewer_instance().settings.enabled_fmts:
                continue
            item = QTableWidgetItem(hnd.DRIVER_NAME)
            item.setFlags(QT_ITEM_FLAG_ITEM_IS_USER_CHECKABLE | QT_ITEM_FLAG_ITEM_IS_ENABLED)
            if get_viewer_instance().settings.enabled_fmts[hnd.DRIVER_NAME]:
                item.setCheckState(QT_CHECKED)
            else:
                item.setCheckState(QT_UNCHECKED)
            item2 = QTableWidgetItem(hnd.AUTO_LOAD_METHOD)
            item2.setFlags(QT_ITEM_FLAG_ITEM_IS_ENABLED)
            row = self.linked_formats_table.rowCount()
            self.linked_formats_table.insertRow(row)
            self.linked_formats_table.setItem(row, 0, item)
            self.linked_formats_table.setItem(row, 1, item2)
        # catch signal when an item in the table checked state changes
        self.linked_formats_table.itemChanged.connect(self.linked_formats_item_changed)
        self.linked_formats_layout.addWidget(self.linked_formats_table)

        # self.formats_layout.addStretch()
        layout.addWidget(self.formats_widget)
        self.formats_widget.hide()
        return self.formats_widget

    def linked_formats_table_header_changed(self):
        widths = [
            self.linked_formats_table.columnWidth(0),
            self.linked_formats_table.columnWidth(1),
        ]
        QSettings().setValue('tuflow_viewer/options_dialog/formats/linked_formats_table/column_widths', widths)

    def linked_formats_item_changed(self, item: QTableWidgetItem):
        fmt_name = item.text()
        is_enabled = item.checkState() == QT_CHECKED
        get_viewer_instance().settings.enabled_fmts[fmt_name] = is_enabled
