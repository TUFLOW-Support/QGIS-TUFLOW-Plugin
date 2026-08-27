"""
QgsProcessingParameterLineStyle — a custom QgsProcessingParameterDefinition that
lets users pick a line style (colour, width, and pen style) inside a
QgsProcessingAlgorithm.

The parameter value is a JSON string so it survives save/load of .model3 files
and batch-processing scripts.

Usage (algorithm side)
----------------------
from processing_parameter_linestyle import QgsProcessingParameterLineStyle
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt

class MyAlgorithm(QgsProcessingAlgorithm):
    LINE = "LINE"

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterLineStyle(
                self.LINE,
                self.tr("Border style"),
                defaultColor=QColor("red"),
                defaultWidth=0.5,
                defaultPenStyle=Qt.SolidLine,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        raw   = self.parameterAsString(parameters, self.LINE, context)
        color = QgsProcessingParameterLineStyle.valueAsColor(raw)
        width = QgsProcessingParameterLineStyle.valueAsWidth(raw)
        style = QgsProcessingParameterLineStyle.valueAsPenStyle(raw)
        feedback.pushInfo(
            f"Line: {color.name(QColor.HexArgb)}  "
            f"width={width}  style={style}"
        )
        return {}

Widget wrapper registration
---------------------------
Call ``QgsProcessingParameterLineStyle.registerWidget()`` once at plugin load time:

    from processing_parameter_linestyle import QgsProcessingParameterLineStyle
    QgsProcessingParameterLineStyle.registerWidget()
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
from qgis.PyQt.QtCore import Qt, qVersion
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QDoubleSpinBox,
    QComboBox,
    QLabel,
)


# ── Pen-style catalogue ───────────────────────────────────────────────────────

# Ordered list of (Qt.PenStyle, human-readable label) pairs shown in the combo.
_PEN_STYLES: list[tuple[Qt.PenStyle, str]] = [
    (Qt.PenStyle.SolidLine,      "Solid"),
    (Qt.PenStyle.DashLine,       "Dash"),
    (Qt.PenStyle.DotLine,        "Dot"),
    (Qt.PenStyle.DashDotLine,    "Dash-Dot"),
    (Qt.PenStyle.DashDotDotLine, "Dash-Dot-Dot"),
]

if qVersion() >= '6.0':
    _PEN_STYLE_BY_INT: dict[int, Qt.PenStyle] = {s.value: s for s, _ in _PEN_STYLES}
else:
    _PEN_STYLE_BY_INT: dict[int, Qt.PenStyle] = {int(s): s for s, _ in _PEN_STYLES}


# ── Serialisation helpers ─────────────────────────────────────────────────────

def _to_str(
    color: QColor,
    width: float,
    pen_style: Qt.PenStyle,
) -> str:
    """Serialise line-style properties to a compact JSON string."""
    return json.dumps(
        {
            "color": color.name(),
            "width": width,
            "penStyle": pen_style.value if qVersion() >= '6.0' else int(pen_style),
        }
    )


def _str_to_color(value: str) -> QColor:
    try:
        return QColor(json.loads(value).get("color", "#ff000000"))
    except (json.JSONDecodeError, TypeError, KeyError):
        return QColor("black")


def _str_to_width(value: str) -> float:
    try:
        return float(json.loads(value).get("width", 1.0))
    except (json.JSONDecodeError, TypeError, KeyError):
        return 1.0


def _str_to_pen_style(value: str) -> Qt.PenStyle:
    try:
        raw = int(json.loads(value).get("penStyle", Qt.PenStyle.SolidLine.value if qVersion() >= '6.0' else int(Qt.PenStyle.SolidLine)))
        return _PEN_STYLE_BY_INT.get(raw, Qt.PenStyle.SolidLine)
    except (json.JSONDecodeError, TypeError, KeyError):
        return Qt.SolidLine


# ── Parameter definition ──────────────────────────────────────────────────────

class QgsProcessingParameterLineStyle(QgsProcessingParameterDefinition):
    """A processing parameter that stores a line colour, width, and pen style."""

    TYPE = "linestyle"

    def __init__(
        self,
        name: str,
        description: str = "",
        defaultColor: QColor | None = None,
        defaultWidth: float = 1.0,
        defaultPenStyle: Qt.PenStyle = Qt.PenStyle.SolidLine,
        optional: bool = False,
    ):
        super().__init__(name, description, None, optional)
        color = defaultColor if defaultColor is not None else QColor("black")
        self.setDefaultValue(_to_str(color, defaultWidth, defaultPenStyle))

    # ------------------------------------------------------------------
    # QgsProcessingParameterDefinition interface
    # ------------------------------------------------------------------

    def clone(self) -> "QgsProcessingParameterLineStyle":
        copy = QgsProcessingParameterLineStyle(self.name(), self.description())
        copy.setDefaultValue(self.defaultValue())
        copy.setFlags(self.flags())
        return copy

    def type(self) -> str:
        return self.TYPE

    def checkValueIsAcceptable(self, value, context: QgsProcessingContext | None = None) -> bool:  # noqa: N802
        if value is None:
            return self.flags() & QgsProcessingParameterDefinition.FlagOptional
        if isinstance(value, str):
            try:
                json.loads(value)
                return True
            except (json.JSONDecodeError, TypeError):
                return False
        return False

    def valueAsPythonString(self, value, context: QgsProcessingContext) -> str:  # noqa: N802
        return repr(str(value))

    def asPythonString(self) -> str:  # noqa: N802
        return (
            f"QgsProcessingParameterLineStyle('{self.name()}', '{self.description()}')"
        )

    # ------------------------------------------------------------------
    # Convenience helpers for algorithm authors
    # ------------------------------------------------------------------

    @staticmethod
    def valueAsColor(value: str) -> QColor:
        """Return the QColor stored in the parameter value string."""
        return _str_to_color(str(value))

    @staticmethod
    def valueAsWidth(value: str) -> float:
        """Return the line width stored in the parameter value string."""
        return _str_to_width(str(value))

    @staticmethod
    def valueAsPenStyle(value: str) -> Qt.PenStyle:
        """Return the Qt.PenStyle stored in the parameter value string."""
        return _str_to_pen_style(str(value))

    # ------------------------------------------------------------------
    # Widget registration
    # ------------------------------------------------------------------

    @classmethod
    def registerWidget(cls) -> None:
        """Register the custom widget wrapper with the Processing GUI registry.

        Call this once during plugin initialisation.
        """
        QgsGui.processingGuiRegistry().addParameterWidgetFactory(
            _LineStyleWidgetFactory()
        )


# ── Widget ────────────────────────────────────────────────────────────────────

class _LineStyleWidget(QWidget):
    """Compact row: colour button | width spin | pen-style combo."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Colour
        self._color_btn = QgsColorButton(self)
        self._color_btn.setAllowOpacity(True)
        self._color_btn.setShowNoColor(False)
        self._color_btn.setColor(QColor("black"))
        self._color_btn.setMinimumWidth(40)
        self._color_btn.setToolTip("Line colour")
        layout.addWidget(self._color_btn)

        # Width
        layout.addWidget(QLabel("w:", self))
        self._width_spin = QDoubleSpinBox(self)
        self._width_spin.setRange(0.0, 999.0)
        self._width_spin.setDecimals(2)
        self._width_spin.setSingleStep(0.1)
        self._width_spin.setValue(1.0)
        self._width_spin.setToolTip("Line width")
        layout.addWidget(self._width_spin)

        # Pen style
        self._style_combo = QComboBox(self)
        for pen_style, label in _PEN_STYLES:
            self._style_combo.addItem(label, pen_style)
        self._style_combo.setToolTip("Line style")
        layout.addWidget(self._style_combo, stretch=1)

    # -- getters -----------------------------------------------------------

    def color(self) -> QColor:
        return self._color_btn.color()

    def width(self) -> float:
        return self._width_spin.value()

    def penStyle(self) -> Qt.PenStyle:
        return self._style_combo.currentData()

    # -- setters -----------------------------------------------------------

    def setColor(self, color: QColor) -> None:
        self._color_btn.setColor(color)

    def setWidth(self, width: float) -> None:
        self._width_spin.setValue(width)

    def setPenStyle(self, style: Qt.PenStyle) -> None:
        idx = self._style_combo.findData(style)
        if idx >= 0:
            self._style_combo.setCurrentIndex(idx)


