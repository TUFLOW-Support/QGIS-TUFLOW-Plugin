from pathlib import Path

import pandas as pd
from qgis.PyQt import QtWidgets, QtCore, QtGui
from qgis.gui import QgsMessageBar
from qgis.core import Qgis

from . import pytuflow, PandasTableModel, ToolButtonDelegate
from ...pyqtgraph import PlotWidget, mkPen, PlotCurveItem
from ...tuflow_viewer_v2.widgets.tv_plot_widget.pyqtgraph_subclass.hoverable_curve_item import HoverableCurveItem
from ...tuflow_viewer_v2.widgets.tv_plot_widget.pyqtgraph_subclass.custom_view_box import CustomViewBox
from ...tuflow_viewer_v2.widgets.tv_plot_widget.plotsourceitem import PlotSourceItem
from ...tuflow_viewer_v2.widgets.tv_plot_widget.base_plot_widget import TVPlotWidget


class TableView(QtWidgets.QTableView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.viewport().installEventFilter(self)

    def messageBar(self) -> QgsMessageBar | None:
        parent = self.parent()
        while parent and not hasattr(parent, 'messageBar'):
            parent = parent.parent()
        if parent and hasattr(parent, 'messageBar'):
            return parent.messageBar()
        return None

    def keyPressEvent(self, event):
        if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier and event.key() == QtCore.Qt.Key.Key_C:
            selection = self.selectionModel().selection()
            if not selection.indexes():
                return
            # get selected rows and columns
            rows = sorted(set(index.row() for index in selection.indexes()))
            cols = sorted(set(index.column() for index in selection.indexes()))
            # build a tab-separated string of the selected cells
            data_str = ''
            for row in rows:
                row_data = []
                for col in cols:
                    index = self.model().index(row, col)
                    row_data.append(str(self.model().data(index, QtCore.Qt.ItemDataRole.DisplayRole)))
                data_str += '\t'.join(row_data) + '\n'
            else:
                super().keyPressEvent(event)

            # copy to clipboard
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(data_str)


class PreviewPlotWidget(TVPlotWidget):
    PLOT_TYPE = 'PreviewPlot'

    def __init__(self, parent=None):
        self._geom_type = 'marker'  # doesn't make any difference, but marker is a valid type
        super().__init__(parent)
        self.toolbar.hide()
        self.plot_linker.hide()

    def messageBar(self) -> QgsMessageBar | None:
        parent = self.parent()
        while parent and not hasattr(parent, 'messageBar'):
            parent = parent.parent()
        if parent and hasattr(parent, 'messageBar'):
            return parent.messageBar()

    def create_context_menu(self, vb: 'CustomViewBox', menu: QtWidgets.QMenu) -> QtWidgets.QMenu:
        menu = super().create_context_menu(vb, menu)
        for action in menu.actions():
            if action.text() == 'Clear':
                action.setVisible(False)
            elif action.text() == 'Copy...' and action.menu():
                for action2 in action.menu().actions():
                    if 'Copy drawn items' in action2.text():
                        action2.setVisible(False)
            elif action.text() == 'Export...' and action.menu():
                for action2 in action.menu().actions():
                    if 'Export drawn items' in action2.text():
                        action2.setVisible(False)
        return menu


class DatabasePreviewWidget(QtWidgets.QDialog):

    closed = QtCore.pyqtSignal(QtWidgets.QDialog)

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        if self.db:
            self.df = self.db._df
            self.setWindowTitle(db.fpath.name + ' - Data Preview')
        if self.df is None:
            self.df = pd.DataFrame()
        self.layout = QtWidgets.QVBoxLayout()
        self.message_bar = QgsMessageBar()
        self.layout.addWidget(self.message_bar)
        self.tab_widget = QtWidgets.QTabWidget()
        self.layout.addWidget(self.tab_widget)
        self.setLayout(self.layout)

        self.tab_widget.addTab(self.database_preview(), 'Data Preview')
        self.resize(800, 300)

    def messageBar(self) -> QgsMessageBar:
        return self.message_bar

    def database_preview(self) -> QtWidgets.QWidget:
        self.preview_table = TableView()

        model = PandasTableModel(df=self.df.copy(), add_button_column=True, include_df_index=True)
        self.preview_table.setModel(model)
        self.preview_table.verticalHeader().setVisible(False)
        self.style_table(self.preview_table)
        self.add_plot_button_delegate(self.preview_table)
        return self.preview_table

    def style_table(self, table: QtWidgets.QTableView):
        # Make the font a bit smaller for better density
        f = table.font()
        # reduce point size by 1 if possible
        ps = f.pointSizeF()
        if ps > 0:
            f.setPointSizeF(max(8.0, ps - 1.0))
        else:
            f.setPointSize(max(8, f.pointSize() - 1))
        table.setFont(f)

        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(False)
        table.resizeRowsToContents()

        # resize columns once to fit contents and add a slight buffer
        table.resizeColumnsToContents()
        buffer_px = 8
        col_count = table.model().columnCount()
        for col in range(col_count):
            w = table.columnWidth(col)
            new_w = int(w + buffer_px)
            table.setColumnWidth(col, new_w)

        # ensure rows are correctly sized after the view is shown (defer to next event loop iteration)
        QtCore.QTimer.singleShot(0, table.resizeRowsToContents)

    def add_plot_button_delegate(self, table: QtWidgets.QTableView):
        # attach a delegate with a tool-button to the leading action column (col 0)
        try:
            try:
                icon_path = Path(__file__).parents[2] / 'icons' / 'time_series.svg'
                action_icon = QtGui.QIcon(str(icon_path))
            except Exception:
                action_icon = QtGui.QIcon()

            # callback that receives a QModelIndex
            should_show = lambda index: self.should_show_plot_button(index.row(), table.model())
            # don't overwrite should_show; it must be a callable passed to the delegate
            delegate = ToolButtonDelegate(action_icon, should_show, parent=self.preview_table)
            delegate.triggered.connect(self.show_plot)
            table.setItemDelegateForColumn(0, delegate)
            # give the action column a reasonable width
            try:
                table.setColumnWidth(0, 28)
            except Exception:
                pass
        except Exception:
            pass

        # ensure the table view is non-editable
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

    def should_show_plot_button(self, row_index: int, model=None) -> bool:
        """Placeholder: return True when an action button should be shown for the given row."""
        entry = self.db.entries.get(self.db.df.index[row_index])
        if not entry:
            return False
        if entry.uses_source_file:
            return True
        if self.db.TUFLOW_TYPE in [pytuflow.const.DB.MAT, pytuflow.const.DB.MAT_TMF] and entry.is_list():
            return True  # depth varying roughness
        return False

    def closeEvent(self, event):
        self.closed.emit(self)
        super().closeEvent(event)

    def show_plot(self, index: QtCore.QModelIndex):
        name = str(self.db.df.index[index.row()])
        i = self.create_data_tab(name)
        if i == -1:
            return
        self.tab_widget.setCurrentIndex(i)

    def create_data_tab(self, name: str) -> int:
        for i in range(1, self.tab_widget.count()):
            if self.tab_widget.tabText(i) == name:
                return i

        try:
            data = self.db.value(name)
        except Exception as e:
            return -1

        data_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(tab_widget)
        data_widget.setLayout(layout)

        plot = PreviewPlotWidget(parent=self)
        tab_widget.addTab(plot, 'Plot')

        # setup - mostly unimportant, the class is from TUFLOW Viewer
        src_item = PlotSourceItem(
            name, 'curve', self.db.fpath.name, data.columns[0], name, 'database',
            [], False, '#4181e8', 'selection', True, None
        )
        src_item.xdata = data.index.values
        src_item.ydata = data.iloc[:, 0].values
        src_item.xaxis_name = data.index.name
        src_item.yaxis_name = data.columns[0]
        src_item.label = name
        src_item.use_label_in_tooltip = False
        curve = HoverableCurveItem(
            x=src_item.xdata,
            y=src_item.ydata,
            name=src_item.label,
            pen=mkPen(src_item.colour, width=2),
            src_item=src_item,
            connect='finite'
        )
        curve.sigHoverEvent.connect(plot._on_hover)
        plot.plot_graph.addItem(curve)

        table = TableView()
        model = PandasTableModel(df=data, add_button_column=False, include_df_index=True)
        table.setModel(model)
        self.style_table(table)
        tab_widget.addTab(table, 'Table')

        return self.tab_widget.addTab(data_widget, name)
