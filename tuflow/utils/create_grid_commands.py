import math
import sys
import traceback as TB

import numpy as np
from qgis.core import QgsGeometry, QgsWkbTypes, QgsFeature
from qgis.gui import QgsMessageBar
from qgis.core import Qgis, QgsMessageLog

from PyQt5.QtWidgets import QInputDialog, QApplication
from tuflow.tuflow_swmm.num_util import floor_to_n_digits, ceiling_to_n_digits

from .plugin import tuflow_plugin

import numpy as np

# uncomment if you need to use visualize code
#import matplotlib.pyplot as plt
#import matplotlib
#matplotlib.use('TkAgg')

# Claude AI helped with the next two functions and one commented out

def is_point_between_rays(point, origin, angle1, angle2):
    """
    Check if a point lies between two rays.
    Assumes angles are in degrees and angle2 > angle1.
    """
    # Convert point to vector from origin
    vector = point - origin
    if np.all(vector == 0):  # Skip origin point
        return False

    # Calculate angle of point vector
    point_angle = np.degrees(np.arctan2(vector[1], vector[0]))
    # Normalize to [0, 360)
    point_angle = point_angle % 360
    angle1 = angle1 % 360
    angle2 = angle2 % 360

    if angle1 < angle2:
        return angle1 <= point_angle <= angle2
    else:  # Ray 2 crosses 0/360 boundary
        return point_angle >= angle1 or point_angle <= angle2


def find_closest_grid_point(origin, angle1, angle2, grid_size=10.0, search_radius=100):
    """
    Find the closest grid point between two rays that is a multiple of grid_size
    in both x and y coordinates.
    angle assumed in degrees
    """
    # Ensure angle2 > angle1
    if angle2 < angle1:
        angle1, angle2 = angle2, angle1

    # Generate grid points to check
    x_range = np.arange(
        np.floor((origin[0] - search_radius) / grid_size) * grid_size,
        np.ceil((origin[0] + search_radius) / grid_size) * grid_size + grid_size,
        grid_size
    )
    y_range = np.arange(
        np.floor((origin[1] - search_radius) / grid_size) * grid_size,
        np.ceil((origin[1] + search_radius) / grid_size) * grid_size + grid_size,
        grid_size
    )

    min_distance = float('inf')
    best_point = None

    # Check each grid point
    for x in x_range:
        for y in y_range:
            point = np.array([x, y])
            # Skip if point is origin
            if np.all(point == origin):
                continue

            if is_point_between_rays(point, origin, angle1, angle2):
                dist = np.linalg.norm(point - origin)
                if dist < min_distance:
                    min_distance = dist
                    best_point = point

    return best_point, min_distance


# Uncomment if needed
# def visualize_solution(origin, angle1, angle2, best_point, grid_size=10.0, search_radius=50):
#     """Visualize the rays, grid, and closest point"""
#     plt.figure(figsize=(10, 10))
#
#     # Plot grid
#     x_grid = np.arange(origin[0] - search_radius, origin[0] + search_radius + grid_size, grid_size)
#     y_grid = np.arange(origin[1] - search_radius, origin[1] + search_radius + grid_size, grid_size)
#
#     for x in x_grid:
#         plt.axvline(x, color='lightgray', linestyle='-', alpha=0.5)
#     for y in y_grid:
#         plt.axhline(y, color='lightgray', linestyle='-', alpha=0.5)
#
#     # Plot rays
#     ray_length = search_radius
#     rad1 = np.radians(angle1)
#     rad2 = np.radians(angle2)
#
#     end1 = origin + ray_length * np.array([np.cos(rad1), np.sin(rad1)])
#     end2 = origin + ray_length * np.array([np.cos(rad2), np.sin(rad2)])
#
#     plt.plot([origin[0], end1[0]], [origin[1], end1[1]], 'b-', label='Ray 1')
#     plt.plot([origin[0], end2[0]], [origin[1], end2[1]], 'r-', label='Ray 2')
#
#     # Plot points
#     if best_point is not None:
#         plt.plot(best_point[0], best_point[1], 'go', markersize=10, label='Closest Grid Point')
#         plt.plot([origin[0], best_point[0]], [origin[1], best_point[1]], 'g--', label='Distance')
#
#     plt.plot(origin[0], origin[1], 'ko', label='Origin')
#
#     plt.axis('equal')
#     plt.grid(True)
#     plt.legend()
#     plt.title('Closest Grid Point Between Rays')
#
#     return plt


def compute_shifted_origin(angle, origin) -> np.array:
    # We want to shift the origin to be a nice round number but has to be smaller than the
    # computed origin in rotated space (which isn't always simple to figure out)

    # We form two rays opposite the axes and find the nearest point between them to guarantee it will give a
    # good starting point (outside the grid) and round number
    return find_closest_grid_point(origin, angle + 180.0, angle + 270.0, grid_size=10.0, search_radius=100)[0]


