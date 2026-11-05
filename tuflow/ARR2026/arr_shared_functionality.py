"""
Script containing any shared functions or variables that are used across multiple scripts for the ARR2026 tool.
Used to avoid code duplication.
"""

import json
import re
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence, Any

from qgis.PyQt.QtWidgets import QComboBox
from qgis.core import QgsFeature, QgsMapLayer, QgsVectorLayer, QgsWkbTypes
from ..compatibility_routines import QT_ITEM_DATA_USER_ROLE

# QComboBox item data role used to stash the QGIS layer id behind each "layer" combobox entry
_LAYER_ID_ROLE = QT_ITEM_DATA_USER_ROLE

# file filter for .jsons
_CONFIG_JSON_FILE_FILTER = 'Config files (*.json)'

# json level 1 sections
JSON_SECTIONS_EXCLUDE_SITE = ["ifd", "events", "temporal_patterns", "climate_change", "preburst", "losses", "arf", "complete_storm", "output", "response_json"]

JSON_SKELETON = {
    "site": {},
    "ifd": {},
    "events": {
        "aep": [],
        "duration": [],
        "output_notation": "ari"
    },
    "temporal_patterns": {},
    "climate_change": {
        "enabled": False,
        "scenarios": [
            {}
        ]
    },
    "preburst": {},
    "losses": {},
    "arf": {},
    "complete_storm": False,
    "output": {},
    "response_json": None,
    "max_retries": 2
}

# Mapping for aep to ui text and ui object name
_AEP_MAPPING = {
    "1 in 2000": ["1 in 2000", "aep_checkbox_1_in_2000"],
    "1 in 1000": ["1 in 1000", "aep_checkbox_1_in_1000"],
    "1 in 500": ["1 in 500", "aep_checkbox_1_in_500"],
    "1 in 200": ["1 in 200", "aep_checkbox_1_in_200"],
    "1%": ["1%", "aep_checkbox_1"],
    "2%": ["2%", "aep_checkbox_2"],
    "5%": ["5%", "aep_checkbox_5"],
    "10%": ["10%", "aep_checkbox_10"],
    "20%": ["20%", "aep_checkbox_20"],
    "50%": ["50%", "aep_checkbox_50"],
    "63.2%": ["63.2%", "aep_checkbox_63_2"]
}
class AEP_MAPPING:
    """Accepts different forms of AEP naming conventions:

        - 1 in 200
        - 0.5%
        - 0.5
    """
    @classmethod
    def get(cls, value: Any) -> list[str] | None:
        try:
            val_interpreted = float(value)
        except ValueError:
            val_interpreted = value

        if isinstance(val_interpreted, str):
            try:
                v = float(val_interpreted.strip('%'))
                if v < 1:
                    val_interpreted = v
            except ValueError:
                pass
        
        if isinstance(val_interpreted, (float, int)):
            val_interpreted = cls._number_to_name(val_interpreted)

        return _AEP_MAPPING.get(val_interpreted)

    @classmethod
    def _number_to_name(cls, value: float | int) -> str:
        if value < 1:
            return f'1 in {cls._aep_to_1inX(value)}'
        if round(value, 1) == 63.2:
            return '63.2%'
        return f'{value:.0f}%'

    @staticmethod
    def _aep_to_1inX(value: float | int) -> float:
        try:
            return int(1 / value * 100)
        except ValueError:
            return value


