"""Useful GIS routines using gdal and add-hoc mesh routines"""

import mimetypes
from osgeo import gdal, osr, ogr
from netCDF4 import Dataset

import matplotlib.pyplot as plt

if __name__ == 'tuflow.swangis.swangis.spatial':  # called from tuflow plugin
    from tuflow.swangis.swangis.maths import *
else:
    from swangis.maths import *


def getFeatureBoundary(shpFile, field, value):
    # get data source and layer handle
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ds = driver.Open(shpFile)
    layer = ds.GetLayer()

    # check geometry type
    if layer.GetGeomType() != 3:
        raise ValueError('Feature not polygon')

    # get field names
    fields = list()
    ld = layer.GetLayerDefn()
    for aa in range(ld.GetFieldCount()):
        fields.append(ld.GetFieldDefn(aa).GetName())
    index = fields.index(field)

    # iterate over features
    for feature in layer:
        if feature.GetField(index) == value:
            xy = np.array(feature.GetGeometryRef().GetGeometryRef(0).GetPoints())
            return xy[:, 0], xy[:, 1]


def getFeatureBoundaries(shpFile):
    # get data source and layer handle
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ds = driver.Open(shpFile)
    layer = ds.GetLayer()

    # check geometry type
    if layer.GetGeomType() != 3:
        raise ValueError('Feature not polygon')

    # iterate over features
    xy = list()
    for feature in layer:
            xy.append(np.array(feature.GetGeometryRef().GetGeometryRef(0).GetPoints()))

    return xy


def isSpherical(srs):
    """Simple wrapper for osr.SpatialReference methods"""
    if srs.IsGeographic():
        return True
    else:
        return False


def isSrsEquivalent(srsA, srsB):
    """Simple wrapper for osr.SpatialReference methods"""
    return srsA.GetName() == srsB.GetName()


def getAuthorityId(srs):
    """Simple wrapper for osr.SpatialReference methods"""
    name = srs.GetAuthorityCode(None)
    code = srs.GetAuthorityName(None)

    return name + ': ' + code


def transformPoints(inX, inY, inSrs, outSrs, grid=False):
    # https://gis.stackexchange.com/questions/201061/python-gdal-api-transformosr-coordinatetransformation

    # if SRS are the same, return input
    if isSrsEquivalent(inSrs, outSrs):
        return inX, inY

    # check to see if input is a grid
    if grid:
        if (inX.ndim == 1) and (inY.ndim == 1):
            nx, ny = len(inX), len(inY)
            inX, inY = np.meshgrid(inX, inY)
        elif(inX.ndim == 2) and (inY.ndim == 2):
            nx, ny = inX.shape[1], inY.shape[0]
        inX, inY = inX.flatten(), inY.flatten()

    # proceed with transformation
    ct = osr.CoordinateTransformation(inSrs, outSrs)

    if isSpherical(inSrs) and (not isSpherical(outSrs)):
        inPoints = np.column_stack((inY, inX))
        outPoints = np.array(ct.TransformPoints(inPoints))[:, 0:2]
        outX, outY = outPoints[:, 0], outPoints[:, 1]
    elif (not isSpherical(inSrs)) and isSpherical(outSrs):
        inPoints = np.column_stack((inX, inY))
        outPoints = np.array(ct.TransformPoints(inPoints))[:, 0:2]
        outX, outY = outPoints[:, 1], outPoints[:, 0]
    elif (not isSpherical(inSrs)) and (not isSpherical(outSrs)):
        inPoints = np.column_stack((inX, inY))
        outPoints = np.array(ct.TransformPoints(inPoints))[:, 0:2]
        outX, outY = outPoints[:, 0], outPoints[:, 1]
    elif isSpherical(inSrs) and isSpherical(outSrs):
        inPoints = np.column_stack((inX, inY))
        outPoints = np.array(ct.TransformPoints(inPoints))[:, 0:2]
        outX, outY = outPoints[:, 1], outPoints[:, 0]

    # reshape if gridded
    if grid:
        outX = np.reshape(outX, (ny, nx))
        outY = np.reshape(outY, (ny, nx))

    # return transformed coordinates
    return outX, outY



