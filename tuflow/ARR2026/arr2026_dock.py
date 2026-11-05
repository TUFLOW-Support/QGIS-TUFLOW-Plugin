"""
Controller for the ARR2026 dock widget.
"""

from __future__ import annotations

import html
import json
import logging
from pathlib import Path
from typing import Optional

from qgis.PyQt.QtCore import QThread, QSize
from qgis.PyQt.QtWidgets import (
    QApplication, QDockWidget, QWidget, QFileDialog, QCheckBox, QMessageBox
)
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication, QgsProject, QgsMapLayer

from ..compatibility_routines import (
    QT_MESSAGE_BOX_YES,
    QT_MESSAGE_BOX_NO,
    QT_DIALOG_ACCEPTED,
    is_qt6
)
from ..forms.arr2026_dock import Ui_arr2026
from ..gui.widgets.wrapping_tab_widget import WrappingTabWidget

from ..toc.toc import findAllVectorLyrsWithGroups, tuflowqgis_find_layer
from .arr_run_worker import ArrRunWorker
from . import catchments_table
from .arr_shared_functionality import (
    is_point_layer,
    is_polygon_layer,
    is_main_config_candidate,
    populate_feature_combobox,
    populate_layer_combobox,
    resolve_config_filename,
    sanitise_filename_part,
    write_json_config,
    write_json_configs,
    _LAYER_ID_ROLE,
    _CONFIG_JSON_FILE_FILTER
)
from .generate_pytuflow_json import GenerateARRjson
from .select_main_config_dialog import MainConfigSelectDialog
from .save_config_dialog import SaveConfigDialog
from .pytuflow_log_bridge import _PytuflowLogBridge, _PYTUFLOW_LOGGER_NAME
from .populate_dock_from_json import PopulateARRDockFromjson

# File dialog filter string for browsing to a temporal patters csv file.
_TP_FILE_FILTER = (
    'Temporal patterns files (*.csv)'
)
# File dialog filter string for browsing to a response .json file.
_RESPONSE_JSON_FILE_FILTER = (
    'Response files (*.json)'
)

