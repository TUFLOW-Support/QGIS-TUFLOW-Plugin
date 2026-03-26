import typing

import numpy as np
try:
    import pandas as pd
except ImportError:
    from ...pt.pytuflow._outputs.pymesh.stubs import pandas as pd

from qgis.core import QgsMapLayer, QgsMeshDatasetIndex, QgsMeshLayer, QgsMeshRendererSettings, Qgis, QgsRectangle
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtXml import QDomDocument

from .tvoutput import TuflowViewerOutput

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from ...pt.pytuflow import Output
    from ...tuflow_plugin_cache import get_cached_content
else:
    from tuflow.pt.pytuflow import Output
    from tuflow.tuflow_plugin_cache import get_cached_content

if typing.TYPE_CHECKING:
    from ..widgets.tv_plot_widget.plotsourceitem import PlotSourceItem

import logging
logger = logging.getLogger('tuflow_viewer')


class MapOutputMixin(TuflowViewerOutput):

    def _init_viewer_output_mixin(self, output_name: str):
        super()._init_viewer_output_mixin(output_name)
        self._style_changed_signals = {}
        self._block_style_changed_signal = False

    def _teardown_viewer_output_mixin(self):
        super()._teardown_viewer_output_mixin()
        for lyr, sig in self._style_changed_signals.items():
            try:
                lyr.styleChanged.disconnect(sig)
            except Exception:
                pass

    def maximum(self, data_type: str) -> float:
        return self._driver.maximum(data_type)

    def minimum(self, data_type: str) -> float:
        return self._driver.minimum(data_type)

    def section_plot(self,
                     df: pd.DataFrame,
                     data_type: str | list[str],
                     src_item: 'PlotSourceItem',
                     ) -> typing.Generator[tuple[np.ndarray, np.ndarray, dict[str, typing.Any]], None, None]:
        if df.empty:
            return
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [x[-1] for x in df.columns.to_flat_index()]
        df.columns = df.columns.str.split('/').str[0].str.strip()
        xdata = df.loc[:, 'offset'].to_numpy()
        ydata = df.loc[:, data_type].to_numpy()
        yield xdata, ydata, {}

    def _init_styling(self, map_layers: list[QgsMapLayer], lyr2resultstyle: dict):
        """Initialise styling for the layer."""
        super()._init_styling(map_layers, lyr2resultstyle)

    def qgis_styling_hook(self, layers: list[QgsMapLayer]):
        pass

    def styling_xml(self, type_: str, group_index: int | str = 'active') -> str:
        raise NotImplementedError

    def load_styling_xml(self, xml: str, type_: str, group_index: int | str = 'active'):
        pass

