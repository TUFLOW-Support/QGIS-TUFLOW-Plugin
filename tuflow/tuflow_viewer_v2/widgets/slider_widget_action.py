import numpy as np
from qgis.PyQt.QtWidgets import QSlider, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QWidgetAction, QDoubleSpinBox
from qgis.PyQt.QtCore import QSettings, pyqtSignal

from .menu_action_widget import MenuActionWidget

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...compatibility_routines import QT_HORIZONTAL, QT_ABSTRACT_SPIN_BOX_NO_BUTTONS
else:
    from tuflow.compatibility_routines import QT_HORIZONTAL, QT_ABSTRACT_SPIN_BOX_NO_BUTTONS


class SliderWidget(QWidget):
    value_changed = pyqtSignal(float)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.layout = QHBoxLayout()
        self.slider = QSlider()
        self.slider.setOrientation(QT_HORIZONTAL)
        self.slider.setRange(0, 100)
        self.slider.sliderMoved.connect(self._slider_moved)
        self.spinbox = QDoubleSpinBox()
        self.spinbox.setButtonSymbols(QT_ABSTRACT_SPIN_BOX_NO_BUTTONS)
        self.spinbox.editingFinished.connect(self._spinbox_edited)
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.spinbox)
        self.setLayout(self.layout)
        self.slider_min = 0.
        self.slider_max = 1.

    def _slider_moved(self, value: int):
        f = value / 100.
        f = self.slider_min + f * (self.slider_max - self.slider_min)
        self.spinbox.setValue(f)
        self.value_changed.emit(self.spinbox.value())

    def _spinbox_edited(self):
        value = self.spinbox.value()
        i = (value - self.slider_min) / (self.slider_max - self.slider_min)
        i = int(100 * i)
        self.slider.setValue(i)
        self.value_changed.emit(value)


class SliderWidgetAction(QWidgetAction):
    value_changed = pyqtSignal(float)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._widget = SliderWidget(parent)
        self._widget.value_changed.connect(self.value_changed.emit)
        self.setDefaultWidget(self._widget)

    def value(self) -> float:
        return self._widget.spinbox.value()

    def set_value(self, value: float):
        self._widget.spinbox.setValue(value)
        self._widget._spinbox_edited()

    def set_minimum(self, value: float):
        self._widget.spinbox.setMinimum(value)
        self._widget.slider_min = value

    def set_maximum(self, value: float):
        self._widget.spinbox.setMaximum(value)
        self._widget.slider_max = value

    def set_slider_min(self, value: float):
        self._widget.slider_min = value

    def set_slider_max(self, value: float):
        self._widget.slider_max = value
