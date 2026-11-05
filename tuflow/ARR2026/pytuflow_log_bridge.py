# Ports logging from pytuflow into a dock

import logging

# Name of the root logger used throughout `pytuflow`
_PYTUFLOW_LOGGER_NAME = 'pytuflow'

# Maps a `logging` levelno onto one of the dock's own `_log` levels ('debug'/'info'/'warning'/'error')
_LOG_LEVEL_MAP = (
    (logging.ERROR, 'error'),
    (logging.WARNING, 'warning'),
    (logging.INFO, 'info'),
    (logging.DEBUG, 'debug'),
)


def _logging_level_to_dock_level(levelno: int) -> str:
    """Maps a ``logging`` levelno onto one of the dock's own ``_log`` levels."""

    for threshold, dock_level in _LOG_LEVEL_MAP:
        if levelno >= threshold:
            return dock_level
    return 'debug'


class _PytuflowLogBridge(logging.Handler):
    """Logging handler that forwards every ``pytuflow`` logger record to a Qt signal
    (``Arr2026Dock``'s ``ArrRunWorker.log_message`` signal - see
    :meth:`Arr2026Dock._on_run_clicked`), so the ``pytuflow.arr`` engine/API
    client/writers' own logging (including verbose ``DEBUG``-level messages, when
    enabled) is visible in the dock's log panel while a run is in progress, in
    addition to (not instead of) the existing QGIS message log/message bar output
    (see ``gui/logging.py``).

    Since the ``pytuflow`` logging calls this handler forwards happen on the
    background run thread (see ``arr_run_worker.ArrRunWorker``), a bound Qt signal is
    used rather than calling the dock's ``_log`` method directly - Qt automatically
    marshals the signal emission across to the GUI thread (a queued connection),
    rather than running GUI code from a non-GUI thread."""

    def __init__(self, log_signal) -> None:
        super().__init__()
        self._log_signal = log_signal

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            message = record.getMessage()
        self._log_signal.emit(message, _logging_level_to_dock_level(record.levelno))
