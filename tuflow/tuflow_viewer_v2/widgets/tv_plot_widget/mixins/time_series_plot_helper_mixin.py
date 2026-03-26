import typing

import numpy as np

from qgis.PyQt.QtCore import QFile

from .plot_helper_mixin import PlotHelperMixin
from ..plotsourceitem import PlotSourceItem
from ....tvdeveloper_tools import Profiler

import tuflow.resources.tuflow

import logging
logger = logging.getLogger('tuflow_viewer')


class TimeSeriesPlotHelperMixin(PlotHelperMixin):

    @staticmethod
    def flow_regime_tooltip(src_item: PlotSourceItem, parent_src_item: PlotSourceItem, position: tuple[float, float], flow_regime: str, *args, **kwargs) -> str:
        if parent_src_item:
            string = PlotHelperMixin.tooltip(parent_src_item, '', position, *args, **kwargs)
            string = f'{string}\n{src_item.data_type_pretty(src_item.yaxis_name)}: {flow_regime}'
        else:
            position = (position[0], flow_regime) if position else position
            string = PlotHelperMixin.tooltip(src_item, '', position , *args, **kwargs)
        if (src_item.data_type == 'channel flow regime' and
                (src_item.chan_type.startswith('C') or src_item.chan_type.startswith('R')) and
                QFile(f':/tuflow-plugin/tuflow_viewer_v2/flow_regime/culvert_flow_regime_{flow_regime.upper()}.png').exists()):
            string += f'\n<img src=":/tuflow-plugin/tuflow_viewer_v2/flow_regime/culvert_flow_regime_{flow_regime.upper()}.png" width="200">'
            string = string.replace('\n', '<br>')
        return string

    def _populate_plot_data(self, src_item: PlotSourceItem, time_fmt: str, *args, **kwargs) -> typing.Generator[PlotSourceItem, None, None]:
        output = src_item.output
        data_type, avg_method = self._split_depth_averaging(src_item.data_type)
        if data_type not in output.data_types('timeseries'):
            return

        src_item.is_flow_regime = 'flow regime' in data_type

        src_item.averaging_method = avg_method
        src_item.data_type = data_type
        if src_item.output.LAYER_TYPE == 'Surface':
            location = src_item.geom
        else:
            location = f'{src_item.loc}/{src_item.domain}'


        src_item.feedback_context = 'static'
        src_item.xaxis_name = 'time'
        src_item.yaxis_name = data_type
        src_item.units = self._units(data_type)
        src_item.ready_for_plotting = True
        src_item.tooltip = self.tooltip if not src_item.is_flow_regime else self.flow_regime_tooltip
        src_item.label = self._label(data_type)

        profiler = Profiler()
        profiler('pytuflow::time_series()')
        try:
            df = output.time_series(location, data_type, time_fmt=time_fmt, averaging_method=avg_method)
        except (ValueError, IndexError) as e:
            logger.info(f'pytuflow failed to plot time series: {e}')
            return
        finally:
            profiler('pytuflow::time_series()')

        for xdata, ydata, extra in output.time_series_plot(df, data_type, src_item):
            src_item = extra['src_item'] if 'src_item' in extra else src_item
            src_item.xdata = np.array([x.timestamp() for x in xdata]) if time_fmt == 'absolute' else xdata
            src_item.ydata = ydata
            src_item.ready_for_plotting = True
            yield src_item
