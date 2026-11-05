"""
Climate change scenario table widget for the ARR2026 dock.

Provides a ``QTableWidget`` subclass with dropdown (combobox) editors for the
"Year" and "SSP" columns.
Also contains helper methods for adding/removing scenario rows and generating a list of unique
scenario names which are written to an output block for users to review.
"""

from qgis.PyQt.QtWidgets import QTableWidget, QTableView

from ..bridge_editor.BridgeEditorTable import ComboBoxDelegate
from ..compatibility_routines import (
    QT_ABSTRACT_ITEM_VIEW_SELECT_ROWS,
    QT_ABSTRACT_ITEM_VIEW_SINGLE_SELECTION,
)
from ..pt.pytuflow.arr.config import CC_BASELINE_YEARS

# Column indices for the climate change scenario table.
COL_YEAR = 0
COL_SSP = 1

# Dropdown options for each column. The first entry in each list is used as the default value for newly added rows.
YEAR_OPTIONS = [str(year) for year in CC_BASELINE_YEARS]
SSP_OPTIONS = ['SSP1', 'SSP2', 'SSP3', 'SSP5']


class ClimateChangeScenTable(QTableWidget):
    """Table widget for selecting climate change (year / SSP) scenarios.

    Column 0 ("Year") and column 1 ("SSP") are edited via combo box dropdowns
    populated from :data:`YEAR_OPTIONS` / :data:`SSP_OPTIONS` respectively.
    """

    def __init__(self, parent=None) -> None:
        QTableView.__init__(self, parent)
        self.setItemDelegateForColumn(COL_YEAR, ComboBoxDelegate(self, list(YEAR_OPTIONS)))
        self.setItemDelegateForColumn(COL_SSP, ComboBoxDelegate(self, list(SSP_OPTIONS)))
        self.setSelectionBehavior(QT_ABSTRACT_ITEM_VIEW_SELECT_ROWS)
        self.setSelectionMode(QT_ABSTRACT_ITEM_VIEW_SINGLE_SELECTION)

    def add_scenario(self) -> None:
        """Adds a new scenario row, defaulting to the first Year/SSP option (as
        declared in :data:`YEAR_OPTIONS` / :data:`SSP_OPTIONS`), and selects it."""

        row = self.rowCount()
        self.insertRow(row)
        self.model().setData(self.model().index(row, COL_YEAR), YEAR_OPTIONS[0])
        self.model().setData(self.model().index(row, COL_SSP), SSP_OPTIONS[0])
        self.selectRow(row)

    def remove_selected_scenario(self) -> None:
        """Removes the currently selected row, if any row is selected."""

        row = self.currentRow()
        if row >= 0:
            self.removeRow(row)

    def scenario_names(self):
        """Returns a list of scenario names (e.g. ``"2030_SSP1"``), one per row in
        the table, in row order. Duplicate names (i.e. duplicate Year/SSP
        combinations) have ``_1``, ``_2`` etc. appended to keep every name unique."""

        names = []
        for row in range(self.rowCount()):
            year = self.model().data(self.model().index(row, COL_YEAR))
            ssp = self.model().data(self.model().index(row, COL_SSP))
            base_name = f'{year}_{ssp}'
            name = base_name
            count = 1
            while name in names:
                name = f'{base_name}_{count}'
                count += 1
            names.append(name)
        return names