# Mapping for duration in mins to ui text and ui object name
DURATION_MAPPING = {
    10: ["10 min", "dur_checkbox_10min"],
    15: ["15 min", "dur_checkbox_15min"],
    20: ["20 min", "dur_checkbox_20min"],
    25: ["25 min", "dur_checkbox_25min"],
    30: ["30 min", "dur_checkbox_30min"],
    45: ["45 min", "dur_checkbox_45min"],
    60: ["1 hr", "dur_checkbox_1hr"],
    90: ["1.5 hr", "dur_checkbox_1_5hr"],
    120: ["2 hr", "dur_checkbox_2hr"],
    180: ["3 hr", "dur_checkbox_3hr"],
    270: ["4.5 hr", "dur_checkbox_4_5hr"],
    360: ["6 hr", "dur_checkbox_6hr"],
    540: ["9 hr", "dur_checkbox_9hr"],
    720: ["12 hr", "dur_checkbox_12hr"],
    1080: ["18 hr", "dur_checkbox_18hr"],
    1440: ["24 hr", "dur_checkbox_24hr"],
    1800: ["30 hr", "dur_checkbox_30hr"],
    2160: ["36 hr", "dur_checkbox_36hr"],
    2880: ["48 hr", "dur_checkbox_48hr"],
    4320: ["72 hr", "dur_checkbox_72hr"],
    5760: ["96 hr", "dur_checkbox_96hr"],
    7200: ["120 hr", "dur_checkbox_120hr"],
    8640: ["144 hr", "dur_checkbox_144hr"],
    10080: ["168 hr", "dur_checkbox_168hr"]
}

# Mapping for index, available extrapolation method, ui text
LOSS_EXTRAPOLATION_METHOD_MAPPING = {
    0: ["interpolate", "Interpolate to zero"],
    1: ["log_interpolate", "Log-interpolate to zero"],
    2: ["interpolate_preburst", "Interpolate pre-burst"],
    3: ["log_interpolate_preburst", "Log-interpolate pre-burst"],
    4: ["constant", "Constant"],
    5: ["constant_preburst_ratio", "Constant pre-burst ratio (default)"],
    6: ["rahman", "Rahman et al. 2002 (requires MAR)"],
    7: ["hill", "Hill et al. 1996/1998 (requires MAR)"],
    8: ["static", "Static value (requires static loss)"]
}

def is_main_config_candidate(json_data: dict) -> bool:
    """Determines whether ``json_data`` looks like a 'main' configuration file.
    A 'main' configuration file will contain 'site' as well as other options, whereas
    a non-main config file will only contain 'site'.

    Will return ``True`` if ``json_data`` contains any non-empty section other than ``site``,
    and ``False`` otherwise.
    """

    # First check if 'site' exists and is non-empty, if not, return False
    site = json_data.get('site')
    if not site or not isinstance(site, dict) or not any(site.values()):
        return False

    # Now, check if any other section exists and is non-empty
    for section in JSON_SECTIONS_EXCLUDE_SITE:
        value = json_data.get(section)
        if not value:
            continue
        # A section with empty lists doesn't count as real content.
        if isinstance(value, dict) and not any(value.values()):
            continue
        return True
    return False

def feature_label(feature) -> str:
    """Returns a ``';'`` separated string of ``feature``'s attribute values, used as its
    display label in a "feature" combobox."""

    attribute_values = ['' if value is None else str(value) for value in feature.attributes()]
    return ';'.join(attribute_values)

def is_polygon_layer(layer) -> bool:
    """Returns ``True`` if ``layer`` is a polygon (or multipolygon) vector layer.
    Used to filter the "Catchment Location" GIS layer combobox."""

    if layer is None or layer.type() != QgsMapLayer.VectorLayer:
        return False
    return layer.geometryType() == QgsWkbTypes.GeometryType.PolygonGeometry

def is_point_layer(layer) -> bool:
    """Returns ``True`` if ``layer`` is a point (or multipoint) vector layer.
    Used to filter the (dock-level, bulk) "Outlet Location" GIS layer combobox - see
    ``arr2026_dock.Arr2026Dock``."""

    if layer is None or layer.type() != QgsMapLayer.VectorLayer:
        return False
    return layer.geometryType() == QgsWkbTypes.GeometryType.PointGeometry


