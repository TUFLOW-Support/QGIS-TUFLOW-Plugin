import sys
from typing import TYPE_CHECKING

from qgis.core import QgsApplication, Qgis

try:
    import traceback
    has_traceback = True
except ImportError:
    has_traceback = False

from qgis.PyQt.QtWidgets import QMessageBox, QPushButton

if TYPE_CHECKING:
    from qgis.gui import QgisInterface



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

    def info(self, msg: str, silent: bool = False) -> None:
        """Log a message with level INFO to QGIS."""
        if not isinstance(msg, str):
            msg = str(msg)
        if self.iface is not None and not silent:
            self.iface.messageBar().pushMessage("TUFLOW Plugin", msg, level=Qgis.MessageLevel.Info)
        else:
            QgsApplication.messageLog().logMessage(msg, 'TUFLOW Plugin', level=Qgis.MessageLevel.Info, notifyUser=False)

    def warning(self, msg: str, silent: bool = False) -> None:
        """Log a message with level WARNING to QGIS."""
        if not isinstance(msg, str):
            msg = str(msg)
        if self.iface is not None:
            self.iface.messageBar().pushMessage("TUFLOW Plugin", msg, level=Qgis.MessageLevel.Warning)
        else:
            QgsApplication.messageLog().logMessage(msg, 'TUFLOW Plugin', level=Qgis.MessageLevel.Warning, notifyUser=False)

    def error(self, msg: str, more_info: str = None, silent: bool = False) -> None:
        """
        Log a message with level CRITICAL/ERROR to QGIS.
        Has the additional option of adding more info (e.g. stack trace). This will appear as a button
        in the message bar called 'More Info'.
        """
        if not isinstance(msg, str):
            msg = str(msg)
        if self.iface is not None:
            if more_info:
                self.dlg = QMessageBox()
                self.dlg.setWindowTitle('TUFLOW')
                self.dlg.setText(msg)
                self.dlg.setInformativeText(more_info)
                self.dlg.setIcon(QT_MESSAGE_BOX_WARNING)
                widget = self.iface.messageBar().createMessage("TUFLOW Plugin", msg)
                button = QPushButton(widget)
                button.setText('More Info')
                button.clicked.connect(self.dlg.exec)
                widget.layout().addWidget(button)
                self.iface.messageBar().pushWidget(widget, level=Qgis.MessageLevel.Critical)
            else:
                self.iface.messageBar().pushMessage("TUFLOW Plugin", msg, level=Qgis.MessageLevel.Critical)
        else:
            QgsApplication.messageLog().logMessage(msg, 'TUFLOW Plugin', level=Qgis.MessageLevel.Critical, notifyUser=False)


# import this - mimics a singleton with static methods
Logging = _Logging()
