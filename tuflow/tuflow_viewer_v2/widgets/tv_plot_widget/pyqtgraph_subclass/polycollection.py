import typing

import numpy as np
try:
    import pandas as pd
except ImportError:
    from .....pt.pytuflow._outputs.pymesh.stubs import pandas as pd

from qgis.PyQt.QtCore import QPointF, QRectF, QSettings
from qgis.PyQt.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QWidget
from qgis.PyQt.QtGui import QPainter, QLinearGradient, QColor, QPolygonF

from .polygon import Polygons, Polygon

if typing.TYPE_CHECKING:
    from ..plotsourceitem import PlotSourceItem


SPECTRAL_R = [(43, 131, 186), (171, 221, 164), (255, 255, 191), (253, 174, 97), (215, 25, 28)]


ColourCurveInputType = typing.Iterable[str | typing.Iterable[int | float]] | typing.Iterable[QColor]


class ColourCurve:

    def __init__(self, colours: ColourCurveInputType = (), interp_method: str = 'linear'):
        self.interp_method = interp_method
        if not colours:
            self.colours = np.array([(0, 0, 0, 0), (1, 1, 1, 1)], dtype=float)
        else:
            if isinstance(colours, dict):
                colours = [(key, colours[key]) for key in sorted(colours)]
            else:
                colours = colours.tolist() if isinstance(colours, (np.ndarray, pd.Series)) else list(colours)
                colours = [(i / len(colours), x) for i, x in enumerate(colours)]
            c = colours[0][1]
            if isinstance(c, QColor):
                self.colours = np.array([[stop, col.redF(), col.greenF(), col.blueF()] for stop, col in colours], dtype=float)
            elif isinstance(c, tuple) and all(isinstance(comp, int) for comp in c):
                self.colours = np.array([[stop, col[0] / 255.0, col[1] / 255.0, col[2] / 255.0] for stop, col in colours], dtype=float)
            elif isinstance(c, tuple) and all(isinstance(comp, float) for comp in c):
                self.colours = np.array([[stop, *col] for stop, col in colours], dtype=float)
            else:
                raise ValueError('Invalid colour format in ColourGradient')

    def color(self, pos: float) -> QColor:
        if self.interp_method == 'linear':
            c = (
                np.interp(pos, self.colours[:,0], self.colours[:,1]),
                np.interp(pos, self.colours[:,0], self.colours[:,2]),
                np.interp(pos, self.colours[:,0], self.colours[:,3]),
                1.
            )
        elif self.interp_method == 'constant':
            idx = np.searchsorted(self.colours[:,0], pos, side='right')
            idx = np.clip(idx, 0, len(self.colours) - 1)
            c = (
                self.colours[idx, 1],
                self.colours[idx, 2],
                self.colours[idx, 3],
                1.
            )
        elif self.interp_method == 'exact':
            idx = np.where(self.colours[:,0] == pos)[0]
            if len(idx) == 0:
                c = (0, 0, 0, 0)
            else:
                c = (
                    self.colours[idx[0], 1],
                    self.colours[idx[0], 2],
                    self.colours[idx[0], 3],
                    1.
                )
        else:
            c = (0, 0, 0, 0)

        return QColor.fromRgbF(*c)


