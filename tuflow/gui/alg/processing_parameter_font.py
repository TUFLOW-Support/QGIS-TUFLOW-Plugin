"""
QgsProcessingParameterFont — a custom QgsProcessingParameterDefinition that
lets users pick a font (family, size) and a colour inside a QgsProcessingAlgorithm.

The parameter value is a JSON string that contains both font properties and an
RGBA colour, so it survives save/load of .model3 files and batch-processing scripts.

Usage (algorithm side)
----------------------
from processing_parameter_font import QgsProcessingParameterFont

class MyAlgorithm(QgsProcessingAlgorithm):
    FONT = "FONT"

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFont(
                self.FONT,
                self.tr("Label font"),
                defaultValue=QFont("Arial", 12),
                defaultColor=QColor("black"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        raw   = self.parameterAsString(parameters, self.FONT, context)
        font  = QgsProcessingParameterFont.valueAsFont(raw)
        color = QgsProcessingParameterFont.valueAsColor(raw)
        feedback.pushInfo(
            f"Font: {font.family()} {font.pointSize()}pt  "
            f"Colour: {color.name(QColor.HexArgb)}"
        )
        return {}

Widget wrapper registration
---------------------------
Call ``QgsProcessingParameterFont.registerWidget()`` once at plugin load time
so the Processing GUI picks up the custom widget automatically:

    from processing_parameter_font import QgsProcessingParameterFont
    QgsProcessingParameterFont.registerWidget()
"""

from __future__ import annotations

import json

from qgis.core import (
    QgsProcessingParameterDefinition,
    QgsProcessingContext,
)
from qgis.gui import (
    QgsAbstractProcessingParameterWidgetWrapper,
    QgsColorButton,
    QgsProcessingParameterWidgetFactoryInterface,
    QgsGui,
)
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QFontComboBox, QSpinBox, QLabel


# ── Serialisation helpers ─────────────────────────────────────────────────────

def _font_to_str(font: QFont, color: QColor | None = None) -> str:
    """Serialise a QFont + QColor to a compact JSON string."""
    c = color if color is not None else QColor("black")
    return json.dumps(
        {
            "family": font.family(),
            "pointSize": font.pointSize(),
            "bold": font.bold(),
            "italic": font.italic(),
            "underline": font.underline(),
            "color": c.name(),
        }
    )


def _str_to_font(value: str) -> QFont:
    """Deserialise a QFont from the JSON string produced by _font_to_str."""
    try:
        d = json.loads(value)
        font = QFont(d.get("family", "Arial"))
        font.setPointSize(d.get("pointSize", 10))
        font.setBold(d.get("bold", False))
        font.setItalic(d.get("italic", False))
        font.setUnderline(d.get("underline", False))
        return font
    except (json.JSONDecodeError, TypeError):
        return QFont()


def _str_to_color(value: str) -> QColor:
    """Deserialise a QColor from the JSON string produced by _font_to_str."""
    try:
        d = json.loads(value)
        return QColor(d.get("color", "#ff000000"))
    except (json.JSONDecodeError, TypeError):
        return QColor("black")


# ── Parameter definition ──────────────────────────────────────────────────────

class QgsProcessingParameterFont(QgsProcessingParameterDefinition):
    """A processing parameter that stores a QFont choice and a text colour."""

    # Unique type string used to identify this parameter kind
    TYPE = "font"

    def __init__(
        self,
        name: str,
        description: str = "",
        defaultValue: QFont | None = None,
        defaultColor: QColor | None = None,
        optional: bool = False,
    ):
        super().__init__(name, description, None, optional)
        font = defaultValue if defaultValue is not None else QFont("Arial", 10)
        color = defaultColor if defaultColor is not None else QColor("black")
        self.setDefaultValue(_font_to_str(font, color))

    # ------------------------------------------------------------------
    # QgsProcessingParameterDefinition interface
    # ------------------------------------------------------------------

    def clone(self) -> "QgsProcessingParameterFont":
        copy = QgsProcessingParameterFont(self.name(), self.description())
        copy.setDefaultValue(self.defaultValue())
        copy.setFlags(self.flags())
        return copy

    def type(self) -> str:
        return self.TYPE

    def checkValueIsAcceptable(self, value, context: QgsProcessingContext | None = None) -> bool:  # noqa: N802
        if value is None:
            return self.flags() & QgsProcessingParameterDefinition.FlagOptional
        if isinstance(value, QFont):
            return True
        if isinstance(value, str):
            try:
                json.loads(value)
                return True
            except (json.JSONDecodeError, TypeError):
                return False
        return False

    def valueAsPythonString(self, value, context: QgsProcessingContext) -> str:  # noqa: N802
        if isinstance(value, QFont):
            return repr(_font_to_str(value))
        return repr(str(value))

    def asPythonString(self) -> str:  # noqa: N802
        return (
            f"QgsProcessingParameterFont('{self.name()}', '{self.description()}')"
        )

    # ------------------------------------------------------------------
    # Convenience helpers for algorithm authors
    # ------------------------------------------------------------------

    @staticmethod
    def valueAsFont(value: str | QFont) -> QFont:
        """Convert a raw parameter value to a QFont."""
        if isinstance(value, QFont):
            return value
        return _str_to_font(str(value))

    @staticmethod
    def valueAsColor(value: str | QColor) -> QColor:
        """Convert a raw parameter value to a QColor."""
        if isinstance(value, QColor):
            return value
        return _str_to_color(str(value))

    # ------------------------------------------------------------------
    # Widget registration
    # ------------------------------------------------------------------

    @classmethod
    def registerWidget(cls) -> None:
        """Register the custom widget wrapper with the Processing GUI registry.

        Call this once during plugin initialisation.
        """
        QgsGui.processingGuiRegistry().addParameterWidgetFactory(
            _FontWidgetFactory()
        )


