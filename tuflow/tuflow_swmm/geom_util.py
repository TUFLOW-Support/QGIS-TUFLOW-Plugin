import math
import numpy as np
import math
try:
    from shapely import get_coordinates
    from shapely.geometry.linestring import LineString, Point
    has_shapely = True
except ImportError:
    has_shapely = False
    LineString = 'LineString'
    Point = 'Point'


def get_first_two_points(geom):
    if not has_shapely:
        raise Exception('Shapely not installed and is required for function: get_first_two_points().')
    pts = get_coordinates(geom)
    if len(pts) < 2:
        raise Exception(f'Trying to get two points from linestring with only {len(pts)} points.')
    return pts[:2]


def get_last_two_points(geom):
    if not has_shapely:
        raise Exception('Shapely not installed and is required for function: get_last_two_points().')
    return get_coordinates(geom, include_z=False)[-2:]


def get_offset_point_at_angle(geom: LineString,
                              offset_dist: float,
                              angle: float,
                              beginning: bool
                              ) -> Point:
    if not has_shapely:
        raise Exception('Shapely not installed and is required for function: get_offset_point_at_angle().')

    if beginning:
        pts = get_first_two_points(geom)[::-1]
    else:
        pts = get_last_two_points(geom)

    direction = pts[1, :] - pts[0, :]
    # print(direction)

    length = math.sqrt(np.sum(direction ** 2))
    # print(length)

    dir_norm = direction / length
    # print(dir_norm)

    dir_rotated = direction
    dir_rotated[0] = dir_norm[0] * math.cos(math.radians(angle)) - dir_norm[1] * math.sin(math.radians(angle))
    dir_rotated[1] = dir_norm[0] * math.sin(math.radians(angle)) + dir_norm[1] * math.cos(math.radians(angle))

    # rotate 180 degrees
    dir_rotated = -dir_rotated

    pt = pts[1, :] + dir_rotated * offset_dist

    return Point(pt)


def get_perp_offset_line_points(geom: LineString,
                                offset_dist: float,
                                width: float,
                                beginning: bool
                                ) -> LineString:
    if not has_shapely:
        raise Exception('Shapely not installed and is required for function: get_perp_offset_line_points().')

    if beginning:
        pts = get_first_two_points(geom)[::-1]
    else:
        pts = get_last_two_points(geom)

    direction = pts[1, :] - pts[0, :]
    # print(direction)

    length = math.sqrt(np.sum(direction ** 2))
    # print(length)

    dir_norm = direction / length
    # print(dir_norm)

    mid_offset = pts[1, :] + offset_dist * dir_norm

    perp_norm = np.flip(dir_norm)
    perp_norm[0] = -perp_norm[0]
    pt1 = mid_offset + perp_norm * (width * 0.5)
    pt2 = mid_offset - perp_norm * (width * 0.5)

    # print(pt1)
    # print(pt2)

    return LineString([pt1, pt2])


def get_line_offset_from_point(point: Point,
                               offset_dist: float,
                               width: float,
                               angle: float, ) -> LineString:
    if not has_shapely:
        raise Exception('Shapely not installed and is required for function: get_line_offset_from_point().')

    direction = np.array([math.cos(math.radians(angle)) * offset_dist,
                          math.sin(math.radians(angle)) * offset_dist])
    mid_offset = get_coordinates(point) + direction
    perm_norm = np.flip(direction/np.sqrt(np.sum(direction**2)))
    perm_norm[0] = -perm_norm[0]

    pt1 = mid_offset + perm_norm * (width * 0.5)
    pt2 = mid_offset - perm_norm * (width * 0.5)

    print(pt1)
    print(pt2)

    return LineString([pt1[0], pt2[0]])