def isXmsFile(inFile):
    """Checks if file is a XMS TIN file."""

    # assume file invalid
    isValid = False

    # check file header
    try:
        with open(inFile, 'r') as f:
            h1 = f.readline()
            h2 = f.readline()

            if h1 == 'TIN' and h2 == 'BEGT':
                isValid = True
    except UnicodeDecodeError:
        pass

    return isValid


def xmsTinRead(inFile):
    """Reads an XMS TIN file. Returns (x, y, z, faces)."""

    # get file handle
    with open(inFile, 'r') as f:
        # skip header
        f.readline()
        f.readline()

        # read number of vertices
        line = f.readline().strip()
        nv = int(line.split()[-1])

        # pre-allocate x, y and z
        x = np.zeros((nv,), np.float64)
        y = np.zeros((nv,), np.float64)
        z = np.zeros((nv,), np.float32)

        # read in x, y, z
        for aa in range(nv):
            # get the entries in line
            line = f.readline().strip()
            entries = line.split()

            # store the data as floats
            x[aa] = float(entries[0])
            y[aa] = float(entries[1])
            z[aa] = float(entries[2])

        # read number of triangles
        line = f.readline().strip()
        nt = int(line.split()[-1])

        # pre-allocate triangles
        tri = np.zeros((nt, 3), np.int32)

        # read in triangles
        for aa in range(nt):
            # get the entries in line
            line = f.readline().strip()
            entries = line.split()

            # store the data as integers
            tri[aa, 0] = int(entries[0]) - 1
            tri[aa, 1] = int(entries[1]) - 1
            tri[aa, 2] = int(entries[2]) - 1

    # return TIN data
    return x, y, z, tri, None


def xmsTinWrite(outFile, x, y, z, faces):
    """Writes a set of tesselated data points (vertices) to an XMS TIN file"""

    # get counts
    nv = z.shape[0]
    nt = faces.shape[0]

    # index starts at 1
    faces = faces + 1

    # get file handle
    with open(outFile, 'w') as f:
        # write header
        f.write('TIN\nBEGT\n')

        # write vertices
        f.write('VERT {:d}\n'.format(nv))
        for aa in range(nv):
            f.write('{:.8f} {:.8f} {:.2f} 0\n'.format(x[aa], y[aa], z[aa]))

        # write triangles
        f.write('TRI {:d}\n'.format(nt))
        for aa in range(nt):
            f.write('{0:d} {1:d} {2:d}\n'.format(*list(faces[aa])))

        # write end of file
        f.write('ENDT\n')


def isFvFile(inFile):
    """Checks if file is a TUFLOW FV netCDF4 file."""

    # assume file invalid
    isValid = False

    try:
        # try to open file assuming it is netCDF4
        nc = Dataset(inFile, 'r')

        # check the 'Origin' attribute of the file
        if nc.getncattr('Origin') == 'Created by TUFLOWFV':
            isValid = True
    except (OSError, AttributeError):
        # do nothing if not netCDF4 file
        pass

    return isValid


def fvMeshRead(inFile):
    """Reads a TUFLOW FV mesh from netCDF4 file. Returns (x, y, z, faces)."""

    # check if file is TUFLOW FV result file
    if not isFvFile(inFile):
        raise ValueError('File must be TUFLOW FV netCDF4 file')

    # get netCDF4 Dataset object
    nc = Dataset(inFile, 'r')

    # read in data
    x = nc['node_X'][:].data
    y = nc['node_Y'][:].data
    z = nc['node_Zb'][:].data

    faces = nc['cell_node'][:].data - 1

    return x, y, z, faces, None


