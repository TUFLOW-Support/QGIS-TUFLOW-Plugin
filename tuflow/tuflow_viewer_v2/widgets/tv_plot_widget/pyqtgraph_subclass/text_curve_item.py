import typing

import numpy as np
try:
    import pandas as pd
except ImportError:
    from .....pt.pytuflow._outputs.pymesh.stubs import pandas as pd

from qgis.PyQt.QtGui import QPainterPath, QFont, QTransform

from .hoverable_scatter_plot import HoverableScatterPlot
from .hoverable_base_class import HoverableBaseClass

from tuflow.pyqtgraph import ScatterPlotItem

if typing.TYPE_CHECKING:
    from ..plotsourceitem import PlotSourceItem


class TextCurveItem(HoverableScatterPlot):

    def __init__(self, *args, **kwargs):
        self.letters = kwargs.pop('letters')
        size = kwargs.pop('size')
        parent_curve = kwargs.get('parent_curve')
        self.parent_src_item = parent_curve.src_item if parent_curve else None
        self.df = None
        super(TextCurveItem, self).__init__(size=7.5, *args, **kwargs)
        self.setPointsVisible(False)
        self.df = pd.DataFrame({
            'x': self.xData,
            'y': self.yData,
            'letters': self.letters,
        })
        self.node_ids = self.letters

        self.symbols = {}
        self.letter_scatter = {}
        for letter in self.df['letters'].unique():
            if not letter.strip():
                continue
            path = self.make_letter_path(str(letter))
            self.symbols[str(letter)] = path

            xydata = self.df.loc[self.df['letters'] == letter, ['x', 'y']]
            xdata = xydata['x'].to_numpy()
            ydata = xydata['y'].to_numpy()

            scatter = ScatterPlotItem(
                x=xdata,
                y=ydata,
                symbol=path,
                pen=kwargs.get('pen'),
                brush=kwargs.get('brush'),
                size=size,
            )
            self.letter_scatter[str(letter)] = scatter
            scatter.setParentItem(self)

    def setData(self, *args, **kwargs):
        super().setData(*args, **kwargs)
        if self.df is None:
            return
        self.setPointsVisible(False)
        xdata = ydata = None
        if args:
            xdata = args[0]
        if len(args) > 1:
            ydata = args[1]
        if xdata is None:
            xdata = kwargs['x'] if 'x' in kwargs else self.src_item.xdata
        if ydata is None:
            ydata = kwargs['y'] if 'y' in kwargs else self.src_item.ydata
        self.df.loc[:, ['x', 'y']] = np.array(list(zip(xdata, ydata))).reshape((-1, 2))
        for letter, scatter in self.letter_scatter.items():
            xydata = self.df.loc[self.df['letters'] == letter, ['x', 'y']]
            xdata = xydata['x'].to_numpy()
            ydata = xydata['y'].to_numpy()
            scatter.setData(xdata, ydata)
            scatter._mouseShape = None
        self.range = (self.xData.min(), self.xData.max())

    def set_parent_src_item(self, src_item: 'PlotSourceItem'):
        self.parent_src_item = src_item
        if src_item is None:
            xdata = self.src_item.xdata
            ydata = np.zeros((len(xdata),), dtype='f8')
        else:
            xdata = src_item.xdata
            ydata = src_item.ydata
        self.setData(xdata, ydata)

    def make_letter_path(self, letter):
        """Create a normalized QPainterPath for a single letter (fits into 1x1 square)."""
        font = QFont('Arial', 12)
        path = QPainterPath()
        path.addText(0, 0, font, letter)

        br = path.boundingRect()
        # Translate so (0,0) is the center
        path.translate(-br.center())
        # Scale to fit within unit size
        scale = 1.0 / max(br.width(), br.height())
        m = QTransform()
        m.scale(scale, scale)
        path = m.map(path)
        return path

    def hoverEvent(self, ev, *args, **kwargs):
        if self.suppress_tooltip:
            self.setToolTip('')
            return

        HoverableBaseClass.hoverEvent(self, ev)
        if ev.isExit():
            return

        if self._p:
            self.hover_text = self.src_item.tooltip(self.src_item, self.parent_src_item, (self._p.x(), self._p.y()),
                                                    self._node_id, is_datetime=self.is_datetime)
        else:
            self.setToolTip('')
            self.hover_local_pos = None

        self.sigHoverEvent.emit(self.getViewBox().mapFromView(ev.pos()), self.feedback_context)
