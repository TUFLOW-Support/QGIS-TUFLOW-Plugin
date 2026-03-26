import typing
import logging
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    from .....pt.pytuflow._outputs.pymesh.stubs import pandas as pd
from qgis.gui import QgsMapCanvasItem
from qgis.PyQt.QtCore import pyqtSignal, QPointF, QSettings
from qgis.PyQt.QtWidgets import QAction, QToolTip, QMenu, QFileDialog
from qgis.PyQt.QtGui import QColor

from ..pyqtgraph_subclass.hoverable_curve_item import HoverableCurveItem
from ..pyqtgraph_subclass.tuflow_viewer_curve import TuflowViewerCurve
from ..pyqtgraph_subclass.custom_view_box import CustomViewBox
from ..pyqtgraph_subclass.custom_axis import SecondaryAxisItem
from ..pyqtgraph_subclass.quiver import Quiver
from ....selection import Selection
from ....tvinstance import get_viewer_instance

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....compatibility_routines import QT_DASH_LINE, QT_SOLID_LINE
    from .....pyqtgraph.exporters import ImageExporter, SVGExporter
else:
    from tuflow.compatibility_routines import QT_DASH_LINE, QT_SOLID_LINE
    from tuflow.pyqtgraph.exporters import ImageExporter, SVGExporter

if typing.TYPE_CHECKING:
    from ..colours import ColourAllocator
    from ...tv_plot_toolbar import TVPlotToolBar
    from ..pyqtgraph_subclass.custom_plot_widget import CustomPlotWidget
    from .....pyqtgraph import PlotCurveItem
    from ..plotsourceitem import PlotSourceItem
    from qgis.PyQt.QtCore import pyqtBoundSignal
    from qgis.core import QgsFeature


logger = logging.getLogger('tuflow_viewer')


class SupportsQgisHooks(typing.Protocol):
    _geom_type: str

    def update_qgis_static_feedback(self, geom: list[float] | list[list[float]] | None) -> None: ...
    def update_qgis_cursor_tracking(self, pos: QPointF) -> None: ...
    def get_channel_feature(self, output_id: str, channel_id: str) -> 'QgsFeature | None': ...
    def get_node_feature(self, output_id: str, node_id: str) -> 'QgsFeature | None': ...


class SupportsPlotManager(typing.Protocol):
    secondary_vb: 'CustomViewBox | None' = None

    def clear_drawn_items(self) -> None: ...
    def clear_feature_selection(self) -> None: ...


class SupportsMenuToolbar(typing.Protocol):
    results_changed: 'pyqtBoundSignal'
    data_types_changed: 'pyqtBoundSignal'

    def add_context_menu_action(self, action: QAction, position: int, group_name: str, callback) -> None: ...
    def add_context_menu_group(self, group_name: str, insert_before: list[str]) -> None: ...
    def get_result_combinations_for_plotting(self, items_on_plot: list['PlotSourceItem']) -> list['PlotSourceItem']: ...
    def get_current_combinations_on_plot(self) -> list['PlotSourceItem']: ...


class SupportUI(SupportsQgisHooks, SupportsPlotManager, SupportsMenuToolbar, typing.Protocol):
    plot_graph: 'CustomPlotWidget'
    toolbar: 'TVPlotToolBar'
    _colours: 'ColourAllocator'

    def setToolTip(self, text: str) -> None: ...


