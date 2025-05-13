import math

import numpy as np
from qgis.core import Qgis, QgsGeometry, QgsPointXY, QgsRectangle
from qgis.gui import QgsMapTool, QgsMapCanvas, QgsMapMouseEvent, QgsRubberBand, QgsVertexMarker

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtGui import QColor



from ..compatibility_routines import QT_CURSOR_SIZE_DIAG_B, QT_LEFT_BUTTON, QT_CURSOR_SIZE_DIAG_F, QT_CURSOR_SIZE_ALL, QT_CURSOR_SIZE_VER, QT_STYLE_DASHED_PEN, QT_CURSOR_CROSS, QT_CURSOR_SIZE_HOR, QT_TRANSPARENT, QT_BLACK


def clamp_angle(angle):
    while angle <= -math.pi:
        angle += 2 * math.pi
    while angle > math.pi:
        angle -= 2 * math.pi
    return angle


class InteractiveRectMapTool(QgsMapTool):
    """QgsMapTool for drawing and interacting with a rectangle on the map canvas. The tool
    initialises in draw mode, where the user can draw a rectangle by clicking and dragging. Once
    drawn, the user can interact with the rectangle by resizing, translating, and rotating it.
    """

    updated = pyqtSignal()

    def __init__(self, canvas: QgsMapCanvas, color: QColor) -> None:
        super().__init__(canvas)
        self.canvas = canvas
        self.geom_rect = RectOutline(canvas, None, color=color)
        self.geom_centre = RectCentre(canvas, None, color=color)
        self.geom_rot_arm_r = RectRotationArm(canvas, None, color=color)
        self.geom_rot_arm_l = RectRotationArm(canvas, None, color=color)
        self.geom_rot_arm_t = RectRotationArm(canvas, None, color=color)
        self.geom_rot_arm_b = RectRotationArm(canvas, None, color=color)
        self.angle = 0.
        self.origin_x = 0.
        self.origin_y = 0.
        self.width = 0.
        self.height = 0.

        self._draw_mode = False

        # "md" is shorthand for "mouse down" and is used to store the state of the rectangle when the mouse is pressed
        self._mouse_is_down = False
        self._md_point = None
        self._md_angle = None
        self._md_angle_up = None
        self._md_geom = None
        self._md_width = None
        self._md_height = None

        self._centroid_idx = None
        self._corner_idx = None
        self._edge_idx = None
        self._rot_arm_idx = None
        self._dif = np.zeros((4, 2), dtype='f8')

    def valid(self) -> bool:
        """Returns whether the rectangle is valid."""
        return self.width > 0 and self.height > 0

    def centre(self) -> QgsPointXY:
        if self.valid():
            return self.geom_centre.geometry.asPoint()

    def set_color(self, color: QColor) -> None:
        """Sets the color of the rectangle and other graphics on the canvas."""
        self.geom_rect.set_color(color)
        self.geom_centre.set_color(color)
        self.geom_rot_arm_r.set_color(color)
        self.geom_rot_arm_l.set_color(color)
        self.geom_rot_arm_t.set_color(color)
        self.geom_rot_arm_b.set_color(color)

    def clear(self) -> None:
        """Clears the rectangle and other graphics from the canvas."""
        self.geom_rect.clear()
        self.geom_centre.clear()
        self.geom_rot_arm_r.clear()
        self.geom_rot_arm_l.clear()
        self.geom_rot_arm_t.clear()
        self.geom_rot_arm_b.clear()
        self.angle = 0.
        self.origin_x = 0.
        self.origin_y = 0.
        self.width = 0.
        self.height = 0.
        self.updated.emit()

    def update(self, geom: QgsGeometry) -> None:
        """Updates the rectangle and graphics on the canvas based on the input rectangle geometry."""
        self.geom_rect.geometry = geom
        self.geom_centre.geometry = geom.centroid()

        c = geom.centroid().asPoint()

        # left/right rotation arm
        dist = self.width * 1.5 * 0.5
        dx = math.cos(self.angle) * dist
        dy = math.sin(self.angle) * dist
        self.geom_rot_arm_l.geometry = QgsGeometry.fromPolylineXY([c, QgsPointXY(c.x() - dx, c.y() - dy)])
        self.geom_rot_arm_r.geometry = QgsGeometry.fromPolylineXY([c, QgsPointXY(c.x() + dx, c.y() + dy)])

        # top/bottom rotation arm
        dist = self.height * 1.5 * 0.5
        dx = math.sin(self.angle) * dist
        dy = math.cos(self.angle) * dist
        self.geom_rot_arm_t.geometry = QgsGeometry.fromPolylineXY([c, QgsPointXY(c.x() - dx, c.y() + dy)])
        self.geom_rot_arm_b.geometry = QgsGeometry.fromPolylineXY([c, QgsPointXY(c.x() + dx, c.y() - dy)])

        self.updated.emit()

    def canvasPressEvent(self, e: QgsMapMouseEvent) -> None:
        """Triggered when the mouse is pressed on the canvas."""
        super().canvasPressEvent(e)
        if e.button() != QT_LEFT_BUTTON:
            return
        p = e.mapPoint()
        self._mouse_is_down = True
        self._md_point = p
        self._md_angle = clamp_angle(self.angle)
        self._md_geom = self.geom_rect.geometry
        self._md_width = self.width
        self._md_height = self.height
        if self.valid():
            verts = self._md_geom.asMultiPolygon()[0][0]
            self._md_angle_up = math.atan2(verts[3].y() - verts[0].y(), verts[3].x() - verts[0].x())
        else:
            self._draw_mode = True

    def canvasReleaseEvent(self, e: QgsMapMouseEvent) -> None:
        """Triggered when the mouse is released on the canvas."""
        super().canvasReleaseEvent(e)
        if e.button() != QT_LEFT_BUTTON:
            return
        self._mouse_is_down = False
        self._draw_mode = False

    def canvasMoveEvent(self, e: QgsMapMouseEvent) -> None:
        """Triggered when the mouse is moved on the canvas."""
        super().canvasMoveEvent(e)
        p = e.mapPoint()

        if not self._mouse_is_down:
            if self.valid():
                self._check_cursor_hover(e)  # check if cursor is hovering over anything interactable
            return

        if self._draw_mode:
            rect = QgsRectangle(self._md_point, p)
            self.width = rect.width()
            self.height = rect.height()
            self.origin_x = rect.xMinimum()
            self.origin_y = rect.yMinimum()
            self.update(QgsGeometry.fromWkt(rect.asWktPolygon()))
            return

        if self.valid():
            self._interaction(p)

    def _interaction(self, p: QgsPointXY) -> None:
        """Method to handle the interaction with the rectangle. Called when the user has the mouse pressed down."""
        if self._centroid_idx:
            self._translate(p)
        elif self._corner_idx is not None or self._edge_idx:
            self._scale(p)
        elif self._rot_arm_idx:
            self._rotate(p)

    def _translate(self, p: QgsPointXY) -> None:
        """Method to translate the rectangle based on the mouse movement."""
        dx = p.x() - self.geom_centre.geometry.asPoint().x()
        dy = p.y() - self.geom_centre.geometry.asPoint().y()
        self.origin_x += dx
        self.origin_y += dy
        geometry = self.geom_rect.geometry
        geometry.translate(dx, dy)
        self.update(geometry)

    def _rotate(self, p: QgsPointXY) -> None:
        """Method to rotate the rectangle based on the mouse movement."""
        c = self._md_geom.centroid().asPoint()
        vec1 = np.array([self._md_point.x() - c.x(), self._md_point.y() - c.y()])
        vec2 = np.array([p.x() - c.x(), p.y() - c.y()])
        dot = np.dot(vec1, vec2)
        mag1 = np.linalg.norm(vec1)
        mag2 = np.linalg.norm(vec2)
        cos_theta = max(min(dot / (mag1 * mag2), 1.), -1.)
        angle = np.arccos(cos_theta)
        if np.cross(vec1, vec2) < 0:
            angle = -angle
        self.angle = self._md_angle + angle
        geometry = QgsGeometry(self._md_geom)
        geometry.rotate(-math.degrees(angle), c)
        self.origin_x = geometry.asMultiPolygon()[0][0][0].x()
        self.origin_y = geometry.asMultiPolygon()[0][0][0].y()
        self.update(geometry)

    def _scale(self, p: QgsPointXY) -> None:
        """Method to scale the rectangle based on the mouse movement and which edge/corner the user has selected."""
        verts = self._md_geom.asMultiPolygon()[0][0]
        self._dif[:] = 0.
        movement_vec = np.array([p.x() - self._md_point.x(), p.y() - self._md_point.y()])
        if self._edge_idx == 1 or self._corner_idx == 0 or self._corner_idx == 1:
            self._bottom_edge(verts, movement_vec)
        if self._edge_idx == 2 or self._corner_idx == 1 or self._corner_idx == 2:
            self._right_edge(verts, movement_vec)
        if self._edge_idx == 3 or self._corner_idx == 2 or self._corner_idx == 3:
            self._top_edge(verts, movement_vec)
        if self._edge_idx == 4 or self._corner_idx == 3 or self._corner_idx == 0:
            self._left_edge(verts, movement_vec)

        # don't let user drag size beyond opposite edge
        angle = math.atan2(verts[1].y() - verts[0].y(), verts[1].x() - verts[0].x())
        angle_up = math.atan2(verts[3].y() - verts[0].y(), verts[3].x() - verts[0].x())
        if not np.isclose([self._md_angle, self._md_angle_up], [angle, angle_up], atol=0.01).all():
            return

        self.width = np.linalg.norm([verts[1].x() - verts[0].x(), verts[1].y() - verts[0].y()])
        self.height = np.linalg.norm([verts[3].x() - verts[0].x(), verts[3].y() - verts[0].y()])
        self.origin_x = verts[0].x()
        self.origin_y = verts[0].y()
        verts[4] = verts[0]
        self.update(QgsGeometry.fromPolygonXY([verts]))

    def _left_edge(self, verts: list[QgsPointXY], movement_vec: np.ndarray) -> None:
        """Method to scale the (original) left edge of the rectangle, whichever way it may be orientated."""
        edge_orth_vec = np.array([verts[1].x() - verts[0].x(), verts[1].y() - verts[0].y()])
        xdif, ydif = self._project_movement(edge_orth_vec, movement_vec)
        i, j = 3, 0
        self._move_edge(verts, xdif, ydif, i, j)

    def _right_edge(self, verts: list[QgsPointXY], movement_vec: np.ndarray) -> None:
        """Method to scale the (original) right edge of the rectangle, whichever way it may be orientated."""
        edge_orth_vec = np.array([verts[3].x() - verts[2].x(), verts[3].y() - verts[2].y()])
        xdif, ydif = self._project_movement(edge_orth_vec, movement_vec)
        i, j = 1, 2
        self._move_edge(verts, xdif, ydif, i, j)

    def _top_edge(self, verts: list[QgsPointXY], movement_vec: np.ndarray) -> None:
        """Method to scale the (original) top edge of the rectangle, whichever way it may be orientated."""
        edge_orth_vec = np.array([verts[4].x() - verts[3].x(), verts[4].y() - verts[3].y()])
        xdif, ydif = self._project_movement(edge_orth_vec, movement_vec)
        i, j = 2, 3
        self._move_edge(verts, xdif, ydif, i, j)

    def _bottom_edge(self, verts: list[QgsPointXY], movement_vec: np.ndarray) -> None:
        """Method to scale the (original) bottom edge of the rectangle, whichever way it may be orientated."""
        edge_orth_vec = np.array([verts[2].x() - verts[1].x(), verts[2].y() - verts[1].y()])
        xdif, ydif = self._project_movement(edge_orth_vec, movement_vec)
        i, j = 0, 1
        self._move_edge(verts, xdif, ydif, i, j)

    def _project_movement(self, edge_orth_vec: np.ndarray, movement_vec: np.ndarray) -> tuple[float, float]:
        """Method to project the movement vector onto the orthogonal edge vector.
        Returns the x and y differences to move the edge by.
        """
        edge_orth_vec /= np.linalg.norm(edge_orth_vec)
        proj = np.dot(movement_vec, edge_orth_vec)
        xdif = proj * edge_orth_vec[0]
        ydif = proj * edge_orth_vec[1]
        return xdif, ydif

    def _move_edge(self, verts: list[QgsPointXY], xdif: float, ydif: float, i: int, j: int) -> None:
        """Method to move the edge between vertices i and j by the x and y differences.
        Tracks the total movement in the _dif array so that more than one edge can be moved
        at once (i.e. corner scaling).
        """
        md_verts = self._md_geom.asMultiPolygon()[0][0]
        self._dif[i,0] += xdif
        self._dif[i,1] += ydif
        self._dif[j,0] += xdif
        self._dif[j,1] += ydif
        verts[i] = QgsPointXY(md_verts[i].x() + self._dif[i,0], md_verts[i].y() + self._dif[i,1])
        verts[j] = QgsPointXY(md_verts[j].x() + self._dif[j,0], md_verts[j].y() + self._dif[j,1])

    def _check_cursor_hover(self, e: QgsMapMouseEvent) -> None:
        """Method to check if the cursor is hovering over any interactable parts of the rectangle.
        Uses a cursor snap geometry with a tolerance to 10 pixels in each direction.
        """
        # cursor snap geometry
        p1 = self.canvas.getCoordinateTransform().toMapCoordinates(e.pos().x() - 5, e.pos().y() - 5)
        p2 = self.canvas.getCoordinateTransform().toMapCoordinates(e.pos().x() - 5, e.pos().y() + 5)
        p3 = self.canvas.getCoordinateTransform().toMapCoordinates(e.pos().x() + 5, e.pos().y() + 5)
        p4 = self.canvas.getCoordinateTransform().toMapCoordinates(e.pos().x() + 5, e.pos().y() - 5)
        cur = QgsGeometry.fromPolygonXY([[p1, p2, p3, p4, p1]])

        self._centroid_idx = None
        self._corner_idx = None
        self._edge_idx = None
        self._rot_arm_idx = None

        # check if cursor is over centroid
        if self.geom_centre.geometry and cur.intersects(self.geom_centre.geometry):
            self._centroid_idx = 1
            self.setCursor(QT_CURSOR_SIZE_ALL)
            return

        # check if the cursor is on a domain corner
        if self.geom_rect.geometry:
            vec1 = np.array([1., 0.])
            verts = self.geom_rect.geometry.asMultiPolygon()
            if not verts or not verts[0]:
                return
            verts = verts[0][0]
            for i, p in enumerate(verts[:-1]):
                p1_ = p
                p2_ = verts[i + 1]
                if QgsGeometry.fromPointXY(p).intersects(cur):
                    self._corner_idx = i
                    vec2 = np.array([p2_.x() - p1_.x(), p2_.y() - p1_.y()])
                    cos_theta = max(min(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)), 1.), -1.)
                    angle = np.degrees(np.arccos(cos_theta))
                    cursor = QT_CURSOR_SIZE_DIAG_B if abs(angle) <= 45 or abs(angle) > 135 else QT_CURSOR_SIZE_DIAG_F
                    self.setCursor(cursor)
                    return

            # check if cursor is on a domain edge
            vec1 = np.array([1., 0.])
            for i in range(1, len(verts)):
                p1_ = verts[i - 1]
                p2_ = verts[i]
                edge = QgsGeometry.fromPolylineXY([p1_, p2_])
                if edge.intersects(cur):
                    self._edge_idx = i
                    vec2 = np.array([p2_.x() - p1_.x(), p2_.y() - p1_.y()])
                    cos_theta = max(min(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)), 1.), -1.)
                    angle = np.degrees(np.arccos(cos_theta))
                    cursor = QT_CURSOR_SIZE_VER if abs(angle) <= 45 or abs(angle) > 135 else QT_CURSOR_SIZE_HOR
                    self.setCursor(cursor)
                    return

        # check if cursor is on a rotation arm
        if self.geom_rot_arm_b.geometry:
            vec1 = np.array([1., 0.])
            if cur.intersects(self.geom_rot_arm_l.geometry):
                self._rot_arm_idx = 'left'
                p1_, p2_ = self.geom_rot_arm_l.geometry.asPolyline()
            elif cur.intersects(self.geom_rot_arm_r.geometry):
                self._rot_arm_idx = 'right'
                p1_, p2_ = self.geom_rot_arm_r.geometry.asPolyline()
            elif cur.intersects(self.geom_rot_arm_b.geometry):
                self._rot_arm_idx = 'bottom'
                p1_, p2_ = self.geom_rot_arm_b.geometry.asPolyline()
            elif cur.intersects(self.geom_rot_arm_t.geometry):
                self._rot_arm_idx = 'top'
                p1_, p2_ = self.geom_rot_arm_t.geometry.asPolyline()
            if self._rot_arm_idx:
                vec2 = np.array([p2_.x() - p1_.x(), p2_.y() - p1_.y()])
                cos_theta = max(min(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)), 1.), -1.)
                angle = np.degrees(np.arccos(cos_theta))
                cursor = QT_CURSOR_SIZE_VER if abs(angle) <= 45 or abs(angle) > 135 else QT_CURSOR_SIZE_HOR
                self.setCursor(cursor)
                return

        self.setCursor(QT_CURSOR_CROSS)


