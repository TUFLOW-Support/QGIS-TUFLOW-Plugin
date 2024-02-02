import itertools
import re

from qgis._core import QgsProject, QgsMapLayer, QgsMeshLayer, QgsLayerTreeGroup, QgsLayerTreeLayer


def node_to_layer(node: QgsLayerTreeLayer) -> QgsMapLayer:
    layer = None
    if node is None:
        pass
    elif isinstance(node, QgsLayerTreeLayer):
        layer = node.layer()
    else:  # when opened via API, it is sometimes not given a QgsLayerTreeLayer type
        if 'LAYER:' in node.dump():
            try:
                info = {x.split('=')[0].strip(): x.split('=')[1].strip() for x in node.dump().split(' ')[2:]}
                layer = QgsProject.instance().mapLayer(info['id'])
            except (IndexError, KeyError):
                pass
    return layer


def tuflowqgis_get_geopackage_from_layer(layer):
    try:
        db, lyrname = re.split(r'\|layername=', layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE)
        return db
    except:
        return ""


def tuflowqgis_find_layer_in_datasource(datasource, layer_name, **kwargs):
    return_type = kwargs['return_type'] if 'return_type' in kwargs else 'layer'

    for name, search_layer in QgsProject.instance().mapLayers().items():
        if tuflowqgis_get_geopackage_from_layer(search_layer) == datasource and \
                search_layer.name() == layer_name:
            if return_type == 'layer':
                return search_layer
            elif return_type == 'layerid':
                return name
            elif return_type == 'name':
                return search_layer.name()
            else:
                return name
    return None


def tuflowqgis_get_all_layers_for_datasource(datasource, **kwargs):
    return_type = kwargs['return_type'] if 'return_type' in kwargs else 'layer'

    items = []

    for name, search_layer in QgsProject.instance().mapLayers().items():
        if tuflowqgis_get_geopackage_from_layer(search_layer) == datasource:
            if return_type == 'layer':
                items.append(search_layer)
            elif return_type == 'layerid':
                items.append(name)
            elif return_type == 'name':
                items.append(search_layer.name())
            else:
                items.append(name)
    return items


def tuflowqgis_find_layer(layer_name, **kwargs):
    search_type = kwargs['search_type'] if 'search_type' in kwargs.keys() else 'name'
    return_type = kwargs['return_type'] if 'return_type' in kwargs else 'layer'

    for name, search_layer in QgsProject.instance().mapLayers().items():
        if search_type.lower() == 'name':
            if search_layer.name() == layer_name:
                if return_type == 'layer':
                    return search_layer
                elif return_type == 'layerid':
                    return name
                elif return_type == 'name':
                    return search_layer.name()
                else:
                    return name
        elif search_type.lower() == 'layerid':
            if name == layer_name:
                if return_type == 'layer':
                    return search_layer
                elif return_type == 'layerid':
                    return name
                elif return_type == 'name':
                    return search_layer.name()
                else:
                    return name

        elif search_type.lower() == 'datasource':
            if search_layer.dataProvider().dataSourceUri() == layer_name:
                if return_type == 'layer':
                    return search_layer
                elif return_type == 'layerid':
                    return name
                elif return_type == 'name':
                    return search_layer.name()
                else:
                    return name

    return None


def tuflowqgis_find_plot_layers():
    plotLayers = []

    for name, search_layer in QgsProject.instance().mapLayers().items():
        if '_PLOT_P' in search_layer.name() or 'PLOT_L' in search_layer.name():
            plotLayers.append(search_layer)
        if len(plotLayers) == 2:
            return plotLayers

    if len(plotLayers) == 1:
        return plotLayers
    else:
        return None


def findAllRasterLyrs():
    """
    Finds all open raster layers

    :return: list -> str layer name
    """

    rasterLyrs = []
    for name, search_layer in QgsProject.instance().mapLayers().items():
        if search_layer.type() == QgsMapLayer.RasterLayer:
            rasterLyrs.append(search_layer.name())

    return rasterLyrs


def findAllMeshLyrs():
    """
    Finds all open mesh layers

    :return: list -> str layer name
    """

    meshLyrs = []
    for name, search_layer in QgsProject.instance().mapLayers().items():
        if isinstance(search_layer, QgsMeshLayer):
            meshLyrs.append(search_layer.name())

    return meshLyrs


def findAllVectorLyrs():
    """
    Finds all open vector layers

    :return: list -> str layer name
    """

    vectorLyrs = []
    for name, search_layer in QgsProject.instance().mapLayers().items():
        if search_layer.type() == QgsMapLayer.VectorLayer:
            vectorLyrs.append(search_layer.name())

    return vectorLyrs


def getLyrsRecursive(node, groups, vector_layers, layer_type):
    for child in node.children():
        if isinstance(child, QgsLayerTreeGroup):
            groups.append(child.name())
            getLyrsRecursive(child, groups, vector_layers, layer_type)
            # Remove the group afterward
            groups.pop()
        else:
            layer = node_to_layer(child)
            vector_layers.append((' >> '.join(itertools.chain(groups, [layer.name()])), layer.id()))

# This code wasn't working for the strange case that we get QgsLayerTreeNodes instead of QgsLayerTreeLayer
#        elif isinstance(child, QgsLayerTreeLayer):
#            if child.layer() and child.layer().type() == layer_type:
#                name = child.layer().name()
#                vector_layers.append((' >> '.join(itertools.chain(groups, [name])), child.layer().id()))


def findAllVectorLyrsWithGroups():
    """
    Finds all open vector layers

    :return: list -> (layer_tocpath:str, layer.id())
    """
    # import pydevd_pycharm
    # pydevd_pycharm.settrace('localhost', port=53110, stdoutToServer=True, stderrToServer=True)

    vectorLyrs = []

    curr_groups = []
    root = QgsProject.instance().layerTreeRoot()
    getLyrsRecursive(root, curr_groups, vectorLyrs, QgsMapLayer.VectorLayer)

    # for name, search_layer in QgsProject.instance().mapLayers().items():
    # 	if search_layer.type() == QgsMapLayer.VectorLayer:
    # 		# name = search_layer.name()
    # 		name = search_layer.legendUrl()
    # 		# if search_layer.storageType() == 'GPKG':
    # 		# 	db, layername = re.split(re.escape(r'|layername='),
    # 		# 							 search_layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE)
    # 		# 	name = f'{Path(db).name} -- {layername}'
    # 		vectorLyrs.append(name)

    return vectorLyrs
