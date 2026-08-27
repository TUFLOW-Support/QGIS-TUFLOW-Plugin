"""
QgsProcessingParameterJson — a custom QgsProcessingParameterDefinition that
stores a JSON value and presents it as an editable tree inside a
QgsProcessingAlgorithm dialog.

Features
--------
* Displays any JSON (object, array, or scalar) as a collapsible tree.
* Inline editing of values directly in the tree.
* Type selector per leaf node: string, number, boolean, null.
* Toolbar buttons to add object keys, append array items, and delete nodes.
* "Load from file" button to populate the tree from a .json file on disk.
* Full round-trip: tree ↔ JSON string stored as the parameter value.

Usage (algorithm side)
----------------------
from processing_parameter_json import QgsProcessingParameterJson

class MyAlgorithm(QgsProcessingAlgorithm):
    JSON = "JSON"

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterJson(
                self.JSON,
                self.tr("Configuration"),
                defaultValue={"key": "value", "count": 1},
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        import json
        raw  = self.parameterAsString(parameters, self.JSON, context)
        data = json.loads(raw)
        feedback.pushInfo(str(data))
        return {}

Widget wrapper registration
---------------------------
Call once at plugin load time:

    from processing_parameter_json import QgsProcessingParameterJson
    QgsProcessingParameterJson.registerWidget()
"""

from __future__ import annotations

import json
from typing import Any

from qgis.core import Qgis
from qgis.core import (
    QgsProcessingParameterDefinition,
    QgsProcessingContext,
)
from qgis.gui import (
    QgsAbstractProcessingParameterWidgetWrapper,
    QgsProcessingParameterWidgetFactoryInterface,
    QgsGui,
)

from qgis.PyQt.QtGui import QColor

from .processing_parameter_attach_signal import ProcessingParameterAttachSignalMixin
from ..widgets.json_viewer import JsonWidget


FLAG_OPTIONAL = Qgis.ProcessingParameterFlag.Optional if Qgis.QGIS_VERSION_INT >= 33600 else QgsProcessingParameterDefinition.FlagOptional


# ── Serialisation helpers ─────────────────────────────────────────────────────

def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=None)


def _loads(text: str) -> Any:
    return json.loads(text)


# ── Parameter definition ──────────────────────────────────────────────────────

class QgsProcessingParameterJson(QgsProcessingParameterDefinition):
    """A processing parameter that stores an arbitrary JSON value."""

    TYPE = "json"

    def __init__(
        self,
        name: str,
        description: str = "",
        defaultValue: Any = None,
        optional: bool = False,
    ):
        super().__init__(name, description, None, optional)
        if defaultValue is None:
            default_str = "{}"
        elif isinstance(defaultValue, str):
            # Validate it's actually JSON; fall back to wrapping as a string
            try:
                _loads(defaultValue)
                default_str = defaultValue
            except (json.JSONDecodeError, TypeError):
                default_str = _dumps(defaultValue)
        else:
            default_str = _dumps(defaultValue)
        self.setDefaultValue(default_str)

    # ------------------------------------------------------------------
    # QgsProcessingParameterDefinition interface
    # ------------------------------------------------------------------

    def clone(self) -> "QgsProcessingParameterJson":
        copy = QgsProcessingParameterJson(self.name(), self.description())
        copy.setDefaultValue(self.defaultValue())
        copy.setFlags(self.flags())
        return copy

    def type(self) -> str:
        return self.TYPE

    def checkValueIsAcceptable(self, value, context: QgsProcessingContext | None = None) -> bool:  # noqa: N802
        if value is None:
            return bool(self.flags() & FLAG_OPTIONAL)
        if not isinstance(value, str):
            return False
        try:
            _loads(value)
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    def valueAsPythonString(self, value, context: QgsProcessingContext) -> str:  # noqa: N802
        return repr(str(value))

    def asPythonString(self) -> str:  # noqa: N802
        return f"QgsProcessingParameterJson('{self.name()}', '{self.description()}')"

    # ------------------------------------------------------------------
    # Convenience helper
    # ------------------------------------------------------------------

    @staticmethod
    def valueAsJson(value: str) -> Any:
        """Parse the raw parameter string back to a Python object."""
        return _loads(str(value))

    # ------------------------------------------------------------------
    # Widget registration
    # ------------------------------------------------------------------

    @classmethod
    def registerWidget(cls) -> None:
        """Register the widget factory. Call once at plugin load time."""
        QgsGui.processingGuiRegistry().addParameterWidgetFactory(
            JsonWidgetFactory()
        )


# ── Widget wrapper ────────────────────────────────────────────────────────────

class JsonWidgetWrapper(QgsAbstractProcessingParameterWidgetWrapper, ProcessingParameterAttachSignalMixin):

    def __init__(self, parameter, dialog_type, parent=None):
        super().__init__(parameter, dialog_type, parent)

    def createWidget(self) -> QWidget:  # noqa: N802
        self.widget = JsonWidget()
        self.widget.highlight_changes = True
        self.widget.highlight_colour = QColor('#fcd465')
        default = self.parameterDefinition().defaultValue()
        if default:
            self.widget.setValue(str(default))
        return self.widget

    def postInitialize(self, wrappers):
        setup_callbacks = self.setupCallbacks(wrappers)
        for callback, wrapper in setup_callbacks:
            callback(self, wrapper, wrappers)

    def setWidgetValue(self, value, context: QgsProcessingContext) -> None:  # noqa: N802
        if value is not None:
            self.widget.setValue(str(value))

    def widgetValue(self) -> str:  # noqa: N802
        return self.widget.value()

    def parameterLabelString(self) -> str:  # noqa: N802
        return self.parameterDefinition().description()


# ── Widget factory ────────────────────────────────────────────────────────────

class JsonWidgetFactory(QgsProcessingParameterWidgetFactoryInterface):

    def parameterType(self) -> str:  # noqa: N802
        return QgsProcessingParameterJson.TYPE

    def createWidgetWrapper(self, parameter, type_, parent=None):  # noqa: N802
        return JsonWidgetWrapper(parameter, type_, parent)

    def compatibleParameterTypes(self) -> list[str]:  # noqa: N802
        return [QgsProcessingParameterJson.TYPE]

    def compatibleOutputTypes(self) -> list[str]:  # noqa: N802
        return []
