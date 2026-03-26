import sys
from typing import TYPE_CHECKING

from qgis.core import QgsApplication, Qgis
from qgis.gui import QgsMessageBar
from qgis.PyQt import QtCore

try:
    import traceback
    has_traceback = True
except ImportError:
    has_traceback = False

from qgis.PyQt.QtWidgets import QMessageBox, QPushButton

if TYPE_CHECKING:
    from qgis.gui import QgisInterface


import logging



from ..compatibility_routines import QT_MESSAGE_BOX_WARNING


class _Logging:
    """Logging class - do not import this class directly, use Logging variable below instead."""

    def __init__(self):
        self.iface = None

    @staticmethod
    def get_stack_trace() -> str:
        """Return the entire stack trace."""
        if has_traceback:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            return ''.join(traceback.extract_tb(exc_traceback).format()) + '{0}{1}'.format(exc_type, exc_value)
        return ''

    def init_logging(self, iface: 'QgisInterface') -> None:
        """Method to initialise the logging."""
        self.iface = iface
        ptlogger = logging.getLogger('pytuflow')
        tmflogger = logging.getLogger('tmf')
        loggers = [ptlogger, tmflogger]
        for logger in loggers:
            for hnd in logger.handlers.copy():
                logger.removeHandler(hnd)
        hnd = PyTuflowLoggingHandler(logging.WARNING)
        for logger in loggers:
            logger.addHandler(hnd)

    def visible_message_bar(self) -> QgsMessageBar:
        focus_widget = QgsApplication.instance().focusWidget()
        if focus_widget and getattr(focus_widget, 'messageBar', None):
            message_bar = focus_widget.messageBar()
            if not message_bar:
                message_bar = self.iface.messageBar()
        else:
            message_bar = self.iface.messageBar()
        return message_bar

    def info(self, msg: str, silent: bool = False) -> None:
        """Log a message with level INFO to QGIS."""
        if not silent:
            silent = QtCore.QThread.currentThread() != QtCore.QCoreApplication.instance().thread()
        if not isinstance(msg, str):
            msg = str(msg)
        if self.iface is not None and not silent:
            self.visible_message_bar().pushMessage("TUFLOW Plugin", msg, level=Qgis.MessageLevel.Info)
        else:
            QgsApplication.messageLog().logMessage(msg, 'TUFLOW Plugin', level=Qgis.MessageLevel.Info, notifyUser=False)

    def warning(self, msg: str, silent: bool = False, more_info: str = None) -> None:
        """Log a message with level WARNING to QGIS."""
        if not silent:
            silent = QtCore.QThread.currentThread() != QtCore.QCoreApplication.instance().thread()
        if not isinstance(msg, str):
            msg = str(msg)
        if self.iface is not None and not silent:
            if more_info:
                self.dlg = QMessageBox()
                self.dlg.setWindowTitle('TUFLOW')
                self.dlg.setText(msg)
                self.dlg.setInformativeText(more_info)
                self.dlg.setIcon(QT_MESSAGE_BOX_WARNING)
                widget = self.visible_message_bar().createMessage("TUFLOW Plugin", msg)
                button = QPushButton(widget)
                button.setText('More Info')
                button.clicked.connect(self.dlg.exec)
                widget.layout().addWidget(button)
                self.visible_message_bar().pushWidget(widget, level=Qgis.MessageLevel.Warning)
            else:
                self.visible_message_bar().pushMessage("TUFLOW Plugin", msg, level=Qgis.MessageLevel.Warning)
        else:
            QgsApplication.messageLog().logMessage(msg, 'TUFLOW Plugin', level=Qgis.MessageLevel.Warning, notifyUser=False)

    def error(self, msg: str, more_info: str = None, silent: bool = False) -> None:
        """
        Log a message with level CRITICAL/ERROR to QGIS.
        Has the additional option of adding more info (e.g. stack trace). This will appear as a button
        in the message bar called 'More Info'.
        """
        if not silent:
            silent = QtCore.QThread.currentThread() != QtCore.QCoreApplication.instance().thread()
        if not isinstance(msg, str):
            msg = str(msg)
        if self.iface is not None and not silent:
            if more_info:
                self.dlg = QMessageBox()
                self.dlg.setWindowTitle('TUFLOW')
                self.dlg.setText(msg)
                self.dlg.setInformativeText(more_info)
                self.dlg.setIcon(QT_MESSAGE_BOX_WARNING)
                widget = self.visible_message_bar().createMessage("TUFLOW Plugin", msg)
                button = QPushButton(widget)
                button.setText('More Info')
                button.clicked.connect(self.dlg.exec)
                widget.layout().addWidget(button)
                self.visible_message_bar().pushWidget(widget, level=Qgis.MessageLevel.Critical)
            else:
                self.visible_message_bar().pushMessage("TUFLOW Plugin", msg, level=Qgis.MessageLevel.Critical)
        else:
            QgsApplication.messageLog().logMessage(msg, 'TUFLOW Plugin', level=Qgis.MessageLevel.Critical, notifyUser=False)


# import this - mimics a singleton with static methods
Logging = _Logging()


class PyTuflowLoggingHandler(logging.Handler):

    def emit(self, record):
        from qgis.utils import iface
        msg = f'{record.msg}\n{record.exc_info}' if record.exc_info else record.msg
        silent = QtCore.QThread.currentThread() != QtCore.QCoreApplication.instance().thread()
        QgsApplication.messageLog().logMessage(
            msg, 'PyTUFLOW',
            level=self.loglevel2qgis(record.levelno),
            notifyUser=record.levelno >= self.level and not silent
        )
        show_msg_in_msgbar = getattr(record, "messagebar", False)
        focus_widget = QgsApplication.instance().focusWidget()
        if focus_widget and getattr(focus_widget, 'messageBar', None):
            message_bar = focus_widget.messageBar()
            if not message_bar:
                message_bar = iface.messageBar()
        else:
            message_bar = iface.messageBar()
        if not silent and iface is not None and (show_msg_in_msgbar or record.levelno >= logging.WARNING):
            message_bar.pushMessage('PyTUFLOW', record.msg, level=self.loglevel2qgis(record.levelno))

    @staticmethod
    def loglevel2qgis(level):
        if level >= logging.CRITICAL:
            return Qgis.MessageLevel.Critical
        elif level >= logging.ERROR:
            return Qgis.MessageLevel.Critical
        elif level >= logging.WARNING:
            return Qgis.MessageLevel.Warning
        elif level >= logging.INFO:
            return Qgis.MessageLevel.Info
        else:
            return Qgis.MessageLevel.Success
