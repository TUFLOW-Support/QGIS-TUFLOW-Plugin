from datetime import datetime, timezone, timedelta

import numpy as np
from qgis.core import QgsDateTimeRange
from qgis.gui import QgisInterface
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QDockWidget, QToolButton, QDoubleSpinBox, QComboBox, QDateTimeEdit, QSlider, QWidget, QPushButton
from qgis.PyQt.QtCore import QDateTime, QDate, QTime, QSettings

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ..compatibility_routines import QT_TIMESPEC_UTC
else:
    from tuflow.compatibility_routines import QT_TIMESPEC_UTC

import logging
logger = logging.getLogger('tuflow_viewer')


class TemporalControllerWidget:

    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self._controller = self._get_temporal_controller_dock(self.iface)
        self._cur_time = None
        if not self._controller:
            return
        self._step = self._controller.findChild(QDoubleSpinBox, 'mStepSpinBox')
        if not self._step:
            logger.error('Could not find temporal controller timestep spinbox.')
            return
        self._cbo_units = self._controller.findChild(QComboBox, 'mTimeStepsComboBox')
        if not self._cbo_units:
            logger.error('Could not find temporal controller units combobox.')
            return
        self._start_time_edit = self._controller.findChild(QDateTimeEdit, 'mStartDateTime')
        if not self._start_time_edit:
            logger.error('Could not find temporal controller start time edit.')
            return
        self._end_time_edit = self._controller.findChild(QDateTimeEdit, 'mEndDateTime')
        if not self._end_time_edit:
            logger.error('Could not find temporal controller end time edit.')
            return
        self._time_slider = self._controller.findChild(QSlider, 'mAnimationSlider')
        if not self._time_slider:
            logger.error('Could not find temporal controller time slider.')
            return
        anim_controller = self._controller.findChild(QWidget, 'mAnimationController')
        self._play_btn = anim_controller.findChild(QPushButton, 'mForwardButton')
        self._pause_btn = anim_controller.findChild(QPushButton, 'mPauseButton')
        self._next_btn = anim_controller.findChild(QPushButton, 'mNextButton')
        self._rewind_btn = anim_controller.findChild(QPushButton, 'mRewindButton')

    @property
    def start_time(self) -> datetime:
        if self._controller:
            return self._start_time_edit.dateTime().toPyDateTime().replace(tzinfo=timezone.utc)
        return datetime(1970, 1, 1, tzinfo=timezone.utc)

    @start_time.setter
    def start_time(self, value: datetime):
        if self._controller:
            self._start_time_edit.setDateTime(self._to_qdatetime(value))

    @property
    def end_time(self) -> datetime:
        if self._controller:
            return self._end_time_edit.dateTime().toPyDateTime().replace(tzinfo=timezone.utc)
        return datetime(1970, 1, 1, tzinfo=timezone.utc)

    @end_time.setter
    def end_time(self, value: datetime):
        if self._controller:
            self._end_time_edit.setDateTime(self._to_qdatetime(value))

    @property
    def timestep(self) -> float:
        if self._controller:
            return self._step.value()
        return 0.

    @timestep.setter
    def timestep(self, value: float):
        if self._controller:
            self._step.setValue(value)

    @property
    def units(self) -> str:
        if self._controller:
            return self._cbo_units.currentText()
        return 'seconds'

    @units.setter
    def units(self, value: str):
        if self._controller:
            self._cbo_units.setCurrentText(value)

    def currentTime(self) -> datetime:
        if not self._controller:
            return self._cur_time
        try:
            td = eval(f'timedelta({self.units}={self._time_slider.value() * self.timestep})')
        except TypeError:
            if self.units == 'months':
                td = timedelta(days=self._time_slider.value() * self.timestep * 30)
            elif self.units == 'years':
                td = timedelta(days=self._time_slider.value() * self.timestep * 365)
            elif self.units == 'decades':
                td = timedelta(days=self._time_slider.value() * self.timestep * 365 * 10)
            elif self.units == 'centuries':
                td = timedelta(days=self._time_slider.value() * self.timestep * 365 * 100)
            else:
                return self.timestep
        return self.start_time + td

    def setCurrentTime(self, dt: datetime):
        if not self._controller:
            self._cur_time = dt
            start_time = QDateTime(QDate(dt.year, dt.month, dt.day), QTime(dt.hour, dt.minute, dt.second), QT_TIMESPEC_UTC)
            end_time = start_time.addSecs(3600)
            iface.mapCanvas().setTemporalRange(QgsDateTimeRange(start_time, end_time))
            return
        try:
            if dt > self.end_time or dt < self.start_time:
                return
        except TypeError:
            return
        timedelta = dt - self.start_time
        if self.units == 'seconds':
            time_sec = timedelta.total_seconds()
        elif self.units == 'minutes':
            time_sec = timedelta.total_seconds() / 60.0
        elif self.units == 'hours':
            time_sec = timedelta.total_seconds() / 3600.0
        elif self.units == 'days':
            time_sec = timedelta.days
        elif self.units == 'weeks':
            time_sec = timedelta.days / 7.0
        elif self.units == 'months':
            time_sec = timedelta.days / 30.0
        elif self.units == 'years':
            time_sec = timedelta.days / 365.0
        elif self.units == 'decades':
            time_sec = timedelta.days / (365.0 * 10)
        elif self.units == 'centuries':
            time_sec = timedelta.days / (365.0 * 100)
        else:
            return
        i = time_sec / self.timestep
        timesteps = np.arange(0, i + 2) * self.timestep
        diffs = timesteps - time_sec
        idx = np.argmin(np.abs(diffs))
        self._time_slider.setValue(idx)

    def finished(self) -> bool:
        if self._controller:
            return self._time_slider.value() == self._time_slider.maximum()
        return True

    def rewind(self):
        if self._controller:
            if self._time_slider.value() != 0:
                self._rewind_btn.click()

    def play(self):
        if self._controller:
            if self._time_slider.value() != self._time_slider.maximum():
                self._play_btn.click()

    def next_frame(self):
        if self._controller:
            if self._time_slider.value() != self._time_slider.maximum():
                self._next_btn.click()

    def show(self):
        if self._controller:
            self._controller.show()

    def activate_temporal_navigation(self):
        if self._controller:
            tool_btn = self._controller.findChild(QToolButton, 'mNavigationAnimated')
            if tool_btn and not tool_btn.isChecked():
                tool_btn.click()

    @staticmethod
    def _to_qdatetime(dt: datetime) -> QDateTime:
        if dt.tzinfo is None:
            tz = timezone.utc
            dt = dt.replace(tzinfo=tz)
        else:
            dt = dt.astimezone(timezone.utc)
        return QDateTime.fromSecsSinceEpoch(int(dt.timestamp()), QT_TIMESPEC_UTC)

    @staticmethod
    def _get_temporal_controller_dock(iface: QgisInterface) -> QDockWidget:
        """Retrieve the temporal controller dock widget."""
        return iface.mainWindow().findChild(QDockWidget, 'Temporal Controller')


temporal_controller = TemporalControllerWidget(iface)
