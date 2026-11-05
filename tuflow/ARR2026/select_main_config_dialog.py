"""
Small dialog used by ``arr2026_dock.Arr2026Dock`` to let the user choose which of the input
configuration .json files should be treated as the "main" config, when more than one
of the selected files looks like it could be the main one (see
``arr_shared_functionality.is_main_config_candidate``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QDialogButtonBox, QAbstractItemView
)

from ..compatibility_routines import QT_ITEM_DATA_USER_ROLE, QT_DIALOG_ACCEPTED


class MainConfigSelectDialog(QDialog):
    """Lets the user pick a single "main" configuration .json file out of ``candidate_paths``.

    Shown by :meth:`arr2026_dock.Arr2026Dock._on_config_json_browse_clicked` when more than one
    of the user's selected files looks like it could be the main config (i.e. contains more than
    just a ``site`` section)."""

    def __init__(self, candidate_paths: Sequence[str], parent=None) -> None:
        super().__init__(parent)

        # Window setup
        self.setWindowTitle('Select Main Configuration File')
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        # Info to display to help users determine their next step
        message = QLabel(
            "More than one selected file looks like it could be the 'main' configuration "
            "(i.e. it contains more than just 'site' information).\n\n"
            "Choose which one to use to populate all settings other then 'site'. "
            "The rest will only load their 'site' (catchment) information.",
            self,
        )
        # Window content - add info
        message.setWordWrap(True)
        layout.addWidget(message)

        # Window content - set up list of candidate json files
        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for path in candidate_paths:
            item = QListWidgetItem(Path(path).name, self.list_widget)
            item.setData(QT_ITEM_DATA_USER_ROLE, str(path))
            item.setToolTip(str(path))
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
        layout.addWidget(self.list_widget)

        # Window content - set up buttons
        button_box = QDialogButtonBox(self)
        self._use_selected_button = button_box.addButton(
            'Use Selected', QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton('Cancel', QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self._use_selected_button.setEnabled(self.list_widget.count() > 0)
        self.list_widget.itemSelectionChanged.connect(
            lambda: self._use_selected_button.setEnabled(bool(self.list_widget.selectedItems())))
        self.list_widget.itemDoubleClicked.connect(lambda *_: self.accept())
        layout.addWidget(button_box)

    def selected_path(self) -> Optional[str]:
        """Returns the chosen file path, or ``None`` if nothing is selected.
        This gets added to the line edit in the dock."""

        items = self.list_widget.selectedItems()
        if not items:
            return None
        return items[0].data(QT_ITEM_DATA_USER_ROLE)

    @staticmethod
    def get_main_config_path(candidate_paths: Sequence[str], parent=None) -> Optional[str]:
        """Convenience helper: shows the dialog and returns the chosen path, or ``None`` if the
        user cancelled."""

        dlg = MainConfigSelectDialog(candidate_paths, parent)
        if dlg.exec() == QT_DIALOG_ACCEPTED:
            return dlg.selected_path()
        return None

