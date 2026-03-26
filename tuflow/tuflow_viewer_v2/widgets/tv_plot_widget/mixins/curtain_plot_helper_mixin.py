import typing
from datetime import datetime

import numpy as np
from qgis.PyQt.QtCore import QSettings, QObject
from qgis.core import (QgsMeshDatasetIndex, Qgis, QgsProject, QgsDistanceArea, QgsCoordinateTransformContext,
                       QgsMeshRendererVectorSettings, QgsMeshRendererVectorArrowSettings, QgsColorRampShader,
                       QgsInterpolatedLineColor, QgsGeometry, QgsPointXY)

from ..pyqtgraph_subclass.polycollection import PolyCollection, ColourCurve
from ..pyqtgraph_subclass.quiver import (Quiver, ArrowPainterDefinedByMinMax, ArrowPainterFixed,
                                         ArrowPainterScaledByMagnitude, ArrowPainter)
from .plot_helper_mixin import PlotHelperMixin
from ..plotsourceitem import PlotSourceItem
from ....tvinstance import get_viewer_instance
from ....tvdeveloper_tools import Profiler
from ....fmts.tvoutput import TuflowViewerOutput

if not QSettings().value('TUFLOW/TestCase', False, type=bool):
    from .....pt.pytuflow import MapOutput
else:
    from tuflow.pt.pytuflow import MapOutput

import logging
logger = logging.getLogger('tuflow_viewer')