def fvMeshWrite(outFile, x, y, z, faces):
    """Writes a mesh to a TUFLOW FV netCDF4 file"""

    # get netCDF4 Dataset object
    nc = Dataset(outFile, 'w')

    # add attributes needed for file identification
    attributes = \
        {
            'Origin': 'Created by TUFLOWFV',
            'Type': 'Cell-centred TUFLOWFV output',
        }

    nc.setncatts(attributes)

    # add dimensions
    nv, nf = x.shape[0], faces.shape[0]
    nc.createDimension('NumCells2D', nf)
    nc.createDimension('NumCells3D', nf)
    nc.createDimension('NumVert2D', nv)
    nc.createDimension('NumVert3D', nv)

    nc.createDimension('MaxNumCellVert', faces.shape[1])
    nc.createDimension('NumLayerFaces3D', 2 * nf)
    nc.createDimension('Time', 0)

    # add variables
    nc.createVariable('cell_Nvert', np.int32, 'NumCells2D')
    nc.createVariable('cell_node', np.int32, ('NumCells2D', 'MaxNumCellVert'))

    nc.createVariable('node_X', np.float32, 'NumVert2D')
    nc.createVariable('node_Y', np.float32, 'NumVert2D')
    nc.createVariable('node_Zb', np.float32, 'NumVert2D')

    # count number of vertices in each cell
    NumVertices = 4*np.ones((nf,), np.int32)
    isTri = faces[:, -1] == -1
    NumVertices[isTri] = 3

    # set variables
    nc['cell_Nvert'][:] = NumVertices

    nc['node_X'][:] = x
    nc['node_Y'][:] = y
    nc['node_Zb'][:] = z

    nc['cell_node'][:] = faces + 1


def isUGridFile(inFile):
    """Checks if file is a TUFLOW FV netCDF4 output file."""

    # assume file invalid
    isValid = False

    try:
        # try to open file assuming it is netCDF4
        nc = Dataset(inFile, 'r')

        # check the 'Conventions' attribute of the file
        if 'UGRID' in nc.getncattr('Conventions'):
            isValid = True
    except (OSError, AttributeError):
        # do nothing if not netCDF4 file
        pass

    return isValid


def uGridRead(inFile):
    """Reads a TUFLOW FV mesh from netCDF4 file. Returns (x, y, z, faces)."""

    # check if file is TUFLOW FV result file
    if not isUGridFile(inFile):
        raise ValueError('File must be UGRID netCDF4 file')

    # get netCDF4 Dataset object
    nc = Dataset(inFile, 'r')

    # read in data
    x = nc['mesh2d_node_x'][:].data
    y = nc['mesh2d_node_y'][:].data
    z = nc['mesh2d_node_z'][:].data

    faces = nc['mesh2d_face_nodes'][:].data

    wkt = nc['projected_coordinate_system'].getncattr('wkt')
    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt)

    return x, y, z, faces, srs