class InteractionMixin:
    """Handles interaction with the plot, including hover events,
    plot linking, and draw tool management.

    Depends on QgisHooksMixin, PlotManagerMixin, and MenuToolbarMixin.
    """

    # custom signals
    plot_link_toggled = pyqtSignal(object, bool)
    drawn_item_geom_changed = pyqtSignal(QgsMapCanvasItem)

    def _init_interaction(self: SupportUI):
        # active (i.e. selected) curve item
        self._active_curve = None
        self._move_item = None

        # view box hover
        self.plot_graph.getViewBox().hovered.connect(self._on_view_box_hover)
        self.plot_graph.getViewBox().hoveredLeave.connect(self._on_view_box_hover_leave)

        # result name changed
        self.results_changed.connect(self.update_plot)

        # data type changed
        self.data_types_changed.connect(self.update_plot)

        # clear context action
        self._clear_plot_action = QAction('Clear', self)
        self._clear_plot_separator = QAction(self)
        self._clear_plot_separator.setSeparator(True)
        self._clear_plot_action.triggered.connect(self.clear_plot_all)
        self.add_context_menu_action(self._clear_plot_action, position=1, group_name='', callback=lambda x: True)
        self.add_context_menu_action(self._clear_plot_separator, position=2, group_name='', callback=lambda x: True)

        # move curve context actions
        self.add_context_menu_group(group_name='move_curve', insert_before=['X axis'])

        # move to secondary axis context action
        self._move_to_secondary_axis_action = QAction('Move to secondary axis', self)
        self._move_to_secondary_axis_action.triggered.connect(self._move_item_to_secondary_axis)
        self.add_context_menu_action(
            self._move_to_secondary_axis_action,
            position=0,
            group_name='move_curve',
            callback=self._move_to_secondary_axis_context_handler
        )

        # move to primary axis context action
        self._move_to_primary_axis_action = QAction('Move to primary axis', self)
        self._move_to_primary_axis_action.triggered.connect(self._move_item_to_primary_axis)
        self.add_context_menu_action(
            self._move_to_primary_axis_action,
            position=0,
            group_name='move_curve',
            callback=self._move_to_primary_axis_context_handler
        )

        # remove secondary axis context action - if a curve is clicked
        self._remove_secondary_axis_action = QAction('Remove secondary axis', self)
        self._remove_secondary_axis_action.triggered.connect(self.move_all_from_secondary_axis)
        self.add_context_menu_action(
            self._remove_secondary_axis_action,
            position=1,
            group_name='move_curve',
            callback=lambda x: self.secondary_vb is not None and self.secondary_vb.isVisible()
        )

        # export actions
        self.add_context_menu_group('export', insert_before=[])
        self._copy_menu = QMenu('Copy...', self)
        self._export_menu = QMenu('Export...', self)
        self.add_context_menu_action(self._copy_menu.menuAction(), position=0, group_name='export', callback=lambda x: True)
        self.add_context_menu_action(self._export_menu.menuAction(), position=1, group_name='export', callback=lambda x: True)

        # export / copy actions (copy to memoery and export to vector layer are in the drawtool mixin)
        self.copy_data_action = QAction('Copy data to clipboard...', self)
        self.copy_data_action.triggered.connect(self.copy_plot_data_to_clipboard)
        self._copy_menu.addAction(self.copy_data_action)
        self.export_data_action = QAction('Export data to csv...', self)
        self.export_data_action.triggered.connect(self.export_plot_data_to_csv)
        self._export_menu.addAction(self.export_data_action)
        self.copy_image_action = QAction('Copy image to clipboard', self)
        self.copy_image_action.triggered.connect(self.copy_plot_image_to_clipboard)
        self._copy_menu.addAction(self.copy_image_action)
        self.export_image_action = QAction('Export image to file...', self)
        self.export_image_action.triggered.connect(self.copy_plot_image_to_file)
        self._export_menu.addAction(self.export_image_action)
        self.copy_svg_action = QAction('Copy SVG to clipboard', self)
        self.copy_svg_action.triggered.connect(self.copy_plot_svg_to_clipboard)
        self._copy_menu.addAction(self.copy_svg_action)
        self.export_svg_action = QAction('Export SVG to file...', self)
        self.export_svg_action.triggered.connect(self.copy_plot_svg_to_file)
        self._export_menu.addAction(self.export_svg_action)

    def _teardown_interaction(self: SupportUI):
        # view box hover
        try:
            self.plot_graph.getViewBox().hovered.disconnect(self._on_view_box_hover)
        except Exception:
            pass

        # result name changed
        try:
            self.results_changed.disconnect(self.update_plot)
        except Exception:
            pass

        # data type changed
        try:
            self.data_types_changed.disconnect(self.update_plot)
        except Exception:
            pass

    def _move_to_secondary_axis_context_handler(self, vb: CustomViewBox):
        if not self.selected_curve():
            return False
        show = self.selected_curve().getViewBox().axis_name == 'primary'
        if show:
            self._move_item = self.selected_curve()
        return show

    def _move_to_primary_axis_context_handler(self, vb: CustomViewBox):
        if not self.selected_curve():
            return False
        show = self.selected_curve().getViewBox().axis_name == 'secondary'
        if show:
            self._move_item = self.selected_curve()
        return show

    def clear_plot_all(self: SupportUI):
        self.clear_drawn_items()
        self.clear_feature_selection()
        self.update_plot()

    def _on_view_box_hover(self: SupportUI, ev):
        for item in self.plot_graph.scene().items():
            if hasattr(item, 'data_type'):
                if not item.selected:
                    item.reset_hover()
        self._on_hover(ev.pos(), 'dynamic')

    def _on_view_box_hover_leave(self: SupportUI):
        if self._geom_type == 'line':
            self.update_qgis_cursor_tracking(None)
        for item in self.plot_graph.scene().items():
            if isinstance(item, TuflowViewerCurve):
                item.reset_hover()

    def _on_hover(self: SupportUI, pos, feedback_context: str):
        # position is local viewbox coordinates, not the coordinates displayed in the viewbox
        # pos = self.plot_graph.getViewBox().mapToView(ev.pos())
        # pos = self.secondary_vb.mapToView(ev.pos())
        dist = 9e29
        plot_item = None
        curve_item = None
        zValue = -9e29
        for item in self.plot_graph.items():
            if hasattr(item, 'hover_dist'):
                if item.hover_dist < dist or item.active_channel_curve:
                    if item.hover_dist < dist:
                        dist = item.hover_dist
                        plot_item = item
                    elif item.active_channel_curve and dist > 1e20 and item.zValue() > zValue:
                        plot_item = item
                        zValue = item.zValue()
                if item.is_cursor_over_curve:
                    curve_item = item

        if plot_item is None:
            QToolTip.hideText()
            self.setToolTip('')

        for item in self.plot_graph.items():
            if hasattr(item, 'hover_dist'):
                item.set_hover_visible(item == plot_item)

        if plot_item is None and curve_item:
            plot_item = curve_item  # not snapped to a point, but cursor is over a curve, so still show that in map canvas

        if 'static' in feedback_context:
            self.update_qgis_static_feedback(plot_item.geom if plot_item else None)

        if 'channel feature' in feedback_context:
            feat = self.get_channel_feature(plot_item.src_item.output_id,
                                            plot_item.active_channel_curve.channel_id) if plot_item and plot_item.active_channel_curve else None
            geom = feat.geometry() if feat is not None else None
            if geom is not None:
                geom = Selection.geom_extract(geom)
            self.update_qgis_static_feedback(geom)

        if 'node feature' in feedback_context:
            feat = self.get_node_feature(plot_item.src_item.output_id,
                                            plot_item.active_channel_curve.channel_id) if plot_item and plot_item.active_channel_curve else None
            geom = feat.geometry() if feat is not None else None
            if geom is not None:
                geom = Selection.geom_extract(geom)
            self.update_qgis_static_feedback(geom)

        if 'dynamic' in feedback_context:
            self.update_qgis_cursor_tracking(pos)

        self._active_curve = plot_item

    def selected_curve(self: SupportUI) -> 'PlotCurveItem | None':
        selected = [x for x in self.plot_graph.scene().items() if hasattr(x, 'selected') and x.selected]
        z = -9e29
        active = None
        for sel in selected:
            if sel.zValue() > z:
                z = sel.zValue()
                active = sel
        return active

    def create_secondary_axis(self: SupportUI, axis_pos: str = 'right'):
        first = False
        if self.secondary_vb is None:
            self.secondary_vb = CustomViewBox(enableMenu=True, axisName='secondary')
            self.secondary_vb.setParentItem(self.plot_graph.plotItem)
            self.plot_graph.scene().addItem(self.secondary_vb)
            if axis_pos == 'right':
                self.secondary_vb.setXLink(self.plot_graph)
            else:
                self.secondary_vb.setYLink(self.plot_graph)
            axis = SecondaryAxisItem(axis_pos, axis_name='secondary')
            self.plot_graph.setAxisItems({axis_pos: axis})
            first = True

        if first or not self.secondary_vb.isVisible():
            self.secondary_vb.show()
            self.plot_graph.showAxis(axis_pos)
            self.plot_graph.getAxis(axis_pos).linkToView(self.secondary_vb)
            self.plot_graph.plotItem.vb.sigResized.connect(self.updateViews)
            self.secondary_vb.hovered.connect(self._on_view_box_hover)

    def reset_all_mouse_shapes(self: SupportUI):
        for item in self.plot_graph.items():
            if hasattr(item, '_mouseShape'):
                item._mouseShape = None
        if self.secondary_vb is None:
            return
        for item in self.secondary_vb.scene().items():
            if hasattr(item, '_mouseShape'):
                item._mouseShape = None

    def updateViews(self):
        # override method - this is why camelCase is used here
        if self.secondary_vb:
            self.secondary_vb.setGeometry(self.plot_graph.plotItem.vb.sceneBoundingRect())
            self.secondary_vb.linkedViewChanged(self.plot_graph.plotItem.vb, self.secondary_vb.XAxis)

    def copy_plot_data_to_clipboard(self):
        df = self._export_plot_data()
        if df.empty:
            logger.warning('No plot data to copy to clipboard')
            return
        df.to_clipboard()
        logger.info('Copied data to clipboard', extra={'messagebar': True})

    def export_plot_data_to_csv(self):
        df = self._export_plot_data()
        if df.empty:
            logger.warning('No plot data to export')
            return

        start_dir = QSettings().value('tuflow_viewer/export_data_location')
        loc = QFileDialog.getSaveFileName(
            self.plot_window, 'Export plot data to CSV', start_dir, 'CSV files (*.csv);;All files (*.*)'
        )[0]
        if not loc:
            return
        QSettings().setValue('tuflow_viewer/export_data_location', str(Path(loc).parent))
        df.to_csv(loc)
        logger.info(f'Exported plot data to {loc}', extra={'messagebar': True})

    def _export_plot_data(self) -> pd.DataFrame:
        plot_items = [x for x in self.plot_graph.items() if isinstance(x, TuflowViewerCurve)]
        dfs = []
        for item in reversed(plot_items):
            if not item.isVisible():
                continue
            data = item.export_data()
            if data.size == 0:
                continue
            columns = ['x', 'y', 'value'][:data.shape[1]] if data.shape[1] <= 3 else ['x', 'y', 'value_x', 'value_y']
            df = pd.DataFrame(data, columns=columns)
            label = item.src_item.export_label()
            if isinstance(item, Quiver):
                label = f'{label}/vector'
            df.columns = pd.MultiIndex.from_tuples([(label, col) for col in df.columns])
            dfs.append(df)
        if dfs:
            return pd.concat(dfs, axis=1)
        return pd.DataFrame()

    def copy_plot_image_to_clipboard(self):
        exporter = ImageExporter(item=self.plot_graph.scene())
        exporter.export(copy=True)
        logger.info('Copied plot image to clipboard', extra={'messagebar': True})

    def copy_plot_image_to_file(self):
        filter = ImageExporter.getSupportedImageFormats()
        start_dir = QSettings().value('tuflow_viewer/export_data_location')
        file = QFileDialog.getSaveFileName(
            self.plot_window, 'Export plot data to Image', start_dir, ';;'.join(filter)
        )[0]
        if not file:
            return
        QSettings().setValue('tuflow_viewer/export_data_location', str(Path(file).parent))
        exporter = ImageExporter(item=self.plot_graph.scene())
        exporter.export(fileName=file)
        logger.info(f'Exported plot image to {file}', extra={'messagebar': True})

    def copy_plot_svg_to_clipboard(self):
        exporter = SVGExporter(item=self.plot_graph.scene())
        exporter.export(copy=True)
        logger.info('Copied SVG image to clipboard', extra={'messagebar': True})

    def copy_plot_svg_to_file(self):
        start_dir = QSettings().value('tuflow_viewer/export_data_location')
        file = QFileDialog.getSaveFileName(
            self.plot_window, 'Export plot data to Image', start_dir, 'SVG files (*.svg)'
        )[0]
        if not file:
            return
        QSettings().setValue('tuflow_viewer/export_data_location', str(Path(file).parent))
        exporter = SVGExporter(item=self.plot_graph.scene())
        exporter.export(fileName=file)
        logger.info(f'Exported plot SVG to {file}', extra={'messagebar': True})

    def remove_secondary_axis(self: SupportUI):
        if self.plot_graph.getAxis('right') is not None:
            pos = 'right'
            self.plot_graph.getAxis('right').linkToView(self.plot_graph.plotItem.vb)
        else:
            pos = 'top'
            self.plot_graph.getAxis('top').linkToView(self.plot_graph.plotItem.vb)
        self.secondary_vb.hide()
        self.plot_graph.hideAxis(pos)

    def _update_plot(self, for_adding: list['PlotSourceItem'], for_overwrite: list['PlotSourceItem']):
        """Subclass for specific plotting code."""
        pass

    def update_plot(self: SupportUI):
        comb_have = self.get_current_combinations_on_plot()
        comb_want = self.get_result_combinations_for_plotting(comb_have)
        if not comb_have:
            self.plot_graph.getViewBox().enableAutoRange()
        if self._time_updated and self.PLOT_TYPE != 'Timeseries':
            for_adding = [x for x in comb_want if not x.static]
            for_overwrite = [x for x in comb_have if not x.static]
        else:
            for_adding = [x for x in comb_want if x not in comb_have]
            for_overwrite = [x for x in comb_have if x not in comb_want]
        self._update_plot(for_adding, for_overwrite)
        self._time_updated = False
        self.reset_all_mouse_shapes()

    def move_all_from_secondary_axis(self):
        for item in self.secondary_vb.addedItems.copy():
            if hasattr(item, 'data_type'):
                self._move_item = item
                self._move_item_to_primary_axis()
        else:
            count = len([x for x in self.secondary_vb.addedItems if hasattr(x, 'data_type')])
            if not count:
                self.remove_secondary_axis()

    def _shift_plot_colours_backward(self: SupportUI, colour: str, vb: CustomViewBox) -> bool:
        """Shift all plot colours back one shift place.
        Returns True if there is still room to shift again.
        """
        room_to_shift = False
        orig_shifted = set()
        new_shifted = set()
        i = -1
        for plot_item in self.plot_graph.items():
            if not isinstance(plot_item, TuflowViewerCurve) or plot_item.getViewBox() != vb:
                continue
            base_colour = plot_item.src_item.colour
            if base_colour != colour:
                continue
            i += 1
            if i == 0:
                room_to_shift = True
            shifted_colour = plot_item.opts['pen'].color().name()
            orig_shifted.add(shifted_colour)
            c = self._colours.shift_colour_backward(base_colour, shifted_colour, vb)
            if c == base_colour:
                room_to_shift = False
            new_shifted.add(c)
            plot_item.opts['pen'].setColor(QColor(c))

        left_over = orig_shifted - new_shifted
        for c in left_over:  # should only be one or none
            self._colours.release_shifted(colour, c, vb)
        return room_to_shift

    def _set_move_item_colour(self: SupportUI, plot_item: HoverableCurveItem, src_vb: CustomViewBox, dst_vb: CustomViewBox):
        """Set the shifted colour of the plot item depending on the destination viewbox and release the
         colour in the source viewbox.

         If the shifted colour is the same as the base colour, then shift all other items with the same base colour
         back until one reaches the base colour.
         """
        if plot_item is None:
            return
        base_colour = plot_item.src_item.colour
        shifted_colour = plot_item.opts['pen'].color().name()
        self._colours.release_shifted(base_colour, shifted_colour, src_vb)
        if base_colour == shifted_colour:
            while self._shift_plot_colours_backward(base_colour, src_vb):
                pass
        c = self._colours.shift_colour(base_colour, dst_vb)
        plot_item.opts['pen'].setColor(QColor(c))

    def _move_item_to_secondary_axis(self: SupportUI):
        if self._move_item is None:
            return
        self.create_secondary_axis()
        self.plot_graph.removeItem(self._move_item)
        if isinstance(self._move_item, HoverableCurveItem):
            self._set_move_item_colour(self._move_item, self.plot_graph.getViewBox(), self.secondary_vb)
        self.secondary_vb.addItem(self._move_item)
        if self._move_item.opts.get('pen') is not None:
            pen = self._move_item.opts['pen']
            pen.setStyle(QT_DASH_LINE)
            self._move_item.setPen(pen)
        self.reset_all_mouse_shapes()
        self._move_item = None

    def _move_item_to_primary_axis(self: SupportUI):
        if self._move_item is None:
            return
        self.secondary_vb.removeItem(self._move_item)
        if isinstance(self._move_item, HoverableCurveItem):
            self._set_move_item_colour(self._move_item, self.secondary_vb, self.plot_graph.getViewBox())
        self.plot_graph.addItem(self._move_item)
        if self._move_item.opts.get('pen') is not None:
            pen = self._move_item.opts['pen']
            pen.setStyle(QT_SOLID_LINE)
            self._move_item.setPen(pen)
        self.reset_all_mouse_shapes()
        count = len([x for x in self.secondary_vb.addedItems if hasattr(x, 'data_type')])
        if not count:
            self.remove_secondary_axis()
        self._move_item = None

    def _current_plot_output(self: SupportUI):
        output = None
        for item in self.plot_graph.items():
            if isinstance(item, TuflowViewerCurve):
                output = get_viewer_instance().output(item.output_id)
                break
        if output is None:
            for result_name in self.toolbar.selected_result_names():
                for output in get_viewer_instance().outputs(result_name):
                    break
        if output is None:
            for output in get_viewer_instance().outputs():
                break
        return output
