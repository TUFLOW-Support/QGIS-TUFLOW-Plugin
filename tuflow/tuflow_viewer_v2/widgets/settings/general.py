from qgis.PyQt.QtWidgets import (QWidget, QBoxLayout, QComboBox, QLabel, QVBoxLayout, QHBoxLayout, QRadioButton,
                                 QButtonGroup, QSpinBox)
from qgis.gui import QgsCollapsibleGroupBox

from ...tvinstance import get_viewer_instance


class General:

    def _init_general(self, layout: QBoxLayout) -> QWidget:
        self.general_widget = QWidget()
        self.general_layout = QVBoxLayout()
        self.general_widget.setLayout(self.general_layout)

        # Appearance GroupBox
        self.appearance_groupbox = QgsCollapsibleGroupBox()
        self.appearance_groupbox.setTitle('Appearance')
        self.appearance_groupbox.setToolTip('Settings related to the TUFLOW Viewer plotting theme and appearance.')
        self.general_layout.addWidget(self.appearance_groupbox)
        self.appearance_layout = QVBoxLayout()
        self.appearance_groupbox.setLayout(self.appearance_layout)

        # Appearance / Theme
        self.theme_layout = QHBoxLayout()
        self.theme_label = QLabel('Plot theme:')
        self.theme_cbo = QComboBox()
        self.theme_cbo.addItems(['Default', 'Light', 'Blend of Gray', 'Night Mapping'])
        self.theme_cbo.setCurrentText(get_viewer_instance().settings.theme_name)
        self.theme_cbo.currentIndexChanged.connect(self.theme_changed)
        self.theme_layout.addWidget(self.theme_label)
        self.theme_layout.addStretch()
        self.theme_layout.addWidget(self.theme_cbo)
        self.appearance_layout.addLayout(self.theme_layout)

        # Loading results
        self.output_loading_groupbox = QgsCollapsibleGroupBox()
        self.output_loading_groupbox.setTitle('Output Loading')
        self.output_loading_groupbox.setToolTip('Settings related to how results are loaded into the TUFLOW Viewer.')
        self.general_layout.addWidget(self.output_loading_groupbox)
        self.output_loading_layout = QVBoxLayout()
        self.output_loading_groupbox.setLayout(self.output_loading_layout)

        # Loading results / Copy on load
        self.copy_on_load_layout = QHBoxLayout()
        self.copy_on_load_label = QLabel('Copy hdf5 files before loading:')
        self.copy_on_load_label.setToolTip(
            'If enabled, results that use hdf5 libraries (XMDF, NetCDF) will be copied locally and cached before loading.'
            '\n\nThis will enable simultaneous access to the same result file by QGIS and TUFLOW.')
        self.copy_on_load_button_grp = QButtonGroup()
        self.copy_on_load_no = QRadioButton('No')
        self.copy_on_load_button_grp.addButton(self.copy_on_load_no)
        self.copy_on_load_yes = QRadioButton('Yes')
        self.copy_on_load_button_grp.addButton(self.copy_on_load_yes)
        if get_viewer_instance().settings.copy_results_on_load:
            self.copy_on_load_yes.setChecked(True)
        else:
            self.copy_on_load_no.setChecked(True)
        self.copy_on_load_button_grp.buttonClicked.connect(self.copy_on_load_changed)
        self.copy_on_load_layout.addWidget(self.copy_on_load_label)
        self.copy_on_load_layout.addStretch()
        self.copy_on_load_layout.addWidget(self.copy_on_load_no)
        self.copy_on_load_layout.addWidget(self.copy_on_load_yes)
        self.output_loading_layout.addLayout(self.copy_on_load_layout)

        # Plotting
        self.output_plotting_groupbox = QgsCollapsibleGroupBox()
        self.output_plotting_groupbox.setTitle('Plotting')
        self.output_plotting_groupbox.setToolTip('Settings related to plotting.')
        self.general_layout.addWidget(self.output_plotting_groupbox)
        self.output_plotting_layout = QVBoxLayout()
        self.output_plotting_groupbox.setLayout(self.output_plotting_layout)

        # Long plot branch limit
        self.long_plot_branch_limit_layout = QHBoxLayout()
        self.long_plot_branch_limit_label = QLabel('1D long plot branch limit:')
        self.long_plot_branch_limit_label.setToolTip(
            'This value will limit how many branches / paths are collected when extracting 1D long plots. Limiting the number of branches ' \
            'will short-circuit the connectivity process which can speed up the plot if there are many branches along a section of 1D channels.' \
            '\n\nA value of zero sets the branch limit to unlimited.'
        )
        self.long_plot_branch_limit_spinbox = QSpinBox()
        self.long_plot_branch_limit_spinbox.setMinimum(0)
        self.long_plot_branch_limit_spinbox.setMaximum(999)
        self.long_plot_branch_limit_spinbox.valueChanged.connect(self.branch_limit_value_changed)
        self.long_plot_branch_limit_spinbox.setValue(get_viewer_instance().settings.long_plot_branch_limit)
        self.long_plot_branch_limit_layout.addWidget(self.long_plot_branch_limit_label)
        self.long_plot_branch_limit_layout.addStretch()
        self.long_plot_branch_limit_layout.addWidget(self.long_plot_branch_limit_spinbox)
        self.output_plotting_layout.addLayout(self.long_plot_branch_limit_layout)

        self.general_layout.addStretch()
        layout.addWidget(self.general_widget)
        self.general_widget.hide()
        return self.general_widget

    def theme_changed(self, index: int):
        theme_name = self.theme_cbo.currentText()
        get_viewer_instance().set_theme(theme_name)

    def copy_on_load_changed(self, button: QRadioButton):
        if button == self.copy_on_load_yes:
            get_viewer_instance().settings.copy_results_on_load = True
        else:
            get_viewer_instance().settings.copy_results_on_load = False

    def branch_limit_value_changed(self, value: int):
        get_viewer_instance().settings.long_plot_branch_limit = value
