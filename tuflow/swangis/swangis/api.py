"""A module that builds on the python QGIS API. Holds all functions that interact with QGIS."""

# normal imports
import io
import os
from osgeo import osr
import numpy as np


from PyQt5.QtCore import Qt, QVariant
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMessageBox

# QGIS imports
from qgis.core import *
from qgis.utils import *

def getProject():
    """Returns current project instance"""
    return QgsProject.instance()

def getIcon(string):
    return QgsApplication.getThemeIcon(string)


def isLayer(file):

    # get all QGIS map layers (alt. iface.mapCanvas().layers())
    layers = list(QgsProject.instance().mapLayers().values())

    # reverse backslashes, QGIS paths use '/'
    file = file.replace('\\', '/')

    # iterate through layers and check source
    matchFound = False
    for layer in layers:
        if len(layer.source()) < 250:
            path = layer.source().split('|')[0]
            if file == path:
                matchFound = True

    # return if matches found
    return matchFound


def addLayer(file):
    """Helper function for loading layers into QGIS"""

    # get the name of the file
    name, _ = os.path.splitext(os.path.split(file)[1])

    # try loading as a mesh
    layer = QgsMeshLayer(file, name, 'MDAL')

    # if invalid, try loading as a raster
    if not layer.isValid():
        layer = QgsRasterLayer(file, name, 'GDAL')

    # if invalid, try loading as a vector
    if not layer.isValid():
        layer = QgsVectorLayer(file, name, 'OGR')

    if layer.isValid():
        QgsProject.instance().addMapLayer(layer)
        return layer
    else:
        return None


def removeLayer(name):
    pass


def getLayer(name):
    """Returns QGIS map layer with specified name"""

    # get all QGIS map layers (alt. iface.mapCanvas().layers())
    layers = list(QgsProject.instance().mapLayers().values())

    # reverse backslashes, QGIS paths use '/'
    name = name.replace('\\', '/')

    # find layer with specified name
    for layer in layers:
        file = layer.source().split('|')[0]
        if (layer.name() == name) or (file == name):
            return layer

    # if not found, return None
    return None


def getLayers(keys=None, useMemory=False):
    """
    Returns QGIS map layers using specified keys. keys: ['point', 'line', 'polygon', 'vector', 'raster', 'mesh']
    """

    # get all QGIS map layers (alt. iface.mapCanvas().layers())
    layers = list(QgsProject.instance().mapLayers().values())

    # if no keys are specified, return all layers
    if keys is None:
        return layers

    # get all valid object types (Class)
    types = list()
    for key in keys:
        if key in ['point', 'line', 'polygon', 'vector']:
            types.append(QgsVectorLayer)
        elif key == 'raster':
            types.append(QgsRasterLayer)
        elif key == 'mesh':
            types.append(QgsMeshLayer)

    # get all valid vector geometry types
    ids = list()
    for key in keys:
        if key == 'point':
            ids.append(0)
        elif key == 'line':
            ids.append(1)
        elif key == 'polygon':
            ids.append(2)
        elif key == 'vector':
            ids = [0, 1, 2]

    # remove invalid layers from search
    ii = 0
    while ii < len(layers):
        layer = layers[ii]
        if type(layer) not in types:
            layers.remove(layer)
        elif hasattr(layer, 'geometryType'):
            if layer.geometryType() not in ids:
                layers.remove(layer)
            else:
                ii += 1
        else:
            ii += 1

    # remove memory layers
    if not useMemory:
        ii = 0
        while ii < len(layers):
            layer = layers[ii]
            source = layer.source()
            path = source.split('|')[0]

            if len(path) > 260:
                layers.remove(layer)
            elif not os.path.exists(path):
                layers.remove(layer)
            else:
                ii += 1

    # return remaining layers
    return layers


