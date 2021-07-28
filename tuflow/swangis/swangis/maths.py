"""
A few useful geometry and interpolation routines.
"""

import numpy as np

import matplotlib.path as mplPath
from matplotlib.tri import LinearTriInterpolator, Triangulation


def inPolygon(points, polygon):
    """
    Point in polygon routine that uses fast mpl Path object.

    Parameters
    ----------
    points : ndarray
        Points to test as (n, 2) array of (xp, yp)
    polygon : ndarray
        Boundary of polygon as (n, 2) array of (xp, yp)

    Returns
    -------
    logical : ndarray
        Logical index for points in polygon.
    """

    path = mplPath.Path(polygon)
    return path.contains_points(points)


def inWhichPolygon(polygons):
    """
    Finds which polygons are contained within one another.

    Parameters
    ----------
    polygons : ndarray
        Array of arrays, each of size (n, 2).

    Returns
    -------
    inside : ndarray
        Logical index of size (n, n) for polygon within polygons.
    """

    # get number of polygons
    n = len(polygons)

    # pre-allocate 'inside' logical index
    inside = np.zeros((n, n), dtype=bool)

    # cross iterate polygons
    for aa in range(n):
        for bb in range(n):
            # don't evaluate self
            if aa == bb:
                continue
            # returns true if a point in aa in bb
            lgi = inPolygon(polygons[aa], polygons[bb])
            # if all points of aa is in bb
            if np.all(lgi):
                inside[aa, bb] = True

    # inside[aa] is logical index for polygon aa
    return inside


def getInterpolationIndex(x, x1, x2):
    """Simple function to return index of array values needed to interpolate from x1 to x2"""

    # assume full domain of array needed
    ixs, ixe = 0, len(x) - 1

    # find values below and above limits
    below = np.where(x <= x1)[0]
    above = np.where(x >= x2)[0]

    # use last value below x1 if x1 > x[0]
    if len(below) != 0:
        ixs = below[-1]

    # use first value above x2 if x2 < x[-1]
    if len(above) != 0:
        ixe = above[0]

    # return indices
    return np.arange(ixs, ixe + 1)


def convertDirection(direction):
    """
    Converts from nautical to cartesian and vice versa

    Parameters
    ----------
    direction : ndarray
        Wave direction in either nautical (direction from w.r.t True North) or cartesian (direction to w.r.t x-axis)

    Returns
    -------
    converted: ndarray
        Converted wave directions as ndarray.
    """

    converted = 270 - direction

    negative = converted < 0

    converted[negative] = 360 + converted[negative]

    return converted


def getTriangleIndices(nVertices):
    """Returns indices of triangles from a polygon made of N vertices"""

    # get number of triangles
    nTriangles = nVertices - 2

    # if no triangles, return None
    if nTriangles < 1:
        return None

    # create container for indices
    indices = list()

    # start at first triangle
    a, b, c, r = 0, 1, 2, 1

    # note: r is nth revolution

    # iterate over triangles
    for ii in range(nTriangles):
        # append current triangle to list
        indices.append([a, b, c])

        # reset start point (last point of last triangle)
        a = c

        # find second and third point from first point
        b = a + r
        c = b + r

        # check for full revolution
        if c > nVertices - 1:
            r += 1
            # Case 1: last point is A (odd number)
            if a == nVertices - 1:
                b, c = 0, r
            # Case 2: last point is B (even number)
            elif b == nVertices - 1:
                c = 0

    return indices


def simplifyFaces(faces):
    """Simplifies mesh faces with N vertices to triangles with N=3."""

    # create empty array for triangles
    tFaces = np.empty((0, 3), np.int32)

    # iterate from 3 vertices to max vertices
    maxNum = faces.shape[1]
    for n in range(3, maxNum + 1):
        # get faces with n vertices
        if n != maxNum:
            nFaces = faces[faces[:, n] == -1]
        else:
            nFaces = faces[faces[:, -1] != -1]

        if nFaces.shape[0] == 0:
            continue

        # get triangle indices of shape with n vertices
        indices = getTriangleIndices(n)

        # iterate over each index and stack tri faces
        for index in indices:
            tFaces = np.vstack((tFaces, nFaces[:, index]))

    return tFaces


