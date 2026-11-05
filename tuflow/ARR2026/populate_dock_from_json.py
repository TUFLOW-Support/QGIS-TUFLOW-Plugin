"""
Populates the arr2026 dock widget with the configuration options defined in an input json file or files.

Any configuration options in the json that are defined incorrectly or not available will be ignored
and the default values will be used like normal.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from qgis.core import QgsProject, QgsVectorLayer

from . import catchments_table
from .climate_change_scenarios import COL_SSP, COL_YEAR
from .arr_shared_functionality import (
    JSON_SECTIONS_EXCLUDE_SITE,
    AEP_MAPPING,
    DURATION_MAPPING,
    LOSS_EXTRAPOLATION_METHOD_MAPPING,
    source_file_path,
)

class PopulateARRDockFromjson:
    """Populates the ARR2026 dock widget from the input .json file(s)."""

    def __init__(
            self, parent=None,
            log: Optional[Callable[[str, str], None]] = None
    ) -> None:
        self.parent = parent
        # Callback used to report messages back to the dock's log panel, invoked as
        # ``log(message, level)`` where ``level`` is one of ``'info'``/``'warning'``/``'error'``
        # (matching ``Arr2026Dock._log``). Defaults to a no-op if not supplied (e.g. in tests).
        self.log = log if log is not None else (lambda message, level='warning': None)
        # The json config currently being applied to the dock - set in :meth:`populate_dock`.
        self.pytuflow_jsons: list[dict] = []

    def _select_or_load_catchment_layer(self, path: str) -> Optional[QgsVectorLayer]:
        """Finds an already-loaded vector layer whose source file matches ``path``, loading it
        as a new layer (and adding it to the QGIS project) if none is found.

        :param path: a ``site.catchment_boundary`` file path from a json config.
        :returns: the matching/newly loaded layer, or ``None`` if ``path`` doesn't exist or
            couldn't be loaded as a valid vector layer.
        """

        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == layer.VectorLayer and source_file_path(layer) == path:
                return layer

        if not Path(path).is_file():
            self.log(f"Catchment boundary file '{path}' could not be found. Skipping catchment layer selection.", level='warning')
            return None

        layer_name = Path(path).stem
        layer = QgsVectorLayer(path, layer_name, 'ogr')
        if not layer.isValid():
            self.log(f"Could not load '{path}' as a vector layer. Skipping catchment layer selection.", level='warning')
            return None

        QgsProject.instance().addMapLayer(layer)
        return layer

    def _populate_catchment_row(self, row: int, json_data: dict) -> None:
        """Populates a single row of ``inputs_catchments_table`` from a json config's ``site``
        section - used by both :meth:`populate_inputs_single` (a single row) and
        :meth:`populate_inputs_multi` (one row per json config)."""

        dock = self.parent
        table = dock.inputs_catchments_table

        site_data = json_data.get("site")
        if site_data is None:
            self.log("Config .json has no 'site' section. Skipping population of this catchment row. Ensure these inputs are set before running the tool.", level='warning')
            return

        name = site_data.get("name") or ""
        table.set_catchment_name(row, name)

        catchment_boundary = site_data.get("catchment_boundary")
        latitude = site_data.get("latitude")
        longitude = site_data.get("longitude")

        if catchment_boundary:
            table.set_catchment_method(row, catchments_table.CATCHMENT_METHOD_GIS)
            layer = self._select_or_load_catchment_layer(catchment_boundary)
            if layer is not None:
                feature = next(layer.getFeatures(), None)
                table.set_catchment_gis_selection(row, layer.id(), feature.id() if feature is not None else None)
        elif latitude is not None and longitude is not None:
            table.set_catchment_method(row, catchments_table.CATCHMENT_METHOD_LAT_LONG)
            table.set_catchment_latlong(row, latitude, longitude)
        else:
            self.log(
                "Config .json 'site' section has neither 'catchment_boundary' nor "
                "'latitude'/'longitude'. Skipping population of this catchment's location. Ensure these inputs are set before running the tool.", level='warning')

    def _populate_outlet_location(self, json_data: dict) -> None:
        """Populates the dock "Outlet Location" controls from the *first* catchment's ``site``
        section ``outlet_latitude``/``outlet_longitude`` values, if present."""

        dock = self.parent
        site_data = json_data.get("site") or {}
        outlet_latitude = site_data.get("outlet_latitude")
        outlet_longitude = site_data.get("outlet_longitude")
        if outlet_latitude is not None and outlet_longitude is not None:
            dock.outlet_location_checkbox.setChecked(True)  # switch on outlet location
            dock.outlet_location_method_combobox.setCurrentIndex(1)  # Latitude/longitude
            dock.outlet_location_lat_long_lat_spinbox.setValue(outlet_latitude)
            dock.outlet_location_lat_long_long_spinbox.setValue(outlet_longitude)

    def populate_inputs_single(self, json_data: dict) -> None:
        """
        Populates the 'inputs' section of the 'Required Settings' tab for a *single* json configuration file input
        (i.e. 1 catchment)."""

        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached. Cannot populate 'Inputs' section.")

        table = dock.inputs_catchments_table
        table.setRowCount(0)
        row = table.add_catchment()
        self._populate_catchment_row(row, json_data)
        self._populate_outlet_location(json_data)

    def populate_inputs_multi(self, json_configs: list[dict]) -> None:
        """Populates ``inputs_catchments_table`` with one row per json config in
        ``json_configs`` (see ``GenerateARRjson.build_json_multiple``), each row's "Catchment
        Location" populated from that config's ``site`` section (see :meth:`_populate_catchment_row`).
        The dock "Outlet Location" parameters are populated once, from the *first* json config only
        (see :meth:`_populate_outlet_location`).

        :param json_configs: one parsed json config dict per catchment, in catchment order.
        """

        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached. Cannot populate multi-catchment 'site' inputs.")

        table = dock.inputs_catchments_table
        table.setRowCount(0)
        for json_data in json_configs:
            row = table.add_catchment()
            self._populate_catchment_row(row, json_data)
        self._populate_outlet_location(json_configs[0])

        # Multiple catchments always use "Calculate area" - see ``GenerateARRjson.site_catchment_area``.
        dock.arf_calculate_area_radio_button.setChecked(True)

        self.log(f"Populated catchments table from {len(json_configs)} catchment(s).", level='info')

    def populate_required_settings(self, json_data: dict) -> None:
        """Populates the 'Required Settings' tab of the ARR2026 dock (apart from inputs section)
        from an input json configuration file.
        The inputs section is populated by either populate_site (single catchment) or populate_site_multi (multiple catchments).
        If any sections of the json configuration file are missing or broken, will log a warning and
        skip that section (leaving the parameters as default in dock)."""

        # Check dock attached
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached. Cannot populate 'Required Settings' tab.")

        # Check and populate the 'outputs' section of the 'Required Settings' tab
        output = json_data.get("output")
        if output is not None:
            output_path = output.get("path")
            if output_path:
                dock.output_location_outfolder_line.setText(output_path)
            else:
                # reset to default
                dock.output_location_outfolder_line.setText(None)
                self.log("Config .json has no 'path' value in 'output' section. Skipping population of output folder path in dock. Ensure this path is specified before running the tool.", level='warning')

            output_format = output.get("format")
            if output_format == "csv":
                dock.output_options_format_combobox.setCurrentIndex(0)
            elif output_format == "ts1":
                dock.output_options_format_combobox.setCurrentIndex(1)
            elif output_format is None:
                pass
            else:
                self.log(f"Output format specified in config .json ({output_format}) is not recognised. Setting to default ('csv').", level='warning')
        else:
            self.log(f"Config .json has no 'output' section. Skipping population of 'output' section in dock. Ensure this is populated before running the tool.", level='warning')

        # Check and populate the 'ifd' section of the 'Required Settings' tab
        ifd = json_data.get("ifd")
        if ifd is not None:
            ifd_year = ifd.get("baseline_year")
            if ifd_year == 2030:
                dock.ifd_baseline_year_combobox.setCurrentIndex(0)
            elif ifd_year == 1990:
                dock.ifd_baseline_year_combobox.setCurrentIndex(1)
            elif ifd_year is None:
                pass
            else:
                self.log(f"IFD baseline year specified in config .json ({ifd_year}) is not recognised. Setting to default (2030).", level='info')

        # Check and populate the 'events' section of the 'Required Settings' tab
        events = json_data.get("events")
        if events is not None:
            aeps = events.get("aep")
            if aeps is not None:
                # select input aeps
                for aep in aeps:
                    mapped_aep = AEP_MAPPING.get(aep)
                    if mapped_aep:
                        getattr(dock, mapped_aep[1]).setChecked(True)
                    else:
                        self.log(f"AEP specified in config .json ({aep}) is not recognised. Skipping...", level='warning')
            else:
                self.log(f"Config .json has no 'aep' list in 'events' section. Skipping population of AEP checkboxes. Ensure at least one AEP event is selected before running the tool.", level='warning')

            durations = events.get("duration")
            if durations is not None:
                for dur in durations:
                    mapped_dur = DURATION_MAPPING.get(dur)
                    if mapped_dur:
                        getattr(dock, mapped_dur[1]).setChecked(True)
                    else:
                        self.log(f"Duration specified in config .json ({dur}) is not recognised. Skipping...", level='warning')
            else:
                self.log(f"Config .json has no 'duration' list in 'events' section. Skipping population of duration checkboxes. Ensure at least one duration event is selected before running the tool.", level='warning')
        else:
            self.log(f"Config .json has no 'events' section. Skipping population of 'events' section. Ensure at least one AEP event and one duration event are selected before running the tool.", level='warning')

    def populate_climate_change(self, json_data: dict) -> None:
        """Populates the 'Climate Change' tab of the ARR2026 dock from an input json configuration file.
        If any sections of the json configuration file are missing or broken, will log a warning and
        skip that section (leaving the parameters as default in dock)"""

        # Check dock attached
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached. Cannot populate 'Climate Change' tab.")

        # Check and populate the 'climate change' tab
        cc_data = json_data.get("climate_change")
        if cc_data is not None:
            cc_enabled = cc_data.get("enabled")
            if cc_enabled is None:
                return
            elif cc_enabled is False:
                return
            elif cc_enabled is True:
                cc_scenarios = cc_data.get("scenarios")
                if cc_scenarios is not None and cc_scenarios != []:
                    model = dock.climate_change_table.model()
                    for scenario in cc_scenarios:
                        year = scenario.get("baseline_year")
                        ssp = scenario.get("ssp")
                        dock.climate_change_table.add_scenario()
                        row = dock.climate_change_table.rowCount() - 1
                        if year is not None:
                            model.setData(model.index(row, COL_YEAR), str(year))
                        if ssp is not None:
                            model.setData(model.index(row, COL_SSP), ssp)
                else:
                    self.log(f"Config .json has enabled climate change, but has no scenarios. Skipping population of climate change section in dock.", level='warning')

        # Check for climate_change_method and check the radio button
        losses = json_data.get("losses")
        cc_method = losses.get("climate_change_method") if losses is not None else None
        if cc_method is not None:
            if cc_method == "storm":
                dock.climate_change_scale_storm_radio_button.setChecked(True)
            elif cc_method == "burst":
                dock.climate_change_scale_burst_radio_button.setChecked(True)
            else:
                self.log(f"Config .json has unrecognised 'climate_change_method' value ({cc_method}). Skipping population of climate change initial loss option in dock.", level='warning')

    def populate_arf(self, json_data: dict, multi: bool = False) -> None:
        """Populates the 'ARF' tab of the ARR2026 dock from an input json configuration file.
        If any sections of the json configuration file are missing or broken, will log a warning and
        skip that section (leaving the parameters as default in dock)"""

        # Check dock attached
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached. Cannot populate 'ARF' tab.")

        # Check and populate catchment area
        if multi:
            dock.arf_calculate_area_radio_button.setChecked(True)
            self.log(f"Ignoring any catchment area values in config .json(s). For multi-catchment runs, the catchment area must be calculated.", level='warning')
        else:
            site = json_data.get("site")
            catchment_area = site.get("catchment_area") if site is not None else None
            if catchment_area is not None:
                dock.arf_user_area_radio_button.setChecked(True)
                dock.arf_user_area_spinbox.setValue(catchment_area)
            else:
                dock.arf_calculate_area_radio_button.setChecked(True)
                self.log(f"Config .json has no 'catchment_area' value in 'site' section. Defaulting to calculate area.", level='info')

        # Check and populate the 'arf' part
        arf_data = json_data.get("arf")
        if arf_data is not None:
            arf_override = arf_data.get("arf_override")
            if arf_override is not None:
                dock.arf_manual_specify_block.setChecked(True)
                dock.arf_manual_specify_spinbox.setValue(arf_override)

            ignore_limits = arf_data.get("ignore_limits_for_frequent")
            if ignore_limits is not None and ignore_limits is True:
                dock.arf_for_events_checkbox.setChecked(True)

            min_arf = arf_data.get("min_arf")
            if min_arf is not None:
                dock.arf_min_arf_value_spinbox.setValue(min_arf)

    def populate_temporal_patterns(self, json_data: dict) -> None:
        """Populates the 'Temporal Patterns' tab of the ARR2026 dock from an input json configuration file.
        If any sections of the json configuration file are missing or broken, will log a warning and
        skip that section (leaving the parameters as default in dock)"""

        # Check dock attached
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached. Cannot populate 'Temporal Patterns' tab.")

        # Check and populate the 'temporal_patterns' tab
        tp_data = json_data.get("temporal_patterns")
        if tp_data is not None:
            add_tp = tp_data.get("additional_tp")
            if add_tp is not None:
                for tp in add_tp:
                    found = False
                    for i in range(dock.tp_optional_tps_list_widget.count()):
                        item = dock.tp_optional_tps_list_widget.item(i)
                        if item.text() == tp:
                            item.setSelected(True)
                            found = True
                            break
                    if not found:
                        self.log(
                            f"Additional temporal pattern specified in config .json ('{tp}') is not recognised. Skipping...",
                            level='warning')

            all_point_tp = tp_data.get("all_point_tp")
            if all_point_tp is not None and all_point_tp is True:
                dock.tp_use_add_point_tps_checkbox.setChecked(True)

            add_areal_tp = tp_data.get("add_areal_tp")
            if add_areal_tp is not None and add_areal_tp > 0:
                dock.tp_use_add_areal_tps_block.setChecked(True)
                dock.tp_use_add_areal_tps_no_spinbox.setValue(add_areal_tp)

    def populate_preburst(self, json_data: dict) -> None:
        """Populates the 'Preburst' tab of the ARR2026 dock from an input json configuration file.
        If any sections of the json configuration file are missing or broken, will log a warning and
        skip that section (leaving the parameters as default in dock)"""

        # Check dock attached
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached. Cannot populate 'Preburst' tab.")

        # Check and populate the 'preburst' tab
        preburst = json_data.get("preburst")
        cs = json_data.get("complete_storm")
        if preburst is not None:
            method = preburst.get("pattern_method")
            percentile = preburst.get("percentile")
            # set perburst percentile, if specified
            if percentile is not None:
                combobox = dock.preburst_percentile_combobox
                for i in range(combobox.count()):
                    if combobox.itemText(i).lower() == str(percentile).lower():
                        combobox.setCurrentIndex(i)
                        return
                self.log(f"Preburst percentile specified in config .json ('{percentile}') is not recognised. Skipping...",
                         level='warning')

            # Set other params based on pattern method
            if method == "recommended":
                dock.preburst_pattern_method_combobox.setCurrentIndex(0)
                if cs is not None and cs is True:
                    dock.preburst_rec_controls_complete_storm_checkbox.setChecked(True)
            elif method == "constant":
                dock.preburst_pattern_method_combobox.setCurrentIndex(1)
                if cs is not None and cs is True:
                    dock.preburst_constant_controls_complete_storm_checkbox.setChecked(True)
                self._populate_preburst_duration(
                    preburst,
                    dock.preburst_constant_controls_prop_controls_checkbox,
                    dock.preburst_constant_controls_prop_value_spinbox,
                    dock.preburst_constant_controls_prop_max_dur_value_spinbox,
                    dock.preburst_constant_controls_preburst_dur_value_spinbox
                )
            elif method == "temporal_pattern":
                dock.preburst_pattern_method_combobox.setCurrentIndex(2)
                if cs is not None and cs is True:
                    dock.preburst_tp_controls_complete_storm_checkbox.setChecked(True)
                pattern_tp = preburst.get("pattern_tp")
                if pattern_tp is not None:
                    if pattern_tp.lower() == "design_burst":
                        pattern_tp = "design_burst"
                    for i in range(dock.preburst_tp_controls_tp_combobox.count()):
                        if pattern_tp == dock.preburst_tp_controls_tp_combobox.itemText(i).lower():
                            dock.preburst_tp_controls_tp_combobox.setCurrentIndex(i)
                            break
                self._populate_preburst_duration(
                    preburst,
                    dock.preburst_tp_controls_prop_controls_checkbox,
                    dock.preburst_tp_controls_prop_value_spinbox,
                    dock.preburst_tp_controls_prop_max_dur_value_spinbox,
                    dock.preburst_tp_controls_preburst_dur_value_spinbox
                )
            elif method == "none":
                dock.preburst_pattern_method_combobox.setCurrentIndex(3)
                return
            elif method is None:
                return
            else:
                self.log(f"Config .json has unrecognised 'pattern_method' value ({method}) in 'preburst' section. Skipping population of 'preburst' section in dock.", level='warning')

    @staticmethod
    def _populate_preburst_duration(
            preburst_data: dict, prop_checkbox, prop_spinbox, prop_max_spinbox, fixed_dur_spinbox
    ) -> None:
        """Shared duration-controls population for the 'constant'/'temporal_pattern' preburst
        pattern methods (proportional-to-storm-duration vs a fixed preburst duration)."""

        duration_proportional = preburst_data.get("duration_proportional")
        pattern_duration = preburst_data.get("pattern_duration")
        pattern_duration_max = preburst_data.get("pattern_duration_max")
        if duration_proportional:
            prop_checkbox.setChecked(True)
            if pattern_duration is not None:
                prop_spinbox.setValue(pattern_duration)
            if pattern_duration_max is not None:
                prop_max_spinbox.setValue(pattern_duration_max)
        else:
            prop_checkbox.setChecked(False)
            if pattern_duration is not None:
                fixed_dur_spinbox.setValue(pattern_duration)

    def populate_initial_loss(self, json_data: dict) -> None:
        """Populates the 'Initial Loss' tab of the ARR2026 dock from an input json configuration file.
        If any sections of the json configuration file are missing or broken, will log a warning and
        skip that section (leaving the parameters as default in dock)"""

        # Check dock attached
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached. Cannot populate 'Initial Loss' tab.")

        # Check and populate the 'losses' tab
        losses = json_data.get("losses")
        if losses is not None:
            method = losses.get("method")
            if method == "recommended":
                dock.il_burst_il_rec_radio_button.setChecked(True)
            elif method == "probability_neutral":
                dock.il_burst_il_prop_neutral_radio_button.setChecked(True)
                self.log(f"Config .json has '{method}' method in 'losses' section. This is a legacy method and not recommended.", level='warning')
            else:
                self.log(f"Config .json has unrecognised 'method' value ({method}) in 'losses' section. Setting to default (Recommended).", level='warning')

            extrap_method = losses.get("extrapolation_method")
            if extrap_method is not None:
                for index, (value, _) in LOSS_EXTRAPOLATION_METHOD_MAPPING.items():
                    if value == extrap_method:
                        dock.il_short_dur_extrapolation_method_combobox.setCurrentIndex(index)
                        break
            elif extrap_method is None:
                pass
            else:
                self.log(
                    f"Loss extrapolation method specified in config .json ('{extrap_method}') is not recognised. Leaving extrapolation method as default.",
                    level='warning')

            mar = losses.get("mar")
            if mar is not None:
                dock.il_shor_dur_mar_value_spinbox.setValue(mar)
            static_loss = losses.get("static_loss")
            if static_loss is not None:
                dock.il_shor_dur_static_value_spinbox.setValue(static_loss)

            tuflow_loss_method = losses.get("tuflow_loss_method")
            if tuflow_loss_method == "infiltration":
                dock.il_tuflow_loss_method_combobox.setCurrentIndex(0)
            elif tuflow_loss_method == "excess":
                dock.il_tuflow_loss_method_combobox.setCurrentIndex(1)
                urban_il = losses.get("urban_initial_loss")
                urban_cl = losses.get("urban_continuing_loss")
                if urban_il is not None and urban_cl is not None:
                    dock.il_tuflow_loss_method_infil_ilcl_block.setChecked(True)
                    dock.il_tuflow_loss_method_infil_il_spinbox.setValue(urban_il)
                    dock.il_tuflow_loss_method_infil_cl_spinbox.setValue(urban_cl)
            elif tuflow_loss_method is None:
                pass
            else:
                self.log(
                    f"TUFLOW loss method specified in config .json ('{tuflow_loss_method}') is not recognised. Setting tuflow loss method as default.",
                    level='warning')

            user_il, user_cl = losses.get("user_initial_loss"), losses.get("user_continuing_loss")
            if user_il is not None:
                dock.il_user_overrides_il_checkbox.setChecked(True)
                dock.il_user_overrides_il_spinbox.setValue(user_il)
            if user_cl is not None:
                dock.il_user_overrides_cl_checkbox.setChecked(True)
                dock.il_user_overrides_cl_spinbox.setValue(user_cl)

    def populate_manually_specified_data(self, json_data: dict) -> None:
        """Populates the 'Manually Specified Data' tab of the ARR2026 dock from an input json configuration file.
        If any sections of the json configuration file are missing or broken, will log a warning and
        skip that section (leaving the parameters as default in dock)"""

        # Check dock attached
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached. Cannot populate 'Manually Specified Data' tab.")

        # Check and populate the 'manually_specified_data' tab
        response_json = json_data.get("response_json")
        if response_json is not None:
            dock.offline_mode_json_line_edit.setText(response_json)
        tp = json_data.get("temporal_patterns")
        if tp is not None:
            man_point_tp, man_areal_tp = tp.get("point_tp_csv"), tp.get("areal_tp_csv")
            if man_point_tp is not None:
                dock.tp_manual_point_tp_file_path_line.setText(man_point_tp)
            if man_areal_tp is not None:
                dock.tp_manual_areal_tp_file_path_line.setText(man_areal_tp)

    def check_multi_json_match(self, multi_json_data: list[dict]) -> None:
        """Runs checks to ensure that all the input json config files match everywhere but 'site'.
        If they don't match, this function will log a warning with the differences.
        The dock is always populated with the first json config file in the list."""

        for j in range(1, len(multi_json_data)):
            for sec in JSON_SECTIONS_EXCLUDE_SITE:
                if multi_json_data[0][sec] != multi_json_data[j][sec]:
                    self.log(f"json config files 0 and {j} have different '{sec}' sections - using 0's values for dock population.", level='warning')
                    self.log(f"      json config file 0 '{sec}': {multi_json_data[0][sec]}", level='info')
                    self.log(f"      json config file {j} '{sec}': {multi_json_data[j][sec]}", level='info')

    def load_json(self, path: str) -> dict:
        """Loads and returns the json config at ``path``.

        :param path: path to a configuration .json file.
        :returns: the parsed json config dict.
        """

        with open(path, 'r') as f:
            return json.load(f)

    def populate_dock(self, json_paths: list[str]) -> None:
        """Populates every section of the dock widget from ``json_data``, mirroring the
        section layout of :data:`JSON_SKELETON`/:meth:`GenerateARRjson.build_json`.

        Any configuration options in ``json_data`` that are defined incorrectly or not available
        are ignored (logged as a warning) and the dock is left at its existing/default value for
        that section instead of aborting the whole load.

        :param json_paths: a list of ``.json`` config files.
        """

        # Check dock attached
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to PopulateARRDockFromjson. Cannot populate dock.")

        # Convert all input json config file paths into a list of dicts - log and skip any that fail
        self.pytuflow_jsons = []
        multi_catchment_bool = False
        for path in json_paths:
            try:
                json_data = self.load_json(path)
            except Exception as e:
                self.log(f"Could not load json file '{path}': {e}", level='error')
                continue
            self.pytuflow_jsons.append(json_data)

        if len(self.pytuflow_jsons) == 0:
            self.log("No valid json config files were loaded. Dock will not be populated.", level='error')
            return
        elif len(self.pytuflow_jsons) == 1:
            self.log(f"Populating dock from single json config file '{json_paths[0]}'", level='info')
            self.populate_inputs_single(self.pytuflow_jsons[0])
        else:
            self.log(
                f"Populating dock from {len(self.pytuflow_jsons)} json config files: {',\n'.join(json_paths)}. \nUsing {json_paths[0]} to populate all shared parameters.",
                level='warning')
            multi_catchment_bool = True
            self.populate_inputs_multi(self.pytuflow_jsons)

        # Populate the rest of the dock from the first json config file in the list (shared parameters)
        default_json = self.pytuflow_jsons[0]
        self.populate_required_settings(default_json)
        self.populate_climate_change(default_json)
        self.populate_arf(default_json, multi_catchment_bool)
        self.populate_temporal_patterns(default_json)
        self.populate_preburst(default_json)
        self.populate_initial_loss(default_json)
        self.populate_manually_specified_data(default_json)

        self.log(f"Dock population completed.", level='info')