def uGridWrite(outFile, x, y, z, faces, srs=None):
    """Writes a mesh to a UGRID netCDF4 file"""

    # get netCDF4 Dataset object
    nc = Dataset(outFile, 'w', format="NETCDF3_CLASSIC")

    # add attributes needed for file identification
    attributes = \
        {
            'source': 'MDAL 0.7.1',
            'date_created': '2020-12-06T17:11:54+1100',
            'Conventions': 'CF-1.6 UGRID-1.0'
        }

    nc.setncatts(attributes)

    # add dimensions
    nv, nf = x.shape[0], faces.shape[0]
    nc.createDimension('nmesh2d_node', nv)
    nc.createDimension('nmesh2d_face', nf)

    nc.createDimension('nmesh2d_edge', 1)
    nc.createDimension('time', 0)
    nc.createDimension('max_nmesh2d_face_nodes', faces.shape[1])

    # add variables
    nc.createVariable('mesh2d', np.int32)
    attributes  = \
        {
            'cf_role': 'mesh_topology',
            'long_name': 'Topology data of 2D network',
            'topology_dimension': 2,
            'node_coordinates': 'mesh2d_node_x mesh2d_node_y',
            'node_dimension': 'nmesh2d_node',
            'edge_dimension': 'nmesh2d_edge',
            'max_face_nodes_dimension': 'max_nmesh2d_face_nodes',
            'face_node_connectivity': 'mesh2d_face_nodes',
            'face_dimension': 'nmesh2d_face',
    }
    nc['mesh2d'].setncatts(attributes)

    nc.createVariable('mesh2d_node_x', np.float64, 'nmesh2d_node')
    nc['mesh2d_node_x'].setncatts({'standard_name': 'projection_x_coordinate',
                                   'long_name': 'x - coordinate of mesh nodes',
                                   'mesh': 'mesh2d', 'location': 'node'})

    nc.createVariable('mesh2d_node_y', np.float64, 'nmesh2d_node')
    nc['mesh2d_node_y'].setncatts({'standard_name': 'projection_y_coordinate',
                                   'long_name': 'y-coordinate of mesh nodes',
                                   'mesh': 'mesh2d', 'location': 'node'})

    nc.createVariable('mesh2d_node_z', np.float64, 'nmesh2d_node')
    nc['mesh2d_node_z'].setncatts({'mesh': 'mesh2d', 'location': 'node', 'coordinates': 'mesh2d_node_x mesh2d_node_y',
                                   'standard_name': 'altitude', 'long_name': 'z-coordinate of mesh nodes',
                                   'grid_mapping': 'projected_coordinate_system'})


    nc.createVariable('mesh2d_face_nodes', np.int32, ('nmesh2d_face', 'max_nmesh2d_face_nodes'))
    nc['mesh2d_face_nodes'].setncatts({'cf_role': 'face_node_connectivity', 'mesh': 'mesh2d', 'location': 'face',
                                       'long_name': 'Mapping from every face to its corner nodes (counterclockwise)',
                                       'start_index': 0})

    nc.createVariable('projected_coordinate_system', np.int32)
    nc.createVariable('time', np.float64, 'time')

    # set variables
    nc['mesh2d_node_x'][:] = x
    nc['mesh2d_node_y'][:] = y
    nc['mesh2d_node_z'][:] = z

    nc['mesh2d_face_nodes'][:] = faces

    nc['time'][:] = np.array([0.])

    # set SRS via wkt attribute
    if srs is not None:
        nc['projected_coordinate_system'].setncattr('wkt', srs.ExportToWkt())


def isMesh(inFile):
    checks = (isXmsFile, isFvFile, isUGridFile)
    return any([check(inFile) for check in checks])


def meshRead(inFile):
    """Reads mesh of either XMS, TUFLOW FV or UGRID format as (x, y, z, faces)"""

    # select mesh reader function
    if isXmsFile(inFile):
        reader = xmsTinRead
    elif isFvFile(inFile):
        reader = fvMeshRead
    elif isUGridFile(inFile):
        reader = uGridRead
    else:
        raise ValueError('Invalid mesh file. File must be XMS TIN, TUFLOW FV or UGRID netCDF4')

    # return mesh as (x, y, z, faces)
    return reader(inFile)


def meshInspect(inFile, xp, yp, srs=None, method='linear'):
    """Interpolates mesh elevations at points (xp, yp) using specified interpolation method"""

    # read the mesh
    x, y, z, faces, meshSrs = meshRead(inFile)

    # if input srs not None transform points
    if srs is not None:
        xp, yp = transformPoints(xp, yp, srs, meshSrs)

    # select interpolation method
    if method == 'linear':
        interpolate = linearMesh
    elif method == 'barycentric':
        interpolate = barycentricMesh
    else:
        raise ValueError('Invalid interpolation method. Method must be "linear" or "barycentric"')

    # return interpolated values
    return interpolate(x, y, z, xp, yp, faces=faces)


def meshWrite(outFile, x, y, z, faces, srs=None, format='UGRID'):

    # select mesh writer function
    if format == 'XMS':
        writer = xmsTinWrite
    elif format == 'FV':
        writer = fvMeshWrite
    elif format == 'UGRID':
        writer = uGridWrite
    else:
        raise ValueError('Invalid format. Format must be "XMS", "FV" or "UGRID"')

    # write mesh to file
    writer(outFile, x, y, z, faces, srs)


