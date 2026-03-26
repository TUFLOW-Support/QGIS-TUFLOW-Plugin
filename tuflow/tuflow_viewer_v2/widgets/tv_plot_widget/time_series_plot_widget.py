import numpy as np
try:
    import pandas as pd
except ImportError:
    from ....pt.pytuflow._outputs.pymesh.stubs import pandas as pd
from datetime import datetime, timezone, timedelta

from qgis.PyQt.QtCore import QSettings

from .pyqtgraph_subclass.hoverable_curve_item import HoverableCurveItem
from .pyqtgraph_subclass.tuflow_viewer_curve import TuflowViewerCurve
from .pyqtgraph_subclass.text_curve_item import TextCurveItem

from .base_plot_widget import TVPlotWidget
from .mixins.time_series_plot_helper_mixin import TimeSeriesPlotHelperMixin
from .plotsourceitem import PlotSourceItem
from ...tvinstance import get_viewer_instance
from ...tvdeveloper_tools import Profiler


from ...temporal_controller_widget import temporal_controller

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ....pyqtgraph import mkPen, PlotCurveItem, InfiniteLine, DateAxisItem, AxisItem, ViewBox, mkBrush
    from ....compatibility_routines import is_qt6
else:
    from tuflow.pyqtgraph import mkPen, PlotCurveItem, InfiniteLine, DateAxisItem, AxisItem, ViewBox, mkBrush
    from tuflow.compatibility_routines import is_qt6

if is_qt6:
    from qgis.PyQt.QtGui import QAction
else:
    from qgis.PyQt.QtWidgets import QAction

import logging
logger = logging.getLogger('tuflow_viewer')


