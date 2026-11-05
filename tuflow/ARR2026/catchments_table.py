"""
"Catchments" table widget for the ARR2026 dock.

One row per catchment, add/remove via +/- buttons - same convention as
``climate_change_scenarios.ClimateChangeScenTable``. Each row independently chooses a
"Catchment Location" - either a GIS layer polygon feature, or a latitude/longitude.
"""

from __future__ import annotations

from typing import Optional

from qgis.PyQt.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHBoxLayout, QLineEdit, QStackedWidget, QTableWidget, QWidget,
)
from qgis.core import QgsVectorLayer

from ..compatibility_routines import (
    QT_ABSTRACT_ITEM_VIEW_SELECT_ROWS, QT_ABSTRACT_ITEM_VIEW_SINGLE_SELECTION, 
)
from ..toc.toc import findAllVectorLyrsWithGroups, tuflowqgis_find_layer
from .arr_shared_functionality import (
    is_polygon_layer, populate_feature_combobox, populate_layer_combobox, _LAYER_ID_ROLE,
)

# Column indices
COL_NAME = 0
COL_CATCHMENT_METHOD = 1
COL_CATCHMENT_VALUE = 2
COLUMN_COUNT = 3
COLUMN_HEADERS = ['Name', 'Catchment Method', 'Catchment Location']

# "Catchment Location" method combobox options/indices
CATCHMENT_METHOD_GIS = 0
CATCHMENT_METHOD_LAT_LONG = 1
CATCHMENT_METHOD_OPTIONS = ['GIS Layer', 'Latitude/Longitude']

class LayerFeatureWidget(QWidget):
    """A "GIS layer" + "feature" combobox pair, used for GIS catchment boundary features.

    The "layer" combobox lists every vector layer in the current QGIS project matching
    ``is_valid_layer`` (grouped/labelled to match the layer tree, via
    ``toc.toc.findAllVectorLyrsWithGroups``). Selecting a layer repopulates the "feature"
    combobox with every one of that layer's features.
    """

    def __init__(self, is_valid_layer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._is_valid_layer = is_valid_layer

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)

        self.layer_combobox = QComboBox()
        self.feature_combobox = QComboBox()
        layout.addWidget(self.layer_combobox, 1)
        layout.addWidget(self.feature_combobox, 1)

        self.layer_combobox.currentIndexChanged.connect(self._on_layer_changed)
        self.refresh_layers()

    def refresh_layers(self) -> None:
        """(Re)populates ``layer_combobox`` with every matching vector layer currently loaded
        in the QGIS project, preserving the current selection if it's still valid."""

        layers = (
            (layer_toc, layer_id, tuflowqgis_find_layer(layer_id, search_type='layerid'))
            for layer_toc, layer_id in findAllVectorLyrsWithGroups()
        )
        populate_layer_combobox(
            self.layer_combobox, layers, self._is_valid_layer, empty_label='(no layer selected)'
        )
        self._on_layer_changed()

    def _on_layer_changed(self, *_args) -> None:
        """``layer_combobox.currentIndexChanged``: rebuilds ``feature_combobox`` to match the
        newly-selected layer, preserving the current feature selection if it's still valid."""

        layer = self.current_layer()
        populate_feature_combobox(
            self.feature_combobox, layer.getFeatures() if layer is not None else ()
        )

    def current_layer(self) -> Optional[QgsVectorLayer]:
        """Returns the currently selected ``QgsVectorLayer``, or ``None`` if nothing valid is
        selected."""

        layer_id = self.layer_combobox.currentData(_LAYER_ID_ROLE)
        if not layer_id:
            return None
        return tuflowqgis_find_layer(layer_id, search_type='layerid')

    def current_feature_id(self) -> Optional[int]:
        """Returns the currently selected feature's id, or ``None`` if nothing is selected."""

        return self.feature_combobox.currentData()

    def set_selection(self, layer_id: Optional[str], feature_id: Optional[int] = None) -> None:
        """Selects ``layer_id`` (and, once its features have loaded, ``feature_id``) if still
        valid.
        Used to restore a previously saved selection (see ``populate_dock_from_json.PopulateARRDockFromjson``)."""

        if layer_id is not None:
            index = self.layer_combobox.findData(layer_id)
            if index >= 0:
                self.layer_combobox.setCurrentIndex(index)
        if feature_id is not None:
            index = self.feature_combobox.findData(feature_id)
            if index >= 0:
                self.feature_combobox.setCurrentIndex(index)


class LatLongWidget(QWidget):
    """A latitude/longitude spinbox pair.
    Used for lat/long catchment locations."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)

        self.lat_spinbox = QDoubleSpinBox()
        self.lat_spinbox.setDecimals(6)
        self.lat_spinbox.setMinimum(-90.0)
        self.lat_spinbox.setMaximum(90.0)
        self.lat_spinbox.setPrefix('Lat: ')

        self.long_spinbox = QDoubleSpinBox()
        self.long_spinbox.setDecimals(6)
        self.long_spinbox.setMinimum(-180.0)
        self.long_spinbox.setMaximum(180.0)
        self.long_spinbox.setPrefix('Long: ')

        layout.addWidget(self.lat_spinbox, 1)
        layout.addWidget(self.long_spinbox, 1)


class CatchmentLocationCell(QStackedWidget):
    """A row's "Catchment Location" cell - either a :class:`LayerFeatureWidget` (polygon
    layers) or a :class:`LatLongWidget`, switched via that row's "Catchment Method" combobox
    (see :data:`CATCHMENT_METHOD_GIS`/:data:`CATCHMENT_METHOD_LAT_LONG`)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.gis_widget = LayerFeatureWidget(is_polygon_layer)
        self.latlong_widget = LatLongWidget()
        self.addWidget(self.gis_widget)      # index CATCHMENT_METHOD_GIS
        self.addWidget(self.latlong_widget)  # index CATCHMENT_METHOD_LAT_LONG


