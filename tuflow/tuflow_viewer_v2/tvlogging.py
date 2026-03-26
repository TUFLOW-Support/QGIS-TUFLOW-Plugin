import logging
from qgis.core import QgsApplication, Qgis
from qgis.utils import iface
from qgis.PyQt import QtCore


class QgisTuflowLoggingHandler(logging.Handler):

    def emit(self, record):
        silent = QtCore.QThread.currentThread() != QtCore.QCoreApplication.instance().thread()
        msg = f'{record.msg}\n{record.exc_info}' if record.exc_info else record.msg
        QgsApplication.messageLog().logMessage(
            msg, 'TUFLOW Viewer',
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
            message_bar.pushMessage('TUFLOW Viewer', record.msg, level=self.loglevel2qgis(record.levelno))

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