class RectDrawItem:
    """Base class for drawing items on the map canvas for the InteractiveRectMapTool."""

    def __init__(self, canvas: QgsMapCanvas, geometry: QgsGeometry, **styling):
        self.canvas = canvas
        self.geometry = geometry

    @property
    def geometry(self) -> QgsGeometry:
        """Sets the items geometry."""
        pass

    @geometry.setter
    def geometry(self, geom: QgsGeometry) -> None:
        """Returns the items geometry."""
        pass

    def clear(self) -> None:
        """Clear the item's geometry."""
        pass


class RectDrawRubberBand(RectDrawItem):
    """Base class for drawing rubber-bands for the InteractiveRectMapTool."""

    DEFAULT_WIDTH = 2
    DEFAULT_STYLE = QT_STYLE_DASHED_PEN
    DEFAULT_COLOR = QT_BLACK
    DEFAULT_FILL_COLOR = QT_TRANSPARENT
    GEOMETRY = Qgis.GeometryType.Polygon

    def __init__(self, canvas: QgsMapCanvas, geometry: QgsGeometry, **styling):
        self.rubber_band = QgsRubberBand(canvas, self.GEOMETRY)
        self.width = styling.get('width', self.DEFAULT_WIDTH)
        self.style = styling.get('style', self.DEFAULT_STYLE)
        self.color = styling.get('color', self.DEFAULT_COLOR)
        self.fill_color = styling.get('fill_color', self.DEFAULT_FILL_COLOR)
        self.rubber_band.setWidth(int(self.width))
        self.rubber_band.setColor(self.color)
        self.rubber_band.setLineStyle(self.style)
        self.rubber_band.setFillColor(self.fill_color)
        super().__init__(canvas, geometry, **styling)

    @property
    def geometry(self) -> QgsGeometry:
        return self.rubber_band.asGeometry()

    @geometry.setter
    def geometry(self, geom: QgsGeometry) -> None:
        if geom is None:
            self.rubber_band.setVisible(False)
            return
        self.rubber_band.setVisible(True)
        self.rubber_band.setToGeometry(geom)

    def clear(self) -> None:
        self.geometry = None
        self.rubber_band.reset()

    def set_color(self, color: QColor) -> None:
        self.rubber_band.setStrokeColor(color)