# ── Widget wrapper ────────────────────────────────────────────────────────────

class _LineStyleWidgetWrapper(QgsAbstractProcessingParameterWidgetWrapper):
    """Bridges _LineStyleWidget to the Processing GUI framework."""

    def __init__(self, parameter, dialog_type, parent=None):
        super().__init__(parameter, dialog_type, parent)

    def createWidget(self) -> QWidget:  # noqa: N802
        self._widget = _LineStyleWidget()
        self._apply(self.parameterDefinition().defaultValue())
        return self._widget

    def postInitialize(self, wrappers) -> None:  # noqa: N802
        pass

    def setWidgetValue(self, value, context: QgsProcessingContext) -> None:  # noqa: N802
        self._apply(value)

    def widgetValue(self):  # noqa: N802
        return _to_str(
            self._widget.color(),
            self._widget.width(),
            self._widget.penStyle(),
        )

    def parameterLabelString(self) -> str:  # noqa: N802
        return self.parameterDefinition().description()

    # -- internal ----------------------------------------------------------

    def _apply(self, value) -> None:
        if not value:
            return
        s = str(value)
        self._widget.setColor(_str_to_color(s))
        self._widget.setWidth(_str_to_width(s))
        self._widget.setPenStyle(_str_to_pen_style(s))


# ── Widget factory ────────────────────────────────────────────────────────────

class _LineStyleWidgetFactory(QgsProcessingParameterWidgetFactoryInterface):
    """Factory that tells the Processing GUI how to create line-style widgets."""

    def parameterType(self) -> str:  # noqa: N802
        return QgsProcessingParameterLineStyle.TYPE

    def createWidgetWrapper(self, parameter, type_, parent=None):  # noqa: N802
        return _LineStyleWidgetWrapper(parameter, type_, parent)

    def compatibleParameterTypes(self) -> list[str]:  # noqa: N802
        return [QgsProcessingParameterLineStyle.TYPE]

    def compatibleOutputTypes(self) -> list[str]:  # noqa: N802
        return []
