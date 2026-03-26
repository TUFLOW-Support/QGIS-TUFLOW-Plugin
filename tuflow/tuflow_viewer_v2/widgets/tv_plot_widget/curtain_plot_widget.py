from copy import deepcopy
from datetime import datetime

from qgis.PyQt.QtWidgets import QMenu, QAction
from qgis.PyQt.QtCore import QSettings

from .base_plot_widget import TVPlotWidget
from .mixins.curtain_plot_helper_mixin import CurtainPlotHelperMixin
from .plotsourceitem import PlotSourceItem
from .pyqtgraph_subclass.polycollection import PolyCollection
from .pyqtgraph_subclass.quiver import Quiver, ArrowPainterScaledByMagnitude, ArrowPainterDefinedByMinMax, ArrowPainterFixed

from ...tvinstance import get_viewer_instance
from ...tvdeveloper_tools import Profiler
from ...widgets.slider_widget_action import SliderWidgetAction
from ...theme import TuflowViewerTheme

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ....pyqtgraph import mkPen, mkBrush
else:
    from tuflow.pyqtgraph import mkPen, mkBrush


class CurtainPlotWidget(TVPlotWidget, CurtainPlotHelperMixin):
    PLOT_TYPE = 'Curtain'

    def __init__(self, parent=None):
        self._geom_type = 'line'
        super(CurtainPlotWidget, self).__init__(parent)
        self._init_plot_helper()

        self.curtain_grid_line_thickness = 0.1
        self.curtain_grid_line_colour = '#000000' if get_viewer_instance().theme.theme_name != 'Night Mapping' else '#999999'

        # context menu group
        self.add_context_menu_group(group_name='curtain', insert_before=['Plot Options'])

        # vectors
        self.vector_menu = QMenu('Velocity vectors', self)
        self.show_vectors_action = QAction('Show vectors', self)
        self.show_vectors_action.setCheckable(True)
        self.show_vectors_action.setChecked(False)
        self.show_vectors_action.toggled.connect(self.show_vectors)
        self.vector_menu.addAction(self.show_vectors_action)
        self.add_context_menu_action(
            self.show_vectors_action,
            position=0,
            group_name='curtain',
            callback=lambda x: True,
        )
        self.vertical_velocity_scale_menu = QMenu('Vertical velocity scale', self)
        self.vertical_velocity_scale_slider = SliderWidgetAction(self)
        self.vertical_velocity_scale_slider.set_minimum(0.)
        self.vertical_velocity_scale_slider.set_slider_max(2.)
        self.vertical_velocity_scale_slider.set_value(1.)
        self.vertical_velocity_scale_slider.value_changed.connect(self.vertical_velocity_scale_changed)
        self.vertical_velocity_scale_menu.addAction(self.vertical_velocity_scale_slider)
        self.add_context_menu_action(
            self.vertical_velocity_scale_menu.menuAction(),
            position=1,
            group_name='curtain',
            callback=lambda x: True,
        )

        # curtain grid line thickness
        self.curtain_grid_line_menu = QMenu('Curtain grid line thickness', self)
        self.curtain_grid_line_thickness_action = SliderWidgetAction(self)
        self.curtain_grid_line_thickness_action.set_minimum(0.01)
        self.curtain_grid_line_thickness_action.set_value(self.curtain_grid_line_thickness)
        self.curtain_grid_line_thickness_action.value_changed.connect(self._curtain_grid_line_thickness_changed)
        self.curtain_grid_line_menu.addAction(self.curtain_grid_line_thickness_action)
        self.add_context_menu_action(
            self.curtain_grid_line_menu.menuAction(),
            position=2,
            group_name='curtain',
            callback=lambda x: True,
        )

        self.plot_graph.getViewBox().sigRangeChanged.connect(self._plot_graph_range_changed)
        self.plot_graph.getViewBox().sigTransformChanged.connect(self._plot_graph_range_changed)

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
            if ('bed level' not in dtypes or 'water level' not in dtypes) and not get_viewer_instance().data_types([output_name], '3d'):
                continue
            data_types.extend([x for x in dtypes if x not in excluded_types and excluded_pat not in x.lower()])
        return data_types

    def qgis_time_changed(self):
        super().qgis_time_changed()
        self.update_plot()

    def set_theme(self, theme: TuflowViewerTheme):
        super().set_theme(theme)
        self.curtain_grid_line_colour = '#000000' if theme.theme_name != 'Night Mapping' else '#999999'
        for item in self.plot_graph.items():
            if isinstance(item, PolyCollection):
                item.set_grid_line_colour(self.curtain_grid_line_colour)
        self.plot_graph.update()

    def _plot_graph_range_changed(self, *args):
        if self.show_vectors_action.isChecked():
            for item in self.plot_graph.items():
                if isinstance(item, Quiver):
                    item.update()

    def vertical_velocity_scale_changed(self, value: int):
        if self.show_vectors_action.isChecked():
            self.show_vectors(True)

    def show_vectors(self, show: bool) -> list[PlotSourceItem]:
        def get_cached_data(wkt: str, output_id: str, time: datetime):
            if wkt not in self._vector_cache:
                return None
            if output_id not in self._vector_cache[wkt]:
                return None
            if time not in self._vector_cache[wkt][output_id]:
                return None
            vec = self._vector_cache[wkt][output_id][time]
            if not self.vertical_velocity_scale_slider.value() > 0. or 'vertical velocity' not in get_viewer_instance().output(output_id).data_types():
                return vec
            if wkt not in self._vert_vel_cache or output_id not in self._vert_vel_cache[wkt] or time not in self._vert_vel_cache[wkt][output_id]:
                return None
            vec['vector_y'] = self._vert_vel_cache[wkt][output_id][time] * self.vertical_velocity_scale_slider.value()
            return vec

        def get_velocity_vectors(wkt: str, output_id: str, time: datetime):
            """Get cached data. If cached data does not exist, populate it."""
            data = get_cached_data(wkt, output_id, time)
            if data is not None:
                return data
            outputs = [
                output for result_name in self.toolbar.selected_result_names() for output in get_viewer_instance().outputs(result_name)
            ]
            if time == 'max':
                data_types = ['max velocity']
            elif time == 'min':
                data_types = ['min velocity']
            else:
                data_types = ['velocity']
            if self.vertical_velocity_scale_slider.value() > 0.:
                data_types.append('vertical velocity')
            src_items = self.items_for_plotting(
                outputs, data_types, [], self.toolbar.selection_includes_map_outputs()
            )
            for src_item in src_items:
                for _ in self._populate_plot_data(src_item, time):
                    pass
            return get_cached_data(wkt, output_id, time)

        vector_items = []  # returned list of source items that are the vector items

        # list of existing curtain plot PolyCollection items - these will get the vectors added to them
        items = {
            (
                self._line_to_wkt(item.src_item.geom), item.src_item.output_id
            ): item.src_item for item in self.plot_graph.items() if isinstance(item, PolyCollection)
        }

        time = self.qgis_current_time()

        # first update existing vector plot items
        used_keys = []
        for item in self.plot_graph.items():
            if not isinstance(item, Quiver):
                continue
            key = (self._line_to_wkt(item.src_item.geom), item.src_item.output.id)
            if key in used_keys or key not in items:
                continue
            items.pop(key)
            used_keys.append(key)
            if not show:
                item.setVisible(False)
                continue
            item.setVisible(True)
            if item.src_item.data_type.startswith('max'):
                t = 'max'
            elif item.src_item.data_type.startswith('min'):
                t = 'min'
            else:
                t = time
            vector_data = get_velocity_vectors(*key, t)
            if vector_data is None:
                continue
            item.setData(
                pos=vector_data[['x', 'y']].to_numpy(),
                values=vector_data[['vector_x', 'vector_y']].to_numpy(),
                src_item=item.src_item
            )
            vector_items.append(item.src_item)

        # if there are any remaining items, these are new and need to be added
        for item, src_item in items.items():
            wkt, output_id = item
            if src_item.data_type.startswith('max'):
                t = 'max'
            elif src_item.data_type.startswith('min'):
                t = 'min'
            else:
                t = time
            vector_data = get_velocity_vectors(wkt, output_id, t)
            if vector_data is None:
                continue

            output = get_viewer_instance().output(output_id)
            min_ = 0.
            max_ = output.maximum('velocity')
            ismax = src_item.data_type.startswith('max')
            ismin = src_item.data_type.startswith('min')
            arrow_painter = self._create_vector_painter(output, ismax, ismin, only_if_updated=False)

            # debug - use HoverableScatterPlot for now
            src_item1 = deepcopy(src_item)
            src_item1.id = f'{src_item1.id}.vector'
            plot_item = Quiver(
                pos=vector_data[['x', 'y']].to_numpy(),
                values=vector_data[['vector_x', 'vector_y']].to_numpy(),
                pen=mkPen(width=0.26, color='#000000'),
                brush=mkBrush(color=(0, 0, 0)),
                src_item=src_item1,
            )
            plot_item.painter = arrow_painter
            plot_item.setZValue(100)
            self.plot_graph.addItem(plot_item)
            vector_items.append(src_item1)

        return vector_items

    def _curtain_grid_line_thickness_changed(self, value: float):
        self.curtain_grid_line_thickness = value
        for item in self.plot_graph.items():
            if isinstance(item, PolyCollection):
                item.set_grid_line_thickness(value)
        self.plot_graph.update()

    def _update_plot(self, for_adding: list['PlotSourceItem'], for_overwrite: list['PlotSourceItem']):
        profiler = Profiler()
        profiler('Curtain Plot Total Time')

        time = self.qgis_current_time()
        for src_item in for_adding:
            for src_item_filled in self._populate_plot_data(src_item, time):
                if not src_item_filled.ready_for_plotting:
                    continue

                if self._overwrite_existing_plot_item(src_item_filled, for_overwrite):
                    continue

                profiler('Curtain - Add New Plot Item')
                plot_item = PolyCollection(
                    polygons=src_item_filled.xdata,
                    values=src_item_filled.ydata,
                    src_item=src_item_filled,
                    pen=mkPen(width=self.curtain_grid_line_thickness, color='#888888' if get_viewer_instance().theme.theme_name == 'Night Mapping' else '#000000'),
                )
                self.plot_graph.addItem(plot_item)
                self._cursor_tracker.add_tracker(plot_item, src_item_filled.geom)
                plot_item.sigHoverEvent.connect(self._on_hover)
                profiler('Curtain - Add New Plot Item')

        if self.show_vectors_action.isChecked():
            vector_items = self.show_vectors(True)
            for item in vector_items:
                if item in for_overwrite:
                    for_overwrite.remove(item)

        # remove overwritten items
        self.remove_items_from_plot(for_overwrite)

        profiler('Curtain Plot Total Time')
        profiler.report()

    def _overwrite_existing_plot_item(self, src_item: PlotSourceItem, for_overwrite: list[PlotSourceItem]) -> bool:
        if not for_overwrite:
            return False

        idx, idxs = None, []

        if self._time_updated:  # if time updated then try and match ids exactly
            idxs = [i for i, x in enumerate(for_overwrite) if x.id == src_item.id]

        if not idxs:  # try and match id but ignore the ID and match the data type and result name
            idxs = [i for i, x in enumerate(for_overwrite) if src_item.fuzzy_match(x) if not x.id.endswith('.vector')]
            if not idxs:  # just grab the first one that isn't pipes or pits
                idxs = [i for i, x in enumerate(for_overwrite) if not x.id.endswith('.vector')]

        idx = idxs[0] if idxs else None
        if idx is None:
            return False

        profiler = Profiler()
        profiler('Curtain - Overwrite Plot Item')
        item_for_overwrite = for_overwrite.pop(idx)
        plot_item = self.item_2_curve(item_for_overwrite, self.plot_graph)
        src_item.colour = item_for_overwrite.colour
        plot_item.setData(x=src_item.xdata, y=src_item.ydata)
        plot_item.src_item = src_item
        plot_item.setVisible(True)
        self._cursor_tracker.set_geometry(plot_item, src_item.geom)
        profiler('Curtain - Overwrite Plot Item')
        return True