def populate_layer_combobox(
        combobox: QComboBox,
        layers: Iterable[tuple[str, str, object]],
        is_valid_layer: Callable[[object], bool],
        empty_label: Optional[str] = None,
) -> None:
    """Repopulates a layer combobox, preserving its selection when still available.

    ``layers`` contains ``(label, layer_id, layer)`` tuples. An optional empty entry is
    prepended when ``empty_label`` is supplied.
    """

    previous_layer_id = combobox.currentData(_LAYER_ID_ROLE)
    combobox.blockSignals(True)
    try:
        combobox.clear()
        if empty_label is not None:
            combobox.addItem(empty_label, None)
        for label, layer_id, layer in layers:
            if is_valid_layer(layer):
                combobox.addItem(label, layer_id)
        if previous_layer_id is not None:
            index = combobox.findData(previous_layer_id)
            if index >= 0:
                combobox.setCurrentIndex(index)
    finally:
        combobox.blockSignals(False)


def populate_feature_combobox(combobox: QComboBox, features: Iterable[QgsFeature]) -> None:
    """Repopulates a feature combobox with labelled features, preserving its selection
    when that feature is still available."""

    previous_feature_id = combobox.currentData()
    combobox.blockSignals(True)
    try:
        combobox.clear()
        for feature in features:
            combobox.addItem(feature_label(feature), feature.id())
        if previous_feature_id is not None:
            index = combobox.findData(previous_feature_id)
            if index >= 0:
                combobox.setCurrentIndex(index)
    finally:
        combobox.blockSignals(False)


def source_file_path(layer: QgsVectorLayer) -> str:
    """Returns the file path of ``layer`` without any provider URI suffix."""

    return layer.dataProvider().dataSourceUri().split('|')[0]


def sanitise_filename_part(name: str, fallback: str = 'site') -> str:
    """Sanitises ``name`` for use as part of a filename.

    Runs of characters other than word characters or hyphens become a single
    underscore; leading/trailing underscores are stripped. Returns ``fallback``
    if sanitisation leaves the name empty.
    """

    return re.sub(r'[^\w\-]+', '_', name or '').strip('_') or fallback


def resolve_config_filename(pattern: str, site_name: str, enum: int) -> str:
    """Resolves a filename ``pattern`` by substituting its ``${name}``/``${enum}`` placeholders:
        - ``${name}`` - ``site_name``, sanitised via :func:`sanitise_filename_part`;
        - ``${enum}`` - ``enum`` (a catchment's position in the table, in table order).

    A ``.json`` extension is appended automatically if ``pattern`` doesn't already end with one.
    If ``pattern`` contains neither placeholder, it's returned unchanged (other than the ``.json`` extension).
    """

    filename = pattern.replace('${name}', sanitise_filename_part(site_name)).replace('${enum}', str(enum))
    if not filename.lower().endswith('.json'):
        filename += '.json'
    return filename


def write_json_config(path: Path | str, pytuflow_json: dict) -> Path:
    """Writes one formatted pytuflow ``arr`` configuration dict to ``path``.

    Any missing parent directories are created first.
    """

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(pytuflow_json, f, indent=4)
    return out_path


def write_json_configs(
        output_dir: Path | str,
        configs: Sequence[dict],
        name_prefix: str = 'generated_input',
        name_pattern: Optional[str] = None,
) -> list[Path]:
    """Writes named pytuflow ``arr`` configurations to individual JSON files.

    If ``name_pattern`` is supplied (non-empty), it's used as the output filename for every config,
    with placeholders substituted (if present):
        - ``${name}`` - the catchment's (sanitised) site name;
        - ``${enum}`` - the catchment's position in ``configs``.
    A ``.json`` extension is appended automatically if ``name_pattern`` doesn't already end with one.

    Otherwise, files are named ``<name_prefix>_<sanitised site name>.json``.

    Returned in the same order as the input ``configs``.
    """

    output_dir = Path(output_dir)
    paths: list[Path] = []
    for index, entry in enumerate(configs, start=1):
        safe_name = sanitise_filename_part(entry.get('site_name'))
        if name_pattern:
            filename = resolve_config_filename(name_pattern, entry.get('site_name'), index)
            out_path = output_dir / filename
        else:
            out_path = output_dir / f'{name_prefix}_{safe_name}.json'
        paths.append(write_json_config(out_path, entry['json']))
    return paths
