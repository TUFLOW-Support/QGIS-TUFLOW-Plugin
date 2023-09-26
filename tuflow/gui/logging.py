import sys
from typing import TYPE_CHECKING
try:
    import traceback
    has_traceback = True
except ImportError:
    has_traceback = False

from PyQt5.QtWidgets import QMessageBox, QPushButton

if TYPE_CHECKING:
    from qgis.gui import QgisInterface


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

    def info(self, msg: str) -> None:
        """Log a message with level INFO to QGIS."""
        if self.iface is not None:
            self.iface.messageBar().pushMessage("TUFLOW Catch", msg, level=0)
        else:
            print(f'TUFLOW Catch: {msg}')

    def warning(self, msg: str) -> None:
        """Log a message with level WARNING to QGIS."""
        if self.iface is not None:
            self.iface.messageBar().pushMessage("TUFLOW Catch", msg, level=1)
        else:
            print(f'TUFLOW Catch: {msg}')

    def error(self, msg: str, more_info: str = None) -> None:
        """
        Log a message with level CRITICAL/ERROR to QGIS.
        Has the additional option of adding more info (e.g. stack trace). This will appear as a button
        in the message bar called 'More Info'.
        """
        if self.iface is not None:
            if more_info:
                self.dlg = QMessageBox()
                self.dlg.setWindowTitle('TUFLOW Catch')
                self.dlg.setText(msg)
                self.dlg.setInformativeText(more_info)
                self.dlg.setIcon(QMessageBox.Warning)
                widget = self.iface.messageBar().createMessage("TUFLOW Catch", msg)
                button = QPushButton(widget)
                button.setText('More Info')
                button.clicked.connect(self.dlg.exec_)
                widget.layout().addWidget(button)
                self.iface.messageBar().pushWidget(widget, level=2)
            else:
                self.iface.messageBar().pushMessage("TUFLOW Catch", msg, level=2)
        else:
            print(f'TUFLOW Catch: {msg}')


# import this - mimics a singleton with static methods
Logging = _Logging()
