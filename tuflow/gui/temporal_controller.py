from qgis.gui import QgisInterface
from qgis.PyQt.QtWidgets import QDockWidget, QToolButton, QDateTimeEdit, QDoubleSpinBox, QComboBox

from ..compatibility_routines import is_qt6

if is_qt6:
    from qgis.PyQt.QtGui import QAction
else:
    from qgis.PyQt.QtWidgets import QAction


def get_temporal_controller_dock(iface: QgisInterface) -> QDockWidget:
    """Retrieve the temporal controller dock widget."""
    return iface.mainWindow().findChild(QDockWidget, 'Temporal Controller')


def turn_on_temporal_controller_animated_nav(iface: QgisInterface) -> None:
    """Turns on the animated navigation mode on the temporal controller."""
    temporal_controller_dock = get_temporal_controller_dock(iface)
    if temporal_controller_dock:
        tool_btn = temporal_controller_dock.findChild(QToolButton, 'mNavigationAnimated')
        if tool_btn and not tool_btn.isChecked():
            tool_btn.click()


def refresh_temporal_controller_range(iface: QgisInterface) -> None:
    temporal_controller_dock = get_temporal_controller_dock(iface)
    if not temporal_controller_dock:
        return
    a = [x for x in temporal_controller_dock.findChildren(QAction) if x.text() == 'Set to Full Range']
    if a:
        a[0].trigger()


def set_temporal_controller_time_interval(iface: QgisInterface, interval: float, units: str) -> None:
    temporal_controller_dock = get_temporal_controller_dock(iface)
    if not temporal_controller_dock:
        return
    step = temporal_controller_dock.findChild(QDoubleSpinBox, 'mStepSpinBox')
    cbo_units = temporal_controller_dock.findChild(QComboBox, 'mTimeStepsComboBox')
    if not step or not cbo_units:
        return
    step.setValue(interval)
    # if units == 'h':
    #     cbo_units.setCurrentIndex(3)
    # elif units == 's':
    cbo_units.setCurrentIndex(1)
