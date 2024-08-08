import math
import numpy as np
from shapely import get_coordinates
from shapely.geometry.linestring import LineString


def get_first_two_points(geom):
    return get_coordinates(geom, include_z=False)[:2]


def get_last_two_points(geom):
    return get_coordinates(geom, include_z=False)[-2:]

def get_perp_offset_line_points(geom : LineString,
                                offset_dist : float,
                                width : float,
                                beginning : bool
                                ) -> LineString:
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