from qgis.PyQt.QtWidgets import QToolBar, QComboBox, QWidget, QLabel, QHBoxLayout, QMenu
from qgis.PyQt.QtCore import QSize, pyqtSignal, QSettings

from qgis.core import QgsApplication
from qgis.gui import QgsMapCanvasItem
from qgis.utils import iface

from ..tvinstance import get_viewer_instance
from .menu_button import MenuButton
from .branch_selector_menu import BranchSelectorMenu
from .depth_averaging.depth_averaging_menu import DepthAveragingMenu
from .drawn_item_menu import DrawnItemMenu
from .drawn_item_action import DrawnItemAction
from ..fmts.tvoutput import TuflowViewerOutput
from ..theme import TuflowViewerTheme

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...compatibility_routines import is_qt6
else:
    from tuflow.compatibility_routines import is_qt6

if is_qt6:
    from qgis.PyQt.QtGui import QAction
else:
    from qgis.PyQt.QtWidgets import QAction


class TVPlotToolBar(QToolBar):

    result_name_selection_changed = pyqtSignal()
    data_type_selection_changed = pyqtSignal()
    branch_selection_changed = pyqtSignal()

    plot_by_selection_cleared = pyqtSignal()

    # draw menu
    draw_tool_toggled = pyqtSignal(bool)
    draw_menu_cleared = pyqtSignal()
    draw_menu_action_toggled = pyqtSignal(DrawnItemAction, bool)
    draw_menu_action_removed = pyqtSignal(DrawnItemAction)
    draw_menu_hover_changed = pyqtSignal([], [QgsMapCanvasItem])

    # selection tool
    selection_tool_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(16, 16))

        # layer selection
        self.selection_action = QAction(QgsApplication.getThemeIcon('mActionSelectRectangle.svg'), 'Selection', self)
        self.selection_action.setCheckable(True)
        if iface is not None and not QSettings().value('TUFLOW/TestCase', False, type=bool):
            self.selection_action.triggered.connect(iface.actionSelect().trigger)
            self.selection_action.triggered.connect(self.selection_tool_toggled.emit)
        self.selection_action_menu = QMenu(self)
        self.extract_map_outputs_action = QAction('Extract from map outputs', self)
        self.extract_map_outputs_action.setCheckable(True)
        self.selection_action_menu.addAction(self.extract_map_outputs_action)
        self.selection_action_menu.addSeparator()
        self.clear_selection_action = QAction('Clear', self)
        self.clear_selection_action.triggered.connect(self.plot_by_selection_cleared.emit)
        self.selection_action_menu.addAction(self.clear_selection_action)
        self.selection_action.setMenu(self.selection_action_menu)
        self.addAction(self.selection_action)

        # draw menu
        self.draw_action = QAction(get_viewer_instance().icon('draw'), 'Draw', self)
        self.draw_action.setCheckable(True)
        self.draw_action.toggled.connect(self.draw_tool_toggled.emit)
        self.draw_action_menu = DrawnItemMenu(self)
        self.draw_action_menu.cleared.connect(self.draw_menu_cleared.emit)
        self.draw_action_menu.action_toggled.connect(self.draw_menu_action_toggled.emit)
        self.draw_action_menu.action_removed.connect(self.draw_menu_action_removed.emit)
        self.draw_action_menu.action_hover_changed.connect(self.on_draw_menu_hover_changed)
        self.draw_action_menu.action_hover_changed[QgsMapCanvasItem].connect(self.on_draw_menu_hover_changed)
        self.draw_action.setMenu(self.draw_action_menu)
        self.addAction(self.draw_action)

        # result names
        self.active_result_names = []
        self.result_names_menu = MenuButton(
            get_viewer_instance().icon('layers'),
            'Result Names',
            self,
            persistent_menu=True
        )
        self.addWidget(self.result_names_menu)
        self.result_names_menu.triggered.connect(self.active_result_names_changed)

        # data types
        self.data_types_menu = MenuButton(
            get_viewer_instance().icon('selection-filter'),
            'Data Types',
            self,
            persistent_menu=True
        )
        self.addWidget(self.data_types_menu)
        self.data_types_menu.triggered.connect(self.data_type_selection_changed.emit)

        self.dep_avg_menu = DepthAveragingMenu('Depth Averaging', self.data_types_menu)
        self.dep_avg_menu.changed.connect(self.data_type_selection_changed.emit)

        self.outputs_changed(None)
        get_viewer_instance().outputs_changed.connect(self.outputs_changed)
        get_viewer_instance().outputs_removed.connect(self.outputs_removed)

        # branch selector - only for section plots, and only visible when the current long plot has multiple branches
        self.branch_selector = BranchSelectorMenu(
            get_viewer_instance().icon('branch'),
            'Branch Selector',
            self,
            persistent_menu=True
        )
        self.branch_selector.setCheckable(False)
        self.branch_selector_action = self.addWidget(self.branch_selector)
        self.branch_selector_action.setVisible(False)
        self.branch_selector.triggered.connect(self.branch_selection_changed.emit)

    def set_theme(self, theme: TuflowViewerTheme):
        icon = get_viewer_instance().icon
        self.draw_action.setIcon(icon('draw'))
        self.result_names_menu.setIcon(icon('layers'))
        self.data_types_menu.setIcon(icon('selection-filter'))
        self.branch_selector.setIcon(icon('branch'))

    def selection_includes_map_outputs(self) -> bool:
        return self.extract_map_outputs_action.isChecked()

    def selection_active(self) -> bool:
        return self.selection_action.isChecked()

    def drawn_item_actions(self) -> list[DrawnItemAction]:
        return self.draw_action_menu.drawn_item_actions()

    def draw_menu_editable_action(self) -> DrawnItemAction | None:
        return self.draw_action_menu.editable_action()

    def add_drawn_item_action(self, text: str, item: QgsMapCanvasItem, checked: bool):
        self.draw_action_menu.add_action(text, item, checked)

    def remove_drawn_item_action(self, action: DrawnItemAction):
        self.draw_action_menu.remove_action(action)

    def on_draw_menu_hover_changed(self, item: QgsMapCanvasItem = None):
        if item is None:
            self.draw_menu_hover_changed.emit()
            return
        self.draw_menu_hover_changed[QgsMapCanvasItem].emit(item)

    def result_names(self) -> list[str]:
        return [x.text() for x in self.result_names_menu.actions() if not x.isSeparator()]

    def selected_result_names(self) -> list[str]:
        return [x.text() for x in self.result_names_menu.actions() if x.isChecked()]

    def active_result_names_changed(self, action: QAction):
        if action.isSeparator() or action == self.dep_avg_menu.menuAction():
            return
        if action.isChecked() and action.text() not in self.active_result_names:
            self.active_result_names.append(action.text())
        elif action.text() in self.active_result_names:
            self.active_result_names.remove(action.text())

        # data types
        checked_dtypes = [x.text() for x in self.data_types_menu.actions() if x.isChecked()]
        self.data_types_menu.clear()
        data_types = self.parent().plot_data_types(self.active_result_names)
        actions = [QAction(x, self.data_types_menu) for x in data_types]
        _ = [x.setCheckable(True) for x in actions]
        _ = [x.setChecked(True) for x in actions if x.text() in checked_dtypes]
        self.data_types_menu.addActions(actions)

        self.result_name_selection_changed.emit()

    def data_types(self) -> list[str]:
        return [x.text() for x in self.data_types_menu.actions() if not x.isSeparator() and x != self.dep_avg_menu.menuAction()]

    def selected_data_types(self) -> list[str]:
        dtypes = [x.text() for x in self.data_types_menu.actions() if x.isChecked()]
        if self.dep_avg_menu is None:
            return dtypes
        for menu in self.dep_avg_menu.menus:
            if not menu.menuAction().isChecked():
                continue
            for action in menu.actions():
                if not action.isChecked():
                    continue
                string = action.to_string()
                if string:
                    dtypes.append(action.to_string())
        return dtypes

    def outputs_removed(self, output_ids: list[str]):
        self.outputs_changed(None)

    def outputs_changed(self, output: TuflowViewerOutput = None):
        """output parameter is newly added."""
        loaded_output_names = get_viewer_instance().result_names()
        previous_count = len(self.active_result_names)

        # remove results that were removed from QGIS
        for output_name in reversed(self.active_result_names):
            if output_name not in loaded_output_names:
                self.active_result_names.remove(output_name)

        # add
        for output_name in loaded_output_names:
            if output_name not in self.active_result_names:
                self.active_result_names.append(output_name)

        # re-populate menu
        self.result_names_menu.clear()
        actions = [QAction(x, self.result_names_menu) for x in loaded_output_names]
        _ = [x.setCheckable(True) for x in actions]
        _ = [x.setChecked(True) for x in actions if x.text() in self.active_result_names]
        self.result_names_menu.addActions(actions)
        new_count = len([x.text() for x in self.result_names_menu.actions() if x.isChecked()])
        require_update_plot = previous_count != new_count and output is None

        # data types
        checked_dtypes = [x.text() for x in self.data_types_menu.actions() if x.isChecked()]
        self.data_types_menu.clear()
        data_types = self.parent().plot_data_types(self.active_result_names)
        actions = [QAction(x, self.data_types_menu) for x in data_types]
        _ = [x.setCheckable(True) for x in actions]
        _ = [x.setChecked(True) for x in actions if x.text() in checked_dtypes]
        self.data_types_menu.addActions(actions)

        # depth averaging - this needs sorting out
        dtypes_3d = self.parent().plot_data_types_3d(self.active_result_names)
        if dtypes_3d:
            # add 2d depth average options for 3d results
            self.data_types_menu.addSeparator()
            self.dep_avg_menu.set_data_types(dtypes_3d)
            self.data_types_menu.addMenu(self.dep_avg_menu)

        if require_update_plot:
            self.result_name_selection_changed.emit()

    def selected_branches(self) -> list[int]:
        return self.branch_selector.selected_branches()
