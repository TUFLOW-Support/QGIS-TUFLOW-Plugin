from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QAction

from .base_plot_widget import TVPlotWidget
from .mixins.profile_plot_helper_mixin import ProfilePlotHelperMixin
from .plotsourceitem import PlotSourceItem
from .pyqtgraph_subclass.hoverable_curve_item import HoverableCurveItem

from ...tvinstance import get_viewer_instance
from ...tvdeveloper_tools import Profiler

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ....pyqtgraph import mkPen, InfiniteLine
    from ....compatibility_routines import QT_STYLE_DASHED_PEN
else:
    from tuflow.pyqtgraph import mkPen, InfiniteLine


class ProfilePlotWidget(TVPlotWidget, ProfilePlotHelperMixin):
    PLOT_TYPE = 'Profile'

    def __init__(self, parent=None):
        self._geom_type = 'marker'
        super(ProfilePlotWidget, self).__init__(parent)
        self._init_plot_helper()

        self._interpolation_method = 'stepped'
        self._level_boundary_curves = {}

        # context menu
        # interpolation method
        self.add_context_menu_group(group_name='profile', insert_before=['Plot Options'])
        self.lerp_profile_action = QAction('Linear interpolation between levels', self)
        self.lerp_profile_action.setCheckable(True)
        self.lerp_profile_action.setChecked(False)
        self.lerp_profile_action.toggled.connect(self._lerp_profile_toggled)
        self.add_context_menu_action(
            self.lerp_profile_action,
            position=0,
            group_name='profile',
            callback=lambda x: True,
        )
        # vertical level boundaries
        self.vertical_boundary_action = QAction('Show vertical level boundaries', self)
        self.vertical_boundary_action.setCheckable(True)
        self.vertical_boundary_action.setChecked(False)
        self.vertical_boundary_action.toggled.connect(self._update_vertical_boundaries)
        self.add_context_menu_action(
            self.vertical_boundary_action,
            position=1,
            group_name='profile',
            callback=lambda x: True,
        )

    def close(self):
        super().close()
        self._teardown_plot_helper()

    def plot_data_types(self, output_names: list[str]) -> list[str]:
        data_types = []
        output_names = [y for y in output_names for x in get_viewer_instance().outputs(y) if x.LAYER_TYPE == 'Surface']
        excluded_types = ['bed level', 'water level', 'max water level', 'depth', 'max depth']
        excluded_pat = 'tmax'
        for output_name in output_names:
            dtypes = get_viewer_instance().data_types([output_name], 'section')
            if ('bed level' not in dtypes or 'water level' not in dtypes) and not get_viewer_instance().data_types(
                    [output_name], '3d'):
                continue
            data_types.extend([x for x in dtypes if x not in excluded_types and excluded_pat not in x.lower()])
        return data_types

    def qgis_time_changed(self):
        super().qgis_time_changed()
        self.update_plot()

    def create_secondary_axis(self, axis_pos: str = 'right'):
        super().create_secondary_axis('top')

    def _lerp_profile_toggled(self, checked: bool):
        self._interpolation_method = 'linear' if checked else 'stepped'
        self._time_updated = True  # abuse time updated variable :(
        self.update_plot()

    def _update_vertical_boundaries(self, checked: bool):
        outputs = []
        for item in self.plot_graph.items():
            if not isinstance(item, HoverableCurveItem):
                continue
            src_item = item.src_item
            if src_item.output in outputs:
                continue
            outputs.append(src_item.output)
            lvls = src_item.level_boundaries.copy()
            if src_item.output in self._level_boundary_curves:
                curves = self._level_boundary_curves[src_item.output].copy()
                for i in range(len(lvls)):
                    z = lvls.pop(0)
                    if not curves:
                        break
                    curve = curves.pop(0)
                    if checked:
                        curve.setValue(z)
                    else:
                        self.plot_graph.removeItem(curve)
                if curves:
                    for curve in curves:
                        self.plot_graph.removeItem(curve)
                        self._level_boundary_curves[src_item.output].remove(curve)
            if lvls and checked:
                for z in lvls:
                    curve = InfiniteLine(
                        pos=z,
                        angle=0,
                        pen=mkPen('#fc5b5b', style=QT_STYLE_DASHED_PEN),
                        movable=False,
                    )
                    self.plot_graph.addItem(curve)
                    if src_item.output not in self._level_boundary_curves:
                        self._level_boundary_curves[src_item.output] = []
                    self._level_boundary_curves[src_item.output].append(curve)
            if not checked:
                self._level_boundary_curves[src_item.output] = []

    def _update_plot(self, for_adding: list['PlotSourceItem'], for_overwrite: list['PlotSourceItem']):
        profiler = Profiler()
        profiler('Profile Plot Total Time')

        colours_retained = set()
        time = self.qgis_current_time()
        for src_item in for_adding:
            for src_item_filled in self._populate_plot_data(src_item, time, self._interpolation_method):
                if not src_item_filled.ready_for_plotting:
                    continue

                if self._overwrite_existing_plot_item(src_item_filled, for_overwrite, colours_retained):
                    continue

                profiler('Profile - Add New Plot Item')
                c = src_item_filled.colour if src_item_filled.colour else self.next_colour(src_item_filled.sel_type)
                src_item_filled.colour = c
                c = self._colours.shift_colour(c, self.plot_graph.getViewBox())  # shift colour if it is already in use on the same plot
                plot_item = HoverableCurveItem(
                    x=src_item_filled.xdata,
                    y=src_item_filled.ydata,
                    name=src_item_filled.label,
                    pen=mkPen(c, width=2),
                    src_item=src_item_filled,
                )
                self.plot_graph.addItem(plot_item)
                plot_item.sigHoverEvent.connect(self._on_hover)
                profiler('Profile - Add New Plot Item')

        self.remove_items_from_plot(for_overwrite, colours_retained)
        if self._time_updated and self.vertical_boundary_action.isChecked():
            self._update_vertical_boundaries(True)

        profiler('Profile Plot Total Time')
        profiler.report()

    def _overwrite_existing_plot_item(self, src_item: PlotSourceItem, for_overwrite: list[PlotSourceItem], colours_retained: set[str]) -> bool:
        if not for_overwrite:
            return False

        idx, idxs = None, []

        if self._time_updated:  # if time updated then try and match ids exactly
            idxs = [i for i, x in enumerate(for_overwrite) if x.id == src_item.id]

        if not idxs:  # try and match id but ignore the ID and match the data type and result name
            idxs = [i for i, x in enumerate(for_overwrite) if src_item.fuzzy_match(x) ]
            if not idxs:  # just grab the first one that isn't pipes or pits
                idxs = [i for i, x in enumerate(for_overwrite)]

        idx = idxs[0] if idxs else None
        if idx is None:
            return False

        profiler = Profiler()
        profiler('Profile - Overwrite Plot Item')
        item_for_overwrite = for_overwrite.pop(idx)
        plot_item = self.item_2_curve(item_for_overwrite, self.plot_graph)
        colours_retained.add(item_for_overwrite.colour)
        src_item.colour = item_for_overwrite.colour
        plot_item.setData(x=src_item.xdata, y=src_item.ydata, name=src_item.label)
        plot_item.src_item = src_item
        plot_item.setVisible(True)
        profiler('Profile - Overwrite Plot Item')
        return True