def create_grid_commands() -> None:
    iface = tuflow_plugin().iface
    angle, ok = QInputDialog.getDouble(iface.mainWindow(),
                                       "TUFLOW Create Grid Commands -- Grid Angle",
                                       "Enter the Grid Orientation Angle in Degrees from X-axis (-360 to 360)",
                                       value=0.0,
                                       min=-360.0,
                                       max=360.0,
                                       decimals=1)

    if not ok:
        return
    extent = iface.activeLayer().extent()
    center = extent.center()

    calculator = ExtentCalculator(-angle, center)
    if not apply_to_active_layer(iface, calculator.process_vertex):
        return

    # Format results
    extent = {
        'min_x': calculator.min_x + center.x(),
        'max_x': calculator.max_x + center.x(),
        'min_y': calculator.min_y + center.y(),
        'max_y': calculator.max_y + center.y(),
        'width': calculator.max_x - calculator.min_x,
        'height': calculator.max_y - calculator.min_y
    }
    command = f"Origin == {', '.join([str(int(x)) for x in calculator.get_origin()])}\n" \
              f"Orientation angle == {angle}\n" \
              f"Grid Size (X,Y) == {', '.join([str(int(x)) for x in calculator.get_grid_size()])}\n"
    QApplication.clipboard().setText(command)


class ExtentCalculator:
    def __init__(self, angle, center):
        self.angle = math.radians(angle)
        self.arr_rotation = np.array(
            [
                [math.cos(self.angle), -math.sin(self.angle)],
                [math.sin(self.angle), math.cos(self.angle)]
            ]
        )
        self.center = center
        self.center_arr = np.array([self.center.x(), self.center.y()])
        self.min_x = sys.float_info.max
        self.max_x = -sys.float_info.max
        self.min_y = sys.float_info.max
        self.max_y = -sys.float_info.max

    def get_origin(self):
        """Gets the origin back in real world coordinates"""
        return compute_shifted_origin(-math.degrees(self.angle), self.get_origin_no_shift())

    def get_origin_no_shift(self):
        """Gets the origin without any rounding"""
        min_points = [self.min_x, self.min_y]
        min_rotated = np.dot(self.arr_rotation.T, min_points)
        return [min_rotated[0] + self.center.x(),
                min_rotated[1] + self.center.y()]

    def get_grid_size(self):
        """Get the grid size account for shifts that occur when we round"""
        shift_grid = np.dot(self.arr_rotation, np.array(self.get_origin_no_shift()) - self.center_arr) - \
                     np.dot(self.arr_rotation, np.array(self.get_origin()) - self.center_arr)
        return [
            ceiling_to_n_digits(self.max_x - self.min_x + abs(shift_grid[0]), 1),
            ceiling_to_n_digits(self.max_y - self.min_y + abs(shift_grid[1]), 1),
        ]

    def process_vertex(self, vertex):
        """Update min/max values for each vertex"""

        rotated = np.dot(self.arr_rotation, np.array([vertex.x() - self.center.x(), vertex.y() - self.center.y()]))
        x = rotated[0]
        y = rotated[1]
        self.min_x = min(self.min_x, x)
        self.max_x = max(self.max_x, x)
        self.min_y = min(self.min_y, y)
        self.max_y = max(self.max_y, y)


def process_polygon_vertices(iface, layer, vertex_function) -> bool:
    """
    Process all vertices in a polygon layer with a custom function

    Args:
        layer: QgsVectorLayer - The polygon layer to process
        vertex_function: function - Custom function that takes a QgsPointXY as input

    Returns:
        bool: Successful
    """
    try:
        # Iterate through all features in the layer
        for feature in layer.getFeatures():
            geometry = feature.geometry()

            if geometry.type() != QgsWkbTypes.PolygonGeometry:
                continue

            # Convert to multi-part if it's not already
            if geometry.isMultipart():
                polygons = geometry.asMultiPolygon()
            else:
                polygons = [geometry.asPolygon()]

            # Process each polygon
            for polygon in polygons:
                # Process each ring (exterior and interior boundaries)
                for ring in polygon:
                    # Process each vertex in the ring
                    for vertex in ring:
                        vertex_function(vertex)

    except Exception as e:
        # Show error message if something goes wrong
        exc_type, exc_value, exc_traceback = sys.exc_info()
        iface.messageBar().pushCritical(
            "Error",
            f"Error processing vertices: {str(e)} {TB.format_exception(exc_type, exc_value, exc_traceback)}"
        )
        return False

    return True


def apply_to_active_layer(iface, vertex_function) -> bool:
    """
    Apply custom function to vertices of active layer

    Args:
        iface: The QGIS interface
        vertex_function: function - Custom function that takes a QgsPointXY as input
    Returns:
        bool: True - Successful operation
    """
    # Get the active layer
    layer = iface.activeLayer()

    if layer is None:
        iface.messageBar().pushWarning(
            "Warning",
            "No active layer selected"
        )
        return False

    if layer.geometryType() != QgsWkbTypes.PolygonGeometry:
        iface.messageBar().pushWarning(
            "Warning",
            "Selected layer is not a polygon layer"
        )
        return False

    # Process the layer
    return process_polygon_vertices(iface, layer, vertex_function)
