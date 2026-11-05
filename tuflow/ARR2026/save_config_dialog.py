"""
Dialog that allows the user to choose where and how to save the docks current state to
one or more .json configuration files.

Will collect the output location and file name.
The actual .json building and saving is in ``Arr2026Dock._save_config_json``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import os

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QToolButton, QDialogButtonBox, QFileDialog
)
from qgis.core import QgsApplication
from .arr_shared_functionality import _CONFIG_JSON_FILE_FILTER

class SaveConfigDialog(QDialog):
    """Allows the user to choose where and how to save the docks current state to
    one or more .json configuration files.

    ``catchment_count`` changes the browse button's behaviour:
        - 1 (or 0) catchment(s) - browser picks a single ``.json`` file, splitting the chosen
          path into ``output_loc_line_edit`` (folder)/``file_name_line_edit`` (filename);
        - more than 1 catchment - browsing picks a folder (``file_name_line_edit`` is left untouched),
          since one .json file per catchment is written.
    """

    def __init__(self, catchment_count: int, main_path: Optional[str] = None, parent=None) -> None:
        super().__init__(parent)

        # Window setup
        self.setWindowTitle('Save Dock As Configuration .json')
        self.setMinimumWidth(480)
        self._catchment_count = max(catchment_count, 0)

        # Main output location and default filename
        main_path_obj = Path(main_path) if main_path else None
        default_folder = str(main_path_obj.parent) if main_path_obj else ''
        default_name = main_path_obj.stem if main_path_obj else 'config'

        # Setup window content
        layout = QVBoxLayout(self)

        # Window content - output location
        grid = QGridLayout()
        grid.addWidget(QLabel('Output location:', self), 0, 0)
        self.output_loc_line_edit = QLineEdit(default_folder, self)
        grid.addWidget(self.output_loc_line_edit, 0, 1)
        self.browse_tool_button = QToolButton(self)
        self.browse_tool_button.setText('...')
        self.browse_tool_button.setIcon(QgsApplication.getThemeIcon('/mActionFileOpen.svg'))
        grid.addWidget(self.browse_tool_button, 0, 2)

        # Window content - output filename
        grid.addWidget(QLabel('Filename:', self), 1, 0)
        self.file_name_line_edit = QLineEdit(default_name, self)
        grid.addWidget(self.file_name_line_edit, 1, 1, 1, 2)
        layout.addLayout(grid)

        # Window content - information text containers
        info = QLabel(self._info_text(), self)
        info.setWordWrap(True)
        layout.addWidget(info)

        # Window content - save and cancel buttons
        button_box = QDialogButtonBox(self)
        self.save_tool_button = button_box.addButton('Save', QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton('Cancel', QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.browse_tool_button.clicked.connect(self._on_browse_clicked)

    def _info_text(self) -> str:
        """
        Set the text to put into the info text containers defined above.
        This text is to help the user understand the different input options that are available.

        The info text used varies depending on the number of catchments currently configured in the dock.
        """
        if self._catchment_count <= 1:
            return (
                "A single configuration .json file will be saved to: '<output location>/<filename>.json' \n"
                "Note that '.json' is appended automatically if not specified."
            )
        return (
            f"{self._catchment_count} catchments are currently configured in the tool window. \n"
            "One .json file will be saved per catchment into the output location.\n\n"
            "The placeholders ${name} and/or ${enum} can be used in the filename to input the catchment's name "
            "(Name column) and/or a number corresponding to its position in the table.\n"
            "e.g., 'config-SEQ-${name}-${enum} may have an output .json 'config-SEQ-SC_A-1.json' \n\n"
            "If neither placeholder is used, each catchment's name is appended to the filename automatically instead."
        )

    def _on_browse_clicked(self) -> None:
        """
        Handles what happens when the user clicks the file browse button.
        The behaviour depends on the number of catchments currently configured in the dock:
            - 1 catchment - .json file
            - >= 2 catchments - folder
        """
        current_folder = self.output_loc_line_edit.text().strip()
        start_dir = current_folder if current_folder and Path(current_folder).is_dir() else ''

        if self._catchment_count <= 1:
            current_name = self.file_name_line_edit.text().strip()
            start_path = str(Path(start_dir) / current_name) if start_dir else current_name
            path, _ = QFileDialog.getSaveFileName(
                self, 'Save Configuration .json', start_path, _CONFIG_JSON_FILE_FILTER)
            if not path:
                return
            selected = Path(path)
            self.output_loc_line_edit.setText(str(selected.parent))
            self.file_name_line_edit.setText(selected.stem)
        else:
            folder = QFileDialog.getExistingDirectory(self, 'Output Location', start_dir)
            if folder:
                self.output_loc_line_edit.setText(folder)

    def output_folder(self) -> str:
        """Returns the currently entered output folder path."""

        return self.output_loc_line_edit.text().strip()

    def filename_pattern(self) -> str:
        """Returns the currently entered filename."""

        return self.file_name_line_edit.text().strip()

