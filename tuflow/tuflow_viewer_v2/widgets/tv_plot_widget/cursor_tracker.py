import typing

from qgis.PyQt.QtCore import QPointF
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsVertexMarker
from qgis.core import QgsGeometry, QgsPointXY

if typing.TYPE_CHECKING:
    from qgis.gui import QgsMapCanvas
    from .pyqtgraph_subclass.tuflow_viewer_curve import TuflowViewerCurve


class GeometryDict(dict):

    def __setitem__(self, key, value):
        key = key.asPolyline()
        for geom in self.keys():
            if QgsGeometry.compare(key, list(geom)):
                super().__setitem__(geom, value)
                return
        super().__setitem__(tuple(key), value)

    def __contains__(self, item):
        item = item.asPolyline()
        for geom in self.keys():
            if QgsGeometry.compare(item, list(geom)):
                return True
        return False


class CursorTrackerManager:

    def __init__(self, canvas: 'QgsMapCanvas'):
        self.canvas = canvas
        self.trackers = {}

    def __contains__(self, item):
        return item in self.trackers

    def get(self, plot_item: 'TuflowViewerCurve') -> 'CursorTracker':
        return self.trackers.get(plot_item)

    def add_tracker(self, plot_item: 'TuflowViewerCurve', geom: list[tuple[float, float]]):
        self.trackers[plot_item] = CursorTracker(self.canvas, plot_item, geom)

    def set_geometry(self, plot_item: 'TuflowViewerCurve', geom: list[tuple[float, float]]):
        if plot_item not in self.trackers:
            self.add_tracker(plot_item, geom)
        else:
            self.trackers[plot_item].set_geometry(geom)

    def remove_tracker(self, plot_item: 'TuflowViewerCurve'):
        self.trackers.pop(plot_item, None)

    def clear(self):
        self.trackers.clear()

    def set_visible(self, plot_item: 'TuflowViewerCurve', vis: bool):
        if plot_item in self.trackers:
            self.trackers[plot_item].set_visible(vis)

    def update(self, pos: QPointF):
        used_geoms = GeometryDict()

        # find unique geometries and make sure to use the plot_item that is snapped if available
        for_rem = []
        for plot_item, tracker in self.trackers.items():
            tracker.marker.setVisible(False)
            if plot_item.getViewBox() is None:
                for_rem.append(plot_item)
                continue
            if tracker.geometry is None:
                continue
            if tracker.geometry in used_geoms and plot_item.hover_local_pos is None:  # only show one tracker per geometry
                continue
            used_geoms[tracker.geometry] = (plot_item, tracker)

        for plot_item in for_rem:
            self.remove_tracker(plot_item)

        for geom, (plot_item, tracker) in used_geoms.items():
            if plot_item.hover_local_pos is not None and pos is not None:
                tracker.update(plot_item.hover_local_pos)  # this is the snapped position
            else:
                tracker.update(pos)


class CursorTracker:

    def __init__(self, canvas: 'QgsMapCanvas', plot_item: 'TuflowViewerCurve', geom: list[tuple[float, float]]):
        self.canvas = canvas
        self.plot_item = plot_item
        self.vis = True
        self.geom = geom  # ref to parameter
        self.geometry = None  # QgsGeometry
        self.length = None
        self.set_geometry(geom)
        self.marker = self.create_marker()
        self.marker.setVisible(False)

    def __del__(self):
        try:
            self.canvas.scene().removeItem(self.marker)
        except RuntimeError:
            pass

    def set_visible(self, vis: bool):
        self.vis = vis
        self.marker.setVisible(vis)

    def create_marker(self):
        marker = QgsVertexMarker(self.canvas)
        marker.setColor(QColor('#000000'))
        marker.setFillColor(QColor('#ffffff'))
        marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
        marker.setIconSize(10)
        return marker

    def set_geometry(self, geom: list[tuple[float, float]]):
        if geom is not None and len(geom) >= 2:
            self.geometry = QgsGeometry.fromPolylineXY([QgsPointXY(x, y) for x, y in geom])
            self.length = self.geometry.length()
        else:
            self.geometry = None

    def update(self, pos: QPointF):
        # pos is in local viewbox coordinates - need to convert to data coordinates
        if not self.vis:
            self.marker.setVisible(False)
            return
        vb = self.plot_item.getViewBox()
        if not vb or pos is None:
            self.marker.setVisible(False)
            return
        coord = vb.mapToView(pos)
        x = coord.x()
        xmin, xmax = self.plot_item.range
        alpha = None
        if  (xmax - xmin) != 0:
            alpha = (x - xmin) / (xmax - xmin) if xmin <= x <= xmax else None
        if alpha is None or self.geometry is None:
            self.marker.setVisible(False)
            return
        dist = alpha * self.length
        self.marker.setCenter(self.geometry.interpolate(dist).asPoint())
        self.marker.setVisible(True)
