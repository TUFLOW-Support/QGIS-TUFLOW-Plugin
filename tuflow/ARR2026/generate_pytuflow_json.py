"""
Helper script that is called by the arr2026_dock.py to generate the input .json file required by the arr tool in pytuflow.

See pytuflow documentation for more info on what is required in the .json file.

Sub-helper functions:
    - function to split a multi-catchment boundary file into individual per-catchment files
    - function to determine the input catchment area
"""

from __future__ import annotations

import copy
import re
import tempfile
import json
from pathlib import Path
from typing import Callable, Optional, Sequence

import processing
from qgis.PyQt.QtWidgets import QTableWidget, QCheckBox, QGroupBox
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsDistanceArea,
    QgsFeature,
    QgsProject,
    QgsVectorLayer,
)

from .climate_change_scenarios import COL_SSP, COL_YEAR
from .arr_shared_functionality import (
    JSON_SKELETON,
    LOSS_EXTRAPOLATION_METHOD_MAPPING,
    sanitise_filename_part as _sanitise_filename_part,
    source_file_path as layer_source_file_path,
    write_json_config as _write_json_config,
    write_json_configs as _write_json_configs,
)


def sanitise_filename_part(name: str, fallback: str = 'site') -> str:
    """Compatibility wrapper for the shared filename sanitiser."""

    return _sanitise_filename_part(name, fallback)


def write_json_config(path: Path | str, pytuflow_json: dict) -> Path:
    """Compatibility wrapper for the shared JSON config writer."""

    return _write_json_config(path, pytuflow_json)


def write_json_configs(
        output_dir: Path | str,
        configs: Sequence[dict],
        name_prefix: str = 'generated_input',
        name_pattern: Optional[str] = None,
) -> list[Path]:
    """Compatibility wrapper for the shared multi-config writer."""

    return _write_json_configs(output_dir, configs, name_prefix, name_pattern)