def rasterRead(inFile, band=1):

    """Simple gdal wrapper to read entire contents of raster. Note, raster data can't exceed memory."""

    # get input data source parameters
    ds = gdal.Open(inFile)
    gt = ds.GetGeoTransform()
    # n = ds.RasterCount

    # define the output grid as (x, y) with 1D arrays (use pixel centres not edges)
    x0, x2 = gt[0] + gt[1] / 2, (gt[0] + gt[1] * ds.RasterXSize) - gt[1] / 2
    y0, y2 = gt[3] + gt[5] / 2, (gt[3] + gt[5] * ds.RasterYSize) - gt[5] / 2

    x, y = np.linspace(x0, x2, ds.RasterXSize), np.linspace(y0, y2, ds.RasterYSize)

    # read in array from specified band
    b = ds.GetRasterBand(band)
    z = b.ReadAsArray().astype(float)

    # mask the array
    mask = (z == b.GetNoDataValue())
    z[mask] = np.nan

    return x, y, z


def rasterInspect(rasFile, xp, yp, srs=None, rasBand=1):

    """A basic function for inspecting a raster (nearest neighbor search) at points (xp, yp)"""

    # get data source handle
    rasDs = gdal.Open(rasFile)

    # get raster spatial reference
    rasSrs = osr.SpatialReference()
    rasSrs.ImportFromWkt(rasDs.GetProjectionRef())

    # transform points if input SRS not None
    if srs is not None:
        xp, yp = transformPoints(xp, yp, srs, rasSrs)

    # get geotransform and first band
    gt = rasDs.GetGeoTransform()
    band = rasDs.GetRasterBand(rasBand)

    # get total size
    nx = band.XSize
    ny = band.YSize

    # check if size will smash memory
    mem = nx*ny*64*10**-9

    if mem < 0.5:
        # load the entire raster and interpolate
        x, y, z = rasterRead(rasFile)
        zp = linearGrid(x, y, z, xp, yp)

        outside = ((xp < x[0]) | (xp > x[-1])) | \
                  ((yp < y[-1]) | (yp > y[0]))

        zp[outside] = np.nan
    else:
        # loop through points
        num = len(xp)
        zp = np.nan*np.zeros((num,))
        for aa in range(num):
            ix = int((xp[aa] - gt[0])/gt[1])
            iy = int((yp[aa] - gt[3])/gt[5])

            outside = ((ix < 0) or (ix >= nx)) or \
                      ((iy < 0) or (iy >= ny))

            if outside:
                zp[aa] = np.nan
            else:
                zp[aa] = rasDs.ReadAsArray(ix, iy, 1, 1)

    # mask bad data
    zp[zp == band.GetNoDataValue()] = np.nan

    # return data
    return zp


def rasterWrite():
    pass

# add one raster write and tinWrite function for check files


# example of writing rotated grid to tiff
#     driver = gdal.GetDriverByName('GTiff')
#     tifFile = outFile.replace('.txt', '.tif')
#     ds = driver.Create(tifFile, swanGrid.nx, swanGrid.ny, 1, gdal.GDT_Float32)
#
#     srs = osr.SpatialReference()
#     srs.ImportFromEPSG(4326)
#     ds.SetProjection(srs.ExportToWkt())
#
#     alpha = swanGrid.getAlpha()*np.pi/180
#
#     A = x[0, 0]
#     B = dx*np.cos(alpha)
#     C = -dx*np.sin(alpha)
#     D = y[0, 0]
#     E = dy*np.sin(alpha)
#     F = dy*np.cos(alpha)
#
#     ds.SetGeoTransform((A, B, C, D, E, F))
#
#     band = ds.GetRasterBand(1)
#
#
#     # set band no data value
#     band.SetNoDataValue(-99999)
#     band.WriteArray(np.flipud((zp0/100).astype(float)))
#
#     # flush the cache
#     band.FlushCache()