class CatchmentsTable(QTableWidget):
    """Table widget for the ARR2026 "Catchments" input - one row per catchment, each with an
    independently selectable catchment location method (GIS layer feature or
    latitude/longitude).

    Rows are added/removed via :meth:`add_catchment`/:meth:`remove_selected_catchment`, the
    same convention as ``climate_change_scenarios.ClimateChangeScenTable``.
    """

    def __init__(self, parent=None) -> None:
        QTableWidget.__init__(self, parent)
        self.setColumnCount(COLUMN_COUNT)
        self.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QT_ABSTRACT_ITEM_VIEW_SELECT_ROWS)
        self.setSelectionMode(QT_ABSTRACT_ITEM_VIEW_SINGLE_SELECTION)

        self.setStyleSheet("""
                QTableWidget::item:selected {
                    background-color: palette(base);
                    color: palette(text);
                }
            """)

    def add_catchment(self) -> int:
        """Appends a new catchment row, defaulting to "GIS Layer", and selects it.

        :returns: the new row's index.
        """

        row = self.rowCount()
        self.insertRow(row)

        name_edit = QLineEdit(f'Catchment {row + 1}')
        self.setCellWidget(row, COL_NAME, name_edit)

        catchment_value = CatchmentLocationCell()
        catchment_method = QComboBox()
        catchment_method.addItems(CATCHMENT_METHOD_OPTIONS)
        catchment_method.currentIndexChanged.connect(catchment_value.setCurrentIndex)
        self.setCellWidget(row, COL_CATCHMENT_METHOD, catchment_method)
        self.setCellWidget(row, COL_CATCHMENT_VALUE, catchment_value)

        self.selectRow(row)
        return row

    def remove_selected_catchment(self) -> None:
        """Removes the currently selected row, if any row is selected."""

        row = self.currentRow()
        if row >= 0:
            self.removeRow(row)

    def refresh_layer_comboboxes(self) -> None:
        """Refreshes every row's "Catchment Location" GIS layer combobox to match the QGIS
        project's currently loaded layers. Connected to the same project signals used elsewhere
        in the dock (layer add/remove/rename/reorder/data source change) - see
        ``Arr2026Dock._connect_signals``."""

        for row in range(self.rowCount()):
            catchment_value = self.cellWidget(row, COL_CATCHMENT_VALUE)
            if catchment_value is not None:
                catchment_value.gis_widget.refresh_layers()

    # ------------------------------------------------------------------
    # Row data getters/setters
    # ------------------------------------------------------------------

    def catchment_name(self, row: int) -> str:
        """Returns ``row``'s "Name" cell text."""

        edit = self.cellWidget(row, COL_NAME)
        return edit.text().strip() if edit is not None else ''

    def set_catchment_name(self, row: int, name: str) -> None:
        edit = self.cellWidget(row, COL_NAME)
        if edit is not None:
            edit.setText(name)

    def catchment_method(self, row: int) -> int:
        """Returns ``row``'s "Catchment Method" combobox index (:data:`CATCHMENT_METHOD_GIS`/
        :data:`CATCHMENT_METHOD_LAT_LONG`)."""

        combobox = self.cellWidget(row, COL_CATCHMENT_METHOD)
        return combobox.currentIndex() if combobox is not None else CATCHMENT_METHOD_GIS

    def set_catchment_method(self, row: int, method: int) -> None:
        combobox = self.cellWidget(row, COL_CATCHMENT_METHOD)
        if combobox is not None:
            combobox.setCurrentIndex(method)

    def catchment_location(self, row: int) -> dict:
        """Returns ``row``'s "Catchment Location" as either:
            - ``{"method": "gis", "layer": QgsVectorLayer|None, "feature_id": int|None}``, or
            - ``{"method": "latlong", "latitude": float, "longitude": float}``.
        """

        value_cell: Optional[CatchmentLocationCell] = self.cellWidget(row, COL_CATCHMENT_VALUE)
        if value_cell is None:
            return {"method": "gis", "layer": None, "feature_id": None}
        if self.catchment_method(row) == CATCHMENT_METHOD_LAT_LONG:
            widget = value_cell.latlong_widget
            return {
                "method": "latlong",
                "latitude": widget.lat_spinbox.value(),
                "longitude": widget.long_spinbox.value(),
            }
        widget = value_cell.gis_widget
        return {"method": "gis", "layer": widget.current_layer(), "feature_id": widget.current_feature_id()}

    def set_catchment_latlong(self, row: int, latitude: float, longitude: float) -> None:
        value_cell: Optional[CatchmentLocationCell] = self.cellWidget(row, COL_CATCHMENT_VALUE)
        if value_cell is None:
            return
        value_cell.latlong_widget.lat_spinbox.setValue(latitude)
        value_cell.latlong_widget.long_spinbox.setValue(longitude)

    def set_catchment_gis_selection(self, row: int, layer_id: Optional[str], feature_id: Optional[int] = None) -> None:
        value_cell: Optional[CatchmentLocationCell] = self.cellWidget(row, COL_CATCHMENT_VALUE)
        if value_cell is None:
            return
        value_cell.gis_widget.set_selection(layer_id, feature_id)