class TimeSeriesPlotWidget(TVPlotWidget, TimeSeriesPlotHelperMixin):
    PLOT_TYPE = 'Timeseries'

    def __init__(self, parent=None):
        self._geom_type = 'marker'
        super(TimeSeriesPlotWidget, self).__init__(parent)
        self._init_plot_helper()

        # context menu
        self.add_context_menu_group(group_name='time_series', insert_before=['Plot Options'])

        # current time
        self._show_current_time = QAction('Show current time', self)
        self._show_current_time.setCheckable(True)
        self._show_current_time.toggled.connect(self._update_display_time)
        self.add_context_menu_action(
            self._show_current_time,
            position=0,
            group_name='time_series',
            callback=lambda x: True
        )

        # use datetime
        self.as_datetime = QAction('Use datetime', self)
        self.as_datetime.setCheckable(True)
        self.as_datetime.toggled.connect(self._datetime_toggled)
        self.add_context_menu_action(
            self.as_datetime,
            position=1,
            group_name='time_series',
            callback=lambda x: True
        )

        self._cur_time_item = None
        self._time_being_dragged = False

    def close(self):
        super().close()
        self._teardown_plot_helper()

    def plot_data_types(self, output_names: list[str]) -> list[str]:
        return get_viewer_instance().data_types(output_names, 'timeseries')

    def plot_data_types_3d(self, output_names: list[str]) -> list[str]:
        return get_viewer_instance().data_types(output_names, 'timeseries/3d')

    def qgis_time_changed(self):
        super().qgis_time_changed()
        if hasattr(self, '_show_current_time'):  # may only be partially loaded
            self._update_display_time(self._show_current_time.isChecked())

    def plot_flow_regime(self, src_item: 'PlotSourceItem') -> TextCurveItem:
        parent_curve = None
        existing_curve = None
        for curve in self.plot_graph.items():
            if not isinstance(curve, TuflowViewerCurve):
                continue
            if curve.src_item.id == src_item.id:
                existing_curve = curve
        parent_src_item = existing_curve.parent_src_item if existing_curve else None
        for curve in self.plot_graph.items():
            if not isinstance(curve, TuflowViewerCurve):
                continue
            if curve.src_item.output_id != src_item.output_id:
                continue
            if parent_src_item == curve.src_item:
                parent_curve = curve
                break
            if src_item.data_type == 'channel flow regime' and curve.src_item.data_type == 'flow':
                parent_curve = curve
            elif src_item.data_type == 'channel flow regime' and curve.src_item.data_type == 'velocity' and parent_curve is None:
                parent_curve = curve
            elif src_item.data_type == 'node flow regime' and curve.src_item.data_type == 'water level':
                parent_curve = curve

        if existing_curve:
            existing_curve.set_parent_src_item(parent_curve.src_item if parent_curve else None)
            return existing_curve

        if parent_curve:
            ydata = parent_curve.yData
        else:
            ydata = np.zeros((len(src_item.xdata),), dtype='f8')

        # remove nan and any additional flags
        letters = pd.Series(src_item.ydata)
        letters[(letters.astype(str) == 'nan') | (letters.astype(str) == '')] = ' '
        letters = letters.str[0]

        c = (120, 120, 120)
        plot_item = TextCurveItem(
            x=src_item.xdata,
            y=ydata,
            letters=letters.to_numpy(),
            name=src_item.label,
            pen=mkPen((0, 0, 0), width=0.5),
            brush=mkBrush(c),
            src_item=src_item,
            size=10,
            parent_curve=parent_curve,
        )
        plot_item.setZValue(1000)
        self.plot_graph.addItem(plot_item)
        plot_item.sigHoverEvent.connect(self._on_hover)
        return plot_item

    def update_flow_regime_curve(self, new_regime_curve: list[TextCurveItem]):
        for curve in self.plot_graph.items():
            if curve in new_regime_curve or not isinstance(curve, TuflowViewerCurve):
                continue
            if 'flow regime' in curve.src_item.data_type:
                self.plot_flow_regime(curve.src_item)

    def _update_plot(self, for_adding: list['PlotSourceItem'], for_overwrite: list['PlotSourceItem']):
        profiler = Profiler()
        profiler('Time Series Plot Total Time')

        # re-order so that flow regime data types are at the end
        key = {x: i + 1000 if 'flow regime' in x.data_type else i for i, x in enumerate(for_adding)}
        for_adding = sorted(for_adding, key=lambda x: key[x])
        new_regime_curves = []

        time_fmt = 'absolute' if self.as_datetime.isChecked() else 'relative'
        for src_item in for_adding:
            for src_item_filled in self._populate_plot_data(src_item, time_fmt):

                if src_item_filled.is_flow_regime:
                    profiler('Time Series - Plot Flow Regime')
                    plot_item = self.plot_flow_regime(src_item_filled)
                    new_regime_curves.append(plot_item)
                    profiler('Time Series - Plot Flow Regime')
                    continue

                if for_overwrite:
                    profiler('Time Series - Overwrite Plot Item')
                    item_for_overwrite = for_overwrite.pop(0)
                    plot_item = self.item_2_curve(item_for_overwrite, self.plot_graph)
                    plot_item.setData(x=src_item_filled.xdata, y=src_item_filled.ydata, name=src_item_filled.label)
                    src_item_filled.colour = item_for_overwrite.colour
                    plot_item.src_item = src_item_filled
                    profiler('Time Series - Overwrite Plot Item')
                else:
                    profiler('Time Series - Add New Plot Item')
                    c = src_item_filled.colour if src_item_filled.colour else self.next_colour(src_item_filled.sel_type)
                    src_item_filled.colour = c
                    c = self._colours.shift_colour(c, self.plot_graph.getViewBox())  # shift colour if it is already in use on the same plot
                    plot_item = HoverableCurveItem(
                        x=src_item_filled.xdata,
                        y=src_item_filled.ydata,
                        name=src_item_filled.label,
                        pen=mkPen(c, width=2),
                        src_item=src_item_filled,
                        connect='finite',
                    )
                    self.plot_graph.addItem(plot_item)
                    plot_item.sigHoverEvent.connect(self._on_hover)
                    profiler('Time Series - Add New Plot Item')

        self.remove_items_from_plot(for_overwrite)

        self.update_flow_regime_curve(new_regime_curves)

        profiler('Time Series Plot Total Time')
        profiler.report()

    def _current_plot_time(self) -> datetime | float | None:
        dt = self.qgis_current_time()
        if dt is None:
            return None
        if self.as_datetime.isChecked():
            return dt.timestamp()
        output = self._current_plot_output()
        if output is None:
            return None
        return (dt - output.reference_time).total_seconds() / 3600.

    def _get_cur_time_item(self) -> InfiniteLine:
        cur_time = self._current_plot_time()
        if self._cur_time_item is None:
            for item in self.plot_graph.items():
                if isinstance(item, InfiniteLine):
                    self._cur_time_item = item
                    break
            if self._cur_time_item is None:
                self._cur_time_item = InfiniteLine(cur_time, pen=mkPen('r', width=2), movable=True, hoverPen=mkPen('y', width=3))
                self.plot_graph.addItem(self._cur_time_item)
                self._cur_time_item.sigDragged.connect(self._on_cur_time_dragged)
                self._cur_time_item.sigPositionChangeFinished.connect(self._on_cur_time_dragged_finished)
        return self._cur_time_item

    def _update_display_time(self, checked: bool):
        if self._time_being_dragged:
            return
        cur_time = self._current_plot_time()
        if cur_time is None:
            return
        self._cur_time_item = self._get_cur_time_item()
        if self._cur_time_item is not None:
            self._cur_time_item.setValue(cur_time)
            self._cur_time_item.setVisible(checked)

    def _on_cur_time_dragged(self):
        if not self._time_being_dragged:
            self._time_being_dragged = True
            cur_time_item = self._get_cur_time_item()
            cur_time_item.setPen(mkPen('y', width=3))
        self._update_qgis_time()

    def _on_cur_time_dragged_finished(self):
        cur_time_item = self._get_cur_time_item()
        cur_time_item.setPen(mkPen('r', width=2))
        self._update_qgis_time()
        self._time_being_dragged = False
        self._update_display_time(True)

    def _update_qgis_time(self):
        self._cur_time_item = self._get_cur_time_item()
        if self._cur_time_item is None:
            return
        cur_time = self._cur_time_item.value()
        if self.as_datetime.isChecked():
            cur_time = datetime.fromtimestamp(self._cur_time_item.value(), tz=timezone.utc)
        else:
            output = self._current_plot_output()
            if not output:
                return
            try:
                cur_time = output.reference_time + pd.Timedelta(hours=cur_time)
            except Exception:
                pass
        temporal_controller.setCurrentTime(cur_time)

    def _datetime_toggled(self, checked: bool):
        # update x axis
        if checked:
            axis = DateAxisItem(utcOffset=0, pen=self.plot_graph.getAxis('bottom').pen())
        else:
            axis = AxisItem(orientation='bottom', pen=self.plot_graph.getAxis('bottom').pen())
        self.plot_graph.setAxisItems({'bottom': axis})
        self.plot_graph.plotItem.updateGrid()

        for item in self.plot_graph.items():
            if not isinstance(item, TuflowViewerCurve):
                continue
            xdata = item.xData
            if not xdata.size:
                continue
            output = self.tv.output(item.output_id)
            if not output:
                continue
            if checked:
                xdata = [(output.reference_time + timedelta(hours=float(x))).timestamp() for x in xdata]
            else:
                xdata = [(datetime.fromtimestamp(x, tz=timezone.utc) - output.reference_time).total_seconds() / 3600. for x in xdata]
            item.src_item.xdata = xdata
            item.setData(x=xdata, y=item.yData, is_datetime=checked)

        # update the current time item
        self._update_display_time(self._show_current_time.isChecked())

        # update view
        self.plot_graph.getViewBox().autoRange()
        if self.secondary_vb and self.secondary_vb.isVisible():
            self.secondary_vb.autoRange()

        # loop through other linked views
        if self.plot_linker.active:
            for w in self.plot_window.find_plot_widgets(self):
                if w is self:
                    continue
                if w.plot_linker.active:
                    w.as_datetime.setChecked(checked)
