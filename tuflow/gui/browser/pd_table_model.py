import pandas as pd

from qgis.PyQt import QtCore


class PandasTableModel(QtCore.QAbstractTableModel):
    """PandasTableModel is a QAbstractTableModel that wraps a pandas DataFrame for display in a QTableView.

    An additional column can be added at the start for an action button e.g. a QToolButtonDelegate.
    """

    def __init__(self, df: pd.DataFrame = None, parent=None, add_button_column: bool = False, include_df_index: bool = True):
        super().__init__(parent)
        self.add_button_column = add_button_column
        self.include_df_index = include_df_index
        self.df = df

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if self.df is None else len(self.df.index)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        count = 0 if self.df is None else len(self.df.columns)
        if self.include_df_index:
            count += 1
        if self.add_button_column:
            count += 1
        return count

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or self.df is None:
            return None
        # For the action column we don't return textual content
        if self.add_button_column and index.column() == 0:
            if role == QtCore.Qt.ItemDataRole.DisplayRole:
                return ''
            return None

        col = index.column() - 1 if self.add_button_column else index.column()
        if role in (QtCore.Qt.ItemDataRole.DisplayRole, QtCore.Qt.ItemDataRole.EditRole):
            try:
                if self.include_df_index and col == 0:
                    val = self.df.index[index.row()]
                else:
                    if self.include_df_index:
                        col -= 1
                    val = self.df.iat[index.row(), col]
            except Exception:
                return None
            if pd.isna(val):
                return ''
            return str(val)
        return None

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == QtCore.Qt.Orientation.Horizontal:
            if self.add_button_column and section == 0:
                return '' # header for action column
            col = section - 1 if self.add_button_column else section
            try:
                if self.include_df_index and col == 0:
                    return str(self.df.index.name) if self.df.index.name is not None else 'index'
                else:
                    if self.include_df_index:
                        col -= 1
                    return str(self.df.columns[col])
            except Exception:
                return str(section)
        else:
            # show simple row numbers for vertical header (or hide it in the view)
            return str(section)

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags
        # action column shouldn't be editable/selectable (delegate handles clicks)
        if index.column() == 0 and self.add_button_column:
            return QtCore.Qt.ItemFlag.ItemIsEnabled
        return QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled

    def setDataFrame(self, df: pd.DataFrame):
        # convenience method to replace the DataFrame and refresh the view
        self.beginResetModel()
        self.df = df
        self.endResetModel()