class Arr2026Dock(QDockWidget, Ui_arr2026):
    """Dock widget controller for the ARR2026 tool."""

    def __init__(self, iface) -> None:
        QDockWidget.__init__(self)
        self.iface = iface
        self.setupUi(self)

        # arr2026 logo doesn't render well in Qt5 - correct it with pngs
        if not is_qt6:
            basename = str(Path(__file__).parents[1] / 'icons' / 'arr2026_tuflow')
            icon = QIcon()
            icon.addFile(f'{basename}_16.png', QSize(73, 16))
            icon.addFile(f'{basename}_24.png', QSize(109, 24))
            icon.addFile(f'{basename}_36.png', QSize(164, 36))
            icon.addFile(f'{basename}_48.png', QSize(219, 48))
            icon.addFile(f'{basename}_64.png', QSize(292, 64))
            pxmap = icon.pixmap(QSize(164, 36))
            self.top_doco_block_logo.setPixmap(pxmap)

        self._replace_tab_widget_with_wrapping_version()
        self._add_verbose_logging_checkbox()

        # Background thread/worker (see :mod:`arr_run_worker`) used to run the pytuflow
        # ``arr`` tool without blocking the QGIS GUI thread - set up in :meth:`_on_run_clicked`,
        # torn down in :meth:`_on_run_finished`. ``None`` while no run is in progress.
        self._run_thread: QThread | None = None
        self._run_worker: ArrRunWorker | None = None
        self._pytuflow_log_handler: _PytuflowLogBridge | None = None
        self._pytuflow_log_previous_level: int | None = None

        # The GIS point layer currently being watched for selection changes by
        # ``_on_outlet_location_select_feature_clicked``/``_on_outlet_location_feature_selection_changed``.
        self._outlet_location_watched_layer = None

        # Parsed json config dicts stashed from a multi-file browse for every selected file *other* than the chosen
        # "main" config
        # This is used to populate ``inputs_catchments_table`` with every catchment when "Load from disk..." is clicked.
        # It is cleared whenever the text in ``req_set_pop_from_json_line_edit`` is edited
        # (either by hand or by loading a new file)
        self._pending_catchment_jsons: list[dict] = []
        # The "main" config path ``_pending_catchment_jsons`` is also stashed
        self._pending_catchment_jsons_main_path: Optional[str] = None
        # The config path the dock was last populated from (via browsing or hand
        # editing/confirming ``req_set_pop_from_json_line_edit``), so ``editingFinished`` doesn't
        # needlessly re-populate the dock if the path hasn't actually changed.
        self._last_auto_populated_config_path: Optional[str] = None

        self._connect_signals()
        self._init_conditional_state()

        # --- Set icon images for tool buttons ---
        # Climate change table add/remove buttons
        self.climate_change_add_tool_button.setIcon(QgsApplication.getThemeIcon('/symbologyAdd.svg'))
        self.climate_change_subtract_tool_button.setIcon(QgsApplication.getThemeIcon('/symbologyRemove.svg'))
        # Catchments table add/remove buttons
        self.inputs_catchments_add_tool_button.setIcon(QgsApplication.getThemeIcon('/symbologyAdd.svg'))
        self.inputs_catchments_subtract_tool_button.setIcon(QgsApplication.getThemeIcon('/symbologyRemove.svg'))
        # Response .json file browse button
        self.offline_mode_json_tool_button.setIcon(QgsApplication.getThemeIcon('/mActionFileOpen.svg'))
        # Manually specified temporal patterns (point/areal) file browse buttons
        self.tp_manual_point_tp_file_tool_button.setIcon(QgsApplication.getThemeIcon('/mActionFileOpen.svg'))
        self.tp_manual_areal_tp_file_tool_button.setIcon(QgsApplication.getThemeIcon('/mActionFileOpen.svg'))
        # Output location folder browse button
        self.output_location_file_button.setIcon(QgsApplication.getThemeIcon('/mActionFileOpen.svg'))
        # Configuration .json file browse button and refresh button
        self.req_set_pop_from_json_file_tool_button.setIcon(QgsApplication.getThemeIcon('/mActionFileOpen.svg'))
        # Outlet location "select point feature" button
        self.outlet_location_gis_layer_feature_select_tool_button.setIcon(
            QgsApplication.getThemeIcon('/mActionSelectRectangle.svg'))

    def _replace_tab_widget_with_wrapping_version(self) -> None:
        """Swaps the ``QTabWidget`` (``tab_widget``) in the arr2026_dock.ui for a custom :class:`WrappingTabWidget`.
        This custom widget will allow the 'tab bar' to wrap onto a new line when the available width has
        been filled, rather then scrolling horizontally.

        It keeps the ``tab_widget`` attribute name and the same grid position so the rest of the dock is unaffected.

        NOTE: This function exists to allow this change to happen in code so the ui can remain the same.
        """

        old_tab_widget = self.tab_widget
        # determine the parent layout of the tab_widget
        try:
            parent_layout = old_tab_widget.parent().layout()
        except Exception:
            raise ValueError(f"Could not determine the parent layout of {old_tab_widget}.")

        index = parent_layout.indexOf(old_tab_widget)
        row, col, row_span, col_span = parent_layout.getItemPosition(index)

        # Collect each tab's page widget/icon/title before reparenting anything.
        tabs = [
            (old_tab_widget.widget(i), old_tab_widget.tabIcon(i), old_tab_widget.tabText(i))
            for i in range(old_tab_widget.count())
        ]
        current_index = old_tab_widget.currentIndex()

        new_tab_widget = WrappingTabWidget(self.ARR2026)
        for page_widget, icon, title in tabs:
            new_tab_widget.addTab(page_widget, icon, title)
        new_tab_widget.setCurrentIndex(max(current_index, 0))

        parent_layout.removeWidget(old_tab_widget)
        old_tab_widget.deleteLater()
        parent_layout.addWidget(new_tab_widget, row, col, row_span, col_span)

        self.tab_widget = new_tab_widget

    def _add_verbose_logging_checkbox(self) -> None:
        """Adds a "Verbose log" checkbox to ``bottom_status_block``, not present in the ``.ui``
        file itself.
        Toggles whether ``pytuflow``'s ``DEBUG``-level log messages (in addition to
        its normal ``INFO``/``WARNING``/``ERROR`` messages) are output to ``log_text_edit`` while a
        run is in progress."""

        self.pytuflow_verbose_logging_checkbox = QCheckBox('Verbose log', self)
        self.pytuflow_verbose_logging_checkbox.setToolTip(
            "Verbose output in log."
        )
        # Next to Run button (after the stretch spacer)
        run_button_index = self.bottom_status_block.indexOf(self.bottom_status_block_run_button)
        self.bottom_status_block.insertWidget(run_button_index, self.pytuflow_verbose_logging_checkbox)


    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """Connects every "controlling" widget's change signal to its conditional visibility slot.
        Each slot is also called once in :meth:`_init_conditional_state`
        so the dock's initial appearance matches whatever the controlling widgets are
        set to in the ``.ui`` file (signals only fire on a *change*, not for the current/initial value)."""

        # --- Inputs: catchments table add/remove/clear rows ---
        self.inputs_catchments_add_tool_button.clicked.connect(self._on_catchments_add_clicked)
        self.inputs_catchments_subtract_tool_button.clicked.connect(self._on_catchments_subtract_clicked)
        self.inputs_catchments_clear_table_tool_button.clicked.connect(self._on_catchments_clear_table_clicked)

        # --- Inputs: bulk-populate catchments table GIS layer/field selection ---
        self.bulk_pop_catchments_gis_layer_combobox.currentIndexChanged.connect(
            self._on_bulk_pop_catchments_layer_changed)
        self.bulk_pop_catchments_populate_tool_button.clicked.connect(
            self._on_bulk_pop_catchments_populate_clicked)

        # --- Inputs: outlet location on/off switch, method/GIS layer/feature selection ---
        self.outlet_location_checkbox.toggled.connect(
            self._on_outlet_location_checkbox_toggled)
        self.outlet_location_method_combobox.currentIndexChanged.connect(
            self._on_outlet_location_method_changed)
        self.outlet_location_gis_layer_combobox.currentIndexChanged.connect(
            self._on_outlet_location_layer_changed)
        self.outlet_location_gis_layer_feature_select_tool_button.clicked.connect(
            self._on_outlet_location_select_feature_clicked)

        # --- Save configuration .json file selection/save ---
        self.save_config_json_save_tool_button.clicked.connect(
            self._on_save_config_json_save_clicked)

        # --- Reload tab parameters from config .json file ---
        self.req_set_reload_json_tool_button.clicked.connect(
            lambda: self._on_reload_json_tool_button_clicked(tab="req_set"))
        self.climate_change_reload_json_tool_button.clicked.connect(
            lambda: self._on_reload_json_tool_button_clicked(tab="cc"))
        self.arf_reload_json_tool_button.clicked.connect(
            lambda: self._on_reload_json_tool_button_clicked(tab="arf"))
        self.tp_reload_json_tool_button.clicked.connect(
            lambda: self._on_reload_json_tool_button_clicked(tab="tp"))
        self.preburst_reload_json_tool_button.clicked.connect(
            lambda: self._on_reload_json_tool_button_clicked(tab="preburst"))
        self.il_reload_json_tool_button.clicked.connect(
            lambda: self._on_reload_json_tool_button_clicked(tab="il"))
        self.manual_data_reload_json_tool_button.clicked.connect(
            lambda: self._on_reload_json_tool_button_clicked(tab="manual_data"))


        # --- Inputs: keep inputs_catchments_table's GIS layer comboboxes in sync with the QGIS workspace ---
        # Reloads the comboboxes whenever a vector layer is added, removed, reordered, renamed or has its data source changed
        QgsProject.instance().legendLayersAdded.connect(self._on_catchment_layers_added)
        QgsProject.instance().layersRemoved.connect(self._on_catchment_layers_removed)
        QgsProject.instance().layerTreeRoot().layerOrderChanged.connect(
            self._refresh_catchment_layer_comboboxes)
        QgsProject.instance().readProject.connect(self._on_catchment_project_read)
        for layer in QgsProject.instance().mapLayers().values():
            layer.nameChanged.connect(self._refresh_catchment_layer_comboboxes)
            layer.dataSourceChanged.connect(self._refresh_catchment_layer_comboboxes)

        # --- Offline mode: pregenerated json file selection ---
        self.offline_mode_json_tool_button.clicked.connect(
            self._on_offline_mode_json_browse_clicked)

        # --- Populate with config .json: config .json file selection ---
        self.req_set_pop_from_json_file_tool_button.clicked.connect(
            self._on_config_json_browse_clicked)
        # Hand editing the path clears any stashed catchments from a previous multi-file browse
        self.req_set_pop_from_json_line_edit.textEdited.connect(
            self._on_config_json_line_edit_hand_edited)
        # Hand editing/pasting a path and then confirming it (Enter/focus-out) auto populates the
        # dock from it, same as pressing the refresh button
        self.req_set_pop_from_json_line_edit.editingFinished.connect(
            self._on_config_json_line_edit_editing_finished)
        # Refresh button
        self.req_set_pop_from_json_refresh_tool_button.clicked.connect(
            self._on_json_refresh_button_clicked)

        # --- ARF: calculate area vs user-supplied area ---
        self.arf_calculate_area_radio_button.toggled.connect(self._on_arf_method_changed)
        self.arf_user_area_radio_button.toggled.connect(self._on_arf_method_changed)

        # --- ARF: manual override (greys out the automatic calculation only inputs) ---
        self.arf_manual_specify_block.toggled.connect(self._on_arf_manual_override_toggled)

        # --- Temporal Patterns: manual point/areal TP csv file selection ---
        self.tp_manual_point_tp_file_tool_button.clicked.connect(
            self._on_tp_file_browse_clicked)
        self.tp_manual_areal_tp_file_tool_button.clicked.connect(
            self._on_tp_file_browse_clicked)

        # --- Preburst: pattern method (recommended/constant/temporal pattern/none) ---
        self.preburst_pattern_method_combobox.currentIndexChanged.connect(
            self._on_preburst_method_changed)

        # --- Preburst: proportional vs fixed duration (constant / temporal pattern) ---
        self.preburst_constant_controls_prop_controls_checkbox.toggled.connect(
            self._on_preburst_constant_prop_toggled)
        self.preburst_tp_controls_prop_controls_checkbox.toggled.connect(
            self._on_preburst_tp_prop_toggled)

        # --- Initial loss: short duration extrapolation method ---
        self.il_short_dur_extrapolation_method_combobox.currentIndexChanged.connect(
            self._on_il_short_dur_method_changed)

        # --- Initial loss: TUFLOW loss method (infiltration (soils) vs rainfall excess (materials)) ---
        self.il_tuflow_loss_method_combobox.currentIndexChanged.connect(
            self._on_il_loss_method_changed)

        # --- AEP / Duration selection: "Select all" checkbox drives the individual checkboxes ---
        self.aep_checkbox_select_all.toggled.connect(self._on_aep_select_all_toggled)
        self.dur_checkbox_select_all.toggled.connect(self._on_duration_select_all_toggled)

        # --- Climate change: add/remove scenario rows ---
        self.climate_change_add_tool_button.clicked.connect(self._on_climate_change_add_clicked)
        self.climate_change_subtract_tool_button.clicked.connect(self._on_climate_change_subtract_clicked)
        climate_change_model = self.climate_change_table.model()
        climate_change_model.dataChanged.connect(self._update_climate_change_names_output)
        climate_change_model.rowsInserted.connect(self._update_climate_change_names_output)
        climate_change_model.rowsRemoved.connect(self._update_climate_change_names_output)

        # --- Outputs: output location folder browse ---
        self.output_location_file_button.clicked.connect(self._on_output_location_browse_clicked)

        # --- Run button ---
        self.bottom_status_block_run_button.clicked.connect(self._on_run_clicked)

    def _init_conditional_state(self) -> None:
        """Runs every conditional slot once so the dock's initial appearance matches
        the controlling widgets' initial values (signals don't fire retroactively)."""

        self._refresh_catchment_layer_comboboxes()
        self._on_outlet_location_checkbox_toggled(self.outlet_location_checkbox.isChecked())
        self._on_outlet_location_method_changed(self.outlet_location_method_combobox.currentIndex())
        self._on_arf_method_changed()
        self._on_arf_manual_override_toggled(self.arf_manual_specify_block.isChecked())
        self._on_preburst_method_changed(self.preburst_pattern_method_combobox.currentIndex())
        self._on_preburst_constant_prop_toggled(
            self.preburst_constant_controls_prop_controls_checkbox.isChecked())
        self._on_preburst_tp_prop_toggled(
            self.preburst_tp_controls_prop_controls_checkbox.isChecked())
        self._on_il_short_dur_method_changed(
            self.il_short_dur_extrapolation_method_combobox.currentIndex())
        self._on_il_loss_method_changed(self.il_tuflow_loss_method_combobox.currentIndex())
        self._update_climate_change_names_output()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def reset_dock_to_defaults(self, tab: Optional[str] = None) -> None:
        """Resets every dock input widget back to its ``.ui``-defined default value/state (see
        ``forms/arr2026_dock.py``'s ``Ui_arr2026.setupUi``), without re-running ``setupUi`` itself.

        Optional input ``tab`` to allow the reset of just one tab of the dock.
        ``tab`` can be one of: "req_set", "cc", "arf", "tp", "preburst", "il" or "manual_data"

        Intended to be run immediately before (re)populating the dock from a config .json file
        (see :mod:`populate_dock_from_json`), so every field not present in the json is left at
        its default value rather than whatever was previously entered/loaded, instead of each
        ``populate_*`` method having to carry its own ad-hoc "clear this field first" logic.

        Does not touch:
            - the QGIS project/any loaded layers (e.g. a previously loaded catchment boundary
              layer is left in the project, just deselected from the comboboxes it appears in);
            - ``log_text_edit``/the progress bar/run button state;
            - ``req_set_pop_from_json_line_edit`` itself (the config .json path(s) being applied).
        """

        # Set up helpers to track if just resetting one tab
        tabs = ["req_set", "cc", "arf", "tp", "preburst", "il", "manual_data"]
        tab = tab if tab in tabs else None
        all_tabs = False if tab is not None else True

        # --- Required Settings tab ---
        if all_tabs or (tab == "req_set" and all_tabs is False):
            # Catchments table - reset to empty
            self.inputs_catchments_table.setRowCount(0)
            # Outlet Location - reset switched off and params to default
            self.outlet_location_checkbox.setChecked(False)
            self.outlet_location_method_combobox.setCurrentIndex(0)
            self.outlet_location_lat_long_lat_spinbox.setValue(0.0)
            self.outlet_location_lat_long_long_spinbox.setValue(0.0)
            # Output
            self.output_location_outfolder_line.clear()
            self.output_options_format_combobox.setCurrentIndex(0)
            # IFD
            self.ifd_baseline_year_combobox.setCurrentIndex(0)
            # Event selection
            self.aep_checkbox_select_all.setChecked(False)
            for checkbox in self._aep_checkboxes():
                checkbox.setChecked(False)
            self.dur_checkbox_select_all.setChecked(False)
            for checkbox in self._duration_checkboxes():
                checkbox.setChecked(False)

        # --- Climate Change tab ---
        if all_tabs or (tab == "cc" and all_tabs is False):
            self.climate_change_table.setRowCount(0)
            self.climate_change_scale_storm_radio_button.setChecked(True)

        # --- ARF tab ---
        if all_tabs or (tab == "arf" and all_tabs is False):
            self.arf_calculate_area_radio_button.setChecked(True)
            self.arf_user_area_spinbox.setValue(0.0)
            self.arf_min_arf_value_spinbox.setValue(0.0)
            self.arf_for_events_checkbox.setChecked(False)
            self.arf_manual_specify_block.setChecked(False)
            self.arf_manual_specify_spinbox.setValue(0.0)

        # --- Temporal Patterns tab ---
        if all_tabs or (tab == "tp" and all_tabs is False):
            self.tp_optional_tps_list_widget.clearSelection()
            self.tp_use_add_point_tps_checkbox.setChecked(False)
            self.tp_use_add_areal_tps_block.setChecked(False)
            self.tp_use_add_areal_tps_no_spinbox.setValue(0)

        # --- Preburst tab ---
        if all_tabs or (tab == "preburst" and all_tabs is False):
            self.preburst_pattern_method_combobox.setCurrentIndex(0)
            self.preburst_rec_controls_complete_storm_checkbox.setChecked(False)
            self.preburst_percentile_combobox.setCurrentIndex(0)
            self.preburst_constant_controls_complete_storm_checkbox.setChecked(False)
            self.preburst_constant_controls_prop_controls_checkbox.setChecked(False)
            self.preburst_constant_controls_preburst_dur_value_spinbox.setValue(2.0)
            self.preburst_constant_controls_prop_value_spinbox.setValue(2.0)
            self.preburst_constant_controls_prop_max_dur_value_spinbox.setValue(6.0)
            self.preburst_tp_controls_complete_storm_checkbox.setChecked(False)
            self.preburst_tp_controls_tp_combobox.setCurrentIndex(0)
            self.preburst_tp_controls_prop_controls_checkbox.setChecked(False)
            self.preburst_tp_controls_preburst_dur_value_spinbox.setValue(2.0)
            self.preburst_tp_controls_prop_value_spinbox.setValue(2.0)
            self.preburst_tp_controls_prop_max_dur_value_spinbox.setValue(6.0)
            self.preburst_none_controls_complete_storm_checkbox.setChecked(False)

        # --- Initial Loss tab ---
        if all_tabs or (tab == "il" and all_tabs is False):
            self.il_burst_il_rec_radio_button.setChecked(True)
            self.il_short_dur_extrapolation_method_combobox.setCurrentIndex(5)  # "Constant pre-burst ratio (default)"
            self.il_shor_dur_mar_value_spinbox.setValue(0.0)
            self.il_shor_dur_static_value_spinbox.setValue(0.0)
            self.il_tuflow_loss_method_combobox.setCurrentIndex(0)
            self.il_tuflow_loss_method_infil_ilcl_block.setChecked(False)
            self.il_tuflow_loss_method_infil_il_spinbox.setValue(0.0)
            self.il_tuflow_loss_method_infil_cl_spinbox.setValue(0.0)
            self.il_user_overrides_il_checkbox.setChecked(False)
            self.il_user_overrides_il_spinbox.setValue(0.0)
            self.il_user_overrides_cl_checkbox.setChecked(False)
            self.il_user_overrides_cl_spinbox.setValue(0.0)

        # --- Manually Specified Data tab ---
        if all_tabs or (tab == "manual_data" and all_tabs is False):
            self.offline_mode_json_line_edit.clear()
            self.tp_manual_point_tp_file_path_line.clear()
            self.tp_manual_areal_tp_file_path_line.clear()

        # Re-run the conditional slots once so the dock's enabled/visible state matches the defaults just set above
        self._init_conditional_state()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, message: str, level: str = 'info') -> None:
        """Appends a line to ``log_text_edit``.

        Plain text is used for 'info' level messages. 'error' messages are shown in red,
        'warning' messages are shown in orange, and 'debug' messages (pytuflow's own
        verbose logging - see :meth:`_on_run_clicked`/:class:`_PytuflowLogBridge`) are
        shown in grey.
        ``log_block`` is automatically expanded on an error.

        :param message: the message to log.
        :param level: one of ``'debug'``, ``'info'``, ``'warning'`` or ``'error'``.
        """

        prefix = level.upper()
        line = f'{prefix}: {message}'

        if level == 'error':
            self.log_text_edit.append(f'<span style="color:red;">{html.escape(line)}</span>')
            self.log_block.setCollapsed(False)
        elif level == 'warning':
            self.log_text_edit.append(f'<span style="color:orange;">{html.escape(line)}</span>')
        elif level == 'debug':
            self.log_text_edit.append(f'<span style="color:grey;">{html.escape(line)}</span>')
        else:
            self.log_text_edit.append(line)

        scrollbar = self.log_text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _log_info(self, message: str) -> None:
        """Logs an info message to ``log_text_edit`` (plain text)."""

        self._log(message, level='info')

    def _log_warning(self, message: str) -> None:
        """Logs a warning message to ``log_text_edit`` (orange text) - used for
        unusual/unexpected configurations that don't stop the run."""

        self._log(message, level='warning')

    def _log_error(self, message: str) -> None:
        """Logs an error message to ``log_text_edit`` (red text), expandings
        ``log_block`` - used for errors that stop the run."""

        self._log(message, level='error')

    # ------------------------------------------------------------------
    # pytuflow verbose logging bridge
    # ------------------------------------------------------------------

    def _install_pytuflow_log_bridge(self, log_signal) -> logging.Logger:
        """Attaches a :class:`_PytuflowLogBridge` handler to the ``'pytuflow'`` logger
        so its log messages are forwarded to ``log_signal`` (``ArrRunWorker.log_message`` -
        connected to :meth:`_log`) while a run is in progress. If
        ``pytuflow_verbose_logging_checkbox`` is checked, the logger's level is
        (temporarily) lowered to ``DEBUG`` so pytuflow's verbose logging is included too
        - otherwise only its normal ``INFO``/``WARNING``/``ERROR`` messages are forwarded.
        Returns the logger, so the caller can restore its previous level/remove the handler afterwards (see
        :meth:`_uninstall_pytuflow_log_bridge`)."""

        pytuflow_logger = logging.getLogger(_PYTUFLOW_LOGGER_NAME)
        self._pytuflow_log_handler = _PytuflowLogBridge(log_signal)
        self._pytuflow_log_previous_level = pytuflow_logger.level
        if self.pytuflow_verbose_logging_checkbox.isChecked():
            pytuflow_logger.setLevel(logging.DEBUG)
        pytuflow_logger.addHandler(self._pytuflow_log_handler)
        return pytuflow_logger

    def _uninstall_pytuflow_log_bridge(self, pytuflow_logger: logging.Logger) -> None:
        """Undoes :meth:`_install_pytuflow_log_bridge` - removes the forwarding handler
        and restores the ``'pytuflow'`` logger's previous level, so a run with verbose
        logging enabled doesn't leave pytuflow logging at ``DEBUG`` level globally
        once the run has finished."""

        pytuflow_logger.removeHandler(self._pytuflow_log_handler)
        pytuflow_logger.setLevel(self._pytuflow_log_previous_level)

    # ------------------------------------------------------------------
    # Progress bar
    # ------------------------------------------------------------------

    def _on_build_progress(self, total_steps: int) -> None:
        """Marks the json config generation step (the *first* step of ``bottom_status_block_progress_bar``) as complete,
        once :meth:`generate_pytuflow_json.GenerateARRjson.build_json_multiple` has finished.

        :param total_steps: total number of steps for this run - 1 (json config generation)
            plus one per catchment that will be run through pytuflow.
        """

        percent = int(round((1 / total_steps) * 100)) if total_steps else 0
        self.bottom_status_block_progress_bar.setValue(percent)
        # Force the progress bar to repaint immediately
        QApplication.processEvents()

    @staticmethod
    def _set_exclusive_visible(widget_to_show: QWidget, *all_widgets: QWidget) -> None:
        """Shows ``widget_to_show`` and hides every other widget in ``all_widgets``.
        Used for groups of widgets where exactly one should be visible at a time."""

        for widget in all_widgets:
            widget.setVisible(widget is widget_to_show)

    # ------------------------------------------------------------------
    # Inputs: catchments table
    # ------------------------------------------------------------------

    def _on_catchments_add_clicked(self) -> None:
        """``inputs_catchments_add_tool_button``: adds a new catchment row to
        ``inputs_catchments_table``."""

        self.inputs_catchments_table.add_catchment()

    def _on_catchments_subtract_clicked(self) -> None:
        """``inputs_catchments_subtract_tool_button``: removes the currently selected catchment
        row (if any) from ``inputs_catchments_table``."""

        self.inputs_catchments_table.remove_selected_catchment()

    def _on_catchments_clear_table_clicked(self) -> None:
        """``inputs_catchments_clear_table_tool_button``: removes every row (catchment) from
        ``inputs_catchments_table``."""

        self.inputs_catchments_table.setRowCount(0)

    # ------------------------------------------------------------------
    # Inputs: bulk-populate catchments table from a GIS layer
    # ------------------------------------------------------------------

    def _refresh_bulk_pop_catchments_layer_combobox(self, *args) -> None:
        """Refreshes ``bulk_pop_catchments_gis_layer_combobox`` with every polygon ("region")
        vector layer currently loaded in the QGIS project, preserving the current selection if
        it's still valid."""

        combobox = self.bulk_pop_catchments_gis_layer_combobox
        layers = (
            (layer_toc, layer_id, tuflowqgis_find_layer(layer_id, search_type='layerid'))
            for layer_toc, layer_id in findAllVectorLyrsWithGroups()
        )
        populate_layer_combobox(combobox, layers, is_polygon_layer)
        self._on_bulk_pop_catchments_layer_changed()

    def _on_bulk_pop_catchments_layer_changed(self, *args) -> None:
        """``bulk_pop_catchments_gis_layer_combobox``: (re)populates
        ``bulk_pop_catchments_site_id_combobox`` with every field name of the newly selected
        layer."""

        combobox = self.bulk_pop_catchments_site_id_combobox
        combobox.blockSignals(True)
        try:
            combobox.clear()
            layer_id = self.bulk_pop_catchments_gis_layer_combobox.currentData(_LAYER_ID_ROLE)
            if layer_id:
                layer = tuflowqgis_find_layer(layer_id, search_type='layerid')
                if layer is not None:
                    combobox.addItems([field.name() for field in layer.fields()])
        finally:
            combobox.blockSignals(False)

    def _existing_catchment_gis_selections(self) -> set[tuple[str, int]]:
        """Returns a set of ``(layer_id, feature_id)`` pairs for every row currently in
        ``inputs_catchments_table`` whose "Catchment Method" is "GIS Layer"
        Used by :meth:`_on_bulk_pop_catchments_populate_clicked` to avoid duplicate rows."""

        table = self.inputs_catchments_table
        existing = set()
        for row in range(table.rowCount()):
            if table.catchment_method(row) != catchments_table.CATCHMENT_METHOD_GIS:
                continue
            catchment = table.catchment_location(row)
            layer = catchment.get("layer")
            feature_id = catchment.get("feature_id")
            if layer is not None and feature_id is not None:
                existing.add((layer.id(), feature_id))
        return existing

    def _on_bulk_pop_catchments_populate_clicked(self) -> None:
        """``bulk_pop_catchments_populate_tool_button``: adds one new row per feature of the
        polygon layer currently selected in ``bulk_pop_catchments_gis_layer_combobox`` to
        ``inputs_catchments_table``, each new row's "Catchment Location" set to that feature (GIS method)
        and its "Name" taken from the field currently selected in ``bulk_pop_catchments_site_id_combobox``.

        Features already represented by an existing "GIS Layer" row in the table
        (see :meth:`_existing_catchment_gis_selections`) are skipped rather than added again as duplicates.
        Existing "Latitude/Longitude" rows are not checked against/considered duplicates."""

        layer_id = self.bulk_pop_catchments_gis_layer_combobox.currentData(_LAYER_ID_ROLE)
        if not layer_id:
            self._log_warning("No GIS layer selected to bulk populate the catchments table from.")
            return

        layer = tuflowqgis_find_layer(layer_id, search_type='layerid')
        if layer is None:
            self._log_warning("Selected GIS layer could not be found. Cannot bulk populate the catchments table.")
            return

        site_id_field = self.bulk_pop_catchments_site_id_combobox.currentText()
        existing_selections = self._existing_catchment_gis_selections()

        feature_count = 0
        duplicates = []
        for feature in layer.getFeatures():
            if (layer_id, feature.id()) in existing_selections:
                duplicates.append(feature.id())
                continue

            row = self.inputs_catchments_table.add_catchment()
            if site_id_field:
                name = feature[site_id_field]
                if name is not None and str(name).strip():
                    self.inputs_catchments_table.set_catchment_name(row, str(name))
            self.inputs_catchments_table.set_catchment_method(row, catchments_table.CATCHMENT_METHOD_GIS)
            self.inputs_catchments_table.set_catchment_gis_selection(row, layer_id, feature.id())
            feature_count += 1

        if feature_count == 0 and duplicates == []:
            self._log_warning(f"Selected layer '{layer.name()}' has no features to populate the catchments table from.")
        else:
            message = f"Added {feature_count} catchment(s) to the catchments table from layer '{layer.name()}'."
            num_duplicates = len(duplicates)
            if num_duplicates > 0:
                message += f" Skipped {num_duplicates} catchment(s) already present in the table: \n {', \n'.join(map(str, duplicates))}."
            self._log_info(message)

    # ------------------------------------------------------------------
    # Inputs: outlet location method/GIS layer/feature selection
    # ------------------------------------------------------------------

    def _on_outlet_location_checkbox_toggled(self, checked: bool) -> None:
        """``outlet_location_checkbox``: global on/off switch for specifying a catchment
        outlet location. When unchecked, the entire ``outlet_location_widget`` (method
        combobox, GIS layer/feature selection and latitude/longitude controls) is disabled.
        When checked, it's enabled again."""

        self.outlet_location_widget.setEnabled(checked)

    def _on_outlet_location_method_changed(self, index: int) -> None:
        """``outlet_location_method_combobox``:
            0 = GIS point layer,
            1 = Latitude/longitude.
        ``outlet_location_gis_layer_widget``/``outlet_location_lat_long_widget`` are only shown
        for the corresponding method."""

        self.outlet_location_gis_layer_widget.setVisible(index == 0)
        self.outlet_location_lat_long_widget.setVisible(index == 1)

    def _refresh_outlet_location_layer_combobox(self, *args) -> None:
        """Refreshes ``outlet_location_gis_layer_combobox`` with every point vector layer
        currently loaded in the QGIS project, preserving the current selection if it's still
        valid."""

        combobox = self.outlet_location_gis_layer_combobox
        layers = (
            (layer_toc, layer_id, tuflowqgis_find_layer(layer_id, search_type='layerid'))
            for layer_toc, layer_id in findAllVectorLyrsWithGroups()
        )
        populate_layer_combobox(combobox, layers, is_point_layer)
        self._on_outlet_location_layer_changed()

    def _outlet_location_selected_layer(self):
        """Returns the ``QgsVectorLayer`` currently selected in ``outlet_location_gis_layer_combobox``,
        or ``None`` if nothing valid is selected."""

        layer_id = self.outlet_location_gis_layer_combobox.currentData(_LAYER_ID_ROLE)
        if not layer_id:
            return None
        return tuflowqgis_find_layer(layer_id, search_type='layerid')

    def _on_outlet_location_layer_changed(self, *args) -> None:
        """``outlet_location_gis_layer_combobox``: (re)populates
        ``outlet_location_gis_layer_feature_combobox`` with every feature of the newly selected
        layer, labelled by its ``';'``-separated attribute values (see
        ``arr_shared_functionality.feature_label``)."""

        layer = self._outlet_location_selected_layer()
        populate_feature_combobox(
            self.outlet_location_gis_layer_feature_combobox,
            layer.getFeatures() if layer is not None else (),
        )

    def _watch_outlet_location_layer_selection(self, layer) -> None:
        """(Dis)connects ``selectionChanged`` on the GIS point layer being watched for
        :meth:`_on_outlet_location_select_feature_clicked`'s "select features" map tool, so only
        the most-recently activated layer's selection is tracked."""

        if self._outlet_location_watched_layer is not None:
            try:
                self._outlet_location_watched_layer.selectionChanged.disconnect(
                    self._on_outlet_location_feature_selection_changed)
            except (TypeError, RuntimeError):
                pass
        self._outlet_location_watched_layer = layer
        if layer is not None:
            layer.selectionChanged.connect(self._on_outlet_location_feature_selection_changed)

    def _on_outlet_location_select_feature_clicked(self) -> None:
        """``outlet_location_gis_layer_feature_select_tool_button``: activates QGIS's native
        "select features" map tool for the layer currently selected in
        ``outlet_location_gis_layer_combobox``, so the user can click/drag on the canvas to
        choose the outlet point feature instead of using ``outlet_location_gis_layer_feature_combobox``
        directly. The newly selected feature (if any) is reflected back into that combobox - see
        :meth:`_on_outlet_location_feature_selection_changed`."""

        layer = self._outlet_location_selected_layer()
        if layer is None:
            self._log_warning("No GIS point layer selected to select a feature from.")
            return

        self._watch_outlet_location_layer_selection(layer)
        self.iface.setActiveLayer(layer)
        self.iface.actionSelectRectangle().trigger()

    def _on_outlet_location_feature_selection_changed(self, *args) -> None:
        """``QgsVectorLayer.selectionChanged`` (connected in
        :meth:`_watch_outlet_location_layer_selection`): updates
        ``outlet_location_gis_layer_feature_combobox`` to match the layer's newly selected
        feature, if exactly one feature is currently selected."""

        layer = self.sender()
        if layer is None:
            return
        selected_ids = layer.selectedFeatureIds()
        if len(selected_ids) != 1:
            return
        index = self.outlet_location_gis_layer_feature_combobox.findData(selected_ids[0])
        if index >= 0:
            self.outlet_location_gis_layer_feature_combobox.setCurrentIndex(index)

    def _on_catchment_layers_added(self, layers) -> None:
        """``QgsProject.instance().legendLayersAdded``: refreshes every row's GIS layer
        comboboxes in ``inputs_catchments_table`` whenever a vector layer is added to the
        workspace, and watches new layers for renames/data source changes."""

        refresh = False
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                refresh = True
            layer.nameChanged.connect(self._refresh_catchment_layer_comboboxes)
            layer.dataSourceChanged.connect(self._refresh_catchment_layer_comboboxes)
        if refresh:
            self._refresh_catchment_layer_comboboxes()

    def _on_catchment_layers_removed(self, layer_ids) -> None:
        """``QgsProject.instance().layersRemoved``: refreshes every row's GIS layer comboboxes
        in ``inputs_catchments_table`` whenever any layer is removed from the workspace."""

        self._refresh_catchment_layer_comboboxes()

    def _on_catchment_project_read(self, *args) -> None:
        """``QgsProject.instance().readProject``: refreshes every row's GIS layer comboboxes in
        ``inputs_catchments_table`` when a new project is opened, and (re)watches every layer
        for renames/data source changes."""

        self._refresh_catchment_layer_comboboxes()
        for layer in QgsProject.instance().mapLayers().values():
            layer.nameChanged.connect(self._refresh_catchment_layer_comboboxes)
            layer.dataSourceChanged.connect(self._refresh_catchment_layer_comboboxes)

    def _refresh_catchment_layer_comboboxes(self, *args) -> None:
        """Refreshes every row's "Catchment Location"/"Outlet Location" GIS layer comboboxes in
        ``inputs_catchments_table``, as well as ``bulk_pop_catchments_gis_layer_combobox`` and
        ``outlet_location_gis_layer_combobox``, to match the QGIS project's currently loaded
        layers."""

        self.inputs_catchments_table.refresh_layer_comboboxes()
        self._refresh_bulk_pop_catchments_layer_combobox()
        self._refresh_outlet_location_layer_combobox()

    def _on_arf_method_changed(self) -> None:
        """ARF area radio buttons: the user-area spinbox/units are only relevant when
        "User Area" is selected rather than "Calculate area"."""

        use_user_area = self.arf_user_area_radio_button.isChecked()
        self.arf_user_area_spinbox.setEnabled(use_user_area)
        self.arf_user_area_units_label.setEnabled(use_user_area)

    def _on_arf_manual_override_toggled(self, checked: bool) -> None:
        """``arf_manual_specify_block``: when checked, a manually specified ARF value
        is used directly instead of being calculated.
        The inputs that only affect the  automatic calculation (``arf_min_arf_value_spinbox`` and
        ``arf_for_events_checkbox``) are greyed out."""

        self.arf_min_arf_value_label.setEnabled(not checked)
        self.arf_min_arf_value_spinbox.setEnabled(not checked)
        self.arf_for_events_checkbox.setEnabled(not checked)

    def _on_offline_mode_json_browse_clicked(self) -> None:
        """``offline_mode_json_tool_button``:
        opens a file browser to load a previously saved ARR data hub response .json file and
        stores the selected path (as a string) in the corresponding line edit
        (``offline_mode_json_line_edit``)."""

        line_edit = self.offline_mode_json_line_edit
        current = self.offline_mode_json_line_edit.text()
        start_dir = current if current and Path(current).is_file() else self._project_folder()
        path, _ = QFileDialog.getOpenFileName(
            self, 'ARR Data Hub response .json', start_dir, _RESPONSE_JSON_FILE_FILTER)
        if not path:
            return

        line_edit.setText(path)

    def _on_config_json_browse_clicked(self) -> None:
        """``req_set_pop_from_json_file_tool_button``:
        opens a multi-select "open file" browser (``QFileDialog.getOpenFileNames``) to select one
        or more existing configuration .json files, then stores the single "main" config's path in
        ``req_set_pop_from_json_line_edit``.

        If a single file is selected, it's used directly.
        If more than one is selected, each is parsed and checked using
        :func:`arr_shared_functionality.is_main_config_candidate` to guess which one is the "main" config:
            - exactly one candidate -> that file is used automatically;
            - more than one candidate -> :class:`main_config_select_dlg.MainConfigSelectDialog` is
              shown so the user can choose which one to use;
            - no candidates -> the first selected file is used as a fallback, with a warning logged.

        Only the chosen "main" config's path ends up in ``req_set_pop_from_json_line_edit``.
        The other selected files are stashed in memory to be used if reload buttons are pressed to
        populate the catchments table. The stash is cleared if the user then hand edits the line edit (see
        :meth:`_on_config_json_line_edit_hand_edited`).

        Once the path is set, the whole dock is automatically (re)populated from it, as if
        ``req_set_pop_from_json_refresh_tool_button`` had been clicked.
        """

        line_edit = self.req_set_pop_from_json_line_edit
        current_path = line_edit.text().strip()
        start_dir = current_path if current_path else self._project_folder()

        paths, _ = QFileDialog.getOpenFileNames(
            self, 'Configuration .json file(s)', start_dir, _CONFIG_JSON_FILE_FILTER)
        if not paths:
            return

        if len(paths) == 1:
            self._pending_catchment_jsons = []
            self._pending_catchment_jsons_main_path = None
            line_edit.setText(paths[0])
            self._on_json_refresh_button_clicked()
            return

        # More than one file selected - parse every one up front.
        parsed: dict[str, dict] = {}
        for path in paths:
            try:
                with open(path, 'r') as f:
                    parsed[path] = json.load(f)
            except Exception as e:
                self._log_warning(f"Could not parse '{path}' as json: {e}. Skipping.")

        if not parsed:
            self._log_error("None of the selected files could be parsed. Nothing loaded.")
            return

        candidates = [path for path, json_data in parsed.items() if is_main_config_candidate(json_data)]

        if len(candidates) == 1:
            chosen_path = candidates[0]
            self._log_info(f"Auto-detected '{chosen_path}' as the main configuration file.")
        elif len(candidates) > 1:
            chosen_path = MainConfigSelectDialog.get_main_config_path(candidates, parent=self)
            if chosen_path is None:
                self._log_info("Main configuration selection cancelled.")
                return
        else:
            chosen_path = next(iter(parsed))
            self._log_warning(
                "Could not confidently detect a 'main' configuration file among the selected "
                f"files. Defaulting to '{chosen_path}'.")

        others = [json_data for path, json_data in parsed.items() if path != chosen_path]
        self._pending_catchment_jsons = others
        self._pending_catchment_jsons_main_path = chosen_path
        if others:
            self._log_info(
                f"Stashed {len(others)} additional catchment(s) from the selected files.")

        line_edit.setText(chosen_path)
        self._on_json_refresh_button_clicked()

    def _on_config_json_line_edit_hand_edited(self, text: str) -> None:
        """``req_set_pop_from_json_line_edit.textEdited``
        Only executes on user typing, not a programmatic ``setText`` call (file browse).
        Discards any catchment json(s) stashed from a previous multi-file browse."""

        if self._pending_catchment_jsons:
            self._pending_catchment_jsons = []
            self._pending_catchment_jsons_main_path = None
            self._log_info(
                "Configuration path edited - clearing any stashed catchment(s).")

    def _on_config_json_line_edit_editing_finished(self) -> None:
        """``req_set_pop_from_json_line_edit.editingFinished``: fires when the user finishes
        hand editing/pasting the path (presses Enter or the line edit loses focus).
        If the (changed) text points to an existing file, the whole dock is automatically
        (re)populated from it, as if ``req_set_pop_from_json_refresh_tool_button`` had been
        clicked."""

        path = self.req_set_pop_from_json_line_edit.text().strip()
        if not path or path == self._last_auto_populated_config_path:
            return
        if not Path(path).is_file():
            return
        self._on_json_refresh_button_clicked()

    def _load_main_config_json(self) -> Optional[dict]:
        """Loads and returns the json config currently listed in ``req_set_pop_from_json_line_edit``,
        or ``None`` (with an error logged) if no path is specified or it can't be parsed."""

        path = self.req_set_pop_from_json_line_edit.text().strip()
        if not path:
            self._log_warning("No configuration .json file specified.")
            return None
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self._log_error(f"Could not load configuration .json file '{path}': {e}")
            return None

    def _catchment_jsons_for_load(self, main_json: dict) -> list[dict]:
        """Returns the full ordered list of catchment json configs to populate
        ``inputs_catchments_table`` from. ``main_json`` plus any stashed catchment(s) from the
        last multi-file browse, if that stash is still valid for the path currently in
        ``req_set_pop_from_json_line_edit``."""

        current_path = self.req_set_pop_from_json_line_edit.text().strip()
        stash_valid = (
            bool(self._pending_catchment_jsons)
            and self._pending_catchment_jsons_main_path == current_path
        )
        if stash_valid:
            return [main_json] + self._pending_catchment_jsons
        return [main_json]

    def _on_json_refresh_button_clicked(self) -> None:
        """``req_set_pop_from_json_refresh_tool_button`` ("Load from disk..."):
        (re)populates the whole dock from the "main" configuration .json file currently listed in
        ``req_set_pop_from_json_line_edit``, then (re)populates ``inputs_catchments_table`` from
        that main config plus any catchment(s) stashed in memory from a previous
        multi-file browse (see :meth:`_catchment_jsons_for_load`)."""

        main_json = self._load_main_config_json()
        if main_json is None:
            return

        self._last_auto_populated_config_path = self.req_set_pop_from_json_line_edit.text().strip()

        # Collect catchments from json
        catchment_jsons = self._catchment_jsons_for_load(main_json)
        multi_catchment = len(catchment_jsons) > 1

        # Reset dock back to default values before populating the dock from json
        self.reset_dock_to_defaults()

        # Populate the dock from json
        populator = PopulateARRDockFromjson(parent=self, log=self._log)
        if multi_catchment:
            populator.populate_inputs_multi(catchment_jsons)
        else:
            populator.populate_inputs_single(main_json)

        populator.populate_required_settings(main_json)
        populator.populate_climate_change(main_json)
        populator.populate_arf(main_json, multi_catchment)
        populator.populate_temporal_patterns(main_json)
        populator.populate_preburst(main_json)
        populator.populate_initial_loss(main_json)
        populator.populate_manually_specified_data(main_json)

        self._log_info("Dock population completed.")

    # ------------------------------------------------------------------
    # Save dock state as configuration .json file(s)
    # ------------------------------------------------------------------

    def _on_reload_json_tool_button_clicked(self, tab: str) -> None:
        """Reloads the dock settings on the specified tab (``tab``) from the "main" configuration
        .json file currently listed in ``req_set_pop_from_json_line_edit``, plus any stashed
        catchment(s) (see :meth:`_catchment_jsons_for_load`) if ``tab`` is ``"req_set"``.

        ``tab`` can be one of: "req_set", "cc", "arf", "tp", "preburst", "il" or "manual_data"
        """

        main_json = self._load_main_config_json()
        if main_json is None:
            self._log_warning("No configuration .json specified to reload from.")
            return

        catchment_jsons = self._catchment_jsons_for_load(main_json)
        multi_catchment = len(catchment_jsons) > 1

        # Reset tab back to default values before populating the tab from json
        self.reset_dock_to_defaults(tab=tab)

        # Populate each tab from the main json (or stashed for multi json)
        populator = PopulateARRDockFromjson(parent=self, log=self._log)
        if tab == "req_set":
            if multi_catchment:
                populator.populate_inputs_multi(catchment_jsons)
            else:
                populator.populate_inputs_single(main_json)
            populator.populate_required_settings(main_json)
        elif tab == "cc":
            populator.populate_climate_change(main_json)
        elif tab == "arf":
            populator.populate_arf(main_json, multi_catchment)
        elif tab == "tp":
            populator.populate_temporal_patterns(main_json)
        elif tab == "preburst":
            populator.populate_preburst(main_json)
        elif tab == "il":
            populator.populate_initial_loss(main_json)
        elif tab == "manual_data":
            populator.populate_manually_specified_data(main_json)

    def _on_save_config_json_save_clicked(self) -> None:
        """``save_config_json_save_tool_button`` ("Save to disk..."): opens
        :class:`save_config_dlg.SaveConfigDialog` so the user can choose an output
        location/filename (pattern), then builds and writes the pytuflow ``arr`` json config(s)
        for the dock's current state (see :meth:`_save_config_json`)."""

        catchment_count = self.inputs_catchments_table.rowCount()
        if catchment_count == 0:
            self._log_warning("No catchments configured. Nothing to save.")
            return

        main_path = self.req_set_pop_from_json_line_edit.text().strip() or None
        dlg = SaveConfigDialog(catchment_count=catchment_count, main_path=main_path, parent=self)
        if dlg.exec() != QT_DIALOG_ACCEPTED:
            return

        output_folder = dlg.output_folder()
        filename_pattern = dlg.filename_pattern()
        if not output_folder or not filename_pattern:
            self._log_error("An output location and filename must both be specified. Save cancelled.")
            return

        self._save_config_json(Path(output_folder), filename_pattern)

    def _save_config_json(self, output_folder: Path, filename_pattern: str) -> None:
        """Builds the pytuflow ``arr`` json config(s) from the dock's current state (via
        :meth:`generate_pytuflow_json.GenerateARRjson.build_json_multiple` - this works equally
        well for a single catchment row as for many, see :meth:`_on_run_clicked`) and writes them
        to ``output_folder``, named according to ``filename_pattern`` (see
        :class:`save_config_dlg.SaveConfigDialog`).

        If there's a single catchment row, exactly one .json file is written, named
        ``filename_pattern`` (with .json extension added if not already present).

        If there's more than one, one .json file per catchment is written: using
        ``${name}``/``${enum}`` substitution if ``filename_pattern`` contains either placeholder,
        otherwise falling back to appending each catchment's (sanitised) name to
        ``filename_pattern`` (see :func:`arr_shared_functionality.write_json_configs`).
        """

        try:
            generator = GenerateARRjson(self, log=self._log)
            result = generator.build_json_multiple()
            configs = result['configs']
            if not configs:
                self._log_error("No valid catchment configuration(s) could be built. Nothing saved.")
                return

            has_placeholder = '${name}' in filename_pattern or '${enum}' in filename_pattern
            name_prefix = Path(filename_pattern).stem or 'generated_input'

            if len(configs) == 1:
                planned_paths = [
                    output_folder / resolve_config_filename(filename_pattern, configs[0].get('site_name', ''), 1)
                ]
            elif has_placeholder:
                planned_paths = [
                    output_folder / resolve_config_filename(filename_pattern, entry.get('site_name', ''), index)
                    for index, entry in enumerate(configs, start=1)
                ]
            else:
                planned_paths = [
                    output_folder / f"{name_prefix}_{sanitise_filename_part(entry.get('site_name'))}.json"
                    for entry in configs
                ]

            existing = [p for p in planned_paths if p.is_file()]
            if existing:
                names = '\n'.join(f"  - '{p}'" for p in existing)
                answer = QMessageBox.question(
                    self, 'Save Configuration .json',
                    f"The following file(s) already exist:\n{names}\n\nDo you want to replace them?",
                    QT_MESSAGE_BOX_YES | QT_MESSAGE_BOX_NO, QT_MESSAGE_BOX_NO)
                if answer != QT_MESSAGE_BOX_YES:
                    self._log_info("Save cancelled.")
                    return

            if len(configs) == 1:
                out_path = write_json_config(planned_paths[0], configs[0]['json'])
                self._log_info(f"Saved configuration .json to '{out_path}'.")
            else:
                out_paths = write_json_configs(
                    output_folder, configs, name_prefix=name_prefix,
                    name_pattern=filename_pattern if has_placeholder else None)
                for out_path in out_paths:
                    self._log_info(f"Saved configuration .json to '{out_path}'.")

            if result['errors']:
                summary = '\n'.join(
                    f"  - '{error['catchment']}': {error['error']}" for error in result['errors'])
                self._log_warning(
                    f"{len(result['errors'])} catchment(s) were skipped while saving:\n{summary}")
        except Exception as e:
            self._log_error(f"Failed to save configuration .json: {e}")


    def _on_tp_file_browse_clicked(self) -> None:
        """``tp_manual_point_tp_file_tool_button`` or ``tp_manual_areal_tp_file_tool_button``:
        opens a file browser to load a manually specified temporal pattern file (``.csv``) and
        stores the selected path (as a string) in the corresponding line edit
        (``tp_manual_point_tp_file_path_line`` / ``tp_manual_areal_tp_file_path_line``),
        depending on which tool button triggered the slot."""

        if self.sender() is self.tp_manual_areal_tp_file_tool_button:
            line_edit = self.tp_manual_areal_tp_file_path_line
        else:
            line_edit = self.tp_manual_point_tp_file_path_line

        current = line_edit.text()
        start_dir = current if current and Path(current).is_file() else self._project_folder()
        path, _ = QFileDialog.getOpenFileName(
            self, 'Temporal Pattern File', start_dir, _TP_FILE_FILTER)
        if not path:
            return

        line_edit.setText(path)

    def _on_preburst_method_changed(self, index: int) -> None:
        """``preburst_pattern_method_combobox``:
            0 = Recommended,
            1 = Constant,
            2 = Temporal pattern,
            3 = None
        Exactly one of the four control panels below the combobox is shown at a time."""

        panels = (
            self.preburst_rec_controls_widget,
            self.preburst_constant_controls_widget,
            self.preburst_tp_controls_widget,
            self.preburst_none_controls_widget,
        )
        if 0 <= index < len(panels):
            self._set_exclusive_visible(panels[index], *panels)

    def _on_preburst_constant_prop_toggled(self, checked: bool) -> None:
        """``preburst_constant_controls_prop_controls_checkbox``: toggles between a
        fixed preburst duration and a duration proportional to the storm duration
        (with a max duration cap)."""

        self.preburst_constant_controls_preburst_dur_widget.setVisible(not checked)
        self.preburst_constant_controls_prop_widget.setVisible(checked)

    def _on_preburst_tp_prop_toggled(self, checked: bool) -> None:
        """As :meth:`_on_preburst_constant_prop_toggled`, for the "Temporal pattern"
        preburst method's own duration controls."""

        self.preburst_tp_controls_preburst_dur_widget.setVisible(not checked)
        self.preburst_tp_controls_prop_widget.setVisible(checked)

    def _on_il_short_dur_method_changed(self, index: int) -> None:
        """``il_short_dur_extrapolation_method_combobox``:
            - the MAR field is only relevant for the Rahman/Hill methods (indices 7, 8);
            - the static loss field is only relevant for the "Static value" method (index 9)."""

        self.il_shor_dur_mar_value_spinbox.setVisible(index == 7)
        self.il_shor_dur_mar_label.setVisible(index == 7)
        self.il_shor_dur_static_value_spinbox.setVisible(index == 8)
        self.il_shor_dur_static_label.setVisible(index == 8)

    def _on_il_loss_method_changed(self, index: int) -> None:
        """``il_tuflow_loss_method_combobox``:
            0 = Infiltration (soil file),
            1 = Rainfall excess (material file).
        The fixed impervious/urban area ILCL block only applies to the infiltration method."""

        is_excess = index == 1
        self.il_tuflow_loss_method_infil_ilcl_block.setVisible(is_excess)
        if not is_excess:
            self.il_tuflow_loss_method_infil_ilcl_block.setChecked(False)

    # ------------------------------------------------------------------
    # Event selection: AEP / duration checkbox lists
    # ------------------------------------------------------------------

    def _aep_checkboxes(self) -> list[QCheckBox]:
        """Collects every individual AEP checkbox in ``aep_selection_block`` (i.e. excluding
        ``aep_checkbox_select_all`` itself)."""

        return [
            checkbox for checkbox in self.aep_selection_block.findChildren(QCheckBox)
            if checkbox is not self.aep_checkbox_select_all
        ]

    def _duration_checkboxes(self) -> list[QCheckBox]:
        """As :meth:`_aep_checkboxes`, for ``duration_selection_block``."""

        return [
            checkbox for checkbox in self.duration_selection_block.findChildren(QCheckBox)
            if checkbox is not self.dur_checkbox_select_all
        ]

    @staticmethod
    def _set_checkboxes_checked(checkboxes: list[QCheckBox], checked: bool) -> None:
        """Sets every checkbox in ``checkboxes`` to ``checked``, blocking signals so
        this doesn't recursively trigger each checkbox's own toggled slot (if any)."""

        for checkbox in checkboxes:
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(False)

    def _on_aep_select_all_toggled(self, checked: bool) -> None:
        """``aep_checkbox_select_all``: checks/unchecks every other checkbox in
        ``aep_selection_block`` to match. Changes made to individual AEP checkboxes are
        left untouched (i.e. this is one-directional - unchecking an individual AEP
        checkbox does not uncheck "Select all")."""

        self._set_checkboxes_checked(self._aep_checkboxes(), checked)

    def _on_duration_select_all_toggled(self, checked: bool) -> None:
        """As :meth:`_on_aep_select_all_toggled`, for ``duration_selection_block``."""

        self._set_checkboxes_checked(self._duration_checkboxes(), checked)

    # ------------------------------------------------------------------
    # Climate change scenario table
    # ------------------------------------------------------------------

    def _on_climate_change_add_clicked(self) -> None:
        """``climate_change_add_tool_button``: adds a new scenario row to ``climate_change_table``."""

        self.climate_change_table.add_scenario()

    def _on_climate_change_subtract_clicked(self) -> None:
        """``climate_change_subtract_tool_button``:
        removes the currently selected row (if any) from ``climate_change_table``."""

        self.climate_change_table.remove_selected_scenario()

    def _update_climate_change_names_output(self, *args) -> None:
        """Refreshes ``climate_change_names_output`` with the current list of scenario names
        generated from ``climate_change_table`` (one per line).
        Connected to the table's underlying model so it stays in sync whenever a row is added,
        removed, or a cell's Year/SSP value changes."""

        names = self.climate_change_table.scenario_names()
        self.climate_change_names_output.setPlainText('\n'.join(names))

    # ------------------------------------------------------------------
    # Outputs: output location folder browse
    # ------------------------------------------------------------------

    @staticmethod
    def _project_folder() -> str:
        """Returns the current TUFLOW project folder, read from the same ``QgsProject``
        ``'tuflow'``/``'project/folder'`` entry used elsewhere in the plugin,
        or ``''`` if no TUFLOW project folder has been configured."""

        folder, _ = QgsProject.instance().readEntry('tuflow', 'project/folder', '')
        return folder

    def _on_output_location_browse_clicked(self) -> None:
        """``output_location_file_button``: opens a folder browser
            defaulting to the current ``output_location_outfolder_line`` value if it's an existing folder,
            otherwise the current QGIS project's folder
        Populates ``output_location_outfolder_line`` with the selected folder."""

        current = self.output_location_outfolder_line.text()
        start_dir = current if current and Path(current).is_dir() else self._project_folder()
        path = QFileDialog.getExistingDirectory(self, 'Output Location', start_dir)
        if path:
            self.output_location_outfolder_line.setText(path)

    # ------------------------------------------------------------------
    # Run button
    # ------------------------------------------------------------------

    def _on_run_clicked(self) -> None:
        """``bottom_status_block_run_button``: builds the pytuflow ``arr`` json config(s) from
        the dock's current state (via :class:`GenerateARRjson`) - this needs to happen on the
        GUI thread, since it reads QGIS layers/uses the ``processing`` framework - then hands
        the already-built json/config(s) off to a background :class:`ArrRunWorker` (moved to its
        own ``QThread``, mirroring the worker/thread pattern used elsewhere in this plugin, e.g.
        ``SCS``/``ReFH2``) to perform the network request(s)/engine computation/output writing,
        so a slow ARR Data Hub request or large run doesn't freeze the QGIS GUI. See
        :meth:`_on_run_finished` for completion handling.

        One json config is built (and run) per catchment row currently in
        ``inputs_catchments_table`` (see :meth:`generate_pytuflow_json.GenerateARRjson.build_json_multiple`)
        - this works equally well for a single catchment row as for many.

        ``bottom_status_block_progress_bar`` is split into one step for the *entire* json config generation,
        plus one step per catchment run through pytuflow (see :class:`ArrRunWorker`).
        """

        self.log_text_edit.clear()
        self._log_info('Run started.')
        self.bottom_status_block_progress_bar.setValue(0)
        self.bottom_status_block_ready_label.setText('Running...')
        self.bottom_status_block_run_button.setEnabled(False)

        try:
            # remote debugging
            # todo - remove
            # import pydevd_pycharm
            # pydevd_pycharm.settrace('localhost', port=50000, stdout_to_server=True, stderr_to_server=True)
            generator = GenerateARRjson(self, log=self._log)
            build_result = generator.build_json_multiple()
        except Exception as e:
            self.bottom_status_block_ready_label.setText('Error - see log')
            self._log_error(f'Run failed: {e}')
            self.bottom_status_block_run_button.setEnabled(True)
            return

        # json config generation is 1 step, every remaining step is one catchment run through pytuflow.
        total_steps = 1 + len(build_result['configs'])
        self._on_build_progress(total_steps)

        worker = ArrRunWorker(multiple_catchments=True, build_result=build_result, total_steps=total_steps)
        self._run_worker = worker
        self._run_thread = QThread(self)
        worker.moveToThread(self._run_thread)
        worker.log_message.connect(self._log)
        worker.progress.connect(self.bottom_status_block_progress_bar.setValue)
        worker.finished.connect(self._on_run_finished)
        self._run_thread.started.connect(worker.run)

        self._install_pytuflow_log_bridge(worker.log_message)

        self._run_thread.start()

    def _on_run_finished(self, error_message: str) -> None:
        """``ArrRunWorker.finished``: tears down the background run thread/worker
        started in :meth:`_on_run_clicked`, restores the ``'pytuflow'`` logger's
        previous state (see :meth:`_uninstall_pytuflow_log_bridge`), re-enables the
        run button and updates the progress bar/ready label/log to reflect the
        outcome - an empty ``error_message`` indicates the run succeeded, otherwise
        it's the error that stopped the run (kept solely in the dock's own log
        panel, not a separate message box)."""

        self._uninstall_pytuflow_log_bridge(logging.getLogger(_PYTUFLOW_LOGGER_NAME))

        self._run_thread.quit()
        self._run_thread.wait()
        self._run_thread = None
        self._run_worker = None

        self.bottom_status_block_run_button.setEnabled(True)
        if error_message:
            self.bottom_status_block_ready_label.setText('Error - see log')
            self._log_error(f'Run failed: {error_message}')
        else:
            self.bottom_status_block_progress_bar.setValue(100)
            self.bottom_status_block_ready_label.setText('Finished')
            self._log_info('Finished')
        self._log_info(f'Finished')
