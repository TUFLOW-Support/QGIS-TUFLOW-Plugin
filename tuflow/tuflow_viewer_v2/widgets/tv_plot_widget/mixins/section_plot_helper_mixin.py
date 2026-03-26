import typing
from copy import deepcopy
from datetime import datetime

from qgis.PyQt.QtCore import QSettings
from qgis.core import Qgis, QgsProject, QgsDistanceArea, QgsCoordinateTransformContext

from ....tvdeveloper_tools import Profiler
from ..plotsourceitem import PlotSourceItem
from .plot_helper_mixin import PlotHelperMixin

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pt.pytuflow import misc
else:
    from tuflow.pt.pytuflow import misc

import logging
logger = logging.getLogger('tuflow_viewer')


class SectionPlotHelperMixin(PlotHelperMixin):

    def _populate_plot_data(self, src_item: PlotSourceItem, time: datetime, *args, **kwargs) -> typing.Generator[PlotSourceItem, None, None]:
        """Populate source item with section plot data from this output."""
        output = src_item.output
        data_type, avg_method = self._split_depth_averaging(src_item.data_type)
        if data_type not in output.data_types('section'):
            return

        src_item.averaging_method = avg_method
        src_item.data_type = data_type
        src_item.is_pits = data_type == 'pits'
        src_item.is_pipes = data_type == 'pipes'
        if src_item.is_pipes:
            data_type = ['bed level', 'pipes']
        location = src_item.geom if output.LAYER_TYPE == 'Surface' else src_item.loc

        src_item.tooltip = self.tooltip
        if src_item.is_pits:
            src_item.feedback_context = 'node feature'
        elif misc.list_depth(src_item.geom) == 1:  # point - e.g. na table
            src_item.feedback_context = 'static'
        else:
            src_item.feedback_context = 'dynamic channel feature'
        src_item.xaxis_name = 'offset'
        src_item.yaxis_name = data_type if not src_item.is_pipes else 'pipes'
        self.xaxis_units = ''
        src_item.label = self._label(data_type)
        src_item.units = self._units(data_type)
        src_item.ready_for_plotting = True

        profiler = Profiler()
        profiler('Section - pytuflow::section()')
        try:
            df = output.section(location, data_type, time, averaging_method=avg_method)
        except (ValueError, IndexError) as e:
            logger.info(f'pytuflow failed to plot section: {e}')
            return
        finally:
            profiler('Section - pytuflow::section()')

        src_item.branch_count = df['branch_id'].max() + 1 if 'branch_id' in df.columns else 1
        i = -1
        for xdata, ydata, extra in output.section_plot(df, data_type, src_item):
            src_item1 = extra['src_item'] if 'src_item' in extra else deepcopy(src_item)
            i += 1
            src_item1.branch = i
            src_item1.xdata = xdata
            src_item1.ydata = ydata
            src_item1.channel_ids = extra.get('channel_ids', [])
            src_item1.node_ids = extra.get('node_ids', [])
            if src_item1.channel_ids:
                src_item1.loc = [src_item1.channel_ids[0], src_item1.channel_ids[-1]]
            yield src_item1
