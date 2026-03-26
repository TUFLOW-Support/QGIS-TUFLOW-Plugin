import typing
from datetime import datetime, timezone

try:
    import pandas as pd
except ImportError:
    from .....pt.pytuflow._outputs.pymesh.stubs import pandas as pd

from ..plotsourceitem import PlotSourceItem
from ....fmts import TuflowViewerOutput


class PlotHelperMixin:

    def _init_plot_helper(self):
        pass

    def _teardown_plot_helper(self):
        pass

    @staticmethod
    def _split_depth_averaging(data_type: str) -> tuple[str, str | None]:
        """Split depth averaging from data type if present."""
        avg_method = None
        if ':' in data_type:
            data_type, _, avg_method = data_type.split(':', 2)
        return data_type, avg_method

    def _label(self, data_type: str | list[str]):
        return data_type if isinstance(data_type, str) else data_type[-1]

    def _units(self, data_type: str | list[str]) -> str:
        return ''

    @staticmethod
    def tooltip(src_item: PlotSourceItem, location_id: str, position: tuple[float, float], *args, **kwargs) -> str:
        """Generate tooltip for section plot."""
        string = src_item.output.name
        if location_id:
            string = f'{string}\n{location_id}'
        elif src_item.use_label_in_tooltip:
            string = f'{string}\n{src_item.label}'
        if position:
            if isinstance(position[0], float) and kwargs.get('is_datetime', False):
                dt = datetime.fromtimestamp(position[0], tz=timezone.utc)
                pos0 = '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S}'.format(dt)
            else:
                pos0 = f'{position[0]:.3g}'
            pos1 = f'{position[1]:.3g}' if isinstance(position[1], float) else position[1]
            string = f'{string}\n{src_item.data_type_pretty(src_item.xaxis_name)}: {pos0}'
            if src_item.xaxis_units:
                string = f'{string} {src_item.xaxis_units}'
            string = f'{string}\n{src_item.data_type_pretty(src_item.yaxis_name)}: {pos1}'
            if src_item.units:
                string = f'{string} {src_item.units}'
        else:
            string = f'{string}\n{src_item.data_type_pretty(src_item.yaxis_name)}'
        return string

    def _populate_plot_data(self, src_item: PlotSourceItem, *args, **kwargs) -> typing.Generator[PlotSourceItem, None, None]:
        pass