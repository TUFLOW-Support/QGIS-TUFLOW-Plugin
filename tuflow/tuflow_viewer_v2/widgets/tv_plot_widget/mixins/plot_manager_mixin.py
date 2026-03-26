from __future__ import annotations
import typing

from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsProject, Qgis

from ....selection import Selection, DrawnSelection, SelectionItem
from ..plotsourceitem import PlotSourceItem
from ..pyqtgraph_subclass.hoverable_curve_item import HoverableCurveItem
from ..pyqtgraph_subclass.tuflow_viewer_curve import TuflowViewerCurve

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pt.pytuflow import TimeSeries, MapOutput
    from ....tvinstance import get_viewer_instance
    from ....fmts.fmts import FMTS
else:
    from tuflow.pt.pytuflow import TimeSeries, MapOutput
    from tuflow.tuflow_viewer_v2.tvinstance import get_viewer_instance
    from tuflow.tuflow_viewer_v2.fmts import FMTS

if typing.TYPE_CHECKING:
    from qgis.core import QgsVectorLayer
    from ....fmts.tvoutput import TuflowViewerOutput
    from ..pyqtgraph_subclass.custom_plot_widget import CustomPlotWidget
    from qgis.gui import QgsMapCanvasItem


class PlotManagerMixin:
    """Handles adding/removing items on the plot,
    and exposing hooks for subclasses to implement their plotting logic.

    Does not depend on any other mixins.
    """

    def _init_plot_manager(self):
        self._selection = Selection(None, [])
        self.secondary_vb = None
        self.branch_count = 1
        QgsProject.instance().layersRemoved.connect(self.layers_removed)

    def _teardown_plot_manager(self):
        try:
            QgsProject.instance().layersRemoved.disconnect(self.layers_removed)
        except Exception:
            pass

    def layers_removed(self, lyrids: list[str]):
        for lyrid in lyrids:
            while self._selection.pop('selection', lyrid=lyrid):
                pass

    def plot_data_types(self, output_names: list[str]) -> list[str]:
        """Returns a list of all supported/available data types based on the plot type
        and the checked-on results.

        Should be overridden by subclasses to provide specific data types for the plot type.
        """
        return []

    def plot_data_types_3d(self, output_names: list[str]) -> list[str]:
        """Returns a list of all supported/available 3D data types based on the plot type
        and the checked-on results.

        Should be overridden by subclasses to provide specific data types for the plot type.
        """
        return []

    def create_item_id(self, plot_type: str, output_id: str, domain: str, data_type: str, loc: str | list[str], sub_id: int = 0) -> str:
        """Creates a uniqe identifier based on the plot type, output ID, data type, and location."""
        if isinstance(loc, list):
            loc = '&'.join(loc)
        return f'{plot_type}/{output_id}/{domain}/{data_type}/{loc}/{sub_id}'

    def update_feature_selection(self, lyr: 'QgsVectorLayer | None', selected_fids: list[int]):
        """Updates the selection with `the selected features from the given layer."""
        lyrid = lyr.id() if lyr and lyr.isValid() else ''
        while self._selection.pop('selection', lyrid=lyrid):
            pass
        if lyrid:
            self._selection = self._selection + Selection(lyr, lyr.getFeatures(selected_fids))

    def add_drawn_item_to_selection(self, map_item: 'QgsMapCanvasItem'):
        """Adds a drawn item to the current selection."""
        sel = DrawnSelection(map_item)
        self._selection = self._selection + sel

    def remove_drawn_item_from_selection(self, map_item: 'QgsMapCanvasItem') -> SelectionItem | None:
        """Removes a drawn item from the current selection. Returns the removed selection.
        Returns None if nothing was removed.
        """
        c = map_item.color() if self._geom_type == 'marker' else map_item.fillColor()
        return self._selection.pop('drawn', colour=c.name())

    def clear_selection(self):
        """Clear entire current selection."""
        while self._selection.pop():
            pass

    def clear_feature_selection(self):
        """Clear all selected features from the current selection."""
        while self._selection.pop('selection'):
            pass

    def clear_drawn_selection(self):
        """Clear the drawn selection from the current selection."""
        while self._selection.pop('drawn'):
            pass

    def items_for_plotting(self,
                           outputs: list['TuflowViewerOutput'],
                           data_types: list[str],
                           items_on_plot: list[PlotSourceItem],
                           allow_map_output_feature_selection: bool) -> list[PlotSourceItem]:
        def is_long_section_channel(sel) -> bool:
            sel_output = get_viewer_instance().map_layer_to_output(sel_lyr) if sel_lyr is not None else None
            return sel.domain == 'channel' or (sel.domain == 'node' and isinstance(sel_output, FMTS))

        self.branch_count = 1
        comb = []
        comb_id = []
        for output in outputs:
            channel_used = False
            static_types = output.data_types('static')
            for sel in self._selection:
                sel_lyr = QgsProject.instance().mapLayer(sel.lyrid)
                sel_output = get_viewer_instance().map_layer_to_output(sel_lyr) if sel_lyr is not None else None
                if sel_output and sel_output != output and sel_output.LAYER_TYPE != output.LAYER_TYPE and sel.sel_type != 'drawn' and sel.is_tv_layer:
                    continue
                ids = sel.id
                if ids.startswith('TUFLOW-VIEWER::'):
                    ids = ids.split('::', 2)[1]
                if isinstance(output, TimeSeries) and (not sel.is_tv_layer or sel.sel_type == 'drawn'):
                    continue
                if is_long_section_channel(sel) and not channel_used and self.PLOT_TYPE == 'Section':
                    channel_used = True
                    for sel1 in self._selection:
                        if sel1.id == sel.id or not is_long_section_channel(sel1):
                            continue
                        id1 = sel1.id.split('::', 2)[1]
                        ids = [ids] + [id1] if not isinstance(ids, list) else ids + [id1]
                elif is_long_section_channel(sel) and channel_used:
                    continue
                for dtype in data_types:
                    dtype_, _ = self._split_depth_averaging(dtype)
                    if dtype_ not in output.data_types(f'{self.PLOT_TYPE.lower()}/{sel.domain_geom}'):
                        continue
                    id_ = self.create_item_id('curve', output.id, sel.domain, dtype, ids)
                    if isinstance(output, MapOutput) and sel.sel_type == 'selection':
                        if not allow_map_output_feature_selection and id_ not in items_on_plot:
                            continue
                    if id_ in comb_id:
                        continue
                    comb_id.append(id_)
                    static = dtype in static_types
                    item = PlotSourceItem(
                        id_,
                        'curve',
                        output.id,
                        dtype,
                        ids,
                        sel.domain,
                        sel.geom,
                        sel.is_tv_layer,
                        sel.colour,
                        sel.sel_type,
                        static,
                        sel.chan_type
                    )
                    if item in items_on_plot:
                        item_ = items_on_plot[items_on_plot.index(item)]
                        self.branch_count = max(self.branch_count, item_.branch + 1)
                    comb.append(item)
        return comb

    def remove_items_from_plot(self, items: list[PlotSourceItem], retained_colours: set[str] = ()):
        for item in items:
            plot_item = self.item_2_curve(item, self.plot_graph)
            if self._time_updated:
                plot_item.setVisible(False)
                continue
            if plot_item is None:
                continue
            self._colours.release_shifted(item.colour, plot_item.hover_colour, plot_item.getViewBox())
            if plot_item.sel_type == 'selection' and item.colour is not None and item.colour not in retained_colours:
                self.release_colour(plot_item.hover_colour, 'selection')
            if self._geom_type == 'line':
                self._cursor_tracker.remove_tracker(plot_item)
            plot_item.getViewBox().removeItem(plot_item)

    def items_on_plot(self, plot_items: list[TuflowViewerCurve]) -> list[PlotSourceItem]:
        comb = []
        for plot_item in plot_items:
            comb.append(plot_item.src_item)
        return comb

    def item_2_curve(self, item: PlotSourceItem, plot_graph: 'CustomPlotWidget') -> HoverableCurveItem | None:
        plot_item = [x for x in plot_graph.items() if isinstance(x, TuflowViewerCurve) and x.src_item.id == item.id]
        if item.data_type in ['pipes', 'pits']:
            plot_item = [x for x in plot_item if x.channel_ids == item.channel_ids]
        if plot_item:
            return plot_item[0]
        return None
