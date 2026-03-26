from __future__ import annotations

import typing
import logging
from collections import OrderedDict

from qgis.gui import QgsMapCanvasItem
from qgis.PyQt.QtCore import pyqtSignal, QSettings
from qgis.PyQt.QtWidgets import QAction

from ..plotsourceitem import PlotSourceItem
from ..pyqtgraph_subclass.hoverable_curve_item import HoverableCurveItem
from ..pyqtgraph_subclass.tuflow_viewer_curve import TuflowViewerCurve
from ...drawn_item_action import DrawnItemAction
from ....tvinstance import get_viewer_instance

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pt.pytuflow import AppendDict
else:
    from tuflow.pt.pytuflow import AppendDict

if typing.TYPE_CHECKING:
    from ..pyqtgraph_subclass.custom_view_box import CustomViewBox
    from qgis.PyQt.QtWidgets import QMenu
    from qgis.gui import QgsRubberBand, QgsVertexMarker
    from ..pyqtgraph_subclass.custom_plot_widget import CustomPlotWidget
    from ...tv_plot_toolbar import TVPlotToolBar
    from ....fmts.tvoutput import TuflowViewerOutput


logger = logging.getLogger('tuflow_viewer')


class SupportsQgisHooks(typing.Protocol):
    _hover_marker: 'QgsVertexMarker'
    _hover_rubber_band: 'QgsRubberBand'
    _geom_type: str


class SupportsPlotManager(typing.Protocol):
    secondary_vb: 'CustomViewBox | None' = None

    def items_on_plot(self, plot_items: list[HoverableCurveItem]) -> dict[str, PlotSourceItem]: ...
    def items_for_plotting(self,
                           outputs: list['TuflowViewerOutput'],
                           data_types: list[str],
                           allow_map_output_feature_selection: bool) -> dict[str, PlotSourceItem]: ...


class SupportUI(SupportsQgisHooks, SupportsPlotManager, typing.Protocol):
    plot_graph: 'CustomPlotWidget'
    toolbar: 'TVPlotToolBar'