def linearMesh(x, y, z, xp, yp, faces=None):
    """Linear interpolation of scatter points (x, y, z) onto points (xp, yp)"""

    # simplify faces with vertices > 3
    if faces is not None:
        if faces.shape[1] > 3:
            faces = simplifyFaces(faces)

    # use matplotlib interpolator
    t = Triangulation(x, y, faces)
    i = LinearTriInterpolator(t, z)

    zp = i(xp, yp)

    return zp.data


def barycentricMesh(x, y, z, xp, yp, faces=None):
    """Barycentric interpolation of scatter points (x, y, z) onto points (xp, yp)"""

    # simplify faces with vertices > 3
    if faces is not None:
        if faces.shape[1] > 3:
            faces = simplifyFaces(faces)

    # use matplotlib object to find triangles of each point
    t = Triangulation(x, y, faces)
    i = LinearTriInterpolator(t, z)

    indices = i._trifinder(xp, yp)

    # get faces and points for valid points
    isValid = indices != -1
    pFaces = faces[indices[isValid]]
    xp, yp = xp[isValid], yp[isValid]

    # for each face, get three points
    x1, x2, x3 = x[pFaces[:, 0]], x[pFaces[:, 1]], x[pFaces[:, 2]]
    y1, y2, y3 = y[pFaces[:, 0]], y[pFaces[:, 1]], y[pFaces[:, 2]]
    z1, z2, z3 = z[pFaces[:, 0]], z[pFaces[:, 1]], z[pFaces[:, 2]]

    # get weights for each point (xp, yp)
    w1 = ((y2 - y3) * (xp - x3) + (x3 - x2) * (yp - y3)) / ((y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3))
    w2 = ((y3 - y1) * (xp - x3) + (x1 - x3) * (yp - y3)) / ((y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3))

    w3 = 1 - w1 - w2

    # sum the weights
    zp = z1*w1 + z2*w2 + z3*w3

    return zp


def checkFormat(x, y, z):
    """Basic argument checker to enforce image format"""
    if x.ndim == 2 or y.ndim == 2:
        raise ValueError('x and y arrays should be 1D, not 2D')
    if x.size != z.shape[1]:
        raise ValueError('Length of x does not match z.shape[1]')
    if y.size != z.shape[0]:
        raise ValueError('Length of y does not match z.shape[0]')
    if np.median(np.diff(y)) > 0:
        raise ValueError('Y array is not descending, flip array')


def linearGrid(x, y, z, xp, yp, grid=False):
    """Bilinear interpolation of gridded points (x, y, z) onto (xp, yp)"""

    # check input format
    checkFormat(x, y, z)

    # get index of four corners
    dx = np.median(np.diff(x))
    dy = np.median(np.diff(y))

    if grid:
        xp, yp = np.meshgrid(xp, yp)

    # map values to index space
    j = np.clip((xp - x[0]) / dx, 0, x.size - 1)
    i = np.clip((yp - y[0]) / dy, 0, y.size - 1)

    j0 = np.clip(np.floor(j), 0, x.size - 1).astype(int)
    j1 = np.clip(np.ceil(j), 0, x.size - 1).astype(int)
    i0 = np.clip(np.floor(i), 0, y.size - 1).astype(int)
    i1 = np.clip(np.ceil(i), 0, y.size - 1).astype(int)

    # get values at four corners
    f00 = z[i0, j0]
    f10 = z[i0, j1]
    f01 = z[i1, j0]
    f11 = z[i1, j1]

    # translate positions to 0 to 1
    j = j - j0
    i = i - i0

    # get weights at four corners
    w00 = (1 - j)*(1 - i)
    w10 = j*(1 - i)
    w01 = i*(1 - j)
    w11 = i*j

    # correct for NaNs
    n00 = np.isnan(f00)
    n10 = np.isnan(f10)
    n01 = np.isnan(f01)
    n11 = np.isnan(f11)

    f00[n00] = -999
    f10[n10] = -999
    f01[n01] = -999
    f11[n11] = -999

    w00[n00] = 0
    w10[n10] = 0
    w01[n01] = 0
    w11[n11] = 0

    t = (w00 + w10 + w01 + w11)
    nodata = (t == 0)

    t[nodata] = 1
    scale = 1/t

    w00 = w00*scale
    w10 = w10*scale
    w01 = w01*scale
    w11 = w11*scale

    # return interpolated values
    zp = w00*f00 + w10*f10 + w01*f01 + w11*f11
    zp[nodata] = np.nan

    return zp