class CurtainPlotHelperMixin(PlotHelperMixin):

    def _init_plot_helper(self):
        super()._init_plot_helper()
        self._connected_layers = []
        self._vector_cache = {}
        self._vert_vel_cache = {}

    def _line_to_wkt(self, line: list[list[float]]) -> str:
        wkt = 'LINESTRING('
        wkt += ', '.join([f'{pt[0]} {pt[1]}' for pt in line])
        wkt += ')'
        return wkt

    def _populate_plot_data(self, src_item: PlotSourceItem, time: datetime, *args, **kwargs) -> typing.Generator[PlotSourceItem, None, None]:
        output = src_item.output
        data_type, _ = self._split_depth_averaging(src_item.data_type)
        if data_type not in output.data_types('section'):
            return

        src_item.data_type = data_type
        location = src_item.geom if src_item.output.LAYER_TYPE == 'Surface' else src_item.loc
        start = 0.
        end = 0.
        if location:
            da = QgsDistanceArea()
            if QgsProject.instance().crs().isGeographic():
                da.setEllipsoid('WGS84')
            end = da.measureLength(QgsGeometry.fromPolylineXY([QgsPointXY(*x) for x in location]))
        src_item.range = (start, end)

        src_item.feedback_context = 'dynamic'
        src_item.xaxis_name = 'offset'
        src_item.yaxis_name = data_type
        src_item.units = self._units(data_type)
        src_item.ready_for_plotting = True
        src_item.tooltip = self.tooltip
        src_item.label = self._label(data_type)

        src_item.qgis_data_min, src_item.qgis_data_max, src_item.qgis_data_colour_curve, src_item.qgis_data_colour_interp_method = \
            self._qgis_render_data(output, data_type)
        lyr = output.map_layers()[0]
        if lyr not in self._connected_layers:
            lyr.rendererChanged.connect(self._qgis_renderer_changed)
            self._connected_layers.append(lyr)

        profiler = Profiler()
        profiler('pytuflow::curtain()')
        try:
            df = output.curtain(location, data_type, time)
        except (ValueError, IndexError) as e:
            logger.info(f'pytuflow failed to plot curtain: {e}')
            return
        finally:
            profiler('pytuflow::curtain()')

        for xdata, ydata, extra in output.curtain_plot(df, data_type, src_item):
            src_item = extra['src_item'] if 'src_item' in extra else src_item
            src_item.xdata = xdata
            src_item.ydata = ydata
            src_item.ready_for_plotting = True
            if 'vector' in extra:
                wkt = self._line_to_wkt(location)
                if wkt not in self._vector_cache:
                    self._vector_cache[wkt] = {}
                if output.id not in self._vector_cache[wkt]:
                    self._vector_cache[wkt][output.id] = {}
                if src_item.data_type.startswith('max'):
                    time = 'max'
                elif src_item.data_type.startswith('min'):
                    time = 'min'
                self._vector_cache[wkt][output.id][time] = extra['vector']
            if 'vertical vector' in extra:
                wkt = self._line_to_wkt(location)
                if wkt not in self._vert_vel_cache:
                    self._vert_vel_cache[wkt] = {}
                if output.id not in self._vert_vel_cache[wkt]:
                    self._vert_vel_cache[wkt][output.id] = {}
                self._vert_vel_cache[wkt][output.id][time] = extra['vertical vector']
            yield src_item

    def _qgis_renderer_changed(self):
        sender = self.plot_graph.sender()
        if not sender:
            return
        idx = sender.rendererSettings().activeScalarDatasetGroup()
        if idx == -1:
            return
        data_type = sender.datasetGroupMetadata(QgsMeshDatasetIndex(idx)).name()
        data_type = MapOutput._get_standard_data_type_name(data_type)
        output = get_viewer_instance().map_layer_to_output(sender)
        if not output:
            return
        for item in self.plot_graph.items():
            if not isinstance(item, (PolyCollection, Quiver)):
                continue
            if item.src_item.output != output:
                continue
            if isinstance(item, PolyCollection):
                if item.data_type != data_type:
                    continue
                item.src_item.qgis_data_min, item.src_item.qgis_data_max, item.src_item.qgis_data_colour_curve, item.src_item.qgis_data_colour_interp_method = \
                    self._qgis_render_data(output, data_type)
                if item.src_item.qgis_data_colour_interp_method:
                    item.setColourCurveData(
                        item.src_item.qgis_data_min,
                        item.src_item.qgis_data_max,
                        item.src_item.qgis_data_colour_curve,
                        item.src_item.qgis_data_colour_interp_method
                    )
            else:  # Quiver
                ismax = item.src_item.data_type.startswith('max')
                ismin = item.src_item.data_type.startswith('min')
                painter = self._create_vector_painter(output, ismax, ismin)
                if painter:
                    item.painter = painter

    def _qgis_render_data(self, output: TuflowViewerOutput, data_type: str) -> tuple[float, float, dict, str]:
        lyr = output.map_layers()[0]
        idx = -1
        for i in range(lyr.datasetGroupCount()):
            name = lyr.datasetGroupMetadata(QgsMeshDatasetIndex(i)).name()
            name = MapOutput._get_standard_data_type_name(name)
            if name == data_type:
                idx = i
                break
        if idx == -1:
            return -1, -1, {}, ''
        rs = lyr.rendererSettings()
        settings = rs.scalarSettings(idx)
        return self._extract_shader_info(settings.colorRampShader())

    def _extract_shader_info(self, shader: QgsColorRampShader) -> tuple[float, float, dict, str]:
        minval = shader.minimumValue()
        maxval = shader.maximumValue()
        f = lambda x: (np.clip(x, minval, maxval) - minval) / (maxval - minval)
        stops = {f(x.value): x.color for x in shader.colorRampItemList()}
        interpolation_method = {
            Qgis.ShaderInterpolationMethod.Linear: 'linear',
            Qgis.ShaderInterpolationMethod.Discrete: 'constant',
            Qgis.ShaderInterpolationMethod.Exact: 'exact',
        }[shader.colorRampType()]
        return minval, maxval, stops, interpolation_method

    def _create_vector_painter(self, output: TuflowViewerOutput, ismax: bool, ismin: bool, only_if_updated: bool = True) -> ArrowPainter | None:
        lyr = output.map_layers()[0]

        if ismax:
            name = 'max vector velocity' if 'max vector velocity' in output.data_types() else 'max velocity'
        elif ismin:
            name = 'min vector velocity' if 'min vector velocity' in output.data_types() else 'min velocity'
        else:
            name = 'vector velocity' if 'vector velocity' in output.data_types() else 'velocity'

        try:
            idx = output.group_index_from_name(name)
        except ValueError:
            idx = -1

        if idx == -1:
            return None

        rs = lyr.rendererSettings()
        if rs.activeVectorDatasetGroup() != idx and only_if_updated:
            return None

        settings = rs.vectorSettings(idx)
        if settings.symbology() != QgsMeshRendererVectorSettings.Arrows and only_if_updated:
            return None

        minval = output.minimum('velocity')
        maxval = output.maximum('velocity')
        arrows = settings.arrowSettings()
        method = arrows.shaftLengthMethod()
        if method == QgsMeshRendererVectorArrowSettings.MinMax:
            painter = ArrowPainterDefinedByMinMax(minval, maxval)
            painter.min_length = arrows.minShaftLength()
            painter.max_length = arrows.maxShaftLength()
        elif method == QgsMeshRendererVectorArrowSettings.Fixed:
            painter = ArrowPainterFixed(minval, maxval)
            painter.fixed_length = arrows.fixedShaftLength()
        else:
            painter = ArrowPainterScaledByMagnitude(minval, maxval)
            painter.scale_factor = arrows.scaleFactor()
        painter.head_length = arrows.arrowHeadLengthRatio()
        painter.head_width = arrows.arrowHeadWidthRatio()
        painter.line_width = settings.lineWidth()
        painter.single_colour = settings.color()
        min_, max_, stops, interp_method = self._extract_shader_info(settings.colorRampShader())
        painter.color_curve = ColourCurve(stops, interp_method)
        painter.colmin = min_
        painter.colmax = max_
        if settings.coloringMethod() == QgsInterpolatedLineColor.SingleColor:
            painter.colour_method = 'single'
        else:
            painter.colour_method = 'curve'

        return painter