def createSwanDomainLayer(file):

    # for some reason call to QgsVectorFileWriter() is buggy, can't add features in QGIS.

    # get project singleton
    project = QgsProject.instance()

    # get data provider string and create memory vectory layer
    string = 'Polygon?crs={}'.format(project.crs().geographicCrsAuthId())
    layer = QgsVectorLayer(string, "SWAN Domain", "memory")
    # layer.setCrs(QgsProject.instance().crs())

    # pass attributes to the data provider
    attributes = \
        [
            QgsField(name='ID', type=QVariant.Int, len=2),
            QgsField(name='Name', type=QVariant.String, len=200),
            QgsField(name='Rotation', type=QVariant.Double, len=5, prec=2),
            QgsField(name='X Length', type=QVariant.Double, len=12, prec=6),
            QgsField(name='Y Length', type=QVariant.Double, len=12, prec=6),
            QgsField(name='Num Cells', type=QVariant.Int, len=7)
        ]
    layer.dataProvider().addAttributes(attributes)

    # update the fields in the layer
    layer.updateFields()

    # write the memory layer to disk
    QgsVectorFileWriter.writeAsVectorFormat(layer, file, 'UTF-8', project.crs(), 'ESRI Shapefile')

    # Alternatively, could use QgsVectorLayerExporter

    # get layer handle from file saved to disk
    name, _ = os.path.splitext(os.path.split(file)[1])
    layer = QgsVectorLayer(file, name, 'OGR')

    # get QgsSimpleFillSymbolLayer for the QgsRenderer
    symbolLayer = layer.renderer().symbol().symbolLayers()[0]
    symbolLayer.setStrokeColor(QColor.fromRgb(255, 0, 0))
    symbolLayer.setStrokeWidth(0.4)
    symbolLayer.setBrushStyle(Qt.NoBrush)

    # add layer the project
    project.addMapLayer(layer)


def getSwanDomainLayers():
    # specify attributes to find
    findThese = ['ID', 'Name', 'Rotation', 'X Length', 'Y Length', 'Num Cells']

    # find layers with right attributes
    layers = list()
    for layer in getLayers(['polygon']):
        fields = layer.dataProvider().fields().toList()
        foundThese = [field.name() for field in fields]

        if foundThese == findThese:
            layers.append(layer)

    return layers


def getFeatures(layer):
    return [feature for feature in layer.getFeatures()]


def getExtents(layer):
    for ii in range(layer.featureCount()):
        xy = getGeometry(layer, ii)
        x, y = xy[:, 0], xy[:, 1]

        if ii == 0:
            x1, x2 = x.min(), x.max()
            y1, y2 = y.min(), y.max()
        else:
            x1 = np.min((x1, x.min()))
            x2 = np.max((x2, x.max()))

            y1 = np.min((y1, y.min()))
            y2 = np.max((y2, y.max()))

    return (x1, x2), (y1, y2)


def getSrs(layer):
    srs = osr.SpatialReference()
    srs.ImportFromWkt(layer.crs().toWkt())

    return srs


def setActiveLayer(layer):
    iface.setActiveLayer(layer)


def getVisibility(layer):
    QgsProject.instance().layerTreeRoot().findLayer(layer.id()).isVisible()


def setVisibility(layer, value):
    QgsProject.instance().layerTreeRoot().findLayer(layer.id()).setItemVisibilityChecked(value)


def getLayerOrder(layer):
    leaf = QgsProject.instance().layerTreeRoot().findLayer(layer)  # find leaf on tree
    index = leaf.parent().layerOrder().index(layer)  # use leaf's group to get index

    return leaf.parent(), index


def setLayerOrder(layer, value):
    pass

def setLayerFlags(vectorLayer, isIdentifiable=True,
    isSearchable=True, isRequired=False):
    """
    Sets the layer flags to prevent it being removed etc.

    This has been copied from:

    https://gis.stackexchange.com/questions/318506/setting-layer-identifiable-seachable-and-removable-with-python-in-qgis-3
    """

    flags = 0
    if isIdentifiable:
        flags += QgsMapLayer.Identifiable

    if isSearchable:
        flags += QgsMapLayer.Searchable

    if not isRequired:
        flags += QgsMapLayer.Removable

    vectorLayer.setFlags(QgsMapLayer.LayerFlag(flags))

def getLayerFlags(vectorLayer):
    return \
        {
            'isIdentifiable': bool(QgsMapLayer.LayerFlag(vectorLayer.flags()) & QgsMapLayer.Identifiable),
            'isSearchable': bool(QgsMapLayer.LayerFlag(vectorLayer.flags()) & QgsMapLayer.Searchable),
            'isRequired': not bool(QgsMapLayer.LayerFlag(vectorLayer.flags()) & QgsMapLayer.Removable),
        }




def getFeature(layer, fid):
    """Returns QgsFeature with given ID from QgsVectorLayer"""
    return layer.getFeature(fid)