# ── Widget ────────────────────────────────────────────────────────────────────

class _FontWidget(QWidget):
    """Compact widget: font-family combo + point-size spin box + colour button."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._combo = QFontComboBox(self)
        layout.addWidget(self._combo, stretch=1)

        layout.addWidget(QLabel("pt", self))

        self._spin = QSpinBox(self)
        self._spin.setRange(1, 512)
        self._spin.setValue(10)
        layout.addWidget(self._spin)

        self._color_btn = QgsColorButton(self)
        self._color_btn.setAllowOpacity(True)
        self._color_btn.setShowNoColor(False)
        self._color_btn.setColor(QColor("black"))
        self._color_btn.setMinimumWidth(40)
        self._color_btn.setToolTip("Text colour")
        layout.addWidget(self._color_btn)

    def font(self) -> QFont:  # noqa: A003
        f = self._combo.currentFont()
        f.setPointSize(self._spin.value())
        return f

    def setFont(self, font: QFont) -> None:  # noqa: A003
        self._combo.setCurrentFont(font)
        self._spin.setValue(font.pointSize() if font.pointSize() > 0 else 10)

    def color(self) -> QColor:
        return self._color_btn.color()

    def setColor(self, color: QColor) -> None:
        self._color_btn.setColor(color)


# ── Widget wrapper ────────────────────────────────────────────────────────────

class _FontWidgetWrapper(QgsAbstractProcessingParameterWidgetWrapper):
    """Bridges the _FontWidget to the Processing GUI framework."""

    def __init__(self, parameter, dialog_type, parent=None):
        super().__init__(parameter, dialog_type, parent)

    # -- creation ----------------------------------------------------------

    def createWidget(self) -> QWidget:  # noqa: N802
        self._widget = _FontWidget()
        default = self.parameterDefinition().defaultValue()
        if default:
            self._widget.setFont(_str_to_font(str(default)))
            self._widget.setColor(_str_to_color(str(default)))
        return self._widget

    def postInitialize(self, wrappers):  # noqa: N802
        pass

    # -- value interface ---------------------------------------------------

    def setWidgetValue(self, value, context: QgsProcessingContext) -> None:  # noqa: N802
        if isinstance(value, str) and value:
            self._widget.setFont(_str_to_font(value))
            self._widget.setColor(_str_to_color(value))

    def widgetValue(self):  # noqa: N802
        return _font_to_str(self._widget.font(), self._widget.color())

    # -- label -------------------------------------------------------------

    def parameterLabelString(self) -> str:  # noqa: N802
        return self.parameterDefinition().description()


# ── Widget factory ────────────────────────────────────────────────────────────

class _FontWidgetFactory(QgsProcessingParameterWidgetFactoryInterface):
    """Factory that tells the Processing GUI how to create font widgets."""

    def parameterType(self) -> str:  # noqa: N802
        return QgsProcessingParameterFont.TYPE

    def createWidgetWrapper(self, parameter, type_, parent=None):  # noqa: N802
        return _FontWidgetWrapper(parameter, type_, parent)

    def compatibleParameterTypes(self) -> list[str]:  # noqa: N802
        return [QgsProcessingParameterFont.TYPE]

    def compatibleOutputTypes(self) -> list[str]:  # noqa: N802
        return []
