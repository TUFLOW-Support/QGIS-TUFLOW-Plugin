from qgis.PyQt.QtWidgets import (QWidget, QBoxLayout, QComboBox, QLabel, QVBoxLayout, QHBoxLayout, QRadioButton,
                                 QButtonGroup)
from qgis.PyQt.QtCore import QSettings
from qgis.gui import QgsCollapsibleGroupBox

from ...tvdeveloper_tools import set_log_level


class Debug:

    def _init_debug(self, layout: QBoxLayout) -> QWidget:
        self.debug_widget = QWidget()
        self.debug_layout = QVBoxLayout()
        self.debug_widget.setLayout(self.debug_layout)

        # debug logging
        self.debug_logging_groupbox = QgsCollapsibleGroupBox()
        self.debug_logging_groupbox.setTitle('Logging')
        self.debug_logging_groupbox.setToolTip('TUFLOW Viewer logging settings.')
        self.debug_layout.addWidget(self.debug_logging_groupbox)
        self.debug_logging_layout = QVBoxLayout()
        self.debug_logging_groupbox.setLayout(self.debug_logging_layout)

        # debug logging / log level
        self.log_level_cbo = QComboBox()
        self.log_level_cbo.addItems(['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'])
        log_level = QSettings().value('TUFLOW/Debug', 'INFO', type=str)
        self.log_level_cbo.setCurrentText(log_level)
        self.log_level_cbo.currentIndexChanged.connect(self.log_level_changed)
        self.debug_logging_layout.addWidget(QLabel('Log level:'))
        self.debug_logging_layout.addWidget(self.log_level_cbo)

        self.debug_layout.addStretch()
        layout.addWidget(self.debug_widget)
        self.debug_widget.hide()
        return self.debug_widget

    def log_level_changed(self, index: int):
        log_level = self.log_level_cbo.currentText()
        QSettings().setValue('TUFLOW/Debug', log_level)
        set_log_level(log_level)