class GenerateARRjson:
    """Builds the pytuflow ``arr`` tool's input ``.json`` config from the current state of
    the ARR2026 dock widget."""

    def __init__(
            self, parent=None,
            log: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.parent = parent
        # Callback used to report messages back to the dock's log panel, invoked as
        # ``log(message, level)`` where ``level`` is one of ``'info'``/``'warning'``/``'error'``
        # (matching ``Arr2026Dock._log``). Defaults to a no-op if not supplied (e.g. in tests).
        self.log = log if log is not None else (lambda message, level='warning': None)
        self.pytuflow_json = copy.deepcopy(JSON_SKELETON)

    # ------------------------------------------------------------------
    # Sub-helpers
    # ------------------------------------------------------------------

    @staticmethod
    def source_file_path(layer: QgsVectorLayer) -> str:
        """Returns the file path of ``layer`` (stripping any OGR sublayer/query suffix)."""

        return layer_source_file_path(layer)

    @staticmethod
    def calculate_catchment_area(layer: QgsVectorLayer, features: Sequence[QgsFeature]) -> float:
        """Determines the area (km^2) of a single catchment - ``features`` is expected to
        contain exactly one feature. If ``layer`` has more than one feature, an error is raised.

        Uses :class:`QgsDistanceArea` configured with ``layer``'s source CRS and an
        ellipsoidal area calculation, so that the result is correct regardless of
        whether ``layer``'s CRS is projected or geographic.

        :param layer: the catchment boundary layer that ``features`` belong to
        :param features: the catchment's feature(s) - must contain exactly one feature.
        :returns: the catchment area (km^2).
        """

        features = list(features)

        # Check that there is exactly one feature (region) in the layer
        if len(features) != 1:
            raise ValueError(
                f"Expected exactly 1 feature for this catchment on layer '{layer.name()}', but found {len(features)}."
                f"Each catchment row must select a single feature."
            )

        # Calculate area of feature (region) in km^2
        distance_area = QgsDistanceArea()
        distance_area.setSourceCrs(layer.crs(), QgsProject.instance().transformContext())
        ellipsoid = QgsProject.instance().ellipsoid()
        distance_area.setEllipsoid(ellipsoid if ellipsoid else 'WGS84')
        area_m2 = distance_area.measureArea(features[0].geometry())
        return area_m2 / 1_000_000

    def export_catchment_feature_to_shapefile(
            self, layer: QgsVectorLayer, feature_id: int, output_folder: Optional[str], name_hint: str
    ) -> str:
        """Extracts a single feature (``feature_id``) from ``layer`` out to its own ``.shp``
        file (via the ``native:extractbyexpression`` processing tool), since the pytuflow
        ``arr`` tool's ``site.catchment_boundary`` expects a path to a file containing a single
        catchment polygon, not a shared multi-feature layer.

        The extracted file is written to a ``"split catchment files"`` subfolder of
        ``output_folder`` (or a temp folder, if ``output_folder`` isn't given/doesn't exist).

        :param layer: the catchment boundary layer the feature belongs to.
        :param feature_id: the id of the single feature to extract.
        :param output_folder: the dock's chosen output folder (``output_location_outfolder_line``).
        :param name_hint: used (sanitised) as the output file's name.
        :returns: the path to the newly written ``.shp`` file.
        """

        if output_folder and Path(output_folder).is_dir():
            target_dir = Path(output_folder) / 'split catchment files'
        else:
            target_dir = Path(tempfile.mkdtemp(prefix='arr2026_catchment_'))
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = re.sub(r'[^\w\-]+', '_', name_hint).strip('_') or f'catchment_{feature_id}'
        # Guard against names that are otherwise "safe" but start with a character GDAL/OGR can
        # misinterpret as part of a path/option.
        if not safe_name[:1].isalpha():
            safe_name = f'catchment_{safe_name}'
        out_path = target_dir / f'{safe_name}.shp'

        result = processing.run('native:extractbyexpression', {
            'INPUT': layer,
            'EXPRESSION': f'$id = {feature_id}',
            'OUTPUT': str(out_path),
        })
        return result['OUTPUT']

    @staticmethod
    def get_selected_checkbox_labels(block: QGroupBox, select_all_checkbox: QCheckBox) -> list[str]:
        """Returns the label text of every "selected" checkbox within ``block``.

        Used to collect the user-selected AEP / duration checkboxes from ``aep_selection_block`` /
        ``duration_selection_block``.

        If ``select_all_checkbox`` is checked, every other checkbox in ``block`` is treated as
        selected regardless of its own individual checked state - this mirrors
        :meth:`Arr2026Dock._on_aep_select_all_toggled`/:meth:`Arr2026Dock._on_duration_select_all_toggled`'s
        one-directional "Select all" behaviour, without relying on the individual checkboxes having
        already been synced up by the dock's ``toggled`` handler.
        ``select_all_checkbox`` itself is never included in the returned list.

        :param block: the container widget holding the checkboxes (``aep_selection_block`` /
            ``duration_selection_block``).
        :param select_all_checkbox: the "Select all" checkbox within ``block``.
        :returns: a list of label strings, in widget order, for every selected checkbox
            (excluding ``select_all_checkbox``).
        """

        select_all_checked = select_all_checkbox.isChecked()
        selected_labels = []
        for checkbox in block.findChildren(QCheckBox):
            if checkbox is select_all_checkbox:
                continue
            if select_all_checked or checkbox.isChecked():
                selected_labels.append(checkbox.text())
        return selected_labels

    @staticmethod
    def get_table_row_tuples(table: QTableWidget, columns: Sequence[int]) -> list[tuple]:
        """Returns a list of tuples, one per row in ``table``, each containing the values
        held in ``columns`` (in the order given) for that row.

        e.g. (``columns=(COL_YEAR, COL_SSP)``) with the climate_change_table result in ``(year, ssp)`` pairs

        :param table: the table to iterate.
        :param columns: the column indices - the order determines the order of the output tuples.
        :returns: a list of tuples (one per row, in row order), each containing the values of ``columns`` for that row.
        """

        model = table.model()
        rows = []
        for row in range(table.rowCount()):
            rows.append(tuple(model.data(model.index(row, column)) for column in columns))
        return rows

    def site_catchment_area(self, computed_area: Optional[float], multiple_catchments: bool = False) -> float:
        """Returns the catchment area (km^2) for a single region.

        The output of this function depends on the selected ARF method in the dock:
            - If the "User Area" ARF method is selected, the value is taken directly from ``arf_user_area_spinbox``
                - When ``multiple_catchments`` is ``True`` (more than one row in ``inputs_catchments_table``), selecting this option will raise an error
            - If the "Calculate area" ARF method is selected, ``computed_area`` (from :meth:`calculate_catchment_area`) is used as-is.
        """

        dock = self.parent
        if dock is not None and dock.arf_user_area_radio_button.isChecked():
            if multiple_catchments:
                raise ValueError(
                    "ARF 'User Area' option cannot be used when more than one catchment has been added to "
                    "the catchments table. Ensure ARF 'Calculate Area' option is selected, or remove the "
                    "additional catchment row(s)."
                )
            return dock.arf_user_area_spinbox.value()
        return computed_area if computed_area is not None else 0.0

    # ------------------------------------------------------------------
    # Build JSON
    # ------------------------------------------------------------------

    def _build_catchment_site_dict(self, row: int) -> dict:
        """Builds the ``site`` section dict for a single row of ``inputs_catchments_table``.

        :param row: the catchment row index in ``inputs_catchments_table``.
        :returns: a dictionary containing the ``site`` section of the JSON config for this catchment.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot populate site section.")

        table = dock.inputs_catchments_table
        multiple_catchments = table.rowCount() > 1

        name = table.catchment_name(row)
        if not name:
            raise ValueError(f"Catchment in row {row + 1} of the catchments table has no name specified.")
        site_dict = {"name": name}

        catchment = table.catchment_location(row)
        if catchment["method"] == "latlong":
            site_dict["latitude"] = catchment["latitude"]
            site_dict["longitude"] = catchment["longitude"]
        else:
            layer = catchment["layer"]
            feature_id = catchment["feature_id"]
            if layer is None or feature_id is None:
                raise ValueError(
                    f"Catchment '{name}' has no GIS layer/feature selected for its Catchment Location."
                )
            feature = layer.getFeature(feature_id)
            if not feature.isValid():
                raise ValueError(
                    f"The selected catchment boundary feature (id {feature_id}) for catchment '{name}' "
                    f"could not be found in layer {layer.name()} or is invalid."
                )

            # Check if the layer is already a single catchment layer before trying to split
            if layer.featureCount() == 1:
                boundary_path = self.source_file_path(layer)
            else:
                output_folder = dock.output_location_outfolder_line.text()
                boundary_path = self.export_catchment_feature_to_shapefile(layer, feature_id, output_folder, name)

            area = self.calculate_catchment_area(layer, [feature])
            site_dict["catchment_boundary"] = boundary_path
            site_dict["catchment_area"] = self.site_catchment_area(area, multiple_catchments)

        outlet = self._build_outlet_dict(name)
        if outlet is not None:
            site_dict["outlet_latitude"] = outlet["latitude"]
            site_dict["outlet_longitude"] = outlet["longitude"]

        return site_dict

    def _build_outlet_dict(self, catchment_label: str) -> Optional[dict]:
        """Builds the (optional) outlet latitude/longitude override for a catchment, from the
        dock "Outlet Location" inputs.
        First checks if the dock's ``outlet_location_checkbox`` is checked (returns None if not).
        Outlet location does not vary per catchment. It is either:
            - Unspecified (ARR handles it), or
            - Bulk specified for every catchment via lat/long

        :param catchment_label: the catchment's name - used only for log/error messages.
        :returns: ``{"latitude": float, "longitude": float}``, or ``None`` if default "Catchment Centroid" is used
        """

        dock = self.parent
        outlet_loc_enabled = dock.outlet_location_checkbox.isChecked()
        if outlet_loc_enabled:
            method_index = dock.outlet_location_method_combobox.currentIndex()
            if method_index == 0:  # GIS point layer
                outlet_layer = dock._outlet_location_selected_layer()
                outlet_feature_id = dock.outlet_location_gis_layer_feature_combobox.currentData()
                if outlet_layer is None or outlet_feature_id is None:
                    return None
                outlet_feature = outlet_layer.getFeature(outlet_feature_id)
                if not outlet_feature.isValid():
                    raise ValueError(
                        f"The selected outlet point feature (id {outlet_feature_id}) could not be found in "
                        f"layer {outlet_layer.name()} or is invalid."
                    )
                point = outlet_feature.geometry().centroid().asPoint()
                transform = QgsCoordinateTransform(
                    outlet_layer.crs(), QgsCoordinateReferenceSystem('EPSG:4326'), QgsProject.instance())
                wgs84_point = transform.transform(point)
                return {"latitude": wgs84_point.y(), "longitude": wgs84_point.x()}

            elif method_index == 1:  # Latitude/longitude
                return {
                    "latitude": dock.outlet_location_lat_long_lat_spinbox.value(),
                    "longitude": dock.outlet_location_lat_long_long_spinbox.value(),
                }
            else:
                return None

        return None

    def populate_site(self) -> dict:
        """Populates the ``site`` section of the JSON skeleton with values from the dock's current state.

        Only the *first* row of ``inputs_catchments_table`` is used here - see
        :meth:`build_json_multiple` for building a separate ``site`` section (and ``.json``
        config) per catchment row.

        :returns: a dictionary containing the ``site`` section of the JSON config.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot populate site section.")

        table = dock.inputs_catchments_table
        if table.rowCount() == 0:
            raise ValueError("No catchments have been added. Add at least one row to the catchments table.")

        site_dict = self._build_catchment_site_dict(0)

        self.log(f"Site/catchment inputs: \n {json.dumps(site_dict, indent=4)}", level='info')
        return site_dict

    def populate_response_json(self) -> str | None:
        """Populates the ``response_json`` section of the JSON skeleton with values from the dock's current state.

        This section does *not* change based on the number of input catchments.
        As such, the output dict can be used for every output .json file.

        :returns: a string containing the ``response_json`` path or `None` if no path.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot populate response_json section.")

        # Check if 'response json' has been loaded
        json_path = dock.offline_mode_json_line_edit.text()
        if json_path is not None and json_path != "":
            self.log(f"Response .json input: {json_path}", level='info')
            return json_path
        else:
            return None

    def populate_ifd(self) -> dict:
        """Populates the ``ifd`` section of the JSON skeleton with values from the dock's current state.

        This section does *not* change based on the number of input catchments.
        As such, the output dict can be used for every output .json file.

        :returns: a dictionary containing the ``ifd`` section of the JSON config.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot populate ifd section.")

        # Initialise empty ifd dictionary to populate 'ifd' section of .json
        ifd_dict = {}

        # Get ifd selection from dock
        baseline_year_index = dock.ifd_baseline_year_combobox.currentIndex()
        if baseline_year_index == 0:
            ifd_dict["baseline_year"] = 2030
        elif baseline_year_index == 1:
            ifd_dict["baseline_year"] = 1990
        else:
            # should never get this error as the combobox only has 2 options.
            raise ValueError(f"Unexpected baseline year has been selected in dock. ifd_baseline_year_combobox index: {baseline_year_index}")

        self.log(f"IFD input: \n {json.dumps(ifd_dict, indent=4)}", level='info')
        return ifd_dict

    def populate_events(self) -> dict:
        """Populates the ``events`` section of the JSON skeleton with values from the dock's current state.

        This section does *not* change based on the number of input catchments.
        As such, the output dict can be used for every output .json file.

        The ``events`` section of the json contains the AEP's and durations and the output notation.

        :returns: a dictionary containing the ``events`` section of the JSON config.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot populate events section.")

        # Initialise empty events dictionary to populate 'events' section of .json
        events_dict = {}

        # Collect user-selected AEP / duration checkbox labels
        selected_aeps = self.get_selected_checkbox_labels(dock.aep_selection_block, dock.aep_checkbox_select_all)
        selected_durations = self.get_selected_checkbox_labels(
            dock.duration_selection_block, dock.dur_checkbox_select_all)

        # Convert durations to integers (in minutes)
        cleaned_durations = []
        for dur in selected_durations:
            i, units = dur.split(" ")
            i = float(i) # convert to float to handle decimal durations
            if units == "hr":
                i = i * 60 # convert to mins
            cleaned_durations.append(int(i)) # convert back to int to match expected input

        # Populate events_dict
        events_dict["aep"] = selected_aeps
        events_dict["duration"] = cleaned_durations

        # Hardcoded to default 'aep'
        events_dict["output_notation"] = "aep" # default

        # Check for empty aep/dur lists
        if not events_dict["aep"]:
            raise ValueError("No AEPs have been selected. Please select at least one AEP checkbox.")
        if not events_dict["duration"]:
            raise ValueError("No durations have been selected. Please select at least one duration checkbox.")

        self.log(f"Event (AEP/duration) inputs: \n {json.dumps(events_dict, indent=4)}", level='info')
        return events_dict

    def populate_tps(self) -> dict:
        """Populates the ``temporal_patterns`` section of the JSON skeleton with values from the dock's current state.

        This section does *not* change based on the number of input catchments.
        As such, the output dict can be used for every output .json file.

        The ``temporal_patterns`` section of the json contains the AEP's and durations and the output notation.

        :returns: a dictionary containing the ``temporal_patterns`` section of the JSON config.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot populate temporal_patterns section.")

        # Initialise empty tps dictionary to populate 'temporal_patterns' section of .json
        tps_dict = {}

        # Add manually specified point and/or areal tps (csv's) if specified
        point_tp_csv_path = dock.tp_manual_point_tp_file_path_line.text()
        areal_tp_csv_path = dock.tp_manual_areal_tp_file_path_line.text()
        if point_tp_csv_path is not None and point_tp_csv_path != "":
            tps_dict["point_tp_csv"] = point_tp_csv_path
        if areal_tp_csv_path is not None and areal_tp_csv_path != "":
            tps_dict["areal_tp_csv"] = areal_tp_csv_path

        # Get selected optional additional tps from list
        add_tps = []
        for i in range(dock.tp_optional_tps_list_widget.count()):
            list_item = dock.tp_optional_tps_list_widget.item(i)
            if list_item.isSelected():
                add_tps.append(list_item.text())
        tps_dict["additional_tp"] = add_tps

        # 'Use all additional point temporal patterns available within region' checkbox
        tps_dict["all_point_tp"] = dock.tp_use_add_point_tps_checkbox.isChecked()

        # 'Use additional areal tps' and the int number to use
        if dock.tp_use_add_areal_tps_block.isChecked():
            tps_dict["add_areal_tp"] = dock.tp_use_add_areal_tps_no_spinbox.value()
        else:
            tps_dict["add_areal_tp"] = 0

        self.log(f"Temporal pattern inputs: \n {json.dumps(tps_dict, indent=4)}", level='info')
        return tps_dict

    def populate_cc(self) -> dict:
        """Populates the ``climate_change`` section of the JSON skeleton with values from the dock's current state.

        This section does *not* change based on the number of input catchments.
        As such, the output dict can be used for every output .json file.

        :returns: a dictionary containing the ``climate_change`` section of the JSON config.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot populate climate_change section.")

        # Initialise empty cc dictionary to populate 'climate_change' section of .json
        cc_dict = {}

        # Extract (year, ssp) pairs from the climate change scenario table and format
        year_ssp_tuples = self.get_table_row_tuples(dock.climate_change_table, (COL_YEAR, COL_SSP))

        # Check if any climate change scenarios have been specified and use that to determine if enabled
        if year_ssp_tuples:
            cc_dict["enabled"] = True
        else:
            cc_dict["enabled"] = False
            self.log(f"Climate change not enabled.", level='info')
            return cc_dict


        cc_dict["scenarios"] = [{"baseline_year": int(year), "ssp": ssp} for year, ssp in year_ssp_tuples]

        self.log(f"Climate change inputs: \n {json.dumps(cc_dict, indent=4)}", level='info')
        return cc_dict

    def populate_preburst(self) -> dict:
        """Populates the ``preburst`` section of the JSON skeleton with values from the dock's current state.

        This section does *not* change based on the number of input catchments.
        As such, the output dict can be used for every output .json file.

        The ``preburst`` section of the json changes a lot depending on the preburst method selected.

        :returns: a dictionary containing the ``preburst`` section of the JSON config.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot populate preburst section.")

        # Initialise empty preburst dictionary to populate 'preburst' section of .json
        preburst_dict = {}

        # Add preburst percentile
        preburst_dict["percentile"] = dock.preburst_percentile_combobox.currentText().lower()

        # Process depending on pattern method
        pp_method = dock.preburst_pattern_method_combobox.currentText().lower()
        if pp_method == "none":
            preburst_dict["pattern_method"] = "none"
            # todo - maybe need to set null for all other preburst options, will need to check when validating final json
            self.log(f"Preburst pattern method set to 'None'.", level='info')
            return preburst_dict
        elif pp_method == "recommended":
            preburst_dict["pattern_method"] = "recommended"
            self.log(f"Preburst pattern method set to 'Recommended'. Inputs: \n {json.dumps(preburst_dict, indent=4)}", level='info')
            return preburst_dict
        elif pp_method == "constant" or pp_method == "temporal pattern":
            # initial population for constant / pp methods
            if pp_method == "constant":
                preburst_dict["pattern_method"] = "constant"
                # bool to track if duration proportional or not
                prop_bool = dock.preburst_constant_controls_prop_controls_checkbox.isChecked()
            else:
                preburst_dict["pattern_method"] = "temporal_pattern"
                # configure tp - input specific to tp method
                input_tp = dock.preburst_tp_controls_tp_combobox.currentText()
                if input_tp.lower() == "design burst":
                    preburst_dict["pattern_tp"] = "design_burst"
                else:
                    preburst_dict["pattern_tp"] = input_tp
                # bool to track if duration proportional or not
                prop_bool = dock.preburst_tp_controls_prop_controls_checkbox.isChecked()

            # conditional inputs depending on proportional or not
            if prop_bool:
                preburst_dict["duration_proportional"] = True
                # per method inputs
                if pp_method == "constant":
                    preburst_dict["pattern_duration"] = dock.preburst_constant_controls_prop_value_spinbox.value() # proportion of duration
                    preburst_dict["pattern_duration_max"] = dock.preburst_constant_controls_prop_max_dur_value_spinbox.value()
                else:
                    preburst_dict["pattern_duration"] = dock.preburst_tp_controls_prop_value_spinbox.value() # proportion of duration
                    preburst_dict["pattern_duration_max"] = dock.preburst_tp_controls_prop_max_dur_value_spinbox.value()
            else:
                preburst_dict["duration_proportional"] = False
                # per method inputs
                if pp_method == "constant":
                    preburst_dict["pattern_duration"] = dock.preburst_constant_controls_preburst_dur_value_spinbox.value()
                else:
                    preburst_dict["pattern_duration"] = dock.preburst_tp_controls_preburst_dur_value_spinbox.value()

            self.log(f"Preburst inputs (preburst pattern method = {pp_method}): \n {json.dumps(preburst_dict, indent=4)}", level='info')
            return preburst_dict
        else:
            # should never get this error as the combobox only has 4 options.
            raise ValueError("Invalid preburst pattern method selected.")

    def populate_losses(self) -> dict:
        """Populates the ``losses`` section of the JSON skeleton with values from the dock's current state.

        This section does *not* change based on the number of input catchments.
        As such, the output dict can be used for every output .json file.

        :returns: a dictionary containing the ``losses`` section of the JSON config.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot populate losses section.")

        # Initialise empty losses dictionary to populate 'losses' section of .json
        losses_dict = {}

        # determine burst initial loss method
        if dock.il_burst_il_rec_radio_button.isChecked():
            losses_dict["method"] = "recommended"
        if dock.il_burst_il_prop_neutral_radio_button.isChecked():
            losses_dict["method"] = "probability_neutral"

        # determine extrapolation method
        input_method_index = dock.il_short_dur_extrapolation_method_combobox.currentIndex()
        losses_dict["extrapolation_method"] = LOSS_EXTRAPOLATION_METHOD_MAPPING[input_method_index][0]

        # add extra params as needed
        if losses_dict["extrapolation_method"] == "hill":
            losses_dict["mar"] = dock.il_shor_dur_mar_value_spinbox.value()
        elif losses_dict["extrapolation_method"] == "static":
            losses_dict["static_loss"] = dock.il_shor_dur_static_value_spinbox.value()
        else:
            losses_dict["mar"] = None
            losses_dict["static_loss"] = None

        # tuflow loss method and optional params
        input_tuflow_method_index = dock.il_tuflow_loss_method_combobox.currentIndex()
        if input_tuflow_method_index == 0:
            losses_dict["tuflow_loss_method"] = "infiltration"
        else:
            losses_dict["tuflow_loss_method"] = "excess"
            if dock.il_tuflow_loss_method_infil_ilcl_block.isChecked():
                losses_dict["urban_initial_loss"] = dock.il_tuflow_loss_method_infil_il_spinbox.value()
                losses_dict["urban_continuing_loss"] = dock.il_tuflow_loss_method_infil_cl_spinbox.value()


        # user overrides
        if dock.il_user_overrides_il_checkbox.isChecked():
            losses_dict["user_initial_loss"] = dock.il_user_overrides_il_spinbox.value()
        if dock.il_user_overrides_cl_checkbox.isChecked():
            losses_dict["user_continuing_loss"] = dock.il_user_overrides_cl_spinbox.value()

        # climate change method - defaults to storm
        if dock.climate_change_scale_storm_radio_button.isChecked():
            losses_dict["climate_change_method"] = "storm"
        if dock.climate_change_scale_burst_radio_button.isChecked():
            losses_dict["climate_change_method"] = "burst"

        self.log(f"Losses inputs: \n {json.dumps(losses_dict, indent=4)}", level='info')
        return losses_dict

    def populate_arf(self) -> dict:
        """Populates the ``arf`` section of the JSON skeleton with values from the dock's current state.

        This section does *not* change based on the number of input catchments.
        As such, the output dict can be used for every output .json file.

        :returns: a dictionary containing the ``arf`` section of the JSON config.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot populate arf section.")

        # Initialise empty arf dictionary to populate 'arf' section of .json
        arf_dict = {}

        # Get arf info from dock
        if dock.arf_for_events_checkbox.isChecked():
            arf_dict["ignore_limits_for_frequent"] = True
        else:
            arf_dict["ignore_limits_for_frequent"] = False
        arf_dict["min_arf"] = dock.arf_min_arf_value_spinbox.value()

        self.log(f"ARF inputs: \n {json.dumps(arf_dict, indent=4)}", level='info')
        return arf_dict

    def populate_complete_storm(self) -> bool:
        """Determines whether complete storm is enabled from the dock's current state.

        This section does *not* change based on the number of input catchments.
        As such, the output bool can be used for every output .json file.

        :returns: a boolean indicating whether complete storm is enabled.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot populate complete_storm section.")

        # check preburst method
        tp_method = dock.preburst_pattern_method_combobox.currentText().lower()
        if tp_method == "recommended":
            self.log(f"Complete storm: {dock.preburst_rec_controls_complete_storm_checkbox.isChecked()}.", level='info')
            return dock.preburst_rec_controls_complete_storm_checkbox.isChecked()
        elif tp_method == "constant":
            self.log(f"Complete storm: {dock.preburst_constant_controls_complete_storm_checkbox.isChecked()}.", level='info')
            return dock.preburst_constant_controls_complete_storm_checkbox.isChecked()
        elif tp_method == "temporal pattern":
            self.log(f"Complete storm: {dock.preburst_tp_controls_complete_storm_checkbox.isChecked()}.", level='info')
            return dock.preburst_tp_controls_complete_storm_checkbox.isChecked()
        else:
            self.log(f"Complete storm: False.", level='info')
            return False

    def populate_output(self) -> dict:
        """Populates the ``output`` section of the JSON skeleton with values from the dock's current state.

        This section does *not* change based on the number of input catchments.
        As such, the output dict can be used for every output .json file.

        :returns: a dictionary containing the ``output`` section of the JSON config.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot populate output section.")

        # Initialise empty output dictionary to populate 'output' section of .json
        output_dict = {}

        # output path
        path = dock.output_location_outfolder_line.text()
        if path is None or path == "":
            raise ValueError("No output folder has been specified.")
        else:
            output_dict["path"] = dock.output_location_outfolder_line.text()

        # output format
        output_dict["format"] = dock.output_options_format_combobox.currentText().lower()

        # verbose output - hardcoded to True
        output_dict["verbose"] = True

        self.log(f"Output inputs: \n {json.dumps(output_dict, indent=4)}", level='info')
        return output_dict

    def build_json(self) -> dict:
        """Builds the full pytuflow ``arr`` tool input ``.json`` config dict from the current
        state of the ARR2026 dock widget.

        :returns: the full ``.json`` config dict, ready for ``json.dump``.
        """

        self.pytuflow_json = copy.deepcopy(JSON_SKELETON)

        # (json key, builder function) pairs - executed in this order.
        sections = (
            ("site", self.populate_site),
            ("response_json", self.populate_response_json),
            ("ifd", self.populate_ifd),
            ("events", self.populate_events),
            ("temporal_patterns", self.populate_tps),
            ("climate_change", self.populate_cc),
            ("preburst", self.populate_preburst),
            ("losses", self.populate_losses),
            ("arf", self.populate_arf),
            ("complete_storm", self.populate_complete_storm),
            ("output", self.populate_output),
        )

        for key, builder in sections:
            self.pytuflow_json[key] = builder()

        return self.pytuflow_json

    def build_json_multiple(self) -> dict:
        """Builds one pytuflow ``arr`` json config per row of ``inputs_catchments_table``.

        The *first* row's json config is built in full via :meth:`build_json` (identical to
        running with a single catchment row). For every subsequent row, only its ``site`` section
        is populated (via :meth:`_build_catchment_site_dict`) for each new catchment row.
        Every other section (events, losses, climate change, etc) is only in the first .json.

        If building a particular row's ``site`` section fails, a warning is output to the log
        and that row is skipped rather than aborting the whole batch.

        This works equally well for a single catchment row as for many - it's always safe to
        call this instead of :meth:`build_json` directly.

        :returns:
            ``{"configs": [{"site_name": str, "json": dict}, ...] -> one entry per successfully built catchment,
                    in table row order (always including the first row),
            "errors": [{"catchment": str, "error": str}, ...]}`` -> one entry per catchment (row) that was skipped
                    due to an error while building its ``site`` section.
        """

        # Check dock exists
        dock = self.parent
        if dock is None:
            raise ValueError("No dock has been attached to GenerateARRjson. Cannot build json.")

        table = dock.inputs_catchments_table
        row_count = table.rowCount()
        if row_count == 0:
            raise ValueError("No catchments have been added. Add at least one row to the catchments table.")

        configs: list[dict] = []
        errors: list[dict] = []

        # Build the first catchment's json config in full - reused by every other catchment.
        primary_json = self.build_json()
        configs.append({"site_name": primary_json["site"].get("name"), "json": primary_json})

        # Build each subsequent catchment's (row's) 'site' section only, no need to have any other section
        for row in range(1, row_count):
            catchment_label = table.catchment_name(row) or f"catchment row {row + 1}"
            try:
                site_dict = self._build_catchment_site_dict(row)
                catchment_json = {"site": site_dict}
                configs.append({"site_name": site_dict.get("name"), "json": catchment_json})
                self.log(
                    f"Site/catchment inputs for '{catchment_label}': \n {json.dumps(site_dict, indent=4)}",
                    level='info',
                )
            except Exception as e:
                self.log(f"Skipping catchment '{catchment_label}': {e}", level='warning')
                errors.append({"catchment": catchment_label, "error": str(e)})

        return {"configs": configs, "errors": errors}