class MenuToolbarMixin:
    """Deals with the plot context menu and the toolbar.

    Depends on QgisHooksMixin and PlotManagerMixin.
    """

    # clear plot signals
    clear_all_selection_requested = pyqtSignal()
    clear_drawn_selection_requested = pyqtSignal()
    clear_feature_selection_requested = pyqtSignal()

    # draw tool
    draw_tool_toggled = pyqtSignal(bool)
    draw_item_toggled = pyqtSignal(DrawnItemAction, bool)
    draw_item_removed = pyqtSignal(DrawnItemAction)
    draw_item_hovered = pyqtSignal([], [QgsMapCanvasItem])

    # selection tool
    selection_tool_toggled = pyqtSignal(bool)

    # result types and results
    results_changed = pyqtSignal()
    data_types_changed = pyqtSignal()

    def _init_menus_and_toolbar(self: SupportUI):
        # context menu actions
        self._ctx_menu_actions = []
        self._ctx_menu_groups = OrderedDict()
        self._sep_actions = []

        # hide some default context menu actions
        for plot_menu_context_action in ['Transforms', 'Downsample', 'Average', 'Alpha', 'Points']:
            self.plot_graph.plotItem.setContextMenuActionVisible(plot_menu_context_action, False)

        # remove default export action
        self.plot_graph.scene().contextMenu.pop(0)

        # draw menu
        self._sig1 = self.toolbar.draw_menu_cleared.connect(self.clear_drawn_selection_requested.emit)
        self._sig2 = self.toolbar.draw_tool_toggled.connect(self.draw_tool_toggled.emit)
        self._sig3 = self.toolbar.draw_menu_action_toggled.connect(self.draw_item_toggled.emit)
        self._sig4 = self.toolbar.draw_menu_action_removed.connect(self.draw_item_removed.emit)
        self._sig5 = self.toolbar.draw_menu_hover_changed.connect(self.draw_item_hovered.emit)
        self._sig6 = self.toolbar.draw_menu_hover_changed[QgsMapCanvasItem].connect(self.draw_item_hovered.emit)

        # selection menu
        self._sig7 = self.toolbar.selection_tool_toggled.connect(self.selection_tool_toggled.emit)
        self._sig8 = self.toolbar.plot_by_selection_cleared.connect(self.clear_feature_selection_requested.emit)

        # result types and results
        self._sig9 = self.toolbar.result_name_selection_changed.connect(self.results_changed.emit)
        self._sig10 = self.toolbar.data_type_selection_changed.connect(self.data_types_changed.emit)

    def _teardown_menus_and_toolbar(self: SupportUI):
        # draw menu
        try:
            self.toolbar.draw_menu_cleared.disconnect(self._sig1)
        except Exception:
            pass
        try:
            self.toolbar.draw_tool_toggled.disconnect(self._sig2)
        except Exception:
            pass
        try:
            self.toolbar.draw_menu_action_toggled.disconnect(self._sig3)
        except Exception:
            pass
        try:
            self.toolbar.draw_menu_action_removed.disconnect(self._sig4)
        except Exception:
            pass
        try:
            self.toolbar.draw_menu_hover_changed.disconnect(self._sig5)
        except Exception:
            pass

        try:
            self.toolbar.draw_menu_hover_changed[QgsMapCanvasItem].disconnect(self._sig6)
        except Exception:
            pass

        # selection menu
        try:
            self.toolbar.selection_tool_toggled.disconnect(self._sig7)
        except Exception:
            pass
        try:
            self.toolbar.plot_by_selection_cleared.disconnect(self._sig8)
        except Exception:
            pass

        # result types and results
        try:
            self.toolbar.result_name_selection_changed.disconnect(self._sig9)
        except Exception:
            pass
        try:
            self.toolbar.data_type_selection_changed.disconnect(self._sig10)
        except Exception:
            pass

    def add_context_menu_group(self, group_name: str, insert_before: list[str]):
        self._ctx_menu_groups[group_name] = insert_before

    def add_context_menu_action(self,
                                action: QAction,
                                position: int,
                                group_name: str,
                                callback: typing.Callable[['CustomViewBox'], bool]):
        """Adds custom actions to the context menu."""
        self._ctx_menu_actions.append((action, callback, position, group_name))

    def create_context_menu(self: SupportUI, vb: 'CustomViewBox', menu: 'QMenu') -> 'QMenu':
        sel = self.selected_curve()
        if sel:
            sel.context_menu_about_to_show()

        for plot_item in self.plot_graph.items():
            if isinstance(plot_item, TuflowViewerCurve):
                plot_item.reset_hover()

        # clear context menu of existing custom actions
        self.clear_context_menu(menu)

        # sort actions into groups
        menus = AppendDict()
        for action, handler, idx, group in self._ctx_menu_actions:
            if handler(vb):
                menus[group] = (action, idx)

        # sort actions within groups by position
        menus_ordered = {}
        for group in menus:
            menus_ordered[group] = sorted(menus[group], key=lambda x: x[1])

        # add ungrouped actions first
        ungrouped = menus_ordered.pop('', ())
        for action, idx in ungrouped:
            if idx >= len(menu.actions()):
                menu.addAction(action)
            else:
                a = menu.actions()[idx]
                menu.insertAction(a, action)

        def add_separator_if_required(i: int, menu: 'QMenu') -> bool:
            a = QAction(self)
            a.setSeparator(True)
            if i >= len(menu.actions()):
                a0 = menu.actions()[-1]
                if not a0.isSeparator():
                    self._sep_actions.append(a)
                    menu.addAction(a)
                    return True
            elif i > 0:
                a0 = menu.actions()[i]
                if not a0.isSeparator():
                    self._sep_actions.append(a)
                    menu.insertAction(a0, a)
                    return True
            return False

        # add grouped actions
        for group, insert_before_txt in reversed(self._ctx_menu_groups.items()):
            idx = len(menu.actions())
            for txt in insert_before_txt:
                a = [x for x in menu.actions() if x.text() == txt]
                if a:
                    idx = menu.actions().index(a[0])
                    break
            if group not in menus_ordered:
                continue
            if add_separator_if_required(idx, menu):
                idx += 1
            for j, (action, action_idx) in enumerate(menus_ordered[group]):
                k = idx + j
                if k >= len(menu.actions()):
                    menu.addAction(action)
                else:
                    a = menu.actions()[k]
                    menu.insertAction(a, action)
            add_separator_if_required(len(menus_ordered[group]) + idx, menu)

        return menu

    def clear_context_menu(self, menu: 'QMenu'):
        ctx_actions = [x[0] for x in self._ctx_menu_actions] + self._sep_actions
        for action in menu.actions():
            if action in ctx_actions:
                menu.removeAction(action)
        self._sep_actions.clear()

    def get_result_combinations_for_plotting(self: SupportUI, items_on_plot: list[PlotSourceItem]) -> dict[str, PlotSourceItem]:
        outputs = [output for result_name in self.toolbar.selected_result_names() for output in get_viewer_instance().outputs(result_name)]
        data_types = self.toolbar.selected_data_types()
        return self.items_for_plotting(outputs, data_types, items_on_plot, self.toolbar.selection_includes_map_outputs())

    def get_current_combinations_on_plot(self: SupportUI) -> dict[str, PlotSourceItem]:
        plot_items = [x for x in self.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
        return self.items_on_plot(plot_items)

    def draw_menu_editable_action(self: SupportUI) -> DrawnItemAction | None:
        return self.toolbar.draw_menu_editable_action()

    def update_draw_menu(self: SupportUI, drawn_items: list['QgsMapCanvasItem'], new_drawn_item: 'QgsMapCanvasItem | None'):
        # add new drawn items to the menu and rename existing ones
        map_item2action = {a.map_item: a for a in self.toolbar.drawn_item_actions()}
        for i, map_item in enumerate(drawn_items):
            text = f'Item {i + 1}'
            if map_item in map_item2action:
                action = map_item2action[map_item]
                action.setText(text)
                continue
            self.toolbar.add_drawn_item_action(text, map_item, map_item == new_drawn_item)

        # remove actions that no longer should be in the menu
        for action in self.toolbar.drawn_item_actions():
            if action.map_item not in drawn_items:
                self.toolbar.remove_drawn_item_action(action)
