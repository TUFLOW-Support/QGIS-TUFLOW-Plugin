import json
import typing
from datetime import timedelta, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
try:
    import pandas as pd
except ImportError:
    from ...pt.pytuflow._outputs.pymesh.stubs import pandas as pd
from qgis.core import QgsMapLayer, QgsProject
from qgis.PyQt.QtCore import QDateTime, QTimer
from qgis.PyQt.QtWidgets import QDockWidget, QToolButton, QDoubleSpinBox, QComboBox, QDateTimeEdit

if typing.TYPE_CHECKING:
    from ..widgets.tv_plot_widget.plotsourceitem import PlotSourceItem


import logging
logger = logging.getLogger('tuflow_viewer')


class TuflowViewerOutput:
    """Base class / mixin for Tuflow Viewer outputs that can be added to the QGIS map canvas.
    Class should be mixed in with pytuflow output classes.
    """

    DRIVER_NAME = ''
    LAYER_TYPE = ''
    AUTO_LOAD_METHOD = 'DragDrop'

    def _init_viewer_output_mixin(self, output_name: str):
        self.start_time = None
        self.end_time = None
        self.timestep = None
        self.id = self.generate_id(output_name)
        self.duplicated_outputs = []
        self.copied_files = {}
        self._map_layer_ids = []
        self._map_layers = []
        self._lyr2output = {}
        self._lyr2resultstyle = {}

    def _teardown_viewer_output_mixin(self):
        pass

    def generate_id(self, output_name: str) -> str:
        self.id = f'{output_name}_{uuid4()}'
        return self.id

    @staticmethod
    def format_compatible(fpath: Path | str) -> bool:
        """Returns True if the file is of this format.
        This is used to determine if the handler is suitable for the file.
        """
        return False

    def to_json(self) -> str:
        """Serialize the object to a JSON string.
        Used for saving/loading sessions.
        """
        d = {
            'class': self.__class__.__name__,
            'id': self.id,
            'fpath': str(self.fpath),
            'name': self.name,
            'lyrids': [x.id() for x in self.map_layers()],
            'duplicated': [lyr.id() for x in self.duplicated_outputs for lyr in x.map_layers()],
            'copied_files': {str(k): (str(v[0]), v[1]) for k, v in self.copied_files.items()},
        }
        return json.dumps(d)

    @staticmethod
    def from_json(string) -> 'TuflowViewerOutput | None':
        """Deserialize the object from a JSON string.
        Used for saving/loading sessions.
        """
        d = json.loads(string)
        lyrids = d['lyrids']
        lyrs = [QgsProject.instance().mapLayer(x) for x in lyrids if QgsProject.instance().mapLayer(x)]
        if not lyrs:
            return
        for lyr in lyrs:
            if not lyr.isValid():
                logger.error('Vector layer for {class} output not found in project: {name}'.format(**d))
                raise ValueError('Vector layer for {class} output not found in project: {name}'.format(**d))
        exec('from . import {0}'.format(d['class']))
        res = eval('{class}(r"{fpath}", layers=lyrs)'.format(**d))
        res.id = d['id']
        res.duplicated_outputs = [QgsProject.instance().mapLayer(x) for x in d['duplicated'] if QgsProject.instance().mapLayer(x)]
        res.copied_files = d.get('copied_files', {})
        return res

    def map_layers(self) -> list[QgsMapLayer]:
        """Returns a list of QgsMapLayer objects that can be added to the QGIS map canvas."""
        if not self._map_layer_ids:
            self._map_layer_ids = [lyr.id() for lyr in self._map_layers]
        return self._map_layers

    def map_layer_ids(self) -> list[str]:
        return self._map_layer_ids

    def time_series_plot(self,
                         df: pd.DataFrame,
                         data_type: str | list[str],
                         src_item: 'PlotSourceItem',
                         ) -> typing.Generator[tuple[np.ndarray, np.ndarray, dict[str, typing.Any]], None, None]:
        if df.empty:
            return
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [x[-1] for x in df.columns.to_flat_index()]
        df.columns = df.columns.str.split('/').str[1].str.strip()
        xdata = df.index.to_numpy()
        ydata = df.loc[:, data_type].to_numpy()
        yield xdata, ydata, {}

    def section_plot(self,
                     df: pd.DataFrame,
                     data_type: str | list[str],
                     src_item: 'PlotSourceItem',
                     ) -> typing.Generator[tuple[np.ndarray, np.ndarray, dict[str, typing.Any]], None, None]:
        pass

    def profile_plot(self,
                     df: pd.DataFrame,
                     data_type: str | list[str],
                     src_item: 'PlotSourceItem',
                     ) -> typing.Generator[tuple[np.ndarray, np.ndarray, dict[str, typing.Any]], None, None]:
        if df.empty:
            return
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [x[-1] for x in df.columns.to_flat_index()]
        xdata = df.loc[:, data_type].to_numpy()
        ydata = df.iloc[:,0].to_numpy()
        yield xdata, ydata, {}

    def curtain_plot(self,
                     df: pd.DataFrame,
                     data_type: str | list[str],
                     src_item: 'PlotSourceItem',
                     ) -> typing.Generator[tuple[np.ndarray, np.ndarray, dict[str, typing.Any]], None, None]:
        if df.empty:
            return
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [x[-1] for x in df.columns.to_flat_index()]
        extra = {}
        xdata = df[['x', 'y']].to_numpy('f4').reshape((-1, 4, 2))
        if df[data_type].dtype != float:
            df = df.join(pd.DataFrame(df[data_type].tolist(), columns=[f'{data_type}_x', f'{data_type}_y']))
            ydata = (df[f'{data_type}_x'] ** 2 + df[f'{data_type}_y'] ** 2) ** 0.5
            ydata = ydata.to_numpy().flatten()[::4]

            vector_val = np.vstack(df[f'{data_type}_local'].to_numpy())[::4]
            vector_pos_x = xdata[:,:,0].mean(axis=1)
            vector_pos_y = xdata[:,:,1].mean(axis=1)
            extra['vector'] = pd.DataFrame({
                'x': vector_pos_x,
                'y': vector_pos_y,
                'vector_x': vector_val[:,1],
                'vector_y': np.zeros((vector_val.shape[0],)),
            })
        else:
            ydata = df[[data_type]].to_numpy().flatten()[::4]

        if data_type == 'vertical velocity':
            extra['vertical vector'] = df['vertical velocity'].to_numpy().flatten()[::4]

        yield xdata, ydata, extra

    def set_reference_time(self, reference_time: datetime):
        pass

    def init_temporal_properties(self):
        """Initialise temporal properties for the layer."""
        times = self.times(fmt='absolute')
        if not times:
            return
        diff = np.diff(times)
        self.timestep = diff[diff != timedelta(seconds=0)].min().total_seconds()
        self.start_time = times[0] if times else None
        self.end_time = times[-1] if times else None
        # if self.end_time:
        #     self.end_time += timedelta(seconds=self.timestep)

    def _set_custom_property(self, *args, **kwargs):
        for lyr in self.map_layers():
            if not lyr.customProperty('tuflow_viewer'):
                continue
            lyr.blockSignals(True)
            lyr.setCustomProperty('tuflow_viewer', self.to_json())
            lyr.blockSignals(False)
        QTimer.singleShot(100, lambda: self.set_reference_time(self.reference_time))

    def _init_styling(self, map_layers: list[QgsMapLayer], lyr2resultstyle: dict):
        for lyr in map_layers:
            custom_property = lyr.customProperty('tuflow_viewer')
            if custom_property:
                continue
            lyr.customPropertyChanged.connect(self._set_custom_property)