class PolyCollection(Polygons):

    def __init__(self, polygons: np.ndarray, values: np.ndarray, src_item: 'PlotSourceItem', *args, **kwargs):
        self.xData = np.array([])
        self.yData = np.array([])
        self.polygons = np.ndarray([])
        self.poly_data_x = np.ndarray([])
        self.poly_data_y = np.ndarray([])
        self.values = np.ndarray([])
        self.minval = None
        self.maxval = None
        self.values_norm = np.ndarray([])
        self.qpolygons = []
        self._bounding_rect = QRectF()
        self.colour_gradient = ColourCurve(
            src_item.qgis_data_colour_curve if src_item and src_item.qgis_data_colour_curve else SPECTRAL_R,
            src_item.qgis_data_colour_interp_method
        )
        self.colours = []
        self._setData(polygons, values, src_item)
        super().__init__(self.qpolygons, self.values.tolist(), node_ids=[], src_item=src_item, *args, **kwargs)
        self.data_type = src_item.data_type
        self.setBrush()

    def export_data(self) -> np.ndarray:
        return np.column_stack((self.xData, self.yData, np.repeat(self.values, 4)))

    def boundingRect(self) -> QRectF:
        return self._bounding_rect

    def set_grid_line_thickness(self, value: float):
        pen = self.opts['pen']
        pen.setWidthF(value)
        self.setPen(pen)

    def set_grid_line_colour(self, colour: str):
        pen = self.opts['pen']
        pen.setColor(QColor(colour))
        self.setPen(pen)

    def setBrush(self):
        for poly, col in zip(self._polygons, self.colours):
            poly.setBrush(col)

    def setColourCurveData(self, minval: float, maxval: float, colour_curve: ColourCurveInputType, interp_method: str):
        self.colour_gradient = ColourCurve(colour_curve, interp_method)
        self.minval = minval
        self.maxval = maxval
        self.values_norm = (np.clip(self.values, self.minval, self.maxval) - self.minval) / (self.maxval - self.minval)
        self.colours = [self.colour_gradient.color(v) for v in self.values_norm]
        self.setBrush()
        self.getViewWidget().update()

    def getData(self):
        return self.poly_data_x, self.poly_data_y

    def setData(self, x: np.ndarray, y: np.ndarray, src_item: 'PlotSourceItem' = None):
        self._setData(x, y, src_item)
        for val, poly_item, qpoly in zip(self.values, self._polygons, self.qpolygons):
            poly_item.set_polygon(qpoly)
            poly_item.channel_id = str(val)
        if len(self._polygons) > len(self.qpolygons):
            for poly_item in self._polygons[len(self.qpolygons):]:
                self.getViewBox().removeItem(poly_item)
                self._polygons.remove(poly_item)
        elif len(self.qpolygons) > len(self._polygons):
            for val, qpoly in zip(self.values[len(self._polygons):], self.qpolygons[len(self._polygons):]):
                item = Polygon(qpoly, str(val), parent=self)
                item.setPen(self.opts['pen'])
                item.sigHoverEvent.connect(self.hoverEvent)
                self._polygons.append(item)
        self.setBrush()
        self.prepareGeometryChange()
        self.update()

    def _setData(self, polygons: np.ndarray, values: np.ndarray, src_item: 'PlotSourceItem'):
        self.poly_data_x = polygons.reshape((-1, 2))
        self.poly_data_y = np.array([[x] * 4 for x in values]).reshape((-1,))
        self.xData = self.poly_data_x[:, 0]
        self.yData = self.poly_data_x[:, 1]
        self.polygons = polygons
        self.values = np.array(values).flatten()
        if src_item and src_item.qgis_data_min is None and self.minval is None:
            self.minval = np.nanmin(values)
        if src_item and src_item.qgis_data_max is None and self.maxval is None:
            self.maxval = np.nanmax(values)
        self.minval = src_item.qgis_data_min if src_item and src_item.qgis_data_min is not None else self.minval
        self.maxval = src_item.qgis_data_max if src_item and src_item.qgis_data_max is not None else self.maxval
        # make sure there is no divide by zero
        diff = self.maxval - self.minval
        if diff == 0 or np.isnan(diff):
            diff = 1
        self.values_norm = (np.clip(self.values, self.minval, self.maxval) - self.minval) / diff
        self.colours = [self.colour_gradient.color(v) for v in self.values_norm]
        self.qpolygons = [QPolygonF([QPointF(float(px), float(py)) for px, py in poly]) for poly in self.polygons]
        if self.qpolygons:
            xmin = self.polygons[:, :, 0].min()
            xmax = self.polygons[:, :, 0].max()
            ymin = self.polygons[:, :, 1].min()
            ymax = self.polygons[:, :, 1].max()
            self._bounding_rect = QRectF(QPointF(xmin, ymax), QPointF(xmax, ymin))