class RectOutline(RectDrawRubberBand):
    """Rectangle outline item for the InteractiveRectMapTool."""
    pass


class RectRotationArm(RectDrawRubberBand):
    """Rotation arm item for the InteractiveRectMapTool."""
    DEFAULT_WIDTH = 0.5
    GEOMETRY = Qgis.GeometryType.Line


class RectCentre(RectDrawItem):
    """Centre marker item for the InteractiveRectMapTool."""

    def __init__(self, canvas: QgsMapCanvas, geometry: QgsGeometry, **styling):
        self.canvas = canvas
        self.size = styling.get('size', 15)
        self.width = styling.get('width', 2)
        self.icon = styling.get('icon', QgsVertexMarker.ICON_CROSS)
        self.color = styling.get('color', QT_BLACK)
        self.marker = QgsVertexMarker(canvas)
        self.marker.setColor(self.color)
        self.marker.setIconSize(self.size)
        self.marker.setIconType(self.icon)
        self.marker.setPenWidth(self.width)
        super().__init__(canvas, geometry, **styling)

    @property
    def geometry(self) -> QgsGeometry:
        return QgsGeometry.fromPointXY(self.marker.center())

    @geometry.setter
    def geometry(self, geom: QgsGeometry):
        if geom is None:
            self.marker.setVisible(False)
            return
        self.marker.setVisible(True)
        self.marker.setCenter(geom.asPoint())

    def clear(self) -> None:
        self.geometry = None

    def set_color(self, color: QColor) -> None:
        self.marker.setColor(color)