def getGeometry(layer, fid):
    """Returns geometry of QgsFeature with given ID as (n, 2) array of points (xp, yp)"""

    # this causes QGIS to crash when called on vector layer, the problem is calling the vertices iterator
    # on called, QGIS crashes unexpectedly, alternate fetching of geometry shown below.
    # return np.array([[v.x(), v.y()] for v in getFeature(layer, fid).geometry().vertices()])

    # get the feature geometry
    g = getFeature(layer, fid).geometry()

    # convert the geometry to singular
    g.convertToSingleType()

    # get the geometry based on Wkb type, to see types QgsWkbTypes.displayString(int), int = [0, 1, 2, 3, ...]
    if g.type() == 0:
        point = g.asPoint()
        v = np.column_stack((point.x(), point.y()))
    elif g.type() == 1:
        polyline = g.asPolyline()
        x = [p.x() for p in polyline]
        y = [p.y() for p in polyline]
        v = np.column_stack((x, y))
    elif g.type() == 2:
        polygon = g.asPolygon()[0]
        x = [p.x() for p in polygon]
        y = [p.y() for p in polygon]
        v = np.column_stack((x, y))
    else:
        v = None

    return v


def getAttributes(layer, fid):
    """Returns attributes of QgsFeature as dictionary"""

    feature, attributes = getFeature(layer, fid), dict()
    for (field, value) in zip(feature.fields(), feature.attributes()):
        if value == NULL:
            attributes[field.name()] = None
        else:
            attributes[field.name()] = value

    # append geometry as attribute
    attributes['Geometry'] = getGeometry(layer, fid)

    # append SRS as attribute
    attributes['SRS'] = getSrs(layer)

    return attributes


def setAttributes(layer, fid, values):
    """Sets attributes of QgsFeature with given ID in QgsVectorLayer. Layer must be in edit mode."""
    for ii in range(len(values)):
        if values[ii] is not None:
            layer.changeAttributeValue(fid, ii, values[ii])
        else:
            layer.changeAttributeValue(fid, ii, NULL)


def createMesh(name, nodes, faces):
    # get node string as IO
    nodeIO = io.BytesIO()
    np.savetxt(nodeIO, nodes, fmt='%.6f', delimiter=',')

    # get face string as IO
    faceIO = io.BytesIO()
    np.savetxt(faceIO, faces, fmt='%d', delimiter=',')

    # add to make the URI
    uri = nodeIO.getvalue().decode('latin1') + '\n---' + faceIO.getvalue().decode('latin1')

    mesh = QgsMeshLayer(uri, name, "mesh_memory")
    mesh.setCrs(QgsProject.instance().crs())

    QgsProject.instance().addMapLayer(mesh)

    # this has to be set after its added
    rset = QgsMeshRendererSettings()
    nset = QgsMeshRendererMeshSettings()

    nset.setEnabled(True)
    nset.setColor(QColor.fromRgb(255, 0, 0))
    nset.setLineWidth(0.1)

    rset.setNativeMeshSettings(nset)
    mesh.setRendererSettings(rset)

    return mesh


def clearMesh(mesh):
    QgsProject.instance().removeMapLayer(mesh)


def updateMesh(mesh, name, nodes, faces):
    # get existing mesh attributes
    visibility = QgsProject.instance().layerTreeRoot().findLayer(mesh.id()).isVisible()  # visibility
    leaf = QgsProject.instance().layerTreeRoot().findLayer(mesh)  # find leaf on tree
    group = leaf.parent()  # group that the leaf belongs to, need this and index
    index = group.layerOrder().index(mesh)  # use leaf's group to get index
    renderer = mesh.rendererSettings()  # render settings for style

    # clear reference to leaf as this will get deleted
    leaf = None

    # remove the existing mesh from map canvas
    clearMesh(mesh)

    # create a new mesh in place of the old
    mesh = createMesh(name, nodes, faces)

    # toggle the visibility
    QgsProject.instance().layerTreeRoot().findLayer(mesh.id()).setItemVisibilityChecked(visibility)

    # shuffle the layers tree leaf to correct group and index
    leaf = QgsProject.instance().layerTreeRoot().findLayer(mesh)  # find leaf on tree
    clone = leaf.clone()  # clone that leaf
    leaf.parent().removeChildNode(leaf)  # remove from current parent
    group.insertChildNode(index, clone)  # insert to where it was before

    # set the renderer settings
    mesh.setRendererSettings(renderer)

    return mesh


def toggleRequiredAndSave():
    """Hack to stop layers made required from being saved"""

    layers = list(getProject().requiredLayers())

    if len(layers) != 0:
        for l in layers:
            setLayerFlags(l, isRequired=False)
        getProject().write()
        for l in layers:
            setLayerFlags(l, isRequired=True)




def getPolygonBounds(layer):
    pass
