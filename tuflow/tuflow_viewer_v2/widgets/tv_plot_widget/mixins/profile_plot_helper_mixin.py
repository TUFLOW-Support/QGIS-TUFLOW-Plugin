import typing
from datetime import datetime

import numpy as np
try:
    import pandas as pd
except ImportError:
    from .....pt.pytuflow._outputs.pymesh.stubs import pandas as pd

from .plot_helper_mixin import PlotHelperMixin
from ..plotsourceitem import PlotSourceItem
from ....tvdeveloper_tools import Profiler

import logging
logger = logging.getLogger('tuflow_viewer')


class ProfilePlotHelperMixin(PlotHelperMixin):

    def _populate_plot_data(self,
                            src_item: PlotSourceItem,
                            time: datetime,
                            interpolation_method: str,
                            *args, **kwargs) -> typing.Generator[PlotSourceItem, None, None]:
        output = src_item.output
        data_type, _ = self._split_depth_averaging(src_item.data_type)
        if data_type not in output.data_types('section'):
            return

        src_item.data_type = data_type
        location = src_item.geom if src_item.output.LAYER_TYPE == 'Surface' else src_item.loc

        src_item.feedback_context = 'static'
        src_item.xaxis_name = data_type
        src_item.yaxis_name = 'elevation'
        src_item.units = self._units(data_type)
        src_item.ready_for_plotting = True
        src_item.tooltip = self.tooltip
        src_item.label = self._label(data_type)

        profiler = Profiler()
        profiler('pytuflow::profile()')
        try:
            df = output.profile(location, data_type, time, interpolation='stepped')  # always stepped so we can get the level boundaries
        except (ValueError, IndexError) as e:
            logger.info(f'pytuflow failed to plot profile: {e}')
            return
        finally:
            profiler('pytuflow::profile()')

        if not df.empty:
            src_item.level_boundaries = df.iloc[:, 0].dropna().unique().tolist()

        # change to linear interpolation if selected
        if not df.empty and interpolation_method == 'linear' and df.shape[0] > 2:
            df.columns = ['elevation', data_type]
            df.set_index('elevation', inplace=True)
            df.sort_index(inplace=True)
            df1 = pd.DataFrame()
            df1['elevation'] = src_item.level_boundaries
            df1[data_type] = np.interp(
                df1['elevation'],
                df.index,
                df[data_type],
            )
            df = df1

        for xdata, ydata, extra in output.profile_plot(df, data_type, src_item):
            src_item = extra['src_item'] if 'src_item' in extra else src_item
            src_item.xdata = xdata
            src_item.ydata = ydata
            src_item.ready_for_plotting = True
            yield src_item
