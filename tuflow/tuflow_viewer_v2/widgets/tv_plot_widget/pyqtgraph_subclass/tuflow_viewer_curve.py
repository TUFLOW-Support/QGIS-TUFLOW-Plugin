import typing

import numpy as np
from qgis.PyQt.QtCore import QRect, QSettings
from qgis.PyQt.QtWidgets import QToolTip

from ....tvinstance import get_viewer_instance
from ..plotsourceitem import PlotSourceItem

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pyqtgraph import mkPen
    from .....compatibility_routines import QT_RIGHT_BUTTON
else:
    from tuflow.pyqtgraph import mkPen
    from tuflow.compatibility_routines import QT_RIGHT_BUTTON

if typing.TYPE_CHECKING:
    from ...tv_plot_widget.base_plot_widget import TVPlotWidget
    from .....pyqtgraph import ViewBox


class TuflowViewerCurve:

    def __init__(self, *args, **kwargs):
        self._src_item = None
        self.opts = {}
        self.hover_colour = None
        self.sel_type = ''
        self.plot_type = ''
        self.result_name = ''
        self.output_id = ''
        self.data_type = ''
        self.data_type_pretty = ''
        self.loc = ''
        self.geom = ''
        self.is_geometry = False
        self.selected = False
        self.is_cursor_over_curve = False
        self.hover_dist = 9e29
        self.hover_text = ''
        self.hover_pos = None  # global position
        self.hover_local_pos = None  # local position in the viewBox (not the data coordinates)
        self.suppress_tooltip = False
        self.active_channel_curve = None
        self.units = 'm'
        self.range = (0, 0)
        super().__init__(*args, **kwargs)

    def __repr__(self):
        loc = self.geom if self.is_geometry else self.loc
        return f'{self.__class__.__name__} (result={self.result_name}, data_type={self.data_type}, loc={loc})'

    @property
    def src_item(self) -> 'PlotSourceItem':
        return self._src_item

    @src_item.setter
    def src_item(self, src_item: 'PlotSourceItem'):
        self._src_item = src_item
        if src_item is None:
            return
        if src_item.output is not None:
            self.result_name = src_item.output.name
        self.output_id = src_item.output_id
        self.data_type = src_item.data_type
        self.data_type_pretty = self.create_pretty_data_type_string(src_item.data_type)
        self.loc = src_item.loc
        self.geom = src_item.geom
        self.is_geometry = src_item.output.LAYER_TYPE == 'Surface' if src_item.output is not None else False
        self.sel_type = src_item.sel_type
        self.channel_ids = src_item.channel_ids
        self.node_ids = np.array(src_item.node_ids)
        self.feedback_context = src_item.feedback_context
        self.units = src_item.units
        self.opts['tip'] = src_item.tooltip
        if src_item.range is not None:
            self.range = src_item.range

    @staticmethod
    def create_pretty_data_type_string(data_type) -> str:
        data_type_pretty = data_type
        if ':' in data_type:
            data_type, _, avg_method = data_type.split(':', 2)
            avg_method_comp = avg_method.split('&')
            avg_method_str = avg_method_comp[0]
            if '?' in avg_method_str:
                name_, dir_ = avg_method_str.split('?')
                dir_ = dir_.split('=')[1]
                avg_method_str = f'{name_} (from {dir_})'
            avg_method_str = '{0} - {1}'.format(avg_method_str, ', '.join(avg_method_comp[1:]))
            data_type_pretty = f'{data_type}: {avg_method_str}'
        return data_type_pretty

    def getTopViewBox(self) -> 'ViewBox':
        return self.getTVPlotWidget().get_top_view_box()

    def getTVPlotWidget(self) -> 'TVPlotWidget':
        return self.getViewWidget().parent()

    def showTooltip(self):
        self.setToolTip(self.hover_text)
        style = 'border: 3px solid {0};' \
                f'color: {get_viewer_instance().theme.palette.text().color().name()};' \
                f'background-color: {get_viewer_instance().theme.palette.base().color().name()};' \
                'border-radius: 4px;' \
                'padding: 2px;'.format(self.hover_colour)
        self.getViewWidget().setStyleSheet('QToolTip { ' + style + '}')
        QToolTip.showText(self.hover_pos, self.hover_text, self.getViewWidget(), QRect(), -1)

    def mousePressEvent(self, event):
        if event.button() == QT_RIGHT_BUTTON:
            if self.hoverable and self.isVisible() and self.is_mouse_over_curve(event):
                # hide any tooltips
                self.reset_hover()
                self.is_cursor_over_curve = True
                self.selected = True
                self.setToolTip('')

        super().mousePressEvent(event)

    def context_menu_about_to_show(self):
        self.getTVPlotWidget().suppress_tooltip(True)
        self._pen = self.opts['pen']
        self.setPen(mkPen('r', width=2))
        self.getTopViewBox().ctxMenuAboutToHide.connect(self.context_menu_closed)
        self.getTopViewBox().dragEventStarted.connect(self.context_menu_closed)
        if self.getTopViewBox() != self.getViewWidget().getViewBox():
            self.getViewWidget().getViewBox().dragEventStarted.connect(self.context_menu_closed)

    def context_menu_closed(self):
        self.selected = False
        self.setPen(self._pen)
        self.getTVPlotWidget().suppress_tooltip(False)
        self.getTopViewBox().ctxMenuAboutToHide.disconnect(self.context_menu_closed)
        self.getTopViewBox().dragEventStarted.disconnect(self.context_menu_closed)
        if self.getTopViewBox() != self.getViewWidget().getViewBox():
            self.getViewWidget().getViewBox().dragEventStarted.disconnect(self.context_menu_closed)
        self._pen = None

    def export_data(self) -> np.ndarray:
        return np.column_stack((self.xData, self.yData))
