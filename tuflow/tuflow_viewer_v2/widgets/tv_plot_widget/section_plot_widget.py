import logging

import numpy as np

from qgis.PyQt.QtCore import QPointF, QSettings
from qgis.PyQt.QtGui import QPolygonF

from .base_plot_widget import TVPlotWidget
from .mixins.section_plot_helper_mixin import SectionPlotHelperMixin
from .plotsourceitem import PlotSourceItem
from .pyqtgraph_subclass.hoverable_curve_item import HoverableCurveItem
from .pyqtgraph_subclass.hoverable_scatter_plot import HoverableScatterPlot
from .pyqtgraph_subclass.polygon import Polygons
from ...tvdeveloper_tools import Profiler
from ...tvinstance import get_viewer_instance

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ....pyqtgraph import mkPen, mkBrush
    from ....pt.pytuflow import misc
else:
    from tuflow.pyqtgraph import mkPen, mkBrush
    from tuflow.pt.pytuflow import misc


logger = logging.getLogger('tuflow_viewer')


class SectionPlotWidget(TVPlotWidget, SectionPlotHelperMixin):
    PLOT_TYPE = 'Section'

    def __init__(self, parent=None):
        self._geom_type = 'line'
        super().__init__(parent)
        self._init_plot_helper()
        self.toolbar.branch_selection_changed.connect(self.update_branch_visibility)
        self._geom_cache = {}  # for long plots, saves having to do the same expensive feature queries multiple times

    def close(self):
        super().close()
        self._teardown_plot_helper()

    def plot_data_types(self, output_names: list[str]) -> list[str]:
        return [x for x in get_viewer_instance().data_types(output_names, 'section') if x != 'node flow regime']

    def plot_data_types_3d(self, output_names: list[str]) -> list[str]:
        return [x for x in get_viewer_instance().data_types(output_names, 'section/3d') if x != 'node flow regime']

    def qgis_time_changed(self):
        super().qgis_time_changed()
        self.update_plot()

    def _update_plot(self, for_adding: list[PlotSourceItem], for_overwrite: list[PlotSourceItem]):
        profiler = Profiler()
        profiler('Section Plot Total Time')

        colours_retained = set()
        time = self.qgis_current_time()
        for src_item in for_adding:
            for src_item_filled in self._populate_plot_data(src_item, time):
                if not src_item_filled.ready_for_plotting:
                    continue

                self.branch_count = max(self.branch_count, src_item_filled.branch_count)

                # long plot geometry
                if src_item_filled.channel_ids:
                    key = f'{src_item_filled.output_id}/{src_item_filled.loc}'
                    if key not in self._geom_cache:
                        profiler('Section - long_plot_geom()')
                        geom = self.long_plot_geom(src_item_filled.output.id, src_item_filled.channel_ids)
                        self._geom_cache[key] = geom
                        profiler('Section - long_plot_geom()')
                    src_item_filled.geom = self._geom_cache[key]

                if src_item_filled.is_pipes:
                    profiler('Section - Plot Pipes')
                    self.plot_pipes(src_item_filled)
                    profiler('Section - Plot Pipes')
                    continue

                if src_item_filled.is_pits:
                    profiler('Section - Plot Pits')
                    self.plot_pits(src_item_filled)
                    profiler('Section - Plot Pits')
                    continue

                if self._overwrite_existing_plot_item(src_item_filled, for_overwrite, colours_retained):
                    src_item.colour = src_item_filled.colour
                    continue

                profiler('Section - Add New Plot Item')
                c = src_item.colour if src_item.colour else self.next_colour(src_item_filled.sel_type)  # use same colour for different branches (use item here not item_)
                src_item.colour = c
                src_item_filled.colour = c
                c = self._colours.shift_colour(c, self.plot_graph.getViewBox())  # shift colour if it is already in use on the same plot
                plot_item = HoverableCurveItem(
                    x=src_item_filled.xdata,
                    y=src_item_filled.ydata,
                    name=src_item_filled.label,
                    pen=mkPen(c, width=2),
                    src_item=src_item_filled,
                    connect='finite'
                )
                self.plot_graph.addItem(plot_item)
                if src_item_filled.feedback_context != 'static':
                    self._cursor_tracker.add_tracker(plot_item, src_item_filled.geom)
                plot_item.sigHoverEvent.connect(self._on_hover)

                if src_item_filled.branch_count > 1 and not self.toolbar.branch_selector.is_checked(src_item_filled.branch):
                    plot_item.setVisible(False)
                    self._cursor_tracker.set_visible(plot_item, False)

                profiler('Section - Add New Plot Item')

        self.remove_items_from_plot(for_overwrite, colours_retained)
        self.toolbar.branch_selector.set_count(self.branch_count)
        self.toolbar.branch_selector_action.setVisible(bool(self.branch_count > 1))

        profiler('Section Plot Total Time')
        profiler.report()

    def _overwrite_existing_plot_item(self, src_item: PlotSourceItem, for_overwrite: list[PlotSourceItem], colours_retained: set) -> bool:
        if not for_overwrite:
            return False

        idx, idxs = None, []

        if self._time_updated:  # if time updated then try and match ids exactly
            idxs = [i for i, x in enumerate(for_overwrite) if x.id == src_item.id]

        if not idxs:  # try and match id but ignore the ID and match the data type and result name
            idxs = [i for i, x in enumerate(for_overwrite) if src_item.fuzzy_match(x) and x.data_type not in ['pipes', 'pits']]
            if not idxs:  # just grab the first one that isn't pipes or pits
                idxs = [i for i, x in enumerate(for_overwrite) if x.data_type not in ['pipes', 'pits']]

        idxs = sorted(idxs, key=lambda x: for_overwrite[x].branch if for_overwrite[x].branch_count > 1 else 999)
        idx = idxs[src_item.branch] if len(idxs) > src_item.branch else (idxs[0] if idxs else None)

        if idx is None or (src_item.branch > 0 and for_overwrite[idx].colour != src_item.colour):
            return False

        profiler = Profiler()
        profiler('Section - Overwrite Plot Item')

        item_for_overwrite = for_overwrite.pop(idx)
        plot_item = self.item_2_curve(item_for_overwrite, self.plot_graph)
        colours_retained.add(item_for_overwrite.colour)
        src_item.colour = item_for_overwrite.colour
        plot_item.setData(x=src_item.xdata, y=src_item.ydata, name=src_item.label)
        plot_item.src_item = src_item
        plot_item.update_channel_curve_data()

        if src_item.feedback_context == 'static' and plot_item in self._cursor_tracker:
            self._cursor_tracker.remove_tracker(plot_item)
        elif src_item.feedback_context != 'static' and plot_item not in self._cursor_tracker:
            self._cursor_tracker.add_tracker(plot_item, src_item.geom)
        elif src_item.feedback_context != 'static':
            self._cursor_tracker.set_geometry(plot_item, src_item.geom)

        if src_item.branch_count > 1 and not self.toolbar.branch_selector.is_checked(src_item.branch):
            plot_item.setVisible(False)
            if src_item.feedback_context != 'static':
                self._cursor_tracker.set_visible(plot_item, False)
        else:
            plot_item.setVisible(True)

        profiler('Section - Overwrite Plot Item')
        return True

    def long_plot_geom(self, output_id: str, ids: list[str]):
        if self.get_plot_layer(output_id, 'Line') is None:
            return []
        output = get_viewer_instance().output(output_id)
        profiler = Profiler()
        profiler('Section - QGIS feature query')
        filter_ = '"ID" in ({0})'.format(','.join(f"'{id_}'" for id_ in set(ids)))
        if output.DRIVER_NAME == 'GPKG Time Series':
            start = '{0:%Y}-{0:%m}-{0:%d}T{0:%H}:{0:%M}:{0:%S}.{0:%f}'.format(self.qgis_current_time())
            end = '{0:%Y}-{0:%m}-{0:%d}T{0:%H}:{0:%M}:{0:%S}.{0:%f}'.format(self.qgis_time_range_end())
            filter_ = '{0} AND "Datetime" >= \'{1}\' AND "Datetime" < \'{2}\''.format(filter_, start, end)
        feats = list(self.get_plot_layer(output_id, 'Line').getFeatures(filter_))
        profiler('Section - QGIS feature query')
        geom = []
        prev_id = None
        for id_ in ids:
            if id_ == prev_id:
                continue
            prev_id = id_
            for feat in feats:
                if feat['ID'] == id_:
                    geom1 = feat.geometry()
                    if geom1.isMultipart():
                        geom1 = geom1.asMultiPolyline()[0]
                    else:
                        geom1 = geom1.asPolyline()
                    geom.extend([(x.x(), x.y()) for x in geom1 if not np.isnan(x.x())])
                    break
        return geom

    def plot_pipes(self, src_item: PlotSourceItem):
        # create polygons
        polygons = [
            QPolygonF([
                QPointF(x_, src_item.ydata[i*2,0]),
                QPointF(src_item.xdata[i*2+1], src_item.ydata[i*2+1,0]),
                QPointF(src_item.xdata[i*2+1], src_item.ydata[i*2+1,1]),
                QPointF(x_, src_item.ydata[i*2,1])
            ]) for i, x_ in enumerate(src_item.xdata[::2])
        ]
        # pack polygons with channel and node ids, removing any with NaN vertex values
        polygons = [
            [
                x,
                src_item.channel_ids[i*2],
                src_item.node_ids[i*2],
                src_item.node_ids[i*2+1]
            ] for i, x in enumerate(polygons) if not any([np.isnan(y.y()) for y in x])
        ]

        # unpack now that invalid polygons have been removed
        node_ids = misc.flatten([x[2:] for x in polygons])
        channel_ids = [x[1] for x in polygons]
        polygons = [x[0] for x in polygons]

        # add curve to plot
        pipes = Polygons(polygons, channel_ids, node_ids, src_item)
        self.plot_graph.addItem(pipes)
        pipes.setZValue(-100)  # ensure polygons are behind lines/points

        # setup interactivity
        self._cursor_tracker.add_tracker(pipes, src_item.geom)
        pipes.sigHoverEvent.connect(self._on_hover)
        if src_item.branch_count > 1 and not self.toolbar.branch_selector.is_checked(src_item.branch):
            pipes.setVisible(False)
            self._cursor_tracker.set_visible(pipes, False)

    def plot_pits(self, src_item: PlotSourceItem):
        scatter_plot = HoverableScatterPlot(
            x=src_item.xdata,
            y=src_item.ydata,
            src_item=src_item,
            pen=mkPen(color=(0, 0, 0), width=1),
            brush=mkBrush('r'),
            symbol='o',
            size=7,
            feedback_context='node feature'
        )
        self.plot_graph.addItem(scatter_plot)
        scatter_plot.sigHoverEvent.connect(self._on_hover)
        if src_item.branch_count > 1 and not self.toolbar.branch_selector.is_checked(src_item.branch):
            scatter_plot.setVisible(False)

    def update_branch_visibility(self):
        branch_selection = self.toolbar.selected_branches()
        for src_item in self.get_current_combinations_on_plot():
            if src_item.branch_count < 2:
                continue
            plot_item = self.item_2_curve(src_item, self.plot_graph)
            if not plot_item:
                continue
            vis = src_item.branch in branch_selection
            plot_item.setVisible(vis)
            self._cursor_tracker.set_visible(plot_item, vis)
